"""Pre-generate the vernacular scam-warning audio for /languages.

Relying on the browser's INSTALLED voices is too fragile (most devices only have
English + maybe Hindi). Instead we render each warning once to an MP3 with
Microsoft neural TTS (edge-tts) and serve the file — so every language plays on
any device/browser, offline, no installed voice needed.

    pip install edge-tts        # needs internet at generation time only
    python tools/prep_warning_audio.py

Writes frontend/public/warnings/<code>.mp3. Translations are ILLUSTRATIVE (match
routes/languages.tsx; production uses professional Bhashini localization) — a
native speaker can edit the strings here and re-run. Punjabi/Odia/Assamese and
the tribal dialects have no edge-tts voice → they stay Bhashini-in-production.
"""
from __future__ import annotations

import asyncio
import os

import edge_tts

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "frontend", "public", "warnings")

# code: (neural voice, illustrative translation of
#        "Warning! This is fraud. Don't tell anyone your OTP.")
WARN: dict[str, tuple[str, str]] = {
    "hi": ("hi-IN-SwaraNeural", "सावधान! यह धोखा है। किसी को अपना OTP न बताएं।"),
    "bn": ("bn-IN-TanishaaNeural", "সাবধান! এটি একটি প্রতারণা। কাউকে আপনার OTP জানাবেন না।"),
    "mr": ("mr-IN-AarohiNeural", "सावधान! ही फसवणूक आहे. कोणालाही तुमचा OTP सांगू नका."),
    "gu": ("gu-IN-DhwaniNeural", "સાવધાન! આ છેતરપિંડી છે. કોઈને તમારો OTP ન આપો."),
    "ta": ("ta-IN-PallaviNeural", "எச்சரிக்கை! இது ஒரு மோசடி. உங்கள் OTP-ஐ யாரிடமும் சொல்லாதீர்கள்."),
    "te": ("te-IN-ShrutiNeural", "జాగ్రత్త! ఇది మోసం. మీ OTP ఎవరికీ చెప్పకండి."),
    "kn": ("kn-IN-SapnaNeural", "ಎಚ್ಚರ! ಇದು ವಂಚನೆ. ನಿಮ್ಮ OTP ಅನ್ನು ಯಾರಿಗೂ ಹೇಳಬೇಡಿ."),
    "ml": ("ml-IN-SobhanaNeural", "ജാഗ്രത! ഇതൊരു തട്ടിപ്പാണ്. നിങ്ങളുടെ OTP ആർക്കും പറയരുത്."),
}


async def _gen() -> None:
    os.makedirs(OUT, exist_ok=True)
    for code, (voice, text) in WARN.items():
        path = os.path.join(OUT, f"{code}.mp3")
        await edge_tts.Communicate(text, voice, rate="-8%").save(path)
        print(f"wrote {code}.mp3  ({os.path.getsize(path)} bytes, {voice})")
    print(f"\ndone -> {OUT}")


if __name__ == "__main__":
    asyncio.run(_gen())
