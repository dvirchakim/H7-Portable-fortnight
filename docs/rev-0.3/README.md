[← Back to the main README](../../README.md)

# What changed in rev 0.3 (design review, 2026-11-15)

A review by five parallel research/review tracks (hardware integration, firmware, circuit, market and
standards, layout/mechanics) before showing the board to Arduino. Fixed on the board:

- **ADC reference.** The module only pulls VREF+ (J2-71) up through ~100 kΩ / 100 nF and users measured
  it sagging from 3.1 V to ~2.6 V during conversions (battery/current readings up to ~19 % off). A TI
  **REF3125** 2.5 V series reference (U7, C24, C25) now drives J2-71; VREF- (J2-72) goes to GND. It works
  down to 2.55 V input (the module's 3V3 sits at 3.0 V on USB). For a Portenta C33 build leave U7/C25
  unfitted (J2-71 is an output there). Full scale: VBAT 27.5 V, current-sense 2.5 V.
- **ESC telemetry on its own UART.** J10-4 was wired to UART3_RX, which J7's device also drives. It now
  goes to PA8 = UART7_RX (J2-59), and M1 moved to PK1 (J2-60), still TIM1_CH1 beside M2 on TIM1_CH2.
  J7 keeps a full UART. (UART7 is the module's Bluetooth UART: keep Bluetooth off.)
- **LED strip that firmware can drive.** PH6 is TIM12, which has no DMA on the H7, so WS2812 LEDs could
  not work. The LED and S5 nets swapped (no copper moved): LED strip on PJ10 = TIM8_CH2 (DMA), S5 on
  PH6 = TIM12_CH1. S6 shares TIM8 with the LEDs (second LED string or GPIO while they run).
- **Sense inputs off the analog-only pads.** VBAT / current sense moved from PA0_C / PA1_C (no
  injection allowed, absolute max 4.0 V, unsupported by ArduPilot without a patch) to PA4 / PA6
  (J2-78 / J2-80). R10 went 1 k -> 10 k to limit current from an ESC output above 3.3 V.
- **Buck output capacitance.** 2 x 22 µF 0805 gave ~20 µF effective at 5.25 V; C26 / C27 bring it to
  4 x 22 µF as in TI's table for 5 V / 400 kHz. Values now say 25 V (the real part).
- **CAN terminator on by default** (the flight controller is a bus end): JP1 is a bridged solder jumper
  with a declared net tie; cut it to take the 120 Ω out.
- **Buzzer gate:** R13 10 k -> 100 k, so Q1 sees 3.27 V instead of 3.0 V.
- **Silkscreen:** forward arrows ("FWD", away from USB-C) beside the IMU on top and behind it on the
  bottom; a port map on the bottom behind each connector (the H7 hides most top labels); no
  "Portenta"/"Arduino" on the board (Arduino's trademark guide): board ID "FC CARRIER R0.3".
- **Checked and fine:** nothing under the H7 touches the module (tallest pair 0.9 + 1.0 mm in a 3.5 mm
  gap, from Arduino's STEP model); USB-C back-feeds the VIN pins through the module's Schottky, so +5V
  and the sensor rail are up on USB too (D2 blocks it from the buck); motors on TIM1/TIM3 do DShot and
  bidirectional DShot; J10 matches the Betaflight 8-pin ESC standard; GPS/TELEM/CAN/I2C match Pixhawk
  DS-009.

Deliberately left for rev 0.4 (need board space or a power-stage redesign): fuse + reverse-polarity
protection and a bulk input capacitor (the SMBJ26A clamp can exceed U1's 38 V); a higher-voltage buck
(8S); ESD arrays and a current-limited 5 V on the connectors; 10 V video regulator; second IMU / heater;
Pixhawk debug, POWER and 10-pin GPS ports; IMU caps closer to the supply pins; ideal diode instead of D2;
USB-FS pads (J1-26/28) for ROM DFU and ArduPilot without ULPI.
