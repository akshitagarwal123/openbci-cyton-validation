"""
BrainTech-8 (rev B) circuit description: every part, its library symbol, footprint, value and pin -> net map.
Built up one block per week-3 task; the source of each value is noted next to it.
gen_schematic.py turns this into braintech8.kicad_sch.

Pin maps use pin *names* (applied to every pin with that name) or pin *numbers* ("#12").
Any pin not mapped becomes a no-connect.
"""

FP_R = "Resistor_SMD:R_0402_1005Metric"
FP_C = "Capacitor_SMD:C_0402_1005Metric"
FP_C0603 = "Capacitor_SMD:C_0603_1608Metric"
FP_C0805 = "Capacitor_SMD:C_0805_2012Metric"
FP_LED = "LED_SMD:LED_0603_1608Metric"

parts = []      # dict(ref, lib_id, value, footprint, pins {pin: net}, block, mpn)
_count = {}


def ref(prefix):
    _count[prefix] = _count.get(prefix, 0) + 1
    return f"{prefix}{_count[prefix]}"


def add(prefix, lib_id, value, fp, pins, block, mpn=""):
    r = ref(prefix)
    parts.append(dict(ref=r, lib_id=lib_id, value=value, footprint=fp, pins=pins, block=block, mpn=mpn))
    return r


def R(value, a, b, block, fp=FP_R):
    return add("R", "Device:R", value, fp, {"#1": a, "#2": b}, block)


def C(value, a, b, block, fp=FP_C):
    return add("C", "Device:C", value, fp, {"#1": a, "#2": b}, block)


# ------------------------------------------------------------------ power ------------------------------------------
# Same circuit as rev A (hardware/kicad/circuit.py), with the rev B changes: JST-SH battery plug, FNR4020 inductor
# (JLCPCB C167825), USB-plugged detection to the ESP32, 0402 passives where the value allows.
B = "Power"

# USB-C: charging and ESP32 programming. Never record from a person while it is plugged in.
add("J", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C (charge + firmware)",
    "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
    {"VBUS": "VBUS", "GND": "GND", "SHIELD": "GND", "CC1": "CC1", "CC2": "CC2", "D+": "USB_DP", "D-": "USB_DN"}, B)
R("5.1k", "CC1", "GND", B)                  # USB-C sink: 5.1 kOhm pull-down on each CC pin (USB Type-C spec, Rd)
R("5.1k", "CC2", "GND", B)
R("100k", "VBUS", "VBUS_SENSE", B)          # USB-plugged detection: 5 V / 2 = 2.5 V to an ESP32 GPIO (rev A review item 9)
R("100k", "VBUS_SENSE", "GND", B)

# LiPo charger: MCP73831-2 = 4.20 V. I_charge = 1000 V / R_PROG = 1000 / 2k = 500 mA (MCP73831 datasheet).
add("U", "Battery_Management:MCP73831-2-OT", "MCP73831-2 (4.2 V, 500 mA)", "Package_TO_SOT_SMD:SOT-23-5",
    {"V_{DD}": "VBUS", "V_{SS}": "GND", "V_{BAT}": "VBAT", "PROG": "CHG_PROG", "STAT": "CHG_STAT"}, B, "MCP73831T-2ACI/OT")
C("4.7uF", "VBUS", "GND", B, FP_C0603)      # MCP73831: 4.7 uF minimum on VDD and on VBAT
C("4.7uF", "VBAT", "GND", B, FP_C0603)
R("2k", "CHG_PROG", "GND", B)
R("1k", "VBUS", "CHG_LED_A", B)
add("D", "Device:LED", "red (charging)", FP_LED, {"#2": "CHG_LED_A", "#1": "CHG_STAT"}, B)   # STAT pulls low while charging

# Battery and switch. JST SH contacts are rated 1 A: fine for 500 mA charging and ~350 mA Wi-Fi peaks.
add("J", "Connector_Generic:Conn_01x02", "LiPo 1S (protected), JST SH",
    "Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal", {"#1": "VBAT", "#2": "GND"}, B)   # check pack polarity
add("SW", "Switch:SW_SPDT", "power switch", "Button_Switch_SMD:SW_SPDT_PCM12", {"#2": "VBAT", "#1": "VSYS"}, B)
R("100k", "VSYS", "VBAT_SENSE", B)          # battery monitor: VSYS / 2 to an ESP32 ADC pin (4.2 V -> 2.1 V)
R("100k", "VBAT_SENSE", "GND", B)
C("100nF", "VBAT_SENSE", "GND", B)

