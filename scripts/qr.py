"""Make the QR code matrix for the bottom silkscreen (system python; uses cv2 only to verify).

  python scripts/qr.py  ->  scripts/qr_matrix.txt   (25 x 25, '1' = dark module)

Version 2, error correction Q, alphanumeric mode (upper-case URL: scheme, host and GitHub
user names are case-insensitive).
"""
import os
import sys

TEXT = 'HTTPS://GITHUB.COM/DVIRCHAKIM'
SIZE = 25
DATA_CW, EC_CW = 22, 22                  # version 2-Q, one block
ALNUM = '0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ $%*+-./:'

# ---- data bits
bits = []
def put(v, n):
    for i in range(n - 1, -1, -1):
        bits.append((v >> i) & 1)
put(0b0010, 4)
put(len(TEXT), 9)
for i in range(0, len(TEXT) - 1, 2):
    put(ALNUM.index(TEXT[i]) * 45 + ALNUM.index(TEXT[i + 1]), 11)
if len(TEXT) % 2:
    put(ALNUM.index(TEXT[-1]), 6)
assert len(bits) <= DATA_CW * 8, len(bits)
put(0, min(4, DATA_CW * 8 - len(bits)))
put(0, (-len(bits)) % 8)
data = [int(''.join(map(str, bits[i:i + 8])), 2) for i in range(0, len(bits), 8)]
pad = [0xEC, 0x11]
while len(data) < DATA_CW:
    data.append(pad[(len(data) - len(bits) // 8) % 2])

# ---- Reed-Solomon over GF(256), polynomial 0x11D
def gmul(a, b):
    r = 0
    while b:
        if b & 1:
            r ^= a
        a <<= 1
        if a & 0x100:
            a ^= 0x11D
        b >>= 1
    return r
gen = [1]
root = 1
for _ in range(EC_CW):
    gen = [gmul(g, root) ^ (gen[i + 1] if i + 1 < len(gen) else 0) for i, g in enumerate(gen)]
    gen = [1] + gen if False else gen
    root = gmul(root, 2)
# gen now holds the generator polynomial without its leading 1 -- rebuild it the plain way to be safe
gen = [1]
root = 1
for _ in range(EC_CW):
    nxt = [0] * (len(gen) + 1)
    for i, g in enumerate(gen):
        nxt[i] ^= g
        nxt[i + 1] ^= gmul(g, root)
    gen = nxt
    root = gmul(root, 2)
rem = [0] * EC_CW
for d in data:
    f = d ^ rem[0]
    rem = rem[1:] + [0]
    for i in range(EC_CW):
        rem[i] ^= gmul(gen[i + 1], f)
codewords = data + rem

# ---- function patterns
M = [[0] * SIZE for _ in range(SIZE)]
F = [[False] * SIZE for _ in range(SIZE)]
def setf(x, y, v):
    if 0 <= x < SIZE and 0 <= y < SIZE:
        M[y][x] = 1 if v else 0
        F[y][x] = True
for cx, cy in ((3, 3), (SIZE - 4, 3), (3, SIZE - 4)):
    for dy in range(-4, 5):
        for dx in range(-4, 5):
            d = max(abs(dx), abs(dy))
            setf(cx + dx, cy + dy, d != 2 and d != 4)
for dy in range(-2, 3):                                  # alignment pattern, centre (18, 18)
    for dx in range(-2, 3):
        setf(18 + dx, 18 + dy, max(abs(dx), abs(dy)) != 1)
for i in range(SIZE):
    if not F[6][i]:
        setf(i, 6, i % 2 == 0)
    if not F[i][6]:
        setf(6, i, i % 2 == 0)

def draw_format(mask):
    d = (0b11 << 3) | mask                               # Q = 11
    r = d
    for _ in range(10):
        r = (r << 1) ^ ((r >> 9) * 0x537)
    fb = ((d << 10) | r) ^ 0x5412
    b = lambda i: (fb >> i) & 1
    for i in range(6):
        setf(8, i, b(i))
    setf(8, 7, b(6)); setf(8, 8, b(7)); setf(7, 8, b(8))
    for i in range(9, 15):
        setf(14 - i, 8, b(i))
    for i in range(8):
        setf(SIZE - 1 - i, 8, b(i))
    for i in range(8, 15):
        setf(8, SIZE - 15 + i, b(i))
    setf(8, SIZE - 8, 1)
draw_format(0)                                           # reserves the format area

# ---- data placement
i = 0
right = SIZE - 1
while right >= 1:
    if right == 6:
        right = 5
    for vert in range(SIZE):
        for j in range(2):
            x = right - j
            up = ((right + 1) & 2) == 0
            y = SIZE - 1 - vert if up else vert
            if not F[y][x] and i < len(codewords) * 8:
                M[y][x] = (codewords[i >> 3] >> (7 - (i & 7))) & 1
                i += 1
    right -= 2
assert i == len(codewords) * 8

MASKS = [lambda x, y: (x + y) % 2 == 0, lambda x, y: y % 2 == 0, lambda x, y: x % 3 == 0,
         lambda x, y: (x + y) % 3 == 0, lambda x, y: (x // 3 + y // 2) % 2 == 0,
         lambda x, y: x * y % 2 + x * y % 3 == 0, lambda x, y: (x * y % 2 + x * y % 3) % 2 == 0,
         lambda x, y: ((x + y) % 2 + x * y % 3) % 2 == 0]

def penalty(m):
    p = 0
    for lines in (m, [list(c) for c in zip(*m)]):
        for row in lines:
            run = 1
            for a, b in zip(row, row[1:]):
                run = run + 1 if a == b else 1
                if run == 5:
                    p += 3
                elif run > 5:
                    p += 1
            s = ''.join(map(str, row))
            p += 40 * (s.count('10111010000') + s.count('00001011101'))
    for y in range(SIZE - 1):
        for x in range(SIZE - 1):
            if m[y][x] == m[y][x + 1] == m[y + 1][x] == m[y + 1][x + 1]:
                p += 3
    dark = sum(map(sum, m)) * 100 // (SIZE * SIZE)
    return p + 10 * (abs(dark - 50) // 5)

best = None
base = [row[:] for row in M]
for k, fn in enumerate(MASKS):
    M = [row[:] for row in base]
    for y in range(SIZE):
        for x in range(SIZE):
            if not F[y][x] and fn(x, y):
                M[y][x] ^= 1
    draw_format(k)
    sc = penalty(M)
    if best is None or sc < best[0]:
        best = (sc, k, [row[:] for row in M])
M = best[2]
print('mask', best[1], 'penalty', best[0])

# ---- verify by decoding a rendered image
try:
    import numpy as np
    import cv2
    ok = True
    for scale, quiet in ((10, 4), (6, 3)):
        n = (SIZE + 2 * quiet) * scale
        img = np.full((n, n), 255, np.uint8)
        for y in range(SIZE):
            for x in range(SIZE):
                if M[y][x]:
                    img[(y + quiet) * scale:(y + quiet + 1) * scale, (x + quiet) * scale:(x + quiet + 1) * scale] = 0
        txt = cv2.QRCodeDetector().detectAndDecode(img)[0]
        print('decoded (quiet zone %d):' % quiet, repr(txt))
        ok = ok and txt == TEXT
    if not ok:
        sys.exit('QR verification FAILED')
except ImportError:
    print('cv2 not available - NOT verified')
out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'qr_matrix.txt')
open(out, 'w').write('\n'.join(''.join(map(str, r)) for r in M) + '\n')
print('wrote', out)
