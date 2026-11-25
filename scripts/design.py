"""Single source of truth for the Portenta H7 drone carrier: parts, nets, placement.

Everything (schematic, PCB, pin-map doc) is generated from this file by gen.py.
Board coordinates are mm, origin top-left of the carrier, viewed from the TOP,
with the Portenta's USB-C connector at the left (x = 0) end.
"""

BOARD_W, BOARD_H = 68.0, 40.0
H7_W, H7_H = 66.04, 25.40
H7_X0, H7_Y0 = (BOARD_W - H7_W) / 2, (BOARD_H - H7_H) / 2   # H7 outline origin on carrier

# From the Arduino datasheet (ABX00042, section 7.3, bottom view):
# J1 centre 17.14 mm and J2 centre 60.32 mm from the USB edge, both on the board centreline.
J1_POS = (H7_X0 + 17.14, BOARD_H / 2)
J2_POS = (H7_X0 + 60.32, BOARD_H / 2)

# ---------------------------------------------------------------- H7 connector signal names
J1_NAMES = {
    1: 'ETH_A_P', 3: 'ETH_A_N', 5: 'ETH_B_P', 7: 'ETH_B_N', 17: 'ETH_L1', 19: 'ETH_L2',
    21: 'VIN', 23: 'USB1_VBUS', 25: 'USB1_D_P', 27: 'USB1_D_N', 29: 'USB1_ID', 31: 'GND',
    33: 'UART1_TX/PA9', 35: 'UART1_RX/PA10', 37: 'UART1_RTS/PI14', 39: 'UART1_CTS/PI15',
    41: 'VIN', 43: 'I2C1_SDA/PB7', 45: 'I2C1_SCL/PB6', 47: 'GND', 49: 'CAN1_TX/PH13',
    51: 'CAN1_RX/PB8', 53: 'VSYS', 55: 'SDC_CLK/PD6', 57: 'SDC_CMD/PD7', 59: 'SDC_D0/PB14',
    61: 'SDC_D1/PB15', 63: 'SDC_D2/PB3', 65: 'SDC_D3/PB4', 73: 'RESET', 75: 'SWDIO/PA13',
    77: 'SWCK/PA14', 79: 'SWO/PB3',
    10: 'DSI_D1_P', 12: 'DSI_D1_N', 14: 'DSI_D0_P', 16: 'DSI_D0_N', 18: 'DSI_CK_P',
    20: 'DSI_CK_N', 22: 'GND', 26: 'USB0_D_P/PA12', 28: 'USB0_D_N/PA11', 32: 'VIN',
    34: 'UART0_TX/PA0', 36: 'UART0_RX/PI9', 38: 'UART0_RTS/PI10', 40: 'UART0_CTS/PI13',
    42: 'GND', 44: 'I2C0_SDA/PH8', 46: 'I2C0_SCL/PH7', 48: 'VIN', 54: 'GND',
    56: 'I2S_MCK/PD3', 58: 'I2S_WS/PB9', 60: 'I2S_DI/PI2', 62: 'I2S_DO/PI3', 64: 'VSYS',
    66: 'DMIC_CK/PE2', 68: 'DMIC_D0/PB2', 72: 'V_SDCARD',
}
J2_NAMES = {
    1: 'FORCE_BOOTLOADER', 3: 'BOOT_SOURCE/PI8', 5: 'POWER_ON_REQ', 7: 'COINCELL',
    23: '+3V3', 25: 'UART3_TX/PJ8', 27: 'UART3_RX/PJ9', 33: 'GND', 43: '+3V3',
    45: 'I2C2_SDA/PH12', 47: 'I2C2_SCL/PH11', 49: 'SAI_CK/PI5', 51: 'SAI_FS/PI7',
    53: 'SAI_D0/PI6', 57: 'GND', 59: 'PWM0/PA8', 61: 'PWM1/PC6', 63: 'PWM2/PC7',
    65: 'PWM3/PG7', 67: 'PWM4/PJ11', 69: '+3V3', 71: 'ADC_VREF_P', 73: 'A0/PA0_C',
    75: 'A1/PA1_C', 77: 'A2/PC2_C', 79: 'A3/PC3_C',
    2: 'CAM_D7/PI7', 4: 'CAM_D6/PI6', 6: 'CAM_D5/PI4', 8: 'CAM_D4/PH14', 10: 'CAM_D3/PH12',
    12: 'CAM_D2/PH11', 14: 'CAM_D1/PH10', 16: 'CAM_D0/PH9', 18: 'CAM_VS/PI5',
    20: 'CAM_CLK/PA6', 22: 'CAM_HS/PA4', 24: 'GND', 26: 'UART2_TX/PG14', 28: 'UART2_RX/PG9',
    34: '+3V3', 36: 'SPI1_CS/PI0', 38: 'SPI1_CK/PI1', 40: 'SPI1_CIPO/PC2',
    42: 'SPI1_COPI/PC3', 44: 'GND', 46: 'GPIO0/PC13', 48: 'GPIO1/PC15', 50: 'GPIO2/PD4',
    52: 'GPIO3/PD5', 54: 'GPIO4/PE3', 56: 'GPIO5/PG3', 58: 'GPIO6/PG10', 60: 'PWM5/PK1',
    62: 'PWM6/PH15', 64: 'PWM7/PJ7', 66: 'PWM8/PJ10', 68: 'PWM9/PH6', 70: 'GND',
    72: 'ADC_VREF_N', 74: 'A4/PC2', 76: 'A5/PC3', 78: 'A6/PA4', 80: 'A7/PA6',
}

