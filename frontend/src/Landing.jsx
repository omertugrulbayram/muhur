import { BAND, Footer, MuhurBadge, TopNav } from "./shared";

/* ============================================================
   Açılış: MÜHÜR (SEAL) ne yapar, nasıl kullanılır, ne gerçek ne demo
   ============================================================ */

const STEPS = [
  {
    n: "1", key: "PoP", title: "Kanıtlanmış insan",
    text: "Hesabın arkasında gerçek ve tek bir kişi olduğu bir kez doğrulanır. TC kimlik numarası saklanmaz; yalnız geri döndürülemez bir takma kimlik ve \"15 yaş üstü\" bilgisi taşınır.",
    tech: "Ed25519 imzalı token · ayrı HMAC takma kimlik",
  },
  {
    n: "2", key: "PoA", title: "Kanıtlanmış katılım",
    text: "Kulüp, etkinlik girişinde 90 saniyelik, tek kullanımlık bir QR gösterir. Okutan kişiye kendi kimliğine bağlı, imzalı bir katılım kanıtı verilir.",
    tech: "Yalnız organizatör üretir · tekrar kullanım engelli",
  },
  {
    n: "3", key: "AI", title: "Koordinasyon tespiti",
    text: "Kısa sürede benzer şeyler paylaşan hesap grupları bulunur. Her uyarı nedenini ve olası masum açıklamasını (ortak etkinlik, kulüp, bölüm) birlikte söyler.",
    tech: "Açıklanabilir model · hesaba \"bot\" demez",
  },
  {
    n: "4", key: "İnsan", title: "Son karar yöneticide",
    text: "Topluluk yöneticisi uyarıyı inceler: \"sorun yok\", \"izle\" ya da \"işaretle\". Güven puanını istemci değiştiremez; sunucu yalnız imzalı kanıtlara bakar.",
    tech: "Kalıcı inceleme kaydı · şeffaf puan",
  },
];

