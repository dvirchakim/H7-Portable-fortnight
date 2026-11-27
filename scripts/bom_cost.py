"""Parts cost of the JLCPCB assembly order: 'before' = the rev 0.1 BOM (kept as the reference),
'after' = the current order, read from fab/jlcpcb_bom.csv (run scripts/jlc.py first).

  python scripts/bom_cost.py        -> prints the comparison, writes fab/bom_cost.csv

Prices are JLCPCB's part prices (USD) read from their parts library on 2026-11-14, as price breaks
{min quantity: unit price}.  EXT_FEE is the setup fee JLCPCB charges once per order for each unique
extended part (basic and preferred-extended parts have none) - check the current figure in their quote.
Board fabrication and assembly labour are not included.
"""
import os
import csv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXT_FEE = 3.0
# LCSC: (description, class, price breaks)   class: B basic, P preferred extended, E extended
P = {
    'C13585': ('10uF 50V 1206', 'B', {1: 0.121, 100: 0.1002}),
    'C14663': ('100nF 50V 0603', 'B', {1: 0.0104}),
    'C52923': ('1uF 0402', 'B', {1: 0.0057}),
    'C1525': ('100nF 0402', 'B', {1: 0.0024}),
    'C45783': ('22uF 0805', 'B', {1: 0.1084, 200: 0.0873}),
    'C12530': ('2.2uF 0402', 'B', {1: 0.0051}),
    'C15850': ('10uF 0805', 'B', {1: 0.0311}),
    'C123820': ('SMBJ26A TVS', 'E', {1: 0.0601, 100: 0.0503}),
    'C8678': ('SS34', 'B', {1: 0.0351}),
    'C2288': ('LED blue KT-0603B', 'E', {1: 0.0106}),
    'C12624': ('LED green KT-0603G', 'E', {1: 0.0119}),
    'C2286': ('LED red KT-0603R', 'B', {1: 0.0077}),
    'C2290': ('LED white KT-0603W', 'B', {1: 0.0123}),
    'C81598': ('1N4148W', 'B', {1: 0.0124}),
    'C3641790': ('Hirose DF40HC(3.5)-80DS socket', 'E', {1: 1.1306, 10: 1.1093, 30: 1.0946}),
    'C160407': ('JST SH 8p', 'E', {1: 0.3114, 50: 0.2468}),
    'C585350': ('Molex microSD', 'E', {1: 0.6774, 10: 0.5449, 30: 0.4778}),
    'C133065': ('JST GH 6p', 'E', {1: 0.306, 50: 0.2512}),
    'C189895': ('JST GH 4p', 'E', {1: 0.4413, 50: 0.3883}),
    'C3224327': ('MPS MPL-AL5050-6R8', 'E', {1: 1.7834, 100: 1.3829}),
    'C2847478': ('KOHER MDA5030-6R8M', 'E', {1: 0.6169, 10: 0.4925, 30: 0.4287}),
    'C94638': ('Infineon BSS138N', 'E', {1: 0.0945, 50: 0.0774}),
    'C8545': ('2N7002', 'B', {1: 0.0158}),
    'C25741': ('100k 0402', 'B', {1: 0.0009}),
    'C327362': ('23.7k 0402', 'E', {1: 0.0019}),
    'C25794': ('51k 0402', 'B', {1: 0.0019}),
    'C25752': ('12k 0402', 'B', {1: 0.0018}),
    'C25744': ('10k 0402', 'B', {1: 0.001}),
    'C25879': ('2.2k 0402', 'B', {1: 0.0011}),
    'C25079': ('120R 0402', 'B', {1: 0.0012}),
    'C11702': ('1k 0402', 'B', {1: 0.0013}),
    'C841384': ('TI LMR33630ADDAR', 'E', {1: 0.6316, 10: 0.5252, 30: 0.45}),
    'C80670': ('TI LP5907MFX-3.3', 'E', {1: 0.1649, 50: 0.1272}),
    'C1850418': ('TDK ICM-42688-P', 'E', {1: 21.6263, 30: 20.6152}),
    'C2988404': ('TDK IIM-42652', 'E', {1: 11.1273}),
    'C3232508': ('Infineon DPS368XTSA1', 'E', {1: 4.1313, 10: 3.5177, 30: 3.1529}),
    'C22459454': ('TDK ICM-45686', 'E', {1: 8.232, 10: 7.0225, 30: 6.2861}),   # 2026-11-27
    'C97627': ('TE MS5607-02BA03', 'E', {1: 4.375}),
    'C3288646': ('TDK ICM-42670-P', 'E', {1: 2.0763, 10: 1.8351, 30: 1.6633}),   # 2026-11-27
    'C5362283': ('Bosch BMP581', 'E', {1: 2.1315, 10: 1.8745, 30: 1.6948}),      # 2026-11-27
    'C12084': ('TI SN65HVD230DR', 'P', {1: 0.5596, 10: 0.4647, 30: 0.396}),
    'C33297': ('TI REF3125 2.5 V reference', 'E', {1: 1.0684, 10: 0.8754}),   # 2026-11-15
}
# (LCSC, quantity per board)
BEFORE = [('C13585', 2), ('C14663', 1), ('C52923', 4), ('C1525', 10), ('C45783', 3), ('C12530', 1), ('C15850', 1),
          ('C123820', 1), ('C8678', 1), ('C2288', 1), ('C81598', 1), ('C12624', 1), ('C3641790', 2), ('C160407', 1),
          ('C585350', 1), ('C133065', 2), ('C189895', 4), ('C3224327', 1), ('C94638', 1), ('C25741', 3),
          ('C327362', 1), ('C25744', 3), ('C25879', 3), ('C25079', 1), ('C11702', 3), ('C841384', 1),
          ('C80670', 1), ('C1850418', 1), ('C3232508', 1), ('C12084', 1)]
