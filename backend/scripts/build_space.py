"""Assemble a clean HF Space folder and (optionally) push it. ₹0, no card.

Local assemble (always safe):
    ../.venv/Scripts/python.exe scripts/build_space.py            # builds ./space/

Push (needs a free write token from huggingface.co/settings/tokens):
    HF_TOKEN=hf_xxx ../.venv/Scripts/python.exe scripts/build_space.py --push you/dhwani-kavach

Then set the Space secret KV_ADMIN_KEY in the Space settings UI. See deploy/README.md.
"""
from __future__ import annotations

import argparse
import os
import shutil

_HERE = os.path.dirname(os.path.abspath(__file__))
_BACKEND = os.path.dirname(_HERE)
_REPO = os.path.dirname(_BACKEND)
_OUT = os.path.join(_REPO, "space")

_SPACE_README = """---
title: Dhwani Kavach Voice Verify
emoji: 🛡️
colorFrom: indigo
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Dhwani Kavach — Voice Verification
Enroll once, then verify identity with a random one-time digit challenge run
through a 4-gate cascade (quality → phrase → liveness → voice match). See the
repo's MASTER-PLAN.md. Set the Space secret `KV_ADMIN_KEY` before using admin endpoints.
"""

# Small model files the container needs (NOT the multi-GB weights).
_MODELS = ["AASIST.pth", "silero_vad_16k.onnx", "w2v2aasist_cotrain.safetensors",
           "w2v2aasist_full.safetensors", "xlsr_300m_config.json"]


def build() -> str:
    if os.path.exists(_OUT):
        shutil.rmtree(_OUT)
    os.makedirs(os.path.join(_OUT, "models"))
    # Dockerfile at Space root
    shutil.copy(os.path.join(_REPO, "deploy", "Dockerfile"), os.path.join(_OUT, "Dockerfile"))
    shutil.copy(os.path.join(_BACKEND, "requirements-verify.txt"), _OUT)
    # code: ml/ (minus caches) and verify_app/ (minus db/cache)
    _ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".cache", "kavach.db*", "*.zip")
    shutil.copytree(os.path.join(_BACKEND, "ml"), os.path.join(_OUT, "ml"), ignore=_ignore)
    shutil.copytree(os.path.join(_BACKEND, "verify_app"), os.path.join(_OUT, "verify_app"), ignore=_ignore)
    for m in _MODELS:
        shutil.copy(os.path.join(_BACKEND, "models", m), os.path.join(_OUT, "models", m))
    with open(os.path.join(_OUT, "README.md"), "w", encoding="utf-8") as f:
        f.write(_SPACE_README)
    print(f"built Space folder: {_OUT}")
    return _OUT


def push(repo_id: str) -> None:
    token = os.environ.get("HF_TOKEN")
    if not token:
        raise SystemExit("set HF_TOKEN (free write token from huggingface.co/settings/tokens)")
    from huggingface_hub import HfApi
    api = HfApi(token=token)
    api.create_repo(repo_id, repo_type="space", space_sdk="docker", exist_ok=True)
    api.upload_folder(folder_path=_OUT, repo_id=repo_id, repo_type="space")
    print(f"pushed -> https://huggingface.co/spaces/{repo_id}")
    print("Now set Space secret KV_ADMIN_KEY in the Space settings UI.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--push", metavar="repo_id", help="e.g. yourname/dhwani-kavach")
    args = ap.parse_args()
    build()
    if args.push:
        push(args.push)
