"""
Faz 3 — Baseline model eğitimi + değerlendirme + ablasyon.

Sentetik ağ üzerinde bir gradyan artırma (gradient boosting) modeli eğitir,
GÖRÜLMEYEN test kümesinde Precision/Recall/F1/AUC ölçer ve ablasyon yapar:
  - Tüm öznitelikler (bireysel + ağ)
  - Yalnızca bireysel öznitelikler (ağ sinyali çıkarılmış)
Böylece ağ sinyalinin katkısı sayısal olarak gösterilir — rapordaki tez budur.

Çalıştırma (backend/ klasöründen):
    python -m app.ml.train_baseline
"""

import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import precision_score, recall_score, f1_score, roc_auc_score

from app.ml.synthetic import generate, to_matrix, ALL_FEATURES, INDIVIDUAL_FEATURES


def evaluate(feature_list, feats, labels, seed=42):
    X, y = to_matrix(feats, labels, feature_list)
    X_tr, X_te, y_tr, y_te = train_test_split(
        X, y, test_size=0.30, random_state=seed, stratify=y
    )
    # Overfitting önlemleri: sınırlı derinlik + düşük öğrenme oranı + erken durdurma
    clf = GradientBoostingClassifier(
        n_estimators=150, learning_rate=0.05, max_depth=3,
        validation_fraction=0.2, n_iter_no_change=15, random_state=seed,
    )
    clf.fit(X_tr, y_tr)

    # k-katlı çapraz doğrulama (kararlılık)
    cv = cross_val_score(clf, X, y, cv=5, scoring="f1").mean()

    proba = clf.predict_proba(X_te)[:, 1]
    pred = (proba >= 0.5).astype(int)
    return {
        "precision": precision_score(y_te, pred),
        "recall": recall_score(y_te, pred),
        "f1": f1_score(y_te, pred),
        "auc": roc_auc_score(y_te, proba),
        "cv_f1": cv,
    }


def main():
    G, feats, labels = generate(n_users=1000, n_bots=150, seed=42)
    n_bot = sum(labels.values())
    print(f"\n  Sentetik ag: {len(labels)} hesap, {n_bot} bot ({n_bot/len(labels)*100:.0f}%), "
          f"{G.number_of_edges()} takip iliskisi\n")

    full = evaluate(ALL_FEATURES, feats, labels)
    indiv = evaluate(INDIVIDUAL_FEATURES, feats, labels)

    print("  Sybil/CIB Baseline (Gradient Boosting) — Test Kumesi Sonuclari\n")
    print(f"  {'Model':<34}{'Precision':<11}{'Recall':<9}{'F1':<8}{'AUC'}")
    print("  " + "-" * 66)
    print(f"  {'Tum ozellikler (bireysel+ag)':<34}"
          f"{full['precision']:<11.3f}{full['recall']:<9.3f}{full['f1']:<8.3f}{full['auc']:.3f}")
    print(f"  {'Yalnizca bireysel (ablasyon)':<34}"
          f"{indiv['precision']:<11.3f}{indiv['recall']:<9.3f}{indiv['f1']:<8.3f}{indiv['auc']:.3f}")
    print()
    print(f"  5-kat capraz dogrulama F1 (tum ozellikler): {full['cv_f1']:.3f}")
    delta = full["f1"] - indiv["f1"]
    print(f"  Ag sinyalinin F1 katkisi: +{delta:.3f}  "
          f"(ag ozellikleri cikinca basari {'dusuyor' if delta>0 else 'degismiyor'})\n")


if __name__ == "__main__":
    main()
