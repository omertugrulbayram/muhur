"""
NSosyal MÜHÜR — Backend API.

Güvenlik ilkesi: istemciye güvenilmez. Güven kararını etkileyen her girdi
ya sunucunun imzaladığı bir token'dır ya da sunucunun kendi kaydıdır.

Çalıştırma (backend/ klasöründen):
    uvicorn app.main:app --reload
"""

import re
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, Field

from app.config import settings
from app.db import store
from app.poa.checkin import (
    AuthorizationError, CheckinError, issue_checkin_challenge, verify_checkin,
)
from app.pop.issuer import issue_personhood_credential, issue_personhood_token
from app.pop.verifier import verify_personhood_token, PersonhoodTokenError
from app.security import keys, ratelimit
from app.trust.service import TrustInputError, trust_for_tokens

VERSION = "0.4.0"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.validate()          # fail-closed: anahtar eksikse başlamaz
    store.init_db()
    yield


app = FastAPI(
    title="NSosyal MÜHÜR API",
    description="Güven ve otantiklik katmanı — prototip (PoP mock issuer, SİMÜLASYON).",
    version=VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-Organizer-Key"],
)


class Strict(BaseModel):
    """Bilinmeyen alan gönderilirse 422 — ör. istemci 'sybil_probability' gönderemez."""
    model_config = ConfigDict(extra="forbid")


_ID_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,62}$")


def require_organizer(x_organizer_key: Optional[str] = Header(None)) -> dict:
    if not x_organizer_key:
        raise HTTPException(status_code=401, detail="organizer_key_required")
    org = store.organizer_by_key(x_organizer_key)
    if org is None:
        raise HTTPException(status_code=401, detail="organizer_key_invalid")
    return org


@app.get("/")
def root():
    return {"service": "NSosyal MÜHÜR API", "docs": "/docs", "health": "/health"}


@app.get("/health")
def health():
    return {"status": "ok", "service": "muhur-backend", "version": VERSION,
            "environment": settings.app_env, "signing": settings.alg,
            "demo_endpoints": settings.enable_demo_endpoints}


@app.get("/.well-known/muhur-keys")
def public_keys():
    """Açık anahtarlar: herkes MÜHÜR token'larını bağımsız doğrulayabilir."""
    return keys.jwks()


# ---------------- PoP ----------------
class PopVerifyRequest(Strict):
    national_id: str = Field(..., min_length=1, max_length=64,
                             description="Simülasyon girişi. Saklanmaz, loglanmaz.")
    birth_date: Optional[str] = Field(None, description="YYYY-AA-GG (kesin yaş)")
    birth_year: Optional[int] = Field(None, ge=1900, le=2025, description="Legacy")


@app.post("/pop/verify", dependencies=[Depends(ratelimit.limit)])
def pop_verify(req: PopVerifyRequest):
    if req.birth_date is None and req.birth_year is None:
        raise HTTPException(status_code=422, detail="birth_date veya birth_year gerekli")
    try:
        credential = issue_personhood_credential(
            req.national_id, birth_year=req.birth_year, birth_date=req.birth_date)
    except ValueError:
        raise HTTPException(status_code=422, detail="birth_date biçimi YYYY-AA-GG olmalı")
    return {
        "message": "Doğrulandı (simülasyon). Kimlik bilgisi saklanmadı.",
        "credential": credential,
        "personhood_token": issue_personhood_token(credential),
    }


# ---------------- Organizatör ----------------
class EventCreate(Strict):
    event_id: str = Field(..., description="küçük harf, rakam, tire: 'bahar-senligi-2027'")
    name: str = Field(..., min_length=2, max_length=120)
    starts_at: int = Field(..., description="Unix zaman (sn)")
    ends_at: int


@app.get("/organizer/me")
def organizer_me(org: dict = Depends(require_organizer)):
    return org


@app.get("/organizer/events")
def organizer_events(org: dict = Depends(require_organizer)):
    return {"events": store.list_events(org["id"])}


