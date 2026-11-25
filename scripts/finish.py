"""Post-routing touches on the board (safe to re-run; run scripts/vias.py first):

  1. L1 pads widened so Bourns SRP5030TA, KOHER MDA5030 and MPS MPL-AL5050 all fit
  2. silkscreen made JLCDFM-clean: footprint outlines trimmed back 0.2 mm from pads and drilled holes
     and drawn 0.16 mm wide; all text 1.0 mm / 0.16 mm, re-placed clear of pads, holes (vias too),
     parts, the edge and other text; test pads and connectors labelled with their function
  3. QR code (scripts/qr_matrix.txt from scripts/qr.py) + caption on the bottom silkscreen, placed
     where the fewest vias are; cells on top of a via hole are left unprinted

  "C:\\Program Files\\KiCad\\7.0\\bin\\python.exe" scripts/finish.py
"""
import os
import math
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
T, MM = pcbnew.ToMM, pcbnew.FromMM
SILK_W = 0.16                # line / stroke width (JLCDFM warns below 0.153)
SILK_CLR = 0.2               # silkscreen to pad / hole (JLCDFM warns below 0.18)
QR_QUIET = 3
QR_CAPTION = 'github.com/dvirchakim'
SIZE = [1.0]                 # text height in use (1.0 mm, 0.8 mm as a last resort)
# Board name / revision / date, as production boards carry.  No "Arduino" or "Portenta" on the board:
# Arduino's trademark guide forbids its marks on third-party boards (text may say "for Arduino® Portenta H7").
BOARD_ID = 'FC CARRIER  R0.3  2026-11'

board = pcbnew.LoadBoard(PCB)
bb = board.GetBoardEdgesBoundingBox()
BX0, BY0, BX1, BY1 = T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())
SIDES = {pcbnew.F_Cu: pcbnew.F_SilkS, pcbnew.B_Cu: pcbnew.B_SilkS}
SILK2CU = {pcbnew.F_SilkS: pcbnew.F_Cu, pcbnew.B_SilkS: pcbnew.B_Cu}
REMOVE = []                  # (parent, item) - removed at the very end: KiCad 7's python getters
                             # misbehave once something has been removed from the board


def rect_of(r, m=0.0):
    return (T(r.GetLeft()) - m, T(r.GetTop()) - m, T(r.GetRight()) + m, T(r.GetBottom()) + m)


def hit(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def pt_rect(p, r):
    return math.hypot(max(r[0] - p[0], p[0] - r[2], 0), max(r[1] - p[1], p[1] - r[3], 0))


# ---------------------------------------------------------------- 1. L1 pads
l1 = board.FindFootprintByReference('L1')
for pad in l1.Pads():
    pad.SetSize(pcbnew.VECTOR2I(MM(2.4), MM(4.7)))   # takes Bourns SRP5030TA, KOHER MDA5030 and MPS MPL-AL5050

# ---------------------------------------------------------------- geometry everything else must avoid
PADS = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}          # pad rectangles per side (NPTH on both)
BODY = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}          # footprint bodies per side
HOLES = []                                         # (x, y, radius) of every drilled hole, vias included
for fp in board.GetFootprints():
    BODY[fp.GetLayer()].append(rect_of(fp.GetBoundingBox(False, False)))
    for pad in fp.Pads():
        if pad.GetDrillSize().x > 0:
            HOLES.append((T(pad.GetPosition().x), T(pad.GetPosition().y), T(pad.GetDrillSize().x) / 2))
        for s in SIDES:
            if pad.IsOnLayer(s) or pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                PADS[s].append(rect_of(pad.GetBoundingBox()))
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        HOLES.append((T(t.GetPosition().x), T(t.GetPosition().y), T(t.GetDrill()) / 2))


def silk_free(p, side, hw):
    """may silkscreen ink of half-width hw be centred on point p?"""
    for r in PADS[side]:
        if abs(p[0] - (r[0] + r[2]) / 2) < (r[2] - r[0]) / 2 + SILK_CLR + hw and pt_rect(p, r) < SILK_CLR + hw:
            return False
    for x, y, r in HOLES:
        if abs(p[0] - x) < r + SILK_CLR + hw and math.hypot(p[0] - x, p[1] - y) < r + SILK_CLR + hw:
            return False
    return True


