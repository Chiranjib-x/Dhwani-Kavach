import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch import Tensor

from ml.audio_utils import SAMPLE_RATE, CHUNK_SAMPLES, preprocess


# ── Sinc filter bank (no learnable params -> not in checkpoint) ──────────────

class _SincConv(nn.Module):
    @staticmethod
    def _to_mel(hz):
        return 2595 * np.log10(1 + hz / 700)

    @staticmethod
    def _to_hz(mel):
        return 700 * (10 ** (mel / 2595) - 1)

    def __init__(self, out_channels, kernel_size, sample_rate=16000):
        super().__init__()
        if kernel_size % 2 == 0:
            kernel_size += 1
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.sample_rate = sample_rate

        NFFT = 512
        f = int(sample_rate / 2) * np.linspace(0, 1, int(NFFT / 2) + 1)
        fmel = self._to_mel(f)
        filbw = np.linspace(np.min(fmel), np.max(fmel), out_channels + 1)
        filbw_hz = self._to_hz(filbw)

        hsupp = torch.arange(-(kernel_size - 1) / 2, (kernel_size - 1) / 2 + 1)
        band_pass = torch.zeros(out_channels, kernel_size)
        for i in range(len(filbw_hz) - 1):
            fmin, fmax = filbw_hz[i], filbw_hz[i + 1]
            hH = (2 * fmax / sample_rate) * np.sinc(2 * fmax * hsupp.numpy() / sample_rate)
            hL = (2 * fmin / sample_rate) * np.sinc(2 * fmin * hsupp.numpy() / sample_rate)
            band_pass[i] = Tensor(np.hamming(kernel_size)) * Tensor(hH - hL)
        self.band_pass = band_pass

    def forward(self, x):
        filters = self.band_pass.clone().to(x.device).view(self.out_channels, 1, self.kernel_size)
        return F.conv1d(x, filters, stride=1, padding=0, bias=None)


# ── 2-D Residual block ───────────────────────────────────────────────────────

class _ResBlock(nn.Module):
    def __init__(self, nb_filts, first=False):
        super().__init__()
        self.first = first
        if not first:
            self.bn1 = nn.BatchNorm2d(nb_filts[0])
        self.conv1 = nn.Conv2d(nb_filts[0], nb_filts[1], kernel_size=(2, 3), padding=(1, 1))
        self.selu = nn.SELU(inplace=True)
        self.bn2 = nn.BatchNorm2d(nb_filts[1])
        self.conv2 = nn.Conv2d(nb_filts[1], nb_filts[1], kernel_size=(2, 3), padding=(0, 1))
        self.downsample = nb_filts[0] != nb_filts[1]
        if self.downsample:
            self.conv_downsample = nn.Conv2d(nb_filts[0], nb_filts[1], kernel_size=(1, 3), padding=(0, 1))
        self.mp = nn.MaxPool2d((1, 3))

    def forward(self, x):
        identity = x
        out = x if self.first else self.selu(self.bn1(x))
        out = self.conv1(out)
        out = self.selu(self.bn2(out))
        out = self.conv2(out)
        if self.downsample:
            identity = self.conv_downsample(identity)
        out = out + identity
        return self.mp(out)


# ── Homogeneous Graph Attention Layer ────────────────────────────────────────

class _GAT(nn.Module):
    def __init__(self, in_dim, out_dim, temperature=1.0):
        super().__init__()
        self.temp = temperature
        self.att_proj = nn.Linear(in_dim, out_dim)
        self.att_weight = nn.Parameter(torch.empty(out_dim, 1))
        nn.init.xavier_normal_(self.att_weight)
        self.proj_with_att = nn.Linear(in_dim, out_dim)
        self.proj_without_att = nn.Linear(in_dim, out_dim)
        self.bn = nn.BatchNorm1d(out_dim)
        self.input_drop = nn.Dropout(0.2)
        self.act = nn.SELU(inplace=True)

    def forward(self, x):
        x = self.input_drop(x)
        nb = x.size(1)
        x_exp = x.unsqueeze(2).expand(-1, -1, nb, -1)
        att = torch.tanh(self.att_proj(x_exp * x_exp.transpose(1, 2)))
        att = F.softmax(torch.matmul(att, self.att_weight) / self.temp, dim=-2)
        out = self.proj_with_att(torch.matmul(att.squeeze(-1), x)) + self.proj_without_att(x)
        s = out.size()
        return self.act(self.bn(out.view(-1, s[-1])).view(s))


# ── Heterogeneous Graph Attention Layer ──────────────────────────────────────

