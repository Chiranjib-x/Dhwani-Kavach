"""Random one-time digit challenges + tolerant matching of what Whisper heard.

The random challenge is Gate 1 and the backbone of the whole security model: a
fresh 6-digit code, single-use, 90 s expiry, kills every replay and every
pre-generated clone. Matching is homophone- and single-error-tolerant so a
genuine caller isn't failed for one misheard digit.
"""
from __future__ import annotations

import secrets

from verify_app import config


def new_prime(randomize: bool | None = None) -> str:
    """A plosive-rich word said with the digits to elicit pop noise (near-field
    liveness). randomize=False (TESTING) returns the fixed word so you can repeat
    tests without word variability; None -> config.RANDOMIZE_PRIME default."""
    randomize = config.RANDOMIZE_PRIME if randomize is None else randomize
    if not randomize:
        return config.FIXED_PRIME
    return secrets.choice(config.PLOSIVE_PRIMES).strip()


def new_challenge(n: int | None = None, randomize: bool | None = None) -> str:
    """A one-time digit code. randomize=False (TESTING) returns the fixed code so
    you can read the same digits every time; None -> config.RANDOMIZE default."""
    n = n or config.CHALLENGE_LEN
    randomize = config.RANDOMIZE if randomize is None else randomize
    if not randomize:
        return (config.FIXED_CHALLENGE * n)[:n]      # fixed, length-normalized
    return "".join(secrets.choice("0123456789") for _ in range(n))


# Spoken-word -> digit, including the homophones people actually say and Whisper
# actually emits ("oh" for zero, "for"/"to"/"ate" mishears).
_W2D = {
    "zero": "0", "oh": "0", "o": "0", "naught": "0", "nought": "0",
    "one": "1", "won": "1",
    "two": "2", "to": "2", "too": "2",
    "three": "3", "tree": "3",
    "four": "4", "for": "4", "fore": "4",
    "five": "5",
    "six": "6",
    "seven": "7",
    "eight": "8", "ate": "8",
    "nine": "9",
}


def digits_from(text: str) -> str:
    """Extract a digit string from free ASR text: keep literal digits, map
    spelled-out number words (and their homophones)."""
    out: list[str] = []
    cleaned = "".join(c if c.isalnum() else " " for c in text.lower())
    for tok in cleaned.split():
        if tok.isdigit():
            out.extend(tok)
        elif tok in _W2D:
            out.append(_W2D[tok])
    return "".join(out)


def edit_distance(a: str, b: str) -> int:
    """Levenshtein distance (iterative, O(len(a)*len(b)) time, O(len(b)) space)."""
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[-1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def content_ok(expected: str, transcript: str, max_edits: int | None = None) -> dict:
    """Gate 1 decision: did the caller read the challenge? Tolerates <= max_edits
    (default from config) so one misheard digit doesn't fail a genuine caller —
    the 6-digit space keeps guessing infeasible (<=13 of 10^6 within distance 1)."""
    max_edits = config.CONTENT_MAX_EDITS if max_edits is None else max_edits
    heard = digits_from(transcript)
    d = edit_distance(expected, heard)
    return {"expected": expected, "heard": heard, "edits": d, "ok": d <= max_edits}
