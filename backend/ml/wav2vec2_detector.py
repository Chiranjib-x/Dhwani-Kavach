"""wav2vec2 (SSL) deepfake detector — the strongest neural layer.

Weights (`models/deepfake_w2v.pt`) are a wav2vec2-base front-end fine-tuned on
ASVspoof 2019 LA + augmentation. Preprocessing MUST match training:
16 kHz, zero-pad/trim to 4 s, per-utterance standardize, mean-pool, classifier head.

The base architecture is built from config (tiny download) and then fully
overwritten by the fine-tuned state dict, so no 360 MB base download is needed.
"""
import os
import numpy as np
import torch
import torch.nn as nn

from ml.audio_utils import CHUNK_SAMPLES, pad_or_trim

_MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "deepfake_w2v.pt")
_BASE_ID = "facebook/wav2vec2-base"
_model = None


def available() -> bool:
    return os.path.exists(_MODEL_PATH)


class _SSL(nn.Module):
    def __init__(self):
        super().__init__()
        from transformers import Wav2Vec2Config, Wav2Vec2Model
        self.w2v = Wav2Vec2Model(Wav2Vec2Config.from_pretrained(_BASE_ID))
        self.head = nn.Sequential(
            nn.Linear(768, 256), nn.ReLU(), nn.Dropout(0.3), nn.Linear(256, 2)
        )

    def embed(self, x):
        """Mean-pooled wav2vec2 features (768-d) — the utterance voiceprint."""
        return self.w2v(x).last_hidden_state.mean(1)

    def forward(self, x):
        return self.head(self.embed(x))


def _get_model() -> "_SSL":
    global _model
    if _model is None:
        m = _SSL()
        m.load_state_dict(torch.load(_MODEL_PATH, map_location="cpu"))
        m.eval()
        _model = m
    return _model


def infer(audio: np.ndarray) -> float:
    """Return spoof probability in [0, 1]; higher = more likely fake."""
    w = pad_or_trim(audio, CHUNK_SAMPLES).astype(np.float32)
    w = (w - w.mean()) / (w.std() + 1e-7)  # per-utterance standardize, like training
    x = torch.from_numpy(w).unsqueeze(0)   # (1, N)
    with torch.no_grad():
        prob = torch.softmax(_get_model()(x), dim=1)[0, 1].item()
    return float(prob)


def embed(audio: np.ndarray) -> np.ndarray:
    """Return the 768-d L2-normalised voiceprint for an utterance (for campaign
    correlation). Same preprocessing as infer()."""
    w = pad_or_trim(audio, CHUNK_SAMPLES).astype(np.float32)
    w = (w - w.mean()) / (w.std() + 1e-7)
    x = torch.from_numpy(w).unsqueeze(0)
    with torch.no_grad():
        v = _get_model().embed(x)[0].numpy().astype(np.float32)
    n = np.linalg.norm(v)
    return v / n if n > 0 else v
