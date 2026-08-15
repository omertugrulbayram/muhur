"""
NSosyal MÜHÜR — Backend API (giriş noktası).
Faz 0-1: /health + ilk PoP doğrulama ucu.

Çalıştırma (backend/ klasöründen):
    uvicorn app.main:app --reload
Sonra tarayıcıda:  http://127.0.0.1:8000/docs
"""

from fastapi import FastAPI
from pydantic import BaseModel, Field

from app.pop.issuer import issue_personhood_credential

app = FastAPI(
    title="NSosyal MÜHÜR API",
    description="Güven ve otantiklik katmanı — prototip (mock issuer, SİMÜLASYON).",
    version="0.1.0",
)


@app.get("/health")
def health():
    """Sistemin ayakta olduğunu doğrular."""
    return {"status": "ok", "service": "muhur-backend", "version": "0.1.0"}


class PopVerifyRequest(BaseModel):
    national_id: str = Field(..., description="Simülasyon girişi. GERÇEKTE saklanmaz.")
    birth_year: int = Field(..., ge=1900, le=2025)


@app.post("/pop/verify")
def pop_verify(req: PopVerifyRequest):
    """
    PoP doğrulama (SİMÜLASYON).
    Girdi olarak alınan national_id HİÇBİR YERE yazılmaz; yalnızca
    unlinkable nişan hesaplanıp credential döndürülür.
    """
    credential = issue_personhood_credential(req.national_id, req.birth_year)
    return {
        "message": "Doğrulandı (simülasyon). Kimlik bilgisi saklanmadı.",
        "credential": credential,
    }
