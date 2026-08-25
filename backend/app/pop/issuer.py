"""
PoP (Proof-of-Personhood) — Mock Issuer.

DİKKAT: Bu bir SİMÜLASYONDUR. Gerçek e-Devlet entegrasyonu YOKTUR.
Standarda (W3C VC / SD-JWT mantığı) uygun bir referans akışı taklit eder.

Mahremiyet ilkesi (KVKK — veri minimizasyonu):
- TC kimlik numarası ASLA saklanmaz.
- Yalnızca geri-döndürülemez, tuzlanmış (salted) bir "benzersizlik nişanı" saklanır.
- Bu nişandan kimlik geri üretilemez (tek yönlü HMAC-SHA256).
- Seçmeli açıklama: yalnızca gereken özellik ("15+" gibi) taşınır.
"""

import hmac
import hashlib
import os
import time

# Sunucu gizli anahtarı. Üretimde ortam değişkeninden gelir; prototipte sabit fallback.
_SERVER_SECRET = os.environ.get("MUHUR_SECRET", "dev-only-secret-change-me").encode()


def uniqueness_nishani(national_id: str) -> str:
    """
    TC kimlik no'dan geri-döndürülemez, unlinkable bir benzersizlik nişanı üretir.
    Aynı kişi -> aynı nişan (Sybil engeli). Nişan -> kimlik ASLA (tek yönlü).
    TC kimlik burada YALNIZCA hesaplama için kullanılır, HİÇBİR YERE yazılmaz.
    """
    digest = hmac.new(_SERVER_SECRET, national_id.encode(), hashlib.sha256)
    return digest.hexdigest()


def issue_personhood_credential(national_id: str, birth_year: int) -> dict:
    """
    Mock issuer: bir 'doğrulanmış insan' credential'ı üretir.
    Dönen yapı SD-JWT mantığını (seçmeli açıklama) temsil eder.
    Not: national_id yalnızca nişan hesaplanır hesaplanmaz düşürülür; saklanmaz.
    """
    current_year = time.gmtime().tm_year
    is_over_15 = (current_year - birth_year) >= 15

    return {
        "credential_type": "ProofOfPersonhood",
        "issuer": "mock://e-devlet-simulation",   # dürüstlük: bu bir simülasyon
        "simulated": True,
        "claims": {
            "verified_human": True,
            "uniqueness_nishani": uniqueness_nishani(national_id),
            # seçmeli açıklama — yalnızca boolean, doğum yılı DEĞİL:
            "over_15": is_over_15,
        },
        "issued_at": int(time.time()),
    }


# ---------------------------------------------------------------------------
# Faz 4a — PoP -> PoA sunucu-taraflı bağlama (server-side binding)
# Raporda açıkça belirtilen açığı kapatır: PoA artık istemciden gelen ham
# nişana değil, PoP'un İMZALADIĞI bir "personhood token"a güvenir.
# PoP ve PoA ayrı anahtar kullanır (anahtar ayrımı da raporda önerilmişti).
# ---------------------------------------------------------------------------

import time as _time
import jwt as _jwt

_POP_SECRET = os.environ.get("MUHUR_POP_SECRET", "dev-only-pop-secret-change-me")
_POP_ALG = "HS256"
_POP_TOKEN_TTL = 600  # 10 dakika - PoA check-in'i tamamlamak için makul süre


def issue_personhood_token(credential: dict) -> str:
    """
    PoP tarafından imzalanan, kısa ömürlü bir 'personhood token' üretir.
    PoA servisi artık ham uniqueness_nishani yerine BU token'ı ister ve
    imzasını doğrulayarak nişanın gerçekten PoP'tan geldiğini garanti eder.
    """
    now = int(_time.time())
    payload = {
        "uniqueness_nishani": credential["claims"]["uniqueness_nishani"],
        "over_15": credential["claims"]["over_15"],
        "iat": now,
        "exp": now + _POP_TOKEN_TTL,
    }
    return _jwt.encode(payload, _POP_SECRET, algorithm=_POP_ALG)


class PersonhoodTokenError(Exception):
    pass


def verify_personhood_token(token: str) -> dict:
    """PoA tarafından çağrılır. Token PoP tarafından imzalanmamışsa veya
    süresi dolmuşsa reddedilir."""
    try:
        payload = _jwt.decode(token, _POP_SECRET, algorithms=[_POP_ALG])
    except _jwt.ExpiredSignatureError:
        raise PersonhoodTokenError("personhood_token_expired")
    except _jwt.InvalidTokenError:
        raise PersonhoodTokenError("personhood_token_invalid")
    return payload
