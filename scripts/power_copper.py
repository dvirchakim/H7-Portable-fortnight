"""Power-stage copper: thermal vias in U1's exposed pad, and power tracks widened wherever clearance allows.

  "C:\\Program Files\\KiCad\\7.0\\bin\\python.exe" scripts/power_copper.py [--dry]

1. U1 (LMR33630ADDA, HSOIC-8 PowerPAD) sheds its heat through its exposed pad: TI's layout guidance is a grid
   of vias in the pad down to the ground plane.  Up to 6 GND vias (0.2 mm drill, 0.45 mm - vias.py grows them
   to 0.50 mm where there is room) are placed in a 2 x 3 grid inside the pad, each only if it keeps clearance
   to every other net on every layer.  Small drills keep solder wicking down.
2. Each track of the high-current nets is widened to the widest of WIDTHS that keeps CLR to every other-net
   track, via and pad on its layer (pads by their exact outline), the board edge and the F.Cu keep-out rule areas.  Zone fills are left to
   the refill (they pull back by themselves).
Zones are refilled at the end.  Run post_route.sh afterwards (DRC, DFM, EMI, fab files).
"""
import os
import sys
import math
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
T, MM = pcbnew.ToMM, pcbnew.FromMM
CLR = 0.20                    # power copper keeps a little more than the 0.16 routing target
EDGE = 0.5
NETS = {'VBAT': (1.0, 0.8, 0.65), 'BUCK_SW': (1.0, 0.8, 0.65), '+5V_BUCK': (1.0, 0.8, 0.65),
        '+5V': (1.0, 0.8, 0.65, 0.5)}
PLUS5_ONLY_NEAR = (9.4, 29.6, 6.0)      # +5V tracks are signal-width elsewhere (connector feeds): only the
                                        # buck -> D2 -> C8 -> H7 section is widened (within 6 mm of D2)
VBAT_BOX = (0.0, 0.0, 8.5, 18.0)        # VBAT: only the battery pads -> C1/C2 -> C3 -> U1 path carries current;
                                        # the EN pull-up and battery-sense branches stay at 0.5 mm
INNER_MAX = 0.8                         # wider In2 tracks leave +5V-plane slivers between them (DRC copper_sliver)
VIA_D, VIA_DRILL = 0.45, 0.2
DRY = '--dry' in sys.argv

board = pcbnew.LoadBoard(PCB)
bb = board.GetBoardEdgesBoundingBox()
BX0, BY0, BX1, BY1 = T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())


def seg_dist(a, b, c, d):
    """distance between segments ab and cd"""
    def pt(p, s, e):
        dx, dy = e[0] - s[0], e[1] - s[1]
        L = dx * dx + dy * dy
        u = 0 if L == 0 else max(0, min(1, ((p[0] - s[0]) * dx + (p[1] - s[1]) * dy) / L))
        return math.hypot(p[0] - s[0] - u * dx, p[1] - s[1] - u * dy)
    def cross(p, q, r, s):
        o = lambda a_, b_, c_: (b_[0] - a_[0]) * (c_[1] - a_[1]) - (b_[1] - a_[1]) * (c_[0] - a_[0])
        return o(p, q, r) * o(p, q, s) < 0 and o(r, s, p) * o(r, s, q) < 0
    if cross(a, b, c, d):
        return 0.0
    return min(pt(a, c, d), pt(b, c, d), pt(c, a, b), pt(d, a, b))


# ---- obstacles per layer: (net, kind, geometry) with geometry = segment (a, b, half width) ----
LAYERS = {pcbnew.F_Cu: 'F', pcbnew.In1_Cu: 'In1', pcbnew.In2_Cu: 'In2', pcbnew.B_Cu: 'B'}
obst = {l: [] for l in LAYERS}
PADPOLY = {}
tracks = []
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        p = (T(t.GetPosition().x), T(t.GetPosition().y))
        for l in LAYERS:
            obst[l].append((t.GetNetname(), p, p, T(t.GetWidth()) / 2, t))
    else:
        a, b = (T(t.GetStart().x), T(t.GetStart().y)), (T(t.GetEnd().x), T(t.GetEnd().y))
        obst[t.GetLayer()].append((t.GetNetname(), a, b, T(t.GetWidth()) / 2, t))
        tracks.append(t)