# ---------------------------------------------------------------- H7 connector net use
J1_NETS = {
    21: '+5V', 32: '+5V', 41: '+5V', 48: '+5V',
    22: 'GND', 31: 'GND', 42: 'GND', 47: 'GND', 54: 'GND',
    33: 'UART1_TX', 35: 'UART1_RX', 37: 'UART1_RTS', 39: 'UART1_CTS',
    34: 'UART0_TX', 36: 'UART0_RX', 44: 'I2C0_SDA', 46: 'I2C0_SCL',
    49: 'CAN1_TX', 51: 'CAN1_RX',
    55: 'SDC_CLK', 57: 'SDC_CMD', 59: 'SDC_D0', 61: 'SDC_D1', 63: 'SDC_D2', 65: 'SDC_D3',
    72: 'V_SDCARD', 73: 'NRST', 75: 'SWDIO', 77: 'SWCLK',
}
J2_NETS = {
    23: '+3V3', 34: '+3V3', 43: '+3V3',          # J2-69 (4th 3V3 pin) left open: no escape room; 3 pins carry 0.9 A
    24: 'GND', 33: 'GND', 44: 'GND', 57: 'GND', 70: 'GND',
    72: 'GND',                                       # ADC VREF- to ground
    25: 'UART3_TX', 27: 'UART3_RX', 26: 'UART2_TX', 28: 'UART2_RX',
    36: 'IMU_CS', 38: 'SPI1_SCK', 40: 'SPI1_CIPO', 42: 'SPI1_COPI',   # the MCU's SPI2 (AF5)
    50: 'IMU_INT', 52: 'LED_STATUS',
    # Motors: M1 PK1 = TIM1_CH1, M2 PJ11 = TIM1_CH2, M3 PC6 = TIM3_CH1, M4 PC7 = TIM3_CH2 - no complementary
    # channels, DMA on both timers: DShot and bidirectional DShot on all four.
    60: 'M1', 67: 'M2', 61: 'M3', 63: 'M4',
    59: 'ESC_TLM',                                   # PA8 = UART7_RX (AF11): ESC telemetry on its own UART
    # LED strip on PJ10 = TIM8_CH2 (has DMA, so WS2812 works; TIM12 has none on the H7). S6 PH15 = TIM8_CH3N
    # shares TIM8 with it (second LED string or GPIO when the LEDs run). S5 PH6 = TIM12_CH1 (servo PWM).
    # Buzzer PJ7 = GPIO for an active buzzer (its TIM8_CH2N is the LED channel's complement).
    66: 'LED_STRIP', 68: 'S5', 62: 'S6', 64: 'BUZZER',
    71: 'ADC_VREF',                                  # VREF+ from U7 (module only pulls it up weakly, 100k)
    78: 'VBAT_SENSE', 80: 'CURR_SENSE',              # PA4 / PA6: plain ADC pins, not the analog-only PA0_C / PA1_C
}

