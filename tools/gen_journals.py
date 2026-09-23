"""Build app/journals.py from the resolved Crossref records + curated tier/IF table."""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app import http_client as h

recs = json.load(open('/tmp/journals_crossref.json'))
by_query = {r["query"]: r for r in recs}

# fill the last gap
r = h.request("https://api.crossref.org/journals/2575-0356",
              params={"mailto": "ssb-radar@localhost"}, cache_ttl=86400*30)
m = (r.json() or {}).get("message") or {}
if m.get("title"):
    by_query["Energy & Environmental Materials"] = {
        "query": "Energy & Environmental Materials", "ok": True, "title": m["title"].strip(),
        "issn": sorted(set(s for s in (m.get("ISSN") or []) if s)), "publisher": m.get("publisher")}

# tier: 1 = flagship, 2 = leading, 3 = solid specialist.  jif = approximate JCR reference value.
META = {
 "Nature": (1, 50.5), "Science": (1, 44.7), "Nature Energy": (1, 49.7),
 "Nature Materials": (1, 37.2), "Nature Nanotechnology": (1, 36.8),
 "Nature Reviews Materials": (1, 79.8), "Nature Chemistry": (1, 19.2),
 "Nature Sustainability": (1, 25.7), "Nature Communications": (1, 15.7),
 "Science Advances": (1, 12.5), "Chemical Reviews": (1, 51.4),
 "Chemical Society Reviews": (1, 40.4), "Nature Reviews Chemistry": (1, 33.9),
 "Joule": (1, 38.6), "Chem": (1, 19.1), "Matter": (1, 17.5),
 "Energy & Environmental Science": (1, 32.4),
 "Journal of the American Chemical Society": (1, 14.4),
 "Angewandte Chemie International Edition": (1, 16.1),
 "Advanced Materials": (1, 27.4), "Advanced Energy Materials": (1, 24.4),
 "ACS Energy Letters": (1, 19.3), "Proceedings of the National Academy of Sciences": (1, 9.4),
 "Nature Reviews Clean Technology": (1, None), "Electrochemical Energy Reviews": (1, 28.5),
 "Advanced Functional Materials": (2, 18.5), "Energy Storage Materials": (2, 18.9),
 "Materials Today": (2, 21.1), "Accounts of Chemical Research": (2, 16.4),
 "JACS Au": (2, 8.5), "Nano Energy": (2, 16.8), "ACS Nano": (2, 15.8),
 "Nano Letters": (2, 9.6), "Small": (2, 13.0), "Advanced Science": (2, 14.3),
 "Journal of Materials Chemistry A": (2, 10.7), "Chemistry of Materials": (2, 7.2),
 "Chemical Engineering Journal": (2, 13.3), "Journal of Energy Chemistry": (2, 14.0),
 "InfoMat": (2, 22.7), "eScience": (2, 42.9), "SusMat": (2, 18.7),
 "Carbon Energy": (2, 19.5), "Small Structures": (2, 13.9), "Aggregate": (2, 13.9),
 "Chemical Science": (2, 7.6), "ACS Materials Letters": (2, 9.6),
 "Materials Horizons": (2, 12.2), "National Science Review": (2, 16.6),
 "Science Bulletin": (2, 18.8), "Nano-Micro Letters": (2, 31.6),
 "Small Methods": (2, 10.7), "Device": (2, 8.7), "Interdisciplinary Materials": (2, 18.6),
 "Advanced Powder Materials": (2, 28.6), "npj Computational Materials": (2, 9.4),
 "Cell Reports Physical Science": (2, 7.9),
 "ACS Applied Materials & Interfaces": (3, 8.3), "Journal of Power Sources": (3, 8.1),
 "Electrochimica Acta": (3, 5.5), "Journal of The Electrochemical Society": (3, 3.1),
 "ACS Applied Energy Materials": (3, 5.4), "Batteries & Supercaps": (3, 4.7),
 "Journal of Materials Science & Technology": (3, 11.2), "Nano Research": (3, 9.6),
 "Green Energy & Environment": (3, 12.6), "Rare Metals": (3, 8.6),
 "Chinese Chemical Letters": (3, 9.4), "Energy Material Advances": (3, 26.0),
 "Battery Energy": (3, 8.5), "EcoMat": (3, 9.2), "Journal of Energy Storage": (3, 8.9),
 "Sustainable Energy & Fuels": (3, 5.0), "Physical Review Materials": (3, 3.4),
 "Chemical Communications": (3, 4.9), "The Journal of Physical Chemistry Letters": (3, 4.8),
 "ACS Central Science": (3, 12.7), "Energy & Environmental Materials": (3, 13.0),
 "Advanced Materials Technologies": (3, 6.8), "Materials Futures": (3, 12.0),
 "Journal of Materials Chemistry C": (3, 5.7), "ACS Applied Polymer Materials": (3, 4.4),
 "Solid State Ionics": (3, 3.0), "Journal of Alloys and Compounds": (3, 5.8),
 "Ceramics International": (3, 5.1), "ACS Sustainable Chemistry & Engineering": (3, 7.1),
}
# Preferred display names (Crossref titles are sometimes abbreviated oddly).
DISPLAY_FIX = {
 "Journal of Materials Science & Technology": "Journal of Materials Science & Technology",
 "Proceedings of the National Academy of Sciences": "PNAS",
 "The Journal of Physical Chemistry Letters": "J. Phys. Chem. Lett.",
 "Angewandte Chemie International Edition": "Angewandte Chemie Int. Ed.",
 "Journal of the American Chemical Society": "J. Am. Chem. Soc. (JACS)",
 "Journal of The Electrochemical Society": "J. Electrochem. Soc.",
}

