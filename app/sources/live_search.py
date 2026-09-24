# -*- coding: utf-8 -*-
"""Real-time global multi-disciplinary academic search engine.

Enables searching across all scientific domains (Computer Science, AI,
Biomedicine, Materials, Physics, Chemistry, etc.) via OpenAlex with
automatic Crossref fallback.
"""
from __future__ import annotations

from datetime import date, timedelta
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


def _openalex_headers() -> dict:
    key = (config.get("openalex_api_key") or "").strip()
    return {"Authorization": "Bearer " + key} if key else {}

# Frequent Chinese queries get precise English equivalents. Other Chinese
# concepts are looked up by exact label in Wikidata; an unresolved term is
# still sent to OpenAlex unchanged, rather than silently guessing a field.
ZH_QUERY_ALIASES = {
    "固态电池": '("solid-state battery" OR "all-solid-state battery" OR "solid-state batteries")',
    "全固态电池": '("all-solid-state battery" OR "all-solid-state batteries")',
    "ai算法": '("machine learning algorithm" OR "deep learning algorithm" OR "artificial intelligence algorithm")',
    "人工智能算法": '("machine learning algorithm" OR "deep learning algorithm" OR "artificial intelligence algorithm")',
    "硫化物电解质": '"sulfide electrolyte"',
    "界面稳定性": '"interfacial stability"',
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


def _precise_terms(q: str) -> str:
    """A detailed query is searched as supplied; precision is checked in results."""
    if re.search(r"[\u3400-\u9fff]", q):
        parts = [part for part in re.split(r"[\s,，;；、]+", q) if part]
        if len(parts) > 1:
            return " AND ".join(_search_terms(part) for part in parts)
    return _search_terms(q)


def _crossref_terms(terms: str) -> str:
    """Crossref does not understand OpenAlex's Boolean OR syntax."""
    match = re.search(r'"([^"]+)"', terms)
    return match.group(1) if match else terms


def _title_words(value: str) -> list[str]:
    """Normalize spelling and punctuation for a conservative title match."""
    words = re.findall(r"[a-z0-9]+|[\u3400-\u9fff]+", value.casefold())
    return [word[:-3] + "y" if len(word) > 4 and word.endswith("ies") else
            word[:-1] if len(word) > 4 and word.endswith("s") and
            not word.endswith(("ss", "us", "is")) else word for word in words]


def _query_phrases(terms: str) -> list[str]:
    return re.findall(r'"([^"]+)"', terms) or [terms]


def _phrase_in_words(phrase: list[str], words: list[str]) -> bool:
    return bool(phrase) and any(words[i:i + len(phrase)] == phrase
                                for i in range(len(words) - len(phrase) + 1))


def _phrase_strength(terms: str, title: str, abstract: str = "") -> int:
    """Favor title matches, then abstract matches; reject full-text-only noise."""
    title_words = _title_words(title)
    abstract_words = _title_words(abstract)
    for phrase in _query_phrases(terms):
        if re.search(r"[\u3400-\u9fff]", phrase):
            if phrase.casefold() in title.casefold():
                return 5
            if phrase.casefold() in abstract.casefold():
                return 2
            continue
        words = _title_words(phrase)
        if _phrase_in_words(words, title_words):
            return 5
    for phrase in _query_phrases(terms):
        words = _title_words(phrase)
        if words and set(words) <= set(title_words):
            return 4
    for phrase in _query_phrases(terms):
        words = _title_words(phrase)
        if _phrase_in_words(words, abstract_words):
            return 2
    for phrase in _query_phrases(terms):
        words = _title_words(phrase)
        if words and set(words) <= set(abstract_words):
            return 1
    return 0


QUERY_STOPWORDS = {"a", "an", "and", "for", "in", "of", "on", "the", "to", "with",
                   "using", "based", "study", "research", "effect", "effects"}


def _topic_strength(q: str, terms: str, paper: dict, mode: str) -> int:
    """Require the whole subject in broad mode and all details in precise mode."""
    title = paper.get("title") or ""
    abstract = paper.get("abstract") or ""
    if mode != "precise":
        return _phrase_strength(terms, title, abstract)
    if " AND " in terms:
        groups = terms.split(" AND ")
        strengths = [_phrase_strength(group, title, abstract) for group in groups]
        if not all(strengths):
            return 0
        return 5 if all(s >= 4 for s in strengths) else 2
    phrases = _query_phrases(terms)
    # Boolean aliases describe alternate names for one broad concept.
    if terms.startswith("(") and " OR " in terms:
        return _phrase_strength(terms, title, abstract)
    if re.search(r"[\u3400-\u9fff]", terms):
        return _phrase_strength(terms, title, abstract)
    wanted = [w for w in _title_words(terms) if w not in QUERY_STOPWORDS]
    if not wanted:
        return 0
    title_words = _title_words(title)
    combined = set(title_words + _title_words(abstract))
    if not set(wanted) <= combined:
        return 0
    return 5 if set(wanted) <= set(title_words) else 2


def _classic_title_match(q: str, terms: str, title: str, mode: str) -> bool:
    """Keep highly cited full-text hits whose title actually names the topic."""
    title_words = _title_words(title)
    title_set = set(title_words)
    if q.casefold() in ("固态电池", "全固态电池"):
        return ({"solid", "state", "battery"} <= title_set and
                any(title_words[i:i + 2] == ["solid", "state"]
                    for i in range(len(title_words) - 1)))
    phrases = _query_phrases(terms)
    for phrase in phrases:
        if re.search(r"[\u3400-\u9fff]", phrase):
            if phrase.casefold() in title.casefold():
                return True
            continue
        words = _title_words(phrase)
        if not words:
            continue
        if mode == "precise":
            if _phrase_in_words(words, title_words):
                return True
        elif set(words) <= title_set:
            return True
    return False


CLASSIC_METHOD_HINTS = {
    "ai": (
        "machine learning", "deep learning", "neural network", "representation learning",
        "generative adversarial network", "transformer", "random forest",
        "gradient boosting", "support vector", "reinforcement learning",
        "federated learning", "bayesian optimization", "data mining",
        "scikit learn", "tensorflow", "pytorch", "caffe",
    ),
    "gene": ("gene editing", "genome editing", "crispr", "cas9"),
    "quantum": ("quantum computing", "quantum computation", "quantum computer",
                "quantum processor", "quantum algorithm", "quantum supremacy", "qubit"),
}


def _classic_profile(q: str) -> str:
    compact = re.sub(r"\s+", "", q.casefold())
    if compact in ("ai算法", "人工智能算法", "aialgorithms", "artificialintelligencealgorithms"):
        return "ai"
    if compact in ("基因编辑", "geneediting", "genomeediting"):
        return "gene"
    if compact in ("量子计算", "quantumcomputing"):
        return "quantum"
    return ""


def _classic_strength(q: str, terms: str, paper: dict, mode: str) -> int:
    title = paper.get("title") or ""
    if mode == "precise":
        return _topic_strength(q, terms, paper, mode)
    if q.casefold() in ("固态电池", "全固态电池"):
        return 5 if _classic_title_match(q, terms, title, mode) else 0
    strength = _phrase_strength(terms, title, paper.get("abstract") or "")
    profile = _classic_profile(q)
    if profile:
        words = _title_words(title)
        if any(_phrase_in_words(_title_words(hint), words)
               for hint in CLASSIC_METHOD_HINTS[profile]):
            strength = max(strength, 4)
    if profile == "gene":
        topic = (paper.get("primary_node") or "").casefold()
        if "crispr" in topic or "genetic engineering" in topic:
            strength = max(strength, 4)
    if profile == "ai":
        application = (title + " " + (paper.get("primary_node") or "")).casefold()
        if any(word in application for word in (
                "medical", "cancer", "healthcare", "disease", "diagnos",
                "retina", "protein", "drug discovery", "education")):
            strength = max(0, strength - 3)
    return strength


def _hot_strength(q: str, terms: str, paper: dict, mode: str) -> int:
    """Keep nearby applications of a method out of the new-paper shortlist."""
    if mode == "broad" and _classic_profile(q) == "gene":
        title = paper.get("title") or ""
        words = _title_words(title)
        if any(_phrase_in_words(_title_words(phrase), words) for phrase in (
                "gene editing", "genome editing", "genome engineering",
                "genetic engineering")):
            return 5
        return _phrase_strength(terms, title, paper.get("abstract") or "")
    return _classic_strength(q, terms, paper, mode)


def _source_quality(paper: dict) -> int:
    """Keep article and field preprint records ahead of general repositories."""
    venue = (paper.get("journal") or "").casefold()
    doi = (paper.get("doi") or "").casefold()
    title = (paper.get("title") or "").casefold()
    if any(name in venue for name in ("zenodo", "osf preprint", "figshare",
                                      "researchgate")) or doi.startswith((
                                          "10.5281/zenodo.", "10.17605/osf.io/")):
        return -6
    if title.startswith(("data and analysis code for", "data and code for",
                         "supplementary material for")):
        return -5
    if venue in ("", "academic publication"):
        return -2
    return 1


def _title_identity(title: str) -> str:
    """Merge preprint/deposit versions of the same paper without DOI loss."""
    return " ".join(_title_words(title))


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


def _search_openalex(q: str, page: int = 1, page_size: int = 25,
                     sort: str = "relevance", mode: str = "broad",
                     to_date: Optional[str] = None,
                     from_date: Optional[str] = None) -> Optional[dict]:
    """Search OpenAlex global works index."""
    filters = "type:article|preprint|conference-paper|review,to_publication_date:" \
              + (to_date or date.today().isoformat())
    if from_date:
        filters += ",from_publication_date:" + from_date
    params = {
        "search": q,
        "page": max(1, int(page)),
        "per-page": max(5, min(100, int(page_size))),
        "filter": filters,
    }
    if sort == "date":
        params["sort"] = "publication_date:desc,relevance_score:desc"
    elif sort == "cited":
        params["sort"] = "cited_by_count:desc"

    # Repeated UI searches should not spend a fresh API request on each tab
    # switch. Recent results stay fresh within two minutes; older citation
    # lists change slowly enough to cache longer.
    cache_ttl = 3600 if sort == "cited" else 120 if sort == "date" else 300
    resp = http_client.request(OPENALEX_API, params=params, headers=_openalex_headers(), timeout=12,
                               retries=1, cache_ttl=cache_ttl)
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
            "openalex_id": (item.get("id") or "").rstrip("/").split("/")[-1],
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


def _search_crossref(q: str, page: int = 1, page_size: int = 25,
                     sort: str = "relevance", mode: str = "broad",
                     to_date: Optional[str] = None,
                     from_date: Optional[str] = None) -> Optional[dict]:
    """Fallback search using Crossref Works API."""
    rows = max(5, min(100, int(page_size)))
    offset = (max(1, int(page)) - 1) * rows
    date_filter = "until-pub-date:" + (to_date or date.today().isoformat())
    if from_date:
        date_filter += ",from-pub-date:" + from_date
    params = {
        "query.bibliographic" if mode == "precise" else "query":
            _crossref_terms(q),
        "rows": rows,
        "offset": offset,
        "filter": date_filter,
    }
    if sort == "date":
        params["sort"] = "published"
        params["order"] = "desc"
    elif sort == "cited":
        params["sort"] = "is-referenced-by-count"
        params["order"] = "desc"

    resp = http_client.request(CROSSREF_API, params=params, timeout=12,
                               retries=1, cache_ttl=3600 if sort == "cited" else 120)
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

    # Crossref query ranking can include unrelated full-text or metadata hits.
    # Never present its unverified total as a count of matching papers.
    papers = [p for p in papers if _topic_strength(q, q, p, mode) > 0]
    return {"papers": papers, "total": len(papers), "source": "crossref",
            "candidate_count": total, "limited": True}


def query_global(q: str, page: int = 1, page_size: int = 25,
                 sort: str = "relevance", mode: str = "broad") -> dict:
    """Execute multi-disciplinary global search.

    Tries OpenAlex first for full citation and topic support; falls back to
    Crossref on any issue.
    """
    q = (q or "").strip()
    if not q:
        return {"papers": [], "total": 0, "pages": 0, "page": page,
                "page_size": page_size, "source": "none", "query": "", "search_terms": ""}

    mode = "precise" if mode == "precise" else "broad"
    terms = _precise_terms(q) if mode == "precise" else _search_terms(q)
    ranked = True
    if ranked:
        # Date-sorted full-text search can put incidental mentions at the top.
        # Inspect a bounded batch of new papers and favor a title or abstract
        # match.  The raw index count is retained as candidate_count only.
        first_page = (page - 1) * 2 + 1
        result = _search_openalex(terms, page=first_page, page_size=100,
                                  sort=sort, mode=mode)
        if result is not None:
            raw_total = result["total"]
            candidates = list(result["papers"])
            if raw_total > first_page * 100:
                extra = _search_openalex(terms, page=first_page + 1,
                                         page_size=100, sort=sort, mode=mode)
                if extra is not None:
                    candidates.extend(extra["papers"])
            scored = []
            seen = set()
            for paper in candidates:
                doi = paper["doi"]
                if doi in seen:
                    continue
                seen.add(doi)
                strength = _topic_strength(q, terms, paper, mode)
                if q.casefold() in ("固态电池", "全固态电池") and _classic_title_match(
                        q, terms, paper["title"], mode):
                    strength = max(strength, 4)
                if strength:
                    paper["topic_match"] = "title" if strength >= 4 else "abstract"
                    score = strength * 3 + _source_quality(paper)
                    scored.append((score, paper))
            # OpenAlex can index a preprint and several repository deposits
            # separately. Keep the best record for each normalized title.
            best_by_title = {}
            for score, paper in scored:
                identity = _title_identity(paper["title"])
                previous = best_by_title.get(identity)
                rank = (score, paper["cited_by"], paper["pub_date"])
                if previous is None or rank > previous[0]:
                    best_by_title[identity] = (rank, paper)
            unique = list(best_by_title.values())
            unique.sort(key=lambda item: (
                item[0][0],
                item[1]["cited_by"] if sort == "cited" else item[1]["pub_date"],
                item[1]["pub_date"] if sort == "cited" else item[1]["cited_by"]
            ), reverse=True)
            result["papers"] = [paper for _, paper in unique[:page_size]]
            result["candidate_count"] = raw_total
            result["ranked"] = True
            result["pages"] = min(50, math.ceil(raw_total / 200))
    else:
        result = _search_openalex(terms, page=page, page_size=page_size,
                                  sort=sort, mode=mode)
    if result is None:
        log.info("OpenAlex unavailable, falling back to Crossref for '%s'", q)
        result = _search_crossref(terms, page=1, page_size=100,
                                  sort=sort, mode=mode)
        if result is not None:
            seen = {p["doi"] for p in result["papers"]}
            for batch in (2, 3):
                if (len(result["papers"]) >= page_size or
                        result["candidate_count"] <= (batch - 1) * 100):
                    break
                extra = _search_crossref(terms, page=batch, page_size=100,
                                         sort=sort, mode=mode)
                if extra is None:
                    break
                for paper in extra["papers"]:
                    if paper["doi"] not in seen:
                        seen.add(paper["doi"])
                        result["papers"].append(paper)
            result["papers"] = result["papers"][:page_size]
            result["total"] = len(result["papers"])
    if result is None:
        result = {"papers": [], "total": 0, "source": "unavailable",
                  "unavailable": True}

    result["page"] = page
    result["page_size"] = page_size
    result["query"] = q
    result["search_terms"] = terms
    result["mode"] = mode
    if "pages" not in result:
        result["pages"] = 1 if result.get("limited") else min(
            max(1, 10000 // page_size), math.ceil(result["total"] / page_size))
    return result


def query_classics(q: str, mode: str = "broad", limit: int = 6) -> dict:
    """Older, highly cited topic matches, presented as candidates, not a canon."""
    q = (q or "").strip()
    limit = max(1, min(10, int(limit)))
    mode = "precise" if mode == "precise" else "broad"
    today = date.today()
    try:
        cutoff = today.replace(year=today.year - 5).isoformat()
    except ValueError:  # 29 February in a non-leap year
        cutoff = today.replace(year=today.year - 5, day=28).isoformat()
    if not q:
        return {"papers": [], "total": 0, "source": "none", "query": "",
                "mode": mode, "cutoff": cutoff}
    terms = _precise_terms(q) if mode == "precise" else _search_terms(q)
    sample_size = 50
    result = _search_openalex(terms, page=1, page_size=sample_size,
                              sort="cited", mode=mode, to_date=cutoff)
    if result is None:
        result = _search_crossref(terms, page=1, page_size=sample_size,
                                  sort="cited", mode=mode, to_date=cutoff)
    if result is None:
        return {"papers": [], "total": 0, "source": "unavailable",
                "unavailable": True, "query": q, "mode": mode, "cutoff": cutoff}
    seen = set()
    seen_titles = set()
    papers = []

    def collect(rows: list[dict]) -> None:
        for paper in rows:
            doi = paper.get("doi")
            title_key = _title_identity(paper.get("title") or "")
            if (doi in seen or title_key in seen_titles or
                    not paper.get("pub_date") or
                    paper["pub_date"] > cutoff or not paper.get("cited_by") or
                    _classic_strength(q, terms, paper, mode) <
                    (2 if mode == "precise" else 4)):
                continue
            seen.add(doi)
            seen_titles.add(title_key)
            papers.append(paper)

    collect(result["papers"])
    if result["source"] == "openalex":
        for page in (2, 3):
            if len(papers) >= limit or result["total"] <= (page - 1) * sample_size:
                break
            extra = _search_openalex(terms, page=page, page_size=sample_size,
                                     sort="cited", mode=mode, to_date=cutoff)
            if extra is None:
                break
            collect(extra["papers"])
        # CRISPR foundations often have titles that predate the term "gene
        # editing". Search this related method too, then verify the OpenAlex
        # topic before letting a title without the phrase into the shortlist.
        if mode == "broad" and _classic_profile(q) == "gene":
            extra = _search_openalex("crispr cas9", page=1, page_size=100,
                                     sort="cited", mode="broad", to_date=cutoff)
            if extra is not None:
                collect(extra["papers"])
    papers.sort(key=lambda p: (p.get("cited_by") or 0, p.get("pub_date") or ""),
                reverse=True)
    return {"papers": papers[:limit], "total": result["total"],
            "source": result["source"], "query": q, "mode": mode,
            "search_terms": terms, "cutoff": cutoff}


def query_hot(q: str, mode: str = "broad", limit: int = 12) -> dict:
    """Rank topic-matched candidate works by citations from the past 30 days."""
    q = (q or "").strip()
    mode = "precise" if mode == "precise" else "broad"
    limit = max(1, min(20, int(limit)))
    today = date.today()
    start = (today - timedelta(days=29)).isoformat()
    end = today.isoformat()
    empty = {"papers": [], "total": 0, "source": "none", "query": q,
             "mode": mode, "from_date": start, "to_date": end}
    if not q:
        return empty

    terms = _precise_terms(q) if mode == "precise" else _search_terms(q)
    result = _search_openalex(terms, page=1, page_size=100,
                              sort="cited", mode=mode, to_date=end)
    if result is None:
        return {**empty, "source": "unavailable", "unavailable": True}
    # This is a bounded candidate pool; global exhaustive ranking would need
    # a complete citation graph snapshot. Add newer relevant candidates so a
    # recently rising paper is not excluded solely by lifetime citation rank.
    recent = _search_openalex(terms, page=1, page_size=100,
                              sort="date", mode=mode, to_date=end)
    candidates = list(result["papers"]) + (recent["papers"] if recent else [])
    best = {}
    for paper in candidates:
        strength = _hot_strength(q, terms, paper, mode)
        if strength < (2 if mode == "precise" else 4) or _source_quality(paper) <= -5:
            continue
        work_id = paper.get("openalex_id") or ""
        if not re.fullmatch(r"W\d+", work_id):
            continue
        identity = _title_identity(paper.get("title") or "")
        prior = best.get(identity)
        if prior is None or paper.get("cited_by", 0) > prior.get("cited_by", 0):
            best[identity] = paper
    pool = list(best.values())
    pool.sort(key=lambda p: (p.get("cited_by", 0),
                             _hot_strength(q, terms, p, mode)), reverse=True)
    # Limit external calls; each count is verified independently in OpenAlex.
    shortlist = pool[:14]
    newer = sorted(pool[14:], key=lambda p: p.get("pub_date") or "", reverse=True)[:6]
    shortlist += newer
    verified = []
    failed = 0
    for paper in shortlist:
        count = _recent_citation_count(paper["openalex_id"], start, end)
        if count is None:
            failed += 1
            continue
        if count > 0:
            paper["recent_citations"] = count
            verified.append(paper)
    verified.sort(key=lambda p: (p["recent_citations"], p.get("cited_by", 0)),
                  reverse=True)
    if failed and not verified:
        return {**empty, "source": "unavailable", "unavailable": True}
    return {"papers": verified[:limit], "total": len(verified),
            "source": "openalex", "query": q, "mode": mode,
            "search_terms": terms, "from_date": start, "to_date": end,
            "candidates_checked": len(shortlist), "checks_failed": failed,
            "partial": bool(failed)}


def _recent_citation_count(work_id: str, start: str, end: str) -> Optional[int]:
    """Count indexed citing works published in the requested rolling window."""
    if not re.fullmatch(r"W\d+", work_id):
        return None
    resp = http_client.request(OPENALEX_API, params={
        "filter": f"cites:{work_id},from_publication_date:{start},to_publication_date:{end}",
        "per-page": 1,
    }, headers=_openalex_headers(), timeout=10, retries=0, cache_ttl=3600)
    if not resp.ok:
        return None
    data = resp.json()
    try:
        return max(0, int(data["meta"]["count"]))
    except (KeyError, TypeError, ValueError):
        return None
