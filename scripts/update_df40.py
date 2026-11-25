"""Swap the J1/J2 footprints on the routed board for the current fc.pretty version
(pads are unchanged, so nets and routing stay as they are), then re-run DRC."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pcbnew
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
NAME = 'Hirose_DF40HC(3.5)-80DS-0.4V_2x40_P0.4mm'
b = pcbnew.LoadBoard(PCB)
for ref in ('J1', 'J2'):
    old = b.FindFootprintByReference(ref)
    new = pcbnew.FootprintLoad(os.path.join(ROOT, 'fc.pretty'), NAME)
    new.SetFPID(pcbnew.LIB_ID('fc', NAME))
    new.SetReference(ref); new.SetValue(old.GetValue())
    b.Add(new)
    new.SetPosition(old.GetPosition()); new.SetOrientationDegrees(old.GetOrientationDegrees())
    new.SetPath(old.GetPath())
    nets = {p.GetNumber(): p.GetNet() for p in old.Pads()}
    moved = 0
    for p in new.Pads():
        o = [q for q in old.Pads() if q.GetNumber() == p.GetNumber()][0]
        d = p.GetPosition() - o.GetPosition()
        moved = max(moved, abs(d.x), abs(d.y))
        assert p.GetSize() == o.GetSize()
        p.SetNet(nets[p.GetNumber()])
    print(ref, 'max pad shift nm:', moved)
    b.Remove(old)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
pcbnew.SaveBoard(PCB, b)
