"""Build the Attack Range demo clips into frontend/public/attacks/.

The /range page feeds these clips DIGITALLY into /api/analyze (never
speaker->air->mic) so the on-stage verdicts are deterministic. The source clips
are private team voices (Dataset_orig, gitignored) so the built clips are
gitignored too -- run this once on the demo machine:

    python tools/prep_attack_clips.py

Needs imageio-ffmpeg (in backend/requirements.txt). Override the source clips
with --clone / --normal if the named files aren't present.
"""
from __future__ import annotations

import argparse
import os
import subprocess

import imageio_ffmpeg

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "frontend", "public", "attacks")
_DEF_CLONE = os.path.join(ROOT, "Dataset_orig", "fake", "aditya_17-clone.mp3")   # verified RED
_DEF_NORMAL = os.path.join(ROOT, "Dataset_orig", "real", "aditya_10.m4a.mp3")    # verified GREEN


def _ff(args: list[str]) -> None:
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", *args], check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--clone", default=_DEF_CLONE, help="a verified clone clip (reads RED)")
    ap.add_argument("--normal", default=_DEF_NORMAL, help="a verified genuine clip (reads GREEN)")
    a = ap.parse_args()
    for p in (a.clone, a.normal):
        if not os.path.isfile(p):
            raise SystemExit(f"missing source clip: {p}\nPass --clone/--normal to point at your own.")
    os.makedirs(OUT, exist_ok=True)

    # clone attack (RED) + genuine control (GREEN)
    _ff(["-i", a.clone, "-c:a", "libmp3lame", "-b:a", "128k", os.path.join(OUT, "clone.mp3")])
    _ff(["-i", a.normal, "-c:a", "libmp3lame", "-b:a", "128k", os.path.join(OUT, "normal.mp3")])
    # loudspeaker replay: band-limit (kills sub-220 Hz and >3.3 kHz) + room echo,
    # the LF/HF channel signature a real near-field voice never has.
    _ff(["-i", a.clone, "-af", "highpass=f=220,lowpass=f=3300,aecho=0.8:0.6:35:0.4,volume=1.2",
         "-c:a", "libmp3lame", "-b:a", "128k", os.path.join(OUT, "replay.mp3")])

    print("built:", ", ".join(sorted(os.listdir(OUT))), "->", OUT)


if __name__ == "__main__":
    main()
