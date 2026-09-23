# -*- coding: utf-8 -*-
"""Text normalisation: the layer every rule depends on."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app.textnorm import views, strip_markup, clean_title, loose

CASES_VIEWS = [
    ("Li₆PS₅Cl", "li6ps5cl", "li6ps5cl"),
    ("Li6PS5Cl", "li6ps5cl", "li6ps5cl"),
    ("Li2S–P2S5", "li2s p2s5", "li2sp2s5"),
    ("Li2S-P2S5", "li2s p2s5", "li2sp2s5"),
    ("β-Li3PS4", "beta li3ps4", "betali3ps4"),
    ("all-solid-state", "all solid state", "allsolidstate"),
    ("Li1.3Al0.3Ti1.7(PO4)3", "li1 3al0 3ti1 7 po4 3", "li13al03ti17po43"),
    ("Li6.5La3Zr1.5Ta0.5O12", "li6 5la3zr1 5ta0 5o12", "li65la3zr15ta05o12"),
    ("poly(ethylene oxide)", "poly ethylene oxide", "polyethyleneoxide"),
    ("Li₉.₅₄Si₁.₇₄P₁.₄₄S₁₁.₇Cl₀.₃", "li9 54si1 74p1 44s11 7cl0 3", "li954si174p144s117cl03"),
]

# Publishers pretty-print JATS: a newline plus deep indentation wraps every
# <sub>.  These cases pin down both failure modes we hit on real data --
# shattered formulas ("In 2 O 3") and glued words ("In2O3conductive").
IND = "\n                    "

CASES_MARKUP = [
    ("<jats:title>Abstract</jats:title><jats:p>Hello</jats:p>", "Hello"),
    ("Abstract: real content here", "real content here"),
    # inline tags are zero-width, so hyphenated words survive intact
    ("high-voltage <i>quasi</i>-solid-state", "high-voltage quasi-solid-state"),
    ("word1</jats:italic><jats:italic>word2", "word1word2"),
    # block boundaries become a real paragraph break
    ("<jats:p>First.</jats:p>\n   <jats:p>Second.</jats:p>", "First.\n\nSecond."),
    ("<jats:sec><jats:title>Methods</jats:title><jats:p>We measured</jats:p></jats:sec>",
     "Methods\n\nWe measured"),
    # sub/sup close up
    ("Li<sub>6</sub>PS<sub>5</sub>Cl", "Li6PS5Cl"),
    ("E<sup>2</sup> value", "E2 value"),
    ("<jats:p>Na<jats:sub>3</jats:sub>Zr<jats:sub>2</jats:sub>Si<jats:sub>2</jats:sub>"
     "PO<jats:sub>12</jats:sub></jats:p>", "Na3Zr2Si2PO12"),
    # pretty-printed formulas stay whole ...
    ("Nanoscale In" + IND + "<sub>2</sub>" + IND + "O" + IND + "<sub>3</sub>" + IND + "Induced",
     "Nanoscale In2O3 Induced"),
    ("Li" + IND + "<sub>6</sub>" + IND + "PS" + IND + "<sub>5</sub>" + IND + "Cl argyrodite",
     "Li6PS5Cl argyrodite"),
    ("Na" + IND + "<sub>3</sub>" + IND + "Zr" + IND + "<sub>2</sub>" + IND + "Si" + IND +
     "<sub>2</sub>" + IND + "PO" + IND + "<sub>12</sub>", "Na3Zr2Si2PO12"),
    ("a Li" + IND + "<jats:sub>3</jats:sub>" + IND + "P fast-ion conductor",
     "a Li3P fast-ion conductor"),
    ("80Li" + IND + "<sub>2</sub>" + IND + "S–20P" + IND + "<sub>2</sub>" + IND + "S" + IND +
     "<sub>5</sub>" + IND + "solid electrolyte", "80Li2S–20P2S5 solid electrolyte"),
    # ... and the following *word* keeps its space
    ("nanoscale In" + IND + "<jats:sub>2</jats:sub>" + IND + "O" + IND + "<jats:sub>3</jats:sub>"
     + IND + "conductive agent", "nanoscale In2O3 conductive agent"),
    ("value X" + IND + "<sub>2</sub>" + IND + "The results follow",
     "value X2 The results follow"),
    ("<p>A &amp; B &lt;tag&gt;</p>", "A & B <tag>"),
    # a spaced U+2010 hyphen is a deposit artefact and closes up ...
    ("Fast \u2010 Charging Composite Solid \u2010 State Batteries",
     "Fast\u2010Charging Composite Solid\u2010State Batteries"),
    ("Li \u2010 ion transport", "Li\u2010ion transport"),
    # ... while real separators are left alone
    ("Structure \u2013 Property relationships", "Structure \u2013 Property relationships"),
    ("Type I \u2014 Type II", "Type I \u2014 Type II"),
    ("Range 5 - 10 mS", "Range 5 - 10 mS"),
    ("", ""),
    (None, ""),
]

def run():
    fails = []
    for text, want_loose, want_joined in CASES_VIEWS:
        got_l, got_j = views(text)
        ok = got_l == want_loose and got_j == want_joined
        if not ok:
            fails.append(("views", text, (got_l, got_j), (want_loose, want_joined)))
        print(f"  [{'OK ' if ok else 'FAIL'}] views {text!r:34s} -> {got_l!r}")
    for raw, want in CASES_MARKUP:
        got = strip_markup(raw)
        ok = got == want
        if not ok:
            fails.append(("markup", raw, got, want))
        print(f"  [{'OK ' if ok else 'FAIL'}] markup {str(raw)[:44]!r:46s} -> {got!r}")

    # short formulas must not leak across word boundaries in the joined view
    j = views("LiFePO4 vs LiF and LiI in a library")[1]
    checks = [
        ("joined text concatenates", "lif" in j, True),
        ("clean_title collapses whitespace", clean_title("A  <i>b</i>\n c"), "A b c"),
        ("loose() helper agrees", loose("Solid-State"), "solid state"),
    ]
    for name, got, want in checks:
        ok = got == want
        if not ok:
            fails.append(("check", name, got, want))
        print(f"  [{'OK ' if ok else 'FAIL'}] {name}: {got!r}")

    print("\n%d/%d checks pass" % (len(CASES_VIEWS) + len(CASES_MARKUP) + len(checks) - len(fails),
                                  len(CASES_VIEWS) + len(CASES_MARKUP) + len(checks)))
    for f in fails:
        print("   ", f)
    return len(fails)


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
