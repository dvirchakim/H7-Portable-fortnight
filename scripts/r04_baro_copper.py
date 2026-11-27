"""R0.4 sensor swap: hand-placed copper for the BMP581 (U4, 0.5 mm pitch LGA-10 at 44, 13) and C14.
Removes what the grid router laid around the part and puts in short, straight escapes; every pad leaves
outwards, nothing runs under the body (Bosch).  Run once after swap_fp.py U4 / C14 (kept as the record)."""
import os
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
T, MM = pcbnew.ToMM, pcbnew.FromMM
b = pcbnew.LoadBoard(PCB)
KEEP_OUT_X, BOX = 43.0, (42.0, 9.7, 46.5, 14.6)        # router copper inside this box goes


def inbox(x, y):
    return BOX[0] <= x <= BOX[2] and BOX[1] <= y <= BOX[3]


nets = ('GND', '+3V3_SENS', 'I2C0_SDA', 'I2C0_SCL')
gone = 0
for t in list(b.GetTracks()):
    if t.GetNetname() not in nets:
        continue
    if t.Type() == pcbnew.PCB_VIA_T:
        p = t.GetPosition()
        hit = inbox(T(p.x), T(p.y)) and not (abs(T(p.x) - 45.85) < 0.01 and abs(T(p.y) - 13.05) < 0.01)
    else:
        s, e = t.GetStart(), t.GetEnd()
        hit = t.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu) and (inbox(T(s.x), T(s.y)) or inbox(T(e.x), T(e.y)))
        if t.GetNetname() == '+3V3_SENS' and t.GetLayer() == pcbnew.B_Cu:
            hit = False                                     # the B.Cu sensor-rail feed stays
        if t.GetNetname() == 'I2C0_SDA' and min(T(s.x), T(e.x)) < 43.7:
            hit = False                                     # the SDA run to the west stays
        if t.GetNetname() == 'I2C0_SCL' and t.GetLayer() == pcbnew.B_Cu:
            hit = False
    if hit:
        b.Remove(t)
        gone += 1


def trk(net, w, *pts):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(MM(x0), MM(y0)))
        t.SetEnd(pcbnew.VECTOR2I(MM(x1), MM(y1)))
        t.SetWidth(MM(w))
        t.SetLayer(pcbnew.F_Cu)
        t.SetNet(b.FindNet(net))
        b.Add(t)


def via(net, x, y):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    v.SetWidth(MM(0.45))
    v.SetDrill(MM(0.2))
    v.SetNet(b.FindNet(net))
    b.Add(v)


E = 0.7625
P = {n: (44 + x, 13 + y) for n, (x, y) in {
    '1': (-E, -0.25), '2': (-E, 0.25), '3': (-0.5, E), '4': (0, E), '5': (0.5, E),
    '6': (E, 0.25), '7': (E, -0.25), '8': (0.5, -E), '9': (0, -E), '10': (-0.5, -E)}.items()}
C14_1, C14_2 = (43.48, 11.1), (42.52, 11.1)
# +3V3_SENS: VDD (10) straight up to C14, VDDIO (1) out to a via on the B.Cu sensor-rail feed, CSB (6) east to its via
trk('+3V3_SENS', 0.2, P['10'], C14_1)
trk('+3V3_SENS', 0.2, (43.5, 11.9), (42.55, 11.9), (42.55, 12.6))
trk('+3V3_SENS', 0.2, P['1'], (42.7, 12.75), (42.55, 12.6))
via('+3V3_SENS', 42.55, 12.6)                          # lands on the B.Cu run (43, 13.05)-(42, 12.05)
trk('+3V3_SENS', 0.2, P['6'], (45.65, 13.25), (45.85, 13.05))
# I2C: SCK (2) west to the SCL via, SDI (4) south then west
trk('I2C0_SCL', 0.15, P['2'], (42.95, 13.25), (42.85, 13.15), (40.65, 13.15))
via('I2C0_SCL', 40.65, 13.15)                          # on the In2.Cu SCL run along x = 40.65
trk('I2C0_SDA', 0.15, P['4'], (44.0, 14.05), (43.85, 14.2), (43.75, 14.2))
# GND: each pad to its own via into the In1 plane
trk('GND', 0.15, P['3'], (42.75, 13.7))
via('GND', 42.75, 13.7)
trk('GND', 0.15, P['5'], (44.5, 14.0), (44.65, 14.15), (44.65, 14.45))
via('GND', 44.65, 14.45)
trk('GND', 0.15, P['9'], (44.0, 11.75), (44.5, 11.75), P['8'])
trk('GND', 0.15, (44.5, 11.75), (45.5, 11.75), (45.5, 12.55))     # joins pad 7's run (SDC_D0 passes under on B.Cu)
trk('GND', 0.15, P['7'], (45.3, 12.75), (45.5, 12.55), (47.65, 12.55))
trk('GND', 0.25, C14_2, (42.0, 11.1))
via('GND', 42.0, 11.1)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
print('removed', gone, 'router items; hand copper placed')
