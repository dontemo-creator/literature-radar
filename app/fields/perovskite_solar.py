# -*- coding: utf-8 -*-
"""Field pack: perovskite solar cells.

The word "perovskite" alone is not a field marker -- perovskite oxides show up
across catalysis and solid electrolytes -- so the gate requires photovoltaic
context, and battery / catalysis vocabulary is pushed out.
"""
from __future__ import annotations

from .base import F, N, Pack

COMPOSITION = [
    N("comp.cation", "阳离子组分工程", "Cation composition engineering", [
        ("triple cation", 12), ("mixed cation", 11), ("sqw:fapbi3", 11),
        ("sqw:mapbi3", 11), ("sqw:cspbi3", 11), ("formamidinium", 11),
        ("methylammonium", 10), ("sqw:fa", 4), ("sqw:ma", 4), ("cesium", 8),
        ("a-site", 10), ("compositional engineering", 11), ("sqw:csfama", 12),
        ("halide composition", 10), ("bromide substitution", 10)]),
    N("comp.leadfree", "无铅与低铅", "Lead-free & low-lead", [
        ("lead-free perovskite", 13), ("tin perovskite", 12), ("sqw:snpbi3", 11),
        ("sqw:cssni3", 12), ("bismuth-based perovskite", 12),
        ("double perovskite", 11), ("antimony-based", 10), ("sqw:fasni3", 12),
        ("tin-lead", 11), ("low-toxicity", 10)]),
    N("comp.lowdim", "二维与准二维", "2D & quasi-2D", [
        ("quasi-2d perovskite", 13), ("two-dimensional perovskite", 13),
        ("ruddlesden-popper", 13), ("dion-jacobson", 13), ("sqw:pea", 6),
        ("bulky ammonium", 11), ("2d/3d", 11), ("layered perovskite", 10),
        ("spacer cation", 11)]),
    N("comp.inorganic", "全无机钙钛矿", "All-inorganic perovskites", [
        ("all-inorganic perovskite", 13), ("sqw:cspbbr3", 12), ("sqw:cspbi2br", 12),
        ("inorganic perovskite", 11), ("phase stability of cspbi3", 13)]),
    N("comp.additive", "添加剂与钝化剂", "Additives & passivators", [
        ("additive engineering", 11), ("passivat", 8), ("surface passivation", 11),
        ("defect passivation", 12), ("lewis base", 11), ("ammonium salt treatment", 12),
        ("post-treatment", 10), ("grain boundary passivation", 12),
        ("antisolvent", 11), ("sqw:mac", 5), ("zwitterion", 10)]),
]

DEVICE = [
    N("dev.nip", "正式结构 (n-i-p)", "Regular n-i-p", [
        ("n-i-p", 12), ("regular structure", 10), ("mesoporous tio2", 12),
        ("planar n-i-p", 12), ("spiro-ometad", 11)]),
    N("dev.pin", "反式结构 (p-i-n)", "Inverted p-i-n", [
        ("p-i-n", 12), ("inverted perovskite", 13), ("inverted structure", 11),
        ("sqw:niox", 10), ("self-assembled monolayer", 12), ("sqw:sam", 5),
        ("sqw:me4pacz", 12), ("carbazole", 10), ("sqw:2pacz", 12)]),
    N("dev.tandem", "叠层器件", "Tandem devices", [
        ("tandem solar cell", 13), ("perovskite/silicon", 13),
        ("all-perovskite tandem", 13), ("two-terminal tandem", 13),
        ("four-terminal", 11), ("current matching", 11), ("recombination layer", 11),
        ("sqw:cigs tandem", 12), ("triple-junction", 12)]),
    N("dev.module", "大面积与组件", "Large area & modules", [
        ("solar module", 12), ("large-area", 10), ("blade coating", 12),
        ("slot-die coating", 13), ("scalable deposition", 12), ("aperture area", 12),
        ("minimodule", 12), ("upscaling", 11), ("vacuum deposition", 10),
        ("roll-to-roll", 11)]),
    N("dev.flexible", "柔性与轻质器件", "Flexible & lightweight", [
        ("flexible perovskite", 13), ("flexible substrate", 10), ("sqw:pet", 5),
        ("bending", 8), ("lightweight solar", 12), ("wearable", 9),
        ("indoor photovoltaic", 12)]),
]

