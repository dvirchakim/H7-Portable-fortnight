[← Back to the main README](../../README.md)

# EMI

`scripts/emi.py` (layout review) and [`emi_test.md`](emi_test.md) (how to measure: near-field probes,
LISN, GPS C/N0 desense test). Current layout results (`out/emi.rpt`):

| Check | Result |
|---|---|
| Signal copper on the GND plane (In1) | 0 mm — OK |
| Fast signals within 1 mm of the edge | none — OK |
| GND stitching gap round the edge | 6.1 mm — OK |
| Buck switch-node copper | 19.0 mm² — OK |
| Buck input loop (centre-to-centre) | 4.0 mm (was 11) — at the limit |
| Fast-signal vias > 5 mm from a bypass cap | 22 of 35 — review |
| Fast-signal length over plane voids | up to 21.5 mm (In2 is cut by signals) — review |

Next-revision EMI items: add two or three 100 nF GND-to-+5V capacitors near the J1 SD/CAN escape
and the J2 motor escape; 22–33 ohm series resistors on the SDMMC clock and the DShot lines; keep
In2 free of signals (6 layers would allow it).