# ---------------------------------------------------------------- 2a. footprint outlines
BLOCK = ('S5', 'S6', 'LED', 'BUZ', '+5V', 'GND')   # 2 x 3 pad block on top: outlines dropped, labels above pads
for fp in board.GetFootprints():
    block = fp.GetLayer() == pcbnew.F_Cu and fp.GetReference().startswith('TP') and \
        fp.Value().GetText() in BLOCK + ('LED_STRIP', 'BUZZ_N')
    for g in list(fp.GraphicalItems()):
        if g.GetClass() == 'FP_TEXT' or g.GetLayer() not in SILK2CU:
            continue
        side = SILK2CU[g.GetLayer()]
        if block:
            REMOVE.append((fp, g))
            continue
        if g.GetShape() != pcbnew.SHAPE_T_SEGMENT:
            r = rect_of(g.GetBoundingBox())
            c = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
            if not all(silk_free(p, side, 0) for p in ((r[0], r[1]), (r[2], r[1]), (r[0], r[3]), (r[2], r[3]), c)):
                REMOVE.append((fp, g))
            elif not g.IsFilled():
                g.SetWidth(MM(SILK_W))
            continue
        a = (T(g.GetStart().x), T(g.GetStart().y))
        b = (T(g.GetEnd().x), T(g.GetEnd().y))
        L = math.hypot(b[0] - a[0], b[1] - a[1])
        n = max(1, int(L / 0.05))
        pts = [(a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n) for i in range(n + 1)]
        ok = [silk_free(p, side, SILK_W / 2) for p in pts]
        if all(ok):
            g.SetWidth(MM(SILK_W))
            continue
        REMOVE.append((fp, g))
        i = 0
        while i <= n:
            if not ok[i]:
                i += 1
                continue
            j = i
            while j + 1 <= n and ok[j + 1]:
                j += 1
            if math.hypot(pts[j][0] - pts[i][0], pts[j][1] - pts[i][1]) >= 0.3:
                s = pcbnew.FP_SHAPE(fp)
                s.SetShape(pcbnew.SHAPE_T_SEGMENT)
                s.SetStart(pcbnew.VECTOR2I(MM(pts[i][0]), MM(pts[i][1])))
                s.SetEnd(pcbnew.VECTOR2I(MM(pts[j][0]), MM(pts[j][1])))
                s.SetWidth(MM(SILK_W))
                s.SetLayer(g.GetLayer())
                s.SetLocalCoord()
                fp.Add(s)
            i = j + 1

# ---------------------------------------------------------------- 3. QR (before the text: it is an obstacle)
for d in board.GetDrawings():                      # previous QR / caption
    if d.GetLayer() == pcbnew.B_SilkS:
        REMOVE.append((board, d))
qr = [l.strip() for l in open(os.path.join(ROOT, 'scripts', 'qr_matrix.txt')) if l.strip()]
n = len(qr)
cells = n + 2 * QR_QUIET
best = None
for module in (0.4, 0.35):                         # fewest via holes wins; the larger module on a tie
    tot = cells * module
    y = BY0 + 0.6
    while y + tot + 2.4 <= BY1 - 0.6:              # 2.4 mm below is kept for the caption
        x = BX0 + 0.6
        while x + tot <= BX1 - 0.6:
            area = (x - 0.4, y - 0.4, x + tot + 0.4, y + tot + 2.4)
            if not any(hit(area, r) for r in BODY[pcbnew.B_Cu]) and not any(hit(area, r) for r in PADS[pcbnew.B_Cu]):
                nv = sum(1 for hx, hy, hr in HOLES if x - 0.3 < hx < x + tot + 0.3 and y - 0.3 < hy < y + tot + 0.3)
                if best is None or nv < best[0]:
                    best = (nv, x, y, module)
            x += 0.1
        y += 0.1
