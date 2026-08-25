"""Faz 2 + Faz 4a testleri — PoA anti-spoofing + PoP-PoA sunucu-tarafli baglama."""
import time
import jwt
from app.poa import checkin as poa
from app.pop import issuer as pop

NISHANI = "ornek-dogrulanmis-hesap-nisani"


def setup_function():
    poa._used_nonces.clear()


def _valid_personhood_token():
    """Gercek PoP akisindan gecen, imzali bir personhood token uretir."""
    credential = pop.issue_personhood_credential("test-id", 1999)
    return pop.issue_personhood_token(credential)


def test_valid_checkin_succeeds():
    token = poa.issue_checkin_token("teknofest-2026")
    ptoken = _valid_personhood_token()
    cred = poa.verify_checkin(token, ptoken, enforce_defenses=True)
    assert cred["credential_type"] == "ProofOfAttendance"
    assert cred["bound_to"]  # PoP'tan gelen gercek nisan atanmis


def test_replay_is_blocked():
    token = poa.issue_checkin_token("teknofest-2026")
    ptoken = _valid_personhood_token()
    poa.verify_checkin(token, ptoken, enforce_defenses=True)          # 1. giris
    try:
        poa.verify_checkin(token, ptoken, enforce_defenses=True)      # replay
        assert False, "replay engellenmeliydi"
    except poa.CheckinError as e:
        assert str(e) == "replay_detected"


def test_tampered_token_is_rejected():
    token = poa.issue_checkin_token("teknofest-2026")
    forged = token[:-3] + "aaa"
    ptoken = _valid_personhood_token()
    try:
        poa.verify_checkin(forged, ptoken, enforce_defenses=True)
        assert False, "tamper engellenmeliydi"
    except poa.CheckinError as e:
        assert str(e) == "invalid_signature"


def test_expired_token_is_rejected():
    now = int(time.time())
    expired = jwt.encode(
        {"event_id": "e", "jti": "j", "iat": now - 1000, "exp": now - 500},
        poa._SERVER_SECRET, algorithm=poa._ALG,
    )
    ptoken = _valid_personhood_token()
    try:
        poa.verify_checkin(expired, ptoken, enforce_defenses=True)
        assert False, "expiry engellenmeliydi"
    except poa.CheckinError as e:
        assert str(e) == "expired"


def test_forged_personhood_claim_is_rejected():
    """
    KRITIK TEST — Faz 4a'nin kapattigi acik:
    Bir saldirgan, PoP'tan gecmeden, sahte bir nisan icerecek keyfi bir JWT
    uydurup PoA'ya gonderirse (PoP anahtariyla imzalanmamis), sistem bunu
    ARTIK KABUL ETMEMELI. Rapor bu acigi 'teknik borc' olarak isaretlemisti.
    """
    token = poa.issue_checkin_token("teknofest-2026")
    # Saldirgan kendi (yanlis) anahtariyla sahte bir personhood token uydurur
    forged_ptoken = jwt.encode(
        {"uniqueness_nishani": "sahte-nisan", "over_15": True,
         "iat": int(time.time()), "exp": int(time.time()) + 600},
        "saldirganin-uydurma-anahtari", algorithm="HS256",
    )
    try:
        poa.verify_checkin(token, forged_ptoken, enforce_defenses=True)
        assert False, "sahte personhood token reddedilmeliydi"
    except poa.CheckinError as e:
        assert str(e) == "personhood_token_invalid"
