"""Refit calibration for the NEURAL-ONLY pipeline.

The verdict is now the mean of the calibrated v2 detector and (when loaded) the
v3 clone detector -- no heuristics (see ml/ensemble.py). So calibration has two
jobs and we fit both here:
  * Platt (a, b)      -- shape the v2 detector's collapsed spoof prob into a
                         usable range (this is what ml.scoring.calibrate applies).
  * (t_low, t_high)   -- band the FINAL FUSED score (mean of calibrate(p_v2) and
                         p_v3), which is what ml/detector.py actually thresholds.

Fitting the bands on the fused score -- not on calibrate(p_v2) alone -- is the fix
for the razor-thin boundary: the old calibration.json banded a signal the app no
longer uses directly.

Labels come from the FILENAME (our sample_audio/ convention): a stem containing
"clone" is FAKE, everything else (incl. "original") is REAL. Decodes mp3/mpeg/wav/
flac via ml.audio_utils.load_audio. Also reports a TELEPHONY-degraded EER so we can
see the phone-line gap the demo will actually face.

usage:
    PYTHONPATH=backend python -m tools.fit_calibration                 # -> sample_audio/
    PYTHONPATH=backend python -m tools.fit_calibration <folder>
    PYTHONPATH=backend python -m tools.fit_calibration --exclude=lily_original,chris_original
    PYTHONPATH=backend python -m tools.fit_calibration --selfcheck     # math only, no models

--exclude drops named clips (substring match) from the FIT -- use it for clips a
prior run's "OUTLIER REAL" warning flagged as a documented model gap (see
HANDOFF.md), so a known-bad file doesn't corrupt otherwise-clean thresholds. It
does not hide the problem: the excluded files are printed, and re-running WITHOUT
--exclude always shows the raw, unfiltered truth.
"""
from __future__ import annotations

import glob
import json
import math
import os
import sys

import numpy as np

_HERE = os.path.dirname(__file__)
_OUT = os.path.join(_HERE, "..", "models", "calibration.json")
_DEFAULT_DIR = os.path.join(_HERE, "..", "..", "sample_audio")
_AUDIO_EXT = ("*.wav", "*.flac", "*.mp3", "*.ogg", "*.m4a", "*.mpeg", "*.mp3.mpeg")


# --------------------------------------------------------------------------- #
# pure math (unit-testable without any model)
# --------------------------------------------------------------------------- #
def _logit(p: np.ndarray) -> np.ndarray:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def fit_platt(p_v2: np.ndarray, y: np.ndarray, iters: int = 100, lam: float = 2.0) -> tuple[float, float]:
    """Ridge-regularized Newton-Raphson logistic regression of label y on
    logit(p_v2). Returns (a, b).

    Plain (unregularized) Platt scaling DIVERGES when the dev set is small and
    the classes are near-perfectly separable on the raw score -- exactly our
    case (15 hand-labeled clips, a strong detector). Newton-Raphson then walks
    a,b toward +-infinity chasing a step function; we measured a=46, b=84 on
    real data, both miles outside scoring.py's safety clamps [0.5,1.5]/[-8,8].
    The clamp would silently rescue the app at runtime, but with DIFFERENT
    (a,b) than what fit t_low/t_high here -- the thresholds would no longer
    match the scores the app actually produces. A small ridge penalty toward
    the identity mapping (a=1, b=0) keeps the fit inside a sane, well-behaved
    range on separable data while still fitting real separation on non-toy
    data (see the self-check for both cases)."""
    z = _logit(p_v2)
    a, b = 1.0, 0.0
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(a * z + b)))
        g = np.array([np.sum((p - y) * z), np.sum(p - y)]) + lam * np.array([a - 1.0, b])
        w = p * (1 - p)
        H = np.array([[np.sum(w * z * z), np.sum(w * z)],
                      [np.sum(w * z), np.sum(w)]]) + lam * np.eye(2) + 1e-6 * np.eye(2)
        a, b = np.array([a, b]) - np.linalg.solve(H, g)
    return float(a), float(b)


def calibrate_ab(p_v2: np.ndarray, a: float, b: float) -> np.ndarray:
    return 1 / (1 + np.exp(-(a * _logit(p_v2) + b)))


def fuse(cal_v2: np.ndarray, p_v3: np.ndarray | None) -> np.ndarray:
    """App fusion: mean of calibrated-v2 and v3 (or v2 alone when v3 absent) --
    mirrors compute_ensemble with the neural-only 0.5/0.5 weights."""
    return cal_v2 if p_v3 is None else 0.5 * cal_v2 + 0.5 * p_v3


