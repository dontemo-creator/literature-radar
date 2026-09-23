# -*- coding: utf-8 -*-
"""Field pack: sodium-ion batteries.

Sodium work shares almost all of its vocabulary with lithium work, so the gate
here leans on explicit sodium markers: a paper that only says "battery" and
"cathode" is not enough, and lithium-only studies are pushed out.
"""
from __future__ import annotations

from .base import F, N, Pack

CATHODE = [
    N("cathode.layered", "层状氧化物 (O3/P2)", "Layered oxides (O3/P2)", [
        ("sqw:p2", 8), ("sqw:o3", 8), ("p2-type", 11), ("o3-type", 11),
        ("layered oxide cathode", 10), ("sqw:naniomno2", 9), ("na layered oxide", 11),
        ("sqw:nanimno2", 10), ("sqw:nafemno2", 10), ("p2/o3", 11),
        ("phase transition of layered", 9), ("na deficient", 9)]),
    N("cathode.pba", "普鲁士蓝类似物", "Prussian blue analogues", [
        ("prussian blue", 12), ("sqw:pba", 9), ("sqw:pbas", 9),
        ("hexacyanoferrate", 12), ("prussian white", 12), ("interstitial water", 9)]),
    N("cathode.polyanion", "聚阴离子化合物", "Polyanion compounds", [
        ("polyanion", 11), ("sqw:na3v2po43", 12), ("sqw:navpo4f", 12),
        ("nasicon-type cathode", 12), ("fluorophosphate", 11), ("pyrophosphate", 11),
        ("sqw:na4fe3po43p2o7", 12), ("sulfate cathode", 10), ("alluaudite", 11)]),
    N("cathode.organic", "有机正极", "Organic cathodes", [
        ("organic cathode", 11), ("quinone", 10), ("carboxylate", 9),
        ("conjugated", 7), ("redox-active organic", 11)]),
    N("cathode.other", "其他正极与改性", "Other cathodes & modification", [
        ("cathode coating", 9), ("doping", 6), ("surface reconstruction", 9),
        ("cathode active material", 7), ("gradient design", 9)]),
]

ANODE = [
    N("anode.hardcarbon", "硬碳", "Hard carbon", [
        ("hard carbon", 12), ("closed pore", 11), ("plateau capacity", 11),
        ("biomass-derived carbon", 11), ("carbonization temperature", 10),
        ("sqw:hc", 4), ("pore filling mechanism", 12), ("defect-rich carbon", 9)]),
    N("anode.alloy", "合金与磷基负极", "Alloy & phosphorus anodes", [
        ("tin anode", 11), ("antimony anode", 11), ("phosphorus anode", 11),
        ("alloy anode", 11), ("sqw:sb", 4), ("sqw:snsb", 10),
        ("red phosphorus", 11), ("volume expansion", 8), ("sqw:bi anode", 10)]),
    N("anode.titanate", "钛基与氧化物负极", "Titanates & oxide anodes", [
        ("sqw:na2ti3o7", 12), ("titanate anode", 11), ("sqw:natio2", 10),
        ("oxide anode", 9), ("sqw:tio2 anode", 10)]),
    N("anode.nametal", "钠金属与无负极", "Na-metal & anode-free", [
        ("sodium metal anode", 12), ("na metal anode", 12), ("anode-free", 11),
        ("sodium dendrite", 12), ("na plating", 11), ("sodiophilic", 12),
        ("zero excess sodium", 12)]),
    N("anode.conversion", "转换型与其他负极", "Conversion & other anodes", [
        ("conversion anode", 11), ("sulfide anode", 10), ("selenide anode", 10),
        ("mxene anode", 10), ("intercalation anode", 9)]),
]

