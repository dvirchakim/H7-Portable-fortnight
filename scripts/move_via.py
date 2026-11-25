"""Move vias and drag the track ends attached to them:  python move_via.py NET:x:y:newx:newy ..."""
import os
import sys
import math
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
T, MM = pcbnew.ToMM, pcbnew.FromMM
board = pcbnew.LoadBoard(PCB)
items = list(board.GetTracks())
for arg in sys.argv[1:]:
    net, x, y, nx, ny = arg.split(':')
    x, y, nx, ny = float(x), float(y), float(nx), float(ny)
    via = next(t for t in items if t.Type() == pcbnew.PCB_VIA_T and t.GetNetname() == net
               and math.hypot(T(t.GetPosition().x) - x, T(t.GetPosition().y) - y) < 0.02)
    new = pcbnew.VECTOR2I(MM(nx), MM(ny))
    n = 0
    for t in items:
        if t.Type() == pcbnew.PCB_VIA_T or t.GetNetname() != net:
            continue
        if math.hypot(T(t.GetStart().x) - x, T(t.GetStart().y) - y) < 0.02:
            t.SetStart(new); n += 1
        if math.hypot(T(t.GetEnd().x) - x, T(t.GetEnd().y) - y) < 0.02:
            t.SetEnd(new); n += 1
    via.SetPosition(new)
    print('via %s (%.2f,%.2f) -> (%.2f,%.2f), %d track ends dragged' % (net, x, y, nx, ny, n))
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
board = pcbnew.LoadBoard(PCB)
pcbnew.WriteDRCReport(board, os.path.join(ROOT, 'out', 'drc.rpt'), pcbnew.EDA_UNITS_MILLIMETRES, True)
