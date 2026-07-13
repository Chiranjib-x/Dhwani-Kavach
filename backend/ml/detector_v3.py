"""wav2vec2-XLSR-53 voice-clone detector (garystafford/wav2vec2-deepfake-voice-detector).

Complements ml/detector_v2.py (Codecfake -- a codec/compression-artifact
specialist) with a second, INDEPENDENT detector fine-tuned specifically on
modern commercial TTS/voice-clone engines (ElevenLabs, Amazon Polly, Hexgrad
Kokoro, Hume AI, Speechify, Luvvoice) -- matching this product's actual
threat model (an attacker cloning a voice) far more directly than a
codec-artifact-trained model. Built on wav2vec2-large-XLSR-53, pretrained on
53 languages, so the underlying features are far more language-robust than a
single-language checkpoint -- helps with the Hindi/Bengali/Tamil/etc.
requirement, though the classification head itself hasn't been validated on
those languages specifically.

Standard HuggingFace `transformers` model (Wav2Vec2ForSequenceClassification,
id2label = {0: "real", 1: "fake"} per its config.json) -- no custom
architecture to vendor. Apache 2.0.

Unlike ml/detector_v2.py (a local checkpoint file), this model has no local
file to check for -- it's pulled from the HF Hub cache. available() therefore
does NOT hit the network: it only checks whether the model is already
resident in the local cache (instant, deterministic), so a test run or an
offline deployment never blocks on this check. Call warm() once at process
startup (app/main.py) to populate the cache ahead of the first real request;
absent that, the first infer() call will download it on demand (~1.2 GB).
"""
import numpy as np
import torch

_MODEL_ID = "garystafford/wav2vec2-deepfake-voice-detector"
_extractor = None
_model = None


def _get_model(local_only: bool):
    global _extractor, _model
    if _model is None:
        from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
        kwargs = {"local_files_only": True} if local_only else {}
        extractor = AutoFeatureExtractor.from_pretrained(_MODEL_ID, **kwargs)
        model = AutoModelForAudioClassification.from_pretrained(_MODEL_ID, **kwargs)
        model.eval()
        _extractor, _model = extractor, model
    return _extractor, _model


def available() -> bool:
    """True only if the model is already in the local HF cache. No network
    call -- safe to call on every chunk without risking a slow/blocking probe."""
    if _model is not None:
        return True
    try:
        _get_model(local_only=True)
        return True
    except Exception:
        return False


def warm() -> bool:
    """Download/load the model if not already cached (network allowed).
    Call once at app startup so the first real request isn't the one paying
    for the download."""
    try:
        _get_model(local_only=False)
        return True
    except Exception:
        return False


def infer(audio: np.ndarray) -> float:
    """Return spoof probability in [0, 1]; higher = more likely fake."""
    extractor, model = _get_model(local_only=False)  # network allowed as a last resort
    inputs = extractor(audio, sampling_rate=16000, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits
        prob = torch.softmax(logits, dim=1)[0, 1].item()  # id2label: 0=real, 1=fake
    return float(prob)