LAYERS = [
    N("layer.etl", "电子传输层", "Electron transport layers", [
        ("electron transport layer", 12), ("sqw:etl", 9), ("sqw:sno2", 9),
        ("sqw:tio2", 7), ("sqw:pcbm", 10), ("sqw:c60", 9), ("fullerene", 9),
        ("sqw:bcp", 9), ("buried interface", 12), ("sqw:zno", 8)]),
    N("layer.htl", "空穴传输层", "Hole transport layers", [
        ("hole transport layer", 12), ("sqw:htl", 9), ("sqw:ptaa", 11),
        ("spiro-ometad", 11), ("sqw:niox", 9), ("sqw:pedotpss", 10),
        ("dopant-free", 11), ("sqw:cui", 9), ("sqw:cuscn", 11)]),
    N("layer.electrode", "电极与背接触", "Electrodes & back contacts", [
        ("transparent conductive", 11), ("sqw:ito", 8), ("sqw:fto", 9),
        ("carbon electrode", 11), ("back contact", 11), ("silver electrode", 10),
        ("copper electrode", 10), ("metal diffusion", 11), ("sqw:izo", 9)]),
    N("layer.interface", "界面与能级排列", "Interfaces & energy alignment", [
        ("energy level alignment", 12), ("band alignment", 11),
        ("interfacial recombination", 12), ("built-in potential", 11),
        ("interface engineering", 10), ("dipole layer", 11), ("work function", 9)]),
]

THEME = [
    N("theme.efficiency", "效率与认证", "Efficiency & certification", [
        ("power conversion efficiency", 10), ("sqw:pce", 8), ("certified efficiency", 13),
        ("open-circuit voltage", 10), ("fill factor", 10), ("voltage deficit", 12),
        ("sqw:voc", 7), ("record efficiency", 12), ("quasi-fermi level splitting", 12)]),
    N("theme.stability", "稳定性与老化", "Stability & ageing", [
        ("operational stability", 12), ("thermal stability", 9),
        ("light soaking", 11), ("damp heat", 12), ("sqw:iec 61215", 13),
        ("sqw:t80", 10), ("maximum power point tracking", 11), ("encapsulation", 11),
        ("moisture", 8), ("photostability", 12), ("reverse bias", 11),
        ("ion migration", 11), ("hysteresis", 10)]),
    N("theme.defects", "缺陷与载流子动力学", "Defects & carrier dynamics", [
        ("defect density", 11), ("trap state", 11), ("non-radiative recombination", 12),
        ("carrier lifetime", 11), ("photoluminescence", 10), ("sqw:tas", 6),
        ("transient absorption", 11), ("charge extraction", 11),
        ("deep-level", 11), ("space-charge-limited current", 12)]),
    N("theme.crystallization", "结晶与薄膜生长", "Crystallisation & film growth", [
        ("crystallization", 10), ("nucleation", 10), ("grain growth", 11),
        ("film morphology", 10), ("intermediate phase", 11), ("solvent engineering", 12),
        ("gas quenching", 12), ("annealing", 8), ("orientation", 8)]),
    N("theme.characterization", "先进表征", "Advanced characterisation", [
        ("operando", 10), ("in situ grazing", 12), ("sqw:gixrd", 11),
        ("synchrotron", 10), ("kelvin probe", 12), ("sqw:kpfm", 12),
        ("photoemission", 10), ("sqw:xps", 6), ("hyperspectral", 11),
        ("drive-level capacitance", 12)]),
    N("theme.modelling", "模拟与机器学习", "Simulation & ML", [
        ("drift-diffusion", 13), ("device simulation", 12), ("sqw:scaps", 12),
        ("density functional theory", 10), ("sqw:dft", 6), ("machine learning", 10),
        ("high-throughput screening", 11), ("first-principles", 10)]),
    N("theme.sustainability", "铅安全、回收与成本", "Lead safety, recycling & cost", [
        ("lead leakage", 13), ("lead sequestration", 13), ("recycl", 11),
        ("life cycle assessment", 12), ("levelized cost", 12), ("toxicity", 10),
        ("techno-economic", 12)]),
    N("theme.beyondpv", "发光与探测器件", "LEDs & detectors", [
        ("perovskite light-emitting", 13), ("sqw:peled", 12), ("photodetector", 12),
        ("x-ray detector", 12), ("laser", 9), ("scintillator", 12)]),
    N("theme.review", "综述与展望", "Reviews & perspectives", [
        ("review", 5), ("this review", 10), ("recent progress", 10),
        ("recent advance", 10), ("roadmap", 10), ("perspective", 5),
        ("challenges and opportunities", 10)]),
]

