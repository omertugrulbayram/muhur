"""
Ed25519 anahtar yönetimi.

Neden asimetrik imza? HS256'da token'ı DOĞRULAYAN taraf aynı anahtarla token
ÜRETEBİLİR. Ed25519'da yalnız özel anahtarı tutan servis imzalar; açık anahtarı
bilen herkes (başka bir topluluk, jüri, denetçi) imzayı doğrulayabilir ama
sahte token üretemez. Açık anahtarlar /.well-known/muhur-keys adresinde yayınlanır.
"""

import base64
from functools import lru_cache

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey,
)

from app.config import settings


def generate_private_pem() -> str:
    key = Ed25519PrivateKey.generate()
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


def _load(pem: str) -> Ed25519PrivateKey:
    pem = pem.strip().strip('"').replace("\\n", "\n")   # .env'de tek satır yazılmış olabilir
    key = serialization.load_pem_private_key(pem.encode(), password=None)
    if not isinstance(key, Ed25519PrivateKey):
        raise RuntimeError("[MÜHÜR] İmza anahtarı Ed25519 olmalı.")
    return key


@lru_cache(maxsize=None)
def pop_private_key() -> Ed25519PrivateKey:
    return _load(settings.pop_signing_key_pem)


@lru_cache(maxsize=None)
def poa_private_key() -> Ed25519PrivateKey:
    return _load(settings.poa_signing_key_pem)


def pop_public_key() -> Ed25519PublicKey:
    return pop_private_key().public_key()


def poa_public_key() -> Ed25519PublicKey:
    return poa_private_key().public_key()


def _b64u(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode()


def _jwk(pub: Ed25519PublicKey, kid: str, use: str) -> dict:
    raw = pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return {"kty": "OKP", "crv": "Ed25519", "x": _b64u(raw), "kid": kid,
            "alg": "EdDSA", "use": "sig", "muhur_use": use}


def jwks() -> dict:
    """Açık anahtar seti (JWKS). Özel anahtar ASLA buradan çıkmaz."""
    return {"keys": [
        _jwk(pop_public_key(), settings.pop_kid, "personhood"),
        _jwk(poa_public_key(), settings.poa_kid, "checkin+attendance"),
    ]}
