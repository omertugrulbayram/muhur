"""
PoP doğrulayıcı.

PoA ve güven servisi, istemcinin gönderdiği ham bir nişana DEĞİL, PoP'un Ed25519
ile imzaladığı personhood token'a güvenir: imza + issuer + audience + tür + süre +
verified_human. Doğrulama için yalnız AÇIK anahtar gerekir.
"""

from app.config import settings
from app.security import keys, tokens

TYP_PERSONHOOD = "muhur-personhood"


class PersonhoodTokenError(Exception):
    """Personhood token geçersiz / sahte / süresi dolmuş / yanlış hedef."""


def verify_personhood_token(token: str) -> dict:
    try:
        payload = tokens.verify(
            token, keys.pop_public_key(), typ=TYP_PERSONHOOD,
            iss=settings.pop_issuer, aud=settings.aud_personhood, prefix="personhood",
        )
    except tokens.TokenError as e:
        raise PersonhoodTokenError(str(e))
    if payload.get("verified_human") is not True:
        raise PersonhoodTokenError("personhood_not_verified_human")
    return payload
