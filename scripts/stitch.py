"""Tie GND / +5V pads down to their inner planes after autorouting.

Freerouting leaves plane nets unconnected when the plane layer is excluded from signal
routing.  For every group of same-net pads/tracks that has no via yet, this adds one via
plus a short stub, checking clearance against all other-net copper on every layer.

  python stitch.py            (then zones are refilled and DRC re-run)
"""
import os
import sys
import math
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
PLANE_NETS = ('GND', '+5V')
NARROW = 'narrow' in sys.argv          # last-resort pass: 0.127 mm stubs at minimum clearance
CLR = 0.165 if NARROW else 0.18        # mm, a little over the 0.16 rule (JLCDFM warns below 0.15)
EDGE = 0.5
VIA_D, VIA_DRILL = 0.5, 0.2
T = pcbnew.ToMM


def pt_seg(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    return math.hypot(px - ax - t * dx, py - ay - t * dy)


def seg_seg(a, b, c, d):
    def ccw(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    if a != b and c != d:
        if ccw(a, b, c) * ccw(a, b, d) < 0 and ccw(c, d, a) * ccw(c, d, b) < 0:
            return 0.0
    return min(pt_seg(a, c, d), pt_seg(b, c, d), pt_seg(c, a, b), pt_seg(d, a, b))


def seg_rect(a, b, r):
    x0, y0, x1, y1 = r
    for p in (a, b):
        if x0 <= p[0] <= x1 and y0 <= p[1] <= y1:
            return 0.0
    cs = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    return min(seg_seg(a, b, cs[i], cs[(i + 1) % 4]) for i in range(4))


board = pcbnew.LoadBoard(PCB)
bb = board.GetBoardEdgesBoundingBox()
BX0, BY0, BX1, BY1 = T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]

pads = []      # (net, layer, rect, centre, ref)
for fp in board.GetFootprints():
    for pad in fp.Pads():
        r = pad.GetBoundingBox()
        rect = (T(r.GetLeft()), T(r.GetTop()), T(r.GetRight()), T(r.GetBottom()))
        c = (T(pad.GetPosition().x), T(pad.GetPosition().y))
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
            for l in CU:
                pads.append(('<hole>', l, rect, c, fp.GetReference()))
            continue
        for l in CU:
            if pad.IsOnLayer(l):
                pads.append((pad.GetNetname(), l, rect, c, fp.GetReference() + '-' + pad.GetNumber()))
tracks = []    # (net, layer, a, b, halfwidth)
vias = []      # (net, centre, radius)
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        vias.append((t.GetNetname(), (T(t.GetPosition().x), T(t.GetPosition().y)), T(t.GetWidth()) / 2))
    else:
        tracks.append((t.GetNetname(), t.GetLayer(), (T(t.GetStart().x), T(t.GetStart().y)),
                       (T(t.GetEnd().x), T(t.GetEnd().y)), T(t.GetWidth()) / 2))
keepouts = []  # (centre, radius) from HOLE_KEEPOUT rule areas
sock_rects = []
for i in range(board.GetAreaCount()):
    z = board.GetArea(i)
    if z.GetIsRuleArea():
        r = z.GetBoundingBox()
        if z.GetZoneName() == 'SOCKET_KEEPOUT':      # F.Cu only: no tracks, no vias under the DF40 body
            sock_rects.append((T(r.GetLeft()), T(r.GetTop()), T(r.GetRight()), T(r.GetBottom())))
        else:
            keepouts.append(((T(r.GetCenter().x), T(r.GetCenter().y)), T(r.GetWidth()) / 2))


def via_ok(net, c):
    if not (BX0 + EDGE <= c[0] <= BX1 - EDGE and BY0 + EDGE <= c[1] <= BY1 - EDGE):
        return False
    R = VIA_D / 2
    for kc, kr in keepouts:
        if math.hypot(c[0] - kc[0], c[1] - kc[1]) < kr + R + 0.1:
            return False
    for sr in sock_rects:
        if seg_rect(c, c, sr) < R + 0.05:
            return False
    for n, vc, vr in vias:
        d = math.hypot(c[0] - vc[0], c[1] - vc[1])
        if d < (vr + R + (CLR if n != net else 0.16)):
            return False
    for n, l, rect, _, _ in pads:
        if l in (pcbnew.F_Cu, pcbnew.B_Cu) and seg_rect(c, c, rect) < R + (CLR if n != net else 0.16):
            return False                     # also keeps vias out of same-net pads (no via-in-pad)
    for n, l, a, b, hw in tracks:
        if n != net and pt_seg(c, a, b) < R + hw + CLR:
            return False
    return True


def stub_ok(net, layer, a, b, hw):
    if layer == pcbnew.F_Cu:
        for sr in sock_rects:
            if seg_rect(a, b, sr) < hw + 0.02:
                return False
    for n, l, rect, _, _ in pads:
        if l == layer and n != net and seg_rect(a, b, rect) < hw + CLR:
            return False
    for n, l, ta, tb, thw in tracks:
        if l == layer and n != net and seg_seg(a, b, ta, tb) < hw + thw + CLR:
            return False
    for n, vc, vr in vias:
        if n != net and pt_seg(vc, a, b) < hw + vr + CLR:
            return False
    return True


def maze(net, layer, start, hw, step=0.05, R=5.0, goal=None):
    """Breadth-first search on a fine grid from a pad to the nearest legal via position."""
    from collections import deque
    lp = [x for x in pads if x[0] != net and x[1] == layer and seg_rect(start, start, x[2]) < R * 1.45 + 1]
    lt = [x for x in tracks if x[0] != net and x[1] == layer and pt_seg(start, x[2], x[3]) < R * 1.45 + 1]
    lv = [x for x in vias if x[0] != net and math.hypot(x[1][0] - start[0], x[1][1] - start[1]) < R * 1.45 + 1]   # the search area is a square

    def free(p):
        if not (BX0 + EDGE <= p[0] <= BX1 - EDGE and BY0 + EDGE <= p[1] <= BY1 - EDGE):
            return False
        for kc, kr in keepouts:
            if math.hypot(p[0] - kc[0], p[1] - kc[1]) < kr + hw:
                return False
        if layer == pcbnew.F_Cu:
            for sr in sock_rects:
                if seg_rect(p, p, sr) < hw + 0.02:
                    return False
        for x in lp:
            if seg_rect(p, p, x[2]) < hw + CLR:
                return False
        for x in lt:
            if pt_seg(p, x[2], x[3]) < hw + x[4] + CLR:
                return False
        for x in lv:
            if math.hypot(p[0] - x[1][0], p[1] - x[1][1]) < hw + x[2] + CLR:
                return False
        return True
    n = int(R / step)
    prev = {(0, 0): None}
    q = deque([(0, 0)])
    while q:
        cur = q.popleft()
        p = (round(start[0] + cur[0] * step, 3), round(start[1] + cur[1] * step, 3))
        if cur[0] ** 2 + cur[1] ** 2 >= (0.5 / step) ** 2 and via_ok(net, p) and (goal is None or goal(p)):
            cells = []
            while cur is not None:
                cells.append(cur)
                cur = prev[cur]
            cells.reverse()
            pts = [cells[0]]
            for i in range(1, len(cells) - 1):      # drop collinear points
                d1 = (cells[i][0] - cells[i - 1][0], cells[i][1] - cells[i - 1][1])
                d2 = (cells[i + 1][0] - cells[i][0], cells[i + 1][1] - cells[i][1])
                if d1 != d2:
                    pts.append(cells[i])
            pts.append(cells[-1])
            return [(round(start[0] + x * step, 3), round(start[1] + y * step, 3)) for x, y in pts]
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)):
            nx = (cur[0] + dx, cur[1] + dy)
            if nx in prev or abs(nx[0]) > n or abs(nx[1]) > n:
                continue
            if free((start[0] + nx[0] * step, start[1] + nx[1] * step)):
                prev[nx] = cur
                q.append(nx)
    return None


