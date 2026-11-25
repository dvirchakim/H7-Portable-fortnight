"""Local clean-up router for the few connections Freerouting leaves open.

  python patch.py  rip:NET:x:y:r   route:REF-PAD[:width]   ...

rip    deletes tracks/vias of NET that come within r mm of (x, y)
route  connects the copper attached to pad REF-PAD to the nearest other copper of the same net
       (4-layer grid search, 0.05 mm grid, clearance-checked against everything else)
Zones are refilled and out/drc.rpt rewritten at the end.
"""
import os
import sys
import math
import heapq
import numpy as np
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
T = pcbnew.ToMM
S = 0.05                     # grid
CLR = 0.17                   # a little over the 0.16 rule
SAME = 0.16                  # new via to a pad / via of its own net (JLCDFM measures those gaps too)
VR, VDRILL = 0.25, 0.2
EDGE = 0.5
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
LCOST = [1.0, 3.0, 2.0, 1.0]  # keep patches off the planes where possible
VIA_COST = 300

board = pcbnew.LoadBoard(PCB)
bb = board.GetBoardEdgesBoundingBox()
BX0, BY0, BX1, BY1 = T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())
NX, NY = int(round((BX1 - BX0) / S)) + 1, int(round((BY1 - BY0) / S)) + 1


PADS = []
CORE = {}       # pad name -> inner rectangle that is surely copper (non-rectangular pads)
TRK = []       # [proxy, data] - everything is read up front: KiCad 7's python bindings return
               # untyped objects once an item has been removed from the board
for _t in board.GetTracks():
    if _t.Type() == pcbnew.PCB_VIA_T:
        TRK.append([_t, ('v', _t.GetNetname(), (T(_t.GetPosition().x), T(_t.GetPosition().y)), T(_t.GetWidth()) / 2)])
    else:
        TRK.append([_t, ('t', _t.GetNetname(), [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu].index(_t.GetLayer()),
                         (T(_t.GetStart().x), T(_t.GetStart().y)), (T(_t.GetEnd().x), T(_t.GetEnd().y)), T(_t.GetWidth()) / 2)])
AREAS = [[], []]


def collect():
    pads, tracks, vias, keep, sock = PADS, [], [], AREAS[0], AREAS[1]
    for fp in ([] if PADS else board.GetFootprints()):      # pads never change; read them once
        for pad in fp.Pads():
            r = pad.GetBoundingBox()
            rect = (T(r.GetLeft()), T(r.GetTop()), T(r.GetRight()), T(r.GetBottom()))
            npth = pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH
            if pad.GetShape() not in (pcbnew.PAD_SHAPE_RECT, pcbnew.PAD_SHAPE_ROUNDRECT):
                k = 0.3 * min(rect[2] - rect[0], rect[3] - rect[1])   # round / custom pad: aim at its core
                CORE[fp.GetReference() + '-' + pad.GetNumber()] = (rect[0] + k, rect[1] + k, rect[2] - k, rect[3] - k)
            for li, l in enumerate(CU):
                if npth or pad.IsOnLayer(l):
                    pads.append(('<hole>' if npth else pad.GetNetname(), li, rect,
                                 fp.GetReference() + '-' + pad.GetNumber()))
    for _, d in TRK:
        (vias if d[0] == 'v' else tracks).append(d[1:])
    for i in ([] if keep else range(board.GetAreaCount())):
        z = board.GetArea(i)
        if z.GetIsRuleArea():
            r = z.GetBoundingBox()
            if z.GetZoneName() != 'HOLE_KEEPOUT' and z.GetZoneName().endswith('_KEEPOUT'):   # F.Cu rects (sockets, U4)
                sock.append((T(r.GetLeft()), T(r.GetTop()), T(r.GetRight()), T(r.GetBottom())))
            else:
                keep.append(((T(r.GetCenter().x), T(r.GetCenter().y)), T(r.GetWidth()) / 2))
    return pads, tracks, vias, keep, sock


