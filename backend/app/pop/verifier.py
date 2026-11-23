"""
PoP doğrulayıcı (verifier).

PoA servisi, istemciden gelen ham bir takma-kimlik nişanına DEĞİL, PoP tarafından
imzalanmış bir personhood token'a güvenir. Bu modül o token'ı katı biçimde doğrular:
imza + doğru issuer + doğru audience + süre + verified_human claim'i.

Böylece "istemci uydursun" saldırısı (rastgele uniqueness_nishani göndermek) kapanır.
"""

import jwt  # PyJWT
from app.config import settings


class PersonhoodTokenError(Exception):
    """Personhood token geçersiz/forged/expired/yanlış hedef vb."""


def verify_personhood_token(token: str) -> dict:
    """
    PoP tarafından imzalanmış personhood token'ı doğrular ve claim'leri döner.
    Hatalıysa PersonhoodTokenError yükseltir (sebep mesajıyla).
    """
    try:
        payload = jwt.decode(
            token,
            settings.pop_secret,
            algorithms=[settings.alg],
            audience=settings.pop_audience,
            issuer=settings.pop_issuer,
            options={"require": ["exp", "iat", "iss", "aud"]},
        )
    except jwt.ExpiredSignatureError:
        raise PersonhoodTokenError("personhood_expired")
    except jwt.InvalidAudienceError:
        raise PersonhoodTokenError("personhood_wrong_audience")
    except jwt.InvalidIssuerError:
        raise PersonhoodTokenError("personhood_wrong_issuer")
    except jwt.MissingRequiredClaimError as e:
        raise PersonhoodTokenError(f"personhood_missing_claim:{e.claim}")
    except jwt.InvalidTokenError:
        raise PersonhoodTokenError("personhood_invalid")  # imza/tamper dahil

    if payload.get("verified_human") is not True:
        raise PersonhoodTokenError("personhood_not_verified_human")
    return payload
