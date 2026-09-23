# -*- coding: utf-8 -*-
"""Field pack: electrocatalysis and green hydrogen.

Organised by reaction first, because that is how the field indexes itself: a
reader following OER cares little about CO2 reduction even though both share
catalyst vocabulary.  Battery and photovoltaic work is pushed out -- "catalyst"
appears in both without meaning electrocatalysis.
"""
from __future__ import annotations

from .base import F, N, Pack

REACTION = [
    N("rxn.her", "析氢 (HER)", "Hydrogen evolution (HER)", [
        ("hydrogen evolution reaction", 13), ("sqw:her", 10),
        ("hydrogen evolution", 11), ("volmer", 12), ("heyrovsky", 12),
        ("tafel slope", 8), ("hydrogen production", 9), ("overpotential at 10", 10)]),
    N("rxn.oer", "析氧 (OER)", "Oxygen evolution (OER)", [
        ("oxygen evolution reaction", 13), ("sqw:oer", 10), ("oxygen evolution", 11),
        ("lattice oxygen mechanism", 13), ("sqw:lom", 8), ("adsorbate evolution", 12),
        ("oxyhydroxide", 11), ("water oxidation", 11)]),
    N("rxn.orr", "氧还原 (ORR)", "Oxygen reduction (ORR)", [
        ("oxygen reduction reaction", 13), ("sqw:orr", 10), ("oxygen reduction", 11),
        ("four-electron pathway", 12), ("half-wave potential", 12),
        ("rotating disk electrode", 11), ("sqw:rde", 9)]),
    N("rxn.co2rr", "CO2 还原 (CO2RR)", "CO2 reduction (CO2RR)", [
        ("co2 reduction reaction", 13), ("sqw:co2rr", 12), ("sqw:ecr", 8),
        ("co2 electroreduction", 13), ("carbon dioxide reduction", 12),
        ("formate", 10), ("ethylene", 10), ("c2+ product", 13),
        ("faradaic efficiency", 9), ("co2-to-", 12), ("syngas", 10)]),
    N("rxn.nrr", "氮还原与硝酸盐还原", "N2 / nitrate reduction", [
        ("nitrogen reduction reaction", 13), ("sqw:nrr", 11),
        ("ammonia synthesis", 11), ("electrochemical ammonia", 13),
        ("nitrate reduction", 13), ("sqw:no3rr", 12), ("nitrite reduction", 12),
        ("n2 fixation", 12)]),
    N("rxn.organic", "有机小分子氧化", "Organic oxidation", [
        ("methanol oxidation", 13), ("sqw:mor", 8), ("ethanol oxidation", 12),
        ("urea oxidation", 13), ("sqw:hmf", 11), ("glycerol oxidation", 13),
        ("formic acid oxidation", 12), ("biomass upgrading", 12),
        ("hybrid water electrolysis", 13)]),
    N("rxn.other", "其他反应与耦合体系", "Other & coupled reactions", [
        ("chlorine evolution", 12), ("hydrogen peroxide production", 12),
        ("sqw:2e oer", 10), ("coupled electrolysis", 12), ("paired electrolysis", 13),
        ("sulfion oxidation", 12)]),
]

