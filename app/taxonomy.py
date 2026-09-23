# -*- coding: utf-8 -*-
"""The subject taxonomy for solid-state battery literature.

Two independent facet trees, mirroring how the field organises itself:

``CHEMISTRY``  which electrolyte family a paper is about (polymer / oxide /
               sulfide / halide / hydride / composite), each subdivided.
``THEME``      what the paper studies (interfaces, Li-metal anode, composite
               cathode, manufacturing, characterisation, modelling, ...).

Rule syntax -- see :mod:`app.classify` for the matching semantics:
  ``(none)`` substring on the loose view   ``sqw:`` whole token on the loose view
  ``sq:``    substring on the joined view  ``re:`` / ``jre:`` regex on either
"""
from __future__ import annotations

# --------------------------------------------------------------------------
# Facet 1: electrolyte chemistry
# --------------------------------------------------------------------------
CHEMISTRY = [
    {
        "id": "polymer", "name_en": "Polymer electrolytes", "name_zh": "聚合物电解质",
        "rules": [
            ("polymer electrolyte", 6), ("solid polymer electrolyte", 8),
            ("polymeric electrolyte", 6), ("polymer-based electrolyte", 6),
            ("polymer solid electrolyte", 7), ("all-solid-state polymer", 7),
            ("sqw:spe", 2), ("sqw:spes", 2), ("copolymer electrolyte", 6),
            ("polymer matrix", 3), ("polymer host", 4), ("polymer membrane", 2),
            ("polymerized electrolyte", 6), ("macromolecular electrolyte", 6),
            ("re:polymers? (based |type )?(all )?solid state", 7),
            ("re:polymers? (based )?(assb|asslb|asslib)", 7),
        ],
        "children": [
            {"id": "polymer.peo", "name_en": "PEO & polyethers", "name_zh": "PEO 与聚醚",
             "rules": [("poly(ethylene oxide)", 8), ("polyethylene oxide", 8), ("sqw:peo", 6),
                       ("polyether", 5), ("poly(ethylene glycol)", 5), ("sqw:peg", 4),
                       ("polyethylene glycol", 5), ("ethylene oxide", 3), ("crown ether", 3),
                       ("poly(propylene oxide)", 5), ("polyoxyethylene", 6), ("sqw:pegda", 5),
                       ("sqw:pegdme", 5), ("polyether electrolyte", 8), ("sqw:peobased", 2)]},
            {"id": "polymer.carbonate", "name_en": "Polycarbonates & polyesters", "name_zh": "聚碳酸酯与聚酯",
             "rules": [("polycarbonate", 7), ("poly(propylene carbonate)", 8), ("sqw:ppc", 4),
                       ("poly(ethylene carbonate)", 8), ("sqw:pec", 4), ("polyester", 5),
                       ("poly(vinylene carbonate)", 7), ("poly(trimethylene carbonate)", 7),
                       ("sqw:ptmc", 5), ("polycaprolactone", 6), ("sqw:pcl", 4),
                       ("poly(1,3-dioxolane)", 7), ("dioxolane", 4), ("polyacetal", 4),
                       ("ring-opening polymeriz", 4)]},
            {"id": "polymer.fluoro", "name_en": "Fluoropolymers (PVDF etc.)", "name_zh": "含氟聚合物",
             "rules": [("poly(vinylidene fluoride)", 8), ("polyvinylidene fluoride", 8),
                       ("sqw:pvdf", 7), ("sqw:pvdfhfp", 8), ("hexafluoropropylene", 5),
                       ("fluoropolymer", 6), ("sqw:ptfe", 5), ("fluorinated polymer", 6),
                       ("sqw:pvdftrfe", 6)]},
            {"id": "polymer.nitrile", "name_en": "Nitrile & acrylate polymers", "name_zh": "腈类与丙烯酸酯聚合物",
             "rules": [("polyacrylonitrile", 7), ("sqw:pan", 4), ("succinonitrile", 6),
                       ("nitrile", 4), ("poly(methyl methacrylate)", 6), ("sqw:pmma", 5),
                       ("acrylate", 4), ("polyacrylamide", 5), ("cyanoethyl", 5),
                       ("sqw:petea", 5)]},
            {"id": "polymer.singleion", "name_en": "Single-ion conductors", "name_zh": "单离子导体",
             "rules": [("single-ion conduct", 10), ("single ion conduct", 10),
                       ("ionomer", 6), ("anion-tethered", 8), ("anion immobil", 8),
                       ("transference number of unity", 7), ("polyanion electrolyte", 6),
                       ("lithiated ionomer", 9), ("polymerized ionic liquid", 6),
                       ("unity transference", 8), ("single-lithium-ion", 9)]},
            {"id": "polymer.gel", "name_en": "Gel & quasi-solid electrolytes", "name_zh": "凝胶与准固态电解质",
             "rules": [("gel polymer electrolyte", 10), ("sqw:gpe", 5), ("quasi-solid", 8),
                       ("in-situ polymeriz", 8), ("in situ polymeriz", 8),
                       ("plastic crystal", 6), ("semi-solid", 5), ("in-situ solidif", 8),
                       ("gel electrolyte", 8), ("uv-curable", 5), ("photopolymeriz", 6),
                       ("thermally initiated polymeriz", 7), ("solid-like electrolyte", 6)]},
            {"id": "polymer.composite", "name_en": "Composite polymer electrolytes", "name_zh": "复合聚合物电解质",
             "rules": [("composite polymer electrolyte", 11), ("sqw:cpe", 5),
                       ("ceramic-in-polymer", 10), ("polymer-in-ceramic", 10),
                       ("inorganic filler", 8), ("ceramic filler", 9), ("active filler", 7),
                       ("polymer-ceramic", 9), ("hybrid polymer electrolyte", 8),
                       ("nanofiller", 6), ("garnet-polymer", 9), ("filler", 3),
                       ("polymer-inorganic composite", 9)]},
            {"id": "polymer.framework", "name_en": "MOF / COF & supramolecular", "name_zh": "MOF/COF 与超分子",
             "rules": [("metal-organic framework", 8), ("sqw:mof", 5), ("sqw:mofs", 5),
                       ("covalent organic framework", 9), ("sqw:cof", 5), ("sqw:cofs", 5),
                       ("supramolecular", 6), ("hydrogen-bonded organic framework", 7),
                       ("porous organic", 5), ("cyclodextrin", 5), ("molecular cage", 5),
                       ("covalent organic", 5)]},
            {"id": "polymer.bio", "name_en": "Bio-based & cellulose", "name_zh": "生物基与纤维素",
             "rules": [("cellulose", 7), ("chitosan", 7), ("lignin", 6), ("bio-based polymer", 8),
                       ("biopolymer", 7), ("bacterial cellulose", 9), ("aramid", 5),
                       ("nanocellulose", 8)]},
        ],
    },
    {
        "id": "oxide", "name_en": "Oxide electrolytes", "name_zh": "氧化物电解质",
        "rules": [
            ("oxide electrolyte", 8), ("oxide solid electrolyte", 9),
            ("oxide-based solid electrolyte", 9), ("oxide-based electrolyte", 7),
            ("ceramic solid electrolyte", 6), ("oxide ceramic electrolyte", 8),
            ("re:oxides? (based |type )?(all )?solid state", 8),
            ("re:oxides? (based )?(assb|asslb|asslib)", 8),
            ("re:(?<!glass )ceramic electrolyte", 6),
        ],
        "children": [
            {"id": "oxide.garnet", "name_en": "Garnet (LLZO)", "name_zh": "石榴石 (LLZO)",
             "rules": [("garnet", 9), ("sqw:llzo", 10), ("sqw:llzto", 10), ("sqw:llzno", 8),
                       ("sqw:li7la3zr2o12", 10), ("sq:li65la3zr15ta05o12", 10),
                       ("lithium lanthanum zirconate", 9), ("cubic garnet", 9),
                       ("sq:li7la3zr2o", 9), ("garnet-type", 10), ("sqw:lltzo", 9),
                       ("garnet-based", 10), ("garnet solid electrolyte", 10)]},
            {"id": "oxide.perovskite", "name_en": "Perovskite (LLTO)", "name_zh": "钙钛矿 (LLTO)",
             "rules": [("sqw:llto", 10), ("perovskite electrolyte", 10),
                       ("lithium lanthanum titanate", 9), ("sq:li3xla23xtio3", 10),
                       ("perovskite-type electrolyte", 10), ("perovskite-type", 5),
                       ("sq:lasrtio", 6)]},
            {"id": "oxide.nasicon", "name_en": "NASICON (LATP / LAGP)", "name_zh": "NASICON (LATP/LAGP)",
             "rules": [("nasicon", 9), ("sqw:latp", 10), ("sqw:lagp", 10), ("sqw:ltap", 9),
                       ("sq:li13al03ti17po43", 10), ("sq:li15al05ge15po43", 10),
                       ("sq:lizr2po43", 9), ("sq:liti2po43", 9), ("nasicon-type", 10),
                       ("sqw:natzp", 7), ("sqw:na3zr2si2po12", 9), ("phosphate electrolyte", 6)]},
            {"id": "oxide.lisicon", "name_en": "LISICON & silicates", "name_zh": "LISICON 与硅酸盐",
             "rules": [("lisicon", 9), ("sq:li14zngeo44", 10), ("silicate electrolyte", 7),
                       ("sqw:li4sio4", 8), ("orthosilicate", 6)]},
            {"id": "oxide.antiperovskite", "name_en": "Anti-perovskite", "name_zh": "反钙钛矿",
             "rules": [("anti-perovskite", 11), ("antiperovskite", 11), ("sqw:li3ocl", 10),
                       ("sqw:li3obr", 10), ("sqw:li2ohcl", 10),
                       ("lithium-rich anti-perovskite", 11)]},
            {"id": "oxide.thinfilm", "name_en": "Thin film & LiPON", "name_zh": "薄膜与 LiPON",
             "rules": [("sqw:lipon", 11), ("thin-film battery", 9), ("thin-film solid electrolyte", 10),
                       ("sputtered electrolyte", 9), ("atomic layer deposition", 6), ("sqw:ald", 3),
                       ("magnetron sputter", 6), ("pulsed laser deposition", 5), ("microbattery", 8),
                       ("thin-film electrolyte", 9)]},
            {"id": "oxide.borate", "name_en": "Borates, glasses & other oxides", "name_zh": "硼酸盐/玻璃与其他氧化物",
             "rules": [("borate electrolyte", 8), ("sqw:li3bo3", 8), ("lithium borate", 7),
                       ("oxide glass", 6), ("sqw:li2wo4", 6), ("sqw:li2zro3", 6),
                       ("sqw:linbo3", 6), ("sqw:li2moo4", 6), ("sqw:li3po4", 7),
                       ("tungstate", 5), ("niobate", 5), ("sqw:lialo2", 6)]},
        ],
    },
    {
        "id": "sulfide", "name_en": "Sulfide electrolytes", "name_zh": "硫化物电解质",
        "rules": [
            ("sulfide electrolyte", 9), ("sulfide solid electrolyte", 10),
            ("sulphide electrolyte", 9), ("sulfide-based solid electrolyte", 10),
            ("sulfide-based electrolyte", 8), ("thiophosphate", 7), ("sq:li2sp2s5", 9),
            ("sulfide superionic", 9), ("sulfide-based", 4),
            ("re:sulfides? (based |type )?(all )?solid state", 9),
            ("re:sulfides? (based )?(electrolyte|sse)", 9),
            ("re:sulfides? (based )?(assb|asslb|asslib)", 9),
        ],
        "children": [
            {"id": "sulfide.argyrodite", "name_en": "Argyrodite (Li6PS5Cl)", "name_zh": "硫银锗矿 (Li6PS5Cl)",
             "rules": [("argyrodite", 11), ("sqw:li6ps5cl", 11), ("sqw:li6ps5br", 11),
                       ("sqw:li6ps5i", 10), ("sq:li55ps45cl15", 11), ("sqw:li5ps4cl2", 11),
                       ("sqw:li6ps5x", 10), ("sqw:li7ps6", 9), ("argyrodite-type", 11),
                       ("jre:li6ps5?cl[0-9]{0,3}br", 10)]},
            {"id": "sulfide.lgps", "name_en": "LGPS & thio-LISICON", "name_zh": "LGPS 与 thio-LISICON",
             "rules": [("sqw:lgps", 11), ("sqw:li10gep2s12", 11), ("thio-lisicon", 11),
                       ("thiolisicon", 11), ("sqw:li10snp2s12", 11),
                       ("sq:li954si174p144s117cl03", 11), ("sqw:li10sip2s12", 11),
                       ("sq:lisips", 6), ("sqw:li11si2ps12", 10)]},
            {"id": "sulfide.glass", "name_en": "Glass & glass-ceramics", "name_zh": "玻璃与玻璃陶瓷",
             "rules": [("glass-ceramic", 9), ("sqw:li7p3s11", 11), ("sq:75li2s25p2s5", 11),
                       ("sulfide glass", 10), ("amorphous sulfide", 9), ("melt-quench", 6),
                       ("sq:li2sp2s5glass", 11), ("mechanochemical synthesis", 6),
                       ("glassy sulfide", 9)]},
            {"id": "sulfide.li3ps4", "name_en": "Li3PS4 & binary Li–P–S", "name_zh": "Li3PS4 与二元 Li–P–S",
             "rules": [("sqw:li3ps4", 11), ("sq:betali3ps4", 11), ("sqw:li4p2s6", 10),
                       ("sqw:li4ps4i", 10), ("binary li2s-p2s5", 9), ("sqw:li2ps3", 9)]},
            {"id": "sulfide.oxysulfide", "name_en": "Oxysulfides & doped sulfides", "name_zh": "氧硫化物与掺杂硫化物",
             "rules": [("oxysulfide", 11), ("oxy-sulfide", 11), ("oxygen-doped sulfide", 10),
                       ("sq:lisipso", 10), ("oxygen substitution", 6), ("sq:li2ops", 7),
                       ("nitrogen-doped sulfide", 8), ("oxide-sulfide solid solution", 9)]},
            {"id": "sulfide.other", "name_en": "Other sulfides (Sb, Sn, Si, Na)", "name_zh": "其他硫化物 (Sb/Sn/Si/Na)",
             "rules": [("sqw:li3sbs4", 10), ("sqw:na3sbs4", 10), ("sqw:na11sn2ps12", 10),
                       ("sqw:li4sns4", 10), ("sqw:li4ges4", 10), ("sqw:na3ps4", 10),
                       ("antimony sulfide electrolyte", 9), ("sqw:na2ps4", 9)]},
        ],
    },
    {
        "id": "halide", "name_en": "Halide electrolytes", "name_zh": "卤化物电解质",
        "rules": [
            ("halide electrolyte", 10), ("halide solid electrolyte", 11),
            ("halide-based solid electrolyte", 11), ("halide-based electrolyte", 9),
            ("halide superionic", 11), ("lithium halide", 6), ("metal halide electrolyte", 10),
            ("re:halides? (based |type )?(all )?solid state", 10),
            ("re:halides? (based )?(assb|asslb|asslib)", 10),
            ("sqw:li3mx6", 9), ("halide se", 5),
        ],
        "children": [
            {"id": "halide.chloride", "name_en": "Chlorides (Li3YCl6, Li3InCl6, Li2ZrCl6)", "name_zh": "氯化物",
             "rules": [("sqw:li3ycl6", 11), ("sqw:li3incl6", 11), ("sqw:li2zrcl6", 11),
                       ("sqw:li3ercl6", 11), ("sqw:li3scl6", 11), ("sqw:litacl6", 11),
                       ("sqw:li3hocl6", 10), ("chloride electrolyte", 10), ("sqw:lialcl4", 10),
                       ("sqw:li3mcl6", 10), ("chloride superionic", 11),
                       ("jre:li[0-9]{0,2}zrcl", 8), ("sqw:licl", 3),
                       ("jre:li3y[0-9x]{0,6}zr", 9), ("chloride-based electrolyte", 10),
                       ("re:chlorides? (based |type )?(all )?solid state", 10),
                       ("re:chlorides? (based )?(electrolyte|sse)", 10)]},
            {"id": "halide.bromide_iodide", "name_en": "Bromides & iodides", "name_zh": "溴化物与碘化物",
             "rules": [("sqw:li3ybr6", 11), ("bromide electrolyte", 10), ("iodide electrolyte", 10),
                       ("sqw:li3erbr6", 11), ("sqw:lii", 5), ("lithium iodide", 7),
                       ("sqw:li3inbr6", 11), ("sqw:li2inbr5", 10), ("sqw:libr", 4),
                       ("iodide-based electrolyte", 10), ("sqw:li4pi", 6)]},
            {"id": "halide.fluoride", "name_en": "Fluorides", "name_zh": "氟化物",
             "rules": [("fluoride electrolyte", 10), ("sqw:li3alf6", 11),
                       ("fluoride solid electrolyte", 11), ("fluoride-ion conduct", 9),
                       ("sqw:lif", 3), ("sqw:li2tif6", 9)]},
            {"id": "halide.oxyhalide", "name_en": "Oxyhalides (LiMOCl4)", "name_zh": "氧卤化物 (LiMOCl4)",
             "rules": [("oxyhalide", 11), ("oxychloride", 11), ("sqw:linbocl4", 11),
                       ("sqw:litaocl4", 11), ("sqw:limocl4", 11), ("sqw:liwocl4", 11),
                       ("jre:lizr[0-9]{0,2}ocl", 10), ("amorphous oxychloride", 11)]},
            {"id": "halide.mixed", "name_en": "Mixed & dual-halide", "name_zh": "混合/双卤体系",
             "rules": [("dual-halide", 11), ("mixed halide", 11), ("mixed-halide", 11),
                       ("halide mixture", 9), ("halogen substitution", 8),
                       ("jre:li3ybr[0-9x]{0,3}cl", 10), ("anion mixing", 7),
                       ("dual-anion halide", 10)]},
        ],
    },
    {
        "id": "hydride", "name_en": "Hydride & borohydride electrolytes", "name_zh": "氢化物与硼氢化物电解质",
        "rules": [
            ("borohydride", 10), ("sqw:libh4", 11), ("hydride electrolyte", 11),
            ("closo-borate", 11), ("closoborate", 11), ("sqw:li2b12h12", 11),
            ("sqw:licb11h12", 11), ("sqw:lib3h8", 11), ("complex hydride", 10),
            ("carborane", 9), ("amide-hydride", 9), ("sqw:linh2", 6),
        ],
        "children": [
            {"id": "hydride.borohydride", "name_en": "LiBH4-based", "name_zh": "LiBH4 基",
             "rules": [("sqw:libh4", 11), ("sq:libh4lii", 11), ("borohydride", 9),
                       ("sqw:nabh4", 8)]},
            {"id": "hydride.closoborate", "name_en": "Closo-borates & carboranes", "name_zh": "笼型硼酸盐与碳硼烷",
             "rules": [("closo-borate", 11), ("closoborate", 11), ("carborane", 10),
                       ("sqw:li2b12h12", 11), ("sqw:licb11h12", 11), ("sqw:b12h12", 10),
                       ("sqw:b10h10", 10)]},
        ],
    },
    {
        "id": "composite", "name_en": "Composite & hybrid electrolytes", "name_zh": "复合与混合电解质",
        "rules": [
            ("hybrid solid electrolyte", 9), ("composite solid electrolyte", 9),
            ("organic-inorganic hybrid electrolyte", 10), ("bilayer electrolyte", 10),
            ("multilayer electrolyte", 10), ("asymmetric electrolyte", 9),
            ("sandwich electrolyte", 10), ("dual-layer electrolyte", 10),
            ("heterostructured electrolyte", 10), ("composite electrolyte", 7),
            ("janus electrolyte", 10), ("gradient electrolyte", 10),
        ],
        "children": [
            {"id": "composite.orgino", "name_en": "Organic–inorganic hybrids", "name_zh": "有机-无机复合",
             "rules": [("organic-inorganic", 9), ("inorganic-organic", 9), ("hybrid electrolyte", 7),
                       ("polymer-inorganic", 9)]},
            {"id": "composite.multilayer", "name_en": "Multilayer / gradient designs", "name_zh": "多层与梯度设计",
             "rules": [("bilayer electrolyte", 10), ("trilayer", 9), ("multilayer electrolyte", 10),
                       ("gradient electrolyte", 10), ("layered electrolyte architecture", 9),
                       ("sandwich structure", 7), ("asymmetric electrolyte", 8)]},
            {"id": "composite.crosschem", "name_en": "Cross-chemistry stacks", "name_zh": "跨体系堆叠",
             "rules": [("halide-sulfide", 11), ("sulfide-halide", 11), ("oxide-polymer", 10),
                       ("polymer-sulfide", 10), ("catholyte-anolyte", 10),
                       ("halide sulfide bilayer", 11)]},
        ],
    },
    {
        # Assigned only when no specific family matches, so that a paper is
        # never invisible once the reader filters by electrolyte system.
        "id": "other", "name_en": "General / not system-specific",
        "name_zh": "综合 / 未指明体系",
        "rules": [],
        "children": [],
    },
]

