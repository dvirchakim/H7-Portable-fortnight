"""EMI fixes that need no re-routing (run after routing, before vias.py / finish.py):

  0. a 2.5 mm GND ring round the edge of the outer layers
  1. GND stitching vias round the board edge, no more than EDGE_PITCH apart (lambda/20 at 3 GHz = 5 mm),
     tying the ring to the In1 GND plane
  (Return vias beside signal vias are not added: here a signal changing F.Cu <-> B.Cu changes its
   reference from In1 GND to In2 +5V, so its return current crosses through decoupling capacitors,
   not through a GND via.  scripts/emi.py reports the distance to the nearest one.)

Every new via keeps 0.18 mm to other-net copper on all layers, 0.2 mm to pads of its own net,
stays out of the mounting-hole and socket keep-outs, and 0.5 mm from the board edge.

  "C:\\Program Files\\KiCad\\7.0\\bin\\python.exe" scripts/emi_fix.py
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
VIA_D, VIA_DRILL = 0.5, 0.2
CLR, SAME = 0.18, 0.2
EDGE_PITCH, RET_R = 5.0, 1.0
FAST = ['SDC_CLK', 'SPI1_SCK', 'SDC_CMD', 'SDC_D0', 'SDC_D1', 'SDC_D2', 'SDC_D3', 'SPI1_COPI', 'SPI1_CIPO',
        'IMU_CS', 'M1', 'M2', 'M3', 'M4', 'S5', 'S6', 'LED_STRIP', 'CANH', 'CANL', 'CAN1_TX', 'CAN1_RX']

board = pcbnew.LoadBoard(PCB)
bb = board.GetBoardEdgesBoundingBox()
BX0, BY0, BX1, BY1 = T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())
items, holes, rings = dfm.load(board)
keep, sock = [], []
for i in range(board.GetAreaCount()):
    z = board.GetArea(i)
    if z.GetIsRuleArea():
        r = z.GetBoundingBox()
        if z.GetZoneName() == 'SOCKET_KEEPOUT':
            sock.append((T(r.GetLeft()), T(r.GetTop()), T(r.GetRight()), T(r.GetBottom())))
        else:
            keep.append(((T(r.GetCenter().x), T(r.GetCenter().y)), T(r.GetWidth()) / 2))
gnd = board.FindNet('GND')


def free(c):
    r = VIA_D / 2
    if not (BX0 + 0.5 + r <= c[0] <= BX1 - 0.5 - r and BY0 + 0.5 + r <= c[1] <= BY1 - 0.5 - r):
        return False
    for kc, kr in keep:
        if math.hypot(c[0] - kc[0], c[1] - kc[1]) < kr + r + 0.1:
            return False
    for s in sock:
        if dfm.seg_rect(c, c, s) < r + 0.05:
            return False
    for x, y, hr in [(h[0][0], h[0][1], h[1]) for h in holes]:
        if math.hypot(c[0] - x, c[1] - y) < hr + r + 0.25:        # hole to hole
            return False
    probe = dfm.Item('v', 'GND', 0, 'new', c=c, r=r)
    for li in range(4):
        for it in items[li]:
            if it.box[0] - 0.5 > probe.box[2] or probe.box[0] - 0.5 > it.box[2] or \
               it.box[1] - 0.5 > probe.box[3] or probe.box[1] - 0.5 > it.box[3]:
                continue
            g = dfm.gap(probe, it)
            if it.net == 'GND':
                if it.kind == 'p' and g < SAME:
                    return False                          # no via in or right beside a GND pad
                if it.kind == 'v' and g < 0.2:
                    return False
            elif g < CLR + (0.05 if it.net in ('VBAT', '+5V_BUCK', 'BUCK_SW') else 0):
                return False
    return True


def add(c):
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(MM(c[0]), MM(c[1])))
    v.SetWidth(MM(VIA_D))
    v.SetDrill(MM(VIA_DRILL))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNet(gnd)
    board.Add(v)
    for li in range(4):
        items[li].append(dfm.Item('v', 'GND', li, 'new', c=c, r=VIA_D / 2))
    holes.append((c, VIA_DRILL / 2, 'via'))


# ---------------------------------------------------------------- 0. GND ring on the outer layers
# A 2.5 mm GND band round the edge of F.Cu and B.Cu (above the +5V pours in priority), tied to the
# In1 GND plane by the edge vias below: a fence that keeps the planes from radiating at the edge.
RING = 2.5
for zname, zlayer in (('GND_RING_F', pcbnew.F_Cu), ('GND_RING_B', pcbnew.B_Cu)):
    if any(board.GetArea(i).GetZoneName() == zname for i in range(board.GetAreaCount())):
        continue
    z = pcbnew.ZONE(board)
    z.SetLayer(zlayer)
    z.SetNetCode(gnd.GetNetCode())
    z.SetZoneName(zname)
    z.SetAssignedPriority(5)
    z.SetLocalClearance(MM(0.25))
    z.SetMinThickness(MM(0.2))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    ol = z.Outline()
    ol.NewOutline()
    for x, y in [(BX0 + 0.3, BY0 + 0.3), (BX1 - 0.3, BY0 + 0.3), (BX1 - 0.3, BY1 - 0.3), (BX0 + 0.3, BY1 - 0.3)]:
        ol.Append(MM(x), MM(y))
    ol.NewHole()
    for x, y in [(BX0 + RING, BY0 + RING), (BX0 + RING, BY1 - RING), (BX1 - RING, BY1 - RING), (BX1 - RING, BY0 + RING)]:
        ol.Append(MM(x), MM(y), 0, 0)
    board.Add(z)

# ---------------------------------------------------------------- 1. edge stitching
W, H = BX1 - BX0, BY1 - BY0
PER = 2 * (W + H)


def edge_point(s, inset):
    s %= PER
    if s < W:
        return (BX0 + s, BY0 + inset)
    s -= W
    if s < H:
        return (BX1 - inset, BY0 + s)
    s -= H
    if s < W:
        return (BX1 - s, BY1 - inset)
    s -= W
    return (BX0 + inset, BY1 - s)


def edge_pos(c):
    d = [c[1] - BY0, BX1 - c[0], BY1 - c[1], c[0] - BX0]
    k = d.index(min(d))
    return [c[0] - BX0, W + c[1] - BY0, W + H + BX1 - c[0], 2 * W + H + BY1 - c[1]][k], min(d)


existing = sorted(edge_pos(h[0])[0] for h in holes if h[2] == 'via' and edge_pos(h[0])[1] < 2.5
                  and any(it.kind == 'v' and it.net == 'GND' and it.c == h[0] for it in items[0]))
added_edge = 0
s = 0.0
last = existing[-1] - PER if existing else -EDGE_PITCH
nexts = list(existing)
while s < PER:
    while nexts and nexts[0] <= s:
        last = nexts.pop(0)
    nxt = nexts[0] if nexts else (existing[0] + PER if existing else PER + EDGE_PITCH)
    if s - last >= EDGE_PITCH * 0.8 or (nxt - last > EDGE_PITCH and s - last >= EDGE_PITCH / 2):
        for inset in (0.9, 1.2, 1.5, 1.8, 2.1):
            c = tuple(round(v, 3) for v in edge_point(s, inset))
            if free(c):
                add(c)
                added_edge += 1
                last = s
                break
    s += 0.25
edge_now = sorted(edge_pos(h[0])[0] for h in holes if h[2] == 'via' and edge_pos(h[0])[1] < 2.5
                  and any(it.kind == 'v' and it.net == 'GND' and it.c == h[0] for it in items[0]))
gaps = [b - a for a, b in zip(edge_now, edge_now[1:])] + [PER - edge_now[-1] + edge_now[0]]
print('edge GND vias added: %d (now %d, largest gap %.1f mm)' % (added_edge, len(edge_now), max(gaps)))

pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(PCB, board)
board = pcbnew.LoadBoard(PCB)
pcbnew.WriteDRCReport(board, os.path.join(ROOT, 'out', 'drc.rpt'), pcbnew.EDA_UNITS_MILLIMETRES, True)
