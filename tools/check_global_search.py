#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check live global search across several disciplines without changing the library."""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.sources import live_search  # noqa: E402


DEFAULT_QUERIES = (
    "固态电池", "AI算法", "quantum computing",
    "cancer immunotherapy", "medieval history",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("queries", nargs="*", help="Topics to check (defaults span five fields)")
    args = parser.parse_args()
    queries = args.queries or DEFAULT_QUERIES
    today = date.today()
    failed = False

    for query in queries:
        result = live_search.query_global(query, page_size=5, sort="date")
        papers = result["papers"]
        dates = []
        for paper in papers:
            try:
                dates.append(date.fromisoformat(paper.get("pub_date") or ""))
            except ValueError:
                pass
        newest = max(dates) if dates else None
        lag = (today - newest).days if newest else None
        linked = sum(bool(paper.get("url")) for paper in papers)
        status = "UNAVAILABLE" if result.get("unavailable") else (
            "OK" if papers and linked == len(papers) else "CHECK")
        failed |= status != "OK"
        print("{}  {}  source={}  shown={}  approx_total={}  newest={}  lag_days={}  links={}/{}".format(
            status, query, result["source"], len(papers), result["total"],
            newest.isoformat() if newest else "—", lag if lag is not None else "—",
            linked, len(papers)))
        if papers:
            print("    sample_title={}".format((papers[0].get("title") or "")[:100]))
        if result.get("search_terms") != query:
            print("    searched_as={}".format(result["search_terms"]))

    print("Results reflect source indexing and the first date-sorted page; this is a smoke check, not a recall guarantee.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
