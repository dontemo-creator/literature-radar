#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""One-off: turn the original hard-coded taxonomy into a field pack module.

Generated rather than retyped: the rule weights were tuned against live data
over many iterations, and hand-copying 490 lines would be a transcription-error
factory.
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app import taxonomy as old
from app import journals as oldj


def emit_nodes(nodes, indent):
    pad = " " * indent
    out = []
    for n in nodes:
        rules = ", ".join("({!r}, {})".format(p, w) for p, w in (n.get("rules") or []))
        kids = n.get("children") or []
        head = "{}N({!r}, {!r}, {!r},".format(pad, n["id"], n["name_zh"], n["name_en"])
        out.append(head)
        out.append("{}  [{}],".format(pad, rules) if rules else "{}  [],".format(pad))
        if kids:
            out.append("{}  [".format(pad))
            out.extend(emit_nodes(kids, indent + 4))
            out.append("{}  ]),".format(pad))
        else:
            out[-1] = out[-1].rstrip(",") + "),"
    return out


def rules_block(rules, indent):
    pad = " " * indent
    lines, cur = [], pad
    for p, w in rules:
        piece = "({!r}, {}), ".format(p, w)
        if len(cur) + len(piece) > 96:
            lines.append(cur.rstrip())
            cur = pad
        cur += piece
    if cur.strip():
        lines.append(cur.rstrip().rstrip(","))
    return "\n".join(lines)


header = '''# -*- coding: utf-8 -*-
"""Field pack: solid-state batteries.

The original subject of the app, and the one whose rules are tuned against a
real corpus: on 44,000 scanned journal records the relevance gate keeps ~2.9%,
and the negative markers exist to exclude specific families of near-miss papers
that were measured leaking in -- liquid-electrolyte work that mentions the
"solid electrolyte interphase", proton-exchange fuel cells, solid oxide fuel
cells, aqueous zinc systems and neuromorphic devices.

Generated once from the pre-refactor taxonomy by tools/convert_ssb_pack.py, then
maintained here.
"""
from __future__ import annotations

from .base import F, N, Pack

'''

parts = [header]

parts.append("CHEMISTRY = [\n" + "\n".join(emit_nodes(old.CHEMISTRY, 4)) + "\n]\n")
parts.append("THEME = [\n" + "\n".join(emit_nodes(old.THEME, 4)) + "\n]\n")
parts.append("CORE = [\n" + rules_block(old.CORE_MARKERS, 4) + ",\n]\n")
parts.append("CONTEXT = [\n" + rules_block(old.CONTEXT_MARKERS, 4) + ",\n]\n")
parts.append("NEGATIVE = [\n" + rules_block(old.NEGATIVE_MARKERS, 4) + ",\n]\n")

journal_names = [j["name"] for j in oldj.JOURNALS]
jl, cur = [], "    "
for name in journal_names:
    piece = "{!r}, ".format(name)
    if len(cur) + len(piece) > 96:
        jl.append(cur.rstrip())
        cur = "    "
    cur += piece
if cur.strip():
    jl.append(cur.rstrip().rstrip(","))
parts.append("JOURNALS = [\n" + "\n".join(jl) + ",\n]\n")

parts.append('''
PACK = Pack(
    id="solid-state-battery",
    zh="固态电池",
    en="Solid-State Batteries",
    tagline="固态电解质、界面、锂金属负极与全固态电芯",
    icon="🔋",
    facets=[
        F("chemistry", "电解质体系", "Electrolyte systems", CHEMISTRY,
          top_min=6.0, sub_min=7.0, unspecified="other",
          note_zh="点箭头展开细分体系，可多选（或关系）"),
        F("theme", "研究主题", "Research themes", THEME, top_min=8.0, sub_min=8.0),
    ],
    core=CORE,
    context=CONTEXT,
    negative=NEGATIVE,
    journals=JOURNALS,
    search_hints=["argyrodite", '"stack pressure"', "LLZO", "Li6PS5Cl interface"],
    core_min=6.0,
    relevance_min=6.0,
)
''')

out = pathlib.Path("app/fields/solid_state_battery.py")
out.write_text("\n".join(parts), encoding="utf-8")
print("wrote", out, "-", len(out.read_text(encoding='utf-8').splitlines()), "lines")
