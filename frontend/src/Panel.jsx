import { useEffect, useMemo, useState } from "react";
import { DEMO_ORGANIZER_KEY, organizerApi } from "./api";
import { EN, L } from "./i18n";
import { TopNav } from "./shared";

/* ============================================================
   Topluluk yöneticisi paneli
   Öğrenci kulübü / topluluk yöneticisinin açtığı ekran:
   koordinasyon uyarıları, nedenleri, olası masum açıklamalar,
   hesaplar arası ağ ve İNSAN İNCELEMESİ. Model karar vermez.
   ============================================================ */

// Grafik renkleri (dataviz doğrulayıcısından geçti: CVD ΔE ≥ 24, kontrast ≥ 3:1)
const C_SEALED = "#2a78d6";     // mühürlü (PoP)
const C_UNSEALED = "#eb6834";   // mühürsüz
const C_UP = "#e34948";         // riski artırır
const C_DOWN = "#2a78d6";       // riski azaltır
const C_FOLLOW = "#b8c0c9";

const FEATURE_TR = EN ? {
  log_size: "Cluster size",
  mean_similarity: "Message similarity",
  exact_dup_frac: "Identical text",
  log_span_hours: "Time spread",
  new_account_frac: "New-account share",
  creation_spread: "Creation-date spread",
  dormant_frac: "Dormant, then active",
  follow_density: "In-cluster follows",
  hashtag_link_rate: "Hashtag / link",
  shared_event_frac: "Shared event (PoA)",
  shared_club_frac: "Shared club",
  shared_dept_frac: "Same department",
} : {
  log_size: "Küme büyüklüğü",
  mean_similarity: "Mesaj benzerliği",
  exact_dup_frac: "Birebir aynı metin",
  log_span_hours: "Zamana yayılma",
  new_account_frac: "Yeni hesap oranı",
  creation_spread: "Açılış tarihi yayılımı",
  dormant_frac: "Sessizken aktifleşme",
  follow_density: "Küme içi takip",
  hashtag_link_rate: "Hashtag / link",
  shared_event_frac: "Ortak etkinlik (PoA)",
  shared_club_frac: "Ortak kulüp",
  shared_dept_frac: "Aynı bölüm",
};

const LEVEL = {
  "yüksek": { label: L("Yüksek", "High"), icon: "▲", cls: "bg-[#d03b3b] text-white" },
  "orta": { label: L("Orta", "Medium"), icon: "●", cls: "bg-[#fab219] text-ink" },
  "düşük": { label: L("Düşük", "Low"), icon: "○", cls: "bg-surface-2 text-ink-soft ring-1 ring-hair" },
};
const STATUS = {
  acik: { label: L("İncelenmedi", "Not reviewed"), cls: "text-ink-soft" },
  sorun_yok: { label: L("Sorun yok", "No issue"), cls: "text-trust-high" },
  izle: { label: L("İzlemede", "Watching"), cls: "text-trust-med" },
  isaretle: { label: L("İşaretlendi", "Flagged"), cls: "text-brand" },
};
const DECISIONS = [
  ["sorun_yok", L("Sorun yok", "No issue"), L("Doğal bir paylaşım; uyarıyı kapat.", "Natural posting; close the alert.")],
  ["izle", L("İzle", "Watch"), L("Şimdilik karar verme, takipte tut.", "Don't decide yet; keep an eye on it.")],
  ["isaretle", L("İşaretle", "Flag"), L("Koordineli görünüyor; topluluk kurallarına göre ele al.", "Looks coordinated; handle it under the community rules.")],
];

const fmtDur = (m) => (m < 90 ? `${Math.max(1, Math.round(m))} ${L("dk", "min")}` : m < 2880 ? `${Math.round(m / 60)} ${L("sa", "h")}` : `${Math.round(m / 1440)} ${L("gün", "days")}`);
const fmtDate = (t) => new Date(t * 1000).toLocaleString(EN ? "en-GB" : "tr-TR", { dateStyle: "short", timeStyle: "short" });

const DemoBadge = ({ children = L("DEMO VERİ", "DEMO DATA") }) => (
  <span className="text-[10px] font-700 tracking-wide px-2 py-0.5 rounded bg-brand/10 text-brand ring-1 ring-brand/20">
    {children}
  </span>
);

