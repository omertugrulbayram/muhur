"""
Tek tip imzalı token üretimi/doğrulaması.

Her token türünün kendi `typ` değeri ve `aud` (hedef kitle) değeri vardır.
Böylece bir türün token'ı başka bir yerde kullanılamaz (ör. QR challenge'ı
katılım kanıtı yerine gönderilemez). Doğrulamada YALNIZ EdDSA kabul edilir:
"alg=none" veya "HS256 + açık anahtar" gibi algoritma karıştırma saldırıları
kendiliğinden reddedilir.
"""

import time
import uuid

import jwt  # PyJWT

from app.config import settings


class TokenError(Exception):
    """Token geçersiz. Mesaj, makine-okunur kısa bir sebep kodudur."""


def sign(private_key, kid: str, *, typ: str, iss: str, aud: str, sub: str | None,
         ttl: int, claims: dict | None = None) -> tuple[str, dict]:
    now = int(time.time())
    payload = {"typ": typ, "iss": iss, "aud": aud, "iat": now, "exp": now + ttl,
               "jti": str(uuid.uuid4())}
    if sub is not None:
        payload["sub"] = sub
    if claims:
        payload.update(claims)
    token = jwt.encode(payload, private_key, algorithm=settings.alg, headers={"kid": kid})
    return token, payload


def verify(token: str, public_key, *, typ: str, iss: str, aud: str, prefix: str,
           require_sub: bool = True) -> dict:
    if not isinstance(token, str) or not token or len(token) > 4096:
        raise TokenError(f"{prefix}_malformed")
    required = ["exp", "iat", "iss", "aud", "jti", "typ"] + (["sub"] if require_sub else [])
    try:
        payload = jwt.decode(
            token, public_key, algorithms=[settings.alg],
            audience=aud, issuer=iss, options={"require": required},
        )
    except jwt.ExpiredSignatureError:
        raise TokenError(f"{prefix}_expired")
    except jwt.InvalidAudienceError:
        raise TokenError(f"{prefix}_wrong_audience")
    except jwt.InvalidIssuerError:
        raise TokenError(f"{prefix}_wrong_issuer")
    except jwt.MissingRequiredClaimError as e:
        raise TokenError(f"{prefix}_missing_claim:{e.claim}")
    except jwt.InvalidTokenError:
        raise TokenError(f"{prefix}_invalid")  # imza, tamper, yanlış algoritma dahil
    if payload.get("typ") != typ:
        raise TokenError(f"{prefix}_wrong_type")
    return payload
