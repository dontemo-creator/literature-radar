# -*- coding: utf-8 -*-
"""SQLite persistence: papers, per-field labels, per-user state, accounts.

Schema shape and why
--------------------
``papers``        one row per DOI: the bibliographic record, shared by every
                  field that happens to cover it.
``paper_fields``  one row per (field, DOI): the labels, relevance and
                  first-seen date *for that field*.  A paper can legitimately
                  belong to two fields with different labels, and duplicating
                  the title and abstract to express that would be wasteful.
``users``         accounts, so a phone and a laptop hitting the same server
                  share one reading state.
``user_papers``   starred / read, per user.  Keyed by DOI rather than by
                  (field, DOI): starring is about the paper, not the lens.
``sessions``      opaque tokens; the cookie never carries user data.

Other notes: one connection per thread (the HTTP server is threaded), WAL so a
background refresh never blocks a read, and the FTS5 index is maintained
explicitly on write rather than by trigger.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional

from . import config, journals
from .logging_util import get_logger

log = get_logger("store")

SCHEMA_VERSION = 2
SESSION_DAYS = 60
PBKDF2_ROUNDS = 240_000

_local = threading.local()
_write_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS papers (
    doi              TEXT PRIMARY KEY,
    title            TEXT NOT NULL,
    abstract         TEXT NOT NULL DEFAULT '',
    abstract_source  TEXT NOT NULL DEFAULT '',
    journal          TEXT NOT NULL DEFAULT '',
    journal_tier     INTEGER NOT NULL DEFAULT 3,
    journal_jif      REAL,
    publisher        TEXT NOT NULL DEFAULT '',
    authors          TEXT NOT NULL DEFAULT '',
    author_count     INTEGER NOT NULL DEFAULT 0,
    pub_date         TEXT NOT NULL DEFAULT '',
    indexed_date     TEXT NOT NULL DEFAULT '',
    volume           TEXT NOT NULL DEFAULT '',
    issue            TEXT NOT NULL DEFAULT '',
    pages            TEXT NOT NULL DEFAULT '',
    url              TEXT NOT NULL DEFAULT '',
    doc_type         TEXT NOT NULL DEFAULT '',
    is_oa            INTEGER NOT NULL DEFAULT 0,
    cited_by         INTEGER NOT NULL DEFAULT 0,
    first_seen       TEXT NOT NULL DEFAULT '',
    updated_at       TEXT NOT NULL DEFAULT '',
    abstract_tries   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_papers_pub  ON papers(pub_date DESC);
CREATE INDEX IF NOT EXISTS ix_papers_abs  ON papers(abstract_source, abstract_tries);

CREATE TABLE IF NOT EXISTS paper_fields (
    field        TEXT NOT NULL,
    doi          TEXT NOT NULL,
    labels       TEXT NOT NULL DEFAULT '{}',
    primary_node TEXT NOT NULL DEFAULT '',
    relevance    REAL NOT NULL DEFAULT 0,
    first_seen   TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (field, doi)
);
CREATE INDEX IF NOT EXISTS ix_pf_field ON paper_fields(field, first_seen DESC);
CREATE INDEX IF NOT EXISTS ix_pf_doi   ON paper_fields(doi);

CREATE TABLE IF NOT EXISTS users (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    username     TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL DEFAULT '',
    pw_hash      TEXT NOT NULL,
    pw_salt      TEXT NOT NULL,
    pw_rounds    INTEGER NOT NULL DEFAULT 240000,
    field        TEXT NOT NULL DEFAULT '',
    field_spec   TEXT NOT NULL DEFAULT '',
    created_at   TEXT NOT NULL DEFAULT '',
    last_login   TEXT NOT NULL DEFAULT '',
    prefs        TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL,
    created_at TEXT NOT NULL DEFAULT '',
    expires_at TEXT NOT NULL DEFAULT '',
    seen_at    TEXT NOT NULL DEFAULT '',
    agent      TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_sessions_user ON sessions(user_id);

CREATE TABLE IF NOT EXISTS user_papers (
    user_id  INTEGER NOT NULL,
    doi      TEXT NOT NULL,
    starred  INTEGER NOT NULL DEFAULT 0,
    read_at  TEXT NOT NULL DEFAULT '',
    noted_at TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (user_id, doi)
);
CREATE INDEX IF NOT EXISTS ix_up_star ON user_papers(user_id, starred);

CREATE TABLE IF NOT EXISTS user_marks (
    user_id    INTEGER NOT NULL,
    field      TEXT NOT NULL,
    key        TEXT NOT NULL,
    value      TEXT NOT NULL DEFAULT '',
    PRIMARY KEY (user_id, field, key)
);

CREATE TABLE IF NOT EXISTS meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS refresh_log (
    id       INTEGER PRIMARY KEY AUTOINCREMENT,
    field    TEXT NOT NULL DEFAULT '',
    started  TEXT NOT NULL DEFAULT '',
    finished TEXT NOT NULL DEFAULT '',
    ok       INTEGER NOT NULL DEFAULT 0,
    scanned  INTEGER NOT NULL DEFAULT 0,
    matched  INTEGER NOT NULL DEFAULT 0,
    added    INTEGER NOT NULL DEFAULT 0,
    updated  INTEGER NOT NULL DEFAULT 0,
    detail   TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_refresh_field ON refresh_log(field, id DESC);

CREATE TABLE IF NOT EXISTS login_attempts (
    ip   TEXT NOT NULL,
    at   TEXT NOT NULL,
    ok   INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS ix_attempts ON login_attempts(ip, at);

CREATE VIRTUAL TABLE IF NOT EXISTS papers_fts USING fts5(
    doi UNINDEXED, title, abstract, journal, authors,
    tokenize = 'unicode61 remove_diacritics 2'
);
"""

