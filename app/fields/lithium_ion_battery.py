# -*- coding: utf-8 -*-
"""Field pack: lithium-ion batteries (liquid electrolyte).

Complements the solid-state pack rather than excluding it -- solid-state work
is part of lithium battery research, so overlap is expected.  Sibling
chemistries that would only be noise here (sodium-, zinc-, magnesium-ion) carry
a mild negative weight, enough to drop a paper that is *only* about them while
still keeping a Li/Na comparison study.
"""
from __future__ import annotations

from .base import F, N, Pack

CATHODE = [
    N("cathode.layered", "层状氧化物 (NCM/NCA)", "Layered oxides (NCM/NCA)", [
        ("sqw:ncm", 8), ("sqw:nmc", 8), ("sqw:nca", 8), ("layered oxide cathode", 10),
        ("sqw:lini08co01mn01o2", 10), ("nickel-rich", 9), ("ni-rich", 9),
        ("high-nickel", 9), ("sqw:licoo2", 8), ("sqw:linio2", 8),
        ("single-crystal cathode", 9), ("polycrystalline cathode", 8),
        ("cobalt-free cathode", 9), ("cation mixing", 7), ("sqw:nmc811", 10),
        ("sqw:nmc622", 10), ("sqw:nmc532", 10), ("lithium nickel manganese cobalt", 10)]),
    N("cathode.lirich", "富锂锰基", "Li-rich Mn-based", [
        ("li-rich", 10), ("lithium-rich", 10), ("sqw:lrmo", 10),
        ("anionic redox", 10), ("oxygen redox", 9), ("li2mno3", 9),
        ("voltage decay", 8), ("li-rich layered oxide", 11)]),
    N("cathode.spinel", "尖晶石 (LMO/LNMO)", "Spinel (LMO/LNMO)", [
        ("spinel", 9), ("sqw:limn2o4", 10), ("sqw:lnmo", 10),
        ("sqw:lini05mn15o4", 11), ("high-voltage spinel", 11),
        ("disordered rocksalt", 8), ("mn dissolution", 8)]),
    N("cathode.phosphate", "磷酸盐 (LFP/LMFP)", "Phosphates (LFP/LMFP)", [
        ("sqw:lifepo4", 10), ("sqw:lfp", 8), ("sqw:lmfp", 10), ("olivine", 10),
        ("sqw:limnfepo4", 10), ("lithium iron phosphate", 11),
        ("sqw:limnpo4", 10), ("phosphate cathode", 9)]),
    N("cathode.conversion", "转换型与硫正极", "Conversion & sulfur cathodes", [
        ("sulfur cathode", 10), ("lithium-sulfur", 10), ("polysulfide", 9),
        ("conversion cathode", 10), ("sqw:fes2", 8), ("fluoride conversion", 9),
        ("sqw:li2s", 7), ("selenium cathode", 9)]),
    N("cathode.organic", "有机与聚合物正极", "Organic cathodes", [
        ("organic cathode", 11), ("quinone", 9), ("radical polymer cathode", 11),
        ("conjugated polymer cathode", 11), ("redox-active organic", 10)]),
    N("cathode.other", "其他正极与包覆改性", "Other cathodes & coatings", [
        ("cathode coating", 9), ("surface modification of cathode", 10),
        ("cathode active material", 7), ("doping strategy", 6),
        ("core-shell cathode", 10), ("concentration gradient", 9)]),
]