assert best, 'no room for the QR code'
nv, qx0, qy0, QR_MODULE = best
tot = cells * QR_MODULE
print('QR at x %.1f..%.1f  y %.1f..%.1f, module %.2f mm (%d via holes under it)' % (qx0, qx0 + tot, qy0, qy0 + tot, QR_MODULE, nv))
# Silkscreen ink is the LIGHT colour: light modules and the quiet zone are printed, dark modules are
# bare solder mask.  Columns are mirrored because the code is read from the bottom.
light = [[True] * cells for _ in range(cells)]
for yy in range(n):
    for xx in range(n):
        if qr[yy][xx] == '1':
            light[yy + QR_QUIET][QR_QUIET + (n - 1 - xx)] = False


def qr_rect(x0, y0, x1, y1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0)))
    s.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
    s.SetFilled(True)
    s.SetWidth(0)
    s.SetLayer(pcbnew.B_SilkS)
    board.Add(s)


def near_hole(r):
    return any(pt_rect((hx, hy), r) < hr + SILK_CLR for hx, hy, hr in HOLES)


SUB = 4                                            # a cell next to a via hole is drawn as 4 x 4 tiles,
for yy, row in enumerate(light):                   # and only the tiles too close to the hole are left out
    xx = 0
    while xx < cells:
        cy0 = qy0 + yy * QR_MODULE
        if not row[xx]:
            xx += 1
            continue
        if near_hole((qx0 + xx * QR_MODULE, cy0, qx0 + (xx + 1) * QR_MODULE, cy0 + QR_MODULE)):
            t = QR_MODULE / SUB
            for sy in range(SUB):
                for sx in range(SUB):
                    r = (qx0 + xx * QR_MODULE + sx * t, cy0 + sy * t, qx0 + xx * QR_MODULE + (sx + 1) * t, cy0 + (sy + 1) * t)
                    if not near_hole(r):
                        qr_rect(*r)
            xx += 1
            continue
        x2 = xx
        while x2 < cells and row[x2] and not near_hole((qx0 + x2 * QR_MODULE, cy0, qx0 + (x2 + 1) * QR_MODULE, cy0 + QR_MODULE)):
            x2 += 1
        qr_rect(qx0 + xx * QR_MODULE, cy0, qx0 + x2 * QR_MODULE, cy0 + QR_MODULE)
        xx = x2
QR_RECT = (qx0 - 0.3, qy0 - 0.3, qx0 + tot + 0.3, qy0 + tot + 0.3)

# ---------------------------------------------------------------- 2b. silkscreen text
TEXT_PAD = 0.17              # KiCad's text bounding box is this much bigger than the glyphs (1 mm text)
obst = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
for s in SIDES:
    obst[s] += [(r[0] - 0.1, r[1] - 0.1, r[2] + 0.1, r[3] + 0.1) for r in BODY[s]]
    obst[s] += [(r[0] - SILK_CLR - 0.03, r[1] - SILK_CLR - 0.03, r[2] + SILK_CLR + 0.03, r[3] + SILK_CLR + 0.03) for r in PADS[s]]
    obst[s] += [(x - r - SILK_CLR - 0.03, y - r - SILK_CLR - 0.03, x + r + SILK_CLR + 0.03, y + r + SILK_CLR + 0.03) for x, y, r in HOLES]
obst[pcbnew.B_Cu].append(QR_RECT)
HOLE_OBST = [(x - r - SILK_CLR, y - r - SILK_CLR, x + r + SILK_CLR, y + r + SILK_CLR) for x, y, r in HOLES]


def measure(t, size):
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(SILK_W))
    out = {}
    for a in (0, 90):
        t.SetTextAngle(pcbnew.EDA_ANGLE(a, pcbnew.DEGREES_T))
        r = t.GetBoundingBox()
        w, h = T(r.GetWidth()), T(r.GetHeight())
        out['h' if w >= h else 'v'] = (a, w, h)
    return out


placed = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}


