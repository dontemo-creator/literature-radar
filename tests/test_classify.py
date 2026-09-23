# -*- coding: utf-8 -*-
"""Ground-truth checks for the relevance gate and the classifier."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app import fields
from app.classify import classify

PACK = fields.get("solid-state-battery")

# (title, abstract, must_be_in_scope, expected_chemistry_subset, expected_themes_subset)
CASES = [
 ("Mechanistic study of mixed lithium halides solid-state electrolytes",
  "Li3YCl6 and Li3YBr3Cl3 halide solid electrolytes show high ionic conductivity; we use "
  "first-principles molecular dynamics to unravel the Li-ion migration mechanism.",
  True, {"halide", "halide.chloride", "halide.mixed"}, {"transport", "computation"}),

 ("Molecular Interfacial Regulators Enable Stable Sulfide Electrolyte/Li Metal Interfaces",
  "Sulfide solid electrolytes such as Li6PS5Cl argyrodite suffer from interfacial instability "
  "against lithium metal anodes, causing dendrite growth and low critical current density.",
  True, {"sulfide", "sulfide.argyrodite"}, {"interface", "limetal"}),

 ("Charged grain boundaries limit short-circuit endurance in garnet solid electrolytes",
  "Using operando X-ray tomography of Li7La3Zr2O12 (LLZO) pellets we show that grain boundary "
  "resistance and Li penetration determine failure.",
  True, {"oxide", "oxide.garnet"}, {"characterization", "limetal"}),

 ("Enabling high-voltage quasi-solid-state batteries via engineered polyether electrolyte interfaces",
  "An in-situ polymerized poly(ethylene oxide) based gel polymer electrolyte enables 4.6 V "
  "operation of NCM cathodes in quasi-solid-state lithium metal batteries.",
  True, {"polymer", "polymer.peo", "polymer.gel"}, {"interface", "cathode"}),

 ("Amorphous oxychloride LiNbOCl4 superionic conductors for all-solid-state batteries",
  "A new family of amorphous oxyhalide electrolytes LiNbOCl4 and LiTaOCl4 reaches 10 mS/cm and "
  "enables sheet-type all-solid-state cells with a dry process.",
  True, {"halide", "halide.oxyhalide"}, {"manufacturing"}),

 ("Ta-doped Li6.5La3Zr1.5Ta0.5O12 garnet with a Li1.3Al0.3Ti1.7(PO4)3 interlayer",
  "We combine a garnet-type oxide electrolyte with a NASICON LATP interlayer in a bilayer "
  "electrolyte architecture for anode-free solid-state cells under low stack pressure.",
  True, {"oxide", "oxide.garnet", "oxide.nasicon", "composite"}, {"anodefree", "chemomech"}),

 ("LiBH4–LiI complex hydride electrolytes for all-solid-state lithium batteries",
  "Closo-borate Li2B12H12 additives raise the ionic conductivity of LiBH4 based complex hydride "
  "solid electrolytes.",
  True, {"hydride", "hydride.borohydride", "hydride.closoborate"}, set()),

 ("Recent progress in composite polymer electrolytes with ceramic fillers: a review",
  "This review summarises ceramic-in-polymer and polymer-in-ceramic composite polymer electrolytes, "
  "covering PVDF, PEO and succinonitrile systems for solid-state lithium batteries.",
  True, {"polymer", "polymer.composite"}, {"review"}),

 ("All-solid-state sodium batteries enabled by Na3SbS4 and Na3Zr2Si2PO12",
  "Sodium solid electrolytes Na3SbS4 (sulfide) and NASICON Na3Zr2Si2PO12 are compared for "
  "all-solid-state sodium batteries.",
  True, {"sulfide", "sulfide.other", "oxide", "oxide.nasicon"}, {"beyondli"}),

 ("β-Li3PS4 glass-ceramic electrolytes from 75Li2S·25P2S5 with oxysulfide doping",
  "Melt-quenched Li2S-P2S5 glass converts to Li7P3S11 glass-ceramic; oxygen-doped sulfide "
  "(oxysulfide) shows improved air stability and less H2S evolution.",
  True, {"sulfide", "sulfide.glass", "sulfide.li3ps4", "sulfide.oxysulfide"}, {"safety"}),

 # ---- out of scope -----------------------------------------------------
 ("High-efficiency perovskite solar cells with a solid-state hole transport layer",
  "We report perovskite solar cells with 26% power conversion efficiency using a solid-state "
  "hole transport material; photovoltaic stability is improved.",
  False, set(), set()),
 ("Proton-conducting solid oxide fuel cells with a BaZrO3 electrolyte",
  "A solid oxide fuel cell (SOFC) with a proton-conducting oxide electrolyte reaches high power "
  "density at 600 C for hydrogen electrochemical conversion.",
  False, set(), set()),
 ("MXene-based supercapacitors for flexible energy storage",
  "Ti3C2 MXene films with a gel electrolyte deliver high areal capacitance in flexible "
  "supercapacitors.",
  False, set(), set()),
 ("Hydrogen-bonded organic frameworks with tunable pore expansion",
  "HOFs offer versatile porous architectures; we show predictable pore expansion via tecton "
  "extension for gas separation.",
  False, set(), set()),
 ("LiFePO4 cathodes with carbon coating for liquid-electrolyte lithium-ion batteries",
  "Carbon-coated LiFePO4 shows improved rate capability in conventional carbonate liquid "
  "electrolyte lithium-ion cells.",
  False, set(), set()),

 # ---- extra precision / recall probes ----------------------------------
 ("Sheet-type all-solid-state cells with a dry-processed Li6PS5Cl catholyte",
  "A solvent-free dry process produces sheet-type electrodes; stack pressure is reduced to 2 MPa "
  "and Ah-level pouch cells are demonstrated with a bipolar stack.",
  True, {"sulfide", "sulfide.argyrodite"}, {"manufacturing", "chemomech", "cellengineering"}),

 ("Machine-learned interatomic potentials for high-throughput screening of Li superionic conductors",
  "We train a neural network potential and screen 20,000 candidate inorganic solid electrolytes, "
  "computing activation energies and Li-ion migration barriers with ab initio accuracy.",
  True, set(), {"computation", "transport"}),

 ("Recycling of sulfide solid electrolytes from end-of-life all-solid-state batteries",
  "A closed-loop process recovers Li6PS5Cl argyrodite; life cycle assessment shows a 60% lower "
  "carbon footprint than fresh synthesis.",
  True, {"sulfide", "sulfide.argyrodite"}, {"recycling"}),

 ("Anode-free solid-state batteries with zero excess lithium on a Cu current collector",
  "Zero-excess-lithium cells using a Li6PS5Cl separator achieve 300 cycles under 5 MPa stack "
  "pressure; void formation at the current collector governs failure.",
  True, {"sulfide"}, {"anodefree", "limetal", "chemomech"}),

 ("Single-ion conducting polymer electrolytes with unity lithium transference number",
  "A lithiated ionomer backbone immobilises anions, giving a single-ion conducting solid polymer "
  "electrolyte for solid-state lithium metal batteries.",
  # note: a passing mention of "for solid-state lithium metal batteries" must NOT
  # tag the Li-metal-anode theme -- nearly every paper in the corpus says that,
  # and over-tagging would make the facet useless.
  True, {"polymer", "polymer.singleion"}, {"transport"}),

 # out of scope
 ("Solid-state NMR of membrane proteins in lipid bilayers",
  "Magic-angle spinning solid-state NMR reveals the structure of a membrane protein in native "
  "lipid bilayers; tissue samples were also measured.",
  False, set(), set()),
 ("Li-ion battery thermal runaway propagation in a module with liquid electrolyte",
  "We model thermal runaway propagation in a 12-cell module of commercial NMC/graphite lithium-ion "
  "cells with carbonate liquid electrolyte and quantify safety margins.",
  False, set(), set()),
 ("Zeolite-templated carbon for CO2 capture",
  "Microporous carbons show high CO2 uptake and selectivity over N2 at ambient pressure.",
  False, set(), set()),

]

def run():
    fails = []
    for title, abstract, want_scope, want_chem, want_theme in CASES:
        r = classify(PACK, title, abstract)
        chem = r["labels"].get("chemistry", [])
        themes = r["labels"].get("theme", [])
        tag = "OK  " if r["in_scope"] == want_scope else "SCOPE"
        missing_chem = want_chem - set(chem)
        missing_theme = want_theme - set(themes)
        if r["in_scope"] != want_scope or missing_chem or missing_theme:
            fails.append((title, r, missing_chem, missing_theme))
            tag = "FAIL"
        print(f"[{tag}] rel={r['relevance']:6.1f} scope={r['in_scope']!s:5s} "
              f"chem={chem} themes={themes[:4]}")
        if missing_chem:
            print(f"        missing chemistry: {sorted(missing_chem)}")
        if missing_theme:
            print(f"        missing themes   : {sorted(missing_theme)}")
        if r["in_scope"] != want_scope:
            print(f"        core={r['core']} ctx={r['context']} neg={r['negative']} "
                  f"neg_hits={r['hits']['negative']}")
        print(f"        {title[:78]}")
    print("\n%d/%d cases pass" % (len(CASES) - len(fails), len(CASES)))
    return len(fails)

if __name__ == "__main__":
    sys.exit(1 if run() else 0)
