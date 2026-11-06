import zipfile, re, html, json, sys
B = '/private/tmp/claude-501/-Users-akshitagarwal-Documents-Projects-BrainTech/dce332fa-8623-40e9-9f72-e9afb7d75bc0/scratchpad/bom/'
def load(path):
    z = zipfile.ZipFile(path); ss = [re.sub(r'<[^>]+>', '', x) for x in re.findall(r'<si>(.*?)</si>', z.read('xl/sharedStrings.xml').decode(), re.S)]
    sh = z.read('xl/worksheets/sheet1.xml').decode(); rows = []
    for row in re.findall(r'<row[^>]*>(.*?)</row>', sh, re.S):
        out = []
        for attrs, inner in re.findall(r'<c ([^>]*?)(?:/>|>(.*?)</c>)', row, re.S):
            v = re.search(r'<v>(.*?)</v>', inner or '')
            out.append('' if not v else html.unescape(ss[int(v.group(1))] if 't="s"' in attrs else v.group(1)).strip())
        rows.append(out)
    return rows
MFR = {'TI': 'Texas Instruments', 'ST': 'STMicroelectronics', 'BOURNS': 'Bourns', 'TDK': 'TDK', 'COPAL': 'Copal', 'SUNTECH': 'Suntech', 'ABRACON': 'Abracon', 'RF DIGITAL': 'RF Digital', 'Wurth': 'Würth Elektronik'}
DESC = {'MLCC': 'Multilayer ceramic capacitor', '4 R-ARRAY': 'Resistor array: 4 resistors in one package', '4 CAP ARRAY': 'Capacitor array: 4 capacitors in one package', '4 CAPACITOR ARRAY': 'Capacitor array: 4 capacitors in one package',
        'Capacitor, Surface Mount Multi-Layer Ceramic': 'Multilayer ceramic capacitor', 'ST ACCELEROMETER': '3-axis accelerometer', 'OR_GATE': 'Single 2-input OR gate', 'V INVERTER': 'Voltage inverter (charge pump)',
        '+2.5V LDO REG': '+2.5 V low-dropout regulator', '3V3 LDO REG': '+3.3 V low-dropout regulator', '-2.5 LDO REG': '−2.5 V low-dropout regulator', 'ADS1299': '8-channel, 24-bit analog front end for EEG',
        'PIC32 MICROCONTROLLER': '32-bit microcontroller', 'BTLE Module': 'Bluetooth Low Energy radio module', 'BLUE LED': 'Blue LED', 'DIODE': 'Diode', 'TI QUAD TVS': 'Quad TVS array (static-discharge protection, 4 lines)', 'QUAD TVS': 'Quad TVS array (static-discharge protection, 4 lines)',
        '3V Zener Diode': '3 V Zener diode', 'Resistor': 'Resistor', '8MHz XTAL': '8 MHz crystal', 'CONN HEADER PH SIDE 2POS 2MM SMD': 'JST PH battery connector: 2 positions, 2 mm pitch, side entry, SMD', 'SP3T SLIDE SWITCH': '3-position slide switch (PC · OFF · BLE)',
        'TACT SWITCH': 'Tactile push button', 'microSD card slot': 'microSD card slot', 'Dual 11 x 2  0.1" pitch MALE header row Right Angle': 'Right-angle male header, 2 rows × 11 pins, 0.1 in pitch'}
def fmtval(v):
    if not v: return ''
    m = re.fullmatch(r'([\d.]+)\s*([uUpPnNkKmM]?)(F|MHz|V)?', v)
    if not m: return v
    num, pre, unit = m.groups()
    if v == 'LED': return ''
    if unit == 'MHz': return f'{num} MHz'
    if unit == 'V': return f'{num} V'
    if unit == 'F' or pre.lower() == 'u' and unit == 'F':
        p = {'u': 'µ', 'U': 'µ', 'p': 'p', 'P': 'p', 'n': 'n', 'N': 'n'}.get(pre, pre); s = f'{num} {p}F'
        if (pre, num) in (('u', '0.001'), ('u', '0.01')): s += {'0.001': ' (1 nF)', '0.01': ' (10 nF)'}[num]
        if (pre, num) == ('u', '0.1'): s += ' (100 nF)'
        return s
    if re.fullmatch(r'[\d.]+[KkMm]', v): return f'{v[:-1]} {"k" if v[-1] in "Kk" else "M"}Ω'
    return v
def build(path, prefix):
    out = {}
    for r in load(path)[2:]:
        if len(r) < 9 or not r[1]: continue
        refs = [x.strip() for x in r[1].split(',') if x.strip()]; qty = len(refs)
        for ref in refs:
            out[prefix + ref] = {'pn': r[7].strip(), 'mfr': MFR.get(r[6].strip(), r[6].strip()), 'val': fmtval(r[4]), 'pkg': r[5].strip(), 'type': DESC.get(r[8].strip(), r[8].strip()), 'same': [prefix + x for x in refs if x != ref], 'qty': qty}
    return out
S = build(B + 'cyton_bom.xlsx', ''); S.update(build('/private/tmp/claude-501/-Users-akshitagarwal-Documents-Projects-BrainTech/dce332fa-8623-40e9-9f72-e9afb7d75bc0/scratchpad/daisy/bom.xlsx', 'Daisy '))
KEY = {
 'U6': ['8 low-noise PGAs and 8 simultaneous 24-bit ADCs', 'gain 1, 2, 4, 6, 8, 12 or 24', '250 to 16,000 samples per second', 'input-referred noise 1 µVpp (70 Hz bandwidth)', 'CMRR −110 dB · input bias current 300 pA', 'analog supply 4.75 to 5.25 V · digital 1.8 to 3.6 V', 'built-in bias amplifier, lead-off detection, test signals and oscillator', 'source: TI datasheet SBAS499C, page 1'],
 'U5': ['150 mA output (MCP1754 family)', 'the layout file names this footprint "LP5907", but the rev C BOM lists the MCP1754'],
 'U1': ['3 axes, firmware sets the ±4 g range', 'SPI (CS4), interrupt on INT1'],
 'U7': ['runs OpenBCI firmware with the chipKIT UDB32-MX2-DIP bootloader', 'SPI to the ADS1299, accelerometer, SD card and Daisy; UART to the radio'],
 'B1': ['the board is powered by a 3 to 6 V battery only'],
 'D2': ['4 protected lines per package'], 'D3': ['4 protected lines per package'], 'D4': ['4 protected lines per package'], 'D5': ['4 protected lines per package'], 'D6': ['4 protected lines per package'], 'D7': ['4 protected lines per package'],
}
for k in list(KEY):
    if k.startswith('D') and k != 'D6': pass
KEY['Daisy U1'] = KEY['U6'][:7] + ['clock from the Cyton chip (CLKSEL tied to ground)', KEY['U6'][7]]
KEY['Daisy C2'] = ['100 µF on VCAP1 (X5R ceramic)']
json.dump({'specs': S, 'key': KEY}, open('specs.json', 'w'), ensure_ascii=False, separators=(',', ':'))
print(len(S), 'parts;', len(KEY), 'with key specs')
for k in ('U6', 'U5', 'C2', 'R2', 'C9', 'PL1', 'Daisy U1', 'Daisy C9', 'SW1', 'X1', 'D9', 'B1'): print(k, S.get(k))
