"""Design-for-manufacture check against the limits JLCPCB's JLCDFM tool reports on.

  "C:\\Program Files\\KiCad\\7.0\\bin\\python.exe" scripts/dfm.py [-v]     -> prints a table, writes out/dfm.rpt

JLCDFM has no netlist, so it also measures gaps between copper of the SAME net (a via next to
its own pad, a stub passing its own pad).  Both kinds are counted here, separately.
Limits used (danger / warning):  copper spacing 0.10 / 0.15,  silkscreen to pad or hole 0.13 / 0.18,
silkscreen line width 0.15 / 0.153,  annular ring 0.10 / 0.15.
"""
import os
import sys
import math
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
T = pcbnew.ToMM
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
NAMES = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu']
EPS = 0.004


def pt_seg(p, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / L))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def seg_seg(a, b, c, d):
    def ccw(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])
    if a != b and c != d and ccw(a, b, c) * ccw(a, b, d) < 0 and ccw(c, d, a) * ccw(c, d, b) < 0:
        return 0.0
    return min(pt_seg(a, c, d), pt_seg(b, c, d), pt_seg(c, a, b), pt_seg(d, a, b))


def seg_rect(a, b, r):
    for p in (a, b):
        if r[0] <= p[0] <= r[2] and r[1] <= p[1] <= r[3]:
            return 0.0
    cs = [(r[0], r[1]), (r[2], r[1]), (r[2], r[3]), (r[0], r[3])]
    return min(seg_seg(a, b, cs[i], cs[(i + 1) % 4]) for i in range(4))


def rect_rect(r, s):
    dx = max(r[0] - s[2], s[0] - r[2], 0)
    dy = max(r[1] - s[3], s[1] - r[3], 0)
    return math.hypot(dx, dy)


class Item(object):
    """kind 't' track (a, b, hw) | 'v' via (c, r) | 'p' pad (rect)"""
    def __init__(self, kind, net, layer, name, **kw):
        self.kind, self.net, self.layer, self.name = kind, net, layer, name
        self.__dict__.update(kw)
        if kind == 't':
            self.box = (min(self.a[0], self.b[0]) - self.hw, min(self.a[1], self.b[1]) - self.hw,
                        max(self.a[0], self.b[0]) + self.hw, max(self.a[1], self.b[1]) + self.hw)
        elif kind == 'v':
            self.box = (self.c[0] - self.r, self.c[1] - self.r, self.c[0] + self.r, self.c[1] + self.r)
        else:
            self.box = self.rect


def gap(x, y):
    if x.kind > y.kind:
        x, y = y, x
    k = x.kind + y.kind
    if k == 'pp':
        return rect_rect(x.rect, y.rect)
    if k == 'pt':
        return seg_rect(y.a, y.b, x.rect) - y.hw
    if k == 'pv':
        return seg_rect(y.c, y.c, x.rect) - y.r
    if k == 'tt':
        return seg_seg(x.a, x.b, y.a, y.b) - x.hw - y.hw
    if k == 'tv':
        return pt_seg(y.c, x.a, x.b) - x.hw - y.r
    return math.hypot(x.c[0] - y.c[0], x.c[1] - y.c[1]) - x.r - y.r


def load(board):
    items = [[] for _ in CU]
    holes = []                                        # (centre, radius) of every drilled hole
    rings = []
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            r = pad.GetBoundingBox()
            rect = (T(r.GetLeft()), T(r.GetTop()), T(r.GetRight()), T(r.GetBottom()))
            name = '%s-%s' % (fp.GetReference(), pad.GetNumber())
            if pad.GetDrillSize().x > 0:
                holes.append(((T(pad.GetPosition().x), T(pad.GetPosition().y)), T(pad.GetDrillSize().x) / 2, name))
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            for li, l in enumerate(CU):
                if pad.IsOnLayer(l):
                    if pad.GetShape() == pcbnew.PAD_SHAPE_CIRCLE:
                        items[li].append(Item('v', pad.GetNetname(), li, name, c=(T(pad.GetPosition().x), T(pad.GetPosition().y)),
                                              r=T(pad.GetSize().x) / 2))
                    else:           # rounded-rectangle pads are measured as plain rectangles, as JLCDFM does
                        items[li].append(Item('p', pad.GetNetname(), li, name, rect=rect))
    for t in board.GetTracks():
        if t.Type() == pcbnew.PCB_VIA_T:
            c = (T(t.GetPosition().x), T(t.GetPosition().y))
            holes.append((c, T(t.GetDrill()) / 2, 'via'))
            rings.append((c, (T(t.GetWidth()) - T(t.GetDrill())) / 2))
            for li in range(4):
                items[li].append(Item('v', t.GetNetname(), li, 'via', c=c, r=T(t.GetWidth()) / 2))
        else:
            li = CU.index(t.GetLayer())
            items[li].append(Item('t', t.GetNetname(), li, 'track', a=(T(t.GetStart().x), T(t.GetStart().y)),
                                  b=(T(t.GetEnd().x), T(t.GetEnd().y)), hw=T(t.GetWidth()) / 2))
    return items, holes, rings


