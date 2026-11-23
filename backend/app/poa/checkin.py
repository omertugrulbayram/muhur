"""
PoA (Proof-of-Attendance) — Check-in + Anti-Spoofing.

Etkinlik giris noktasinda kisa omurlu, tek kullanimlik, SUNUCU-IMZALI bir challenge
(nonce) uretilir. Katilim nisani yalnizca: imza gecerli (tamper), sure dolmamis
(expiry), nonce daha once kullanilmamis (replay) ve dogrulanmis personhood token'a
bagli ise verilir.

Anahtar ayrimi: check-in challenge'i PoA secret'i ile imzalanir; personhood token
ise PoP secret'i ile (verifier tarafindan dogrulanir). Iki secret AYRIDIR (config).
"""

import time
import uuid

import jwt  # PyJWT

from app.config import settings
from app.pop.issuer import verify_personhood_token, PersonhoodTokenError

_used_nonces: set[str] = set()  # prototip: bellek. Kalici store (SQLite) -> sonraki PR.


def issue_checkin_token(event_id: str) -> str:
    """Giris noktasi icin kisa omurlu, imzali, benzersiz bir check-in challenge uretir."""
    now = int(time.time())
    payload = {
        "event_id": event_id,
        "jti": str(uuid.uuid4()),
        "iat": now,
        "exp": now + settings.checkin_ttl,
    }
    return jwt.encode(payload, settings.poa_secret, algorithm=settings.alg)


class CheckinError(Exception):
    pass


def verify_checkin(token: str, personhood_token: str, enforce_defenses: bool = True) -> dict:
    """
    Check-in token'ini dogrular ve katilim nisani uretir.
    enforce_defenses=False iken expiry ve tek-kullanim atlanir (savunmasiz 'once' durumu).
    Imza kontrolu her modda aciktir.
    """
    try:
        payload = jwt.decode(
            token, settings.poa_secret, algorithms=[settings.alg],
            options={"verify_exp": enforce_defenses},
        )
    except jwt.ExpiredSignatureError:
        raise CheckinError("expired")
    except jwt.InvalidTokenError:
        raise CheckinError("invalid_signature")

    jti = payload["jti"]

    # PoP -> PoA sunucu-tarafli baglama: ham nisan degil, imzali personhood dogrulanir.
    try:
        pop_claims = verify_personhood_token(personhood_token)
    except PersonhoodTokenError as e:
        raise CheckinError(str(e))
    subject = pop_claims.get("sub") or pop_claims.get("uniqueness_nishani")

    if enforce_defenses:
        if jti in _used_nonces:
            raise CheckinError("replay_detected")
        _used_nonces.add(jti)

    return {
        "credential_type": "ProofOfAttendance",
        "event_id": payload["event_id"],
        "bound_to": subject,
        "issued_at": int(time.time()),
    }
