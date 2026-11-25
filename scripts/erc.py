"""Electrical rules check for the generated schematic, plus schematic <-> PCB parity.

  "C:\\Program Files\\KiCad\\7.0\\bin\\python.exe" scripts/erc.py

KiCad 7 has no command-line ERC.  The schematic gen.py writes is simple - every symbol pin is passive, and
every pin end carries either a global label (its net) or a no-connect flag, with no wires or power symbols -
so the ERC checks that can fire on it are the ones below, and they are checked here directly:

  pin_not_connected     every pin end has a label or a no-connect flag, never both, never two labels
  label_dangling        every label / no-connect flag sits on a pin end
  single_global_label   every net reaches at least two pins
  duplicate_reference   references are unique
  lib_symbol_issues     embedded symbols match fc.kicad_sym
  (power_pin_not_driven / pin_to_pin need power_in or output pins; there are none - checked too)

Then the netlist read from the schematic is compared with the PCB pad by pad (KiCad's "Update PCB from
Schematic" would report these): same parts, same footprints, same values, same net on every pad, same link
(KIID path) from every footprint to its symbol.  Exit code 0 = clean.
"""
import os
import sys
import uuid
from collections import defaultdict
import pcbnew
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sexp

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCH = os.path.join(ROOT, 'portenta_drone_fc.kicad_sch')
LIB = os.path.join(ROOT, 'fc.kicad_sym')
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
NS = uuid.UUID('5f0f6a34-3c0e-4d55-9b0e-0d6a5a1f7e11')          # as gen.py
R = lambda v: round(float(v), 3)

root = sexp.parse(open(SCH, encoding='utf8').read())
errors = []


def err(kind, msg):
    errors.append((kind, msg))


# ---- library symbols embedded in the schematic: pins (number -> (x, y, type)) ----
def pins_of(sym):
    out = {}
    for unit in [sym] + sexp.find(sym, 'symbol'):
        for p in sexp.find(unit, 'pin'):
            at = sexp.find(p, 'at')[0]
            num = sexp.find(p, 'number')[0][1]
            out[num] = (R(at[1]), R(at[2]), p[1])
    return out


emb = {s[1]: s for s in sexp.find(sexp.find(root, 'lib_symbols')[0], 'symbol')}
lib = sexp.lib_symbols(LIB)
for name, s in emb.items():
    short = name.split(':', 1)[1]
    if short not in lib:
        err('lib_symbol_issues', '%s is not in fc.kicad_sym' % name)
    elif pins_of(lib[short]) != pins_of(s):
        err('lib_symbol_issues', '%s differs from fc.kicad_sym' % name)
types = defaultdict(int)
for s in emb.values():
    for _, _, t in pins_of(s).values():
        types[t] += 1
for t in types:
    if t not in ('passive',):
        err('pin types', '%d pins of type %s - this script assumes passive pins only' % (types[t], t))

# ---- placed symbols: pin ends in sheet coordinates ----
parts = {}               # ref -> dict(value, fp, uuid, pins{num: (x, y)})
for s in sexp.find(root, 'symbol'):
    at = sexp.find(s, 'at')[0]
    X, Y, rot = R(at[1]), R(at[2]), R(at[3]) if len(at) > 3 else 0
    if rot or sexp.find(s, 'mirror'):
        err('script', 'symbol at %s %s is rotated/mirrored - not handled' % (X, Y))
    props = {p[1]: p[2] for p in sexp.find(s, 'property')}
    ref = props['Reference']
    if ref in parts:
        err('duplicate_reference', ref)
    lp = pins_of(emb[sexp.find(s, 'lib_id')[0][1]])
    parts[ref] = dict(value=props.get('Value'), fp=props.get('Footprint'), uuid=sexp.find(s, 'uuid')[0][1],
                      pins={n: (R(X + x), R(Y - y)) for n, (x, y, _) in lp.items()})

at_point = defaultdict(list)       # (x, y) -> [('pin', ref, num) | ('label', net) | ('nc',)]
for ref, p in parts.items():
    for n, xy in p['pins'].items():
        at_point[xy].append(('pin', ref, n))
