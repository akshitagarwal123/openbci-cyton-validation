"""
Create braintech16.kicad_pcb: 4-layer board outline, all footprints from circuit.py placed by zone,
pads assigned to nets, ground plane on In1.Cu. Routing: route_prep.py -> Freerouting -> import_ses.py (see build.sh).

Run with KiCad's own Python (has the pcbnew module):
    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 gen_pcb.py
"""

import os
import pcbnew
try:
    import wx
    _app = wx.App(False)
except Exception:
    _app = None

from circuit import parts
from kicad_lib import get_symbol, pins

HERE = os.path.dirname(os.path.abspath(__file__))
FPDIR = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
W, H = 80.0, 76.0                     # board size, mm (case inner ~ 88 x 84)
MM = pcbnew.FromMM

ANALOG_POWER_NETS = {"AVDD", "AVSS", "NEG3V3", "CP_P", "CP_N"}
# zone rectangles (x0, y0, x1, y1) in mm
ZONES = {
    "connector": (9, 1.0, 50, 13.5),
    "protection": (2, 14, 53, 30.5),
    "ads1": (2, 31, 27, 57),
    "ads2": (27.5, 31, 53, 57),
    "analog_power": (2, 57.5, 53, 68.5),    # under both ADS1299s, equal distance to each
    "mcu": (54.5, 22, 79, 46),
    "digital_power": (54.5, 47, 79, 75.5),
    "holes": None,
}
GAP = float(os.environ.get("GAP", "1.2"))   # extra space around every part = routing channels
ZGAP = {"protection": float(os.environ.get("PGAP", "1.6"))}   # densest fan-out area gets more


def zone_of(p):
    b = p["block"]
    if b.startswith("Electrode"):
        return "connector" if p["ref"].startswith("J") else "protection"
    if b.startswith("ADS1299 #1"):
        return "ads1"
    if b.startswith("ADS1299 #2"):
        return "ads2"
    if b == "Power":
        return "analog_power" if set(p["pins"].values()) & ANALOG_POWER_NETS else "digital_power"
    if b == "MCU":
        return "esp32" if "ESP32" in p["lib_id"] else "mcu"
    return "holes"


board = pcbnew.BOARD()
board.SetCopperLayerCount(4)
board.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)   # solid GND plane: the autorouter must not put tracks here
ds = board.GetDesignSettings()      # typical JLCPCB/PCBWay 4-layer capabilities
ds.m_MinThroughDrill = MM(0.2)
ds.m_HoleClearance = MM(0.15)
ds.m_MinClearance = MM(0.15)
ds.m_CopperEdgeClearance = MM(0.3)
try:
    ds.m_NetSettings.GetDefaultNetclass().SetClearance(MM(0.15))
except Exception as e:
    print("netclass clearance not set:", e)

# outline with 3 mm corner radius approximated by chamfer-free rectangle
for (x0, y0, x1, y1) in [(0, 0, W, 0), (W, 0, W, H), (W, H, 0, H), (0, H, 0, 0)]:
    seg = pcbnew.PCB_SHAPE(board)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0)))
    seg.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
    seg.SetLayer(pcbnew.Edge_Cuts)
    seg.SetWidth(MM(0.1))
    board.Add(seg)

nets = {}


def net(name):
    if name not in nets:
        n = pcbnew.NETINFO_ITEM(board, name)
        board.Add(n)
        nets[name] = n
    return nets[name]


