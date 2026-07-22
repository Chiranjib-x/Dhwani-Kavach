import { createFileRoute } from "@tanstack/react-router"
import { useCallback, useState } from "react"

// Language Reach — how the shield covers India's many languages & tribal dialects.
// Two honest layers: (1) deepfake detection is ACOUSTIC and language-agnostic — it
// works in every language/dialect with zero language support; (2) the coercion
// (APP-fraud) layer needs transcription, covered by Whisper auto-detect for major
// languages and by a Bhashini / AI4Bharat adapter for the 22 scheduled languages
// and low-resource tribal dialects Whisper struggles with.
//
// We do NOT print fabricated scam translations — the verified Hindi warning is
// shown/spoken; other languages are shown by endonym with an honest coverage tag.

export const Route = createFileRoute("/languages")({ component: LanguageReach })

const C = { cyan: "#5EEAD4", ok: "#22C55E", warn: "#F59E0B", threat: "#FF4D6D", info: "#38BDF8", violet: "#A78BFA", text: "#F1F5F9", muted: "#64748B", surface: "#0F1117", bg: "#08090C", faint: "rgba(255,255,255,0.08)" }

type Cov = "native" | "bhashini"
type Lang = { name: string; endo: string; cov: Cov; bcp?: string }

// cov = how the COERCION layer transcribes it. Deepfake detection covers all.
const LANGS: Lang[] = [
  { name: "Hindi", endo: "हिन्दी", cov: "native", bcp: "hi-IN" },
  { name: "Bengali", endo: "বাংলা", cov: "native", bcp: "bn-IN" },
  { name: "Marathi", endo: "मराठी", cov: "native", bcp: "mr-IN" },
  { name: "Telugu", endo: "తెలుగు", cov: "native", bcp: "te-IN" },
  { name: "Tamil", endo: "தமிழ்", cov: "native", bcp: "ta-IN" },
  { name: "Gujarati", endo: "ગુજરાતી", cov: "native", bcp: "gu-IN" },
  { name: "Kannada", endo: "ಕನ್ನಡ", cov: "native", bcp: "kn-IN" },
  { name: "Punjabi", endo: "ਪੰਜਾਬੀ", cov: "native", bcp: "pa-IN" },
  { name: "Odia", endo: "ଓଡ଼ିଆ", cov: "bhashini" },
  { name: "Assamese", endo: "অসমীয়া", cov: "bhashini" },
  { name: "Santali", endo: "ᱥᱟᱱᱛᱟᱲᱤ", cov: "bhashini" },
  { name: "Bodo", endo: "बड़ो", cov: "bhashini" },
  { name: "Gondi", endo: "गोंडी", cov: "bhashini" },
  { name: "Maithili", endo: "मैथिली", cov: "bhashini" },
]

const WARN_HI = "सावधान! यह धोखा है। अपना OTP किसी को न बताएं।"

