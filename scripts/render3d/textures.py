"""Board-face textures (30 px/mm) from the board's own layers: black mask, faint copper relief,
ENIG pads, white silk, dark holes.  usage: python textures.py WORKDIR   (run run.sh, which exports the layers)"""
import sys, os
import numpy as np
from PIL import Image, ImageDraw
D = sys.argv[1]
def ink(name):
    return np.asarray(Image.open(os.path.join(D, 'L_%s-1.png' % name)).convert('L'))[:1200, :2040] < 128
holes = [(18.75, 4.75, 1.6), (49.25, 4.75, 1.6), (18.75, 35.25, 1.6), (49.25, 35.25, 1.6)] + \
        [(0.98 + x, 7.3 + y, 1.125) for x in (2.03, 64.01) for y in (2.03, 23.37)]
for side in ('F', 'B'):
    cu, opening, silk = ink(side + '.Cu'), ink(side + '.Mask'), ink(side + '.SilkS')
    img = np.zeros((1200, 2040, 3), np.float32)
    img[:] = (0.035, 0.04, 0.04)
    img[cu] = (0.10, 0.105, 0.10)
    img[opening & cu] = (0.85, 0.68, 0.32)
    img[opening & ~cu] = (0.32, 0.29, 0.20)
    img[silk & ~opening] = (0.93, 0.93, 0.91)
    im = Image.fromarray((img * 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    for x, y, r in holes:
        d.ellipse([(x - r) * 30, (y - r) * 30, (x + r) * 30, (y + r) * 30], fill=(8, 8, 8))
    im.save(os.path.join(D, 'tex_%s.png' % side))
