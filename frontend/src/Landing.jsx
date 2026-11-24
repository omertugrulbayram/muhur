import { L } from "./i18n";
import { BAND, Footer, MuhurBadge, TopNav } from "./shared";

/* ============================================================
   Açılış: MÜHÜR (SEAL) ne yapar, nasıl kullanılır, ne gerçek ne demo
   ============================================================ */

const STEPS = [
  {
    n: "1", key: "PoP", title: L("Kanıtlanmış insan", "Proof of personhood"),
    text: L(
      "Hesabın arkasında gerçek ve tek bir kişi olduğu bir kez doğrulanır. TC kimlik numarası saklanmaz; yalnız geri döndürülemez bir takma kimlik ve \"15 yaş üstü\" bilgisi taşınır.",
      "It is verified once that a single real person stands behind the account. The national ID number is never stored; only an irreversible pseudonym and the fact \"over 15\" are carried."),
    tech: L("Ed25519 imzalı token · ayrı HMAC takma kimlik", "Ed25519-signed token · separate HMAC pseudonym"),
  },
  {
    n: "2", key: "PoA", title: L("Kanıtlanmış katılım", "Proof of attendance"),
    text: L(
      "Kulüp, etkinlik girişinde 90 saniyelik, tek kullanımlık bir QR gösterir. Okutan kişiye kendi kimliğine bağlı, imzalı bir katılım kanıtı verilir.",
      "At the door, the club shows a 90-second, single-use QR code. Whoever scans it receives a signed attendance proof bound to their own identity."),
    tech: L("Yalnız organizatör üretir · tekrar kullanım engelli", "Only the organizer can issue it · replay blocked"),
  },
  {
    n: "3", key: "AI", title: L("Koordinasyon tespiti", "Coordination detection"),
    text: L(
      "Kısa sürede benzer şeyler paylaşan hesap grupları bulunur. Her uyarı nedenini ve olası masum açıklamasını (ortak etkinlik, kulüp, bölüm) birlikte söyler.",
      "Finds groups of accounts posting similar things in a short time. Every alert states its reasons together with possible innocent explanations (a shared event, club or department)."),
    tech: L("Açıklanabilir model · hesaba \"bot\" demez", "Explainable model · never calls an account a \"bot\""),
  },
  {
    n: "4", key: L("İnsan", "Human"), title: L("Son karar yöneticide", "A human makes the call"),
    text: L(
      "Topluluk yöneticisi uyarıyı inceler: \"sorun yok\", \"izle\" ya da \"işaretle\". Güven puanını istemci değiştiremez; sunucu yalnız imzalı kanıtlara bakar.",
      "The community moderator reviews the alert: \"no issue\", \"watch\" or \"flag\". The client cannot change the trust score; the server only looks at signed proofs."),
    tech: L("Kalıcı inceleme kaydı · şeffaf puan", "Persistent review log · transparent score"),
  },
];

const REAL = [
  L("İmzalı kimlik ve katılım kanıtları (Ed25519), açık anahtarla bağımsız doğrulama",
    "Signed identity and attendance proofs (Ed25519), independently verifiable with the public key"),
  L("TC kimlik numarasının hiçbir yere yazılmaması (veritabanı dahil test edildi)",
    "The national ID number is never written anywhere (tested, including the database)"),
  L("Organizatör yetkili, tek kullanımlık QR ile check-in", "Check-in with an organizer-authorized, single-use QR"),
  L("Sunucuda hesaplanan, kandırılamayan güven puanı", "A trust score computed on the server that the client cannot fake"),
  L("Arayüze bağlı, açıklanabilir koordinasyon modeli", "An explainable coordination model wired into the UI"),
  L("Yönetici paneli ve kalıcı insan incelemesi", "Moderator panel and persistent human review"),
  L("77 otomatik test, 15 saldırının engellendiğini gösteren saldırı koşumu",
    "77 automated tests and an attack harness showing 15/15 attacks blocked"),
];
const DEMO = [
  L("e-Devlet girişi (simülasyon, gerçek kuruma bağlanmaz)", "e-Devlet login (simulated, no connection to the real government service)"),
  L("Hesaplar ve paylaşımlar: sentetik kampüs verisi", "Accounts and posts: synthetic campus data (in Turkish)"),
  L("Model sonuçları: yalnız sentetik veride ölçüldü", "Model results: measured on synthetic data only"),
  L("Bu demoda arayüz, etkinlik QR'ını üretmek için kulüp rolünü de oynar",
    "In this demo the UI also plays the club's role to generate the event QR"),
];