def window(x0, y0, x1, y1, m):
    ix0 = max(0, int((x0 - m - BX0) / S)); ix1 = min(NX, int((x1 + m - BX0) / S) + 2)
    iy0 = max(0, int((y0 - m - BY0) / S)); iy1 = min(NY, int((y1 + m - BY0) / S) + 2)
    X = BX0 + S * np.arange(ix0, ix1)[None, :]
    Y = BY0 + S * np.arange(iy0, iy1)[:, None]
    return (slice(iy0, iy1), slice(ix0, ix1)), X, Y


def d_seg(a, b, m):
    sl, X, Y = window(min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]), m)
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    t = 0 if L == 0 else np.clip(((X - a[0]) * dx + (Y - a[1]) * dy) / L, 0, 1)
    return sl, np.hypot(X - a[0] - t * dx, Y - a[1] - t * dy)


def d_rect(r, m):
    sl, X, Y = window(r[0], r[1], r[2], r[3], m)
    ddx = np.maximum(np.maximum(r[0] - X, X - r[2]), 0)
    ddy = np.maximum(np.maximum(r[1] - Y, Y - r[3]), 0)
    return sl, np.hypot(ddx, ddy)


def pt_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy), (a[0] + t * dx, a[1] + t * dy)


def seg_seg(a, b, c, d):
    def ccw(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    if a != b and c != d and ccw(a, b, c) * ccw(a, b, d) < 0 and ccw(c, d, a) * ccw(c, d, b) < 0:
        return 0.0
    return min(pt_seg(a, c, d)[0], pt_seg(b, c, d)[0], pt_seg(c, a, b)[0], pt_seg(d, a, b)[0])


def seg_rect(a, b, r):
    for p in (a, b):
        if r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3]:
            return 0.0
    cs = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    return min(seg_seg(a, b, cs[i], cs[(i + 1) % 4]) for i in range(4))


def rip(net, x, y, r):
    n = 0
    for e in list(TRK):
        d = e[1]
        if d[1] != net:
            continue
        dd = math.hypot(d[2][0] - x, d[2][1] - y) if d[0] == 'v' else pt_seg((x, y), d[3], d[4])[0]
        if dd < r:
            board.Remove(e[0])
            TRK.remove(e)
            n += 1
    print('rip', net, 'removed', n)


POWER = ('VBAT', '+5V_BUCK', 'BUCK_SW')       # 'Power' net class: 0.2 mm clearance


def cl(n, net):
    """clearance between a new track of NET and copper of net n"""
    return max(CLR, 0.205) if (n in POWER or net in POWER) else CLR


