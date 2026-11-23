"""PoA — check-in, replay, organizatör yetkisi, etkinlik penceresi, tek katılım."""

import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.config import settings
from app.db import store
from app.poa.checkin import (
    AuthorizationError, CheckinError, issue_checkin_challenge, verify_checkin,
)
from conftest import make_person


def _challenge(event="teknofest-2026", org="demo-kulup"):
    tok, _ = issue_checkin_challenge(event, org)
    return tok


def test_valid_checkin_returns_signed_attendance():
    cred, ptok = make_person()
    r = verify_checkin(_challenge(), ptok)
    assert r["credential"]["bound_to"] == cred["claims"]["uniqueness_nishani"]
    assert r["attendance_token"].count(".") == 2


def test_replay_is_blocked():
    _, p1 = make_person("1")
    _, p2 = make_person("2")
    ch = _challenge()
    verify_checkin(ch, p1)
    with pytest.raises(CheckinError, match="replay_detected"):
        verify_checkin(ch, p2)


def test_replay_survives_restart():
    """Kullanılmış QR listesi veritabanında: 'yeniden başlatma' sonrası da reddedilir."""
    _, p1 = make_person("1")
    _, p2 = make_person("2")
    ch = _challenge()
    verify_checkin(ch, p1)
    store._initialized_for = None     # süreç yeniden başlamış gibi
    store.init_db()
    with pytest.raises(CheckinError, match="replay_detected"):
        verify_checkin(ch, p2)


def test_same_person_cannot_attend_twice():
    _, p = make_person()
    verify_checkin(_challenge(), p)
    with pytest.raises(CheckinError, match="already_attended"):
        verify_checkin(_challenge(), p)


def test_tampered_challenge_rejected():
    _, p = make_person()
    ch = _challenge()
    with pytest.raises(CheckinError, match="checkin_invalid"):
        verify_checkin(ch[:-3] + ("aaa" if not ch.endswith("aaa") else "bbb"), p)


def test_expired_challenge_rejected():
    _, p = make_person()
    now = int(time.time())
    from app.security import keys
    expired = jwt.encode(
        {"typ": "muhur-checkin-challenge", "iss": settings.poa_issuer,
         "aud": settings.aud_checkin, "event_id": "teknofest-2026", "jti": "eski",
         "iat": now - 1000, "exp": now - 500},
        keys.poa_private_key(), algorithm="EdDSA")
    with pytest.raises(CheckinError, match="checkin_expired"):
        verify_checkin(expired, p)


def test_challenge_forged_with_attacker_key_rejected():
    """Saldırgan kendi anahtarıyla QR üretemez (eskiden /poa/qr herkese açıktı)."""
    _, p = make_person()
    now = int(time.time())
    forged = jwt.encode(
        {"typ": "muhur-checkin-challenge", "iss": settings.poa_issuer,
         "aud": settings.aud_checkin, "event_id": "teknofest-2026", "jti": "x",
         "iat": now, "exp": now + 60},
        Ed25519PrivateKey.generate(), algorithm="EdDSA")
    with pytest.raises(CheckinError, match="checkin_invalid"):
        verify_checkin(forged, p)


def test_only_event_owner_can_issue_challenge():
    store.create_organizer("baska-kulup", "Başka Kulüp", "baska-anahtar")
    with pytest.raises(AuthorizationError, match="not_event_owner"):
        issue_checkin_challenge("teknofest-2026", "baska-kulup")


def test_unknown_event_rejected():
    with pytest.raises(AuthorizationError, match="event_not_found"):
        issue_checkin_challenge("olmayan-etkinlik", "demo-kulup")


def test_closed_event_rejected():
    now = int(time.time())
    store.create_event("gecmis-etkinlik", "demo-kulup", "Geçmiş", now - 7200, now - 3600)
    with pytest.raises(AuthorizationError, match="event_not_open"):
        issue_checkin_challenge("gecmis-etkinlik", "demo-kulup")


def test_forged_personhood_rejected_at_checkin():
    now = int(time.time())
    forged_ptok = jwt.encode(
        {"typ": "muhur-personhood", "iss": settings.pop_issuer, "aud": settings.aud_personhood,
         "sub": "sahte", "verified_human": True, "iat": now, "exp": now + 600, "jti": "j"},
        Ed25519PrivateKey.generate(), algorithm="EdDSA")
    with pytest.raises(CheckinError, match="personhood_invalid"):
        verify_checkin(_challenge(), forged_ptok)


def test_failed_checkin_does_not_consume_or_record():
    """Personhood geçersizse QR tüketilmez ve katılım yazılmaz."""
    _, good = make_person()
    ch = _challenge()
    with pytest.raises(CheckinError):
        verify_checkin(ch, "bozuk.token.degeri")
    r = verify_checkin(ch, good)          # aynı QR hâlâ kullanılabilir
    assert r["credential"]["event_id"] == "teknofest-2026"
