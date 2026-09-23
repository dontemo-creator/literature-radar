# -*- coding: utf-8 -*-
"""Local HTTP server: accounts, per-field JSON API, static front end.

Accounts exist so a phone and a laptop pointed at the same server share one
reading state -- starred papers, read marks and the chosen research field all
live server-side, keyed by user.  The cookie carries only an opaque token.

Every data route requires a session; unauthenticated callers get a 401 and the
front end shows the sign-in view.  Standard library only.
"""
from __future__ import annotations

import http.cookies
import json
import mimetypes
import posixpath
import socket
import threading
import traceback
import urllib.parse
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional

from . import config, fields, ingest, journals, netinfo, store
from .fields.base import Pack
from .logging_util import get_logger
from .sources import live_search

log = get_logger("server")

MAX_BODY = 256 * 1024
COOKIE_NAME = "ssb_session"
COOKIE_MAX_AGE = store.SESSION_DAYS * 86400
FACET_PREFIX = "f."


# =============================================================== helpers ====
def _today_local() -> str:
    return datetime.now().astimezone().date().isoformat()


def digest_marker(user_id: int, field: str) -> str:
    """Timestamp defining "new since your last visit", per user and field.

    It advances only when the calendar day changes, so reloading the page does
    not silently clear NEW badges that have not been read yet.
    """
    today = _today_local()
    key_date = "seen_date"
    key_at = "seen_at"
    key_since = "new_since"
    last_date = _mark_get(user_id, field, key_date)
    if last_date != today:
        previous = _mark_get(user_id, field, key_at)
        if not previous:
            previous = (datetime.now(timezone.utc) - timedelta(days=1)).replace(
                microsecond=0).isoformat()
        _mark_set(user_id, field, key_since, previous)
        _mark_set(user_id, field, key_at, store.now_iso())
        _mark_set(user_id, field, key_date, today)
        return previous
    return _mark_get(user_id, field, key_since)


def _mark_get(user_id: int, field: str, key: str, default: str = "") -> str:
    row = store.conn().execute(
        "SELECT value FROM user_marks WHERE user_id=? AND field=? AND key=?",
        (user_id, field, key)).fetchone()
    return row["value"] if row else default


def _mark_set(user_id: int, field: str, key: str, value: str) -> None:
    with store._write_lock:
        store.conn().execute(
            "INSERT INTO user_marks(user_id,field,key,value) VALUES(?,?,?,?) "
            "ON CONFLICT(user_id,field,key) DO UPDATE SET value=excluded.value",
            (user_id, field, key, str(value)))


def _as_int(value, default=0, lo=None, hi=None) -> int:
    try:
        n = int(str(value).strip())
    except (TypeError, ValueError):
        return default
    if lo is not None:
        n = max(lo, n)
    if hi is not None:
        n = min(hi, n)
    return n


def _as_bool(value) -> bool:
    return str(value).strip().lower() in ("1", "true", "yes", "on")


def pack_for_user(user: dict) -> Optional[Pack]:
    """The field pack this reader has chosen, building a custom one if needed."""
    field_id = (user or {}).get("field") or ""
    if not field_id:
        return None
    pack = fields.get(field_id)
    if pack is not None:
        return pack
    if fields.is_custom(field_id):
        spec = (user or {}).get("field_spec") or {}
        try:
            pack = fields.build_custom(field_id, spec,
                                       spec.get("journals") or _default_journals())
        except Exception as exc:
            log.warning("cannot rebuild custom field %s: %s", field_id, exc)
            return None
        fields.register_custom(pack)
        return pack
    return None


def _default_journals() -> list[str]:
    """A broad, high-quality default for custom fields."""
    return [j["name"] for j in journals.JOURNALS if j["tier"] <= 2]


# ============================================================== API layer ===
def api_auth_state(user: Optional[dict]) -> dict:
    return {
        "app": {"name": config.APP_NAME, "version": config.APP_VERSION},
        "has_users": store.user_count() > 0,
        "authenticated": bool(user),
        "user": _public_user(user) if user else None,
    }


def _public_user(user: dict) -> dict:
    pack = pack_for_user(user)
    return {"id": user["id"], "username": user["username"],
            "display_name": user["display_name"],
            "field": user.get("field") or "",
            "field_zh": pack.zh if pack else "",
            "field_icon": pack.icon if pack else "",
            "is_custom": fields.is_custom(user.get("field") or "")}


