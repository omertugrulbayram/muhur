import { useEffect, useState } from "react";
import { EN, L, LANG, setLang } from "./i18n";

/* ============================================================
   Ortak parçalar: marka, rozetler, üst menü, yönlendirme
   ============================================================ */

export const BAND = {
  high:   { label: L("Yüksek güven", "High trust"),  cls: "text-trust-high", bg: "bg-trust-high", ring: "ring-trust-high/25" },
  medium: { label: L("Orta güven", "Medium trust"),  cls: "text-trust-med",  bg: "bg-trust-med",  ring: "ring-trust-med/25" },
  low:    { label: L("Düşük güven", "Low trust"),    cls: "text-trust-low",  bg: "bg-trust-low",  ring: "ring-trust-low/25" },
};

export const initials = (n) => n.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

export function useHash() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const f = () => { setHash(window.location.hash); window.scrollTo(0, 0); };
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);
  return hash;
}

/* MÜHÜRLÜ rozeti (kanıtlanmış gerçek insan) */
export function MuhurBadge({ size = 15, title = L("Mühürlü — kanıtlanmış gerçek insan", "Sealed — verified real person") }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" aria-label={title}
         className="inline-block shrink-0" style={{ verticalAlign: "-2px" }}>
      <title>{title}</title>
      <path d="M12 1.6l2.3 1.7 2.8-.3 1 2.7 2.5 1.3-.6 2.8 1.7 2.3-1.7 2.3.6 2.8-2.5 1.3-1 2.7-2.8-.3L12 22.4l-2.3-1.7-2.8.3-1-2.7-2.5-1.3.6-2.8L2.9 12l1.7-2.3-.6-2.8 2.5-1.3 1-2.7 2.8.3z"
            fill="var(--color-brand)" />
      <path d="M8.2 12.2l2.6 2.6 5-5.6" fill="none" stroke="#fff" strokeWidth="2"
            strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

/* Büyük mühür (doğrulama başarısı) */
export function SealStamp({ stampKey, label = L("NSOSYAL MÜHÜR • KANITLANMIŞ GERÇEK İNSAN • ", "SEAL • VERIFIED REAL PERSON • ") }) {
  const ring = label.repeat(EN ? 3 : 2);
  return (
    <svg viewBox="0 0 220 220" className="w-full h-full seal-stamped" key={stampKey}
         style={{ transformOrigin: "110px 110px" }}>
      <defs><path id="sc" d="M110,110 m-78,0 a78,78 0 1,1 156,0 a78,78 0 1,1 -156,0" /></defs>
      <circle cx="110" cy="110" r="86" fill="none" stroke="var(--color-brand)" strokeWidth="6" />
      <circle cx="110" cy="110" r="92" fill="none" stroke="var(--color-brand)" strokeWidth="2" opacity="0.5" />
      <circle cx="110" cy="110" r="64" fill="none" stroke="var(--color-brand)" strokeWidth="1.5" opacity="0.5" />
      <text fill="var(--color-brand)" fontSize="11" className="seal-ring-text">
        <textPath href="#sc">{ring}</textPath>
      </text>
      <path d="M84,112 l18,18 l34,-40" fill="none" stroke="var(--color-brand)"
            strokeWidth="9" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function Logo({ className = "", light = false }) {
  if (EN) {
    return (
      <span className={`inline-flex items-center gap-2 ${className}`}>
        <span className="grid place-items-center w-8 h-8 rounded-lg bg-brand text-white font-700 text-lg">S</span>
        <span className={`font-700 text-xl tracking-tight ${light ? "text-white" : ""}`}>SEAL</span>
        <span className={`text-[11px] font-700 tracking-widest px-1.5 py-0.5 rounded ring-1
          ${light ? "text-white/80 ring-white/30" : "text-brand ring-brand/30"}`}>TRUST LAYER</span>
      </span>
    );
  }
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <span className="grid place-items-center w-8 h-8 rounded-lg bg-brand text-white font-700 text-lg">N</span>
      <span className={`font-700 text-xl tracking-tight ${light ? "text-white" : ""}`}>NSosyal</span>
      <span className={`text-[11px] font-700 tracking-widest px-1.5 py-0.5 rounded ring-1
        ${light ? "text-white/80 ring-white/30" : "text-brand ring-brand/30"}`}>MÜHÜR</span>
    </span>
  );
}

export const DemoBadge = ({ children = "DEMO" }) => (
  <span className="text-[10px] font-700 tracking-wide px-2 py-0.5 rounded bg-brand/10 text-brand ring-1 ring-brand/20 whitespace-nowrap">
    {children}
  </span>
);

const NAV = [
  ["home", "#/", L("Nasıl çalışır", "How it works")],
  ["demo", "#/demo", L("Kullanıcı demosu", "User demo")],
  ["panel", "#/panel", L("Topluluk paneli", "Community panel")],
];

function LangSwitch() {
  return (
    <span className="inline-flex rounded-lg ring-1 ring-hair overflow-hidden text-[11px] font-700" role="group" aria-label="Language">
      {[["tr", "TR"], ["en", "EN"]].map(([k, l]) => (
        <button key={k} onClick={() => k !== LANG && setLang(k)}
          className={`px-2 py-1 ${k === LANG ? "bg-ink text-white" : "text-ink-soft hover:text-ink"}`}>{l}</button>
      ))}
    </span>
  );
}

export function TopNav({ active, right, wide = false }) {
  return (
    <header className="sticky top-0 z-40 bg-surface/95 backdrop-blur border-b border-hair">
      <div className={`${wide ? "max-w-7xl" : "max-w-6xl"} mx-auto px-4 h-14 flex items-center gap-3`}>
        <a href="#/" aria-label={L("Ana sayfa", "Home")}><Logo /></a>
        <nav className="hidden sm:flex items-center gap-1 text-sm ml-3">
          {NAV.map(([id, href, label]) => (
            <a key={id} href={href}
              className={`px-3 py-1.5 rounded-lg transition ${active === id ? "bg-ink text-white" : "text-ink-soft hover:text-ink hover:bg-surface-2"}`}>
              {label}
            </a>
          ))}
        </nav>
        <div className="ml-auto flex items-center gap-3 text-sm">
          {right}
          <DemoBadge>{L("SİMÜLASYON", "SIMULATION")}</DemoBadge>
          <LangSwitch />
        </div>
      </div>
      <nav className="sm:hidden flex border-t border-hair text-xs">
        {NAV.map(([id, href, label]) => (
          <a key={id} href={href} className={`flex-1 text-center py-2 ${active === id ? "font-700 text-ink" : "text-ink-soft"}`}>{label}</a>
        ))}
      </nav>
    </header>
  );
}

export function Footer() {
  return (
    <footer className="max-w-6xl mx-auto px-4 py-8 text-[11px] text-ink-soft font-mono leading-relaxed">
      {L(
        "MÜHÜR (SEAL) prototipi · kimlik doğrulama simülasyondur, e-Devlet entegrasyonu yoktur · hesaplar ve paylaşımlar sentetik demo kampüsünden gelir · güven puanları ve uyarılar canlı backend'den (Ed25519 imzalı token, açıklanabilir model)",
        "SEAL prototype · identity verification is simulated, there is no e-Devlet integration · accounts and posts come from a synthetic demo campus · trust scores and alerts come from the live backend (Ed25519-signed tokens, explainable model)",
      )}
    </footer>
  );
}
