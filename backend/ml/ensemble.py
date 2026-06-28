import numpy as np

# The "aasist" slot is the trained neural model (now wav2vec2, ~0.4% dev EER) and
# carries the verdict. The 4 heuristics measurably under-perform it on real audio
# (e.g. breath returns a constant ~0.75 on short windows), so they're kept as
# minor supporting signal only. Weights reflect that honestly.
WEIGHTS = {
    "aasist":   0.80,
    "mfcc":     0.07,
    "breath":   0.03,
    "phase":    0.05,
    "liveness": 0.05,
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
