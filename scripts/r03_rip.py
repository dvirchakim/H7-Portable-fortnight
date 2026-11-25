"""R0.3 review fixes, step 2: remove the copper that r03_renet.py made obsolete (run once, after it).

  - the old ESC-telemetry branch J10-4 -> UART3_RX (up to where it joins the UART3 route near J7)
  - the M1 stub between J10-5 and its first via (that route now carries ESC_TLM; J10-4 is re-attached by
    patch.py route:J10-4)
  - the VBAT / current-sense branches J2-73 / J2-75 -> their resistor clusters (re-routed to J2-78 / J2-80)
Branches are found from copper connectivity before anything is removed (KiCad 7's python bindings
misbehave after a removal), then removed in one go.  Follow with patch.py prune and the routes.
"""
import os, math
from collections import defaultdict, deque
import pcbnew
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
T = pcbnew.ToMM
b = pcbnew.LoadBoard(PCB)
ALL = {'F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu'}


def items_of(netname, pad_override=None):
    """copper items of a net (pads by their CURRENT net, plus pad_override = [(ref, num)] treated as members)"""
    its = []
    for t in b.GetTracks():
        if t.GetNetname() != netname:
            continue
        if t.Type() == pcbnew.PCB_VIA_T:
            p = (T(t.GetPosition().x), T(t.GetPosition().y))
            its.append(dict(obj=t, kind='via', layers=ALL, a=p, c=p, r=T(t.GetWidth()) / 2))
        else:
            its.append(dict(obj=t, kind='trk', layers={t.GetLayerName()}, a=(T(t.GetStart().x), T(t.GetStart().y)),
                            c=(T(t.GetEnd().x), T(t.GetEnd().y)), r=T(t.GetWidth()) / 2))
    for f in b.GetFootprints():
        for p in f.Pads():
            name = f.GetReference() + '-' + p.GetNumber()
            if p.GetNetname() == netname or (pad_override and (f.GetReference(), p.GetNumber()) in pad_override):
                bb = p.GetBoundingBox()
                ls = {b.GetLayerName(l) for l in (pcbnew.F_Cu, pcbnew.B_Cu) if p.IsOnLayer(l)}
                if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                    ls = ALL
                c = (T(bb.GetCenter().x), T(bb.GetCenter().y))
                its.append(dict(obj=p, kind='pad', name=name, layers=ls, a=c, c=c, hx=T(bb.GetWidth()) / 2, hy=T(bb.GetHeight()) / 2))
    return its


def segd(a, b_, c, d):
    def pt(p, s, e):
        dx, dy = e[0] - s[0], e[1] - s[1]
        L = dx * dx + dy * dy
        u = 0 if L == 0 else max(0, min(1, ((p[0] - s[0]) * dx + (p[1] - s[1]) * dy) / L))
        return math.hypot(p[0] - s[0] - u * dx, p[1] - s[1] - u * dy)
    return min(pt(a, c, d), pt(b_, c, d), pt(c, a, b_), pt(d, a, b_))


def touch(i, j):
    if not (i['layers'] & j['layers']):
        return False
    if i['kind'] == 'pad' and j['kind'] == 'pad':
        return False
    if 'pad' in (i['kind'], j['kind']):
        pd, o = (i, j) if i['kind'] == 'pad' else (j, i)
        for k in range(21):
            x = o['a'][0] + (o['c'][0] - o['a'][0]) * k / 20
            y = o['a'][1] + (o['c'][1] - o['a'][1]) * k / 20
            if abs(x - pd['a'][0]) <= pd['hx'] + o['r'] and abs(y - pd['a'][1]) <= pd['hy'] + o['r']:
                return True
        return False
    return segd(i['a'], i['c'], j['a'], j['c']) <= i['r'] + j['r'] - 0.001


def graph(its):
    adj = defaultdict(set)
    for x in range(len(its)):
        for y in range(x + 1, len(its)):
            if touch(its[x], its[y]):
                adj[x].add(y)
                adj[y].add(x)
    return adj


def branch(netname, src, pad_override=None):
    """items from pad src up to (not including) the first item shared with the paths to the net's other pads"""
    its = items_of(netname, pad_override)
    adj = graph(its)
    s = [i for i, it in enumerate(its) if it.get('name') == src][0]
    prev = {s: None}
    dq = deque([s])
    while dq:
        u = dq.popleft()
        for w in adj[u]:
            if w not in prev:
                prev[w] = u
                dq.append(w)
    others = [i for i, it in enumerate(its) if it['kind'] == 'pad' and i != s and i in prev]
    paths = []
    for o in others:
        p, n = [], o
        while n is not None:
            p.append(n)
            n = prev[n]
        paths.append(p[::-1])
    common = paths[0]
    for p in paths[1:]:
        common = [a for a, c in zip(common, p) if a == c]
    return [its[i]['obj'] for i in common[1:-1] if its[i]['kind'] != 'pad'], [its[i].get('name', its[i]['kind']) for i in common]


def stub(netname, padname):
    """tracks from a pad up to (not including) the first via"""
    its = items_of(netname, [tuple(padname.split('-'))])
    adj = graph(its)
    s = [i for i, it in enumerate(its) if it.get('name') == padname][0]
    out, seen, cur = [], {s}, [s]
    while cur:
        nxt = []
        for u in cur:
            for w in adj[u]:
                if w in seen or its[w]['kind'] == 'pad':
                    continue
                seen.add(w)
                if its[w]['kind'] == 'via':
                    continue
                out.append(its[w]['obj'])
                nxt.append(w)
        cur = nxt
    return out


remove = []
r, names = branch('UART3_RX', 'J10-4', pad_override=[('J10', '4')])
print('UART3_RX branch from J10-4: %d items, ends at %s' % (len(r), names[-1]))
remove += r
r = stub('ESC_TLM', 'J10-5')
print('M1 stub at J10-5: %d tracks' % len(r))
remove += r
for net, pad in (('VBAT_SENSE', 'J2-73'), ('CURR_SENSE', 'J2-75')):
    r, names = branch(net, pad, pad_override=[tuple(pad.split('-'))])
    print('%s branch from %s: %d items, ends at %s' % (net, pad, len(r), names[-1]))
    remove += r
for o in remove:
    b.Remove(o)
pcbnew.SaveBoard(PCB, b)
print('removed', len(remove))