R0402 = 'Resistor_SMD:R_0402_1005Metric'
C0402 = 'Capacitor_SMD:C_0402_1005Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
C1206 = 'Capacitor_SMD:C_1206_3216Metric'
GH4 = 'Connector_JST:JST_GH_SM04B-GHS-TB_1x04-1MP_P1.25mm_Horizontal'
GH6 = 'Connector_JST:JST_GH_SM06B-GHS-TB_1x06-1MP_P1.25mm_Horizontal'
SH8 = 'Connector_JST:JST_SH_SM08B-SRSS-TB_1x08-1MP_P1.00mm_Horizontal'
TP15 = 'TestPoint:TestPoint_Pad_1.5x1.5mm'
TPD15 = 'TestPoint:TestPoint_Pad_D1.5mm'
TP30 = 'TestPoint:TestPoint_Pad_3.0x3.0mm'

PARTS = []   # dicts: ref, sym, value, fp, pins[(num, name)], nets{num: net}, side, x, y, rot, block


def part(block, ref, sym, value, fp, pins, nets, side, x, y, rot=0, mpn=''):
    PARTS.append(dict(block=block, ref=ref, sym=sym, value=value, fp=fp, pins=pins,
                      nets={str(k): v for k, v in nets.items()}, side=side, x=x, y=y,
                      rot=rot, mpn=mpn))


def two(block, ref, sym, value, fp, n1, n2, side, x, y, rot=0, mpn=''):
    names = {'D': ('K', 'A'), 'LED': ('K', 'A')}.get(sym, ('1', '2'))
    part(block, ref, sym, value, fp, [('1', names[0]), ('2', names[1])], {1: n1, 2: n2},
         side, x, y, rot, mpn)


def tp(block, ref, value, fp, net, side, x, y):
    part(block, ref, 'TP', value, fp, [('1', '1')], {1: net}, side, x, y)


def conn(block, ref, value, fp, names, nets, side, x, y, rot):
    pins = [(str(i + 1), n) for i, n in enumerate(names)] + [('MP', 'SHIELD')]
    d = {i + 1: n for i, n in enumerate(nets)}
    d['MP'] = 'GND'
    part(block, ref, 'CONN%d' % len(names), value, fp, pins, d, side, x, y, rot)


# ================================================================ Portenta H7 socket
part('Portenta H7 socket', 'J1', 'PORTENTA_J1', 'DF40HC(3.5)-80DS-0.4V(51)',
     'fc:Hirose_DF40HC(3.5)-80DS-0.4V_2x40_P0.4mm',
     [(str(i), J1_NAMES.get(i, 'NC')) for i in range(1, 81)], J1_NETS, 'F', *J1_POS, 0,
     mpn='DF40HC(3.5)-80DS-0.4V(51)')
part('Portenta H7 socket', 'J2', 'PORTENTA_J2', 'DF40HC(3.5)-80DS-0.4V(51)',
     'fc:Hirose_DF40HC(3.5)-80DS-0.4V_2x40_P0.4mm',
     [(str(i), J2_NAMES.get(i, 'NC')) for i in range(1, 81)], J2_NETS, 'F', *J2_POS, 180,
     mpn='DF40HC(3.5)-80DS-0.4V(51)')

