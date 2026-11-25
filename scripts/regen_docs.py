"""Rewrite the schematic, symbol library, bom_placement.csv and expected_nets.json from design.py
WITHOUT touching the routed PCB or the project's net-class settings (gen.py would overwrite both)."""
import os
import sys
import json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gen
import design as D

gen.write_schematic()
rows = ['Ref,Value,MPN,Footprint,Side,X_mm,Y_mm,Rot']
for p in D.PARTS:
    rows.append('%s,%s,%s,%s,%s,%.2f,%.2f,%d' % (p['ref'], p['value'].replace(',', ';'), p['mpn'],
                                                p['fp'], p['side'], p['x'], p['y'], p['rot']))
open(os.path.join(gen.ROOT, 'bom_placement.csv'), 'w').write('\n'.join(rows) + '\n')
nt = gen.net_table()
json.dump({k: sorted(v) for k, v in nt.items()}, open(os.path.join(gen.ROOT, 'scripts', 'expected_nets.json'), 'w'), indent=1)
print('schematic, bom_placement.csv and expected_nets.json rewritten,', len(D.PARTS), 'parts,', len(nt), 'nets')
