[← Back to the main README](../../README.md)

# BOM and cost

Parts only (fabrication and assembly labour not included), JLCPCB prices of 2026-11-14/15 (IMU and
barometer 2026-11-27), `scripts/bom_cost.py` -> `fab/bom_cost.csv`:

| Boards | Rev 0.1 | Rev 0.4 | Per board (rev 0.4) |
|---|---|---|---|
| 5 | $221.91 | $136.17 | $27.23 |
| 10 | $389.36 | $215.17 | $21.52 |
| 30 | $1019.93 | $527.26 | $17.58 |

Rev 0.4 swaps the barometer ($4.38 -> $1.87) and re-prices the ICM-45686 ($10.22 -> $7.02 at 10):
$27.21 -> $21.52 a board at 10 boards. Rev 0.3 had added the REF3125 ADC reference
($0.88 plus one more extended-part setup fee) and four capacitors over rev 0.2's $25.81.
`scripts/bom_cost.py` reads the current `fab/jlcpcb_bom.csv`.

| Part | Choice | Why |
|---|---|---|
| U1 buck, U2 LDO | TI LMR33630ADDAR, TI LP5907 | as before |
| U6 CAN | TI SN65HVD230DR | JLCPCB preferred part: no setup fee |
| U3 IMU | TDK ICM-45686 ($7.02 at 10) | kept in rev 0.4: every cheaper IMU at JLCPCB (ICM-42670-P $1.84, BMI270, ICM-42607, MPU-6500, IIM-42652) is flagged "processing of this component is difficult" (2026-11-27). The ICM-42670-P fits the same pads if that changes |
| U4 baro | Bosch BMP581 ($1.87) | 16k in stock, ArduPilot driver (`AP_Baro_BMP581`), lower noise than the MS5607 it replaced, 2 x 2 mm. JLCPCB rates **every** barometer it stocks "Assembly Difficulty: High" (BMP581, MS5607, MS5611, BMP388, BMP280, DPS368, ICP-20100, LPS22HH), so the BOM tool leaves U4 unticked: tick it to have it placed. The BMP581 is also flagged "processing difficult" (the MS5607 was not) |
| L1 | KOHER MDA5030-6R8M ($0.49) | MPS MPL-AL5050-6R8 also fits the pads ($1.78, 19 in stock) |
| Q1, D3, D5, R2/R3 | 2N7002, red / white LEDs, 51k / 12k | JLCPCB basic parts (no setup fee); 51k/12k gives 5.25 V |

Further savings if wanted: XYECONN clones of the JST GH/SH connectors (about $2 per board).
