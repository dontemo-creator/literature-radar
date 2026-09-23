# -*- coding: utf-8 -*-
"""Registry of research fields.

Built-in packs are hand-authored and their relevance rules are tuned against
live Crossref data.  Anything else is covered by a *custom* pack, built from
keywords the reader supplies -- honest about being shallower than a curated
one, but immediately useful for a direction nobody anticipated.
"""
from __future__ import annotations

import json
from typing import Optional

from ..logging_util import get_logger
from .base import F, N, Pack

log = get_logger("fields")

CUSTOM_PREFIX = "custom:"

_BUILTIN_MODULES = [
    "solid_state_battery",
    "lithium_ion_battery",
    "sodium_ion_battery",
    "perovskite_solar",
    "electrocatalysis",
    "fuel_cell",
]

_builtin: dict[str, Pack] = {}
_custom: dict[str, Pack] = {}


def _load_builtin() -> None:
    if _builtin:
        return
    import importlib
    for mod_name in _BUILTIN_MODULES:
        try:
            mod = importlib.import_module("." + mod_name, __name__)
            pack: Pack = mod.PACK
        except Exception as exc:            # a broken pack must not hide the rest
            log.error("field pack %s failed to load: %s", mod_name, exc)
            continue
        if pack.id in _builtin:
            log.error("duplicate field id %s in %s", pack.id, mod_name)
            continue
        _builtin[pack.id] = pack
    log.info("loaded %d built-in field packs", len(_builtin))


def builtin_packs() -> list[Pack]:
    _load_builtin()
    order = {m: i for i, m in enumerate(_BUILTIN_MODULES)}
    return sorted(_builtin.values(),
                  key=lambda p: order.get(p.id.replace("-", "_"), 99))


def get(field_id: str) -> Optional[Pack]:
    _load_builtin()
    if field_id in _builtin:
        return _builtin[field_id]
    return _custom.get(field_id)


def default_id() -> str:
    _load_builtin()
    return "solid-state-battery" if "solid-state-battery" in _builtin else (
        next(iter(_builtin), ""))


def summaries() -> list[dict]:
    return [p.summary() for p in builtin_packs()]


# --------------------------------------------------------------------------
# Custom packs
# --------------------------------------------------------------------------
def custom_id(owner: int) -> str:
    return "{}{}".format(CUSTOM_PREFIX, owner)


def is_custom(field_id: str) -> bool:
    return (field_id or "").startswith(CUSTOM_PREFIX)


def build_custom(field_id: str, spec: dict, journal_names: list[str]) -> Pack:
    """Turn a reader's description into a working pack.

    ``spec`` carries ``name``, ``keywords`` (the phrases that define the field)
    and ``categories`` (``[{name|zh, keywords[]}, ...]``).  Every keyword becomes a
    rule; a phrase gets a higher weight than a single word because it is far
    less likely to fire by accident.
    """
    name = (spec.get("name") or "我的研究方向").strip()[:40]
    kws = _clean_list(spec.get("keywords"), limit=40)
    if not kws:
        raise ValueError("custom field needs at least one keyword")

    cats = []
    for i, cat in enumerate(spec.get("categories") or []):
        # the stored spec may name a category either way; accept both
        cname = (cat.get("name") or cat.get("zh") or "").strip()[:30]
        ckws = _clean_list(cat.get("keywords"), limit=25)
        if not cname or not ckws:
            continue
        cats.append(N("c{}".format(i), cname, cname,
                      [(k, _weight(k, base=7.0)) for k in ckws]))
        if len(cats) >= 24:
            break
    cats.append(N("other", "其他", "Other"))

    facets = [F("topic", "自定义分类", "Categories", cats,
                top_min=7.0, sub_min=8.0, unspecified="other",
                note_zh="按你填写的关键词归类，可在「研究方向」里随时调整")]

    core = [(k, _weight(k, base=9.0)) for k in kws]
    context = _clean_context(spec.get("context"))
    negative = [(k, 10.0) for k in _clean_list(spec.get("exclude"), limit=30)]

    return Pack(
        id=field_id, zh=name, en=spec.get("name_en") or name,
        tagline=(spec.get("tagline") or "、".join(kws[:4]))[:60],
        icon=spec.get("icon") or "✳️",
        facets=facets, core=core, context=context, negative=negative,
        journals=journal_names,
        search_hints=kws[:4],
        # A hand-tuned pack can afford a firm gate; a keyword pack cannot, so
        # one solid phrase match is enough to qualify.
        core_min=8.0, relevance_min=8.0,
        builtin=False,
    )


def register_custom(pack: Pack) -> None:
    _custom[pack.id] = pack


def drop_custom(field_id: str) -> None:
    _custom.pop(field_id, None)


def _clean_list(raw, limit: int) -> list[str]:
    if isinstance(raw, str):
        raw = [x for part in raw.replace("，", ",").replace("、", ",").split(",")
               for x in [part]]
    out, seen = [], set()
    for item in raw or []:
        s = " ".join(str(item).split()).strip().lower()
        if len(s) < 2 or s in seen:
            continue
        seen.add(s)
        out.append(s)
        if len(out) >= limit:
            break
    return out


def _clean_context(raw) -> list[tuple[str, float]]:
    extra = _clean_list(raw, limit=12)
    base = [("materials", 1.0), ("synthesis", 1.0), ("performance", 1.0),
            ("mechanism", 1.0), ("characterization", 1.0), ("device", 1.0),
            ("electrochemical", 1.0), ("efficiency", 1.0), ("stability", 1.0)]
    return base + [(k, 2.0) for k in extra]


def _weight(keyword: str, base: float) -> float:
    """Multi-word phrases are specific; bare words are cheap and risky."""
    words = keyword.split()
    if len(words) >= 3:
        return base + 2.0
    if len(words) == 2:
        return base
    return max(4.0, base - 3.0)
