"""
Generate the BrainTech-8 (rev B) KiCad schematic from circuit.py (adapted from rev A's generator).

Every pin is connected by a net label placed exactly on the pin end (no drawn wires), unused pins get a
no-connect flag. This keeps the schematic machine-checkable: run
    kicad-cli sch erc braintech8.kicad_sch
and the netlist is exactly what circuit.py describes.
"""

import json
import os
import uuid

from circuit import parts
from kicad_lib import get_symbol, pins, dump

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "braintech8"
GRID = 2.54
PAPER_W, PAPER_H = 594, 420            # A2 landscape, mm
U = lambda: str(uuid.uuid4())
ROOT = "28f62a96-383f-46f9-8430-e56d65c88426"   # fixed: must match the sheet in braintech8.kicad_pro


def snap(v):
    return round(v / GRID) * GRID


def q(s):
    return '"' + str(s).replace('"', '\\"') + '"'


def pin_net(part, num, name):
    m = part["pins"]
    if f"#{num}" in m:
        return m[f"#{num}"]
    return m.get(name)


def bbox(pl):
    if not pl:
        return -5, -5, 5, 5
    xs = [p[2] for p in pl]
    ys = [-p[3] for p in pl]
    return min(xs), min(ys), max(xs), max(ys)



CHAR = 1.05     # approximate width of one 1.27 mm label character, mm


def body_points(node, out):
    """collect the drawn outline points (rectangle corners, polyline/arc/circle points) of a symbol, skipping pins."""
    if not isinstance(node, list) or not node:
        return out
    if node[0] in ("pin", "property"):
        return out
    if node[0] in ("start", "end", "xy", "center", "mid") and len(node) >= 3:
        try:
            out.append((float(node[1]), -float(node[2])))
        except ValueError:
            pass
    for c in node[1:]:
        body_points(c, out)
    return out


def extent(p, pl, sym=None):
    """box (sheet coords, relative to the symbol origin) covering the drawn body and every pin's net label,
    plus whether the part is a small vertical one (all pins up/down) whose text goes to the right."""
    x0, y0, x1, y1 = bbox(pl)
    for bx_, by_ in body_points(sym, []) if sym is not None else []:
        x0, y0, x1, y1 = min(x0, bx_), min(y0, by_), max(x1, bx_), max(y1, by_)
    vertical = len(pl) <= 2 and all(int(a) % 180 == 90 for *_, a, _t in pl)
    for num, name, px, py, ang, _t in pl:
        net = pin_net(p, num, name)
        L = (len(net) * CHAR + 1.5) if net else 1.5
        ex, ey = px, -py
        la = {0: 180, 180: 0, 90: 270, 270: 90}[int(ang) % 360]
        if la == 180: x0 = min(x0, ex - L)
        elif la == 0: x1 = max(x1, ex + L)
        elif la == 270: y1 = max(y1, ey + L)
        else: y0 = min(y0, ey - L)
    return x0, y0, x1, y1, vertical


lib_syms, placed, items = {}, [], []
blocks = []
for p in parts:
    if not blocks or blocks[-1][0] != p["block"]:
        blocks.append((p["block"], []))
    blocks[-1][1].append(p)

# block regions on the A1 sheet (x, y, width) in mm
REGIONS = {
    "Power": (20, 30, 550),
    "MCU": (20, 200, 260),
    "ADS1299": (300, 200, 270),
    "Electrode inputs + protection": (20, 330, 550),
}

for block, plist in blocks:
    bx, by, bw = REGIONS[block]
    items.append(f'(text {q(block)} (exclude_from_sim no) (at {bx} {by - 8} 0) '
                 f'(effects (font (size 3 3) (thickness 0.5) bold) (justify left)) (uuid {q(U())}))')
    x, y, row_h = bx, by, 0
    for p in plist:
        sym = get_symbol(p["lib_id"])
        lib_syms[p["lib_id"]] = sym
        pl = pins(sym)
        x0, y0, x1, y1, vert = extent(p, pl, sym)
        tw = max(len(p["ref"]), len(p["value"])) * CHAR + 2
        if vert:
            x1 = max(x1, max([bbox(pl)[2]] + [q_[0] for q_ in body_points(sym, [])]) + 1.5 + tw)                  # ref + value to the right of the body
        else:
            y0, y1 = y0 - 3.5, y1 + 3.5                          # ref above, value below everything
            x0, x1 = min(x0, -tw / 2), max(x1, tw / 2)
        w = (x1 - x0) + 8
        h = (y1 - y0) + 8
        if x + w > bx + bw:
            x, y, row_h = bx, y + row_h, 0
        sx, sy = snap(x - x0 + 4), snap(y - y0 + 3)
        placed.append((p, sx, sy, pl))
        x += w
        row_h = max(row_h, h)