pending = []
hole_pos = [(3.5, 3.5), (52.5, 3.5), (3.5, H - 3.5), (W - 3.5, H - 3.5)]   # top-right corner is the antenna
assigned = unmatched = 0
for p in parts:
    if not p["footprint"]:
        continue                                   # PWR_FLAG
    lib, fpname = p["footprint"].split(":")
    fp = pcbnew.FootprintLoad(os.path.join(FPDIR, lib + ".pretty"), fpname)
    fp.SetReference(p["ref"])
    fp.SetValue(p["value"])
    if p["ref"].startswith("J") and "02x10" in p["lib_id"]:
        fp.SetOrientationDegrees(90)                # harness connector lies along the top edge
    fp.Reference().SetVisible(False)               # machine-assembled: refs live on F.Fab, not silkscreen
    fp.Value().SetVisible(False)
    board.Add(fp)
    # pad -> net, using the symbol's pin numbers
    sym_pins = pins(get_symbol(p["lib_id"])) if p["lib_id"] != "Mechanical:MountingHole" else []
    num_to_net = {}
    for num, name, *_ in sym_pins:
        n = p["pins"].get(f"#{num}", p["pins"].get(name))
        if n:
            num_to_net[num] = n
    for pad in fp.Pads():
        pn = pad.GetNumber()
        if pn in num_to_net:
            pad.SetNet(net(num_to_net[pn]))
            assigned += 1
        elif pn == "S1" and "SHIELD" in p["pins"]:
            pad.SetNet(net(p["pins"]["SHIELD"]))
            assigned += 1
        elif pn and p["pins"]:
            unmatched += 1
            print(f"unmatched pad {p['ref']}:{pn}")
    pending.append((p, fp))

# parts that must sit on the board edge (reachable through the case): ref -> centre x, overhang past bottom edge
EDGE_BOTTOM = {"J1": (35.0, 1.0), "SW1": (47.0, 0.6)}

# placement: per zone, tallest parts first, packed in rows (reduces wasted row height)
byzone = {}
for p, fp in pending:
    bb = fp.GetBoundingBox(False)
    if p["ref"] in EDGE_BOTTOM:
        cxm, over = EDGE_BOTTOM[p["ref"]]
        fp.SetPosition(fp.GetPosition() + pcbnew.VECTOR2I(MM(cxm) - bb.GetCenter().x, MM(H + over) - bb.GetBottom()))
        continue
    g = ZGAP.get(zone_of(p), GAP)
    byzone.setdefault(zone_of(p), []).append((p, fp, bb, pcbnew.ToMM(bb.GetWidth()) + g, pcbnew.ToMM(bb.GetHeight()) + g))
for z, items in byzone.items():
    if z == "esp32":   # top-right corner, antenna (keep-out end) at the top edge
        p, fp, bb, w, h = items[0]
        fp.SetPosition(fp.GetPosition() + pcbnew.VECTOR2I(MM(W - 1.0) - bb.GetRight(), MM(0.5) - bb.GetTop()))
        continue
    if z == "holes":
        for (p, fp, *_), (x, y) in zip(items, hole_pos):
            fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
        continue
    x0, y0, x1, y1 = ZONES[z]
    cx, cy, rowh = x0, y0, 0
    for p, fp, bb, w, h in sorted(items, key=lambda t: -t[4]):
        if cx + w > x1:
            cx, cy, rowh = x0, cy + rowh, 0
        off = fp.GetPosition() - bb.GetOrigin()
        g = ZGAP.get(z, GAP)
        fp.SetPosition(pcbnew.VECTOR2I(MM(cx + g / 2) + off.x, MM(cy + g / 2) + off.y))
        cx, rowh = cx + w, max(rowh, h)
        if cy + h > y1 + 0.01:
            print(f"note: zone {z} overflows ({p['ref']} at y={cy + h:.1f} > {y1})")
    print(f"zone {z}: used to y={cy + rowh:.1f} of {y1}")

# ground plane on In1.Cu
zone = pcbnew.ZONE(board)
zone.SetLayer(pcbnew.In1_Cu)
zone.SetNet(net("GND"))
zone.SetLocalClearance(MM(0.2))                      # keeps the plane continuous between dense via fields
zone.SetMinThickness(MM(0.2))
zone.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
zone.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
outline = zone.Outline()
outline.NewOutline()
for x, y in [(0.5, 0.5), (W - 0.5, 0.5), (W - 0.5, H - 0.5), (0.5, H - 0.5)]:
    outline.Append(MM(x), MM(y))
board.Add(zone)
print("zone added; filling is done by kicad-cli (pcb drc --refill-zones) / the PCB editor", flush=True)

out = os.path.join(HERE, "braintech16.kicad_pcb")
print("saving...", flush=True)
board.Save(out)
print(f"saved {out}: {len(board.GetFootprints())} footprints, {len(nets)} nets, {assigned} pads on nets, {unmatched} pads unmatched")
