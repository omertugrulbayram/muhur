"""
Test ortamı: her test için ayrı geçici SQLite + testlere özel Ed25519 anahtarları.
Gerçek .dev_keys/ ya da muhur.db dosyalarına dokunulmaz.
"""

import os
import tempfile

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def _pem() -> str:
    return Ed25519PrivateKey.generate().private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption()).decode()


os.environ["APP_ENV"] = "development"
os.environ["MUHUR_POP_SIGNING_KEY"] = _pem()
os.environ["MUHUR_POA_SIGNING_KEY"] = _pem()
os.environ["MUHUR_PSEUDONYM_SECRET"] = "test-pseudonym-secret"
os.environ["MUHUR_DEMO_ORGANIZER_KEY"] = "test-org-key"
os.environ["MUHUR_RATE_LIMIT_PER_MIN"] = "0"
os.environ["MUHUR_DB_PATH"] = os.path.join(tempfile.mkdtemp(), "boot.db")

import pytest  # noqa: E402

from app.config import settings  # noqa: E402
from app.db import store  # noqa: E402
from app.security import ratelimit  # noqa: E402

ORG_KEY = "test-org-key"


@pytest.fixture(autouse=True)
def fresh_db(tmp_path):
    settings.db_path = str(tmp_path / "muhur_test.db")
    store.init_db()
    ratelimit.reset()
    yield


@pytest.fixture
def client():
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def org_headers():
    return {"X-Organizer-Key": ORG_KEY}


def make_person(nid="12345678901", birth_date="2000-01-01"):
    from app.pop.issuer import issue_personhood_credential, issue_personhood_token
    cred = issue_personhood_credential(nid, birth_date=birth_date)
    return cred, issue_personhood_token(cred)


def attend(ptoken, event_id="teknofest-2026"):
    from app.poa.checkin import issue_checkin_challenge, verify_checkin
    ch, _ = issue_checkin_challenge(event_id, "demo-kulup")
    return verify_checkin(ch, ptoken)
