# Flight-controller carrier for Arduino® Portenta H7

**A 68 × 40 mm, 4-layer carrier that snaps onto the Portenta H7's two high-density connectors and turns it
into an ArduPilot-class flight controller**, with Pixhawk-standard ports, microSD logging and DroneCAN.

<p align="center">
  <img src="docs/render_assembled.png" alt="The carrier with a Portenta H7 fitted" width="49%">
  <img src="docs/render_carrier.png" alt="The carrier on its own" width="49%">
</p>

**Revision R0.4 · fab-ready, not yet built.** DRC and ERC clean, 0 JLCDFM-style dangers, schematic and PCB
agree pad for pad, sockets match Arduino's own Portenta Breakout to 0.000 mm.

## Highlights

- **Power:** 3–6S LiPo in, TI LMR33630 buck, 5.25 V at 2 A continuous (1.5 A from 3S), 3 A peaks.
- **Sensors:** TDK ICM-45686 IMU at the board centre, Bosch BMP581 barometer shielded under the module.
- **Logging and buses:** 4-bit microSD, DroneCAN (terminated by default), I2C.
- **Ports:** GPS, TELEM (with flow control), RC, UART, CAN and I2C on JST-GH with Pixhawk DS-009
  pinouts; 4-in-1 ESC on JST-SH 8 in the Betaflight standard order.
- **Motors:** DShot and bidirectional DShot on all four; ESC telemetry on its own UART.
- **Measurement:** battery voltage and ESC current into an ADC with its own 2.5 V reference.
- **Mounting:** 30.5 mm M3 stack pattern; the module is held by its own four M2 holes.
- **Built from code:** everything is generated from one Python netlist (`scripts/design.py`) and
  checked by scripts: DRC, ERC, DFM, EMI, socket match, JLCPCB placement.

## Specifications

| | |
|---|---|
| Board | 68 × 40 mm, 4 layers (GND and 5 V planes), 1.6 mm, black mask / white silk, ENIG |
| Module | Portenta H7 / H7 Lite (STM32H747, M7 480 MHz + M4) on two Hirose DF40HC(3.5), 3.5 mm stack |
| Input | 3–6S LiPo through solder pads or the ESC harness; SMBJ26A TVS |
| Outputs | M1–M4 (DShot), S5, S6, WS2812 LED strip, buzzer |
| Parts | 63 placed parts, 32 BOM lines; about $22 per board in parts at 10 boards (module not included) |
| Assembly | JLCPCB, both sides; the DF40 sockets are consigned |

## Architecture