PAPER_COLUMNS = ("doi", "title", "abstract", "abstract_source", "journal", "journal_tier",
                 "journal_jif", "publisher", "authors", "author_count", "pub_date",
                 "indexed_date", "volume", "issue", "pages", "url", "doc_type", "is_oa",
                 "cited_by", "first_seen", "updated_at", "abstract_tries")

# Columns whose change means "this record was genuinely updated".
_MEANINGFUL = ("title", "abstract", "journal", "pub_date", "url", "cited_by",
               "volume", "issue", "pages")


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def conn() -> sqlite3.Connection:
    c = getattr(_local, "conn", None)
    if c is not None:
        return c
    c = sqlite3.connect(str(config.DB_PATH), timeout=30.0, isolation_level=None)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA synchronous=NORMAL")
    c.execute("PRAGMA busy_timeout=15000")
    _local.conn = c
    return c


def close() -> None:
    """Drop this thread's handle -- needed when the file itself is replaced."""
    c = getattr(_local, "conn", None)
    if c is not None:
        try:
            c.close()
        except sqlite3.Error:
            pass
        _local.conn = None


def schema_version() -> int:
    try:
        return int(meta_get("schema_version", "0") or 0)
    except ValueError:
        return 0


# ============================================================== migration ===
def _table_columns(c, table: str) -> set[str]:
    try:
        return {r["name"] for r in c.execute("PRAGMA table_info(%s)" % table)}
    except sqlite3.OperationalError:
        return set()


def _ensure_column(c, table: str, column: str, decl: str) -> bool:
    """Add a column to an existing table if it is missing.

    ``CREATE TABLE IF NOT EXISTS`` silently skips a table that already exists,
    so a v1 table keeps its old shape and any new index over a new column then
    fails.  Columns therefore have to be added explicitly.
    """
    cols = _table_columns(c, table)
    if not cols or column in cols:
        return False
    c.execute("ALTER TABLE {} ADD COLUMN {} {}".format(table, column, decl))
    log.info("added column %s.%s", table, column)
    return True


def _migrate_columns(c) -> None:
    _ensure_column(c, "refresh_log", "field", "TEXT NOT NULL DEFAULT ''")


def _migrate_v1_to_v2(c) -> None:
    """Split the single-subject v1 table into papers + paper_fields.

    v1 stored the electrolyte/theme labels and the reader's own flags directly
    on the paper row, which only works while there is exactly one field and one
    reader.  The data itself is worth keeping -- it took several minutes of
    scanning to build -- so it is moved rather than discarded.
    """
    cols = _table_columns(c, "papers")
    if not cols or "chemistry" not in cols:
        return
    log.info("migrating database from v1 to v2 ...")
    default_field = "solid-state-battery"
    rows = list(c.execute("SELECT * FROM papers"))
    c.execute("ALTER TABLE papers RENAME TO papers_v1")
    c.execute("DROP TABLE IF EXISTS papers_fts")
    _migrate_columns(c)
    c.executescript(SCHEMA)

    moved, flagged, unreadable = 0, 0, []
    for r in rows:
        rec = {k: r[k] for k in PAPER_COLUMNS if k in r.keys()}
        rec.setdefault("first_seen", r["first_seen"] if "first_seen" in r.keys() else now_iso())
        vals = [rec.get(k, _default_for(k)) for k in PAPER_COLUMNS]
        c.execute("INSERT OR REPLACE INTO papers({}) VALUES({})".format(
            ",".join(PAPER_COLUMNS), ",".join("?" * len(PAPER_COLUMNS))), vals)
        _fts_write(c, rec)
        labels = {}
        for old_key, facet in (("chemistry", "chemistry"), ("themes", "theme")):
            raw = r[old_key] if old_key in r.keys() else ""
            try:
                parsed = json.loads(raw or "[]")
            except (ValueError, TypeError):
                parsed = []
                unreadable.append(r["doi"])
            labels[facet] = parsed if isinstance(parsed, list) else []
        c.execute("INSERT OR REPLACE INTO paper_fields"
                  "(field,doi,labels,primary_node,relevance,first_seen) VALUES(?,?,?,?,?,?)",
                  (default_field, r["doi"], json.dumps(labels, ensure_ascii=False),
                   r["primary_chem"] if "primary_chem" in r.keys() else "",
                   r["relevance"] if "relevance" in r.keys() else 0.0,
                   rec.get("first_seen") or now_iso()))
        moved += 1
        starred = r["starred"] if "starred" in r.keys() else 0
        read_at = r["read_at"] if "read_at" in r.keys() else ""
        if starred or read_at:
            c.execute("INSERT OR REPLACE INTO meta(key,value) VALUES(?,?)",
                      ("legacy_flag:" + r["doi"],
                       json.dumps({"starred": int(bool(starred)), "read_at": read_at})))
            flagged += 1
    c.execute("DROP TABLE papers_v1")
    log.info("migration done: %d papers moved to field '%s', %d reader flags parked",
             moved, default_field, flagged)
    if unreadable:
        log.warning("%d papers had unreadable labels and will be re-classified: %s",
                    len(unreadable), ", ".join(unreadable[:5]))


