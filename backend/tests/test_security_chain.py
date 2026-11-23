"""
Güvenlik zinciri testleri (Developer Handoff bölüm 4.7 / 19.1).

Kilitlenen garantiler:
- geçerli personhood token doğrulanır; forged/expired/wrong-issuer/wrong-audience reddedilir;
- verified_human=false ise PoA kabul etmez;
- ham national_id credential/token payload'ında bulunmaz;
- kesin 15. yaş sınırı doğru çalışır (bir gün önce 15 değil, doğum gününde 15+);
- PoP ve PoA ayrı secret kullanır.
"""

import time
from datetime import date

import jwt
import pytest

from app.config import settings
from app.pop.issuer import (
    issue_personhood_credential, issue_personhood_token,
    is_at_least_15, pseudonymous_subject,
)
from app.pop.verifier import verify_personhood_token, PersonhoodTokenError
from app.poa.checkin import issue_checkin_token, verify_checkin, CheckinError


def _cred(nid="12345678901", birth_date="2000-01-01"):
    return issue_personhood_credential(nid, birth_date=birth_date)


# ---------------- PoP token doğrulama ----------------
def test_valid_personhood_token_verifies():
    tok = issue_personhood_token(_cred())
    claims = verify_personhood_token(tok)
    assert claims["verified_human"] is True
    assert claims["iss"] == settings.pop_issuer
    assert claims["aud"] == settings.pop_audience


def test_forged_signature_rejected():
    tok = issue_personhood_token(_cred())
    # secret'i bilmeyen biri imzalarsa
    forged = jwt.encode({**verify_personhood_token(tok)}, "baska-secret", algorithm="HS256")
    with pytest.raises(PersonhoodTokenError):
        verify_personhood_token(forged)


def test_wrong_issuer_rejected():
    now = int(time.time())
    bad = jwt.encode(
        {"iss": "sahte-issuer", "aud": settings.pop_audience, "sub": "x",
         "verified_human": True, "iat": now, "exp": now + 60},
        settings.pop_secret, algorithm="HS256")
    with pytest.raises(PersonhoodTokenError):
        verify_personhood_token(bad)


def test_wrong_audience_rejected():
    now = int(time.time())
    bad = jwt.encode(
        {"iss": settings.pop_issuer, "aud": "baska-servis", "sub": "x",
         "verified_human": True, "iat": now, "exp": now + 60},
        settings.pop_secret, algorithm="HS256")
    with pytest.raises(PersonhoodTokenError):
        verify_personhood_token(bad)


def test_expired_personhood_rejected():
    now = int(time.time())
    bad = jwt.encode(
        {"iss": settings.pop_issuer, "aud": settings.pop_audience, "sub": "x",
         "verified_human": True, "iat": now - 100, "exp": now - 10},
        settings.pop_secret, algorithm="HS256")
    with pytest.raises(PersonhoodTokenError):
        verify_personhood_token(bad)


def test_verified_human_false_rejected_by_poa():
    now = int(time.time())
    tok = jwt.encode(
        {"iss": settings.pop_issuer, "aud": settings.pop_audience, "sub": "x",
         "verified_human": False, "iat": now, "exp": now + 60},
        settings.pop_secret, algorithm="HS256")
    checkin = issue_checkin_token("teknofest-2026")
    with pytest.raises(CheckinError):
        verify_checkin(checkin, tok)


# ---------------- Mahremiyet ----------------
def test_no_raw_national_id_in_outputs():
    nid = "12345678901"
    cred = issue_personhood_credential(nid, birth_date="2000-01-01")
    tok = issue_personhood_token(cred)
    assert nid not in str(cred)
    assert nid not in tok
    # nişan deterministik + tek yönlü (aynı girdi aynı çıktı, ham id yok)
    assert cred["claims"]["uniqueness_nishani"] == pseudonymous_subject(nid)


# ---------------- Kesin yaş ----------------
def test_exact_15th_birthday_boundary():
    today = date(2026, 8, 27)
    # tam 15. doğum günü -> 15+
    assert is_at_least_15(date(2011, 8, 27), today) is True
    # bir gün sonrası doğmuş -> henüz 15 değil
    assert is_at_least_15(date(2011, 8, 28), today) is False


def test_leap_day_birth_boundary():
    # 29 Şubat doğumlu, 15 yıl sonrası 29 Şubat yok -> 28 Şubat'a düşer
    assert is_at_least_15(date(2008, 2, 29), date(2023, 2, 28)) is True


# ---------------- Anahtar ayrımı ----------------
def test_pop_and_poa_secrets_differ():
    assert settings.pop_secret != settings.poa_secret


# ---------------- Uçtan uca (mutlu yol hâlâ çalışıyor) ----------------
def test_end_to_end_checkin_still_works():
    cred = _cred()
    tok = issue_personhood_token(cred)
    checkin = issue_checkin_token("teknofest-2026")
    poa = verify_checkin(checkin, tok, enforce_defenses=True)
    assert poa["bound_to"] == cred["claims"]["uniqueness_nishani"]