sym_items = []
for p, sx, sy, pl in placed:
    lid = p["lib_id"]
    props = [("Reference", p["ref"], 0, -3), ("Value", p["value"], 0, 3), ("Footprint", p["footprint"], 0, 6),
             ("Datasheet", "", 0, 0), ("MPN", p["mpn"], 0, 9)]
    hidden = {"Footprint", "Datasheet", "MPN"}
    ptxt = []
    ex0, ey0, ex1, ey1, vert = extent(p, pl, lib_syms[lid])
    bx1 = max([bbox(pl)[2]] + [x for x, _ in body_points(lib_syms[lid], [])])
    for k, v, dx, dy in props:
        if vert:
            px_, py = sx + bx1 + 1.5, sy + {"Reference": -1.4, "Value": 1.4}.get(k, 4)
            just = " (justify left)"
        else:
            px_, py = sx, sy + (ey0 - 2.0 if k == "Reference" else ey1 + 2.0 if k == "Value" else ey1 + 4.5)
            just = ""
        eff = "(effects (font (size 1.27 1.27))" + just + (" hide" if k in hidden else "") + ")"
        ptxt.append(f'(property {q(k)} {q(v)} (at {px_:.2f} {py:.2f} 0) {eff})')
    pins_txt = " ".join(f'(pin {q(num)} (uuid {q(U())}))' for num, *_ in pl)
    is_flag = p["ref"].startswith("#")
    sym_items.append(
        f'(symbol (lib_id {q(lid)}) (at {sx:.2f} {sy:.2f} 0) (unit 1) (exclude_from_sim no) '
        f'(in_bom {"no" if is_flag or lid.startswith("Mechanical") else "yes"}) (on_board {"no" if is_flag else "yes"}) (dnp no) '
        f'(uuid {q(U())}) {" ".join(ptxt)} {pins_txt} '
        f'(instances (project {q(NAME)} (path {q("/" + ROOT)} (reference {q(p["ref"])}) (unit 1)))))')
    for num, name, px, py, ang, ptype in pl:
        ax, ay = sx + px, sy - py
        net = pin_net(p, num, name)
        if net is None:
            items.append(f'(no_connect (at {ax:.2f} {ay:.2f}) (uuid {q(U())}))')
            continue
        la = {0: 180, 180: 0, 90: 270, 270: 90}[int(ang) % 360]
        just = "left" if la in (0, 90) else "right"
        items.append(f'(label {q(net)} (at {ax:.2f} {ay:.2f} {la}) (fields_autoplaced yes) '
                     f'(effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid {q(U())}))')

notes = [
    "BrainTech-8 rev B - 8-channel EEG (ADS1299 + ESP32-S3), front end derived from the OpenBCI Cyton (CC BY-SA).",
    "Battery-powered while worn: never record from a person while USB is plugged in.",
    "Single GND net; 4-layer board with one solid ground plane on In1.Cu (GND).",
    "Generated by gen_schematic.py from circuit.py - edit circuit.py, not this file.",
]
for i, n in enumerate(notes):
    items.append(f'(text {q(n)} (exclude_from_sim no) (at 20 {PAPER_H - 40 + i * 6} 0) '
                 f'(effects (font (size 2 2)) (justify left)) (uuid {q(U())}))')

lib_txt = "\n".join("    " + dump(s) for s in lib_syms.values())
sch = (f'(kicad_sch (version 20231120) (generator "braintech_gen") (generator_version "1.0")\n'
       f'  (uuid {q(ROOT)})\n  (paper "A2")\n'
       f'  (title_block (title "BrainTech-8 8-channel EEG") (rev "B") (company "BrainTech") '
       f'(comment 1 "Front end derived from the OpenBCI Cyton, CC BY-SA"))\n'
       f'  (lib_symbols\n{lib_txt}\n  )\n  ' + "\n  ".join(sym_items + items) +
       f'\n  (sheet_instances (path "/" (page "1")))\n)\n')
open(os.path.join(HERE, NAME + ".kicad_sch"), "w").write(sch)
PRO = os.path.join(HERE, NAME + ".kicad_pro")
if not os.path.exists(PRO):          # never overwrite: KiCad keeps the board's design rules in this file
    json.dump({"meta": {"filename": NAME + ".kicad_pro", "version": 1}}, open(PRO, "w"))
print(f"wrote {NAME}.kicad_sch: {len(placed)} symbols, {sum(1 for i in items if i.startswith('(label'))} labels")
