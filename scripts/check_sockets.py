"""Check the H7 sockets J1/J2 against Arduino's own Portenta Breakout (ASX00031), pad by pad.

  "C:\\Program Files\\KiCad\\7.0\\bin\\python.exe" scripts/check_sockets.py

docs/portenta_breakout_sockets.json holds the Breakout's two DF40HC(3.5)-80DS-0.4V(51) receptacles J1/J2
(pad centre x, y in mm with y up, pad size, Altium layer, net name), read from Arduino's Altium layout
(ASX00031-cad-files.zip, docs.arduino.cc) by scripts/altium_pads.py.  Both boards are compared in the frame
x = J1 -> J2 centre, y = 90 deg counter-clockwise from x, seen from the top (the side the H7 sits on), so the
result does not depend on where the sockets sit on either board.  It also checks the pads against Hirose's
recommended pattern (EDC-337747-51-01) and that no other net has F.Cu copper in the drawing's hatched note-2
area (each pad column extended inwards to 0.46 mm off the centre line).  Exit code 0 = same pin-1 corners, numbering
and pad positions as Arduino's board, Hirose's land pattern, hatched area clear.
"""
import os
import sys
import json
import math
import pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = pcbnew.ToMM
TOL = 0.01                                          # mm
REF = json.load(open(os.path.join(ROOT, 'docs', 'portenta_breakout_sockets.json')))
board = pcbnew.LoadBoard(os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb'))

ours, theirs, brk_net = {}, {}, {}
for ref in ('J1', 'J2'):
    fp = board.FindFootprintByReference(ref)
    ours[ref] = {p.GetNumber(): (T(p.GetPosition().x), -T(p.GetPosition().y),
                                 sorted((round(T(p.GetSize().x), 3), round(T(p.GetSize().y), 3))),
                                 fp.GetLayer() == pcbnew.F_Cu) for p in fp.Pads()}
    theirs[ref] = {k: (v[0], v[1], sorted(v[2:4]), v[4] == 1) for k, v in REF[ref]['pads'].items()}
    brk_net[ref] = {k: v[5] for k, v in REF[ref]['pads'].items()}


def frame(pads):
    """pad positions relative to their socket centre, in the J1 -> J2 frame"""
    c = {r: (sum(v[0] for v in pads[r].values()) / len(pads[r]), sum(v[1] for v in pads[r].values()) / len(pads[r]))
         for r in ('J1', 'J2')}
    dx, dy = c['J2'][0] - c['J1'][0], c['J2'][1] - c['J1'][1]
    L = math.hypot(dx, dy)
    ux, uy = dx / L, dy / L
    return {r: {k: ((v[0] - c[r][0]) * ux + (v[1] - c[r][1]) * uy, -(v[0] - c[r][0]) * uy + (v[1] - c[r][1]) * ux)
                for k, v in pads[r].items()} for r in ('J1', 'J2')}, L


ro, Lo = frame(ours)
rt, Lt = frame(theirs)
ok = abs(Lo - Lt) < TOL
print('J1 -> J2 centre distance: ours %.3f mm, Breakout %.3f mm' % (Lo, Lt))
for ref in ('J1', 'J2'):
    same_pins = set(ro[ref]) == set(rt[ref])
    worst = max(math.hypot(ro[ref][k][0] - rt[ref][k][0], ro[ref][k][1] - rt[ref][k][1]) for k in rt[ref]) \
        if same_pins else 99.0
    top = all(v[3] for v in ours[ref].values()) and all(v[3] for v in theirs[ref].values())
    size = all(ours[ref][k][2] == theirs[ref][k][2] for k in rt[ref]) if same_pins else False
    ok = ok and same_pins and worst < TOL and top and size
    print('%s: %d pads (Breakout %d), both on top: %s, same pad sizes: %s, worst position difference %.4f mm' % (
        ref, len(ro[ref]), len(rt[ref]), top, size, worst))
    for k in ('1', '2', '79', '80'):
        print('   pin %-2s ours (%+.3f, %+.3f)   Breakout (%+.3f, %+.3f)' % (
            k, ro[ref][k][0], ro[ref][k][1], rt[ref][k][0], rt[ref][k][1]))

print('\nH7 pins this carrier uses - H7 signal (design.py) / our net / net on Arduino\'s Breakout:')
for ref, names, nets in (('J1', D.J1_NAMES, D.J1_NETS), ('J2', D.J2_NAMES, D.J2_NETS)):
    for n in sorted(nets):
        print('  %s-%-2d  %-18s %-12s %s' % (ref, n, names.get(n, '?'), nets[n], brk_net[ref].get(str(n), '?')))
# Hirose EDC-337747-51-01 recommended pattern: pads 0.2 x 0.7 mm at 0.4 mm pitch, outer ends 3.78 mm apart,
# inner ends 2.38 mm apart (pad centres +/-1.54 mm).  Note 2: the hatched area - each pad column extended inwards
# from 1.19 to 0.46 mm off the centre line (0.92 MAX) - takes no copper other than the same circuit.
print('\nHirose land pattern and note-2 area (F.Cu, foreign copper only):')
SAMPLES = [(s * (0.46 + i * (1.19 - 0.46) / 6), j * 0.05) for s in (-1, 1) for i in range(7) for j in (-2, -1, 0, 1, 2)]
for ref in ('J1', 'J2'):
    fp = board.FindFootprintByReference(ref)
    a = math.radians(fp.GetOrientationDegrees())
    cx, cy = T(fp.GetPosition().x), T(fp.GetPosition().y)
    to_board = lambda lx, ly: pcbnew.VECTOR2I(pcbnew.FromMM(cx + lx * math.cos(a) + ly * math.sin(a)),
                                              pcbnew.FromMM(cy - lx * math.sin(a) + ly * math.cos(a)))
    local = {}
    for p in fp.Pads():
        dx, dy = T(p.GetPosition().x) - cx, T(p.GetPosition().y) - cy
        local[p] = (dx * math.cos(a) - dy * math.sin(a), dx * math.sin(a) + dy * math.cos(a))
    land = all(abs(abs(lx) - 1.54) < TOL and sorted((T(p.GetSize().x), T(p.GetSize().y))) == [0.2, 0.7]
               for p, (lx, ly) in local.items())
    land = land and abs(max(ly for lx, ly in local.values()) - min(ly for lx, ly in local.values()) - 15.6) < TOL
    bad = set()
    for p, (lx, ly) in local.items():
        for sx, dy in SAMPLES:
            if (sx > 0) != (lx > 0):
                continue
            pt = to_board(sx, ly + dy)
            for t in board.GetTracks():
                if t.IsOnLayer(pcbnew.F_Cu) and t.GetNetCode() != p.GetNetCode() and t.HitTest(pt, 0):
                    bad.add((t.GetNetname(), p.GetNumber()))
            for z in board.Zones():
                if not z.GetIsRuleArea() and z.IsOnLayer(pcbnew.F_Cu) and z.GetNetCode() != p.GetNetCode() \
                        and z.GetFilledPolysList(pcbnew.F_Cu).Contains(pt):
                    bad.add((z.GetNetname() + ' pour', p.GetNumber()))
            for f in board.GetFootprints():
                for q in f.Pads():
                    if q.IsOnLayer(pcbnew.F_Cu) and q.GetNetCode() != p.GetNetCode() and q.HitTest(pt):
                        bad.add((f.GetReference() + '-' + q.GetNumber(), p.GetNumber()))
    ok = ok and land and not bad
    print('  %s: pads per drawing: %s; foreign copper in the hatched area: %s' % (
        ref, land, ', '.join('%s at pin %s' % b for b in sorted(bad)) or 'none'))

print('\nPASS: J1/J2 match the Portenta Breakout pad for pad and Hirose\'s land pattern' if ok else
      '\nFAIL: J1/J2 differ from the Portenta Breakout or Hirose\'s land pattern')
sys.exit(0 if ok else 1)
