"""Faz 2 testleri — PoA anti-spoofing garantileri."""
import time
import jwt
from app.poa import checkin as poa


def setup_function():
    poa._used_nonces.clear()


def test_valid_checkin_succeeds():
    token = poa.issue_checkin_token("teknofest-2026")
    cred = poa.verify_checkin(token, "nisan-1", enforce_defenses=True)
    assert cred["credential_type"] == "ProofOfAttendance"
    assert cred["bound_to"] == "nisan-1"


def test_replay_is_blocked():
    token = poa.issue_checkin_token("teknofest-2026")
    poa.verify_checkin(token, "nisan-1", enforce_defenses=True)          # 1. giris
    try:
        poa.verify_checkin(token, "nisan-1", enforce_defenses=True)      # replay
        assert False, "replay engellenmeliydi"
    except poa.CheckinError as e:
        assert str(e) == "replay_detected"


def test_tampered_token_is_rejected():
    token = poa.issue_checkin_token("teknofest-2026")
    forged = token[:-3] + "aaa"
    try:
        poa.verify_checkin(forged, "nisan-1", enforce_defenses=True)
        assert False, "tamper engellenmeliydi"
    except poa.CheckinError as e:
        assert str(e) == "invalid_signature"


def test_expired_token_is_rejected():
    now = int(time.time())
    expired = jwt.encode(
        {"event_id": "e", "jti": "j", "iat": now - 1000, "exp": now - 500},
        poa._SERVER_SECRET, algorithm=poa._ALG,
    )
    try:
        poa.verify_checkin(expired, "nisan-1", enforce_defenses=True)
        assert False, "expiry engellenmeliydi"
    except poa.CheckinError as e:
        assert str(e) == "expired"
