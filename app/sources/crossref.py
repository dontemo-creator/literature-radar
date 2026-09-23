# -*- coding: utf-8 -*-
"""Crossref: the primary metadata source.

Crossref is the right primary source here because it lets us ask exactly the
question we care about -- "everything these 122 ISSNs published since date X" --
with cursor paging and no practical rate ceiling.  It also carries abstracts
for Wiley, ACS, RSC, Springer Nature and APS deposits.
"""
from __future__ import annotations

from datetime import date as _date
from typing import Iterator, Optional

from .. import journals
from ..http_client import request
from ..logging_util import get_logger
from ..textnorm import clean_title, strip_markup

log = get_logger("crossref")

API = "https://api.crossref.org/works"
SELECT = ("DOI,title,abstract,container-title,ISSN,published,published-online,"
          "published-print,issued,created,type,URL,author,volume,issue,page,publisher,"
          "is-referenced-by-count,license")
# Crossref work types worth showing in a literature feed.
GOOD_TYPES = {"journal-article", "review-article", "proceedings-article", "book-chapter"}
# Front/back matter that some publishers deposit as articles.
JUNK_TITLES = (
    "issue information", "front cover", "back cover", "inside front cover",
    "inside back cover", "editorial board", "masthead", "table of contents",
    "contents list", "graphical contents", "cover picture", "frontispiece",
    "author index", "subject index", "corrigendum to", "erratum to",
    "publisher's note", "retraction", "acknowledgment to reviewers",
    "issue publication information", "cover image", "list of contributors",
)


def _date_parts(obj) -> str:
    """Crossref date-parts -> ``YYYY-MM-DD`` (padding partial dates)."""
    if not isinstance(obj, dict):
        return ""
    parts = obj.get("date-parts") or []
    if not parts or not isinstance(parts[0], list) or not parts[0]:
        return ""
    p = [x for x in parts[0] if isinstance(x, int)]
    if not p:
        return ""
    y = p[0]
    m = p[1] if len(p) > 1 else 1
    d = p[2] if len(p) > 2 else 1
    try:
        return "%04d-%02d-%02d" % (y, max(1, min(12, m)), max(1, min(31, d)))
    except (TypeError, ValueError):
        return ""


def effective_date(item: dict, today: str = "") -> str:
    """The date the article actually became readable.

    Many publishers (Elsevier especially) stamp an article with a *future*
    print-issue date: an article deposited in June 2026 may carry
    ``published: 2027-02``.  Sorting on that would float months-old papers
    above today's, which would wreck a "latest first" feed.  So:

      1. ``published-online`` when the publisher states it;
      2. otherwise ``published``/``issued`` when it is not in the future;
      3. otherwise ``created`` -- the DOI deposit date, the best available
         proxy for when the article went online.

    The result is never later than today.
    """
    today = today or _date.today().isoformat()
    online = _date_parts(item.get("published-online"))
    created = _date_parts(item.get("created"))
    stated = _date_parts(item.get("published")) or _date_parts(item.get("issued"))

    if online and online <= today:
        best = online
    elif stated and stated <= today:
        best = stated
    elif created:
        best = created
    else:
        best = online or stated or ""
    if best and best > today:
        best = created if (created and created <= today) else today
    return best


def _authors(items) -> tuple[str, int]:
    names = []
    for a in items or ():
        if not isinstance(a, dict):
            continue
        fam = (a.get("family") or "").strip()
        given = (a.get("given") or "").strip()
        if fam:
            initials = " ".join(w[0].upper() + "." for w in given.replace("-", " ").split() if w)
            names.append("{}, {}".format(fam, initials) if initials else fam)
        elif a.get("name"):
            names.append(str(a["name"]).strip())
    return "; ".join(names), len(names)


def _is_oa(licenses) -> bool:
    for lic in licenses or ():
        url = (lic.get("URL") or "").lower() if isinstance(lic, dict) else ""
        if "creativecommons.org" in url:
            return True
    return False


def is_junk(title: str, doc_type: str) -> bool:
    t = (title or "").strip().lower()
    if not t or len(t) < 8:
        return True
    if doc_type and doc_type not in GOOD_TYPES:
        return True
    return any(t.startswith(j) or t == j for j in JUNK_TITLES)


