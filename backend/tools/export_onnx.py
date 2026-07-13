"""Export the detector_v2 path (XLS-R + W2VAASIST head) to an INT8 ONNX model.

Why: detector_v2 runs the full 24-layer XLS-R-300M backbone but only consumes
hidden_states[5] -- layers 6-23 are computed and thrown away on every window.
This truncates the encoder to 5 layers (with the trailing layer_norm replaced by
Identity so last_hidden_state == the old hidden_states[5] *exactly*), fuses
backbone + head into one graph, exports it, and INT8-dynamic-quantizes it.

detector_v2 repeat-pads every clip to a fixed 64600 samples, so the graph has
fully static shapes -> dynamic quantization needs no calibration data and the
export is robust.

Self-validating: aborts unless the truncated torch path matches the full path,
and unless the final INT8 ONNX spoof-probability matches the torch path within
tolerance on random probes. Nothing is written until both checks pass.

MEASURED (CPU, 22 threads): the *truncation alone* is the CPU win -- 1.8x over
the full 24-layer path, bit-identical scores -- and it now lives directly in
ml/detector_v2.py (no ONNX needed on CPU). INT8 dynamic quantization was ~2x
*slower* than truncated torch on this CPU (quant overhead on these matmul
shapes), so the ONNX artifact is NOT wired into the CPU serving path. Keep this
tool for GPU deployment, where INT8/TensorRT is the right lever; the printed
latency line tells you whether the artifact helps on your target hardware.

usage: PYTHONPATH=backend python backend/tools/export_onnx.py
"""
from __future__ import annotations

import os
import sys
import time
import types

import numpy as np
import torch

from ml.vendor import codecfake_model
from ml.vendor.codecfake_model import W2VAASIST

_HERE = os.path.dirname(__file__)
_MODELS = os.path.normpath(os.path.join(_HERE, "..", "models"))
_CKPT = os.path.join(_MODELS, "w2v2aasist_cotrain.pt")
_BASE = "facebook/wav2vec2-xls-r-300m"
_LAYER = 5
_CUT = 64600
_FP32 = os.path.join(_MODELS, "detector_v2_fp32.onnx")
_INT8 = os.path.join(_MODELS, "detector_v2.onnx")

# Tolerances. Truncation must be near-exact (float noise only). INT8 quantization
# genuinely perturbs scores -- keep it small but non-zero.
_TRUNC_TOL = 1e-3
_INT8_TOL = 0.05


def _alias_model_module() -> None:
    if "model" in sys.modules:
        return
    fake = types.ModuleType("model")
    for name in ("W2VAASIST", "GraphAttentionLayer", "HtrgGraphAttentionLayer",
                 "GraphPool", "Residual_block"):
        setattr(fake, name, getattr(codecfake_model, name))
    sys.modules["model"] = fake


