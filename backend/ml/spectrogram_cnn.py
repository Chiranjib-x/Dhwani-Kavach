"""Trained mel-spectrogram CNN — the neural deepfake detector.

Weights (`models/deepfake_cnn.pt`) are trained on ASVspoof 2019 LA.
Preprocessing here MUST match training: 16 kHz, zero-pad/trim to 4 s,
mel(n_fft=512, hop=160, n_mels=80) -> dB -> per-sample standardize.
"""
import os
import numpy as np
import torch
import torch.nn as nn
import torchaudio

from ml.audio_utils import SAMPLE_RATE, CHUNK_SAMPLES, pad_or_trim

_N_MELS = 80
_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "deepfake_cnn.pt")
_model = None
_mel = torchaudio.transforms.MelSpectrogram(
    sample_rate=SAMPLE_RATE, n_fft=512, hop_length=160, n_mels=_N_MELS
)
_to_db = torchaudio.transforms.AmplitudeToDB()


class _CNN(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(
            nn.Conv2d(1, 16, 3, padding=1), nn.BatchNorm2d(16), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(16, 32, 3, padding=1), nn.BatchNorm2d(32), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(32, 64, 3, padding=1), nn.BatchNorm2d(64), nn.ReLU(), nn.AdaptiveAvgPool2d(1),
        )
        self.fc = nn.Linear(64, 2)

    def forward(self, x):
        return self.fc(self.net(x).flatten(1))


def available() -> bool:
    return os.path.exists(_MODEL_PATH)


def _get_model() -> _CNN:
    global _model
    if _model is None:
        m = _CNN()
        m.load_state_dict(torch.load(_MODEL_PATH, map_location="cpu"))
        m.eval()
        _model = m
    return _model


def infer(audio: np.ndarray) -> float:
    """Return spoof probability in [0, 1]; higher = more likely fake."""
    wav = torch.from_numpy(pad_or_trim(audio, CHUNK_SAMPLES).astype(np.float32))  # zero-pad/trim, like training
    spec = _to_db(_mel(wav))
    spec = (spec - spec.mean()) / (spec.std() + 1e-6)
    x = spec.unsqueeze(0).unsqueeze(0)  # (1, 1, n_mels, T)
    with torch.no_grad():
        prob = torch.softmax(_get_model()(x), dim=1)[0, 1].item()
    return float(prob)