CORE = [
    ("perovskite solar cell", 14), ("perovskite photovoltaic", 14),
    ("perovskite solar", 12), ("halide perovskite", 11), ("metal halide perovskite", 13),
    ("perovskite film", 10), ("perovskite absorber", 13), ("perovskite device", 11),
    ("perovskite/silicon tandem", 14), ("all-perovskite tandem", 14), ("sqw:mapbi3", 12),
    ("sqw:fapbi3", 12), ("sqw:cspbi3", 12), ("sqw:cspbbr3", 12), ("sqw:pscs", 9),
    ("perovskite light-emitting", 12), ("perovskite photodetector", 12),
    ("perovskite quantum dot", 11), ("inverted perovskite", 13),
]
CONTEXT = [
    ("perovskite", 3), ("solar", 3), ("photovoltaic", 3), ("efficiency", 2), ("device", 1),
    ("film", 1), ("charge transport", 2), ("illumination", 2), ("sun", 1), ("light", 1),
    ("stability", 2), ("interface", 1), ("power conversion efficiency", 3), ("sqw:pce", 3),
    ("tandem solar cell", 3), ("hole transport layer", 3), ("electron transport layer", 3),
    ("photovoltaic performance", 3), ("solar cell efficiency", 3),
    ("open-circuit voltage", 3), ("self-assembled monolayer", 3),
]
NEGATIVE = [
    ("solid oxide fuel cell", 14), ("sqw:sofc", 13), ("fuel cell", 10),
    ("oxygen evolution reaction", 12), ("hydrogen evolution reaction", 12),
    ("water splitting", 11), ("electrocataly", 11), ("thermocataly", 11),
    ("co2 reduction", 9), ("ammonia synthesis", 11), ("methane", 9),
    ("solid electrolyte", 11), ("lithium-ion batter", 12), ("sodium-ion batter", 12),
    ("all-solid-state batter", 13), ("supercapacitor", 11), ("oxygen carrier", 12),
    ("proton conduct", 11), ("dielectric", 8), ("piezoelectric", 11),
    ("ferroelectric memory", 11), ("multiferroic", 12), ("thermoelectric", 11),
    ("photocatalytic degradation", 12), ("dye-sensitized", 7), ("organic solar cell", 6),
    ("biosensor", 11), ("drug delivery", 12), ("wastewater", 11),
]

JOURNALS = [
    "Nature", "Science", "Nature Energy", "Nature Materials", "Nature Photonics",
    "Nature Nanotechnology", "Nature Reviews Materials", "Nature Communications",
    "Nature Sustainability", "Science Advances", "Chemical Reviews",
    "Chemical Society Reviews", "Joule", "Chem", "Matter",
    "Energy & Environmental Science", "J. Am. Chem. Soc. (JACS)",
    "Angewandte Chemie Int. Ed.", "Advanced Materials", "Advanced Energy Materials",
    "ACS Energy Letters", "PNAS", "Progress in Materials Science",
    "Materials Science and Engineering R Reports",
    "Advanced Functional Materials", "Materials Today", "Nano Energy", "ACS Nano",
    "Nano Letters", "Small", "Advanced Science", "Journal of Materials Chemistry A",
    "Chemistry of Materials", "Chemical Engineering Journal", "InfoMat", "eScience",
    "Chemical Science", "ACS Materials Letters", "Materials Horizons",
    "Science Bulletin", "Nano-Micro Letters", "Small Methods",
    "Cell Reports Physical Science", "Advanced Optical Materials", "ACS Photonics",
    "Solar RRL", "Progress in Photovoltaics Research and Applications",
    "Solar Energy Materials and Solar Cells", "npj Flexible Electronics",
    "ACS Applied Materials & Interfaces", "Journal of Materials Chemistry C",
    "J. Phys. Chem. Lett.", "Chemical Communications", "ChemSusChem",
    "Advanced Materials Technologies", "Applied Energy",
    "Advanced Energy and Sustainability Research", "Nano Research",
    "Journal of Energy Chemistry", "ACS Applied Nano Materials",
]

PACK = Pack(
    id="perovskite-solar",
    zh="钙钛矿太阳能电池",
    en="Perovskite Solar Cells",
    tagline="组分工程、器件结构、叠层与稳定性",
    icon="☀️",
    facets=[
        F("composition", "材料体系", "Material systems", COMPOSITION,
          top_min=10.0, sub_min=11.0, unspecified="comp.additive",
          note_zh="按钙钛矿组分与改性策略归类，可多选"),
        F("device", "器件结构", "Device architecture", DEVICE, top_min=11.0, sub_min=12.0),
        F("layers", "功能层与界面", "Functional layers", LAYERS, top_min=10.0, sub_min=11.0),
        F("theme", "研究主题", "Research themes", THEME, top_min=10.0, sub_min=10.0),
    ],
    core=CORE, context=CONTEXT, negative=NEGATIVE, journals=JOURNALS,
    search_hints=['"inverted perovskite"', "tandem", '"self-assembled monolayer"', "FAPbI3"],
    core_min=11.0, relevance_min=12.0,
)
