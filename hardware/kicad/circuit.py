"""
BrainTech-16 circuit description: every part, its library symbol, footprint, value and pin -> net map.
Values are taken from the OpenBCI Cyton schematic (CC BY-SA 3.0) and the TI ADS1299 datasheet (SBAS499C);
the source of each choice is noted. gen_schematic.py turns this into a KiCad schematic.

Pin maps use pin *names* (applied to every pin with that name) or pin *numbers* ("#12").
Any pin not mapped becomes a no-connect.
"""

FP_R = "Resistor_SMD:R_0603_1608Metric"
FP_C = "Capacitor_SMD:C_0603_1608Metric"
FP_C0805 = "Capacitor_SMD:C_0805_2012Metric"
FP_C1206 = "Capacitor_SMD:C_1206_3216Metric"
FP_TVS = "Diode_SMD:D_0402_1005Metric"
FP_LED = "LED_SMD:LED_0603_1608Metric"

parts = []      # (ref, lib_id, value, footprint, {pin: net}, block)
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
B = "Power"
add("J", "Connector:USB_C_Receptacle_USB2.0_16P", "USB-C (charge + firmware)",
    "Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal",
    {"VBUS": "VBUS", "GND": "GND", "SHIELD": "GND", "CC1": "CC1", "CC2": "CC2", "D+": "USB_DP", "D-": "USB_DN"}, B)
R("5.1k", "CC1", "GND", B)   # USB-C sink: 5.1k pull-downs on CC (USB-C spec)
R("5.1k", "CC2", "GND", B)
add("U", "Battery_Management:MCP73831-2-OT", "MCP73831-2 (4.2 V, 500 mA)", "Package_TO_SOT_SMD:SOT-23-5",
    {"V_{DD}": "VBUS", "V_{SS}": "GND", "V_{BAT}": "VBAT", "PROG": "CHG_PROG", "STAT": "CHG_STAT"}, B, "MCP73831T-2ACI/OT")
C("4.7uF", "VBUS", "GND", B, FP_C0805)
C("4.7uF", "VBAT", "GND", B, FP_C0805)
R("2k", "CHG_PROG", "GND", B)               # I_charge = 1000 V / 2k = 500 mA (MCP73831 datasheet)
R("1k", "VBUS", "CHG_LED_A", B)
add("D", "Device:LED", "red (charging)", FP_LED, {"#2": "CHG_LED_A", "#1": "CHG_STAT"}, B)
add("J", "Connector_Generic:Conn_01x02", "LiPo 1S 2000 mAh (protected)",
    "Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal", {"#1": "VBAT", "#2": "GND"}, B)
add("SW", "Switch:SW_SPDT", "power switch", "Button_Switch_SMD:SW_SPDT_PCM12", {"#2": "VBAT", "#1": "VSYS"}, B)
R("100k", "VSYS", "VBAT_SENSE", B)          # battery monitor: VSYS/2 to ESP32 ADC
R("100k", "VBAT_SENSE", "GND", B)
C("100nF", "VBAT_SENSE", "GND", B)

# 3.3 V digital: TLV62569 buck (ESP32 Wi-Fi peaks ~400 mA). Vout = 0.6 V * (1 + 100k/22.1k) = 3.31 V
add("U", "Regulator_Switching:TLV62569DBV", "TLV62569 (3.3 V buck)", "Package_TO_SOT_SMD:SOT-23-5",
    {"VIN": "VSYS", "EN": "VSYS", "SW": "SW_3V3", "FB": "FB_3V3", "GND": "GND"}, B, "TLV62569DBVR")
C("10uF", "VSYS", "GND", B, FP_C0805)
add("L", "Device:L", "2.2uH (>=1.5 A)", "Inductor_SMD:L_1210_3225Metric", {"#1": "SW_3V3", "#2": "3V3"}, B)
R("100k", "3V3", "FB_3V3", B)
R("22.1k", "FB_3V3", "GND", B)
C("22uF", "3V3", "GND", B, FP_C0805)
C("22uF", "3V3", "GND", B, FP_C0805)

# +2.5 V analog (AVDD) from 3.3 V, as Cyton (TLV70025 there; LP5907 = 6.5 uVrms noise)
add("U", "Regulator_Linear:LP5907MFX-2.5", "LP5907 +2.5 V (AVDD)", "Package_TO_SOT_SMD:SOT-23-5",
    {"IN": "3V3", "EN": "3V3", "OUT": "AVDD", "GND": "GND"}, B, "LP5907MFX-2.5")
C("1uF", "3V3", "GND", B)
C("1uF", "AVDD", "GND", B)
C("10uF", "AVDD", "GND", B, FP_C0805)

# -2.5 V analog (AVSS): charge-pump inverter on 3.3 V (Cyton: LM2664) then negative LDO (Cyton: TPS72325)
add("U", "Regulator_SwitchedCapacitor:LM2776", "LM2776 inverter (-3.3 V)", "Package_TO_SOT_SMD:SOT-23-6",
    {"VIN": "3V3", "EN": "3V3", "VOUT": "NEG3V3", "C1+": "CP_P", "C1-": "CP_N", "GND": "GND"}, B, "LM2776DBVR")
