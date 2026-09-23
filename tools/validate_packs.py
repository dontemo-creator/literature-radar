#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Check each field pack against live Crossref data.

A rule set that has never met real records is guesswork.  For every pack this
scans a recent window of its own journals and reports the hit rate plus samples
at both ends of the relevance range, so precision problems are visible instead
of assumed.

    python3 tools/validate_packs.py [days] [max_pages_per_pack]
"""
import json, pathlib, sys, time
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app import classify as clf
from app import fields, journals
from app.sources import crossref
from app.textnorm import clean_title, strip_markup

DAYS = int(sys.argv[1]) if len(sys.argv) > 1 else 14
MAX_PAGES = int(sys.argv[2]) if len(sys.argv) > 2 else 8
from datetime import date, timedelta
FROM = (date.today() - timedelta(days=DAYS)).isoformat()

report = {}
for pack in fields.builtin_packs():
    issns = journals.issns_for(pack.journals)
    t0, scanned, hits = time.time(), 0, []
    for item in crossref.scan(issns, from_pub=FROM, rows=1000, max_pages=MAX_PAGES):
        scanned += 1
        rec = crossref.parse(item)
        if rec is None:
            continue
        v = clf.classify(pack, rec["title"], rec["abstract"])
        if v["in_scope"]:
            hits.append({"rel": v["relevance"], "title": rec["title"],
                         "journal": rec["journal"], "labels": v["labels"],
                         "has_abs": bool(rec["abstract"]),
                         "abs": (rec["abstract"] or "")[:150]})
    hits.sort(key=lambda h: h["rel"])
    rate = 100.0 * len(hits) / max(1, scanned)
    report[pack.id] = {"zh": pack.zh, "scanned": scanned, "hits": len(hits),
                       "rate": round(rate, 2), "seconds": round(time.time() - t0, 1),
                       "issns": len(issns),
                       "unlabelled": sum(1 for h in hits if not any(h["labels"].values())),
                       "lowest": hits[:10], "highest": hits[-6:]}
    print("\n=== %s (%s) ===" % (pack.id, pack.zh), flush=True)
    print("  扫描 %d 条 / %d 个 ISSN，命中 %d 条（%.2f%%），耗时 %.0fs"
          % (scanned, len(issns), len(hits), rate, report[pack.id]["seconds"]), flush=True)
    print("  --- 相关度最低的（最可能是误收） ---", flush=True)
    for h in hits[:8]:
        print("    rel=%5.1f | %-26s | %s" % (h["rel"], h["journal"][:24], h["title"][:82]),
              flush=True)
    print("  --- 相关度最高的（应当明显对题） ---", flush=True)
    for h in hits[-4:]:
        print("    rel=%5.1f | %-26s | %s" % (h["rel"], h["journal"][:24], h["title"][:82]),
              flush=True)

json.dump(report, open("/tmp/pack_validation.json", "w"), indent=1, ensure_ascii=False)
print("\n\n=== 汇总 ===")
print("%-24s %-8s %-8s %-8s %s" % ("field", "scanned", "hits", "rate%", "无标签"))
for fid, r in report.items():
    print("%-24s %-8d %-8d %-8.2f %d" % (fid, r["scanned"], r["hits"], r["rate"], r["unlabelled"]))
