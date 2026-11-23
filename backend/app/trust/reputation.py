"""
Güven / İtibar Motoru (Trust & Reputation Engine).

MÜHÜR'ün BAĞLAYICI katmanı: PoP (kanıtlanmış insan), PoA (kanıtlanmış katılım)
ve Sybil/CIB modelinin ürettiği sinyali TEK bir güven skoruna (0..1) çevirir.
Şimdiye kadar bu üç parça repoda ayrı ayrı vardı ama birbirine bağlı değildi;
bu modül onları tek, açıklanabilir bir skorda toplar.

Tasarım ilkeleri
----------------
- ŞEFFAF: Skor, açıklanabilir bileşenlerin birleşimidir — kara kutu yok. Her
  skorun yanında bir "kırılım" ve insan-okunur "gerekçe" listesi döner. Bu liste,
  şeffaf keşif katmanının ("Neden bunu görüyorum?") ham verisidir.
- STATELESS / DETERMİNİSTİK: Kalıcı DB gerektirmez. Girdileri (credential'lar +
  olasılık) alır, saf biçimde skoru üretir. Aynı girdi -> her zaman aynı skor.
- İKİ EKSEN:
      kimlik      = "kimsin + ne yaptın"      (PoP + PoA)
      otantiklik  = "davranışın gerçek mi"     (1 - sybil_olasılığı)
  Güven = kimlik x otantiklik. Yani GÜÇLÜ bir kimlik bile, koordineli/sahte
  davranış (yüksek sybil olasılığı) tespit edilirse baskılanır. Bu, "gerçek insan
  != gerçek/otantik katılım" ayrımının ve CIB tezinin doğrudan icrasıdır: bir
  hesabın arkasında gerçek biri olması, o hesabın koordineli manipülasyona
  katılmadığını garanti etmez.

DÜRÜSTLÜK NOTU: Girdi credential'ları mock issuer'dan gelir (simülasyon). Skorun
kendisi gerçek ve deterministiktir; "devlet doğruladı" gibi bir iddia YOKTUR.
"""

from math import exp

# --- Ağırlıklar (şeffaf, ayarlanabilir) -------------------------------------
# Kimlik ekseni kendi içinde PoP ağırlıklı: tez "kanıtlanmış insan"ı temel alır.
W_PERSONHOOD = 0.65   # PoP: doğrulanmış, benzersiz insan olmak
W_ATTENDANCE = 0.35   # PoA: gerçek etkinliklere fiziksel katılım
assert abs((W_PERSONHOOD + W_ATTENDANCE) - 1.0) < 1e-9

# Katılım doygunluk katsayısı: her EK bağlı etkinlik azalan katkı verir
# (1 etkinlik ~0.50, 2 ~0.75, 3 ~0.88). Tek etkinlikle "maks güven" olmaz.
_ATTENDANCE_K = 0.70

# Güven bantları (keşif/eşik kararları için)
BAND_HIGH = 0.70
BAND_MEDIUM = 0.40


def _clamp01(x: float) -> float:
    return 0.0 if x < 0.0 else 1.0 if x > 1.0 else float(x)


def _personhood_component(cred: dict | None) -> tuple[float, str | None, list[str]]:
    """PoP credential'ını doğrular. Geçerliyse (skor=1, nişan, gerekçeler)."""
    reasons: list[str] = []
    if not isinstance(cred, dict):
        return 0.0, None, ["Kanıtlanmış insan (PoP) nişanı yok."]
    if cred.get("credential_type") != "ProofOfPersonhood":
        return 0.0, None, ["PoP nişanı geçersiz tipte."]

    claims = cred.get("claims") or {}
    nishani = claims.get("uniqueness_nishani")
    if claims.get("verified_human") is not True or not nishani:
        return 0.0, None, ["PoP nişanı doğrulanmış insan içermiyor."]

    reasons.append("Kanıtlanmış, benzersiz gerçek insan (PoP nişanı doğrulandı).")
    if cred.get("simulated"):
        reasons.append("(PoP kaynağı simülasyon issuer'dır.)")
    return 1.0, nishani, reasons


