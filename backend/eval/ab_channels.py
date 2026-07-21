"""Channel-robust A/B: detector_v2 vs detector_v4 vs fusion, across the
acoustic channels a live call actually traverses.

Motivation (measured this session): v2 (home fine-tune) nails the user's own
phone-mic recordings but inverts on out-of-domain studio voices; ported SLS (v4)
nails studio/in-the-wild voices but stumbles on some phone-mic clips. Their
failures ANTI-CORRELATE, so this harness scores every labeled clip through both
models over {clean, reverb, noise, telephony, replay-sim} and reports per-channel
EER for v2, v4, mean-fusion, and max-fusion. The winner takes the detect path.

Data: sample_audio/ (naming: *clone* = fake) + eval/corpus/{real,fake}.
Windowing is production-matched per model: v2 scores 64000-sample windows (its
fine-tune distribution); v4 scores exact-64600 windows (its ASVspoof training
cut -- feeding it repeat-pad-spliced 64000 windows reads the splice as a
synthetic artifact; verified: real-clip mean 0.46 spliced vs 0.19 exact).
Per-clip aggregate = max over a 2-window moving average -- the offline analog of
the stream's EWMA + confirm=2 (one spiky window never decides a call).

Run (background; ~20-40 min CPU):
    python -m eval.ab_channels            # writes eval/ab_channels.json + prints table
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np

from ml.audio_utils import load_audio, chunk_audio, SAMPLE_RATE
from ml.telephony import to_telephony
from tools.augment import add_reverb, add_noise

_HERE = os.path.dirname(__file__)
_OUT = os.path.join(_HERE, "ab_channels.json")
_SILENCE_RMS = 1e-3
_V4_CUT = 64600


def channels(x: np.ndarray) -> dict[str, np.ndarray]:
    """The acoustic paths a call traverses. Fixed seeds -> reproducible."""
    return {
        "clean": x,
        "reverb": add_reverb(x, rt60=0.5, seed=7),
        "noise": add_noise(x, snr_db=10, seed=7),
        "telephony": to_telephony(x, SAMPLE_RATE),
        # speaker -> room -> phone line: the replay/laundering path
        "replay": to_telephony(add_noise(add_reverb(x, rt60=0.3, seed=11), 15, seed=11), SAMPLE_RATE),
    }


def _voiced(chunks: list[np.ndarray]) -> list[np.ndarray]:
    v = [c for c in chunks if float(np.sqrt(np.mean(c.astype(np.float64) ** 2))) >= _SILENCE_RMS]
    return v or chunks


def clip_score(window_probs: list[float]) -> float:
    """max of 2-window moving average == offline confirm-2 aggregate."""
    p = np.asarray(window_probs, dtype=float)
    if len(p) == 1:
        return float(p[0])
    return float(np.max((p[:-1] + p[1:]) / 2))


def eer(reals: np.ndarray, fakes: np.ndarray) -> float:
    scores = np.concatenate([reals, fakes])
    labels = np.concatenate([np.zeros(len(reals)), np.ones(len(fakes))])
    order = np.argsort(scores)
    best = 1.0
    for t in scores[order]:
        far = np.mean(reals >= t)          # false alarm on reals
        frr = np.mean(fakes < t)           # miss on fakes
        best = min(best, max(far, frr))
    return best


def collect() -> list[tuple[str, bool, np.ndarray]]:
    items = []
    for f in sorted(glob.glob(os.path.join(_HERE, "..", "..", "sample_audio", "*"))):
        try:
            x, _ = load_audio(f)
        except Exception:
            continue
        items.append((os.path.basename(f), "clone" in os.path.basename(f).lower(), x))
    for label, sub in [(False, "real"), (True, "fake")]:
        for f in sorted(glob.glob(os.path.join(_HERE, "corpus", sub, "*.wav"))):
            x, _ = load_audio(f)
            items.append((f"corpus/{sub}/{os.path.basename(f)}", label, x))
    return items


def main():
    from ml import detector_v2, detector_v4
    items = collect()
    print(f"{len(items)} labeled clips", flush=True)

    rows = []  # per clip x channel: {name, fake, channel, v2, v4}
    for name, fake, x in items:
        for ch, xa in channels(x).items():
            w2 = _voiced(chunk_audio(xa))                                   # 64000, v2's cut
            w4 = _voiced(chunk_audio(xa, chunk_samples=_V4_CUT, hop_samples=_V4_CUT))
            s2 = clip_score(detector_v2.infer_batch(w2))
            s4 = clip_score(detector_v4.infer_batch(w4))
            rows.append({"name": name, "fake": fake, "channel": ch, "v2": s2, "v4": s4})
        done = [r for r in rows if r["name"] == name]
        print(f"  {name}: " + " ".join(f"{r['channel']}=v2:{r['v2']:.2f}/v4:{r['v4']:.2f}" for r in done),
              flush=True)

    json.dump(rows, open(_OUT, "w"), indent=1)

    print("\n=== per-channel EER (lower is better) ===")
    print(f"{'channel':10} {'v2':>7} {'v4':>7} {'mean':>7} {'max':>7}")
    for ch in ["clean", "reverb", "noise", "telephony", "replay"]:
        sub = [r for r in rows if r["channel"] == ch]
        r2 = np.array([r["v2"] for r in sub if not r["fake"]])
        f2 = np.array([r["v2"] for r in sub if r["fake"]])
        r4 = np.array([r["v4"] for r in sub if not r["fake"]])
        f4 = np.array([r["v4"] for r in sub if r["fake"]])
        e2, e4 = eer(r2, f2), eer(r4, f4)
        em = eer((r2 + r4) / 2, (f2 + f4) / 2)
        ex = eer(np.maximum(r2, r4), np.maximum(f2, f4))
        print(f"{ch:10} {e2:7.1%} {e4:7.1%} {em:7.1%} {ex:7.1%}")
    print(f"\nwrote {os.path.abspath(_OUT)}")


if __name__ == "__main__":
    main()
