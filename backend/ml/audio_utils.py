import io
import numpy as np
import librosa
import soundfile as sf
from typing import Tuple, Optional

SAMPLE_RATE = 16000
CHUNK_DURATION = 4.0
CHUNK_SAMPLES = int(SAMPLE_RATE * CHUNK_DURATION)  # 64000


def load_audio(path: str, sr: int = SAMPLE_RATE) -> Tuple[np.ndarray, int]:
    audio, _ = librosa.load(path, sr=sr, mono=True)
    return audio.astype(np.float32), sr


def load_audio_bytes(data: bytes, sr: int = SAMPLE_RATE) -> Tuple[np.ndarray, int]:
    buf = io.BytesIO(data)
    try:
        audio, orig_sr = sf.read(buf, dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        if orig_sr != sr:
            audio = librosa.resample(audio, orig_sr=orig_sr, target_sr=sr)
        return audio.astype(np.float32), sr
    except Exception:
        buf.seek(0)
        audio, orig_sr = librosa.load(buf, sr=None, mono=True)
        if orig_sr != sr:
            audio = librosa.resample(audio, orig_sr=orig_sr, target_sr=sr)
        return audio.astype(np.float32), sr


def normalize(audio: np.ndarray) -> np.ndarray:
    peak = np.abs(audio).max()
    return audio / peak if peak > 0 else audio


def pad_or_trim(audio: np.ndarray, length: int = CHUNK_SAMPLES) -> np.ndarray:
    if len(audio) < length:
        return np.pad(audio, (0, length - len(audio)))
    return audio[:length]


def repeat_pad(audio: np.ndarray, length: int = CHUNK_SAMPLES) -> np.ndarray:
    """Tile to `length` instead of zero-padding — the ASVspoof/AASIST convention.
    Feeding the trained model repeated speech (not appended silence) keeps short
    clips inside the distribution it was trained on."""
    if len(audio) == 0:
        return np.zeros(length, dtype=np.float32)
    if len(audio) >= length:
        return audio[:length].astype(np.float32)
    reps = -(-length // len(audio))  # ceil
    return np.tile(audio, reps)[:length].astype(np.float32)


def chunk_audio(
    audio: np.ndarray,
    chunk_samples: int = CHUNK_SAMPLES,
    hop_samples: Optional[int] = None,
) -> list[np.ndarray]:
    if hop_samples is None:
        hop_samples = chunk_samples // 2
    chunks = [
        audio[s : s + chunk_samples]
        for s in range(0, len(audio) - chunk_samples + 1, hop_samples)
    ]
    if not chunks:
        chunks = [pad_or_trim(audio, chunk_samples)]
    return chunks


def preprocess(audio: np.ndarray) -> np.ndarray:
    """Normalize then pad/trim to CHUNK_SAMPLES — ready for model input."""
    return pad_or_trim(normalize(audio))
