"""
Güven / İtibar Motoru — saf hesaplama.

PoP (kanıtlanmış insan), PoA (kanıtlanmış katılım) ve koordineli davranış riskini
tek, açıklanabilir bir güven skoruna (0..1) çevirir.

ÖNEMLİ: Bu modül girdilerinin DOĞRULANMIŞ olduğunu varsayar. İstemciden gelen
token'ların imzasını doğrulayan ve risk değerini sunucu kaydından alan katman
`app/trust/service.py`'dir. HTTP ucu yalnız o katmanı çağırır; istemci ne
credential JSON'u ne de risk olasılığı gönderebilir.

Tasarım
- ŞEFFAF: her skorla birlikte kırılım ve insan-okunur gerekçe listesi döner.
- DETERMİNİSTİK: aynı girdi → aynı skor.
- İKİ EKSEN: kimlik (PoP + PoA) × otantiklik (1 − risk).
  Gerçek bir insanın hesabı bile koordineli davranış riski yüksekse baskılanır.
- RİSK YOKSA NÖTR: hesap için henüz davranış analizi yapılmadıysa otantiklik 1
  kabul edilir ve bu açıkça "değerlendirilmedi" diye yazılır. Analiz yokluğu
  ceza sebebi değildir.

DÜRÜSTLÜK NOTU: PoP mock issuer'dan gelir (simülasyon). Skor gerçek ve
deterministiktir; "devlet doğruladı" gibi bir iddia YOKTUR.
"""

from math import exp

W_PERSONHOOD = 0.65   # PoP: doğrulanmış, benzersiz insan olmak
W_ATTENDANCE = 0.35   # PoA: gerçek etkinliklere fiziksel katılım
assert abs((W_PERSONHOOD + W_ATTENDANCE) - 1.0) < 1e-9

# Her ek etkinlik azalan katkı verir (1 → ~0.50, 2 → ~0.75, 3 → ~0.88).
_ATTENDANCE_K = 0.70

BAND_HIGH = 0.70
BAND_MEDIUM = 0.40


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else float(x)


def band_of(score: float) -> str:
    if score >= BAND_HIGH:
        return "high"
    if score >= BAND_MEDIUM:
        return "medium"
    return "low"


def compute_trust_score(
    personhood: dict | None,
    attended_event_ids: set[str] | list[str] | None = None,
    risk: dict | None = None,
    rejected_attendance: int = 0,
) -> dict:
    """
    personhood          : doğrulanmış personhood claim'leri (verify_personhood_token çıktısı) veya None
    attended_event_ids  : bu kişiye bağlı, doğrulanmış katılım kanıtlarının etkinlikleri
    risk                : sunucudaki son risk kaydı {probability, source, reasons...} veya None
    rejected_attendance : doğrulanamadığı için sayılmayan kanıt sayısı (gerekçe için)
    """
    reasons: list[str] = []

    # --- PoP ---
    if personhood and personhood.get("verified_human") is True:
        p_score = 1.0
        reasons.append("Kanıtlanmış, benzersiz gerçek insan (imzalı PoP token'ı doğrulandı).")
        if personhood.get("simulated"):
            reasons.append("(PoP kaynağı simülasyon issuer'dır, gerçek e-Devlet değildir.)")
    else:
        p_score = 0.0
        reasons.append("Kanıtlanmış insan (PoP) token'ı yok.")

    # --- PoA ---
    events = set(attended_event_ids or []) if p_score else set()
    n = len(events)
    a_score = 1.0 - exp(-_ATTENDANCE_K * n) if n else 0.0
    if n:
        reasons.append(f"{n} gerçek etkinliğe kanıtlanmış fiziksel katılım (imzalı PoA).")
    else:
        reasons.append("Kanıtlanmış fiziksel katılım (PoA) yok.")
    if rejected_attendance:
        reasons.append(f"{rejected_attendance} katılım kanıtı doğrulanamadığı için sayılmadı.")

    # --- Otantiklik ---
    if risk is None:
        p = None
        factor = 1.0
        reasons.append("Koordineli davranış analizi bu hesap için henüz yapılmadı (nötr kabul edildi).")
    else:
        p = _clamp01(risk["probability"])
        factor = 1.0 - p
        src = " (demo amaçlı elle girilmiş değer)" if risk.get("source") == "manual-demo" else ""
        if p >= 0.60:
            reasons.append(f"Koordineli davranış sinyali yüksek (risk {p:.0%}){src}. "
                           "Bu bir yargı değildir; son karar insan incelemesindedir.")
        elif p >= 0.30:
            reasons.append(f"Koordineli davranış açısından orta risk (risk {p:.0%}){src}.")
        else:
            reasons.append(f"Davranış otantik görünüyor (risk {p:.0%}){src}.")

    identity = W_PERSONHOOD * p_score + W_ATTENDANCE * a_score
    trust = _clamp01(identity * factor)

    return {
        "trust_score": round(trust, 4),
        "band": band_of(trust),
        "axes": {"identity": round(identity, 4), "authenticity": round(factor, 4)},
        "breakdown": {
            "personhood": {"weight": W_PERSONHOOD, "score": round(p_score, 4),
                           "contribution": round(W_PERSONHOOD * p_score, 4)},
            "attendance": {"weight": W_ATTENDANCE, "score": round(a_score, 4),
                           "contribution": round(W_ATTENDANCE * a_score, 4),
                           "events": sorted(events)},
            "authenticity": {"type": "multiplier", "factor": round(factor, 4),
                             "risk_probability": None if p is None else round(p, 4),
                             "risk_source": None if risk is None else risk.get("source")},
        },
        "explanation": reasons,
    }
