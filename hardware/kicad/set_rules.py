"""Write the fab design rules and net classes into braintech16.kicad_pro (where KiCad keeps them).

Run after gen_schematic.py / before DRC. Values are standard 4-layer fab capability (JLCPCB/PCBWay:
0.09 mm track/space, 0.2 mm min drill, 0.45 mm min via) with a margin.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
PRO = os.path.join(HERE, "braintech16.kicad_pro")
POWER_NETS = ["VBUS", "VBAT", "VSYS", "3V3", "SW_3V3", "AVDD", "AVSS", "NEG3V3"]

d = json.load(open(PRO))
rules = d["board"]["design_settings"]["rules"]
rules.update({
    "min_clearance": 0.15, "min_track_width": 0.1, "min_via_diameter": 0.45, "min_via_annular_width": 0.1,
    "min_through_hole_diameter": 0.2, "min_hole_clearance": 0.15, "min_hole_to_hole": 0.25,
    "min_copper_edge_clearance": 0.3,
})
ns = d["net_settings"]
base = dict(ns["classes"][0])
default = dict(base, name="Default", clearance=0.15, track_width=0.15, via_diameter=0.45, via_drill=0.2)
power = dict(base, name="Power", clearance=0.15, track_width=0.3, via_diameter=0.6, via_drill=0.3, priority=0)
ns["classes"] = [default, power]
ns["netclass_patterns"] = [{"netclass": "Power", "pattern": n} for n in POWER_NETS]
json.dump(d, open(PRO, "w"), indent=2)
print("rules + net classes written to", os.path.basename(PRO))
