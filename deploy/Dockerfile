# Dhwani-Kavach v2 — Hugging Face Spaces (Docker SDK, free CPU Basic).
# Built context is the repo's backend/ directory (see deploy/README.md / build_space.py).
FROM python:3.11-slim

# HF Spaces runs the container as uid 1000.
RUN useradd -m -u 1000 user
WORKDIR /app

# CPU-only torch from the pytorch index, then the rest of the pinned deps.
COPY requirements-verify.txt .
RUN pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu \
      torch==2.3.0 torchaudio==2.3.0 && \
    pip install --no-cache-dir -r requirements-verify.txt

# Only the ml/ modules verify_app imports + the small model files it needs.
# NOT the 1.5 GB models.zip / xlsr_sls.safetensors (SLS is a Phase-7 A/B option;
# if chosen, hf_hub_download it in warmup.py instead of baking it in).
COPY ml/ ml/
COPY models/AASIST.pth models/silero_vad_16k.onnx \
     models/w2v2aasist_cotrain.safetensors models/w2v2aasist_full.safetensors \
     models/xlsr_300m_config.json models/
COPY verify_app/ verify_app/

ENV HF_HOME=/app/.cache/hf \
    ECAPA_DIR=/app/.cache/ecapa \
    WHISPER_DIR=/app/verify_app/.cache/whisper \
    KAVACH_DB=/tmp/kavach.db \
    KMP_DUPLICATE_LIB_OK=TRUE \
    KV_CM=cotrain

# Bake model downloads into the image so cold start is instant.
RUN python -m verify_app.warmup && chown -R user:user /app
USER user
EXPOSE 7860
CMD ["uvicorn", "verify_app.main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
