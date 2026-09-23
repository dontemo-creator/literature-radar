# -*- coding: utf-8 -*-
"""The research-field model.

The app used to hard-code one subject (solid-state batteries).  A field pack
now carries everything subject-specific:

* **facets** -- the classification axes.  Solid-state batteries have two
  (electrolyte system, research theme); a different field may want other axes
  entirely, so the front end renders whatever a pack declares rather than
  assuming fixed names.
* **relevance rules** -- the core / context / negative marker lists that decide
  whether a paper belongs to the field at all.
* **journals** -- which titles from the shared catalogue to scan.

Rule syntax is shared with :mod:`app.classify`:
  ``(none)`` substring on the loose view   ``sqw:`` whole token on the loose view
  ``sq:``    substring on the joined view  ``re:`` / ``jre:`` regex on either
"""
from __future__ import annotations

from dataclasses import dataclass, field as dc_field
from typing import Iterable, Optional

Rule = tuple[str, float]


# A plain (unprefixed) rule matches as a *substring*, which is what makes stems
# like "batter" useful -- and what makes short fragments catastrophic.  The
# sodium pack once carried "na//": normalisation strips the slashes, leaving a
# bare "na" that matched "nanocomposite", "dynamics", "analysis" ... and pushed
# the field's hit rate to 40%.  Short fragments must therefore use ``sqw:``
# (whole token) instead, and packs are audited on construction.
MIN_PLAIN_TOKEN = 5
MIN_CONTEXT_TOKEN = 3


def audit_rules(rules, where: str, min_token: int = MIN_PLAIN_TOKEN) -> list[str]:
    """Report rules that would match far more text than intended."""
    from ..textnorm import views
    problems = []
    for pattern, weight in rules or ():
        if not isinstance(pattern, str) or not pattern.strip():
            problems.append("{}: empty pattern".format(where))
            continue
        if pattern.startswith(("sqw:", "sq:", "re:", "jre:")):
            body = pattern.split(":", 1)[1]
            if not body:
                problems.append("{}: prefix with no pattern ({!r})".format(where, pattern))
            continue
        loose = views(pattern)[0]
        if not loose:
            problems.append("{}: {!r} normalises to nothing".format(where, pattern))
        elif " " not in loose and len(loose) < min_token:
            problems.append(
                "{}: {!r} normalises to the short fragment {!r}; use 'sqw:{}' "
                "so it only matches a whole token".format(where, pattern, loose, loose))
    return problems


@dataclass
class Node:
    """One category, possibly with subdivisions."""
    id: str
    zh: str
    en: str
    rules: list[Rule] = dc_field(default_factory=list)
    children: list["Node"] = dc_field(default_factory=list)


@dataclass
class Facet:
    """One classification axis."""
    id: str
    zh: str
    en: str
    nodes: list[Node]
    # Threshold a top-level node must reach to be assigned, and the (higher)
    # threshold for a subdivision.
    top_min: float = 6.0
    sub_min: float = 7.0
    # When set, in-scope papers matching nothing on this axis land here rather
    # than becoming invisible the moment the reader filters by it.
    unspecified: Optional[str] = None
    note_zh: str = ""

    # ---- derived, filled by _index() -------------------------------------
    flat: dict[str, Node] = dc_field(default_factory=dict, repr=False)
    parent: dict[str, Optional[str]] = dc_field(default_factory=dict, repr=False)
    depth: dict[str, int] = dc_field(default_factory=dict, repr=False)


