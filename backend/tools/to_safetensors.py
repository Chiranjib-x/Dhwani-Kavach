"""Convert the W2VAASIST head checkpoint to safetensors (security hardening).

The champion head ships as `w2v2aasist_cotrain.pt`, saved with torch.save(model)
-- a full pickled nn.Module. Loading it needs torch.load(weights_only=False) AND
a sys.modules["model"] alias so pickle can find the class. Unpickling an
arbitrary object is a remote-code-execution vector: a swapped checkpoint runs
whatever it wants at load time.

This reads the pickled module ONCE (here, deliberately, with the alias), extracts
its state_dict, and rewrites it as `w2v2aasist_cotrain.safetensors` -- pure
tensors, no code. ml.detector_v2 then loads the state_dict into a freshly
constructed W2VAASIST() with no pickle and no alias.

Idempotent: skips if the .safetensors already exists. Prints a SHA-256 so the
artifact can be pinned in model_registry.json.

usage: PYTHONPATH=backend python backend/tools/to_safetensors.py
"""
from __future__ import annotations

import hashlib
import os
import sys
import types

import torch

from ml.vendor import codecfake_model
from ml.vendor.codecfake_model import W2VAASIST

_MODELS = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "models"))
_PT = os.path.join(_MODELS, "w2v2aasist_cotrain.pt")
_ST = os.path.join(_MODELS, "w2v2aasist_cotrain.safetensors")


def _alias_model_module() -> None:
    if "model" in sys.modules:
        return
    fake = types.ModuleType("model")
    for name in ("W2VAASIST", "GraphAttentionLayer", "HtrgGraphAttentionLayer",
                 "GraphPool", "Residual_block"):
        setattr(fake, name, getattr(codecfake_model, name))
    sys.modules["model"] = fake


def _state_dict():
    _alias_model_module()
    obj = torch.load(_PT, map_location="cpu", weights_only=False)
    if isinstance(obj, torch.nn.Module):
        return obj.state_dict()
    if isinstance(obj, dict):
        return obj.get("model", obj.get("state_dict", obj))
    raise TypeError(f"unexpected checkpoint type: {type(obj)}")


def main():
    if not os.path.exists(_PT):
        raise SystemExit(f"missing {_PT}")
    if os.path.exists(_ST):
        print(f"already exists: {_ST}")
        return

    from safetensors.torch import save_file
    sd = _state_dict()
    # safetensors requires contiguous CPU tensors and no shared storage.
    sd = {k: v.detach().cpu().contiguous().clone() for k, v in sd.items()}

    # Prove it round-trips into a real W2VAASIST before trusting it.
    W2VAASIST().load_state_dict(sd)

    save_file(sd, _ST)
    h = hashlib.sha256(open(_ST, "rb").read()).hexdigest()
    print(f"wrote {_ST} ({os.path.getsize(_ST)/1e6:.0f} MB)")
    print(f"sha256 {h}")


if __name__ == "__main__":
    main()
