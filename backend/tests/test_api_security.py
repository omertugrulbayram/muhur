"""
HTTP düzeyinde saldırı testleri — 2026-11-23 denetiminde bulunan açıklar.

1. /trust/score elle yazılmış JSON "kanıtlarla" 0.9997 veriyordu.
2. İstemci kendi bot olasılığını (sybil_probability) gönderebiliyordu.
3. /poa/qr herkese açıktı: gitmediğin etkinliğe katılım kanıtı alınabiliyordu.
"""

import time

import jwt
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.config import settings
from app.db import store


def _person(client, nid="12345678901"):
    return client.post("/pop/verify", json={"national_id": nid,
                                            "birth_date": "2000-01-01"}).json()


def _checkin(client, headers, ptok, event="teknofest-2026"):
    ch = client.post("/poa/challenge", json={"event_id": event}, headers=headers).json()
    return client.post("/poa/checkin", json={"checkin_token": ch["checkin_token"],
                                             "personhood_token": ptok})


# ---------- Açık 1: sahte JSON kanıtla tam puan ----------
def test_old_forged_json_exploit_is_rejected(client):
    fake = {"credential_type": "ProofOfPersonhood",
            "claims": {"verified_human": True, "uniqueness_nishani": "uydurma"}}
    poas = [{"credential_type": "ProofOfAttendance", "event_id": f"e{i}",
             "bound_to": "uydurma"} for i in range(10)]
    r = client.post("/trust/score", json={"personhood_credential": fake,
                                          "attendance_credentials": poas,
                                          "sybil_probability": 0.0})
    assert r.status_code == 422


def test_garbage_personhood_token_is_400(client):
    r = client.post("/trust/score", json={"personhood_token": "uydurma"})
    assert r.status_code == 400


def test_attendance_forged_with_attacker_key_not_counted(client):
    p = _person(client)
    sub = p["credential"]["claims"]["uniqueness_nishani"]
    now = int(time.time())
    fakes = [jwt.encode({"typ": "muhur-attendance", "iss": settings.poa_issuer,
                         "aud": settings.aud_attendance, "sub": sub, "event_id": f"e{i}",
                         "iat": now, "exp": now + 600, "jti": f"j{i}"},
                        Ed25519PrivateKey.generate(), algorithm="EdDSA") for i in range(5)]
    r = client.post("/trust/score", json={"personhood_token": p["personhood_token"],
                                          "attendance_tokens": fakes}).json()
    assert r["breakdown"]["attendance"]["score"] == 0.0
    assert r["rejected_attendance_reasons"] == ["attendance_invalid"] * 5


def test_someone_elses_attendance_not_counted(client, org_headers):
    alice, bob = _person(client, "1"), _person(client, "2")
    att = _checkin(client, org_headers, alice["personhood_token"]).json()["attendance_token"]
    r = client.post("/trust/score", json={"personhood_token": bob["personhood_token"],
                                          "attendance_tokens": [att]}).json()
    assert r["breakdown"]["attendance"]["score"] == 0.0
    assert r["rejected_attendance_reasons"] == ["attendance_not_bound_to_subject"]


def test_attendance_not_on_server_record_not_counted(client, org_headers):
    """İmza doğru olsa bile sunucu kaydında yoksa (ör. iptal edildiyse) sayılmaz."""
    p = _person(client)
    att = _checkin(client, org_headers, p["personhood_token"]).json()["attendance_token"]
    with store.connect() as c:
        c.execute("UPDATE attendances SET revoked = 1")
    r = client.post("/trust/score", json={"personhood_token": p["personhood_token"],
                                          "attendance_tokens": [att]}).json()
    assert r["rejected_attendance_reasons"] == ["attendance_not_on_record"]


def test_same_attendance_token_repeated_counts_once(client, org_headers):
    p = _person(client)
    att = _checkin(client, org_headers, p["personhood_token"]).json()["attendance_token"]
    r = client.post("/trust/score", json={"personhood_token": p["personhood_token"],
                                          "attendance_tokens": [att] * 10}).json()
    assert r["breakdown"]["attendance"]["events"] == ["teknofest-2026"]


