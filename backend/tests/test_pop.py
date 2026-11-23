"""PoP — mahremiyet garantileri (HTTP üzerinden)."""

from app.pop.issuer import pseudonymous_subject


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    assert r.json()["signing"] == "EdDSA"


def test_pop_verify_returns_signed_token(client):
    r = client.post("/pop/verify", json={"national_id": "12345678901", "birth_date": "2000-01-01"})
    assert r.status_code == 200
    body = r.json()
    assert body["credential"]["claims"]["verified_human"] is True
    assert body["credential"]["simulated"] is True
    assert body["personhood_token"].count(".") == 2


def test_pseudonym_is_deterministic_and_one_way():
    a = pseudonymous_subject("12345678901")
    assert a == pseudonymous_subject("12345678901")      # aynı kişi → aynı değer
    assert a != pseudonymous_subject("12345678902")
    assert "12345678901" not in a
    assert len(a) == 64


def test_over_15_selective_disclosure(client):
    young = client.post("/pop/verify", json={"national_id": "1", "birth_year": 2020}).json()
    old = client.post("/pop/verify", json={"national_id": "2", "birth_year": 1990}).json()
    assert young["credential"]["claims"]["over_15"] is False
    assert old["credential"]["claims"]["over_15"] is True
    assert "birth_year" not in old["credential"]["claims"]


def test_bad_birth_date_is_422(client):
    r = client.post("/pop/verify", json={"national_id": "1", "birth_date": "dun"})
    assert r.status_code == 422
