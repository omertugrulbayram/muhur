"""
İngilizce mod (?lang=en): metinler çevrilir, karar mantığı değişmez.

Kilitlenen garantiler:
- İngilizce açıklama, Türkçe açıklamayla AYNI özellikleri aynı ağırlıklarla seçer;
- her İngilizce uyarıda masum açıklama ve "son karar insanda" notu vardır;
- güven puanı dil değişince değişmez, yalnız gerekçe metni değişir;
- varsayılan dil Türkçe kalır.
"""

from app.analysis import service as analysis
from app.ml.campus import generate
from app.ml.coordination import analyze

H = {"X-Organizer-Key": "test-org-key"}


def test_english_explanation_selects_same_features():
    for a in analyze(generate(seed=57)):
        tr, en = a["explanation"], a["explanation_en"]
        for key in ("signals", "mitigating"):
            assert [(s["feature"], s["weight"]) for s in tr[key]] == \
                   [(s["feature"], s["weight"]) for s in en[key]]
        assert len(tr["innocent_explanations"]) == len(en["innocent_explanations"])
        assert len(tr["cautions"]) == len(en["cautions"])
        assert "final decision" in en["caveat"]
        assert "dakika" not in " ".join(s["text"] for s in en["signals"])


def test_english_endpoints(client):
    analysis.run_demo_analysis()
    alerts = client.get("/organizer/alerts?lang=en", headers=H).json()["alerts"]
    assert alerts and alerts[0]["first_post"].startswith("day ")
    d = client.get(f"/organizer/alerts/{alerts[0]['id']}?lang=en", headers=H).json()
    assert d["explanation"]["innocent_explanations"]
    assert "not an accusation" in d["explanation"]["caveat"]
    tr = client.get(f"/organizer/alerts/{alerts[0]['id']}", headers=H).json()
    assert "suçlama değildir" in tr["explanation"]["caveat"]
    card = client.get("/organizer/model?lang=en", headers=H).json()
    assert any("synthetic" in x for x in card["limits"])


def test_trust_score_same_in_both_languages(client):
    tok = client.post("/pop/verify", json={"national_id": "10000000146", "birth_year": 2003}).json()
    t = tok["personhood_token"]
    tr = client.post("/trust/score", json={"personhood_token": t}).json()
    en = client.post("/trust/score?lang=en", json={"personhood_token": t}).json()
    assert tr["trust_score"] == en["trust_score"]
    assert en["explanation"][0].startswith("Verified")
    assert tr["explanation"][0].startswith("Kanıtlanmış")
