"""One-time port: XLSR-SLS public checkpoint (fairseq) -> our transformers stack.

The strongest public open-weights deepfake detector we found (Zhang et al., ACM MM
2024, github.com/QiShanZhang/SLSforASVspoof-2021-DF) reports 1.92% EER on
ASVspoof21-DF and 7.46% on In-the-Wild -- In-the-Wild being real-world
varied-mic/room audio, exactly the channel our home-trained bundle collapses on.
The HF mirror (sukhdeveyash/XLS-R-SLS-Deepfake-Detection, v1/epoch_2.pth)
reproduces DF=2.14% / Wild=7.84%.

Their checkpoint is fairseq-based, but the SSL backbone is the SAME
wav2vec2-xls-r-300m we already run via transformers -- only the tensor NAMES
differ. This script remaps every backbone tensor fairseq->HF (the same mapping
transformers' own convert_wav2vec2_original_pytorch_checkpoint_to_pytorch.py
encodes), carries the 4-layer SLS head over verbatim, and writes a single
models/xlsr_sls.safetensors bundle (backbone.* + head.*) that ml/detector_v4.py
loads with zero fairseq dependency.

Run once:
    python -m tools.port_sls            # reads the HF-cached epoch_2.pth
    python -m tools.port_sls <path.pth> # or an explicit checkpoint path

Every source key must be consumed (mapped or in the explicit pretraining-only
drop list) and every target key filled, or this FAILS LOUDLY -- a silently
half-mapped backbone would produce plausible-looking garbage scores.
"""
from __future__ import annotations

import os
import re
import sys

import torch

_OUT = os.path.join(os.path.dirname(__file__), "..", "models", "xlsr_sls.safetensors")

# fairseq keys that exist only for wav2vec2 PRE-TRAINING (quantization); the
# fine-tuned inference path never touches them. (mask_emb IS carried over, as
# masked_spec_embed -- inference never uses it either, but HF registers it as a
# Parameter so strict loading demands it.)
_DROP = re.compile(r"^(quantizer\.|project_q\.|final_proj\.)")

# encoder.layer_norm is the FINAL layer norm. SLS consumes per-layer outputs
# (fairseq layer_results) which do NOT have it applied, so detector_v4 replaces
# that module with Identity -- meaning the runtime model has no such keys to
# load. Dropped, with a note, rather than carried dead weight.
_DROP_FINAL_LN = re.compile(r"^encoder\.layer_norm\.")

_LAYER_MAP = {
    "self_attn.k_proj": "attention.k_proj",
    "self_attn.v_proj": "attention.v_proj",
    "self_attn.q_proj": "attention.q_proj",
    "self_attn.out_proj": "attention.out_proj",
    "self_attn_layer_norm": "layer_norm",
    "fc1": "feed_forward.intermediate_dense",
    "fc2": "feed_forward.output_dense",
    "final_layer_norm": "final_layer_norm",
}


def map_backbone_key(k: str, pos_conv_parametrized: bool) -> str | None:
    """fairseq wav2vec2 (layer_norm-mode, i.e. XLS-R) key -> HF Wav2Vec2Model key.
    Returns None for keys that are deliberately dropped."""
    if _DROP.match(k) or _DROP_FINAL_LN.match(k):
        return None
    if k == "mask_emb":
        return "masked_spec_embed"

    # conv feature extractor: Sequential indices -> named modules
    m = re.match(r"^feature_extractor\.conv_layers\.(\d+)\.0\.(weight|bias)$", k)
    if m:
        return f"feature_extractor.conv_layers.{m.group(1)}.conv.{m.group(2)}"
    m = re.match(r"^feature_extractor\.conv_layers\.(\d+)\.2\.1\.(weight|bias)$", k)
    if m:
        return f"feature_extractor.conv_layers.{m.group(1)}.layer_norm.{m.group(2)}"

    if k in ("post_extract_proj.weight", "post_extract_proj.bias"):
        return k.replace("post_extract_proj", "feature_projection.projection")
    # fairseq's top-level layer_norm normalizes conv features pre-projection
    if k in ("layer_norm.weight", "layer_norm.bias"):
        return k.replace("layer_norm", "feature_projection.layer_norm")

    # positional conv (weight-normed): weight_g/weight_v vs parametrizations naming
    m = re.match(r"^encoder\.pos_conv\.0\.(weight_g|weight_v|bias)$", k)
    if m:
        part = m.group(1)
        if part == "bias":
            return "encoder.pos_conv_embed.conv.bias"
        if pos_conv_parametrized:
            return ("encoder.pos_conv_embed.conv.parametrizations.weight.original0"
                    if part == "weight_g" else
                    "encoder.pos_conv_embed.conv.parametrizations.weight.original1")
        return f"encoder.pos_conv_embed.conv.{part}"

    # encoder transformer layers
    m = re.match(r"^encoder\.layers\.(\d+)\.(.+)$", k)
    if m:
        idx, rest = m.group(1), m.group(2)
        for src, dst in _LAYER_MAP.items():
            if rest.startswith(src + "."):
                return f"encoder.layers.{idx}.{dst}{rest[len(src):]}"
    return "?" + k  # unknown -> caught by the caller