function LevelChip({ level, risk }) {
  const l = LEVEL[level];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-700 ${l.cls}`}>
      <span aria-hidden>{l.icon}</span>{l.label}{risk != null && <span className="font-mono font-500">· {Math.round(risk * 100)}%</span>}
    </span>
  );
}

function useHashRoute() {
  const [hash, setHash] = useState(window.location.hash);
  useEffect(() => {
    const f = () => setHash(window.location.hash);
    window.addEventListener("hashchange", f);
    return () => window.removeEventListener("hashchange", f);
  }, []);
  const parts = hash.replace(/^#\/?/, "").split("/");   // ["panel", "<id>" | "model"]
  return { view: parts[1] === "model" ? "model" : "alerts", alertId: parts[1] && parts[1] !== "model" ? parts[1] : null };
}

/* ------------------------------------------------------------ kök */
export default function Panel() {
  const [key, setKey] = useState(() => sessionStorage.getItem("muhur-org-key") || DEMO_ORGANIZER_KEY);
  const api = useMemo(() => organizerApi(key), [key]);
  const [org, setOrg] = useState(null);
  const [err, setErr] = useState("");
  const route = useHashRoute();

  useEffect(() => {
    api.me().then((o) => { setOrg(o); setErr(""); sessionStorage.setItem("muhur-org-key", key); })
      .catch((e) => { setOrg(null); setErr(e.message); });
  }, [api, key]);

  return (
    <div className="min-h-screen">
      <TopNav active="panel" wide right={org ? <span className="hidden md:inline font-600">{EN && org.id === "demo-kulup" ? "Demo Student Club (DEMO)" : org.name}</span> : null} />
      <div className="bg-surface border-b border-hair">
        <div className="max-w-7xl mx-auto px-4 py-2 flex items-center gap-2 text-sm">
          <a href="#/panel" className={`px-3 py-1.5 rounded-lg ${route.view === "alerts" ? "bg-ink text-white" : "text-ink-soft hover:text-ink"}`}>{L("Uyarılar", "Alerts")}</a>
          <a href="#/panel/model" className={`px-3 py-1.5 rounded-lg ${route.view === "model" ? "bg-ink text-white" : "text-ink-soft hover:text-ink"}`}>{L("Model kartı", "Model card")}</a>
          <span className="ml-auto text-xs text-ink-soft hidden sm:inline">{L("Uyarı bir suçlama değildir · son karar yöneticidedir", "An alert is not an accusation · the moderator makes the final call")}</span>
        </div>
      </div>

      {!org ? (
        <KeyLogin initial={key} onSubmit={setKey} error={err} />
      ) : route.view === "model" ? (
        <ModelCard api={api} />
      ) : (
        <AlertsView api={api} selectedId={route.alertId} />
      )}
    </div>
  );
}

function KeyLogin({ initial, onSubmit, error }) {
  const [v, setV] = useState(initial);
  return (
    <div className="max-w-md mx-auto mt-16 bg-surface rounded-2xl ring-1 ring-hair p-6">
      <h2 className="text-lg font-700">{L("Organizatör girişi", "Organizer sign-in")}</h2>
      <p className="text-sm text-ink-soft mt-1">{L("Panel yalnız topluluk yöneticilerine açıktır. Demo kulübün anahtarı hazır yazılı.", "The panel is only open to community moderators. The demo club's key is pre-filled.")}</p>
      <input value={v} onChange={(e) => setV(e.target.value)} type="password"
        className="mt-4 w-full font-mono text-sm px-3 py-2.5 rounded-lg bg-surface-2 ring-1 ring-hair outline-none focus:ring-ink" />
      {error && <p className="mt-2 text-sm text-brand">{error === "organizer_key_invalid" ? L("Anahtar geçersiz.", "Invalid key.") : `${error} — ${L("backend açık mı?", "is the backend running?")}`}</p>}
      <button onClick={() => onSubmit(v)} className="mt-4 w-full py-2.5 rounded-xl bg-ink text-white font-600">{L("Giriş", "Sign in")}</button>
    </div>
  );
}

/* ------------------------------------------------------------ uyarılar */
function AlertsView({ api, selectedId }) {
  const [minLevel, setMinLevel] = useState("orta");
  const [alerts, setAlerts] = useState(null);
  const [err, setErr] = useState("");
  const [reload, setReload] = useState(0);

  useEffect(() => {
    api.alerts(minLevel).then((r) => setAlerts(r.alerts)).catch((e) => setErr(e.message));
  }, [api, minLevel, reload]);

  useEffect(() => {
    if (!selectedId && alerts?.length) window.location.hash = `#/panel/${alerts[0].id}`;
  }, [alerts, selectedId]);

  const open = alerts?.filter((a) => a.status === "acik").length ?? 0;

  return (
    <div className="max-w-7xl mx-auto px-4 py-4 grid lg:grid-cols-[380px_1fr] gap-4 items-start">
      <aside className="lg:sticky lg:top-28">
        <div className="bg-surface rounded-2xl ring-1 ring-hair p-3">
          <div className="flex items-center justify-between px-1">
            <h2 className="font-700">{L("Koordinasyon uyarıları", "Coordination alerts")}</h2>
            {alerts && <span className="text-xs text-ink-soft">{alerts.length} {L("uyarı", "alerts")} · {open} {L("incelenmedi", "not reviewed")}</span>}
          </div>
          <p className="px-1 mt-1 text-xs text-ink-soft leading-snug">
            {L("Kısa sürede benzer şeyler paylaşan hesap grupları. Uyarı bir suçlama değildir; incelemen için öneridir.",
              "Groups of accounts posting similar things in a short time. An alert is not an accusation; it is a suggestion for your review.")}
          </p>
          <div className="flex gap-1 mt-3 text-xs" role="group" aria-label={L("Risk düzeyi filtresi", "Risk level filter")}>
            {[["yüksek", L("Yalnız yüksek", "High only")], ["orta", L("Orta ve üstü", "Medium and up")], ["düşük", L("Tümü", "All")]].map(([v, l]) => (
              <button key={v} onClick={() => setMinLevel(v)}
                className={`px-2.5 py-1 rounded-full ring-1 ${minLevel === v ? "bg-ink text-white ring-ink" : "ring-hair text-ink-soft hover:text-ink"}`}>
                {l}
              </button>
            ))}
          </div>
        </div>
        {err && <p className="mt-3 text-sm text-brand">{err}</p>}
        <ul className="mt-3 space-y-2 lg:max-h-[calc(100vh-17rem)] overflow-auto pr-1">
          {alerts?.map((a) => (
            <li key={a.id}>
              <a href={`#/panel/${a.id}`}
                className={`block bg-surface rounded-xl ring-1 p-3 transition ${a.id === selectedId ? "ring-ink" : "ring-hair hover:ring-ink/40"}`}>
                <div className="flex items-center gap-2">
                  <LevelChip level={a.level} risk={a.risk} />
                  <span className="text-xs text-ink-soft">{a.size} {L("hesap", "accounts")} · {fmtDur(a.span_min)}</span>
                  <span className={`ml-auto text-[11px] font-600 ${STATUS[a.status].cls}`}>{STATUS[a.status].label}</span>
                </div>
                <p className="mt-2 text-sm leading-snug line-clamp-2">“{a.sample_text}”</p>
                {a.top_signals[0] && <p className="mt-1.5 text-xs text-ink-soft">▲ {a.top_signals[0]}</p>}
              </a>
            </li>
          ))}
          {alerts?.length === 0 && <li className="text-sm text-ink-soft p-3">{L("Bu filtreyle uyarı yok.", "No alerts with this filter.")}</li>}
        </ul>
      </aside>

      <section>
        {selectedId ? <AlertDetail api={api} id={selectedId} onReviewed={() => setReload((x) => x + 1)} />
          : <p className="text-sm text-ink-soft p-6">{L("Soldan bir uyarı seç.", "Pick an alert on the left.")}</p>}
      </section>
    </div>
  );
}