# 3.3 V digital: TLV62569 buck (ESP32 Wi-Fi peaks ~350 mA). Vout = 0.6 V * (1 + 100k / 22.1k) = 3.31 V (datasheet FB = 0.6 V)
add("U", "Regulator_Switching:TLV62569DBV", "TLV62569 (3.3 V buck)", "Package_TO_SOT_SMD:SOT-23-5",
    {"VIN": "VSYS", "EN": "VSYS", "SW": "SW_3V3", "FB": "FB_3V3", "GND": "GND"}, B, "TLV62569DBVR")
C("10uF", "VSYS", "GND", B, FP_C0805)
add("L", "Device:L", "2.2uH FNR4020S2R2MT", "Inductor_SMD:L_Changjiang_FNR4020S", {"#1": "SW_3V3", "#2": "3V3"}, B)
R("100k", "3V3", "FB_3V3", B)
R("22.1k", "FB_3V3", "GND", B)
C("22uF", "3V3", "GND", B, FP_C0805)
C("22uF", "3V3", "GND", B, FP_C0805)

# +2.5 V analog (AVDD) from 3.3 V, as the Cyton (TLV70025 there; LP5907 is lower noise, 6.5 uVrms)
add("U", "Regulator_Linear:LP5907MFX-2.5", "LP5907 +2.5 V (AVDD)", "Package_TO_SOT_SMD:SOT-23-5",
    {"IN": "3V3", "EN": "3V3", "OUT": "AVDD", "GND": "GND"}, B, "LP5907MFX-2.5")
C("1uF", "3V3", "GND", B)
C("1uF", "AVDD", "GND", B)
C("10uF", "AVDD", "GND", B, FP_C0805)       # 10 uF at each regulator output (week 3 decision; check LP5907 stability range)

# -2.5 V analog (AVSS): charge-pump inverter on 3.3 V (Cyton: LM2664), then a negative LDO (Cyton: TPS72325)
add("U", "Regulator_SwitchedCapacitor:LM2776", "LM2776 inverter (-3.3 V)", "Package_TO_SOT_SMD:SOT-23-6",
    {"VIN": "3V3", "EN": "3V3", "VOUT": "NEG3V3", "C1+": "CP_P", "C1-": "CP_N", "GND": "GND"}, B, "LM2776DBVR")
C("4.7uF", "3V3", "GND", B, FP_C0603)
C("1uF", "CP_P", "CP_N", B)                 # flying capacitor
C("4.7uF", "NEG3V3", "GND", B, FP_C0603)
add("U", "Regulator_Linear:ADP7182AUJZ-2.5", "ADP7182 -2.5 V (AVSS)", "Package_TO_SOT_SMD:TSOT-23-5",
    {"VIN": "NEG3V3", "EN": "NEG3V3", "VOUT": "AVSS", "GND": "GND"}, B, "ADP7182AUJZ-2.5")   # datasheet: "for automatic startup, connect EN to VIN"
C("2.2uF", "NEG3V3", "GND", B)
C("2.2uF", "AVSS", "GND", B)
C("10uF", "AVSS", "GND", B, FP_C0805)

for net in ("VBUS", "VSYS", "3V3", "GND"):   # VBAT is driven by the charger output
    add("#FLG", "power:PWR_FLAG", "PWR_FLAG", "", {"#1": net}, B)

