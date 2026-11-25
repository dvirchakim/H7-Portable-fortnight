import sys, zlib
sys.path.insert(0, sys.argv[3])
from altium_ole import cfb, props
paths, get = cfb(sys.argv[1])
names = props(get('Models/Data'))
print(len(names), 'model records;', [p for p in paths if p.startswith('Models')][:5])
for i, d in enumerate(names):
    n = d.get('NAME', '')
    if 'ortenta' in n.lower():
        raw = get('Models/%d' % i)
        try: raw = zlib.decompress(raw)
        except Exception as e: print('zlib', e)
        out = sys.argv[2] + '/' + n
        open(out, 'wb').write(raw); print('wrote', n, len(raw))
