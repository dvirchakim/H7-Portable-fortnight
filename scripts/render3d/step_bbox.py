"""Minimal STEP (AP214) reader: world bounding box of every solid, with its assembly path.
usage: python -I step_bbox.py model.step out.json"""
import re, sys, json, math
from collections import defaultdict
txt = open(sys.argv[1], encoding='latin-1').read()
data = txt[txt.index('DATA;') + 5:txt.rindex('ENDSEC;')]
ents = {}
for m in re.finditer(r'#(\d+)\s*=\s*(.*?);\s*(?=#\d+\s*=|$)', data, re.S):
    ents[int(m.group(1))] = ' '.join(m.group(2).split())
def typ(e):
    m = re.match(r'([A-Z0-9_]+)\s*\(', ents[e]); return m.group(1) if m else 'COMPLEX'
def refs(e): return [int(x) for x in re.findall(r'#(\d+)', ents[e])]
def nums(s): return [float(x) for x in re.findall(r'[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?', s)]
byt = defaultdict(list)
for e in ents: byt[typ(e)].append(e)
def point(e):
    s = ents[e]; inner = s[s.index('(', s.index('(') + 1) + 1:s.rindex(')')]
    return nums(inner.split(')')[0])
def axis(e):
    r = refs(e); o = point(r[0])
    z = point(r[1]) if len(r) > 1 else [0, 0, 1]
    x = point(r[2]) if len(r) > 2 else [1, 0, 0]
    n = math.sqrt(sum(v * v for v in z)); z = [v / n for v in z]
    d = sum(a * b for a, b in zip(x, z)); x = [a - d * b for a, b in zip(x, z)]
    n = math.sqrt(sum(v * v for v in x)); x = [v / n for v in x]
    y = [z[1] * x[2] - z[2] * x[1], z[2] * x[0] - z[0] * x[2], z[0] * x[1] - z[1] * x[0]]
    return (o, x, y, z)
def to_mat(ax):
    o, x, y, z = ax
    return [[x[0], y[0], z[0], o[0]], [x[1], y[1], z[1], o[1]], [x[2], y[2], z[2], o[2]], [0, 0, 0, 1]]
def mul(a, b): return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def inv(m):
    R = [[m[j][i] for j in range(3)] for i in range(3)]; t = [m[i][3] for i in range(3)]
    ti = [-sum(R[i][k] * t[k] for k in range(3)) for i in range(3)]
    return [R[0] + [ti[0]], R[1] + [ti[1]], R[2] + [ti[2]], [0, 0, 0, 1]]
def app(m, p): return [sum(m[i][k] * p[k] for k in range(3)) + m[i][3] for i in range(3)]
I4 = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
pd_name = {}
for e in byt['PRODUCT_DEFINITION']:
    pdf = refs(e)[0]; prod = refs(pdf)[0]
    pd_name[e] = re.match(r"PRODUCT\s*\(\s*'([^']*)'", ents[prod]).group(1)
pds_pd = {e: refs(e)[0] for e in byt['PRODUCT_DEFINITION_SHAPE']}
pd_sr = {}
for e in byt['SHAPE_DEFINITION_REPRESENTATION']:
    a, b = refs(e)[:2]
    if pds_pd.get(a) in pd_name: pd_sr[pds_pd[a]] = b
sr_geo = defaultdict(list)
for e in byt['SHAPE_REPRESENTATION_RELATIONSHIP']:
    r = refs(e); sr_geo[r[0]].append(r[1]); sr_geo[r[1]].append(r[0])
vp = {e: point(refs(e)[0]) for e in byt['VERTEX_POINT']}
def solid_pts(root):
    seen, st, pts = set(), [root], []
    while st:
        e = st.pop()
        if e in seen: continue
        seen.add(e)
        if e in vp: pts.append(vp[e]); continue
        if typ(e) in ('CARTESIAN_POINT', 'DIRECTION'): continue
        st.extend(refs(e))
    return pts
SOLID_T = ('MANIFOLD_SOLID_BREP', 'BREP_WITH_VOIDS', 'SHELL_BASED_SURFACE_MODEL', 'FACETED_BREP')
def solids_of_sr(sr):
    out, seen, st = [], set(), [sr]
    while st:
        s = st.pop()
        if s in seen: continue
        seen.add(s)
        for r in refs(s):
            if r in ents and typ(r) in SOLID_T: out.append(r)
        st.extend(x for x in sr_geo.get(s, []) if x not in seen)
    return out
# colour per solid if present (STYLED_ITEM -> ... COLOUR_RGB)
colour = {}
for e in byt['STYLED_ITEM']:
    r = refs(e)
    if not r: continue
    item = r[-1]
    st, seen = list(r[:-1]), set()
    while st:
        x = st.pop()
        if x in seen: continue
        seen.add(x)
        if typ(x) == 'COLOUR_RGB':
            colour[item] = nums(ents[x].split(',', 1)[1]); break
        st.extend(refs(x))
children = defaultdict(list)
nauo_pds = {refs(e)[0]: e for e in byt['PRODUCT_DEFINITION_SHAPE']}
cdsr = {}
for e in byt['CONTEXT_DEPENDENT_SHAPE_REPRESENTATION']:
    a, b = refs(e)[:2]; cdsr[b] = a
for e in byt['NEXT_ASSEMBLY_USAGE_OCCURRENCE']:
    r = refs(e); parent, child = r[0], r[1]
    T = I4
    rr = cdsr.get(nauo_pds.get(e))
    if rr is not None:
        idt = [x for x in refs(rr) if typ(x) == 'ITEM_DEFINED_TRANSFORMATION']
        if idt:
            a1, a2 = refs(idt[0])[:2]
            T = mul(to_mat(axis(a2)), inv(to_mat(axis(a1))))
    children[parent].append((child, T))
allchild = {c for v in children.values() for c, _ in v}
roots = [p for p in pd_name if p not in allchild]
res = []
def walk(pd, M, path):
    sr = pd_sr.get(pd)
    if sr is not None:
        for s in solids_of_sr(sr):
            pts = [app(M, p) for p in solid_pts(s)]
            if pts:
                xs, ys, zs = zip(*pts)
                res.append(dict(name=pd_name[pd], path='/'.join(path), x0=min(xs), x1=max(xs), y0=min(ys), y1=max(ys), z0=min(zs), z1=max(zs), rgb=colour.get(s)))
    for c, T in children.get(pd, []):
        walk(c, mul(M, T), path + [pd_name[c]])
for r in roots: walk(r, I4, [pd_name[r]])
json.dump(res, open(sys.argv[2], 'w'))
print('entities', len(ents), 'products', len(pd_name), 'roots', [pd_name[r] for r in roots], 'solids', len(res))
