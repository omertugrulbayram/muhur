"""
NSosyal MÜHÜR — Backend API (giriş noktası).
Faz 0-2: /health + PoP doğrulama + PoA check-in (anti-spoofing).

Çalıştırma (backend/ klasöründen):
    uvicorn app.main:app --reload
Sonra tarayıcıda:  http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from app.pop.issuer import issue_personhood_credential
from app.poa.checkin import issue_checkin_token, verify_checkin, CheckinError

app = FastAPI(
    title="NSosyal MÜHÜR API",
    description="Güven ve otantiklik katmanı — prototip (mock issuer, SİMÜLASYON).",
    version="0.2.0",
)


@app.get("/")
def root():
    return {"service": "NSosyal MÜHÜR API", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "muhur-backend", "version": "0.2.0"}


# ---------------- PoP ----------------
class PopVerifyRequest(BaseModel):
    national_id: str = Field(..., description="Simülasyon girişi. GERCEKTE saklanmaz.")
    birth_year: int = Field(..., ge=1900, le=2025)


@app.post("/pop/verify")
def pop_verify(req: PopVerifyRequest):
    credential = issue_personhood_credential(req.national_id, req.birth_year)
    return {"message": "Dogrulandi (simulasyon). Kimlik bilgisi saklanmadi.", "credential": credential}


# ---------------- PoA ----------------
class QrRequest(BaseModel):
    event_id: str = Field(..., description="Etkinlik kimligi, orn. 'teknofest-2026'")


@app.post("/poa/qr")
def poa_qr(req: QrRequest):
    """Giris noktasi icin kisa omurlu, imzali, tek kullanimlik check-in QR (nonce) uretir."""
    token = issue_checkin_token(req.event_id)
    return {"checkin_token": token, "note": "90 sn gecerli, tek kullanimlik, sunucu-imzali."}


class CheckinRequest(BaseModel):
    checkin_token: str
    uniqueness_nishani: str = Field(..., description="Kullanicinin PoP nisani")


@app.post("/poa/checkin")
def poa_checkin(req: CheckinRequest):
    """Check-in token'ini dogrular; gecerliyse katilim nisani verir (anti-spoofing acik)."""
    try:
        credential = verify_checkin(req.checkin_token, req.uniqueness_nishani, enforce_defenses=True)
    except CheckinError as e:
        raise HTTPException(status_code=400, detail=f"Check-in reddedildi: {e}")
    return {"message": "Katilim dogrulandi.", "credential": credential}
