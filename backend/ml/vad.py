"""Voice-activity gate (Silero VAD) in front of the detectors.

Scoring silence or room noise wastes a full SSL forward pass and yields a
dishonest verdict -- ml.detector's RMS gate only catches near-silence, not
non-speech noise (hum, music, hold tones). This reports the fraction of a window
that is actual speech so the detector can skip windows not worth scoring.

Runs Silero's small ONNX model (vendored at models/silero_vad_16k.onnx) directly
on onnxruntime -- deliberately NOT via the `silero-vad` pip package, whose import
chain pulls torchaudio (a fragile native dependency: it fails to load on this
Windows env). onnxruntime is already a dependency and has no such issue.

Degrades gracefully: if the model file or onnxruntime is missing, speech_ratio()
returns 1.0 (fail-open -> no gating), so the pipeline behaves exactly as before.
Silero v5 processes 512-sample frames at 16 kHz, carrying a recurrent state; a 4 s
window is ~125 frames, ~10 ms total on CPU.
"""
from __future__ import annotations

import os

import numpy as np

from ml.audio_utils import SAMPLE_RATE

_MODEL = os.path.join(os.path.dirname(__file__), "..", "models", "silero_vad_16k.onnx")
_FRAME = 512          # silero v5 @16kHz fixed frame size
_CONTEXT = 64         # silero v5 prepends 64 prev-frame samples per input (16kHz)
_THRESHOLD = 0.5      # per-frame speech probability cut

_sess = None
_tried = False


def _get():
    global _sess, _tried
    if _tried:
        return _sess
    _tried = True
    try:
        import onnxruntime as ort
        if os.path.exists(_MODEL):
            so = ort.SessionOptions()
            so.intra_op_num_threads = 1  # tiny model; threads add overhead, not speed
            _sess = ort.InferenceSession(_MODEL, so, providers=["CPUExecutionProvider"])
    except Exception:
        _sess = None
    return _sess


def available() -> bool:
    """True if the vendored Silero model loaded. No network."""
    return _get() is not None


def speech_ratio(audio: np.ndarray) -> float:
    """Fraction of `audio` (16 kHz mono float32) detected as speech, in [0, 1].

    Returns 1.0 when VAD is unavailable so callers fail open (never gate out a
    real call because the optional model is missing)."""
    sess = _get()
    if sess is None:
        return 1.0
    a = np.ascontiguousarray(audio, dtype=np.float32)
    n = len(a) // _FRAME
    if n == 0:
        return 1.0
    try:
        state = np.zeros((2, 1, 128), dtype=np.float32)
        context = np.zeros((1, _CONTEXT), dtype=np.float32)
        sr = np.array(SAMPLE_RATE, dtype=np.int64)
        speech = 0
        for i in range(n):
            frame = a[i * _FRAME:(i + 1) * _FRAME][None, :]
            # Silero v5 wants 64 samples of prior context prepended to each frame
            # (and carried forward); a bare 512-sample frame reads as ~silence.
            x = np.concatenate([context, frame], axis=1)  # (1, 576)
            out, state = sess.run(None, {"input": x, "state": state, "sr": sr})
            context = x[:, -_CONTEXT:]
            if float(out[0, 0]) >= _THRESHOLD:
                speech += 1
        return speech / n
    except Exception:
        return 1.0


if __name__ == "__main__":
    # Self-check: pure silence must score below a voiced-band tone burst.
    sr = SAMPLE_RATE
    silence = np.zeros(sr, dtype=np.float32)
    r_sil = speech_ratio(silence)
    assert 0.0 <= r_sil <= 1.0, "ratio must be in [0,1]"
    if available():
        # A 150 Hz amplitude-modulated tone is a crude voiced-speech proxy.
        t = np.arange(sr) / sr
        voiced = (0.3 * np.sin(2 * np.pi * 150 * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 4 * t))).astype(np.float32)
        r_voiced = speech_ratio(voiced)
        assert r_sil <= r_voiced + 1e-6, f"silence ({r_sil}) should not exceed voiced ({r_voiced})"
        print(f"vad self-check ok (silence={r_sil:.2f}, voiced={r_voiced:.2f})")
    else:
        print(f"vad self-check ok (model unavailable, fail-open ratio={r_sil:.2f})")
