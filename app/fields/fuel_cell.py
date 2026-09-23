# -*- coding: utf-8 -*-
"""Field pack: fuel cells.

Deliberately narrower than the electrocatalysis pack: a catalyst paper counts
here only when it is framed as fuel-cell work (MEA, durability protocol, stack,
power density), which is what separates the two fields in practice.
"""
from __future__ import annotations

from .base import F, N, Pack

TYPE = [
    N("type.pemfc", "质子交换膜 (PEMFC)", "PEMFC", [
        ("proton exchange membrane fuel cell", 14), ("sqw:pemfc", 13),
        ("polymer electrolyte membrane fuel cell", 14), ("sqw:pefc", 12),
        ("sqw:nafion", 10), ("low-temperature fuel cell", 11),
        ("high-temperature pemfc", 13), ("sqw:ht-pemfc", 13)]),
    N("type.aemfc", "阴离子交换膜 (AEMFC)", "AEMFC", [
        ("anion exchange membrane fuel cell", 14), ("sqw:aemfc", 13),
        ("alkaline fuel cell", 13), ("sqw:afc", 9), ("hydroxide conducting", 13),
        ("anion exchange membrane", 11)]),
    N("type.sofc", "固体氧化物 (SOFC)", "SOFC", [
        ("solid oxide fuel cell", 14), ("sqw:sofc", 13), ("sqw:ysz", 12),
        ("sqw:gdc", 11), ("protonic ceramic fuel cell", 14), ("sqw:pcfc", 13),
        ("intermediate temperature sofc", 14), ("anode-supported cell", 12),
        ("sqw:lscf", 12), ("triple conducting", 12)]),
    N("type.dmfc", "直接液体燃料", "Direct liquid-fuel cells", [
        ("direct methanol fuel cell", 14), ("sqw:dmfc", 13),
        ("direct ethanol fuel cell", 14), ("direct formic acid", 13),
        ("direct ammonia fuel cell", 14), ("direct borohydride", 13),
        ("methanol crossover", 13)]),
    N("type.other", "其他类型与混合体系", "Other & hybrid types", [
        ("molten carbonate fuel cell", 14), ("phosphoric acid fuel cell", 14),
        ("microbial fuel cell", 13), ("enzymatic fuel cell", 13),
        ("reversible fuel cell", 13), ("unitized regenerative", 13)]),
]

COMPONENT = [
    N("comp.catalyst", "催化剂与载体", "Catalysts & supports", [
        ("cathode catalyst", 11), ("pt/c", 11), ("platinum loading", 13),
        ("low-pt", 13), ("pt-free", 13), ("sqw:ptco", 12), ("sqw:ptni", 12),
        ("catalyst support", 11), ("carbon corrosion", 13),
        ("single-atom catalyst", 10), ("sqw:fenc", 11), ("oxygen reduction", 9),
        ("mass activity", 12)]),
    N("comp.membrane", "膜与离聚物", "Membranes & ionomers", [
        ("proton exchange membrane", 12), ("anion exchange membrane", 12),
        ("ionomer", 11), ("sqw:nafion", 10), ("membrane conductivity", 12),
        ("hydrocarbon membrane", 13), ("reinforced membrane", 13),
        ("chemical degradation of membrane", 13), ("water uptake", 10),
        ("radical scavenger", 13)]),
    N("comp.mea", "膜电极组件 (MEA)", "Membrane electrode assembly", [
        ("membrane electrode assembly", 13), ("sqw:mea", 10),
        ("catalyst layer", 11), ("catalyst coated membrane", 13),
        ("ionomer distribution", 13), ("electrode thickness", 11),
        ("triple phase boundary", 13)]),
    N("comp.gdl", "气体扩散层与流场", "GDL & flow fields", [
        ("gas diffusion layer", 13), ("sqw:gdl", 11), ("microporous layer", 13),
        ("flow field", 12), ("serpentine channel", 13), ("interdigitated", 12),
        ("porous transport layer", 13), ("hydrophobic treatment", 11)]),
    N("comp.bipolar", "双极板与密封", "Bipolar plates & sealing", [
        ("bipolar plate", 13), ("metallic bipolar", 13), ("coating for bipolar", 13),
        ("interfacial contact resistance", 13), ("gasket", 11), ("stack sealing", 12),
        ("graphite plate", 11)]),
]

THEME = [
    N("theme.durability", "耐久性与衰减", "Durability & degradation", [
        ("durability", 11), ("degradation mechanism", 11), ("accelerated stress test", 13),
        ("voltage cycling", 12), ("start-stop", 13), ("platinum dissolution", 13),
        ("membrane thinning", 13), ("5000 h", 12), ("performance loss", 11),
        ("reversal tolerance", 13)]),
    N("theme.water", "水管理与热管理", "Water & thermal management", [
        ("water management", 13), ("flooding", 11), ("membrane dehydration", 13),
        ("thermal management", 12), ("humidification", 12), ("relative humidity", 11),
        ("liquid water transport", 13), ("two-phase flow", 12)]),
    N("theme.operation", "工况、冷启动与杂质", "Operation, cold start & impurities", [
        ("cold start", 13), ("sub-zero start", 13), ("freeze", 10),
        ("impurity tolerance", 13), ("co poisoning", 13), ("sulfur poisoning", 13),
        ("hydrogen purity", 13), ("dynamic load", 12), ("idling", 11)]),
    N("theme.modelling", "建模与仿真", "Modelling & simulation", [
        ("computational fluid dynamics", 13), ("sqw:cfd", 11),
        ("multiphysics model", 13), ("pore-network model", 13),
        ("performance model", 11), ("machine learning", 10),
        ("digital twin", 12), ("parameter identification", 12)]),
    N("theme.characterization", "表征与诊断", "Characterisation & diagnostics", [
        ("operando", 11), ("neutron imaging", 13), ("x-ray tomograph", 12),
        ("electrochemical impedance", 11), ("distribution of relaxation times", 13),
        ("sqw:drt", 10), ("segmented cell", 13), ("current distribution", 12)]),
    N("theme.system", "系统集成与成本", "System integration & cost", [
        ("fuel cell stack", 12), ("fuel cell vehicle", 13), ("balance of plant", 13),
        ("techno-economic", 12), ("cost target", 12), ("system efficiency", 11),
        ("hybrid system", 10), ("combined heat and power", 13),
        ("heavy-duty", 12), ("aviation", 11)]),
    N("theme.review", "综述与展望", "Reviews & perspectives", [
        ("review", 5), ("this review", 10), ("recent progress", 10),
        ("recent advance", 10), ("roadmap", 10), ("perspective", 5)]),
]

