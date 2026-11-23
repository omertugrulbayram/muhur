"""
Güven/İtibar motoru testleri.

Tezin sayısal/davranışsal garantilerini kilitler:
- PoP yoksa güven ~0 (kanıtlanmış insan olmadan güven olmaz).
- PoP + katılım + temiz davranış -> yüksek bant.
- Gerçek insan olsa bile YÜKSEK sybil olasılığı skoru düşük banda çeker (CIB).
- Başkasına bağlı katılım nişanı güveni yükseltemez.
- Skor her zaman [0..1] ve deterministik.
"""

from app.pop.issuer import issue_personhood_credential
from app.poa.checkin import verify_checkin, issue_checkin_token
from app.pop.issuer import issue_personhood_token
from app.trust.reputation import compute_trust_score, band_of


def _sealed_person(nid="12345678901", birth_year=2000):
    """Gerçek PoP + PoA üretir (mock issuer üzerinden), tam bağlı zincir."""
    cred = issue_personhood_credential(nid, birth_year)
    ptoken = issue_personhood_token(cred)
    poas = []
    for ev in ("teknofest-2026", "hackathon-2026"):
        checkin = issue_checkin_token(ev)
        poas.append(verify_checkin(checkin, ptoken, enforce_defenses=True))
    return cred, poas


def test_no_personhood_means_no_trust():
    r = compute_trust_score(None, None, sybil_probability=0.0)
    assert r["trust_score"] == 0.0
    assert r["band"] == "low"


def test_sealed_human_clean_is_high():
    cred, poas = _sealed_person()
    r = compute_trust_score(cred, poas, sybil_probability=0.03)
    assert r["band"] == "high"
    assert r["trust_score"] > 0.85


def test_sealed_human_no_attendance_is_reasonable():
    cred = issue_personhood_credential("98765432109", 1995)
    r = compute_trust_score(cred, [], sybil_probability=0.05)
    # PoP var, katılım yok: orta-üst; ama tek başına maks değil
    assert 0.55 <= r["trust_score"] <= 0.75


def test_coordinated_human_is_suppressed():
    """Gerçek insan + katılım olsa BİLE yüksek sybil -> düşük güven (CIB)."""
    cred, poas = _sealed_person()
    r = compute_trust_score(cred, poas, sybil_probability=0.90)
    assert r["band"] == "low"
    assert r["trust_score"] < 0.20
    # kimlik ekseni hâlâ yüksek, otantiklik ekseni onu eziyor:
    assert r["axes"]["identity"] > 0.8
    assert r["axes"]["authenticity"] < 0.2


def test_unbound_attendance_is_ignored():
    """Başkasının nişanına bağlı PoA, bu hesabın güvenini yükseltmemeli."""
    cred = issue_personhood_credential("11111111111", 2000)
    foreign_poa = {
        "credential_type": "ProofOfAttendance",
        "event_id": "teknofest-2026",
        "bound_to": "baskasinin-nishani-abcdef",
        "issued_at": 0,
    }
    with_foreign = compute_trust_score(cred, [foreign_poa], sybil_probability=0.05)
    without = compute_trust_score(cred, [], sybil_probability=0.05)
    assert with_foreign["trust_score"] == without["trust_score"]
    assert with_foreign["breakdown"]["attendance"]["score"] == 0.0


def test_score_is_bounded_and_deterministic():
    cred, poas = _sealed_person()
    for p in (0.0, 0.2, 0.5, 0.8, 1.0):
        r1 = compute_trust_score(cred, poas, sybil_probability=p)
        r2 = compute_trust_score(cred, poas, sybil_probability=p)
        assert 0.0 <= r1["trust_score"] <= 1.0
        assert r1 == r2  # deterministik


def test_explanation_is_present_for_discovery_layer():
    cred, poas = _sealed_person()
    r = compute_trust_score(cred, poas, sybil_probability=0.1)
    assert isinstance(r["explanation"], list) and len(r["explanation"]) >= 3
    assert band_of(r["trust_score"]) == r["band"]
