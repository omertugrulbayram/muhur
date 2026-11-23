"""
MÜHÜR — Saldırı koşumu (attack harness).

Gerçek HTTP API'ye (FastAPI TestClient, geçici veritabanı, geçici anahtarlar)
karşı saldırıları sırayla dener ve sonucu tablo olarak basar. Rapordaki
"saldırı → sonuç" tablosunun kaynağı budur; sayılar elle yazılmaz.

Çalıştırma (proje kökünden):
    backend/.venv/Scripts/python attack_harness/replay_attack.py
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import tempfile
import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _pem():
    return Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()).decode()


# Koşum kendi geçici ortamında çalışır; gerçek anahtarlara/veritabanına dokunmaz.
_tmp = tempfile.mkdtemp()
os.environ.update({
    "APP_ENV": "development",
    "MUHUR_POP_SIGNING_KEY": _pem(),
    "MUHUR_POA_SIGNING_KEY": _pem(),
    "MUHUR_PSEUDONYM_SECRET": "harness-secret",
    "MUHUR_DEMO_ORGANIZER_KEY": "harness-org-key",
    "MUHUR_DB_PATH": os.path.join(_tmp, "harness.db"),
    "MUHUR_RATE_LIMIT_PER_MIN": "0",
})
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import jwt  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import store  # noqa: E402
from app.main import app  # noqa: E402
from app.security import keys  # noqa: E402

ORG = {"X-Organizer-Key": "harness-org-key"}
c = TestClient(app)
c.__enter__()


def person(nid):
    return c.post("/pop/verify", json={"national_id": nid, "birth_date": "2000-01-01"}).json()


def challenge(event="teknofest-2026"):
    return c.post("/poa/challenge", json={"event_id": event}, headers=ORG).json()["checkin_token"]


def checkin(ch, ptok):
    return c.post("/poa/checkin", json={"checkin_token": ch, "personhood_token": ptok})


def b64(d):
    return base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=")


def pop_claims(sub="sahte"):
    now = int(time.time())
    return {"typ": "muhur-personhood", "iss": settings.pop_issuer, "aud": settings.aud_personhood,
            "sub": sub, "verified_human": True, "iat": now, "exp": now + 600, "jti": "x"}


# Her saldırı True dönerse SALDIRI BAŞARILI (kötü), False dönerse ENGELLENDİ.
def a_forged_json_trust():
    fake = {"credential_type": "ProofOfPersonhood",
            "claims": {"verified_human": True, "uniqueness_nishani": "uydurma"}}
    r = c.post("/trust/score", json={"personhood_credential": fake, "sybil_probability": 0.0})
    return r.status_code == 200 and r.json().get("trust_score", 0) > 0.5


def a_client_sybil():
    p = person("1")
    r = c.post("/trust/score", json={"personhood_token": p["personhood_token"],
                                     "sybil_probability": 0.0})
    return r.status_code == 200


def a_unauth_qr():
    return c.post("/poa/challenge", json={"event_id": "teknofest-2026"}).status_code == 200


def a_other_org_qr():
    try:
        store.create_organizer("saldirgan-kulup", "Saldırgan", "saldirgan-anahtar")
    except Exception:
        pass
    r = c.post("/poa/challenge", json={"event_id": "teknofest-2026"},
               headers={"X-Organizer-Key": "saldirgan-anahtar"})
    return r.status_code == 200


def a_replay():
    ch = challenge()
    checkin(ch, person("2")["personhood_token"])
    return checkin(ch, person("3")["personhood_token"]).status_code == 200


def a_replay_after_restart():
    ch = challenge()
    checkin(ch, person("4")["personhood_token"])
    store._initialized_for = None
    store.init_db()
    return checkin(ch, person("5")["personhood_token"]).status_code == 200


def a_double_attendance():
    p = person("6")["personhood_token"]
    checkin(challenge(), p)
    return checkin(challenge(), p).status_code == 200


def a_tamper():
    ch = challenge()
    return checkin(ch[:-3] + ("aaa" if not ch.endswith("aaa") else "bbb"),
                   person("7")["personhood_token"]).status_code == 200


def a_expired():
    now = int(time.time())
    ch = jwt.encode({"typ": "muhur-checkin-challenge", "iss": settings.poa_issuer,
                     "aud": settings.aud_checkin, "event_id": "teknofest-2026", "jti": "eski",
                     "iat": now - 1000, "exp": now - 500}, keys.poa_private_key(), algorithm="EdDSA")
    return checkin(ch, person("8")["personhood_token"]).status_code == 200


def a_forged_personhood():
    tok = jwt.encode(pop_claims(), Ed25519PrivateKey.generate(), algorithm="EdDSA")
    return checkin(challenge(), tok).status_code == 200


def a_alg_none():
    tok = (b64({"alg": "none", "typ": "JWT"}) + b"." + b64(pop_claims()) + b".").decode()
    return checkin(challenge(), tok).status_code == 200


def a_alg_confusion():
    pub = keys.pop_public_key().public_bytes(serialization.Encoding.PEM,
                                             serialization.PublicFormat.SubjectPublicKeyInfo)
    si = b64({"alg": "HS256", "typ": "JWT"}) + b"." + b64(pop_claims())
    sig = base64.urlsafe_b64encode(hmac.new(pub, si, hashlib.sha256).digest()).rstrip(b"=")
    return checkin(challenge(), (si + b"." + sig).decode()).status_code == 200


def a_borrowed_attendance():
    alice, bob = person("9"), person("10")
    att = checkin(challenge(), alice["personhood_token"]).json()["attendance_token"]
    r = c.post("/trust/score", json={"personhood_token": bob["personhood_token"],
                                     "attendance_tokens": [att]}).json()
    return r["breakdown"]["attendance"]["score"] > 0


def a_forged_attendance():
    p = person("11")
    sub = p["credential"]["claims"]["uniqueness_nishani"]
    now = int(time.time())
    fakes = [jwt.encode({"typ": "muhur-attendance", "iss": settings.poa_issuer,
                         "aud": settings.aud_attendance, "sub": sub, "event_id": f"e{i}",
                         "iat": now, "exp": now + 600, "jti": f"j{i}"},
                        Ed25519PrivateKey.generate(), algorithm="EdDSA") for i in range(5)]
    r = c.post("/trust/score", json={"personhood_token": p["personhood_token"],
                                     "attendance_tokens": fakes}).json()
    return r["breakdown"]["attendance"]["score"] > 0


def a_token_type_swap():
    """QR challenge'ını personhood token yerine göndermek."""
    return checkin(challenge(), challenge()).status_code == 200


