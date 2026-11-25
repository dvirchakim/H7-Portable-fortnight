[← Back to the main README](../../README.md)

# Placement check against JLCPCB's footprints

JLCPCB places every part with its own (EasyEDA) footprint. For each LCSC part, that footprint was
fetched and fitted to ours by pad position (`scripts/jlc_corrections.json`), and
`scripts/jlc_place.py` writes the placement file from the board with those corrections (it first
checks that its geometry reproduces KiCad's pad positions exactly — error 0.0000 mm). Findings:

- JLCPCB's LED footprints number the **anode** as pad 1 (KiCad: cathode) — matched cathode to
  cathode, so the LEDs are not reversed.
- JST GH/SH connector origins differ by 0.06–0.25 mm; the microSD socket and SOT-23 parts are
  drawn rotated 180 degrees, SOIC-8 270 degrees, the DF40 sockets 90 degrees.
- JLCPCB's DF40 footprint numbers its pads in mirror order to ours. That does not matter: the
  socket is symmetric and each contact simply joins the pad under it to the H7 pin above it.
