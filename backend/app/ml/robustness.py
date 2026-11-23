"""
Koordinasyon modeli — sağlamlık deneyleri (5. adım).

Ürün modelini (coordination_lr.json) DEĞİŞTİRMEZ; yalnız ölçer.

Deneyler
  1. Eşik taraması      : eşik değişince yakalama ve yanlış alarm nasıl değişiyor?
  2. Ablasyon           : bağlam özellikleri / hashtag özelliği çıkarılırsa ne olur?
  3. Kamufle saldırı    : kampanya, gerçek bir etkinliğe katılmış öğrencilere etkinlik
                          sonrası yaptırılırsa (eğitimde hiç görülmeyen saldırı) ne olur?
  4. Dağılım kayması    : daha küçük / büyük kampüs, farklı senaryo karışımı.

Çalıştırma (backend/ klasöründen):
    python -m app.ml.robustness --json app/ml/models/robustness.json
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict

import numpy as np
from sklearn.linear_model import LogisticRegression

from app.ml.campus import ADVERSARIAL_TYPES, BENIGN_TYPES, COORD_TYPES, generate
from app.ml.coordination import (
    CONTEXT_FEATURES, FEATURES, CoordinationModel, candidate_clusters, cluster_features, label_of,
)
from app.ml.train_coordination import TEST_SEEDS, TRAIN_SEEDS

ALL_TYPES = BENIGN_TYPES + COORD_TYPES + ADVERSARIAL_TYPES


def build_world_rows(campus):
    rows = []
    for cl in candidate_clusters(campus):
        feats, _ = cluster_features(campus, cl)
        y, typ, _ = label_of(campus, cl["members"])
        rows.append({"feats": feats, "y": y, "type": typ, "members": cl["members"]})
    return rows


def worlds(seeds, **kw):
    out = []
    for s in seeds:
        c = generate(seed=s, **kw)
        out.append((c, build_world_rows(c)))
    return out


def scenario_rates(world_list, score_fn, thr):
    """Her senaryo türü için: senaryo hesaplarının çoğunu içeren bir küme eşiği geçti mi?"""
    res = defaultdict(lambda: [0, 0])
    normal_hit, normal_total = 0, 0
    for campus, rows in world_list:
        scores = [score_fn(r["feats"]) for r in rows]
        posters = defaultdict(set)
        for p in campus.posts:
            if p.scenario is not None:
                posters[p.scenario].add(p.account)
        for sc in campus.scenarios:
            mem = posters[sc.id]
            best = max([s for r, s in zip(rows, scores)
                        if len(mem & set(r["members"])) >= 0.5 * max(1, len(mem))] or [0.0])
            res[sc.type][0] += 1
            res[sc.type][1] += int(best >= thr)
        normals = {a.id for a in campus.accounts if a.kind == "normal"}
        hit = set()
        for r, s in zip(rows, scores):
            if s >= thr:
                hit |= set(r["members"]) & normals
        normal_hit += len(hit)
        normal_total += len(normals)
    rates = {t: round(res[t][1] / res[t][0], 3) for t in ALL_TYPES if res[t][0]}
    return rates, round(normal_hit / max(1, normal_total), 4)


def fit(train_rows, features):
    X = np.array([[r["feats"][f] for f in features] for r in train_rows])
    y = np.array([r["y"] for r in train_rows])
    mean, std = X.mean(0), X.std(0) + 1e-9
    lr = LogisticRegression(C=0.5, class_weight="balanced", max_iter=2000).fit((X - mean) / std, y)

    def score(feats):
        x = (np.array([feats[f] for f in features]) - mean) / std
        return float(1 / (1 + np.exp(-(x @ lr.coef_[0] + lr.intercept_[0]))))
    return score


def summarize(rates):
    benign = [rates[t] for t in BENIGN_TYPES if t in rates]
    coord = [rates[t] for t in COORD_TYPES if t in rates]
    return {"masum_ortalama_alarm": round(float(np.mean(benign)), 3),
            "koordineli_ortalama_tespit": round(float(np.mean(coord)), 3)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    args = ap.parse_args()
    model = CoordinationModel.load()
    prod = model.predict
    out = {}

    print("\n  Dünyalar hazırlanıyor…")
    train_rows = [r for _, rows in worlds(TRAIN_SEEDS) for r in rows]
    test_w = worlds(TEST_SEEDS)

    # 1) Eşik taraması
    print("\n  1) Eşik taraması (ürün modeli)\n")
    print(f"  {'Eşik':<6}{'Masum alarm':>13}{'Koord. tespit':>15}{'Normal öğr. YP':>16}")
    sweep = []
    for thr in (0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9):
        rates, fpr = scenario_rates(test_w, prod, thr)
        sm = summarize(rates)
        sweep.append({"threshold": thr, **sm, "normal_account_fpr": fpr, "rates": rates})
        print(f"  {thr:<6}{sm['masum_ortalama_alarm']:>13.2f}{sm['koordineli_ortalama_tespit']:>15.2f}{fpr:>16.3f}")
    out["threshold_sweep"] = sweep

    # 2) Ablasyon
    print("\n  2) Ablasyon (eşik 0.5, aynı eğitim/test dünyaları)\n")
    variants = {
        "tum_ozellikler": FEATURES,
        "baglam_yok": [f for f in FEATURES if f not in CONTEXT_FEATURES],
        "hashtag_yok": [f for f in FEATURES if f != "hashtag_link_rate"],
        "yalniz_metin_ve_zaman": ["mean_similarity", "exact_dup_frac", "log_span_hours", "log_size"],
    }
    abl = {}
    print(f"  {'Varyant':<24}{'Masum alarm':>13}{'Koord. tespit':>15}{'Normal öğr. YP':>16}")
    for name, feats in variants.items():
        rates, fpr = scenario_rates(test_w, fit(train_rows, feats), 0.5)
        abl[name] = {**summarize(rates), "normal_account_fpr": fpr, "rates": rates}
        print(f"  {name:<24}{abl[name]['masum_ortalama_alarm']:>13.2f}"
              f"{abl[name]['koordineli_ortalama_tespit']:>15.2f}{fpr:>16.3f}")
    out["ablation"] = abl

    # 3) Kamufle saldırı
    print("\n  3) Kamufle saldırı (eğitimde görülmedi)\n")
    adv_w = worlds([201, 202, 203, 204, 205, 206],
                   coordinated={"bot_network": 1, "paid_humans": 1, "camouflaged_campaign": 2})
    rates, fpr = scenario_rates(adv_w, prod, 0.5)
    out["adversarial"] = {"rates": rates, "normal_account_fpr": fpr}
    for t in ("paid_humans", "camouflaged_campaign"):
        print(f"  {t:<24}tespit {rates.get(t, float('nan')):.2f}")

    # 4) Dağılım kayması
    print("\n  4) Dağılım kayması\n")
    shifts = {
        "kucuk_kampus_250": dict(n_students=250),
        "buyuk_kampus_900": dict(n_students=900),
        "masum_agirlikli": dict(benign={"event_crowd": 6, "club_announce": 6, "dorm_friends": 3, "exam_night": 4},
                                coordinated={"bot_network": 1, "paid_humans": 1}),
        "saldiri_agirlikli": dict(benign={"event_crowd": 1, "club_announce": 1},
                                  coordinated={"bot_network": 3, "bought_accounts": 3, "paid_humans": 3,
                                               "slow_campaign": 2}),
    }
    sh = {}
    print(f"  {'Kurgu':<22}{'Masum alarm':>13}{'Koord. tespit':>15}{'Normal öğr. YP':>16}")
    for name, kw in shifts.items():
        w = worlds([301, 302, 303, 304], **kw)
        rates, fpr = scenario_rates(w, prod, 0.5)
        sh[name] = {**summarize(rates), "normal_account_fpr": fpr, "rates": rates}
        print(f"  {name:<22}{sh[name]['masum_ortalama_alarm']:>13.2f}"
              f"{sh[name]['koordineli_ortalama_tespit']:>15.2f}{fpr:>16.3f}")
    out["distribution_shift"] = sh

    if args.json:
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, ensure_ascii=False, indent=2)
    print()


if __name__ == "__main__":
    main()
