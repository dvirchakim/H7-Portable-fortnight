"""Generate the KiCad 7 project (schematic + placed PCB) from design.py.

Run with KiCad's bundled interpreter:
  "C:\\Program Files\\KiCad\\7.0\\bin\\python.exe" scripts\\gen.py
"""
import os
import sys
import uuid
import json
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import design as D
import pcbnew

NAME = 'portenta_drone_fc'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KICAD_FP = r'C:\Program Files\KiCad\7.0\share\kicad\footprints'
NS = uuid.UUID('5f0f6a34-3c0e-4d55-9b0e-0d6a5a1f7e11')


def uid(*k):
    return str(uuid.uuid5(NS, '/'.join(str(x) for x in k)))


ROOT_UUID = uid('root')


def q(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


# =============================================================== DF40 footprint
def write_df40():
    """80-pin DF40 receptacle land pattern.

    Pad geometry follows Hirose drawing EDC-337747-51-01 (docs/DF40HC_3.5_80DS_drawing.pdf),
    "recommended pattern": pitch 0.4, pad width 0.2, pad rows 3.78 mm outside / 2.38 mm inside
    (0.70 mm long pads centred at x = +/-1.54), 15.6 mm between first and last pad.
    Body is 18.6 x 3.38 mm. Odd pins in the -x row, even pins in the +x row, pin 1/2 at +y
    (the pin numbering is this project's convention - see README about orientation).
    """
    os.makedirs(os.path.join(ROOT, 'fc.pretty'), exist_ok=True)
    name = 'Hirose_DF40HC(3.5)-80DS-0.4V_2x40_P0.4mm'
    px, pw, pl, pitch = 1.54, 0.20, 0.70, 0.4
    y0 = 39 * pitch / 2
    o = ['(footprint %s (version 20221018) (generator gen.py) (layer "F.Cu")' % q(name),
         '  (descr "Hirose DF40HC(3.5)-80DS-0.4V(51) receptacle, mates with Arduino Portenta '
         'high-density plug DF40C-80DP-0.4V(51). Land pattern per Hirose drawing EDC-337747-51-01.")',
         '  (attr smd)',
         '  (fp_text reference "REF**" (at 0 -10.7) (layer "F.SilkS") (effects (font (size 0.8 0.8) (thickness 0.12))))',
         '  (fp_text value %s (at 0 10.6) (layer "F.Fab") (effects (font (size 0.6 0.6) (thickness 0.1))))' % q(name)]

    def rect(layer, hx, hy, w):
        pts = [(-hx, -hy), (hx, -hy), (hx, hy), (-hx, hy), (-hx, -hy)]
        for a, b in zip(pts, pts[1:]):
            o.append('  (fp_line (start %g %g) (end %g %g) (stroke (width %g) (type solid)) (layer %s))'
                     % (a[0], a[1], b[0], b[1], w, q(layer)))
    rect('F.Fab', 1.69, 9.3, 0.1)
    rect('F.CrtYd', 2.4, 9.8, 0.05)
    for sx in (-1, 1):
        for sy in (-1, 1):
            o.append('  (fp_line (start %g %g) (end %g %g) (stroke (width 0.12) (type solid)) (layer "F.SilkS"))'
                     % (sx * 1.0, sy * 9.45, sx * 2.1, sy * 9.45))
    o.append('  (fp_circle (center -2.7 %g) (end -2.5 %g) (stroke (width 0.2) (type solid)) (fill solid) (layer "F.SilkS"))' % (y0, y0))
    for n in range(1, 81):
        k = (n - 1) // 2
        x = -px if n % 2 else px
        y = y0 - k * pitch
        o.append('  (pad "%d" smd rect (at %g %g) (size %g %g) (layers "F.Cu" "F.Paste" "F.Mask"))'
                 % (n, x, round(y, 4), pl, pw))
    o.append(')')
    open(os.path.join(ROOT, 'fc.pretty', name + '.kicad_mod'), 'w', encoding='utf8').write('\n'.join(o) + '\n')


# =============================================================== symbols
def sym_layout(p):
    """Return (half_width, {num: (x, y, side)}, rows) in symbol coords (y up)."""
    pins = p['pins']
    sym = p['sym']
    if sym.startswith('PORTENTA'):
        left = [n for n, _ in pins if int(n) % 2]
        right = [n for n, _ in pins if not int(n) % 2]
        hw = 22.86
    elif len(pins) == 1:
        left, right, hw = [pins[0][0]], [], 2.54
    elif len(pins) == 2:
        left, right, hw = [pins[0][0]], [pins[1][0]], 2.54
    else:
        h = (len(pins) + 1) // 2
        left = [n for n, _ in pins[:h]]
        right = [n for n, _ in pins[h:]][::-1]
        hw = 10.16
    rows = max(len(left), len(right))
    pos = {}
    for i, n in enumerate(left):
        pos[n] = (-hw - 2.54, (rows - 1) * 1.27 - i * 2.54, 'L')
    for i, n in enumerate(right):
        pos[n] = (hw + 2.54, (rows - 1) * 1.27 - i * 2.54, 'R')
    return hw, pos, rows


def sym_def(p):
    hw, pos, rows = sym_layout(p)
    sid = 'fc:' + p['sym']
    base = p['sym']
    small = len(p['pins']) <= 2
    hh = rows * 1.27 + (0 if small else 1.27)
    prefix = ''.join(c for c in p['ref'] if c.isalpha())
    o = ['    (symbol %s %s(in_bom yes) (on_board yes)' % (
        q(sid), '(pin_numbers hide) (pin_names (offset 0.5) hide) ' if small else '(pin_names (offset 0.6)) ')]
    for key, val, hide in (('Reference', prefix, ''), ('Value', base, ''),
                           ('Footprint', '', ' hide'), ('Datasheet', '', ' hide')):
        o.append('      (property %s %s (at 0 0 0) (effects (font (size 1.27 1.27))%s))' % (q(key), q(val), hide))
    o.append('      (symbol %s (rectangle (start %g %g) (end %g %g) (stroke (width 0.254) (type default)) (fill (type background))))'
             % (q(base + '_0_1'), -hw, hh, hw, -hh))
    o.append('      (symbol %s' % q(base + '_1_1'))
    for num, name in p['pins']:
        x, y, side = pos[num]
        o.append('        (pin passive line (at %g %g %d) (length 2.54) (name %s (effects (font (size 1 1)))) (number %s (effects (font (size 1 1)))))'
                 % (x, y, 0 if side == 'L' else 180, q(name), q(num)))
    o.append('      )')
    o.append('    )')
    return '\n'.join(o)


def write_schematic():
    defs = {}
    body = []
    COLW, YMAX = 106.68, 540.0
    cx, cy = 60.96, 25.4
    last_block = None
    for p in D.PARTS:
        defs.setdefault(p['sym'], sym_def(p))
        hw, pos, rows = sym_layout(p)
        h = rows * 2.54 + 10.16
        new_block = p['block'] != last_block
        if cy + h + (10.16 if new_block else 0) > YMAX:
            cx += COLW
            cy = 25.4
        if new_block:
            body.append('  (text %s (at %g %g 0) (effects (font (size 2.54 2.54) (thickness 0.4) bold) (justify left bottom)) (uuid %s))'
                        % (q(p['block']), cx - 30.48, cy, uid('txt', p['block'], cx, cy)))
            cy += 7.62
            last_block = p['block']
        X = cx
        Y = round((cy + rows * 1.27 + 2.54) / 1.27) * 1.27
        su = uid('sym', p['ref'])
        p['uuid'] = su
        top = Y - rows * 1.27 - 2.54
        dnp = p['ref'] in getattr(D, 'DNP', {})
        s = ['  (symbol (lib_id %s) (at %g %g 0) (unit 1) (in_bom %s) (on_board yes) (dnp %s) (uuid %s)'
             % (q('fc:' + p['sym']), X, Y, 'no' if dnp else 'yes', 'yes' if dnp else 'no', su)]
        s.append('    (property "Reference" %s (at %g %g 0) (effects (font (size 1.27 1.27)) (justify left)))' % (q(p['ref']), X - hw, top))
        s.append('    (property "Value" %s (at %g %g 0) (effects (font (size 1.27 1.27)) (justify left)))' % (q(p['value']), X - hw + 7.62, top))
        s.append('    (property "Footprint" %s (at %g %g 0) (effects (font (size 1.27 1.27)) hide))' % (q(p['fp']), X, Y))
        s.append('    (property "Datasheet" "" (at %g %g 0) (effects (font (size 1.27 1.27)) hide))' % (X, Y))
        if p['mpn']:
            s.append('    (property "MPN" %s (at %g %g 0) (effects (font (size 1.27 1.27)) hide))' % (q(p['mpn']), X, Y))
        for num, _ in p['pins']:
            s.append('    (pin %s (uuid %s))' % (q(num), uid('pin', p['ref'], num)))
        s.append('    (instances (project %s (path %s (reference %s) (unit 1))))' % (q(NAME), q('/' + ROOT_UUID), q(p['ref'])))
        s.append('  )')
        body.append('\n'.join(s))
        for num, _ in p['pins']:
            px, py, side = pos[num]
            ax, ay = round(X + px, 4), round(Y - py, 4)
            net = p['nets'].get(num)
            if net is None:
                body.append('  (no_connect (at %g %g) (uuid %s))' % (ax, ay, uid('nc', p['ref'], num)))
            else:
                body.append('  (global_label %s (shape passive) (at %g %g %d) (effects (font (size 1.27 1.27)) (justify %s)) (uuid %s))'
                            % (q(net), ax, ay, 180 if side == 'L' else 0,
                               'right' if side == 'L' else 'left', uid('lbl', p['ref'], num)))
        cy += h
    lib = '\n'.join(defs.values())
    sch = ['(kicad_sch (version 20230121) (generator eeschema)', '  (uuid %s)' % ROOT_UUID,
           '  (paper "A1")',
           '  (title_block (title "Portenta H7 drone flight-controller carrier") (rev "0.1")'
           ' (comment 1 "Generated by scripts/gen.py from scripts/design.py"))',
           '  (lib_symbols', lib, '  )'] + body + [
           '  (sheet_instances (path "/" (page "1")))', ')']
    open(os.path.join(ROOT, NAME + '.kicad_sch'), 'w', encoding='utf8').write('\n'.join(sch) + '\n')
    symlib = '(kicad_symbol_lib (version 20220914) (generator gen.py)\n' + \
        lib.replace('(symbol "fc:', '(symbol "') + '\n)\n'
    open(os.path.join(ROOT, 'fc.kicad_sym'), 'w', encoding='utf8').write(symlib)


# =============================================================== PCB
def mm(v):
    return pcbnew.FromMM(float(v))


def vec(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def load_fp(fpid):
    lib, name = fpid.split(':', 1)
    path = os.path.join(ROOT, 'fc.pretty') if lib == 'fc' else os.path.join(KICAD_FP, lib + '.pretty')
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise SystemExit('footprint not found: ' + fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def add_line(board, layer, a, b, w=0.1):
    s = pcbnew.PCB_SHAPE(board)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(vec(*a))
    s.SetEnd(vec(*b))
    s.SetLayer(layer)
    s.SetWidth(mm(w))
    board.Add(s)


def add_rect(board, layer, x0, y0, x1, y1, w=0.1):
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    for a, b in zip(pts, pts[1:]):
        add_line(board, layer, a, b, w)


def add_text(board, layer, txt, x, y, size=1.0, mirror=False):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(txt)
    t.SetPosition(vec(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(size * 0.15))
    t.SetMirrored(mirror)
    board.Add(t)


def write_pcb():
    board = pcbnew.BOARD()
    board.SetCopperLayerCount(4)
    nets = {}

    def net(n):
        if n not in nets:
            ni = pcbnew.NETINFO_ITEM(board, n)
            board.Add(ni)
            nets[n] = ni
        return nets[n]

    add_rect(board, pcbnew.Edge_Cuts, 0, 0, D.BOARD_W, D.BOARD_H, 0.1)
    # Portenta outline for reference
    add_rect(board, pcbnew.Dwgs_User, D.H7_X0, D.H7_Y0, D.H7_X0 + D.H7_W, D.H7_Y0 + D.H7_H, 0.15)
    add_text(board, pcbnew.Dwgs_User, 'PORTENTA H7 OUTLINE (top view) - USB-C THIS END', 22, D.H7_Y0 + 1.3, 0.8)
    add_text(board, pcbnew.F_SilkS, 'USB', 1.6, 20.0, 0.9)
    add_text(board, pcbnew.F_SilkS, 'J1', D.J1_POS[0] + 4.2, 20.0, 0.9)
    add_text(board, pcbnew.F_SilkS, 'J2', D.J2_POS[0] - 4.2, 20.0, 0.9)

    report = []
    boxes = []
    for p in D.PARTS:
        fp = load_fp(p['fp'])
        fp.SetReference(p['ref'])
        fp.SetValue(p['value'])
        board.Add(fp)
        fp.SetPosition(vec(p['x'], p['y']))
        if p['side'] == 'B':
            fp.Flip(fp.GetPosition(), False)
        fp.SetOrientationDegrees(p['rot'])
        try:
            fp.SetPath(pcbnew.KIID_PATH('/' + p['uuid']))
        except Exception as e:      # linking is a convenience only
            report.append('note: could not set path for %s (%s)' % (p['ref'], e))
        seen = set()
        for pad in fp.Pads():
            num = pad.GetNumber()
            seen.add(num)
            n = p['nets'].get(num)
            if n:
                pad.SetNet(net(n))
        for num in p['nets']:
            if num not in seen:
                report.append('ERROR: %s has no pad %s in %s' % (p['ref'], num, p['fp']))
        for num in seen:
            if num and num not in dict(p['pins']):
                report.append('ERROR: %s footprint pad %s not in symbol' % (p['ref'], num))
        bb = None
        try:
            fp.BuildCourtyardCaches()
            layer = pcbnew.B_CrtYd if p['side'] == 'B' else pcbnew.F_CrtYd
            c = fp.GetCourtyard(layer)
            if c.OutlineCount():
                bb = c.BBox()
        except Exception:
            bb = None
        if bb is None:
            bb = fp.GetBoundingBox(False, False)
        boxes.append((p['ref'], p['side'], pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()),
                      pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom())))

    for i, (x, y) in enumerate(D.M3_HOLES):
        fp = load_fp('MountingHole:MountingHole_3.2mm_M3')
        fp.SetReference('H%d' % (i + 1)); fp.SetValue('M3 30.5mm stack')
        board.Add(fp); fp.SetPosition(vec(x, y))
    for i, (x, y) in enumerate(D.M2_HOLES):
        fp = load_fp('MountingHole:MountingHole_2.2mm_M2')
        fp.SetReference('H%d' % (i + 5)); fp.SetValue('M2 Portenta standoff')
        board.Add(fp); fp.SetPosition(vec(x, y))

    # no tracks / vias under mounting hardware (also what the autorouter sees instead of the holes)
    for holes, r in ((D.M3_HOLES, 3.2), (D.M2_HOLES, 1.7)):
        for hx, hy in holes:
            k = pcbnew.ZONE(board)
            k.SetIsRuleArea(True)
            k.SetDoNotAllowTracks(True)
            k.SetDoNotAllowVias(True)
            k.SetDoNotAllowCopperPour(False)
            k.SetDoNotAllowPads(False)
            k.SetDoNotAllowFootprints(False)
            ls = pcbnew.LSET()
            for cu in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
                ls.AddLayer(cu)
            k.SetLayerSet(ls)
            k.SetZoneName('HOLE_KEEPOUT')
            ol = k.Outline()
            ol.NewOutline()
            for i in range(16):
                ang = 2 * math.pi * i / 16
                ol.Append(mm(hx + r * math.cos(ang)), mm(hy + r * math.sin(ang)))
            board.Add(k)

    # Hirose drawing note 2: no foreign pattern under the DF40 body -> no top-layer tracks or
    # vias between the pad rows (inner pad ends are at +/-1.19 mm).
    for jx, jy in (D.J1_POS, D.J2_POS):
        k = pcbnew.ZONE(board)
        k.SetIsRuleArea(True)
        k.SetDoNotAllowTracks(True)
        k.SetDoNotAllowVias(True)
        k.SetDoNotAllowCopperPour(True)
        k.SetDoNotAllowPads(False)
        k.SetDoNotAllowFootprints(False)
        k.SetLayer(pcbnew.F_Cu)
        k.SetZoneName('SOCKET_KEEPOUT')
        ol = k.Outline()
        ol.NewOutline()
        for dx, dy in ((-1.1, -9.3), (1.1, -9.3), (1.1, 9.3), (-1.1, 9.3)):
            ol.Append(mm(jx + dx), mm(jy + dy))
        board.Add(k)

    try:
        for layer, zn in ((pcbnew.In1_Cu, 'GND'), (pcbnew.In2_Cu, '+5V')):
            z = pcbnew.ZONE(board)
            z.SetLayer(layer)
            z.SetNetCode(net(zn).GetNetCode())
            z.SetZoneName(zn + '_PLANE')
            z.SetLocalClearance(mm(0.2))
            z.SetMinThickness(mm(0.15))
            z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
            ol = z.Outline()
            ol.NewOutline()
            for x, y in [(0.3, 0.3), (D.BOARD_W - 0.3, 0.3), (D.BOARD_W - 0.3, D.BOARD_H - 0.3), (0.3, D.BOARD_H - 0.3)]:
                ol.Append(mm(x), mm(y))
            board.Add(z)
    except Exception as e:
        report.append('note: GND zone not added (%s)' % e)

    pcbnew.SaveBoard(os.path.join(ROOT, NAME + '.kicad_pcb'), board)

    # ---------------- placement checks
    for i, a in enumerate(boxes):
        if a[2] < 0 or a[3] < 0 or a[4] > D.BOARD_W or a[5] > D.BOARD_H:
            report.append('OFF-BOARD: %s bbox (%.2f,%.2f)-(%.2f,%.2f)' % (a[0], a[2], a[3], a[4], a[5]))
        for b in boxes[i + 1:]:
            if a[1] == b[1] and a[2] < b[4] and b[2] < a[4] and a[3] < b[5] and b[3] < a[5]:
                report.append('OVERLAP(%s): %s / %s' % (a[1], a[0], b[0]))
        for holes, r, nm in ((D.M3_HOLES, 3.3, 'M3'), (D.M2_HOLES, 1.9, 'M2')):
            for hx, hy in holes:
                dx = max(a[2] - hx, 0, hx - a[4])
                dy = max(a[3] - hy, 0, hy - a[5])
                if math.hypot(dx, dy) < (1.2 if (a[0] == 'J2' and nm == 'M2') else r):
                    report.append('HOLE CLEARANCE: %s within %.1f mm of %s hole at (%.1f, %.1f)' % (a[0], r, nm, hx, hy))
    # tall / top-side parts under the Portenta
    for a in boxes:
        if a[1] == 'F' and a[0] not in ('J1', 'J2'):
            inside = a[2] < D.H7_X0 + D.H7_W and a[4] > D.H7_X0 and a[3] < D.H7_Y0 + D.H7_H and a[5] > D.H7_Y0
            if inside and a[0][0] in 'JQLD':
                report.append('UNDER-H7 (check height): ' + a[0])
    return report, boxes


def net_table():
    t = {}
    for p in D.PARTS:
        for num, n in p['nets'].items():
            t.setdefault(n, []).append((p['ref'], num))
    return t


NC_BASE = dict(bus_width=12, diff_pair_gap=0.25, diff_pair_via_gap=0.25, diff_pair_width=0.2,
               line_style=0, microvia_diameter=0.3, microvia_drill=0.1, pcb_color="rgba(0, 0, 0, 0.000)",
               schematic_color="rgba(0, 0, 0, 0.000)", wire_width=6)


def write_project_files():
    pro = {"meta": {"filename": NAME + ".kicad_pro", "version": 1},
           "board": {"design_settings": {"defaults": {}, "rules": {
               "min_clearance": 0.1, "min_track_width": 0.127, "min_via_diameter": 0.45,
               "min_through_hole_diameter": 0.2, "min_via_annular_width": 0.1,
               "min_copper_edge_clearance": 0.25, "min_hole_clearance": 0.2,
               "min_hole_to_hole": 0.25}}},
           "net_settings": {"classes": [
               dict(NC_BASE, name="Default", clearance=0.127, track_width=0.15, via_diameter=0.45, via_drill=0.2),
               dict(NC_BASE, name="Rail", clearance=0.127, track_width=0.25, via_diameter=0.5, via_drill=0.25),
               dict(NC_BASE, name="Power", clearance=0.2, track_width=0.5, via_diameter=0.7, via_drill=0.35)],
               "meta": {"version": 3}, "net_colors": None,
               "netclass_patterns": [{"netclass": c, "pattern": n} for c, ns in D.NETCLASSES.items() for n in ns]},
           "schematic": {"legacy_lib_dir": "", "legacy_lib_list": []},
           "sheets": [[ROOT_UUID, ""]], "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []}}
    json.dump(pro, open(os.path.join(ROOT, NAME + '.kicad_pro'), 'w'), indent=2)
    open(os.path.join(ROOT, 'sym-lib-table'), 'w').write(
        '(sym_lib_table\n  (lib (name "fc")(type "KiCad")(uri "${KIPRJMOD}/fc.kicad_sym")(options "")(descr "Project symbols"))\n)\n')
    open(os.path.join(ROOT, 'fp-lib-table'), 'w').write(
        '(fp_lib_table\n  (lib (name "fc")(type "KiCad")(uri "${KIPRJMOD}/fc.pretty")(options "")(descr "Project footprints"))\n)\n')
    rows = ['Ref,Value,MPN,Footprint,Side,X_mm,Y_mm,Rot']
    for p in D.PARTS:
        rows.append('%s,%s,%s,%s,%s,%.2f,%.2f,%d' % (p['ref'], p['value'].replace(',', ';'), p['mpn'],
                                                    p['fp'], p['side'], p['x'], p['y'], p['rot']))
    open(os.path.join(ROOT, 'bom_placement.csv'), 'w').write('\n'.join(rows) + '\n')


if __name__ == '__main__':
    pcb_path = os.path.join(ROOT, NAME + '.kicad_pcb')
    if os.path.exists(pcb_path) and '--force' not in sys.argv:
        if any(True for _ in pcbnew.LoadBoard(pcb_path).GetTracks()):
            raise SystemExit('PCB already has routing; re-run with --force to overwrite it.')
    write_df40()
    write_schematic()
    report, boxes = write_pcb()
    write_project_files()
    nt = net_table()
    json.dump({k: sorted(v) for k, v in nt.items()}, open(os.path.join(ROOT, 'scripts', 'expected_nets.json'), 'w'), indent=1)
    for n, nodes in sorted(nt.items()):
        if len(nodes) < 2:
            report.append('SINGLE-PIN NET: %s %s' % (n, nodes))
    print('parts:', len(D.PARTS), 'nets:', len(nt))
    print('\n'.join(report) if report else 'no placement/net issues found')
