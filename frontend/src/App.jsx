import { useEffect, useState } from "react";
import { api } from "./api";
import Panel from "./Panel";

/* ============================================================
   Ortak yardimcilar
   ============================================================ */
const BAND = {
  high:   { label: "Yüksek güven", cls: "text-trust-high", bg: "bg-trust-high", ring: "ring-trust-high/25" },
  medium: { label: "Orta güven",   cls: "text-trust-med",  bg: "bg-trust-med",  ring: "ring-trust-med/25" },
  low:    { label: "Düşük güven",   cls: "text-trust-low",  bg: "bg-trust-low",  ring: "ring-trust-low/25" },
};
const initials = (n) => n.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase();

/* MÜHÜRLÜ rozeti (dogrulanmis gercek insan) */
function MuhurBadge({ size = 15, title = "Mühürlü — kanıtlanmış gerçek insan" }) {
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

/* Buyuk muhur (giris basarisi / profil) */
function SealStamp({ stampKey }) {
  const ring = "NSOSYAL MÜHÜR • KANITLANMIŞ GERÇEK İNSAN • ".repeat(2);
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

/* NSosyal logo isareti */
function Logo({ className = "" }) {
  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <span className="grid place-items-center w-8 h-8 rounded-lg bg-brand text-white font-700 text-lg">N</span>
      <span className="font-700 text-xl tracking-tight">NSosyal</span>
    </span>
  );
}

const SimBadge = () => (
  <span className="text-[10px] font-700 tracking-wide px-2 py-0.5 rounded bg-brand/10 text-brand ring-1 ring-brand/20">
    SİMÜLASYON
  </span>
);

/* ============================================================
   1) GIRIS EKRANI (NSosyal)
   ============================================================ */
function LoginScreen({ onEdevlet }) {
  return (
    <div className="min-h-screen grid lg:grid-cols-2">
      <div className="hidden lg:flex flex-col justify-between p-12 bg-ink text-white">
        <Logo className="[&_span:last-child]:text-white" />
        <div>
          <h1 className="text-4xl font-700 leading-tight">
            Gerçek insanların,<br />manipülasyondan uzak alanı.
          </h1>
          <p className="mt-4 text-white/70 max-w-md">
            Reklamsız · Sansürsüz · Algoritmasız. MÜHÜR ile artık her hesabın
            arkasında <b className="text-white">kanıtlanmış gerçek bir insan</b> olduğunu görebilirsin.
          </p>
          <div className="mt-8 flex flex-wrap gap-2 text-xs">
            {["Kronolojik akış", "Kara kutu yok", "Mühürlü kimlik", "TC saklanmaz"].map((t) => (
              <span key={t} className="px-3 py-1 rounded-full bg-white/10 ring-1 ring-white/15">{t}</span>
            ))}
          </div>
        </div>
        <p className="text-xs text-white/40 font-mono">TEKNOFEST 2026 · NSosyal İnovasyon · demo</p>
      </div>

      <div className="flex items-center justify-center p-8">
        <div className="w-full max-w-sm">
          <div className="lg:hidden mb-8"><Logo /></div>
          <div className="flex items-center justify-between mb-1">
            <h2 className="text-2xl font-700">Giriş yap</h2>
            <SimBadge />
          </div>
          <p className="text-sm text-ink-soft mb-6">
            NSosyal'e girişte kimliğin bir kez doğrulanır ve <b>MÜHÜR'ün</b> verilir.
          </p>

          <button onClick={onEdevlet}
            className="w-full flex items-center justify-center gap-3 py-3.5 rounded-xl
                       bg-gov text-white font-600 hover:bg-gov-deep transition">
            <span className="grid place-items-center w-6 h-6 rounded bg-white/20 text-sm font-700">e</span>
            e-Devlet ile Giriş Yap
          </button>

          <div className="mt-4 flex items-start gap-2 text-xs text-ink-soft bg-surface-2 rounded-lg p-3">
            <span className="text-trust-high mt-0.5">✓</span>
            <span>
              TC kimlik numaran <b>hiçbir yere kaydedilmez</b> — yalnızca geri döndürülemez,
              tek yönlü bir takma kimliğe (benzersizlik nişanına) çevrilir.
            </span>
          </div>

          <p className="mt-6 text-[11px] text-ink-soft text-center">
            Bu bir yarışma demosudur. e-Devlet girişi <b>simülasyondur</b>, gerçek devlet
            sistemlerine bağlanmaz.
          </p>
        </div>
      </div>
    </div>
  );
}

/* ============================================================
   2) e-DEVLET (DEMO) GIRISI
   ============================================================ */
function EDevletModal({ onSuccess, onClose }) {
  const [tc, setTc] = useState("10000000146");
  const [pw, setPw] = useState("demo1234");
  const [busy, setBusy] = useState(false);
  const [ok, setOk] = useState(false);
  const [err, setErr] = useState("");
  const [stampKey, setStampKey] = useState(0);

  async function login() {
    setErr(""); setBusy(true);
    try {
      const r = await api.popVerify(tc || "10000000146", 2000);
      setOk(true); setStampKey((k) => k + 1);
      setTimeout(() => onSuccess({
        name: "Sen", handle: "sen",
        credential: r.credential, token: r.personhood_token,
        nishani: r.credential.claims.uniqueness_nishani,
      }), 1400);
    } catch (e) {
      setErr(String(e.message || e) + " — backend açık mı?"); setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-surface rounded-2xl overflow-hidden shadow-2xl ink-in">
        <div className="bg-gov text-white px-5 py-3 flex items-center justify-between">
          <span className="font-700">e-Devlet Kapısı</span>
          <span className="text-[10px] font-700 px-2 py-0.5 rounded bg-white/20">DEMO</span>
        </div>

        <div className="bg-trust-med/10 text-[12px] text-ink-soft px-5 py-2.5 border-b border-hair">
          ⚠ Bu ekran bir <b>simülasyondur</b>. Gerçek e-Devlet değildir; girdiğin hiçbir
          bilgi herhangi bir kuruma gönderilmez.
        </div>

        {ok ? (
          <div className="p-8 text-center">
            <div className="w-28 h-28 mx-auto"><SealStamp stampKey={stampKey} /></div>
            <p className="mt-4 font-600">Kimliğin doğrulandı, mührün verildi.</p>
            <p className="text-sm text-ink-soft">NSosyal'e yönlendiriliyorsun…</p>
          </div>
        ) : (
          <div className="p-5">
            <label className="block text-sm font-600 mb-1">T.C. Kimlik No</label>
            <input value={tc} onChange={(e) => setTc(e.target.value)}
              className="w-full font-mono text-sm px-3 py-2.5 rounded-lg bg-surface-2 ring-1 ring-hair focus:ring-gov outline-none" />
            <label className="block text-sm font-600 mb-1 mt-4">e-Devlet Şifresi</label>
            <input value={pw} onChange={(e) => setPw(e.target.value)} type="password"
              className="w-full font-mono text-sm px-3 py-2.5 rounded-lg bg-surface-2 ring-1 ring-hair focus:ring-gov outline-none" />

            {err && <p className="mt-3 text-sm text-brand">{err}</p>}

            <button onClick={login} disabled={busy}
              className="mt-5 w-full py-3 rounded-xl bg-gov text-white font-600 hover:bg-gov-deep disabled:opacity-60">
              {busy ? "Doğrulanıyor…" : "Giriş Yap"}
            </button>
            <button onClick={onClose}
              className="mt-2 w-full py-2 text-sm text-ink-soft hover:text-ink">Vazgeç</button>
          </div>
        )}
      </div>
    </div>
  );
}

/* ============================================================
   3) NSosyal AKISI (mikroblog + MÜHÜR katmani)
   Hesaplar ve paylaşımlar sentetik demo kampüsünden gelir (/demo/personas).
   Risk değerleri ELLE DEĞİL, koordinasyon modelinin sunucuda yazdığı kayıttan gelir.
   ============================================================ */
const DEMO_TOKENS_KEY = "muhur-demo-attendance-v2";

/* Mühürlü demo hesap: PoP alır, normal öğrenciler bir etkinliğe check-in yapar
   (aynı kişi aynı etkinliğe iki kez katılamadığı için kanıt tarayıcıda saklanır). */
async function sealPersona(p) {
  const r = await api.popVerify(p.national_id, 2003);
  const saved = JSON.parse(localStorage.getItem(DEMO_TOKENS_KEY) || "{}");
  const attendance = [];
  if (!p.alert_id) {
    const key = `${p.national_id}:teknofest-2026`;
    if (!saved[key]) {
      try {
        const q = await api.poaChallenge("teknofest-2026");
        const c = await api.poaCheckin(q.checkin_token, r.personhood_token);
        saved[key] = c.attendance_token;
      } catch (e) {
        if (e.status !== 409) throw e;   // zaten katılmış ama kanıt bu tarayıcıda yok
      }
    }
    if (saved[key]) attendance.push(saved[key]);
    localStorage.setItem(DEMO_TOKENS_KEY, JSON.stringify(saved));
  }
  return { token: r.personhood_token, attendance };
}

const UNSEALED_RESULT = {
  trust_score: 0, band: "low",
  axes: { identity: 0, authenticity: 1 },
  explanation: ["Kanıtlanmış insan (PoP) token'ı yok — hesap mühürsüz."],
};

function NSosyalApp({ user }) {
  const [authors, setAuthors] = useState(null);
  const [posts, setPosts] = useState([]);
  const [filter, setFilter] = useState("all");
  const [draft, setDraft] = useState("");
  const [userResult, setUserResult] = useState(null);
  const [loadErr, setLoadErr] = useState("");

  useEffect(() => {
    let alive = true;
    (async () => {
      try {
        const ur = await api.trustScore(user.token, []);
        if (alive) setUserResult(ur);
      } catch {}
      try {
        const { personas } = await api.demoPersonas();
        const map = {};
        for (const p of personas) {
          let result = UNSEALED_RESULT;
          if (p.sealed) {
            const s = await sealPersona(p);
            result = await api.trustScore(s.token, s.attendance);
          }
          map[p.handle] = { sealed: p.sealed, result, alertLevel: p.alert_level, alertId: p.alert_id };
        }
        if (alive) { setAuthors(map); setPosts(personas); }
      } catch (e) {
        if (alive) setLoadErr(String(e.message || e));
      }
    })();
    return () => { alive = false; };
  }, [user]);

  function share() {
    if (!draft.trim()) return;
    setPosts([{ name: user.name, handle: user.handle, sealed: true, text: draft.trim() }, ...posts]);
    setDraft("");
  }

  const meta = (h) => (h === user.handle ? { sealed: true, result: userResult } : authors?.[h]);

  const visible = posts.filter((p) => {
    const m = meta(p.handle); if (!m?.result) return true;
    if (filter === "sealed") return m.sealed;
    if (filter === "high") return m.result.band !== "low";
    return true;
  });

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-30 bg-surface/90 backdrop-blur border-b border-hair">
        <div className="max-w-2xl mx-auto px-4 h-14 flex items-center justify-between">
          <Logo />
          <div className="flex items-center gap-3">
            <SimBadge />
            <div className="flex items-center gap-1.5 text-sm font-600">@{user.handle} <MuhurBadge /></div>
          </div>
        </div>
      </header>

      <main className="max-w-2xl mx-auto px-4 py-4">
        {/* olustur */}
        <div className="bg-surface rounded-2xl ring-1 ring-hair p-4 mb-4">
          <div className="flex gap-3">
            <div className="w-10 h-10 rounded-full bg-brand/10 text-brand grid place-items-center font-700 shrink-0">
              {initials(user.name)}
            </div>
            <div className="flex-1">
              <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={2}
                placeholder="Neler oluyor?"
                className="w-full resize-none bg-transparent outline-none text-[15px] placeholder:text-ink-soft" />
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-ink-soft flex items-center gap-1">
                  <MuhurBadge size={13} /> mühürlü hesabınla paylaşıyorsun
                </span>
                <button onClick={share} disabled={!draft.trim()}
                  className="px-4 py-1.5 rounded-full bg-brand text-white text-sm font-600 hover:bg-brand-deep disabled:opacity-50">
                  Paylaş
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* topluluk paneli bağlantısı */}
        <a href="#/panel" className="block bg-ink text-white rounded-2xl p-4 mb-4 hover:bg-ink/90 transition">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-sm font-700">Topluluk yöneticisi paneli</div>
              <div className="text-xs text-white/60">
                Bu akıştaki hesapların hangi koordinasyon uyarılarına düştüğünü, nedenlerini ve olası
                masum açıklamalarını gör. Son kararı yönetici verir.
              </div>
            </div>
            <span className="shrink-0 px-3 py-2 rounded-lg text-sm font-600 bg-white/15">Panele git →</span>
          </div>
        </a>

        {loadErr && (
          <p className="mb-3 text-sm text-brand">Akış yüklenemedi: {loadErr} — backend açık mı?</p>
        )}

        {/* filtre (kullanici kontrollu — algoritma degil) */}
        <div className="flex items-center gap-2 mb-3 text-sm flex-wrap">
          <span className="text-ink-soft">Göster:</span>
          {[["all", "Tümü"], ["sealed", "Yalnızca mühürlü"], ["high", "Yüksek güven"]].map(([id, l]) => (
            <button key={id} onClick={() => setFilter(id)}
              className={`px-3 py-1 rounded-full ring-1 transition
                ${filter === id ? "bg-ink text-white ring-ink" : "ring-hair text-ink-soft hover:text-ink"}`}>
              {l}
            </button>
          ))}
        </div>

        {!authors ? (
          <p className="text-sm text-ink-soft py-8 text-center">Akış yükleniyor…</p>
        ) : (
          <div className="space-y-3">
            {visible.map((p, i) => (
              <PostCard key={p.handle + i} post={p} meta={meta(p.handle)} />
            ))}
            {visible.length === 0 && (
              <p className="text-sm text-ink-soft py-8 text-center">
                Bu filtreyle gösterilecek gönderi yok. Filtreyi sen belirledin — istediğinde "Tümü"ne dönebilirsin.
              </p>
            )}
          </div>
        )}
      </main>

      <footer className="max-w-2xl mx-auto px-4 py-6 text-[11px] text-ink-soft font-mono border-t border-hair">
        mock issuer · e-Devlet entegrasyonu YOK · güven skorları canlı backend'den (Ed25519 imzalı token) · hesaplar ve paylaşımlar sentetik DEMO kampüsünden · risk değerleri koordinasyon modelinden
      </footer>
    </div>
  );
}

