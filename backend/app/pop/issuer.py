"""
PoP (Proof-of-Personhood) — Mock Issuer.

DİKKAT: Bu bir SİMÜLASYONDUR. Gerçek e-Devlet entegrasyonu YOKTUR.
W3C VC / SD-JWT mantığına uygun bir referans akışı taklit eder.

Mahremiyet (KVKK — veri minimizasyonu):
- TC kimlik no ASLA credential'a, token'a, veritabanına veya loga yazılmaz.
- Kişi, ayrı bir anahtarla (MUHUR_PSEUDONYM_SECRET) üretilen tek yönlü HMAC-SHA256
  takma kimliğiyle temsil edilir. Takma kimlikten TC geri ÜRETİLEMEZ.
  Not: anahtarı tutan sunucu aynı kişiyi tanıyabilir; bu yüzden doğru terim
  "unlinkable" değil "pseudonymous"tur.
- Seçmeli açıklama: yalnız gereken özellik ("15+") taşınır, doğum tarihi taşınmaz.
- İmza: Ed25519 (PoP'a özel anahtar). Açık anahtarla herkes doğrular, kimse taklit edemez.
"""

import hmac
import hashlib
import time
from datetime import date

from app.config import settings
from app.security import keys, tokens
# Doğrulama verifier.py'de; geriye dönük uyum için buradan da dışa aktarılır.
from app.pop.verifier import verify_personhood_token, PersonhoodTokenError  # noqa: F401

TYP_PERSONHOOD = "muhur-personhood"


def pseudonymous_subject(national_id: str) -> str:
    """TC'den kararlı, geri döndürülemez takma kimlik. Aynı kişi → aynı değer (Sybil engeli)."""
    digest = hmac.new(settings.pseudonym_secret.encode(), national_id.encode(), hashlib.sha256)
    return digest.hexdigest()


# Geriye dönük uyum
uniqueness_nishani = pseudonymous_subject


def is_at_least_15(birth_date: date, today: date | None = None) -> bool:
    """Kesin yaş kontrolü (gerçek 15. doğum günü baz alınır, 29 Şubat dahil)."""
    today = today or date.today()
    try:
        fifteenth = birth_date.replace(year=birth_date.year + 15)
    except ValueError:  # 29 Şubat → 28 Şubat
        fifteenth = birth_date.replace(year=birth_date.year + 15, day=28)
    return today >= fifteenth


def _parse_birth(birth_date, birth_year) -> bool:
    if birth_date is not None:
        bd = birth_date if isinstance(birth_date, date) else date.fromisoformat(str(birth_date))
        return is_at_least_15(bd)
    if birth_year is not None:  # legacy: yalnız yıl → yaklaşık
        return (time.gmtime().tm_year - int(birth_year)) >= 15
    raise ValueError("birth_date veya birth_year gerekli")


def issue_personhood_credential(national_id: str, birth_year: int | None = None,
                                birth_date=None) -> dict:
    """
    Gösterim amaçlı (imzasız) credential özeti. GÜVEN KARARINDA KULLANILMAZ —
    güven servisi yalnız imzalı personhood token'a bakar.
    """
    return {
        "credential_type": "ProofOfPersonhood",
        "issuer": f"mock://{settings.pop_issuer}",
        "simulated": True,
        "claims": {
            "verified_human": True,
            "uniqueness_nishani": pseudonymous_subject(national_id),
            "over_15": _parse_birth(birth_date, birth_year),
        },
        "issued_at": int(time.time()),
    }


def issue_personhood_token(credential: dict) -> str:
    """PoP'un Ed25519 ile imzaladığı kısa ömürlü personhood token. Ham kimlik İÇERMEZ."""
    claims = credential["claims"]
    token, _ = tokens.sign(
        keys.pop_private_key(), settings.pop_kid,
        typ=TYP_PERSONHOOD, iss=settings.pop_issuer, aud=settings.aud_personhood,
        sub=claims["uniqueness_nishani"], ttl=settings.personhood_ttl,
        claims={"verified_human": True, "over_15": claims["over_15"], "simulated": True},
    )
    return token
