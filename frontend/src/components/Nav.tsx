export default function Nav() {
  return (
    <nav
      className="fixed top-0 inset-x-0 z-50 border-b"
      style={{
        backgroundColor: "rgba(8,9,12,0.8)",
        backdropFilter: "blur(12px)",
        borderColor: "rgba(255,255,255,0.07)",
      }}
    >
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <a href="#top" className="flex items-center gap-2 text-[15px] font-semibold tracking-tight">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#5EEAD4" strokeWidth="1.8">
            <path d="M12 2 4 5v6c0 5 3.5 9.5 8 11 4.5-1.5 8-6 8-11V5l-8-3Z" />
          </svg>
          <span className="text-[#F1F5F9]">Dhwani-Kavach</span>
        </a>
        <div className="hidden md:flex items-center gap-7 text-[13px] text-[#64748B]">
          <a href="#threat" className="hover:text-[#F1F5F9] transition-colors">Threat</a>
          <a href="#defense" className="hover:text-[#F1F5F9] transition-colors">Defense</a>
          <a href="#demos" className="hover:text-[#F1F5F9] transition-colors">Demos</a>
          <a href="/range" style={{ color: "#5EEAD4" }} className="transition-colors">Attack Range</a>
          <a href="/voice-trust" style={{ color: "#38BDF8" }} className="transition-colors">Bank Security</a>
          <a href="/rural" style={{ color: "#F59E0B" }} className="transition-colors">ग्रामीण Rural</a>
          <a href="/voiceprint" className="hover:text-[#F1F5F9] transition-colors">Voiceprint</a>
        </div>
        <a
          href="#demo"
          className="text-[12px] font-medium px-3.5 py-1.5 rounded-full"
          style={{ backgroundColor: "#5EEAD4", color: "#08090C" }}
        >
          Live demo
        </a>
      </div>
    </nav>
  );
}
