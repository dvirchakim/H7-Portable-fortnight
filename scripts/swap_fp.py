"""Swap a placed footprint for another one on the routed board.

  python swap_fp.py REF LIB:FOOTPRINT ROT [X Y]

Keeps the position (or moves to X, Y) and side, gives the new pads the nets design.py lists for REF,
removes every track/via that now overlaps the new footprint (pads + 0.2 mm) or was attached to the old
pads, and prints the nets that need reconnecting.  Follow with: patch.py prune, leftovers.py, patch.py.
"""
import os
import sys
import math
import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
STD = r'C:\Program Files\KiCad\7.0\share\kicad\footprints'
T, MM = pcbnew.ToMM, pcbnew.FromMM
ref, fpid, rot = sys.argv[1], sys.argv[2], float(sys.argv[3])
part = next(p for p in D.PARTS if p['ref'] == ref)

board = pcbnew.LoadBoard(PCB)
old = board.FindFootprintByReference(ref)
pos = old.GetPosition() if len(sys.argv) < 6 else pcbnew.VECTOR2I(MM(float(sys.argv[4])), MM(float(sys.argv[5])))
bottom = old.GetLayer() == pcbnew.B_Cu
old_pads = [(p.GetNetname(), p.GetBoundingBox()) for p in old.Pads()]
lib, name = fpid.split(':')
new = pcbnew.FootprintLoad(os.path.join(ROOT, 'fc.pretty') if lib == 'fc' else os.path.join(STD, lib + '.pretty'), name)
new.SetFPID(pcbnew.LIB_ID(lib, name))
new.SetReference(ref)
new.SetValue(part['value'])
new.SetPosition(pos)
new.SetOrientationDegrees(rot)
new.SetPath(old.GetPath())          # keep the link to the schematic symbol (else Update PCB adds a duplicate)
board.Add(new)
if bottom:
    new.Flip(pos, False)
for p in new.Pads():
    n = part['nets'].get(p.GetNumber())
    if n:
        p.SetNet(board.FindNet(n))
    else:
        p.SetNetCode(0)
cu = pcbnew.F_Cu if not bottom else pcbnew.B_Cu
keep = []
for p in new.Pads():
    r = p.GetBoundingBox()
    keep.append((p.GetNetname(), T(r.GetLeft()) - 0.2, T(r.GetTop()) - 0.2, T(r.GetRight()) + 0.2, T(r.GetBottom()) + 0.2))


def seg_hits_rect(a, b, w, r):
    """track a-b of width w against rectangle r (sampled)"""
    n = max(2, int(math.hypot(b[0] - a[0], b[1] - a[1]) / 0.05))
    for i in range(n + 1):
        x = a[0] + (b[0] - a[0]) * i / n
        y = a[1] + (b[1] - a[1]) * i / n
        if r[0] - w / 2 < x < r[2] + w / 2 and r[1] - w / 2 < y < r[3] + w / 2:
            return True
    return False


rip, nets = [], set()
for t in board.GetTracks():
    net = t.GetNetname()
    if t.Type() == pcbnew.PCB_VIA_T:
        c = (T(t.GetPosition().x), T(t.GetPosition().y))
        hit = any(k[0] != net and k[1] - 0.25 < c[0] < k[3] + 0.25 and k[2] - 0.25 < c[1] < k[4] + 0.25 for k in keep)
    else:
        if t.GetLayer() != cu:
            continue
        a = (T(t.GetStart().x), T(t.GetStart().y))
        b = (T(t.GetEnd().x), T(t.GetEnd().y))
        w = T(t.GetWidth())
        hit = any(k[0] != net and seg_hits_rect(a, b, w, k[1:]) for k in keep)
        # tracks that ended on one of the old pads now lead nowhere
        hit = hit or any(seg_hits_rect(a, b, 0, (T(r.GetLeft()), T(r.GetTop()), T(r.GetRight()), T(r.GetBottom())))
                         for _, r in old_pads)
    if hit:
        rip.append(t)
        nets.add(net)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
for t in rip:
    board.Remove(t)
board.Remove(old)
pcbnew.SaveBoard(PCB, board)
print('%s -> %s at rot %g; removed %d tracks/vias; nets to reconnect: %s' % (ref, fpid, rot, len(rip), ', '.join(sorted(nets))))
