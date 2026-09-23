# -*- coding: utf-8 -*-
"""Real-time global multi-disciplinary academic search engine.

Enables searching across all scientific domains (Computer Science, AI,
Biomedicine, Materials, Physics, Chemistry, etc.) via OpenAlex with
automatic Crossref fallback.
"""
from __future__ import annotations

from datetime import date
from functools import lru_cache
import math
import re
from typing import Optional
from urllib.parse import urlparse

from .. import config, http_client, journals
from ..logging_util import get_logger
from ..textnorm import clean_title, strip_markup
from .crossref import (_authors as crossref_authors, effective_date as crossref_effective_date,
                       is_junk as crossref_is_junk)
from .openalex import _from_inverted

log = get_logger("live_search")

OPENALEX_API = "https://api.openalex.org/works"
CROSSREF_API = "https://api.crossref.org/works"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

# Frequent Chinese queries get precise English equivalents. Other Chinese
# concepts are looked up by exact label in Wikidata; an unresolved term is
# still sent to OpenAlex unchanged, rather than silently guessing a field.
ZH_QUERY_ALIASES = {
    "固态电池": '("solid-state battery" OR "all-solid-state battery" OR "solid-state batteries")',
    "全固态电池": '("all-solid-state battery" OR "all-solid-state batteries")',
    "ai算法": '("machine learning algorithm" OR "deep learning algorithm" OR "artificial intelligence algorithm")',
    "人工智能算法": '("machine learning algorithm" OR "deep learning algorithm" OR "artificial intelligence algorithm")',
}


@lru_cache(maxsize=128)
def _search_terms(q: str) -> str:
    alias = ZH_QUERY_ALIASES.get(q.casefold())
    if alias:
        return alias
    if not re.search(r"[\u3400-\u9fff]", q) or len(q) > 40:
        return q
    resp = http_client.request(WIKIDATA_API, params={
        "action": "wbsearchentities", "format": "json", "language": "zh",
        "uselang": "en", "search": q, "limit": 3,
    }, timeout=4, retries=0, cache_ttl=7 * 86400)
    if not resp.ok:
        return q
    data = resp.json()
    if not isinstance(data, dict):
        return q
    for hit in data.get("search") or []:
        if not isinstance(hit, dict):
            continue
        match = hit.get("match") or {}
        if not isinstance(match, dict):
            continue
        label = (hit.get("label") or "").strip()
        desc = (hit.get("description") or "").lower()
        if (match.get("text") == q and label and
                not re.search(r"[\u3400-\u9fff]", label) and
                not any(x in desc for x in ("scholarly article", "academic journal", "book", "film"))):
            return '"{}"'.format(label.replace('"', '')) if " " in label else label
    return q


def _format_openalex_authors(authorships: list) -> tuple[str, int]:
    if not isinstance(authorships, list):
        return "", 0
    names = []
    for item in authorships:
        author = (item or {}).get("author") or {}
        name = (author.get("display_name") or "").strip()
        if name:
            names.append(name)
    count = len(names)
    if count == 0:
        return "", 0
    if count <= 5:
        return ", ".join(names), count
    return ", ".join(names[:5]) + " et al.", count


def _safe_url(value: str) -> str:
    url = (value or "").strip()
    parsed = urlparse(url)
    return url if parsed.scheme in ("http", "https") and parsed.netloc else ""


def _search_openalex(q: str, page: int = 1, page_size: int = 25, sort: str = "relevance") -> Optional[dict]:
    """Search OpenAlex global works index."""
    email = config.get("contact_email") or "literature-radar@research.org"
    if "@localhost" in email:
        email = "literature-radar@research.org"

    params = {
        "search": q,
        "page": max(1, int(page)),
        "per-page": max(5, min(50, int(page_size))),
        "mailto": email,
        "filter": "type:article|preprint|conference-paper|review,to_publication_date:"
                  + date.today().isoformat(),
    }
    if sort == "date":
        params["sort"] = "publication_date:desc,relevance_score:desc"
    elif sort == "cited":
        params["sort"] = "cited_by_count:desc"

    resp = http_client.request(OPENALEX_API, params=params, timeout=12, retries=1)
    if not resp.ok:
        log.warning("OpenAlex search failed with %d: %s", resp.status, resp.error)
        return None

    data = resp.json()
    if (not isinstance(data, dict) or
            not isinstance(data.get("results"), list) or
            not isinstance(data.get("meta"), dict)):
        log.warning("OpenAlex returned an invalid search response")
        return None
    results = data["results"]
    try:
        total = int(data["meta"].get("count") or len(results))
    except (TypeError, ValueError):
        log.warning("OpenAlex returned an invalid result count")
        return None

    papers = []
    for item in results:
        if not isinstance(item, dict):
            continue
        raw_doi = item.get("doi") or ""
        doi = raw_doi.replace("https://doi.org/", "").strip().lower()
        if not doi:
            openalex_id = (item.get("id") or "").rstrip("/").split("/")[-1]
            if not re.fullmatch(r"W\d+", openalex_id):
                continue
            doi = "openalex:" + openalex_id.lower()

        title = clean_title(item.get("title") or "")
        if not title or (item.get("publication_date") or "") > date.today().isoformat():
            continue

        loc = item.get("primary_location") or {}
        source = loc.get("source") or {}
        journal_name = (source.get("display_name") or "").strip()
        issn_l = source.get("issn_l") or ""

        # Check if journal matches any known curated tier
        jrn_info = journals.lookup([issn_l] if issn_l else [], journal_name)
        tier = jrn_info["tier"] if jrn_info else 0
        jif = jrn_info.get("jif") if jrn_info else None

        authors_str, author_count = _format_openalex_authors(item.get("authorships") or [])
        abstract = _from_inverted(item.get("abstract_inverted_index"))

        oa_info = item.get("open_access") or {}
        is_oa = bool(oa_info.get("is_oa"))
        oa_url = _safe_url(oa_info.get("oa_url") or "")

        biblio = item.get("biblio") or {}

        # Topic tags if available
        primary_topic = item.get("primary_topic") or {}
        topic_name = (primary_topic.get("display_name") or "").strip()
        labels = {}
        if topic_name:
            labels["topic"] = [topic_name]

        papers.append({
            "doi": doi,
            "title": title,
            "abstract": abstract,
            "abstract_source": "openalex" if abstract else "",
            "journal": journal_name or "Academic Publication",
            "journal_tier": tier,
            "journal_jif": jif,
            "publisher": (source.get("host_organization_name") or "").strip(),
            "authors": authors_str,
            "author_count": author_count,
            "pub_date": item.get("publication_date") or "",
            "volume": str(biblio.get("volume") or "").strip(),
            "issue": str(biblio.get("issue") or "").strip(),
            "pages": str(biblio.get("first_page") or "").strip(),
            "url": ("https://doi.org/" + doi if raw_doi else
                    _safe_url(loc.get("landing_page_url") or "") or
                    _safe_url(item.get("id") or "")),
            "is_oa": is_oa,
            "oa_url": oa_url,
            "cited_by": int(item.get("cited_by_count") or 0),
            "starred": False,
            "read_at": "",
            "labels": labels,
            "primary_node": topic_name,
            "relevance": 100,
            "source_engine": "openalex",
        })

    return {"papers": papers, "total": total, "source": "openalex"}