# ================================================================ Power: 3-6S in, 5.2 V buck
B = 'Power 3-6S to 5V'
tp(B, 'TP1', 'VBAT', TP30, 'VBAT', 'B', 2.3, 4.5)
tp(B, 'TP2', 'GND', TP30, 'GND', 'B', 2.3, 13.6)
two(B, 'D1', 'D', 'SMBJ26A', 'Diode_SMD:D_SMB', 'VBAT', 'GND', 'B', 9.6, 4.5, 0, 'SMBJ26A')
two(B, 'C1', 'C', '10u 50V', C1206, 'VBAT', 'GND', 'B', 9.0, 7.9)
two(B, 'C2', 'C', '10u 50V', C1206, 'VBAT', 'GND', 'B', 9.0, 10.3)
two(B, 'C3', 'C', '100n 50V', C0603, 'VBAT', 'GND', 'B', 4.0, 17.1, 270)   # hot-loop cap beside U1 VIN/PGND
part(B, 'U1', 'LMR33630ADDA', 'LMR33630ADDA', 'Package_SO:Texas_HSOP-8-1EP_3.9x4.9mm_P1.27mm',
     [('1', 'PGND'), ('2', 'VIN'), ('3', 'EN'), ('4', 'PG'), ('5', 'FB'), ('6', 'VCC'),
      ('7', 'BOOT'), ('8', 'SW'), ('9', 'AGND')],
     {1: 'GND', 2: 'VBAT', 3: 'BUCK_EN', 5: 'BUCK_FB', 6: 'BUCK_VCC', 7: 'BUCK_BOOT',
      8: 'BUCK_SW', 9: 'GND'}, 'B', 8.6, 15.2, 0, 'LMR33630ADDAR')
two(B, 'R1', 'R', '100k', R0402, 'VBAT', 'BUCK_EN', 'B', 14.0, 12.4, 90)
two(B, 'C4', 'C', '1u', C0402, 'BUCK_VCC', 'GND', 'B', 14.0, 15.0, 90)
two(B, 'C5', 'C', '100n', C0402, 'BUCK_BOOT', 'BUCK_SW', 'B', 14.0, 17.6, 90)
two(B, 'L1', 'L', '6.8uH 3.5A', 'Inductor_SMD:L_Bourns_SRP5030T', 'BUCK_SW', '+5V_BUCK',
    'B', 8.6, 22.2, 0, 'MDA5030-6R8M')   # KOHER; pads also take Bourns SRP5030TA / MPS MPL-AL5050
two(B, 'R2', 'R', '51k 1%', R0402, '+5V_BUCK', 'BUCK_FB', 'B', 14.6, 20.6, 90)   # 1.0 V x (1 + 51/12) = 5.25 V
two(B, 'R3', 'R', '12k 1%', R0402, 'BUCK_FB', 'GND', 'B', 14.6, 23.2, 90)
two(B, 'C6', 'C', '22u 25V', C0805, '+5V_BUCK', 'GND', 'B', 6.6, 26.6)
two(B, 'C7', 'C', '22u 25V', C0805, '+5V_BUCK', 'GND', 'B', 11.2, 26.6)
# C26 / C27: 0805 22 uF gives ~10 uF each at 5.25 V; four of them come close to TI's 4 x 22 uF for 5 V / 400 kHz
two(B, 'C26', 'C', '22u 25V', C0805, '+5V_BUCK', 'GND', 'B', 13.9, 26.9, 90)
two(B, 'C27', 'C', '22u 25V', C0805, '+5V_BUCK', 'GND', 'B', 15.9, 27.5, 90)
two(B, 'D2', 'D', 'SS34', 'Diode_SMD:D_SMA', '+5V', '+5V_BUCK', 'B', 9.4, 29.6, 0, 'SS34')
two(B, 'C8', 'C', '22u 25V', C0805, '+5V', 'GND', 'B', 9.4, 32.6)
two(B, 'R15', 'R', '2.2k', R0402, '+5V', 'PWR_LED_A', 'F', 14.2, 35.2, 90)
two(B, 'D5', 'LED', 'WHITE', 'LED_SMD:LED_0603_1608Metric', 'GND', 'PWR_LED_A', 'F', 14.2, 37.8, 90)

