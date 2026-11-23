"""
Merkezi yapılandırma — anahtar ayrımı ve fail-closed davranış.

- PoP ve PoA AYRI Ed25519 imza anahtarı kullanır. Takma kimlik (pseudonym) için
  ayrı bir HMAC anahtarı vardır; imza anahtarı ile karıştırılmaz.
- demo/production ortamında anahtar eksikse servis BAŞLAMAZ (fail-closed).
- development ortamında anahtar verilmemişse `backend/.dev_keys/` altında bir kez
  üretilir ve yeniden kullanılır (sunucu yeniden başlayınca token'lar geçerli kalır).
  Bu klasör git'e girmez. Yüksek sesle uyarılır.
- Anahtar değerleri asla loglanmaz.

Ortam değişkenleri (hepsi .env.example'da):
    APP_ENV                      development | demo | production
    MUHUR_POP_SIGNING_KEY        Ed25519 özel anahtar (PEM metni)
    MUHUR_POA_SIGNING_KEY        Ed25519 özel anahtar (PEM metni)
    MUHUR_PSEUDONYM_SECRET       takma kimlik HMAC anahtarı
    MUHUR_DB_PATH                SQLite dosyası
    MUHUR_CORS_ORIGINS           virgülle ayrılmış izinli kökenler
    MUHUR_DEMO_ORGANIZER_KEY     demo organizatörün API anahtarı
    MUHUR_ENABLE_DEMO_ENDPOINTS  /demo/* simülasyon uçları (varsayılan: yalnız development)
    MUHUR_RATE_LIMIT_PER_MIN     IP + uç başına dakikalık istek sınırı (0 = kapalı)
"""

import os
import secrets
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
DEV_KEY_DIR = BACKEND_DIR / ".dev_keys"

_DEV_ORGANIZER_KEY = "demo-kulup-anahtari"


def _bool(v: str | None, default: bool) -> bool:
    if v is None:
        return default
    return v.strip().lower() in ("1", "true", "yes", "on")


def _warn(msg: str) -> None:
    sys.stderr.write(f"[MÜHÜR][UYARI] {msg}\n")


class Settings:
    def __init__(self) -> None:
        self.app_env = os.environ.get("APP_ENV", "development").lower()
        self.is_dev = self.app_env == "development"
        self.allow_insecure_dev_keys = _bool(
            os.environ.get("ALLOW_INSECURE_DEV_KEYS"), default=self.is_dev
        )
        self.personhood_ttl = int(os.environ.get("PERSONHOOD_TTL_SECONDS", "3600"))
        self.checkin_ttl = int(os.environ.get("CHECKIN_CHALLENGE_TTL_SECONDS", "90"))
        self.attendance_ttl = int(os.environ.get("ATTENDANCE_TTL_SECONDS", str(180 * 86400)))

        self.db_path = os.environ.get("MUHUR_DB_PATH", str(BACKEND_DIR / "muhur.db"))
        self.cors_origins = [
            o.strip() for o in os.environ.get(
                "MUHUR_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
            ).split(",") if o.strip()
        ]
        # İstek sınırı (dakikada, IP başına). 0 = kapalı.
        self.rate_limit_per_min = int(os.environ.get("MUHUR_RATE_LIMIT_PER_MIN", "60"))
        # Demo uçları (/demo/*): elle risk değeri girmek gibi SİMÜLASYON araçları.
        self.enable_demo_endpoints = _bool(
            os.environ.get("MUHUR_ENABLE_DEMO_ENDPOINTS"), default=self.is_dev
        )
        # Açılışta sentetik demo kampüsü modelle analiz et (uyarıları doldurur).
        self.demo_campus = _bool(os.environ.get("MUHUR_DEMO_CAMPUS"), default=self.is_dev)

        # Sabit kimlikler (token iss/aud/kid)
        self.pop_issuer = "muhur-mock-identity-provider"
        self.poa_issuer = "muhur-poa"
        self.aud_personhood = "muhur-poa"          # personhood token'ı PoA ve güven servisi okur
        self.aud_checkin = "muhur-checkin"         # check-in challenge (QR)
        self.aud_attendance = "muhur-trust"        # katılım kanıtı
        self.pop_kid = "pop-ed25519-v1"
        self.poa_kid = "poa-ed25519-v1"
        self.alg = "EdDSA"

        self._cache: dict[str, str] = {}

    # ---------------- gizli değerler ----------------
    def _dev_file(self, name: str, make) -> str:
        DEV_KEY_DIR.mkdir(exist_ok=True)
        path = DEV_KEY_DIR / name
        if not path.exists():
            path.write_text(make(), encoding="utf-8")
        return path.read_text(encoding="utf-8")

    def _value(self, env_name: str, dev_name: str, make) -> str:
        if env_name in self._cache:
            return self._cache[env_name]
        val = os.environ.get(env_name)
        if not val:
            if not self.allow_insecure_dev_keys:
                raise RuntimeError(
                    f"[MÜHÜR] {env_name} tanımlı değil ve APP_ENV={self.app_env} "
                    f"(fail-closed). Anahtarı ortam değişkeni olarak verin."
                )
            _warn(f"{env_name} tanımlı değil, geliştirme anahtarı kullanılıyor "
                  f"({DEV_KEY_DIR.name}/{dev_name}). Demo/üretimde APP_ENV=demo ile fail-closed olur.")
            val = self._dev_file(dev_name, make)
        self._cache[env_name] = val
        return val

    @property
    def pop_signing_key_pem(self) -> str:
        from app.security.keys import generate_private_pem
        return self._value("MUHUR_POP_SIGNING_KEY", "pop_ed25519.pem", generate_private_pem)

    @property
    def poa_signing_key_pem(self) -> str:
        from app.security.keys import generate_private_pem
        return self._value("MUHUR_POA_SIGNING_KEY", "poa_ed25519.pem", generate_private_pem)

    @property
    def pseudonym_secret(self) -> str:
        return self._value("MUHUR_PSEUDONYM_SECRET", "pseudonym.secret",
                           lambda: secrets.token_hex(32))

    @property
    def demo_organizer_key(self) -> str | None:
        val = os.environ.get("MUHUR_DEMO_ORGANIZER_KEY")
        if val:
            return val
        return _DEV_ORGANIZER_KEY if self.is_dev else None

    def validate(self) -> None:
        """Startup'ta çağrılır: demo/prod'da anahtar eksikse burada patlar (fail-closed)."""
        pop, poa = self.pop_signing_key_pem, self.poa_signing_key_pem
        _ = self.pseudonym_secret
        if pop.strip() == poa.strip():
            raise RuntimeError("[MÜHÜR] PoP ve PoA imza anahtarları AYNI olamaz (anahtar ayrımı).")
        if not self.is_dev and "*" in self.cors_origins:
            raise RuntimeError("[MÜHÜR] demo/üretimde CORS '*' olamaz.")


settings = Settings()
