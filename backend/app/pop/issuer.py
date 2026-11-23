"""
PoP (Proof-of-Personhood) — Mock Issuer.

DİKKAT: Bu bir SİMÜLASYONDUR. Gerçek e-Devlet entegrasyonu YOKTUR.
Standarda (W3C VC / SD-JWT mantığı) uygun bir referans akışı taklit eder.

Mahremiyet ilkesi (KVKK — veri minimizasyonu):
- TC kimlik numarası ASLA credential/token çıktısına veya kalıcı depolamaya yazılmaz.
- Yalnızca geri döndürülemez, KARARLI TAKMA KİMLİKLİ (pseudonymous) bir benzersizlik
  nişanı taşınır. Bu nişan tek yönlü HMAC-SHA256 ile üretilir: nişandan kimlik
  yeniden ÜRETİLEMEZ. (Not: secret'ı tutan sunucu aynı kişiyi tanıyabileceği için
  bu "unlinkable" DEĞİL, "pseudonymous"tur — dürüst terim budur.)
- Seçmeli açıklama: yalnızca gereken özellik ("15+" gibi) taşınır; doğum tarihi taşınmaz.
"""

import hmac
import hashlib
import time
import uuid
from datetime import date

import jwt  # PyJWT

from app.config import settings
# Doğrulama artık verifier.py'de; geriye dönük uyum için buradan da dışa aktarılır.
from app.pop.verifier import verify_personhood_token, PersonhoodTokenError  # noqa: F401


def pseudonymous_subject(national_id: str) -> str:
    """
    TC kimlik no'dan geri döndürülemez, kararlı takma kimlikli benzersizlik nişanı üretir.
    Aynı kişi -> aynı nişan (Sybil engeli). Nişan -> kimlik ASLA (tek yönlü HMAC).
    TC kimlik burada YALNIZCA hesaplama için kullanılır, HİÇBİR YERE yazılmaz.
    """
    digest = hmac.new(settings.pop_secret.encode(), national_id.encode(), hashlib.sha256)
    return digest.hexdigest()


# Geriye dönük uyum: eski isimle çağıran kod/testler bozulmasın.
uniqueness_nishani = pseudonymous_subject


def is_at_least_15(birth_date: date, today: date | None = None) -> bool:
    """
    Kesin yaş kontrolü. 'current_year - birth_year >= 15' hatalıydı: yılın doğum
    günü gelmemiş kısmında yanlış True üretiyordu. Bu fonksiyon gerçek 15. yaş
    gününü baz alır. 29 Şubat gibi edge case'ler de ele alınır.
    """
    today = today or date.today()
    try:
        fifteenth = birth_date.replace(year=birth_date.year + 15)
    except ValueError:  # 29 Şubat -> 15 yıl sonra yoksa 28 Şubat'a çek
        fifteenth = birth_date.replace(year=birth_date.year + 15, day=28)
    return today >= fifteenth


def _parse_birth(birth_date, birth_year) -> tuple[bool, str]:
    """over_15 booleanını üretir. Tercih: birth_date (kesin). Legacy: birth_year (yaklaşık)."""
    if birth_date is not None:
        bd = birth_date if isinstance(birth_date, date) else date.fromisoformat(str(birth_date))
        return is_at_least_15(bd), "exact"
    if birth_year is not None:
        # Legacy yol (geriye dönük uyum): yalnız yıl bilindiğinde yaklaşık.
        return (time.gmtime().tm_year - int(birth_year)) >= 15, "approx"
    raise ValueError("birth_date veya birth_year gerekli")


def issue_personhood_credential(national_id: str, birth_year: int | None = None,
                                birth_date=None) -> dict:
    """
    Mock issuer: bir 'doğrulanmış insan' credential'ı üretir.
    national_id yalnız nişan hesaplanır hesaplanmaz düşürülür; SAKLANMAZ.
    Doğum tarihi credential'a YAZILMAZ; yalnız over_15 boolean'ı taşınır.
    """
    over_15, _mode = _parse_birth(birth_date, birth_year)
    return {
        "credential_type": "ProofOfPersonhood",
        "issuer": f"mock://{settings.pop_issuer}",   # dürüstlük: simülasyon
        "simulated": True,
        "claims": {
            "verified_human": True,
            "uniqueness_nishani": pseudonymous_subject(national_id),  # pseudonymous
            "over_15": over_15,
        },
        "issued_at": int(time.time()),
    }


def issue_personhood_token(credential: dict) -> str:
    """
    PoP tarafından imzalanan, kısa ömürlü personhood token üretir.
    PoA servisi ham nişan yerine BU token'ı ister ve imza/iss/aud/exp doğrular.
    Payload minimum claim seti taşır; ham kimlik alanı İÇERMEZ.
    """
    now = int(time.time())
    nishani = credential["claims"]["uniqueness_nishani"]
    payload = {
        "iss": settings.pop_issuer,
        "aud": settings.pop_audience,
        "sub": nishani,                     # pseudonymous subject
        "uniqueness_nishani": nishani,      # geriye dönük uyum (eski PoA/testler)
        "verified_human": True,
        "over_15": credential["claims"]["over_15"],
        "simulated": True,
        "iat": now,
        "exp": now + settings.personhood_ttl,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.pop_secret, algorithm=settings.alg,
                      headers={"kid": settings.pop_kid})
