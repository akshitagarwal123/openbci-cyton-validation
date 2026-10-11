"""Set net classes and export Specctra DSN for Freerouting. Run with KiCad's Python on the unrouted board.

Default: 0.15 mm tracks / 0.15 mm clearance / 0.45 mm vias (0.2 mm drill) - fits between 0.5 mm-pitch TQFP pins.
Power:   0.3 mm tracks for supply rails. GND is NOT routed as tracks: it connects by vias to the In1.Cu plane.
All values are within standard 4-layer fab capability (JLCPCB: 0.09 mm track/space, 0.2 mm drill).
"""
import pcbnew, wx
app = wx.App(False)
MM = pcbnew.FromMM
b = pcbnew.LoadBoard("braintech16.kicad_pcb")
b.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)      # In1 = solid GND plane, no tracks
ds = b.GetDesignSettings()
ds.m_TrackMinWidth = MM(0.1)
ds.m_ViasMinSize = MM(0.45)
ds.m_MinThroughDrill = MM(0.2)
ns = ds.m_NetSettings
dflt = ns.GetDefaultNetclass()
dflt.SetTrackWidth(MM(0.15)); dflt.SetClearance(MM(0.15)); dflt.SetViaDiameter(MM(0.45)); dflt.SetViaDrill(MM(0.2))
pwr = pcbnew.NETCLASS("Power")
pwr.SetTrackWidth(MM(0.3)); pwr.SetClearance(MM(0.15)); pwr.SetViaDiameter(MM(0.6)); pwr.SetViaDrill(MM(0.3))
try:
    ns.SetNetclass("Power", pwr)
except Exception:
    ns.GetNetclasses()["Power"] = pwr
for n in ["VBUS", "VBAT", "VSYS", "3V3", "SW_3V3", "AVDD", "AVSS", "NEG3V3"]:
    ns.SetNetclassPatternAssignment(n, "Power")
b.SynchronizeNetsAndNetClasses(True)
b.Save("braintech16.kicad_pcb")
ok = pcbnew.ExportSpecctraDSN(b, "braintech16.dsn")
print("DSN export:", ok)