def near_pairs(items, lim):
    """all pairs with 0 < gap < lim  (touching / overlapping copper is one piece and is skipped)"""
    cell = 1.0
    grid = {}
    for i, it in enumerate(items):
        for gx in range(int((it.box[0] - lim) // cell), int((it.box[2] + lim) // cell) + 1):
            for gy in range(int((it.box[1] - lim) // cell), int((it.box[3] + lim) // cell) + 1):
                grid.setdefault((gx, gy), []).append(i)
    seen = set()
    out = []
    for lst in grid.values():
        for ai in range(len(lst)):
            for bi in range(ai + 1, len(lst)):
                i, j = lst[ai], lst[bi]
                if (i, j) in seen:
                    continue
                seen.add((i, j))
                x, y = items[i], items[j]
                if x.box[0] - lim > y.box[2] or y.box[0] - lim > x.box[2] or x.box[1] - lim > y.box[3] or y.box[1] - lim > x.box[3]:
                    continue
                g = gap(x, y)
                if EPS < g < lim - EPS:
                    out.append((g, x, y))
    return out


def where(it):
    if it.kind == 't':
        return '(%.2f,%.2f)-(%.2f,%.2f)' % (it.a + it.b)
    if it.kind == 'v':
        return '(%.2f,%.2f)' % it.c
    return '(%.2f,%.2f)' % ((it.rect[0] + it.rect[2]) / 2, (it.rect[1] + it.rect[3]) / 2)


def silk_items(board):
    """silkscreen graphics as (side, kind, geometry, width, name); text as rectangles"""
    out = []
    def add(obj, name):
        l = obj.GetLayer()
        if l not in (pcbnew.F_SilkS, pcbnew.B_SilkS):
            return
        side = 0 if l == pcbnew.F_SilkS else 3
        cls = obj.GetClass()
        if cls in ('FP_TEXT', 'PCB_TEXT'):
            if cls == 'FP_TEXT' and not obj.IsVisible():
                return
            r = obj.GetBoundingBox()
            # the bounding box has ~0.19 mm of padding round the glyphs at 1 mm text height
            m = 0.19 * T(obj.GetTextHeight())
            out.append((side, 'text', (T(r.GetLeft()) + m, T(r.GetTop()) + m, T(r.GetRight()) - m, T(r.GetBottom()) - m),
                        T(obj.GetTextThickness()), name + ' "%s"' % obj.GetText()))
            return
        w = T(obj.GetWidth())
        sh = obj.GetShape()
        if sh == pcbnew.SHAPE_T_SEGMENT:
            out.append((side, 'seg', ((T(obj.GetStart().x), T(obj.GetStart().y)), (T(obj.GetEnd().x), T(obj.GetEnd().y))), w, name))
        else:
            r = obj.GetBoundingBox()
            out.append((side, 'box', (T(r.GetLeft()), T(r.GetTop()), T(r.GetRight()), T(r.GetBottom())),
                        w if not (sh == pcbnew.SHAPE_T_RECT and obj.IsFilled()) else 9, name))
    for fp in board.GetFootprints():
        for t in (fp.Reference(), fp.Value()):
            add(t, fp.GetReference())
        for g in fp.GraphicalItems():
            add(g, fp.GetReference())
    for d in board.GetDrawings():
        add(d, 'board')
    return out


def run(board, verbose=False):
    items, holes, rings = load(board)
    rows = []
    detail = []
    def tally(title, vals, danger, warn, lines):
        d = [v for v in vals if v < danger - EPS]
        w = [v for v in vals if danger - EPS <= v < warn - EPS]
        rows.append((title, len(d), len(w), min(vals) if vals else None))
        detail.extend(lines)
    for li in (0, 3, 1, 2):
        pairs = near_pairs(items[li], 0.15)
        for same, cats in ((False, (('trace-trace', ('tt',)), ('pad/via-trace', ('pt', 'tv')), ('pad/via-pad/via', ('pp', 'pv', 'vv')))),
                           (True, (('pad/via-pad/via', ('pp', 'pv', 'vv')),))):      # same-net track joints are one piece of copper
            for cat, kinds in cats:
                sel = [(g, x, y) for g, x, y in pairs if (x.net == y.net and x.net != '') == same
                       and ''.join(sorted(x.kind + y.kind)) in kinds]
                tally('%-7s %-16s %s' % (NAMES[li], cat, 'same net' if same else 'DIFFERENT nets'), [g for g, _, _ in sel], 0.10, 0.15,
                      ['%s %s %s gap %.3f: %s %s %s  |  %s %s %s' % (NAMES[li], cat, 'same' if same else 'DIFF', g, x.name, x.net, where(x),
                                                                    y.name, y.net, where(y)) for g, x, y in sorted(sel, key=lambda s: s[0])])
    tally('annular ring (vias)', [r for _, r in rings], 0.10, 0.15, [])
    silk = silk_items(board)
    for side, nm in ((0, 'F'), (3, 'B')):
        pads = [it for it in items[side] if it.kind == 'p']
        sp, sh, lw, lines = [], [], [], []
        for s, kind, geo, w, name in silk:
            if s != side:
                continue
            hw = 0 if kind in ('text', 'box') and w >= 9 else (w / 2 if kind != 'text' else 0)
            if w < 9:
                lw.append(w)
            def dist_rect(r):
                if kind == 'seg':
                    return seg_rect(geo[0], geo[1], r) - hw
                return rect_rect(geo, r) - hw
            def dist_pt(c):
                if kind == 'seg':
                    return pt_seg(c, geo[0], geo[1]) - hw
                return rect_rect(geo, (c[0], c[1], c[0], c[1])) - hw
            box = (min(geo[0][0], geo[1][0]), min(geo[0][1], geo[1][1]), max(geo[0][0], geo[1][0]), max(geo[0][1], geo[1][1])) if kind == 'seg' else geo
            for p in pads:
                if p.rect[0] - 0.4 > box[2] or box[0] - 0.4 > p.rect[2] or p.rect[1] - 0.4 > box[3] or box[1] - 0.4 > p.rect[3]:
                    continue
                d = dist_rect(p.rect)
                if d < 0.18 - EPS:
                    sp.append(max(d, 0))
                    lines.append('%s silk-pad %.3f: %s -> %s' % (nm, max(d, 0), name, p.name))
            for c, r, hn in holes:
                if c[0] + r + 0.4 < box[0] or c[0] - r - 0.4 > box[2] or c[1] + r + 0.4 < box[1] or c[1] - r - 0.4 > box[3]:
                    continue
                d = dist_pt(c) - r
                if d < 0.18 - EPS:
                    sh.append(max(d, 0))
                    lines.append('%s silk-hole %.3f: %s -> %s (%.2f,%.2f)' % (nm, max(d, 0), name, hn, c[0], c[1]))
        tally('%s silkscreen to pad' % nm, sp, 0.13, 0.18, lines)
        tally('%s silkscreen to hole' % nm, sh, 0.13, 0.18, [])
        tally('%s silkscreen line width' % nm, lw, 0.15, 0.153, [])
    txt = ['%-48s %7s %8s %8s' % ('check', 'danger', 'warning', 'min mm')]
    for title, d, w, mn in rows:
        txt.append('%-48s %7d %8d %8s' % (title, d, w, '-' if mn is None else '%.3f' % mn))
    open(os.path.join(ROOT, 'out', 'dfm.rpt'), 'w').write('\n'.join(txt + [''] + detail) + '\n')
    print('\n'.join(txt))
    if verbose:
        print('\n'.join(detail[:80]))
    return rows


if __name__ == '__main__':
    run(pcbnew.LoadBoard(PCB), '-v' in sys.argv)
