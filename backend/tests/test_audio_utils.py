import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import torch
import soundfile as sf
import io

from ml.audio_utils import (
    SAMPLE_RATE, CHUNK_SAMPLES,
    load_audio_bytes, normalize, pad_or_trim, chunk_audio, preprocess,
)
from ml.spectrogram import mel_spectrogram, mfcc_features, to_tensor, waveform_to_tensor


def make_sine(duration=4.0, freq=440.0, sr=SAMPLE_RATE) -> np.ndarray:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    return (0.5 * np.sin(2 * np.pi * freq * t)).astype(np.float32)


def audio_to_bytes(audio: np.ndarray, sr: int = SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, audio, sr, format="WAV")
    return buf.getvalue()


def test_normalize():
    a = np.array([0.0, 0.5, -2.0, 1.0], dtype=np.float32)
    out = normalize(a)
    assert np.isclose(np.abs(out).max(), 1.0), "normalize: peak should be 1.0"
    print("  [OK] normalize")


def test_pad_or_trim_pad():
    a = np.zeros(1000, dtype=np.float32)
    out = pad_or_trim(a, CHUNK_SAMPLES)
    assert len(out) == CHUNK_SAMPLES, "pad_or_trim: wrong length after padding"
    print("  [OK] pad_or_trim (pad)")


def test_pad_or_trim_trim():
    a = np.zeros(CHUNK_SAMPLES + 5000, dtype=np.float32)
    out = pad_or_trim(a)
    assert len(out) == CHUNK_SAMPLES, "pad_or_trim: wrong length after trimming"
    print("  [OK] pad_or_trim (trim)")


def test_chunk_audio():
    audio = make_sine(duration=10.0)
    chunks = chunk_audio(audio, CHUNK_SAMPLES, hop_samples=CHUNK_SAMPLES // 2)
    assert len(chunks) > 0, "chunk_audio: no chunks produced"
    assert all(len(c) == CHUNK_SAMPLES for c in chunks), "chunk_audio: chunk length mismatch"
    print(f"  [OK] chunk_audio ({len(chunks)} chunks from 10s audio)")


def test_chunk_audio_short():
    audio = make_sine(duration=1.0)  # shorter than one chunk
    chunks = chunk_audio(audio)
    assert len(chunks) == 1 and len(chunks[0]) == CHUNK_SAMPLES
    print("  [OK] chunk_audio (short audio -> 1 padded chunk)")


def test_load_audio_bytes():
    audio = make_sine()
    data = audio_to_bytes(audio)
    loaded, sr = load_audio_bytes(data)
    assert sr == SAMPLE_RATE
    assert len(loaded) == len(audio)
    assert loaded.dtype == np.float32
    print("  [OK] load_audio_bytes")


def test_preprocess():
    audio = make_sine(duration=6.0)
    out = preprocess(audio)
    assert len(out) == CHUNK_SAMPLES
    assert np.abs(out).max() <= 1.0
    print("  [OK] preprocess")


def test_mel_spectrogram():
    audio = make_sine()
    spec = mel_spectrogram(audio)
    assert spec.ndim == 2
    assert spec.shape[0] == 80   # N_MELS
    assert spec.dtype == np.float32
    print(f"  [OK] mel_spectrogram shape={spec.shape}")


def test_mfcc_features():
    audio = make_sine()
    feat = mfcc_features(audio)
    assert feat.ndim == 2
    assert feat.shape[0] == 120  # 40 mfcc * 3
    assert feat.dtype == np.float32
    print(f"  [OK] mfcc_features shape={feat.shape}")


def test_to_tensor():
    spec = mel_spectrogram(make_sine())
    t = to_tensor(spec)
    assert isinstance(t, torch.Tensor)
    assert t.shape == (1, 1, 80, spec.shape[1])
    print(f"  [OK] to_tensor shape={tuple(t.shape)}")


def test_waveform_to_tensor():
    audio = preprocess(make_sine())
    t = waveform_to_tensor(audio)
    assert isinstance(t, torch.Tensor)
    assert t.shape == (1, CHUNK_SAMPLES)
    print(f"  [OK] waveform_to_tensor shape={tuple(t.shape)}")


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 1A — Audio Ingestion Tests")
    print("=" * 50)
    tests = [
        test_normalize,
        test_pad_or_trim_pad,
        test_pad_or_trim_trim,
        test_chunk_audio,
        test_chunk_audio_short,
        test_load_audio_bytes,
        test_preprocess,
        test_mel_spectrogram,
        test_mfcc_features,
        test_to_tensor,
        test_waveform_to_tensor,
    ]
    failed = []
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed.append(t.__name__)
    print("=" * 50)
    if failed:
        print(f"FAILED: {failed}")
        sys.exit(1)
    else:
        print(f"All {len(tests)} tests passed. Phase 1A complete.")
