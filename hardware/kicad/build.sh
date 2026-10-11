#!/bin/bash
# Rebuild every BrainTech-16 hardware output from circuit.py. macOS paths; adjust for other systems.
#   ./build.sh            schematic + rule files + fab outputs from the current (routed) board
#   ./build.sh --pcb      ALSO regenerate placement and re-route (discards the current routing!)
set -e
cd "$(dirname "$0")"
KC=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
KPY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3
JAVA=/opt/homebrew/opt/openjdk/bin/java
FREEROUTING=${FREEROUTING:-../../../BrainTech/tools_ext/freerouting.jar}
q() { "$@" 2>/dev/null | grep -v '^$' | tail -1; }

python3 gen_schematic.py                                   # circuit.py -> braintech16.kicad_sch
python3 set_rules.py                                       # fab rules + net classes -> .kicad_pro
q $KC sch erc braintech16.kicad_sch -o erc.rpt
q $KC sch export pdf braintech16.kicad_sch -o braintech16_schematic.pdf
q $KC sch export netlist braintech16.kicad_sch -o braintech16.net
q $KC sch export bom braintech16.kicad_sch -o braintech16_bom.csv \
    --fields 'Reference,Value,Footprint,MPN,${QUANTITY}' --group-by Value,Footprint

if [ "$1" == "--pcb" ]; then
  $KPY gen_pcb.py                                          # placement
  python3 set_rules.py                                     # (saving a new board resets the project rules)
  $KPY gnd_vias.py                                         # every SMD ground pad -> own via to the plane
  $KPY route_prep.py                                       # -> braintech16.dsn
  $JAVA -Djava.awt.headless=true -jar "$FREEROUTING" -de braintech16.dsn -do braintech16.ses \
        -mp 100 -mt 4 --gui.enabled=false > freerouting.log 2>&1
  $KPY import_ses.py
fi

python3 set_rules.py
q $KC pcb drc --refill-zones --save-board braintech16.kicad_pcb -o drc.rpt
grep '^\*\* Found' drc.rpt

# fabrication outputs
rm -rf fab && mkdir -p fab/gerbers
q $KC pcb export gerbers braintech16.kicad_pcb -o fab/gerbers/ \
    --layers F.Cu,In1.Cu,In2.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts
q $KC pcb export drill braintech16.kicad_pcb -o fab/gerbers/ --format excellon --excellon-separate-th
q $KC pcb export pos braintech16.kicad_pcb -o fab/braintech16_pos.csv --format csv --units mm --side both
cp braintech16_bom.csv fab/
(cd fab && zip -qr braintech16_gerbers.zip gerbers)
q $KC pcb export step braintech16.kicad_pcb -o fab/braintech16.step --subst-models --force

# pictures
q $KC pcb render braintech16.kicad_pcb -o ../images/pcb_3d_top.png --side top --quality high --width 1600 --height 1520 --background opaque
q $KC pcb render braintech16.kicad_pcb -o ../images/pcb_3d_bottom.png --side bottom --quality high --width 1600 --height 1520 --background opaque
q $KC pcb render braintech16.kicad_pcb -o ../images/pcb_3d_iso.png --rotate '-40,0,30' --perspective --quality high --width 1800 --height 1300 --zoom 0.9 --background opaque
for L in F.Cu In2.Cu B.Cu; do
  q $KC pcb export pdf braintech16.kicad_pcb -o fab/$L.pdf --layers $L,Edge.Cuts --mode-single
  sips -s format png -Z 7000 fab/$L.pdf --out fab/tmp.png >/dev/null && rm fab/$L.pdf
  python3 crop_png.py fab/tmp.png ../images/copper_${L%.Cu}.png && rm fab/tmp.png
done
echo done