def route(ref, width):
    HW = width / 2
    pads, tracks, vias, keep, sock = collect()
    start = [p for p in pads if p[3] == ref]
    assert start, ref
    net = start[0][0]
    # ---- clusters of same-net copper
    items = [('p',) + p for p in pads if p[0] == net] + [('t',) + t for t in tracks if t[0] == net] + \
            [('v',) + v for v in vias if v[0] == net]
    par = list(range(len(items)))

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i

    def touch(a, b):
        ka, kb = a[0], b[0]
        if ka > kb:
            a, b, ka, kb = b, a, kb, ka
        if ka == 'p' and kb == 'p':
            return a[4] == b[4]                                   # same pad on several layers
        if ka == 'p' and kb == 't':
            return a[2] == b[2] and seg_rect(b[3], b[4], CORE.get(a[4], a[3])) < 0.01
        if ka == 'p' and kb == 'v':
            return seg_rect(b[2], b[2], CORE.get(a[4], a[3])) < b[3]
        if ka == 't' and kb == 't':
            return a[2] == b[2] and seg_seg(a[3], a[4], b[3], b[4]) < max(a[5], b[5])
        if ka == 't' and kb == 'v':
            return pt_seg(b[2], a[3], a[4])[0] < b[3]
        return math.hypot(a[2][0] - b[2][0], a[2][1] - b[2][1]) < 0.01
    for i in range(len(items)):
        for j in range(i):
            if find(i) != find(j) and touch(items[i], items[j]):
                par[find(i)] = find(j)
    root = find(next(i for i, it in enumerate(items) if it[0] == 'p' and it[4] == ref))
    # ---- obstacle maps
    bt = np.zeros((4, NY, NX), bool)
    bv = np.zeros((NY, NX), bool)
    e = int(round(EDGE / S))
    for a in (bt[:, :e, :], bt[:, -e:, :], bt[:, :, :e], bt[:, :, -e:]):
        a[...] = True
    for a in (bv[:e, :], bv[-e:, :], bv[:, :e], bv[:, -e:]):
        a[...] = True
    for n, l, rect, _ in pads:
        if n != net:
            c_ = cl(n, net)
            sl, d = d_rect(rect, HW + c_ + S); bt[l][sl] |= d < HW + c_
            sl, d = d_rect(rect, VR + c_ + S); bv[sl] |= d < VR + c_
        else:
            sl, d = d_rect(rect, VR + SAME + S); bv[sl] |= d < VR + SAME
    for n, l, a, b, hw in tracks:
        if n != net:
            c_ = cl(n, net)
            sl, d = d_seg(a, b, hw + VR + c_ + S)
            bt[l][sl] |= d < hw + HW + c_
            bv[sl] |= d < hw + VR + c_
    for n, c, r in vias:
        c_ = cl(n, net)
        sl, d = d_seg(c, c, r + VR + max(c_, SAME) + S)
        if n != net:
            for l in range(4):
                bt[l][sl] |= d < r + HW + c_
            bv[sl] |= d < r + VR + c_
        else:
            bv[sl] |= d < r + VR + SAME
    for c, r in keep:
        sl, d = d_seg(c, c, r + VR + 0.1 + S)
        for l in range(4):
            bt[l][sl] |= d < r + HW
        bv[sl] |= d < r + VR + 0.1
    for r in sock:
        sl, d = d_rect(r, VR + 0.05 + S)
        bt[0][sl] |= d < HW + 0.02
        bv[sl] |= d < VR + 0.05
    # ---- seeds / targets: cell -> anchor point on existing copper
    seeds, targets = {}, {}

    def cells_of(it, out):
        if it[0] == 'p':
            sl, d = d_rect(CORE.get(it[4], it[3]), S)
            ys, xs = np.nonzero(d == 0)
            for y, x in zip(ys, xs):
                c = (it[2], int(y) + sl[0].start, int(x) + sl[1].start)
                out[c] = None
        elif it[0] == 't':
            sl, d = d_seg(it[3], it[4], S)
            ys, xs = np.nonzero(d < 0.04)
            for y, x in zip(ys, xs):
                c = (it[2], int(y) + sl[0].start, int(x) + sl[1].start)
                out[c] = pt_seg((BX0 + c[2] * S, BY0 + c[1] * S), it[3], it[4])[1]
        else:
            sl, d = d_seg(it[2], it[2], S)
            ys, xs = np.nonzero(d < 0.04)
            for y, x in zip(ys, xs):
                for l in range(4):
                    out[(l, int(y) + sl[0].start, int(x) + sl[1].start)] = it[2]
    for i, it in enumerate(items):
        cells_of(it, seeds if find(i) == root else targets)
    if not targets:
        return None                                   # the net is already in one piece
    # ---- Dijkstra
    dist = dict((c, 0) for c in seeds)
    prev = {}
    pq = [(0, c) for c in seeds]
    heapq.heapify(pq)
    end = None
    while pq:
        dcur, cur = heapq.heappop(pq)
        if dist.get(cur, 1e18) < dcur:
            continue
        if cur in targets:
            end = cur
            break
        l, y, x = cur
        nb = []
        for dx, dy, c in ((1, 0, 10), (-1, 0, 10), (0, 1, 10), (0, -1, 10), (1, 1, 14), (1, -1, 14), (-1, 1, 14), (-1, -1, 14)):
            nb.append(((l, y + dy, x + dx), c * LCOST[l]))
        if not bv[y, x]:
            for l2 in range(4):
                if l2 != l:
                    nb.append(((l2, y, x), VIA_COST))
        for c, w in nb:
            if not (0 <= c[1] < NY and 0 <= c[2] < NX):
                continue
            if bt[c] and c not in targets:
                continue
            nd = dcur + w
            if nd < dist.get(c, 1e18):
                dist[c] = nd
                prev[c] = cur
                heapq.heappush(pq, (nd, c))
    if end is None:
        print('route', ref, net, 'FAILED')
        FAILED.append(ref)
        return False
    cells = [end]
    while cells[-1] in prev:
        cells.append(prev[cells[-1]])
    cells.reverse()
    P = lambda c: (round(BX0 + c[2] * S, 3), round(BY0 + c[1] * S, 3))
    ni = board.FindNet(net)

    def add_track(l, a, b):
        if a == b:
            return
        tr = pcbnew.PCB_TRACK(board)
        tr.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(a[0]), pcbnew.FromMM(a[1])))
        tr.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(b[0]), pcbnew.FromMM(b[1])))
        tr.SetWidth(pcbnew.FromMM(width)); tr.SetLayer(CU[l]); tr.SetNet(ni)
        board.Add(tr)
        TRK.append([tr, ('t', net, l, a, b, width / 2)])
    nvia = 0
    if seeds[cells[0]]:
        add_track(cells[0][0], seeds[cells[0]], P(cells[0]))
    if targets[end]:
        add_track(end[0], P(end), targets[end])
    i = 0
    while i < len(cells) - 1:
        a, b = cells[i], cells[i + 1]
        if a[0] != b[0]:
            j = i + 1                                   # several layer changes at one spot = one via
            while j < len(cells) - 1 and cells[j + 1][1:] == a[1:]:
                j += 1
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(P(a)[0]), pcbnew.FromMM(P(a)[1])))
            via.SetWidth(pcbnew.FromMM(VR * 2)); via.SetDrill(pcbnew.FromMM(VDRILL))
            via.SetViaType(pcbnew.VIATYPE_THROUGH); via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            via.SetNet(ni)
            board.Add(via)
            TRK.append([via, ('v', net, P(a), VR)])
            nvia += 1
            i = j
            continue
        d = (b[1] - a[1], b[2] - a[2])
        j = i + 1
        while j < len(cells) - 1 and cells[j + 1][0] == a[0] and \
                (cells[j + 1][1] - cells[j][1], cells[j + 1][2] - cells[j][2]) == d:
            j += 1
        add_track(a[0], P(a), P(cells[j]))
        i = j
    print('route', ref, net, 'ok: %s -> %s, %d vias, length %.1f mm' %
          (P(cells[0]), P(end), nvia, sum(math.hypot(P(a)[0] - P(b)[0], P(a)[1] - P(b)[1]) for a, b in zip(cells, cells[1:]))))
    return True


