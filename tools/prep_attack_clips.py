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
import sys

import imageio_ffmpeg
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "frontend", "public", "attacks")
_DEF_CLONE = os.path.join(ROOT, "Dataset_orig", "fake", "aditya_17-clone.mp3")   # verified RED
_DEF_NORMAL = os.path.join(ROOT, "Dataset_orig", "real", "aditya_10.m4a.mp3")    # verified GREEN


def _ff(args: list[str]) -> None:
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-v", "error", "-y", *args], check=True)


def _make_replay(src_mp3: str, out_mp3: str) -> None:
    """Simulate a loudspeaker replay so it actually trips ml.replay's LF+HF
    deficit check -- ffmpeg's default highpass/lowpass are gentle single-pole
    filters and leave enough energy in the 60-160 Hz band to read as a live
    voice (verified: LF ratio 0.12, floor is 0.05 -- doesn't trigger). Use the
    same steep 4th-order Butterworth bandpass ml/replay.py's own self-check
    uses, via scipy, so the demo clip matches the detector's actual test."""
    from ml.audio_utils import load_audio
    from scipy.signal import butter, sosfilt
    import soundfile as sf

    x, sr = load_audio(src_mp3, sr=16000)
    sos = butter(4, [250, 4200], btype="bandpass", fs=sr, output="sos")
    y = sosfilt(sos, x).astype(np.float32)
    peak = np.abs(y).max()
    if peak > 0:
        y = y / peak * 0.9
    wav_tmp = out_mp3 + ".tmp.wav"
    sf.write(wav_tmp, y, sr, subtype="PCM_16")
    _ff(["-i", wav_tmp, "-c:a", "libmp3lame", "-b:a", "128k", out_mp3])
    os.remove(wav_tmp)


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
    # loudspeaker replay: steep bandpass -> triggers ml.replay's suspect flag
    _make_replay(a.clone, os.path.join(OUT, "replay.mp3"))

    print("built:", ", ".join(sorted(os.listdir(OUT))), "->", OUT)

    # verify the replay clip actually trips the detector it's meant to demo
    os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
    from ml.audio_utils import load_audio as _load
    from ml import replay as _replay
    wav, sr = _load(os.path.join(OUT, "replay.mp3"))
    r = _replay.assess(wav, sr)
    status = "OK — suspect=True" if r["suspect"] else "WARNING — suspect=False, demo chip will not fire!"
    print(f"replay.mp3 self-check: {status}  (lf={r['lf_ratio']} hf={r['hf_ratio']} score={r['score']})")


if __name__ == "__main__":
    main()