def init() -> None:
    c = conn()
    with _write_lock:
        _migrate_v1_to_v2(c)
        _migrate_columns(c)
        c.executescript(SCHEMA)
        row = c.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
        if row is None or row["value"] != str(SCHEMA_VERSION):
            c.execute("INSERT INTO meta(key,value) VALUES('schema_version',?) "
                      "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                      (str(SCHEMA_VERSION),))
    log.info("database ready at %s (schema v%d)", config.DB_PATH, SCHEMA_VERSION)


def _bindable(value):
    """A source adapter handing us a list must not kill the whole refresh."""
    if isinstance(value, (list, tuple, set)):
        return "; ".join(str(v) for v in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return int(value)
    return value


def _default_for(key: str):
    if key == "journal_jif":
        return None
    if key in ("journal_tier", "author_count", "is_oa", "cited_by", "abstract_tries"):
        return 0
    return ""


# ==================================================================== meta ===
def meta_get(key: str, default: str = "") -> str:
    row = conn().execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
    return row["value"] if row else default


def meta_set(key: str, value: str) -> None:
    with _write_lock:
        conn().execute(
            "INSERT INTO meta(key,value) VALUES(?,?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


# ================================================================== users ===
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_.\-]{3,32}$")


def _hash_password(password: str, salt: bytes, rounds: int = PBKDF2_ROUNDS) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds).hex()


def username_problem(username: str) -> str:
    if not _USERNAME_RE.match(username or ""):
        return "用户名需为 3–32 位字母、数字、下划线、点或短横线"
    return ""


def password_problem(password: str) -> str:
    if len(password or "") < 8:
        return "密码至少 8 位"
    if len(password) > 200:
        return "密码过长"
    return ""


def user_count() -> int:
    return int(conn().execute("SELECT COUNT(*) n FROM users").fetchone()["n"])


def create_user(username: str, password: str, display_name: str = "") -> dict:
    """Create an account. Returns the user row; raises ValueError on bad input."""
    username = (username or "").strip()
    problem = username_problem(username) or password_problem(password)
    if problem:
        raise ValueError(problem)
    salt = os.urandom(16)
    pw_hash = _hash_password(password, salt)
    ts = now_iso()
    with _write_lock:
        c = conn()
        exists = c.execute("SELECT 1 FROM users WHERE username=? COLLATE NOCASE",
                           (username,)).fetchone()
        if exists:
            raise ValueError("该用户名已被占用")
        cur = c.execute(
            "INSERT INTO users(username,display_name,pw_hash,pw_salt,pw_rounds,"
            "created_at,last_login) VALUES(?,?,?,?,?,?,?)",
            (username, (display_name or username).strip()[:40], pw_hash, salt.hex(),
             PBKDF2_ROUNDS, ts, ts))
        uid = int(cur.lastrowid)
    _claim_legacy_flags(uid)
    log.info("created user %s (id=%d)", username, uid)
    return get_user(uid) or {}


def _claim_legacy_flags(user_id: int) -> int:
    """Hand the pre-account starred/read flags to the first real account."""
    c = conn()
    rows = list(c.execute("SELECT key,value FROM meta WHERE key LIKE 'legacy_flag:%'"))
    if not rows:
        return 0
    with _write_lock:
        for r in rows:
            doi = r["key"].split(":", 1)[1]
            try:
                blob = json.loads(r["value"])
            except ValueError:
                continue
            c.execute("INSERT OR REPLACE INTO user_papers(user_id,doi,starred,read_at) "
                      "VALUES(?,?,?,?)", (user_id, doi, int(blob.get("starred") or 0),
                                          blob.get("read_at") or ""))
            c.execute("DELETE FROM meta WHERE key=?", (r["key"],))
    log.info("claimed %d legacy reader flags for user %d", len(rows), user_id)
    return len(rows)


def verify_login(username: str, password: str) -> Optional[dict]:
    row = conn().execute("SELECT * FROM users WHERE username=? COLLATE NOCASE",
                         ((username or "").strip(),)).fetchone()
    if not row:
        # Spend comparable time so a missing user is not obviously faster.
        _hash_password(password or "", b"0" * 16)
        return None
    expect = row["pw_hash"]
    got = _hash_password(password or "", bytes.fromhex(row["pw_salt"]),
                         int(row["pw_rounds"] or PBKDF2_ROUNDS))
    if not hmac.compare_digest(expect, got):
        return None
    with _write_lock:
        conn().execute("UPDATE users SET last_login=? WHERE id=?", (now_iso(), row["id"]))
    return _user_row(row)


def get_user(user_id: int) -> Optional[dict]:
    row = conn().execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    return _user_row(row) if row else None


def _user_row(row) -> dict:
    try:
        prefs = json.loads(row["prefs"] or "{}")
    except ValueError:
        prefs = {}
    try:
        spec = json.loads(row["field_spec"] or "{}")
    except ValueError:
        spec = {}
    return {"id": int(row["id"]), "username": row["username"],
            "display_name": row["display_name"] or row["username"],
            "field": row["field"] or "", "field_spec": spec,
            "created_at": row["created_at"], "last_login": row["last_login"],
            "prefs": prefs}


def set_user_field(user_id: int, field_id: str, spec: Optional[dict] = None) -> None:
    with _write_lock:
        conn().execute("UPDATE users SET field=?, field_spec=? WHERE id=?",
                       (field_id, json.dumps(spec or {}, ensure_ascii=False), user_id))


def set_user_prefs(user_id: int, prefs: dict) -> None:
    with _write_lock:
        conn().execute("UPDATE users SET prefs=? WHERE id=?",
                       (json.dumps(prefs or {}, ensure_ascii=False), user_id))


def change_password(user_id: int, new_password: str) -> None:
    problem = password_problem(new_password)
    if problem:
        raise ValueError(problem)
    salt = os.urandom(16)
    with _write_lock:
        conn().execute("UPDATE users SET pw_hash=?, pw_salt=?, pw_rounds=? WHERE id=?",
                       (_hash_password(new_password, salt), salt.hex(),
                        PBKDF2_ROUNDS, user_id))
    drop_sessions_for(user_id)


def active_fields() -> list[str]:
    """Fields at least one account has chosen -- the only ones worth refreshing."""
    return [r["field"] for r in conn().execute(
        "SELECT DISTINCT field FROM users WHERE field <> ''") if r["field"]]


# =============================================================== sessions ===
def create_session(user_id: int, agent: str = "") -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc).replace(microsecond=0)
    with _write_lock:
        conn().execute("INSERT INTO sessions(token,user_id,created_at,expires_at,seen_at,"
                       "agent) VALUES(?,?,?,?,?,?)",
                       (token, user_id, now.isoformat(),
                        (now + timedelta(days=SESSION_DAYS)).isoformat(),
                        now.isoformat(), (agent or "")[:200]))
    return token


