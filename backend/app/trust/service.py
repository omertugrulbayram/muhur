"""
Güven servisi — istemciye güvenmeyen katman.

İstemci yalnız İMZALI token gönderir:
  - personhood_token  (PoP, Ed25519)
  - attendance_tokens (PoA, Ed25519, sunucu kaydıyla da karşılaştırılır)
Risk olasılığı istemciden ALINMAZ; sunucudaki risk kaydından okunur.
Böylece "elle yazılmış JSON ile kendine 1.0 puan verme" saldırısı kapanır.
"""

from app.db import store
from app.poa.checkin import verify_attendance_token, CheckinError
from app.pop.verifier import verify_personhood_token, PersonhoodTokenError
from app.trust.reputation import compute_trust_score

MAX_ATTENDANCE_TOKENS = 50


class TrustInputError(Exception):
    pass


def trust_for_tokens(personhood_token: str, attendance_tokens: list[str] | None,
                     lang: str = "tr") -> dict:
    try:
        pop = verify_personhood_token(personhood_token)
    except PersonhoodTokenError as e:
        raise TrustInputError(str(e))
    subject = pop["sub"]

    tokens_in = list(attendance_tokens or [])
    if len(tokens_in) > MAX_ATTENDANCE_TOKENS:
        raise TrustInputError("too_many_attendance_tokens")

    events: set[str] = set()
    rejected: list[str] = []
    for t in tokens_in:
        try:
            att = verify_attendance_token(t, subject)
            events.add(att["event_id"])
        except CheckinError as e:
            rejected.append(str(e))

    risk = store.latest_risk(subject)
    result = compute_trust_score(pop, events, risk, rejected_attendance=len(rejected),
                                 lang="en" if lang == "en" else "tr")
    result["subject"] = subject
    result["rejected_attendance_reasons"] = rejected
    if risk:
        result["risk"] = {k: risk[k] for k in ("probability", "source", "model_version",
                                                "reasons", "created_at")}
    return result
