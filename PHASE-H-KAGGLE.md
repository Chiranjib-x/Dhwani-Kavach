# Phase H — Telephony-Robust Retraining (Kaggle runbook)

Goal: the wav2vec2 detector works on real 8 kHz, band-limited, G.711, lossy
phone lines — not just clean mic audio. Run this on Kaggle (T4 GPU) in parallel
while the engineering phases (I, J) are built. Reuse your existing wav2vec2
training notebook; this only changes the data.

The augmentation is already in the repo: [`backend/ml/telephony.py`](backend/ml/telephony.py)
(`to_telephony(audio, sr, packet_loss)`). Copy that file into the Kaggle notebook.

---

## Step 1 — Add the augmentation to your dataset
In the training `Dataset.__getitem__`, after loading the waveform, randomly
degrade ~50% of samples so the model sees both clean and telephony audio:

```python
from telephony import to_telephony   # the repo file, copied into the notebook

def augment(wav, sr=16000):
    import random
    if random.random() < 0.5:                       # 50% telephony
        wav = to_telephony(wav, sr,
                           packet_loss=random.choice([0.0, 0.0, 0.05, 0.1]))
    return wav
```

Apply `augment(wav)` to **both** real and fake training clips. Keep the rest of
the recipe (per-utterance standardise, pad/trim to 4 s, etc.) unchanged.

## Step 2 — Build an 8 kHz telephony eval set
Take your held-out eval set and make a telephony copy (don't augment eval
randomly — keep it fixed so results are comparable):

```python
eval_tel = [(to_telephony(w), label) for (w, label) in eval_clean]
```

You now have two eval sets: `eval_clean` and `eval_tel`.

## Step 3 — Retrain
Same training loop, same hyperparameters, just with `augment()` in the loader.
T4 GPU (P100 is incompatible). ~same epochs as before.

## Step 4 — Validate (the gate)
Report EER on both sets, for the new model vs the current one:

| Model | EER clean | EER telephony |
|-------|-----------|---------------|
| current (`deepfake_w2v.pt`) | baseline | **measure this — expect it's worse** |
| retrained (+telephony aug) | should stay ~same | **should improve a lot** |

✅ Ship if: telephony EER drops meaningfully **and** clean EER doesn't regress.

## Step 5 — Save & deploy
- Kaggle: **Save Version** (so it survives session wipes).
- Download the weights, replace `backend/models/deepfake_w2v.pt` locally.
- Keep the old file as `deepfake_w2v_v1.pt` (rollback + model registry / Phase J).
- Restart the backend — no code change needed; inference already resamples.

---

## Notes
- Inference already handles 8 kHz (librosa loads any rate → 16 kHz), so **no
  backend change is required** — this is purely a better-trained weight file.
- Demo today (pre-retrain): you can already play a clone through the phone
  filter and show it stays RED. Retraining makes that reliable across voices.
- Effort: the long pole is data + GPU time, which is why it runs in parallel.
