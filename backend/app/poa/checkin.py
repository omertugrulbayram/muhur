"""
PoA (Proof-of-Attendance) — Check-in + Anti-Spoofing.

Fikir: Etkinlik giriş noktasında kısa ömürlü, tek kullanımlık, SUNUCU-İMZALI bir
QR (nonce) üretilir. Kullanıcı okuttuğunda, katılım nişanı yalnızca:
  - imza geçerliyse (tamper engeli),
  - süre dolmamışsa (expiry engeli),
  - nonce daha önce kullanılmadıysa (replay engeli),
  - ve doğrulanmış bir hesaba (PoP nişanı) bağlıysa
verilir.

Bu modül iki modu destekler:
  - enforce_defenses=True  -> tüm anti-spoofing önlemleri açık (üretim davranışı)
  - enforce_defenses=False -> savunmasız ("önce" durumu; saldırı tablosu için)
Bu sayede attack_harness, aynı saldırının önce başarılı/sonra engellenmiş
olduğunu ölçüp rapora "önce/sonra" tablosu üretebilir.
"""

import os
import time
import uuid

import jwt  # PyJWT

_SERVER_SECRET = os.environ.get("MUHUR_SECRET", "dev-only-secret-change-me")
_ALG = "HS256"
_TTL_SECONDS = 90  # QR nonce ömrü (kısa)

# Kullanılmış nonce deposu (tek kullanım). Prototipte bellek; üretimde DB/Redis.
_used_nonces: set[str] = set()


def issue_checkin_token(event_id: str) -> str:
    """Giriş noktası için kısa ömürlü, imzalı, benzersiz bir check-in QR üretir."""
    now = int(time.time())
    payload = {
        "event_id": event_id,
        "jti": str(uuid.uuid4()),   # benzersiz nonce
        "iat": now,
        "exp": now + _TTL_SECONDS,  # kısa ömür
    }
    return jwt.encode(payload, _SERVER_SECRET, algorithm=_ALG)


class CheckinError(Exception):
    pass


def verify_checkin(token: str, uniqueness_nishani: str, enforce_defenses: bool = True) -> dict:
    """
    Check-in token'ını doğrular ve katılım nişanı üretir.
    enforce_defenses=False iken expiry ve tek-kullanım kontrolleri atlanır
    (savunmasız 'önce' durumu). İmza kontrolü her zaman yapılır.
    """
    # İmza doğrulaması (tamper engeli) — her modda açık.
    try:
        payload = jwt.decode(
            token, _SERVER_SECRET, algorithms=[_ALG],
            options={"verify_exp": enforce_defenses},  # savunmasız modda exp yok sayılır
        )
    except jwt.ExpiredSignatureError:
        raise CheckinError("expired")           # expiry engeli
    except jwt.InvalidTokenError:
        raise CheckinError("invalid_signature")  # tamper engeli

    jti = payload["jti"]

    if enforce_defenses:
        # Replay engeli: nonce daha önce kullanıldı mı?
        if jti in _used_nonces:
            raise CheckinError("replay_detected")
        _used_nonces.add(jti)

    return {
        "credential_type": "ProofOfAttendance",
        "event_id": payload["event_id"],
        "bound_to": uniqueness_nishani,  # PoP kimliğine bağlı (bilet paylaşımı engeli)
        "issued_at": int(time.time()),
    }