ANODE = [
    N("anode.graphite", "石墨与碳负极", "Graphite & carbon anodes", [
        ("graphite anode", 11), ("graphite electrode", 9), ("sqw:hard carbon", 6),
        ("soft carbon", 8), ("intercalation of lithium into graphite", 11),
        ("li plating on graphite", 11), ("sqw:mcmb", 8)]),
    N("anode.silicon", "硅基负极", "Silicon anodes", [
        ("silicon anode", 11), ("si anode", 10), ("sqw:siox", 9), ("sqw:sio", 6),
        ("si-c composite", 10), ("silicon-carbon", 10), ("micro-silicon", 10),
        ("volume expansion of silicon", 11), ("nano-silicon", 10),
        ("silicon-graphite", 11)]),
    N("anode.limetal", "锂金属负极", "Li-metal anodes", [
        ("lithium metal anode", 11), ("li metal anode", 11), ("dendrite", 9),
        ("lithium plating", 9), ("dead lithium", 10), ("coulombic efficiency of li", 10),
        ("host for lithium", 9), ("anode-free", 9), ("zero excess lithium", 11)]),
    N("anode.lto", "钛基负极 (LTO/TNO)", "Titanates (LTO/TNO)", [
        ("sqw:lto", 9), ("sqw:li4ti5o12", 11), ("lithium titanate", 11),
        ("sqw:tinb2o7", 10), ("niobium tungsten oxide", 10), ("titanate anode", 10)]),
    N("anode.alloy", "合金与转换型负极", "Alloy & conversion anodes", [
        ("tin anode", 10), ("antimony anode", 10), ("phosphorus anode", 10),
        ("alloy anode", 10), ("conversion anode", 10), ("sqw:sno2", 8),
        ("bismuth anode", 10), ("germanium anode", 10)]),
]

ELECTROLYTE = [
    N("elyte.carbonate", "碳酸酯基电解液", "Carbonate electrolytes", [
        ("carbonate electrolyte", 10), ("sqw:ec dmc", 8), ("sqw:lipf6", 9),
        ("ethylene carbonate", 9), ("sqw:emc", 6), ("sqw:dec", 5),
        ("conventional electrolyte", 7), ("baseline electrolyte", 8)]),
    N("elyte.additive", "成膜添加剂", "Film-forming additives", [
        ("electrolyte additive", 11), ("sqw:fec", 7), ("sqw:vc", 4),
        ("film-forming additive", 11), ("sacrificial additive", 10),
        ("sqw:lidfob", 9), ("sqw:libob", 9), ("sqw:lifsi", 8), ("sqw:litfsi", 8),
        ("additive engineering", 10)]),
    N("elyte.hce", "高浓与弱溶剂化电解液", "High-concentration & weakly solvating", [
        ("high-concentration electrolyte", 11), ("localized high-concentration", 12),
        ("sqw:lhce", 10), ("weakly solvating", 11), ("solvation structure", 9),
        ("contact ion pair", 10), ("anion-derived", 9), ("salt-concentrated", 10),
        ("diluent", 9), ("fluorinated ether", 9)]),
    N("elyte.ionicliquid", "离子液体与阻燃电解液", "Ionic liquids & flame-retardant", [
        ("ionic liquid electrolyte", 11), ("nonflammable electrolyte", 11),
        ("flame-retardant electrolyte", 11), ("phosphate electrolyte solvent", 10),
        ("sqw:tep", 6), ("sqw:tmp", 6)]),
    N("elyte.aqueous", "水系与准固态电解液", "Aqueous & quasi-solid", [
        ("aqueous electrolyte", 10), ("water-in-salt", 12), ("hydrogel electrolyte", 10),
        ("gel polymer electrolyte", 9), ("quasi-solid", 8), ("in-situ polymeriz", 9)]),
    N("elyte.wide", "宽温域电解液", "Wide-temperature electrolytes", [
        ("low-temperature electrolyte", 11), ("wide-temperature", 10),
        ("high-temperature electrolyte", 10), ("sub-zero", 9), ("cryogenic", 9),
        ("desolvation energy", 10)]),
]

