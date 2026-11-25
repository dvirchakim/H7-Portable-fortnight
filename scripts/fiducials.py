"""Three global fiducials per side (1 mm copper dot, 2 mm mask opening), as assembly houses ask for on
boards with 0.4-0.5 mm pitch parts.  Spots are chosen automatically: at least FREE mm from every pad,
track, via and hole on that side, 2.5 mm inside the edge, spread as far apart as possible (largest
triangle).  Safe to re-run: existing FID* footprints are removed first.

  "C:\\Program Files\\KiCad\\7.0\\bin\\python.exe" scripts/fiducials.py      (run before finish.py)
"""
import os
import sys
import math
import itertools
import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dfm

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
LIB = r'C:\Program Files\KiCad\7.0\share\kicad\footprints\Fiducial.pretty'
NAME = 'Fiducial_1mm_Mask2mm'
T, MM = pcbnew.ToMM, pcbnew.FromMM
FREE = 1.5                      # copper dot radius 0.5 + 1.0 mm clear ring (= mask opening + margin)

board = pcbnew.LoadBoard(PCB)
old = [fp for fp in board.GetFootprints() if fp.GetReference().startswith('FID')]
bb = board.GetBoardEdgesBoundingBox()
BX0, BY0, BX1, BY1 = T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())
items, holes, _ = dfm.load(board)
bodies = {0: [], 3: []}
for fp in board.GetFootprints():
    if fp.GetReference().startswith('FID'):
        continue
    r = fp.GetBoundingBox(False, False)
    bodies[0 if fp.GetLayer() == pcbnew.F_Cu else 3].append((T(r.GetLeft()), T(r.GetTop()), T(r.GetRight()), T(r.GetBottom())))
for d in board.GetDrawings():                  # board-level silk text (USB, labels): the 2 mm mask opening would clip it
    if d.GetLayer() in (pcbnew.F_SilkS, pcbnew.B_SilkS) and d.Type() in (pcbnew.PCB_TEXT_T, pcbnew.PCB_TEXTBOX_T):
        r = d.GetBoundingBox()
        bodies[0 if d.GetLayer() == pcbnew.F_SilkS else 3].append((T(r.GetLeft()), T(r.GetTop()), T(r.GetRight()), T(r.GetBottom())))


def free(li, x, y):
    if not (BX0 + 2.5 <= x <= BX1 - 2.5 and BY0 + 2.5 <= y <= BY1 - 2.5):
        return False
    probe = dfm.Item('v', '', li, 'fid', c=(x, y), r=0.5)
    for it in items[li]:
        if it.fp_old if hasattr(it, 'fp_old') else False:
            continue
        if it.box[0] - FREE > x or x > it.box[2] + FREE or it.box[1] - FREE > y or y > it.box[3] + FREE:
            continue
        if dfm.gap(probe, it) < FREE - 0.5:
            return False
    for (hx, hy), hr, _ in holes:
        if math.hypot(x - hx, y - hy) < hr + FREE + 0.3:
            return False
    for r in bodies[li]:                       # 1.4 mm: the fiducial's own 1.25 mm courtyard + margin
        if r[0] - 1.4 < x < r[2] + 1.4 and r[1] - 1.4 < y < r[3] + 1.4:
            return False
    return True


new = []
for li, side in ((0, pcbnew.F_Cu), (3, pcbnew.B_Cu)):
    cands = []
    y = BY0 + 2.5
    while y <= BY1 - 2.5:
        x = BX0 + 2.5
        while x <= BX1 - 2.5:
            if free(li, x, y):
                cands.append((round(x, 2), round(y, 2)))
            x += 0.25
        y += 0.25
    if len(cands) < 3:
        print('side %s: only %d free fiducial spots' % ('top' if li == 0 else 'bottom', len(cands)))
        continue
    # thin the candidates, then pick the largest triangle (asymmetric by construction is checked below)
    pool = cands[::max(1, len(cands) // 400)]
    best = None
    for a, b, c in itertools.combinations(pool, 3):
        area = abs((b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])) / 2
        if best is None or area > best[0]:
            best = (area, (a, b, c))
    print('%s fiducials at %s (triangle %.0f mm2, %d free spots)' % ('top' if li == 0 else 'bottom', best[1], best[0], len(cands)))
    for p in best[1]:
        new.append((side, p))

n = 1
for side, (x, y) in new:
    fp = pcbnew.FootprintLoad(LIB, NAME)
    fp.SetFPID(pcbnew.LIB_ID('Fiducial', NAME))
    fp.SetReference('FID%d' % n)
    fp.SetValue('Fiducial')
    fp.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    board.Add(fp)
    if side == pcbnew.B_Cu:
        fp.Flip(fp.GetPosition(), False)
    for p in fp.Pads():
        p.SetLocalClearance(MM(1.0))          # keeps pours 1 mm away: a clean ring for the camera
    fp.Reference().SetVisible(False)
    fp.Value().SetVisible(False)
    n += 1
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
for fp in old:
    board.Remove(fp)
pcbnew.SaveBoard(PCB, board)
board = pcbnew.LoadBoard(PCB)
pcbnew.WriteDRCReport(board, os.path.join(ROOT, 'out', 'drc.rpt'), pcbnew.EDA_UNITS_MILLIMETRES, True)
