import numpy as np
import torch
import librosa
from ml.audio_utils import SAMPLE_RATE

N_FFT = 512
HOP_LENGTH = 160       # 10 ms at 16 kHz
N_MELS = 80
N_MFCC = 40
FMIN = 0
FMAX = 8000


def mel_spectrogram(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """Log-mel spectrogram → (N_MELS, T) float32."""
    mel = librosa.feature.melspectrogram(
        y=audio, sr=sr, n_fft=N_FFT, hop_length=HOP_LENGTH,
        n_mels=N_MELS, fmin=FMIN, fmax=FMAX,
    )
    return librosa.power_to_db(mel, ref=np.max).astype(np.float32)


def mfcc_features(audio: np.ndarray, sr: int = SAMPLE_RATE) -> np.ndarray:
    """MFCC + delta + delta² → (N_MFCC*3, T) float32."""
    m = librosa.feature.mfcc(
        y=audio, sr=sr, n_mfcc=N_MFCC, n_fft=N_FFT, hop_length=HOP_LENGTH,
    )
    return np.vstack([m, librosa.feature.delta(m), librosa.feature.delta(m, order=2)]).astype(np.float32)


def to_tensor(spec: np.ndarray) -> torch.Tensor:
    """(F, T) numpy → (1, 1, F, T) torch tensor."""
    return torch.from_numpy(spec).unsqueeze(0).unsqueeze(0)


def waveform_to_tensor(audio: np.ndarray) -> torch.Tensor:
    """1-D waveform → (1, N) torch tensor for AASIST input."""
    return torch.from_numpy(audio).unsqueeze(0)
