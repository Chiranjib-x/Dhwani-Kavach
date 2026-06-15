import numpy as np

# AASIST is the only trained classifier in the pipeline;
# layers 2-5 are signal-processing heuristics that provide supporting signal.
# Weights reflect that disparity honestly.
WEIGHTS = {
    "aasist":   0.60,
    "mfcc":     0.10,
    "breath":   0.10,
    "phase":    0.10,
    "liveness": 0.10,
}


def compute_ensemble(layer_scores: dict) -> dict:
    """
    Combine per-layer spoof probabilities into a final risk score.

    Parameters
    ----------
    layer_scores : dict
        Keys must include all entries of WEIGHTS; values in [0, 1].

    Returns
    -------
    dict with risk_score (int 0-100) and alert_level (GREEN/AMBER/RED).
    """
    risk_float = float(
        sum(layer_scores.get(k, 0.0) * w for k, w in WEIGHTS.items())
    )
    risk_score = int(round(np.clip(risk_float * 100, 0, 100)))

    if risk_score >= 70:
        alert_level = "RED"
    elif risk_score >= 40:
        alert_level = "AMBER"
    else:
        alert_level = "GREEN"

    return {"risk_score": risk_score, "alert_level": alert_level}
