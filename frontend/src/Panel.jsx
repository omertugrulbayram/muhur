import { useEffect, useMemo, useState } from "react";
import { DEMO_ORGANIZER_KEY, organizerApi } from "./api";
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

const FEATURE_TR = {
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
  "yüksek": { label: "Yüksek", icon: "▲", cls: "bg-[#d03b3b] text-white" },
  "orta": { label: "Orta", icon: "●", cls: "bg-[#fab219] text-ink" },
  "düşük": { label: "Düşük", icon: "○", cls: "bg-surface-2 text-ink-soft ring-1 ring-hair" },
};
const STATUS = {
  acik: { label: "İncelenmedi", cls: "text-ink-soft" },
  sorun_yok: { label: "Sorun yok", cls: "text-trust-high" },
  izle: { label: "İzlemede", cls: "text-trust-med" },
  isaretle: { label: "İşaretlendi", cls: "text-brand" },
};
const DECISIONS = [
  ["sorun_yok", "Sorun yok", "Doğal bir paylaşım; uyarıyı kapat."],
  ["izle", "İzle", "Şimdilik karar verme, takipte tut."],
  ["isaretle", "İşaretle", "Koordineli görünüyor; topluluk kurallarına göre ele al."],
];

const fmtDur = (m) => (m < 90 ? `${Math.max(1, Math.round(m))} dk` : m < 2880 ? `${Math.round(m / 60)} sa` : `${Math.round(m / 1440)} gün`);
const fmtDate = (t) => new Date(t * 1000).toLocaleString("tr-TR", { dateStyle: "short", timeStyle: "short" });