# --------------------------------------------------------------------------
# Facet 2: research theme
# --------------------------------------------------------------------------
THEME = [
    {"id": "interface", "name_en": "Interfaces & interphases", "name_zh": "界面与界面相",
     "rules": [("interfacial", 6), ("interphase", 7), ("interface", 4), ("sqw:sei", 4),
               ("solid electrolyte interphase", 8), ("cathode-electrolyte interface", 9),
               ("space charge layer", 8), ("buffer layer", 7), ("coating layer", 6),
               ("interfacial resistance", 9), ("contact loss", 7), ("wetting", 5),
               ("interfacial stability", 8), ("interface engineering", 9),
               ("interfacial compatibility", 8)]},
    {"id": "limetal", "name_en": "Li-metal anode & dendrites", "name_zh": "锂金属负极与枝晶",
     "rules": [("lithium metal anode", 9), ("li metal anode", 9), ("dendrite", 9),
               ("critical current density", 10), ("lithium plating", 8), ("lithiophilic", 9),
               ("li deposition", 7), ("short circuit", 6), ("li penetration", 9),
               ("lithium stripping", 7), ("void formation", 8), ("li metal batter", 7),
               ("lithium metal batter", 7),
               ("lithium dendrite", 10)]},
    {"id": "anodefree", "name_en": "Anode-free / anode-less cells", "name_zh": "无负极/贫锂体系",
     "rules": [("anode-free", 11), ("anodeless", 11), ("anode-less", 11),
               ("li-free anode", 10), ("lithium-free anode", 10), ("zero excess lithium", 11),
               ("zero-excess", 10), ("in-situ formed anode", 9), ("current-collector-only", 9)]},
    {"id": "alloyanode", "name_en": "Si / alloy & conversion anodes", "name_zh": "硅/合金与转换型负极",
     "rules": [("silicon anode", 10), ("si anode", 9), ("alloy anode", 10),
               ("indium anode", 9), ("li in alloy", 8), ("tin anode", 9), ("graphite anode", 7),
               ("conversion anode", 9), ("li mg", 6), ("lithium alloy", 8),
               ("micro-silicon", 9), ("si-based anode", 9), ("sqw:liin", 7)]},
    {"id": "cathode", "name_en": "Composite cathodes & catholytes", "name_zh": "复合正极与正极电解质",
     "rules": [("composite cathode", 11), ("catholyte", 11), ("cathode composite", 10),
               ("sqw:ncm", 6), ("sqw:nmc", 6), ("single-crystal cathode", 9), ("sqw:lco", 4),
               ("cathode", 3), ("high-voltage cathode", 9),
               ("high-nickel", 8), ("cathode active material", 8), ("cathode loading", 8),
               ("areal capacity", 6), ("cathode coating", 8), ("sqw:licoo2", 7),
               ("sqw:linio2", 7), ("cobalt-free cathode", 9), ("disordered rocksalt", 8),
               ("cathode-electrolyte composite", 10)]},
    {"id": "lis", "name_en": "Solid-state Li–S & conversion", "name_zh": "固态锂硫与转换反应",
     "rules": [("lithium-sulfur", 10), ("li-s batter", 10), ("sulfur cathode", 10),
               ("polysulfide", 7), ("li2s cathode", 10), ("sulfur utilization", 9),
               ("all-solid-state lithium-sulfur", 11), ("sqw:fes2", 7),
               ("conversion cathode", 9), ("iron sulfide cathode", 9)]},
    {"id": "beyondli", "name_en": "Beyond-Li (Na, K, Mg, Zn, Ca)", "name_zh": "钠/钾/镁/锌等非锂体系",
     "rules": [("sodium solid electrolyte", 11), ("all-solid-state sodium", 11),
               ("solid-state sodium batter", 11), ("na-ion solid", 10), ("potassium solid", 10),
               ("magnesium solid electrolyte", 11), ("zinc solid-state", 10),
               ("calcium solid electrolyte", 11), ("na superionic", 10),
               ("solid-state sodium", 9), ("fluoride-ion batter", 10),
               ("aluminium solid electrolyte", 10), ("solid-state potassium", 10)]},
    {"id": "transport", "name_en": "Ion transport mechanisms", "name_zh": "离子输运机理",
     "rules": [("ionic conductivity", 7), ("ion transport", 8), ("activation energy", 6),
               ("li-ion migration", 9), ("conduction mechanism", 10), ("concerted migration", 10),
               ("hopping", 6), ("diffusion pathway", 9), ("anion rotation", 9),
               ("paddle-wheel", 10), ("transference number", 7), ("superionic conduct", 8),
               ("lattice dynamics", 7), ("grain boundary resistance", 9),
               ("ionic transport mechanism", 10)]},
    {"id": "chemomech", "name_en": "Chemo-mechanics & stack pressure", "name_zh": "化学-力学与堆叠压力",
     "rules": [("stack pressure", 11), ("chemo-mechanical", 11), ("mechanical propert", 6),
               ("volume change", 7), ("fracture", 7), ("elastic modulus", 8),
               ("cracking", 7), ("densification", 7), ("cold press", 7), ("pelletiz", 6),
               ("external pressure", 9), ("mechanical failure", 9), ("plastic deformation", 8),
               ("stress", 4), ("creep", 6)]},
    {"id": "manufacturing", "name_en": "Manufacturing & scale-up", "name_zh": "制造与规模化",
     "rules": [("scale-up", 9), ("dry process", 10), ("roll-to-roll", 11),
               ("sheet-type", 10), ("tape cast", 9), ("slurry", 6), ("pouch cell", 9),
               ("solvent-free", 9), ("free-standing membrane", 9), ("scalable", 6),
               ("thin electrolyte membrane", 10), ("manufactur", 8), ("cost analysis", 8),
               ("ultrathin electrolyte", 9), ("sintering", 6), ("pilot-scale", 10),
               ("dry-film", 10)]},
    {"id": "cellengineering", "name_en": "Cell & pack engineering", "name_zh": "电芯与系统工程",
     "rules": [("bipolar stack", 10), ("bipolar", 6), ("cell design", 8), ("energy density", 6),
               ("multilayer cell", 8), ("thermal management", 9), ("fast charg", 8),
               ("low-temperature operation", 8), ("wide temperature", 8), ("cycle life", 5),
               ("practical cell", 8), ("ah-level", 10), ("pouch", 5), ("full cell", 5),
               ("high-rate performance", 6)]},
    {"id": "characterization", "name_en": "Advanced characterisation", "name_zh": "先进表征",
     "rules": [("operando", 10), ("in situ characteriz", 9), ("cryo-em", 10),
               ("cryogenic electron", 10), ("solid-state nmr", 10), ("sqw:nmr", 6),
               ("synchrotron", 9), ("x-ray tomograph", 10), ("neutron", 7), ("tof-sims", 10),
               ("sqw:xps", 6), ("electron microscopy", 6), ("impedance spectroscopy", 7),
               ("sqw:eis", 5), ("raman", 5), ("diffraction", 5), ("ptychograph", 9),
               ("atom probe", 9), ("sqw:mri", 5)]},
    {"id": "computation", "name_en": "Computation, ML & screening", "name_zh": "计算、机器学习与筛选",
     "rules": [("density functional theory", 10), ("sqw:dft", 6), ("first-principles", 10),
               ("molecular dynamics", 10), ("machine learning", 10),
               ("machine-learned potential", 11), ("neural network potential", 11),
               ("high-throughput screening", 11), ("computational screening", 11),
               ("phase-field", 10), ("ab initio", 10), ("descriptor", 6),
               ("generative model", 9), ("sqw:mlip", 8), ("monte carlo", 8),
               ("continuum model", 8), ("digital twin", 9), ("simulation", 5)]},
    {"id": "safety", "name_en": "Safety, thermal & degradation", "name_zh": "安全、热与失效",
     "rules": [("thermal stability", 8), ("thermal runaway", 11), ("safety", 7),
               ("flammab", 9), ("degradation mechanism", 9), ("aging", 6),
               ("gas evolution", 9), ("sqw:h2s", 9), ("moisture stability", 10),
               ("air stability", 10), ("electrochemical stability window", 10),
               ("decomposition", 6), ("calorimetr", 8), ("failure mechanism", 9)]},
    {"id": "recycling", "name_en": "Sustainability & recycling", "name_zh": "可持续性与回收",
     "rules": [("recycl", 10), ("life cycle assessment", 11), ("sqw:lca", 5),
               ("circular econom", 10), ("critical raw material", 9), ("sustainab", 7),
               ("upcycl", 10), ("second life", 9), ("carbon footprint", 9),
               ("techno-economic", 10)]},
    {"id": "review", "name_en": "Reviews & perspectives", "name_zh": "综述与展望",
     "rules": [("review", 5), ("this review", 10), ("critical review", 11),
               ("comprehensive review", 11), ("perspective", 5), ("roadmap", 10),
               ("recent progress", 10), ("recent advance", 10), ("outlook", 5),
               ("challenges and opportunities", 10), ("state of the art", 5),
               ("we review", 10), ("overview", 4), ("tutorial", 8), ("in this perspective", 10)]},
]

