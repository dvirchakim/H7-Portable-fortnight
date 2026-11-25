# EMI testing — Portenta H7 drone FC

Two stages, the way product houses do it: **design-time checks** (free, every revision) and **bench
pre-compliance** (cheap gear, before paying a lab). Formal certification (FCC Part 15B / CE
EN 55032 + EN 55035) is only worth booking once pre-compliance is clean.

## 1. Design-time checks (run on every board revision)

`scripts/emi.py` measures, from the KiCad board, the layout faults behind most emissions:

| Check | Why it matters | Target |
|---|---|---|
| Fast signals over a plane void | return current detours round the gap → loop antenna | < 2 mm per net |
| Signal copper on In1 (GND plane) | every track there is a slot in the main reference | 0 mm |
| Fast-signal vias far from a bypass cap | when a signal changes from the GND-referenced to the +5V-referenced layer, its return crosses through the nearest decoupling cap | < 5 mm |
| Fast signals near the board edge | edge fringing fields radiate | > 1 mm |
| GND stitching round the edge | the GND ring + via fence stops the planes radiating at the edge | gap ≤ 5 mm (λ/20 at 3 GHz) |
| Buck input loop (cap ↔ U1 VIN/PGND) | the 400 kHz switching loop with ns edges is the strongest emitter | < 4 mm |
| Buck switch-node copper | the SW node is a near-field antenna | < 25 mm² |

`scripts/emi_fix.py` adds the GND ring and edge via fence. Results are in `out/emi.rpt`.

## 2. Bench pre-compliance

### Kit (about $150–$300)

- **Spectrum analyser:** a tinySA Ultra (100 kHz–5.3 GHz) is enough for comparisons; a Siglent
  SSA3021X or Rigol DSA815 adds proper RBW filters and a quasi-peak detector.
- **H-field near-field probes:** a 3–4 loop set (e.g. Tekbox TBPS01 or a DIY coax loop).
- **LISN** for conducted emissions on the battery lead (Tekbox TBLC08, or a DIY 5 µH LISN).
- A battery or linear bench supply. A switch-mode bench supply adds its own noise.
- **Optional:** a 20 dB preamp for the probes; a GPS module with u-center / u-blox status
  output for the C/N0 test.

### Procedure

1. **Ambient:** analyser on, board off. Save the trace — every later trace is compared with it.
2. **Conducted, 150 kHz–30 MHz:** battery → LISN → VBAT input, board idle, then motors spinning
   (props off). Look at the buck's 400 kHz fundamental and harmonics. Compare against CISPR 32
   class B (or CISPR 25 if the drone is a vehicle product) with the analyser's LISN correction.
3. **Near-field sweep, 30 MHz–1 GHz:** move the small loop slowly over these areas, noting
   peaks:
   - U1/L1/C3 (buck)
   - the microSD socket and its lines (SDMMC clock 25–50 MHz and its harmonics)
   - the DF40 sockets
   - every cable exit: GPS, telemetry, RC, ESC, CAN
4. **Cables:** cables are the real antennas. Clip a current probe (or a ferrite + loop) round each
   attached cable while the near-field probe shows the source.
5. **Fix, then re-measure the same spot with the same probe height** (relative dB counts, not
   absolute). Typical fixes:
   - 22–47 Ω series resistors on SDMMC clock and DShot lines
   - a ferrite bead and 100 nF on the GPS 5 V feed
   - shorter or twisted motor leads
   - a shield can over the buck
6. **Drone-specific — GPS desense test:** this is the emission that actually matters in flight.
   - With the GPS on its mast and the board off, note the average C/N0 of the strongest satellites.
   - Power the board, log to the SD card and spin the motors.
   - A drop of more than 2–3 dB-Hz means the board is radiating in the GPS L1 band (1575.42 MHz).
   - Find the source with the near-field probe at 1.5–1.6 GHz.

### Record

Save each trace (CSV/PNG) with board revision, firmware and configuration. A before/after
pair per fix is the evidence a test lab (or a customer) will want.