rows, seen_issn = [], {}
for name, (tier, jif) in META.items():
    rec = by_query.get(name)
    if not rec or not rec.get("ok") or not rec.get("issn"):
        print("!! unresolved, skipped:", name); continue
    issns = sorted(set(rec["issn"]))
    dup = [i for i in issns if i in seen_issn]
    if dup:
        print("!! duplicate ISSN", dup, "between", seen_issn[dup[0]], "and", name); continue
    for i in issns:
        seen_issn[i] = name
    rows.append({"name": DISPLAY_FIX.get(name, rec["title"]), "canonical": name,
                 "issn": issns, "tier": tier, "jif": jif,
                 "publisher": (rec.get("publisher") or "").strip()})

rows.sort(key=lambda r: (r["tier"], -(r["jif"] or 0), r["name"]))
out = pathlib.Path("app/journals.py")
body = ['# -*- coding: utf-8 -*-',
        '"""Curated whitelist of high-quality journals that publish solid-state battery work.',
        '',
        'Generated by ``tools/gen_journals.py`` from authoritative Crossref journal records.',
        'ISSNs are what the ingest layer actually queries, so they must stay exact.',
        '',
        '``tier``  1 = flagship, 2 = leading specialist, 3 = solid specialist / high volume',
        '``jif``   approximate recent JCR impact factor, for display and sorting only',
        '"""',
        'from __future__ import annotations', '',
        'TIER_LABELS = {',
        '    1: {"en": "Flagship", "zh": "顶级期刊"},',
        '    2: {"en": "Leading", "zh": "一流期刊"},',
        '    3: {"en": "Specialist", "zh": "专业期刊"},',
        '}', '',
        'JOURNALS = [']
for r in rows:
    body.append("    {{\"name\": {n!r}, \"issn\": {i!r}, \"tier\": {t}, \"jif\": {j!r}, \"publisher\": {p!r}}},"
                .format(n=r["name"], i=r["issn"], t=r["tier"], j=r["jif"], p=r["publisher"]))
body += [']', '',
 '# ---- lookup tables -------------------------------------------------------',
 'ISSN_TO_JOURNAL = {issn: j for j in JOURNALS for issn in j["issn"]}',
 'ALL_ISSNS = sorted(ISSN_TO_JOURNAL)',
 'BY_NAME = {j["name"]: j for j in JOURNALS}',
 '',
 '',
 'def issns_for_tiers(max_tier: int = 3) -> list[str]:',
 '    """Every ISSN belonging to a journal at or above ``max_tier``."""',
 '    return sorted({i for j in JOURNALS if j["tier"] <= max_tier for i in j["issn"]})',
 '',
 '',
 'def lookup(issns, container_title: str = "") -> dict | None:',
 '    """Resolve a Crossref record to a whitelisted journal, ISSN first then title."""',
 '    for issn in issns or ():',
 '        j = ISSN_TO_JOURNAL.get((issn or "").strip().upper())',
 '        if j:',
 '            return j',
 '    key = " ".join((container_title or "").split())',
 '    return BY_NAME.get(key)',
 '']
out.write_text("\n".join(body) + "\n", encoding="utf-8")
print("\nwrote", out, "with", len(rows), "journals")
