#!/bin/sh
# Everything after routing, in order (run from the project folder with Git Bash).
set -e
K="/c/Program Files/KiCad/7.0/bin/python.exe"
C="/c/Program Files/KiCad/7.0/bin/kicad-cli.exe"
P=portenta_drone_fc.kicad_pcb
q() { grep -v "swig/python detected\|no destructor found" || true; }
"$K" scripts/sync_values.py 2>&1 | q
"$K" scripts/emi_fix.py 2>&1 | q
"$K" scripts/fiducials.py 2>&1 | q
"$K" scripts/vias.py 2>&1 | q
"$K" scripts/finish.py 2>&1 | q
echo "== DRC"; grep -o "^\[[a-z_]*\]" out/drc.rpt | sort | uniq -c | grep -v "lib_" || true
"$K" scripts/netcheck.py +5V 2>&1 | q | head -2
"$K" scripts/netcheck.py GND 2>&1 | q | head -2
echo "== DFM"; "$K" scripts/dfm.py 2>&1 | q | awk 'NR==1 || $(NF-2)+0>0 || $(NF-1)+0>0'
echo "== EMI"; "$K" scripts/emi.py 2>&1 | q
rm -rf fab/gerbers fab/*.zip; mkdir -p fab/gerbers
"$C" pcb export gerbers -o fab/gerbers/ -l F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.SilkS,B.SilkS,F.Mask,B.Mask,Edge.Cuts --subtract-soldermask --no-x2 $P >/dev/null
"$C" pcb export drill -o fab/gerbers/ --format excellon --excellon-units mm --excellon-separate-th --excellon-zeros-format decimal $P >/dev/null
"$C" pcb export pos -o fab/pos_raw.csv --format csv --units mm --side both $P >/dev/null
"$K" -c "
import zipfile, os
z = zipfile.ZipFile('fab/portenta_drone_fc_gerbers.zip', 'w', zipfile.ZIP_DEFLATED)
for f in sorted(os.listdir('fab/gerbers')):
    if not f.endswith('.gbrjob'):
        z.write(os.path.join('fab/gerbers', f), f)
z.close()
print('gerber zip:', len(zipfile.ZipFile('fab/portenta_drone_fc_gerbers.zip').namelist()), 'files')"
"$K" scripts/jlc.py
"$K" scripts/jlc_place.py 2>&1 | q
for v in "top F.Cu,F.SilkS,Edge.Cuts" "bottom B.Cu,B.SilkS,Edge.Cuts"; do set -- $v
  "$C" pcb export pdf -o out/$1.pdf -l $2 $P >/dev/null; done
"$C" pcb export svg -o out/top.svg -l F.Cu,F.SilkS,Edge.Cuts --page-size-mode 2 --exclude-drawing-sheet $P >/dev/null
"$C" pcb export svg -o out/bottom.svg -l B.Cu,B.SilkS,Edge.Cuts --page-size-mode 2 --exclude-drawing-sheet --mirror $P >/dev/null
"$C" pcb export svg -o out/In1.svg -l In1.Cu,Edge.Cuts --page-size-mode 2 --exclude-drawing-sheet $P >/dev/null
"$C" pcb export svg -o out/In2.svg -l In2.Cu,Edge.Cuts --page-size-mode 2 --exclude-drawing-sheet $P >/dev/null
"$C" pcb export svg -o out/silk_top.svg -l F.SilkS,F.Mask,Edge.Cuts --black-and-white --page-size-mode 2 --exclude-drawing-sheet $P >/dev/null
"$C" pcb export svg -o out/silk_bottom.svg -l B.SilkS,B.Mask,Edge.Cuts --black-and-white --page-size-mode 2 --exclude-drawing-sheet --mirror $P >/dev/null
"$C" sch export pdf -o out/schematic.pdf portenta_drone_fc.kicad_sch >/dev/null 2>&1 || true
echo "== done"
