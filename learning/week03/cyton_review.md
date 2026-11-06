# Cyton review: problems and weak spots

A review of the OpenBCI Cyton (with the Daisy) for lessons to carry into BrainTech-8. Every item gives its evidence. **Verified** means it was read directly from a source. **Check** means it is reasoning from the sources that still needs a measurement or a datasheet lookup before you rely on it.

Sources: OpenBCI's published Cyton schematic (`OBCI_V3_32bit-Schematic.jpg`, titled "OpenBCI Draft_03"), the rev C bill of materials, the V4 placement file (`positions.csv`), the open-source Cyton firmware, and TI's ADS1299 datasheet SBAS499C.

These are not claims that the Cyton is a bad board. It works and is widely used. They are the places where it departs from the datasheet, where it is limited, or where its documents disagree.

## A. Departures from the ADS1299 datasheet

| # | Problem | Evidence | Why it matters | For BrainTech-8 |
|---|---|---|---|---|
| A1 | **Supply capacitors on the bottom, through vias.** All eight analog supply capacitors (C13, C17, C18, C21, C22, C24, C27, C28) sit on the bottom, under the chip. | Verified: placement file. Datasheet Figure 78 note (p.72): place them close, on the same layer, with no vias. | Each via adds inductance, so the capacitors are less effective against the fastest current spikes. | Put the pin capacitors on the same side as the chip if space allows. If not, use short, multiple vias. |
| A2 | **No dedicated capacitors on AVDD1/AVSS1 (pins 54, 53) or the charge-pump pins (59, 58).** They join the main AVDD/AVSS wires and share the group above. | Verified: schematic. Datasheet pin table (p.6) asks for 1 µF on each. | The charge-pump pins carry switching spikes at the clock frequency. A capacitor right at those pins keeps the spikes local. | Give pins 59/58 and 54/53 their own 1 µF each. |
| A3 | **AVDD1/AVSS1 star connection not visible.** The datasheet asks to join AVDD1 to AVDD (and AVSS1 to AVSS) at one point (p.70). The schematic just ties them to the same wire. | Verified: schematic. Check: the copper layout, which is not published as a netlist. | Without a single join point, the charge pump's spikes can travel along the shared analog supply. | Draw it as a star point, or a net tie, in your schematic and route it that way. |
| A4 | **VCAP1 is a 100 µF X5R ceramic** (Yageo CC1206MKX5R5BB107, C2). | Verified: BOM and schematic. Datasheet p.70: X7R/X5R are piezoelectric; prefer C0G or tantalum where there is vibration. | A headset moves. Vibration on VCAP1 becomes noise on the reference, so it ends up in every sample. | Decide: C0G is not available at 100 µF, so tantalum, or accept X5R and test with tapping. |
| A5 | **Bias network differs from TI's example.** TI Figure 68 puts 1 MΩ ∥ 1.5 nF in the feedback path (BIASINV to BIASOUT). The Cyton puts R5 1 MΩ ∥ C16 1 nF in series between BIASOUT and the bias electrode, and takes BIASINV only to a header pin. | Verified: schematic and datasheet p.33, p.63. Check: the effect on loop stability, which the datasheet says depends on the system. | It changes how strongly and how fast the bias loop works. TI's typical values are not used. | Choose one network and add test pads on BIASIN, BIASINV and BIASREF so rev B can change it. |
| A6 | **Ground plane is not next to the parts.** The Cyton's order is Top (signals) / Layer 2 (a plane cut into several areas, plus a few traces) / Layer 3 (solid ground) / Bottom (signals). One Layer 2 cut runs right under the ADS1299. | Verified: OpenBCI's Top, Layer 2, Layer 3 and Bottom copper Gerbers. J2's AGND pin connects to Layer 3 (thermal spokes) and not to Layer 2. Check: which rail each Layer 2 area carries, which the files do not name. | Top-layer traces use the split Layer 2 as their nearest plane, so fast return currents must jump across cuts through capacitors or down to ground. The EEG signals are slow, so this matters most for fast digital lines and the radio. | Use Top / solid ground / power / Bottom: one unbroken ground on Layer 2, under your parts. |

