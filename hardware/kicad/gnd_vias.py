"""Give every SMD ground pad its own short stub + via to the In1.Cu ground plane (locked, so the autorouter
keeps them and only has to route signals). Standard practice: each decoupling cap and each TVS gets the
shortest possible path to ground.

Searches 24 directions x several distances around each pad for a via spot that keeps >= 0.2 mm from every
other-net object (and from every other pad) on all layers. Run with KiCad's Python on the placed board,
before route_prep.py:   $KPY gnd_vias.py           (all GND pads)
                        $KPY gnd_vias.py D7 D8     (only these parts)
"""
import math
import sys
import pcbnew, wx
app = wx.App(False)
MM, TO = pcbnew.FromMM, pcbnew.ToMM
VIA_D, VIA_DR = 0.45, 0.2
PASSES = [(0.2, 0.25), (0.15, 0.2)]          # (clearance, stub width): preferred, then board minimum
CLR, STUB_W = PASSES[0]
W, H = 80.0, 76.0

b = pcbnew.LoadBoard("braintech16.kicad_pcb")
gnd = b.FindNet("GND")
G = gnd.GetNetCode()


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def box_dist(px, py, bb):
    x0, y0, x1, y1 = TO(bb.GetLeft()), TO(bb.GetTop()), TO(bb.GetRight()), TO(bb.GetBottom())
    return math.hypot(max(x0 - px, 0, px - x1), max(y0 - py, 0, py - y1))


# obstacles: (kind, geometry, half-width, layers or None = all, net, pad object or None)
obst = []
has_stub = {}                                  # pads that already have a locked stub from an earlier run
for t in b.GetTracks():
    if t.GetClass() == "PCB_TRACK" and t.IsLocked() and t.GetNetCode() == G:
        has_stub[(round(TO(t.GetStart().x), 6), round(TO(t.GetStart().y), 6))] = True
for t in b.GetTracks():
    if t.GetClass() == "PCB_VIA":
        p = t.GetPosition()
        obst.append(("pt", (TO(p.x), TO(p.y)), TO(t.GetWidth(pcbnew.F_Cu)) / 2, None, t.GetNetCode(), None))
    else:
        s, e = t.GetStart(), t.GetEnd()
        obst.append(("seg", (TO(s.x), TO(s.y), TO(e.x), TO(e.y)), TO(t.GetWidth()) / 2, {t.GetLayer()}, t.GetNetCode(), None))
for pd in b.GetPads():
    th = pd.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
    lay = None if th else {pcbnew.F_Cu if pd.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu}
    obst.append(("box", pd.GetBoundingBox(), 0, lay, pd.GetNetCode(), pd.m_Uuid.AsString()))


def dist(o, px, py):
    kind, g, hw = o[0], o[1], o[2]
    if kind == "pt":
        return math.hypot(px - g[0], py - g[1]) - hw
    if kind == "seg":
        return seg_dist(px, py, *g) - hw
    return box_dist(px, py, g)


def via_ok(px, py, src):
    """via (all layers): clear of every other-net object, every other pad and every other GND via."""
    for o in obst:
        if o[5] == src:
            continue
        same_net = o[4] == G
        if same_net and o[0] == "seg":
            continue                       # touching a GND track is fine
        if dist(o, px, py) - VIA_D / 2 < (0.25 if o[0] == "pt" else CLR):
            return False
    return True


def stub_ok(px, py, layer, src):
    for o in obst:
        if o[5] == src or o[4] == G:
            continue
        if o[3] is not None and layer not in o[3]:
            continue
        if dist(o, px, py) - STUB_W / 2 < CLR:
            return False
    return True


refs = set(sys.argv[1:])
added = failed = 0
# fine-pitch ICs first (most pads), so passives do not take the only free spots next to their pins
for fp in sorted(b.GetFootprints(), key=lambda f: -len(f.Pads())):
    if refs and fp.GetReference() not in refs:
        continue
    for pad in fp.Pads():
        if pad.GetNetCode() != G or pad.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
            continue
        uid = pad.m_Uuid.AsString()
        c = pad.GetPosition(); cx, cy = TO(c.x), TO(c.y)
        if has_stub.get((round(cx, 6), round(cy, 6))):
            continue                                   # this pad already has its via (re-run)
        r0 = max(TO(pad.GetSize().x), TO(pad.GetSize().y)) / 2
        done = False
        for (CLR, STUB_W), d in [(p, r0 + 0.35 + 0.1 * k) for p in PASSES for k in range(14)]:
            for k in range(24):
                a = 2 * math.pi * k / 24
                vx, vy = cx + d * math.cos(a), cy + d * math.sin(a)
                if not (1 < vx < W - 1 and 1 < vy < H - 1) or not via_ok(vx, vy, uid):
                    continue
                n = max(2, int(d / 0.15))
                if not all(stub_ok(cx + (vx - cx) * i / n, cy + (vy - cy) * i / n, pad.GetLayer(), uid) for i in range(1, n)):
                    continue
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(pcbnew.VECTOR2I(MM(vx), MM(vy))); v.SetWidth(MM(VIA_D)); v.SetDrill(MM(VIA_DR))
                v.SetNet(gnd); v.SetViaType(pcbnew.VIATYPE_THROUGH); v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                v.SetLocked(True); b.Add(v)
                tr = pcbnew.PCB_TRACK(b)
                tr.SetStart(c); tr.SetEnd(pcbnew.VECTOR2I(MM(vx), MM(vy))); tr.SetWidth(MM(STUB_W))
                tr.SetLayer(pad.GetLayer()); tr.SetNet(gnd); tr.SetLocked(True); b.Add(tr)
                obst.append(("pt", (vx, vy), VIA_D / 2, None, G, None))
                obst.append(("seg", (cx, cy, vx, vy), STUB_W / 2, {pad.GetLayer()}, G, None))
                added += 1; done = True
                break
            if done:
                break
        if not done:
            failed += 1
            print(f"no via spot for {fp.GetReference()} pad {pad.GetNumber()} (left to the router)")
b.Save("braintech16.kicad_pcb")
print(f"GND vias added: {added}, left to the router: {failed}")
