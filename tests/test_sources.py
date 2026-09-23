# -*- coding: utf-8 -*-
"""Source adapters: parsing and date logic, with no network required."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app.sources import crossref, elsevier, openalex

fails = []


def check(name, got, want):
    ok = got == want
    if not ok:
        fails.append((name, got, want))
    print(f"  [{'OK ' if ok else 'FAIL'}] {name}: {got!r}" + ("" if ok else f" (want {want!r})"))


TODAY = "2026-09-07"

DATE_CASES = [
    ({"published": {"date-parts": [[2027, 2]]}, "created": {"date-parts": [[2026, 6, 19]]}},
     "2026-06-19", "future print issue falls back to deposit date"),
    ({"published": {"date-parts": [[2026, 8, 26]]}, "created": {"date-parts": [[2026, 8, 26]]}},
     "2026-08-26", "normal record"),
    ({"published-online": {"date-parts": [[2026, 9, 1]]},
      "published": {"date-parts": [[2026, 12]]},
      "created": {"date-parts": [[2026, 8, 30]]}}, "2026-09-01", "online date wins"),
    ({"created": {"date-parts": [[2026, 9, 5]]}}, "2026-09-05", "only a deposit date"),
    ({"published": {"date-parts": [[2028, 1]]}, "created": {"date-parts": [[2029, 1, 1]]}},
     TODAY, "everything future clamps to today"),
    ({"issued": {"date-parts": [[2026, 7, 4]]}}, "2026-07-04", "issued as fallback"),
    ({}, "", "no dates at all"),
]

FULL_ITEM = {
    "DOI": "10.1016/J.JOULE.2026.102638",
    "title": ["Enabling high-voltage <i>quasi</i>-solid-state batteries"],
    "abstract": "<jats:title>Abstract</jats:title><jats:p>An Li<jats:sub>6</jats:sub>"
                "PS<jats:sub>5</jats:sub>Cl catholyte.</jats:p>",
    "container-title": ["Joule"], "ISSN": ["2542-4351"],
    "published": {"date-parts": [[2026, 8, 1]]}, "created": {"date-parts": [[2026, 8, 1]]},
    "type": "journal-article", "author": [{"given": "Yu-Ming", "family": "Zhang"},
                                          {"given": "H", "family": "Li"},
                                          {"name": "Consortium X"}],
    "volume": "10", "issue": "8", "page": "102638", "publisher": "Elsevier BV",
    "is-referenced-by-count": 3,
    "license": [{"URL": "https://creativecommons.org/licenses/by/4.0/"}],
}


def run():
    for item, want, why in DATE_CASES:
        check("date: " + why, crossref.effective_date(item, TODAY), want)

    check("date-parts partial month", crossref._date_parts({"date-parts": [[2026, 8]]}), "2026-08-01")
    check("date-parts year only", crossref._date_parts({"date-parts": [[2026]]}), "2026-01-01")
    check("date-parts junk", crossref._date_parts({"date-parts": [[]]}), "")
    check("date-parts None", crossref._date_parts(None), "")

    check("authors formatted", crossref._authors(FULL_ITEM["author"])[0],
          "Zhang, Y. M.; Li, H.; Consortium X")
    check("author count", crossref._authors(FULL_ITEM["author"])[1], 3)
    check("authors empty", crossref._authors(None), ("", 0))
    check("cc licence means OA", crossref._is_oa(FULL_ITEM["license"]), True)
    check("no licence means not OA", crossref._is_oa(None), False)

    for junk in ("Issue Information", "Front Cover", "Editorial Board",
                 "Corrigendum to previous work", "Masthead"):
        check("junk rejected: " + junk, crossref.is_junk(junk, "journal-article"), True)
    check("real title kept", crossref.is_junk("Garnet electrolytes for solid-state cells",
                                              "journal-article"), False)
    check("wrong type rejected", crossref.is_junk("A real title here", "component"), True)
    check("empty title rejected", crossref.is_junk("", "journal-article"), True)

    rec = crossref.parse(FULL_ITEM)
    check("parsed doi lowercased", rec["doi"], "10.1016/j.joule.2026.102638")
    check("parsed title de-marked", rec["title"],
          "Enabling high-voltage quasi-solid-state batteries")
    check("parsed abstract tight formula", rec["abstract"], "An Li6PS5Cl catholyte.")
    check("parsed journal from ISSN", rec["journal"], "Joule")
    check("parsed tier", rec["journal_tier"], 1)
    check("parsed url", rec["url"], "https://doi.org/10.1016/j.joule.2026.102638")
    check("parsed citations", rec["cited_by"], 3)
    check("parsed OA", rec["is_oa"], 1)

    check("unknown journal dropped",
          crossref.parse({**FULL_ITEM, "ISSN": ["9999-9999"], "container-title": ["Nowhere"]}),
          None)
    check("no doi dropped", crossref.parse({**FULL_ITEM, "DOI": ""}), None)
    check("non-dict dropped", crossref.parse("not a dict"), None)
    check("journal resolved by title when ISSN unknown",
          (crossref.parse({**FULL_ITEM, "ISSN": []}) or {}).get("journal"), "Joule")

    check("inverted abstract rebuilt",
          openalex._from_inverted({"Solid": [0], "electrolytes": [1], "win": [2]}),
          "Solid electrolytes win")
    check("inverted empty", openalex._from_inverted({}), "")
    check("inverted junk", openalex._from_inverted("nope"), "")

    check("elsevier off without a key", elsevier.enabled(), False)
    check("elsevier prefix match", elsevier.handles("10.1016/j.joule.1"), True)
    check("elsevier ignores others", elsevier.handles("10.1038/nature"), False)
    check("elsevier returns '' when off", elsevier.abstract_for("10.1016/x"), "")
    check("elsevier extract", elsevier._extract(
        {"full-text-retrieval-response": {"coredata": {"dc:description": "x" * 100}}}),
        "x" * 100)
    check("elsevier extract short is rejected", elsevier._extract(
        {"full-text-retrieval-response": {"coredata": {"dc:description": "too short"}}}), "")

    print("\n%s" % ("ALL SOURCE CHECKS PASS" if not fails else "FAILURES:"))
    for f in fails:
        print("   ", f)
    return len(fails)


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
