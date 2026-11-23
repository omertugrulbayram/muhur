"""Güven motoru (saf formül) — tezin sayısal garantileri."""

from app.trust.reputation import compute_trust_score, band_of

POP = {"verified_human": True, "simulated": True, "sub": "s"}
EVENTS = {"teknofest-2026", "hackathon-2026"}


def risk(p, source="model"):
    return {"probability": p, "source": source}


def test_no_personhood_means_no_trust():
    r = compute_trust_score(None, EVENTS, None)
    assert r["trust_score"] == 0.0 and r["band"] == "low"
    assert r["breakdown"]["attendance"]["score"] == 0.0   # PoP yoksa katılım da sayılmaz


def test_sealed_human_clean_is_high():
    r = compute_trust_score(POP, EVENTS, risk(0.03))
    assert r["band"] == "high" and r["trust_score"] > 0.85


def test_sealed_human_no_attendance_is_reasonable():
    r = compute_trust_score(POP, set(), risk(0.05))
    assert 0.55 <= r["trust_score"] <= 0.75


def test_coordinated_human_is_suppressed():
    r = compute_trust_score(POP, EVENTS, risk(0.90))
    assert r["band"] == "low" and r["trust_score"] < 0.20
    assert r["axes"]["identity"] > 0.8 and r["axes"]["authenticity"] < 0.2


def test_no_risk_assessment_is_neutral_and_says_so():
    r = compute_trust_score(POP, EVENTS, None)
    assert r["axes"]["authenticity"] == 1.0
    assert any("henüz yapılmadı" in line for line in r["explanation"])


def test_high_risk_explanation_keeps_human_in_loop():
    r = compute_trust_score(POP, EVENTS, risk(0.8))
    assert any("son karar insan" in line for line in r["explanation"])


def test_manual_demo_risk_is_labelled():
    r = compute_trust_score(POP, EVENTS, risk(0.8, "manual-demo"))
    assert any("demo" in line for line in r["explanation"])
    assert r["breakdown"]["authenticity"]["risk_source"] == "manual-demo"


def test_score_is_bounded_and_deterministic():
    for p in (0.0, 0.2, 0.5, 0.8, 1.0):
        r1 = compute_trust_score(POP, EVENTS, risk(p))
        assert 0.0 <= r1["trust_score"] <= 1.0
        assert r1 == compute_trust_score(POP, EVENTS, risk(p))
        assert band_of(r1["trust_score"]) == r1["band"]
