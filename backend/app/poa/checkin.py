"""
PoA (Proof-of-Attendance) — Check-in + Anti-Spoofing.

Akış:
1. Organizatör (API anahtarıyla) KENDİ etkinliği için kısa ömürlü, tek kullanımlık,
   Ed25519 imzalı bir check-in challenge'ı (QR) üretir. Etkinlik kayıtlı ve o an
   açık olmalıdır. Başkası bu QR'ı üretemez.
2. Katılımcı QR'ı okutur ve PoP'tan aldığı imzalı personhood token'ı gönderir.
3. Sunucu: QR imzası + tür + süre, etkinliğin açık olması, personhood token
   doğrulanır. Sonra TEK veritabanı işleminde QR tüketilir (replay engeli, kalıcı)
   ve katılım kaydedilir (kişi başına etkinlik başına bir kez).
4. Kişiye PoA anahtarıyla imzalı, kendi takma kimliğine bağlı bir katılım kanıtı
   (attendance token) verilir. Güven servisi yalnız bu imzalı kanıtı sayar.
"""

import time

from app.config import settings
from app.db import store
from app.pop.verifier import verify_personhood_token, PersonhoodTokenError
from app.security import keys, tokens

TYP_CHALLENGE = "muhur-checkin-challenge"
TYP_ATTENDANCE = "muhur-attendance"


class CheckinError(Exception):
    """Check-in reddedildi. Mesaj makine-okunur sebep kodudur."""


class AuthorizationError(Exception):
    """Organizatör bu işlem için yetkili değil."""


def _event_open(event: dict, now: int | None = None) -> bool:
    now = now or int(time.time())
    return event["starts_at"] <= now <= event["ends_at"]


def issue_checkin_challenge(event_id: str, organizer_id: str) -> tuple[str, dict]:
    """Yalnız etkinliğin sahibi, etkinlik açıkken QR üretebilir."""
    event = store.get_event(event_id)
    if event is None:
        raise AuthorizationError("event_not_found")
    if event["organizer_id"] != organizer_id:
        raise AuthorizationError("not_event_owner")
    if not _event_open(event):
        raise AuthorizationError("event_not_open")
    return tokens.sign(
        keys.poa_private_key(), settings.poa_kid,
        typ=TYP_CHALLENGE, iss=settings.poa_issuer, aud=settings.aud_checkin,
        sub=None, ttl=settings.checkin_ttl, claims={"event_id": event_id},
    )


def verify_checkin(checkin_token: str, personhood_token: str) -> dict:
    """QR + personhood doğrular, katılımı kalıcı kaydeder, imzalı katılım kanıtı döner."""
    try:
        ch = tokens.verify(checkin_token, keys.poa_public_key(), typ=TYP_CHALLENGE,
                           iss=settings.poa_issuer, aud=settings.aud_checkin,
                           prefix="checkin", require_sub=False)
    except tokens.TokenError as e:
        raise CheckinError(str(e))

    event_id = ch.get("event_id")
    event = store.get_event(event_id) if isinstance(event_id, str) else None
    if event is None:
        raise CheckinError("event_not_found")
    if not _event_open(event):
        raise CheckinError("event_not_open")

    try:
        pop = verify_personhood_token(personhood_token)
    except PersonhoodTokenError as e:
        raise CheckinError(str(e))
    subject = pop["sub"]

    # Kanıt önce imzalanır (henüz kimseye verilmedi), sonra aynı jti ile tek işlemde
    # QR tüketilip katılım kaydedilir. Kayıt başarısız olursa token atılır.
    att_token, att = tokens.sign(
        keys.poa_private_key(), settings.poa_kid,
        typ=TYP_ATTENDANCE, iss=settings.poa_issuer, aud=settings.aud_attendance,
        sub=subject, ttl=settings.attendance_ttl, claims={"event_id": event_id},
    )
    try:
        store.record_checkin(ch["jti"], ch["exp"], event_id, subject, att["jti"])
    except store.ReplayError:
        raise CheckinError("replay_detected")
    except store.AlreadyAttendedError:
        raise CheckinError("already_attended")

    return {
        "credential": {
            "credential_type": "ProofOfAttendance",
            "event_id": event_id,
            "event_name": event["name"],
            "bound_to": subject,
            "issued_at": att["iat"],
        },
        "attendance_token": att_token,
    }


def verify_attendance_token(token: str, expected_subject: str) -> dict:
    """İmza + tür + süre + bu kişiye ait mi + sunucu kaydında var/iptal edilmemiş mi."""
    try:
        att = tokens.verify(token, keys.poa_public_key(), typ=TYP_ATTENDANCE,
                            iss=settings.poa_issuer, aud=settings.aud_attendance,
                            prefix="attendance")
    except tokens.TokenError as e:
        raise CheckinError(str(e))
    if att["sub"] != expected_subject:
        raise CheckinError("attendance_not_bound_to_subject")
    if not store.attendance_is_valid(att["jti"], att["sub"], att.get("event_id")):
        raise CheckinError("attendance_not_on_record")
    return att
