"""JLCPCB assembly files from bom_placement.csv and the kicad-cli position export.

  kicad-cli pcb export pos -o fab/pos_raw.csv --format csv --units mm --side both portenta_drone_fc.kicad_pcb
  python scripts/jlc.py        -> fab/jlcpcb_bom.csv   (then scripts/jlc_place.py -> fab/jlcpcb_cpl.csv)

LCSC numbers below were looked up in JLCPCB's parts library on 2026-11-13 (stock noted then).
"""
import os
import sys
import csv
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKIP_PREFIX = ('TP', 'H', 'JP', 'FID')   # pads, holes, solder jumper, fiducials: nothing to place
DNP = set(D.DNP)                         # not fitted: see design.py
MPN_BY_FP = {                            # parts whose MPN is implied by the footprint
    'JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal': 'SM04B-GHS-TB',
    'JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal': 'SM06B-GHS-TB',
    'JST_SH_SM08B-SRSS-TB_1x08-1MP_P1.00mm_Horizontal': 'SM08B-SRSS-TB',
}

LCSC = {                                 # BOM comment -> LCSC part (price / stock checked 2026-11-14)
    # basic parts (no setup fee)
    '100n': 'C1525', '1u': 'C52923', '2.2u': 'C12530', '10u': 'C15850', '22u 25V': 'C45783',   # Samsung CL21A226MAQNNNE, 25 V X5R
    '100n 50V': 'C14663', '10u 50V': 'C13585',
    '1k': 'C11702', '2.2k': 'C25879', '10k': 'C25744', '10k 1%': 'C25744', '100k': 'C25741',
    '100k 1%': 'C25741', '120R': 'C25079', '51k 1%': 'C25794', '12k 1%': 'C25752',
    '0R': 'C17168',
    'SS34': 'C8678', '1N4148W': 'C81598', '2N7002': 'C8545', 'RED': 'C2286', 'WHITE': 'C2290',
    # preferred extended (no setup fee)
    'SN65HVD230DR': 'C12084',
    # extended (setup fee per unique part)
    'SMBJ26A': 'C123820', 'LMR33630ADDAR': 'C841384', 'LP5907MFX-3.3/NOPB': 'C80670',
    'ICM-45686': 'C22459454',                # TDK IMU, pin-compatible with ICM-42688-P; JLC assembly difficulty normal
                                             # (ICM-42688-P C1850418: $21.6, 7 in stock; IIM-42652 C2988404 and
                                             #  DPS368 C3232508 are flagged 'processing difficult' by JLCPCB)
    'REF3125AIDBZR': 'C33297',               # TI 2.5 V series reference for ADC VREF+ (29.9k in stock 2026-11-15)
    'MS560702BA03-50': 'C97627',             # TE MS5607 barometer (MS5611 C15639 is a drop-in upgrade)
    'MDA5030-6R8M': 'C2847478',              # KOHER 6.8 uH (MPS MPL-AL5050-6R8 C3224327 also fits: $1.78, 19 in stock)
    '104031-0811': 'C585350', 'SM04B-GHS-TB': 'C189895', 'SM06B-GHS-TB': 'C133065', 'SM08B-SRSS-TB': 'C160407',
    'DF40HC(3.5)-80DS-0.4V(51)': 'C3641790', # NO STOCK at JLCPCB: pre-order or consign
}

parts = list(csv.DictReader(open(os.path.join(ROOT, 'bom_placement.csv'), encoding='utf8')))
keep = [p for p in parts if not p['Ref'].startswith(SKIP_PREFIX) and p['Ref'] not in DNP]
groups = {}
for p in keep:
    fp = p['Footprint'].split(':')[-1]
    mpn = p['MPN'] or MPN_BY_FP.get(fp, '')
    comment = mpn if mpn else p['Value']
    if fp.startswith('JST_'):
        comment = mpn
    groups.setdefault((LCSC[comment], fp), []).append((p['Ref'], comment))   # one BOM line per LCSC part
with open(os.path.join(ROOT, 'fab', 'jlcpcb_bom.csv'), 'w', newline='', encoding='utf8') as f:
    w = csv.writer(f)
    w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
    def natural(r):
        return (r.rstrip('0123456789'), int(r[len(r.rstrip('0123456789')):] or 0))
    for (lcsc, fp), items in sorted(groups.items(), key=lambda x: natural(min(x[1], key=lambda i: natural(i[0]))[0])):
        refs = sorted((r for r, _ in items), key=natural)
        comment = max((c for _, c in items), key=len)        # e.g. "100k 1%" covers the plain "100k" too
        w.writerow([comment, ','.join(refs), fp, lcsc])
    assert len(set(k[0] for k in groups)) == len(groups)       # JLCPCB rejects one part on two lines

print('BOM lines:', len(groups), 'parts:', len(keep), 'not fitted:', sorted(DNP))
# the placement file comes from scripts/jlc_place.py (corrected to JLCPCB's part footprints)
