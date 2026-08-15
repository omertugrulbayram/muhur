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