C("4.7uF", "3V3", "GND", B, FP_C0805)
C("1uF", "CP_P", "CP_N", B)
C("4.7uF", "NEG3V3", "GND", B, FP_C0805)
add("U", "Regulator_Linear:ADP7182AUJZ-2.5", "ADP7182 -2.5 V (AVSS)", "Package_TO_SOT_SMD:TSOT-23-5",
    {"VIN": "NEG3V3", "EN": "NEG3V3", "VOUT": "AVSS", "GND": "GND"}, B, "ADP7182AUJZ-2.5")   # EN tied to VIN [verify]
C("2.2uF", "NEG3V3", "GND", B)
C("2.2uF", "AVSS", "GND", B)
C("10uF", "AVSS", "GND", B, FP_C0805)

for net in ("VBUS", "VSYS", "3V3", "GND"):   # VBAT is driven by the charger output
    add("#FLG", "power:PWR_FLAG", "PWR_FLAG", "", {"#1": net}, B)

# ------------------------------------------------------------------ MCU --------------------------------------------
B = "MCU"
add("U", "RF_Module:ESP32-S3-WROOM-1", "ESP32-S3-WROOM-1U-N8 (u.FL antenna)", "RF_Module:ESP32-S3-WROOM-1U", {
    "3V3": "3V3", "GND": "GND", "EN": "ESP_EN", "IO0": "BOOT",
    "IO12": "SCLK", "IO11": "MOSI", "IO13": "MISO", "IO10": "CS1", "IO9": "CS2",
    "IO14": "DRDY1", "IO8": "DRDY2", "IO15": "START", "IO16": "ADS_RESET", "IO17": "ADS_PWDN",
    "IO1": "VBAT_SENSE", "IO4": "LED_G", "IO5": "LED_B",
    "IO38": "I2C_SDA", "IO39": "I2C_SCL", "IO40": "ACC_INT",
    "USB_D-": "USB_DN", "USB_D+": "USB_DP"}, B, "ESP32-S3-WROOM-1U-N8")
C("10uF", "3V3", "GND", B, FP_C0805)
C("100nF", "3V3", "GND", B)
R("10k", "3V3", "ESP_EN", B)                # EN RC reset (Espressif hardware design guidelines)
C("1uF", "ESP_EN", "GND", B)
add("SW", "Switch:SW_Push", "RESET", "Button_Switch_SMD:SW_SPST_TL3342", {"#1": "ESP_EN", "#2": "GND"}, B)
R("10k", "3V3", "BOOT", B)
add("SW", "Switch:SW_Push", "BOOT", "Button_Switch_SMD:SW_SPST_TL3342", {"#1": "BOOT", "#2": "GND"}, B)
R("1k", "LED_G", "LED_G_A", B)
add("D", "Device:LED", "green (streaming)", FP_LED, {"#2": "LED_G_A", "#1": "GND"}, B)
R("1k", "LED_B", "LED_B_A", B)
add("D", "Device:LED", "blue (Wi-Fi)", FP_LED, {"#2": "LED_B_A", "#1": "GND"}, B)
add("U", "Sensor_Motion:LIS3DH", "LIS3DH (I2C 0x18)", "Package_LGA:LGA-16_3x3mm_P0.5mm_LayoutBorder3x5y", {
    "VDD": "3V3", "VDD_IO": "3V3", "GND": "GND", "SPC": "I2C_SCL", "SDI": "I2C_SDA", "SDO": "ACC_SA0",
    "CS": "3V3", "INT1": "ACC_INT"}, B, "LIS3DHTR")
C("100nF", "3V3", "GND", B)
C("10uF", "3V3", "GND", B, FP_C0805)
R("10k", "ACC_SA0", "GND", B)             # SA0 low -> I2C address 0x18
R("4.7k", "3V3", "I2C_SDA", B)
R("4.7k", "3V3", "I2C_SCL", B)