THEME = [
    N("theme.interphase", "界面相 (SEI/CEI)", "Interphases (SEI/CEI)", [
        ("solid electrolyte interphase", 10), ("sqw:sei", 7), ("sqw:cei", 7),
        ("cathode electrolyte interphase", 11), ("interphase chemistry", 10),
        ("passivation layer", 8), ("interfacial", 5), ("lif-rich", 10),
        ("inorganic-rich interphase", 11)]),
    N("theme.fastcharge", "快充与倍率", "Fast charging & rate", [
        ("fast charging", 11), ("fast-charge", 11), ("extreme fast charging", 12),
        ("rate capability", 8), ("sqw:xfc", 9), ("sqw:6c", 5), ("high current density", 7),
        ("li plating during fast charge", 12)]),
    N("theme.lowtemp", "低温与宽温性能", "Low-temperature performance", [
        ("low temperature performance", 11), ("sub-zero temperature", 11),
        ("cold climate", 10), ("charge transfer resistance at low", 11)]),
    N("theme.degradation", "老化、衰减与失效", "Ageing & degradation", [
        ("capacity fade", 10), ("degradation mechanism", 10), ("calendar ag", 11),
        ("cycle ag", 10), ("lithium inventory loss", 11), ("impedance growth", 10),
        ("post-mortem", 10), ("failure analysis", 9), ("crack", 6),
        ("transition metal dissolution", 10)]),
    N("theme.safety", "安全与热失控", "Safety & thermal runaway", [
        ("thermal runaway", 12), ("safety", 7), ("gas evolution", 9),
        ("venting", 9), ("calorimetr", 9), ("internal short circuit", 11),
        ("propagation", 7), ("flammab", 9), ("overcharge", 9)]),
    N("theme.manufacturing", "电极工艺与制造", "Electrode processing & manufacturing", [
        ("dry electrode", 12), ("slurry", 8), ("calender", 10), ("tape cast", 9),
        ("thick electrode", 11), ("binder", 7), ("aqueous processing", 10),
        ("roll-to-roll", 11), ("electrode architecture", 10), ("areal loading", 9),
        ("pouch cell", 8), ("cost analysis", 9)]),
    N("theme.characterization", "先进表征", "Advanced characterisation", [
        ("operando", 10), ("in situ characteriz", 10), ("cryo-em", 11),
        ("solid-state nmr", 10), ("synchrotron", 10), ("x-ray tomograph", 11),
        ("neutron diffraction", 10), ("tof-sims", 11), ("sqw:xps", 6),
        ("titration gas chromatography", 11)]),
    N("theme.modelling", "建模、计算与机器学习", "Modelling, DFT & ML", [
        ("machine learning", 10), ("density functional theory", 10), ("sqw:dft", 6),
        ("molecular dynamics", 10), ("first-principles", 10),
        ("physics-based model", 11), ("sqw:p2d", 8), ("doyle-fuller-newman", 12),
        ("digital twin", 10), ("state of health estimation", 11),
        ("high-throughput screening", 11)]),
    N("theme.recycling", "回收与可持续", "Recycling & sustainability", [
        ("recycl", 11), ("direct recycling", 12), ("hydrometallurg", 11),
        ("pyrometallurg", 11), ("life cycle assessment", 11), ("second life", 10),
        ("critical raw material", 10), ("upcycl", 11), ("black mass", 11)]),
    N("theme.pack", "电芯与系统工程", "Cell & pack engineering", [
        ("battery management", 11), ("state of charge", 9), ("module", 6),
        ("pack design", 11), ("thermal management", 10), ("cell-to-pack", 12),
        ("energy density target", 10), ("ah-level", 10)]),
    N("theme.review", "综述与展望", "Reviews & perspectives", [
        ("review", 5), ("this review", 10), ("critical review", 11),
        ("recent progress", 10), ("recent advance", 10), ("roadmap", 10),
        ("perspective", 5), ("challenges and opportunities", 10)]),
]