added, failed = 0, []
for net in PLANE_NETS:
    ni = board.FindNet(net)
    npads = [p for p in pads if p[0] == net]
    # union-find over pads of this net joined by same-net tracks; groups with a via are done
    parent = list(range(len(npads)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    ntr = [t for t in tracks if t[0] == net]
    # track connectivity: flood from each pad along touching tracks
    touch = {}
    for ti, (n, l, a, b, hw) in enumerate(ntr):
        for pi, p in enumerate(npads):
            if p[1] == l and seg_rect(a, b, p[2]) <= hw:
                touch.setdefault(ti, set()).add(pi)
    tpar = list(range(len(ntr)))

    def tfind(i):
        while tpar[i] != i:
            tpar[i] = tpar[tpar[i]]
            i = tpar[i]
        return i
    for i in range(len(ntr)):
        for j in range(i + 1, len(ntr)):
            if ntr[i][1] == ntr[j][1] and seg_seg(ntr[i][2], ntr[i][3], ntr[j][2], ntr[j][3]) <= ntr[i][4] + ntr[j][4]:
                tpar[tfind(i)] = tfind(j)
    tgroup_pads, tgroup_via = {}, set()
    for ti in range(len(ntr)):
        g = tfind(ti)
        tgroup_pads.setdefault(g, set()).update(touch.get(ti, ()))
        for n, vc, vr in vias:
            if n == net and pt_seg(vc, ntr[ti][2], ntr[ti][3]) <= vr + ntr[ti][4]:
                tgroup_via.add(g)
    has_via = set()
    for g, ps in tgroup_pads.items():
        ps = sorted(ps)
        for p in ps[1:]:
            parent[find(p)] = find(ps[0])
    for g, ps in tgroup_pads.items():
        if g in tgroup_via and ps:
            has_via.add(find(sorted(ps)[0]))
    has_via = {find(i) for i in has_via}
    groups = {}
    for i in range(len(npads)):
        groups.setdefault(find(i), []).append(i)
    for g, members in groups.items():
        if g in has_via:
            continue
        done = False
        for d in (0.55, 0.7, 0.9, 1.1, 1.4, 1.8, 2.3, 3.0):
            for pi in members:
                _, layer, rect, c, ref = npads[pi]
                small = min(rect[2] - rect[0], rect[3] - rect[1])
                hw = min(0.25, max(0.15, small - 0.02)) / 2
                # start beyond the pad edge so short candidates still clear the pad
                reach = max(rect[2] - rect[0], rect[3] - rect[1]) / 2
                for k in range(24):
                    ang = 2 * math.pi * k / 24
                    v = (round(c[0] + (reach + d) * math.cos(ang), 3), round(c[1] + (reach + d) * math.sin(ang), 3))
                    if via_ok(net, v) and stub_ok(net, layer, c, v, hw):
                        tr = pcbnew.PCB_TRACK(board)
                        tr.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(c[0]), pcbnew.FromMM(c[1])))
                        tr.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(v[0]), pcbnew.FromMM(v[1])))
                        tr.SetWidth(pcbnew.FromMM(hw * 2)); tr.SetLayer(layer); tr.SetNet(ni)
                        board.Add(tr)
                        via = pcbnew.PCB_VIA(board)
                        via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(v[0]), pcbnew.FromMM(v[1])))
                        via.SetWidth(pcbnew.FromMM(VIA_D)); via.SetDrill(pcbnew.FromMM(VIA_DRILL))
                        via.SetViaType(pcbnew.VIATYPE_THROUGH); via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                        via.SetNet(ni)
                        board.Add(via)
                        vias.append((net, v, VIA_D / 2))
                        tracks.append((net, layer, c, v, hw))
                        added += 1
                        done = True
                        break
                if done:
                    break
            if done:
                break
        if not done:
            for pi in members:
                _, layer, rect, c, ref = npads[pi]
                small = min(rect[2] - rect[0], rect[3] - rect[1])
                hw = 0.075 if NARROW else min(0.2, max(0.15, small - 0.02)) / 2
                path = maze(net, layer, c, hw, R=7.0 if NARROW else 5.0)
                if path:
                    for a, b in zip(path, path[1:]):
                        tr = pcbnew.PCB_TRACK(board)
                        tr.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]), pcbnew.FromMM(a[1])))
                        tr.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(b[0]), pcbnew.FromMM(b[1])))
                        tr.SetWidth(pcbnew.FromMM(hw * 2)); tr.SetLayer(layer); tr.SetNet(ni)
                        board.Add(tr)
                        tracks.append((net, layer, a, b, hw))
                    v = path[-1]
                    via = pcbnew.PCB_VIA(board)
                    via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(v[0]), pcbnew.FromMM(v[1])))
                    via.SetWidth(pcbnew.FromMM(VIA_D)); via.SetDrill(pcbnew.FromMM(VIA_DRILL))
                    via.SetViaType(pcbnew.VIATYPE_THROUGH); via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                    via.SetNet(ni)
                    board.Add(via)
                    vias.append((net, v, VIA_D / 2))
                    added += 1
                    done = True
                    break
        if not done:
            failed.append((net, [npads[i][4] for i in members]))