# ------------------------------------------------------------------ ADS1299 x 2 --------------------------------------
for chip in (1, 2):
    B = f"ADS1299 #{chip} (ch {8 * chip - 7}-{8 * chip})"
    p = {"AVDD": "AVDD", "AVDD1": "AVDD", "AVSS": "AVSS", "AVSS1": "AVSS", "DVDD": "3V3", "DGND": "GND",
         "VREFP": f"VREFP{chip}", "VREFN": "AVSS", "VCAP1": f"VCAP1_{chip}", "VCAP2": f"VCAP2_{chip}",
         "VCAP3": f"VCAP3_{chip}", "VCAP4": f"VCAP4_{chip}",
         "RESV1": "GND",                                  # datasheet: connect RESV1 directly to DGND
         "DAISY_IN": "GND",                               # datasheet: tie to DGND when not daisy-chaining
         "CLKSEL": f"CLKSEL{chip}", "CLK": "ADS_CLK",
         "SCLK": "SCLK", "DIN": "MOSI", "DOUT": "MISO", "~{CS}": f"CS{chip}", "~{DRDY}": f"DRDY{chip}",
         "START": "START", "~{RESET}": "ADS_RESET", "~{PWDN}": "ADS_PWDN",
         "SRB1": "SRB",                                   # reference to every negative input (MISC1.SRB1 = 1)
         "GPIO1": f"GPIO1_{chip}", "GPIO2": f"GPIO2_{chip}", "GPIO3": f"GPIO3_{chip}", "GPIO4": f"GPIO4_{chip}"}
    for ch in range(1, 9):
        p[f"IN{ch}P"] = f"CH{(chip - 1) * 8 + ch}"
        p[f"IN{ch}N"] = "SRB"                             # referential montage, datasheet Fig. 73
    if chip == 1:   # bias drive amplifier (datasheet Fig. 68: 1 MOhm || 1.5 nF between BIASINV and BIASOUT)
        p.update({"BIASOUT": "BIAS_OUT", "BIASIN": "BIAS_OUT", "BIASINV": "BIAS_INV", "BIASREF": "AVSS"})
    else:           # unused bias amp: power down, float BIASOUT/BIASINV, BIASIN + BIASREF to AVSS (datasheet 10.1.1)
        p.update({"BIASIN": "AVSS", "BIASREF": "AVSS"})
    add("U", "Analog_ADC:ADS1299", f"ADS1299 #{chip}", "Package_QFP:TQFP-64_10x10mm_P0.5mm", p, B, "ADS1299IPAGR")
    # reference + internal regulator caps (datasheet pin table; same values on Cyton)
    C("10uF", f"VREFP{chip}", "AVSS", B, FP_C0805)
    C("100nF", f"VREFP{chip}", "AVSS", B)
    C("100uF", f"VCAP1_{chip}", "AVSS", B, FP_C1206)
    C("1uF", f"VCAP2_{chip}", "AVSS", B)
    C("1uF", f"VCAP3_{chip}", "AVSS", B)
    C("100nF", f"VCAP3_{chip}", "AVSS", B)
    C("1uF", f"VCAP4_{chip}", "AVSS", B)
    # supply decoupling: 1 uF per AVDD pin to AVSS (datasheet), 1 uF + 100 nF on DVDD
    for _ in range(3):
        C("1uF", "AVDD", "AVSS", B)
    C("100nF", "AVDD", "AVSS", B)
    C("1uF", "3V3", "GND", B)
    C("100nF", "3V3", "GND", B)
    # mode pin + unused GPIOs through >= 10k (datasheet note 1); chip 1 = internal clock master, chip 2 = external
    R("10k", f"CLKSEL{chip}", "3V3" if chip == 1 else "GND", B)
    for g in range(1, 5):
        R("10k", f"GPIO{g}_{chip}", "GND", B)

B = "ADS1299 #1 (ch 1-8)"
R("1M", "BIAS_INV", "BIAS_OUT", B)
C("1.5nF", "BIAS_INV", "BIAS_OUT", B)

# ------------------------------------------------------------------ electrode inputs ---------------------------------
B = "Electrode inputs + protection"
hdr = {f"#{i}": f"E{i}" for i in range(1, 17)}
hdr.update({"#17": "E_SRB", "#18": "E_BIAS", "#19": "GND", "#20": "GND"})
add("J", "Connector_Generic:Conn_02x10_Odd_Even", "EEG harness (16 ch + SRB + BIAS + 2 GND)",
    "Connector_IDC:IDC-Header_2x10_P2.54mm_Vertical", hdr, B)
# per input, as Cyton: bidirectional TVS at the connector, 2.2 kOhm series, 1 nF to ground at the ADC pin
for i in range(1, 17):
    add("D", "Device:D_TVS", "TVS bidir 5.5 V (e.g. PESD5V0S1BL)", FP_TVS, {"#1": f"E{i}", "#2": "GND"}, B)
    R("2.2k", f"E{i}", f"CH{i}", B)
    C("1nF", f"CH{i}", "GND", B)
add("D", "Device:D_TVS", "TVS bidir 5.5 V", FP_TVS, {"#1": "E_SRB", "#2": "GND"}, B)
R("2.2k", "E_SRB", "SRB", B)
C("1nF", "SRB", "GND", B)
add("D", "Device:D_TVS", "TVS bidir 5.5 V", FP_TVS, {"#1": "E_BIAS", "#2": "GND"}, B)
R("2.2k", "BIAS_OUT", "E_BIAS", B)

# ------------------------------------------------------------------ mechanical --------------------------------------
B = "Mechanical"
for _ in range(4):
    add("H", "Mechanical:MountingHole", "M2.5", "MountingHole:MountingHole_2.7mm_M2.5", {}, B)
