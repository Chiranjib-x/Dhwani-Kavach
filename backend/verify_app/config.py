"""All tunable knobs for the v2 verification pipeline — the ONLY place a
threshold literal may live (see MASTER-PLAN.md §14 rule 3). Every value has a
`KV_*` env override so deployment/calibration never edits code.

Phase 7 rewrites the CM_* and ASV_* defaults from measurements on the team's own
recordings. Until then these are conservative starting points, not truth.
"""
from __future__ import annotations

import os


def _f(name: str, default: float) -> float:
    return float(os.environ.get(name, default))


def _i(name: str, default: int) -> int:
    return int(os.environ.get(name, default))


# --- Gate 0: quality / duration ------------------------------------------- #
DUR_MIN_S = _f("KV_DUR_MIN", 2.0)          # shorter than this: not enough to judge
DUR_MAX_S = _f("KV_DUR_MAX", 20.0)         # longer than this: reject (probably not a digit read)
SPEECH_MIN_S = _f("KV_SPEECH_MIN", 1.5)    # min seconds of actual speech (VAD)

# --- Gate 1: content (digit challenge) ------------------------------------ #
CONTENT_MAX_EDITS = _i("KV_CONTENT_EDITS", 1)   # Levenshtein tolerance vs challenge
CHALLENGE_LEN = _i("KV_CHALLENGE_LEN", 6)
# Randomization toggle (TESTING). On (default) = a fresh random one-time code per
# session, the real security property. Off = always FIXED_CHALLENGE, so you can
# read the same digits every time while testing the other gates. Global default
# here; the UI / a /v2/session body can override per session (KV_RANDOMIZE=0 to
# flip the default). Turning this OFF removes replay protection — testing only.
RANDOMIZE = os.environ.get("KV_RANDOMIZE", "1") == "1"
FIXED_CHALLENGE = os.environ.get("KV_FIXED_CHALLENGE", "123456")
# Plosive word randomization (testing). Same as challenge: KV_RANDOMIZE_PRIME=0 locks
# to FIXED_PRIME for repeatable testing of other gates without random word variability.
RANDOMIZE_PRIME = os.environ.get("KV_RANDOMIZE_PRIME", "1") == "1"
FIXED_PRIME = os.environ.get("KV_FIXED_PRIME", "papa")

# Gate execution order after quality (which is always first). Must be a
# permutation of exactly these three names. Current default = voice-match first
# (testing, per request). SECURE/production order is "content,liveness,speaker"
# (cheap phrase check first, so a wrong-code attempt never reaches the models) —
# set KV_GATE_ORDER=content,liveness,speaker to restore it.
_GATE_NAMES = {"content", "liveness", "speaker"}
_TEST_ORDER = ["speaker", "content", "liveness"]
GATE_ORDER = [g.strip() for g in os.environ.get("KV_GATE_ORDER", ",".join(_TEST_ORDER)).split(",")]
if set(GATE_ORDER) != _GATE_NAMES or len(GATE_ORDER) != 3:   # malformed -> test default
    GATE_ORDER = _TEST_ORDER

# --- Gate 2: liveness / anti-spoof (SOFT gate — see MASTER-PLAN §4 warning) - #
# bonafide_p = 1 - spoof_p from the CM. The existing CMs over-flag genuine
# out-of-domain speech, so this gate NEVER hard-rejects except at near-certainty.
KV_CM = os.environ.get("KV_CM", "cotrain")        # 'cotrain' | 'sls' | 'aasist' — A/B in Phase 7
CM_BONAFIDE_OK = _f("KV_CM_OK", 0.35)             # >= this: liveness passes cleanly
CM_BONAFIDE_REJECT = _f("KV_CM_REJECT", 0.03)     # < this (spoof_p > 0.97): hard REJECT.
#                                                   Calibrated so ZERO genuine team clip lands here.
#                                                   Between REJECT and OK -> STEP_UP, never silent reject.
CM_MAX_SECONDS = _f("KV_CM_MAX_SEC", 8.0)         # truncate before the CM (CPU win; see memory)

# Pop-noise / near-field liveness (physical replay defense — verify_app/popnoise.py).
# REPORT-ONLY until calibrated on real live-vs-replay captures (scripts/calibrate_popnoise.py):
# with KV_POP=0 the score is measured and shown but never rejects. Turn on with KV_POP=1
# AFTER calibration sets KV_POP_MIN, or it may reject genuine near-field users.
POP_ENFORCE = os.environ.get("KV_POP", "0") == "1"
POP_MIN = _f("KV_POP_MIN", 0.35)                  # min pop_score to be "live" when enforced
# Plosive "prime" words spoken with the digits to elicit strong pops (p/b/t/k/d/g onsets).
PLOSIVE_PRIMES = os.environ.get(
    "KV_PRIMES", "papa,bravo,tango,kilo,delta,golf,peter,tiger,panda,bucket").split(",")

# --- Gate 3: speaker (ECAPA cosine vs enrollment) ------------------------- #
ASV_ACCEPT = _f("KV_ASV_ACCEPT", 0.40)            # >= this: accept
ASV_REJECT = _f("KV_ASV_REJECT", 0.25)            # <= this: reject; between -> retry/step-up

# --- Enrollment ----------------------------------------------------------- #
ENROLL_SLOTS = _i("KV_ENROLL_SLOTS", 3)
ENROLL_CONSISTENCY_MIN = _f("KV_ENROLL_MIN", 0.45)   # min pairwise cosine across enroll clips
ENROLL_PROMPTS = [
    "My voice is my password and it keeps my account safe every single day.",
    "I bank securely from my phone whether I am at home or travelling far away.",
    "Seven three nine two five one eight zero four six.",  # digits: same phonetic ground as verify
]

# --- Sessions / lockout / abuse ------------------------------------------- #
MAX_ATTEMPTS = _i("KV_MAX_ATTEMPTS", 3)           # per verify session
SESSION_TTL_S = _f("KV_SESSION_TTL", 90.0)        # challenge validity window
LOCKOUT_FAILS = _i("KV_LOCKOUT_FAILS", 5)         # failed verify sessions before lockout
LOCKOUT_MIN = _f("KV_LOCKOUT_MIN", 15.0)          # lockout duration, minutes
MAX_UPLOAD_BYTES = _i("KV_MAX_UPLOAD", 8_000_000) # reject bigger uploads before decode

# --- Ops ------------------------------------------------------------------ #
ADMIN_KEY = os.environ.get("KV_ADMIN_KEY", "dev-admin-key")   # MUST be set from env in deploy
DB_PATH = os.environ.get(
    "KAVACH_DB", os.path.join(os.path.dirname(__file__), "kavach.db"))
# Capture uploaded clips to disk for offline red-team analysis (Tier-1 tuning).
# Debug/testing only — never persist customer audio in production.
KEEP_AUDIO = os.environ.get("KEEP_AUDIO", "0") == "1"
CAPTURE_DIR = os.environ.get("KV_CAPTURE_DIR", os.path.join(os.path.dirname(__file__), "captured"))