# The +5V plane on In2 is cut into islands by signals routed on that layer; a +5V pour on the
# bottom layer ties the islands back together through the +5V vias.
for zname, zlayer in (() if 'nopour' in sys.argv else (('+5V_POUR_B', pcbnew.B_Cu), ('+5V_POUR_F', pcbnew.F_Cu))):
    if any(board.GetArea(i).GetZoneName() == zname for i in range(board.GetAreaCount())):
        continue
    z = pcbnew.ZONE(board)
    z.SetLayer(zlayer)
    z.SetNetCode(board.FindNet('+5V').GetNetCode())
    z.SetZoneName(zname)
    z.SetLocalClearance(pcbnew.FromMM(0.25))
    z.SetMinThickness(pcbnew.FromMM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)   # no floating +5V copper
    ol = z.Outline()
    ol.NewOutline()
    for x, y in [(BX0 + 0.3, BY0 + 0.3), (BX1 - 0.3, BY0 + 0.3), (BX1 - 0.3, BY1 - 0.3), (BX0 + 0.3, BY1 - 0.3)]:
        ol.Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    board.Add(z)

def add_path(net, layer, path, hw):
    ni = board.FindNet(net)
    for a, b in zip(path, path[1:]):
        tr = pcbnew.PCB_TRACK(board)
        tr.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]), pcbnew.FromMM(a[1])))
        tr.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(b[0]), pcbnew.FromMM(b[1])))
        tr.SetWidth(pcbnew.FromMM(hw * 2)); tr.SetLayer(layer); tr.SetNet(ni)
        board.Add(tr)
        tracks.append((net, layer, a, b, hw))
    v = path[-1]
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(v[0]), pcbnew.FromMM(v[1])))
    via.SetWidth(pcbnew.FromMM(VIA_D)); via.SetDrill(pcbnew.FromMM(VIA_DRILL))
    via.SetViaType(pcbnew.VIATYPE_THROUGH); via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    via.SetNet(ni)
    board.Add(via)
    vias.append((net, v, VIA_D / 2))


