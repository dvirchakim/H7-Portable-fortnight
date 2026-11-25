"""Minimal KiCad s-expression reader used to pull pin data from the stock libraries."""
import re

TOK = re.compile(r'"(?:\\.|[^"\\])*"|[()]|[^\s()"]+')


def parse(text):
    stack = [[]]
    for m in TOK.finditer(text):
        t = m.group(0)
        if t == '(':
            stack.append([])
        elif t == ')':
            l = stack.pop()
            stack[-1].append(l)
        elif t[0] == '"':
            stack[-1].append(t[1:-1].replace('\\"', '"'))
        else:
            stack[-1].append(t)
    return stack[0][0]


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def lib_symbols(path):
    root = parse(open(path, encoding='utf8').read())
    return {s[1]: s for s in find(root, 'symbol')}


def sym_info(lib, name):
    """Return (properties, [(pin number, pin name, electrical type)])."""
    s = lib[name]
    props = {p[1]: p[2] for p in find(s, 'property')}
    base = s
    ext = find(s, 'extends')
    if ext:
        base = lib[ext[0][1]]
        bp = {p[1]: p[2] for p in find(base, 'property')}
        bp.update(props)
        props = bp
    pins = []
    for sub in find(base, 'symbol'):
        for p in find(sub, 'pin'):
            pins.append((find(p, 'number')[0][1], find(p, 'name')[0][1], p[1]))
    return props, pins
