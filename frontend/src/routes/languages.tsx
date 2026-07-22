import { createFileRoute } from "@tanstack/react-router"
import { useCallback, useEffect, useRef, useState } from "react"

// Language Reach — how the shield covers India's many languages & tribal dialects,
// and (new) PLAY the vernacular scam warning in each one. Two honest layers:
// (1) deepfake detection is ACOUSTIC and language-agnostic; (2) the coercion layer
// needs transcription — Whisper for major languages, a Bhashini / AI4Bharat
// adapter for the 22 scheduled languages + low-resource tribal dialects.
//
// Honesty: the translated warnings are ILLUSTRATIVE (production uses professional
// Bhashini localization), and playback uses the voices INSTALLED ON THIS DEVICE —
// languages without a local voice are shown as "Bhashini TTS in production".
// Translations live in one array (LANGS) so a native-speaker teammate can refine.

export const Route = createFileRoute("/languages")({ component: LanguageReach })

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", violet: "#A78BFA", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", bg: "#08090C", faint: "rgba(255,255,255,0.08)" }

type Lang = { name: string; endo: string; bcp?: string; warn?: string; audio?: string }

// warn = illustrative translation of "Warning! This is fraud. Don't tell anyone
// your OTP." Langs with `audio` play a pre-rendered neural-TTS clip (works on ANY
// device — see tools/prep_warning_audio.py); Punjabi has a translation but no
// edge-tts voice, so it falls back to a device voice if present; the rest are
// Bhashini-covered (no clip / no common voice) and shown as coverage only.
const LANGS: Lang[] = [
  { name: "Hindi", endo: "हिन्दी", bcp: "hi-IN", audio: "/warnings/hi.mp3", warn: "सावधान! यह धोखा है। किसी को अपना OTP न बताएं।" },
  { name: "Bengali", endo: "বাংলা", bcp: "bn-IN", audio: "/warnings/bn.mp3", warn: "সাবধান! এটি একটি প্রতারণা। কাউকে আপনার OTP জানাবেন না।" },
  { name: "Marathi", endo: "मराठी", bcp: "mr-IN", audio: "/warnings/mr.mp3", warn: "सावधान! ही फसवणूक आहे. कोणालाही तुमचा OTP सांगू नका." },
  { name: "Gujarati", endo: "ગુજરાતી", bcp: "gu-IN", audio: "/warnings/gu.mp3", warn: "સાવધાન! આ છેતરપિંડી છે. કોઈને તમારો OTP ન આપો." },
  { name: "Tamil", endo: "தமிழ்", bcp: "ta-IN", audio: "/warnings/ta.mp3", warn: "எச்சரிக்கை! இது ஒரு மோசடி. உங்கள் OTP-ஐ யாரிடமும் சொல்லாதீர்கள்." },
  { name: "Telugu", endo: "తెలుగు", bcp: "te-IN", audio: "/warnings/te.mp3", warn: "జాగ్రత్త! ఇది మోసం. మీ OTP ఎవరికీ చెప్పకండి." },
  { name: "Kannada", endo: "ಕನ್ನಡ", bcp: "kn-IN", audio: "/warnings/kn.mp3", warn: "ಎಚ್ಚರ! ಇದು ವಂಚನೆ. ನಿಮ್ಮ OTP ಅನ್ನು ಯಾರಿಗೂ ಹೇಳಬೇಡಿ." },
  { name: "Malayalam", endo: "മലയാളം", bcp: "ml-IN", audio: "/warnings/ml.mp3", warn: "ജാഗ്രത! ഇതൊരു തട്ടിപ്പാണ്. നിങ്ങളുടെ OTP ആർക്കും പറയരുത്." },
  { name: "Punjabi", endo: "ਪੰਜਾਬੀ", bcp: "pa-IN", warn: "ਸਾਵਧਾਨ! ਇਹ ਧੋਖਾ ਹੈ। ਕਿਸੇ ਨੂੰ ਆਪਣਾ OTP ਨਾ ਦੱਸੋ।" },
  // Bhashini-covered (no clip / no common on-device voice): coverage only
  { name: "Odia", endo: "ଓଡ଼ିଆ" },
  { name: "Assamese", endo: "অসমীয়া" },
  { name: "Santali", endo: "ᱥᱟᱱᱛᱟᱲᱤ" },
  { name: "Bodo", endo: "बड़ो" },
  { name: "Gondi", endo: "गोंडी" },
  { name: "Maithili", endo: "मैथिली" },
]