def session_user(token: str) -> Optional[dict]:
    if not token:
        return None
    row = conn().execute("SELECT * FROM sessions WHERE token=?", (token,)).fetchone()
    if not row:
        return None
    if row["expires_at"] and row["expires_at"] < now_iso():
        drop_session(token)
        return None
    if row["seen_at"][:10] != now_iso()[:10]:      # touch once a day, not per request
        with _write_lock:
            conn().execute("UPDATE sessions SET seen_at=? WHERE token=?", (now_iso(), token))
    return get_user(int(row["user_id"]))


def drop_session(token: str) -> None:
    with _write_lock:
        conn().execute("DELETE FROM sessions WHERE token=?", (token,))


def drop_sessions_for(user_id: int) -> None:
    with _write_lock:
        conn().execute("DELETE FROM sessions WHERE user_id=?", (user_id,))


def purge_expired_sessions() -> int:
    with _write_lock:
        cur = conn().execute("DELETE FROM sessions WHERE expires_at < ?", (now_iso(),))
        return cur.rowcount


def sessions_for(user_id: int) -> list[dict]:
    return [dict(r) for r in conn().execute(
        "SELECT token,created_at,expires_at,seen_at,agent FROM sessions "
        "WHERE user_id=? ORDER BY seen_at DESC", (user_id,))]


# ---- login throttling ------------------------------------------------------
def note_login_attempt(ip: str, ok: bool) -> None:
    with _write_lock:
        c = conn()
        c.execute("INSERT INTO login_attempts(ip,at,ok) VALUES(?,?,?)",
                  (ip or "?", now_iso(), 1 if ok else 0))
        c.execute("DELETE FROM login_attempts WHERE at < ?",
                  ((datetime.now(timezone.utc) - timedelta(hours=6)).isoformat(),))


def login_blocked(ip: str, limit: int = 10, window_minutes: int = 15) -> int:
    """Failed attempts from this address inside the window."""
    since = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    n = conn().execute("SELECT COUNT(*) n FROM login_attempts "
                       "WHERE ip=? AND ok=0 AND at >= ?", (ip or "?", since)).fetchone()["n"]
    return max(0, int(n) - limit + 1) if int(n) >= limit else 0


