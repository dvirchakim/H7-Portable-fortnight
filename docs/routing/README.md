[← Back to the main README](../../README.md)

# Routing

4 layers: F.Cu / In1 GND plane / In2 +5V plane / B.Cu. 0.15 mm signals, 0.25 mm rails, 0.5 mm
VBAT/buck. Flow (all in `scripts/`): `stitch.py nopour` places plane vias on the empty board ->
Freerouting 1.9.0 (`tools/`, `route.py export/import`) -> `stitch.py narrow` (+5V pours and
bridges) -> `leftovers.py` + `patch.py` (grid router: `route`, `reroute`, `regroup` rip-up,
`prune`) and `route.py ... only:NETS` for local Freerouting passes -> `netcheck.py NET --bridge`
for split pours -> `scripts/post_route.sh` (values, EMI fixes, fiducials, vias, silkscreen,
checks, exports). `out/unrouted.kicad_pcb` is the placed, unrouted board; earlier routings are kept
in `out/` as `routed_v1_*` / `routed_v2_*`.