# ---------- Açık 2: istemci kendi bot olasılığını gönderiyordu ----------
def test_client_cannot_send_sybil_probability(client):
    p = _person(client)
    r = client.post("/trust/score", json={"personhood_token": p["personhood_token"],
                                          "sybil_probability": 0.0})
    assert r.status_code == 422


def test_risk_comes_from_server_record(client, org_headers):
    p = _person(client)
    before = client.post("/trust/score", json={"personhood_token": p["personhood_token"]}).json()
    client.post("/demo/risk", json={"personhood_token": p["personhood_token"],
                                    "probability": 0.9}, headers=org_headers)
    after = client.post("/trust/score", json={"personhood_token": p["personhood_token"]}).json()
    assert after["trust_score"] < before["trust_score"]
    assert after["risk"]["source"] == "manual-demo"


def test_demo_risk_requires_organizer(client):
    p = _person(client)
    r = client.post("/demo/risk", json={"personhood_token": p["personhood_token"],
                                        "probability": 0.0})
    assert r.status_code == 401


def test_demo_risk_disabled_outside_demo_mode(client, org_headers, monkeypatch):
    monkeypatch.setattr(settings, "enable_demo_endpoints", False)
    p = _person(client)
    r = client.post("/demo/risk", json={"personhood_token": p["personhood_token"],
                                        "probability": 0.0}, headers=org_headers)
    assert r.status_code == 404


# ---------- Açık 3: herkes QR üretebiliyordu ----------
def test_challenge_requires_organizer_key(client):
    assert client.post("/poa/challenge", json={"event_id": "teknofest-2026"}).status_code == 401
    assert client.post("/poa/qr", json={"event_id": "teknofest-2026"}).status_code == 401


def test_wrong_organizer_key_rejected(client):
    r = client.post("/poa/challenge", json={"event_id": "teknofest-2026"},
                    headers={"X-Organizer-Key": "tahmin"})
    assert r.status_code == 401


def test_other_organizer_cannot_issue_for_my_event(client):
    store.create_organizer("baska-kulup", "Başka Kulüp", "baska-anahtar")
    r = client.post("/poa/challenge", json={"event_id": "teknofest-2026"},
                    headers={"X-Organizer-Key": "baska-anahtar"})
    assert r.status_code == 403


def test_organizer_key_stored_hashed():
    with store.connect() as c:
        rows = c.execute("SELECT api_key_hash FROM organizers").fetchall()
    assert all(r[0] != "test-org-key" and len(r[0]) == 64 for r in rows)


# ---------- Uçtan uca ----------
def test_full_flow_gives_high_trust(client, org_headers):
    p = _person(client)
    atts = [_checkin(client, org_headers, p["personhood_token"], ev).json()["attendance_token"]
            for ev in ("teknofest-2026", "hackathon-2026")]
    r = client.post("/trust/score", json={"personhood_token": p["personhood_token"],
                                          "attendance_tokens": atts}).json()
    assert r["band"] == "high"
    assert r["breakdown"]["attendance"]["events"] == ["hackathon-2026", "teknofest-2026"]


def test_double_checkin_is_409(client, org_headers):
    p = _person(client)
    assert _checkin(client, org_headers, p["personhood_token"]).status_code == 200
    assert _checkin(client, org_headers, p["personhood_token"]).status_code == 409


def test_organizer_can_create_and_list_events(client, org_headers):
    now = int(time.time())
    r = client.post("/organizer/events", json={"event_id": "bahar-senligi", "name": "Bahar Şenliği",
                                               "starts_at": now - 60, "ends_at": now + 3600},
                    headers=org_headers)
    assert r.status_code == 201
    events = client.get("/organizer/events", headers=org_headers).json()["events"]
    assert "bahar-senligi" in [e["id"] for e in events]


def test_cors_blocks_unknown_origin(client):
    r = client.options("/trust/score", headers={"Origin": "https://kotu-site.example",
                                                "Access-Control-Request-Method": "POST"})
    assert r.headers.get("access-control-allow-origin") != "https://kotu-site.example"


def test_rate_limit(client, monkeypatch):
    monkeypatch.setattr(settings, "rate_limit_per_min", 3)
    codes = [client.post("/pop/verify", json={"national_id": "1", "birth_year": 2000}).status_code
             for _ in range(5)]
    assert codes[:3] == [200] * 3 and codes[3:] == [429, 429]
