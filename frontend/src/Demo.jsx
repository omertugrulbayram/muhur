import { useCallback, useEffect, useRef, useState } from "react";
import QRCode from "qrcode";
import { api } from "./api";
import { EN, L } from "./i18n";
import { BAND, Footer, MuhurBadge, SealStamp, TopNav, initials } from "./shared";

/* ============================================================
   Kullanıcı demosu — rehberli akış
   1 Kimliğini doğrula (PoP)  2 Etkinliğe QR ile katıl (PoA)
   3 Akışı incele              4 Topluluk paneli
   Hesaplar/paylaşımlar sentetik demo kampüsünden, riskler modelden gelir.
   ============================================================ */

const EVENT_ID = "hackathon-2026";
const EVENT_NAME = L("Kampüs Hackathon 2026", "Campus Hackathon 2026");
const ME = L("Sen", "You");

// Sunucunun makine-okunur ret kodları → okunur metin
const REASON_EN = {
  replay_detected: "this QR code has already been used (replay detected)",
  already_attended: "you already attended this event",
  expired: "the QR code has expired",
};
const REASON_TR = {
  replay_detected: "bu QR daha önce kullanıldı (tekrar kullanım tespit edildi)",
};
function reasonText(msg) {
  const code = String(msg).replace("Check-in reddedildi: ", "").trim();
  return (EN ? REASON_EN : REASON_TR)[code] || code;
}

function demoTc() {
  let tc = localStorage.getItem("muhur-demo-tc");
  if (!tc) {
    tc = "9" + Array.from({ length: 10 }, () => Math.floor(Math.random() * 10)).join("");
    localStorage.setItem("muhur-demo-tc", tc);
  }
  return tc;
}
const attKey = (tc) => `muhur-user-att:${tc}`;

/* ------------------------------------------------------------ rehber */
function Guide({ done, onStep }) {
  const steps = [
    ["pop", L("Kimliğini doğrula", "Verify you are human"), "PoP"],
    ["poa", L("Etkinliğe QR ile katıl", "Check in to an event by QR"), "PoA"],
    ["explore", L("Akışı incele", "Explore the feed"), L("Uyarılar", "Alerts")],
    ["panel", L("Yönetici olarak karar ver", "Decide as a moderator"), "Panel"],
  ];
  const current = steps.findIndex(([k]) => !done[k]);
  return (
    <div className="bg-surface border-b border-hair">
      <ol className="max-w-6xl mx-auto px-4 py-2.5 flex gap-2 overflow-x-auto text-sm">
        {steps.map(([k, label, tag], i) => {
          const isDone = done[k], isNow = i === current;
          return (
            <li key={k} className="shrink-0">
              <button onClick={() => onStep(k)}
                className={`flex items-center gap-2 px-3 py-1.5 rounded-full ring-1 transition
                  ${isNow ? "ring-brand bg-brand/5" : isDone ? "ring-hair" : "ring-hair opacity-60"}`}>
                <span className={`grid place-items-center w-5 h-5 rounded-full text-[11px] font-700
                  ${isDone ? "bg-trust-high text-white" : isNow ? "bg-brand text-white" : "bg-surface-2 text-ink-soft"}`}>
                  {isDone ? "✓" : i + 1}
                </span>
                <span className={isNow ? "font-600" : ""}>{label}</span>
                <span className="text-[10px] text-ink-soft font-mono">{tag}</span>
              </button>
            </li>
          );
        })}
      </ol>
    </div>
  );
}