def api_fields(user: Optional[dict]) -> dict:
    out = {"presets": fields.summaries(), "current": (user or {}).get("field") or ""}
    if user and fields.is_custom(user.get("field") or ""):
        pack = pack_for_user(user)
        if pack:
            out["custom"] = pack.summary()
            out["custom_spec"] = user.get("field_spec") or {}
    out["stored"] = store.field_summary()
    return out


def api_bootstrap(user: dict) -> dict:
    pack = pack_for_user(user)
    if pack is None:
        return {"needs_field": True, "user": _public_user(user),
                "fields": api_fields(user)}
    field = pack.id
    should, reason = ingest.needs_refresh(field)
    marker = digest_marker(user["id"], field)
    started = False
    if should and not ingest.is_running(field):
        started = ingest.refresh_async(field)
    stats = store.stats(field, user["id"])
    stats["new_count"] = store.new_count(field, marker)
    stats["journals_tracked"] = len(pack.journals)
    return {
        "app": {"name": config.APP_NAME, "version": config.APP_VERSION},
        "user": _public_user(user),
        "needs_field": False,
        "field": {"id": pack.id, "zh": pack.zh, "en": pack.en, "icon": pack.icon,
                  "tagline": pack.tagline, "builtin": pack.builtin,
                  "hints": pack.search_hints},
        "facets": pack.tree_json(),
        "journals": [{"name": j["name"], "tier": j["tier"], "jif": j["jif"]}
                     for j in journals.JOURNALS if j["name"] in set(pack.journals)],
        "tier_labels": journals.TIER_LABELS,
        "stats": stats,
        "new_since": marker,
        "refresh": {"needed": should, "reason": reason, "started": started,
                    "status": ingest.status(field), "last": store.last_refresh(field)},
        "settings": {"refresh_window_days": config.get("refresh_window_days"),
                     "auto_refresh_after_hours": config.get("auto_refresh_after_hours"),
                     "max_journal_tier": config.get("max_journal_tier")},
    }


def api_search(user: dict, params: dict) -> dict:
    pack = pack_for_user(user)
    if pack is None:
        return {"error": "no field selected", "needs_field": True}

    def multi(key):
        out = []
        for item in params.get(key) or []:
            out.extend(x for x in item.split(",") if x)
        return out

    one = lambda k, d="": (params.get(k) or [d])[0]

    selections: dict[str, list[str]] = {}
    for facet in pack.facets:
        chosen = [n for n in multi(FACET_PREFIX + facet.id) if n in facet.flat]
        if chosen:
            selections[facet.id] = chosen
    jrn = [j for j in multi("journal") if j in journals.BY_NAME]
    new_only = _as_bool(one("new_only"))
    marker = _mark_get(user["id"], pack.id, "new_since") if new_only else ""

    result = store.search(
        user_id=user["id"], field=pack.id, q=one("q")[:200],
        selections=selections, journals_sel=jrn,
        max_tier=_as_int(one("tier", "3"), 3, 1, 3),
        days=_as_int(one("days", "0"), 0, 0, 3650),
        only_new_since=marker,
        only_starred=_as_bool(one("starred")),
        only_unread=_as_bool(one("unread")),
        only_with_abstract=_as_bool(one("has_abs")),
        sort=one("sort", "date"),
        page=_as_int(one("page", "1"), 1, 1, 10000),
        page_size=_as_int(one("page_size", "25"), 25, 5, 100),
        facet_ids=[f.id for f in pack.facets],
        descendants=pack.descendants,
    )
    since = _mark_get(user["id"], pack.id, "new_since")
    for p in result["papers"]:
        p["is_new"] = bool(since and (p.get("field_first_seen") or "") > since)
        p["label_chips"] = [
            {"facet": f.id, "id": nid, "zh": pack.label(nid, "zh"),
             "en": pack.label(nid, "en"), "path": pack.path_label(nid, "zh")}
            for f in pack.facets for nid in (p["labels"].get(f.id) or [])]
    result["query"] = {"q": one("q"), "selections": selections, "journal": jrn,
                       "sort": one("sort", "date"), "new_only": new_only}
    result["new_since"] = since
    return result


def api_search_live(user: Optional[dict], params: dict) -> dict:
    one = lambda k, d="": (params.get(k) or [d])[0]
    q = one("q")[:200]
    page = _as_int(one("page", "1"), 1, 1, 1000)
    page_size = _as_int(one("page_size", "25"), 25, 5, 50)
    sort = one("sort", "relevance")
    res = live_search.query_global(q, page=page, page_size=page_size, sort=sort)
    if res.get("papers") and user:
        dois = [p["doi"] for p in res["papers"]]
        flag_map = store.user_flag_map(user["id"], dois)
        for p in res["papers"]:
            f = flag_map.get(p["doi"]) or {}
            p["starred"] = f.get("starred", False)
            p["read_at"] = f.get("read_at", "")
    return res