def fits(side, px, py, w, h, loose=False):
    """glyph rectangle against pads / holes / parts; full box against other text and the board edge"""
    r = (px - w / 2, py - h / 2, px + w / 2, py + h / 2)
    if r[0] < BX0 + 0.3 or r[1] < BY0 + 0.3 or r[2] > BX1 - 0.3 or r[3] > BY1 - 0.3:
        return None
    g = (r[0] + TEXT_PAD, r[1] + TEXT_PAD, r[2] - TEXT_PAD, r[3] - TEXT_PAD)
    if any(hit(g, o) for o in (HOLE_OBST if loose else obst[side])) or any(hit(g if loose else r, o) for o in placed[side]):
        if loose and os.environ.get('FINISH_DEBUG'):
            print('forced spot (%.2f, %.2f) blocked by holes %s / texts %s' % (px, py,
                  [tuple(round(v, 2) for v in o) for o in HOLE_OBST if hit(g, o)],
                  [tuple(round(v, 2) for v in o) for o in placed[side] if hit(g, o)]))
        return None
    return r


def place(side, t, anchor, maxgap=3.0, forced=None):
    """anchor = rectangle the label belongs to; False = no room (label hidden)"""
    t.SetVisible(True)
    x0, y0, x1, y1 = anchor
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    best = None
    for orient, (ang, w, h) in measure(t, SIZE[0]).items():
        cands = []
        if forced and orient == 'h':
            cands.append((-1.0, forced[0], forced[1]))
        g = 0.1
        while g <= maxgap:
            sx = [cx + k * 0.25 for k in range(-int((x1 - x0 + w) / 0.5) - 1, int((x1 - x0 + w) / 0.5) + 2)]
            sy = [cy + k * 0.25 for k in range(-int((y1 - y0 + h) / 0.5) - 1, int((y1 - y0 + h) / 0.5) + 2)]
            for px, py in [(x, y0 - g - h / 2) for x in sx] + [(x, y1 + g + h / 2) for x in sx] + \
                    [(x0 - g - w / 2, y) for y in sy] + [(x1 + g + w / 2, y) for y in sy]:
                cands.append((math.hypot(px - cx, py - cy) + (0.4 if orient == 'v' else 0), px, py))
            g += 0.3
        for sc, px, py in cands:
            if best is not None and sc >= best[0]:
                continue
            r = fits(side, px, py, w, h, loose=sc < 0)
            if r:
                best = (sc, ang, px, py, r)
    if not best:
        t.SetVisible(False)
        return False
    _, ang, px, py, r = best
    t.SetTextAngle(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))
    t.SetPosition(pcbnew.VECTOR2I(MM(px), MM(py)))
    if t.GetClass() == 'FP_TEXT':
        t.SetLocalCoord()
    placed[side].append((r[0] - 0.05, r[1] - 0.05, r[2] + 0.05, r[3] + 0.05))
    return True


stats = {'placed': 0, 'hidden': [], 'small': []}


def do(side, t, anchor, name, **kw):
    if place(side, t, anchor, **kw):
        stats['placed'] += 1
        return
    SIZE[0] = 0.8                                  # last resort: smaller text
    ok = place(side, t, anchor, **kw)
    SIZE[0] = 1.0
    if ok:
        stats['placed'] += 1
        stats['small'].append(name)
    else:
        stats['hidden'].append(name)


# QR caption, then the board-level labels, then the footprints (pads and connectors first)
cap = pcbnew.PCB_TEXT(board)
cap.SetText(QR_CAPTION)
cap.SetLayer(pcbnew.B_SilkS)
cap.SetMirrored(True)
board.Add(cap)
do(pcbnew.B_Cu, cap, QR_RECT, 'QR caption', maxgap=1.5)
bid = pcbnew.PCB_TEXT(board)
bid.SetText(BOARD_ID)
bid.SetLayer(pcbnew.B_SilkS)
bid.SetMirrored(True)
board.Add(bid)
ANCH = [((BX0 + BX1) / 2, BY1 - 3.5), ((BX0 + BX1) / 2, BY0 + 3.5), (BX0 + 12, (BY0 + BY1) / 2),
        (BX1 - 12, (BY0 + BY1) / 2), ((BX0 + BX1) / 2, (BY0 + BY1) / 2)]
