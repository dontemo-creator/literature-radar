# -*- coding: utf-8 -*-
"""Rewrite a field pack's CORE / CONTEXT / NEGATIVE blocks in place.

Hand-editing 30+ rule tuples with sed is how a closing bracket goes missing, so
every change here is computed from the imported lists and spliced back as a
freshly formatted block, with an assert on every anchor.

Usage is programmatic; see ``retune()``.
"""
from __future__ import annotations

import importlib
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _lit(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _fmt_block(name: str, rules, width: int = 92) -> str:
    """Render a rule list as an indented, wrapped Python literal."""
    parts = ["({}, {:g}),".format(_lit(k), float(w)) for k, w in rules]
    lines, cur = [], "   "
    for part in parts:
        if len(cur) + 1 + len(part) > width and cur.strip():
            lines.append(cur)
            cur = "   "
        cur += " " + part
    if cur.strip():
        lines.append(cur)
    return "{} = [\n{}\n]".format(name, "\n".join(lines))


def _splice(text: str, name: str, rules) -> str:
    start = text.index("\n{} = [".format(name)) + 1
    end = text.index("\n]\n", start) + len("\n]\n")
    block = _fmt_block(name, rules) + "\n"
    return text[:start] + block + text[end:]


def retune(module: str, *, demote=(), demote_weight=3.0, drop_core=(),
           neg_set=None, neg_drop=(), neg_add=(), dry_run=False) -> dict:
    """Move shared-theme markers out of ``core`` and adjust ``negative``.

    demote        core keys to move into context (they answer "serious about the
                  field's concerns", not "in the field")
    drop_core     core keys to delete outright
    neg_set       {key: weight} weight overrides for existing negatives
    neg_drop      negative keys to delete (dead or over-broad rules)
    neg_add       [(key, weight)] negatives to append
    """
    mod = importlib.import_module("app.fields." + module)
    core = list(mod.CORE)
    context = list(mod.CONTEXT)
    negative = list(mod.NEGATIVE)

    core_keys = {k for k, _ in core}
    for key in tuple(demote) + tuple(drop_core):
        assert key in core_keys, "{}: {!r} is not a core marker".format(module, key)
    ctx_keys = {k for k, _ in context}
    for key in demote:
        assert key not in ctx_keys, "{}: {!r} already in context".format(module, key)

    moved = [(k, demote_weight) for k, _ in core if k in set(demote)]
    core = [(k, w) for k, w in core if k not in set(demote) | set(drop_core)]
    context = context + moved

    neg_keys = {k for k, _ in negative}
    for key in tuple(neg_drop) + tuple((neg_set or {}).keys()):
        assert key in neg_keys, "{}: {!r} is not a negative marker".format(module, key)
    for key, _ in neg_add:
        assert key not in neg_keys, "{}: negative {!r} already there".format(module, key)
    negative = [(k, (neg_set or {}).get(k, w)) for k, w in negative
                if k not in set(neg_drop)] + list(neg_add)

    path = ROOT / "app" / "fields" / (module + ".py")
    text = original = path.read_text(encoding="utf-8")
    for name, rules in (("CORE", core), ("CONTEXT", context), ("NEGATIVE", negative)):
        text = _splice(text, name, rules)
    assert text != original, "{}: nothing changed".format(module)
    if not dry_run:
        path.write_text(text, encoding="utf-8")
    return {"core": len(core), "context": len(context), "negative": len(negative),
            "demoted": len(moved)}
