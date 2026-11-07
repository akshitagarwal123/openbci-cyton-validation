# BrainTech-8 (rev B): KiCad project and libraries

Open `braintech8.kicad_pro` in KiCad 10. It holds an empty schematic (`braintech8.kicad_sch`) and an empty 4-layer board (`braintech8.kicad_pcb`).

## What is set up

| Item | Setting | Where it came from |
|---|---|---|
| Copper layers | F.Cu · In1.Cu named **GND** · In2.Cu named **PWR** · B.Cu | The stack-up lesson: one solid ground on layer 2, power areas on layer 3 |
| Design rules and net classes | Copied from rev A (JLCPCB 4-layer: 0.15 mm clearance, 0.3 mm copper to edge, …) | `hardware/kicad/braintech16.kicad_pro` |
| Symbol libraries | All KiCad 10 built-in libraries, plus the project library **BrainTech** | `sym-lib-table` → `lib/BrainTech.kicad_sym` |
| Footprint libraries | All KiCad 10 built-in libraries, plus the project library **BrainTech** (empty for now) | `fp-lib-table` → `lib/BrainTech.pretty/` |

Not set yet (week 4 tasks): board outline, the layer stack-up thicknesses, and the final JLCPCB rule check.

## Which symbol and footprint each part uses

`Lib:Name` means library and item name, as KiCad's "Choose Symbol" and "Choose Footprint" windows show them. **Check** marks something to confirm before ordering.

| Ref | Part | Symbol | Footprint | LCSC | Check |
|---|---|---|---|---|---|
| U1 | ADS1299IPAGR | `Analog_ADC:ADS1299` | `Package_QFP:TQFP-64_10x10mm_P0.5mm` | C476817 | |
| U2 | ESP32-S3-MINI-1-N8 | `RF_Module:ESP32-S3-MINI-1` | `RF_Module:ESP32-S2-MINI-1` | look up | **KiCad has no S3-MINI-1 footprint; the symbol points to the S2-MINI-1 one. Compare every pad and the antenna keep-out with the ESP32-S3-MINI-1 datasheet, or make a BrainTech footprint.** |
| D1–D3 | TPD4E1B06DCKR | `BrainTech:TPD4E1B06DCK` | `Package_TO_SOT_SMD:SOT-363_SC-70-6` | C840093 | Pin numbers against the TI datasheet (done once in rev A) |
| U3 | MCP73831-2-OT (4.2 V charger) | `Battery_Management:MCP73831-2-OT` | `Package_TO_SOT_SMD:SOT-23-5` | C424093 | |
| U4 | TLV62569DBV (3.3 V buck) | `Regulator_Switching:TLV62569DBV` | `Package_TO_SOT_SMD:SOT-23-5` | C141836 | That the LCSC part is the DBV (SOT-23-5) version |
| L1 | FNR4020S2R2MT (2.2 µH) | `Device:L` | `Inductor_SMD:L_Changjiang_FNR4020S` | C167825 | |
| U5 | LP5907MFX-2.5 (+2.5 V) | `Regulator_Linear:LP5907MFX-2.5` | `Package_TO_SOT_SMD:SOT-23-5` | C165132 | |
| U6 | ADP7182AUJZ-2.5 (−2.5 V) | `Regulator_Linear:ADP7182AUJZ-2.5` | `Package_TO_SOT_SMD:TSOT-23-5` | C462196 | |
| U7 | LM2776 (charge pump) | `Regulator_SwitchedCapacitor:LM2776` | `Package_TO_SOT_SMD:SOT-23-6` | C69527 | |
| J1 | Electrode connector, JST SH 12-pin | `Connector_Generic:Conn_01x12` | `Connector_JST:JST_SH_SM12B-SRSS-TB_1x12-1MP_P1.00mm_Horizontal` | look up | Pin count is still a proposal (8 inputs, SRB, BIAS, 2 × GND) |
| J2 | USB-C, 16-pin | `Connector:USB_C_Receptacle_USB2.0_16P` | `Connector_USB:USB_C_Receptacle_GCT_USB4105-xx-A_16P_TopMnt_Horizontal` | look up | Choose the exact receptacle first, then match its footprint |
| J3 | Battery, JST SH 2-pin | `Connector_Generic:Conn_01x02` | `Connector_JST:JST_SH_SM02B-SRSS-TB_1x02-1MP_P1.00mm_Horizontal` | look up | Polarity: LiPo packs are not all wired the same way |
| R, C | Resistors and capacitors | `Device:R`, `Device:C` | `Resistor_SMD:R_0402_1005Metric`, `Capacitor_SMD:C_0402_1005Metric` (0603/0805/1206 for 10 µF and 100 µF) | per value | 10 µF in 0603 or larger (capacitance drops with voltage in small packages) |
| D | Status LEDs | `Device:LED` | `LED_SMD:LED_0603_1608Metric` | look up | |
| SW, Q | Power switch, BOOT/RESET buttons, ideal-diode MOSFET | to choose | to choose | | Pick the parts first, then their footprints |

## How to check a footprint (do this for every row marked Check)

1. Open the part's datasheet at its "recommended land pattern" or "package outline" drawing.
2. In KiCad, open the Footprint Editor, load the footprint, and compare pad size, pitch, pin 1 position and the overall outline.
3. For the ESP32, also compare the antenna keep-out area.
4. If anything differs, copy the footprint into `BrainTech.pretty`, fix it there, and point the symbol at the copy.
