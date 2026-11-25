"""Carrier parts as coloured blocks (one per KiCad 3D model, from the STEP export), in the STEP frame
(X = KiCad x, Y = -KiCad y, board from Z 0 to 1.6), plus blocks for parts without a KiCad model.
Unfitted parts (R11, C15, U5) are left out.  usage: python carrierobj.py carrier.json out_basename"""
import json, sys
s = json.load(open(sys.argv[1]))
DNP = [(49.6, 15.0), (41.2, 27.0), (44.0, 27.0)]          # R11, C15, U5 (KiCad x, y)


def mat(fp):
    f = fp.upper()
    if f.startswith('R_'): return 'resistor'
    if f.startswith('C_'): return 'ceramic'
    if f.startswith('LED'): return 'led'
    if 'JST' in f: return 'nylon'
    if f.startswith('LGA-8'): return 'metal'            # MS5607: metal cap
    return 'ic'


boxes = []
for r in s:
    fp = r['path'].split('/')[1] if '/' in r['path'] else r['name']
    if 'PCB' in fp:
        continue
    cx, cy = (r['x0'] + r['x1']) / 2, -(r['y0'] + r['y1']) / 2
    if any(abs(cx - x) < 0.9 and abs(cy - y) < 0.9 for x, y in DNP):
        continue
    boxes.append((mat(fp), r['x0'], r['y0'], r['z0'], r['x1'], r['y1'], r['z1']))


def kbox(m, x0, y0, x1, y1, z0, z1):                    # KiCad x / y range
    boxes.append((m, x0, -y1, z0, x1, -y0, z1))


kbox('nylon', 24.5, 35.25, 34.5, 39.5, 1.6, 4.55)       # J10 JST-SH 8-pin, horizontal (2.95 mm tall)
kbox('ferrite', 6.1, 19.7, 11.1, 24.7, -3.0, 0.0)       # L1 5 x 5 x 3 mm power inductor, bottom
kbox('metal', 52.8, 14.0, 65.2, 26.0, -1.42, 0.0)       # J11 microSD socket, bottom
for kx in (18.12, 61.3):                                  # J1/J2 DF40HC(3.5) receptacles (no KiCad model)
    kbox('nylon', kx - 1.69, 20 - 9.3, kx + 1.69, 20 + 9.3, 1.6, 5.0)
MAT = {'resistor': (0.04, 0.04, 0.045), 'ceramic': (0.72, 0.6, 0.42), 'led': (0.9, 0.88, 0.8),
       'nylon': (0.93, 0.91, 0.86), 'metal': (0.78, 0.79, 0.8), 'ic': (0.07, 0.07, 0.08), 'ferrite': (0.18, 0.18, 0.19)}
out = sys.argv[2]
with open(out + '.mtl', 'w') as f:
    for k, c in MAT.items():
        f.write('newmtl c_%s\nKd %.3f %.3f %.3f\n\n' % (k, *c))
with open(out + '.obj', 'w') as f:
    f.write('mtllib %s.mtl\n' % out.split('/')[-1])
    n = 0
    for m, x0, y0, z0, x1, y1, z1 in sorted(boxes):
        f.write('usemtl c_%s\n' % m)
        for x, y, z in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]:
            f.write('v %.4f %.4f %.4f\n' % (x, y, z))
        for a, b, c, d in [(1, 4, 3, 2), (5, 6, 7, 8), (1, 2, 6, 5), (2, 3, 7, 6), (3, 4, 8, 7), (4, 1, 5, 8)]:
            f.write('f %d %d %d %d\n' % (n + a, n + b, n + c, n + d))
        n += 8
print(len(boxes), 'carrier blocks')