ELECTROLYTE = [
    N("elyte.ester", "酯类电解液", "Ester-based electrolytes", [
        ("carbonate electrolyte", 10), ("sqw:naclo4", 11), ("sqw:napf6", 11),
        ("sqw:ec pc", 8), ("propylene carbonate", 9), ("ester-based", 10)]),
    N("elyte.ether", "醚类电解液", "Ether-based electrolytes", [
        ("ether-based electrolyte", 12), ("glyme", 11), ("sqw:dme", 7),
        ("diglyme", 11), ("co-intercalation", 11), ("solvated ion", 10)]),
    N("elyte.additive", "添加剂与界面调控", "Additives & interphase control", [
        ("electrolyte additive", 11), ("sqw:fec", 8), ("sqw:nadfob", 11),
        ("film-forming additive", 11), ("sqw:natfsi", 10), ("sqw:nafsi", 10)]),
    N("elyte.solid", "固态与准固态电解质", "Solid & quasi-solid electrolytes", [
        ("solid electrolyte", 9), ("sqw:na3ps4", 12), ("sqw:na3sbs4", 12),
        ("sqw:na3zr2si2po12", 12), ("nasicon", 9), ("beta-alumina", 11),
        ("gel polymer electrolyte", 10), ("all-solid-state sodium", 12)]),
    N("elyte.aqueous", "水系电解液", "Aqueous electrolytes", [
        ("aqueous sodium", 12), ("water-in-salt", 11), ("aqueous electrolyte", 9)]),
]

THEME = [
    N("theme.interphase", "界面相与界面", "Interphase & interfaces", [
        ("solid electrolyte interphase", 10), ("sqw:sei", 7), ("sqw:cei", 7),
        ("interphase chemistry", 11), ("interfacial", 6), ("passivation", 8)]),
    N("theme.mechanism", "储钠机理", "Na-storage mechanism", [
        ("sodium storage mechanism", 12), ("na+ diffusion", 10),
        ("intercalation mechanism", 11), ("phase evolution", 9),
        ("operando", 9), ("solid solution reaction", 10)]),
    N("theme.fastlowtemp", "快充与宽温", "Fast charging & temperature", [
        ("fast charging", 11), ("rate capability", 8), ("low temperature", 9),
        ("wide temperature", 10), ("high temperature performance", 10)]),
    N("theme.degradation", "衰减与失效", "Degradation & failure", [
        ("capacity fade", 11), ("degradation mechanism", 11), ("cycle life", 8),
        ("post-mortem", 10), ("crack", 7), ("air stability", 10),
        ("moisture sensitivity", 11)]),
    N("theme.manufacturing", "制造与电芯工程", "Manufacturing & cell engineering", [
        ("pouch cell", 10), ("dry electrode", 11), ("thick electrode", 11),
        ("scale-up", 10), ("sqw:cost", 6), ("sqw:costs", 6), ("ah-level", 11),
        ("cylindrical cell", 11),
        ("electrode processing", 10)]),
    N("theme.modelling", "计算与机器学习", "Computation & ML", [
        ("density functional theory", 10), ("sqw:dft", 6), ("molecular dynamics", 10),
        ("machine learning", 10), ("first-principles", 10),
        ("high-throughput screening", 11)]),
    N("theme.resource", "资源、成本与可持续", "Resources, cost & sustainability", [
        ("abundant", 8), ("low-cost", 9), ("lithium-free", 11), ("cobalt-free", 10),
        ("recycl", 11), ("life cycle assessment", 11), ("sustainab", 8),
        ("critical raw material", 11)]),
    N("theme.review", "综述与展望", "Reviews & perspectives", [
        ("review", 5), ("this review", 10), ("recent progress", 10),
        ("recent advance", 10), ("roadmap", 10), ("perspective", 5)]),
]

