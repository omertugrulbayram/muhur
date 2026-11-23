"""
Token güvenlik zinciri.

Kilitlenen garantiler:
- geçerli personhood token doğrulanır; başka anahtarla imzalı, süresi dolmuş,
  yanlış issuer/audience/tür taşıyan token reddedilir;
- algoritma karıştırma saldırıları (alg=none, HS256 + açık anahtar) reddedilir;
- bir token türü başka bir türün yerine kullanılamaz;
- ham TC kimlik no hiçbir çıktıda ve veritabanında yoktur;
- kesin 15. yaş sınırı;
- PoP / PoA / takma kimlik anahtarları birbirinden ayrıdır.
"""

import base64
import json
import time
from datetime import date

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.config import settings
from app.pop.issuer import is_at_least_15, pseudonymous_subject
from app.pop.verifier import verify_personhood_token, PersonhoodTokenError
from app.poa.checkin import issue_checkin_challenge
from app.security import keys
from conftest import make_person, attend


def _claims(**over):
    now = int(time.time())
    base = {"typ": "muhur-personhood", "iss": settings.pop_issuer,
            "aud": settings.aud_personhood, "sub": "x", "verified_human": True,
            "iat": now, "exp": now + 60, "jti": "j"}
    base.update(over)
    return base


def _signed(**over):
    return jwt.encode(_claims(**over), keys.pop_private_key(), algorithm="EdDSA")


def test_valid_personhood_token_verifies():
    _, tok = make_person()
    c = verify_personhood_token(tok)
    assert c["verified_human"] is True and c["iss"] == settings.pop_issuer


def test_token_signed_with_other_ed25519_key_rejected():
    attacker = Ed25519PrivateKey.generate()
    forged = jwt.encode(_claims(), attacker, algorithm="EdDSA")
    with pytest.raises(PersonhoodTokenError, match="personhood_invalid"):
        verify_personhood_token(forged)


def test_alg_none_rejected():
    head = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b"=")
    body = base64.urlsafe_b64encode(json.dumps(_claims()).encode()).rstrip(b"=")
    with pytest.raises(PersonhoodTokenError):
        verify_personhood_token((head + b"." + body + b".").decode())


def test_hs256_with_public_key_as_secret_rejected():
    """Klasik algoritma karıştırma: açık anahtarı HMAC sırrı gibi kullanmak."""
    import hashlib
    import hmac
    pub = keys.pop_public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
    b64 = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=")
    signing_input = b64({"alg": "HS256", "typ": "JWT"}) + b"." + b64(_claims())
    sig = base64.urlsafe_b64encode(hmac.new(pub, signing_input, hashlib.sha256).digest()).rstrip(b"=")
    forged = (signing_input + b"." + sig).decode()
    with pytest.raises(PersonhoodTokenError):
        verify_personhood_token(forged)


@pytest.mark.parametrize("over,reason", [
    ({"iss": "sahte-issuer"}, "personhood_wrong_issuer"),
    ({"aud": "baska-servis"}, "personhood_wrong_audience"),
    ({"exp": int(time.time()) - 10, "iat": int(time.time()) - 100}, "personhood_expired"),
    ({"typ": "muhur-attendance"}, "personhood_wrong_type"),
    ({"verified_human": False}, "personhood_not_verified_human"),
])
def test_bad_claims_rejected(over, reason):
    with pytest.raises(PersonhoodTokenError, match=reason):
        verify_personhood_token(_signed(**over))


def test_checkin_challenge_cannot_be_used_as_personhood():
    ch, _ = issue_checkin_challenge("teknofest-2026", "demo-kulup")
    with pytest.raises(PersonhoodTokenError):
        verify_personhood_token(ch)


def test_no_raw_national_id_anywhere(tmp_path):
    nid = "98765432101"
    cred, tok = make_person(nid)
    result = attend(tok)
    assert nid not in json.dumps(cred)
    assert nid not in tok and nid not in result["attendance_token"]
    assert nid not in json.dumps(jwt.decode(tok, options={"verify_signature": False}))
    db_bytes = open(settings.db_path, "rb").read()
    assert nid.encode() not in db_bytes
    assert cred["claims"]["uniqueness_nishani"] == pseudonymous_subject(nid)


def test_exact_15th_birthday_boundary():
    today = date(2026, 8, 27)
    assert is_at_least_15(date(2011, 8, 27), today) is True
    assert is_at_least_15(date(2011, 8, 28), today) is False


def test_leap_day_birth_boundary():
    assert is_at_least_15(date(2008, 2, 29), date(2023, 2, 28)) is True


def test_keys_are_separated():
    raw = lambda k: k.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    assert raw(keys.pop_public_key()) != raw(keys.poa_public_key())
    assert settings.pseudonym_secret not in (settings.pop_signing_key_pem,
                                             settings.poa_signing_key_pem)


def test_jwks_exposes_no_private_material(client):
    body = client.get("/.well-known/muhur-keys").json()
    assert len(body["keys"]) == 2
    for k in body["keys"]:
        assert "d" not in k and k["crv"] == "Ed25519"


def test_published_key_verifies_token_independently(client):
    """Bir üçüncü taraf, yalnız yayınlanan açık anahtarla token'ı doğrulayabilir."""
    _, tok = make_person()
    jwk = next(k for k in client.get("/.well-known/muhur-keys").json()["keys"]
               if k["muhur_use"] == "personhood")
    pub = jwt.PyJWK(jwk).key
    payload = jwt.decode(tok, pub, algorithms=["EdDSA"], audience=settings.aud_personhood)
    assert payload["verified_human"] is True


def test_fail_closed_without_keys(monkeypatch):
    from app.config import Settings
    for v in ("MUHUR_POP_SIGNING_KEY", "MUHUR_POA_SIGNING_KEY", "MUHUR_PSEUDONYM_SECRET"):
        monkeypatch.delenv(v, raising=False)
    monkeypatch.setenv("APP_ENV", "demo")
    with pytest.raises(RuntimeError, match="fail-closed"):
        Settings().validate()


def test_demo_env_rejects_wildcard_cors(monkeypatch):
    from app.config import Settings
    monkeypatch.setenv("APP_ENV", "demo")
    monkeypatch.setenv("MUHUR_CORS_ORIGINS", "*")
    with pytest.raises(RuntimeError, match="CORS"):
        Settings().validate()
