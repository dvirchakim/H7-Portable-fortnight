"""JLCPCB placement (CPL) file from the board itself, corrected to JLCPCB's own part footprints.

  "C:\\Program Files\\KiCad\\7.0\\bin\\python.exe" scripts/jlc_place.py   -> fab/jlcpcb_cpl.csv, fab/placement_check.csv

JLCPCB places each part with its EasyEDA library footprint.  scripts/jlc_corrections.json holds, per LCSC
part, how that footprint sits relative to our KiCad library footprint (measured by fitting the two pad
layouts, see README): rotation `deg` and the position (tx, ty, mm) of JLC's origin in our footprint's
frame.  Polarised two-pin parts were matched by function (cathode on cathode), not by pad number.

Geometry (y down, R(a) = counter-clockwise as seen from the top):
  KiCad   top:    pad = pos + R(phi) L          bottom: pad = pos + R(phi) My L        (My: y -> -y)
  JLC     top:    pad = mid + R(theta) E        bottom: pad = mid + Mx R(theta) E      (Mx: x -> -x;
          rotation seen from the bottom - the convention of the kicad-jlcpcb-tools plugin)
  with L = R(deg) E + t:   top theta = phi + deg,  bottom theta = 180 - phi + deg,  mid = pos + R(phi) [My] t
"""
import os
import csv
import json
import math
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
STD = r'C:\Program Files\KiCad\7.0\share\kicad\footprints'
T = pcbnew.ToMM
COR = json.load(open(os.path.join(ROOT, 'scripts', 'jlc_corrections.json')))


def rot(v, a):
    c, s = math.cos(math.radians(a)), math.sin(math.radians(a))
    return (v[0] * c + v[1] * s, -v[0] * s + v[1] * c)


FPS = {r['Ref']: r['Footprint'] for r in csv.DictReader(open(os.path.join(ROOT, 'bom_placement.csv')))}
lcsc = {}
for r in csv.DictReader(open(os.path.join(ROOT, 'fab', 'jlcpcb_bom.csv'))):
    for ref in r['Designator'].split(','):
        lcsc[ref] = r['LCSC Part #']
board = pcbnew.LoadBoard(PCB)
rows, checks, worst = [], [], 0.0
for fp in sorted(board.GetFootprints(), key=lambda f: f.GetReference()):
    ref = fp.GetReference()
    if ref not in lcsc:
        continue
    part = lcsc[ref]
    if part not in COR:
        raise SystemExit('no placement correction for %s (%s) - measure it first' % (ref, part))
    deg, tx, ty = COR[part]['deg'], COR[part]['tx'], COR[part]['ty']
    bottom = fp.GetLayer() == pcbnew.B_Cu
    phi = fp.GetOrientationDegrees()
    pos = (T(fp.GetPosition().x), T(fp.GetPosition().y))
    # self-check: our geometry model must reproduce KiCad's pad positions from the library footprint
    lib, name = str(fp.GetFPID().GetLibNickname()), str(fp.GetFPID().GetLibItemName())
    if not lib:                                    # footprint placed by script without a library id
        lib, name = FPS[ref].split(':')
    libfp = pcbnew.FootprintLoad(os.path.join(ROOT, 'fc.pretty') if lib == 'fc' else os.path.join(STD, lib + '.pretty'), name)
    local = {}
    for p in libfp.Pads():                  # several pads may share a number (MP, shield)
        local.setdefault(p.GetNumber(), []).append((T(p.GetPosition().x), T(p.GetPosition().y)))
    err = 0.0
    for p in fp.Pads():
        best = 99.0
        for L in local[p.GetNumber()]:
            if bottom:
                L = (L[0], -L[1])
            q = rot(L, phi)
            best = min(best, math.hypot(pos[0] + q[0] - T(p.GetPosition().x), pos[1] + q[1] - T(p.GetPosition().y)))
        err = max(err, best)
    worst = max(worst, err)
    t = (tx, -ty) if bottom else (tx, ty)
    d = rot(t, phi)
    mid = (pos[0] + d[0], pos[1] + d[1])
    theta = ((180 - phi + deg) if bottom else (phi + deg)) % 360
    rows.append([ref, '%.4fmm' % mid[0], '%.4fmm' % -mid[1], 'Bottom' if bottom else 'Top', '%g' % round(theta, 3)])
    checks.append([ref, part, 'B' if bottom else 'F', '%g' % phi, deg, '%.3f' % math.hypot(tx, ty), '%g' % round(theta, 3),
                   '%.4f' % err, COR[part].get('note', '')])
with open(os.path.join(ROOT, 'fab', 'jlcpcb_cpl.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
    w.writerows(rows)
with open(os.path.join(ROOT, 'fab', 'placement_check.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Ref', 'LCSC', 'Side', 'KiCad rot', 'JLC footprint correction', 'centre offset mm', 'CPL rot',
                'model error mm', 'note'])
    w.writerows(checks)
missing = sorted(set(lcsc) - set(r[0] for r in rows))
print('placed %d parts, geometry self-check worst error %.4f mm%s' % (len(rows), worst,
      ('; NOT ON BOARD: ' + ', '.join(missing)) if missing else ''))
if worst > 0.01:
    raise SystemExit('geometry model does not reproduce KiCad pad positions')