const REAL = [
  "İmzalı kimlik ve katılım kanıtları (Ed25519), açık anahtarla bağımsız doğrulama",
  "TC kimlik numarasının hiçbir yere yazılmaması (veritabanı dahil test edildi)",
  "Organizatör yetkili, tek kullanımlık QR ile check-in",
  "Sunucuda hesaplanan, kandırılamayan güven puanı",
  "Arayüze bağlı, açıklanabilir koordinasyon modeli",
  "Yönetici paneli ve kalıcı insan incelemesi",
  "74 otomatik test, 15 saldırının engellendiğini gösteren saldırı koşumu",
];
const DEMO = [
  "e-Devlet girişi (simülasyon, gerçek kuruma bağlanmaz)",
  "Hesaplar ve paylaşımlar: sentetik kampüs verisi",
  "Model sonuçları: yalnız sentetik veride ölçüldü",
  "Bu demoda arayüz, etkinlik QR'ını üretmek için kulüp rolünü de oynar",
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
          <p className="text-sm font-600 text-brand">MÜHÜR · SEAL — topluluklar için güven katmanı</p>
          <h1 className="mt-3 text-4xl sm:text-5xl font-700 leading-[1.08] tracking-tight">
            Gerçek insanlar.<br />Gerçek katılım.<br /><span className="text-brand">Şeffaf güven.</span>
          </h1>
          <p className="mt-5 text-[17px] text-ink-soft max-w-xl leading-relaxed">
            MÜHÜR, NSosyal gibi platformlara eklenen bir katman: hesabın arkasında gerçek bir insan olduğunu ve
            etkinliklere gerçekten katıldığını kanıtlar; koordineli kampanyaları <b className="text-ink">nedenleriyle</b> topluluk
            yöneticisine gösterir. Kimseyi otomatik olarak suçlamaz — son karar her zaman insandadır.
          </p>
          <div className="mt-7 flex flex-wrap gap-3">
            <a href="#/demo" className="px-5 py-3 rounded-xl bg-brand text-white font-600 hover:bg-brand-deep transition">
              Kullanıcı demosunu başlat →
            </a>
            <a href="#/panel" className="px-5 py-3 rounded-xl bg-ink text-white font-600 hover:bg-ink/85 transition">
              Topluluk paneline git
            </a>
          </div>
          <p className="mt-3 text-xs text-ink-soft">Kayıt gerekmez · yaklaşık 2 dakika · tüm veriler demo</p>
        </div>

        <div className="relative ink-in">
          <div className="absolute -inset-4 bg-brand/5 rounded-3xl -z-10" />
          <p className="text-[11px] text-ink-soft mb-2 text-right">örnek görünüm</p>
          <div className="space-y-2.5">
            <MiniPost name="Selin" handle="selin" sealed text="Kariyer Günleri harikaydı, konuşmacılar çok iyiydi 👏"
              score="0.83" band="high" note="Mühürlü · 1 etkinliğe kanıtlı katılım · koordinasyon sinyali yok" />
            <MiniPost name="Ayşe" handle="ayse" sealed text="Arkadaşlar SınavPro meselesi önemli, yaymamız lazım #sinavpro"
              score="0.04" band="low" flagged
              note="⚠ Gerçek insan, ama bir grup hesapla kısa sürede aynı kampanyayı paylaşmış. Yargı değil; yönetici inceliyor." />
            <MiniPost name="Ogrenci" handle="ogrenci50644" text="Kantin zammına hayır! paylaş yükselt #kantinboykot"
              score="0.00" band="low" flagged note="⚠ Mühürsüz · onlarca yeni hesap dakikalar içinde aynı metni paylaşmış" />
          </div>
        </div>
      </section>

      {/* dört aşama */}
      <section className="max-w-6xl mx-auto px-4 py-8">
        <h2 className="text-2xl font-700">Dört aşamada nasıl çalışır?</h2>
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
          <h2 className="text-xl font-700">Kim kullanır?</h2>
          <p className="mt-2 text-white/75 text-sm leading-relaxed">
            Bir öğrenci kulübünün ya da topluluğun yöneticisi. Örneğin bir kulüp seçimi öncesinde, birkaç dakika içinde
            onlarca hesaptan aynı mesaj yağmaya başladığında:
          </p>
          <ol className="mt-4 space-y-3 text-sm">
            {[
              ["Panel uyarır", "\"32 hesap, 44 dakika, %100'ü son 30 günde açılmış.\""],
              ["Bağlamı gösterir", "\"Bu hesapların hiçbiri o etkinliğe katılmamış; kulüp üyesi de değiller.\""],
              ["Yönetici karar verir", "İnceler, not düşer, \"işaretle\" ya da \"sorun yok\" der. Karar kaydedilir."],
            ].map(([t, d], i) => (
              <li key={t} className="flex gap-3">
                <span className="grid place-items-center w-6 h-6 rounded-full bg-white/15 text-xs font-700 shrink-0">{i + 1}</span>
                <span><b>{t}.</b> <span className="text-white/75">{d}</span></span>
              </li>
            ))}
          </ol>
          <a href="#/panel" className="inline-block mt-5 px-4 py-2 rounded-lg bg-white text-ink text-sm font-600">Paneli aç →</a>
        </div>

        <div className="bg-surface rounded-2xl ring-1 ring-hair p-6">
          <h2 className="text-xl font-700">Rakamlarla <span className="text-sm font-500 text-ink-soft">(sentetik veride)</span></h2>
          <div className="mt-4 grid grid-cols-2 gap-3">
            {[
              ["%2,4", "normal öğrenci uyarıya düşüyor", "bağlama bakmayan basit kuralda %40"],
              ["%0", "kulüp duyurusunda yanlış alarm", "basit kuralda %83"],
              ["%75", "kamufle saldırı yakalandı", "eğitimde hiç görülmedi"],
              ["15/15", "saldırı engellendi", "sahte imza, replay, puan hilesi…"],
            ].map(([big, l, sub]) => (
              <div key={l} className="rounded-xl bg-surface-2 p-3">
                <div className="text-2xl font-700 font-mono">{big}</div>
                <div className="text-sm leading-snug mt-0.5">{l}</div>
                <div className="text-[11px] text-ink-soft mt-1">{sub}</div>
              </div>
            ))}
          </div>
          <p className="mt-3 text-xs text-ink-soft">
            Zayıf noktalar da açık: farklı cümlelerle yazılan kampanyaların bir kısmı hâlâ kaçıyor. Ayrıntılar panelin
            "Model kartı" sekmesinde.
          </p>
        </div>
      </section>

      {/* gerçek / demo */}
      <section className="max-w-6xl mx-auto px-4 py-8">
        <h2 className="text-2xl font-700">Bu prototipte ne gerçek, ne demo?</h2>
        <div className="mt-5 grid md:grid-cols-2 gap-3">
          <div className="bg-surface rounded-2xl ring-1 ring-hair p-5">
            <h3 className="font-700 text-trust-high">✓ Gerçekten çalışıyor</h3>
            <ul className="mt-3 space-y-2 text-sm">{REAL.map((t) => <li key={t} className="flex gap-2"><span className="text-trust-high">•</span>{t}</li>)}</ul>
          </div>
          <div className="bg-surface rounded-2xl ring-1 ring-hair p-5">
            <h3 className="font-700 text-brand">◌ Simülasyon / demo</h3>
            <ul className="mt-3 space-y-2 text-sm">{DEMO.map((t) => <li key={t} className="flex gap-2"><span className="text-brand">•</span>{t}</li>)}</ul>
          </div>
        </div>
        <div className="mt-8 text-center">
          <a href="#/demo" className="inline-block px-6 py-3 rounded-xl bg-brand text-white font-600 hover:bg-brand-deep transition">
            Demoyu başlat →
          </a>
        </div>
      </section>

      <Footer />
    </div>
  );
}
