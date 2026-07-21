"""XLSR-SLS neural detector -- ported public SOTA checkpoint, zero fairseq.

Architecture (Zhang et al., ACM MM 2024): full wav2vec2-xls-r-300m (all 24
encoder layers, fine-tuned) + a tiny Sensitive-Layer-Selection head that
attention-weights the 24 per-layer outputs. Published: 1.92% EER ASVspoof21-DF,
7.46% In-the-Wild -- the best open-weights generalization to real-world
varied-mic/room audio we found, which is exactly the live-mic channel our
home-trained bundle collapses on.

Weights: models/xlsr_sls.safetensors, produced once by tools/port_sls.py from
the public fairseq checkpoint (HF sukhdeveyash/XLS-R-SLS-Deepfake-Detection).

Faithfulness notes (each verified against their model.py / transformers source):
- Input is repeat-padded to 64600 samples and fed RAW -- their pipeline does
  NOT zero-mean/unit-var normalize (deviates from XLS-R pretraining, but the
  checkpoint was FINE-TUNED that way, so inference must match).
- The SLS head consumes fairseq layer_results == per-layer outputs WITHOUT the
  encoder's final layer_norm. HF applies that norm to hidden_states[24], so we
  replace encoder.layer_norm with Identity (same trick detector_v2 uses).
- Their label convention is bonafide=1/spoof=0 (Tak-style, OPPOSITE of
  detector_v2's Codecfake head), so spoof prob = softmax(logits)[:, 0].
  Empirically confirmed on the labeled sample_audio set.
"""
from __future__ import annotations

import math
import os

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

from ml.audio_utils import repeat_pad

_BUNDLE = os.environ.get("DHWANI_SLS_MODEL") or os.path.join(
    os.path.dirname(__file__), "..", "models", "xlsr_sls.safetensors")
_BASE_ID = "facebook/wav2vec2-xls-r-300m"
_CUT = 64600         # ASVspoof convention, same as detector_v2
_N_LAYERS = 24
_SPOOF_INDEX = 0     # Tak-style: bonafide=1, spoof=0

_backbone = None
_head = None


class SLSHead(nn.Module):
    """Verbatim reimplementation of their Model's post-SSL layers (state-dict
    compatible: first_bn/fc0/fc1/fc3). Input: (B, 24, T, 1024) stacked
    per-layer hidden states; T must be 201 (i.e. 64600 samples) because
    fc1's 22847 = (201//3) * (1024//3) after the 3x3 max-pool."""

    def __init__(self):
        super().__init__()
        self.first_bn = nn.BatchNorm2d(num_features=1)
        self.fc0 = nn.Linear(1024, 1)
        self.fc1 = nn.Linear(22847, 1024)
        self.fc3 = nn.Linear(1024, 2)

    def forward(self, layers: torch.Tensor) -> torch.Tensor:
        pooled = layers.mean(dim=2)                       # (B, 24, 1024) == adaptive_avg_pool1d(.,1)
        y0 = torch.sigmoid(self.fc0(pooled))              # (B, 24, 1)
        y0 = y0.unsqueeze(-1)                             # (B, 24, 1, 1)
        full = (layers * y0).sum(dim=1)                   # (B, T, 1024)
        x = full.unsqueeze(1)                             # (B, 1, T, 1024)
        x = F.selu(self.first_bn(x))
        x = F.max_pool2d(x, (3, 3))
        x = torch.flatten(x, 1)                           # (B, 22847)
        x = F.selu(self.fc1(x))
        return F.selu(self.fc3(x))                        # logits (B, 2); col 0 = spoof


def available() -> bool:
    return os.path.exists(_BUNDLE)


def _build_backbone():
    """Config-only Wav2Vec2Model (no stock-weight download/warning), final
    layer_norm neutralized so hidden_states[24] == the un-normed layer-24
    output that SLS trained on. Exposed for tools/port_sls.py."""
    from transformers import Wav2Vec2Config, Wav2Vec2Model
    # vendored config (backend/models/xlsr_300m_config.json): the architecture is
    # fixed, and reading it locally keeps the backend bootable with no network.
    cfg = Wav2Vec2Config.from_json_file(os.path.join(
        os.path.dirname(__file__), "..", "models", "xlsr_300m_config.json"))
    cfg.output_hidden_states = True
    m = Wav2Vec2Model(cfg)
    m.encoder.layer_norm = nn.Identity()
    m.eval()
    return m


def _get():
    global _backbone, _head
    if _backbone is None:
        from safetensors.torch import load_file
        sd = load_file(_BUNDLE)
        m = _build_backbone()
        m.load_state_dict({k[len("backbone."):]: v for k, v in sd.items()
                           if k.startswith("backbone.")})
        h = SLSHead()
        h.load_state_dict({k[len("head."):]: v for k, v in sd.items()
                           if k.startswith("head.")})
        h.eval()
        _backbone, _head = m, h
    return _backbone, _head


def infer_batch(audios: list[np.ndarray]) -> list[float]:
    """Spoof probabilities in [0, 1] for several 16 kHz mono windows in one
    forward pass. Higher = more likely fake. RAW input, no normalization
    (matches the checkpoint's training -- see module docstring)."""
    if not audios:
        return []
    x = torch.from_numpy(np.stack(
        [repeat_pad(a, length=_CUT) for a in audios]).astype(np.float32))
    backbone, head = _get()
    with torch.no_grad():
        hs = backbone(x).hidden_states          # 25 tuples; [1..24] = per-layer outputs
        layers = torch.stack(hs[1:_N_LAYERS + 1], dim=1)   # (B, 24, T, 1024)
        logits = head(layers)
        probs = torch.softmax(logits, dim=1)[:, _SPOOF_INDEX]
    return [float(p) for p in probs]


def infer(audio: np.ndarray) -> float:
    return infer_batch([audio])[0]


def infer_raw(audio: np.ndarray) -> tuple[float, float]:
    """(spoof_prob, logit) -- same contract as detector_v2.infer_raw, consumed
    by tools/fit_calibration.py."""
    p = infer(audio)
    p_c = min(max(p, 1e-6), 1.0 - 1e-6)
    return p, math.log(p_c / (1.0 - p_c))


if __name__ == "__main__":
    # Self-check: model loads, shapes hold, output is a sane probability, and
    # batch == per-item (BatchNorm eval mode means items must not interact).
    if not available():
        print(f"bundle absent ({_BUNDLE}); run tools/port_sls.py first")
        raise SystemExit(0)
    rng = np.random.default_rng(0)
    a = (0.05 * rng.standard_normal(16000 * 4)).astype(np.float32)
    b = (0.05 * rng.standard_normal(16000 * 3)).astype(np.float32)
    pa, pb = infer(a), infer(b)
    assert 0.0 <= pa <= 1.0 and 0.0 <= pb <= 1.0, (pa, pb)
    pair = infer_batch([a, b])
    assert abs(pair[0] - pa) < 1e-4 and abs(pair[1] - pb) < 1e-4, (pair, pa, pb)
    print(f"detector_v4 self-check ok (noise probes: {pa:.4f}, {pb:.4f})")
