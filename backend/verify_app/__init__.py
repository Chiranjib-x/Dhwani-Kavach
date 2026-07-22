"""Dhwani-Kavach v2 — spoofing-aware speaker verification (SASV).

Enroll a customer's voice once, then verify identity via a random one-time
digit challenge run through a 4-gate cascade (quality -> content -> liveness
-> speaker). See MASTER-PLAN.md at the repo root for the full design.

This package imports the existing `ml/` modules (audio_utils, quality, vad,
aasist_model/detector_v2) rather than reimplementing them.
"""
import os

# torch and ctranslate2 (faster-whisper) each bundle their own OpenMP runtime;
# on Windows the second to load aborts with "libiomp5md.dll already initialized".
# Set before ctranslate2 loads (asr.load() is always called after this package
# is imported) so both coexist. Safe for our single-threaded CPU inference.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
