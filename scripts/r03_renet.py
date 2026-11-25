"""R0.3 review fixes, step 1 (no removals): net swaps / re-assignments and new footprints.

  - LED strip moves to PJ10 (J2-66, TIM8_CH2, DMA-capable), S5 to PH6 (J2-68, TIM12_CH1): the copper of the
    two nets is swapped, nothing moves (TP3 becomes LED, TP5 becomes S5).
  - ESC telemetry gets its own UART: PA8 (J2-59) = UART7_RX.  M1 moves to PK1 (J2-60, TIM1_CH1); M1's old route
    (J10 -> J2-59) becomes ESC_TLM, J10-4 is re-attached to it by r03_rip.py + patch.py.
  - VBAT / current sense move from the analog-only PA0_C / PA1_C pads (J2-73/75) to PA4 / PA6 (J2-78/80).
  - ADC VREF+ (J2-71) gets a 2.5 V reference U7 (REF3125, powered from J2-69, the 4th +3V3 pin), VREF- (J2-72)
    goes to GND.
  - Buck output: C26 / C27 (22 uF) join C6 / C7.
Run once on the routed board, then r03_rip.py, then the routing commands listed in README.
Applied 2026-11-15.  Afterwards (by hand, see README "Rev 0.3 review"): U7 moved to (59.9, 29.4) clear of
the motor tracks, C24 / C25 / C27 added beside it and C26, J2-69 left open again (U7 gets +3V3 through
C24's route), and the planned 0 R link R16 dropped - J2-71 has no lane for it - so VREF_2V5 became ADC_VREF.
"""
import os, sys, uuid
import pcbnew
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PCB = os.path.join(ROOT, 'portenta_drone_fc.kicad_pcb')
NS = uuid.UUID('5f0f6a34-3c0e-4d55-9b0e-0d6a5a1f7e11')
MM = pcbnew.FromMM
b = pcbnew.LoadBoard(PCB)


def net(name):
    n = b.FindNet(name)
    if n is None:
        n = pcbnew.NETINFO_ITEM(b, name)
        b.Add(n)
        n = b.FindNet(name)
    return n


def pad(ref, num):
    return [p for p in b.FindFootprintByReference(ref).Pads() if p.GetNumber() == num][0]


# 1. S5 <-> LED_STRIP on every copper item and pad
s5, led = net('S5'), net('LED_STRIP')
swap = []
for t in b.GetTracks():
    if t.GetNetname() in ('S5', 'LED_STRIP'):
        swap.append(t)
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetNetname() in ('S5', 'LED_STRIP'):
            swap.append(p)
for it in swap:
    it.SetNet(led if it.GetNetname() == 'S5' else s5)
print('S5 <-> LED_STRIP swapped on', len(swap), 'items')

# 2. M1's route becomes ESC_TLM; pads re-assigned
tlm = net('ESC_TLM')
n = 0
for t in b.GetTracks():
    if t.GetNetname() == 'M1':
        t.SetNet(tlm)
        n += 1
pad('J2', '59').SetNet(tlm)
pad('J10', '4').SetNet(tlm)
pad('J2', '60').SetNet(net('M1'))
print('M1 route ->', n, 'ESC_TLM items')

# 3. sense pins, VREF, 4th 3V3 pin
pad('J2', '73').SetNetCode(0)
pad('J2', '75').SetNetCode(0)
pad('J2', '78').SetNet(net('VBAT_SENSE'))
pad('J2', '80').SetNet(net('CURR_SENSE'))
pad('J2', '71').SetNet(net('ADC_VREF'))
pad('J2', '72').SetNet(net('GND'))
pad('J2', '69').SetNet(net('+3V3'))


# 4. new footprints (copies of parts already on the bottom, so side / flip / library come along)
def clone(src, ref, value, x, y, rot, nets):
    f = pcbnew.FOOTPRINT(b.FindFootprintByReference(src))
    f.SetReference(ref)
    f.SetValue(value)
    f.SetPosition(pcbnew.VECTOR2I(MM(x), MM(y)))
    f.SetOrientationDegrees(rot)
    f.SetPath(pcbnew.KIID_PATH('/' + str(uuid.uuid5(NS, 'sym/' + ref))))
    for p in f.Pads():
        p.SetNet(net(nets[p.GetNumber()]))
    b.Add(f)
    print(ref, 'added at (%.2f, %.2f) rot %d:' % (x, y, rot),
          [(p.GetNumber(), p.GetNetname(), round(pcbnew.ToMM(p.GetPosition().x), 2), round(pcbnew.ToMM(p.GetPosition().y), 2)) for p in f.Pads()])


clone('Q1', 'U7', 'REF3125', 61.6, 28.9, 0, {'1': '+3V3', '2': 'VREF_2V5', '3': 'GND'})
clone('C7', 'C26', '22u 25V', 13.9, 26.9, 90, {'1': '+5V_BUCK', '2': 'GND'})
pcbnew.SaveBoard(PCB, b)
