"""
Faz 3 — Sentetik sosyal ag ureteci (Sybil/CIB).

NSosyal'in canli verisi olmadigindan, kontrollu bir test sahasi uretiyoruz:
cogunlukla normal kullanici + iceine ENJEKTE edilmis koordineli bot kumesi.
Hangi hesabin bot oldugunu biz bildigimiz icin modelin basarisini olcebiliriz.

Gercekcilik icin: botlarin bir kismi "gizlenen bot"tur (bireysel ozellikleri
insana benzer) ama AG duzeyinde (karsilikli takip + senkron) yine ele verirler.
Boylece bireysel sinyaller tek basina yetmez; ag sinyali ayirt edicidir.
"""

import numpy as np
import networkx as nx


def generate(n_users: int = 1000, n_bots: int = 150, seed: int = 42):
    rng = np.random.default_rng(seed)
    G = nx.DiGraph()
    labels, feats = {}, {}

    n_humans = n_users - n_bots
    human_ids = list(range(n_humans))
    bot_ids = list(range(n_humans, n_users))

    # ---- Normal kullanicilar (bazilari da az takipli / eksik profilli) ----
    for u in human_ids:
        labels[u] = 0
        feats[u] = {
            "age_days": float(rng.uniform(15, 2000)),
            "profile_completeness": float(np.clip(rng.beta(3, 2) + rng.normal(0, 0.08), 0, 1)),
            "posting_time_std": float(rng.uniform(2.0, 8.0)),
            "follower_following_ratio": float(rng.lognormal(0, 0.7)),
        }
        G.add_node(u)

    # ---- Botlar: %45'i "gizlenen bot" (insana benzer bireysel ozellik) ----
    base_age = rng.uniform(10, 60)
    for b in bot_ids:
        stealth = rng.random() < 0.45
        if stealth:
            age = rng.uniform(15, 1200)                          # insan gibi yasli hesap
            completeness = np.clip(rng.beta(3, 2), 0, 1)          # dolu profil
            pstd = rng.uniform(2.0, 6.0)                          # daha dogal saatler
            ratio = float(rng.lognormal(0, 0.6))
        else:
            age = base_age + rng.normal(0, 10)                    # dar aralik
            completeness = np.clip(rng.beta(1.5, 5), 0, 1)        # eksik profil
            pstd = rng.uniform(0.4, 2.2)                          # senkron
            ratio = float(rng.normal(1.0, 0.15))
        labels[b] = 1
        feats[b] = {
            "age_days": float(age),
            "profile_completeness": float(completeness),
            "posting_time_std": float(pstd),
            "follower_following_ratio": ratio,
        }
        G.add_node(b)

    # ---- Kenarlar ----
    # Normaller: seyrek + bazi organik topluluklar (biraz kumelenme)
    for u in human_ids:
        for _ in range(int(rng.integers(2, 9))):
            v = int(rng.integers(0, n_users))
            if v != u:
                G.add_edge(u, v)
    # organik insan toplulugu (network ozelligini tek basina ayirt edici olmaktan cikarir)
    for _ in range(12):
        members = rng.choice(human_ids, size=int(rng.integers(10, 28)), replace=False)
        for a in members:
            for c in members:
                if a != c and rng.random() < 0.45:
                    G.add_edge(int(a), int(c))

    # Botlar: %25'i 'yalniz kurt' (dusuk koordinasyon -> zor yakalanir)
    lone = set(int(x) for x in rng.choice(bot_ids, size=int(0.25*len(bot_ids)), replace=False))
    for b in bot_ids:
        bot_recip_p = 0.03 if b in lone else 0.12
        for c in bot_ids:
            if b != c and rng.random() < bot_recip_p:
                G.add_edge(b, c); G.add_edge(c, b)
        for _ in range(int(rng.integers(1, 5))):   # kamuflaj: normalleri takip
            G.add_edge(b, int(rng.integers(0, n_humans)))

    # ---- Ag-temelli ozellikler (+ gurultu) ----
    undirected = G.to_undirected()
    clustering = nx.clustering(undirected)
    for u in G.nodes():
        succ, pred = set(G.successors(u)), set(G.predecessors(u))
        recip_frac = len(succ & pred) / max(1, len(succ))
        feats[u]["reciprocal_follow_frac"] = float(np.clip(recip_frac + rng.normal(0, 0.09), 0, 1))
        feats[u]["clustering_coeff"] = float(np.clip(clustering.get(u, 0.0) + rng.normal(0, 0.08), 0, 1))
        feats[u]["posting_synchrony"] = float(1.0 / (1.0 + feats[u]["posting_time_std"]))

    return G, feats, labels


INDIVIDUAL_FEATURES = ["age_days", "profile_completeness", "follower_following_ratio"]
NETWORK_FEATURES = ["reciprocal_follow_frac", "clustering_coeff", "posting_synchrony"]
ALL_FEATURES = INDIVIDUAL_FEATURES + NETWORK_FEATURES


def to_matrix(feats: dict, labels: dict, feature_list):
    ids = sorted(feats.keys())
    X = np.array([[feats[i][f] for f in feature_list] for i in ids], dtype=float)
    y = np.array([labels[i] for i in ids], dtype=int)
    return X, y