# ================================================================ writing ===
def _fts_write(c: sqlite3.Connection, rec: dict) -> None:
    c.execute("DELETE FROM papers_fts WHERE doi=?", (rec["doi"],))
    c.execute("INSERT INTO papers_fts(doi,title,abstract,journal,authors) VALUES(?,?,?,?,?)",
              (rec["doi"], rec.get("title", ""), rec.get("abstract", ""),
               rec.get("journal", ""), rec.get("authors", "")))


def upsert(field: str, rec: dict, labels: dict, primary: str, relevance: float) -> str:
    """Insert or update one paper and its labels for ``field``.

    Returns ``added`` (new to this field), ``updated`` or ``unchanged``.
    """
    doi = (rec.get("doi") or "").strip().lower()
    if not doi or not (rec.get("title") or "").strip():
        return "skipped"
    rec = {k: _bindable(v) for k, v in rec.items()}
    rec["doi"] = doi
    ts = now_iso()
    labels_json = json.dumps(labels or {}, ensure_ascii=False)

    with _write_lock:
        c = conn()
        old = c.execute("SELECT * FROM papers WHERE doi=?", (doi,)).fetchone()
        if old is None:
            rec.setdefault("first_seen", ts)
            rec["updated_at"] = ts
            c.execute("INSERT INTO papers({}) VALUES({})".format(
                ",".join(PAPER_COLUMNS), ",".join("?" * len(PAPER_COLUMNS))),
                [rec.get(k, _default_for(k)) for k in PAPER_COLUMNS])
            _fts_write(c, rec)
            paper_changed = True
        else:
            merged = {k: old[k] for k in PAPER_COLUMNS}
            for k, v in rec.items():
                if k not in PAPER_COLUMNS or k == "first_seen":
                    continue
                # Never lose an abstract we already have to a source lacking one.
                if k == "abstract" and not (v or "").strip() and (merged["abstract"] or "").strip():
                    continue
                if k == "abstract_source" and not (rec.get("abstract") or "").strip():
                    continue
                if v in (None, "") and merged.get(k) not in (None, ""):
                    continue
                merged[k] = v
            changed = [k for k in _MEANINGFUL if str(merged.get(k)) != str(old[k])]
            if changed or merged["abstract_tries"] != old["abstract_tries"]:
                merged["updated_at"] = ts
                c.execute("UPDATE papers SET {} WHERE doi=?".format(
                    ",".join("{}=?".format(k) for k in PAPER_COLUMNS if k != "doi")),
                    [merged[k] for k in PAPER_COLUMNS if k != "doi"] + [doi])
                if any(k in changed for k in ("title", "abstract", "journal")):
                    _fts_write(c, merged)
            paper_changed = bool(changed)

        pf = c.execute("SELECT * FROM paper_fields WHERE field=? AND doi=?",
                       (field, doi)).fetchone()
        if pf is None:
            c.execute("INSERT INTO paper_fields(field,doi,labels,primary_node,relevance,"
                      "first_seen) VALUES(?,?,?,?,?,?)",
                      (field, doi, labels_json, primary or "", float(relevance), ts))
            return "added"
        label_changed = (pf["labels"] != labels_json or pf["primary_node"] != (primary or "")
                         or abs(float(pf["relevance"]) - float(relevance)) > 0.01)
        if label_changed:
            c.execute("UPDATE paper_fields SET labels=?,primary_node=?,relevance=? "
                      "WHERE field=? AND doi=?",
                      (labels_json, primary or "", float(relevance), field, doi))
        return "updated" if (label_changed or paper_changed) else "unchanged"


def bump_abstract_try(doi: str) -> None:
    with _write_lock:
        conn().execute("UPDATE papers SET abstract_tries=abstract_tries+1 WHERE doi=?",
                       (doi.lower(),))


def update_paper(doi: str, **changes) -> bool:
    """Patch bibliographic columns (used by the abstract back-fill)."""
    doi = (doi or "").lower()
    fields_ = {k: _bindable(v) for k, v in changes.items()
               if k in PAPER_COLUMNS and k != "doi"}
    if not doi or not fields_:
        return False
    with _write_lock:
        c = conn()
        row = c.execute("SELECT * FROM papers WHERE doi=?", (doi,)).fetchone()
        if row is None:
            return False
        fields_["updated_at"] = now_iso()
        c.execute("UPDATE papers SET {} WHERE doi=?".format(
            ",".join("{}=?".format(k) for k in fields_)),
            list(fields_.values()) + [doi])
        if any(k in fields_ for k in ("title", "abstract", "journal", "authors")):
            merged = {k: row[k] for k in PAPER_COLUMNS}
            merged.update(fields_)
            _fts_write(c, merged)
        return True