/* ------------------------------------------------------------ giriş */
function Welcome({ onStart }) {
  return (
    <div className="max-w-3xl mx-auto px-4 py-12 ink-in">
      <div className="bg-surface rounded-3xl ring-1 ring-hair p-8 sm:p-10">
        <p className="text-sm font-600 text-brand">{L("Adım 1 · Kanıtlanmış insan (PoP)", "Step 1 · Proof of personhood (PoP)")}</p>
        <h1 className="mt-2 text-3xl font-700 tracking-tight">{L("NSosyal'e katıl, mührünü al.", "Join, and get your seal.")}</h1>
        <p className="mt-3 text-ink-soft leading-relaxed">
          {L(
            <>Kimliğin bir kez doğrulanır ve hesabına <b className="text-ink">MÜHÜR</b> verilir. TC kimlik numaran
              hiçbir yere kaydedilmez; yalnız tek yönlü bir takma kimliğe çevrilir ve imzalı bir token olarak sana verilir.</>,
            <>Your identity is verified once and your account receives a <b className="text-ink">SEAL</b>. Your national ID
              number is never stored; it is turned into a one-way pseudonym and handed to you as a signed token.</>,
          )}
        </p>
        <button onClick={onStart}
          className="mt-7 w-full sm:w-auto flex items-center justify-center gap-3 px-6 py-3.5 rounded-xl bg-gov text-white font-600 hover:bg-gov-deep transition">
          <span className="grid place-items-center w-6 h-6 rounded bg-white/20 text-sm font-700">e</span>
          {L("e-Devlet ile doğrula (simülasyon)", "Verify with e-Devlet (simulated)")}
        </button>
        <div className="mt-6 grid sm:grid-cols-3 gap-3 text-sm">
          {[[L("Saklanmaz", "Never stored"), L("TC numarası veritabanında, token'da ya da logda yok.", "The ID number is not in the database, the token or the logs.")],
            [L("Seçmeli açıklama", "Selective disclosure"), L("Doğum tarihi değil, yalnız \"15 yaş üstü\" bilgisi.", "Not your birth date — only the fact \"over 15\".")],
            [L("Doğrulanabilir", "Verifiable"), L("Token Ed25519 ile imzalı; açık anahtar herkese açık.", "The token is Ed25519-signed; the public key is published.")]].map(([t, d]) => (
            <div key={t} className="rounded-xl bg-surface-2 p-3">
              <div className="font-600">{t}</div><div className="text-ink-soft text-[13px] mt-0.5">{d}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function EDevletModal({ onSuccess, onClose }) {
  const [tc, setTc] = useState(demoTc);
  const [busy, setBusy] = useState(false);
  const [ok, setOk] = useState(false);
  const [err, setErr] = useState("");

  async function login() {
    setErr(""); setBusy(true);
    try {
      const r = await api.popVerify(tc.trim() || demoTc(), 2003);
      localStorage.setItem("muhur-demo-tc", tc.trim());
      setOk(true);
      setTimeout(() => onSuccess({ tc: tc.trim(), name: ME, handle: "sen", credential: r.credential, token: r.personhood_token }), 1300);
    } catch (e) {
      setErr(`${e.message || e} — ${L("sunucu açık mı?", "is the server running?")}`); setBusy(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-md bg-surface rounded-2xl overflow-hidden shadow-2xl ink-in">
        <div className="bg-gov text-white px-5 py-3 flex items-center justify-between">
          <span className="font-700">{L("e-Devlet Kapısı", "e-Devlet Gateway")}</span>
          <span className="text-[10px] font-700 px-2 py-0.5 rounded bg-white/20">{L("SİMÜLASYON", "SIMULATION")}</span>
        </div>
        <div className="bg-trust-med/10 text-[12px] text-ink-soft px-5 py-2.5 border-b border-hair">
          {L(
            <>⚠ Bu ekran bir <b>simülasyondur</b>. Gerçek e-Devlet değildir; hiçbir kuruma bilgi gönderilmez.
              Numara bu tarayıcı için rastgele üretildi.</>,
            <>⚠ This screen is a <b>simulation</b>. It is not the real e-Devlet (Turkey's government login); nothing is sent
              to any institution. The number was generated randomly for this browser.</>,
          )}
        </div>
        {ok ? (
          <div className="p-8 text-center">
            <div className="w-28 h-28 mx-auto"><SealStamp stampKey={1} /></div>
            <p className="mt-4 font-600">{L("Kimliğin doğrulandı, mührün verildi.", "Verified. Your seal has been issued.")}</p>
            <p className="text-sm text-ink-soft">{L("Akışa yönlendiriliyorsun…", "Taking you to the feed…")}</p>
          </div>
        ) : (
          <div className="p-5">
            <label className="block text-sm font-600 mb-1" htmlFor="tc">{L("T.C. Kimlik No (demo)", "National ID no. (demo)")}</label>
            <input id="tc" value={tc} onChange={(e) => setTc(e.target.value)} inputMode="numeric"
              className="w-full font-mono text-sm px-3 py-2.5 rounded-lg bg-surface-2 ring-1 ring-hair focus:ring-gov outline-none" />
            <label className="block text-sm font-600 mb-1 mt-4" htmlFor="pw">{L("Şifre", "Password")}</label>
            <input id="pw" defaultValue="demo1234" type="password" disabled
              className="w-full font-mono text-sm px-3 py-2.5 rounded-lg bg-surface-2 ring-1 ring-hair outline-none opacity-60" />
            <p className="mt-1 text-[11px] text-ink-soft">{L("Simülasyonda şifre kontrol edilmez.", "The password is not checked in the simulation.")}</p>
            {err && <p className="mt-3 text-sm text-brand">{err}</p>}
            <button onClick={login} disabled={busy}
              className="mt-5 w-full py-3 rounded-xl bg-gov text-white font-600 hover:bg-gov-deep disabled:opacity-60">
              {busy ? L("Doğrulanıyor…", "Verifying…") : L("Giriş Yap", "Sign in")}
            </button>
            <button onClick={onClose} className="mt-2 w-full py-2 text-sm text-ink-soft hover:text-ink">{L("Vazgeç", "Cancel")}</button>
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------ QR ile katılım */
function CheckinModal({ user, onAttended, onClose }) {
  const [ch, setCh] = useState(null);
  const [svg, setSvg] = useState("");
  const [now, setNow] = useState(() => Date.now());
  const [phase, setPhase] = useState("qr");     // qr | ok | already
  const [replay, setReplay] = useState(null);
  const [err, setErr] = useState("");

  const newQr = useCallback(async () => {
    setErr(""); setReplay(null);
    try {
      const c = await api.poaChallenge(EVENT_ID);
      setCh(c);
      setSvg(await QRCode.toString(c.checkin_token, { type: "svg", margin: 1, errorCorrectionLevel: "L", color: { dark: "#15181c", light: "#ffffff" } }));
    } catch (e) { setErr(e.message); }
  }, []);

  useEffect(() => { newQr(); }, [newQr]);
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(t);
  }, []);
  const left = ch ? Math.max(0, ch.expires_at - Math.floor(now / 1000)) : 0;

  async function scan() {
    setErr("");
    try {
      const r = await api.poaCheckin(ch.checkin_token, user.token);
      onAttended(r.attendance_token);
      setPhase("ok");
    } catch (e) {
      if (e.status === 409 && /already_attended/.test(e.message)) setPhase("already");
      else setErr(reasonText(e.message));
    }
  }
  async function replayAttack() {
    try {
      await api.poaCheckin(ch.checkin_token, user.token);
      setReplay({ ok: false, text: L("Beklenmedik: sunucu aynı QR'ı ikinci kez kabul etti.", "Unexpected: the server accepted the same QR twice.") });
    } catch (e) {
      setReplay({ ok: true, text: reasonText(e.message) });
    }
  }

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4" role="dialog" aria-modal="true">
      <div className="w-full max-w-lg bg-surface rounded-2xl overflow-hidden shadow-2xl ink-in">
        <div className="bg-ink text-white px-5 py-3 flex items-center justify-between">
          <span className="font-700">{EVENT_NAME} · {L("giriş noktası", "entrance")}</span>
          <button onClick={onClose} className="text-white/70 hover:text-white text-sm">{L("Kapat ✕", "Close ✕")}</button>
        </div>
        <div className="p-5">
          {phase === "qr" && (
            <>
              <p className="text-sm text-ink-soft">
                {L(
                  <>Kulüp girişte bu QR'ı gösteriyor. <b className="text-ink">90 saniye</b> geçerli, <b className="text-ink">tek kullanımlık</b> ve
                    kulübün anahtarıyla imzalı. Okuttuğunda katılımın senin mührüne bağlanır.</>,
                  <>The club shows this QR at the door. It is valid for <b className="text-ink">90 seconds</b>, <b className="text-ink">single-use</b> and
                    signed with the club's key. When you scan it, your attendance is bound to your seal.</>,
                )}
              </p>
              <div className="mt-4 flex flex-col sm:flex-row gap-5 items-center">
                <div className="w-48 h-48 shrink-0 rounded-xl ring-1 ring-hair p-2 bg-white"
                  dangerouslySetInnerHTML={{ __html: svg }} aria-label={L("Check-in QR kodu", "Check-in QR code")} />
                <div className="flex-1 w-full">
                  <div className="text-xs text-ink-soft">{L("Kalan süre", "Time left")}</div>
                  <div className={`text-3xl font-700 font-mono ${left < 15 ? "text-brand" : ""}`}>{left} {L("sn", "s")}</div>
                  <div className="mt-2 h-1.5 rounded-full bg-surface-2 overflow-hidden">
                    <div className="h-full bg-ink transition-all" style={{ width: `${(left / 90) * 100}%` }} />
                  </div>
                  {left === 0 && ch ? (
                    <button onClick={newQr} className="mt-4 w-full py-2.5 rounded-xl ring-1 ring-hair font-600">{L("Süre doldu — yeni QR iste", "Expired — request a new QR")}</button>
                  ) : (
                    <button onClick={scan} disabled={!ch}
                      className="mt-4 w-full py-3 rounded-xl bg-brand text-white font-600 hover:bg-brand-deep disabled:opacity-50">
                      📷 {L("QR'ı okut", "Scan the QR")}
                    </button>
                  )}
                  <p className="mt-2 text-[11px] text-ink-soft">{L("Demo: bu arayüz QR'ı üretmek için kulüp rolünü de oynuyor.", "Demo: this UI also plays the club's role to generate the QR.")}</p>
                </div>
              </div>
            </>
          )}
          {phase === "ok" && (
            <div className="text-center">
              <div className="w-24 h-24 mx-auto"><SealStamp stampKey={2} label={L("KANITLANMIŞ KATILIM • PoA • ", "VERIFIED ATTENDANCE • PoA • ")} /></div>
              <p className="mt-3 font-700 text-lg">{L("Katılımın kanıtlandı.", "Attendance verified.")}</p>
              <p className="text-sm text-ink-soft">{L("İmzalı katılım kanıtı yalnız senin mührüne bağlı; başkası kullanamaz. Güven puanın güncellendi.", "The signed attendance proof is bound to your seal only; nobody else can use it. Your trust score was updated.")}</p>
              <div className="mt-5 rounded-xl bg-surface-2 p-4 text-left">
                <div className="text-sm font-700">{L("Saldırıyı sen dene", "Try the attack yourself")}</div>
                <p className="text-[13px] text-ink-soft mt-0.5">
                  {L("Biri QR'ın fotoğrafını çekip tekrar okutursa ne olur? Aynı QR'ı ikinci kez gönder:", "What if someone photographs the QR and scans it again? Send the same QR a second time:")}
                </p>
                <button onClick={replayAttack} className="mt-3 px-4 py-2 rounded-lg ring-1 ring-ink text-sm font-600 hover:bg-ink hover:text-white transition">
                  {L("Aynı QR'ı tekrar okut", "Scan the same QR again")}
                </button>
                {replay && (
                  <p className={`mt-3 text-sm font-600 ${replay.ok ? "text-trust-high" : "text-brand"}`}>
                    {replay.ok ? `🛡 ${L("Sunucu reddetti", "Rejected by the server")}: ${replay.text}` : replay.text}
                    {replay.ok && <span className="block text-[12px] font-400 text-ink-soft">{L("Kullanılmış QR'lar veritabanında tutulur; sunucu yeniden başlasa bile tekrar kabul edilmez.", "Used QR codes are stored in the database; they are not accepted again even after a server restart.")}</span>}
                  </p>
                )}
              </div>
              <button onClick={onClose} className="mt-5 w-full py-3 rounded-xl bg-ink text-white font-600">{L("Akışa dön", "Back to the feed")}</button>
            </div>
          )}
          {phase === "already" && (
            <div className="text-center py-4">
              <p className="font-700">{L("Bu etkinliğe zaten katılmışsın.", "You have already attended this event.")}</p>
              <p className="text-sm text-ink-soft mt-1">{L("Aynı kişi aynı etkinliğe bir kez katılabilir — sunucu ikinci katılım kanıtı vermez.", "One person can attend the same event once — the server will not issue a second attendance proof.")}</p>
              <button onClick={onClose} className="mt-5 px-5 py-2.5 rounded-xl bg-ink text-white font-600">{L("Tamam", "OK")}</button>
            </div>
          )}
          {err && <p className="mt-3 text-sm text-brand">{err}</p>}
        </div>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------ akış */
/* Mühürlü demo hesap PoP alır. Uyarısı olmayan normal öğrencilerin TEKNOFEST katılım
   kanıtı sunucuda kayıtlıdır (demo uç) — her tarayıcıda aynı sonuç görünür. */
async function sealPersona(p) {
  const r = await api.popVerify(p.national_id, 2003);
  return api.trustScore(r.personhood_token, p.attendance_tokens || []);
}

const UNSEALED_RESULT = {
  trust_score: 0, band: "low", axes: { identity: 0, authenticity: 1 },
  explanation: [L("Kanıtlanmış insan (PoP) token'ı yok — hesap mühürsüz.", "No proof-of-personhood (PoP) token — the account is unsealed.")],
};

function TrustPill({ r }) {
  const b = BAND[r.band];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-600 ring-1 ${b.cls} ${b.ring}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${b.bg}`} />{r.trust_score.toFixed(2)}
    </span>
  );
}

const WARN_RE = EN ? /\bhigh\b|^no |not counted|unsealed/i : /yüksek|yok\b|yok\.|sayılmadı|mühürsüz/i;

function Explanation({ r }) {
  const b = BAND[r.band];
  return (
    <div className="mt-2 ink-in rounded-xl bg-surface-2 p-3">
      <div className="flex items-center gap-2 mb-2 text-xs font-600 flex-wrap">
        <span className={b.cls}>{b.label} · {r.trust_score.toFixed(2)}</span>
        <span className="text-ink-soft">= {L("kimlik", "identity")} {Math.round(r.axes.identity * 100)}% × {L("otantiklik", "authenticity")} {Math.round(r.axes.authenticity * 100)}%</span>
      </div>
      <ul className="space-y-1.5">
        {r.explanation.map((line, i) => {
          const warn = WARN_RE.test(line);
          return (
            <li key={i} className="flex gap-2 text-sm text-ink-soft leading-snug">
              <span className={warn ? "text-brand" : "text-trust-high"}>{warn ? "▲" : "•"}</span>{line}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

function PostCard({ post, meta, showNotes, onExplore }) {
  const [open, setOpen] = useState(false);
  const [liked, setLiked] = useState(false);
  const r = meta?.result;
  const flagged = meta?.alertLevel === "yüksek";
  return (
    <article className={`bg-surface rounded-2xl ring-1 p-4 ${flagged ? "ring-brand/40" : "ring-hair"}`}>
      <div className="flex gap-3">
        <div className="w-10 h-10 rounded-full bg-surface-2 grid place-items-center font-700 text-ink-soft shrink-0">{initials(post.name)}</div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 flex-wrap">
            <span className="font-700">{post.name}</span>
            {post.sealed && <MuhurBadge />}
            <span className="text-ink-soft text-sm">@{post.handle}</span>
            {post.time && <span className="text-ink-soft text-xs">· {post.time}</span>}
            {r && <span className="ml-auto"><TrustPill r={r} /></span>}
          </div>
          <p className="mt-1.5 text-[15px] leading-snug">{post.text}</p>
          {flagged && (
            <div className="mt-2 text-xs text-brand bg-brand/5 ring-1 ring-brand/20 rounded-lg px-3 py-1.5">
              {L(
                "⚠ Model bu hesabı yüksek riskli bir koordinasyon kümesinde buldu. Bu bir yargı değil; topluluk yöneticisinin incelemesini bekliyor.",
                "⚠ The model found this account in a high-risk coordination cluster. This is not a verdict; it is waiting for the community moderator's review.")}{" "}
              <a href={`#/panel/${meta.alertId}`} onClick={onExplore} className="underline font-600">{L("Uyarıyı panelde aç →", "Open the alert in the panel →")}</a>
            </div>
          )}
          {showNotes && post.demo_role && (
            <div className="mt-2 text-[11px] text-ink-soft bg-surface-2 rounded-md px-2 py-1 inline-block">
              🎓 {L("Demo notu", "Demo note")}: {post.demo_role} · {L("gerçek senaryo", "true scenario")}: {post.demo_truth}
            </div>
          )}
          <div className="mt-3 flex items-center gap-6 text-ink-soft text-sm">
            <span className="flex items-center gap-1.5">💬 12</span>
            <span className="flex items-center gap-1.5">🔁 4</span>
            <button onClick={() => setLiked((v) => !v)} className={`flex items-center gap-1.5 ${liked ? "text-rocket" : "hover:text-rocket"}`}>
              🚀 {liked ? 89 : 88}
            </button>
            {r && (
              <button onClick={() => { setOpen((o) => !o); onExplore(); }}
                className="ml-auto text-xs font-600 hover:text-ink underline underline-offset-2">
                {open ? L("Gizle", "Hide") : L("Bu puan neden?", "Why this score?")}
              </button>
            )}
          </div>
          {open && r && <Explanation r={r} />}
        </div>
      </div>
    </article>
  );
}

function MySeal({ user, trust, attendance, onCheckin }) {
  const [open, setOpen] = useState(true);
  return (
    <div className="bg-surface rounded-2xl ring-1 ring-hair p-4">
      <div className="flex items-center gap-3">
        <div className="w-11 h-11 rounded-full bg-brand/10 text-brand grid place-items-center font-700">{L("S", "Y")}</div>
        <div>
          <div className="font-700 flex items-center gap-1.5">{ME} <MuhurBadge /></div>
          <div className="text-[11px] text-ink-soft font-mono">{L("takma kimlik", "pseudonym")} {user.credential.claims.uniqueness_nishani.slice(0, 12)}…</div>
        </div>
        {trust && <span className="ml-auto"><TrustPill r={trust} /></span>}
      </div>

      <ul className="mt-4 space-y-2 text-sm">
        <li className="flex gap-2"><span className="text-trust-high">✓</span><span><b>{L("Kanıtlanmış insan", "Verified human")}</b> <span className="text-ink-soft">{L("(PoP, imzalı)", "(PoP, signed)")}</span></span></li>
        <li className="flex gap-2">
          <span className={attendance.length ? "text-trust-high" : "text-ink-soft"}>{attendance.length ? "✓" : "○"}</span>
          <span><b>{L("Kanıtlanmış katılım", "Verified attendance")}</b> <span className="text-ink-soft">{attendance.length ? `(${attendance.length} ${L("etkinlik", attendance.length === 1 ? "event" : "events")})` : L("(henüz yok)", "(none yet)")}</span></span>
        </li>
        <li className="flex gap-2"><span className="text-trust-high">✓</span><span><b>{L("Davranış", "Behaviour")}</b> <span className="text-ink-soft">{L("(koordinasyon uyarısı yok)", "(no coordination alert)")}</span></span></li>
      </ul>

      {!attendance.length ? (
        <button onClick={onCheckin} className="mt-4 w-full py-2.5 rounded-xl bg-brand text-white font-600 hover:bg-brand-deep transition">
          {L(`Adım 2 · ${EVENT_NAME} etkinliğine QR ile katıl`, `Step 2 · Check in to ${EVENT_NAME} by QR`)}
        </button>
      ) : (
        <button onClick={onCheckin} className="mt-4 w-full py-2 rounded-xl ring-1 ring-hair text-sm font-600 hover:ring-ink">
          {L("Katılım QR'ını tekrar aç (saldırıyı dene)", "Open the check-in QR again (try the attack)")}
        </button>
      )}

      {trust && (
        <>
          <button onClick={() => setOpen((o) => !o)} className="mt-3 text-xs font-600 underline underline-offset-2 text-ink-soft hover:text-ink">
            {open ? L("Puan açıklamasını gizle", "Hide the score explanation") : L("Puanım neden bu?", "Why is my score this?")}
          </button>
          {open && <Explanation r={trust} />}
        </>
      )}
    </div>
  );
}

function Feed({ user, done, setDone, checkin, setCheckin }) {
  const [personas, setPersonas] = useState(null);
  const [meta, setMeta] = useState({});
  const [err, setErr] = useState("");
  const [draft, setDraft] = useState("");
  const [mine, setMine] = useState([]);
  const [filter, setFilter] = useState("all");
  const [showNotes, setShowNotes] = useState(true);
  const [attendance, setAttendance] = useState(() => JSON.parse(localStorage.getItem(attKey(user.tc)) || "[]"));
  const [trust, setTrust] = useState(null);
  const loaded = useRef(false);

  const refreshTrust = useCallback(async (att) => {
    try { setTrust(await api.trustScore(user.token, att)); } catch { /* sunucu yoksa sessiz */ }
  }, [user.token]);

  useEffect(() => { refreshTrust(attendance); }, [refreshTrust, attendance]);

  useEffect(() => {
    if (loaded.current) return;
    loaded.current = true;
    (async () => {
      try {
        const { personas } = await api.demoPersonas();
        const m = {};
        await Promise.all(personas.map(async (p) => {
          const result = p.sealed ? await sealPersona(p) : UNSEALED_RESULT;
          m[p.handle] = { result, alertLevel: p.alert_level, alertId: p.alert_id };
        }));
        setMeta(m); setPersonas(personas);
      } catch (e) { setErr(String(e.message || e)); }
    })();
  }, []);

  function attended(tok) {
    const next = [...attendance, tok];
    setAttendance(next);
    localStorage.setItem(attKey(user.tc), JSON.stringify(next));
    setDone((d) => ({ ...d, poa: true }));
  }
  const explore = () => { if (!done.explore) setDone((d) => ({ ...d, explore: true })); };

  const all = [...mine, ...(personas || [])];
  const visible = all.filter((p) => {
    const r = p.handle === "sen" ? trust : meta[p.handle]?.result;
    if (filter === "sealed") return p.sealed;
    if (filter === "high") return r && r.band !== "low";
    return true;
  });

  return (
    <div className="max-w-6xl mx-auto px-4 py-5 grid lg:grid-cols-[1fr_340px] gap-5 items-start">
      <main className="min-w-0">
        {/* paylaşım kutusu */}
        <div className="bg-surface rounded-2xl ring-1 ring-hair p-4 mb-4">
          <div className="flex gap-3">
            <div className="w-10 h-10 rounded-full bg-brand/10 text-brand grid place-items-center font-700 shrink-0">{L("S", "Y")}</div>
            <div className="flex-1">
              <textarea value={draft} onChange={(e) => setDraft(e.target.value)} rows={2} placeholder={L("Neler oluyor?", "What's happening?")}
                className="w-full resize-none bg-transparent outline-none text-[15px] placeholder:text-ink-soft" />
              <div className="flex items-center justify-between mt-1">
                <span className="text-xs text-ink-soft flex items-center gap-1"><MuhurBadge size={13} /> {L("mühürlü hesabınla paylaşıyorsun", "posting with your sealed account")}</span>
                <button onClick={() => { if (!draft.trim()) return; setMine([{ name: ME, handle: "sen", sealed: true, text: draft.trim(), time: L("şimdi", "now") }, ...mine]); setDraft(""); }}
                  disabled={!draft.trim()} className="px-4 py-1.5 rounded-full bg-brand text-white text-sm font-600 hover:bg-brand-deep disabled:opacity-50">
                  {L("Paylaş", "Post")}
                </button>
              </div>
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2 mb-3 text-sm flex-wrap">
          <span className="text-ink-soft">{L("Göster:", "Show:")}</span>
          {[["all", L("Tümü", "All")], ["sealed", L("Yalnızca mühürlü", "Sealed only")], ["high", L("Orta/yüksek güven", "Medium/high trust")]].map(([id, l]) => (
            <button key={id} onClick={() => setFilter(id)}
              className={`px-3 py-1 rounded-full ring-1 transition ${filter === id ? "bg-ink text-white ring-ink" : "ring-hair text-ink-soft hover:text-ink"}`}>{l}</button>
          ))}
          <label className="ml-auto flex items-center gap-1.5 text-xs text-ink-soft cursor-pointer">
            <input type="checkbox" checked={showNotes} onChange={(e) => setShowNotes(e.target.checked)} /> {L("demo notları", "demo notes")}
          </label>
        </div>
        <p className="text-[12px] text-ink-soft mb-3">
          {L("Akış kronolojik; filtreyi sen seçersin — algoritma senin yerine gizlemez.",
            "The feed is chronological; you choose the filter — no algorithm hides things for you. Posts are from a synthetic Turkish campus.")}
        </p>

        {err && <p className="mb-3 text-sm text-brand">{L("Akış yüklenemedi", "Could not load the feed")}: {err}</p>}
        {!personas && !err ? (
          <p className="text-sm text-ink-soft py-10 text-center">{L("Akış yükleniyor…", "Loading the feed…")}</p>
        ) : (
          <div className="space-y-3">
            {visible.map((p, i) => (
              <PostCard key={p.handle + i} post={p} showNotes={showNotes} onExplore={explore}
                meta={p.handle === "sen" ? { result: trust } : meta[p.handle]} />
            ))}
          </div>
        )}
      </main>

      <aside className="space-y-4 lg:sticky lg:top-32">
        <MySeal user={user} trust={trust} attendance={attendance} onCheckin={() => setCheckin(true)} />
        <div className="bg-ink text-white rounded-2xl p-4">
          <div className="text-sm font-700">{L("Adım 4 · Yönetici gözüyle bak", "Step 4 · See it as a moderator")}</div>
          <p className="text-xs text-white/65 mt-1 leading-relaxed">
            {L(
              "Kırmızı çerçeveli gönderiler modelin uyarılarıdır. Topluluk panelinde nedenlerini, olası masum açıklamalarını ve hesaplar arası bağlantıları görüp karar verebilirsin.",
              "Posts with a red frame are the model's alerts. In the community panel you can see their reasons, possible innocent explanations and the links between accounts, and make a decision.")}
          </p>
          <a href="#/panel" className="mt-3 inline-block px-3 py-2 rounded-lg bg-white text-ink text-sm font-600">{L("Topluluk paneli →", "Community panel →")}</a>
        </div>
      </aside>

      {checkin && <CheckinModal user={user} onAttended={attended} onClose={() => setCheckin(false)} />}
    </div>
  );
}

/* ------------------------------------------------------------ kök */
export default function Demo() {
  const [user, setUser] = useState(null);
  const [modal, setModal] = useState(false);
  const [done, setDone] = useState({ pop: false, poa: false, explore: false, panel: false });
  const [checkin, setCheckin] = useState(false);

  // Rehberdeki her adım ilgili işlemi açar.
  function onStep(k) {
    if (k === "pop" && !user) setModal(true);
    if (k === "poa") { if (user) setCheckin(true); else setModal(true); }
    if (k === "explore" && user) document.querySelector("main article")?.scrollIntoView({ behavior: "smooth", block: "center" });
    if (k === "panel") window.location.hash = "#/panel";
  }

  return (
    <div className="min-h-screen">
      <TopNav active="demo" />
      <Guide done={{ ...done, pop: !!user }} onStep={onStep} />
      {!user ? <Welcome onStart={() => setModal(true)} /> : <Feed user={user} done={done} setDone={setDone} checkin={checkin} setCheckin={setCheckin} />}
      {modal && (
        <EDevletModal onClose={() => setModal(false)}
          onSuccess={(u) => {
            const hasAtt = JSON.parse(localStorage.getItem(attKey(u.tc)) || "[]").length > 0;
            setUser(u); setModal(false); setDone((d) => ({ ...d, pop: true, poa: d.poa || hasAtt }));
          }} />
      )}
      <Footer />
    </div>
  );
}
