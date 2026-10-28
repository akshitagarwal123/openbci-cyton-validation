# ESP32 RC filter test rig: breadboard wiring

Breadboard vertical, USB end at the top, ESP32 DevKit V1 (38-pin) in rows 1–19, right-hand pins in column **i**, free hole **j** beside each pin.
Right header from the USB end: 5V, CMD, SD3, SD2, G13, **GND (row 6)**, G12, G14, G27, G26, **G25 (row 11)**, G33, G32, **G35 (row 14)**, **G34 (row 15)**, VN, VP, EN, 3V3.

| # | From | To | Part |
|---|---|---|---|
| 1 | j6 (GND) | right − rail | black jumper |
| 2 | j11 (G25, DAC sine out) | f30 | jumper |
| 3 | j14 (G35, ADC in) | g30 | jumper |
| 4 | j15 (G34, ADC out) | g34 | jumper |
| 5 | h30 | h34 | 10 kΩ resistor (brown-black-orange) |
| 6 | i34 | − rail, row 36 | 0.47 µF capacitor (474); electrolytic: long leg in i34 |

**Connected (same metal strip):** row 30 f–j = input node (G25, G35, resistor top); row 34 f–j = output node (resistor bottom, capacitor, G34); the whole − rail column (GND, capacitor); each pin's row f–j (pin + its jumper).
**Not connected:** a–e vs f–j of the same row (centre gap); row 30 vs row 34 except through the resistor; − rail vs + rail; top and bottom of a rail if the rail is split in the middle.
Row numbers shift if the ESP32 sits lower: count pins from the USB end and use that pin's own row.