CORE = [
    ("lithium-ion batter", 10), ("li-ion batter", 10), ("sqw:lib", 7), ("sqw:libs", 7),
    ("lithium batter", 8), ("lithium metal batter", 9), ("graphite anode", 9),
    ("silicon anode", 9), ("sqw:ncm", 7), ("sqw:nmc", 7), ("sqw:lifepo4", 9),
    ("sqw:licoo2", 8), ("li-rich", 8), ("high-nickel", 8), ("lithium plating", 8),
    ("li plating", 8), ("sqw:lipf6", 8), ("sqw:lifsi", 7),
]
CONTEXT = [
    ("batter", 3), ("lithium", 2), ("cathode", 2), ("anode", 2), ("electrolyte", 2),
    ("electrochemical", 1), ("cycling", 2), ("capacity", 2), ("mah", 2), ("voltage", 1),
    ("coulombic", 2), ("energy density", 2), ("cell", 1), ("rechargeable batter", 3),
    ("cathode material", 3), ("anode material", 3), ("electrolyte additive", 3),
    ("electrode/electrolyte interface", 3), ("solid electrolyte interphase", 3),
    ("cathode electrolyte interphase", 3), ("carbonate electrolyte", 3),
    ("high-concentration electrolyte", 3), ("coulombic efficiency", 3),
    ("capacity retention", 3), ("full cell", 3), ("pouch cell", 3),
    ("battery management", 3), ("thermal runaway", 3), ("battery recycling", 3),
    ("state of health", 3), ("electrode slurry", 3), ("dry electrode", 3),
]
NEGATIVE = [
    ("solid oxide fuel cell", 14), ("sqw:sofc", 12), ("fuel cell", 10),
    ("proton exchange membrane", 13), ("sqw:pemfc", 13), ("nafion", 11),
    ("polymer electrolyte membrane", 12), ("gas diffusion layer", 11),
    ("water splitting", 10), ("oxygen evolution reaction", 10),
    ("hydrogen evolution reaction", 10), ("electrocataly", 8), ("photocatal", 11),
    ("solar cell", 11), ("perovskite solar", 14), ("photovoltaic", 10),
    ("supercapacitor", 8), ("thermoelectric", 10), ("triboelectric", 12), ("biosensor", 11),
    ("drug delivery", 12), ("tissue", 10), ("antibacterial", 11), ("wastewater", 11),
    ("desalination", 11), ("memristor", 5), ("neuromorphic", 5), ("flow batter", 8),
    ("lead-acid", 10), ("nickel-metal hydride", 9), ("sodium-ion batter", 6),
    ("potassium-ion batter", 6), ("zinc-ion batter", 7), ("magnesium batter", 6),
    ("aqueous zinc", 8), ("aluminium-ion batter", 6), ("calcium-ion batter", 6),
]

JOURNALS = [
    "Nature", "Science", "Nature Energy", "Nature Materials", "Nature Nanotechnology",
    "Nature Reviews Materials", "Nature Chemistry", "Nature Sustainability",
    "Nature Communications", "Science Advances", "Chemical Reviews",
    "Chemical Society Reviews", "Joule", "Chem", "Matter",
    "Energy & Environmental Science", "J. Am. Chem. Soc. (JACS)",
    "Angewandte Chemie Int. Ed.", "Advanced Materials", "Advanced Energy Materials",
    "ACS Energy Letters", "PNAS", "Electrochemical Energy Reviews",
    "Advanced Functional Materials", "Energy Storage Materials", "Materials Today",
    "Nano Energy", "ACS Nano", "Nano Letters", "Small", "Advanced Science",
    "Journal of Materials Chemistry A", "Chemistry of Materials",
    "Chemical Engineering Journal", "Journal of Energy Chemistry", "InfoMat",
    "eScience", "Carbon Energy", "Aggregate", "Chemical Science",
    "ACS Materials Letters", "Materials Horizons", "Science Bulletin",
    "Nano-Micro Letters", "Small Methods", "Cell Reports Physical Science",
    "ACS Applied Materials & Interfaces", "Journal of Power Sources",
    "Electrochimica Acta", "J. Electrochem. Soc.", "ACS Applied Energy Materials",
    "Batteries & Supercaps", "Journal of Materials Science & Technology",
    "Nano Research", "Green Energy & Environment", "Chinese Chemical Letters",
    "Energy Material Advances", "Battery Energy", "Journal of Energy Storage",
    "Chemical Communications", "J. Phys. Chem. Lett.", "Applied Energy",
    "Energy Conversion and Management", "Electrochemistry Communications",
]

PACK = Pack(
    id="lithium-ion-battery",
    zh="锂离子电池",
    en="Lithium-Ion Batteries",
    tagline="正极、负极、电解液配方、快充与失效分析",
    icon="🔌",
    facets=[
        F("cathode", "正极材料", "Cathode materials", CATHODE,
          top_min=8.0, sub_min=9.0, unspecified="cathode.other",
          note_zh="按正极体系归类；未点明体系的落在「其他」"),
        F("anode", "负极材料", "Anode materials", ANODE, top_min=9.0, sub_min=9.0),
        F("electrolyte", "电解液", "Electrolytes", ELECTROLYTE, top_min=9.0, sub_min=9.0),
        F("theme", "研究主题", "Research themes", THEME, top_min=9.0, sub_min=9.0),
    ],
    core=CORE, context=CONTEXT, negative=NEGATIVE, journals=JOURNALS,
    search_hints=['"fast charging"', "NMC811", '"localized high-concentration"', "cryo-EM"],
    core_min=8.0, relevance_min=9.0,
)