# --------------------------------------------------------------------------
# Topical gate: is this paper about solid-state batteries at all?
# --------------------------------------------------------------------------
CORE_MARKERS = [
    ("all-solid-state batter", 10), ("all solid state batter", 10),
    ("solid-state batter", 9), ("solid-state lithium batter", 10),
    ("solid-state cell", 7), ("re:solid electrolytes?(?! interphase)", 9),
    ("solid-state electrolyte", 9),
    # An interphase mention alone is far too weak -- every liquid Li-ion paper
    # talks about the "solid electrolyte interphase (SEI)".
    ("solid electrolyte interphase", 2),
    ("superionic conductor", 8), ("sqw:asslb", 10), ("sqw:asslbs", 10), ("sqw:assb", 9),
    ("sqw:asslib", 10), ("sqw:asslibs", 10), ("sqw:sse", 7), ("sqw:sses", 7),
    ("sqw:assbs", 9), ("quasi-solid-state batter", 8), ("solid-state sodium batter", 10),
    ("sulfide electrolyte", 9), ("halide electrolyte", 9), ("oxide electrolyte", 8),
    ("re:polymer electrolytes?(?! membrane)", 7),
    ("garnet electrolyte", 10), ("argyrodite", 10),
    ("sqw:llzo", 10), ("sqw:llzto", 10), ("sqw:li6ps5cl", 10), ("sqw:lgps", 10),
    ("sqw:li10gep2s12", 10), ("sqw:latp", 9), ("sqw:lagp", 9), ("sqw:llto", 9),
    ("sqw:lipon", 9), ("sqw:li3ycl6", 10), ("sqw:li3incl6", 10), ("sqw:li7p3s11", 10),
    ("sqw:li3ps4", 10), ("sqw:li2zrcl6", 10), ("sqw:li7la3zr2o12", 10),
    ("anode-free", 4), ("catholyte", 8), ("thio-lisicon", 10), ("nasicon", 7),
    ("lisicon", 8), ("oxyhalide electrolyte", 10), ("bipolar solid-state", 9),
    ("sqw:li3ocl", 9), ("closo-borate", 9), ("sqw:libh4", 8), ("solid-state ionic", 6),
    ("re:(?<!glass )ceramic electrolyte", 7),
    ("solid-state ion conduct", 8), ("inorganic solid electrolyte", 10),
    ("solid-state anode", 6), ("solid-state conversion", 4),
    ("gel polymer electrolyte", 7), ("composite solid electrolyte", 9),
    ("solid-state metal batter", 9), ("solid-state pouch", 9),
]
# Battery context: keeps e.g. a "solid electrolyte" gas-sensor paper out.
CONTEXT_MARKERS = [
    ("batter", 3), ("lithium", 2), ("li-ion", 2), ("sodium", 1), ("cathode", 2), ("anode", 2),
    ("electrolyte", 2), ("ionic conductivity", 2), ("electrochemical", 1), ("cell", 1),
    ("energy storage", 2), ("charge/discharge", 2), ("cycling", 2), ("coulombic", 2),
    ("areal capacity", 2), ("mah", 2),
]
# Strong signals that a paper is not in scope.
NEGATIVE_MARKERS = [
    ("solid oxide fuel cell", 14), ("sqw:sofc", 12), ("fuel cell", 9), ("electrolyser", 8),
    ("electrolyzer", 8), ("water splitting", 9), ("oxygen evolution reaction", 9),
    ("hydrogen evolution reaction", 9), ("co2 reduction", 9), ("photocatal", 10),
    ("solar cell", 10), ("photovoltaic", 9), ("perovskite solar", 14), ("light-emitting", 10),
    ("supercapacitor", 7), ("thermoelectric", 9), ("drug delivery", 12), ("biosensor", 10),
    ("tissue engineering", 12), ("antibacterial", 10), ("wastewater", 10), ("dye removal", 10),
    ("gas sensor", 9), ("nitrogen reduction", 9), ("ammonia synthesis", 9),
    ("flow batter", 7), ("desalination", 10), ("memristor", 9), ("field-effect transistor", 9),
    ("aqueous zinc-ion", 8),
    ("solid-state laser", 12), ("solid-state lighting", 14), ("quantum dot display", 12),
    ("electrochromic", 9), ("hydrogen storage", 6),
    ("catalyst layer", 5), ("lead-acid", 9), ("nuclear", 8), ("microbial", 10),
    # --- proton-exchange fuel cells / electrolysers -----------------------
    ("polymer electrolyte membrane", 14), ("proton exchange membrane", 14),
    ("sqw:pemfc", 14), ("sqw:pem", 8), ("nafion", 12), ("gas diffusion layer", 12),
    ("membrane electrode assembly", 12), ("anion exchange membrane", 12),
    ("proton conduct", 8), ("sqw:orr", 8), ("oxygen reduction reaction", 9),
    ("oxide-ion conduct", 12), ("oxygen-ion conduct", 12), ("oxide ion conductor", 12),
    ("solid oxide electroly", 12), ("oxygen vacancy conduct", 9),
    ("electrocataly", 7), ("platinum catalyst", 9), ("iridium", 8),
    # --- other adjacent-but-different devices -----------------------------
    ("thermogalvanic", 12), ("thermocell", 10), ("triboelectric", 12),
    ("dye-sensitized", 12), ("reservoir computing", 12), ("neuromorphic", 12),
    ("synaptic", 12), ("actuator", 10), ("sqw:h2o2", 9), ("hydrogen peroxide", 10),
    ("nanofiltration", 12), ("electrodialysis", 12), ("osmotic", 10),
    ("seawater", 8), ("zinc-air", 8), ("aqueous batter", 6),
    ("aqueous zinc", 12), ("zinc-ion batter", 9), ("zn anode", 7),
    ("zinc metal anode", 9), ("aqueous electrolyte", 6), ("redox mediator", 7),
    ("redox-mediated", 7), ("hydrogel electrolyte", 7),
]

