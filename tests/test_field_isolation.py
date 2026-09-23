# -*- coding: utf-8 -*-
"""Cross-field isolation: every pack must accept its own papers and reject its
neighbours'.

A pack's ``core`` markers answer "is this paper *in* my field?"  Its ``context``
markers answer "is this paper serious about my field's concerns?"  A marker that
a sibling field shares -- ``thermal runaway``, ``power conversion efficiency``,
``oxygen reduction reaction`` -- is context, never core: put it in core and a
sodium-ion thermal-runaway paper walks straight into a lithium-ion reading list.

This suite is the regression fence for that mistake.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
from app import fields
from app.classify import for_pack

SSB, LIB, SIB, PSC, EC, FC = ("solid-state-battery", "lithium-ion-battery",
                              "sodium-ion-battery", "perovskite-solar",
                              "electrocatalysis", "fuel-cell")
NONE = "-"

# (true field, allowed-extra fields, title, abstract)
# "allowed extra" documents an overlap that is genuinely useful to that reader
# rather than hiding it.
CASES = [
 (SSB, {LIB}, "Argyrodite Li6PS5Cl electrolyte with suppressed dendrite growth for all-solid-state lithium batteries",
  "A sulfide solid electrolyte is densified by cold pressing; critical current density reaches 2 mA cm-2."),
 (SSB, {LIB}, "Garnet Li7La3Zr2O12 thin films for solid-state lithium metal batteries",
  "LLZO films are deposited by sputtering; the interfacial resistance against lithium metal is 12 ohm cm2."),
 (SSB, {LIB}, "A halide electrolyte Li3InCl6 enabling high-voltage solid-state cells",
  "The chloride superionic conductor is stable against a 4.6 V single-crystal cathode."),

 (LIB, set(), "Single-crystal high-nickel NCM cathode with reduced microcracking for lithium-ion batteries",
  "Ni-rich layered oxide particles are synthesised without grain boundaries; capacity retention is 92% after 1000 cycles."),
 (LIB, set(), "Thermal runaway propagation in prismatic lithium-ion battery modules",
  "Calorimetry and gas analysis of commercial LiFePO4 cells quantify the heat release rate during propagation."),
 (LIB, set(), "A film-forming additive for carbonate electrolytes in graphite/NMC full cells",
  "The LiPF6 electrolyte additive builds a robust solid electrolyte interphase and raises coulombic efficiency."),

 (SIB, set(), "Hard carbon anode with tuned closed pores for sodium-ion batteries",
  "The sodium storage plateau capacity reaches 320 mAh/g; sodiation is followed by operando Raman."),
 (SIB, set(), "Thermal runaway and flue gas transport behavior in sodium-ion battery energy storage systems",
  "Full-scale tests of a sodium-ion battery cabinet measure vent gas composition and state of health decay."),
 (SIB, set(), "P2-type layered oxide cathode for high-rate sodium storage",
  "The Na-ion cathode material shows reversible desodiation with 85% capacity retention."),

 (PSC, set(), "Self-assembled monolayer hole-selective contact for inverted perovskite solar cells",
  "The carbazole monolayer raises the open-circuit voltage; power conversion efficiency reaches 26.1%."),
 (PSC, set(), "Formamidinium lead iodide films with suppressed phase segregation for perovskite photovoltaics",
  "FAPbI3 perovskite absorber layers are stabilised; the photovoltaic performance is retained after 1000 h."),
 (PSC, set(), "Perovskite/silicon tandem solar cell with 33% power conversion efficiency",
  "A textured silicon heterojunction bottom cell is combined with a wide-bandgap halide perovskite top cell."),

 (EC, set(), "Ruthenium single-atom catalyst for acidic oxygen evolution reaction in proton exchange membrane water electrolysis",
  "The electrocatalyst sustains 1 A cm-2 with a low overpotential and a Tafel slope of 42 mV/dec."),
 (EC, set(), "Nickel-iron layered double hydroxide for alkaline seawater electrolysis",
  "The anode resists chloride corrosion during water splitting at industrial current density."),
 (EC, set(), "Copper catalyst for the CO2 reduction reaction to multicarbon products",
  "Faradaic efficiency for C2+ products reaches 78% in a membrane electrode assembly electrolyzer."),
 (EC, set(), "Proton exchange membrane water electrolysis stack degradation under dynamic operation",
  "Iridium dissolution and membrane thinning are quantified over 2000 h of intermittent water electrolysis."),

 (FC, set(), "Platinum-cobalt cathode catalyst layer with reduced ionomer coverage for PEMFC durability",
  "The membrane electrode assembly retains 90% power density after start-stop cycling; the polarization curve is unchanged."),
 (FC, set(), "Protonic ceramic fuel cell operating at 500 C with a barium zirconate electrolyte",
  "The PCFC achieves 0.9 W/cm2 peak power density with a triple phase boundary engineered cathode."),
 (FC, set(), "Bipolar plate coating for improved corrosion resistance in hydrogen fuel cell stacks",
  "Carbon-coated stainless steel plates meet the interfacial contact resistance target for a fuel cell vehicle."),
 (FC, set(), "Solid oxide fuel cell with a perovskite oxide air electrode",
  "The SOFC cathode is a mixed ionic-electronic conducting perovskite; polarization resistance is 0.08 ohm cm2."),

 # --- negative controls: in nobody's reading list -----------------------
 (NONE, set(), "Organic solar cells with non-fullerene acceptors reaching 19% efficiency",
  "The bulk heterojunction blend uses a Y6 derivative; the power conversion efficiency and open-circuit voltage are improved by a hole transport layer."),
 (NONE, set(), "Photocatalytic hydrogen production over cadmium sulfide nanorods under visible light",
  "Sacrificial hydrogen production proceeds with an apparent quantum yield of 40%; catalytic activity is stable for 20 h."),
 (NONE, set(), "Thermocatalytic CO2 hydrogenation to methanol over a copper-zinc oxide catalyst",
  "The fixed-bed reactor test gives a high turnover frequency and 60% selectivity at 250 C."),
 (NONE, set(), "Nitrogen-doped carbon supercapacitor electrodes with high power density",
  "The symmetric supercapacitor delivers 10 Wh/kg energy density with 95% capacity retention over 10000 cycles."),
 (NONE, set(), "A memristor crossbar array for neuromorphic in-memory computing",
  "The device shows 8-bit analogue conductance tuning suitable for neuromorphic accelerators."),
 (NONE, set(), "Aqueous zinc-ion battery with a hydrogel electrolyte",
  "The zinc anode is protected against dendrites; capacity retention is 88% and the full cell runs 5000 cycles."),
 (NONE, set(), "An organic redox flow battery for grid storage",
  "The flow battery uses a quinone electrolyte; coulombic efficiency is 99% over 500 cycles."),
 (NONE, set(), "Dye-sensitized solar cell with a copper complex redox mediator",
  "The DSSC reaches 13% efficiency under one sun illumination with a photovoltaic fill factor of 0.78."),
 (NONE, set(), "Microbial fuel cell for wastewater treatment",
  "The microbial community on the anode degrades organics while producing current at low power density."),
 (NONE, set(), "Thermoelectric performance of a half-Heusler alloy",
  "A figure of merit of 1.4 is reached at 900 K with a reduced lattice thermal conductivity."),
]

ORDER = [SSB, LIB, SIB, PSC, EC, FC]


def run() -> int:
    packs = {fid: fields.get(fid) for fid in ORDER}
    clfs = {fid: for_pack(p) for fid, p in packs.items()}
    fails, misses, leaks = [], 0, 0

    for true_field, allowed, title, abstract in CASES:
        verdicts = {}
        for fid in ORDER:
            r = clfs[fid].classify(title, abstract)
            verdicts[fid] = r
        row, bad = [], []
        for fid in ORDER:
            r = verdicts[fid]
            ok = r["in_scope"]
            if fid == true_field:
                if not ok:
                    bad.append("漏收 " + fid); misses += 1
            elif ok and fid not in allowed:
                bad.append("误收 " + fid); leaks += 1
            mark = "O" if ok else "."
            if fid == true_field:
                mark = "@" if ok else "X"
            elif ok and fid not in allowed:
                mark = "!"
            row.append(mark)
        tag = "FAIL" if bad else "ok"
        print("[%-4s] %s  %-14s | %s" % (tag, "".join(row),
                                         true_field if true_field != NONE else "(无)",
                                         title[:56]))
        if bad:
            fails.append((title, bad))
            for fid in ORDER:
                r = verdicts[fid]
                if (fid == true_field and not r["in_scope"]) or \
                   (fid != true_field and r["in_scope"] and fid not in allowed):
                    print("        %-22s core=%5.1f ctx=%4.1f neg=%5.1f rel=%5.1f" %
                          (fid, r["core"], r["context"], r["negative"], r["relevance"]))
                    print("        核心命中: %s" % (r["hits"]["core"][:5],))
    print("\n列顺序: %s" % "  ".join(ORDER))
    print("@=本领域正确收录  X=本领域漏收  !=其他领域误收  .=正确排除")
    print("%d/%d 条通过（漏收 %d，误收 %d）" % (len(CASES) - len(fails), len(CASES),
                                                misses, leaks))
    return len(fails)


if __name__ == "__main__":
    sys.exit(1 if run() else 0)
