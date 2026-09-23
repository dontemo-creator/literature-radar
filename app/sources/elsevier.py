# -*- coding: utf-8 -*-
"""Elsevier: optional abstract back-fill, requires the user's own API key.

Why this module exists
----------------------
Elsevier does not deposit abstracts to Crossref, and Europe PMC / OpenAlex do
not carry them for recent Elsevier articles either.  Measured on a real sample
of 40 Elsevier solid-state-battery papers, the free sources filled 1.

Elsevier's own API is the sanctioned route.  A free developer key from
https://dev.elsevier.com covers it; put it in ``settings.json`` as
``"elsevier_api_key"``.  How much it returns depends on that key's
entitlements, so this module is strictly best-effort: without a key, or on any
error, it returns nothing and the rest of the pipeline carries on unchanged.

We never scrape ScienceDirect -- automated page access is against its terms.
"""
from __future__ import annotations

from .. import config
from ..http_client import request
from ..logging_util import get_logger
from ..textnorm import strip_markup

log = get_logger("elsevier")

ARTICLE_API = "https://api.elsevier.com/content/article/doi/"
ABSTRACT_API = "https://api.elsevier.com/content/abstract/doi/"
# DOI prefixes Elsevier publishes under; anything else is not worth a call.
PREFIXES = ("10.1016/", "10.1006/", "10.1053/", "10.1054/", "10.1078/")

_disabled = False


def enabled() -> bool:
    return bool(str(config.get("elsevier_api_key") or "").strip()) and not _disabled


def handles(doi: str) -> bool:
    return (doi or "").lower().startswith(PREFIXES)


def _extract(payload) -> str:
    if not isinstance(payload, dict):
        return ""
    for root in ("full-text-retrieval-response", "abstracts-retrieval-response"):
        node = payload.get(root)
        if isinstance(node, dict):
            core = node.get("coredata")
            if isinstance(core, dict):
                text = core.get("dc:description") or ""
                if isinstance(text, dict):
                    text = text.get("$") or ""
                text = strip_markup(str(text))
                if len(text) > 80:
                    return text
    return ""


def abstract_for(doi: str) -> str:
    """Best-effort single-DOI lookup. Returns '' rather than raising."""
    global _disabled
    if not enabled() or not handles(doi):
        return ""
    key = str(config.get("elsevier_api_key")).strip()
    for base in (ARTICLE_API, ABSTRACT_API):
        resp = request(base + doi, params={"apiKey": key, "httpAccept": "application/json"},
                       retries=1, timeout=30, max_retry_delay=6.0, cache_ttl=7 * 86400)
        if resp.ok:
            text = _extract(resp.json())
            if text:
                return text
            continue
        if resp.status in (401, 403):
            # A bad or unentitled key will never start working mid-run.
            _disabled = True
            log.warning("Elsevier key rejected (%s); disabling for this run", resp.status)
            return ""
        if resp.status == 429:
            _disabled = True
            log.warning("Elsevier quota exhausted; disabling for this run")
            return ""
    return ""


def abstracts_for(dois) -> dict[str, str]:
    out: dict[str, str] = {}
    if not enabled():
        return out
    for doi in dois:
        if not enabled():
            break
        text = abstract_for(doi)
        if text:
            out[doi] = text
    return out
