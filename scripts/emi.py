"""EMI layout review (pre-compliance from the design files; it does not replace a measurement).

  "C:\\Program Files\\KiCad\\7.0\\bin\\python.exe" scripts/emi.py      -> prints a summary, writes out/emi.rpt

Checks the layout faults that cause most radiated / conducted emissions on a board like this:
  1. return path   - fast signals on an outer layer must run over unbroken plane on the next layer
                     (F.Cu -> In1 GND, B.Cu -> In2 +5V); tracks on the inner layers are themselves
                     the cuts in those planes
  2. layer changes - a fast signal that changes reference plane (In1 GND <-> In2 +5V) returns through
                     the nearest decoupling capacitor; it should be close
  3. board edge    - fast signals close to the edge radiate (fringing fields)
  4. edge stitching- GND vias round the perimeter keep the planes from radiating at the edge
  5. buck loops    - the LMR33630 input loop (VIN cap -> VIN pin -> GND pin -> cap) and the switch-node
                     copper area are the strongest emitters on the board
"""
import os
import math
import sys
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
T, MM = pcbnew.ToMM, pcbnew.FromMM

# fast edges: clocks, SDMMC, SPI, DShot motor lines, CAN, UARTs at MBaud, I2C
FAST = ['SDC_CLK', 'SPI1_SCK', 'SDC_CMD', 'SDC_D0', 'SDC_D1', 'SDC_D2', 'SDC_D3', 'SPI1_COPI', 'SPI1_CIPO',
        'IMU_CS', 'M1', 'M2', 'M3', 'M4', 'S5', 'S6', 'LED_STRIP', 'CANH', 'CANL', 'CAN1_TX', 'CAN1_RX']
CLOCKS = ['SDC_CLK', 'SPI1_SCK']
REF = {pcbnew.F_Cu: (pcbnew.In1_Cu, 'GND'), pcbnew.B_Cu: (pcbnew.In2_Cu, '+5V')}
STEP = 0.1

board = pcbnew.LoadBoard(PCB)
bb = board.GetBoardEdgesBoundingBox()
BX0, BY0, BX1, BY1 = T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())
fills = {}
for i in range(board.GetAreaCount()):
    z = board.GetArea(i)
    if z.GetIsRuleArea():
        continue
    for l in (pcbnew.In1_Cu, pcbnew.In2_Cu):
        if z.IsOnLayer(l):
            fills.setdefault((l, z.GetNetname()), []).append(z.GetFilledPolysList(l))


def on_plane(layer, net, x, y):
    p = pcbnew.VECTOR2I(MM(x), MM(y))
    return any(f.Contains(p) for f in fills.get((layer, net), []))


tracks, vias = [], []
for t in board.GetTracks():
    if t.Type() == pcbnew.PCB_VIA_T:
        vias.append((t.GetNetname(), T(t.GetPosition().x), T(t.GetPosition().y)))
    else:
        tracks.append((t.GetNetname(), t.GetLayer(), (T(t.GetStart().x), T(t.GetStart().y)),
                       (T(t.GetEnd().x), T(t.GetEnd().y)), T(t.GetWidth())))
lines, summary = [], []

# ---------------------------------------------------------------- 1. return path
over_void = {}
inner = {}
for net, l, a, b, w in tracks:
    L = math.hypot(b[0] - a[0], b[1] - a[1])
    if l in (pcbnew.In1_Cu, pcbnew.In2_Cu):
        inner.setdefault(board.GetLayerName(l), {}).setdefault(net, 0.0)
        inner[board.GetLayerName(l)][net] += L
        continue
    if net not in FAST:
        continue
    rl, rn = REF[l]
    n = max(1, int(L / STEP))
    bad = sum(1 for i in range(n + 1) if not on_plane(rl, rn, a[0] + (b[0] - a[0]) * i / n, a[1] + (b[1] - a[1]) * i / n))
    tot = over_void.setdefault(net, [0.0, 0.0])
    tot[0] += L
    tot[1] += L * bad / (n + 1)
lines.append('1. FAST SIGNALS OVER A PLANE VOID (outer-layer length with no plane underneath)')
worst = 0.0
for net, (L, v) in sorted(over_void.items(), key=lambda x: -x[1][1]):
    if v > 0.05:
        lines.append('   %-10s %5.1f of %5.1f mm (%2.0f %%)%s' % (net, v, L, 100 * v / L, '   <-- clock' if net in CLOCKS else ''))
    worst = max(worst, v)
summary.append(('fast-signal length over plane voids', '%.1f mm worst net' % worst,
                'OK' if worst < 2 else 'REVIEW'))
lines.append('   signal copper on the plane layers (each track is a slot in that plane):')
for ln, d in sorted(inner.items()):
    lines.append('   %s: %d nets, %.0f mm  (%s)' % (ln, len(d), sum(d.values()),
                 ', '.join('%s %.0f' % (k, v) for k, v in sorted(d.items(), key=lambda x: -x[1])[:8])))
summary.append(('signal track length on In1 (GND plane)', '%.0f mm' % sum(inner.get('In1.Cu', {}).values()),
                'OK' if sum(inner.get('In1.Cu', {}).values()) < 20 else 'REVIEW'))

