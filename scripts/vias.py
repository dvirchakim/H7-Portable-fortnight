"""Via clean-up for JLCDFM (run after routing / patching, before finish.py):

  1. a via closer than 0.15 mm to a pad of its own net is nudged straight away from that pad
  2. every 0.45 mm via is grown to 0.50 mm (annular ring 0.15 mm) wherever it then still keeps
     0.15 mm to all other-net copper on every layer
"""
import os
import sys
import math
import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dfm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
T, MM = pcbnew.ToMM, pcbnew.FromMM
board = pcbnew.LoadBoard(PCB)
items, holes, rings = dfm.load(board)
vias = [t for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
tracks = [t for t in board.GetTracks() if t.Type() != pcbnew.PCB_VIA_T]


POWER = ('VBAT', '+5V_BUCK', 'BUCK_SW')


def min_gap(c, r, net, grow=False):
    """smallest gap from a via (centre c, radius r) to other-net copper on any layer"""
    probe = dfm.Item('v', net, 0, 'probe', c=c, r=r)
    m = 9.0
    for li in range(4):
        for it in items[li]:
            same = it.net == net and net != ''
            if same and not (grow and it.kind == 'v' and math.hypot(it.c[0] - c[0], it.c[1] - c[1]) > 0.01):
                continue                                   # own net: only neighbouring vias matter, when growing
            if it.box[0] - 0.3 > probe.box[2] or probe.box[0] - 0.3 > it.box[2] or it.box[1] - 0.3 > probe.box[3] or probe.box[1] - 0.3 > it.box[3]:
                continue
            g = dfm.gap(probe, it)
            if same and g < 0.004:
                continue                                   # overlapping vias of one net are one piece of copper
            if it.net in POWER or net in POWER:
                g -= 0.06                                  # the Power net class needs 0.2 mm
            m = min(m, g)
    return m


for v in vias:                                             # Rail-class vias came out as 0.45 / 0.25: ring only 0.10
    if abs(T(v.GetDrill()) - 0.25) < 0.001:
        v.SetDrill(MM(0.2))
moved = 0
for v in vias:
    c = (T(v.GetPosition().x), T(v.GetPosition().y))
    r = T(v.GetWidth()) / 2
    net = v.GetNetname()
    for li in (0, 3):
        for it in items[li]:
            if it.kind != 'p' or it.net != net:
                continue
            g = dfm.seg_rect(c, c, it.rect) - r
            if not (0.004 < g < 0.15):
                continue
            pc = ((it.rect[0] + it.rect[2]) / 2, (it.rect[1] + it.rect[3]) / 2)
            L = math.hypot(c[0] - pc[0], c[1] - pc[1])
            for step in (0.10, 0.14, 0.18):
                n = (round(c[0] + (c[0] - pc[0]) / L * step, 3), round(c[1] + (c[1] - pc[1]) / L * step, 3))
                if dfm.seg_rect(n, n, it.rect) - r >= 0.15 and min_gap(n, r, net) >= 0.135:
                    for t in tracks:                       # drag the track ends that sit on the via
                        if t.GetNetname() != net:
                            continue
                        if math.hypot(T(t.GetStart().x) - c[0], T(t.GetStart().y) - c[1]) < 0.01:
                            t.SetStart(pcbnew.VECTOR2I(MM(n[0]), MM(n[1])))
                        if math.hypot(T(t.GetEnd().x) - c[0], T(t.GetEnd().y) - c[1]) < 0.01:
                            t.SetEnd(pcbnew.VECTOR2I(MM(n[0]), MM(n[1])))
                    v.SetPosition(pcbnew.VECTOR2I(MM(n[0]), MM(n[1])))
                    for l2 in range(4):
                        for o in items[l2]:
                            if o.kind == 'v' and o.c == c and o.net == net:
                                o.c = n
                                o.box = (n[0] - r, n[1] - r, n[0] + r, n[1] + r)
                    print('via %s (%.2f,%.2f) moved %.2f mm away from %s' % (net, c[0], c[1], step, it.name))
                    c = n
                    moved += 1
                    break
def resize(v, c, d):
    v.SetWidth(MM(d))
    for l2 in range(4):
        for o in items[l2]:
            if o.kind == 'v' and math.hypot(o.c[0] - c[0], o.c[1] - c[1]) < 0.001:
                o.r = d / 2
                o.box = (c[0] - d / 2, c[1] - d / 2, c[0] + d / 2, c[1] + d / 2)


grown = 0
for v in vias:                                             # safe to re-run: re-check vias grown earlier
    c = (T(v.GetPosition().x), T(v.GetPosition().y))
    if abs(T(v.GetWidth()) - 0.5) < 0.001 and min_gap(c, 0.25, v.GetNetname(), True) < 0.15:
        resize(v, c, 0.45)
for v in vias:
    c = (T(v.GetPosition().x), T(v.GetPosition().y))
    if abs(T(v.GetWidth()) - 0.45) < 0.001 and min_gap(c, 0.25, v.GetNetname(), True) >= 0.15:
        resize(v, c, 0.5)
grown = sum(1 for v in vias if abs(T(v.GetWidth()) - 0.5) < 0.001)
print('vias moved:', moved, ' grown to 0.50 mm:', grown, 'of', len(vias))
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
board = pcbnew.LoadBoard(PCB)
pcbnew.WriteDRCReport(board, os.path.join(ROOT, 'out', 'drc.rpt'), pcbnew.EDA_UNITS_MILLIMETRES, True)