@app.post("/organizer/events", status_code=201)
def organizer_create_event(req: EventCreate, org: dict = Depends(require_organizer)):
    if not _ID_RE.match(req.event_id):
        raise HTTPException(status_code=422, detail="event_id_format")
    if req.ends_at <= req.starts_at:
        raise HTTPException(status_code=422, detail="ends_before_start")
    if store.get_event(req.event_id):
        raise HTTPException(status_code=409, detail="event_exists")
    store.create_event(req.event_id, org["id"], req.name, req.starts_at, req.ends_at)
    return store.get_event(req.event_id)


# ---------------- PoA ----------------
class ChallengeRequest(Strict):
    event_id: str


def _challenge(req: ChallengeRequest, org: dict) -> dict:
    try:
        token, payload = issue_checkin_challenge(req.event_id, org["id"])
    except AuthorizationError as e:
        code = 404 if str(e) == "event_not_found" else 403
        raise HTTPException(status_code=code, detail=str(e))
    return {"checkin_token": token, "expires_at": payload["exp"],
            "note": f"{settings.checkin_ttl} sn geçerli, tek kullanımlık, Ed25519 imzalı."}


@app.post("/poa/challenge")
def poa_challenge(req: ChallengeRequest, org: dict = Depends(require_organizer)):
    """Organizatör, KENDİ açık etkinliği için QR'a dönüştürülecek challenge üretir."""
    return _challenge(req, org)


@app.post("/poa/qr", deprecated=True)
def poa_qr(req: ChallengeRequest, org: dict = Depends(require_organizer)):
    """Eski ad. /poa/challenge ile aynı; artık organizatör anahtarı ister."""
    return _challenge(req, org)


class CheckinRequest(Strict):
    checkin_token: str
    personhood_token: str


@app.post("/poa/checkin", dependencies=[Depends(ratelimit.limit)])
def poa_checkin(req: CheckinRequest):
    try:
        result = verify_checkin(req.checkin_token, req.personhood_token)
    except CheckinError as e:
        code = 409 if str(e) in ("replay_detected", "already_attended") else 400
        raise HTTPException(status_code=code, detail=f"Check-in reddedildi: {e}")
    return {"message": "Katılım doğrulandı.", **result}


# ---------------- Güven ----------------
class TrustRequest(Strict):
    personhood_token: str
    attendance_tokens: list[str] = Field(default_factory=list)


@app.post("/trust/score")
def trust_score(req: TrustRequest):
    """Yalnız imzalı token'larla çalışır. Risk değeri sunucu kaydından gelir."""
    try:
        return trust_for_tokens(req.personhood_token, req.attendance_tokens)
    except TrustInputError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ---------------- Demo (SİMÜLASYON) ----------------
class DemoRisk(Strict):
    personhood_token: str
    probability: float = Field(..., ge=0.0, le=1.0)
    note: Optional[str] = Field(None, max_length=200)


@app.post("/demo/risk")
def demo_set_risk(req: DemoRisk, org: dict = Depends(require_organizer)):
    """
    SİMÜLASYON: model bağlanana kadar demo hesaplara elle risk değeri yazar.
    Yalnız demo uçları açıkken ve organizatör anahtarıyla çalışır. Kayıt
    'manual-demo' kaynağıyla işaretlenir ve güven gerekçesinde böyle görünür.
    """
    if not settings.enable_demo_endpoints:
        raise HTTPException(status_code=404, detail="Not Found")
    try:
        pop = verify_personhood_token(req.personhood_token)
    except PersonhoodTokenError as e:
        raise HTTPException(status_code=400, detail=str(e))
    reasons = [req.note] if req.note else []
    store.add_risk_assessment(pop["sub"], req.probability, "manual-demo", None, reasons)
    return {"subject": pop["sub"], "probability": req.probability, "source": "manual-demo",
            "set_by": org["id"], "at": int(time.time())}
