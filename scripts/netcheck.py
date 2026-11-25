"""Group the copper of one net (pads, tracks, vias, zone fragments) into connected clusters, and
optionally join the clusters with vias placed where two zone fragments on different layers overlap.

  python netcheck.py NET [board] [-v]       list the clusters (-v: every item of every small cluster)
  python netcheck.py NET --bridge           add joining vias, refill, save, rewrite out/drc.rpt
"""
import os
import sys
import math
import pcbnew

T, MM = pcbnew.ToMM, pcbnew.FromMM
CU = [pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def nodes_of(b, net):
    nodes = []          # (kind, label, layers, object)
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() == net:
                nodes.append(('pad', '%s-%s' % (fp.GetReference(), p.GetNumber()), [l for l in CU if p.IsOnLayer(l)], p))
    for t in b.GetTracks():
        if t.GetNetname() != net:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            nodes.append(('via', '(%.2f,%.2f)' % (T(t.GetPosition().x), T(t.GetPosition().y)), CU, t))
        else:
            nodes.append(('track', '%s (%.2f,%.2f)-(%.2f,%.2f)' % (b.GetLayerName(t.GetLayer()), T(t.GetStart().x),
                          T(t.GetStart().y), T(t.GetEnd().x), T(t.GetEnd().y)), [t.GetLayer()], t))
    for i in range(b.GetAreaCount()):
        z = b.GetArea(i)
        if z.GetIsRuleArea() or z.GetNetname() != net:
            continue
        for l in CU:
            if not z.IsOnLayer(l):
                continue
            fp = z.GetFilledPolysList(l)
            for k in range(fp.OutlineCount()):
                ol = fp.Outline(k)
                bb = ol.BBox()
                nodes.append(('zone', '%s %s #%d %.1f mm2 (%.1f,%.1f)-(%.1f,%.1f)' % (z.GetZoneName(), b.GetLayerName(l), k,
                              T(T(ol.Area())), T(bb.GetLeft()), T(bb.GetTop()), T(bb.GetRight()), T(bb.GetBottom())), [l], (fp, k)))
    return nodes


def pts(n):
    k, _, _, o = n
    if k in ('pad', 'via'):
        return [o.GetPosition()]
    if k == 'track':
        a, e = o.GetStart(), o.GetEnd()
        return [a, e, pcbnew.VECTOR2I((a.x + e.x) // 2, (a.y + e.y) // 2)]
    return []


def touch(x, y):
    if not set(x[2]) & set(y[2]):
        return False
    if x[0] == 'zone' and y[0] == 'zone':
        return False
    if y[0] == 'zone':
        x, y = y, x
    if x[0] == 'zone':
        fp, k = x[3]
        return any(fp.Outline(k).PointInside(p) for p in pts(y))
    a, c = x[3], y[3]
    if not a.GetBoundingBox().Intersects(c.GetBoundingBox()):
        return False
    if a.Type() == pcbnew.PCB_TRACE_T and c.Type() == pcbnew.PCB_TRACE_T:
        return any(a.HitTest(p, a.GetWidth() // 2) for p in (c.GetStart(), c.GetEnd())) or \
            any(c.HitTest(p, c.GetWidth() // 2) for p in (a.GetStart(), a.GetEnd()))
    tol = max([o.GetWidth() // 2 for o in (a, c) if o.Type() == pcbnew.PCB_TRACE_T] or [0])
    return any(a.HitTest(p, tol) for p in pts(y)) or any(c.HitTest(p, tol) for p in pts(x))


def clusters(b, net):
    nodes = nodes_of(b, net)
    par = list(range(len(nodes)))

    def find(i):
        while par[i] != i:
            par[i] = par[par[i]]
            i = par[i]
        return i
    for i in range(len(nodes)):
        for j in range(i):
            if find(i) != find(j) and touch(nodes[i], nodes[j]):
                par[find(i)] = find(j)
    groups = {}
    for i in range(len(nodes)):
        groups.setdefault(find(i), []).append(nodes[i])
    return sorted(groups.values(), key=len)


def bridge(b, net):
    """one via per minor cluster, where one of its zone fragments overlaps a main-cluster fragment"""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import dfm
    items, holes, _ = dfm.load(b)
    groups = clusters(b, net)
    main = groups[-1]
    added = 0
    for g in groups[:-1]:
        done = False
        for zs in [n for n in g if n[0] == 'zone']:
            fpa, ka = zs[3]
            bb = fpa.Outline(ka).BBox()
            for zm in [n for n in main if n[0] == 'zone' and n[2] != zs[2]]:
                fpb, kb = zm[3]
                x = T(bb.GetLeft()) + 0.3
                while x < T(bb.GetRight()) - 0.3 and not done:
                    y = T(bb.GetTop()) + 0.3
                    while y < T(bb.GetBottom()) - 0.3 and not done:
                        p = pcbnew.VECTOR2I(MM(x), MM(y))
                        ring_ok = all(fpa.Outline(ka).PointInside(pcbnew.VECTOR2I(MM(x + dx), MM(y + dy))) and
                                      fpb.Outline(kb).PointInside(pcbnew.VECTOR2I(MM(x + dx), MM(y + dy)))
                                      for dx, dy in ((0, 0), (0.3, 0), (-0.3, 0), (0, 0.3), (0, -0.3)))
                        if ring_ok:
                            probe = dfm.Item('v', net, 0, 'new', c=(x, y), r=0.25)
                            ok = all(math.hypot(x - h[0][0], y - h[0][1]) > h[1] + 0.25 + 0.25 for h in holes)
                            for li in range(4):
                                for it in items[li]:
                                    if not ok:
                                        break
                                    if it.box[0] - 0.5 > x or x > it.box[2] + 0.5 or it.box[1] - 0.5 > y or y > it.box[3] + 0.5:
                                        continue
                                    g_ = dfm.gap(probe, it)
                                    if (it.net != net and g_ < 0.18) or (it.net == net and it.kind == 'p' and g_ < 0.2):
                                        ok = False
                            if ok:
                                v = pcbnew.PCB_VIA(b)
                                v.SetPosition(p)
                                v.SetWidth(MM(0.5))
                                v.SetDrill(MM(0.2))
                                v.SetViaType(pcbnew.VIATYPE_THROUGH)
                                v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                                v.SetNet(b.FindNet(net))
                                b.Add(v)
                                holes.append(((x, y), 0.1, 'via'))
                                for li in range(4):
                                    items[li].append(dfm.Item('v', net, li, 'new', c=(x, y), r=0.25))
                                print('bridge via %s (%.2f, %.2f): %s  <->  %s' % (net, x, y, zs[1], zm[1]))
                                added += 1
                                done = True
                        y += 0.1
                    x += 0.1
                if done:
                    break
            if done:
                break
        if not done:
            print('no bridge position for cluster with pads', ' '.join(n[1] for n in g if n[0] == 'pad'))
    return added


if __name__ == '__main__':
    NET = sys.argv[1]
    ARGS = [a for a in sys.argv[2:] if not a.startswith('-')]
    PCB = ARGS[0] if ARGS else os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
    b = pcbnew.LoadBoard(PCB)
    if '--bridge' in sys.argv:
        if bridge(b, NET):
            pcbnew.ZONE_FILLER(b).Fill(b.Zones())
            pcbnew.SaveBoard(PCB, b)
            b = pcbnew.LoadBoard(PCB)
            pcbnew.WriteDRCReport(b, os.path.join(ROOT, 'out', 'drc.rpt'), pcbnew.EDA_UNITS_MILLIMETRES, True)
    groups = clusters(b, NET)
    print(NET, ':', len(groups), 'cluster(s)')
    for g in groups:
        print('-- %d items: pads %s' % (len(g), ' '.join(n[1] for n in g if n[0] == 'pad')[:300]))
        if len(groups) > 1 and (len(g) < 40 or '-v' in sys.argv):
            for n in g:
                if n[0] != 'pad':
                    print('     ', n[0], n[1])
