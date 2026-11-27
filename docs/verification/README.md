[← Back to the main README](../../README.md)

# Must verify before ordering

1. ~~J1/J2 pin-1 orientation vs the H7.~~ **Verified 2026-11-14** against Arduino's own
   Portenta Breakout (ASX00031) Altium layout, which uses the same DF40HC(3.5)-80DS-0.4V(51)
   sockets. All 160 pads land in the same place (0.000 mm difference, measured from J1 towards
   J2, seen from the top), with the same 0.2 x 0.7 mm pads and 43.18 mm spacing. All 57 H7 pins
   this board uses carry the same signal on Arduino's board: +5V on J1-21/32/41/48, +3V3 on
   J2-23/34/43, the GND pins, the UARTs, I2C0, CAN1, the SD card, SWD/reset, SPI1, PWM0-9 and
   A0/A1. Re-check after any footprint change: `scripts/check_sockets.py`.
2. ~~Socket keep-out.~~ **Checked 2026-11-15** against Hirose drawing EDC-337747-51-01 (from hirose.com, not in the repo):
   - Pads match the recommended pattern: 0.2 x 0.7 mm at 0.4 mm pitch, 15.6 mm end to end,
     outer ends 3.78 mm apart and inner ends 2.38 mm apart.
   - Note 2's hatched area is each pad column extended inwards to 0.46 mm off the centre line
     (0.92 MAX). Only the same circuit may have copper there. J1 and J2 have no foreign copper
     there on F.Cu.
   - The `SOCKET_KEEPOUT` rule areas (2.2 x 18.6 mm, no F.Cu tracks, vias or pour) cover all of
     it, plus the 0.92 mm centre strip, so this is stricter than Hirose asks. The only F.Cu
     copper under a socket body is a CURR_SENSE track and a +5V pour edge at J2's short ends,
     beyond the last pad column and outside the hatched area.
   - `scripts/check_sockets.py` now checks this too. A track planted in the hatched area makes
     it fail.