def set_flag(user_id: int, doi: str, field_name: str, value) -> bool:
    if field_name not in ("read_at", "starred"):
        return False
    doi = (doi or "").lower()
    if not conn().execute("SELECT 1 FROM papers WHERE doi=?", (doi,)).fetchone():
        return False
    with _write_lock:
        conn().execute(
            "INSERT INTO user_papers(user_id,doi,starred,read_at) VALUES(?,?,?,?) "
            "ON CONFLICT(user_id,doi) DO UPDATE SET {}=excluded.{}".format(
                field_name, field_name),
            (user_id, doi, value if field_name == "starred" else 0,
             value if field_name == "read_at" else ""))
    return True


def user_flag_map(user_id: int, dois: Iterable[str]) -> dict[str, dict]:
    """Return map of doi -> {'starred': bool, 'read_at': str} for given user and dois."""
    dois_list = [d.lower() for d in dois if d]
    if not dois_list:
        return {}
    c = conn()
    marks = ",".join("?" * len(dois_list))
    rows = c.execute("SELECT doi, starred, read_at FROM user_papers WHERE user_id=? AND doi IN ({})".format(marks),
                     [user_id] + dois_list).fetchall()
    return {r["doi"]: {"starred": bool(r["starred"]), "read_at": r["read_at"] or ""} for r in rows}


def save_external_paper(user_id: int, rec: dict, starred: bool = True) -> bool:
    """Save an external paper into papers table and flag it in user_papers."""
    doi = (rec.get("doi") or "").strip().lower()
    if not doi or not (rec.get("title") or "").strip():
        return False
    rec = {k: _bindable(v) for k, v in rec.items()}
    rec["doi"] = doi
    ts = now_iso()
    with _write_lock:
        c = conn()
        old = c.execute("SELECT * FROM papers WHERE doi=?", (doi,)).fetchone()
        if old is None:
            rec.setdefault("first_seen", ts)
            rec["updated_at"] = ts
            c.execute("INSERT INTO papers({}) VALUES({})".format(
                ",".join(PAPER_COLUMNS), ",".join("?" * len(PAPER_COLUMNS))),
                [rec.get(k, _default_for(k)) for k in PAPER_COLUMNS])
            _fts_write(c, rec)
        if starred:
            c.execute(
                "INSERT INTO user_papers(user_id,doi,starred,read_at) VALUES(?,?,1,'') "
                "ON CONFLICT(user_id,doi) DO UPDATE SET starred=1",
                (user_id, doi))
    return True



def delete_field_papers(field: str, dois: Iterable[str]) -> int:
    """Drop papers from a field (rules tightened).  Orphans are cleaned up."""
    dois = [d.lower() for d in dois if d]
    if not dois:
        return 0
    removed = 0
    with _write_lock:
        c = conn()
        for i in range(0, len(dois), 400):
            chunk = dois[i:i + 400]
            marks = ",".join("?" * len(chunk))
            cur = c.execute("DELETE FROM paper_fields WHERE field=? AND doi IN (%s)" % marks,
                            [field] + chunk)
            removed += cur.rowcount
            orphans = [r["doi"] for r in c.execute(
                "SELECT p.doi FROM papers p LEFT JOIN paper_fields f ON f.doi=p.doi "
                "WHERE p.doi IN (%s) GROUP BY p.doi HAVING COUNT(f.doi)=0" % marks, chunk)]
            if orphans:
                om = ",".join("?" * len(orphans))
                c.execute("DELETE FROM papers WHERE doi IN (%s)" % om, orphans)
                c.execute("DELETE FROM papers_fts WHERE doi IN (%s)" % om, orphans)
    return removed


def log_refresh(**kw) -> None:
    cols = ("field", "started", "finished", "ok", "scanned", "matched", "added",
            "updated", "detail")
    ints = ("ok", "scanned", "matched", "added", "updated")
    with _write_lock:
        c = conn()
        c.execute("INSERT INTO refresh_log({}) VALUES({})".format(
            ",".join(cols), ",".join("?" * len(cols))),
            [kw.get(k, 0 if k in ints else "") for k in cols])
        c.execute("DELETE FROM refresh_log WHERE id NOT IN "
                  "(SELECT id FROM refresh_log ORDER BY id DESC LIMIT 300)")


def last_refresh(field: str = "") -> Optional[dict]:
    sql = "SELECT * FROM refresh_log WHERE ok=1"
    args: list = []
    if field:
        sql += " AND field=?"
        args.append(field)
    row = conn().execute(sql + " ORDER BY id DESC LIMIT 1", args).fetchone()
    return dict(row) if row else None


def recent_refreshes(field: str = "", limit: int = 12) -> list[dict]:
    sql = "SELECT * FROM refresh_log"
    args: list = []
    if field:
        sql += " WHERE field=?"
        args.append(field)
    return [dict(r) for r in conn().execute(sql + " ORDER BY id DESC LIMIT ?",
                                            args + [limit])]