function Card({ title, children, right, className = "" }) {
  return (
    <div className={`bg-surface rounded-2xl ring-1 ring-hair p-4 ${className}`}>
      {title && (
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-700 text-[15px]">{title}</h3>{right}
        </div>
      )}
      {children}
    </div>
  );
}

function AlertDetail({ api, id, onReviewed }) {
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  const [showTruth, setShowTruth] = useState(false);
  const [showAllPosts, setShowAllPosts] = useState(false);

  const load = () => api.alert(id).then(setD).catch((e) => setErr(e.message));
  useEffect(() => { setD(null); setShowTruth(false); setShowAllPosts(false); load(); }, [id]); // eslint-disable-line

  if (err) return <p className="text-sm text-brand p-4">{err}</p>;
  if (!d) return <p className="text-sm text-ink-soft p-6">{L("Yükleniyor…", "Loading…")}</p>;
  const exp = d.explanation;
  const posts = showAllPosts ? d.posts : d.posts.slice(0, 8);

  return (
    <div className="space-y-4 ink-in">
      {/* başlık */}
      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <LevelChip level={d.level} />
          <span className="text-2xl font-700 font-mono">{Math.round(d.risk * 100)}%</span>
          <span className="text-sm text-ink-soft">{L("koordinasyon riski", "coordination risk")}</span>
          <span className={`ml-auto text-sm font-600 ${STATUS[d.status].cls}`}>{STATUS[d.status].label}</span>
        </div>
        <div className="mt-2 text-sm text-ink-soft flex flex-wrap gap-x-4 gap-y-1">
          <span>{d.size} {L("hesap", "accounts")}</span><span>{d.n_posts} {L("paylaşım", "posts")}</span>
          <span>{L(`${fmtDur(d.span_min)} içinde`, `within ${fmtDur(d.span_min)}`)}</span><span>{L("ilk paylaşım", "first post")}: {d.first_post}</span>
          <span className="font-mono text-xs self-center">{d.id} · model {d.model_version}</span>
        </div>
        <div className="mt-3 text-[13px] bg-surface-2 rounded-lg px-3 py-2 text-ink-soft">
          ⓘ {exp.caveat}
        </div>
      </Card>

      <div className="grid xl:grid-cols-2 gap-4">
        <Card title={L("Neden dikkat çekti?", "Why was this flagged?")}>
          {exp.signals.length ? (
            <ul className="space-y-2">
              {exp.signals.map((s) => (
                <li key={s.feature} className="flex gap-2 text-sm leading-snug">
                  <span className="text-[#d03b3b]" aria-hidden>▲</span>
                  <span>{s.text} <span className="text-ink-soft text-xs">({s.label})</span></span>
                </li>
              ))}
            </ul>
          ) : <p className="text-sm text-ink-soft">{L("Riski belirgin şekilde artıran bir sinyal yok.", "No signal clearly raises the risk.")}</p>}
          {exp.mitigating.length > 0 && (
            <>
              <h4 className="mt-4 mb-2 text-sm font-700">{L("Riski azaltanlar", "What lowers the risk")}</h4>
              <ul className="space-y-2">
                {exp.mitigating.map((s) => (
                  <li key={s.feature} className="flex gap-2 text-sm leading-snug">
                    <span className="text-[#2a78d6]" aria-hidden>▼</span>
                    <span>{s.text} <span className="text-ink-soft text-xs">({s.label})</span></span>
                  </li>
                ))}
              </ul>
            </>
          )}
        </Card>

        <Card title={L("Olası masum açıklamalar", "Possible innocent explanations")} className="ring-[#2a78d6]/30">
          {exp.cautions?.length > 0 && (
            <ul className="space-y-2 mb-3">
              {exp.cautions.map((t, i) => (
                <li key={i} className="flex gap-2 text-sm leading-snug bg-[#fab219]/15 rounded-lg px-2.5 py-1.5">
                  <span aria-hidden className="font-700">!</span><span>{t}</span>
                </li>
              ))}
            </ul>
          )}
          <ul className="space-y-2">
            {exp.innocent_explanations.map((t, i) => (
              <li key={i} className="flex gap-2 text-sm leading-snug"><span aria-hidden>?</span><span>{t}</span></li>
            ))}
          </ul>
          <p className="mt-3 text-xs text-ink-soft">{exp.pop_context}</p>
        </Card>
      </div>

      <Card title={L("Hesaplar arası bağlantılar", "Links between accounts")} right={<DemoBadge />}>
        <NetworkGraph graph={d.graph} accounts={d.accounts} />
      </Card>

      <Card title={L("Modelin hesabı", "How the model scored it")} right={<span className="text-xs text-ink-soft">{L("her özelliğin risk puanına katkısı", "each feature's contribution to the risk score")}</span>}>
        <ContributionChart values={d.contributions} features={d.features} />
        <p className="mt-3 text-xs text-ink-soft">
          {L("Lojistik regresyon: risk = σ(taban + Σ katkı). Katkılar ortalama bir kümeye göre ölçülür; etkinlik, kulüp ve bölüm bağlamı ise “hiç bağlam yok” noktasına göre, bu yüzden yalnız riski azaltabilir. Gerekçeler bu katkılardan üretilir, sonradan yazılmış metin değildir.",
            "Logistic regression: risk = σ(base + Σ contribution). Contributions are measured against an average cluster; event, club and department context is measured against “no context at all”, so it can only lower the risk. The reasons are generated from these contributions, not written afterwards.")}
        </p>
      </Card>

      <div className="grid xl:grid-cols-2 gap-4">
        <Card title={L("Paylaşımlar", "Posts")} right={<span className="text-xs text-ink-soft">{d.posts.length} {L("paylaşım", "posts")}</span>}>
          <ul className="divide-y divide-hair">
            {posts.map((p, i) => (
              <li key={i} className="py-2 text-sm">
                <div className="text-xs text-ink-soft"><span className="font-600 text-ink">@{p.handle}</span> · {p.time}</div>
                <div className="leading-snug">{p.text}</div>
              </li>
            ))}
          </ul>
          {d.posts.length > 8 && (
            <button onClick={() => setShowAllPosts((x) => !x)} className="mt-2 text-xs font-600 underline underline-offset-2">
              {showAllPosts ? L("Daha az göster", "Show less") : `${L("Tümünü göster", "Show all")} (${d.posts.length})`}
            </button>
          )}
        </Card>

        <Card title={L("Hesaplar", "Accounts")}>
          <div className="overflow-auto max-h-96">
            <table className="w-full text-sm">
              <thead className="text-xs text-ink-soft text-left">
                <tr><th className="py-1 pr-2 font-600">{L("Hesap", "Account")}</th><th className="pr-2 font-600">PoP</th>
                  <th className="pr-2 font-600">{L("Yaş", "Age")}</th><th className="pr-2 font-600">{L("Bölüm", "Department")}</th><th className="font-600">{L("Yakın etkinlik", "Recent event")}</th></tr>
              </thead>
              <tbody className="divide-y divide-hair">
                {d.accounts.map((a) => (
                  <tr key={a.id}>
                    <td className="py-1.5 pr-2 font-mono text-xs">@{a.handle}</td>
                    <td className="pr-2 whitespace-nowrap">{a.sealed ? <span className="text-trust-high" title={L("Mühürlü (PoP)", "Sealed (PoP)")}>✓</span> : <span className="text-ink-soft">—</span>}</td>
                    <td className={`pr-2 whitespace-nowrap ${a.is_new ? "font-600" : ""}`}>{a.account_age_days} {L("gün", "days")}{a.is_new ? L(" (yeni)", " (new)") : ""}</td>
                    <td className="pr-2">{a.department}</td>
                    <td className="text-xs">{a.recent_events.join(", ") || <span className="text-ink-soft">—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>

      <ReviewBox api={api} alert={d} onDone={() => { load(); onReviewed(); }} />

      <div className="text-sm">
        <button onClick={() => setShowTruth((x) => !x)} className="text-ink-soft underline underline-offset-2 text-xs">
          {showTruth ? L("Gerçek senaryoyu gizle", "Hide the true scenario") : L("Demo: gerçek senaryoyu göster (yalnız değerlendirme için)", "Demo: show the true scenario (for evaluation only)")}
        </button>
        {showTruth && (
          <div className="mt-2 bg-surface-2 rounded-lg px-3 py-2 text-[13px]">
            {EN ? (<>This cluster comes from the <b>{d.demo_truth.description}</b> scenario in the synthetic campus
              (purity {Math.round(d.demo_truth.purity * 100)}%). A real product does not have this information;
              it is here only to show whether the model works correctly.</>) : (<>
            Bu küme sentetik kampüste <b>{d.demo_truth.description}</b> senaryosundan geliyor
            (saflık %{Math.round(d.demo_truth.purity * 100)}). Gerçek üründe bu bilgi yoktur;
            yalnız modelin doğru çalışıp çalışmadığını göstermek için buradadır.</>)}
          </div>
        )}
      </div>
    </div>
  );
}

function ReviewBox({ api, alert, onDone }) {
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  async function decide(decision) {
    setBusy(true); setErr("");
    try { await api.review(alert.id, decision, note.trim()); setNote(""); onDone(); }
    catch (e) { setErr(e.message); }
    setBusy(false);
  }
  return (
    <Card title={L("İnsan incelemesi", "Human review")} right={<span className="text-xs text-ink-soft">{L("son karar senin", "the final call is yours")}</span>}>
      <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} maxLength={500}
        placeholder={L("Not (isteğe bağlı): ör. 'Kulübün duyurusu, kontrol ettim.'", "Note (optional): e.g. 'Club announcement, I checked.'")}
        className="w-full text-sm px-3 py-2 rounded-lg bg-surface-2 ring-1 ring-hair outline-none focus:ring-ink resize-none" />
      <div className="mt-2 grid sm:grid-cols-3 gap-2">
        {DECISIONS.map(([v, l, hint]) => (
          <button key={v} disabled={busy} onClick={() => decide(v)} title={hint}
            className={`py-2 rounded-xl text-sm font-600 ring-1 transition disabled:opacity-50
              ${alert.status === v ? "bg-ink text-white ring-ink" : "ring-hair hover:ring-ink"}`}>
            {l}
            <span className="block text-[11px] font-400 opacity-70">{hint}</span>
          </button>
        ))}
      </div>
      {err && <p className="mt-2 text-sm text-brand">{err}</p>}
      {alert.reviews.length > 0 && (
        <>
          <h4 className="mt-4 mb-1 text-sm font-700">{L("Geçmiş", "History")}</h4>
          <ul className="text-sm space-y-1">
            {alert.reviews.slice().reverse().map((r, i) => (
              <li key={i} className="flex gap-2">
                <span className={`font-600 ${STATUS[r.decision].cls}`}>{STATUS[r.decision].label}</span>
                <span className="text-ink-soft text-xs self-center">{fmtDate(r.created_at)}</span>
                {r.note && <span className="text-ink-soft">— {r.note}</span>}
              </li>
            ))}
          </ul>
        </>
      )}
    </Card>
  );
}

/* ------------------------------------------------------------ ağ grafiği */
function forceLayout(nodes, edges, w, h) {
  const n = nodes.length;
  const pos = nodes.map((_, i) => ({
    x: w / 2 + Math.cos((2 * Math.PI * i) / n) * w * 0.3,
    y: h / 2 + Math.sin((2 * Math.PI * i) / n) * h * 0.3,
  }));
  const idx = new Map(nodes.map((d, i) => [d.id, i]));
  const E = edges.map(([a, b]) => [idx.get(a), idx.get(b)]).filter(([a, b]) => a != null && b != null);
  const k = Math.sqrt((w * h) / Math.max(1, n)) * 0.55;
  // Yoğun kümelerde (ör. 32 hesap, yüzlerce benzer paylaşım bağlantısı) çekim baskın gelip
  // düğümler tek yumağa toplanıyordu: çekimi ortalama dereceye göre zayıflat.
  const avgDeg = (2 * E.length) / Math.max(1, n);
  const pull = 1 / Math.max(1, avgDeg / 3);
  const iters = 300;
  for (let it = 0; it < iters; it++) {
    const temp = (w / 10) * (1 - it / iters) + 0.5;
    const disp = pos.map(() => ({ x: 0, y: 0 }));
    for (let i = 0; i < n; i++) for (let j = i + 1; j < n; j++) {
      const dx = pos[i].x - pos[j].x, dy = pos[i].y - pos[j].y;
      const d = Math.max(0.01, Math.hypot(dx, dy)), f = (k * k) / d;
      disp[i].x += (dx / d) * f; disp[i].y += (dy / d) * f;
      disp[j].x -= (dx / d) * f; disp[j].y -= (dy / d) * f;
    }
    for (const [a, b] of E) {
      const dx = pos[a].x - pos[b].x, dy = pos[a].y - pos[b].y;
      const d = Math.max(0.01, Math.hypot(dx, dy)), f = ((d * d) / k) * pull;
      disp[a].x -= (dx / d) * f; disp[a].y -= (dy / d) * f;
      disp[b].x += (dx / d) * f; disp[b].y += (dy / d) * f;
    }
    for (let i = 0; i < n; i++) {
      disp[i].x += (w / 2 - pos[i].x) * 0.05 * pull; disp[i].y += (h / 2 - pos[i].y) * 0.05 * pull;
      const d = Math.max(0.01, Math.hypot(disp[i].x, disp[i].y));
      pos[i].x += (disp[i].x / d) * Math.min(d, temp);
      pos[i].y += (disp[i].y / d) * Math.min(d, temp);
      pos[i].x = Math.min(w - 16, Math.max(16, pos[i].x));
      pos[i].y = Math.min(h - 16, Math.max(16, pos[i].y));
    }
  }
  return pos;
}

function NetworkGraph({ graph, accounts }) {
  const W = 720, H = 360;
  const [hover, setHover] = useState(null);
  const pos = useMemo(
    () => forceLayout(graph.nodes, [...graph.follow_edges, ...graph.similarity_edges.map(([a, b]) => [a, b])], W, H),
    [graph]);
  const at = new Map(graph.nodes.map((nd, i) => [nd.id, pos[i]]));
  const acc = new Map(accounts.map((a) => [a.id, a]));
  const h = hover != null ? acc.get(hover) : null;
  const hp = hover != null ? at.get(hover) : null;
  const sealedN = graph.nodes.filter((x) => x.sealed).length;

  return (
    <div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-soft mb-2" aria-label={L("Lejant", "Legend")}>
        <span className="inline-flex items-center gap-1.5"><svg width="12" height="12"><circle cx="6" cy="6" r="5" fill={C_SEALED} /></svg>{L("mühürlü (PoP)", "sealed (PoP)")} · {sealedN}</span>
        <span className="inline-flex items-center gap-1.5"><svg width="12" height="12"><circle cx="6" cy="6" r="5" fill={C_UNSEALED} /></svg>{L("mühürsüz", "unsealed")} · {graph.nodes.length - sealedN}</span>
        <span className="inline-flex items-center gap-1.5"><svg width="16" height="16"><circle cx="8" cy="8" r="4" fill="#9aa3ad" /><circle cx="8" cy="8" r="7" fill="none" stroke="#15181c" strokeDasharray="2 2" /></svg>{L("son 30 günde açılmış", "created in the last 30 days")}</span>
        <span className="inline-flex items-center gap-1.5"><svg width="20" height="8"><line x1="0" y1="4" x2="20" y2="4" stroke={C_FOLLOW} strokeWidth="2" /></svg>{L("takip", "follows")}</span>
        <span className="inline-flex items-center gap-1.5"><svg width="20" height="8"><line x1="0" y1="4" x2="20" y2="4" stroke="#15181c" strokeOpacity=".55" strokeWidth="2" strokeDasharray="4 3" /></svg>{L("benzer paylaşım", "similar post")}</span>
      </div>
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto bg-[#fcfcfb] rounded-xl ring-1 ring-hair" role="img"
          aria-label={L(`${graph.nodes.length} hesaplık ağ: ${graph.follow_edges.length} takip, ${graph.similarity_edges.length} benzer paylaşım bağlantısı`, `Network of ${graph.nodes.length} accounts: ${graph.follow_edges.length} follow and ${graph.similarity_edges.length} similar-post links`)}>
          {graph.follow_edges.map(([a, b], i) => {
            const p = at.get(a), q = at.get(b);
            return p && q ? <line key={"f" + i} x1={p.x} y1={p.y} x2={q.x} y2={q.y} stroke={C_FOLLOW} strokeWidth="1" /> : null;
          })}
          {graph.similarity_edges.map(([a, b], i) => {
            const p = at.get(a), q = at.get(b);
            return p && q ? <line key={"s" + i} x1={p.x} y1={p.y} x2={q.x} y2={q.y} stroke="#15181c" strokeOpacity=".45" strokeWidth="1.5" strokeDasharray="4 3" /> : null;
          })}
          {graph.nodes.map((nd) => {
            const p = at.get(nd.id);
            const active = hover === nd.id;
            return (
              <g key={nd.id} onMouseEnter={() => setHover(nd.id)} onMouseLeave={() => setHover(null)}
                onFocus={() => setHover(nd.id)} onBlur={() => setHover(null)} tabIndex={0} style={{ cursor: "default", outline: "none" }}>
                <circle cx={p.x} cy={p.y} r="14" fill="transparent" />
                {nd.is_new && <circle cx={p.x} cy={p.y} r="11" fill="none" stroke="#15181c" strokeWidth="1.2" strokeDasharray="2 2" />}
                <circle cx={p.x} cy={p.y} r={active ? 8.5 : 7} fill={nd.sealed ? C_SEALED : C_UNSEALED} stroke="#fcfcfb" strokeWidth="2" />
              </g>
            );
          })}
        </svg>
        {h && hp && (
          <div className="pointer-events-none absolute z-10 bg-ink text-white text-xs rounded-lg px-2.5 py-1.5 shadow-lg"
            style={{ left: `${(hp.x / W) * 100}%`, top: `${(hp.y / H) * 100}%`, transform: "translate(-50%, calc(-100% - 14px))" }}>
            <div className="font-600">@{h.handle}</div>
            <div>{h.sealed ? L("Mühürlü (PoP)", "Sealed (PoP)") : L("Mühürsüz", "Unsealed")} · {L(`${h.account_age_days} günlük hesap`, `${h.account_age_days}-day-old account`)}</div>
            <div className="text-white/70">{h.department}{h.recent_events.length ? ` · ${h.recent_events[0]}` : ""}</div>
          </div>
        )}
      </div>
    </div>
  );
}

/* ------------------------------------------------------------ katkı grafiği */
function ContributionChart({ values, features }) {
  const rows = Object.entries(values).sort((a, b) => Math.abs(b[1]) - Math.abs(a[1]));
  const max = Math.max(0.5, ...rows.map(([, v]) => Math.abs(v)));
  return (
    <div>
      <div className="flex gap-4 text-xs text-ink-soft mb-2">
        <span className="inline-flex items-center gap-1.5"><span className="w-3 h-2 rounded-sm" style={{ background: C_UP }} />{L("riski artırır", "raises risk")}</span>
        <span className="inline-flex items-center gap-1.5"><span className="w-3 h-2 rounded-sm" style={{ background: C_DOWN }} />{L("riski azaltır", "lowers risk")}</span>
      </div>
      <ul className="space-y-1.5">
        {rows.map(([f, v]) => {
          const pct = (Math.abs(v) / max) * 50;
          const raw = features?.[f];
          return (
            <li key={f} className="grid grid-cols-[150px_1fr_52px] items-center gap-2 text-xs group"
              title={`${FEATURE_TR[f] || f}: ${L("katkı", "contribution")} ${v >= 0 ? "+" : ""}${v.toFixed(2)}${raw != null ? ` · ${L("ölçülen değer", "measured value")} ${raw}` : ""}`}>
              <span className="text-ink-soft truncate">{FEATURE_TR[f] || f}</span>
              <span className="relative h-3 rounded group-hover:bg-surface-2">
                <span className="absolute top-0 bottom-0 left-1/2 w-px bg-hair" />
                <span className="absolute top-0.5 h-2"
                  style={v >= 0
                    ? { left: "50%", width: `${pct}%`, background: C_UP, borderRadius: "0 4px 4px 0" }
                    : { right: "50%", width: `${pct}%`, background: C_DOWN, borderRadius: "4px 0 0 4px" }} />
              </span>
              <span className="font-mono text-right text-ink">{v >= 0 ? "+" : ""}{v.toFixed(2)}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/* ------------------------------------------------------------ model kartı */
const SCEN_TR = EN ? {
  event_crowd: "Shared posts after an event", club_announce: "Club announcement",
  dorm_friends: "Dorm friends", exam_night: "Exam night",
  bot_network: "Bot network", bought_accounts: "Bought accounts",
  paid_humans: "Paid real people", slow_campaign: "Slow campaign",
} : {
  event_crowd: "Etkinlik sonrası ortak paylaşım", club_announce: "Kulüp duyurusu",
  dorm_friends: "Yurt arkadaşları", exam_night: "Sınav gecesi",
  bot_network: "Bot ağı", bought_accounts: "Satın alınmış hesaplar",
  paid_humans: "Ücretli gerçek kişiler", slow_campaign: "Yavaş kampanya",
};

const SHIFT_TR = EN ? {
  kucuk_kampus_250: "Small campus (250 students)", buyuk_kampus_900: "Large campus (900 students)",
  masum_agirlikli: "Mostly innocent scenarios", saldiri_agirlikli: "Mostly attacks",
} : {
  kucuk_kampus_250: "Küçük kampüs (250 öğrenci)", buyuk_kampus_900: "Büyük kampüs (900 öğrenci)",
  masum_agirlikli: "Masum senaryo ağırlıklı", saldiri_agirlikli: "Saldırı ağırlıklı",
};

function ModelCard({ api }) {
  const [m, setM] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.model().then(setM).catch((e) => setErr(e.message)); }, [api]);
  if (err) return <p className="p-6 text-sm text-brand">{err}</p>;
  if (!m) return <p className="p-6 text-sm text-ink-soft">{L("Yükleniyor…", "Loading…")}</p>;
  const ev = m.evaluation;
  const pct = (x) => (EN ? `${Math.round(x * 100)}%` : `%${Math.round(x * 100)}`);
  return (
    <div className="max-w-5xl mx-auto px-4 py-4 space-y-4 ink-in">
      <Card title={`${L("Model kartı", "Model card")} · ${m.version}`} right={<DemoBadge>{L("SENTETİK VERİ", "SYNTHETIC DATA")}</DemoBadge>}>
        <p className="text-sm"><b>{m.type}.</b> {m.why}</p>
        <p className="mt-2 text-sm text-ink-soft">{m.data} {L("PoP (mühür) durumu risk hesabına katılmaz: gerçek insan olmak koordinasyon olmadığını, mühürsüz olmak da koordinasyonu kanıtlamaz.",
          "PoP (seal) status is not part of the risk calculation: being a real person does not prove there is no coordination, and being unsealed does not prove there is.")}</p>
      </Card>

      {ev && (
        <div className="grid lg:grid-cols-2 gap-4">
          <Card title={L("Görülmemiş test dünyalarında sonuç", "Results on unseen test worlds")}>
            <table className="w-full text-sm">
              <thead className="text-xs text-ink-soft text-left">
                <tr><th className="py-1 font-600">{L("Yöntem", "Method")}</th><th className="font-600 text-right">F1</th>
                  <th className="font-600 text-right">{L("Yanlış alarm (küme)", "False alarms (clusters)")}</th><th className="font-600 text-right">{L("Uyarıya düşen normal öğrenci", "Normal students alerted")}</th></tr>
              </thead>
              <tbody className="divide-y divide-hair">
                {[["lr", L("Bu model (LR)", "This model (LR)")], ["gb", L("Gradient Boosting (karşılaştırma)", "Gradient Boosting (comparison)")], ["naive", L("Basit kural: benzer + hızlı", "Simple rule: similar + fast")]].map(([k, l]) => (
                  <tr key={k} className={k === "lr" ? "font-600" : ""}>
                    <td className="py-1.5">{l}</td>
                    <td className="text-right font-mono">{ev[k].cluster.f1.toFixed(2)}</td>
                    <td className="text-right font-mono">{pct(ev[k].cluster.cluster_fpr)}</td>
                    <td className="text-right font-mono">{pct(ev[k].normal_account_fpr)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-xs text-ink-soft">{L(`${ev.n_test_clusters} aday küme, ${ev.n_test_positive} koordineli · eğitim ve test farklı kampüs dünyalarında.`, `${ev.n_test_clusters} candidate clusters, ${ev.n_test_positive} coordinated · training and test use different campus worlds.`)}</p>
          </Card>

          <Card title={L("Senaryo bazında uyarı oranı", "Alert rate by scenario")}>
            <table className="w-full text-sm">
              <thead className="text-xs text-ink-soft text-left">
                <tr><th className="py-1 font-600">{L("Senaryo", "Scenario")}</th><th className="font-600">{L("Tür", "Type")}</th>
                  <th className="font-600 text-right">{L("Bu model", "This model")}</th><th className="font-600 text-right">{L("Basit kural", "Simple rule")}</th></tr>
              </thead>
              <tbody className="divide-y divide-hair">
                {Object.entries(ev.lr.scenarios).map(([k, s]) => (
                  <tr key={k}>
                    <td className="py-1.5">{SCEN_TR[k] || k}</td>
                    <td className="text-xs text-ink-soft">{s.kind === "masum" ? L("masum → düşük olmalı", "innocent → should be low") : L("koordineli → yüksek olmalı", "coordinated → should be high")}</td>
                    <td className="text-right font-mono">{pct(s.rate)}</td>
                    <td className="text-right font-mono text-ink-soft">{pct(ev.naive.scenarios[k].rate)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}

      {m.robustness && (
        <div className="grid lg:grid-cols-2 gap-4">
          <Card title={L("Eşik değişince ne olur?", "What if the threshold changes?")}>
            <table className="w-full text-sm">
              <thead className="text-xs text-ink-soft text-left">
                <tr><th className="py-1 font-600">{L("Eşik", "Threshold")}</th><th className="font-600 text-right">{L("Masum alarm", "Innocent alarms")}</th>
                  <th className="font-600 text-right">{L("Koordineli tespit", "Coordinated caught")}</th><th className="font-600 text-right">{L("Normal öğrenci YP", "Normal-student FP")}</th></tr>
              </thead>
              <tbody className="divide-y divide-hair">
                {m.robustness.threshold_sweep.map((r) => (
                  <tr key={r.threshold} className={r.threshold === 0.5 ? "font-600" : ""}>
                    <td className="py-1.5 font-mono">{r.threshold.toFixed(1)}</td>
                    <td className="text-right font-mono">{pct(r.masum_ortalama_alarm)}</td>
                    <td className="text-right font-mono">{pct(r.koordineli_ortalama_tespit)}</td>
                    <td className="text-right font-mono">{pct(r.normal_account_fpr)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-xs text-ink-soft">{L("Tespit eşikten neredeyse bağımsız: kaçan kampanyaların çoğu aday kümeye hiç girmiyor.", "Detection barely depends on the threshold: most missed campaigns never enter a candidate cluster.")}</p>
          </Card>
          <Card title={L("Saldırı ve dağılım kayması", "Attacks and distribution shift")}>
            <table className="w-full text-sm">
              <tbody className="divide-y divide-hair">
                <tr><td className="py-1.5">{L("Kamufle saldırı (etkinlik katılımcılarına kampanya, eğitimde görülmedi)", "Camouflaged attack (campaign run through event attendees, never seen in training)")}</td>
                  <td className="text-right font-mono">{pct(m.robustness.adversarial.rates.camouflaged_campaign)} {L("tespit", "caught")}</td></tr>
                {Object.entries(m.robustness.distribution_shift).map(([k, v]) => (
                  <tr key={k}><td className="py-1.5">{SHIFT_TR[k] || k}</td>
                    <td className="text-right font-mono whitespace-nowrap">{pct(v.koordineli_ortalama_tespit)} {L("tespit", "caught")} · {pct(v.masum_ortalama_alarm)} {L("alarm", "alarms")}</td></tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}

      <Card title={L("Katsayılar", "Coefficients")} right={<span className="text-xs text-ink-soft">{L("standartlaştırılmış özellik başına", "per standardized feature")}</span>}>
        <ContributionChart values={m.coefficients} />
      </Card>

      <Card title={L("Bilinen sınırlar", "Known limits")}>
        <ul className="space-y-1.5 text-sm list-disc pl-5">
          {m.limits.map((l, i) => <li key={i}>{l}</li>)}
        </ul>
      </Card>
    </div>
  );
}