function PostCard({ post, meta }) {
  const [open, setOpen] = useState(false);
  const [liked, setLiked] = useState(false);
  const r = meta?.result;
  const b = r ? BAND[r.band] : null;
  const flagged = meta?.alertLevel === "yüksek";

  return (
    <article className={`bg-surface rounded-2xl ring-1 p-4 ${flagged ? "ring-brand/40" : "ring-hair"}`}>
      <div className="flex gap-3">
        <div className="w-10 h-10 rounded-full bg-surface-2 grid place-items-center font-700 text-ink-soft shrink-0">
          {initials(post.name)}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="font-700">{post.name}</span>
            {post.sealed && <MuhurBadge />}
            <span className="text-ink-soft text-sm">@{post.handle}</span>
            {b && (
              <span className={`ml-auto inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5
                                text-[11px] font-600 ring-1 ${b.cls} ${b.ring}`}>
                <span className={`w-1.5 h-1.5 rounded-full ${b.bg}`} />{r.trust_score.toFixed(2)}
              </span>
            )}
          </div>

          <p className="mt-1.5 text-[15px] leading-snug">{post.text}</p>

          {flagged && (
            <div className="mt-2 text-xs text-brand bg-brand/5 ring-1 ring-brand/20 rounded-lg px-3 py-1.5">
              ⚠ Bu hesap, model tarafından yüksek riskli bulunan bir koordinasyon kümesinde.
              Bu bir yargı değil; topluluk yöneticisinin incelemesini bekliyor.{" "}
              <a href={`#/panel/${meta.alertId}`} className="underline font-600">Uyarıyı gör</a>
            </div>
          )}

          <div className="mt-3 flex items-center gap-6 text-ink-soft text-sm">
            <button className="hover:text-gov flex items-center gap-1.5">💬 <span>12</span></button>
            <button className="hover:text-trust-high flex items-center gap-1.5">🔁 <span>4</span></button>
            <button onClick={() => setLiked((v) => !v)}
              className={`flex items-center gap-1.5 ${liked ? "text-rocket" : "hover:text-rocket"}`}>
              🚀 <span>{liked ? 89 : 88}</span>
            </button>
            <button className="hover:text-ink flex items-center gap-1.5">📊 <span>2,4B</span></button>
            {r && (
              <button onClick={() => setOpen((o) => !o)}
                className="ml-auto text-xs font-600 hover:text-ink underline underline-offset-2">
                {open ? "Gizle" : "Neden bunu görüyorum?"}
              </button>
            )}
          </div>

          {open && r && (
            <div className="mt-2 ink-in rounded-xl bg-surface-2 p-3">
              <div className="flex items-center gap-2 mb-2 text-xs font-600 flex-wrap">
                <span className={b.cls}>{b.label} · {r.trust_score.toFixed(2)}</span>
                <span className="text-ink-soft">
                  (kimlik {Math.round(r.axes.identity * 100)}% × otantiklik {Math.round(r.axes.authenticity * 100)}%)
                </span>
              </div>
              <ul className="space-y-1.5">
                {r.explanation.map((line, i) => {
                  const warn = /Koordineli\/sahte|sahte|yok\.|sayılmadı/i.test(line);
                  return (
                    <li key={i} className="flex gap-2 text-sm text-ink-soft leading-snug">
                      <span className={warn ? "text-brand" : "text-trust-high"}>{warn ? "▲" : "•"}</span>
                      {line}
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </div>
      </div>
    </article>
  );
}

/* ============================================================
   Kok — ekran yonlendirme
   ============================================================ */
export default function App() {
  const [screen, setScreen] = useState("login");
  const [edevlet, setEdevlet] = useState(false);
  const [user, setUser] = useState(null);
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const f = () => setHash(window.location.hash);
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);

  if (hash.startsWith("#/panel")) return <Panel />;

  return (
    <>
      {screen === "login" && <LoginScreen onEdevlet={() => setEdevlet(true)} />}
      {screen === "app" && user && <NSosyalApp user={user} />}
      {edevlet && (
        <EDevletModal
          onClose={() => setEdevlet(false)}
          onSuccess={(u) => { setUser(u); setEdevlet(false); setScreen("app"); }}
        />
      )}
    </>
  );
}