@dataclass
class Pack:
    """A research field: what to fetch, what is relevant, how to classify it."""
    id: str
    zh: str
    en: str
    tagline: str
    facets: list[Facet]
    core: list[Rule]
    context: list[Rule]
    negative: list[Rule]
    journals: list[str]
    search_hints: list[str] = dc_field(default_factory=list)
    # Minimum core score for a paper to count as in-field, and the overall
    # relevance floor.  Tuned per field: a broad field needs a firmer gate.
    core_min: float = 6.0
    relevance_min: float = 6.0
    builtin: bool = True
    icon: str = "◎"

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for f in self.facets:
            _index(f)
            for nid in f.flat:
                if nid in seen:
                    raise ValueError("duplicate node id across facets: " + nid)
                seen.add(nid)
        if not self.facets:
            raise ValueError("pack {} declares no facets".format(self.id))
        problems = self.audit()
        if problems:
            raise ValueError("field pack {} has unsafe rules:\n  {}".format(
                self.id, "\n  ".join(problems[:12])))

    def audit(self) -> list[str]:
        """Rules that would over-match.  Raised for built-ins, filtered for custom."""
        out = audit_rules(self.core, "{}.core".format(self.id))
        out += audit_rules(self.negative, "{}.negative".format(self.id))
        out += audit_rules(self.context, "{}.context".format(self.id),
                           min_token=MIN_CONTEXT_TOKEN)
        for f in self.facets:
            for nid, node in f.flat.items():
                out += audit_rules(node.rules, "{}.{}.{}".format(self.id, f.id, nid))
        return out

    # ---- lookups ---------------------------------------------------------
    @property
    def primary_facet(self) -> Facet:
        return self.facets[0]

    def facet(self, facet_id: str) -> Optional[Facet]:
        return next((f for f in self.facets if f.id == facet_id), None)

    def facet_of(self, node_id: str) -> Optional[Facet]:
        return next((f for f in self.facets if node_id in f.flat), None)

    def node(self, node_id: str) -> Optional[Node]:
        f = self.facet_of(node_id)
        return f.flat.get(node_id) if f else None

    def all_node_ids(self) -> set[str]:
        return {nid for f in self.facets for nid in f.flat}

    def label(self, node_id: str, lang: str = "zh") -> str:
        n = self.node(node_id)
        if not n:
            return node_id
        return n.zh if lang == "zh" else n.en

    def path_label(self, node_id: str, lang: str = "zh") -> str:
        """``氯化物`` -> ``卤化物电解质 › 氯化物`` for breadcrumb chips."""
        f = self.facet_of(node_id)
        if not f:
            return node_id
        parent = f.parent.get(node_id)
        own = self.label(node_id, lang)
        return "{} › {}".format(self.label(parent, lang), own) if parent else own

    def descendants(self, node_id: str) -> set[str]:
        f = self.facet_of(node_id)
        if not f:
            return {node_id}
        out = {node_id}
        changed = True
        while changed:
            changed = False
            for nid, par in f.parent.items():
                if par in out and nid not in out:
                    out.add(nid)
                    changed = True
        return out

    def tree_json(self) -> list[dict]:
        def pack_nodes(nodes: Iterable[Node]) -> list[dict]:
            return [{"id": n.id, "zh": n.zh, "en": n.en,
                     "children": pack_nodes(n.children)} for n in nodes]
        return [{"id": f.id, "zh": f.zh, "en": f.en, "note": f.note_zh,
                 "unspecified": f.unspecified, "nodes": pack_nodes(f.nodes)}
                for f in self.facets]

    def summary(self) -> dict:
        """What the field picker needs to show a card."""
        return {"id": self.id, "zh": self.zh, "en": self.en, "tagline": self.tagline,
                "icon": self.icon, "builtin": self.builtin,
                "journals": len(self.journals),
                "facets": [{"id": f.id, "zh": f.zh,
                            "top": len([n for n in f.nodes])} for f in self.facets],
                "categories": sum(len(f.flat) for f in self.facets),
                "hints": self.search_hints[:3]}


def _index(f: Facet) -> None:
    f.flat, f.parent, f.depth = {}, {}, {}

    def walk(nodes: list[Node], parent: Optional[str], depth: int) -> None:
        for n in nodes:
            if n.id in f.flat:
                raise ValueError("duplicate node id in facet {}: {}".format(f.id, n.id))
            f.flat[n.id] = n
            f.parent[n.id] = parent
            f.depth[n.id] = depth
            walk(n.children, n.id, depth + 1)

    walk(f.nodes, None, 0)
    if f.unspecified and f.unspecified not in f.flat:
        raise ValueError("facet {} points 'unspecified' at a missing node {}".format(
            f.id, f.unspecified))


# --------------------------------------------------------------------------
# Terse constructors, so a pack definition reads as data rather than code.
# --------------------------------------------------------------------------
def N(node_id: str, zh: str, en: str, rules: list[Rule] | None = None,
      children: list[Node] | None = None) -> Node:
    return Node(id=node_id, zh=zh, en=en, rules=rules or [], children=children or [])


def F(facet_id: str, zh: str, en: str, nodes: list[Node], **kw) -> Facet:
    return Facet(id=facet_id, zh=zh, en=en, nodes=nodes, **kw)
