import os
import torch
import numpy as np
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification
from ml.audio_utils import load_audio_bytes, chunk_audio

MODEL_ID = "MelodyMachine/Deepfake-Audio-Detection-V2"
_MAX_CHUNKS = 16
_SILENCE_RMS = 1e-3

_processor = None
_model = None
_device = None

def _get_model():
    global _processor, _model, _device
    if _model is None:
        _device = "cuda" if torch.cuda.is_available() else "cpu"
        
        # FIX: Use FeatureExtractor instead of Processor
        _processor = AutoFeatureExtractor.from_pretrained(MODEL_ID)
        _model = AutoModelForAudioClassification.from_pretrained(MODEL_ID).to(_device)
        
        if _device == "cuda":
            _model.half() # FP16 for max throughput
            
        _model.eval()
        
        if hasattr(torch, "compile") and _device == "cuda" and os.name != 'nt':
            try:
                _model = torch.compile(_model) # Graph tracing for extreme speed
            except Exception:
                pass 
    return _processor, _model, _device

def _rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(np.square(x, dtype=np.float64)))) if len(x) else 0.0

def infer_chunk(processor, model, device, chunk: np.ndarray) -> float:
    inputs = processor(
        chunk,
        sampling_rate=16000,
        return_tensors="pt",
        padding=True
    ).to(device)

    with torch.inference_mode(), torch.autocast(device_type="cuda" if "cuda" in device else "cpu"):
        logits = model(**inputs).logits
        
    prob = torch.softmax(logits, dim=1)[0, 1].item()
    return float(prob)

def detect_samples(audio: np.ndarray) -> dict:
    processor, model, device = _get_model()

    chunks = chunk_audio(audio)
    if len(chunks) > _MAX_CHUNKS:
        chunks = chunks[:: -(-len(chunks) // _MAX_CHUNKS)]

    voiced = [c for c in chunks if _rms(c) >= _SILENCE_RMS]
    if not voiced:
        return {"risk_score": 0, "alert_level": "GREEN", "layer_breakdown": {}}

    scores = [infer_chunk(processor, model, device, c) for c in voiced]
    worst_score = max(scores)
    
    risk_score = int(round(np.clip(worst_score * 100, 0, 100)))
    
    if risk_score >= 70:
        alert_level = "RED"
    elif risk_score >= 40:
        alert_level = "AMBER"
    else:
        alert_level = "GREEN"

    return {
        "risk_score": risk_score, 
        "alert_level": alert_level,
        "layer_breakdown": {"sota_ssl": risk_score}
    }

def detect_audio(audio_bytes: bytes) -> dict:
    audio, _ = load_audio_bytes(audio_bytes)
    return detect_samples(audio)