## B. Limitations

| # | Problem | Evidence | Why it matters | For BrainTech-8 |
|---|---|---|---|---|
| B1 | **Signal sign is flipped.** SRB2 can only connect to the P input, so the reference goes on P and the electrodes on N. The chip measures reference − electrode. | Verified: datasheet Fig. 18 and the CHnSET register; Cyton default SRB2 on. | Every EEG trace comes out upside down unless software flips it. Easy to miss when comparing with other systems. | You chose SRB2: flip the sign in firmware or software, and document it. |
| B2 | **With the Daisy, each 16-channel frame is sent at 125 Hz.** The radio sends channels 1–8 and 9–16 in alternating packets, each averaging two samples. | Verified: Cyton firmware. | The effective rate for 16 channels is half the 250 Hz rate, and averaging adds a little smoothing. | The ESP32-S3's Wi-Fi has much more bandwidth. Make sure your packet format carries every sample. |
| B3 | **The radio module is discontinued.** The Cyton BOM lists the RFD22301 (RFduino). RS lists it as a discontinued product. | Verified: BOM; RS listing. | The board cannot be built as designed from new parts. | Not a problem for you: the ESP32-S3 replaces it. |
| B4 | **Little supply headroom near the end of the battery.** The battery goes through a series diode (D9) and then the 3.3 V LDO (MCP1754). The +2.5 V LDO and the charge pump run from that 3.3 V. | Verified: schematic topology. Check: the exact diode drop and LDO dropout at the real load current. | A Schottky diode typically drops a few hundred millivolts, and the LDO needs its own dropout on top. So the 3.3 V rail likely falls out of regulation while the LiPo still has charge left. | Measure the 3.3 V rail as the battery runs down. Your buck converter avoids most of this. |
| B5 | **AC lead-off frequency sits inside the EEG band.** The firmware configures AC lead-off at 31.2 Hz, 6 nA. | Verified: firmware; the datasheet lists 7.8 Hz, 31.2 Hz and fDR/4 as options. | If AC lead-off is turned on during a recording, its 31.2 Hz excitation lands in the beta/gamma band. | Use lead-off checks before recording, or use fDR/4, which is above the band you keep. |

## C. Documentation problems

| # | Problem | Evidence | Why it matters |
|---|---|---|---|
| C1 | **The published schematic is a draft.** Its title block reads "OpenBCI Draft_03", and it contains leftover notes: "SWITCH THIS TO TCM828" next to the LM2664 inverter, and "CHECK AGAINST DS" next to RESV1 (pin 31). | Verified: schematic. | A draft may not match the shipped board, as C2 shows. |
| C2 | **The 3.3 V regulator doesn't match between files.** The layout file names the U5 footprint "LP5907", but the rev C BOM lists the MCP1754. | Verified: layout file and BOM. | You can't be sure which part a given board carries without checking the board itself. |
| C3 | **RESV1 (pin 31).** The datasheet says to connect it directly to DGND (p.6). The Cyton ties it to its single ground (AGND), which is the same net there because DGND joins AGND. | Verified: schematic. | Not a fault on the Cyton, but the unresolved note in C1 shows it was never checked. |

## What to carry into BrainTech-8

1. Same-side pin capacitors where possible (A1), with their own capacitors on pins 59/58 and 54/53 (A2), and a drawn star point for AVDD1/AVSS1 (A3).
2. A deliberate choice of VCAP1 dielectric (A4) and bias network (A5), with test pads to change your mind.
3. Firmware that handles the SRB2 sign flip (B1) and sends every sample (B2).
4. Measure the supply rails across the whole battery range (B4).
5. Keep one schematic and one BOM that agree, with no leftover notes (C1, C2).
