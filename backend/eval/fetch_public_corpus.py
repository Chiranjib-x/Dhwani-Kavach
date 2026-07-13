"""Build a small PUBLIC labelled corpus for eval.run -- no private data, no
external wheels.

  real/  : LibriSpeech clips (real human speech, 16 kHz) via `datasets`.
  fake/  : the SAME transcripts synthesized by facebook/mms-tts-eng (VITS) via
           `transformers` -- a TTS the detector was NOT trained on, so it probes
           generalization. Pairing on identical text isolates human-vs-synthetic
           as the only difference.

usage: PYTHONPATH=backend python -m eval.fetch_public_corpus --out eval/corpus --n 15
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import soundfile as sf
import librosa
import torch


def _save16k(path: str, arr: np.ndarray, sr: int) -> None:
    arr = np.asarray(arr, dtype="float32")
    if sr != 16000:
        arr = librosa.resample(arr, orig_sr=sr, target_sr=16000)
    sf.write(path, arr, 16000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="eval/corpus")
    ap.add_argument("--n", type=int, default=15)
    args = ap.parse_args()
    real_dir = os.path.join(args.out, "real")
    fake_dir = os.path.join(args.out, "fake")
    os.makedirs(real_dir, exist_ok=True)
    os.makedirs(fake_dir, exist_ok=True)

    from datasets import load_dataset
    ds = load_dataset("hf-internal-testing/librispeech_asr_dummy", "clean", split="validation")
    n = min(args.n, len(ds))
    print(f"real: saving {n} LibriSpeech clips ...", flush=True)
    texts = []
    for i in range(n):
        a = ds[i]["audio"]
        _save16k(os.path.join(real_dir, f"ls_{i:02d}.wav"), a["array"], a["sampling_rate"])
        texts.append(ds[i]["text"])

    print("fake: loading facebook/mms-tts-eng (VITS) ...", flush=True)
    from transformers import VitsModel, AutoTokenizer
    model = VitsModel.from_pretrained("facebook/mms-tts-eng").eval()
    tok = AutoTokenizer.from_pretrained("facebook/mms-tts-eng")
    fsr = model.config.sampling_rate
    for i, text in enumerate(texts):
        inp = tok(text.lower(), return_tensors="pt")
        with torch.no_grad():
            wav = model(**inp).waveform[0].numpy().astype("float32")
        _save16k(os.path.join(fake_dir, f"vits_{i:02d}.wav"), wav, fsr)
        print(f"  [{i+1}/{n}] synthesized", flush=True)

    print(f"done: {n} real + {n} fake wavs under {args.out}", flush=True)


if __name__ == "__main__":
    main()
