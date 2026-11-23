"""
Merkezi yapılandırma — secret ayrımı ve fail-closed davranış.

Developer Handoff (bölüm 6) gereği:
- PoP ve PoA AYRI secret kullanır (tek MUHUR_SECRET dönemi biter).
- demo/production ortamında secret eksikse servis BAŞLAMAZ (fail-closed).
- development ortamında, kolay çalışsın diye, secret yoksa dev anahtarı
  kullanılır ama YÜKSEK SESLE uyarılır. Bunu kapatmak için APP_ENV=demo yeterli.
- Secret değerleri asla loglanmaz.

Not: HS256 + ayrı anahtar, deadline için yeterli. Asimetrik imza (Ed25519/ES256)
belgede P1/P2 olarak planlı; bu katman onu engellemez (kid alanı zaten taşınıyor).
"""

import os
import sys

_DEV_POP = "dev-only-pop-secret-change-me"
_DEV_POA = "dev-only-poa-secret-change-me"


def _bool(v: str | None, default: bool) -> bool:
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


class Settings:
    def __init__(self) -> None:
        self.app_env = os.environ.get("APP_ENV", "development").lower()
        self.is_dev = self.app_env == "development"
        # development'ta varsayılan olarak dev anahtarına izin ver; demo/prod'da hayır.
        self.allow_insecure_dev_keys = _bool(
            os.environ.get("ALLOW_INSECURE_DEV_KEYS"), default=self.is_dev
        )
        self.personhood_ttl = int(os.environ.get("PERSONHOOD_TTL_SECONDS", "3600"))
        self.checkin_ttl = int(os.environ.get("CHECKIN_CHALLENGE_TTL_SECONDS", "90"))

        # Sabit kimlikler (imzalı token doğrulaması için)
        self.pop_issuer = "muhur-mock-identity-provider"
        self.pop_audience = "muhur-poa"
        self.pop_kid = "pop-key-v1"
        self.alg = "HS256"

    def _secret(self, env_name: str, dev_default: str, *fallback_env: str) -> str:
        val = os.environ.get(env_name)
        # geriye dönük uyum: eski MUHUR_SECRET gibi isimler fallback olarak kabul
        for fb in fallback_env:
            if not val:
                val = os.environ.get(fb)
        if val:
            return val
        if self.allow_insecure_dev_keys:
            sys.stderr.write(
                f"[MÜHÜR][UYARI] {env_name} tanımlı değil — GEÇİCİ dev anahtarı "
                f"kullanılıyor. Üretim/demo için APP_ENV=demo ile fail-closed olur.\n"
            )
            return dev_default
        raise RuntimeError(
            f"[MÜHÜR] {env_name} tanımlı değil ve APP_ENV={self.app_env} "
            f"(fail-closed). Secret'ı ortam değişkeni olarak verin."
        )

    @property
    def pop_secret(self) -> str:
        return self._secret("MUHUR_POP_SECRET", _DEV_POP)

    @property
    def poa_secret(self) -> str:
        # eski tek-secret kurulumlar bozulmasın diye MUHUR_SECRET fallback'i
        return self._secret("MUHUR_POA_SECRET", _DEV_POA, "MUHUR_SECRET")

    def validate(self) -> None:
        """Startup'ta çağrılır: demo/prod'da secret eksikse burada patlar (fail-closed)."""
        _ = self.pop_secret
        _ = self.poa_secret
        if self.pop_secret == self.poa_secret:
            raise RuntimeError("[MÜHÜR] PoP ve PoA secret'ları AYNI olamaz (anahtar ayrımı).")


settings = Settings()
