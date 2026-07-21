import json
import math
import os

import numpy as np

# Two INDEPENDENT neural detectors (different architectures, different
# training data/objectives -> different failure modes) plus 4 purely-acoustic
# heuristics. No single signal can dominate the verdict:
#   aasist   -- ml/detector.py's primary neural slot (currently the Codecfake
#               W2VAASIST-cotrain detector: a codec/compression-artifact
#               specialist, not trained on live voice-clone attacks).
#   clone_v3 -- ml/detector_v3.py: wav2vec2-XLSR-53 fine-tuned specifically on
#               modern commercial TTS/clone engines (ElevenLabs etc.) --
#               matches the actual threat model directly.
# Audio-deepfake generalization research (e.g. Muller et al., "Does Audio
# Deepfake Detection Generalize?", Interspeech 2022) documents 200-1000% EER
# degradation for SSL-based countermeasures evaluated out-of-domain -- this
# is why we don't trust either neural detector alone. Fusion measurably
# improves cross-domain robustness (~38% relative EER reduction reported for
# spectral+SSL fusion on cross-dataset benchmarks vs. an SSL-only detector).
#
# NEURAL-ONLY verdict. The acoustic heuristics were measured to be near-noise --
# breath returns ~0.75 on EVERYTHING, and mfcc/phase/liveness sit near 0 for both
# real and fake, so they don't separate the classes; any non-zero weight just
# pulls a confident clone (aasist~0.8, clone_v3~0.98) back toward AMBER. That
# dilution was the "mostly amber, never a clean RED" symptom. The learned-fusion
# experiment independently drove the heuristic coefficients to ~0. So the two
# INDEPENDENT neural detectors now carry the ENTIRE verdict (0.5/0.5); when only
# one is loaded (compute_ensemble redistributes missing keys) it carries it alone.
# The heuristics stay COMPUTED and fully visible in layer_breakdown as human-
# readable EVIDENCE, but their weight is 0 -- they inform, they don't vote.
# (Weights still sum to 1.0 so the ensemble unit tests hold; a 0-weight key
# contributes 0 and is redistribution-neutral.)
WEIGHTS = {
    "aasist":   0.50,
    "clone_v3": 0.50,
    "mfcc":     0.0,
    "breath":   0.0,
    "phase":    0.0,
    "liveness": 0.0,
}


# L6 learned fusion (eval/fit_fusion.py). A logistic regression over the per-layer
# scores that REPLACES the hand weights above -- the eval showed the hand weights
# let the acoustic heuristics dilute a strong neural detector (AUC 0.996 -> 0.887,
# recovered to ~0.92 LOO-CV by the learned fusion, which down-weights the layers
# that don't separate the data).
#
# OPT-IN via DHWANI_FUSION=1 so a fusion.json fit on a small set never silently
# changes the default verdict (staged rollout, same spirit as shadow mode). Ship it
# as default only after refitting on production-scale data.
_FUSION_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "fusion.json")


def _load_fusion():
    if not os.environ.get("DHWANI_FUSION", "").strip():
        return None
    try:
        with open(_FUSION_PATH) as f:
            fu = json.load(f)
        assert len(fu["layers"]) == len(fu["coef"])
        return fu
    except Exception:
        return None


_FUSION = _load_fusion()


def reload_fusion() -> bool:
    """Re-read fusion.json without a restart (e.g. after refitting)."""
    global _FUSION
    _FUSION = _load_fusion()
    return _FUSION is not None


def compute_ensemble(layer_scores: dict) -> dict:
    """
    Combine per-layer spoof probabilities into a final risk score.

    Parameters
    ----------
    layer_scores : dict
        Spoof probabilities in [0, 1], keyed by (a subset of) WEIGHTS. With the
        hand-weight fallback, a missing key has its weight redistributed across
        whatever IS present (never a silent confident-real vote). With the learned
        L6 fusion, a missing layer contributes 0 (its coefficient x 0).

    Returns
    -------
    dict with risk_score (int 0-100) and alert_level (GREEN/AMBER/RED).
    """
    if _FUSION is not None:
        z = _FUSION["intercept"] + sum(
            c * float(layer_scores.get(name, 0.0))
            for name, c in zip(_FUSION["layers"], _FUSION["coef"]))
        risk_float = 1.0 / (1.0 + math.exp(-z))
    else:
        active = {k: w for k, w in WEIGHTS.items() if k in layer_scores}
        total_w = sum(active.values()) or 1.0
        risk_float = sum(layer_scores[k] * w for k, w in active.items()) / total_w
    risk_score = int(round(np.clip(risk_float * 100, 0, 100)))

    if risk_score >= 70:
        alert_level = "RED"
    elif risk_score >= 40:
        alert_level = "AMBER"
    else:
        alert_level = "GREEN"

    return {"risk_score": risk_score, "alert_level": alert_level}
