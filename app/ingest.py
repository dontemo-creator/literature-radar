# -*- coding: utf-8 -*-
"""The refresh pipeline, per research field: scan -> classify -> store -> back-fill.

One refresh of one field does four things:

1. **Publication pass** -- everything that field's journals published inside the
   rolling window (``from-pub-date``).
2. **Arrival pass** -- everything newly *deposited* in the last few days
   (``from-created-date``), which catches records that appear late.
3. **Classification** -- the field's relevance gate drops the large majority of
   the scanned corpus; survivors get that field's labels.
4. **Abstract back-fill** -- Crossref has no abstracts for some publishers
   (Elsevier in particular).  Gaps are retried against Europe PMC, the Elsevier
   API and OpenAlex, and papers still missing one are retried on later
   refreshes rather than being written off.

Refreshes are serialised per field and expose live progress for the UI.
"""
from __future__ import annotations

import json
import threading
import time
from datetime import date, datetime, timedelta, timezone
from typing import Optional

from . import classify as clf
from . import config, fields, http_client, journals, store
from .fields.base import Pack
from .logging_util import get_logger
from .sources import crossref, elsevier, europepmc, openalex

log = get_logger("ingest")

_locks: dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()
_state: dict[str, dict] = {}
_state_lock = threading.Lock()


def _lock_for(field: str) -> threading.Lock:
    with _locks_guard:
        if field not in _locks:
            _locks[field] = threading.Lock()
        return _locks[field]


def _blank_state(field: str) -> dict:
    return {"field": field, "running": False, "phase": "idle", "message": "",
            "scanned": 0, "matched": 0, "added": 0, "updated": 0, "removed": 0,
            "abstracts_filled": 0, "started": "", "finished": "", "ok": None,
            "partial": False, "error": ""}


def status(field: str = "") -> dict:
    with _state_lock:
        if field:
            return dict(_state.get(field) or _blank_state(field))
        return {k: dict(v) for k, v in _state.items()}


def _set(field: str, **kw) -> None:
    with _state_lock:
        cur = _state.setdefault(field, _blank_state(field))
        cur.update(kw)
        cur["field"] = field          # the key is owned by the state, not callers


def _reset(field: str, **kw) -> None:
    """Start a fresh progress record for this field."""
    with _state_lock:
        state = _blank_state(field)
        state.update(kw)
        state["field"] = field
        _state[field] = state


def is_running(field: str = "") -> bool:
    with _state_lock:
        if field:
            return bool((_state.get(field) or {}).get("running"))
        return any(v.get("running") for v in _state.values())


def _iso_days_ago(days: int) -> str:
    return (date.today() - timedelta(days=max(0, int(days)))).isoformat()


def days_since_refresh(field: str) -> float:
    """Days since the last successful refresh of this field."""
    last = store.meta_get("last_refresh_ok:" + field, "")
    if not last:
        return 9999.0
    try:
        when = datetime.fromisoformat(last)
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
    except ValueError:
        return 9999.0
    return max(0.0, (datetime.now(timezone.utc) - when).total_seconds() / 86400.0)


def adaptive_window(field: str) -> int:
    """How many days back to scan, based on how stale this field is.

    Scanning is the slow part (~5 s per 1000 records), so somebody who opens
    the app daily should not pay for a three-week sweep -- while somebody
    returning after a month must still get everything they missed.
    """
    gap = days_since_refresh(field)
    if gap >= 9000:
        return int(config.get("backfill_days") or 90)
    floor = int(config.get("refresh_window_days") or 21)
    return int(max(7, min(floor, gap + 4)) if gap + 4 <= floor else min(120, gap + 6))


def needs_refresh(field: str) -> tuple[bool, str]:
    """Should we refresh this field on app open?  Returns ``(yes, reason)``."""
    last = store.meta_get("last_refresh_ok:" + field, "")
    if not last:
        return True, "首次使用该方向，正在建立文献库"
    gap = days_since_refresh(field)
    hours = gap * 24
    limit = float(config.get("auto_refresh_after_hours") or 8)
    if hours >= limit:
        return True, "距上次更新 {:.0f} 小时，正在获取最新文献".format(hours)
    return False, "文献库为 {:.0f} 小时前更新".format(hours)


