[← Back to the main README](../../README.md)

# Firmware note

No ArduPilot, PX4, Betaflight or INAV build exists for the Portenta H7 (checked 2026-11-15). ArduPilot
is the realistic target: the STM32H747 is an STM32H757 without the crypto block, and ArduPilot already
runs the H757 (CubePilot Cube Orange+). Estimate: 8-12 person-weeks to a flying prototype with logging.
What an ArduPilot hwdef for this board needs:
- **Clock:** 25 MHz oscillator in HSE-bypass mode, enabled by PH1 (drive PH1 high before clock init).
- **Supply mode:** "SMPS 1.8 V supplies LDO" (ArduPilot offers SMPS, bypass or LDO only: a small patch).
- **PMIC:** NXP PF1550 on I2C1 (PB6/PB7) at 0x08. Simplest is to keep Arduino's MCUboot bootloader
  (application at 0x08040000, `FLASH_RESERVE_START_KB 256`), which already sets up the PMIC.
- **USB:** the USB-C port is high-speed through a USB3320 ULPI PHY, which ArduPilot doesn't support
  yet; use the telemetry UART or add ULPI support.
- **Pins:** "SPI1" is the MCU's SPI2 (AF5); ESC telemetry is UART7 RX on PA8; UART1's RTS/CTS (PI14/PI15)
  are not USART1's hardware flow-control pins, so use ArduPilot's GPIO flow control; leave PC2/PC3's
  analog switches open (J2-74/76/77/79 unconnected) and don't wire SWO (PB3 is SD D2).
- **M4 core:** leave it halted.
Drivers: ICM-45686 (Invensense v3 family), MS5607 (MS56xx). Recovery: Arduino double-tap DFU over
USB-C, or the SWD pads.

A first ArduPilot board definition (`PortentaH7-FCCarrier`, compile-only) exists on a local ArduPilot branch, `portenta-h7-fc-carrier`; it is not in this repository yet.
