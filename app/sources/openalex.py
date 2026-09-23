# -*- coding: utf-8 -*-
"""OpenAlex: abstract back-fill and citation counts.

OpenAlex is used sparingly and never on the critical path -- its quota is much
tighter than Crossref's, and a 429 here must degrade gracefully rather than
break a refresh.  Abstracts arrive as an inverted index and are rebuilt below.
"""
from __future__ import annotations

import time

from ..http_client import request
from ..logging_util import get_logger
from ..textnorm import strip_markup

log = get_logger("openalex")

API = "https://api.openalex.org/works"
BATCH = 40
SELECT = "doi,abstract_inverted_index,cited_by_count,open_access,publication_date"

# OpenAlex moved to a metered model with a small free daily allowance.  Once it
# is exhausted every call 429s, so we trip a breaker and stop trying until the
# quota resets (midnight UTC) instead of burning refresh time on retries.
_blocked_until = 0.0


def available() -> bool:
    return time.time() >= _blocked_until


def _trip(error: str) -> None:
    global _blocked_until
    seconds = 3600.0
    if "budget" in (error or "").lower() or "insufficient" in (error or "").lower():
        seconds = _seconds_to_utc_midnight()
    _blocked_until = time.time() + seconds
    log.info("OpenAlex unavailable, pausing %.0f min (%s)", seconds / 60.0, error[:120])


def _seconds_to_utc_midnight() -> float:
    from datetime import datetime, timedelta, timezone
    now = datetime.now(timezone.utc)
    nxt = (now + timedelta(days=1)).replace(hour=0, minute=5, second=0, microsecond=0)
    return max(600.0, (nxt - now).total_seconds())


def _from_inverted(index) -> str:
    if not isinstance(index, dict) or not index:
        return ""
    positions: dict[int, str] = {}
    for word, spots in index.items():
        if not isinstance(spots, list):
            continue
        for p in spots:
            if isinstance(p, int):
                positions[p] = word
    if not positions:
        return ""
    return strip_markup(" ".join(positions[k] for k in sorted(positions)))


def enrich(dois, *, want_abstract: bool = True) -> dict[str, dict]:
    """Map ``doi -> {abstract, cited_by, is_oa}`` for whichever DOIs resolve."""
    from .. import config
    out: dict[str, dict] = {}
    if not available():
        log.debug("skipping enrich, breaker open")
        return out
    dois = [d.strip().lower() for d in dois if d and d.strip()]
    for i in range(0, len(dois), BATCH):
        chunk = dois[i:i + BATCH]
        resp = request(API, params={
            "filter": "doi:" + "|".join(chunk),
            "per-page": len(chunk), "select": SELECT,
            "mailto": config.get("contact_email")}, retries=1, timeout=60,
            max_retry_delay=8.0)
        if not resp.ok:
            # Quota exhaustion is expected and must not be fatal.
            log.info("enrich batch skipped (%s) for %d DOIs", resp.error, len(chunk))
            if resp.status == 429:
                _trip(resp.error)
                return out
            continue
        for rec in ((resp.json() or {}).get("results") or []):
            doi = (rec.get("doi") or "").strip().lower().replace("https://doi.org/", "")
            if not doi:
                continue
            entry = {"cited_by": int(rec.get("cited_by_count") or 0),
                     "is_oa": 1 if ((rec.get("open_access") or {}).get("is_oa")) else 0}
            if want_abstract:
                text = _from_inverted(rec.get("abstract_inverted_index"))
                if len(text) > 80:
                    entry["abstract"] = text
            out[doi] = entry
    return out