SWAP = {'C2288': 'C2286', 'C12624': 'C2290', 'C3224327': 'C2847478', 'C94638': 'C8545',
        'C1850418': 'C22459454', 'C3232508': 'C5362283', 'C327362': 'C25752'}
AFTER = []                                                                     # the current order
for r in csv.DictReader(open(os.path.join(ROOT, 'fab', 'jlcpcb_bom.csv'), encoding='utf8')):
    if r['LCSC Part #'] not in P:
        raise SystemExit('no price for %s (%s): add it to P' % (r['LCSC Part #'], r['Comment']))
    AFTER.append((r['LCSC Part #'], len(r['Designator'].split(','))))


def unit(lcsc, qty):
    br = P[lcsc][2]
    return br[max(k for k in br if k <= qty)]


def order(bom, boards):
    parts = sum(unit(c, n * boards) * n * boards for c, n in bom)
    fees = EXT_FEE * len(set(c for c, _ in bom if P[c][1] == 'E'))
    return parts, fees


rows = [('boards', 'BOM', 'parts $', 'setup fees $', 'total $', 'per board $')]
for boards in (5, 10, 30):
    for name, bom in (('before', BEFORE), ('after', AFTER)):
        parts, fees = order(bom, boards)
        rows.append((boards, name, '%.2f' % parts, '%.2f' % fees, '%.2f' % (parts + fees), '%.2f' % ((parts + fees) / boards)))
with open(os.path.join(ROOT, 'fab', 'bom_cost.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerows(rows)
    w.writerow([])
    w.writerow(('LCSC', 'part', 'class', 'qty/board', 'unit $ @10 boards', 'line $/board'))
    for c, n in AFTER:
        w.writerow((c, P[c][0], P[c][1], n, '%.4f' % unit(c, n * 10), '%.3f' % (unit(c, n * 10) * n)))
for r in rows:
    print('%-7s %-7s %-9s %-13s %-8s %s' % r)
print('\nbiggest lines after (per board, 10-board order):')
for c, n in sorted(AFTER, key=lambda x: -unit(x[0], x[1] * 10) * x[1])[:6]:
    print('  %-34s %6.2f' % (P[c][0], unit(c, n * 10) * n))
print('unique extended parts: before %d, after %d' % (len(set(c for c, _ in BEFORE if P[c][1] == 'E')),
                                                       len(set(c for c, _ in AFTER if P[c][1] == 'E'))))
