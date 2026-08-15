"""
Faz 1 testleri — özellikle PoP mahremiyet garantileri.
Çalıştırma (backend/ klasöründen):  pytest
"""

from fastapi.testclient import TestClient

from app.main import app
from app.pop.issuer import uniqueness_nishani

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_pop_verify_returns_credential():
    r = client.post("/pop/verify", json={"national_id": "12345678901", "birth_year": 2000})
    assert r.status_code == 200
    cred = r.json()["credential"]
    assert cred["claims"]["verified_human"] is True
    assert cred["simulated"] is True


def test_nishani_is_deterministic_and_unlinkable():
    # Aynı kişi -> aynı nişan (Sybil engeli)
    a = uniqueness_nishani("12345678901")
    b = uniqueness_nishani("12345678901")
    assert a == b
    # Nişan, ham TC kimliği İÇERMEZ (geri-döndürülemezlik göstergesi)
    assert "12345678901" not in a
    assert len(a) == 64  # SHA-256 hex


def test_over_15_selective_disclosure():
    young = client.post("/pop/verify", json={"national_id": "1", "birth_year": 2020}).json()
    old = client.post("/pop/verify", json={"national_id": "2", "birth_year": 1990}).json()
    # Yalnızca boolean açıklanır; doğum yılı credential'da YER ALMAZ
    assert young["credential"]["claims"]["over_15"] is False
    assert old["credential"]["claims"]["over_15"] is True
    assert "birth_year" not in old["credential"]["claims"]
