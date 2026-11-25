[← Back to the main README](../../README.md)

# DFM (JLCDFM)

`scripts/dfm.py` repeats JLCDFM's measurements with its limits (it measures rounded pads as
rectangles and also checks gaps within one net, as JLCDFM does) -> `out/dfm.rpt`.

- **Danger: 0.** The last one, an SDC_D0 trace passing a corner of U2's +5V pad at 0.084 mm by the
  rectangle measure, was fixed on 2026-11-24 by moving the trace's jog away from the pad corner.
- Warnings: about 80 copper spacings between 0.10 and 0.15 mm (mostly tight escapes at the 0.4 mm-pitch
  sockets) and 61 vias with a 0.125 mm ring. Silkscreen: none.
