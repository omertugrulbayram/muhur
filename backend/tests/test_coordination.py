"""
Koordinasyon modeli ve yönetici paneli uçları.

Kilitlenen garantiler:
- model dosyası beklenen özelliklerle yüklenir; PoP durumu model özelliği DEĞİLDİR;
- açıklamalar modelle tutarlıdır (riski artıranların katkısı pozitif, azaltanların negatif);
- her uyarıda masum açıklama ve "son karar insanda" notu vardır;
- uyarılar ve inceleme yalnız organizatöre açıktır, başka organizatör göremez;
- insan kararı kalıcıdır ve analiz yeniden çalışınca silinmez;
- kampüs hesaplarının güven puanı modelin yazdığı riski kullanır (elle değil).
"""

import pytest

from app.analysis import service as analysis
from app.db import store
from app.ml.campus import generate
from app.ml.coordination import FEATURES, CoordinationModel, analyze

H = {"X-Organizer-Key": "test-org-key"}


@pytest.fixture
def analyzed(client):
    n = analysis.run_demo_analysis()
    assert n > 0
    return client


def test_model_loads_and_pop_is_not_a_feature():
    m = CoordinationModel.load()
    assert len(m.coef) == len(FEATURES)
    assert "sealed_frac" not in FEATURES


def test_explanations_are_consistent_with_model():
    for a in analyze(generate(seed=55)):
        exp = a["explanation"]
        assert all(s["weight"] > 0 for s in exp["signals"])
        assert all(s["weight"] < 0 for s in exp["mitigating"])
        assert exp["innocent_explanations"], "her uyarıda masum açıklama olmalı"
        assert "son karar" in exp["caveat"]
        for s in exp["signals"] + exp["mitigating"]:
            assert a["contributions"][s["feature"]] == pytest.approx(s["weight"], abs=1e-3)


def test_alerts_require_organizer(analyzed):
    assert analyzed.get("/organizer/alerts").status_code == 401


def test_alert_list_and_detail(analyzed):
    alerts = analyzed.get("/organizer/alerts", headers=H).json()
    assert alerts["demo"] is True and alerts["alerts"]
    risks = [a["risk"] for a in alerts["alerts"]]
    assert risks == sorted(risks, reverse=True)
    top = alerts["alerts"][0]
    d = analyzed.get(f"/organizer/alerts/{top['id']}", headers=H).json()
    assert d["graph"]["nodes"] and d["posts"] and d["accounts"]
    assert {n["id"] for n in d["graph"]["nodes"]} >= {e[0] for e in d["graph"]["follow_edges"]}


def test_min_level_filter(analyzed):
    high = analyzed.get("/organizer/alerts?min_level=yüksek", headers=H).json()["alerts"]
    assert all(a["level"] == "yüksek" for a in high)


def test_review_is_persisted_and_survives_reanalysis(analyzed):
    aid = analyzed.get("/organizer/alerts", headers=H).json()["alerts"][0]["id"]
    r = analyzed.post(f"/organizer/alerts/{aid}/review", headers=H,
                      json={"decision": "sorun_yok", "note": "kulüp etkinliği, kontrol ettim"})
    assert r.status_code == 200
    analysis.run_demo_analysis()                       # yeniden analiz
    d = analyzed.get(f"/organizer/alerts/{aid}", headers=H).json()
    assert d["status"] == "sorun_yok"
    assert d["reviews"][-1]["note"] == "kulüp etkinliği, kontrol ettim"


def test_invalid_review_decision_rejected(analyzed):
    aid = analyzed.get("/organizer/alerts", headers=H).json()["alerts"][0]["id"]
    r = analyzed.post(f"/organizer/alerts/{aid}/review", headers=H, json={"decision": "bot_ilan_et"})
    assert r.status_code == 422


def test_other_organizer_cannot_see_or_review(analyzed):
    store.create_organizer("baska-kulup", "Başka", "baska-anahtar")
    other = {"X-Organizer-Key": "baska-anahtar"}
    assert analyzed.get("/organizer/alerts", headers=other).json()["alerts"] == []
    aid = analyzed.get("/organizer/alerts", headers=H).json()["alerts"][0]["id"]
    assert analyzed.get(f"/organizer/alerts/{aid}", headers=other).status_code == 404
    assert analyzed.post(f"/organizer/alerts/{aid}/review", headers=other,
                         json={"decision": "isaretle"}).status_code == 404


def test_campus_account_trust_uses_model_risk(analyzed):
    rows = store.list_alerts("demo-kulup")
    high = next(r for r in rows if r["level"] == "yüksek")
    c = analysis.campus()
    acc = next(a for a in high["data"]["members"] if c.accounts[a].sealed) \
        if any(c.accounts[a].sealed for a in high["data"]["members"]) else high["data"]["members"][0]
    tok = analyzed.post("/pop/verify", json={"national_id": analysis.demo_national_id(2026, acc),
                                             "birth_year": 2003}).json()["personhood_token"]
    r = analyzed.post("/trust/score", json={"personhood_token": tok}).json()
    assert r["risk"]["source"] == "model"
    assert r["band"] == "low"


def test_model_card(analyzed):
    card = analyzed.get("/organizer/model", headers=H).json()
    assert set(card["coefficients"]) == set(FEATURES)
    assert card["evaluation"]["lr"]["cluster"]["f1"] > 0.8
    assert any("sentetik" in x for x in card["limits"])


def test_contributions_sum_to_logit_and_context_only_lowers_risk():
    import math
    m = CoordinationModel.load()
    for a in analyze(generate(seed=56)):
        c = a["contributions"]
        logit = m.base_logit() + sum(c.values())
        assert 1 / (1 + math.exp(-logit)) == pytest.approx(a["risk"], abs=1e-3)
        for f in ("shared_event_frac", "shared_club_frac", "shared_dept_frac"):
            assert c[f] <= 1e-9, f"{f} riski artıran gerekçe olamaz"