def add_item(d):
    ni = board.FindNet(d[1])
    if d[0] == 'v':
        it = pcbnew.PCB_VIA(board)
        it.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(d[2][0]), pcbnew.FromMM(d[2][1])))
        it.SetWidth(pcbnew.FromMM(d[3] * 2)); it.SetDrill(pcbnew.FromMM(VDRILL))
        it.SetViaType(pcbnew.VIATYPE_THROUGH); it.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    else:
        it = pcbnew.PCB_TRACK(board)
        it.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(d[3][0]), pcbnew.FromMM(d[3][1])))
        it.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(d[4][0]), pcbnew.FromMM(d[4][1])))
        it.SetWidth(pcbnew.FromMM(d[5] * 2)); it.SetLayer(CU[d[2]])
    it.SetNet(ni)
    board.Add(it)
    TRK.append([it, d])


def rip_where(pred):
    out = []
    for e in list(TRK):
        if pred(e[1]):
            board.Remove(e[0])
            TRK.remove(e)
            out.append(e[1])
    return out


def reconnect(net, width, ripped, what):
    """join the pieces of a net again, first with DFM-level spacing; put the old copper back if that fails"""
    global CLR
    start = next(p[3] for p in PADS if p[0] == net)
    mark = len(TRK)
    for clr in (0.18, 0.165, 0.15, 0.135):
        CLR = clr
        ok = True
        for _ in range(6):
            r = route(start, width)
            if r is None:
                break
            if r is False:
                ok = False
                break
        if ok:
            CLR = 0.17
            print(what, 'ok at clearance', clr)
            return True
        for e in TRK[mark:]:                              # undo the partial attempt
            board.Remove(e[0])
        del TRK[mark:]
    CLR = 0.17
    for d in ripped:
        add_item(d)
    print(what, 'NOT improved - original copper restored')
    return False


