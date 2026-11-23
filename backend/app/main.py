"""
NSosyal MÜHÜR — Backend API (giris noktasi).
Faz 0-4b: /health + PoP + PoA + /trust/score. Guvenli config + fail-closed.

Calistirma (backend/ klasorunden):
    uvicorn app.main:app --reload
"""

from typing import Optional
from datetime import date

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.config import settings
from app.pop.issuer import issue_personhood_credential, issue_personhood_token
from app.poa.checkin import issue_checkin_token, verify_checkin, CheckinError
from app.trust.reputation import compute_trust_score

app = FastAPI(
    title="NSosyal MÜHÜR API",
    description="Guven ve otantiklik katmani — prototip (mock issuer, SIMULASYON).",
    version="0.3.0",
)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)


@app.on_event("startup")
def _validate_config():
    # Fail-closed: demo/production'da secret eksikse burada patlar.
    settings.validate()


@app.get("/")
def root():
    return {"service": "NSosyal MÜHÜR API", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "muhur-backend", "version": "0.3.0",
            "environment": settings.app_env}


# ---------------- PoP ----------------
class PopVerifyRequest(BaseModel):
    national_id: str = Field(..., description="Simulasyon girisi. GERCEKTE saklanmaz.")
    # birth_date tercih edilir (kesin yas); birth_year legacy (yaklasik) — geriye donuk uyum.
    birth_date: Optional[str] = Field(None, description="YYYY-AA-GG (kesin yas)")
    birth_year: Optional[int] = Field(None, ge=1900, le=2025, description="Legacy")


@app.post("/pop/verify")
def pop_verify(req: PopVerifyRequest):
    if req.birth_date is None and req.birth_year is None:
        raise HTTPException(status_code=422, detail="birth_date veya birth_year gerekli")
    credential = issue_personhood_credential(
        req.national_id, birth_year=req.birth_year, birth_date=req.birth_date)
    personhood_token = issue_personhood_token(credential)
    return {
        "message": "Dogrulandi (simulasyon). Kimlik bilgisi saklanmadi.",
        "credential": credential,
        "personhood_token": personhood_token,
    }


# ---------------- PoA ----------------
class QrRequest(BaseModel):
    event_id: str = Field(..., description="Etkinlik kimligi, orn. 'teknofest-2026'")


@app.post("/poa/qr")
def poa_qr(req: QrRequest):
    """Kisa omurlu, imzali, tek kullanimlik check-in challenge (QR'a donusturulebilir) uretir."""
    token = issue_checkin_token(req.event_id)
    return {"checkin_token": token, "note": f"{settings.checkin_ttl}s gecerli, tek kullanimlik, sunucu-imzali."}


class CheckinRequest(BaseModel):
    checkin_token: str
    personhood_token: str = Field(..., description="PoP'tan alinan imzali kimlik token'i")


@app.post("/poa/checkin")
def poa_checkin(req: CheckinRequest):
    """Check-in token'ini dogrular; gecerliyse katilim nisani verir (anti-spoofing acik)."""
    try:
        credential = verify_checkin(req.checkin_token, req.personhood_token, enforce_defenses=True)
    except CheckinError as e:
        raise HTTPException(status_code=400, detail=f"Check-in reddedildi: {e}")
    return {"message": "Katilim dogrulandi.", "credential": credential}


# ---------------- TRUST ----------------
class TrustRequest(BaseModel):
    personhood_credential: Optional[dict] = None
    attendance_credentials: Optional[list[dict]] = None
    sybil_probability: float = Field(0.0, ge=0.0, le=1.0)


@app.post("/trust/score")
def trust_score(req: TrustRequest):
    """PoP + PoA + Sybil sinyalini tek guven skoruna cevirir (seffaf kirilimla)."""
    return compute_trust_score(
        req.personhood_credential, req.attendance_credentials, req.sybil_probability)
