"""Print patch.py route commands for every pad DRC still reports as unconnected (reads out/drc.rpt)."""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WIDTH = {'+5V': 0.25, 'GND': 0.25, '+3V3': 0.25, '+3V3_SENS': 0.25, 'VBAT': 0.5, '+5V_BUCK': 0.5, 'BUCK_SW': 0.5}
txt = open(os.path.join(ROOT, 'out', 'drc.rpt')).read()
cmds = []
for block in re.findall(r'\[unconnected_items\].*?(?=\n\[|\Z)', txt, re.S):
    for num, net, ref in re.findall(r'Pad (\S+) \[([^\]]*)\] of (\S+)', block):
        c = 'route:%s-%s' % (ref, num) + (':%g' % WIDTH[net] if net in WIDTH else '')
        if c not in cmds:
            cmds.append(c)
print(' '.join(cmds))
