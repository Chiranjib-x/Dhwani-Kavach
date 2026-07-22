"""Random one-time digit challenges + tolerant matching of what Whisper heard.

The random challenge is Gate 1 and the backbone of the whole security model: a
fresh 6-digit code, single-use, 90 s expiry, kills every replay and every
pre-generated clone. Matching is homophone- and single-error-tolerant so a
genuine caller isn't failed for one misheard digit.
"""
from __future__ import annotations

import re
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


# Spoken-word -> digit across the languages a customer actually reads an OTP in.
# English homophones people say / Whisper emits ("oh" for zero, "for"/"to"/"ate"
# mishears), PLUS Hindi in Devanagari and its common romanizations -- a rural /
# non-English caller reading digits aloud must not be failed by an English-only
# gate (the core reason this app deploys in Indian villages at all). Mirrors the
# shield's app/routes/challenge.py so both OTP paths speak the same languages.
_W2D = {
    # English + homophones
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
    # Hindi -- Devanagari words
    "शून्य": "0", "सुन्य": "0", "एक": "1", "दो": "2", "तीन": "3", "चार": "4",
    "पाँच": "5", "पांच": "5", "छह": "6", "छे": "6", "सात": "7", "आठ": "8", "नौ": "9",
    # Hindi -- common romanizations (Whisper often romanizes Hindi speech)
    "shunya": "0", "sunya": "0", "ek": "1", "do": "2", "teen": "3", "char": "4",
    "chaar": "4", "paanch": "5", "panch": "5", "chhe": "6", "che": "6", "chah": "6",
    "saat": "7", "aath": "8", "nau": "9",
}
# Devanagari numerals ०-९ -> ASCII, in case Whisper returns digits in that script.
_DEVANAGARI_NUM = {c: str(i) for i, c in enumerate("०१२३४५६७८९")}

# Tokenizer: ASCII digit | Devanagari numeral (U+0966-096F) | Latin word |
# Devanagari word run (letters + combining matras, EXCLUDING the numeral block).
# We can't split on isalnum(): Devanagari vowel signs (matras, e.g. ी in तीन) are
# combining marks that isalnum() drops, which would shatter तीन into pieces.
_DIGIT_TOKEN = re.compile(r"[0-9]|[०-९]|[a-z]+|[ऀ-॥॰-ॿ]+")


def digits_from(text: str) -> str:
    """Extract a digit string from free ASR text across English + Hindi: keep
    literal digits, map Devanagari numerals (०-९), and map spelled-out number
    words (English homophones + Devanagari + romanized Hindi)."""
    out: list[str] = []
    for tok in _DIGIT_TOKEN.findall(text.lower()):
        if tok in _DEVANAGARI_NUM:            # before isdigit(): '३'.isdigit() is True
            out.append(_DEVANAGARI_NUM[tok])
        elif tok.isascii() and tok.isdigit():
            out.append(tok)
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
