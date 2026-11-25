"""Autoroute with Freerouting.

  python route.py export   writes out/board.dsn from the unrouted board
  (run Freerouting:  java -jar tools/freerouting/freerouting-1.9.0.jar -de out/board.dsn -do out/board.ses -mp 30)
  python route.py import   reads out/board.ses, adds tracks/vias, fills zones, writes out/drc.rpt

Notes: Freerouting 1.9.0 routes nothing if the DSN contains KiCad's NPTH mounting-hole
footprints, so they are left out of the export (HOLE_KEEPOUT rule areas stand in for them).
KiCad 7's ImportSpecctraSES needs the GUI, so the session file is parsed here instead.
"""
import os
import re
import sys
import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import parse, find

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
DSN = os.path.join(ROOT, 'out', 'board.dsn')
SES = os.path.join(ROOT, 'out', 'board.ses')
PLANE_LAYERS = [a for a in sys.argv[2:] if a != 'noplanes' and not a.startswith('only:')]   # e.g. In1.Cu In2.Cu
ONLY = next((a[5:].split(',') for a in sys.argv[2:] if a.startswith('only:')), None)   # route / import just these nets

board = pcbnew.LoadBoard(PCB)
if sys.argv[1] == 'export':
    for fp in list(board.GetFootprints()):
        if fp.GetReference().startswith('H'):
            board.Remove(fp)
    assert pcbnew.ExportSpecctraDSN(board, DSN)
    s = open(DSN).read()
    s = s.replace('(class kicad_default "" ', '(class kicad_default ')
    for l in PLANE_LAYERS:                      # plane-only layers: no signal routing there
        s2 = re.sub(r'(\(layer %s\s+\(type )signal' % re.escape(l), r'\1power', s)
        assert s2 != s
        s = s2
    if 'noplanes' in sys.argv:                  # treat GND / +5V as ordinary nets (final clean-up pass)
        s = '\n'.join(x for x in s.split('\n') if not x.startswith('    (plane '))
    if ONLY:                                    # every other net's copper is fixed: only ONLY may move
        def fix(m):
            net = m.group(2).strip('"')
            return m.group(0) if net in ONLY else m.group(1) + '(type fix)'
        s = re.sub(r'(\((?:wire|via) .*?\(net ([^)]*)\))\(type route\)', fix, s)
    open(DSN, 'w').write(s)
    print('exported', DSN, 'plane-only layers:', PLANE_LAYERS)
else:
    for t in list(board.GetTracks()):          # the session file carries the complete wiring
        if ONLY is None or t.GetNetname() in ONLY:
            board.Remove(t)
    root = parse(open(SES).read())
    routes = find(root, 'routes')[0]
    res = find(routes, 'resolution')[0]
    assert res[1] == 'um'
    k = 1000.0 / float(res[2])                      # session units -> nm
    nseg = nvia = 0
    for netnode in find(find(routes, 'network_out')[0], 'net'):
        if ONLY is not None and netnode[1].strip('"') not in ONLY:
            continue
        net = board.FindNet(netnode[1])
        assert net is not None, netnode[1]
        for w in find(netnode, 'wire'):
            p = find(w, 'path')[0]
            layer = board.GetLayerID(p[1])
            width = int(round(float(p[2]) * k))
            pts = [(int(round(float(p[i]) * k)), -int(round(float(p[i + 1]) * k))) for i in range(3, len(p) - 1, 2)]
            for a, b in zip(pts, pts[1:]):
                if a == b:
                    continue
                t = pcbnew.PCB_TRACK(board)
                t.SetStart(pcbnew.VECTOR2I(*a))
                t.SetEnd(pcbnew.VECTOR2I(*b))
                t.SetWidth(width)
                t.SetLayer(layer)
                t.SetNet(net)
                board.Add(t)
                nseg += 1
        for v in find(netnode, 'via'):
            m = re.search(r'_(\d+):(\d+)_um', v[1])
            via = pcbnew.PCB_VIA(board)
            via.SetPosition(pcbnew.VECTOR2I(int(round(float(v[2]) * k)), -int(round(float(v[3]) * k))))
            via.SetWidth(int(m.group(1)) * 1000)
            via.SetDrill(int(m.group(2)) * 1000)
            via.SetViaType(pcbnew.VIATYPE_THROUGH)
            via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            via.SetNet(net)
            board.Add(via)
            nvia += 1
    pcbnew.ZONE_FILLER(board).Fill(board.Zones())
    pcbnew.SaveBoard(PCB, board)
    board = pcbnew.LoadBoard(PCB)
    pcbnew.WriteDRCReport(board, os.path.join(ROOT, 'out', 'drc.rpt'), pcbnew.EDA_UNITS_MILLIMETRES, True)
    print('track segments:', nseg, 'vias:', nvia)