def api_save_paper(user: dict, body: dict) -> dict:
    paper = body.get("paper")
    if not isinstance(paper, dict):
        return {"ok": False, "error": "invalid paper data"}
    starred = bool(body.get("starred", True))
    ok = store.save_external_paper(user["id"], paper, starred=starred)
    return {"ok": ok, "doi": paper.get("doi")}


def api_flag(user: dict, body: dict) -> dict:
    doi = str(body.get("doi") or "").strip().lower()
    if not doi:
        return {"ok": False, "error": "missing doi"}
    field_name = str(body.get("field") or "")
    if field_name == "starred":
        value = 1 if body.get("value") else 0
    elif field_name == "read":
        field_name, value = "read_at", (store.now_iso() if body.get("value") else "")
    else:
        return {"ok": False, "error": "unsupported field"}
    return {"ok": store.set_flag(user["id"], doi, field_name, value)}


def api_set_field(user: dict, body: dict) -> dict:
    """Choose a research direction (preset or custom) and start filling it."""
    preset = str(body.get("field") or "").strip()
    custom = body.get("custom")

    if custom:
        spec = dict(custom)
        picked = [n for n in (spec.get("journals") or []) if n in journals.BY_NAME]
        spec["journals"] = picked or _default_journals()
        field_id = fields.custom_id(user["id"])
        try:
            pack = fields.build_custom(field_id, spec, spec["journals"])
        except ValueError as exc:
            return {"ok": False, "error": str(exc)}
        problems = pack.audit()
        if problems:
            # A reader's keyword can be as dangerous as a developer's rule --
            # "na" would match "nanocomposite".  Drop those instead of failing.
            bad = {p.split("'")[1] for p in problems if "'" in p}
            spec["keywords"] = [k for k in (spec.get("keywords") or []) if k not in bad]
            spec["exclude"] = [k for k in (spec.get("exclude") or []) if k not in bad]
            for cat in spec.get("categories") or []:
                cat["keywords"] = [k for k in (cat.get("keywords") or []) if k not in bad]
            try:
                pack = fields.build_custom(field_id, spec, spec["journals"])
            except ValueError as exc:
                return {"ok": False, "error": "关键词过短或无效：{}".format("、".join(sorted(bad)))}
            if pack.audit():
                return {"ok": False, "error": "关键词太短，容易误匹配，请改用更具体的词组"}
            spec["dropped"] = sorted(bad)
        fields.register_custom(pack)
        store.set_user_field(user["id"], field_id, spec)
        started = ingest.refresh_async(field_id)
        return {"ok": True, "field": field_id, "zh": pack.zh, "refreshing": started,
                "dropped": spec.get("dropped") or []}

    if not fields.get(preset):
        return {"ok": False, "error": "未知的研究方向"}
    store.set_user_field(user["id"], preset, {})
    started = ingest.refresh_async(preset)
    return {"ok": True, "field": preset, "zh": fields.get(preset).zh,
            "refreshing": started}