# ---------------------------------------------------------------- 2. layer changes
# A fast signal that changes between F.Cu (reference In1 GND) and B.Cu or In2 (reference In2 +5V)
# moves its return current from one plane to the other; it crosses through the nearest decoupling
# capacitor (GND to +5V / +3V3).  Far away = a large loop.
lines.append('')
lines.append('2. FAST-SIGNAL VIAS: DISTANCE TO THE NEAREST DECOUPLING CAPACITOR (return path between planes)')
caps = []
for fp in board.GetFootprints():
    if not fp.GetReference().startswith('C'):
        continue
    nets = set(p.GetNetname() for p in fp.Pads())
    if 'GND' in nets and nets & {'+5V', '+3V3', '+3V3_SENS'}:
        caps.append((fp.GetReference(), T(fp.GetPosition().x), T(fp.GetPosition().y)))
far, nfast = 0, 0
for net, x, y in vias:
    if net not in FAST:
        continue
    nfast += 1
    d, ref = min((math.hypot(x - cx, y - cy), r) for r, cx, cy in caps)
    if d > 5.0:
        far += 1
        lines.append('   %-10s via (%.2f, %.2f): nearest bypass cap %s at %.1f mm' % (net, x, y, ref, d))
summary.append(('fast-signal vias > 5 mm from a bypass cap', '%d of %d' % (far, nfast), 'OK' if far == 0 else 'REVIEW'))

# ---------------------------------------------------------------- 3. board edge
lines.append('')
lines.append('3. FAST SIGNALS CLOSER THAN 1.0 mm TO THE BOARD EDGE')
near = {}
for net, l, a, b, w in tracks:
    if net not in FAST:
        continue
    for p in (a, b):
        d = min(p[0] - BX0, BX1 - p[0], p[1] - BY0, BY1 - p[1]) - w / 2
        if d < 1.0:
            near[net] = min(near.get(net, 9), d)
for net, d in sorted(near.items()):
    lines.append('   %-10s %.2f mm' % (net, d))
summary.append(('fast signals within 1 mm of the edge', '%d nets' % len(near), 'OK' if not near else 'REVIEW'))

# ---------------------------------------------------------------- 4. edge stitching
lines.append('')
lines.append('4. GND VIA STITCHING ALONG THE BOARD EDGE (vias within 2.5 mm of the edge)')
edge = []
for x, y in [(x, y) for n, x, y in vias if n == 'GND']:
    d = min(x - BX0, BX1 - x, y - BY0, BY1 - y)
    if d < 2.5:
        per = BX1 - BX0
        ph = BY1 - BY0
        if y - BY0 == d:
            s = x - BX0
        elif BX1 - x == d:
            s = per + (y - BY0)
        elif BY1 - y == d:
            s = per + ph + (BX1 - x)
        else:
            s = 2 * per + ph + (BY1 - y)
        edge.append(s)
edge.sort()
perim = 2 * ((BX1 - BX0) + (BY1 - BY0))
gaps = [b - a for a, b in zip(edge, edge[1:])] + ([perim - edge[-1] + edge[0]] if edge else [perim])
mg = max(gaps) if gaps else perim
lines.append('   %d edge GND vias, largest gap %.1f mm (lambda/20 at 1 GHz = 15 mm, at 3 GHz = 5 mm)' % (len(edge), mg))
summary.append(('largest gap between edge GND vias', '%.1f mm' % mg, 'OK' if mg <= 15 else 'REVIEW'))

# ---------------------------------------------------------------- 5. buck converter
lines.append('')
lines.append('5. BUCK CONVERTER (U1 LMR33630)')
u1 = board.FindFootprintByReference('U1')
pin = {}
for p in u1.Pads():
    pin.setdefault(p.GetNetname(), []).append((T(p.GetPosition().x), T(p.GetPosition().y)))
vin = [n for n in pin if n == 'VBAT']
loop = None
for cref in ('C1', 'C2', 'C3'):
    fp = board.FindFootprintByReference(cref)
    if not fp:
        continue
    cp = {p.GetNetname(): (T(p.GetPosition().x), T(p.GetPosition().y)) for p in fp.Pads()}
    if 'VBAT' in cp and 'GND' in cp and 'VBAT' in pin and 'GND' in pin:
        dv = min(math.hypot(cp['VBAT'][0] - x, cp['VBAT'][1] - y) for x, y in pin['VBAT'])
        dg = min(math.hypot(cp['GND'][0] - x, cp['GND'][1] - y) for x, y in pin['GND'])
        lines.append('   input cap %s: VIN pad %.1f mm from U1 VIN, GND pad %.1f mm from U1 GND' % (cref, dv, dg))
        loop = dv + dg if loop is None else min(loop, dv + dg)
if loop is not None:
    summary.append(('buck input loop (cap to U1, VIN + GND path)', '%.1f mm' % loop, 'OK' if loop < 4 else 'REVIEW'))
sw = 0.0
for net, l, a, b, w in tracks:
    if net == 'BUCK_SW':
        sw += math.hypot(b[0] - a[0], b[1] - a[1]) * w
for fp in board.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname() == 'BUCK_SW':
            sw += T(p.GetSize().x) * T(p.GetSize().y)
lines.append('   switch-node (BUCK_SW) copper: %.1f mm2 (keep small: it is the antenna)' % sw)
summary.append(('buck switch-node copper area', '%.1f mm2' % sw, 'OK' if sw < 25 else 'REVIEW'))

out = ['%-46s %-20s %s' % ('check', 'result', 'verdict')] + ['%-46s %-20s %s' % s for s in summary]
open(os.path.join(ROOT, 'out', 'emi.rpt'), 'w').write('\n'.join(out + [''] + lines) + '\n')
print('\n'.join(out))
