# backend/tools/fit_calibration.py
# usage: PYTHONPATH=backend python backend/tools/fit_calibration.py devkit/real devkit/fake
import json, math, sys, glob, os
import numpy as np
from ml.audio_utils import load_audio
from ml import detector_v2  # V2 model wrapper exposing infer_raw(audio)->(p, logit)

def scores(folder):
    out = []
    for f in glob.glob(os.path.join(folder, "*.wav")):
        audio, _ = load_audio(f)
        out.append(detector_v2.infer_raw(audio)[0])
    return np.clip(np.array(out), 1e-6, 1 - 1e-6)

real, fake = scores(sys.argv[1]), scores(sys.argv[2])
z = np.log(np.r_[real, fake] / (1 - np.r_[real, fake]))
y = np.r_[np.zeros(len(real)), np.ones(len(fake))]
a, b = 1.0, 0.0                                   # logistic regression, Newton steps
for _ in range(50):
    p = 1 / (1 + np.exp(-(a * z + b)))
    g = np.array([np.sum((p - y) * z), np.sum(p - y)])
    w = p * (1 - p)
    H = np.array([[np.sum(w * z * z), np.sum(w * z)],
                  [np.sum(w * z),     np.sum(w)]]) + 1e-6 * np.eye(2)
    a, b = np.array([a, b]) - np.linalg.solve(H, g)
pr = 1 / (1 + np.exp(-(a * np.log(real / (1 - real)) + b)))
t_high = float(np.quantile(pr, 0.99))             # 1% FPR on bonafide dev
t_low  = float(np.quantile(pr, 0.95))             # 5% FPR
# EER for the slide:
pf = 1 / (1 + np.exp(-(a * np.log(fake / (1 - fake)) + b)))
ts = np.linspace(0, 1, 1001)
fpr = [(pr >= t).mean() for t in ts]; fnr = [(pf < t).mean() for t in ts]
eer = min(zip(fpr, fnr), key=lambda x: abs(x[0] - x[1]))
print(f"a={a:.3f} b={b:.3f} t_low={t_low:.3f} t_high={t_high:.3f} "
      f"EER~{(eer[0]+eer[1])/2:.3%}")  # ascii '~' not '≈': Windows cp1252 consoles
json.dump({"a": float(a), "b": float(b), "t_low": t_low, "t_high": t_high},
          open("backend/models/calibration.json", "w"), indent=2)