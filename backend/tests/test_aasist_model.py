import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import numpy as np
import torch
from ml.aasist_model import AASISTModel, load_aasist, infer
from ml.audio_utils import CHUNK_SAMPLES

MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "AASIST.pth")


def make_audio(seed=0):
    rng = np.random.RandomState(seed)
    return (rng.randn(CHUNK_SAMPLES) * 0.1).astype(np.float32)


def test_model_loads():
    model = load_aasist(MODEL_PATH)
    assert isinstance(model, AASISTModel)
    assert next(model.parameters()).device.type == "cpu"
    print("  [OK] load_aasist")


def test_model_eval_mode():
    model = load_aasist(MODEL_PATH)
    assert not model.training, "model should be in eval mode after load"
    print("  [OK] model is in eval mode")


def test_forward_shape():
    model = load_aasist(MODEL_PATH)
    x = torch.from_numpy(make_audio()).unsqueeze(0)  # (1, 64000)
    with torch.no_grad():
        last_hidden, logits = model(x)
    assert logits.shape == (1, 2), f"expected (1,2) got {tuple(logits.shape)}"
    assert last_hidden.shape == (1, 160), f"expected (1,160) got {tuple(last_hidden.shape)}"
    print(f"  [OK] forward shapes: logits={tuple(logits.shape)}, hidden={tuple(last_hidden.shape)}")


def test_infer_range():
    model = load_aasist(MODEL_PATH)
    score = infer(model, make_audio())
    assert 0.0 <= score <= 1.0, f"score out of [0,1]: {score}"
    print(f"  [OK] infer score in [0,1]: {score:.4f}")


def test_infer_deterministic():
    model = load_aasist(MODEL_PATH)
    audio = make_audio()
    s1 = infer(model, audio)
    s2 = infer(model, audio)
    assert abs(s1 - s2) < 1e-5, "infer not deterministic in eval mode"
    print(f"  [OK] infer is deterministic: {s1:.6f} == {s2:.6f}")


def test_infer_different_inputs():
    model = load_aasist(MODEL_PATH)
    s1 = infer(model, make_audio(seed=0))
    s2 = infer(model, make_audio(seed=42))
    assert s1 != s2, "different inputs produced identical scores"
    print(f"  [OK] different inputs produce different scores: {s1:.4f} vs {s2:.4f}")


def test_batch_consistency():
    from ml.audio_utils import preprocess
    model = load_aasist(MODEL_PATH)
    a1 = preprocess(make_audio(seed=0))
    a2 = preprocess(make_audio(seed=1))
    s_single_1 = infer(model, a1)
    s_single_2 = infer(model, a2)
    x = torch.stack([torch.from_numpy(a1), torch.from_numpy(a2)])
    with torch.no_grad():
        _, logits = model(x)
        probs = torch.softmax(logits, dim=1)[:, 1].tolist()
    assert abs(probs[0] - s_single_1) < 1e-4, "batch/single mismatch for sample 0"
    assert abs(probs[1] - s_single_2) < 1e-4, "batch/single mismatch for sample 1"
    print(f"  [OK] batch consistent with single inference")


if __name__ == "__main__":
    print("=" * 50)
    print("Phase 1B -- AASIST Inference Tests")
    print("=" * 50)
    tests = [
        test_model_loads,
        test_model_eval_mode,
        test_forward_shape,
        test_infer_range,
        test_infer_deterministic,
        test_infer_different_inputs,
        test_batch_consistency,
    ]
    failed = []
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed.append(t.__name__)
    print("=" * 50)
    if failed:
        print(f"FAILED: {failed}")
        sys.exit(1)
    else:
        print(f"All {len(tests)} tests passed. Phase 1B complete.")