class _HtrgGAT(nn.Module):
    def __init__(self, in_dim, out_dim, temperature=1.0):
        super().__init__()
        self.temp = temperature
        self.proj_type1 = nn.Linear(in_dim, in_dim)
        self.proj_type2 = nn.Linear(in_dim, in_dim)
        self.att_proj = nn.Linear(in_dim, out_dim)
        self.att_projM = nn.Linear(in_dim, out_dim)
        self.att_weight11 = nn.Parameter(torch.empty(out_dim, 1))
        self.att_weight22 = nn.Parameter(torch.empty(out_dim, 1))
        self.att_weight12 = nn.Parameter(torch.empty(out_dim, 1))
        self.att_weightM = nn.Parameter(torch.empty(out_dim, 1))
        for p in [self.att_weight11, self.att_weight22, self.att_weight12, self.att_weightM]:
            nn.init.xavier_normal_(p)
        self.proj_with_att = nn.Linear(in_dim, out_dim)
        self.proj_without_att = nn.Linear(in_dim, out_dim)
        self.proj_with_attM = nn.Linear(in_dim, out_dim)
        self.proj_without_attM = nn.Linear(in_dim, out_dim)
        self.bn = nn.BatchNorm1d(out_dim)
        self.input_drop = nn.Dropout(0.2)
        self.act = nn.SELU(inplace=True)

    def forward(self, x1, x2, master=None):
        n1, n2 = x1.size(1), x2.size(1)
        x1 = self.proj_type1(x1)
        x2 = self.proj_type2(x2)
        x = torch.cat([x1, x2], dim=1)
        if master is None:
            master = torch.mean(x, dim=1, keepdim=True)
        x = self.input_drop(x)

        nb = x.size(1)
        x_exp = x.unsqueeze(2).expand(-1, -1, nb, -1)
        am = torch.tanh(self.att_proj(x_exp * x_exp.transpose(1, 2)))
        board = torch.zeros_like(am[..., 0:1])
        board[:, :n1, :n1] = torch.matmul(am[:, :n1, :n1], self.att_weight11)
        board[:, n1:, n1:] = torch.matmul(am[:, n1:, n1:], self.att_weight22)
        board[:, :n1, n1:] = torch.matmul(am[:, :n1, n1:], self.att_weight12)
        board[:, n1:, :n1] = torch.matmul(am[:, n1:, :n1], self.att_weight12)
        am = F.softmax(board / self.temp, dim=-2)

        am_m = torch.tanh(self.att_projM(x * master))
        am_m = F.softmax(torch.matmul(am_m, self.att_weightM) / self.temp, dim=-2)
        master = (self.proj_with_attM(torch.matmul(am_m.squeeze(-1).unsqueeze(1), x)) +
                  self.proj_without_attM(master))

        out = self.proj_with_att(torch.matmul(am.squeeze(-1), x)) + self.proj_without_att(x)
        s = out.size()
        out = self.act(self.bn(out.view(-1, s[-1])).view(s))
        return out.narrow(1, 0, n1), out.narrow(1, n1, n2), master


# ── Attention-based graph pooling ────────────────────────────────────────────

class _GraphPool(nn.Module):
    def __init__(self, k, in_dim, p=0.3):
        super().__init__()
        self.k = k
        self.proj = nn.Linear(in_dim, 1)
        self.drop = nn.Dropout(p) if p > 0 else nn.Identity()

    def forward(self, h):
        scores = torch.sigmoid(self.proj(self.drop(h)))
        n_keep = max(int(h.size(1) * self.k), 1)
        idx = torch.topk(scores, n_keep, dim=1)[1].expand(-1, -1, h.size(-1))
        return torch.gather(h * scores, 1, idx)


# ── Full AASIST model ────────────────────────────────────────────────────────

_D_ARGS = {
    "first_conv": 128,
    "filts": [70, [1, 32], [32, 32], [32, 64], [64, 64]],
    "gat_dims": [64, 32],
    "pool_ratios": [0.5, 0.7, 0.5, 0.5],
    "temperatures": [2.0, 2.0, 100.0, 100.0],
}


