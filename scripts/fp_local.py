"""Print, per JLCPCB BOM line, the library pad layout of our footprint (pad number -> local x, y in mm,
footprint at 0 deg, top side) as compact JSON for the placement check (scripts/jlc_place.py)."""
import os
import csv
import json
import pcbnew

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STD = r'C:\Program Files\KiCad\7.0\share\kicad\footprints'
T = pcbnew.ToMM
fps = {r['Ref']: r['Footprint'] for r in csv.DictReader(open(os.path.join(ROOT, 'bom_placement.csv')))}
out = {}
for r in csv.DictReader(open(os.path.join(ROOT, 'fab', 'jlcpcb_bom.csv'))):
    ref = r['Designator'].split(',')[0]
    lib, name = fps[ref].split(':')
    path = os.path.join(ROOT, 'fc.pretty') if lib == 'fc' else os.path.join(STD, lib + '.pretty')
    fp = pcbnew.FootprintLoad(path, name)
    pads = {}
    for p in fp.Pads():
        n = p.GetNumber()
        if n and n not in pads:
            pads[n] = [round(T(p.GetPosition().x), 3), round(T(p.GetPosition().y), 3)]
    if len(pads) > 20:                       # DF40: corners and centre of both rows are enough
        keep = [k for k in ('1', '2', '3', '4', '39', '40', '41', '42', '77', '78', '79', '80') if k in pads]
        pads = {k: pads[k] for k in keep}
    out[r['LCSC Part #']] = {'ref': ref, 'p': pads}
print(json.dumps(out, separators=(',', ':')))