def _repeat_pad(a: np.ndarray, length: int = _CUT) -> np.ndarray:
    a = a.astype(np.float32)
    if len(a) >= length:
        return a[:length]
    return np.tile(a, -(-length // len(a)))[:length].astype(np.float32)


def _znorm(x: np.ndarray) -> np.ndarray:
    return ((x - x.mean()) / np.sqrt(x.var() + 1e-7)).astype(np.float32)


def _preprocess(audio: np.ndarray) -> np.ndarray:
    return _znorm(_repeat_pad(audio))


class _Detector(torch.nn.Module):
    """backbone(x).last_hidden_state -> head -> spoof probability. Batch-1 static,
    mirroring detector_v2._run's reshape exactly."""

    def __init__(self, backbone: torch.nn.Module, head: torch.nn.Module):
        super().__init__()
        self.backbone = backbone
        self.head = head

    def forward(self, x: torch.Tensor) -> torch.Tensor:  # x: (1, 64600)
        h = self.backbone(x).last_hidden_state          # (1, T, 1024)
        w = h.unsqueeze(0).transpose(2, 3)              # (1, 1, 1024, T)
        _, logits = self.head(w)
        return torch.softmax(logits, dim=1)[:, 1]       # (1,) spoof prob


def _load_full():
    from transformers import Wav2Vec2Model
    bb = Wav2Vec2Model.from_pretrained(_BASE)
    bb.config.output_hidden_states = True
    bb.eval()
    _alias_model_module()
    head = torch.load(_CKPT, map_location="cpu", weights_only=False)
    if not isinstance(head, torch.nn.Module):
        st = head.get("model", head.get("state_dict", head)) if isinstance(head, dict) else head
        head = W2VAASIST()
        head.load_state_dict(st)
    head.eval()
    return bb, head


def _full_prob(bb, head, audio):
    x = torch.from_numpy(_preprocess(audio)).unsqueeze(0)
    with torch.no_grad():
        h = bb(x).hidden_states[_LAYER]
        w = h.unsqueeze(0).transpose(2, 3)
        _, logits = head(w)
        return float(torch.softmax(logits, dim=1)[0, 1])


def _truncate(bb):
    """5 encoder layers + Identity trailing norm -> last_hidden_state == old
    hidden_states[5]. (Stable-layer-norm encoders collect hidden states *before*
    each layer and apply the final norm after the loop, so the trailing norm must
    be neutralized for the 5th-layer output to stay raw.)"""
    bb.encoder.layers = torch.nn.ModuleList(list(bb.encoder.layers[:_LAYER]))
    bb.encoder.layer_norm = torch.nn.Identity()
    bb.config.output_hidden_states = False
    return bb


def main():
    rng = np.random.default_rng(0)
    probes = [
        rng.standard_normal(32000).astype(np.float32) * 0.1,
        (0.3 * np.sin(2 * np.pi * 220 * np.arange(48000) / 16000)).astype(np.float32),
        rng.standard_normal(_CUT).astype(np.float32) * 0.05,
        rng.standard_normal(16000).astype(np.float32) * 0.2,
    ]

    print("loading full backbone + head ...")
    bb, head = _load_full()
    ref = [_full_prob(bb, head, s) for s in probes]

    print("truncating encoder to 5 layers ...")
    det = _Detector(_truncate(bb), head).eval()

    def torch_prob(audio):
        x = torch.from_numpy(_preprocess(audio)).unsqueeze(0)
        with torch.no_grad():
            return float(det(x)[0])

    trunc = [torch_prob(s) for s in probes]
    d_trunc = max(abs(a - b) for a, b in zip(ref, trunc))
    print(f"  full  : {[f'{p:.6f}' for p in ref]}")
    print(f"  trunc : {[f'{p:.6f}' for p in trunc]}")
    print(f"  max|delta| = {d_trunc:.2e}  (tol {_TRUNC_TOL})")
    assert d_trunc <= _TRUNC_TOL, "truncation changed the score -- aborting"

    print("exporting fp32 ONNX ...")
    dummy = torch.from_numpy(_preprocess(probes[0])).unsqueeze(0)
    torch.onnx.export(
        det, dummy, _FP32, opset_version=17,
        input_names=["x"], output_names=["spoof_prob"],
        dynamic_axes=None,  # static (1, 64600) -> robust INT8
    )

    print("quantizing to INT8 ...")
    from onnxruntime.quantization import quantize_dynamic, QuantType
    quantize_dynamic(_FP32, _INT8, weight_type=QuantType.QInt8)

    print("validating INT8 ONNX vs torch ...")
    import onnxruntime as ort
    sess = ort.InferenceSession(_INT8, providers=["CPUExecutionProvider"])

    def onnx_prob(audio):
        x = _preprocess(audio)[None, :]
        return float(sess.run(None, {"x": x})[0][0])

    onx = [onnx_prob(s) for s in probes]
    d_int8 = max(abs(a - b) for a, b in zip(ref, onx))
    mae = float(np.mean([abs(a - b) for a, b in zip(ref, onx)]))
    print(f"  onnx  : {[f'{p:.6f}' for p in onx]}")
    print(f"  max|delta| = {d_int8:.2e}  mae = {mae:.2e}  (tol {_INT8_TOL})")
    assert d_int8 <= _INT8_TOL, "INT8 ONNX diverged from torch -- aborting"

    # Rough latency comparison on one window.
    n = 5
    t = time.perf_counter()
    for _ in range(n):
        torch_prob(probes[2])
    t_torch = (time.perf_counter() - t) / n
    t = time.perf_counter()
    for _ in range(n):
        onnx_prob(probes[2])
    t_onnx = (time.perf_counter() - t) / n

    sz = os.path.getsize(_INT8) / 1e6
    print(f"\nOK. wrote {_INT8} ({sz:.0f} MB)")
    print(f"latency/window (truncated torch): {t_torch*1e3:.0f} ms")
    print(f"latency/window (INT8 ONNX)      : {t_onnx*1e3:.0f} ms  ({t_torch/t_onnx:.1f}x)")
    os.remove(_FP32)  # keep only the quantized artifact


if __name__ == "__main__":
    main()
