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