for size, (ax, ay) in [(1.0, a) for a in ANCH] + [(0.8, a) for a in ANCH]:
    SIZE[0] = size
    if place(pcbnew.B_Cu, bid, (ax - 1, ay - 0.5, ax + 1, ay + 0.5), maxgap=10.0):
        stats['placed'] += 1
        if size < 1.0:
            stats['small'].append('board id')
        break
else:
    SIZE[0] = 1.0
    stats['hidden'].append('board id')
    REMOVE.append((board, bid))                    # board text cannot be hidden: drop it
SIZE[0] = 1.0                                      # back to normal text for everything else

# ---------------------------------------------------------------- 2c. forward arrows + bottom port map
# A flight controller must show which way is forward (the firmware's board orientation depends on it).
# Forward = +x, away from the Portenta's USB-C end.  The visible strips around the H7 are full of
# connectors, so the top arrow sits beside the IMU (seen during assembly, under the module) and the
# bottom arrow behind the IMU (always visible when the board is flipped).  Port names on the top are
# largely hidden once the H7 is fitted, so the bottom also carries each connector's name, printed
# behind that connector.
FWD_NEAR = {pcbnew.F_Cu: (45.0, 20.0), pcbnew.B_Cu: (34.0, 23.3)}
for d in board.GetDrawings():                      # previous top arrow (bottom ones went with the QR)
    if d.GetLayer() == pcbnew.F_SilkS and (d.GetClass() == 'PCB_SHAPE' or
                                           (d.GetClass() == 'PCB_TEXT' and d.GetText() == 'FWD')):
        REMOVE.append((board, d))


def silk_seg(layer, a, b, w=0.25):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(pcbnew.VECTOR2I(MM(a[0]), MM(a[1])))
    s.SetEnd(pcbnew.VECTOR2I(MM(b[0]), MM(b[1])))
    s.SetWidth(MM(w))
    s.SetLayer(layer)
    board.Add(s)


def silk_poly(layer, pts):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_POLY)
    s.SetPolyPoints([pcbnew.VECTOR2I(MM(x), MM(y)) for x, y in pts])
    s.SetFilled(True)
    s.SetWidth(MM(SILK_W))                         # outline too: JLCDFM wants >= 0.153 mm silk lines
    s.SetLayer(layer)
    board.Add(s)


for side, (ax, ay) in FWD_NEAR.items():
    W, H = 8.4, 1.7                                # "FWD" + 5 mm arrow, centred on (cx, cy)
    best = None
    for k in range(0, 41):
        for dx in [i * 0.25 for i in range(-24, 25)]:
            for dy in (k * 0.25, -k * 0.25):
                cx, cy = ax + dx, ay + dy
                r = (cx - W / 2, cy - H / 2, cx + W / 2, cy + H / 2)
                if r[0] < BX0 + 0.5 or r[2] > BX1 - 0.5 or r[1] < BY0 + 0.5 or r[3] > BY1 - 0.5:
                    continue
                if any(hit(r, o) for o in obst[side]) or any(hit(r, o) for o in placed[side]):
                    continue
                d = math.hypot(dx, dy)
                if best is None or d < best[0]:
                    best = (d, cx, cy, r)
        if best is not None and best[0] <= k * 0.25:
            break
    if best is None:
        stats['hidden'].append('forward arrow (%s)' % ('top' if side == pcbnew.F_Cu else 'bottom'))
        continue
    _, cx, cy, r = best
    layer = SIDES[side]
    x0 = cx - W / 2
    silk_seg(layer, (x0 + 3.2, cy), (x0 + 7.0, cy))                      # shaft
    silk_poly(layer, [(x0 + 6.6, cy - 0.65), (x0 + 8.3, cy), (x0 + 6.6, cy + 0.65)])   # head points to +x
    t = pcbnew.PCB_TEXT(board)
    t.SetText('FWD')
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(1.0), MM(1.0)))
    t.SetTextThickness(MM(SILK_W))
    if side == pcbnew.B_Cu:
        t.SetMirrored(True)
    t.SetPosition(pcbnew.VECTOR2I(MM(x0 + 1.45), MM(cy)))
    board.Add(t)
    placed[side].append((r[0] - 0.05, r[1] - 0.05, r[2] + 0.05, r[3] + 0.05))
    stats['placed'] += 1
    print('forward arrow on %s at (%.2f, %.2f)' % ('top' if side == pcbnew.F_Cu else 'bottom', cx, cy))

