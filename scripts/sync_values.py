"""Copy footprint Value fields from bom_placement.csv (design.py) onto the routed board, and mark the
not-fitted parts (design.DNP) exclude-from-BOM / exclude-from-position-files (KiCad 7 has no board DNP flag)."""
import os
import csv
import sys
import pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
want = {r['Ref']: r['Value'] for r in csv.DictReader(open(os.path.join(ROOT, 'bom_placement.csv')))}
board = pcbnew.LoadBoard(PCB)
changed = []
for fp in board.GetFootprints():
    ref = fp.GetReference()
    if ref in want and not ref.startswith('TP') and fp.GetValue() != want[ref]:
        changed.append('%s %s -> %s' % (ref, fp.GetValue(), want[ref]))
        fp.SetValue(want[ref])
NF = pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES
dnp = []
for fp in board.GetFootprints():
    a = fp.GetAttributes()
    want_a = (a | NF) if fp.GetReference() in D.DNP else a
    if want_a != a:
        fp.SetAttributes(want_a)
        dnp.append(fp.GetReference())
pcbnew.SaveBoard(PCB, board)
print('not-fitted attributes changed:', ', '.join(dnp) or 'none')
print('values updated:', '; '.join(changed) or 'none')
