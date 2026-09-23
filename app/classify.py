# -*- coding: utf-8 -*-
"""Relevance gate + multi-label classifier, driven by a field pack.

Pattern prefixes understood in a pack's rules
---------------------------------------------
``(none)``   substring match on the *loose* view (spaces normalised), so
             ``"solid state batter"`` also matches ``all-solid-state battery``
``sqw:``     whole-token match on the loose view -- for acronyms and short
             formulas (``sqw:lif`` matches ``LiF`` but not ``LiFePO4``)
``sq:``      substring match on the *joined* view -- for formulas containing
             punctuation (``sq:li13al03ti17po43`` matches ``Li1.3Al0.3Ti1.7(PO4)3``)
``re:``      regex on the loose view
``jre:``     regex on the joined view

Scores are additive; a hit in the title counts ``TITLE_WEIGHT`` times as much.
"""
from __future__ import annotations

import re
from typing import Iterable, Optional

from .fields.base import Facet, Node, Pack, Rule
from .textnorm import views

TITLE_WEIGHT = 2.0
CONTEXT_CAP = 8.0


class _Matcher:
    """Pre-compiled form of one ``(pattern, weight)`` rule."""
    __slots__ = ("kind", "needle", "rx", "weight", "raw")

    def __init__(self, pattern: str, weight: float):
        self.raw = pattern
        self.weight = float(weight)
        if pattern.startswith("sqw:"):
            self.kind = "rx_loose"
            self.needle = pattern[4:]
            self.rx = re.compile(r"(?<![a-z0-9])" + re.escape(self.needle) + r"(?![a-z0-9])")
        elif pattern.startswith("sq:"):
            self.kind = "joined"
            self.needle = pattern[3:]
            self.rx = None
        elif pattern.startswith("jre:"):
            self.kind = "rx_joined"
            self.needle = pattern[4:]
            self.rx = re.compile(self.needle)
        elif pattern.startswith("re:"):
            self.kind = "rx_loose"
            self.needle = pattern[3:]
            self.rx = re.compile(self.needle)
        else:
            # Normalise the literal the same way the text is normalised.
            self.kind = "loose"
            self.needle = views(pattern)[0]
            self.rx = None

    def hits(self, loose: str, joined: str) -> bool:
        if self.kind == "loose":
            return bool(self.needle) and self.needle in loose
        if self.kind == "joined":
            return bool(self.needle) and self.needle in joined
        if self.kind == "rx_loose":
            return bool(self.rx.search(loose))
        return bool(self.rx.search(joined))


def _compile(rules: Iterable[Rule]) -> list[_Matcher]:
    out = []
    for pattern, weight in rules or ():
        try:
            out.append(_Matcher(pattern, weight))
        except re.error:
            continue  # a malformed rule must never break the app
    return out


def _score(matchers, loose_t, joined_t, loose_a, joined_a):
    """Weighted score plus the list of patterns that fired."""
    total, hits = 0.0, []
    for m in matchers:
        in_title = m.hits(loose_t, joined_t)
        in_abs = m.hits(loose_a, joined_a)
        if not (in_title or in_abs):
            continue
        total += m.weight * (TITLE_WEIGHT if in_title else 1.0)
        hits.append(m.raw)
    return total, hits


class Classifier:
    """Compiled rules for one field pack.  Build once, reuse for every paper."""

    def __init__(self, pack: Pack):
        self.pack = pack
        self.core = _compile(pack.core)
        self.context = _compile(pack.context)
        self.negative = _compile(pack.negative)
        self.facets: dict[str, dict[str, list[_Matcher]]] = {}
        for f in pack.facets:
            self.facets[f.id] = {nid: _compile(node.rules) for nid, node in f.flat.items()}

    # ------------------------------------------------------------------
    def classify(self, title: str, abstract: str = "", extra: str = "") -> dict:
        """Classify one record against this field.

        Returns ``relevance``, ``in_scope``, ``labels`` (facet id -> ordered
        node ids), ``primary`` (best node on the first facet) and the raw
        ``scores`` / ``hits`` for transparency.
        """
        pack = self.pack
        loose_t, joined_t = views(title or "")
        loose_a, joined_a = views(abstract or "", extra or "")

        core, core_hits = _score(self.core, loose_t, joined_t, loose_a, joined_a)
        ctx, _ = _score(self.context, loose_t, joined_t, loose_a, joined_a)
        neg, neg_hits = _score(self.negative, loose_t, joined_t, loose_a, joined_a)

        # A paper is in scope when it names a concept from the field *and*
        # sits in a plausible context; strong off-topic markers subtract.
        relevance = core + min(ctx, CONTEXT_CAP) - neg
        if core >= 9.0:
            relevance += 2.0            # an unambiguous core term earns a nudge
        if core < pack.core_min:
            # Context words alone must never carry a paper into scope.
            relevance = min(relevance, core - pack.core_min)

        in_scope = core >= pack.core_min and relevance >= pack.relevance_min

        labels: dict[str, list[str]] = {}
        all_scores: dict[str, float] = {}
        all_hits: dict[str, list[str]] = {}
        for f in pack.facets:
            scores: dict[str, float] = {}
            for nid, matchers in self.facets[f.id].items():
                s, hs = _score(matchers, loose_t, joined_t, loose_a, joined_a)
                if s > 0:
                    scores[nid] = s
                    all_hits[nid] = hs[:6]
            # A subdivision hit implies its parent, even when the parent's own
            # wording never appears ("argyrodite" alone means sulfide).
            for nid, s in list(scores.items()):
                parent = f.parent.get(nid)
                if parent and s >= f.sub_min:
                    scores[parent] = max(scores.get(parent, 0.0), s * 0.9)
            chosen = sorted(
                (nid for nid, s in scores.items()
                 if s >= (f.top_min if f.parent.get(nid) is None else f.sub_min)),
                key=lambda n: -scores[n])
            if not chosen and f.unspecified:
                chosen = [f.unspecified]
            labels[f.id] = chosen
            all_scores.update(scores)

        primary = ""
        pf = pack.primary_facet
        tops = [n for n in labels.get(pf.id, []) if pf.parent.get(n) is None]
        if tops:
            primary = tops[0]
        elif labels.get(pf.id):
            primary = pf.parent.get(labels[pf.id][0]) or labels[pf.id][0]

        return {
            "relevance": round(relevance, 2),
            "in_scope": in_scope,
            "core": round(core, 2), "context": round(ctx, 2), "negative": round(neg, 2),
            "labels": labels,
            "primary": primary,
            "scores": {k: round(v, 2) for k, v in
                       sorted(all_scores.items(), key=lambda kv: -kv[1])},
            "hits": {"core": core_hits[:12], "negative": neg_hits[:8],
                     **{k: v for k, v in list(all_hits.items())[:8]}},
        }


_cache: dict[str, Classifier] = {}


def for_pack(pack: Pack) -> Classifier:
    """Cached classifier per pack id (rebuilt when a custom pack changes)."""
    key = "{}:{}".format(pack.id, id(pack))
    hit = _cache.get(key)
    if hit is None:
        hit = Classifier(pack)
        _cache[key] = hit
        if len(_cache) > 24:                 # bound the cache for custom packs
            for k in list(_cache)[:8]:
                if k != key:
                    _cache.pop(k, None)
    return hit


def classify(pack: Pack, title: str, abstract: str = "", extra: str = "") -> dict:
    return for_pack(pack).classify(title, abstract, extra)
