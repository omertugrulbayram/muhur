# Faz 3 — Sybil/CIB Baseline Benchmark (sentetik ağ)

Model: Gradient Boosting (baseline). Veri: 1000 hesap, %15 koordineli bot
(gizlenen botlar + yalnız-kurtlar dahil), 30% görülmeyen test kümesi.

| Model | Precision | Recall | F1 | AUC |
|---|---|---|---|---|
| Tüm öznitelikler (bireysel + ağ) | 0.978 | 1.000 | 0.989 | 0.998 |
| Yalnızca bireysel (ablasyon) | 0.962 | 0.556 | 0.704 | 0.866 |

- 5-kat çapraz doğrulama F1 (tüm öznitelikler): 0.973
- Ağ sinyalinin F1 katkısı: +0.285 (ağ özellikleri çıkınca recall 1.000 -> 0.556)

Yorum: Bireysel sinyaller tek başına botların ~yarısını kaçırır; ayırt edici
sinyal ağ düzeyindedir (karşılıklı takip yoğunluğu, kümelenme, senkron paylaşım).
Not: Sonuçlar sentetik benchmark üzerindedir; sonraki adım GNN (GraphSAGE) ve
kamuya açık veri setiyle genişletmedir.
