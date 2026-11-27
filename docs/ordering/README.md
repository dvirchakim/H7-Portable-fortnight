[← Back to the main README](../../README.md)

# Ordering from JLCPCB

| Upload | File |
|---|---|
| Gerbers + drill | `fab/portenta_drone_fc_gerbers.zip` |
| BOM | `fab/jlcpcb_bom.csv` |
| Placement (CPL) | `fab/jlcpcb_cpl.csv` |

**PCB:** 4 layers, 68 x 40 mm, 1.6 mm, 1 oz outer / 0.5 oz inner, default stackup
(JLC04161H-7628). **Dark solder mask with white silkscreen** (the QR code prints its light
squares). ENIG recommended for the 0.4 mm-pitch sockets and LGA sensors (HASL lead-free works).
Smallest features: 0.127 mm track/space, 0.45–0.50 mm vias with 0.2 mm drill.

**Assembly:** Standard PCBA, both sides.
- **U4 (BMP581 barometer) shows unticked in JLCPCB's BOM tool. Tick it.** JLCPCB rates every
  barometer it stocks "Assembly Difficulty: High" and leaves those lines unticked by default; the
  part is in stock (16k, 2026-11-27). The BMP581 is also flagged "processing difficult" and is a
  Standard-PCBA-only part, which this order is anyway.
- **J1/J2 sockets (C3641790) have no JLCPCB stock: consign them.** JLCPCB's global-sourcing quote
  (2026-11-16) was $0.71 each but **145 business days** lead time (factory order), which would push
  prototypes to mid-2027. Mouser and Digi-Key list the same DF40HC(3.5)-80DS-0.4V(51) in stock at
  about $2.51 each (search snapshots of 2026-11-24, thousands of pieces; confirm on their pages):
  buy 2 per board plus 2 spares and ship them to JLCPCB through Parts Manager -> Consign parts.
  Nothing in JLCPCB's own stock substitutes (DF40C-80DS mates at 1.5 mm, too low). For production
  volumes, the $0.71 factory route works if ordered about 7 months ahead.
- R11, U5 and C15 (U5's capacitor) are deliberately not fitted. The list lives in `scripts/design.py` (`DNP`). Test pads, the CAN jumper JP1, fiducials and holes are
  not parts. The Portenta H7 itself is not in the order.
- In JLCPCB's placement preview, check the bottom-side polarised parts against [verification item 8](../verification/README.md), especially **U6 and J11**. Those two are the only parts where the bottom-rotation
  conventions disagree.