ATTACKS = [
    ("Elle yazılmış JSON kanıtla güven puanı", a_forged_json_trust),
    ("İstemcinin kendi bot olasılığını göndermesi", a_client_sybil),
    ("Anahtarsız QR üretme", a_unauth_qr),
    ("Başka kulübün etkinliğine QR üretme", a_other_org_qr),
    ("Replay (aynı QR'ı ikinci kişiyle)", a_replay),
    ("Replay (sunucu yeniden başladıktan sonra)", a_replay_after_restart),
    ("Aynı kişinin aynı etkinliğe iki kez katılması", a_double_attendance),
    ("Tamper (QR imzasını bozma)", a_tamper),
    ("Süresi dolmuş QR", a_expired),
    ("Başka anahtarla imzalı sahte kimlik", a_forged_personhood),
    ("alg=none token", a_alg_none),
    ("Algoritma karıştırma (HS256 + açık anahtar)", a_alg_confusion),
    ("Başkasının katılım kanıtını kullanma", a_borrowed_attendance),
    ("Sahte imzalı katılım kanıtı", a_forged_attendance),
    ("Token türü değiştirme (QR'ı kimlik diye gönderme)", a_token_type_swap),
]


def main():
    print("\n  MÜHÜR — Saldırı koşumu (v0.4, gerçek HTTP API)\n")
    print(f"  {'Saldırı':<52}Sonuç")
    print("  " + "-" * 66)
    blocked = 0
    for name, fn in ATTACKS:
        ok = fn()
        blocked += not ok
        print(f"  {name:<52}{'BAŞARILI (açık!)' if ok else 'engellendi'}")
    print(f"\n  {blocked}/{len(ATTACKS)} saldırı engellendi.\n")
    return 0 if blocked == len(ATTACKS) else 1


if __name__ == "__main__":
    sys.exit(main())
