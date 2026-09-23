#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Resolve ISSNs for the journals the new field packs need (Crossref)."""
import difflib, json, pathlib, sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app import http_client as h

# Titles not already in the catalogue, grouped by the field that needs them.
NAMES = [
    # --- photovoltaics / optoelectronics
    "Nature Photonics", "Solar RRL", "Progress in Photovoltaics",
    "Solar Energy Materials and Solar Cells", "ACS Photonics",
    "Advanced Optical Materials", "Joule", "Nature Reviews Electrical Engineering",
    # --- catalysis / electrocatalysis
    "Nature Catalysis", "ACS Catalysis", "Applied Catalysis B Environmental",
    "Journal of Catalysis", "ChemCatChem", "ChemSusChem",
    "Catalysis Science & Technology", "Green Chemistry", "Nature Synthesis",
    "EES Catalysis", "ACS Electrochemistry",
    # --- hydrogen / fuel cells / membranes
    "International Journal of Hydrogen Energy", "Journal of Membrane Science",
    "Applied Energy", "Energy Conversion and Management",
    "Electrochemistry Communications", "Journal of Energy Storage",
    "Renewable and Sustainable Energy Reviews", "Fuel",
    # --- broader materials titles the new packs reference
    "Materials Science and Engineering R Reports", "Progress in Materials Science",
    "npj Flexible Electronics", "Advanced Energy and Sustainability Research",
    "ACS Applied Nano Materials", "Journal of Materials Chemistry B",
    "Chemical Engineering Science", "Separation and Purification Technology",
]


def norm(s):
    return "".join(c for c in (s or "").lower().replace("&", "and") if c.isalnum())


out = []
for i, name in enumerate(NAMES, 1):
    r = h.request("https://api.crossref.org/journals",
                  params={"query": name, "rows": 20, "mailto": "ssb-radar@localhost"},
                  cache_ttl=86400 * 30)
    items = ((r.json() or {}).get("message", {}) or {}).get("items", []) or []
    target, best, score = norm(name), None, 0.0
    for it in items:
        t = it.get("title") or ""
        s = 1.0 if norm(t) == target else difflib.SequenceMatcher(None, norm(t), target).ratio()
        if not it.get("ISSN"):
            s -= 0.5
        if s > score:
            best, score = it, s
    rec = ({"query": name, "ok": True, "title": (best.get("title") or "").strip(),
            "issn": sorted({x for x in (best.get("ISSN") or []) if x}),
            "publisher": best.get("publisher"), "score": round(score, 3)}
           if best and score >= 0.84 else
           {"query": name, "ok": False, "score": round(score, 3),
            "candidates": [(it.get("title"), it.get("ISSN")) for it in items[:3]]})
    out.append(rec)
    print("[%2d/%d] %s %s -> %s %s" % (i, len(NAMES), "OK  " if rec["ok"] else "MISS",
          name, rec.get("title"), rec.get("issn")), flush=True)

json.dump(out, open("/tmp/journals_more.json", "w"), indent=1, ensure_ascii=False)
print("\nresolved %d/%d" % (sum(1 for o in out if o["ok"]), len(NAMES)))