| Block | Parts | H7 signals |
|---|---|---|
| Power | 3-6S VBAT -> TVS -> LMR33630 buck 5.25 V (2 A continuous from 4-6S, ~1.5 A from 3S, 3 A peaks) -> SS34 -> +5V -> H7 VIN | J1-21/32/41/48 |
| Sensor rail | LP5907 3.3 V low-noise LDO from +5V | — |
| IMU | TDK ICM-45686, SPI | SPI1 CK/CIPO/COPI (PI1/PC2/PC3), CS PI0, INT GPIO2 (PD4) |
| Barometer | Bosch BMP581 (I2C, address 0x46) | I2C0 (PH8/PH7 = I2C3) |
| Magnetometer | LIS3MDL footprint, not fitted — use the GPS module's compass | I2C0 |
| Motors M1-M4 | 8-pin JST-SH 4-in-1 ESC connector (Betaflight standard order) | M1 PWM5 PK1 TIM1_CH1, M2 PWM4 PJ11 TIM1_CH2, M3 PWM1 PC6 TIM3_CH1, M4 PWM2 PC7 TIM3_CH2: no complementary channels, DMA on both timers, so DShot and bidirectional DShot work on all four |
| Aux S5, S6, LED strip | pads | LED strip PWM8 PJ10 = TIM8_CH2 (has DMA, so WS2812 works); S6 PWM6 PH15 = TIM8_CH3N (shares TIM8 with the LEDs: second LED string or GPIO while they run); S5 PWM9 PH6 = TIM12_CH1 (servo PWM) |
| Buzzer | 2N7002 low-side switch (R13 100k), pad | PWM7 PJ7 as a GPIO: active buzzer |
| Status / power LEDs | red (GPIO3) / white (+5V) | GPIO3 PD5 |
| Battery sense | VBAT 11:1 divider -> A6; ESC current (10k + 100 nF) -> A7; ADC VREF+ = 2.5 V from a TI REF3125 (U7) | A6 PA4 J2-78, A7 PA6 J2-80, VREF+ J2-71 (VREF- J2-72 to GND) |
| GPS + compass | JST-GH 6 (5V TX RX SCL SDA GND) | UART0 + I2C0 |
| Telemetry | JST-GH 6 with RTS/CTS | UART1 (USART1) |
| RC receiver | JST-GH 4 | UART2 (USART6) |
| Spare UART | JST-GH 4 | UART3 (UART8) |
| ESC telemetry | J10 pin 4 | PA8 = UART7_RX (J2-59), its own UART (the module's Bluetooth UART: keep Bluetooth off) |
| CAN | SN65HVD230 + JST-GH 4; 120 ohm terminator ON by default (bridged JP1: cut to remove) | CAN1 TX/RX (PH13/PB8) = FDCAN1 |
| I2C expansion | JST-GH 4 | I2C0 |
| microSD | Molex 104031-0811 | SDC (SDMMC2) |
| Debug | SWDIO/SWCLK/NRST/GND/3V3 pads (bottom) | J1-75/77/73 |

The +5V rail sits after the Schottky, on the same node as the H7's VIN, so the sensors and ports
run from USB on the bench and USB cannot back-feed the buck.

## Snap-on interface

- Carrier sockets J1/J2: **Hirose DF40HC(3.5)-80DS-0.4V(51)**, mating the H7's DF40C-80DP-0.4V(51).
  Board-to-board gap 3.5 mm.
- J1/J2 are 43.18 mm apart on the H7 centreline (17.14 mm and 60.32 mm from the USB edge).
- Pin 1, seen from the top with USB on the left: J1 pin 1 is in the USB-side row at the lower end;
  J2 pin 1 is in the outer row at the upper end. Same as Arduino's Portenta Breakout
  (`scripts/check_sockets.py`).
- Four M2 holes line up with the H7's corner holes — use 3.5 mm spacers so vibration is not
  carried by the connectors. At the J2 end use round spacers of 3 mm diameter or less.
- Four M3 holes on the standard 30.5 x 30.5 mm stack pattern.
- Under the H7 the top side carries only low parts (LGA sensors, 0402). Everything tall (buck,
  inductor, microSD, CAN transceiver) is on the bottom.

## Documentation

| Topic | What's there |
|---|---|
| [Rev 0.4 changes](docs/rev-0.4/README.md) | Sensor cost pass: BMP581 barometer; IMU options checked |
| [Rev 0.3 changes](docs/rev-0.3/README.md) | The design review: what was found and fixed, what's left for rev 0.4 |
| [Rev 0.2 changes](docs/rev-0.2/README.md) | Re-route, buck loop, EMI ring, cost pass, sensor swap |
| [Verification](docs/verification/README.md) | The "must verify before ordering" checks with results, and the bring-up / production test |
| [Ordering](docs/ordering/README.md) | What to upload to JLCPCB, stackup, consigning the DF40 sockets |
| [BOM and cost](docs/bom-and-cost/README.md) | Cost per board and why each main part was chosen |
| [Placement check](docs/placement-check/README.md) | JLCPCB footprint corrections and what they caught |
| [DFM](docs/dfm/README.md) | JLCDFM-style manufacturability results |
| [EMI](docs/emi/README.md) | Layout checks and the bench test procedure |
| [Routing](docs/routing/README.md) | Layer stack and the routing flow |
| [Silkscreen](docs/silkscreen/README.md) | Labels, forward arrows, QR code |
| [Firmware](docs/firmware/README.md) | The ArduPilot port: what the board definition needs |
| [Design review page](docs/FC_Carrier_R0.3_review.html) | The rev 0.3 review written for an Arduino Pro pitch |

## Repository layout

| File | What |
|---|---|
| `portenta_drone_fc.kicad_pro` | Open this in KiCad 7 |
| `portenta_drone_fc.kicad_sch` | Schematic (net-label style, one sheet) |
| `portenta_drone_fc.kicad_pcb` | Routed 4-layer board |
| `fc.pretty/`, `fc.kicad_sym` | Project footprint (DF40 socket) and symbols |
| `bom_placement.csv` | Parts, MPNs, side and XY (from `design.py`) |
| `fab/` | Gerber zip, JLCPCB BOM and CPL, `bom_cost.csv`, `placement_check.csv` |
| `out/` | Renders, `drc.rpt`, `dfm.rpt`, `emi.rpt` |
| `docs/` | One folder per topic (see Documentation above), the 3D renders, `portenta_breakout_sockets.json` (Arduino's socket pads) and `FC_Carrier_R0.3_review.html` (the rev 0.3 design review for the Arduino pitch) |
| `scripts/design.py` | **Single source of truth** — parts, nets, placement |
| `scripts/regen_docs.py` | Rewrites schematic + BOM CSV from `design.py` without touching the routed board |
| `scripts/check_sockets.py` | Compares J1/J2 pad by pad with Arduino's Portenta Breakout and Hirose's land pattern / hatched area (exit 0 = match) |
| `scripts/erc.py` | ERC for the generated schematic plus schematic-vs-PCB parity, pad by pad (exit 0 = clean) |
| `scripts/power_copper.py` | Thermal vias in U1's exposed pad and power tracks widened as far as clearance allows |
| `scripts/render3d/` | Headless 3D renders of the board (STEP export -> blocks, layer textures, Blender) |
| `scripts/r03_renet.py`, `scripts/r03_rip.py` | The rev 0.3 review changes as applied to the routed board: net swaps, pad re-assignments, new footprints, then removal of the obsolete copper (run once; kept as the record) |
| `scripts/altium_pads.py` | Reads pads/nets from an Altium `.PcbDoc` with plain Python (made the reference JSON) |

`scripts/gen.py --force` would regenerate the board and discard the routing — do not use it now.

---

Arduino® and Portenta are trademarks of Arduino S.r.l. / Arduino SA. This is an independent design, not an
Arduino product.