def main(ckpt_path: str | None = None):
    if ckpt_path is None:
        from huggingface_hub import hf_hub_download
        ckpt_path = hf_hub_download("sukhdeveyash/XLS-R-SLS-Deepfake-Detection", "v1/epoch_2.pth")
    print(f"loading {ckpt_path}")
    sd = torch.load(ckpt_path, map_location="cpu", weights_only=True)
    # saved from nn.DataParallel -> every key is prefixed "module."
    sd = {(k[len("module."):] if k.startswith("module.") else k): v for k, v in sd.items()}

    # Build the runtime target to learn its exact key set (incl. whether this
    # torch names pos_conv weight-norm tensors parametrizations.* or weight_g/v).
    from ml import detector_v4
    model = detector_v4._build_backbone()
    target_keys = set(model.state_dict().keys())
    pos_conv_parametrized = any("parametrizations" in k for k in target_keys)

    backbone, head, dropped, unknown = {}, {}, [], []
    for k, v in sd.items():
        if k.startswith("ssl_model.model."):
            fk = k[len("ssl_model.model."):]
            hk = map_backbone_key(fk, pos_conv_parametrized)
            if hk is None:
                dropped.append(fk)
            elif hk.startswith("?"):
                unknown.append(fk)
            else:
                backbone["backbone." + hk] = v
        elif k.split(".")[0] in ("first_bn", "fc0", "fc1", "fc3"):
            head["head." + k] = v
        else:
            unknown.append(k)

    print(f"mapped {len(backbone)} backbone + {len(head)} head tensors; "
          f"dropped {len(dropped)} pretraining-only/final-LN keys")
    if unknown:
        raise SystemExit(f"UNMAPPED KEYS (port would be silently wrong): {unknown[:20]}")

    # Coverage check against the real runtime model: nothing missing, nothing extra.
    got = {k[len("backbone."):] for k in backbone}
    missing = target_keys - got
    extra = got - target_keys
    # num_batches_tracked etc. only exist on BatchNorm (head side, checked below)
    if missing or extra:
        raise SystemExit(f"backbone key mismatch:\n  missing from ckpt: {sorted(missing)[:10]}"
                         f"\n  not in model: {sorted(extra)[:10]}")

    shead = detector_v4.SLSHead()
    hgot = {k[len("head."):] for k in head}
    hneed = set(shead.state_dict().keys())
    if hgot != hneed:
        raise SystemExit(f"head key mismatch:\n  missing: {sorted(hneed - hgot)}"
                         f"\n  extra: {sorted(hgot - hneed)}")

    from safetensors.torch import save_file
    out = {**backbone, **head}
    out = {k: v.contiguous() for k, v in out.items()}
    save_file(out, os.path.abspath(_OUT))
    size_mb = os.path.getsize(os.path.abspath(_OUT)) / 1e6
    print(f"wrote {os.path.abspath(_OUT)} ({size_mb:.0f} MB)")
    print("now run:  python -m ml.detector_v4   (self-check)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