def eer(fused_real: np.ndarray, fused_fake: np.ndarray) -> float:
    """Equal error rate on the fused score (FPR on reals == FNR on fakes)."""
    if not len(fused_real) or not len(fused_fake):
        return float("nan")
    ts = np.linspace(0, 1, 1001)
    fpr = np.array([(fused_real >= t).mean() for t in ts])
    fnr = np.array([(fused_fake < t).mean() for t in ts])
    i = int(np.argmin(np.abs(fpr - fnr)))
    return float((fpr[i] + fnr[i]) / 2)


def bands(fused_real: np.ndarray) -> tuple[float, float]:
    """t_low at 5% FPR, t_high at 1% FPR on bonafide, with the >=0.15 margin the
    scoring clamps enforce (so a tiny real set can't collapse the two together)."""
    t_low = float(np.quantile(fused_real, 0.95))
    t_high = float(np.quantile(fused_real, 0.99))
    t_high = max(t_high, t_low + 0.15)
    return min(t_low, 0.8), min(t_high, 0.95)


# --------------------------------------------------------------------------- #
# scoring (needs the models) -- imported lazily so --selfcheck stays offline
# --------------------------------------------------------------------------- #
def _list_audio(folder: str) -> list[str]:
    files = sorted(set(sum((glob.glob(os.path.join(folder, e)) for e in _AUDIO_EXT), [])))
    return files


def _is_fake(path: str) -> bool:
    return "clone" in os.path.basename(path).lower()


_CHUNK_SILENCE_RMS = 1e-3  # mirrors ml.detector._SILENCE_RMS


def _worst_chunk_score(x, have_v3: bool):
    """Score a clip THE WAY THE APP DOES: chunk into ~4s windows across the WHOLE
    file (ml.audio_utils.chunk_audio, same as ml.detector.detect_samples) and take
    the worst (highest-risk) window -- not detector_v2.infer_raw(x) on the raw
    array, which silently truncates to its first ~4.04s via repeat_pad's "already
    long enough" branch. That truncation was scoring only the OPENING of every
    clip, which under-samples risk on anything longer than ~4s: a clip can open
    clean and drift risky later (verified: lily_original.mp3 scores 0.01-0.12 for
    its first 10s, then 0.87-0.98 from 10s on -- the app's worst-chunk verdict
    would catch that; the old whole-clip fit never would have). Returns
    (worst_p_v2, p_v3_of_that_same_chunk_or_None)."""
    from ml.audio_utils import chunk_audio
    from ml import detector_v2, detector_v3

    chunks = chunk_audio(x)
    voiced = [c for c in chunks if float(np.sqrt(np.mean(c.astype(np.float64) ** 2))) >= _CHUNK_SILENCE_RMS]
    if not voiced:
        voiced = chunks if chunks else [x]
    best_i, best_p2 = 0, -1.0
    for i, c in enumerate(voiced):
        p2 = detector_v2.infer_raw(c)[0]
        if p2 > best_p2:
            best_p2, best_i = p2, i
    p3 = detector_v3.infer(voiced[best_i]) if have_v3 else None
    return best_p2, p3


def _score_folder(folder: str):
    from ml.audio_utils import load_audio, SAMPLE_RATE
    from ml import detector_v3
    from ml.telephony import to_telephony

    have_v3 = detector_v3.available()
    print(f"v3 clone-detector: {'LOADED (fusing)' if have_v3 else 'absent (v2-only calibration)'}", flush=True)

    rows = []  # (is_fake, p_v2, p_v3|None, p_v2_tel, p_v3_tel|None)
    names = []
    files = _list_audio(folder)
    if not files:
        raise SystemExit(f"no audio in {folder}")
    for f in files:
        try:
            x, _ = load_audio(f)
        except Exception as exc:
            print(f"  skip {os.path.basename(f)}: {exc}", flush=True)
            continue
        xt = to_telephony(x, SAMPLE_RATE)
        p2, p3 = _worst_chunk_score(x, have_v3)
        p2t, p3t = _worst_chunk_score(xt, have_v3)
        rows.append((_is_fake(f), p2, p3, p2t, p3t))
        names.append(os.path.basename(f))
        tag = "FAKE" if _is_fake(f) else "real"
        print(f"  {tag:4} {os.path.basename(f):32} worst_p_v2={p2:.4f}"
              + (f" p_v3={p3:.3f}" if p3 is not None else ""), flush=True)
    return rows, have_v3, names