# ---------------------------------------------------------------- harvest ---
def _harvest(pack: Pack, from_pub: str, from_created: str, max_tier: int,
             counters: dict) -> None:
    field = pack.id
    issns = journals.issns_for(pack.journals, max_tier)
    if not issns:
        raise RuntimeError("方向「{}」没有可用的期刊清单".format(pack.zh))

    passes = []
    if from_pub:
        passes.append(("publication", {"from_pub": from_pub}, 150))
    if from_created:
        passes.append(("arrival", {"from_created": from_created}, 12))

    for name, kwargs, max_pages in passes:
        _set(field, phase="scan",
             message="正在扫描 {} 种期刊（{}）".format(
                 len(pack.journals), "按发表日期" if name == "publication" else "按新收录"))

        def progress(page, seen, err, _name=name):
            _set(field, scanned=counters["scanned"] + seen,
                 message="扫描第 {} 页，已检视 {} 条记录{}".format(
                     page, counters["scanned"] + seen, "（" + err + "）" if err else ""))
            if err:
                counters["errors"].append("{} pass: {}".format(_name, err))

        seen_this_pass = 0
        for item in crossref.scan(issns, rows=1000, max_pages=max_pages,
                                  progress=progress, **kwargs):
            seen_this_pass += 1
            rec = crossref.parse(item)
            if rec is None:
                continue
            verdict = clf.classify(pack, rec["title"], rec["abstract"])
            if not verdict["in_scope"]:
                # Already stored but no longer in scope (rules tightened): drop it.
                if store.get(field, rec["doi"]):
                    store.delete_field_papers(field, [rec["doi"]])
                    counters["removed"] += 1
                continue
            outcome = store.upsert(field, rec, verdict["labels"], verdict["primary"],
                                   verdict["relevance"])
            counters["matched"] += 1
            if outcome == "added":
                counters["added"] += 1
            elif outcome == "updated":
                counters["updated"] += 1
            _set(field, matched=counters["matched"], added=counters["added"],
                 updated=counters["updated"], removed=counters["removed"])
        counters["scanned"] += seen_this_pass
        _set(field, scanned=counters["scanned"])
        log.info("[%s] %s pass: %d records scanned", field, name, seen_this_pass)


def backfill_abstracts(field: str, limit: int = 120) -> int:
    """Try Europe PMC, then Elsevier, then OpenAlex for unknown abstracts."""
    gaps = store.missing_abstracts(field, limit=limit)
    if not gaps:
        return 0
    dois = [g["doi"] for g in gaps]
    filled = 0

    _set(field, phase="abstracts",
         message="正在补全 {} 篇缺失摘要（Europe PMC）".format(len(dois)))
    found = europepmc.abstracts_for(dois)
    for doi, text in found.items():
        if store.update_paper(doi, abstract=text, abstract_source="europepmc"):
            filled += 1
    remaining = [d for d in dois if d not in found]

    if remaining and elsevier.enabled():
        targets = [d for d in remaining if elsevier.handles(d)]
        if targets:
            _set(field, message="正在补全 {} 篇缺失摘要（Elsevier API）".format(len(targets)))
            found_el = elsevier.abstracts_for(targets)
            for doi, text in found_el.items():
                if store.update_paper(doi, abstract=text, abstract_source="elsevier"):
                    filled += 1
            remaining = [d for d in remaining if d not in found_el]

    if remaining:
        _set(field, message="正在补全 {} 篇缺失摘要（OpenAlex）".format(len(remaining)))
        for doi, info in openalex.enrich(remaining).items():
            payload = {"cited_by": info.get("cited_by", 0), "is_oa": info.get("is_oa", 0)}
            if info.get("abstract"):
                payload["abstract"] = info["abstract"]
                payload["abstract_source"] = "openalex"
            if store.update_paper(doi, **payload) and info.get("abstract"):
                filled += 1

    # Count the attempt so a permanently missing abstract stops being retried.
    for doi in dois:
        store.bump_abstract_try(doi)
    _set(field, abstracts_filled=filled)
    log.info("[%s] abstract back-fill: %d/%d filled", field, filled, len(dois))
    return filled