for g in sexp.find(root, 'global_label') + sexp.find(root, 'label') + sexp.find(root, 'hierarchical_label'):
    at = sexp.find(g, 'at')[0]
    at_point[(R(at[1]), R(at[2]))].append(('label', g[1]))
for nc in sexp.find(root, 'no_connect'):
    at = sexp.find(nc, 'at')[0]
    at_point[(R(at[1]), R(at[2]))].append(('nc',))
if sexp.find(root, 'wire') or sexp.find(root, 'junction'):
    err('script', 'schematic has wires/junctions - not handled')

net_pins = defaultdict(list)        # net -> [(ref, pin)]
pin_net = {}
for xy, items in at_point.items():
    pins = [i for i in items if i[0] == 'pin']
    labels = [i[1] for i in items if i[0] == 'label']
    ncs = [i for i in items if i[0] == 'nc']
    if not pins:
        err('label_dangling', '%s at %s touches no pin' % (labels or 'no-connect flag', xy))
        continue
    if len(pins) > 1:
        err('pin_to_pin', 'pins %s overlap at %s' % (pins, xy))
    if len(set(labels)) > 1:
        err('multiple_net_names', '%s on one pin at %s' % (labels, xy))
    if labels and ncs:
        err('no_connect_connected', 'pin %s-%s has a label and a no-connect flag' % pins[0][1:])
    if not labels and not ncs:
        err('pin_not_connected', 'pin %s-%s' % pins[0][1:])
    for _, ref, n in pins:
        if labels:
            net_pins[labels[0]].append((ref, n))
            pin_net[(ref, n)] = labels[0]
for net, pins in net_pins.items():
    if len(pins) < 2:
        err('single_global_label', 'net %s reaches only %s-%s' % ((net,) + pins[0]))

nets = len(net_pins)
nc_count = sum(1 for items in at_point.values() if any(i[0] == 'nc' for i in items))
print('schematic: %d symbols, %d pins, %d nets, %d no-connect flags' % (
    len(parts), sum(len(p['pins']) for p in parts.values()), nets, nc_count))

# ---- schematic <-> PCB ----
board = pcbnew.LoadBoard(PCB)
fps = {f.GetReference(): f for f in board.GetFootprints()}
board_only = [r for r in fps if r not in parts and fps[r].GetPadCount() and any(p.GetNetname() for p in fps[r].Pads())]
for r in board_only:
    err('pcb', '%s is on the PCB with connected pads but not in the schematic' % r)
for ref, p in parts.items():
    f = fps.get(ref)
    if f is None:
        err('pcb', '%s is in the schematic but not on the PCB' % ref)
        continue
    if f.GetFPIDAsString() != p['fp']:
        err('pcb', '%s footprint: schematic %s, PCB %s' % (ref, p['fp'], f.GetFPIDAsString()))
    if f.GetValue() != p['value'] and not ref.startswith('TP'):     # test pads carry short silk labels (sync_values.py)
        err('pcb', '%s value: schematic %s, PCB %s' % (ref, p['value'], f.GetValue()))
    if f.GetPath().AsString() != '/' + p['uuid']:
        err('pcb', '%s is not linked to its symbol (path %r)' % (ref, f.GetPath().AsString()))
    for pad in f.Pads():
        num = pad.GetNumber()
        if not num:
            continue
        want = pin_net.get((ref, num), '')
        if num not in p['pins'] and not (ref.startswith('J') and num in ('MP',)):
            if pad.GetNetname():
                err('pcb', '%s pad %s (net %s) has no schematic pin' % (ref, num, pad.GetNetname()))
            continue
        if pad.GetNetname() != want:
            err('pcb', '%s-%s: schematic net %r, PCB net %r' % (ref, num, want, pad.GetNetname()))

bykind = defaultdict(list)
for k, m in errors:
    bykind[k].append(m)
for k, ms in sorted(bykind.items()):
    print('[%s] %d' % (k, len(ms)))
    for m in ms[:12]:
        print('   ', m)
print('ERC: %d violations' % len(errors) if errors else 'ERC clean: 0 violations, schematic and PCB agree pad for pad')
sys.exit(1 if errors else 0)