CATALYST = [
    N("cat.single", "单原子与原子级分散", "Single-atom & atomically dispersed", [
        ("single-atom catalyst", 13), ("sqw:sac", 9), ("sqw:sacs", 9),
        ("atomically dispersed", 13), ("dual-atom", 13), ("sqw:m-n-c", 11),
        ("sqw:fenc", 11), ("coordination environment", 11), ("sqw:n4", 7),
        ("atomic site", 11)]),
    N("cat.noble", "贵金属与合金", "Noble metals & alloys", [
        ("sqw:pt", 6), ("sqw:ir", 6), ("sqw:ru", 6), ("platinum", 9),
        ("iridium oxide", 12), ("sqw:iro2", 12), ("sqw:ruo2", 12),
        ("pt alloy", 12), ("core-shell nanoparticle", 11), ("low-iridium", 13),
        ("intermetallic", 11), ("noble-metal-free", 12)]),
    N("cat.oxide", "氧化物与氢氧化物", "Oxides & (oxy)hydroxides", [
        ("layered double hydroxide", 13), ("sqw:ldh", 10), ("spinel oxide", 12),
        ("perovskite oxide catalyst", 13), ("sqw:nife", 9), ("sqw:nifeooh", 12),
        ("cobalt oxide", 10), ("oxygen vacanc", 9), ("high-entropy oxide", 13)]),
    N("cat.pnc", "磷化物/硫化物/氮化物/碳化物", "Phosphides, sulfides, nitrides, carbides", [
        ("transition metal phosphide", 13), ("sqw:mos2", 11), ("sulfide catalyst", 11),
        ("nitride catalyst", 12), ("carbide catalyst", 12), ("sqw:mxene", 10),
        ("sqw:ni2p", 12), ("sqw:cop", 8), ("selenide catalyst", 12),
        ("boride", 11)]),
    N("cat.carbon", "碳基与非金属", "Carbon-based & metal-free", [
        ("metal-free catalyst", 13), ("heteroatom-doped carbon", 13),
        ("n-doped carbon", 11), ("graphene catalyst", 11), ("carbon nanotube", 9),
        ("defect engineering of carbon", 12)]),
    N("cat.framework", "MOF/COF 及其衍生物", "MOF / COF derived", [
        ("metal-organic framework", 10), ("sqw:mof", 8), ("sqw:mofs", 8),
        ("covalent organic framework", 11), ("sqw:cof", 8),
        ("mof-derived", 13), ("sqw:zif", 11), ("molecular catalyst", 11),
        ("phthalocyanine", 12), ("porphyrin", 11)]),
    N("cat.highentropy", "高熵与无序体系", "High-entropy & disordered", [
        ("high-entropy alloy", 13), ("sqw:hea", 9), ("amorphous catalyst", 12),
        ("compositionally complex", 12), ("entropy stabiliz", 12)]),
]

SYSTEM = [
    N("sys.alkaline", "碱性水电解", "Alkaline water electrolysis", [
        ("alkaline water electrolysis", 13), ("alkaline electrolyzer", 13),
        ("sqw:awe", 9), ("1 m koh", 10), ("industrial current density", 12),
        ("nickel foam", 9)]),
    N("sys.pem", "PEM 水电解", "PEM water electrolysis", [
        ("sqw:pemwe", 13), ("proton exchange membrane water", 14),
        ("acidic oer", 13), ("iridium loading", 13), ("sqw:nafion", 9),
        ("titanium porous transport", 13)]),
    N("sys.aem", "AEM 水电解", "AEM water electrolysis", [
        ("anion exchange membrane water", 14), ("sqw:aemwe", 13),
        ("anion exchange membrane", 11), ("sqw:aem", 9)]),
    N("sys.soec", "高温 SOEC", "High-temperature SOEC", [
        ("solid oxide electrolysis", 14), ("sqw:soec", 13),
        ("high-temperature electrolysis", 13), ("co-electrolysis", 12),
        ("sqw:ysz", 11), ("proton-conducting ceramic", 12)]),
    N("sys.seawater", "海水与非纯水电解", "Seawater & impure feeds", [
        ("seawater electrolysis", 14), ("direct seawater", 13),
        ("chloride selectivity", 13), ("impurity tolerance", 12),
        ("wastewater electrolysis", 12)]),
    N("sys.mea", "膜电极与流场设计", "MEA & flow-field design", [
        ("membrane electrode assembly", 13), ("sqw:mea", 9),
        ("gas diffusion electrode", 13), ("sqw:gde", 10), ("flow cell", 11),
        ("zero-gap", 13), ("catalyst layer", 9), ("ionomer", 10),
        ("flooding", 10), ("bipolar membrane", 12)]),
]