def _attendance_component(
    poa_list: list[dict] | None, expected_nishani: str | None
) -> tuple[float, list[str]]:
    """
    Yalnızca bu kişinin PoP nişanına BAĞLI (bound_to eşleşen) katılım
    nişanlarını sayar. Başkasına ait / bağsız nişanlar YOK sayılır (bilet
    paylaşımı & sahte katılım engeli). Aynı etkinlik iki kez sayılmaz.
    """
    reasons: list[str] = []
    if not poa_list or expected_nishani is None:
        return 0.0, ["Kanıtlanmış fiziksel katılım (PoA) yok."]

    bound_events: set[str] = set()
    unbound = 0
    for poa in poa_list:
        if not isinstance(poa, dict) or poa.get("credential_type") != "ProofOfAttendance":
            continue
        if poa.get("bound_to") == expected_nishani:
            bound_events.add(poa.get("event_id"))
        else:
            unbound += 1  # bu kişiye bağlı değil -> güvene katkı YOK

    n = len(bound_events)
    score = 1.0 - exp(-_ATTENDANCE_K * n) if n else 0.0

    if n == 0:
        reasons.append("Kanıtlanmış fiziksel katılım (PoA) yok.")
    else:
        reasons.append(f"{n} gerçek etkinliğe kanıtlanmış fiziksel katılım (PoA).")
    if unbound:
        reasons.append(
            f"{unbound} katılım nişanı bu hesaba bağlı olmadığı için sayılmadı."
        )
    return score, reasons


def _authenticity_component(sybil_probability: float) -> tuple[float, list[str]]:
    """Sybil/CIB olasılığını otantiklik ÇARPANINA çevirir (1 - p)."""
    p = _clamp01(sybil_probability)
    factor = 1.0 - p
    if p >= 0.60:
        reasons = [f"Koordineli/sahte davranış sinyali YÜKSEK (sybil olasılığı {p:.0%})."]
    elif p >= 0.30:
        reasons = [f"Koordineli davranış açısından orta risk (sybil olasılığı {p:.0%})."]
    else:
        reasons = [f"Davranış otantik görünüyor (sybil olasılığı {p:.0%})."]
    return factor, reasons


def band_of(score: float) -> str:
    if score >= BAND_HIGH:
        return "high"
    if score >= BAND_MEDIUM:
        return "medium"
    return "low"


def compute_trust_score(
    personhood_credential: dict | None,
    attendance_credentials: list[dict] | None = None,
    sybil_probability: float = 0.0,
) -> dict:
    """
    MÜHÜR güven skorunu üretir.

    Parametreler
    ------------
    personhood_credential : PoP credential (issue_personhood_credential çıktısı) veya None
    attendance_credentials: PoA credential listesi (verify_checkin çıktıları) veya None
    sybil_probability     : Sybil/CIB modelinin [0..1] koordineli-bot olasılığı
                            (0 = otantik insan, 1 = bot benzeri)

    Döner
    -----
    dict: trust_score [0..1], band, iki eksen (identity/authenticity), bileşen
          kırılımı ve "explanation" (keşif katmanının kullanacağı gerekçe listesi).
    """
    p_score, nishani, p_reasons = _personhood_component(personhood_credential)
    a_score, a_reasons = _attendance_component(attendance_credentials, nishani)
    auth_factor, auth_reasons = _authenticity_component(sybil_probability)

    # Kimlik ekseni: PoP + PoA ağırlıklı toplam ([0..1])
    identity = W_PERSONHOOD * p_score + W_ATTENDANCE * a_score
    # Güven = kimlik x otantiklik çarpanı
    trust = _clamp01(identity * auth_factor)

    return {
        "trust_score": round(trust, 4),
        "band": band_of(trust),
        "axes": {
            "identity": round(identity, 4),          # kimsin + ne yaptın
            "authenticity": round(auth_factor, 4),   # davranışın gerçek mi
        },
        "breakdown": {
            "personhood": {
                "weight": W_PERSONHOOD,
                "score": round(p_score, 4),
                "contribution": round(W_PERSONHOOD * p_score, 4),
            },
            "attendance": {
                "weight": W_ATTENDANCE,
                "score": round(a_score, 4),
                "contribution": round(W_ATTENDANCE * a_score, 4),
            },
            "authenticity": {
                "type": "multiplier",
                "factor": round(auth_factor, 4),
            },
        },
        # Şeffaf keşif katmanının ("Neden bunu görüyorum?") ham verisi:
        "explanation": p_reasons + a_reasons + auth_reasons,
    }