function MiniPost({ name, handle, sealed, text, score, band, note, flagged }) {
  const b = BAND[band];
  return (
    <div className={`bg-surface rounded-xl ring-1 p-3 ${flagged ? "ring-brand/40" : "ring-hair"}`}>
      <div className="flex items-center gap-1.5 text-sm">
        <span className="font-700">{name}</span>{sealed && <MuhurBadge size={13} />}
        <span className="text-ink-soft text-xs">@{handle}</span>
        <span className={`ml-auto inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-600 ring-1 ${b.cls} ${b.ring}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${b.bg}`} />{score}
        </span>
      </div>
      <p className="mt-1 text-[13px] leading-snug">{text}</p>
      {note && <p className={`mt-1.5 text-[11px] ${flagged ? "text-brand" : "text-ink-soft"}`}>{note}</p>}
    </div>
  );
}

export default function Landing() {
  return (
    <div className="min-h-screen">
      <TopNav active="home" />

      {/* hero */}
      <section className="max-w-6xl mx-auto px-4 pt-10 pb-8 grid lg:grid-cols-[1.1fr_1fr] gap-10 items-center">
        <div className="ink-in">
          <p className="text-sm font-600 text-brand">{L("MÜHÜR · SEAL — topluluklar için güven katmanı", "SEAL — a trust layer for communities")}</p>
          <h1 className="mt-3 text-4xl sm:text-5xl font-700 leading-[1.08] tracking-tight">
            {L("Gerçek insanlar.", "Real people.")}<br />{L("Gerçek katılım.", "Real attendance.")}<br />
            <span className="text-brand">{L("Şeffaf güven.", "Transparent trust.")}</span>
          </h1>
          <p className="mt-5 text-[17px] text-ink-soft max-w-xl leading-relaxed">
            {L(
              <>MÜHÜR, NSosyal gibi platformlara eklenen bir katman: hesabın arkasında gerçek bir insan olduğunu ve
                etkinliklere gerçekten katıldığını kanıtlar; koordineli kampanyaları <b className="text-ink">nedenleriyle</b> topluluk
                yöneticisine gösterir. Kimseyi otomatik olarak suçlamaz — son karar her zaman insandadır.</>,
              <>SEAL is a layer that plugs into social platforms: it proves that a real person stands behind an account and
                that they really attended events, and it shows coordinated campaigns to the community moderator <b className="text-ink">with
                their reasons</b>. It never accuses anyone automatically — a human always makes the final call.</>,
            )}
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <a href="#/demo" className="px-5 py-3 rounded-xl bg-brand text-white font-600 hover:bg-brand-deep transition">
              {L("Kullanıcı demosunu başlat →", "Start the user demo →")}
            </a>
            <a href="#/panel" className="px-5 py-3 rounded-xl bg-ink text-white font-600 hover:bg-ink/85 transition">
              {L("Topluluk paneline git", "Open the community panel")}
            </a>
          </div>
          <p className="mt-3 text-xs text-ink-soft">{L("Kayıt gerekmez · yaklaşık 2 dakika · tüm veriler demo", "No sign-up · about 2 minutes · all data is demo data")}</p>
        </div>

        <div className="relative ink-in">
          <div className="absolute -inset-4 bg-brand/5 rounded-3xl -z-10" />
          <p className="text-[11px] text-ink-soft mb-2 text-right">{L("örnek görünüm", "example view")}</p>
          <div className="space-y-2.5">
            <MiniPost name="Selin" handle="selin" sealed
              text={L("Kariyer Günleri harikaydı, konuşmacılar çok iyiydi 👏", "Career Days was great, the speakers were excellent 👏")}
              score="0.83" band="high"
              note={L("Mühürlü · 1 etkinliğe kanıtlı katılım · koordinasyon sinyali yok", "Sealed · verified attendance at 1 event · no coordination signal")} />
            <MiniPost name="Ayşe" handle="ayse" sealed
              text={L("Arkadaşlar SınavPro meselesi önemli, yaymamız lazım #sinavpro", "Guys, the SınavPro thing matters, we need to spread it #sinavpro")}
              score="0.04" band="low" flagged
              note={L("⚠ Gerçek insan, ama bir grup hesapla kısa sürede aynı kampanyayı paylaşmış. Yargı değil; yönetici inceliyor.",
                "⚠ A real person, but posted the same campaign with a group of accounts in a short time. Not a verdict; a moderator is reviewing it.")} />
            <MiniPost name="Ogrenci" handle="ogrenci50644"
              text={L("Kantin zammına hayır! paylaş yükselt #kantinboykot", "No to the cafeteria price hike! share it #kantinboykot")}
              score="0.00" band="low" flagged
              note={L("⚠ Mühürsüz · onlarca yeni hesap dakikalar içinde aynı metni paylaşmış", "⚠ Unsealed · dozens of new accounts posted the same text within minutes")} />
          </div>
        </div>
      </section>

      {/* dört aşama */}
      <section className="max-w-6xl mx-auto px-4 py-8">
        <h2 className="text-2xl font-700">{L("Dört aşamada nasıl çalışır?", "How does it work, in four steps?")}</h2>
        <div className="mt-5 grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {STEPS.map((s) => (
            <div key={s.n} className="bg-surface rounded-2xl ring-1 ring-hair p-4 flex flex-col">
              <div className="flex items-center gap-2">
                <span className="grid place-items-center w-7 h-7 rounded-full bg-brand text-white text-sm font-700">{s.n}</span>
                <span className="text-xs font-700 tracking-wide text-ink-soft">{s.key}</span>
              </div>
              <h3 className="mt-3 font-700 text-lg">{s.title}</h3>
              <p className="mt-1.5 text-sm text-ink-soft leading-relaxed flex-1">{s.text}</p>
              <p className="mt-3 text-[11px] font-mono text-ink-soft">{s.tech}</p>
            </div>
          ))}
        </div>
      </section>

      {/* kim kullanır */}
      <section className="max-w-6xl mx-auto px-4 py-8 grid lg:grid-cols-2 gap-4">
        <div className="bg-ink text-white rounded-2xl p-6">
          <h2 className="text-xl font-700">{L("Kim kullanır?", "Who uses it?")}</h2>
          <p className="mt-2 text-white/75 text-sm leading-relaxed">
            {L(
              "Bir öğrenci kulübünün ya da topluluğun yöneticisi. Örneğin bir kulüp seçimi öncesinde, birkaç dakika içinde onlarca hesaptan aynı mesaj yağmaya başladığında:",
              "The moderator of a student club or community. For example, when right before a club election the same message suddenly pours in from dozens of accounts within minutes:")}
          </p>
          <ol className="mt-4 space-y-3 text-sm">
            {[
              [L("Panel uyarır", "The panel raises an alert"), L("\"32 hesap, 44 dakika, %100'ü son 30 günde açılmış.\"", "\"32 accounts, 44 minutes, 100% created in the last 30 days.\"")],
              [L("Bağlamı gösterir", "It shows the context"), L("\"Bu hesapların hiçbiri o etkinliğe katılmamış; kulüp üyesi de değiller.\"", "\"None of these accounts attended that event, and none are club members.\"")],
              [L("Yönetici karar verir", "The moderator decides"), L("İnceler, not düşer, \"işaretle\" ya da \"sorun yok\" der. Karar kaydedilir.", "They review it, add a note and choose \"flag\" or \"no issue\". The decision is recorded.")],
            ].map(([t, d], i) => (
              <li key={t} className="flex gap-3">
                <span className="grid place-items-center w-6 h-6 rounded-full bg-white/15 text-xs font-700 shrink-0">{i + 1}</span>
                <span><b>{t}.</b> <span className="text-white/75">{d}</span></span>
              </li>
            ))}
          </ol>
          <a href="#/panel" className="inline-block mt-5 px-4 py-2 rounded-lg bg-white text-ink text-sm font-600">{L("Paneli aç →", "Open the panel →")}</a>
        </div>

        <div className="bg-surface rounded-2xl ring-1 ring-hair p-6">
          <h2 className="text-xl font-700">{L("Rakamlarla", "In numbers")} <span className="text-sm font-500 text-ink-soft">{L("(sentetik veride)", "(on synthetic data)")}</span></h2>
          <div className="mt-4 grid grid-cols-2 gap-3">
            {[
              [L("%2,4", "2.4%"), L("normal öğrenci uyarıya düşüyor", "of normal students get an alert"), L("bağlama bakmayan basit kuralda %40", "40% with a simple rule that ignores context")],
              [L("%0", "0%"), L("kulüp duyurusunda yanlış alarm", "false alarms on club announcements"), L("basit kuralda %83", "83% with the simple rule")],
              [L("%75", "75%"), L("kamufle saldırı yakalandı", "of camouflaged attacks caught"), L("eğitimde hiç görülmedi", "never seen in training")],
              ["15/15", L("saldırı engellendi", "attacks blocked"), L("sahte imza, replay, puan hilesi…", "forged signatures, replay, score tampering…")],
            ].map(([big, l, sub]) => (
              <div key={l} className="rounded-xl bg-surface-2 p-3">
                <div className="text-2xl font-700 font-mono">{big}</div>
                <div className="text-sm leading-snug mt-0.5">{l}</div>
                <div className="text-[11px] text-ink-soft mt-1">{sub}</div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-ink-soft">
            {L(
              "Zayıf noktalar da açık: farklı cümlelerle yazılan kampanyaların bir kısmı hâlâ kaçıyor. Ayrıntılar panelin \"Model kartı\" sekmesinde.",
              "The weak spots are public too: some campaigns written in different sentences still slip through. Details in the panel's \"Model card\" tab.")}
          </p>
        </div>
      </section>

      {/* gerçek / demo */}
      <section className="max-w-6xl mx-auto px-4 py-8">
        <h2 className="text-2xl font-700">{L("Bu prototipte ne gerçek, ne demo?", "What is real in this prototype, and what is demo?")}</h2>
        <div className="mt-5 grid md:grid-cols-2 gap-3">
          <div className="bg-surface rounded-2xl ring-1 ring-hair p-5">
            <h3 className="font-700 text-trust-high">{L("✓ Gerçekten çalışıyor", "✓ Actually works")}</h3>
            <ul className="mt-3 space-y-2 text-sm">{REAL.map((t) => <li key={t} className="flex gap-2"><span className="text-trust-high">•</span>{t}</li>)}</ul>
          </div>
          <div className="bg-surface rounded-2xl ring-1 ring-hair p-5">
            <h3 className="font-700 text-brand">{L("◌ Simülasyon / demo", "◌ Simulation / demo")}</h3>
            <ul className="mt-3 space-y-2 text-sm">{DEMO.map((t) => <li key={t} className="flex gap-2"><span className="text-brand">•</span>{t}</li>)}</ul>
          </div>
        </div>
        <div className="mt-8 text-center">
          <a href="#/demo" className="inline-block px-6 py-3 rounded-xl bg-brand text-white font-600 hover:bg-brand-deep transition">
            {L("Demoyu başlat →", "Start the demo →")}
          </a>
        </div>
      </section>

      <Footer />
    </div>
  );
}
