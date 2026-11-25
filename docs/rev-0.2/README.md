[← Back to the main README](../../README.md)

# What changed in rev 0.2

- **Re-routed from scratch** with a 0.16 mm routing target (JLCDFM rates >= 0.15 mm "good") on a
  0.127 mm DRC rule (what JLCPCB can make). JLCDFM-style warnings fell from ~300 to ~90.
- **Buck converter input loop:** C3 (100 nF) moved beside U1's VIN/PGND pins — the loop went
  from ~11 mm to 4 mm centre-to-centre (about 0.7 mm pad gap). This is the strongest emitter.
- **EMI:** a 2.5 mm GND ring on both outer layers stitched to the GND plane by 80 edge vias
  (largest gap 6.1 mm), an EMI layout check (`scripts/emi.py`) and a bench test procedure
  ([`docs/emi/emi_test.md`](../emi/emi_test.md)).
- **BOM cost:** $38.94 -> $25.81 per board in parts (10-board order), unique extended parts
  15 -> 11 (each costs a setup fee per order).
- **Sensors JLCPCB assembles normally:** U3 = TDK **ICM-45686** IMU, U4 = TE **MS5607** barometer.
  The previous DPS368 (and the IIM-42652 tried briefly) carry JLCPCB's "processing of this
  component is difficult" flag.
- **Placement verified against JLCPCB's own part footprints** — corrected placement file; it
  caught both LEDs, which would have been soldered backwards.
- 3 fiducials per side, board ID on the silkscreen, QR code re-placed and re-verified.
- J2-69 (one of the H7's four 3.3 V pins) is left open — no escape room next to the motor lines;
  the other three carry the 3.3 V load (about 130 mA; 0.9 A capacity).
