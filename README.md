# NSosyal MÜHÜR

Kanıtlanmış gerçek insan (PoP) + kanıtlanmış gerçek katılım (PoA) temelli
güven, otantiklik ve şeffaf keşif katmanı. TEKNOFEST 2026 — NSosyal İnovasyon Yarışması.

> Not: Kimlik doğrulama akışı bir **SİMÜLASYONDUR** (mock issuer). Gerçek e-Devlet
> entegrasyonu yoktur; sistem standart-uyumlu bağımsız bir referans uygulamadır.

## Kurulum (Windows)

```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Çalıştırma

```powershell
uvicorn app.main:app --reload
```

Sonra tarayıcıda:  http://127.0.0.1:8000/docs  (etkileşimli API arayüzü)
Sağlık kontrolü:   http://127.0.0.1:8000/health

## Test

```powershell
cd backend
pytest
```

## Yapı

- `backend/app/pop`  — Proof-of-Personhood (mock issuer, unlinkable nişan)
- `backend/app/poa`  — Proof-of-Attendance (QR + anti-spoofing)  [sıradaki: Faz 2]
- `backend/app/ml`   — Sybil/CIB tespit modeli
- `backend/app/trust`— güven grafiği + itibar
- `backend/app/discovery` — şeffaf keşif
- `attack_harness/`  — saldırı simülasyon scriptleri
- `docs/`            — mimari, tehdit modeli (raporun kaynağı)