def reroute(net, ref):
    """move the tracks of NET that pass within 0.16 mm of pad REF (measured to the pad's rectangle)"""
    rects = [(p[1], p[2]) for p in PADS if p[3] == ref]
    ripped = rip_where(lambda d: d[0] == 't' and d[1] == net and
                       any(l == d[2] and seg_rect(d[3], d[4], r) - d[5] < 0.16 for l, r in rects))
    if not ripped:
        print('reroute', net, ref, ': nothing that close')
        return
    del REMOVED[:]
    prune()                                       # drop the stubs the rip left, before routing
    reconnect(net, max(0.15, min(d[5] for d in ripped) * 2), ripped + list(REMOVED), 'reroute %s away from %s' % (net, ref))


def revia(ref, x, y):
    """replace the via at (x, y) that sits too close to pad REF of its own net"""
    net = next(p[0] for p in PADS if p[3] == ref)
    ripped = rip_where(lambda d: d[1] == net and ((d[0] == 'v' and math.hypot(d[2][0] - x, d[2][1] - y) < 0.02) or
                                                  (d[0] == 't' and pt_seg((x, y), d[3], d[4])[0] < 0.02)))
    w = [d[5] * 2 for d in ripped if d[0] == 't']
    reconnect(net, max(0.15, min(w)) if w else 0.15, ripped, 'revia %s near %s' % (net, ref))


REMOVED = []


def prune():
    """remove what rip / reroute leave behind: stubs with a free end, tracks lying wholly on one pad,
    zero-length tracks and vias that no longer join two layers"""
    zone_nets = ('GND', '+5V')                       # their stubs and vias end in a pour / plane
    n = 0
    while True:
        dead = None
        for e in TRK:
            d = e[1]
            if d[1] in zone_nets:
                continue
            if d[0] == 'v':
                layers = set()
                for f in TRK:
                    o = f[1]
                    if o[0] == 't' and o[1] == d[1] and pt_seg(d[2], o[3], o[4])[0] < d[3]:
                        layers.add(o[2])
                for p in PADS:
                    if p[0] == d[1] and seg_rect(d[2], d[2], p[2]) < d[3]:
                        layers.add(p[1])
                if len(layers) < 2:
                    dead = e
                    break
                continue
            if math.hypot(d[3][0] - d[4][0], d[3][1] - d[4][1]) < 0.02:
                dead = e
                break
            ends = []
            for end in (d[3], d[4]):
                other, pad = False, None
                for f in TRK:
                    o = f[1]
                    if f is e or o[1] != d[1]:
                        continue
                    if o[0] == 'v':
                        if math.hypot(o[2][0] - end[0], o[2][1] - end[1]) < o[3]:
                            other = True
                            break
                    elif o[2] == d[2] and o[3] != o[4] and pt_seg(end, o[3], o[4])[0] < o[5] + 0.005:
                        other = True
                        break
                for p in PADS:
                    if p[0] == d[1] and p[1] == d[2] and p[2][0] - 0.01 <= end[0] <= p[2][2] + 0.01 and p[2][1] - 0.01 <= end[1] <= p[2][3] + 0.01:
                        pad = p[3]
                        break
                ends.append((other, pad))
            (o1, p1), (o2, p2) = ends
            if (not o1 and p1 is None) or (not o2 and p2 is None) or (not o1 and not o2 and p1 == p2) or                     (p1 is not None and not o1 and not o2 and p2 is None):
                dead = e
                break
        if not dead:
            break
        board.Remove(dead[0])
        TRK.remove(dead)
        REMOVED.append(dead[1])
        n += 1
    print('prune: removed', n, 'leftover items')
    return n