class AASISTModel(nn.Module):
    def __init__(self, d_args=None):
        super().__init__()
        if d_args is None:
            d_args = _D_ARGS
        filts = d_args["filts"]
        gat_dims = d_args["gat_dims"]
        pool_ratios = d_args["pool_ratios"]
        temps = d_args["temperatures"]

        self.conv_time = _SincConv(filts[0], d_args["first_conv"])
        self.first_bn = nn.BatchNorm2d(1)
        self.drop = nn.Dropout(0.5, inplace=True)
        self.drop_way = nn.Dropout(0.2, inplace=True)
        self.selu = nn.SELU(inplace=True)

        self.encoder = nn.Sequential(
            nn.Sequential(_ResBlock(filts[1], first=True)),
            nn.Sequential(_ResBlock(filts[2])),
            nn.Sequential(_ResBlock(filts[3])),
            nn.Sequential(_ResBlock(filts[4])),
            nn.Sequential(_ResBlock(filts[4])),
            nn.Sequential(_ResBlock(filts[4])),
        )

        self.pos_S = nn.Parameter(torch.randn(1, 23, filts[-1][-1]))
        self.master1 = nn.Parameter(torch.randn(1, 1, gat_dims[0]))
        self.master2 = nn.Parameter(torch.randn(1, 1, gat_dims[0]))

        self.GAT_layer_S = _GAT(filts[-1][-1], gat_dims[0], temps[0])
        self.GAT_layer_T = _GAT(filts[-1][-1], gat_dims[0], temps[1])

        self.HtrgGAT_layer_ST11 = _HtrgGAT(gat_dims[0], gat_dims[1], temps[2])
        self.HtrgGAT_layer_ST12 = _HtrgGAT(gat_dims[1], gat_dims[1], temps[2])
        self.HtrgGAT_layer_ST21 = _HtrgGAT(gat_dims[0], gat_dims[1], temps[2])
        self.HtrgGAT_layer_ST22 = _HtrgGAT(gat_dims[1], gat_dims[1], temps[2])

        self.pool_S = _GraphPool(pool_ratios[0], gat_dims[0], 0.3)
        self.pool_T = _GraphPool(pool_ratios[1], gat_dims[0], 0.3)
        self.pool_hS1 = _GraphPool(pool_ratios[2], gat_dims[1], 0.3)
        self.pool_hT1 = _GraphPool(pool_ratios[2], gat_dims[1], 0.3)
        self.pool_hS2 = _GraphPool(pool_ratios[2], gat_dims[1], 0.3)
        self.pool_hT2 = _GraphPool(pool_ratios[2], gat_dims[1], 0.3)

        self.out_layer = nn.Linear(5 * gat_dims[1], 2)

    def forward(self, x):
        # x: (batch, N) raw waveform
        x = self.conv_time(x.unsqueeze(1))          # (B, 70, T')
        x = x.unsqueeze(1)                           # (B, 1, 70, T')
        x = F.max_pool2d(torch.abs(x), (3, 3))       # (B, 1, 23, T'')
        x = self.selu(self.first_bn(x))

        e = self.encoder(x)                          # (B, 64, 23, T_enc)

        e_S = torch.max(torch.abs(e), dim=3)[0].transpose(1, 2) + self.pos_S
        gat_S = self.GAT_layer_S(e_S)
        out_S = self.pool_S(gat_S)

        e_T = torch.max(torch.abs(e), dim=2)[0].transpose(1, 2)
        gat_T = self.GAT_layer_T(e_T)
        out_T = self.pool_T(gat_T)

        master1 = self.master1.expand(x.size(0), -1, -1)
        master2 = self.master2.expand(x.size(0), -1, -1)

        out_T1, out_S1, master1 = self.HtrgGAT_layer_ST11(out_T, out_S, master=master1)
        out_S1 = self.pool_hS1(out_S1)
        out_T1 = self.pool_hT1(out_T1)
        out_T_a, out_S_a, master1_a = self.HtrgGAT_layer_ST12(out_T1, out_S1, master=master1)
        out_T1, out_S1, master1 = out_T1 + out_T_a, out_S1 + out_S_a, master1 + master1_a

        out_T2, out_S2, master2 = self.HtrgGAT_layer_ST21(out_T, out_S, master=master2)
        out_S2 = self.pool_hS2(out_S2)
        out_T2 = self.pool_hT2(out_T2)
        out_T_a, out_S_a, master2_a = self.HtrgGAT_layer_ST22(out_T2, out_S2, master=master2)
        out_T2, out_S2, master2 = out_T2 + out_T_a, out_S2 + out_S_a, master2 + master2_a

        out_T1, out_T2 = self.drop_way(out_T1), self.drop_way(out_T2)
        out_S1, out_S2 = self.drop_way(out_S1), self.drop_way(out_S2)
        master1, master2 = self.drop_way(master1), self.drop_way(master2)

        out_T = torch.max(out_T1, out_T2)
        out_S = torch.max(out_S1, out_S2)
        master = torch.max(master1, master2)

        T_max = torch.max(torch.abs(out_T), dim=1)[0]
        T_avg = torch.mean(out_T, dim=1)
        S_max = torch.max(torch.abs(out_S), dim=1)[0]
        S_avg = torch.mean(out_S, dim=1)

        last_hidden = self.drop(
            torch.cat([T_max, T_avg, S_max, S_avg, master.squeeze(1)], dim=1)
        )
        return last_hidden, self.out_layer(last_hidden)


# ── Public interface ─────────────────────────────────────────────────────────

def load_aasist(model_path: str, device: str = "cpu") -> AASISTModel:
    model = AASISTModel()
    state = torch.load(model_path, map_location=device)
    if isinstance(state, dict) and "model" in state:
        state = state["model"]
    elif isinstance(state, dict) and "state_dict" in state:
        state = state["state_dict"]
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model


def infer(model: AASISTModel, audio: np.ndarray, device: str = "cpu") -> float:
    """Return spoof probability in [0, 1]; higher = more likely fake."""
    audio = preprocess(audio)
    x = torch.from_numpy(audio).unsqueeze(0).to(device)  # (1, 64000)
    model.eval()
    with torch.no_grad():
        _, logits = model(x)
        prob = torch.softmax(logits, dim=1)[0, 1].item()
    return float(prob)