for f in board.GetFootprints():
    for p in f.Pads():
        # pad as a fat segment along its long axis (good enough for rectangles / ovals / round pads)
        c = (T(p.GetPosition().x), T(p.GetPosition().y))
        bbx = p.GetBoundingBox()
        w, h = T(bbx.GetWidth()), T(bbx.GetHeight())
        r = max(w, h) / 2          # generous: the exact test is the polygon below
        r0 = min(w, h) / 2
        if w >= h:
            a, b = (c[0] - w / 2 + r0, c[1]), (c[0] + w / 2 - r0, c[1])
        else:
            a, b = (c[0], c[1] - h / 2 + r0), (c[0], c[1] + h / 2 - r0)
        if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
            layers = list(LAYERS)
        else:
            layers = [l for l in LAYERS if p.IsOnLayer(l)]
        for l in layers:
            obst[l].append((p.GetNetname(), a, b, r, p))
            PADPOLY[id(p), l] = p.GetEffectivePolygon()   # exact outline (corners!) for the final test
keepout = []                      # F.Cu rectangles (sockets, U4) and round all-layer hole keep-outs
for z in board.Zones():
    if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
        r = z.GetBoundingBox()
        keepout.append((z.GetZoneName(), T(r.GetLeft()), T(r.GetTop()), T(r.GetRight()), T(r.GetBottom()),
                        [l for l in LAYERS if z.IsOnLayer(l)]))


def in_keepout(a, b, hw, layer):
    for name, x0, y0, x1, y1, layers in keepout:
        if layer not in layers:
            continue
        if name == 'HOLE_KEEPOUT':
            c, rad = ((x0 + x1) / 2, (y0 + y1) / 2), (x1 - x0) / 2
            if seg_dist(a, b, c, c) < rad + hw:
                return True
        elif seg_dist(a, b, ((x0 + x1) / 2, (y0 + y1) / 2), ((x0 + x1) / 2, (y0 + y1) / 2)) < 0 or \
                (min(a[0], b[0]) - hw < x1 and max(a[0], b[0]) + hw > x0 and
                 min(a[1], b[1]) - hw < y1 and max(a[1], b[1]) + hw > y0):
            return True
    return False


def clear(net, a, b, hw, layer, skip=None):
    if min(a[0], b[0]) - hw < BX0 + EDGE or max(a[0], b[0]) + hw > BX1 - EDGE or \
            min(a[1], b[1]) - hw < BY0 + EDGE or max(a[1], b[1]) + hw > BY1 - EDGE:
        return False
    if in_keepout(a, b, hw, layer):
        return False
    for onet, c, d, r, item in obst[layer]:
        if item is skip or onet == net and net:
            continue
        if max(c[0], d[0]) + r + hw + CLR < min(a[0], b[0]) or min(c[0], d[0]) - r - hw - CLR > max(a[0], b[0]):
            continue
        if max(c[1], d[1]) + r + hw + CLR < min(a[1], b[1]) or min(c[1], d[1]) - r - hw - CLR > max(a[1], b[1]):
            continue
        if isinstance(item, pcbnew.PAD):
            # the fat-segment model above is only a coarse filter: rectangular pads have corners
            poly = PADPOLY.get((id(item), layer))
            if poly is not None and poly.Collide(pcbnew.SEG(pcbnew.VECTOR2I(MM(a[0]), MM(a[1])),
                                                            pcbnew.VECTOR2I(MM(b[0]), MM(b[1]))), MM(hw + CLR)):
                return False
            continue
        if seg_dist(a, b, c, d) < r + hw + CLR:
            return False
    return True


