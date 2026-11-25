[← Back to the main README](../../README.md)

# Lessons taken from IMD Technologies, Grinn and Virtium

What their public material stresses, and what this board does about it:

| Practice | Here |
|---|---|
| Design for test, production tests (Grinn) | labelled test pads on every rail, SWD and NRST; fiducials; bring-up test list below; full checks in [verification](../verification/README.md) |
| EMC pre-compliance before certification (Grinn) | `scripts/emi.py` each revision, [`docs/emi/emi_test.md`](../emi/emi_test.md) bench procedure |
| Signal/power integrity (Grinn) | GND ring + via fence, short buck loop, solid GND plane under the top layer |
| Industrial temperature, lifecycle discipline (Virtium) | every IC is rated -40 to +85 °C or wider; the board is limited to **-25 to +85 °C** by the JST GH/SH and microSD connectors (DF40 -35 to +85); all parts active, mainstream sources |
| Power-loss resilience (Virtium) | battery voltage on A0 so firmware can close the SD log before a brown-out |
| Cost-effective carrier + module, assembly options (IMDT) | jellybeans on basic parts, brand parts where they matter; U5 (with its C15) is a do-not-fit option (R11 is not fitted and must stay so, see [verification item 4](../verification/README.md)) |

Not done yet, worth doing before flying hardware: conformal coating, staking L1 and the microSD
socket against vibration, reverse-battery protection (there is only a TVS today), and ESD diodes
on the external connectors.

**Bring-up / production test**

1. Unpowered: no short between VBAT, +5V, +3V3, +3V3_SENS and GND.
2. 12 V, 100 mA current limit on VBAT: +5V_BUCK about 5.25 V, +5V about 4.9 V (after the SS34),
   +3V3_SENS 3.3 V; note the idle current.
3. H7 fitted: SWD connects; I2C scan finds the MS5607 at 0x76; IMU WHO_AM_I over SPI; microSD
   write/read; CAN loopback with a second node; UART loopbacks; PWM outputs on a scope;
   calibrate VBAT_SENSE; buzzer and both LEDs.