CORE = [
    ("sodium-ion batter", 12), ("na-ion batter", 12), ("sqw:sib", 8), ("sqw:sibs", 8),
    ("sodium batter", 11), ("sodium-ion", 9), ("na-ion", 9),
    ("sodium storage", 11), ("na storage", 11), ("sodium metal batter", 12),
    ("hard carbon anode", 11), ("prussian blue", 10), ("sqw:na3v2po43", 11),
    ("p2-type", 10), ("o3-type", 10), ("sodium insertion", 11),
    ("sodiation", 11), ("desodiation", 11), ("sodium-ion full cell", 12),
    ("all-solid-state sodium", 12), ("aqueous sodium-ion", 12),
    ("sodium half cell", 11), ("sqw:napf6", 10), ("sqw:naclo4", 10),
]
CONTEXT = [
    ("batter", 3), ("sodium", 3), ("cathode", 2), ("anode", 2), ("electrolyte", 2),
    ("electrochemical", 1), ("cycling", 2), ("capacity", 2), ("mah", 2),
    ("coulombic", 2), ("energy density", 2), ("cell", 1),
]
NEGATIVE = [
    ("solid oxide fuel cell", 14), ("sqw:sofc", 12), ("fuel cell", 10),
    ("proton exchange membrane", 13), ("nafion", 11), ("water splitting", 10),
    ("oxygen evolution reaction", 10), ("hydrogen evolution reaction", 10),
    ("electrocataly", 8), ("photocatal", 11), ("solar cell", 11),
    ("perovskite solar", 14), ("photovoltaic", 10), ("supercapacitor", 8),
    ("thermoelectric", 10), ("biosensor", 11), ("drug delivery", 12),
    ("wastewater", 11), ("desalination", 10), ("water treatment", 10),
    ("neuromorphic", 12), ("flow batter", 8),
    # sodium-sulfur at high temperature is a separate field
    ("molten sodium", 9), ("high-temperature sodium-sulfur", 11),
    # keep lithium-only work out
    ("lithium-ion batter", 5), ("zinc-ion batter", 7), ("potassium-ion batter", 5),
]

JOURNALS = [
    "Nature", "Science", "Nature Energy", "Nature Materials", "Nature Communications",
    "Nature Sustainability", "Science Advances", "Chemical Reviews",
    "Chemical Society Reviews", "Joule", "Chem", "Matter",
    "Energy & Environmental Science", "J. Am. Chem. Soc. (JACS)",
    "Angewandte Chemie Int. Ed.", "Advanced Materials", "Advanced Energy Materials",
    "ACS Energy Letters", "Electrochemical Energy Reviews",
    "Advanced Functional Materials", "Energy Storage Materials",
    "Nano Energy", "ACS Nano", "Nano Letters", "Small", "Advanced Science",
    "Journal of Materials Chemistry A", "Chemistry of Materials",
    "Chemical Engineering Journal", "Journal of Energy Chemistry", "InfoMat",
    "eScience", "Carbon Energy", "Chemical Science", "ACS Materials Letters",
    "Materials Horizons", "Science Bulletin", "Nano-Micro Letters", "Small Methods",
    "Cell Reports Physical Science", "ACS Applied Materials & Interfaces",
    "Journal of Power Sources", "Electrochimica Acta", "J. Electrochem. Soc.",
    "ACS Applied Energy Materials", "Batteries & Supercaps", "Nano Research",
    "Green Energy & Environment", "Chinese Chemical Letters",
    "Energy Material Advances", "Battery Energy", "Journal of Energy Storage",
    "Chemical Communications", "Rare Metals", "Journal of Materials Science & Technology",
]

PACK = Pack(
    id="sodium-ion-battery",
    zh="钠离子电池",
    en="Sodium-Ion Batteries",
    tagline="层状氧化物、普鲁士蓝、硬碳负极与低成本储能",
    icon="🧂",
    facets=[
        F("cathode", "正极材料", "Cathode materials", CATHODE,
          top_min=9.0, sub_min=10.0, unspecified="cathode.other",
          note_zh="按正极体系归类；未点明体系的落在「其他」"),
        F("anode", "负极材料", "Anode materials", ANODE, top_min=10.0, sub_min=10.0),
        F("electrolyte", "电解液与电解质", "Electrolytes", ELECTROLYTE,
          top_min=10.0, sub_min=10.0),
        F("theme", "研究主题", "Research themes", THEME, top_min=9.0, sub_min=9.0),
    ],
    core=CORE, context=CONTEXT, negative=NEGATIVE, journals=JOURNALS,
    search_hints=['"hard carbon"', '"Prussian blue"', "P2-type", "Na3V2(PO4)3"],
    core_min=10.0, relevance_min=11.0,
)
