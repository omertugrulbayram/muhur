"""
Analiz servisi — modeli ürüne bağlayan katman.

Demo kampüsü (sentetik, DEMO VERİ) koordinasyon modeliyle analiz eder:
  1. Aday kümeler bulunur ve puanlanır (app/ml/coordination.py).
  2. Her küme bir UYARI olarak veritabanına yazılır. Daha önce incelenmiş
     uyarıların durumu ve inceleme geçmişi korunur.
  3. Kümelerdeki hesaplar için risk kaydı yazılır (kaynak: "model"). Böylece
     güven puanı (/trust/score) artık elle girilmiş değil, modelin ürettiği
     risk değerini kullanır.

Kampüs hesapları, PoP takma kimliğine şu demo kimliğiyle bağlanır:
    demo_national_id(seed, account_id) = "demo-kampus-<seed>-<id>"
Bu, gerçek bir TC numarası değildir; yalnız demo hesapların mühürlenmesi içindir.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.db import store
from app.ml.campus import DAY, Campus, generate
from app.ml.coordination import FEATURES, MODEL_PATH, CoordinationModel, analyze, label_of
from app.pop.issuer import pseudonymous_subject

DEMO_SEED = 2026
DEMO_ORGANIZER = "demo-kulup"
EVAL_PATH = Path(MODEL_PATH).with_name("coordination_eval.json")
ROBUST_PATH = Path(MODEL_PATH).with_name("robustness.json")
SCENARIO_TR = {
    "event_crowd": "Etkinlik sonrası ortak paylaşım (masum)",
    "club_announce": "Kulüp duyurusunun paylaşılması (masum)",
    "dorm_friends": "Yurt arkadaşları aynı konuda (masum)",
    "exam_night": "Sınav gecesi paylaşımları (masum)",
    "bot_network": "Bot ağı (koordineli)",
    "bought_accounts": "Satın alınmış / ele geçirilmiş hesaplar (koordineli)",
    "paid_humans": "Ücretli gerçek kişiler (koordineli)",
    "slow_campaign": "Yavaş, yayılmış kampanya (koordineli)",
    "organic": "Organik konuşma (senaryo yok)",
}


def demo_national_id(seed: int, account_id: int) -> str:
    return f"demo-kampus-{seed}-{account_id}"


@lru_cache(maxsize=4)
def campus(seed: int = DEMO_SEED) -> Campus:
    return generate(seed=seed)


@lru_cache(maxsize=1)
def model() -> CoordinationModel:
    return CoordinationModel.load()


@lru_cache(maxsize=4)
def _analysis(seed: int) -> tuple:
    """Kampüs ve model sabitken analiz sonucu da sabittir (deterministik)."""
    return tuple(analyze(campus(seed), model()))


def _fmt_time(t_min: float) -> str:
    day = int(t_min // DAY) + 1
    h = int((t_min % DAY) // 60)
    m = int(t_min % 60)
    return f"{day}. gün {h:02d}:{m:02d}"


def run_demo_analysis(seed: int = DEMO_SEED, organizer_id: str = DEMO_ORGANIZER) -> int:
    """Demo kampüsü analiz eder ve uyarıları yazar. Yazılan uyarı sayısını döner."""
    c = campus(seed)
    m = model()
    results = _analysis(seed)
    best_risk: dict[int, float] = {}
    alerts = []
    for r in results:
        y, typ, purity = label_of(c, r["members"])
        alerts.append({
            "id": f"{seed}-{r['cluster_index']:03d}", "risk": r["risk"], "level": r["level"],
            "model_version": r["model_version"],
            "data": {
                "campus_seed": seed,
                "size": len(r["members"]),
                "n_posts": len(r["post_ids"]),
                "span_min": r["context"]["span_min"],
                "first_post": _fmt_time(r["context"]["t0"]),
                "sample_texts": r["context"]["sample_texts"],
                "explanation": r["explanation"],
                "features": r["features"],
                "contributions": r["contributions"],
                "members": r["members"],
                "post_ids": r["post_ids"],
                "links": r["links"],
                # Yalnız DEMO/değerlendirme içindir: gerçek üründe bu bilgi yoktur.
                "demo_truth": {"scenario": typ, "label": y, "purity": round(purity, 2),
                               "description": SCENARIO_TR.get(typ, typ)},
            },
        })
        for a in r["members"]:
            best_risk[a] = max(best_risk.get(a, 0.0), r["risk"])

    risks = []
    for acc_id, p in best_risk.items():
        subject = pseudonymous_subject(demo_national_id(seed, acc_id))
        prev = store.latest_risk(subject)
        if prev and prev["source"] == "model" and abs(prev["probability"] - p) < 1e-6:
            continue
        risks.append({"subject": subject, "probability": p, "model_version": m.version,
                      "reasons": [f"Koordinasyon kümesi riski (model {m.version})"]})
    store.write_analysis(organizer_id, alerts, risks)
    return len(results)


# ---------------------------------------------------------------- panel görünümleri
def _account_view(c: Campus, acc_id: int, t0: float) -> dict:
    a = c.accounts[acc_id]
    attended = [ev.name for ev in c.events if acc_id in ev.attendees and t0 - DAY <= ev.t <= t0 + DAY]
    return {
        "id": acc_id, "handle": a.handle, "sealed": a.sealed,
        "account_age_days": round(-a.created_day), "is_new": a.created_day > -30,
        "department": a.department,
        "clubs": [c_ for c_ in a.clubs], "recent_events": attended,
    }


def alert_summary(row: dict) -> dict:
    d = row["data"]
    exp = d["explanation"]
    return {
        "id": row["id"], "risk": row["risk"], "level": row["level"], "status": row["status"],
        "model_version": row["model_version"], "size": d["size"], "n_posts": d["n_posts"],
        "span_min": d["span_min"], "first_post": d["first_post"],
        "sample_text": d["sample_texts"][0] if d["sample_texts"] else "",
        "top_signals": [s["text"] for s in exp["signals"][:2]],
        "innocent_explanations": exp["innocent_explanations"],
        "demo": True,
    }


def alert_detail(row: dict) -> dict:
    from app.ml.campus import CLUBS

    d = row["data"]
    c = campus(d["campus_seed"])
    members = d["members"]
    mset = set(members)
    posts = sorted((c.posts[i] for i in d["post_ids"]), key=lambda p: p.t)
    t0 = posts[0].t if posts else 0
    accounts = [_account_view(c, a, t0) for a in members]
    for acc in accounts:
        acc["clubs"] = [CLUBS[i] for i in acc["clubs"]]
    follow_edges = [[a, b] for (a, b) in c.follows if a in mset and b in mset]
    sim_edges: dict[tuple[int, int], float] = {}
    for pi, pj, v in d["links"]:
        a, b = c.posts[pi].account, c.posts[pj].account
        if a == b:
            continue
        k = (min(a, b), max(a, b))
        sim_edges[k] = max(sim_edges.get(k, 0.0), v)
    return {
        **alert_summary(row),
        "explanation": d["explanation"],
        "features": d["features"],
        "contributions": d["contributions"],
        "accounts": accounts,
        "posts": [{"handle": c.accounts[p.account].handle, "account": p.account,
                   "time": _fmt_time(p.t), "text": p.text} for p in posts[:200]],
        "graph": {
            "nodes": [{"id": a["id"], "handle": a["handle"], "sealed": a["sealed"],
                       "is_new": a["is_new"]} for a in accounts],
            "follow_edges": follow_edges,
            "similarity_edges": [[a, b, round(v, 3)] for (a, b), v in sim_edges.items()],
        },
        "reviews": store.list_reviews(row["id"]),
        "demo_truth": d["demo_truth"],
    }


def model_card() -> dict:
    m = model()
    ev = json.loads(EVAL_PATH.read_text(encoding="utf-8")) if EVAL_PATH.exists() else None
    return {
        "version": m.version,
        "type": "Lojistik regresyon (standartlaştırılmış özellikler)",
        "why": ("Her özelliğin risk puanına katkısı tam olarak hesaplanabilir; uyarı gerekçeleri "
                "modelin kendisinden okunur."),
        "coefficients": {f: round(float(c), 3) for f, c in zip(FEATURES, m.coef)},
        "training": m.meta,
        "evaluation": ev,
        "robustness": (json.loads(ROBUST_PATH.read_text(encoding="utf-8"))
                       if ROBUST_PATH.exists() else None),
        "data": "Sentetik kampüs verisi (DEMO). Gerçek kullanıcı verisiyle test edilmedi.",
        "limits": [
            "Yalnız sentetik veride ölçüldü; gerçek kampüs verisinde performans farklı olabilir.",
            "Farklı kelimelerle yazılmış ve hashtag kullanmayan kampanyalar çoğu zaman aday kümeye bile girmez.",
            "Günlere yayılmış yavaş kampanyalar zor yakalanır.",
            "Etkinlik/kulüp bağlamı yalnız paylaşımlar o etkinlikten/kulüpten bahsediyorsa riski düşürür. "
            "Kampanyayı etkinlik katılımcılarına yaptıran saldırının %75'i yakalandı; kampanya metnine "
            "etkinlik adını da ekleyen daha dikkatli bir saldırgan test edilmedi.",
            "Tespit eşikten bağımsız olarak ~%69'da kalıyor: kaçan kampanyaların çoğu aday kümeye hiç girmiyor "
            "(farklı cümleler, hashtag yok). Bu, anlam düzeyinde benzerlik gerektiriyor.",
            "Model bir yargı değildir: hiçbir hesabı bot ya da kötü niyetli ilan etmez, son karar insandadır.",
        ],
    }


def demo_personas(seed: int = DEMO_SEED, organizer_id: str = DEMO_ORGANIZER) -> list[dict]:
    """
    Akış demosu için kampüsten hesap seçer: yüksek riskli kümelerden üyeler,
    masum ama benzer paylaşım yapan bir kümeden bir üye ve hiçbir kümede olmayan
    normal öğrenciler. Mühürlü hesaplar demo kimliğiyle PoP alır; risk değerleri
    modelin yazdığı kayıttan gelir.
    """
    c = campus(seed)
    rows = store.list_alerts(organizer_id)
    picked: list[tuple[int, int | None, str]] = []      # (hesap, uyarı satırı index, rol)
    used: set[int] = set()

    def scenario_poster(row_idx, a):
        pids = set(rows[row_idx]["data"]["post_ids"])
        return any(p.id in pids and p.account == a and p.scenario is not None for p in c.posts)

    def take(row_idx, prefer_sealed, role):
        d = rows[row_idx]["data"]
        # Önce kümenin asıl içeriğini paylaşan, tercih edilen mühür durumundaki hesap
        cands = sorted(d["members"], key=lambda a: (not scenario_poster(row_idx, a),
                                                    c.accounts[a].sealed != prefer_sealed, a))
        for a in cands:
            if a not in used:
                used.add(a)
                picked.append((a, row_idx, role))
                return

    high = [i for i, r in enumerate(rows) if r["level"] == "yüksek"]

    # Tezin gösterimi: mühürlü (gerçek insan) olduğu halde yüksek riskli bir
    # koordinasyon kümesinde olan hesap. En çok mühürlü üyesi olan yüksek uyarıdan seçilir.
    def sealed_share(i):
        mem = rows[i]["data"]["members"]
        return sum(c.accounts[a].sealed for a in mem) / len(mem)

    seen_truth = set()
    thesis = max(high, key=sealed_share, default=None)
    if thesis is not None and sealed_share(thesis) >= 0.5:
        take(thesis, prefer_sealed=True, role="mühürlü gerçek insan ama koordineli kümede")
        seen_truth.add(rows[thesis]["data"]["demo_truth"]["scenario"])
    for i in high:
        t = rows[i]["data"]["demo_truth"]["scenario"]
        if t in seen_truth:
            continue
        seen_truth.add(t)
        take(i, prefer_sealed=(t == "paid_humans"), role="yüksek riskli küme üyesi")
        if len(picked) >= 3:
            break
    # Masum örnek: paylaşımlarının çoğu gerçekten masum bir senaryodan gelen, düşük riskli küme
    benign_ids = {sc.id for sc in c.scenarios if sc.label == 0}

    def benign_post_share(i):
        pids = rows[i]["data"]["post_ids"]
        return sum(c.posts[p].scenario in benign_ids for p in pids) / max(1, len(pids))

    low_benign = sorted((i for i, r in enumerate(rows) if r["level"] == "düşük"),
                        key=benign_post_share, reverse=True)
    if low_benign and benign_post_share(low_benign[0]) >= 0.5:
        take(low_benign[0], prefer_sealed=True, role="benzer paylaşım ama düşük risk (bağlam var)")

    in_any = {a for r in rows for a in r["data"]["members"]}
    for a in c.accounts:
        if len(picked) >= 6:
            break
        if a.kind == "normal" and a.sealed and a.id not in in_any and a.id not in used:
            if any(p.account == a.id for p in c.posts):
                used.add(a.id)
                picked.append((a.id, None, "normal öğrenci, uyarı yok"))

    out = []
    for acc_id, row_idx, role in picked:
        a = c.accounts[acc_id]
        if row_idx is not None:
            pids = set(rows[row_idx]["data"]["post_ids"])
            mine = [p for p in c.posts if p.id in pids and p.account == acc_id]
            post = next((p for p in mine if p.scenario is not None), mine[0])
        else:
            post = next(p for p in reversed(c.posts) if p.account == acc_id)
        out.append({
            "handle": a.handle,
            "name": a.handle.split("_")[0].split(".")[0].rstrip("0123456789").capitalize() or a.handle,
            "sealed": a.sealed,
            "national_id": demo_national_id(seed, acc_id) if a.sealed else None,
            "text": post.text,
            "time": _fmt_time(post.t),
            "alert_id": rows[row_idx]["id"] if row_idx is not None else None,
            "alert_level": rows[row_idx]["level"] if row_idx is not None else None,
            "demo_role": role,
            "demo_truth": rows[row_idx]["data"]["demo_truth"]["description"] if row_idx is not None
            else "Normal öğrenci",
        })
    return out
