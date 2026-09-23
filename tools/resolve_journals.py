"""One-off build step: resolve curated journal names -> authoritative ISSNs via Crossref."""
import json, sys, difflib, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app import http_client as h

NAMES = [
 "Nature", "Science", "Nature Energy", "Nature Materials", "Nature Nanotechnology",
 "Nature Reviews Materials", "Nature Chemistry", "Nature Sustainability", "Nature Communications",
 "Science Advances", "Chemical Reviews", "Chemical Society Reviews", "Nature Reviews Chemistry",
 "Joule", "Chem", "Matter", "Energy & Environmental Science",
 "Journal of the American Chemical Society", "Angewandte Chemie International Edition",
 "Advanced Materials", "Advanced Energy Materials", "ACS Energy Letters",
 "Proceedings of the National Academy of Sciences", "Nature Reviews Clean Technology",
 "Electrochemical Energy Reviews",
 "Advanced Functional Materials", "Energy Storage Materials", "Materials Today",
 "Accounts of Chemical Research", "JACS Au", "Nano Energy", "ACS Nano", "Nano Letters",
 "Small", "Advanced Science", "Journal of Materials Chemistry A", "Chemistry of Materials",
 "Chemical Engineering Journal", "Journal of Energy Chemistry", "InfoMat", "eScience",
 "SusMat", "Carbon Energy", "Small Structures", "Aggregate", "Chemical Science",
 "ACS Materials Letters", "Materials Horizons", "National Science Review", "Science Bulletin",
 "Nano-Micro Letters", "Small Methods", "Device", "Interdisciplinary Materials",
 "Advanced Powder Materials", "npj Computational Materials", "Cell Reports Physical Science",
 "ACS Applied Materials & Interfaces", "Journal of Power Sources", "Electrochimica Acta",
 "Journal of The Electrochemical Society", "ACS Applied Energy Materials", "Batteries & Supercaps",
 "Journal of Materials Science & Technology", "Nano Research", "Green Energy & Environment",
 "Rare Metals", "Chinese Chemical Letters", "Energy Material Advances", "Battery Energy",
 "EcoMat", "Journal of Energy Storage", "Sustainable Energy & Fuels", "Physical Review Materials",
 "Chemical Communications", "The Journal of Physical Chemistry Letters", "ACS Central Science",
 "Energy & Environmental Materials", "Advanced Materials Technologies", "Materials Futures",
 "Journal of Materials Chemistry C", "ACS Applied Polymer Materials", "Solid State Ionics",
 "Journal of Alloys and Compounds", "Ceramics International", "ACS Sustainable Chemistry & Engineering",
]

def norm(s):
    return "".join(c for c in (s or "").lower().replace("&", "and") if c.isalnum())

out = []
for i, name in enumerate(NAMES, 1):
    r = h.request("https://api.crossref.org/journals",
                  params={"query": name, "rows": 20, "mailto": "ssb-radar@localhost"},
                  cache_ttl=86400 * 30)
    j = r.json() if r.ok else None
    items = (j or {}).get("message", {}).get("items", []) or []
    target = norm(name)
    best, best_score = None, 0.0
    for it in items:
        t = it.get("title") or ""
        score = 1.0 if norm(t) == target else difflib.SequenceMatcher(None, norm(t), target).ratio()
        if not it.get("ISSN"):
            score -= 0.5
        if score > best_score:
            best, best_score = it, score
    if best and best_score >= 0.86:
        rec = {"query": name, "ok": True, "title": (best.get("title") or "").strip(),
               "issn": [s for s in (best.get("ISSN") or []) if s],
               "publisher": best.get("publisher"), "score": round(best_score, 3)}
    else:
        rec = {"query": name, "ok": False,
               "candidates": [(it.get("title"), it.get("ISSN")) for it in items[:3]],
               "score": round(best_score, 3), "http": r.error if not r.ok else ""}
    out.append(rec)
    print(f"[{i:3d}/{len(NAMES)}] {'OK ' if rec['ok'] else 'MISS'} {name} -> {rec.get('title')} {rec.get('issn')}", flush=True)

json.dump(out, open("/tmp/journals_crossref.json", "w"), indent=1, ensure_ascii=False)
print("\nresolved", sum(1 for o in out if o["ok"]), "/", len(NAMES))
