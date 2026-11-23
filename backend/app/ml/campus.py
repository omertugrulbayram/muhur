"""
Sentetik kampüs üreteci (DEMO VERİ).

Gerçek kullanıcı verisi kullanmadan, gerçekçi bir üniversite topluluğunun iki
haftalık paylaşım akışını üretir. Amaç modeli yalnız "kolay bot ağlarına" karşı
değil, **masum ama şüpheli görünen** durumlara karşı da sınamaktır.

Hiçbir hesap gerçek bir kişi değildir. İsimler, kulüpler, etkinlikler uydurmadır.

Senaryolar
----------
Masum (etiket 0) — kolayca yanlış pozitif üretebilecek olanlar:
  event_crowd     Aynı etkinliğe katılan öğrenciler etkinlikten sonra kısa sürede
                  benzer şeyler paylaşır.
  club_announce   Kulüp üyeleri kulübün duyurusunu birebir kopyalayıp paylaşır.
  dorm_friends    Aynı yurtta kalan, birbirini yoğun takip eden arkadaşlar aynı
                  akşam aynı konuda yazar.
  exam_night      Sınav gecesi çok sayıda öğrenci aynı ders hakkında yazar.

Koordineli (etiket 1):
  bot_network     Aynı günlerde açılmış, birbirini takip eden yeni hesaplar
                  dakikalar içinde neredeyse aynı kampanya metnini basar.
  bought_accounts Uzun süre sessiz kalmış eski hesaplar birden aynı metni paylaşır.
  paid_humans     Gerçek, mühürlü (PoP) öğrenciler para karşılığı bir kampanyayı
                  farklı kelimelerle paylaşır. Tezin "gerçek insan ≠ otantik
                  davranış" iddiası bu senaryodur.
  slow_campaign   Kampanya üç güne yayılır, metinler yeniden yazılır. Zor vaka.
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

DAY = 1440  # dakika
WINDOW_DAYS = 14

DEPARTMENTS = ["Bilgisayar", "Elektrik", "Makine", "Endüstri", "İşletme", "Psikoloji",
               "Hukuk", "Mimarlık"]
CLUBS = ["Robotik Kulübü", "Siber Güvenlik Kulübü", "Fotoğrafçılık Kulübü", "Dağcılık Kulübü",
         "Tiyatro Kulübü", "Girişimcilik Kulübü", "Yapay Zekâ Topluluğu", "Satranç Kulübü",
         "Müzik Kulübü", "Gönüllülük Topluluğu", "Havacılık Kulübü", "Münazara Kulübü"]
DORMS = ["Çamlık", "Lale", "Kuzey", "Güney", "Papatya", "Yıldız"]
COURSES = ["Diferansiyel Denklemler", "Fizik 2", "Veri Yapıları", "Mikroekonomi", "Statik",
           "Olasılık", "Devre Analizi", "Lineer Cebir"]
EVENT_NAMES = ["Kariyer Günleri", "Bahar Şenliği", "Hackathon", "Robot Yarışması",
               "Siber Güvenlik Zirvesi", "Girişimcilik Zirvesi", "Bilim Şenliği",
               "Mezunlar Buluşması", "Tiyatro Gösterisi", "Konser Gecesi"]
CAMPAIGNS = [
    ("Lezzetçi Döner", "lezzetcidoner", "Kampüsün en iyi dönercisi {x}! Herkes denesin, öğrenciye indirim var 🔥"),
    ("kantin zammı", "kantinboykot", "Kantin zammına hayır! Yarın herkes {x} için toplanıyor, paylaş yükselt 📢"),
    ("SınavPro", "sinavpro", "{x} uygulamasıyla finaller çocuk oyuncağı, linke tıkla kazan 💯"),
    ("öğrenci konseyi", "yenikonsey", "Öğrenci konseyi seçiminde tek doğru tercih belli: {x}! Herkes oy versin 🗳️"),
]

_NAMES = ["ayse", "mehmet", "zeynep", "can", "elif", "emre", "deniz", "burak", "ece", "mert",
          "selin", "kerem", "irem", "onur", "melis", "berk", "yagmur", "arda", "ceren", "ege",
          "dila", "kaan", "sude", "baris", "nehir", "efe", "ipek", "tolga", "asli", "umut"]

# Normal paylaşımlar parça birleştirerek üretilir: aynı konu farklı kişilerde farklı
# cümlelerle çıkar (gerçek akıştaki gibi). Küçük bir sabit cümle havuzu kullanmak,
# herkesin birebir aynı şeyi yazdığı gerçekdışı bir akış üretirdi.
_OPEN = ["", "", "", "ya ", "arkadaşlar ", "bugün ", "sonunda ", "of ", "cidden ", "yine ",
         "sabah sabah ", "akşam akşam ", "itiraf edeyim ", "bu arada ", "şunu söyleyeyim "]
_TOPIC = [
    "{course} ödevi bitmek bilmiyor", "{course} dersinde hiçbir şey anlamadım", "{course} hocası çok iyi anlatıyor",
    "kütüphanede yer bulmak imkânsız", "kütüphane {time} saatinde bile dolu", "{place} önünde kediler toplanmış",
    "{food} yedim fena değildi", "yemekhanede {food} vardı", "kantinde {food} sırası çok uzundu",
    "{dorm} yurdunda sıcak su yok", "{dorm} yurdunun çayı efsane", "otobüs {time} gibi yine dolu geldi",
    "staj başvurusu yaptım {feel}", "yeni bir dizi başladım {feel}", "spor salonuna gittim {feel}",
    "proje grubumla {place} toplandık", "laboratuvar raporu yazıyorum {feel}", "hafta sonu eve gidiyorum {feel}",
    "yağmur başladı ve şemsiyem yok", "kampüs bugün çok sakin", "{place} manzarası harikaydı",
    "telefonum yine şarjsız kaldı", "kulaklığımı {place} unuttum", "gece {time} hâlâ kod yazıyorum",
    "{course} sınavı ertelenmiş", "arkadaşlarla {place} oturduk", "kahvesiz duramıyorum artık",
    "yarın {time} dersim var", "{course} için not paylaşan olur mu", "maç kaç saatte başlıyor bilen var mı",
    "kitap kulübünde güzel bir sohbet döndü", "bisikletimin lastiği patladı", "yeni bir kafe keşfettim {place} yanında",
    "{course} vizesinden kaç aldınız", "bugün {place} çok kalabalıktı", "{food} fiyatı yine artmış",
    "oda arkadaşım {time} saatinde uyandırdı", "yeni bir dil öğrenmeye başladım", "podcast önerisi olan var mı",
    "{place} wifi çekmiyor", "bu hafta üç teslimim var", "kampüse yeni ağaç dikmişler", "gitar çalmayı öğreniyorum",
    "{course} quiz sonuçları açıklanmış", "yürüyüş yaptım {feel}", "{place} önünde konser vardı",
    "ders notlarımı kaybettim", "erasmus başvurusu yapacağım", "hava çok soğudu birden",
    "{dorm} yurdunda çamaşır makinesi bozuk", "film gecesi yapıyoruz gelen var mı",
]
_FILL = {
    "place": ["kütüphane", "A blok", "çimenler", "kantin", "rektörlük", "mühendislik binası",
              "spor salonu", "kafeterya", "göl kenarı", "B blok", "otopark", "durak"],
    "food": ["mercimek çorbası", "tost", "makarna", "pilav", "kuru fasulye", "simit", "börek", "köfte"],
    "time": ["sekiz", "dokuz", "on", "öğlen", "akşam altı", "gece bir", "gece iki"],
    "feel": ["umarım olur", "bakalım", "iyi geldi", "çok yorucuydu", "keyifliydi", "pişman değilim"],
}
_CLOSE = ["", "", "", " neyse", " bakalım", " ne diyeyim", " off", " hadi hayırlısı", " çok iyi",
          " kim var", " değil mi", " ama olsun"]
_SIGNATURES = ["kanka", "hocam", "yaa", "aga", "abi", "lan", "valla", "resmen", "harbiden", "aynen",
               "bence", "galiba", "ciddi ciddi", "of of", "hıh", "dostlar", "millet", "ahah", "sjsj", "jsjs"]
_EMO = ["", "", "", " 😅", " 🙂", " 😂", " ☕", " 🙏", " 😴", " ✨"]


def _slug(text: str) -> str:
    tr = str.maketrans("çğıöşüÇĞİÖŞÜâ", "cgiosuCGIOSUa")
    return re.sub(r"[^a-z0-9]", "", text.translate(tr).lower())


@dataclass
class Account:
    id: int
    handle: str
    created_day: float           # pencere başlangıcına göre gün (negatif = önce açılmış)
    sealed: bool                 # PoP ile mühürlü mü
    department: str
    dorm: str | None
    clubs: list[int]
    kind: str = "normal"         # normal | bot | bought | paid
    scenario: int | None = None


@dataclass
class Post:
    id: int
    account: int
    t: float                     # dakika (pencere başlangıcından)
    text: str
    scenario: int | None = None


@dataclass
class Event:
    id: str
    name: str
    club: int | None
    t: float                     # bitiş zamanı (dakika)
    attendees: set[int] = field(default_factory=set)


@dataclass
class Scenario:
    id: int
    type: str
    label: int                   # 0 masum, 1 koordineli
    members: list[int]
    t0: float
    note: str = ""


@dataclass
class Campus:
    seed: int
    accounts: list[Account]
    posts: list[Post]
    follows: set[tuple[int, int]]
    events: list[Event]
    scenarios: list[Scenario]

    def account(self, i: int) -> Account:
        return self.accounts[i]


BENIGN_TYPES = ["event_crowd", "club_announce", "dorm_friends", "exam_night"]
COORD_TYPES = ["bot_network", "bought_accounts", "paid_humans", "slow_campaign"]
# Yalnız sağlamlık testinde kullanılan, eğitimde HİÇ görülmeyen saldırı türü:
ADVERSARIAL_TYPES = ["camouflaged_campaign"]


class _Gen:
    def __init__(self, seed: int, n_students: int):
        self.r = random.Random(seed)
        self.seed = seed
        self.accounts: list[Account] = []
        self.posts: list[Post] = []
        self.follows: set[tuple[int, int]] = set()
        self.events: list[Event] = []
        self.scenarios: list[Scenario] = []
        self.n_students = n_students
        self._handles: set[str] = set()

    # ---------- yardımcılar ----------
    def handle(self, style: str = "student") -> str:
        r = self.r
        while True:
            if style == "bot":
                h = f"{r.choice(['user', 'kampus', 'ogrenci', 'genc', 'haber'])}{r.randint(1000, 99999)}"
            else:
                h = f"{r.choice(_NAMES)}{r.choice(['', '_', '.'])}{r.choice(_NAMES)[:r.randint(2, 5)]}{r.randint(0, 99)}"
            if h not in self._handles:
                self._handles.add(h)
                return h

    def add_account(self, **kw) -> Account:
        a = Account(id=len(self.accounts), **kw)
        self.accounts.append(a)
        return a

    def post(self, acc: int, t: float, text: str, scenario: int | None = None):
        if 0 <= t < WINDOW_DAYS * DAY:
            self.posts.append(Post(len(self.posts), acc, t, text, scenario))

    def daytime(self, day: int) -> float:
        """Gündüz/akşam ağırlıklı bir paylaşım saati."""
        hour = min(23.9, max(7.0, self.r.gauss(16, 4)))
        return day * DAY + hour * 60 + self.r.random() * 60

    def daily_text(self, a: Account) -> str:
        r = self.r
        topic = r.choice(_TOPIC).format(course=r.choice(COURSES), dorm=a.dorm or r.choice(DORMS),
                                        **{k: r.choice(v) for k, v in _FILL.items()})
        return self.personalize(a, r.choice(_OPEN) + topic + r.choice(_CLOSE)) + r.choice(_EMO)

    def personalize(self, a: Account, text: str) -> str:
        """Kişisel yazım: kelime atlama, küçük yazım hataları, kişiye özgü kapanış."""
        r = self.r
        words = []
        for w in text.split():
            x = r.random()
            if x < 0.08 and len(words) > 1:
                continue
            if x < 0.14 and len(w) > 4:
                i = r.randrange(1, len(w) - 1)
                w = w[:i] + w[i + 1:]
            words.append(w)
        sig = _SIGNATURES[a.id % len(_SIGNATURES)]
        if r.random() < 0.35:
            words.append(sig)
        return " ".join(words)

    # ---------- normal öğrenciler ----------
    def students(self):
        r = self.r
        for _ in range(self.n_students):
            clubs = r.sample(range(len(CLUBS)), k=r.choice([0, 0, 1, 1, 1, 2, 2, 3]))
            self.add_account(handle=self.handle(), created_day=-r.uniform(30, 1500),
                             sealed=r.random() < 0.7, department=r.choice(DEPARTMENTS),
                             dorm=r.choice(DORMS) if r.random() < 0.55 else None, clubs=clubs)
        ids = [a.id for a in self.accounts]
        for a in self.accounts:
            for b in ids:
                if a.id == b:
                    continue
                o = self.accounts[b]
                p = 0.002
                if set(a.clubs) & set(o.clubs):
                    p += 0.06
                if a.dorm and a.dorm == o.dorm:
                    p += 0.03
                if a.department == o.department:
                    p += 0.02
                if r.random() < p:
                    self.follows.add((a.id, b))
                    if r.random() < 0.6:
                        self.follows.add((b, a.id))
        for a in self.accounts:
            rate = r.lognormvariate(-0.4, 0.7)        # gün başına paylaşım
            for d in range(WINDOW_DAYS):
                for _ in range(self._poisson(rate)):
                    self.post(a.id, self.daytime(d), self.daily_text(a))

    def _poisson(self, lam: float) -> int:
        L, k, p = pow(2.718281828, -lam), 0, 1.0
        while True:
            p *= self.r.random()
            if p <= L:
                return k
            k += 1

    def pick_students(self, n: int, where=None) -> list[int]:
        pool = [a.id for a in self.accounts[: self.n_students] if (where is None or where(a))]
        return self.r.sample(pool, k=min(n, len(pool)))

    def new_scenario(self, typ: str, members: list[int], t0: float, note: str = "") -> Scenario:
        s = Scenario(len(self.scenarios), typ, 1 if typ in COORD_TYPES else 0, members, t0, note)
        self.scenarios.append(s)
        return s

    # ---------- masum senaryolar ----------
    def event_crowd(self):
        r = self.r
        club = r.randrange(len(CLUBS))
        name = f"{r.choice(EVENT_NAMES)} {2026 + r.randint(0, 1)}"
        t_end = r.randint(1, WINDOW_DAYS - 2) * DAY + r.uniform(17, 21) * 60
        ev = Event(f"ev-{self.seed}-{len(self.events)}", name, club, t_end)
        attendees = self.pick_students(r.randint(40, 120))
        ev.attendees.update(attendees)
        self.events.append(ev)
        posters = r.sample(attendees, k=max(6, int(len(attendees) * r.uniform(0.25, 0.6))))
        s = self.new_scenario("event_crowd", posters, t_end, name)
        tpl = ["{e} harikaydı, emeği geçen herkese teşekkürler", "{e} bitti ama enerjisi hâlâ üstümde",
               "bugün {e} etkinliğindeydik, {d}", "{e} için gerçekten çok güzel bir organizasyondu",
               "{e} etkinliğinden döndüm, {d}", "{e} gibi etkinlikler daha sık olmalı", "{e} çok iyiydi {d}"]
        det = ["konuşmacılar çok iyiydi", "salon tıklım tıklımdı", "yeni insanlarla tanıştım",
               "çok şey öğrendim", "atmosfer müthişti", "sunumlar çok kaliteliydi", "fotoğraflar yakında"]
        tag = "#" + _slug(name)
        tag_p = r.choice([0.0, 0.5, 0.8, 0.9])     # çoğu etkinlikte etiket yaygın
        for a in posters:
            txt = r.choice(tpl).format(e=name, d=r.choice(det))
            if r.random() < tag_p:
                txt += " " + tag
            self.post(a, t_end + r.expovariate(1 / 50), txt + r.choice(_EMO), s.id)

    def club_announce(self):
        r = self.r
        club = r.randrange(len(CLUBS))
        members = [a.id for a in self.accounts[: self.n_students] if club in a.clubs]
        if len(members) < 8:
            members += self.pick_students(10)
            for m in members:
                if club not in self.accounts[m].clubs:
                    self.accounts[m].clubs.append(club)
        t0 = r.randint(0, WINDOW_DAYS - 1) * DAY + r.uniform(10, 18) * 60
        when = r.choice(["Salı 18:00", "Çarşamba 17:30", "Perşembe 19:00", "Cuma 16:00"])
        where = r.choice(["B blok 204", "Kültür Merkezi", "Mühendislik amfisi", "Kütüphane seminer salonu"])
        text = f"📢 {CLUBS[club]} tanışma toplantısı {when}, {where}. Herkesi bekleriz!"
        if r.random() < 0.75:
            text += " #" + _slug(CLUBS[club].split()[0])
        sharers = r.sample(members, k=max(6, int(len(members) * r.uniform(0.4, 0.8))))
        s = self.new_scenario("club_announce", sharers, t0, CLUBS[club])
        for a in sharers:
            variant = text if r.random() < 0.7 else r.choice(["RT ", "", "Kaçırmayın! "]) + text + r.choice(["", " 🙌", " 🎉"])
            self.post(a, t0 + r.expovariate(1 / 70), variant, s.id)

    def dorm_friends(self):
        r = self.r
        dorm = r.choice(DORMS)
        group = self.pick_students(r.randint(8, 16), where=lambda a: a.dorm == dorm)
        for a in group:
            for b in group:
                if a != b and r.random() < 0.7:
                    self.follows.add((a, b))
        t0 = r.randint(0, WINDOW_DAYS - 1) * DAY + r.uniform(19, 22) * 60
        s = self.new_scenario("dorm_friends", group, t0, f"{dorm} yurdu")
        tpl = [f"{dorm} yurdunda internet yine gitti", f"{dorm} yurdunda internet yine yok, ödev nasıl yetişecek",
               "yurtta internet gitti yine", f"{dorm} yurdu internet kesintisi rekor kırdı",
               "internet yok yurtta bu kaçıncı", f"{dorm}'da internet yine gitti arkadaşlar"]
        for a in group:
            self.post(a, t0 + r.expovariate(1 / 40), r.choice(tpl) + r.choice(_EMO), s.id)

    def exam_night(self):
        r = self.r
        course = r.choice(COURSES)
        dept = r.choice(DEPARTMENTS)
        group = self.pick_students(r.randint(25, 60), where=lambda a: a.department == dept or r.random() < 0.15)
        t0 = r.randint(1, WINDOW_DAYS - 1) * DAY + 21 * 60
        s = self.new_scenario("exam_night", group, t0, course)
        tpl = ["yarın {c} finali var hâlâ hiçbir şey bilmiyorum", "{c} çalışırken sabahladım",
               "{c} finali için dua edin", "{c} soruları çıkmış mı bilen var", "{c} bitmiyor arkadaşlar",
               "gece 3 oldu hâlâ {c}", "{c} hocası bu sefer zor sorar mı"]
        tag_p = r.choice([0.0, 0.4, 0.7])
        for a in group:
            for _ in range(r.choice([1, 1, 2])):
                txt = r.choice(tpl).format(c=course)
                if r.random() < tag_p:
                    txt += r.choice([" #finalhaftasi", " #" + _slug(course)])
                self.post(a, t0 + r.uniform(0, 6 * 60), txt + r.choice(_EMO), s.id)

    # ---------- koordineli senaryolar ----------
    def _campaign_texts(self):
        """
        Kampanya metinleri. Kampanyaların bir kısmı hashtag KULLANMAZ: aksi halde model
        "hashtag varsa kampanyadır" kestirmesini öğrenirdi (gerçekte böyle değil).
        """
        name, tag, base = self.r.choice(CAMPAIGNS)
        h = f" #{tag}" if self.r.random() < 0.65 else ""
        core = base.format(x=name) + h
        paraphrases = [
            core,
            f"Bence {name} gerçekten en iyisi, siz de görün{h}",
            f"{name} konusunda sessiz kalmayın, herkes paylaşsın{h}",
            f"Arkadaşlar {name} meselesi önemli, yaymamız lazım{h}",
            f"Kampüste herkes {name} diyor, haklılar{h}",
            f"{name} için ses çıkarma zamanı!{h}",
        ]
        return name, tag, core, paraphrases

    def bot_network(self):
        r = self.r
        n = r.randint(12, 35)
        born = -r.uniform(0, 20)
        ids = []
        for _ in range(n):
            a = self.add_account(handle=self.handle("bot"), created_day=born + r.uniform(0, 2),
                                 sealed=False, department=r.choice(DEPARTMENTS), dorm=None,
                                 clubs=[], kind="bot")
            ids.append(a.id)
        for a in ids:
            for b in ids:
                if a != b and r.random() < 0.45:
                    self.follows.add((a, b))
            for v in self.pick_students(r.randint(1, 4)):   # kamuflaj
                self.follows.add((a, v))
        name, tag, core, _ = self._campaign_texts()
        t0 = r.randint(0, WINDOW_DAYS - 1) * DAY + r.uniform(8, 23) * 60
        s = self.new_scenario("bot_network", ids, t0, name)
        for a in ids:
            self.accounts[a].scenario = s.id
            for _ in range(r.choice([1, 1, 2, 3])):
                txt = core + r.choice(["", " 🔥", " !!", " 💯", " 👇"])
                self.post(a, t0 + r.expovariate(1 / 6), txt, s.id)

    def bought_accounts(self):
        r = self.r
        n = r.randint(8, 20)
        ids = []
        for _ in range(n):
            a = self.add_account(handle=self.handle(), created_day=-r.uniform(300, 1500),
                                 sealed=r.random() < 0.15, department=r.choice(DEPARTMENTS),
                                 dorm=None, clubs=[], kind="bought")
            ids.append(a.id)
            for d in range(WINDOW_DAYS):                      # neredeyse sessiz geçmiş
                if r.random() < 0.04:
                    self.post(a.id, self.daytime(d), self.daily_text(a))
            for v in self.pick_students(r.randint(5, 25)):
                self.follows.add((v, a.id))
        name, tag, core, para = self._campaign_texts()
        t0 = r.randint(0, WINDOW_DAYS - 1) * DAY + r.uniform(9, 22) * 60
        s = self.new_scenario("bought_accounts", ids, t0, name)
        for a in ids:
            self.accounts[a].scenario = s.id
            txt = core if r.random() < 0.6 else r.choice(para)
            self.post(a, t0 + r.expovariate(1 / 15), txt + r.choice(["", " 👍", " 🔥"]), s.id)

    def paid_humans(self):
        r = self.r
        ids = self.pick_students(r.randint(8, 18), where=lambda a: a.sealed and a.kind == "normal")
        name, tag, core, para = self._campaign_texts()
        t0 = r.randint(0, WINDOW_DAYS - 1) * DAY + r.uniform(10, 22) * 60
        s = self.new_scenario("paid_humans", ids, t0, name)
        for a in ids:
            self.accounts[a].kind = "paid"
            self.accounts[a].scenario = s.id
            self.post(a, t0 + r.expovariate(1 / 30), r.choice(para) + r.choice(_EMO), s.id)

    def slow_campaign(self):
        r = self.r
        n = r.randint(10, 24)
        ids = []
        for i in range(n):
            if r.random() < 0.5:
                a = self.add_account(handle=self.handle("bot"), created_day=-r.uniform(0, 60),
                                     sealed=False, department=r.choice(DEPARTMENTS), dorm=None,
                                     clubs=[], kind="bot")
            else:
                a = self.add_account(handle=self.handle(), created_day=-r.uniform(200, 1200),
                                     sealed=r.random() < 0.2, department=r.choice(DEPARTMENTS),
                                     dorm=None, clubs=[], kind="bought")
            ids.append(a.id)
            for d in range(WINDOW_DAYS):
                if r.random() < 0.15:
                    self.post(a.id, self.daytime(d), self.daily_text(a))
        for a in ids:
            for b in ids:
                if a != b and r.random() < 0.12:
                    self.follows.add((a, b))
        name, tag, core, para = self._campaign_texts()
        t0 = r.randint(0, WINDOW_DAYS - 4) * DAY + r.uniform(9, 12) * 60
        s = self.new_scenario("slow_campaign", ids, t0, name)
        for a in ids:
            self.accounts[a].scenario = s.id
            for _ in range(r.choice([1, 2])):
                self.post(a, t0 + r.uniform(0, 72 * 60), r.choice(para) + r.choice(_EMO), s.id)

    def camouflaged_campaign(self):
        """
        SALDIRI (yalnız test): kampanya gerçek bir etkinliğin hemen ardından, o
        etkinliğe GERÇEKTEN katılmış (PoA kanıtlı) mühürlü öğrencilere yaptırılır.
        Modelin "ortak etkinlik riski azaltır" kuralını istismar eder.
        """
        r = self.r
        if not self.events:
            self.event_crowd()
        ev = r.choice(self.events)
        pool = [a for a in ev.attendees if self.accounts[a].sealed and self.accounts[a].kind == "normal"]
        ids = r.sample(pool, k=min(len(pool), r.randint(8, 16)))
        name, tag, core, para = self._campaign_texts()
        t0 = ev.t + r.uniform(20, 180)
        s = Scenario(len(self.scenarios), "camouflaged_campaign", 1, ids, t0, name)
        self.scenarios.append(s)
        for a in ids:
            self.accounts[a].kind = "paid"
            self.accounts[a].scenario = s.id
            self.post(a, t0 + r.expovariate(1 / 30), r.choice(para) + r.choice(_EMO), s.id)


def generate(seed: int = 7, n_students: int = 500,
             benign: dict[str, int] | None = None, coordinated: dict[str, int] | None = None) -> Campus:
    """Bir kampüs dünyası üretir. Senaryo sayıları değiştirilebilir."""
    benign = benign or {"event_crowd": 3, "club_announce": 3, "dorm_friends": 2, "exam_night": 2}
    coordinated = coordinated or {"bot_network": 2, "bought_accounts": 2, "paid_humans": 2,
                                  "slow_campaign": 1}
    g = _Gen(seed, n_students)
    g.students()
    for typ, k in {**benign, **coordinated}.items():
        for _ in range(k):
            getattr(g, typ)()
    g.posts.sort(key=lambda p: p.t)
    for i, p in enumerate(g.posts):
        p.id = i
    return Campus(seed, g.accounts, g.posts, g.follows, g.events, g.scenarios)