PORT_MAP = {'J4': 'GPS', 'J5': 'TELEM1', 'J6': 'RC', 'J7': 'UART3', 'J8': 'CAN', 'J9': 'I2C',
            'J10': 'ESC 1=VBAT'}
for ref, name in PORT_MAP.items():
    fp = board.FindFootprintByReference(ref)
    if fp is None or fp.GetLayer() != pcbnew.F_Cu:
        continue
    t = pcbnew.PCB_TEXT(board)
    t.SetText(name)
    t.SetLayer(pcbnew.B_SilkS)
    t.SetMirrored(True)
    board.Add(t)
    do(pcbnew.B_Cu, t, rect_of(fp.GetBoundingBox(False, False)), 'port map "%s"' % name, maxgap=4.0)

for d in board.GetDrawings():
    if d.GetClass() == 'PCB_TEXT' and d.GetLayer() == pcbnew.F_SilkS and d.GetText() == 'FWD':
        continue                                       # placed above with its arrow
    if d.GetClass() == 'PCB_TEXT' and d.GetLayer() == pcbnew.F_SilkS:
        r = rect_of(d.GetBoundingBox())
        c = ((r[0] + r[2]) / 2, (r[1] + r[3]) / 2)
        do(pcbnew.F_Cu, d, (c[0], c[1], c[0], c[1]), 'board "%s"' % d.GetText(), forced=c, maxgap=4.0)

SHORT = {'LED_STRIP': 'LED', 'BUZZ_N': 'BUZ'}


def prio(fp):
    r = fp.GetReference()
    return (0 if r.startswith('TP') else 1 if r.startswith('J') else 2 if r[0] in 'UDQL' else 3, r)


for fp in sorted(board.GetFootprints(), key=prio):
    ref = fp.GetReference()
    side = fp.GetLayer()
    jobs = []
    if ref.startswith('H') or ref.startswith('FID') or ref in ('J1', 'J2'):   # holes / fiducials: no label
        fp.Reference().SetVisible(False)
        continue
    if ref.startswith('TP'):                          # show what the pad is, not its number
        fp.Reference().SetVisible(False)
        if fp.Value().GetText() in SHORT:
            fp.Value().SetText(SHORT[fp.Value().GetText()])
        jobs.append(fp.Value())
    elif ref.startswith('J') and ref != 'J11' or ref == 'JP1':
        jobs += [fp.Value(), fp.Reference()]
    else:
        jobs.append(fp.Reference())
    anchor = rect_of(fp.GetBoundingBox(False, False))
    for t in jobs:
        t.SetLayer(SIDES[side])
        kw = {}
        if side == pcbnew.F_Cu and ref.startswith('TP') and t.GetText() in BLOCK:
            for pad in fp.Pads():
                pr = rect_of(pad.GetBoundingBox())
            kw['forced'] = ((pr[0] + pr[2]) / 2, pr[1] - SILK_CLR - 0.05 - 0.5)     # just above its own pad
        do(side, t, anchor, '%s "%s"' % (ref, t.GetText()), **kw)

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
for parent, item in REMOVE:
    parent.Remove(item)
pcbnew.SaveBoard(PCB, board)
print('texts placed:', stats['placed'])
print('hidden (no room):', stats['hidden'])
print('placed at 0.8 mm:', stats['small'])
board = pcbnew.LoadBoard(PCB)
pcbnew.WriteDRCReport(board, os.path.join(ROOT, 'out', 'drc.rpt'), pcbnew.EDA_UNITS_MILLIMETRES, True)