def main(folder: str, exclude: tuple[str, ...] = ()):
    rows, have_v3, names = _score_folder(folder)
    if exclude:
        keep = [i for i, n in enumerate(names) if not any(e.lower() in n.lower() for e in exclude)]
        skipped = [names[i] for i in range(len(names)) if i not in keep]
        if skipped:
            print(f"\nEXCLUDED from the fit (documented known-bad, see HANDOFF.md): {skipped}")
        rows, names = [rows[i] for i in keep], [names[i] for i in keep]
    y = np.array([1 if r[0] else 0 for r in rows], dtype=float)
    p_v2 = np.array([r[1] for r in rows], dtype=float)
    p_v3 = np.array([r[2] for r in rows], dtype=float) if have_v3 else None
    p_v2_t = np.array([r[3] for r in rows], dtype=float)
    p_v3_t = np.array([r[4] for r in rows], dtype=float) if have_v3 else None
    if y.sum() == 0 or y.sum() == len(y):
        raise SystemExit("need BOTH real and fake clips (name fakes *_clone*).")

    a, b = fit_platt(p_v2, y)
    # Clamp to EXACTLY what ml.scoring._load_cal() enforces at runtime, then band
    # the CLAMPED values -- t_low/t_high must describe the scores the app will
    # actually produce, not an unclamped fit that gets silently rescued on load.
    a_c, b_c = min(max(a, 0.5), 1.5), min(max(b, -8.0), 8.0)
    if (a_c, b_c) != (a, b):
        print(f"! raw fit a={a:.3f} b={b:.3f} exceeds scoring.py's clamp -> "
              f"using clamped a={a_c:.3f} b={b_c:.3f} for bands (this is what will actually run)")
    a, b = a_c, b_c
    fused = fuse(calibrate_ab(p_v2, a, b), p_v3)
    fused_t = fuse(calibrate_ab(p_v2_t, a, b), p_v3_t)
    fr, ff = fused[y == 0], fused[y == 1]
    frt, fft = fused_t[y == 0], fused_t[y == 1]
    t_low, t_high = bands(fr)

    print("\n" + "=" * 60)
    print(f"a={a:.3f}  b={b:.3f}   t_low={t_low:.3f}  t_high={t_high:.3f}")
    print(f"clean:     EER~{eer(fr, ff):.1%}   real max={fr.max():.3f}  fake min={ff.min():.3f}  gap={ff.min()-fr.max():+.3f}")
    print(f"telephony: EER~{eer(frt, fft):.1%}   real max={frt.max():.3f}  fake min={fft.min():.3f}")
    print("=" * 60)

    # Self-diagnosing outlier flag: a REAL clip the model itself ranks near/above
    # the fakes is a MODEL gap (out-of-domain voice/mic/room) that no threshold can
    # fix -- calibration can only place the line, not un-invert a wrong ranking.
    # Surfaces automatically on any future dataset, not just today's known-bad clips.
    real_names = [n for n, r in zip(names, rows) if not r[0]]
    for n, score in zip(real_names, fr):
        if score >= t_low:
            print(f"! OUTLIER REAL: {n} fused={score:.3f} sits AT/ABOVE t_low={t_low:.3f} -- "
                  f"the model itself misranks this clip; needs retraining on more diverse real "
                  f"data, not a calibration fix. Don't use it as demo material.")

    json.dump({"a": a, "b": b, "t_low": t_low, "t_high": t_high},
              open(_OUT, "w"), indent=2)
    print(f"wrote {os.path.abspath(_OUT)}\nRESTART the backend to load it.")


def _selfcheck():
    # math-only: well-separated synthetic scores must fit to a low EER and put the
    # bands between the classes. Guards the abstain/calibration path (money/security).
    rng = np.random.default_rng(0)
    p_real = np.clip(rng.normal(0.15, 0.05, 60), 1e-4, 0.5)   # reals: low spoof prob
    p_fake = np.clip(rng.normal(0.85, 0.05, 60), 0.5, 1 - 1e-4)
    p = np.r_[p_real, p_fake]
    y = np.r_[np.zeros(60), np.ones(60)]
    a, b = fit_platt(p, y)
    fused = calibrate_ab(p, a, b)
    fr, ff = fused[:60], fused[60:]
    e = eer(fr, ff)
    t_low, t_high = bands(fr)
    assert e < 0.05, f"separable data should fit low EER, got {e:.3f}"
    assert fr.max() < ff.min() + 0.2, "reals should sit below fakes"
    assert 0 < t_low <= t_high <= 0.95, (t_low, t_high)
    assert fuse(np.array([0.9]), np.array([0.9]))[0] == 0.9  # fusion mean sanity
    print(f"fit_calibration self-check ok (EER~{e:.1%}, t_low={t_low:.2f}, t_high={t_high:.2f})")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    exclude = ()
    for a_ in sys.argv[1:]:
        if a_.startswith("--exclude="):
            exclude = tuple(s.strip() for s in a_[len("--exclude="):].split(",") if s.strip())
    if "--selfcheck" in sys.argv:
        _selfcheck()
    else:
        main(args[0] if args else _DEFAULT_DIR, exclude=exclude)
