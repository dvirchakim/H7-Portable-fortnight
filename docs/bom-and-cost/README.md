[← Back to the main README](../../README.md)

# BOM and cost

Parts only (fabrication and assembly labour not included), JLCPCB prices of 2026-11-14/15,
`scripts/bom_cost.py` -> `fab/bom_cost.csv`:

| Boards | Rev 0.1 | Rev 0.3 | Per board (rev 0.3) |
|---|---|---|---|
| 5 | $221.91 | $157.31 | $31.46 |
| 10 | $389.36 | $272.11 | $27.21 |
| 30 | $1019.93 | $725.56 | $24.19 |

Rev 0.3 adds the REF3125 ADC reference ($0.88 plus one more extended-part setup fee) and four
capacitors over rev 0.2's $25.81. `scripts/bom_cost.py` now reads the current `fab/jlcpcb_bom.csv`.

| Part | Choice | Why |
|---|---|---|
| U1 buck, U2 LDO | TI LMR33630ADDAR, TI LP5907 | as before |
| U6 CAN | TI SN65HVD230DR | JLCPCB preferred part: no setup fee |
| U3 IMU | TDK ICM-45686 ($10.22) | pin-compatible with the ICM-42688-P (now $21.63, 7 in stock); 6.4 kHz ODR; not flagged |
| U4 baro | TE MS5607-02BA03 ($4.38) | the Pixhawk-family barometer; not flagged; MS5611 is a drop-in upgrade |
| L1 | KOHER MDA5030-6R8M ($0.49) | MPS MPL-AL5050-6R8 also fits the pads ($1.78, 19 in stock) |
| Q1, D3, D5, R2/R3 | 2N7002, red / white LEDs, 51k / 12k | JLCPCB basic parts (no setup fee); 51k/12k gives 5.25 V |

Further savings if wanted: XYECONN clones of the JST GH/SH connectors (about $2 per board), or
the TDK ICM-42670-P IMU ($2.15, but limited to 1.6 kHz output, flagged "difficult").