function LanguageReach() {
  const [spoke, setSpoke] = useState(false)

  const speakHindi = useCallback(() => {
    if (!("speechSynthesis" in window)) { setSpoke(true); return }
    const synth = window.speechSynthesis
    synth.cancel()
    const u = new SpeechSynthesisUtterance(WARN_HI)
    u.lang = "hi-IN"
    const hi = synth.getVoices().find((v) => v.lang?.toLowerCase().startsWith("hi"))
    if (hi) u.voice = hi
    u.rate = 0.9
    synth.speak(u)
    setSpoke(true)
  }, [])

  return (
    <div className="min-h-screen px-6 py-10" style={{ backgroundColor: C.bg, color: C.text }}>
      <div className="max-w-5xl mx-auto">
        <div className="font-mono text-[12px] tracking-[0.3em]" style={{ color: C.cyan }}>DHWANI-KAVACH · भाषा · LANGUAGE REACH</div>
        <h1 className="mt-2 text-2xl md:text-3xl font-semibold">One shield, every language a customer speaks</h1>
        <p className="mt-2 text-[14px] max-w-3xl" style={{ color: C.muted, lineHeight: 1.6 }}>
          India isn't one language. Protection can't be either. Two honest layers cover it.
        </p>

        {/* the two layers */}
        <div className="mt-6 grid gap-5 md:grid-cols-2">
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.ok}` }}>
            <div className="flex items-baseline justify-between">
              <h3 className="text-[15px] font-semibold" style={{ color: C.ok }}>1 · Deepfake detection</h3>
              <span className="font-mono text-[12px]" style={{ color: C.ok }}>ALL languages</span>
            </div>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>
              It's <b style={{ color: C.text }}>acoustic</b> — it scores the voice signal, not the words. A cloned voice in Santali
              flags exactly like one in English. <b style={{ color: C.text }}>Zero language support needed</b> — this layer already covers every
              language and tribal dialect.
            </p>
          </div>
          <div className="rounded-2xl p-5" style={{ backgroundColor: C.surface, border: `1px solid ${C.warn}` }}>
            <div className="flex items-baseline justify-between">
              <h3 className="text-[15px] font-semibold" style={{ color: C.warn }}>2 · Coercion (APP-fraud)</h3>
              <span className="font-mono text-[12px]" style={{ color: C.warn }}>needs transcription</span>
            </div>
            <p className="mt-2 text-[13px]" style={{ color: C.muted, lineHeight: 1.6 }}>
              Reading the <i>conversation</i> needs speech-to-text. <b style={{ color: C.text }}>Whisper auto-detects</b> major Indian languages;
              a <b style={{ color: C.text }}>Bhashini / AI4Bharat adapter</b> extends it to the 22 scheduled languages and low-resource tribal
              dialects — built on national language infrastructure.
            </p>
          </div>
        </div>

        {/* the vernacular warning, spoken */}
        <div className="mt-6 rounded-2xl p-5 flex flex-wrap items-center gap-4" style={{ backgroundColor: C.surface, border: `1px solid ${C.faint}` }}>
          <div>
            <div className="font-mono text-[10px] tracking-[0.2em] mb-1" style={{ color: C.muted }}>VERNACULAR WARNING · spoken to the customer</div>
            <div className="text-[18px] font-semibold" style={{ color: C.text }}>{WARN_HI}</div>
            <div className="text-[12px] italic mt-1" style={{ color: C.muted }}>"Warning! This is a scam. Don't share your OTP with anyone."</div>
          </div>
          <button onClick={speakHindi} className="ml-auto rounded-full px-5 py-2.5 text-[13px] font-medium" style={{ border: `1px solid ${C.cyan}`, color: C.cyan }}>
            🔊 सुनें · hear it
          </button>
          {spoke && !("speechSynthesis" in window) && <div className="w-full font-mono text-[11px]" style={{ color: C.warn }}>No TTS on this device — on a real IVR it's spoken by a Hindi/regional voice.</div>}
        </div>

        {/* coverage grid */}
        <div className="mt-6">
          <div className="font-mono text-[11px] tracking-[0.2em] mb-3" style={{ color: C.muted }}>
            COERCION-LAYER LANGUAGE COVERAGE · <span style={{ color: C.ok }}>■</span> Whisper-native · <span style={{ color: C.warn }}>■</span> via Bhashini
          </div>
          <div className="grid gap-2.5" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(150px, 1fr))" }}>
            {LANGS.map((l) => (
              <div key={l.name} className="rounded-xl px-4 py-3" style={{ backgroundColor: C.surface, border: `1px solid ${l.cov === "native" ? "rgba(34,197,94,0.3)" : "rgba(245,158,11,0.3)"}` }}>
                <div className="text-[18px]" style={{ color: C.text }}>{l.endo}</div>
                <div className="flex items-center justify-between mt-1">
                  <span className="text-[11px]" style={{ color: C.muted }}>{l.name}</span>
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: l.cov === "native" ? C.ok : C.warn }} />
                </div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-[12px]" style={{ color: C.muted }}>
            Backend is already language-swappable: <span className="font-mono">KV_ASR_LANG</span> pins a language,
            <span className="font-mono"> KV_WHISPER_SIZE</span> raises accuracy, and the STT/TTS calls drop into Bhashini without touching the detectors.
          </p>
        </div>

        <div className="mt-6 text-center">
          <a href="/" className="font-mono text-[11px] underline-offset-4 hover:underline" style={{ color: C.muted }}>← back to dashboard</a>
        </div>
      </div>
    </div>
  )
}