# ================================================================ Sensor 3V3 rail
B = 'Sensor rail'
part(B, 'U2', 'LP5907MFX-3.3', 'LP5907MFX-3.3', 'Package_TO_SOT_SMD:SOT-23-5',
     [('1', 'IN'), ('2', 'GND'), ('3', 'EN'), ('4', 'NC'), ('5', 'OUT')],
     {1: '+5V', 2: 'GND', 3: '+5V', 5: '+3V3_SENS'}, 'B', 24.5, 13.0, 0, 'LP5907MFX-3.3/NOPB')
two(B, 'C9', 'C', '1u', C0402, '+5V', 'GND', 'B', 24.5, 10.4)
two(B, 'C10', 'C', '1u', C0402, '+3V3_SENS', 'GND', 'B', 24.5, 15.6)

# ================================================================ Sensors
B = 'IMU (SPI1)'
part(B, 'U3', 'ICM-42688-P', 'ICM-45686', 'Package_LGA:LGA-14_3x2.5mm_P0.5mm_LayoutBorder3x4y',
     [('1', 'AP_SDO'), ('2', 'RESV'), ('3', 'RESV'), ('4', 'INT1'), ('5', 'VDDIO'),
      ('6', 'GND'), ('7', 'RESV'), ('8', 'VDD'), ('9', 'INT2/FSYNC'), ('10', 'RESV'),
      ('11', 'RESV'), ('12', 'AP_CS'), ('13', 'AP_SCLK'), ('14', 'AP_SDI')],
     {1: 'SPI1_CIPO', 4: 'IMU_INT', 5: '+3V3_SENS', 6: 'GND', 7: 'GND', 8: '+3V3_SENS',
      12: 'IMU_CS', 13: 'SPI1_SCK', 14: 'SPI1_COPI'}, 'F', 34.0, 20.0, 0, 'ICM-45686')   # TDK, pin-compatible with ICM-42688-P; JLC 'normal' assembly
two(B, 'C11', 'C', '100n', C0402, '+3V3_SENS', 'GND', 'F', 30.6, 19.2)
two(B, 'C12', 'C', '100n', C0402, '+3V3_SENS', 'GND', 'F', 30.6, 20.8)
two(B, 'C13', 'C', '2.2u', C0402, '+3V3_SENS', 'GND', 'F', 37.2, 20.0, 90)
two(B, 'R4', 'R', '10k', R0402, '+3V3_SENS', 'IMU_CS', 'F', 34.0, 17.0)

B = 'Baro + mag (I2C0)'
part(B, 'U4', 'MS5607', 'MS5607-02BA03', 'Package_LGA:LGA-8_3x5mm_P1.25mm',
     [('1', 'VDD'), ('2', 'PS'), ('3', 'GND'), ('4', 'CSB'), ('5', 'CSB'), ('6', 'SDO'),
      ('7', 'SDI/SDA'), ('8', 'SCLK')],
     {1: '+3V3_SENS', 2: '+3V3_SENS', 3: 'GND', 4: '+3V3_SENS', 5: '+3V3_SENS', 7: 'I2C0_SDA', 8: 'I2C0_SCL'},
     'F', 44.0, 13.0, 180, 'MS560702BA03-50')   # TE: PS high = I2C, CSB high = address 0x76; SDO unused
