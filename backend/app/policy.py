"""Shadow vs enforce policy.

Banks pilot in *shadow* — score every call and log the verdict, but take no
action — before trusting the system to enforce (challenge/block). Toggle with
the DHWANI_SHADOW env var; a per-request override wins when provided.
ponytail: env flag + override; per-tenant policy only when a second tenant exists.
"""
from __future__ import annotations

import os

_TRUE = {"1", "true", "yes", "on"}


def is_shadow(override: bool | None = None) -> bool:
    if override is not None:
        return override
    return os.environ.get("DHWANI_SHADOW", "").strip().lower() in _TRUE


def annotate(result: dict, shadow: bool) -> dict:
    """Tag a verdict with its policy mode. In shadow mode the action is advisory."""
    result["mode"] = "shadow" if shadow else "enforce"
    result["enforced"] = not shadow
    return result
