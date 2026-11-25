"""Portenta H7 as coloured blocks (one box per solid of Arduino's STEP model), placed on the carrier.
usage: python -I h7obj.py h7.json out_basename CARRIER_TOP_Z Y_SIGN
Carrier frame: X = KiCad x, Y = Y_SIGN * KiCad y, Z up (top surface at CARRIER_TOP_Z)."""
import json, sys
s = json.load(open(sys.argv[1]))
out, ztop, ysign = sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
H7_X0, H7_Y0, H7_H, STACK, PCB_T = 0.98, 7.3, 25.4, 3.5, 1.646


def colour(name, z0, z1, rgb):
    n = name.upper()
    if name.startswith('Open CASCADE STEP translator 6.8 4.1.1.1'):
        return 'pcb_h7'
    if 'CX90B1' in n or 'LBEE5KL1DX' in n or 'USB' == n[:3] and 'PCMF' not in n:
        return 'metal'
    if 'DF40' in n or 'BM03B' in n or 'SM05B' in n:
        return 'plastic'
    if n.startswith('CAP-'):
        return 'ceramic'
    if 'LOGO' in n:
        return 'silk'
    if 'HSM' in n:
        return 'led'
    if 'PTS820' in n:
        return 'metal'
    if rgb and rgb[0] > 0.9 and rgb[1] > 0.9 and rgb[2] > 0.9:
        return 'ceramic'
    return 'ic'


boxes = []
for r in s:
    if r['name'] == 'BGA_Ball':
        continue
    m = colour(r['name'], r['z0'], r['z1'], r['rgb'])
    X0, X1 = H7_X0 + r['x0'], H7_X0 + r['x1']
    ky0, ky1 = H7_Y0 + H7_H - r['y1'], H7_Y0 + H7_H - r['y0']            # KiCad y (down)
    Y0, Y1 = sorted((ysign * ky0, ysign * ky1))
    zb = ztop + STACK + PCB_T
    Z0, Z1 = zb + r['z0'], zb + r['z1']
    if X1 - X0 < 0.01 or Y1 - Y0 < 0.01 or Z1 - Z0 < 0.005:
        continue
    boxes.append((m, X0, Y0, Z0, X1, Y1, Z1))
MAT = {'pcb_h7': (0.04, 0.05, 0.05), 'metal': (0.75, 0.76, 0.78), 'plastic': (0.86, 0.83, 0.74),
       'ceramic': (0.72, 0.6, 0.42), 'silk': (0.92, 0.92, 0.9), 'led': (0.95, 0.85, 0.4), 'ic': (0.07, 0.07, 0.08)}
with open(out + '.mtl', 'w') as f:
    for k, c in MAT.items():
        f.write('newmtl %s\nKd %.3f %.3f %.3f\n\n' % (k, *c))
with open(out + '.obj', 'w') as f:
    f.write('mtllib %s.mtl\n' % out.replace('\\', '/').split('/')[-1])
    n = 0
    for m, x0, y0, z0, x1, y1, z1 in sorted(boxes):
        f.write('usemtl %s\n' % m)
        for x, y, z in [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]:
            f.write('v %.4f %.4f %.4f\n' % (x, y, z))
        for a, b, c, d in [(1, 4, 3, 2), (5, 6, 7, 8), (1, 2, 6, 5), (2, 3, 7, 6), (3, 4, 8, 7), (4, 1, 5, 8)]:
            f.write('f %d %d %d %d\n' % (n + a, n + b, n + c, n + d))
        n += 8
print(len(boxes), 'boxes')