THEME = [
    N("theme.mechanism", "机理与原位表征", "Mechanism & in-situ probes", [
        ("reaction mechanism", 10), ("operando", 11), ("in situ raman", 12),
        ("sqw:xas", 10), ("x-ray absorption", 11), ("sqw:exafs", 11),
        ("isotope labeling", 12), ("active site identification", 13),
        ("reconstruction", 9), ("in situ atr", 12), ("kinetic isotope", 12)]),
    N("theme.theory", "理论计算与描述符", "Theory & descriptors", [
        ("density functional theory", 11), ("sqw:dft", 7), ("computational hydrogen", 13),
        ("scaling relation", 12), ("volcano plot", 13), ("d-band center", 13),
        ("adsorption energy", 11), ("microkinetic", 13), ("machine learning", 10),
        ("high-throughput screening", 12), ("descriptor", 9)]),
    N("theme.stability", "稳定性与降解", "Stability & degradation", [
        ("durability", 10), ("stability test", 11), ("degradation mechanism", 11),
        ("dissolution", 10), ("accelerated stress test", 13), ("1000 h", 11),
        ("sqw:ast", 8), ("s-number", 13), ("metal leaching", 12)]),
    N("theme.selectivity", "选择性与法拉第效率", "Selectivity & Faradaic efficiency", [
        ("faradaic efficiency", 11), ("selectivity", 9), ("product distribution", 11),
        ("partial current density", 12), ("single-pass conversion", 13),
        ("carbonate crossover", 13)]),
    N("theme.scaleup", "规模化、成本与系统", "Scale-up, cost & systems", [
        ("techno-economic", 13), ("levelized cost of hydrogen", 14),
        ("scale-up", 11), ("stack", 8), ("industrial", 9), ("pilot", 10),
        ("intermittent operation", 12), ("coupling with renewable", 12),
        ("green hydrogen", 12), ("life cycle assessment", 12)]),
    N("theme.review", "综述与展望", "Reviews & perspectives", [
        ("review", 5), ("this review", 10), ("recent progress", 10),
        ("recent advance", 10), ("roadmap", 10), ("perspective", 5),
        ("challenges and opportunities", 10)]),
]

CORE = [
    ("electrocataly", 12), ("electrocatalyst", 13), ("electrocatalysis", 13),
    ("hydrogen evolution reaction", 13), ("oxygen evolution reaction", 13),
    ("oxygen reduction reaction", 13), ("co2 reduction reaction", 13),
    ("nitrogen reduction reaction", 13), ("nitrate reduction", 11), ("water splitting", 12),
    ("water electrolysis", 13), ("electrolyzer", 12), ("electrolyser", 12), ("sqw:her", 9),
    ("sqw:oer", 9), ("sqw:orr", 9), ("sqw:co2rr", 11), ("green hydrogen", 11),
    ("solid oxide electrolysis", 12), ("seawater electrolysis", 13),
    ("methanol oxidation reaction", 12), ("urea oxidation", 12),
]
CONTEXT = [
    ("catalyst", 3), ("catalytic", 2), ("electrode", 2), ("electrochemical", 2),
    ("current density", 2), ("potential", 1), ("selectivity", 2), ("activity", 2),
    ("hydrogen", 2), ("oxygen", 1), ("membrane", 1), ("electrolyte", 1),
    ("overpotential", 3), ("faradaic efficiency", 3), ("tafel slope", 3),
    ("turnover frequency", 3), ("single-atom catalyst", 3),
    ("membrane electrode assembly", 3), ("hydrogen production", 3),
    ("catalytic activity", 3),
]
NEGATIVE = [
    ("lithium-ion batter", 12), ("sodium-ion batter", 12), ("all-solid-state batter", 12),
    ("solid electrolyte interphase", 11), ("supercapacitor", 10),
    ("lithium metal anode", 11), ("cathode material for batter", 12),
    ("zinc-ion batter", 10), ("battery cycling", 9), ("photocatalytic", 9),
    ("photoelectrochemical", 6), ("solar cell", 12), ("perovskite solar", 13),
    ("photovoltaic", 11), ("thermocatalytic", 10), ("fischer-tropsch", 12),
    ("steam reforming", 11), ("fixed-bed reactor", 11), ("enzymatic", 11),
    ("homogeneous catalysis", 8), ("drug delivery", 12), ("biosensor", 10), ("tissue", 11),
    ("antibacterial", 11), ("dye degradation", 12), ("adsorption isotherm", 9),
    ("thermoelectric", 11), ("desalination", 9),
]