const DemoBadge = ({ children = "DEMO VERİ" }) => (
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
      <TopNav active="panel" wide right={org ? <span className="hidden md:inline font-600">{org.name}</span> : null} />
      <div className="bg-surface border-b border-hair">
        <div className="max-w-7xl mx-auto px-4 py-2 flex items-center gap-2 text-sm">
          <a href="#/panel" className={`px-3 py-1.5 rounded-lg ${route.view === "alerts" ? "bg-ink text-white" : "text-ink-soft hover:text-ink"}`}>Uyarılar</a>
          <a href="#/panel/model" className={`px-3 py-1.5 rounded-lg ${route.view === "model" ? "bg-ink text-white" : "text-ink-soft hover:text-ink"}`}>Model kartı</a>
          <span className="ml-auto text-xs text-ink-soft hidden sm:inline">Uyarı bir suçlama değildir · son karar yöneticidedir</span>
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
      <h2 className="text-lg font-700">Organizatör girişi</h2>
      <p className="text-sm text-ink-soft mt-1">Panel yalnız topluluk yöneticilerine açıktır. Demo kulübün anahtarı hazır yazılı.</p>
      <input value={v} onChange={(e) => setV(e.target.value)} type="password"
        className="mt-4 w-full font-mono text-sm px-3 py-2.5 rounded-lg bg-surface-2 ring-1 ring-hair outline-none focus:ring-ink" />
      {error && <p className="mt-2 text-sm text-brand">{error === "organizer_key_invalid" ? "Anahtar geçersiz." : `${error} — backend açık mı?`}</p>}
      <button onClick={() => onSubmit(v)} className="mt-4 w-full py-2.5 rounded-xl bg-ink text-white font-600">Giriş</button>
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
            <h2 className="font-700">Koordinasyon uyarıları</h2>
            {alerts && <span className="text-xs text-ink-soft">{alerts.length} uyarı · {open} incelenmedi</span>}
          </div>
          <p className="px-1 mt-1 text-xs text-ink-soft leading-snug">
            Kısa sürede benzer şeyler paylaşan hesap grupları. Uyarı bir suçlama değildir; incelemen için öneridir.
          </p>
          <div className="flex gap-1 mt-3 text-xs" role="group" aria-label="Risk düzeyi filtresi">
            {[["yüksek", "Yalnız yüksek"], ["orta", "Orta ve üstü"], ["düşük", "Tümü"]].map(([v, l]) => (
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
                  <span className="text-xs text-ink-soft">{a.size} hesap · {fmtDur(a.span_min)}</span>
                  <span className={`ml-auto text-[11px] font-600 ${STATUS[a.status].cls}`}>{STATUS[a.status].label}</span>
                </div>
                <p className="mt-2 text-sm leading-snug line-clamp-2">“{a.sample_text}”</p>
                {a.top_signals[0] && <p className="mt-1.5 text-xs text-ink-soft">▲ {a.top_signals[0]}</p>}
              </a>
            </li>
          ))}
          {alerts?.length === 0 && <li className="text-sm text-ink-soft p-3">Bu filtreyle uyarı yok.</li>}
        </ul>
      </aside>

      <section>
        {selectedId ? <AlertDetail api={api} id={selectedId} onReviewed={() => setReload((x) => x + 1)} />
          : <p className="text-sm text-ink-soft p-6">Soldan bir uyarı seç.</p>}
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
  if (!d) return <p className="text-sm text-ink-soft p-6">Yükleniyor…</p>;
  const exp = d.explanation;
  const posts = showAllPosts ? d.posts : d.posts.slice(0, 8);

  return (
    <div className="space-y-4 ink-in">
      {/* başlık */}
      <Card>
        <div className="flex flex-wrap items-center gap-3">
          <LevelChip level={d.level} />
          <span className="text-2xl font-700 font-mono">{Math.round(d.risk * 100)}%</span>
          <span className="text-sm text-ink-soft">koordinasyon riski</span>
          <span className={`ml-auto text-sm font-600 ${STATUS[d.status].cls}`}>{STATUS[d.status].label}</span>
        </div>
        <div className="mt-2 text-sm text-ink-soft flex flex-wrap gap-x-4 gap-y-1">
          <span>{d.size} hesap</span><span>{d.n_posts} paylaşım</span>
          <span>{fmtDur(d.span_min)} içinde</span><span>ilk paylaşım: {d.first_post}</span>
          <span className="font-mono text-xs self-center">{d.id} · model {d.model_version}</span>
        </div>
        <div className="mt-3 text-[13px] bg-surface-2 rounded-lg px-3 py-2 text-ink-soft">
          ⓘ {exp.caveat}
        </div>
      </Card>

      <div className="grid xl:grid-cols-2 gap-4">
        <Card title="Neden dikkat çekti?">
          {exp.signals.length ? (
            <ul className="space-y-2">
              {exp.signals.map((s) => (
                <li key={s.feature} className="flex gap-2 text-sm leading-snug">
                  <span className="text-[#d03b3b]" aria-hidden>▲</span>
                  <span>{s.text} <span className="text-ink-soft text-xs">({s.label})</span></span>
                </li>
              ))}
            </ul>
          ) : <p className="text-sm text-ink-soft">Riski belirgin şekilde artıran bir sinyal yok.</p>}
          {exp.mitigating.length > 0 && (
            <>
              <h4 className="mt-4 mb-2 text-sm font-700">Riski azaltanlar</h4>
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

        <Card title="Olası masum açıklamalar" className="ring-[#2a78d6]/30">
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

      <Card title="Hesaplar arası bağlantılar" right={<DemoBadge />}>
        <NetworkGraph graph={d.graph} accounts={d.accounts} />
      </Card>

      <Card title="Modelin hesabı" right={<span className="text-xs text-ink-soft">her özelliğin risk puanına katkısı</span>}>
        <ContributionChart values={d.contributions} features={d.features} />
        <p className="mt-3 text-xs text-ink-soft">
          Lojistik regresyon: risk = σ(taban + Σ katkı). Katkılar ortalama bir kümeye göre ölçülür; etkinlik, kulüp ve bölüm bağlamı ise “hiç bağlam yok” noktasına göre, bu yüzden yalnız riski azaltabilir. Gerekçeler bu katkılardan üretilir, sonradan yazılmış metin değildir.
        </p>
      </Card>

      <div className="grid xl:grid-cols-2 gap-4">
        <Card title="Paylaşımlar" right={<span className="text-xs text-ink-soft">{d.posts.length} paylaşım</span>}>
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
              {showAllPosts ? "Daha az göster" : `Tümünü göster (${d.posts.length})`}
            </button>
          )}
        </Card>

        <Card title="Hesaplar">
          <div className="overflow-auto max-h-96">
            <table className="w-full text-sm">
              <thead className="text-xs text-ink-soft text-left">
                <tr><th className="py-1 pr-2 font-600">Hesap</th><th className="pr-2 font-600">PoP</th>
                  <th className="pr-2 font-600">Yaş</th><th className="pr-2 font-600">Bölüm</th><th className="font-600">Yakın etkinlik</th></tr>
              </thead>
              <tbody className="divide-y divide-hair">
                {d.accounts.map((a) => (
                  <tr key={a.id}>
                    <td className="py-1.5 pr-2 font-mono text-xs">@{a.handle}</td>
                    <td className="pr-2 whitespace-nowrap">{a.sealed ? <span className="text-trust-high" title="Mühürlü (PoP)">✓</span> : <span className="text-ink-soft">—</span>}</td>
                    <td className={`pr-2 whitespace-nowrap ${a.is_new ? "font-600" : ""}`}>{a.account_age_days} gün{a.is_new ? " (yeni)" : ""}</td>
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
          {showTruth ? "Gerçek senaryoyu gizle" : "Demo: gerçek senaryoyu göster (yalnız değerlendirme için)"}
        </button>
        {showTruth && (
          <div className="mt-2 bg-surface-2 rounded-lg px-3 py-2 text-[13px]">
            Bu küme sentetik kampüste <b>{d.demo_truth.description}</b> senaryosundan geliyor
            (saflık %{Math.round(d.demo_truth.purity * 100)}). Gerçek üründe bu bilgi yoktur;
            yalnız modelin doğru çalışıp çalışmadığını göstermek için buradadır.
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
    <Card title="İnsan incelemesi" right={<span className="text-xs text-ink-soft">son karar senin</span>}>
      <textarea value={note} onChange={(e) => setNote(e.target.value)} rows={2} maxLength={500}
        placeholder="Not (isteğe bağlı): ör. 'Kulübün duyurusu, kontrol ettim.'"
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
          <h4 className="mt-4 mb-1 text-sm font-700">Geçmiş</h4>
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
      const d = Math.max(0.01, Math.hypot(dx, dy)), f = (d * d) / k;
      disp[a].x -= (dx / d) * f; disp[a].y -= (dy / d) * f;
      disp[b].x += (dx / d) * f; disp[b].y += (dy / d) * f;
    }
    for (let i = 0; i < n; i++) {
      disp[i].x += (w / 2 - pos[i].x) * 0.05; disp[i].y += (h / 2 - pos[i].y) * 0.05;
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
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-ink-soft mb-2" aria-label="Lejant">
        <span className="inline-flex items-center gap-1.5"><svg width="12" height="12"><circle cx="6" cy="6" r="5" fill={C_SEALED} /></svg>mühürlü (PoP) · {sealedN}</span>
        <span className="inline-flex items-center gap-1.5"><svg width="12" height="12"><circle cx="6" cy="6" r="5" fill={C_UNSEALED} /></svg>mühürsüz · {graph.nodes.length - sealedN}</span>
        <span className="inline-flex items-center gap-1.5"><svg width="16" height="16"><circle cx="8" cy="8" r="4" fill="#9aa3ad" /><circle cx="8" cy="8" r="7" fill="none" stroke="#15181c" strokeDasharray="2 2" /></svg>son 30 günde açılmış</span>
        <span className="inline-flex items-center gap-1.5"><svg width="20" height="8"><line x1="0" y1="4" x2="20" y2="4" stroke={C_FOLLOW} strokeWidth="2" /></svg>takip</span>
        <span className="inline-flex items-center gap-1.5"><svg width="20" height="8"><line x1="0" y1="4" x2="20" y2="4" stroke="#15181c" strokeOpacity=".55" strokeWidth="2" strokeDasharray="4 3" /></svg>benzer paylaşım</span>
      </div>
      <div className="relative">
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto bg-[#fcfcfb] rounded-xl ring-1 ring-hair" role="img"
          aria-label={`${graph.nodes.length} hesaplık ağ: ${graph.follow_edges.length} takip, ${graph.similarity_edges.length} benzer paylaşım bağlantısı`}>
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
            <div>{h.sealed ? "Mühürlü (PoP)" : "Mühürsüz"} · {h.account_age_days} günlük hesap</div>
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
        <span className="inline-flex items-center gap-1.5"><span className="w-3 h-2 rounded-sm" style={{ background: C_UP }} />riski artırır</span>
        <span className="inline-flex items-center gap-1.5"><span className="w-3 h-2 rounded-sm" style={{ background: C_DOWN }} />riski azaltır</span>
      </div>
      <ul className="space-y-1.5">
        {rows.map(([f, v]) => {
          const pct = (Math.abs(v) / max) * 50;
          const raw = features?.[f];
          return (
            <li key={f} className="grid grid-cols-[150px_1fr_52px] items-center gap-2 text-xs group"
              title={`${FEATURE_TR[f] || f}: katkı ${v >= 0 ? "+" : ""}${v.toFixed(2)}${raw != null ? ` · ölçülen değer ${raw}` : ""}`}>
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
const SCEN_TR = {
  event_crowd: "Etkinlik sonrası ortak paylaşım", club_announce: "Kulüp duyurusu",
  dorm_friends: "Yurt arkadaşları", exam_night: "Sınav gecesi",
  bot_network: "Bot ağı", bought_accounts: "Satın alınmış hesaplar",
  paid_humans: "Ücretli gerçek kişiler", slow_campaign: "Yavaş kampanya",
};

const SHIFT_TR = {
  kucuk_kampus_250: "Küçük kampüs (250 öğrenci)", buyuk_kampus_900: "Büyük kampüs (900 öğrenci)",
  masum_agirlikli: "Masum senaryo ağırlıklı", saldiri_agirlikli: "Saldırı ağırlıklı",
};

function ModelCard({ api }) {
  const [m, setM] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => { api.model().then(setM).catch((e) => setErr(e.message)); }, [api]);
  if (err) return <p className="p-6 text-sm text-brand">{err}</p>;
  if (!m) return <p className="p-6 text-sm text-ink-soft">Yükleniyor…</p>;
  const ev = m.evaluation;
  const pct = (x) => `%${Math.round(x * 100)}`;
  return (
    <div className="max-w-5xl mx-auto px-4 py-4 space-y-4 ink-in">
      <Card title={`Model kartı · ${m.version}`} right={<DemoBadge>SENTETİK VERİ</DemoBadge>}>
        <p className="text-sm"><b>{m.type}.</b> {m.why}</p>
        <p className="mt-2 text-sm text-ink-soft">{m.data} PoP (mühür) durumu risk hesabına katılmaz: gerçek insan olmak koordinasyon
          olmadığını, mühürsüz olmak da koordinasyonu kanıtlamaz.</p>
      </Card>

      {ev && (
        <div className="grid lg:grid-cols-2 gap-4">
          <Card title="Görülmemiş test dünyalarında sonuç">
            <table className="w-full text-sm">
              <thead className="text-xs text-ink-soft text-left">
                <tr><th className="py-1 font-600">Yöntem</th><th className="font-600 text-right">F1</th>
                  <th className="font-600 text-right">Yanlış alarm (küme)</th><th className="font-600 text-right">Uyarıya düşen normal öğrenci</th></tr>
              </thead>
              <tbody className="divide-y divide-hair">
                {[["lr", "Bu model (LR)"], ["gb", "Gradient Boosting (karşılaştırma)"], ["naive", "Basit kural: benzer + hızlı"]].map(([k, l]) => (
                  <tr key={k} className={k === "lr" ? "font-600" : ""}>
                    <td className="py-1.5">{l}</td>
                    <td className="text-right font-mono">{ev[k].cluster.f1.toFixed(2)}</td>
                    <td className="text-right font-mono">{pct(ev[k].cluster.cluster_fpr)}</td>
                    <td className="text-right font-mono">{pct(ev[k].normal_account_fpr)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="mt-2 text-xs text-ink-soft">{ev.n_test_clusters} aday küme, {ev.n_test_positive} koordineli · eğitim ve test farklı kampüs dünyalarında.</p>
          </Card>

          <Card title="Senaryo bazında uyarı oranı">
            <table className="w-full text-sm">
              <thead className="text-xs text-ink-soft text-left">
                <tr><th className="py-1 font-600">Senaryo</th><th className="font-600">Tür</th>
                  <th className="font-600 text-right">Bu model</th><th className="font-600 text-right">Basit kural</th></tr>
              </thead>
              <tbody className="divide-y divide-hair">
                {Object.entries(ev.lr.scenarios).map(([k, s]) => (
                  <tr key={k}>
                    <td className="py-1.5">{SCEN_TR[k] || k}</td>
                    <td className="text-xs text-ink-soft">{s.kind === "masum" ? "masum → düşük olmalı" : "koordineli → yüksek olmalı"}</td>
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
          <Card title="Eşik değişince ne olur?">
            <table className="w-full text-sm">
              <thead className="text-xs text-ink-soft text-left">
                <tr><th className="py-1 font-600">Eşik</th><th className="font-600 text-right">Masum alarm</th>
                  <th className="font-600 text-right">Koordineli tespit</th><th className="font-600 text-right">Normal öğrenci YP</th></tr>
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
            <p className="mt-2 text-xs text-ink-soft">Tespit eşikten neredeyse bağımsız: kaçan kampanyaların çoğu aday kümeye hiç girmiyor.</p>
          </Card>
          <Card title="Saldırı ve dağılım kayması">
            <table className="w-full text-sm">
              <tbody className="divide-y divide-hair">
                <tr><td className="py-1.5">Kamufle saldırı (etkinlik katılımcılarına kampanya, eğitimde görülmedi)</td>
                  <td className="text-right font-mono">{pct(m.robustness.adversarial.rates.camouflaged_campaign)} tespit</td></tr>
                {Object.entries(m.robustness.distribution_shift).map(([k, v]) => (
                  <tr key={k}><td className="py-1.5">{SHIFT_TR[k] || k}</td>
                    <td className="text-right font-mono whitespace-nowrap">{pct(v.koordineli_ortalama_tespit)} tespit · {pct(v.masum_ortalama_alarm)} alarm</td></tr>
                ))}
              </tbody>
            </table>
          </Card>
        </div>
      )}

      <Card title="Katsayılar" right={<span className="text-xs text-ink-soft">standartlaştırılmış özellik başına</span>}>
        <ContributionChart values={m.coefficients} />
      </Card>

      <Card title="Bilinen sınırlar">
        <ul className="space-y-1.5 text-sm list-disc pl-5">
          {m.limits.map((l, i) => <li key={i}>{l}</li>)}
        </ul>
      </Card>
    </div>
  );
}