# rule areas were created on every copper layer id; restrict them to the 4 real ones
for i in range(board.GetAreaCount()):
    z = board.GetArea(i)
    if z.GetIsRuleArea() and z.GetZoneName() != 'SOCKET_KEEPOUT':
        ls = pcbnew.LSET()
        for l in CU:
            ls.AddLayer(l)
        z.SetLayerSet(ls)

# Bridge every minor island of the In2 +5V plane to the main island
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
for i in range(board.GetAreaCount()):
    z = board.GetArea(i)
    if z.GetIsRuleArea() or z.GetNetname() != '+5V' or not z.IsOnLayer(pcbnew.In2_Cu):
        continue
    polys = z.GetFilledPolysList(pcbnew.In2_Cu)
    n = polys.OutlineCount()
    areas = [abs(polys.Outline(k).Area()) for k in range(n)]
    main = areas.index(max(areas))

    def island_of(p):
        v = pcbnew.VECTOR2I(pcbnew.FromMM(p[0]), pcbnew.FromMM(p[1]))
        for k in range(n):
            if polys.Outline(k).PointInside(v):
                return k
        return None

    def in_main(p):
        return all(island_of((p[0] + dx, p[1] + dy)) == main
                   for dx, dy in ((0, 0), (0.5, 0), (-0.5, 0), (0, 0.5), (0, -0.5)))
    for k in range(n):
        if k == main:
            continue
        vstarts = [v[1] for v in vias if v[0] == '+5V' and island_of(v[1]) == k]
        starts = [(st, l) for st in vstarts for l in (pcbnew.B_Cu, pcbnew.F_Cu)]
        # pads hanging off this island (within 4 mm of one of its vias) are valid starts too
        starts += [(pp[3], pp[1]) for pp in pads if pp[0] == '+5V' and pp[1] in (pcbnew.B_Cu, pcbnew.F_Cu)
                   and any(math.hypot(pp[3][0] - v[0], pp[3][1] - v[1]) < 4 for v in vstarts)]
        ok = False
        for st, layer in starts:
            for _ in (0,):
                path = maze('+5V', layer, st, 0.125, R=12.0, goal=in_main)
                if path:
                    add_path('+5V', layer, path, 0.125)
                    added += 1
                    ok = True
                    break
            if ok:
                break
        print('In2 +5V island %d (%.0f mm2): %s' % (k, areas[k] / 1e12, 'bridged' if ok else 'NOT bridged'))

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
board = pcbnew.LoadBoard(PCB)
pcbnew.WriteDRCReport(board, os.path.join(ROOT, 'out', 'drc.rpt'), pcbnew.EDA_UNITS_MILLIMETRES, True)
print('plane vias added:', added, '| groups without a via position:', failed)