def missing_abstracts(field: str = "", limit: int = 60, max_tries: int = 4) -> list[dict]:
    """Papers whose abstract is unknown and still worth retrying."""
    sql = ("SELECT p.doi, p.title, p.journal FROM papers p "
           "{join} WHERE (p.abstract IS NULL OR p.abstract='') AND p.abstract_tries < ? ")
    args: list = [max_tries]
    join = ""
    if field:
        join = "JOIN paper_fields f ON f.doi = p.doi AND f.field = ?"
        args = [field, max_tries]
    sql = sql.format(join=join) + "ORDER BY p.pub_date DESC LIMIT ?"
    return [dict(r) for r in conn().execute(sql, args + [limit])]


# ================================================================ reading ===
_FTS_SAFE = re.compile(r"[^0-9A-Za-zÀ-ɏ一-鿿\s\"*-]+")


def _fts_expr(q: str) -> str:
    """Turn a user query into a safe FTS5 expression (AND of prefix terms)."""
    q = _FTS_SAFE.sub(" ", q or "").strip()
    if not q:
        return ""
    phrases = re.findall(r'"([^"]+)"', q)
    rest = re.sub(r'"[^"]*"', " ", q)
    terms = [t for t in rest.split() if len(t) > 1 or t.isdigit()]
    parts = ['"{}"'.format(p.replace('"', "")) for p in phrases if p.strip()]
    for t in terms:
        t = t.strip("-*")
        if t:
            parts.append('"{}"*'.format(t))
    return " AND ".join(parts)


def _row_to_paper(row) -> dict:
    d = dict(row)
    try:
        d["labels"] = json.loads(d.get("labels") or "{}")
    except (ValueError, TypeError):
        d["labels"] = {}
    d["starred"] = bool(d.get("starred"))
    d["is_oa"] = bool(d.get("is_oa"))
    d["read_at"] = d.get("read_at") or ""
    return d


SORTS = {
    "date": lambda p: (p.get("pub_date") or "", p.get("relevance") or 0),
    "new": lambda p: (p.get("field_first_seen") or "", p.get("pub_date") or ""),
    "relevance": lambda p: (p.get("relevance") or 0, p.get("pub_date") or ""),
    "journal": lambda p: (-(p.get("journal_tier") or 9), p.get("journal_jif") or 0,
                          p.get("pub_date") or ""),
    "cited": lambda p: (p.get("cited_by") or 0, p.get("pub_date") or ""),
    "title": lambda p: (p.get("title") or "").lower(),
}

_SELECT = """
SELECT p.*, f.labels, f.primary_node, f.relevance,
       f.first_seen AS field_first_seen,
       COALESCE(u.starred, 0) AS starred, COALESCE(u.read_at, '') AS read_at
FROM paper_fields f
JOIN papers p ON p.doi = f.doi
LEFT JOIN user_papers u ON u.doi = f.doi AND u.user_id = ?
"""


