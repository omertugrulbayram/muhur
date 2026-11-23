"""
Koordinasyon modeli — eğitim + değerlendirme.

Eğitim ve test AYRI kampüs dünyalarında yapılır (farklı seed'ler): model, test
dünyalarındaki hiçbir hesabı, paylaşımı veya senaryo örneğini görmez.

Karşılaştırılanlar
    lr       açıklanabilir lojistik regresyon (ürüne giden model)
    gb       Gradient Boosting (yalnız karşılaştırma)
    naive    "çok benzer metin + kısa sürede = şüpheli" kuralı (bağlam yok)

Çalıştırma (backend/ klasöründen):
    python -m app.ml.train_coordination            # eğit, kaydet, özet bas
    python -m app.ml.train_coordination --json r.json   # sonuçları dosyaya da yaz
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score, precision_score, recall_score, roc_auc_score

from app.ml.campus import BENIGN_TYPES, COORD_TYPES, generate
from app.ml.coordination import (
    FEATURES, CoordinationModel, candidate_clusters, cluster_features, label_of,
)

TRAIN_SEEDS = list(range(1, 13))
TEST_SEEDS = list(range(101, 109))
THRESHOLD = 0.5


def build(seeds, **gen_kw):
    rows = []
    for s in seeds:
        campus = generate(seed=s, **gen_kw)
        for cl in candidate_clusters(campus):
            feats, ctx = cluster_features(campus, cl)
            y, typ, purity = label_of(campus, cl["members"])
            rows.append({"seed": s, "x": [feats[f] for f in FEATURES], "feats": feats,
                         "y": y, "type": typ, "purity": purity, "members": cl["members"],
                         "campus": campus})
    return rows


def naive_rule(feats) -> float:
    """Bağlamı hiç dikkate almayan basit kural: benzer + hızlı → şüpheli."""
    return 1.0 if (feats["mean_similarity"] >= 0.7 and feats["log_span_hours"] <= np.log1p(6)) else 0.0


def fit_lr(rows) -> CoordinationModel:
    X = np.array([r["x"] for r in rows])
    y = np.array([r["y"] for r in rows])
    mean, std = X.mean(0), X.std(0) + 1e-9
    lr = LogisticRegression(C=0.5, class_weight="balanced", max_iter=2000)
    lr.fit((X - mean) / std, y)
    return CoordinationModel(lr.coef_[0], lr.intercept_[0], mean, std, version="lr-v1",
                             meta={"train_seeds": TRAIN_SEEDS, "n_train_clusters": int(len(y)),
                                   "positive_rate": round(float(y.mean()), 3)})


def scenario_report(rows, scores) -> dict:
    """
    Senaryo örneği bazında: senaryonun hesaplarının çoğunu içeren küme eşiği geçti mi?
    Masum senaryolarda bu YANLIŞ POZİTİFTİR; koordineli senaryolarda TESPİTTİR.
    Hiç kümeye girmeyen senaryo örneği: masumsa doğru (uyarı yok), koordineliyse kaçırma.
    """
    by_campus = defaultdict(list)
    for r, s in zip(rows, scores):
        by_campus[id(r["campus"])].append((r, s))
    res = defaultdict(lambda: {"instances": 0, "flagged": 0})
    for items in by_campus.values():
        campus = items[0][0]["campus"]
        posters = defaultdict(set)
        for p in campus.posts:
            if p.scenario is not None:
                posters[p.scenario].add(p.account)
        for sc in campus.scenarios:
            mem = posters[sc.id]
            best = 0.0
            for r, s in items:
                if len(mem & set(r["members"])) >= 0.5 * len(mem):
                    best = max(best, s)
            res[sc.type]["instances"] += 1
            res[sc.type]["flagged"] += int(best >= THRESHOLD)
    out = {}
    for t in BENIGN_TYPES + COORD_TYPES:
        d = res[t]
        out[t] = {**d, "rate": round(d["flagged"] / d["instances"], 3) if d["instances"] else None,
                  "kind": "masum" if t in BENIGN_TYPES else "koordineli"}
    return out


def account_fpr(rows, scores) -> float:
    """Normal (koordinasyona katılmayan) öğrencilerin ne kadarı bir uyarıya düştü?"""
    flagged, total = 0, 0
    by_campus = defaultdict(list)
    for r, s in zip(rows, scores):
        by_campus[id(r["campus"])].append((r, s))
    for items in by_campus.values():
        campus = items[0][0]["campus"]
        normals = {a.id for a in campus.accounts if a.kind == "normal"}
        hit = set()
        for r, s in items:
            if s >= THRESHOLD:
                hit |= set(r["members"]) & normals
        flagged += len(hit)
        total += len(normals)
    return flagged / max(1, total)


def metrics(y, s) -> dict:
    pred = (np.array(s) >= THRESHOLD).astype(int)
    out = {"precision": precision_score(y, pred, zero_division=0),
           "recall": recall_score(y, pred, zero_division=0),
           "f1": f1_score(y, pred, zero_division=0)}
    if len(set(y)) > 1 and len(set(s)) > 1:
        out["auc"] = roc_auc_score(y, s)
    neg = [p for p, t in zip(pred, y) if t == 0]
    out["cluster_fpr"] = sum(neg) / max(1, len(neg))
    return {k: round(float(v), 3) for k, v in out.items()}


def evaluate(model: CoordinationModel, gb, test_rows) -> dict:
    y = [r["y"] for r in test_rows]
    s_lr = [model.predict(r["feats"]) for r in test_rows]
    s_gb = list(gb.predict_proba(np.array([r["x"] for r in test_rows]))[:, 1])
    s_nv = [naive_rule(r["feats"]) for r in test_rows]
    out = {}
    for name, s in (("lr", s_lr), ("gb", s_gb), ("naive", s_nv)):
        out[name] = {"cluster": metrics(y, s), "scenarios": scenario_report(test_rows, s),
                     "normal_account_fpr": round(account_fpr(test_rows, s), 4)}
    out["n_test_clusters"] = len(test_rows)
    out["n_test_positive"] = int(sum(y))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="sonuçları bu dosyaya yaz")
    ap.add_argument("--no-save", action="store_true")
    args = ap.parse_args()

    train = build(TRAIN_SEEDS)
    test = build(TEST_SEEDS)
    model = fit_lr(train)
    gb = GradientBoostingClassifier(n_estimators=150, max_depth=3, learning_rate=0.05, random_state=0)
    gb.fit(np.array([r["x"] for r in train]), np.array([r["y"] for r in train]))
    res = evaluate(model, gb, test)
    res["n_train_clusters"] = len(train)
    res["coefficients"] = {f: round(float(c), 3) for f, c in zip(FEATURES, model.coef)}
    if not args.no_save:
        model.save()

    print(f"\n  Eğitim: {len(train)} küme ({len(TRAIN_SEEDS)} dünya) · Test: {len(test)} küme "
          f"({len(TEST_SEEDS)} dünya, {res['n_test_positive']} koordineli)\n")
    print(f"  {'Model':<8}{'Prec':>7}{'Rec':>7}{'F1':>7}{'AUC':>7}{'Küme YP':>9}{'Öğrenci YP':>12}")
    for name in ("lr", "gb", "naive"):
        m = res[name]["cluster"]
        print(f"  {name:<8}{m['precision']:>7.3f}{m['recall']:>7.3f}{m['f1']:>7.3f}"
              f"{m.get('auc', float('nan')):>7.3f}{m['cluster_fpr']:>9.3f}{res[name]['normal_account_fpr']:>12.4f}")
    print("\n  Senaryo bazında uyarı oranı (masumda düşük, koordinelide yüksek olmalı)\n")
    print(f"  {'Senaryo':<18}{'Tür':<12}{'Örnek':>6}{'LR':>8}{'GB':>8}{'Kural':>8}")
    for t in BENIGN_TYPES + COORD_TYPES:
        a, b, c = (res[k]["scenarios"][t] for k in ("lr", "gb", "naive"))
        print(f"  {t:<18}{a['kind']:<12}{a['instances']:>6}{a['rate']:>8.2f}{b['rate']:>8.2f}{c['rate']:>8.2f}")
    print("\n  LR katsayıları (pozitif = riski artırır):")
    for f, c in sorted(res["coefficients"].items(), key=lambda kv: -abs(kv[1])):
        print(f"    {f:<20}{c:+.3f}")
    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