def _search_crossref(q: str, page: int = 1, page_size: int = 25, sort: str = "relevance") -> Optional[dict]:
    """Fallback search using Crossref Works API."""
    rows = max(5, min(50, int(page_size)))
    offset = (max(1, int(page)) - 1) * rows
    params = {
        "query": q,
        "rows": rows,
        "offset": offset,
        "filter": "until-pub-date:" + date.today().isoformat(),
    }
    if sort == "date":
        params["sort"] = "published"
        params["order"] = "desc"
    elif sort == "cited":
        params["sort"] = "is-referenced-by-count"
        params["order"] = "desc"

    resp = http_client.request(CROSSREF_API, params=params, timeout=12, retries=1)
    if not resp.ok:
        log.warning("Crossref fallback search failed: %s", resp.error)
        return None

    data = resp.json()
    msg = data.get("message") if isinstance(data, dict) else None
    if not isinstance(msg, dict) or not isinstance(msg.get("items"), list):
        log.warning("Crossref returned an invalid search response")
        return None
    items = msg["items"]
    try:
        total = int(msg.get("total-results") or len(items))
    except (TypeError, ValueError):
        log.warning("Crossref returned an invalid result count")
        return None

    papers = []
    for item in items:
        if not isinstance(item, dict):
            continue
        doi = (item.get("DOI") or "").strip().lower()
        if not doi:
            continue
        title = clean_title((item.get("title") or [""])[0])
        if not title or crossref_is_junk(title, item.get("type") or "journal-article"):
            continue

        container = " ".join((item.get("container-title") or [""])[0].split())
        issns = item.get("ISSN") or []
        jrn_info = journals.lookup(issns, container)
        tier = jrn_info["tier"] if jrn_info else 0
        jif = jrn_info.get("jif") if jrn_info else None

        authors_str, author_count = crossref_authors(item.get("author"))
        abstract = strip_markup(item.get("abstract") or "")
        pub_date = crossref_effective_date(item)

        papers.append({
            "doi": doi,
            "title": title,
            "abstract": abstract,
            "abstract_source": "crossref" if abstract else "",
            "journal": jrn_info["name"] if jrn_info else (container or "Journal Article"),
            "journal_tier": tier,
            "journal_jif": jif,
            "publisher": (item.get("publisher") or "").strip(),
            "authors": authors_str,
            "author_count": author_count,
            "pub_date": pub_date,
            "volume": str(item.get("volume") or "").strip(),
            "issue": str(item.get("issue") or "").strip(),
            "pages": (item.get("page") or "").strip(),
            "url": "https://doi.org/" + doi,
            "is_oa": 0,
            "oa_url": "",
            "cited_by": int(item.get("is-referenced-by-count") or 0),
            "starred": False,
            "read_at": "",
            "labels": {},
            "primary_node": "",
            "relevance": 100,
            "source_engine": "crossref",
        })

    return {"papers": papers, "total": total, "source": "crossref"}


def query_global(q: str, page: int = 1, page_size: int = 25, sort: str = "relevance") -> dict:
    """Execute multi-disciplinary global search.

    Tries OpenAlex first for full citation and topic support; falls back to
    Crossref on any issue.
    """
    q = (q or "").strip()
    if not q:
        return {"papers": [], "total": 0, "pages": 0, "page": page,
                "page_size": page_size, "source": "none", "query": "", "search_terms": ""}

    terms = _search_terms(q)
    result = _search_openalex(terms, page=page, page_size=page_size, sort=sort)
    if result is None:
        log.info("OpenAlex unavailable, falling back to Crossref for '%s'", q)
        result = _search_crossref(terms, page=page, page_size=page_size, sort=sort)
    if result is None:
        result = {"papers": [], "total": 0, "source": "unavailable",
                  "unavailable": True}

    result["page"] = page
    result["page_size"] = page_size
    result["query"] = q
    result["search_terms"] = terms
    result["pages"] = min(1000, math.ceil(result["total"] / page_size))
    return result
