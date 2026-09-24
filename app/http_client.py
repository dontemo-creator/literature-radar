"""A small, dependency-free HTTP helper built for well-behaved API polling.

Features that matter for reliability:
  * per-host request throttling (never hammer an API),
  * retry with exponential backoff + jitter on 429/5xx/network errors,
  * honours ``Retry-After``,
  * transparent gzip/deflate,
  * optional on-disk response cache (used for slow-changing lookups),
  * every failure is returned, never raised, so one bad call cannot kill a run.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import random
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from . import config
from .logging_util import get_logger

log = get_logger("http")

# Minimum seconds between two requests to the same host.
HOST_MIN_INTERVAL = {
    "api.openalex.org": 1.10,
    "api.crossref.org": 0.60,
    "www.ebi.ac.uk": 0.45,
    "api.semanticscholar.org": 1.60,
    "export.arxiv.org": 3.10,
    "api.elsevier.com": 0.70,
}
DEFAULT_MIN_INTERVAL = 1.0

_lock = threading.Lock()
_last_call: dict[str, float] = {}


@dataclass
class Response:
    ok: bool
    status: int = 0
    url: str = ""
    text: str = ""
    error: str = ""
    from_cache: bool = False
    headers: dict = field(default_factory=dict)

    def json(self) -> Optional[Any]:
        if not self.text:
            return None
        try:
            return json.loads(self.text)
        except ValueError as exc:
            log.warning("bad JSON from %s: %s", self.url, exc)
            return None


def _throttle(host: str) -> None:
    interval = HOST_MIN_INTERVAL.get(host, DEFAULT_MIN_INTERVAL)
    while True:
        with _lock:
            now = time.monotonic()
            wait = interval - (now - _last_call.get(host, 0.0))
            if wait <= 0:
                _last_call[host] = now
                return
        time.sleep(min(wait, 5.0))


def _decode(raw: bytes, encoding: str) -> str:
    encoding = (encoding or "").lower()
    try:
        if "gzip" in encoding:
            raw = gzip.decompress(raw)
        elif "deflate" in encoding:
            try:
                raw = zlib.decompress(raw)
            except zlib.error:
                raw = zlib.decompress(raw, -zlib.MAX_WBITS)
    except (OSError, zlib.error) as exc:
        log.warning("decompress failed (%s), using raw bytes", exc)
    return raw.decode("utf-8", errors="replace")


def _cache_path(key: str) -> Path:
    return config.HTTP_CACHE / (hashlib.sha1(key.encode("utf-8")).hexdigest() + ".json")


def request(
    url: str,
    *,
    params: Optional[dict] = None,
    data: Optional[bytes] = None,
    headers: Optional[dict] = None,
    timeout: float = 45.0,
    retries: int = 4,
    cache_ttl: float = 0.0,
    accept: str = "application/json",
    max_retry_delay: float = 30.0,
) -> Response:
    """Perform a GET (or POST when ``data`` is given). Never raises."""
    if params:
        clean = {k: v for k, v in params.items() if v is not None}
        sep = "&" if "?" in url else "?"
        url = url + sep + urllib.parse.urlencode(clean, safe=":|,+()<>/'\"")

    cache_key = url + ("|POST:" + hashlib.sha1(data).hexdigest() if data else "")
    cpath = _cache_path(cache_key)
    if cache_ttl > 0 and cpath.exists():
        try:
            blob = json.loads(cpath.read_text(encoding="utf-8"))
            if time.time() - blob.get("ts", 0) < cache_ttl:
                return Response(ok=True, status=blob.get("status", 200), url=url,
                                text=blob.get("text", ""), from_cache=True)
        except Exception:
            pass  # unreadable cache entry -> just refetch

    host = urllib.parse.urlparse(url).hostname or ""
    hdrs = {
        "User-Agent": config.USER_AGENT,
        "Accept": accept,
        "Accept-Encoding": "gzip, deflate",
    }
    if data is not None:
        hdrs["Content-Type"] = "application/json"
    if headers:
        hdrs.update(headers)

    last = Response(ok=False, url=url, error="not attempted")
    for attempt in range(retries + 1):
        _throttle(host)
        try:
            req = urllib.request.Request(url, data=data, headers=hdrs,
                                         method="POST" if data is not None else "GET")
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                body = resp.read()
                text = _decode(body, resp.headers.get("Content-Encoding", ""))
                out = Response(ok=True, status=resp.status, url=url, text=text,
                               headers=dict(resp.headers))
                if cache_ttl > 0:
                    try:
                        cpath.write_text(json.dumps({"ts": time.time(), "status": out.status,
                                                     "text": text}), encoding="utf-8")
                    except OSError:
                        pass
                return out
        except urllib.error.HTTPError as exc:
            body = ""
            try:
                body = _decode(exc.read(), exc.headers.get("Content-Encoding", ""))[:400]
            except Exception:
                pass
            last = Response(ok=False, status=exc.code, url=url,
                            error="HTTP {}: {}".format(exc.code, body[:200] or exc.reason))
            retryable = exc.code in (408, 425, 429, 500, 502, 503, 504, 520, 521, 522, 524)
            if not retryable or attempt >= retries:
                if exc.code == 404:
                    log.debug("404 %s", url)
                else:
                    log.warning("giving up on %s -> %s", url, last.error)
                return last
            delay = 2.0 * (2 ** attempt) + random.uniform(0, 1.5)
            ra = exc.headers.get("Retry-After") if exc.headers else None
            if ra:
                try:
                    delay = max(delay, float(ra))
                except ValueError:
                    pass
            # Never let a server's Retry-After stall the whole refresh.
            delay = min(delay, max_retry_delay)
            log.info("HTTP %s from %s, retry %d/%d in %.1fs", exc.code, host, attempt + 1, retries, delay)
            time.sleep(delay)
        except Exception as exc:  # timeouts, SSL/EOF, DNS, connection reset ...
            last = Response(ok=False, url=url, error="{}: {}".format(type(exc).__name__, exc))
            if attempt >= retries:
                log.warning("network failure on %s -> %s", url, last.error)
                return last
            delay = 1.5 * (2 ** attempt) + random.uniform(0, 1.0)
            log.info("%s on %s, retry %d/%d in %.1fs", type(exc).__name__, host, attempt + 1, retries, delay)
            time.sleep(delay)
    return last


def prune_cache(max_age_days: float = 30.0, max_files: int = 4000) -> int:
    """Drop stale cache entries so the directory cannot grow without bound."""
    removed = 0
    try:
        entries = sorted(config.HTTP_CACHE.glob("*.json"),
                         key=lambda f: f.stat().st_mtime, reverse=True)
    except OSError:
        return 0
    cutoff = time.time() - max_age_days * 86400
    for i, f in enumerate(entries):
        try:
            if i >= max_files or f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        except OSError:
            continue
    if removed:
        log.info("pruned %d cached responses", removed)
    return removed


def get_json(url: str, **kw) -> Optional[Any]:
    resp = request(url, **kw)
    return resp.json() if resp.ok else None
