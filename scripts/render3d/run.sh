#!/bin/sh
# 3D renders of the carrier (docs/render_assembled.png, docs/render_carrier.png), headless.
# Needs KiCad 7, Blender 4.5, pdftoppm, Python 3 with numpy + Pillow, and Arduino's Portenta Breakout CAD
# bundle (for the H7 model, CC BY-SA): https://docs.arduino.cc/static/57b7f5b6617fcea61e85cd5a42db89ff/ASX00031-cad-files.zip
# usage (from the project folder, Git Bash):  sh scripts/render3d/run.sh WORKDIR ASX00031-cad-files.zip
set -e
W=$1; ZIP=$2; S=$(dirname "$0")
K="/c/Program Files/KiCad/7.0/bin/kicad-cli.exe"; B="/c/Program Files/Blender Foundation/Blender 4.5/blender.exe"
mkdir -p "$W"
# H7: extract Arduino's embedded model from the Breakout's Altium file, reduce it to coloured blocks
python -I -c "import zipfile,sys; zipfile.ZipFile(sys.argv[1]).extract('ASX00031-cad-files/Altium files/PCB.PcbDoc', sys.argv[2])" "$ZIP" "$W"
python -I "$S/altmodels.py" "$W/ASX00031-cad-files/Altium files/PCB.PcbDoc" "$W" "$S"
python -I "$S/step_bbox.py" "$W/PortentaH7.step" "$W/h7.json"
python -I "$S/h7obj.py" "$W/h7.json" "$W/h7_blocks" 1.6 -1
# carrier: STEP export (headless) -> one block per part; board faces from the real layers
"$K" pcb export step --subst-models --force --user-origin 0x0mm -o "$(cygpath -w "$W")\carrier.step" portenta_drone_fc.kicad_pcb
python -I "$S/step_bbox.py" "$W/carrier.step" "$W/carrier.json"
python -I "$S/carrierobj.py" "$W/carrier.json" "$W/carrier_parts"
sed 's/(paper "[^"]*")/(paper "User" 68 40)/' portenta_drone_fc.kicad_pcb > "$W/tex.kicad_pcb"; cp portenta_drone_fc.kicad_pro "$W/tex.kicad_pro"
for L in F.Cu F.Mask F.SilkS B.Cu B.Mask B.SilkS; do
  "$K" pcb export pdf --black-and-white --layers $L -o "$W/L_$L.pdf" "$W/tex.kicad_pcb" >/dev/null
  pdftoppm -r 762 -gray -png "$W/L_$L.pdf" "$W/L_$L"
done
python "$S/textures.py" "$W"
for m in assembled carrier; do
  "$B" -b --factory-startup -P "$S/render.py" -- "$(cygpath -w "$W")" $m "$(cygpath -w "$PWD")\docs\render_$m.png"
done