def parse(item: dict) -> Optional[dict]:
    """Normalise one Crossref item into the shape :mod:`app.store` expects."""
    if not isinstance(item, dict):
        return None
    doi = (item.get("DOI") or "").strip().lower()
    if not doi:
        return None
    title = clean_title(" ".join(t for t in (item.get("title") or []) if t))
    doc_type = (item.get("type") or "").strip()
    if is_junk(title, doc_type):
        return None

    issns = [s for s in (item.get("ISSN") or []) if s]
    container = " ".join((item.get("container-title") or [""])[0].split())
    jrn = journals.lookup(issns, container)
    if not jrn:
        return None  # outside the curated whitelist

    abstract = strip_markup(item.get("abstract") or "")
    pub = effective_date(item)
    authors, n_auth = _authors(item.get("author"))
    pages = (item.get("page") or "").strip()

    return {
        "doi": doi,
        "title": title,
        "abstract": abstract,
        "abstract_source": "crossref" if abstract else "",
        "journal": jrn["name"],
        "journal_tier": jrn["tier"],
        "journal_jif": jrn.get("jif"),
        "publisher": (item.get("publisher") or jrn.get("publisher") or "").strip(),
        "authors": authors,
        "author_count": n_auth,
        "pub_date": pub,
        "indexed_date": _date_parts(item.get("created")),
        "volume": str(item.get("volume") or "").strip(),
        "issue": str(item.get("issue") or "").strip(),
        "pages": pages,
        "url": "https://doi.org/" + doi,
        "doc_type": doc_type,
        "is_oa": 1 if _is_oa(item.get("license")) else 0,
        "cited_by": int(item.get("is-referenced-by-count") or 0),
    }


def _filter_string(issns, *, from_pub: str = "", from_created: str = "") -> str:
    parts = ["issn:" + i for i in issns]
    if from_pub:
        parts.append("from-pub-date:" + from_pub)
    if from_created:
        parts.append("from-created-date:" + from_created)
    parts.append("type:journal-article")
    return ",".join(parts)


def scan(issns, *, from_pub: str = "", from_created: str = "", rows: int = 1000,
         max_pages: int = 40, progress=None) -> Iterator[dict]:
    """Yield raw Crossref items for the whitelist, cursor-paging until done."""
    issns = list(issns)
    if not issns:
        return
    filt = _filter_string(issns, from_pub=from_pub, from_created=from_created)
    cursor, page, seen = "*", 0, 0
    while cursor and page < max_pages:
        resp = request(API, params={"filter": filt, "rows": rows, "cursor": cursor,
                                    "select": SELECT, "mailto": _mailto()},
                       timeout=120, retries=3)
        if not resp.ok:
            log.warning("scan stopped at page %d: %s", page + 1, resp.error)
            if progress:
                progress(page + 1, seen, resp.error)
            return
        msg = (resp.json() or {}).get("message") or {}
        items = msg.get("items") or []
        total = msg.get("total-results")
        if not items:
            return
        for it in items:
            yield it
        seen += len(items)
        page += 1
        if progress:
            progress(page, seen, "")
        nxt = msg.get("next-cursor")
        # Keep going while the server still has rows for us.  Relying on
        # "len(items) == rows" alone would stop early if a page came back short.
        more = (seen < total) if isinstance(total, int) else (len(items) >= rows)
        cursor = nxt if (nxt and nxt != cursor and more) else None
        if cursor and page >= max_pages:
            # Stopping here would silently drop records; say so loudly.
            msg_txt = ("达到单次扫描页数上限（{} 页 / {} 条），可能有更早的文献未被收录；"
                       "可用更小的时间窗多次更新").format(max_pages, seen)
            log.warning("page cap reached after %d records", seen)
            if progress:
                progress(page, seen, msg_txt)


def fetch_one(doi: str) -> Optional[dict]:
    resp = request(API + "/" + doi.strip().lower(), params={"mailto": _mailto()},
                   retries=2, cache_ttl=6 * 3600)
    if not resp.ok:
        return None
    return ((resp.json() or {}).get("message")) or None


def _mailto() -> str:
    from .. import config
    return config.get("contact_email")
