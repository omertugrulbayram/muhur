"""
Kalıcı kayıt (SQLite).

Neden gerekli?
- Kullanılmış QR kodları (replay listesi) sunucu yeniden başlayınca SİLİNMEMELİ;
  yoksa yeniden başlatma, eski QR'ları tekrar geçerli kılar.
- "Bir kişi bir etkinliğe bir kez katılır" kuralı veritabanı UNIQUE kısıtıyla
  garanti edilir; iki eşzamanlı istek bile iki kanıt alamaz.
- Organizatörler ve etkinlikleri kayıtlıdır; QR'ı yalnız etkinliğin sahibi üretir.

Veri minimizasyonu: bu veritabanında TC kimlik no, isim, e-posta, doğum tarihi
YOKTUR. Kişi yalnızca takma kimlik (HMAC çıktısı, `subject`) ile temsil edilir.
Organizatör API anahtarları düz değil, SHA-256 özeti olarak saklanır.
"""

import hashlib
import json
import sqlite3
import time
from contextlib import contextmanager
from threading import Lock

from app.config import settings

_SCHEMA = """
CREATE TABLE IF NOT EXISTS organizers (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    api_key_hash  TEXT NOT NULL UNIQUE,
    created_at    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
    id            TEXT PRIMARY KEY,
    organizer_id  TEXT NOT NULL REFERENCES organizers(id),
    name          TEXT NOT NULL,
    starts_at     INTEGER NOT NULL,
    ends_at       INTEGER NOT NULL,
    created_at    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS consumed_challenges (
    jti           TEXT PRIMARY KEY,
    event_id      TEXT NOT NULL,
    consumed_at   INTEGER NOT NULL,
    expires_at    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS attendances (
    jti           TEXT PRIMARY KEY,           -- katılım kanıtının kimliği
    event_id      TEXT NOT NULL REFERENCES events(id),
    subject       TEXT NOT NULL,              -- takma kimlik (TC değil)
    issued_at     INTEGER NOT NULL,
    revoked       INTEGER NOT NULL DEFAULT 0,
    UNIQUE (event_id, subject)
);
CREATE TABLE IF NOT EXISTS risk_assessments (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    subject       TEXT NOT NULL,
    probability   REAL NOT NULL,
    source        TEXT NOT NULL,              -- 'model' | 'manual-demo'
    model_version TEXT,
    reasons_json  TEXT NOT NULL DEFAULT '[]',
    created_at    INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_risk_subject ON risk_assessments(subject, id);
CREATE TABLE IF NOT EXISTS alerts (
    id            TEXT PRIMARY KEY,           -- "<kampüs>-<küme>"
    organizer_id  TEXT NOT NULL REFERENCES organizers(id),
    risk          REAL NOT NULL,
    level         TEXT NOT NULL,
    status        TEXT NOT NULL DEFAULT 'acik',   -- acik | sorun_yok | izle | isaretle
    model_version TEXT NOT NULL,
    data_json     TEXT NOT NULL,
    created_at    INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS reviews (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    alert_id      TEXT NOT NULL REFERENCES alerts(id),
    organizer_id  TEXT NOT NULL,
    decision      TEXT NOT NULL,
    note          TEXT,
    created_at    INTEGER NOT NULL
);
"""

_init_lock = Lock()
_initialized_for: str | None = None


