# -*- coding: utf-8 -*-
"""Text normalisation shared by the classifier and the search index.

Chemistry text is typographically messy: ``Li₆PS₅Cl``, ``Li6PS5Cl``,
``Li2S–P2S5``, ``β-Li3PS4``, ``poly(ethylene oxide)``.  We derive two views:

``loose``  lowercase, subscripts folded to digits, Greek letters spelled out,
           every run of non-alphanumerics collapsed to a single space.
           -> ``li2s p2s5``, ``all solid state battery``, ``beta li3ps4``
``joined`` ``loose`` with all spaces removed, so multi-token formulas match.
           -> ``li2sp2s5``, ``betali3ps4``, ``li13al03ti17po43``
"""
from __future__ import annotations

import html
import re
import unicodedata

GREEK = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta", "ε": "epsilon",
    "ζ": "zeta", "η": "eta", "θ": "theta", "ι": "iota", "κ": "kappa",
    "λ": "lambda", "μ": "mu", "ν": "nu", "ξ": "xi", "ο": "omicron",
    "π": "pi", "ρ": "rho", "σ": "sigma", "ς": "sigma", "τ": "tau",
    "υ": "upsilon", "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
    "Α": "alpha", "Β": "beta", "Γ": "gamma", "Δ": "delta", "Θ": "theta",
    "Λ": "lambda", "Σ": "sigma", "Φ": "phi", "Ω": "omega",
}
DASHES = dict.fromkeys(map(ord, "‐‑‒–—―−⁃－"), "-")

_TAG_RE = re.compile(r"<[^>]{0,400}>")
# Tags whose boundary is real whitespace (sections must not run together).
_BLOCK_RE = re.compile(
    r"</?(?:jats:)?(?:p|title|sec|abstract|div|li|ul|ol|tr|td|th|table|h[1-6]|"
    r"blockquote|caption|list|list-item|break)\s*/?>|<br\s*/?>", re.IGNORECASE)
_MARKER_RUN_RE = re.compile(r"\x00+")
_PRETTY_INDENT = re.compile(r"[ \t]*\n[ \t]{2,}")
_SPACED_HYPHEN = re.compile(r"(\w) ([\u2010\u2011]) (\w)")
# Pretty-printed JATS puts a newline plus deep indentation around every
# sub/sup tag, e.g.  In\n    <sub>2</sub>\n    O\n    <sub>3</sub>\n    conductive
# Naively keeping that whitespace gives "In 2 O 3 conductive"; naively dropping
# it gives "In2O3conductive".  The distinction is what follows the tag: a
# formula continuation (a digit, or an element symbol such as O, Cl, Zr) closes
# up, while an ordinary word keeps its space.
_ELEMENTISH = r"(?=[0-9]|[A-Z][a-z]?(?![a-z]))"
_SUBSUP_TAG = r"</?(?:jats:)?(?:sub|sup|inf)\s*/?>"
_INDENT_BEFORE_SUBSUP = re.compile(
    r"(?<=[A-Za-z0-9\)\]])[ \t]*\n[ \t]{2,}(?=" + _SUBSUP_TAG + ")")
_INDENT_AFTER_SUBSUP = re.compile(
    r"(" + _SUBSUP_TAG + r")[ \t]*\n[ \t]{2,}" + _ELEMENTISH)
_WS_RE = re.compile(r"\s+")
_NONALNUM_RE = re.compile(r"[^a-z0-9]+")
_JATS_TITLE_RE = re.compile(
    r"^\s*(?:<[^>]+>\s*)*(?:abstract|summary|graphical abstract)\s*(?:</[^>]+>)?\s*[:.]?\s*",
    re.IGNORECASE)


def strip_markup(text: str) -> str:
    """Remove JATS/HTML markup from a title or abstract, HTML-style.

    Three things have to be right at once:

    * inline tags are zero-width -- ``high-voltage <i>quasi</i>-solid-state``
      must not become ``quasi -solid-state``;
    * block boundaries become real paragraph breaks, so sections do not run
      together;
    * pretty-printed JATS (a newline plus deep indentation around every
      ``<sub>``) must neither shatter formulas into ``In 2 O 3`` nor glue the
      next word on as ``In2O3conductive``.
    """
    if not text:
        return ""
    t = str(text)
    # 1. Formula-aware handling of indentation around sub/sup tags.
    t = _INDENT_BEFORE_SUBSUP.sub("", t)
    t = _INDENT_AFTER_SUBSUP.sub(r"\1", t)
    # 2. Any remaining newline-plus-indentation is XML formatting: one space.
    t = _PRETTY_INDENT.sub(" ", t)
    # 3. Block-level boundaries -> paragraph break.
    t = _BLOCK_RE.sub("\n", t)
    # 4. Every other tag is zero-width.
    t = _TAG_RE.sub("\x00", t)
    t = _MARKER_RUN_RE.sub("\x00", t)
    t = t.replace("\x00", "")
    t = html.unescape(t)
    t = t.replace("\u00a0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" ?\n ?", "\n", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    # Some deposits carry a spaced typographic hyphen: "Fast ‐ Charging
    # Composite Solid ‐ State".  U+2010/U+2011 are word-joining hyphens and are
    # never legitimate spaced separators, so close them up.  ASCII "-" and the
    # en/em dashes are left alone, since " - " and " – " really do separate.
    t = _SPACED_HYPHEN.sub(r"\1\2\3", t)
    t = _JATS_TITLE_RE.sub("", t.strip())
    return t.strip()


def clean_title(text: str) -> str:
    return _WS_RE.sub(" ", strip_markup(text)).strip()


def _fold(text: str) -> str:
    """Lowercase + fold subscripts/superscripts + spell out Greek letters."""
    t = (text or "").translate(DASHES)
    t = "".join(GREEK.get(ch, ch) for ch in t)
    # NFKD turns ₆ -> 6, ² -> 2, ﬁ -> fi, etc.
    t = unicodedata.normalize("NFKD", t)
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    return t.lower()


def views(*parts: str) -> tuple[str, str]:
    """Return the ``(loose, joined)`` views of the concatenated parts."""
    raw = " . ".join(p for p in parts if p)
    loose = _NONALNUM_RE.sub(" ", _fold(raw)).strip()
    loose = _WS_RE.sub(" ", loose)
    return loose, loose.replace(" ", "")


def loose(text: str) -> str:
    return views(text)[0]