const ENGLISH_GLOSS = "\"Warning! This is fraud. Don't tell anyone your OTP.\""

function LanguageReach() {
  const [selected, setSelected] = useState<Lang>(LANGS[0])
  const [voicePrefixes, setVoicePrefixes] = useState<Set<string>>(new Set())
  const [note, setNote] = useState<string | null>(null)
  const audioRef = useRef<HTMLAudioElement | null>(null)

  // which language prefixes (e.g. "hi", "ta") have a voice installed on THIS device
  useEffect(() => {
    if (!("speechSynthesis" in window)) return
    const load = () => setVoicePrefixes(new Set(window.speechSynthesis.getVoices().map((v) => (v.lang || "").slice(0, 2).toLowerCase())))
    load()
    window.speechSynthesis.onvoiceschanged = load
  }, [])

  const hasVoice = useCallback((bcp?: string) => !!bcp && voicePrefixes.has(bcp.slice(0, 2).toLowerCase()), [voicePrefixes])
  // playable on THIS device = a pre-rendered clip exists, or the browser has a voice
  const playable = useCallback((l: Lang) => !!l.audio || (!!l.warn && hasVoice(l.bcp)), [hasVoice])

  const play = useCallback((l: Lang) => {
    setSelected(l); setNote(null)
    window.speechSynthesis?.cancel()
    if (audioRef.current) { audioRef.current.pause(); audioRef.current = null }
    // 1) pre-rendered neural-TTS clip — plays on any device
    if (l.audio) {
      const a = new Audio(l.audio)
      audioRef.current = a
      a.play().catch(() => setNote(`Couldn't play the ${l.name} clip — run tools/prep_warning_audio.py to (re)generate it.`))
      return
    }
    // 2) device voice fallback (e.g. Punjabi, if installed)
    if (l.warn && l.bcp && hasVoice(l.bcp)) {
      const u = new SpeechSynthesisUtterance(l.warn)
      u.lang = l.bcp
      const v = window.speechSynthesis.getVoices().find((vv) => (vv.lang || "").toLowerCase().startsWith(l.bcp!.slice(0, 2).toLowerCase()))
      if (v) u.voice = v
      u.rate = 0.9
      window.speechSynthesis.speak(u)
      return
    }
    // 3) no clip, no voice → Bhashini in production
    setNote(l.warn
      ? `No ${l.name} voice on this device — production speaks it via a Bhashini ${l.name} voice. (Text shown above.)`
      : `${l.name}: spoken via a Bhashini / regional TTS voice in production.`)
  }, [hasVoice])

  return (
    <div className="min-h-screen px-6 py-10" style={{ backgroundColor: C.bg, color: C.text }}>
      <div className="max-w-5xl mx-auto">
        <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · भाषा · LANGUAGE REACH</div>
        <h1 className="mt-2 text-2xl md:text-3xl font-semibold">Hear the warning in the customer's own language</h1>
        <p className="mt-2 text-[14px] max-w-3xl" style={{ color: C.muted, lineHeight: 1.6 }}>
          India isn't one language — protection can't be either. Tap a language to <b style={{ color: C.text }}>play the scam warning</b> in it
          (turn sound on) — 8 languages play a real neural-TTS clip on any device. Deepfake detection already covers every language; the
          spoken warning extends to tribal dialects via <b style={{ color: C.text }}>Bhashini / AI4Bharat</b>.
        </p>

        {/* now playing */}
        <div className="mt-6 rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${selected.warn ? C.warn : C.faint}` }}>
          <div className="flex flex-wrap items-center gap-4">
            <div className="min-w-0">
              <div className="font-mono text-[10px] tracking-[0.2em] mb-1" style={{ color: C.muted }}>SCAM WARNING · {selected.name} · {selected.endo}</div>
              <div className="text-[20px] font-semibold" style={{ color: C.text, lineHeight: 1.5 }}>{selected.warn ?? "— spoken via Bhashini TTS in production —"}</div>
              <div className="text-[12px] italic mt-1" style={{ color: C.muted }}>{ENGLISH_GLOSS}</div>
            </div>
            {(selected.audio || selected.warn) && (
              <button onClick={() => play(selected)} className="ml-auto rounded-full px-5 py-2.5 text-[13px] font-medium" style={{ border: `1px solid ${C.cyan}`, color: C.cyan }}>
                🔊 play
              </button>
            )}
          </div>
          {note && <div className="mt-3 font-mono text-[11px]" style={{ color: C.warn }}>{note}</div>}
        </div>

        {/* language grid */}
        <div className="mt-6">
          <div className="font-mono text-[11px] tracking-[0.2em] mb-3" style={{ color: C.muted }}>
            TAP TO PLAY · <span style={{ color: C.ok }}>■</span> plays here · <span style={{ color: C.warn }}>■</span> Bhashini (production)
          </div>
          <div className="grid gap-2.5" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(155px, 1fr))" }}>
            {LANGS.map((l) => {
              const canPlay = playable(l)
              const active = selected.name === l.name
              return (
                <button key={l.name} onClick={() => play(l)}
                  className="text-left rounded-xl px-4 py-3 transition-colors"
                  style={{ backgroundColor: active ? "rgba(94,234,212,0.06)" : C.surface, border: `1px solid ${active ? C.cyan : canPlay ? "rgba(34,197,94,0.3)" : "rgba(245,158,11,0.3)"}` }}>
                  <div className="flex items-center justify-between">
                    <div className="text-[18px]" style={{ color: C.text }}>{l.endo}</div>
                    {(l.audio || l.warn) && <span className="text-[13px]" style={{ color: active ? C.cyan : C.muted }}>🔊</span>}
                  </div>
                  <div className="flex items-center justify-between mt-1">
                    <span className="text-[11px]" style={{ color: C.muted }}>{l.name}</span>
                    <span className="w-2 h-2 rounded-full" style={{ backgroundColor: canPlay ? C.ok : C.warn }} />
                  </div>
                </button>
              )
            })}
          </div>
          <p className="mt-3 text-[12px]" style={{ color: C.muted }}>
            8 languages play a <b style={{ color: C.text }}>pre-rendered neural-TTS clip</b> (works on any device, offline); others use an installed
            voice or Bhashini on a real IVR. Translations are <b style={{ color: C.text }}>illustrative</b> (production uses Bhashini localization) and
            live in one array a native speaker can refine — re-run <span className="font-mono">tools/prep_warning_audio.py</span>.
          </p>
        </div>

        {/* the two layers */}
        <div className="mt-6 grid gap-5 md:grid-cols-2">
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.ok}` }}>
            <div className="flex items-baseline justify-between">
              <h3 className="text-[15px] font-semibold" style={{ color: C.ok }}>1 · Deepfake detection</h3>
              <span className="font-mono text-[12px]" style={{ color: C.ok }}>ALL languages</span>
            </div>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>
              It's <b style={{ color: C.text }}>acoustic</b> — it scores the voice signal, not the words. A cloned voice in Santali flags exactly
              like one in English. Zero language support needed.
            </p>
          </div>
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.warn}` }}>
            <div className="flex items-baseline justify-between">
              <h3 className="text-[15px] font-semibold" style={{ color: C.warn }}>2 · Coercion + warning</h3>
              <span className="font-mono text-[12px]" style={{ color: C.warn }}>Whisper + Bhashini</span>
            </div>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>
              Reading the conversation and speaking a warning need STT/TTS. <b style={{ color: C.text }}>Whisper</b> covers major languages;
              <b style={{ color: C.text }}> Bhashini / AI4Bharat</b> extends both to the 22 scheduled languages and tribal dialects.
              Backend is STT-swappable (<span className="font-mono">KV_ASR_LANG</span>).
            </p>
          </div>
        </div>

        <div className="mt-6 text-center">
          <a href="/" className="font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: C.muted }}>← back to dashboard</a>
        </div>
      </div>
    </div>
  )
}
