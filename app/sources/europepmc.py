# -*- coding: utf-8 -*-
"""Europe PMC: abstract back-fill.

Europe PMC indexes far more than PubMed and reliably carries Nature-family and
Springer abstracts that Crossref lacks.  DOIs are queried in batches with an
``OR`` expression so a whole page of gaps costs one request.
"""
from __future__ import annotations

from ..http_client import request
from ..logging_util import get_logger
from ..textnorm import strip_markup

log = get_logger("europepmc")

API = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"
BATCH = 12


def abstracts_for(dois) -> dict[str, str]:
    """Map ``doi -> abstract`` for whichever DOIs Europe PMC knows."""
    out: dict[str, str] = {}
    dois = [d.strip().lower() for d in dois if d and d.strip()]
    for i in range(0, len(dois), BATCH):
        chunk = dois[i:i + BATCH]
        query = " OR ".join('DOI:"{}"'.format(d.replace('"', "")) for d in chunk)
        resp = request(API, params={"query": query, "format": "json",
                                    "resultType": "core", "pageSize": len(chunk) * 2},
                       retries=2, timeout=45)
        if not resp.ok:
            log.info("batch failed (%s), skipping %d DOIs", resp.error, len(chunk))
            continue
        results = (((resp.json() or {}).get("resultList")) or {}).get("result") or []
        for rec in results:
            doi = (rec.get("doi") or "").strip().lower()
            text = strip_markup(rec.get("abstractText") or "")
            if doi and text and len(text) > 80:
                out[doi] = text
    return out