CORE = [
    ("fuel cell", 12), ("fuel cells", 12), ("sqw:pemfc", 13), ("sqw:sofc", 13),
    ("sqw:aemfc", 13), ("sqw:dmfc", 13), ("sqw:pcfc", 13), ("proton exchange membrane", 11),
    ("anion exchange membrane", 10), ("solid oxide fuel cell", 14),
    ("gas diffusion layer", 11), ("bipolar plate", 12), ("fuel cell stack", 13),
    ("fuel cell vehicle", 13), ("hydrogen fuel cell", 13),
]
CONTEXT = [
    ("fuel", 2), ("cell", 1), ("membrane", 2), ("catalyst", 2), ("electrode", 2),
    ("hydrogen", 2), ("power", 2), ("current density", 2), ("efficiency", 2),
    ("durability", 2), ("electrochemical", 1), ("stack", 2), ("sqw:mea", 3),
    ("membrane electrode assembly", 3), ("catalyst layer", 3), ("power density", 3),
    ("polarization curve", 3), ("oxygen reduction reaction", 3), ("platinum loading", 3),
    ("ionomer", 3), ("triple phase boundary", 3), ("cathode catalyst", 3),
    ("start-stop cycling", 3), ("cold start", 3),
]
NEGATIVE = [
    ("lithium-ion batter", 12), ("sodium-ion batter", 12), ("all-solid-state batter", 12),
    ("solid electrolyte interphase", 11), ("supercapacitor", 11), ("solar cell", 12),
    ("perovskite solar", 13), ("photovoltaic", 11), ("photocatal", 12),
    ("microbial community", 12), ("wastewater treatment", 11), ("drug delivery", 12),
    ("biosensor", 11), ("tissue", 11), ("thermoelectric", 11), ("gas separation", 9),
    ("desalination", 11), ("internal combustion", 10), ("gas turbine", 10),
    ("water electrolysis", 12), ("water electrolyser", 12), ("electrolyzer", 8),
    ("electrolyser", 8), ("oxygen evolution reaction", 8), ("co2 reduction", 8),
]

JOURNALS = [
    "Nature", "Science", "Nature Energy", "Nature Catalysis", "Nature Materials",
    "Nature Communications", "Nature Sustainability", "Science Advances",
    "Chemical Reviews", "Chemical Society Reviews", "Joule", "Chem", "Matter",
    "Energy & Environmental Science", "J. Am. Chem. Soc. (JACS)",
    "Angewandte Chemie Int. Ed.", "Advanced Materials", "Advanced Energy Materials",
    "ACS Energy Letters", "Electrochemical Energy Reviews",
    "Advanced Functional Materials", "Energy Storage Materials", "Materials Today",
    "Nano Energy", "ACS Nano", "Small", "Advanced Science",
    "Journal of Materials Chemistry A", "Chemistry of Materials",
    "Chemical Engineering Journal", "Journal of Energy Chemistry", "InfoMat",
    "eScience", "Chemical Science", "ACS Materials Letters", "Materials Horizons",
    "Science Bulletin", "Nano-Micro Letters", "Small Methods",
    "ACS Catalysis", "Applied Catalysis B Environment and Energy", "ChemSusChem",
    "ACS Applied Materials & Interfaces", "Journal of Power Sources",
    "Electrochimica Acta", "J. Electrochem. Soc.", "ACS Applied Energy Materials",
    "Electrochemistry Communications", "International Journal of Hydrogen Energy",
    "Journal of Membrane Science", "Applied Energy",
    "Energy Conversion and Management", "Renewable and Sustainable Energy Reviews",
    "Fuel", "Chemical Engineering Science", "Green Energy & Environment",
    "ACS Sustainable Chemistry & Engineering", "Chemical Communications",
]

PACK = Pack(
    id="fuel-cell",
    zh="燃料电池",
    en="Fuel Cells",
    tagline="PEMFC/SOFC/AEMFC、膜电极、耐久性与系统",
    icon="💧",
    facets=[
        F("type", "电池类型", "Fuel cell types", TYPE,
          top_min=12.0, sub_min=13.0, unspecified="type.other",
          note_zh="按燃料电池类型归类，可多选"),
        F("component", "关键部件", "Key components", COMPONENT, top_min=11.0, sub_min=12.0),
        F("theme", "研究主题", "Research themes", THEME, top_min=11.0, sub_min=11.0),
    ],
    core=CORE, context=CONTEXT, negative=NEGATIVE, journals=JOURNALS,
    search_hints=['"membrane electrode assembly"', "AEMFC", '"cold start"', '"low-Pt"'],
    core_min=12.0, relevance_min=13.0,
)