3. **Sensor pinouts (rev 0.4).**
   - **ICM-45686** unchanged (checked against TDK's datasheet in rev 0.2).
   - **BMP581**, checked 2026-11-27 against Bosch BST-BMP581-DS004 rev 1.13 (pin table 28, land pattern
     fig. 32): 1 VDDIO, 2 SCK, 3 VSS, 4 SDI, 5 SDO, 6 CSB, 7 INT, 8/9 VSS, 10 VDD. CSB is tied high for I2C
     and SDO low, which gives address 0x46 ("SDO must not be floating"). INT goes to GND, which Bosch
     allows while the interrupt is disabled, and ArduPilot's driver never enables it.
     - The footprint (`fc:Bosch_LGA-10_2x2mm_P0.5mm_BMP581`) uses Bosch's rows 1.525 mm apart, pads
       25 µm larger than the package on the outer ends, and keeps the 0.2 mm gaps.
     - Pin 1 and the pad order match JLCPCB's footprint for C5362283, so its rotation correction is 0.
     - Bosch asks for no tracks or vias under the body: the `U4_KEEPOUT` rule area covers the middle,
       and every pad leaves outwards.
     - Bosch asks for no solder mask under the body: the footprint opens the mask there.
     - C14 (100 nF) sits on the VDD / VDDIO corner.
   - *Rev 0.3, now replaced:* ~~MS5607~~
   **checked 2026-11-14** against TE's MS5607-02BA03 datasheet (06/2017):
   - Pins match (1 VDD, 2 PS, 3 GND, 4/5 CSB, 6 SDO, 7 SDA, 8 SCLK), and pin 1 sits in the same
     corner as TE's top view.
   - PS is tied high, which selects I2C. CSB is tied high rather than left open (TE says never
     leave it open), which gives address 0x76. SDO is unused in I2C mode.
   - Our pads (0.95 x 0.55 mm at ±1.075 mm) cover the package's 0.9 x 0.5 mm pads, slightly
     smaller than TE's suggested 1.1 x 0.6 mm at ±1.1 mm.
   - Two fixes. U4 is rotated 180° so no track or via passes between its pads (TE: "reserved
     area, do not route tracks between pads"), held by a `U4_KEEPOUT` rule area. The 100 nF cap
     C14 moved next to VDD (about 1 mm pad gap, was 4 mm), as TE asks.
4. ~~V_SDCARD (J1-72)~~ **Checked 2026-11-15** against Arduino's Portenta Breakout schematic
   (ASX00031 rev 1.3, sheets 1, 2 and 5):
   - On the Breakout, the H7's VSD pin (J1-72) is the card's only supply: VSD, then R1 (0 Ω),
     then card VDD, with 100 nF (C2) at the card. So VSD is an SD-card supply the H7 puts out.
   - This board powers the card from +3V3 instead (the H7's VCC output, J2-23/34/43) and leaves
     VSD open. That is safe and works whether or not firmware turns VSD on. The card can't be
     power-cycled by software, which a drone logger doesn't need.
   - **Never fit R11.** It would tie the H7's VSD output straight to +3V3, putting two
     regulators in parallel. It is not a way to switch the card to VSD. (The earlier note that
     this matched Arduino's carriers was wrong.)
   - C21 (100 nF) and C22 (10 µF) sit about 15 mm from the card's VDD pin, at the far end of the
     socket. Arduino puts its 100 nF at the card, so **C23 (100 nF, added 2026-11-15)** now does
     the same. It is on the top side at (66.9, 21.1), 0.5 mm from the +3V3 via that drops
     straight to J11-4, about 3 mm of copper in all. Nothing can go beside the pin on the bottom,
     because the card slides in under the board there.
5. ~~microSD pads~~ **Checked 2026-11-14** against Molex drawing SD-104031-001 (recommended PCB
   layout, ±0.05 mm). Our footprint is Molex's layout turned 180°, which is fine.
   - **Signal pads:** sizes and positions match (7 × 0.85 and 1 × 0.75 mm, 1.1 mm pitch). Contact
     No.1 = T1 (DAT2) is the one 3.105 mm from the centre on the card-detect side. Nets match the
     microSD pin map: 1 D2, 2 D3, 3 CMD, 4 VDD, 5 CLK, 6 VSS, 7 D0, 8 D1.
   - **Card-detect pads 9/10 and shell pads G1–G4 (our pad 11):** sizes and offsets from Molex's
     product line all match. Card detect is unused: pad 9 is open and pad 10 is on GND, which is
     harmless.
   - **Slot:** it opens towards the right-hand board edge, about 3.3 mm in from the edge, under
     the board. The path is clear of parts, but the card is pushed with a fingernail.
6. ~~M3 nuts vs the H7 edge~~ **Checked 2026-11-15.** The four M3 holes (30.5 mm pattern) are
   2.55 mm outside the H7's long edges. The H7 covers x 0.98–67.02, y 7.30–32.70, and its
   underside is 3.5 mm above the carrier.
   - On both sides, the nearest part courtyard is at least 3.9 mm from each hole's centre. So
     M3 hex nuts, hex standoffs (5.5 mm across flats, 6.35 mm across corners) and rubber
     grommets up to about 7.5 mm across all sit flat.
   - **Top side:** hardware reaches up to 0.65 mm under the H7's edge, so everything on top,
     including the screw tip, must stay **under 3.5 mm tall**. A standard M3 nut (2.4 mm) or a
     thin one (1.8 mm) is fine. A standoff going up is not: it would hit the H7.
   - So the carrier is the top board of a stack: standoffs go below it only.
7. ~~Schematic ERC~~ **Checked 2026-11-15** with `scripts/erc.py`. KiCad 7's command line has no
   ERC, and the GUI would pop windows.
   - The generated schematic only has passive pins and labels on pin ends, so the ERC checks
     that can fire on it are checked directly: pins not connected, dangling labels or flags,
     single-pin nets, duplicate references, and symbols that differ from `fc.kicad_sym`.
   - The script also compares every pad's net, value, footprint and schematic link with the PCB.
   - **Result: 0 violations.** 75 symbols, 376 pins, 60 nets and 115 no-connect flags, and
     the schematic and PCB agree pad for pad. A planted fault (one missing no-connect flag and
     one renamed label) is caught.
   - The check found that U4 and C14 had lost their schematic link, which is now fixed, and
     `swap_fp.py` now keeps the link.
   - IC pins left open, reviewed by hand: U1 PG, U2 NC, U3 RESV and INT2, U4 SDO (I2C mode),
     U5 INT and DRDY (U5 not fitted), and U6 VREF. All are allowed open by their datasheets.
8. **Bottom-side rotations: confirm in JLCPCB's preview.** The CPL uses
   rotation = 180 − KiCad rotation + JLC footprint offset, viewed from the bottom.
   - The only report from someone who actually looked at JLCPCB's preview with a bottom part at
     90° (kicad-jlcpcb-tools issue #159) matches this rule. The opposite rule (KiCad − 180)
     comes from a 2025 report whose preview "looked messed up".
   - For every bottom part except **U6** (SOIC-8, offset 270) and **J11** (microSD, KiCad
     rotation 90), all the candidate rules give the same answer, so only those two can be wrong.
   - In the preview, described in top-view terms (left = battery-pad edge, right = microSD
     edge, "J5 edge" = y 0):
     - **U1, U2, U6:** pin 1 is at the corner nearest the left edge and away from the J5 edge.
     - **Q1:** gate (pin 1) on the left, drain alone towards the J5 edge.
     - **D1, D2, D4:** cathode band towards the left edge.
     - **J11:** card slot opening towards the right edge.
     - If U6 or J11 shows 180° off, add 180 to that line of `fab/jlcpcb_cpl.csv`.
9. ~~Power stage hand review~~ **Done 2026-11-15**, against TI's LMR33630 layout guidance.
   - **Schematic:** pinout, VCC 1 µF, BOOT 100 nF and the EN pull-up are right. FB 51k/12k
     gives 5.25 V, about 4.85 V after D2, inside the H7's 4.1–6 V.
   - **Input caps:** the 100 nF hot-loop cap C3 sits 1.9 mm from VIN/PGND. The 10 µF caps C1/C2
     are about 6 mm away through the inner layer, which is acceptable at 400 kHz.
   - **Fixed:**
     - U1's exposed pad had **no thermal vias**. It now has 4 GND vias, 0.2 mm drill, into the
       In1 ground plane. The top row would hit the inner-layer battery track.
     - Power tracks were 0.5 mm and are now widened wherever clearance allows, checked against
       the exact pad outlines (`scripts/power_copper.py`):
       - switch node 0.65 mm (limited by U1's exposed-pad corner; a GND via was moved 0.45 mm to
         make room)
       - buck output 0.81 mm average
       - +5V through D2 0.92 mm
       - battery feed 0.9 mm on the bottom and 0.8 mm on the inner main path. Inner tracks are
         capped at 0.8 mm, because wider ones leave slivers in the +5V plane.
       - The EN and battery-sense branches stay at 0.5 mm, since they carry almost no current.
   - **Rating: 5 V at 2 A continuous from 4–6S, about 1.5 A from 3S, 3 A peaks** (the README
     used to say 3 A).
     - D2 (SS34, SMA) drops about 0.45 V and dissipates about 0.9 W at 2 A.
     - The switch node (0.65 mm, 1 oz outer) carries about 2.4 A for a 20 °C rise.
     - The weakest link is the 0.8 mm inner battery track (half-ounce copper). At 2 A out it
       carries about 0.8 A from 6S but about 1.2 A from a flat 3S pack, so 3S is derated.
     - For more current, use a bigger Schottky or an ideal-diode controller, and 1 oz inner
       copper, in the next revision.
   - TVS D1 (SMBJ26A) clamps at up to 42 V at its full pulse current, above U1's 38 V absolute
     maximum. The input ceramics absorb the energy of normal spikes, and a lower TVS would
     conduct on a full 6S pack (25.2 V), so this is the usual trade-off. It is not fixed.
   - **Rip-up routes:** UART1 and M1–M4 are DRC-clean and fine at their speeds.
     - UART1 runs 58 mm on In2 (the +5V plane), which cuts slots in the bottom layer's
       reference plane.
     - The motor lines cross 4–5.5 mm of plane gaps each (11–14 % of their length), which is
       harmless at ESC/DShot speeds.
     - The real cost is the SD-card lines. SDC_CLK runs 20 mm over gaps. That is in the
       next-revision EMI list (move UART1 off In2, then re-route the SD bus over solid plane).

## Bring-up / production test

1. Unpowered: no short between VBAT, +5V, +3V3, +3V3_SENS and GND.
2. 12 V, 100 mA current limit on VBAT: +5V_BUCK about 5.25 V, +5V about 4.9 V (after the SS34),
   +3V3_SENS 3.3 V; note the idle current.
3. H7 fitted: SWD connects; I2C scan finds the BMP581 at 0x46 (CHIP_ID 0x50); IMU WHO_AM_I over SPI; microSD
   write/read; CAN loopback with a second node; UART loopbacks; PWM outputs on a scope;
   calibrate VBAT_SENSE; buzzer and both LEDs.
