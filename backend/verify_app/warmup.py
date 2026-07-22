"""Warm every model at Docker BUILD time so the deployed container's first
request doesn't download anything (free-tier cold start is slow enough already).

Run as `python -m verify_app.warmup` in the Dockerfile after deps are installed.
Downloads: ECAPA (~80 MB) and faster-whisper tiny (~75 MB) into the image. The
CM (cotrain) builds its XLS-R backbone from the vendored config + the in-repo
fine-tuned bundle, so it needs no download — but we touch it to fail the build
early if a weight file is missing.
"""
from __future__ import annotations

import numpy as np

from verify_app import asr, liveness, speaker


def main() -> None:
    print("warmup: ECAPA…"); speaker.load()
    print("warmup: faster-whisper…"); asr.load()
    print(f"warmup: CM ({liveness.backend_name()})…")
    # one tiny forward so a missing/bad checkpoint fails the build, not a live request
    liveness.bonafide_p(np.zeros(16000, dtype=np.float32))
    print("warmup: done")


if __name__ == "__main__":
    main()
