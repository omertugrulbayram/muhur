"""
Koordineli davranış tespiti — açıklanabilir küme modeli.

Neden hesap değil KÜME?
    Koordinasyon tek bir hesabın özelliği değildir; birden fazla hesabın birlikte
    yaptığı bir şeydir. Bu yüzden önce "kısa sürede birbirine çok benzeyen şeyler
    paylaşan hesap grupları" (aday kümeler) bulunur, sonra her küme bir bütün
    olarak değerlendirilir.

Neden PoP durumu modelde YOK?
    Gerçek insan olmak koordinasyon olmadığını kanıtlamaz; mühürsüz olmak da
    koordinasyon kanıtı değildir. PoP, güven puanında ayrı bir eksendir. Modele
    girseydi mühürsüz kullanıcılar sırf bu yüzden daha riskli görünebilirdi.
    PoP oranı yalnız açıklamada bağlam olarak gösterilir.

Neden lojistik regresyon?
    Her özelliğin risk puanına katkısı tam olarak hesaplanabilir (katsayı × değer).
    Böylece her uyarının "neden"i modelin kendisinden okunur; sonradan uydurulmuş
    bir açıklama değildir. Gradient Boosting yalnız karşılaştırma için raporlanır.

Akış
    1. Metinler karakter n-gram TF-IDF ile vektörlenir.
    2. Zaman pencereleri içinde, farklı hesaplara ait ve benzerliği eşiği geçen
       paylaşımlar hesapları birbirine bağlar.
    3. Bağlı bileşenler (en az MIN_CLUSTER hesap) aday kümedir.
    4. Her küme için açıklanabilir özellikler hesaplanır.
    5. Model risk olasılığı verir; katkılar insan-okunur gerekçelere çevrilir.
       Olası MASUM açıklamalar (ortak etkinlik, ortak kulüp) ayrıca gösterilir.

Model asla "bu hesap bottur" demez. Çıktı bir İNCELEME ÖNERİSİDİR; son karar
topluluk yöneticisinindir.
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from app.ml.campus import CLUBS, DAY, Campus, _slug

MODEL_PATH = Path(__file__).resolve().parent / "models" / "coordination_lr.json"

SIM_THRESHOLD = 0.65        # iki paylaşımın "benzer" sayılması için kosinüs eşiği
WINDOW_MIN = 12 * 60        # pencere genişliği
STEP_MIN = 6 * 60           # pencere kayması (yarı örtüşme)
MAX_GAP_MIN = 6 * 60        # iki benzer paylaşım arasındaki en fazla süre
TAG_GAP_MIN = 12 * 60       # aynı hashtag'i kullanan iki paylaşım arasındaki en fazla süre
MIN_CLUSTER = 6

FEATURES = [
    "log_size",            # küme büyüklüğü
    "mean_similarity",     # paylaşımların ortalama benzerliği
    "exact_dup_frac",      # birebir aynı metin oranı
    "log_span_hours",      # ilk ve son paylaşım arası süre
    "new_account_frac",    # son 30 günde açılmış hesap oranı
    "creation_spread",     # hesap açılış tarihlerinin yayılımı (log gün)
    "dormant_frac",        # önceden neredeyse hiç paylaşmayan hesap oranı
    "follow_density",      # küme içi takip yoğunluğu
    "hashtag_link_rate",   # hashtag/link oranı
    "shared_event_frac",   # aynı etkinliğe katılanlar (PoA) × paylaşımların etkinliği anma oranı
    "shared_club_frac",    # aynı kulübün üyeleri × paylaşımların kulübü anma oranı
    "shared_dept_frac",    # aynı bölümden olanlar
]

FEATURE_LABELS_TR = {
    "log_size": "küme büyüklüğü",
    "mean_similarity": "mesaj benzerliği",
    "exact_dup_frac": "birebir aynı metin",
    "log_span_hours": "zamana yayılma",
    "new_account_frac": "yeni hesap oranı",
    "creation_spread": "açılış tarihi yayılımı",
    "dormant_frac": "sessizken birden aktifleşme",
    "follow_density": "karşılıklı takip yoğunluğu",
    "hashtag_link_rate": "hashtag/link yoğunluğu",
    "shared_event_frac": "içerikle tutarlı ortak etkinlik (PoA)",
    "shared_club_frac": "içerikle tutarlı ortak kulüp",
    "shared_dept_frac": "aynı bölüm",
}

CONTEXT_FEATURES = {"shared_event_frac", "shared_club_frac", "shared_dept_frac"}

_HASHTAG_RE = re.compile(r"#\w+")
_TAG_RE = re.compile(r"#\w+|https?://|bit\.ly|linke")


def _norm(text: str) -> str:
    return re.sub(r"[^\w#]+", " ", text.lower()).strip()


# ---------------------------------------------------------------- kümeleme
def candidate_clusters(campus: Campus) -> list[dict]:
    posts = campus.posts
    if not posts:
        return []
    texts = [_norm(p.text) for p in posts]
    # Kelime düzeyinde (1-2 gram): nadir ve içerik taşıyan kelimeler (kampanya adı,
    # hashtag, etkinlik adı) ağır basar; "bugün", "arkadaşlar" gibi sık kelimeler hafif kalır.
    vec = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), min_df=2, sublinear_tf=True,
                          token_pattern=r"(?u)#?\w\w+")
    X = vec.fit_transform(texts)
    times = np.array([p.t for p in posts])
    accs = np.array([p.account for p in posts])

    # Birleştirme PAYLAŞIM düzeyinde yapılır: iki paylaşım benzer ve zamanca yakınsa
    # aynı "içerik dalgasına" aittir. (Hesap düzeyinde birleştirmek, tek bir benzer
    # cümle yüzünden ilgisiz grupları zincirleme birleştirirdi.)
    parent = list(range(len(posts)))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    links: list[tuple[int, int, float]] = []
    seen: set[tuple[int, int]] = set()
    t_end = times.max()
    start = 0.0
    while start <= t_end:
        idx = np.where((times >= start) & (times < start + WINDOW_MIN))[0]
        if len(idx) > 1:
            S = (X[idx] @ X[idx].T).tocoo()
            for i, j, v in zip(S.row, S.col, S.data):
                if i >= j or v < SIM_THRESHOLD:
                    continue
                pi, pj = int(idx[i]), int(idx[j])
                if accs[pi] == accs[pj] or abs(times[pi] - times[pj]) > MAX_GAP_MIN:
                    continue
                if (pi, pj) in seen:
                    continue
                seen.add((pi, pj))
                links.append((pi, pj, float(v)))
                ra, rb = find(pi), find(pj)
                if ra != rb:
                    parent[ra] = rb
        start += STEP_MIN

    # Ortak hashtag: aynı etiketi kısa aralıklarla kullanan paylaşımlar da bağlanır.
    # (Farklı cümlelerle yazılmış ücretli kampanyalar metin benzerliğiyle yakalanmaz.)
    by_tag: dict[str, list[int]] = defaultdict(list)
    for i, p in enumerate(posts):
        for tag in set(_HASHTAG_RE.findall(p.text.lower())):
            by_tag[tag].append(i)
    for tag, idxs in by_tag.items():
        idxs.sort(key=lambda i: times[i])
        for a_, b_ in zip(idxs, idxs[1:]):
            if accs[a_] == accs[b_] or times[b_] - times[a_] > TAG_GAP_MIN:
                continue
            key = (min(a_, b_), max(a_, b_))
            if key in seen:
                continue
            seen.add(key)
            links.append((key[0], key[1], float(X[a_].multiply(X[b_]).sum())))
            ra, rb = find(a_), find(b_)
            if ra != rb:
                parent[ra] = rb

    comp_links: dict[int, list[tuple[int, int, float]]] = defaultdict(list)
    for pi, pj, v in links:
        comp_links[find(pi)].append((pi, pj, v))

    clusters = []
    for root, cl_links in comp_links.items():
        pids = sorted({p for pi, pj, _ in cl_links for p in (pi, pj)})
        members = sorted({int(accs[p]) for p in pids})
        if len(members) < MIN_CLUSTER:
            continue
        clusters.append({"members": members, "post_ids": pids, "links": cl_links})
    clusters.sort(key=lambda c: -len(c["members"]))
    return clusters


# ---------------------------------------------------------------- özellikler
def cluster_features(campus: Campus, cl: dict) -> tuple[dict, dict]:
    """(özellik vektörü, açıklama için ham bağlam) döner."""
    members = cl["members"]
    mset = set(members)
    n = len(members)
    posts = [campus.posts[i] for i in cl["post_ids"]]
    t0 = min(p.t for p in posts)
    t1 = max(p.t for p in posts)
    sims = [v for _, _, v in cl["links"]]
    normed = Counter(_norm(p.text) for p in posts)
    exact = sum(c for c in normed.values() if c > 1) / max(1, len(posts))

    accs = [campus.accounts[m] for m in members]
    created = [a.created_day for a in accs]
    new_frac = sum(1 for c in created if c > -30) / n
    spread = math.log1p(float(np.std(created)))
    sealed = sum(1 for a in accs if a.sealed) / n

    # önceki aktivite: kümeye giren paylaşımlar dışında, kümeden önceki günlük paylaşım
    cluster_pids = set(cl["post_ids"])
    prior = Counter()
    for p in campus.posts:
        if p.account in mset and p.id not in cluster_pids and p.t < t0:
            prior[p.account] += 1
    days_before = max(1.0, t0 / DAY)
    dormant = sum(1 for m in members if prior[m] / days_before < 0.15) / n

    internal = sum(1 for (a, b) in campus.follows if a in mset and b in mset)
    density = internal / max(1, n * (n - 1))
    tag_rate = sum(1 for p in posts if _TAG_RE.search(p.text.lower())) / len(posts)

    best_event, best_event_frac = None, 0.0
    for ev in campus.events:
        if t0 - DAY <= ev.t <= t1:
            f = len(ev.attendees & mset) / n
            if f > best_event_frac:
                best_event, best_event_frac = ev, f
    club_counts = Counter(c for a in accs for c in a.clubs)
    best_club, club_n = (club_counts.most_common(1)[0] if club_counts else (None, 0))
    club_frac = club_n / n
    dept, dept_n = Counter(a.department for a in accs).most_common(1)[0]
    dept_frac = dept_n / n

    # Bağlam ancak İÇERİKLE TUTARLIYSA riski düşürür: ortak bir etkinliğe katılmış
    # olmak, paylaşımlar o etkinlikten bahsediyorsa masum bir açıklamadır. Etkinlikten
    # hiç bahsetmeyen bir kampanyayı etkinlik katılımcılarına yaptırmak ("kamufle
    # saldırı") böylece bağlamın arkasına saklanamaz.
    slugs = [_slug(p.text) for p in posts]
    event_mention = club_mention = 0.0
    if best_event is not None:
        keys = [_slug(w) for w in best_event.name.split() if not w.isdigit()]
        event_mention = sum(all(k in sp for k in keys) for sp in slugs) / len(slugs)
    if best_club is not None:
        key = _slug(CLUBS[best_club].split()[0])
        club_mention = sum(key in sp for sp in slugs) / len(slugs)

    feats = {
        "log_size": math.log(n),
        "mean_similarity": float(np.mean(sims)) if sims else 0.0,
        "exact_dup_frac": exact,
        "log_span_hours": math.log1p((t1 - t0) / 60),
        "new_account_frac": new_frac,
        "creation_spread": spread,
        "dormant_frac": dormant,
        "follow_density": density,
        "hashtag_link_rate": tag_rate,
        "shared_event_frac": best_event_frac * event_mention,
        "shared_club_frac": club_frac * club_mention,
        "shared_dept_frac": dept_frac,
    }
    ctx = {
        "n": n, "n_posts": len(posts), "t0": t0, "t1": t1, "sealed_frac": sealed,
        "span_min": t1 - t0, "creation_range_days": max(created) - min(created),
        "event": None if best_event is None else {"id": best_event.id, "name": best_event.name},
        "club": None if best_club is None else CLUBS[best_club],
        "department": dept,
        "raw_event_frac": best_event_frac, "event_mention_frac": event_mention,
        "raw_club_frac": club_frac, "club_mention_frac": club_mention,
        "sample_texts": [t for t, _ in normed.most_common(3)],
    }
    return feats, ctx


def label_of(campus: Campus, members: list[int]) -> tuple[int, str, float]:
    """Kümenin gerçek etiketi (yalnız eğitim/değerlendirme için): çoğunluk senaryosu."""
    sc = Counter()
    by_post = defaultdict(set)
    for p in campus.posts:
        if p.scenario is not None:
            by_post[p.scenario].add(p.account)
    for s in campus.scenarios:
        overlap = len(by_post[s.id] & set(members))
        if overlap:
            sc[s.id] += overlap
    if not sc:
        return 0, "organic", 1.0
    sid, cnt = sc.most_common(1)[0]
    s = campus.scenarios[sid]
    return s.label, s.type, cnt / len(members)


# ---------------------------------------------------------------- model
class CoordinationModel:
    """Standartlaştırılmış özellikler üzerinde lojistik regresyon (JSON'dan yüklenir)."""

    def __init__(self, coef, intercept, mean, std, version="lr-v1", meta=None):
        self.coef = np.array(coef, dtype=float)
        self.intercept = float(intercept)
        self.mean = np.array(mean, dtype=float)
        self.std = np.array(std, dtype=float)
        self.version = version
        self.meta = meta or {}

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> "CoordinationModel":
        d = json.loads(Path(path).read_text(encoding="utf-8"))
        assert d["features"] == FEATURES, "model özellik listesi uyuşmuyor"
        return cls(d["coef"], d["intercept"], d["mean"], d["std"], d["version"], d.get("meta"))

    def save(self, path: Path = MODEL_PATH) -> None:
        path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({
            "version": self.version, "features": FEATURES,
            "coef": self.coef.round(6).tolist(), "intercept": round(self.intercept, 6),
            "mean": self.mean.round(6).tolist(), "std": self.std.round(6).tolist(),
            "meta": self.meta,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    def _z(self, feats: dict) -> np.ndarray:
        x = np.array([feats[f] for f in FEATURES], dtype=float)
        return (x - self.mean) / self.std

    def predict(self, feats: dict) -> float:
        logit = float(self._z(feats) @ self.coef + self.intercept)
        return 1.0 / (1.0 + math.exp(-logit))

    def _reference(self) -> np.ndarray:
        """
        Katkıların ölçüldüğü referans nokta. Normal özelliklerde ortalama küme;
        BAĞLAM özelliklerinde (ortak etkinlik/kulüp/bölüm) "hiç bağlam yok" = 0.
        Böylece bağlam yalnız riski AZALTAN bir gerekçe olarak görünür; "kimse aynı
        kulüpte değil" diye bir şüphe nedeni yazılmaz. Olasılık değişmez: aradaki
        fark sabit terime (base) aktarılır.
        """
        ref = self.mean.copy()
        for i, f in enumerate(FEATURES):
            if f in CONTEXT_FEATURES:
                ref[i] = 0.0
        return ref

    def base_logit(self) -> float:
        return float(self.intercept + ((self._reference() - self.mean) / self.std) @ self.coef)

    def contributions(self, feats: dict) -> dict[str, float]:
        """Her özelliğin logit'e katkısı, referans noktaya göre (pozitif = riski artırır)."""
        x = np.array([feats[f] for f in FEATURES], dtype=float)
        c = (x - self._reference()) / self.std * self.coef
        return {f: float(v) for f, v in zip(FEATURES, c)}


# ---------------------------------------------------------------- açıklama
def _dur(minutes: float) -> str:
    if minutes < 90:
        return f"{max(1, round(minutes))} dakika"
    if minutes < 48 * 60:
        return f"{round(minutes / 60)} saat"
    return f"{round(minutes / DAY)} gün"


def _part(x: float, n: int) -> str:
    """'%88 (7/8 hesap)' — Türkçe ek gerektirmeyen oran yazımı."""
    return f"%{round(100 * x)} ({round(x * n)}/{n} hesap)"


def explain(feats: dict, ctx: dict, contrib: dict[str, float]) -> dict:
    """
    Model katkılarını insan-okunur cümlelere çevirir.

    Cümleler TARAFSIZDIR: yalnız ölçülen değeri söyler. Bir özelliğin riski
    artırdığı ya da azalttığı bilgisi cümleden değil, modelin katkısından gelir
    (signals = artıranlar, mitigating = azaltanlar). Böylece açıklama hiçbir zaman
    veriyle çelişmez.

    Döner: {signals, mitigating, innocent_explanations, caveat}
    """
    n = ctx["n"]
    fact = {
        "log_size": f"Kümede {n} hesap var.",
        "mean_similarity": f"Paylaşımların ortalama metin benzerliği: %{round(100 * feats['mean_similarity'])}.",
        "exact_dup_frac": f"Birebir aynı metin oranı: %{round(100 * feats['exact_dup_frac'])}.",
        "log_span_hours": f"Benzer paylaşımların tamamı {_dur(ctx['span_min'])} içinde yapıldı.",
        "new_account_frac": f"Son 30 günde açılmış hesap: {_part(feats['new_account_frac'], n)}.",
        "creation_spread": f"Hesapların açılış tarihleri arasındaki fark: {_dur(ctx['creation_range_days'] * DAY)}.",
        "dormant_frac": f"Daha önce neredeyse hiç paylaşım yapmamış hesap: {_part(feats['dormant_frac'], n)}.",
        "follow_density": f"Küme içi takip yoğunluğu: %{round(100 * feats['follow_density'])}.",
        "hashtag_link_rate": f"Hashtag veya link içeren paylaşım oranı: %{round(100 * feats['hashtag_link_rate'])}.",
        "shared_event_frac": (f"Ortak bir etkinliğe katılmış hesap: {_part(ctx['raw_event_frac'], n)}; "
                              f"paylaşımların %{round(100 * ctx['event_mention_frac'])} kadarı o etkinlikten bahsediyor."),
        "shared_club_frac": (f"Aynı kulübün üyesi olan hesap: {_part(ctx['raw_club_frac'], n)}; "
                             f"paylaşımların %{round(100 * ctx['club_mention_frac'])} kadarı kulüpten bahsediyor."),
        "shared_dept_frac": f"Aynı bölümden hesap: {_part(feats['shared_dept_frac'], n)}.",
    }

    def item(f, w):
        return {"feature": f, "label": FEATURE_LABELS_TR[f], "weight": round(w, 3), "text": fact[f]}

    signals = [item(f, w) for f, w in sorted(contrib.items(), key=lambda kv: -kv[1]) if w > 0.35][:4]
    mitigating = [item(f, w) for f, w in sorted(contrib.items(), key=lambda kv: kv[1]) if w < -0.35][:3]

    innocent = []
    cautions = []
    if ctx["event"] and feats["shared_event_frac"] >= 0.3:
        innocent.append(
            f"{_part(ctx['raw_event_frac'], n)} paylaşımdan önceki 24 saat içinde "
            f"\"{ctx['event']['name']}\" etkinliğine katılmış (PoA kanıtlı) ve paylaşımlar bu "
            "etkinlikten bahsediyor. Ortak bir etkinlik hakkında doğal paylaşım olabilir.")
    elif ctx["event"] and ctx["raw_event_frac"] >= 0.3:
        cautions.append(
            f"{_part(ctx['raw_event_frac'], n)} \"{ctx['event']['name']}\" etkinliğine katılmış, ama "
            f"paylaşımların yalnız %{round(100 * ctx['event_mention_frac'])} kadarı etkinlikten bahsediyor. "
            "Etkinlik bu paylaşımlar için masum bir açıklama sayılmadı.")
    if ctx["club"] and feats["shared_club_frac"] >= 0.4:
        innocent.append(
            f"{_part(ctx['raw_club_frac'], n)} {ctx['club']} üyesi ve paylaşımlar kulüpten bahsediyor. "
            "Bir kulüp duyurusunun paylaşılması olabilir.")
    if feats["shared_dept_frac"] >= 0.5:
        innocent.append(
            f"{_part(feats['shared_dept_frac'], n)} {ctx['department']} bölümünden. Aynı ders, sınav "
            "veya bölüm gündemi hakkında doğal paylaşım olabilir.")
    if ctx["sealed_frac"] >= 0.6:
        innocent.append(
            f"{_part(ctx['sealed_frac'], n)} kanıtlanmış gerçek insan (PoP). Bu, bot olmadıklarını "
            "gösterir; ama koordineli bir kampanya olmadığını tek başına kanıtlamaz.")
    if not innocent:
        innocent.append("Belirgin bir ortak bağlam (etkinlik, kulüp, bölüm) bulunamadı. Yine de ortak "
                        "bir gündem veya haber olabilir; içerik incelenmeli.")

    return {
        "signals": signals,
        "mitigating": mitigating,
        "innocent_explanations": innocent,
        "cautions": cautions,
        "pop_context": f"Mühürlü (PoP) hesap: {_part(ctx['sealed_frac'], n)}. PoP durumu risk "
                       "hesabına katılmaz.",
        "caveat": ("Bu bir uyarıdır, suçlama değildir. Model hiçbir hesabı bot ya da kötü niyetli "
                   "ilan etmez; son karar topluluk yöneticisinindir."),
    }


def risk_level(p: float) -> str:
    return "yüksek" if p >= 0.7 else "orta" if p >= 0.4 else "düşük"


def analyze(campus: Campus, model: CoordinationModel | None = None) -> list[dict]:
    """Bir kampüs için tüm aday kümeleri puanlar ve açıklar."""
    model = model or CoordinationModel.load()
    out = []
    for i, cl in enumerate(candidate_clusters(campus)):
        feats, ctx = cluster_features(campus, cl)
        p = model.predict(feats)
        contrib = model.contributions(feats)
        out.append({
            "cluster_index": i, "risk": round(p, 4), "level": risk_level(p),
            "members": cl["members"], "post_ids": cl["post_ids"],
            "links": [(int(a), int(b), round(v, 3)) for a, b, v in cl["links"]],
            "features": {k: round(v, 4) for k, v in feats.items()},
            "contributions": {k: round(v, 4) for k, v in contrib.items()},
            "context": ctx, "explanation": explain(feats, ctx, contrib),
            "model_version": model.version,
        })
    out.sort(key=lambda a: -a["risk"])
    return out
