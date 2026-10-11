"""Import the Freerouting result (braintech16.ses) into braintech16.kicad_pcb. Run with KiCad's Python."""
import os
import pcbnew
try:
    import wx
    _app = wx.App(False)
except Exception:
    _app = None

HERE = os.path.dirname(os.path.abspath(__file__))
pcb = os.path.join(HERE, "braintech16.kicad_pcb")
board = pcbnew.LoadBoard(pcb)
ok = pcbnew.ImportSpecctraSES(board, os.path.join(HERE, "braintech16.ses"))
print("import ok:", ok, "tracks+vias:", len(board.GetTracks()))
# Freerouting sometimes necks a track down to 0.09 mm next to a fine-pitch pad; bring those up to the
# 0.1 mm board minimum (DRC afterwards confirms clearances still hold)
MIN_W = pcbnew.FromMM(0.1)
thin = [t for t in board.GetTracks() if t.GetClass() == "PCB_TRACK" and t.GetWidth() < MIN_W]
for t in thin:
    t.SetWidth(MIN_W)
print("tracks widened to 0.1 mm:", len(thin))
board.Save(pcb)