def reclassify(field: str, prune: bool = True) -> dict:
    """Re-apply the field's current rules to everything already stored.

    Rules get tightened over time, so anything that no longer passes the gate is
    removed rather than left behind as stale noise.
    """
    pack = fields.get(field)
    if pack is None:
        return {"error": "unknown field", "total": 0, "changed": 0, "removed": 0}
    changed, stale = 0, []
    for rec in store.field_records(field):
        v = clf.classify(pack, rec["title"], rec.get("abstract") or "")
        if prune and not v["in_scope"]:
            stale.append(rec["doi"])
            continue
        row = store.paper_row(rec["doi"]) or {}
        row["doi"] = rec["doi"]
        if store.upsert(field, row, v["labels"], v["primary"], v["relevance"]) == "updated":
            changed += 1
    removed = store.delete_field_papers(field, stale) if stale else 0
    total = len(store.field_dois(field))
    log.info("[%s] reclassified: %d relabelled, %d pruned, %d remain",
             field, changed, removed, total)
    return {"total": total, "changed": changed, "removed": removed}


def refresh(field: str, *, window_days: Optional[int] = None,
            backfill: bool = True) -> dict:
    """Run one full refresh of one field. Concurrent calls for it no-op."""
    pack = fields.get(field)
    if pack is None:
        return {"ok": False, "error": "unknown field: %s" % field}
    lock = _lock_for(field)
    if not lock.acquire(blocking=False):
        log.info("[%s] refresh already in progress, ignoring duplicate request", field)
        return {"ok": False, "skipped": True, "reason": "already running"}

    started = store.now_iso()
    counters = {"scanned": 0, "matched": 0, "added": 0, "updated": 0,
                "removed": 0, "errors": []}
    _reset(field, running=True, phase="start",
           message="正在准备刷新", started=started)
    t0 = time.time()
    ok = False
    try:
        empty = not store.field_dois(field)
        if window_days is None:
            window_days = (int(config.get("backfill_days")) if empty
                           else adaptive_window(field))
        from_pub = _iso_days_ago(window_days)
        gap = days_since_refresh(field)
        from_created = "" if empty else _iso_days_ago(
            max(5, int(gap) + 2) if gap < 60 else 60)
        max_tier = int(config.get("max_journal_tier") or 3)
        log.info("[%s] refresh start: from_pub=%s from_created=%s tier<=%d",
                 field, from_pub, from_created or "-", max_tier)

        _harvest(pack, from_pub, from_created, max_tier, counters)

        # A pass that errored out before returning anything is a failure, not a
        # quiet success -- otherwise the app looks healthy while showing nothing
        # and auto-refresh stays locked out for hours.
        if counters["scanned"] == 0:
            raise RuntimeError(counters["errors"][0] if counters["errors"]
                               else "数据源未返回任何记录（可能是网络问题，请稍后重试）")

        if backfill:
            backfill_abstracts(field)
        http_client.prune_cache()
        ok = True
        partial = bool(counters["errors"])
        store.meta_set("last_refresh_ok:" + field, store.now_iso())
        _set(field, phase="done", partial=partial,
             message="更新完成（部分数据源报错，已使用可获取的结果）" if partial else "更新完成")
    except Exception as exc:            # a refresh must never take the app down
        log.exception("[%s] refresh failed", field)
        counters["errors"].append("{}: {}".format(type(exc).__name__, exc))
        _set(field, phase="error", error=str(exc), message="刷新出错：{}".format(exc))
    finally:
        finished = store.now_iso()
        detail = json.dumps({"errors": counters["errors"][:8],
                             "seconds": round(time.time() - t0, 1)}, ensure_ascii=False)
        store.log_refresh(field=field, started=started, finished=finished,
                          ok=1 if ok else 0, scanned=counters["scanned"],
                          matched=counters["matched"], added=counters["added"],
                          updated=counters["updated"], detail=detail)
        _set(field, running=False, finished=finished, ok=ok)
        lock.release()
        log.info("[%s] refresh %s in %.0fs: scanned=%d matched=%d added=%d updated=%d",
                 field, "ok" if ok else "FAILED", time.time() - t0,
                 counters["scanned"], counters["matched"], counters["added"],
                 counters["updated"])
    return {"ok": ok, "field": field, "elapsed": round(time.time() - t0, 1), **counters}


def refresh_async(field: str, **kw) -> bool:
    """Kick off a refresh in the background. False if one is already running."""
    if is_running(field):
        return False
    threading.Thread(target=refresh, args=(field,), kwargs=kw,
                     name="ssb-refresh-" + field, daemon=True).start()
    return True