# =============================================================== handler ====
class Handler(BaseHTTPRequestHandler):
    server_version = "SSBRadar/" + config.APP_VERSION
    protocol_version = "HTTP/1.1"

    # ---- plumbing --------------------------------------------------------
    def log_message(self, fmt, *args):
        log.debug("%s - %s", self.address_string(), fmt % args)

    def _client_ip(self) -> str:
        return (self.client_address[0] if self.client_address else "?") or "?"

    def _send(self, status: int, body: bytes, ctype: str, extra=None):
        self.send_response(status)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        for k, v in (extra or {}).items():
            if isinstance(v, (list, tuple)):
                for item in v:
                    self.send_header(k, item)
            else:
                self.send_header(k, v)
        self.end_headers()
        if self.command != "HEAD":
            try:
                self.wfile.write(body)
            except (BrokenPipeError, ConnectionResetError):
                pass

    def _json(self, payload, status: int = 200, extra=None):
        body = json.dumps(payload, ensure_ascii=False, default=str).encode("utf-8")
        self._send(status, body, "application/json; charset=utf-8", extra)

    def _read_body(self) -> dict:
        length = _as_int(self.headers.get("Content-Length"), 0, 0, MAX_BODY)
        if not length:
            return {}
        try:
            raw = self.rfile.read(length)
            out = json.loads(raw.decode("utf-8"))
            return out if isinstance(out, dict) else {}
        except (ValueError, UnicodeDecodeError, OSError):
            return {}

    # ---- session ---------------------------------------------------------
    def _token(self) -> str:
        raw = self.headers.get("Cookie") or ""
        try:
            jar = http.cookies.SimpleCookie()
            jar.load(raw)
        except http.cookies.CookieError:
            return ""
        morsel = jar.get(COOKIE_NAME)
        return morsel.value if morsel else ""

    def _user(self) -> Optional[dict]:
        return store.session_user(self._token())

    def _cookie_header(self, token: str, clear: bool = False) -> dict:
        if clear:
            value = "{}=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0".format(COOKIE_NAME)
        else:
            value = ("{}={}; Path=/; HttpOnly; SameSite=Lax; Max-Age={}"
                     .format(COOKIE_NAME, token, COOKIE_MAX_AGE))
        return {"Set-Cookie": value}

    def _static(self, path: str, extra=None):
        rel = posixpath.normpath(urllib.parse.unquote(path)).lstrip("/")
        if not rel or rel in (".", ".."):
            rel = "index.html"
        target = (config.WEB_DIR / rel).resolve()
        try:
            target.relative_to(config.WEB_DIR.resolve())
        except ValueError:
            return self._json({"error": "forbidden"}, 403)
        if not target.is_file():
            return self._json({"error": "not found", "path": rel}, 404)
        ctype = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
        if ctype.startswith("text/") or ctype in ("application/javascript",
                                                  "application/json"):
            ctype += "; charset=utf-8"
        try:
            self._send(200, target.read_bytes(), ctype, extra)
        except OSError as exc:
            self._json({"error": str(exc)}, 500)

    # ---- verbs -----------------------------------------------------------
    def do_GET(self):
        parsed = urllib.parse.urlsplit(self.path)
        route = parsed.path.rstrip("/") or "/"
        params = urllib.parse.parse_qs(parsed.query, keep_blank_values=True)
        try:
            # --- public
            if route == "/api/auth/state":
                return self._json(api_auth_state(self._user()))
            if route == "/healthz":
                return self._json({"ok": True, "users": store.user_count()})
            if route == "/" or route == "/index.html":
                return self._static("index.html")
            if route == "/sw.js":
                return self._static("sw.js", extra={"Service-Worker-Allowed": "/"})
            if route == "/manifest.webmanifest":
                return self._static("manifest.webmanifest")
            if route.startswith("/static/"):
                return self._static(route[len("/static/"):])

            # --- authenticated
            user = self._user()
            if route.startswith("/api/"):
                if not user:
                    return self._json({"error": "unauthenticated"}, 401)
                if route == "/api/bootstrap":
                    return self._json(api_bootstrap(user))
                if route == "/api/search":
                    return self._json(api_search(user, params))
                if route == "/api/search/live":
                    return self._json(api_search_live(user, params))
                if route == "/api/fields":
                    return self._json(api_fields(user))
                if route == "/api/status":
                    pack = pack_for_user(user)
                    fid = pack.id if pack else ""
                    return self._json({"status": ingest.status(fid),
                                       "stats": store.stats(fid, user["id"]) if fid else {},
                                       "last": store.last_refresh(fid) if fid else None})
                if route == "/api/history":
                    pack = pack_for_user(user)
                    return self._json({"refreshes": store.recent_refreshes(
                        pack.id if pack else "", 12)})
                if route == "/api/me/sessions":
                    current = self._token()
                    out = []
                    for s in store.sessions_for(user["id"]):
                        out.append({"created_at": s["created_at"], "seen_at": s["seen_at"],
                                    "agent": s["agent"], "current": s["token"] == current,
                                    "id": s["token"][:12]})
                    return self._json({"sessions": out})
                if route.startswith("/api/paper/"):
                    pack = pack_for_user(user)
                    doi = urllib.parse.unquote(route[len("/api/paper/"):])
                    rec = store.get(pack.id, doi, user["id"]) if pack else None
                    return self._json(rec or {"error": "not found"}, 200 if rec else 404)
                return self._json({"error": "not found", "path": route}, 404)
            return self._json({"error": "not found", "path": route}, 404)
        except Exception as exc:
            log.error("GET %s failed: %s\n%s", self.path, exc, traceback.format_exc())
            return self._json({"error": "internal error", "detail": str(exc)}, 500)

    def do_HEAD(self):
        self.do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlsplit(self.path)
        route = parsed.path.rstrip("/") or "/"
        try:
            body = self._read_body()

            # --- public auth routes
            if route == "/api/auth/register":
                return self._register(body)
            if route == "/api/auth/login":
                return self._login(body)
            if route == "/api/auth/logout":
                token = self._token()
                if token:
                    store.drop_session(token)
                return self._json({"ok": True}, extra=self._cookie_header("", clear=True))

            user = self._user()
            if not user:
                return self._json({"error": "unauthenticated"}, 401)

            if route == "/api/me/field":
                return self._json(api_set_field(user, body))
            if route == "/api/flag":
                return self._json(api_flag(user, body))
            if route == "/api/paper/save":
                return self._json(api_save_paper(user, body))
            if route == "/api/refresh":
                pack = pack_for_user(user)
                if pack is None:
                    return self._json({"ok": False, "error": "no field selected"}, 400)
                if ingest.is_running(pack.id):
                    return self._json({"ok": True, "already_running": True,
                                       "status": ingest.status(pack.id)})
                kw = {}
                if body.get("window_days") is not None:
                    kw["window_days"] = _as_int(body.get("window_days"), 21, 1, 3650)
                started = ingest.refresh_async(pack.id, **kw)
                return self._json({"ok": started, "status": ingest.status(pack.id)})
            if route == "/api/reclassify":
                pack = pack_for_user(user)
                if pack is None:
                    return self._json({"ok": False, "error": "no field selected"}, 400)
                threading.Thread(target=ingest.reclassify, args=(pack.id,),
                                 daemon=True).start()
                return self._json({"ok": True})
            if route == "/api/me/password":
                old = str(body.get("current") or "")
                if not store.verify_login(user["username"], old):
                    return self._json({"ok": False, "error": "当前密码不正确"}, 400)
                try:
                    store.change_password(user["id"], str(body.get("new") or ""))
                except ValueError as exc:
                    return self._json({"ok": False, "error": str(exc)}, 400)
                token = store.create_session(user["id"], self.headers.get("User-Agent", ""))
                return self._json({"ok": True}, extra=self._cookie_header(token))
            if route == "/api/me/sessions/revoke":
                store.drop_sessions_for(user["id"])
                token = store.create_session(user["id"], self.headers.get("User-Agent", ""))
                return self._json({"ok": True}, extra=self._cookie_header(token))
            return self._json({"error": "not found", "path": route}, 404)
        except Exception as exc:
            log.error("POST %s failed: %s\n%s", self.path, exc, traceback.format_exc())
            return self._json({"error": "internal error", "detail": str(exc)}, 500)

    # ---- auth helpers ----------------------------------------------------
    def _register(self, body: dict):
        username = str(body.get("username") or "")
        password = str(body.get("password") or "")
        display = str(body.get("display_name") or "")
        try:
            user = store.create_user(username, password, display)
        except ValueError as exc:
            return self._json({"ok": False, "error": str(exc)}, 400)
        token = store.create_session(user["id"], self.headers.get("User-Agent", ""))
        return self._json({"ok": True, "user": _public_user(user)},
                          extra=self._cookie_header(token))

    def _login(self, body: dict):
        ip = self._client_ip()
        wait = store.login_blocked(ip)
        if wait:
            return self._json({"ok": False,
                               "error": "尝试次数过多，请稍后再试"}, 429)
        user = store.verify_login(str(body.get("username") or ""),
                                  str(body.get("password") or ""))
        store.note_login_attempt(ip, bool(user))
        if not user:
            return self._json({"ok": False, "error": "用户名或密码不正确"}, 401)
        token = store.create_session(user["id"], self.headers.get("User-Agent", ""))
        return self._json({"ok": True, "user": _public_user(user)},
                          extra=self._cookie_header(token))


# ================================================================= serve ====
def lan_addresses() -> list[str]:
    """Kept for callers that only need the addresses a phone can reach."""
    return [a.ip for a in netinfo.addresses() if a.reachable_hint]


def find_port(host: str, preferred: int, tries: int = 20) -> int:
    for offset in range(tries):
        port = preferred + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((host, port))
                return port
            except OSError:
                continue
    raise OSError("no free port in range {}-{}".format(preferred, preferred + tries))


def serve(host: str | None = None, port: int | None = None):
    host = host or config.get("server_host")
    port = find_port(host, port or int(config.get("server_port")))
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    store.purge_expired_sessions()
    return httpd, port