def hash_key(api_key: str) -> str:
    return hashlib.sha256(api_key.encode()).hexdigest()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.db_path, timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Şemayı oluşturur ve (varsa) demo organizatörü + etkinlikleri ekler."""
    global _initialized_for
    with _init_lock:
        conn = _connect()
        try:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript(_SCHEMA)
            _seed_demo(conn)
        finally:
            conn.close()
        _initialized_for = settings.db_path


@contextmanager
def connect():
    if _initialized_for != settings.db_path:
        init_db()
    conn = _connect()
    try:
        yield conn
    finally:
        conn.close()


def _seed_demo(conn: sqlite3.Connection) -> None:
    key = settings.demo_organizer_key
    if not key:
        return
    now = int(time.time())
    conn.execute(
        "INSERT INTO organizers(id, name, api_key_hash, created_at) VALUES (?,?,?,?) "
        "ON CONFLICT(id) DO UPDATE SET api_key_hash = excluded.api_key_hash",
        ("demo-kulup", "Demo Öğrenci Kulübü (DEMO)", hash_key(key), now),
    )
    for eid, name in (("teknofest-2026", "TEKNOFEST 2026 (DEMO)"),
                      ("hackathon-2026", "Kampüs Hackathon 2026 (DEMO)")):
        conn.execute(
            "INSERT OR IGNORE INTO events(id, organizer_id, name, starts_at, ends_at, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (eid, "demo-kulup", name, now - 3600, now + 365 * 86400, now),
        )


# ---------------- organizatör / etkinlik ----------------
def organizer_by_key(api_key: str) -> dict | None:
    with connect() as c:
        row = c.execute("SELECT id, name FROM organizers WHERE api_key_hash = ?",
                        (hash_key(api_key),)).fetchone()
    return dict(row) if row else None


def create_organizer(org_id: str, name: str, api_key: str) -> None:
    with connect() as c:
        c.execute("INSERT INTO organizers(id, name, api_key_hash, created_at) VALUES (?,?,?,?)",
                  (org_id, name, hash_key(api_key), int(time.time())))


def get_event(event_id: str) -> dict | None:
    with connect() as c:
        row = c.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    return dict(row) if row else None


def create_event(event_id: str, organizer_id: str, name: str,
                 starts_at: int, ends_at: int) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO events(id, organizer_id, name, starts_at, ends_at, created_at) "
            "VALUES (?,?,?,?,?,?)",
            (event_id, organizer_id, name, starts_at, ends_at, int(time.time())),
        )


def list_events(organizer_id: str) -> list[dict]:
    with connect() as c:
        rows = c.execute(
            "SELECT e.*, (SELECT COUNT(*) FROM attendances a "
            "             WHERE a.event_id = e.id AND a.revoked = 0) AS attendee_count "
            "FROM events e WHERE organizer_id = ? ORDER BY starts_at",
            (organizer_id,)).fetchall()
    return [dict(r) for r in rows]


# ---------------- check-in ----------------
class ReplayError(Exception):
    pass


class AlreadyAttendedError(Exception):
    pass


def record_checkin(challenge_jti: str, challenge_exp: int, event_id: str,
                   subject: str, attendance_jti: str) -> None:
    """
    QR'ı tüketir ve katılımı kaydeder — TEK işlemde (atomik).
    QR daha önce kullanıldıysa ReplayError, kişi bu etkinliğe zaten katıldıysa
    AlreadyAttendedError. Hata olursa hiçbir şey yazılmaz.
    """
    now = int(time.time())
    with connect() as c:
        c.execute("BEGIN IMMEDIATE")
        try:
            try:
                c.execute("INSERT INTO consumed_challenges(jti, event_id, consumed_at, expires_at) "
                          "VALUES (?,?,?,?)", (challenge_jti, event_id, now, challenge_exp))
            except sqlite3.IntegrityError:
                raise ReplayError()
            try:
                c.execute("INSERT INTO attendances(jti, event_id, subject, issued_at) "
                          "VALUES (?,?,?,?)", (attendance_jti, event_id, subject, now))
            except sqlite3.IntegrityError:
                raise AlreadyAttendedError()
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK")
            raise


def attendance_is_valid(attendance_jti: str, subject: str, event_id: str) -> bool:
    """Kanıt sunucunun kaydında var, bu kişiye ve etkinliğe ait ve iptal edilmemiş mi?"""
    with connect() as c:
        row = c.execute(
            "SELECT 1 FROM attendances WHERE jti = ? AND subject = ? AND event_id = ? "
            "AND revoked = 0", (attendance_jti, subject, event_id)).fetchone()
    return row is not None


# ---------------- risk değerlendirmesi ----------------
def add_risk_assessment(subject: str, probability: float, source: str,
                        model_version: str | None = None,
                        reasons: list | None = None) -> None:
    with connect() as c:
        c.execute(
            "INSERT INTO risk_assessments(subject, probability, source, model_version, "
            "reasons_json, created_at) VALUES (?,?,?,?,?,?)",
            (subject, float(probability), source, model_version,
             json.dumps(reasons or [], ensure_ascii=False), int(time.time())),
        )


def latest_risk(subject: str) -> dict | None:
    with connect() as c:
        row = c.execute(
            "SELECT * FROM risk_assessments WHERE subject = ? ORDER BY id DESC LIMIT 1",
            (subject,)).fetchone()
    if not row:
        return None
    d = dict(row)
    d["reasons"] = json.loads(d.pop("reasons_json"))
    return d


# ---------------- uyarılar ve insan incelemesi ----------------
def upsert_alert(alert_id: str, organizer_id: str, risk: float, level: str,
                 model_version: str, data: dict) -> None:
    """Uyarıyı yazar; daha önce incelenmişse durumunu ve inceleme geçmişini KORUR."""
    with connect() as c:
        c.execute(
            "INSERT INTO alerts(id, organizer_id, risk, level, model_version, data_json, created_at) "
            "VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET risk = excluded.risk, "
            "level = excluded.level, model_version = excluded.model_version, "
            "data_json = excluded.data_json",
            (alert_id, organizer_id, float(risk), level, model_version,
             json.dumps(data, ensure_ascii=False), int(time.time())),
        )


def list_alerts(organizer_id: str) -> list[dict]:
    with connect() as c:
        rows = c.execute("SELECT * FROM alerts WHERE organizer_id = ? ORDER BY risk DESC",
                         (organizer_id,)).fetchall()
    out = []
    for r in rows:
        d = dict(r)
        d["data"] = json.loads(d.pop("data_json"))
        out.append(d)
    return out


def get_alert(alert_id: str) -> dict | None:
    with connect() as c:
        r = c.execute("SELECT * FROM alerts WHERE id = ?", (alert_id,)).fetchone()
    if not r:
        return None
    d = dict(r)
    d["data"] = json.loads(d.pop("data_json"))
    return d


def add_review(alert_id: str, organizer_id: str, decision: str, note: str | None) -> dict:
    now = int(time.time())
    with connect() as c:
        c.execute("BEGIN IMMEDIATE")
        try:
            c.execute("INSERT INTO reviews(alert_id, organizer_id, decision, note, created_at) "
                      "VALUES (?,?,?,?,?)", (alert_id, organizer_id, decision, note, now))
            c.execute("UPDATE alerts SET status = ? WHERE id = ?", (decision, alert_id))
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK")
            raise
    return {"alert_id": alert_id, "decision": decision, "note": note, "created_at": now}


def list_reviews(alert_id: str) -> list[dict]:
    with connect() as c:
        rows = c.execute("SELECT decision, note, organizer_id, created_at FROM reviews "
                         "WHERE alert_id = ? ORDER BY id", (alert_id,)).fetchall()
    return [dict(r) for r in rows]


def write_analysis(organizer_id: str, alerts: list[dict], risks: list[dict]) -> None:
    """Analiz sonucunu TEK işlemde yazar (uyarılar + model risk kayıtları)."""
    now = int(time.time())
    with connect() as c:
        c.execute("BEGIN IMMEDIATE")
        try:
            c.executemany(
                "INSERT INTO alerts(id, organizer_id, risk, level, model_version, data_json, created_at) "
                "VALUES (?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET risk = excluded.risk, "
                "level = excluded.level, model_version = excluded.model_version, "
                "data_json = excluded.data_json",
                [(a["id"], organizer_id, float(a["risk"]), a["level"], a["model_version"],
                  json.dumps(a["data"], ensure_ascii=False), now) for a in alerts])
            c.executemany(
                "INSERT INTO risk_assessments(subject, probability, source, model_version, "
                "reasons_json, created_at) VALUES (?,?,?,?,?,?)",
                [(r["subject"], float(r["probability"]), "model", r["model_version"],
                  json.dumps(r["reasons"], ensure_ascii=False), now) for r in risks])
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK")
            raise