# rot 180: SDA/SCL face the I2C bus, so nothing crosses TE's "do not route tracks between pads" area
# (U4_KEEPOUT rule area on F.Cu); C14 sits beside VDD (pin 1) as TE asks
two(B, 'C14', 'C', '100n', C0402, '+3V3_SENS', 'GND', 'F', 47.1, 14.875, 0)
part(B, 'U5', 'LIS3MDL', 'LIS3MDL', 'Package_LGA:LGA-12_2x2mm_P0.5mm',
     [('1', 'SCL'), ('2', 'GND'), ('3', 'GND'), ('4', 'C1'), ('5', 'VDD'), ('6', 'VDD_IO'),
      ('7', 'INT'), ('8', 'DRDY'), ('9', 'SA1'), ('10', 'CS'), ('11', 'SDA'), ('12', 'GND')],
     {1: 'I2C0_SCL', 2: 'GND', 3: 'GND', 4: 'MAG_C1', 5: '+3V3_SENS', 6: '+3V3_SENS',
      9: 'GND', 10: '+3V3_SENS', 11: 'I2C0_SDA', 12: 'GND'}, 'F', 44.0, 27.0, 0, 'LIS3MDLTR')
two(B, 'C15', 'C', '100n', C0402, 'MAG_C1', 'GND', 'F', 41.2, 27.0, 90)
two(B, 'C16', 'C', '100n', C0402, '+3V3_SENS', 'GND', 'F', 46.8, 27.0, 90)
two(B, 'C17', 'C', '1u', C0402, '+3V3_SENS', 'GND', 'F', 48.2, 27.0, 90)
two(B, 'R5', 'R', '2.2k', R0402, '+3V3', 'I2C0_SDA', 'F', 26.0, 26.0)
two(B, 'R6', 'R', '2.2k', R0402, '+3V3', 'I2C0_SCL', 'F', 26.0, 27.4)

# ================================================================ CAN
B = 'CAN (DroneCAN)'
part(B, 'U6', 'SN65HVD230', 'SN65HVD230', 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
     [('1', 'D'), ('2', 'GND'), ('3', 'VCC'), ('4', 'R'), ('5', 'VREF'), ('6', 'CANL'),
      ('7', 'CANH'), ('8', 'RS')],
     {1: 'CAN1_TX', 2: 'GND', 3: '+3V3', 4: 'CAN1_RX', 6: 'CANL', 7: 'CANH', 8: 'GND'},
     'B', 24.5, 23.0, 0, 'SN65HVD230DR')
two(B, 'C18', 'C', '100n', C0402, '+3V3', 'GND', 'B', 24.5, 19.2)
two(B, 'R7', 'R', '120R', R0402, 'CANH', 'CAN_TERM', 'B', 22.4, 27.4)
# The flight controller is an end of the CAN bus, so the 120 R terminator is ON by default: JP1 is bridged
# (cut the bridge to take the terminator out).
two(B, 'JP1', 'JP', 'CAN_TERM', 'Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm',
    'CAN_TERM', 'CANL', 'B', 26.4, 27.6)
conn(B, 'J8', 'CAN', GH4, ['5V', 'CANH', 'CANL', 'GND'], ['+5V', 'CANH', 'CANL', 'GND'],
     'F', 7.5, 36.8, 0)

# ================================================================ Ports
B = 'Serial / I2C ports'
conn(B, 'J4', 'GPS+COMPASS', GH6, ['5V', 'TX', 'RX', 'SCL', 'SDA', 'GND'],
     ['+5V', 'UART0_TX', 'UART0_RX', 'I2C0_SCL', 'I2C0_SDA', 'GND'], 'F', 7.5, 3.2, 180)
conn(B, 'J5', 'TELEM1', GH6, ['5V', 'TX', 'RX', 'CTS', 'RTS', 'GND'],
     ['+5V', 'UART1_TX', 'UART1_RX', 'UART1_CTS', 'UART1_RTS', 'GND'], 'F', 60.3, 3.2, 180)
conn(B, 'J6', 'RC (CRSF/SBUS)', GH4, ['5V', 'RX', 'TX', 'GND'],
     ['+5V', 'UART2_RX', 'UART2_TX', 'GND'], 'F', 28.0, 3.2, 180)