def search(*, user_id: int, field: str, q: str = "",
           selections: Optional[dict] = None, journals_sel: Iterable[str] = (),
           max_tier: int = 3, days: int = 0, only_new_since: str = "",
           only_starred: bool = False, only_unread: bool = False,
           only_with_abstract: bool = False, sort: str = "date",
           page: int = 1, page_size: int = 25,
           facet_ids: Iterable[str] = (), descendants=None) -> dict:
    """Faceted search inside one field for one reader.

    ``selections`` maps facet id -> chosen node ids; ``descendants`` expands a
    node id to itself plus its children (the caller passes the field pack's
    own function, so the store stays subject-agnostic).
    """
    c = conn()
    where, params = ["f.field = ?"], [field]
    if max_tier and max_tier < 3:
        where.append("p.journal_tier <= ?")
        params.append(int(max_tier))
    if days and days > 0:
        where.append("p.pub_date >= date('now', ?) AND p.pub_date <= date('now')")
        params.append("-{} days".format(int(days)))
    if only_starred:
        where.append("COALESCE(u.starred,0) = 1")
    if only_unread:
        where.append("COALESCE(u.read_at,'') = ''")
    if only_with_abstract:
        where.append("p.abstract <> ''")
    if only_new_since:
        where.append("f.first_seen > ?")
        params.append(only_new_since)

    expr = _fts_expr(q)
    if expr:
        sql = (_SELECT + " JOIN papers_fts x ON x.doi = f.doi "
               "WHERE papers_fts MATCH ? AND " + " AND ".join(where))
        args = [user_id, expr] + params
    else:
        sql = _SELECT + " WHERE " + " AND ".join(where)
        args = [user_id] + params
    try:
        rows = c.execute(sql, args).fetchall()
    except sqlite3.OperationalError as exc:
        log.warning("search failed (%s); retrying without the text match", exc)
        rows = c.execute(_SELECT + " WHERE " + " AND ".join(where),
                         [user_id] + params).fetchall()

    candidates = [_row_to_paper(r) for r in rows]
    selections = {k: [v for v in vals if v] for k, vals in (selections or {}).items()}
    selections = {k: vals for k, vals in selections.items() if vals}
    jrn_sel = [s for s in journals_sel if s]
    expand = descendants or (lambda n: {n})

    def keep(p, skip_facet: Optional[str] = None, use_jrn: bool = True) -> bool:
        for fid, chosen in selections.items():
            if fid == skip_facet:
                continue
            wanted: set[str] = set()
            for node in chosen:
                wanted |= expand(node)
            if not wanted & set(p["labels"].get(fid) or []):
                return False
        if use_jrn and jrn_sel and p["journal"] not in jrn_sel:
            return False
        return True

    result = [p for p in candidates if keep(p)]

    # Facet counts ignore selections on their own axis, so the reader can see
    # what switching to a sibling category would give -- as Web of Science does.
    facet_counts: dict[str, dict[str, int]] = {}
    for fid in (facet_ids or selections.keys()):
        counts: dict[str, int] = {}
        for p in (x for x in candidates if keep(x, skip_facet=fid)):
            for node in set(p["labels"].get(fid) or []):
                counts[node] = counts.get(node, 0) + 1
        facet_counts[fid] = counts
    journal_counts: dict[str, int] = {}
    for p in (x for x in candidates if keep(x, use_jrn=False)):
        journal_counts[p["journal"]] = journal_counts.get(p["journal"], 0) + 1

    keyfn = SORTS.get(sort, SORTS["date"])
    result.sort(key=keyfn, reverse=(sort != "title"))

    total = len(result)
    page_size = max(5, min(int(page_size or 25), 100))
    pages = max(1, (total + page_size - 1) // page_size)
    page = max(1, min(int(page or 1), pages))
    start = (page - 1) * page_size
    return {"papers": result[start:start + page_size], "total": total, "page": page,
            "pages": pages, "page_size": page_size,
            "facets": {"nodes": facet_counts, "journal": journal_counts}}


def stats(field: str = "", user_id: int = 0) -> dict:
    c = conn()
    row = c.execute(
        "SELECT COUNT(*) n, "
        "SUM(CASE WHEN p.abstract<>'' THEN 1 ELSE 0 END) with_abs, "
        "MIN(NULLIF(p.pub_date,'')) oldest, MAX(p.pub_date) newest "
        "FROM paper_fields f JOIN papers p ON p.doi=f.doi WHERE f.field=?",
        (field,)).fetchone()
    out = {k: (row[k] if row else None) for k in ("n", "with_abs", "oldest", "newest")}
    for k in ("n", "with_abs"):
        out[k] = out.get(k) or 0
    out["total"] = out["n"]          # the name the API and front end use
    out["today"] = c.execute(
        "SELECT COUNT(*) n FROM paper_fields f JOIN papers p ON p.doi=f.doi "
        "WHERE f.field=? AND p.pub_date >= date('now','-1 day') "
        "AND p.pub_date <= date('now')", (field,)).fetchone()["n"]
    out["week"] = c.execute(
        "SELECT COUNT(*) n FROM paper_fields f JOIN papers p ON p.doi=f.doi "
        "WHERE f.field=? AND p.pub_date >= date('now','-7 day') "
        "AND p.pub_date <= date('now')", (field,)).fetchone()["n"]
    if user_id:
        out["starred"] = c.execute(
            "SELECT COUNT(*) n FROM user_papers u JOIN paper_fields f ON f.doi=u.doi "
            "WHERE u.user_id=? AND f.field=? AND u.starred=1", (user_id, field)).fetchone()["n"]
        out["unread"] = c.execute(
            "SELECT COUNT(*) n FROM paper_fields f LEFT JOIN user_papers u "
            "ON u.doi=f.doi AND u.user_id=? WHERE f.field=? "
            "AND COALESCE(u.read_at,'')=''", (user_id, field)).fetchone()["n"]
    else:
        out["starred"] = out["unread"] = 0
    return out


def new_count(field: str, since: str) -> int:
    if not since:
        return 0
    row = conn().execute("SELECT COUNT(*) n FROM paper_fields WHERE field=? AND first_seen > ?",
                         (field, since)).fetchone()
    return int(row["n"]) if row else 0


def get(field: str, doi: str, user_id: int = 0) -> Optional[dict]:
    row = conn().execute(_SELECT + " WHERE f.field=? AND f.doi=?",
                         (user_id, field, (doi or "").lower())).fetchone()
    return _row_to_paper(row) if row else None


def paper_row(doi: str) -> Optional[dict]:
    row = conn().execute("SELECT * FROM papers WHERE doi=?", ((doi or "").lower(),)).fetchone()
    return dict(row) if row else None


def field_dois(field: str) -> set[str]:
    return {r["doi"] for r in conn().execute(
        "SELECT doi FROM paper_fields WHERE field=?", (field,))}


def field_records(field: str) -> list[dict]:
    """Everything stored for a field -- used when re-applying changed rules."""
    return [dict(r) for r in conn().execute(
        "SELECT p.doi, p.title, p.abstract FROM paper_fields f "
        "JOIN papers p ON p.doi=f.doi WHERE f.field=?", (field,))]


def field_summary() -> list[dict]:
    return [dict(r) for r in conn().execute(
        "SELECT field, COUNT(*) n, MAX(first_seen) newest FROM paper_fields "
        "GROUP BY field ORDER BY n DESC")]
