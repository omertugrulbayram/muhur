"""
PoA Anti-Spoofing — Saldırı Koşumu (attack harness).

Bu script, üç saldırıyı SAVUNMA KAPALI ("önce") ve SAVUNMA AÇIK ("sonra")
durumlarında koşup sonucu tablo olarak basar. Rapordaki "saldırı başarı oranı
(önlem öncesi / sonrası)" tablosunun gerçek kaynağı budur.

Çalıştırma (backend/ klasöründen):
    python -m attack_harness.replay_attack
(veya proje kökünden:  python attack_harness/replay_attack.py  — path ayarıyla)
"""

import sys
import os
import time

# backend/ klasörünü path'e ekle ki 'app' import edilebilsin
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import jwt
from app.poa import checkin as poa
from app.pop import issuer as pop

def _valid_personhood_token():
    credential = pop.issue_personhood_credential("test-id", 1999)
    return pop.issue_personhood_token(credential)

NISHANI = _valid_personhood_token()  # artik gecerli, imzali bir personhood token


def try_checkin(token, enforce):
    """Bir check-in dener. Başarılıysa True, engellendiyse False döner."""
    try:
        poa.verify_checkin(token, NISHANI, enforce_defenses=enforce)
        return True   # saldırı BAŞARILI (kötü)
    except poa.CheckinError:
        return False  # saldırı ENGELLENDİ (iyi)


def replay_attack(enforce):
    """Aynı QR'ı iki kez okut (replay)."""
    poa._used_nonces.clear()
    token = poa.issue_checkin_token("teknofest-2026")
    try_checkin(token, enforce)              # 1. (meşru) giriş
    return try_checkin(token, enforce)       # 2. (replay) — başarılı olursa açık var


def tamper_attack(enforce):
    """İmzayı bozulmuş (sahte) bir token dene."""
    poa._used_nonces.clear()
    token = poa.issue_checkin_token("teknofest-2026")
    forged = token[:-3] + ("aaa" if not token.endswith("aaa") else "bbb")
    return try_checkin(forged, enforce)


def expiry_attack(enforce):
    """Süresi dolmuş bir token'ı yeniden kullan."""
    poa._used_nonces.clear()
    now = int(time.time())
    expired = jwt.encode(
        {"event_id": "teknofest-2026", "jti": "eski-nonce", "iat": now - 1000, "exp": now - 500},
        poa._SERVER_SECRET, algorithm=poa._ALG,
    )
    return try_checkin(expired, enforce)


def main():
    attacks = [
        ("Replay (QR tekrar okutma)", replay_attack),
        ("Tamper (sahte imza)", tamper_attack),
        ("Expiry (suresi dolmus QR)", expiry_attack),
    ]
    print("\n  PoA Anti-Spoofing — Saldiri Sonuclari\n")
    print(f"  {'Saldiri':<32}{'Onlem ONCESI':<16}{'Onlem SONRASI'}")
    print("  " + "-" * 62)
    for name, fn in attacks:
        before = "BASARILI" if fn(enforce=False) else "engellendi"
        after = "BASARILI" if fn(enforce=True) else "engellendi"
        print(f"  {name:<32}{before:<16}{after}")
    print("\n  Yorum: Onlemler ACIK iken tum saldirilar engellenir.\n")


if __name__ == "__main__":
    main()
