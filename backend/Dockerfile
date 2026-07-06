FROM python:3.11-slim
WORKDIR /app
# libsndfile for soundfile; ffmpeg for mp3/webm decode; portaudio for pyaudio.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libsndfile1 ffmpeg portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
# Model file (models/deepfake_w2v.pt) is mounted at runtime, not baked in.
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health').status==200 else 1)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