# --------------------------------------------------------------------------
# Flat lookup helpers
# --------------------------------------------------------------------------

def _flatten(tree, parent=None, depth=0, acc=None):
    acc = [] if acc is None else acc
    for node in tree:
        acc.append({"id": node["id"], "name_en": node["name_en"], "name_zh": node["name_zh"],
                    "parent": parent, "depth": depth})
        if node.get("children"):
            _flatten(node["children"], node["id"], depth + 1, acc)
    return acc


CHEMISTRY_FLAT = _flatten(CHEMISTRY)
THEME_FLAT = _flatten(THEME)
ALL_NODES = {n["id"]: n for n in CHEMISTRY_FLAT + THEME_FLAT}
CHEM_IDS = {n["id"] for n in CHEMISTRY_FLAT}
THEME_IDS = {n["id"] for n in THEME_FLAT}
TOP_CHEM_IDS = [n["id"] for n in CHEMISTRY_FLAT if n["depth"] == 0]


def label(node_id: str, lang: str = "zh") -> str:
    n = ALL_NODES.get(node_id)
    if not n:
        return node_id
    return n["name_zh"] if lang == "zh" else n["name_en"]


def descendants(node_id: str) -> set[str]:
    """``node_id`` plus every node below it."""
    out = {node_id}
    changed = True
    while changed:
        changed = False
        for n in CHEMISTRY_FLAT + THEME_FLAT:
            if n["parent"] in out and n["id"] not in out:
                out.add(n["id"])
                changed = True
    return out


def tree_json():
    """Serialisable facet definition for the front end."""
    def pack(nodes):
        return [{"id": n["id"], "en": n["name_en"], "zh": n["name_zh"],
                 "children": pack(n.get("children") or [])} for n in nodes]
    return {"chemistry": pack(CHEMISTRY), "theme": pack(THEME)}