LAST_FAIL = [None]


def regroup_any(nets):
    """regroup, and on failure retry with the net that failed moved up to second place (max 4 orders)"""
    order = nets.split(',')
    tried = []
    for _ in range(4):
        tried.append(list(order))
        if regroup(','.join(order)):
            return True
        f = LAST_FAIL[0]
        if f == order[0]:
            return False                         # fails even with the whole group ripped up
        order = [order[0], f] + [n for n in order[1:] if n != f]
        if order in tried:
            order = [f] + [n for n in tried[0] if n != f]
            if order in tried:
                return False
    return False


def regroup(nets, width=0.15):
    """rip every track and via of NETS, then route them again one by one in the given order (first =
    the hardest), each at the widest clearance that works; restore the old copper if any fails"""
    global CLR
    nets = nets.split(',')
    old = rip_where(lambda d: d[1] in nets)
    mark = len(TRK)
    ok_all = True
    for net in nets:
        pads = [p[3] for p in PADS if p[0] == net]
        ok = False
        for clr, wid in ((0.17, width), (0.15, width), (0.135, width), (0.13, width), (0.13, 0.127)):
            m2 = len(TRK)
            CLR = clr
            good = True
            for _ in range(len(set(pads)) + 2):
                r = route(pads[0], wid)
                if r is None:
                    break
                if r is False:
                    good = False
                    break
            if good:
                print('regroup %s routed at clearance %.3f, width %.3f' % (net, clr, wid))
                ok = True
                break
            for e in TRK[m2:]:
                board.Remove(e[0])
            del TRK[m2:]
        if not ok:
            ok_all = False
            print('regroup %s FAILED' % net)
            LAST_FAIL[0] = net
            break
    CLR = 0.17
    if not ok_all:
        for e in TRK[mark:]:
            board.Remove(e[0])
        del TRK[mark:]
        for d in old:
            add_item(d)
        print('regroup', ','.join(nets), ': original copper restored')
    return ok_all


collect()
FAILED = []
for arg in sys.argv[1:]:
    a = arg.split(':')
    if a[0] == 'clr':                                 # routing clearance for the commands that follow
        CLR = float(a[1])
    elif a[0] == 'rip':
        rip(a[1], float(a[2]), float(a[3]), float(a[4]))
    elif a[0] == 'regroup':
        regroup_any(a[1])
    elif a[0] == 'prune':
        prune()
    elif a[0] == 'reroute':
        reroute(a[1], a[2])
    elif a[0] == 'revia':
        revia(a[1], float(a[2]), float(a[3]))
    elif a[0] == 'route':
        route(a[1], float(a[2]) if len(a) > 2 else 0.15)
print('still FAILED:', FAILED)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
board = pcbnew.LoadBoard(PCB)
pcbnew.WriteDRCReport(board, os.path.join(ROOT, 'out', 'drc.rpt'), pcbnew.EDA_UNITS_MILLIMETRES, True)
