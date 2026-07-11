"""Generate synthetic (fake) speech with KittenTTS — for training data, eval sets,
and offline demo clips.

DEV TOOL, not part of the served app. Requires KittenTTS:
  pip install "https://github.com/KittenML/KittenTTS/releases/download/0.8.1/kittentts-0.8.1-py3-none-any.whl"

Why: KittenTTS is a TTS family the detector hasn't trained on (it currently
evades detection). Adding its output to the FAKE training set broadens generator
diversity → better generalisation + novelty coverage. Output is 16 kHz mono wav,
ready to drop into the Kaggle training pipeline.

Usage:
  python -m tools.gen_kitten_fakes --out ./kitten_fakes            # full batch
  python -m tools.gen_kitten_fakes --out ./demo --voices Jasper --category scam
ponytail: fixed script/voice lists; extend the lists, don't add config machinery.
"""
from __future__ import annotations

import argparse
import os

import numpy as np
import soundfile as sf
import librosa
from kittentts import KittenTTS

VOICES = ["Bella", "Jasper", "Luna", "Bruno", "Rosie", "Hugo", "Kiki", "Leo"]

SCRIPTS = {
    "scam": [
        "This is the bank security team. Your account has been compromised. Do not tell anyone. Transfer fifty thousand rupees to this new account right now or it will be frozen.",
        "Hello, I am calling from the fraud department. To verify your identity, please share the one time password we just sent to your phone.",
        "Your card will be blocked in ten minutes. Confirm your PIN and CVV immediately to keep it active.",
        "This is an urgent message from the income tax department. Pay the pending amount now to a new account or face arrest.",
    ],
    "benign": [
        "Hello, I would like to check my account balance and my recent transactions please.",
        "Can you tell me the interest rate on a one year fixed deposit?",
        "I want to update the email address linked to my savings account.",
        "What are your branch working hours on Saturday?",
    ],
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="./kitten_fakes")
    ap.add_argument("--sr", type=int, default=16000)
    ap.add_argument("--voices", nargs="*", default=VOICES)
    ap.add_argument("--category", choices=list(SCRIPTS) + ["all"], default="all")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    model = KittenTTS("KittenML/kitten-tts-mini-0.8")
    cats = list(SCRIPTS) if args.category == "all" else [args.category]

    n = 0
    for cat in cats:
        for li, line in enumerate(SCRIPTS[cat]):
            for v in args.voices:
                audio = np.asarray(model.generate(line, voice=v), dtype="float32")
                if args.sr != 24000:
                    audio = librosa.resample(audio, orig_sr=24000, target_sr=args.sr)
                path = os.path.join(args.out, f"kitten_{cat}_{li:02d}_{v}.wav")
                sf.write(path, audio, args.sr)
                n += 1
    print(f"wrote {n} clips to {args.out} ({args.sr} Hz mono)")


if __name__ == "__main__":
    main()