JOURNALS = [
    "Nature", "Science", "Nature Energy", "Nature Catalysis", "Nature Materials",
    "Nature Nanotechnology", "Nature Chemistry", "Nature Synthesis",
    "Nature Communications", "Nature Sustainability", "Nature Reviews Materials",
    "Nature Reviews Chemistry", "Science Advances", "Chemical Reviews",
    "Chemical Society Reviews", "Joule", "Chem", "Matter",
    "Energy & Environmental Science", "J. Am. Chem. Soc. (JACS)",
    "Angewandte Chemie Int. Ed.", "Advanced Materials", "Advanced Energy Materials",
    "ACS Energy Letters", "PNAS", "Accounts of Chemical Research", "JACS Au",
    "ACS Catalysis", "Applied Catalysis B Environment and Energy",
    "Catalysis Science & Technology", "Journal of Catalysis", "ChemCatChem",
    "ChemSusChem", "Green Chemistry", "EES Catalysis", "ACS Electrochemistry",
    "Advanced Functional Materials", "Materials Today", "Nano Energy", "ACS Nano",
    "Nano Letters", "Small", "Advanced Science", "Journal of Materials Chemistry A",
    "Chemistry of Materials", "Chemical Engineering Journal",
    "Journal of Energy Chemistry", "InfoMat", "eScience", "Chemical Science",
    "ACS Materials Letters", "Materials Horizons", "National Science Review",
    "Science Bulletin", "Nano-Micro Letters", "Small Methods",
    "Cell Reports Physical Science", "ACS Applied Materials & Interfaces",
    "ACS Sustainable Chemistry & Engineering", "J. Electrochem. Soc.",
    "Electrochimica Acta", "Electrochemistry Communications",
    "International Journal of Hydrogen Energy", "Journal of Membrane Science",
    "Chemical Communications", "J. Phys. Chem. Lett.", "ACS Central Science",
    "Nano Research", "Chinese Chemical Letters", "Green Energy & Environment",
    "Applied Energy", "Renewable and Sustainable Energy Reviews",
]

PACK = Pack(
    id="electrocatalysis",
    zh="电催化与制氢",
    en="Electrocatalysis & Green Hydrogen",
    tagline="HER/OER/ORR/CO2RR、单原子催化剂与电解槽",
    icon="⚡",
    facets=[
        F("reaction", "目标反应", "Target reactions", REACTION,
          top_min=11.0, sub_min=12.0, unspecified="rxn.other",
          note_zh="按电催化反应归类，可多选（或关系）"),
        F("catalyst", "催化剂体系", "Catalyst systems", CATALYST,
          top_min=11.0, sub_min=12.0),
        F("system", "器件与体系", "Devices & systems", SYSTEM, top_min=12.0, sub_min=13.0),
        F("theme", "研究主题", "Research themes", THEME, top_min=11.0, sub_min=11.0),
    ],
    core=CORE, context=CONTEXT, negative=NEGATIVE, journals=JOURNALS,
    search_hints=['"single-atom"', "CO2RR", '"seawater electrolysis"', '"d-band center"'],
    core_min=12.0, relevance_min=13.0,
)