# ------------------------------------------------------------------ ADS1299 --------------------------------------------
# Pin rules: TI ADS1299 datasheet SBAS499C pin table (p. 6-7), unused-pin rules (p. 61), layout notes (p. 70-72).
# Capacitor choices are the week-3 decisions in learning/week03/ads1299_pins_and_power.md.
B = "ADS1299"
add("U", "BrainTech:ADS1299_AllPins", "ADS1299 (8 ch EEG ADC)", "Package_QFP:TQFP-64_10x10mm_P0.5mm", {
    "AVDD": "AVDD", "AVSS": "AVSS",                       # pins 19,21,22,56,59 / 20,23,32,57,58
    "AVDD1": "AVDD1", "AVSS1": "AVSS1",                   # pins 54 / 53: joined to AVDD/AVSS at one point (net ties below)
    "DVDD": "3V3", "DGND": "GND",                         # pins 48,50 / 33,49,51: one ground net on this board
    "VREFP": "VREFP", "VREFN": "AVSS",                    # internal reference: VREFN to AVSS (p. 7)
    "VCAP1": "VCAP1", "VCAP2": "VCAP2", "VCAP3": "VCAP3", "VCAP4": "VCAP4",
    "RESV1": "GND",                                       # p. 6: connect RESV1 directly to DGND
    "DAISY_IN": "GND",                                    # p. 61: tie to DGND when not daisy-chaining
    "CLKSEL": "CLKSEL",                                   # pulled up below: internal 2.048 MHz oscillator; CLK pin left open
    "SCLK": "SCLK", "DIN": "MOSI", "DOUT": "MISO", "~{CS}": "ADS_CS", "~{DRDY}": "ADS_DRDY",
    "START": "ADS_START", "~{RESET}": "ADS_RESET", "~{PWDN}": "ADS_PWDN",
    "GPIO1": "ADS_GPIO1", "GPIO2": "ADS_GPIO2", "GPIO3": "ADS_GPIO3", "GPIO4": "ADS_GPIO4",
    "SRB2": "SRB",                                        # week-3 decision: reference on SRB2 (as the Cyton), SRB1 left open (p. 61)
    "BIASOUT": "BIAS_OUT", "BIASIN": "BIAS_OUT", "BIASINV": "BIAS_INV",   # bias network drawn with the electrode inputs
    "BIASREF": "AVSS",                                    # internal bias reference used (CONFIG3.BIASREF_INT = 1), pin to AVSS (p. 61)
    **{f"IN{ch}N": f"CH{ch}" for ch in range(1, 9)},     # electrodes on the negative inputs; SRB2 drives every positive input
}, B, "ADS1299IPAGR")

# Supply capacitors: 1 uF + 100 nF at every power pin, placed beside that pin.
for pin in ("19", "21", "22", "56", "59/58 (charge pump)"):     # one pair per AVDD pin, to AVSS
    C("1uF", "AVDD", "AVSS", B); C("100nF", "AVDD", "AVSS", B)
C("1uF", "AVDD1", "AVSS1", B); C("100nF", "AVDD1", "AVSS1", B)   # pins 54-53
add("NT", "Device:NetTie_2", "AVDD1 to AVDD (single point)", "NetTie:NetTie-2_SMD_Pad0.5mm", {"#1": "AVDD1", "#2": "AVDD"}, B)
add("NT", "Device:NetTie_2", "AVSS1 to AVSS (single point)", "NetTie:NetTie-2_SMD_Pad0.5mm", {"#1": "AVSS1", "#2": "AVSS"}, B)
for pin in ("48", "50"):                                         # DVDD pins, to ground
    C("1uF", "3V3", "GND", B); C("100nF", "3V3", "GND", B)
# Split +-2.5 V supply: each rail also gets a pair to ground at the chip (as the Cyton's C22/C24 and C18/C21)
C("1uF", "AVDD", "GND", B); C("100nF", "AVDD", "GND", B)
C("1uF", "AVSS", "GND", B); C("100nF", "AVSS", "GND", B)

# Reference and internal nodes (pin table p. 6-7, Figure 78 p. 71; same values as the Cyton)
C("10uF", "VREFP", "AVSS", B, FP_C0805); C("100nF", "VREFP", "AVSS", B)   # VREFP-VREFN >= 10 uF
C("100uF", "VCAP1", "AVSS", B, "Capacitor_SMD:C_1206_3216Metric")         # DECISION open: X5R (as Cyton) or tantalum (p. 70)
C("1uF", "VCAP2", "AVSS", B)
C("1uF", "VCAP3", "AVSS", B); C("100nF", "VCAP3", "AVSS", B)
C("1uF", "VCAP4", "AVSS", B)

# Mode and unused pins: two-state pins through >= 10 kOhm (p. 6)
R("10k", "CLKSEL", "3V3", B)                    # CLKSEL = 1: internal oscillator
for g in range(1, 5):
    R("10k", f"ADS_GPIO{g}", "GND", B)          # unused GPIO1-4 to DGND
# Defined levels while the ESP32 boots (its pins float until firmware runs): stay powered, out of reset, not converting
R("10k", "ADS_RESET", "3V3", B)
R("10k", "ADS_PWDN", "3V3", B)
R("10k", "ADS_START", "GND", B)                 # START held low; conversions started by the START command (p. 35)
for net in ("AVDD1", "AVSS1"):                  # fed through the net ties: tell ERC these are supplied
    add("#FLG", "power:PWR_FLAG", "PWR_FLAG", "", {"#1": net}, B)