conn(B, 'J7', 'UART3', GH4, ['5V', 'TX', 'RX', 'GND'],
     ['+5V', 'UART3_TX', 'UART3_RX', 'GND'], 'F', 40.0, 3.2, 180)
conn(B, 'J9', 'I2C', GH4, ['5V', 'SCL', 'SDA', 'GND'],
     ['+5V', 'I2C0_SCL', 'I2C0_SDA', 'GND'], 'F', 40.6, 36.8, 0)

# ================================================================ ESC / outputs
B = 'ESC + outputs'
conn(B, 'J10', 'ESC 4in1', SH8, ['VBAT', 'GND', 'CURR', 'TLM', 'M1', 'M2', 'M3', 'M4'],   # Betaflight standard
     ['VBAT', 'GND', 'ESC_CURR', 'ESC_TLM', 'M1', 'M2', 'M3', 'M4'], 'F', 29.5, 36.7, 0)
two(B, 'R8', 'R', '100k 1%', R0402, 'VBAT', 'VBAT_SENSE', 'B', 37.0, 29.6)
two(B, 'R9', 'R', '10k 1%', R0402, 'VBAT_SENSE', 'GND', 'B', 37.0, 31.0)
two(B, 'C19', 'C', '100n', C0402, 'VBAT_SENSE', 'GND', 'B', 37.0, 32.4)
two(B, 'R10', 'R', '10k', R0402, 'ESC_CURR', 'CURR_SENSE', 'B', 39.8, 29.6)   # 10k: limits injection if the ESC drives > 3.3 V
two(B, 'C20', 'C', '100n', C0402, 'CURR_SENSE', 'GND', 'B', 39.8, 31.0)
for i, (ref, net) in enumerate([('TP3', 'LED_STRIP'), ('TP4', 'S6'), ('TP5', 'S5'),
                                ('TP6', 'BUZZ_N'), ('TP7', '+5V'), ('TP8', 'GND')]):
    tp(B, ref, net, TP15, net, 'F', 57.0 + 3.2 * (i % 3), 35.0 + 3.0 * (i // 3))
part(B, 'Q1', 'NMOS', '2N7002', 'Package_TO_SOT_SMD:SOT-23',
     [('1', 'G'), ('2', 'S'), ('3', 'D')], {1: 'BUZZ_G', 2: 'GND', 3: 'BUZZ_N'},
     'B', 45.6, 30.0, 0, '2N7002')
two(B, 'R12', 'R', '1k', R0402, 'BUZZER', 'BUZZ_G', 'B', 42.6, 29.6, 90)
two(B, 'R13', 'R', '100k', R0402, 'BUZZ_G', 'GND', 'B', 42.6, 32.2, 90)   # 100k: Q1 gets 3.27 V, not 3.0 V
two(B, 'D4', 'D', '1N4148W', 'Diode_SMD:D_SOD-123', '+5V', 'BUZZ_N', 'B', 45.6, 26.8, 0, '1N4148W')
two(B, 'R14', 'R', '1k', R0402, '+3V3', 'STAT_LED_A', 'F', 34.0, 4.8, 90)
two(B, 'D3', 'LED', 'RED', 'LED_SMD:LED_0603_1608Metric', 'LED_STATUS', 'STAT_LED_A', 'F', 34.0, 2.0, 90)

# ================================================================ microSD (SDMMC2) + debug
B = 'microSD + debug'
part(B, 'J11', 'MICROSD', 'microSD', 'Connector_Card:microSD_HC_Molex_104031-0811',
     [('1', 'DAT2'), ('2', 'DAT3'), ('3', 'CMD'), ('4', 'VDD'), ('5', 'CLK'), ('6', 'VSS'),
      ('7', 'DAT0'), ('8', 'DAT1'), ('9', 'DET_B'), ('10', 'DET_A'), ('11', 'SHIELD')],
     {1: 'SDC_D2', 2: 'SDC_D3', 3: 'SDC_CMD', 4: '+3V3', 5: 'SDC_CLK', 6: 'GND',
      7: 'SDC_D0', 8: 'SDC_D1', 10: 'GND', 11: 'GND'}, 'B', 59.0, 20.0, 90, '104031-0811')
two(B, 'C21', 'C', '100n', C0402, '+3V3', 'GND', 'B', 49.6, 18.0, 90)
two(B, 'C22', 'C', '10u', C0805, '+3V3', 'GND', 'B', 49.6, 21.4, 90)
# C23: 100 nF at the card's supply, on top beside the +3V3 via that drops straight to J11-4 (~3 mm of copper);
# C21/C22 are 15 mm away at the far end of the socket, and the card's path under the board must stay clear
two(B, 'C23', 'C', '100n', C0402, '+3V3', 'GND', 'F', 66.9, 21.1, 90)
two(B, 'R11', 'R', '0R', R0402, 'V_SDCARD', '+3V3', 'B', 49.6, 15.0, 90)   # NEVER FIT: would parallel the H7's VSD output with +3V3 (card runs from +3V3)
for i, net in enumerate(['SWDIO', 'SWCLK', 'NRST', 'GND', '+3V3']):
    tp(B, 'TP%d' % (9 + i), net, TPD15, net, 'B', 23.6 + 2.5 * i, 32.2)

# ================================================================ ADC reference
# The module ties VREF+ (J2-71) to its 3.1 V rail through only ~100 k / 100 nF, and it sags during conversions
# (battery and current readings then drift by up to ~19 %).  A 2.5 V series reference drives it instead; it runs
# from 3.0 V too (the module's 3V3 can sit at 3.0 V on USB).  Full scale: VBAT 27.5 V (11:1), current 2.5 V.
# Portenta C33 build: leave U7 (and C25) unfitted - J2-71 is an output on the C33.
B = 'ADC reference'
part(B, 'U7', 'REF3125', 'REF3125', 'Package_TO_SOT_SMD:SOT-23', [('1', 'IN'), ('2', 'OUT'), ('3', 'GND')],
     {1: '+3V3', 2: 'ADC_VREF', 3: 'GND'}, 'B', 59.9, 29.4, 0, 'REF3125AIDBZR')
two(B, 'C24', 'C', '100n', C0402, '+3V3', 'GND', 'F', 57.4, 30.7, 90)   # top, under the module, via to U7-1
two(B, 'C25', 'C', '1u', C0402, 'ADC_VREF', 'GND', 'B', 57.0, 28.5)        # with the module's 100 nF: ST's 1 uF + 100 nF

# ---------------------------------------------------------------- not fitted (do not populate)
# Footprints stay on the board; JLCPCB's BOM/CPL, the schematic (dnp) and the board's exclude-from-BOM/position
# attributes all follow this list (jlc.py, gen.py, sync_values.py).
DNP = {
    'R11': "NEVER FIT: would parallel the H7's VSD output with +3V3 (README item 4)",
    'U5': "LIS3MDLTR (C478483) had no stock and no drop-in; use the GPS module's compass",
    'C15': "U5's C1 capacitor - only needed when U5 is fitted",
}

# ---------------------------------------------------------------- mechanical
M3_HOLES = [(BOARD_W / 2 + sx * 15.25, BOARD_H / 2 + sy * 15.25) for sx in (-1, 1) for sy in (-1, 1)]
# Portenta's own 2.25 mm holes, 2.03 mm in from each corner (datasheet 7.2)
M2_HOLES = [(H7_X0 + x, H7_Y0 + y) for x in (2.03, H7_W - 2.03) for y in (2.03, H7_H - 2.03)]

# ---------------------------------------------------------------- routing classes
# GND and +5V are inner-layer planes (In1 / In2); everything else is Default (0.15 mm).
NETCLASSES = {
    'Power': ['VBAT', '+5V_BUCK', 'BUCK_SW'],
    'Rail': ['+5V', 'GND', '+3V3', '+3V3_SENS', 'V_SDCARD', 'BUZZ_N'],
}
