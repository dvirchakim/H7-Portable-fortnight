[← Back to the main README](../../README.md)

# What changed in rev 0.4 (sensor cost pass, 2026-11-27)

| | Rev 0.3 | Rev 0.4 |
|---|---|---|
| U3 IMU | TDK ICM-45686 (C22459454) | unchanged ($7.02 at 10 boards) |
| U4 barometer | TE MS5607-02BA03 (C97627), $3.73 | **Bosch BMP581** (C5362283), $1.87: new 2 x 2 mm LGA-10 footprint, re-routed |

Parts per board at 10 boards: **$27.21 -> $21.52**.

**IMU.**
- Every IMU under $7 at JLCPCB is flagged "processing of this component is difficult" (componentProductType 2,
  checked 2026-11-27): ICM-42670-P ($1.84), BMI270, ICM-42607, MPU-6500, IIM-42652, LSM6DSV.
- The genuine ICM-42688-P is $25 with 11 in stock; the cheap "ICM-42688-P" listings are HXY / TOKMAS copies.
- So the ICM-45686 stays. The ICM-42670-P (same pads, same pin per pad, same ArduPilot driver) is the drop-in
  if the flag ever goes.

**Barometer.**
- JLCPCB rates every barometer it stocks "Assembly Difficulty: High", the MS5607 included, so U4 shows
  unticked whatever the part: tick it in the BOM tool.
- Rated High: BMP581, BMP585, BMP388, BMP280, MS5607, MS5611, DPS368, ICP-20100, LPS22HH.
- The BMP581 is also flagged "processing difficult".
- Why the BMP581: half the price, lower noise, an ArduPilot driver (`AP_Baro_BMP581`).
- Wiring: I2C, CSB high, SDO low = address **0x46**, INT to GND.
- Layout: Bosch land pattern, no tracks, vias or mask under the body (see
  [verification item 3](../verification/README.md)).
- The copper is recorded in `scripts/r04_baro_copper.py`.

**Checks:**
- DRC: 0 unconnected, same 1 sliver and 2 by-design courtyard overlaps.
- ERC clean, schematic and PCB agree.
- DFM: 0 dangers.
- Sockets PASS.
- JLC placement self-check: 0.000 mm.
- Board ID: "FC CARRIER R0.4".

**Firmware:** `BARO MS5607 I2C:0:0x76` becomes `BARO BMP581 I2C:0:0x46`.