# ---- 1. thermal vias in U1's exposed pad ----
u1 = board.FindFootprintByReference('U1')
ep = [p for p in u1.Pads() if p.GetNumber() == '9'][0]
epb = ep.GetBoundingBox()
ex0, ey0, ex1, ey1 = T(epb.GetLeft()), T(epb.GetTop()), T(epb.GetRight()), T(epb.GetBottom())
cx, cy = (ex0 + ex1) / 2, (ey0 + ey1) / 2
# keep vias inside the pad's solid copper - read the pad size along each axis from its own shape
sx, sy = (ex1 - ex0), (ey1 - ey0)
px = [cx - sx / 4, cx + sx / 4] if sx < sy else [cx - sx / 3, cx, cx + sx / 3]
py = [cy - sy / 3, cy, cy + sy / 3] if sx < sy else [cy - sy / 4, cy + sy / 4]
added = []
existing = [(T(t.GetPosition().x), T(t.GetPosition().y)) for t in board.GetTracks() if t.Type() == pcbnew.PCB_VIA_T]
for x in px:
    for y in py:
        if any(math.hypot(x - ex, y - ey) < 0.6 for ex, ey in existing):
            continue
        ok = all(clear('GND', (x, y), (x, y), VIA_D / 2, l) for l in LAYERS)
        if ok:
            added.append((x, y))
            if not DRY:
                v = pcbnew.PCB_VIA(board)
                v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
                v.SetWidth(MM(VIA_D))
                v.SetDrill(MM(VIA_DRILL))
                v.SetNet(board.FindNet('GND'))
                board.Add(v)
            for l in LAYERS:
                obst[l].append(('GND', (x, y), (x, y), VIA_D / 2, None))
print('U1 exposed pad %.2f x %.2f mm: %d thermal vias added %s' % (sx, sy, len(added),
                                                                 [(round(x, 2), round(y, 2)) for x, y in added]))

# ---- 2. widen power tracks ----
summary = {}
for t in tracks:
    net = t.GetNetname()
    if net not in NETS:
        continue
    a, b = (T(t.GetStart().x), T(t.GetStart().y)), (T(t.GetEnd().x), T(t.GetEnd().y))
    if net == '+5V':
        nx, ny, nr = PLUS5_ONLY_NEAR
        if seg_dist(a, b, (nx, ny), (nx, ny)) > nr:
            continue
    if net == 'VBAT':
        x0, y0, x1, y1 = VBAT_BOX
        if not all(x0 <= p[0] <= x1 and y0 <= p[1] <= y1 for p in (a, b)):
            continue
    old = T(t.GetWidth())
    new = old
    for w in NETS[net]:
        if t.GetLayer() in (pcbnew.In1_Cu, pcbnew.In2_Cu) and w > INNER_MAX:
            continue
        if w <= old:
            break
        if clear(net, a, b, w / 2, t.GetLayer(), skip=t):
            new = w
            break
    s = summary.setdefault((net, t.GetLayerName()), [0, 0.0, 0.0, 0.0])
    s[0] += 1
    s[1] += T(t.GetLength())
    if new > old:
        s[2] += T(t.GetLength())
        if not DRY:
            t.SetWidth(MM(new))
        # update this track's own obstacle entry so later tracks see the new width
        for i, o in enumerate(obst[t.GetLayer()]):
            if o[4] is t:
                obst[t.GetLayer()][i] = (o[0], o[1], o[2], new / 2, t)
    s[3] += T(t.GetLength()) * max(new, old)
for (net, layer), (n, L, Lw, area) in sorted(summary.items()):
    print('%-9s %-6s %3d segments %5.1f mm, widened %5.1f mm, mean width now %.2f mm' % (
        net, layer, n, L, Lw, area / L if L else 0))

if not DRY:
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    print('saved')
