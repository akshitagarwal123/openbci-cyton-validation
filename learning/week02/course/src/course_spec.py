"""The Cyton + Daisy course: chapters, narration (as shown in captions) and the shots for each scene.

Shot keys: at (fraction of the scene), cam, focus, keep, flows, labels [[part, text]], daisy ('off'|'lifted'|'stacked'|'lift'), sch (schematic crop id), fadeD.
cam: 'overC' Cyton overview orbit, 'over' Cyton+Daisy orbit, 'top', 'bot', 'part' (uses focus), 'side', 'pair', 'j1', 'all'.
"""
import json, re, os

S = lambda at, **k: dict(at=at, **k)
CH = []

def chapter(title, scenes): CH.append({"title": title, "scenes": scenes})
def scene(text, *shots): return {"text": " ".join(text.split()), "shots": list(shots)}

# ---------------------------------------------------------------- 1
chapter("What the Cyton + Daisy does", [
 scene("""Welcome. In this course we'll take the OpenBCI Cyton board, and its add-on, the Daisy module, apart, piece by piece.
 Together they turn the tiny electrical activity of your brain into numbers on your computer: 8 channels with the Cyton alone, 16 with the Daisy.
 You don't need any electronics background. We'll use a 3D model built from OpenBCI's own design files, plus the real schematics,
 and follow the electricity as it flows through the boards.""",
  S(0, cam="over", daisy="lift", labels=[["U7", "Cyton: channels 1–8"]]),
  S(0.6, cam="over", daisy="lifted", labels=[["U7", "Cyton: channels 1–8"], ["Daisy U1", "Daisy: channels 9–16"]])),
 scene("""Here's the big picture. Electrodes on your scalp pick up voltages of just 10 to 100 microvolts,
 tens of thousands of times smaller than the voltage of an AA battery. The Cyton protects those signals, amplifies them,
 turns them into numbers 250 times a second, and sends them by radio to a USB dongle on your computer.
 We'll follow five flows: power, the brain signal, the bias loop, the digital control, and the radio.
 Then we'll add the Daisy, and see how two boards stay perfectly in sync.""",
  S(0, cam="overC", daisy="off", flows=["signal"], labels=[["HEAD", "your head"], ["PC", "your computer"]]),
  S(0.55, cam="overC", daisy="off", flows=["signal", "power", "bias"], labels=[])),
])

# ---------------------------------------------------------------- 2
chapter("A tour of the board", [
 scene("""The Cyton is an octagon about 6 centimetres across, with parts on both sides. Let's start on top.
 Along the top edge is the electrode header, a double row of right-angle pins where your electrode wires plug in.
 Just below it are small black resistor arrays, part of the protection on every channel.""",
  S(0, cam="top", daisy="off", labels=[["PL1", "electrode header"]]),
  S(0.55, cam="part", focus="R2", daisy="off", labels=[["R2", "resistor array"], ["PL1", "electrode header"]])),
 scene("""In the middle sits the most important chip: the ADS1299 from Texas Instruments.
 It's an 8-channel amplifier and analog-to-digital converter, designed specifically for EEG.
 Around it are lots of small capacitors that keep its power supplies and its internal reference steady.""",
  S(0, cam="part", focus="U6", daisy="off", labels=[["U6", "ADS1299"], ["C2", "100 µF capacitor"]])),
 scene("""Below it is the PIC32 microcontroller, the board's brain, with its 8 megahertz crystal next to it.
 Two small buttons, RST and PROG, let you restart it or load new firmware, and a blue LED shows its status.""",
  S(0, cam="part", focus="U7", daisy="off", labels=[["U7", "PIC32"], ["X1", "8 MHz crystal"]]),
  S(0.5, cam="part", focus="SW3", daisy="off", labels=[["SW3", "RST"], ["SW1", "PROG"], ["D1", "blue LED"]])),
 scene("""Around the edges are black sockets. J1, on the left, is the Daisy port. J3 and J4 bring out spare pins of the microcontroller.
 Near the bottom is a tiny accelerometer that measures head movement, and next to it an even tinier logic chip, an OR gate, that we'll meet later.""",
  S(0, cam="top", daisy="off", labels=[["J1", "J1 · Daisy port"], ["J3", "J3"], ["J4", "J4"]]),
  S(0.5, cam="part", focus="U1", daisy="off", labels=[["U1", "accelerometer"], ["U2", "OR gate"]])),
 scene("""Now flip the board over. On the underside are the battery plug, the power supply chips, the radio module, and the micro SD card slot.
 Right under the electrode pins you'll also find more protection parts: TVS diodes and capacitor arrays.""",
  S(0, cam="bot", daisy="off", labels=[["B1", "battery plug"], ["BLE1", "radio"], ["CONN1", "micro SD"]]),
  S(0.5, cam="bot", daisy="off", labels=[["U5", "3.3 V regulator"], ["U3", "inverter"], ["VR1", "−2.5 V regulator"], ["D3", "TVS diodes"]])),
 scene("""On one edge is the slide switch, with three positions: PC, OFF and BLE.
 The schematic, the circuit diagram OpenBCI published, groups all these parts into the same blocks:
 power supply, input protection, the ADS1299, the microcontroller, the radio, the SD card and the accelerometer.
 We'll go through them one flow at a time.""",
  S(0, cam="part", focus="SW2", daisy="off", labels=[["SW2", "slide switch: PC · OFF · BLE"]]),
  S(0.3, cam="overC", daisy="off", sch="full", labels=[])),
 scene("""A quick word on how to read a schematic. Each chip is drawn as a box with its pins numbered around the edge.
 Lines are wires. A dot where lines cross means they're connected; no dot, no connection.
 Instead of drawing every long wire, the schematic often uses names, like DVDD or MISO: every point with the same name is connected, even if it's on the other side of the page.
 Parts have reference names, like U6 or R5, and the same name is printed next to the part on the board. That's how you match the drawing to the real thing.""",
  S(0, cam="part", focus="U6", daisy="off", sch="ads", labels=[["U6", "U6 on the board = U6 in the schematic"]])),
 scene("""Underneath the white surface, the Cyton has four layers of copper: one on top, two inside, and one on the bottom.
 The copper traces are the wires from the schematic. Switch the 3D explorer to copper routing, and you can see them:
 red for the top layer, cyan for the bottom. Tiny plated holes, called vias, carry signals from one layer to another.""",
  S(0, cam="overC", daisy="off", copper=True, labels=[["U6", "copper traces"]]),
  S(0.55, cam="bot", daisy="off", copper=True, labels=[["U5", "bottom copper"]])),
])

# ---------------------------------------------------------------- 3
chapter("Power: from battery to ±2.5 V", [
 scene("""Everything starts at the battery plug, B1, on the underside. The Cyton runs from a battery of 3 to 6 volts only, never from the mains.
 That's a safety choice: anything connected to your head should be isolated from the wall socket.""",
  S(0, cam="part", focus="B1", daisy="off", flows=["power"], labels=[["B1", "battery: 3–6 V"]])),
 scene("""The first part after the battery is D9, a diode. A diode is a one-way valve for current.
 If you plug the battery in backwards, D9 blocks it, and nothing gets damaged. The price is a small drop of about 0.3 volts.
 What comes out is called RAW.""",
  S(0, cam="part", focus="D9", daisy="off", flows=["power"], sch="power", labels=[["D9", "one-way valve"]])),
 scene("""RAW goes to U5, a 3.3 volt regulator. A regulator takes a voltage that wanders, as the battery drains,
 and turns it into a perfectly steady one. Its output, DVDD, powers all the digital parts: the microcontroller, the radio,
 the accelerometer, the SD card, and the digital side of the ADS1299.
 A nice detail: the power switch doesn't carry the board's current at all. It only drives U5's enable pin, which switches the regulator, and the whole board, on and off.""",
  S(0, cam="part", focus="U5", daisy="off", flows=["power"], sch="power", labels=[["U5", "3.3 V regulator → DVDD"]]),
  S(0.72, cam="part", focus="SW2", daisy="off", flows=["power"], labels=[["SW2", "drives U5's enable pin"]])),
 scene("""The ADS1299's analog side needs two more supplies. U4 makes plus 2.5 volts, called AVDD.
 It's fed from the already clean 3.3 volts, so AVDD is extra quiet.""",
  S(0, cam="part", focus="U4", daisy="off", flows=["power"], sch="power", labels=[["U4", "+2.5 V → AVDD"]])),
 scene("""The analog side also needs minus 2.5 volts, and a battery can't give you a negative voltage directly. That's U3's job.
 It's a charge pump: thousands of times a second, it charges a small capacitor from 3.3 volts, flips it upside down,
 and pours that charge into its output. The result is about minus 3.3 volts.""",
  S(0, cam="part", focus="U3", daisy="off", flows=["power"], sch="power", labels=[["U3", "charge pump → about −3.3 V"]])),
 scene("""That flipped voltage is a bit rippled, so VR1, a negative regulator, cleans it into a steady minus 2.5 volts, called AVSS.
 Now the ADS1299 has plus and minus 2.5 volts: 5 volts in total, centred on zero.
 Centring on zero means the brain signal, which swings both ways around zero, sits right in the middle of the chip's range.""",
  S(0, cam="part", focus="VR1", daisy="off", flows=["power"], sch="power", labels=[["VR1", "−2.5 V → AVSS"]]),
  S(0.6, cam="part", focus="U6", daisy="off", flows=["power"], labels=[["U6", "AVDD +2.5 V · AVSS −2.5 V"]])),
 scene("""Next to every regulator you'll see small capacitors. Think of them as little water tanks:
 when a chip suddenly gulps current, the capacitor supplies it instantly, so the voltage doesn't dip. Regulators also need them to stay stable.
 In the schematic, this whole chain sits in the power supply block, at the top left.""",
  S(0, cam="bot", daisy="off", flows=["power"], sch="power", labels=[["C39", "capacitor"], ["C40", "capacitor"], ["U5", "U5"]])),
 scene("""Why so many separate supplies? Because digital chips are noisy. Every time the microcontroller or the radio switches,
 it pulls quick spikes of current, and those spikes ripple along its supply. If the ADS1299's analog side shared that supply,
 the ripple would land right on top of your microvolt brain signals. So the analog side gets its own, extra-clean rails, AVDD and AVSS,
 made by their own low-noise regulators, while the digital parts share DVDD. Keeping analog and digital apart is one of the golden rules of EEG design.""",
  S(0, cam="overC", daisy="off", flows=["power"], labels=[["U6", "analog: AVDD · AVSS"], ["U7", "digital: DVDD"]])),
])

# ---------------------------------------------------------------- 4
chapter("The brain signal", [
 scene("""Now the main event: the brain signal. Each EEG electrode measures the voltage at one spot on your scalp.
 But a voltage only means something compared with another point, so every channel is measured against a shared reference electrode,
 usually on your earlobe. That reference connects to the pin called SRB.""",
  S(0, cam="part", focus="HEAD", daisy="off", flows=["signal"], labels=[["HEAD", "electrodes + reference"]])),
 scene("""The electrode wires plug into the header. Each channel has two pins, P and N, in the two rows.
 Then there's SRB, the reference, and BIAS, which we'll meet in the next chapter.
 At the two ends sit small sockets for the analog supplies, which the Daisy uses later.""",
  S(0, cam="part", focus="PL1", daisy="off", flows=["signal"], sch="input", labels=[["PL1", "channels 1–8 · SRB · BIAS"]])),
 scene("""From each pin, the signal first meets a TVS diode, on the underside, right below the pins. TVS stands for transient voltage suppressor.
 Normally it does nothing at all. But if you touch the pins with a static charge of thousands of volts,
 it switches on in nanoseconds and dumps that zap to ground, before it can reach the delicate chip.""",
  S(0, cam="part", focus="D3", daisy="off", flows=["signal"], sch="prot", labels=[["D3", "TVS diodes · underneath"]])),
 scene("""Next, through the board to the top: a 2.2 kΩ resistor. Four resistors are packed into each of these tiny black arrays.
 If something still gets past the diode, the resistor limits how much current can flow into the chip's input.""",
  S(0, cam="part", focus="R2", daisy="off", flows=["signal"], sch="prot", labels=[["R2", "2.2 kΩ × 4 · on top"]])),
 scene("""Then back underneath: a 1 nF capacitor from each line to ground. Together with the 2.2 kΩ resistor, it forms a filter with a cutoff around 72 kilohertz.
 Brain signals are below 100 hertz, so they pass untouched, but radio noise from Wi-Fi and phones is drained away.
 Notice the zig-zag: diode underneath, resistor on top, capacitor underneath. The signal hops through the board twice.""",
  S(0, cam="part", focus="C9", daisy="off", flows=["signal"], sch="prot", labels=[["C9", "1 nF × 4 · underneath"]])),
 scene("""And now the signal reaches the ADS1299. For each of the 8 channels, the chip first takes the difference between the electrode and the reference,
 so the hum your whole body carries largely cancels out. Then a programmable gain amplifier multiplies that tiny difference by 24.""",
  S(0, cam="part", focus="U6", daisy="off", flows=["signal"], sch="ads", labels=[["U6", "subtract reference · gain ×24"]])),
 scene("""Why only 24, and not 1,000? Because electrodes also carry a slowly drifting offset, up to a few hundred millivolts.
 With a gain of 24, the chip's input range is plus or minus 187 millivolts, wide enough for that offset.
 And its 24-bit converter is so fine that one step is only about 0.02 microvolts. So we get both: room for the offset, and detail far below the brain signal.""",
  S(0, cam="part", focus="U6", daisy="off", flows=["signal"], sch="ads", labels=[["U6", "±187 mV range · 0.02 µV steps"]])),
 scene("""Next comes the analog-to-digital converter. All 8 channels are converted at exactly the same instant, 250 times a second, into 24-bit numbers.
 The converter needs a ruler to measure against: a 4.5 volt reference made inside the chip, held steady by capacitors on its VREF and VCAP pins,
 including C2, the big 100 µF one. When a new set of 8 samples is ready, the chip pulls a pin called DRDY, data ready, to say: come and get it.""",
  S(0, cam="part", focus="C2", daisy="off", flows=["signal"], sch="vref", labels=[["C2", "100 µF · VCAP1"], ["U6", "4.5 V reference inside"]]),
  S(0.7, cam="part", focus="U6", daisy="off", flows=["vdrdy"], labels=[["U6", "DRDY: data ready!"]])),
 scene("""The ADS1299 has a few more tricks. In front of each channel is a set of switches, called the input multiplexer.
 Normally it connects the electrode. But the firmware can also short a channel's inputs together to measure the chip's own noise,
 feed in a built-in test square wave to check everything works, or measure the chip's temperature and supply voltages.
 It also decides how the reference is used: with SRB2, the shared reference goes to each channel's P input separately, which is what the Cyton uses by default.
 With SRB1, it goes to all the N inputs at once.""",
  S(0, cam="part", focus="U6", daisy="off", sch="ads", labels=[["U6", "input switches · test signal · SRB1 / SRB2"]])),
 scene("""It can even check your electrodes. The chip sends a tiny current, 6 nanoamps, through each electrode, wobbling at 31.2 hertz.
 From the voltage that this creates, software works out how well each electrode touches your skin, using Ohm's law. That's the impedance check in the OpenBCI GUI.
 A good contact has low impedance; a poor one shows up as a big, noisy signal.""",
  S(0, cam="part", focus="HEAD", daisy="off", flows=["signal"], labels=[["HEAD", "6 nA at 31.2 Hz → impedance"]])),
 scene("""Finally, look at all the small capacitors gathered around the ADS1299, many of them right underneath it.
 Every power pin of the chip gets its own: usually a 1 µF and a 0.1 µF side by side, placed as close to the pin as possible.
 The big one stores energy, the small one reacts fastest. Without them, the chip's own switching would make its supply bounce, and that bounce would show up in your EEG.""",
  S(0, cam="part", focus="C24", daisy="off", sch="decoup", labels=[["C24", "decoupling capacitor"], ["C2", "100 µF"]])),
])

# ---------------------------------------------------------------- 5
chapter("The bias loop", [
 scene("""There's one problem left: mains hum. The power lines in your walls create a 50 or 60 hertz field, and your body picks it up like an antenna.
 That hum can be thousands of times bigger than your brain signal. Subtracting the reference removes most of it, but not all.
 The bias loop pushes it down even further.""",
  S(0, cam="part", focus="HEAD", daisy="off", flows=["bias"], labels=[["HEAD", "50 / 60 Hz hum on your body"]])),
 scene("""Inside the ADS1299, the electrode signals are averaged together. Brain signals differ from place to place, so they mostly cancel in the average.
 What's left is the hum that every electrode shares. A built-in bias amplifier then drives the opposite of that hum back into your body,
 through a separate electrode: the bias electrode.""",
  S(0, cam="part", focus="U6", daisy="off", flows=["bias"], labels=[["U6", "average → invert → drive"]])),
 scene("""On its way out, the bias drive passes R5, a 1 MΩ resistor, with C16, a 1 nF capacitor, across it.
 R5 limits the current into your body to a couple of microamps, even in the worst case. C16 lets faster changes, like the hum, get around R5.
 One detail from the schematic: the amplifier's minus input, BIAS_INV, isn't wired to anything else on the board. It's simply brought out to two pins, J2, so you can experiment.""",
  S(0, cam="part", focus="R5", daisy="off", flows=["bias"], sch="bias", labels=[["R5", "1 MΩ ‖ 1 nF (C16)"]]),
  S(0.72, cam="part", focus="J2", daisy="off", flows=["bias"], sch="bias", labels=[["J2", "BIAS_INV · AGND"]])),
 scene("""Then the drive passes a 2.2 kΩ protection resistor and a TVS diode, like every other line, and leaves through the BIAS pin to the bias electrode,
 often on the other earlobe or the forehead. The loop closes through you: the hum goes up on your body, and the amplifier pushes it back down. Every channel gets cleaner.""",
  S(0, cam="part", focus="R6", daisy="off", flows=["bias"], labels=[["R6", "2.2 kΩ"]]),
  S(0.35, cam="part", focus="D6", daisy="off", flows=["bias"], labels=[["D6", "TVS"]]),
  S(0.6, cam="part", focus="HEAD", daisy="off", flows=["bias"], labels=[["HEAD", "bias electrode"]])),
])

# ---------------------------------------------------------------- 6
chapter("The microcontroller", [
 scene("""Now the digital side. U7 is a PIC32 microcontroller: a tiny computer running OpenBCI's firmware.
 Its job is to collect samples from the ADS1299 and the accelerometer, pack them into packets, and hand them to the radio, or write them to the SD card.""",
  S(0, cam="part", focus="U7", daisy="off", sch="mcu", labels=[["U7", "PIC32 · runs the firmware"]])),
 scene("""It keeps time with X1, an 8 megahertz crystal: a sliver of quartz that vibrates at an exact frequency.
 The two tiny capacitors next to it, 18 pF each, help it start and settle. The chip multiplies this beat up to run its processor.
 Don't confuse it with the ADS1299's own clock: that one runs at 2.048 megahertz, inside the ADS1299, and it times the samples.""",
  S(0, cam="part", focus="X1", daisy="off", flows=["clock"], sch="mcu", labels=[["X1", "8 MHz crystal"], ["C20", "18 pF"], ["C23", "18 pF"]])),
 scene("""The microcontroller talks to the ADS1299 over SPI, a simple four-wire link. The microcontroller drives a clock wire, SCK.
 On each tick, one bit travels out on MOSI, and one bit comes back on MISO. A fourth wire, chip-select, picks which chip is listening.
 The SPI wires are shared with the accelerometer and the SD card, and each has its own chip-select:
 CS1 for the ADS1299, CS3 for the SD card, CS4 for the accelerometer, and CS2 for the Daisy.""",
  S(0, cam="side", daisy="off", flows=["vread1"], labels=[["U7", "SCK · MOSI · MISO"], ["U6", "CS1"]]),
  S(0.6, cam="overC", daisy="off", flows=["vread1", "motion", "storage"], labels=[["U6", "CS1"], ["CONN1", "CS3"], ["U1", "CS4"], ["J1", "CS2"]])),
 scene("""Every 4 milliseconds, the ADS1299 pulls DRDY low. That's a doorbell, wired to an interrupt on the microcontroller.
 It immediately pulls CS1 low and clocks out 27 bytes: 3 bytes of status, then 3 bytes for each of the 8 channels.""",
  S(0, cam="part", focus="U6", daisy="off", flows=["vdrdy"], labels=[["U6", "DRDY rings"]]),
  S(0.45, cam="part", focus="U7", daisy="off", flows=["vdrdy", "vread1"], labels=[["U7", "CS1: read 27 bytes"]])),
 scene("""Two buttons control the microcontroller. RST pulls its reset pin, MCLR, to ground to restart it. A 470 kΩ resistor holds that pin high the rest of the time.
 PROG, held while you reset, tells it to start its bootloader and wait for new firmware.
 And the blue LED, D1, shows the board's status. In the schematic, the microcontroller block shows all of this: chip-selects, crystal, buttons, and the serial link to the radio.""",
  S(0, cam="part", focus="SW3", daisy="off", flows=["controls"], sch="mcu", labels=[["SW3", "RST"], ["R7", "470 kΩ"]]),
  S(0.4, cam="part", focus="SW1", daisy="off", flows=["controls"], sch="mcu", labels=[["SW1", "PROG"], ["D1", "blue LED"]])),
 scene("""The PIC32 comes with a chipKIT bootloader, a small program that lets you load new firmware over USB through the dongle, using the Arduino software.
 Its spare pins are brought out on the two black sockets, J3 and J4, so you can connect your own add-ons, like a button or a trigger signal from another device.""",
  S(0, cam="part", focus="J4", daisy="off", labels=[["J4", "D17 · RST · D18 · D11"], ["J3", "D13 · D12 · VDD · GND"]])),
])

# ---------------------------------------------------------------- 7
chapter("Radio and packets", [
 scene("""Each packet the microcontroller builds is 33 bytes long: a start byte, a sample number, 24 bytes of channel data, 6 bytes of accelerometer data, and a stop byte.
 It sends each packet over a serial link to BLE1, an RFduino radio module on the underside.""",
  S(0, cam="part", focus="U7", daisy="off", flows=["vradio"], labels=[["U7", "33-byte packet"]]),
  S(0.55, cam="part", focus="BLE1", daisy="off", flows=["vradio"], sch="radio", labels=[["BLE1", "RFduino radio"]])),
 scene("""The RFduino transmits each packet wirelessly to the OpenBCI USB dongle, plugged into your computer. Every 4 milliseconds, a packet leaves the board.
 On the computer, software such as the OpenBCI GUI or BrainFlow turns the 24-bit numbers back into microvolts, and plots your brain waves.""",
  S(0, cam="part", focus="PC", daisy="off", flows=["vradio"], labels=[["PC", "USB dongle → OpenBCI GUI / BrainFlow"]])),
 scene("""The radio can also do something clever: it can reprogram the microcontroller over the air, using the programming pins, so you can update the firmware without any cables.
 And remember the slide switch? In the BLE position, it tells the radio to use Bluetooth. That signal comes straight from the battery,
 so it passes through D8 and a resistor, and a Zener diode, D10, clamps it to about 3 volts to protect the radio's input.""",
  S(0, cam="part", focus="BLE1", daisy="off", flows=["vradio"], sch="radio", labels=[["BLE1", "can reprogram the PIC32"]]),
  S(0.45, cam="part", focus="D8", daisy="off", flows=["controls"], sch="radio", labels=[["D8", "BLE enable"], ["SW2", "BLE · OFF · PC"]])),
 scene("""Let's do the maths on the data. 33 bytes per packet, 250 packets a second, makes 8,250 bytes every second.
 The serial link between the microcontroller and the radio runs at 115,200 bits per second, which is about 11,500 bytes a second.
 So the link is already about 70 percent full with 8 channels. That's exactly why 16 channels can't simply be sent at 250 per second, as we'll see with the Daisy.""",
  S(0, cam="part", focus="U7", daisy="off", flows=["vradio"], labels=[["U7", "33 × 250 = 8,250 bytes/s"], ["BLE1", "115,200 bit/s link"]])),
])

# ---------------------------------------------------------------- 8
chapter("Extras: motion and SD card", [
 scene("""The accelerometer, U1, measures how your head tilts and moves, in three directions.
 Its readings go into the 6 aux bytes of each packet, so software can spot movement that might spoil the EEG.""",
  S(0, cam="part", focus="U1", daisy="off", flows=["motion"], sch="accel", labels=[["U1", "x · y · z motion"]])),
 scene("""It shares the SPI wires, but this chip can also speak another protocol, I²C, and busy SPI traffic could accidentally look like an I²C start signal to it.
 So U2, a tiny OR gate, holds its data pin high whenever it isn't selected. It's like an earplug that's only removed when the microcontroller wants to talk to it.""",
  S(0, cam="part", focus="U2", daisy="off", flows=["motion"], sch="accel", labels=[["U2", "OR gate: the earplug"]])),
 scene("""The micro SD card slot, on the underside, lets the board record without a computer at all.
 It uses the same SPI wires, with its own chip-select, CS3. C4, a big 100 µF capacitor, covers the card's bursts of current while it writes.""",
  S(0, cam="part", focus="CONN1", daisy="off", flows=["storage"], sch="sd", labels=[["CONN1", "micro SD · CS3"], ["C4", "100 µF"]])),
])

# ---------------------------------------------------------------- 9
chapter("The Daisy: 8 more channels", [
 scene("""Now let's add the Daisy module. It's a second, smaller board that sits on top of the Cyton and adds 8 more channels: 9 to 16.
 It has its own ADS1299, its own protection parts and its own electrode header, but no microcontroller, no radio and no regulators. Everything else comes from the Cyton.""",
  S(0, cam="over", daisy="lift", labels=[["Daisy U1", "Daisy ADS1299"]]),
  S(0.6, cam="over", daisy="lifted", sch="dz_full", labels=[["Daisy U1", "Daisy ADS1299"], ["U7", "Cyton"]])),
 scene("""Here's the Daisy on its own. On top: its electrode header along the top edge, five resistor arrays under it, the ADS1299 in the middle,
 the 8-pin Daisy bus on the left edge, and two pads, J2, for the bias amplifier's minus input, just like on the Cyton.
 Underneath: TVS diodes and capacitor arrays below the pins, and the ADS1299's decoupling capacitors. Same building blocks, minus the digital side.""",
  S(0, cam="part", focus="Daisy U1", daisy="lifted", labels=[["Daisy U1", "ADS1299"], ["Daisy R2", "resistor array"], ["Daisy J1", "Daisy bus"]]),
  S(0.55, cam="part", focus="Daisy C14", daisy="lifted", labels=[["Daisy C14", "decoupling"], ["Daisy D3", "TVS diodes"]])),
 scene("""Both chips are identical, with identical settings: gain 24, 24-bit, 250 samples a second.
 The Cyton's chip handles channels 1 to 8, and the Daisy's chip handles channels 9 to 16.""",
  S(0, cam="pair", daisy="lifted", fadeD=0.35, keep=["U6", "Daisy U1"], labels=[["U6", "Cyton ADS1299 · ch 1–8"], ["Daisy U1", "Daisy ADS1299 · ch 9–16"]])),
 scene("""The extra electrodes plug into the Daisy's own right-angle header, which sits right above the Cyton's.
 Each line gets the same protection: TVS diode underneath, 2.2 kΩ resistor on top, 1 nF capacitor underneath, and then the Daisy's ADS1299.""",
  S(0, cam="part", focus="Daisy PL1", daisy="lifted", flows=["vsig"], labels=[["Daisy PL1", "Daisy header: channels 9–16"]]),
  S(0.45, cam="part", focus="Daisy D2", daisy="lifted", flows=["vsig"], labels=[["Daisy D2", "TVS · underneath"]]),
  S(0.7, cam="part", focus="Daisy U1", daisy="lifted", flows=["vsig"], labels=[["Daisy U1", "Daisy ADS1299"]])),
 scene("""The boards talk through 8 pins. The Daisy's pins point down into J1, the Cyton's black socket:
 3.3 volt power, ground, the three shared SPI wires, reset, a clock line, and CS2, the Daisy's own chip-select.""",
  S(0, cam="j1", daisy="lifted", flows=["daisybus"], keep=["J1", "Daisy J1"], sch="dz_bus", labels=[["J1", "Cyton J1 · 8-hole socket"], ["Daisy J1", "Daisy pins (pointing down)"]])),
 scene("""Analog power arrives another way. At the two ends of the Cyton's electrode header sit small 2-hole sockets for AVSS and AVDD.
 The Daisy's matching pins plug straight down into them, so both chips run on the very same plus and minus 2.5 volt supplies.""",
  S(0, cam="part", focus="Daisy PL1", daisy="lifted", flows=["daisypower"], labels=[["Daisy PL1", "AVSS · AVDD pins → Cyton sockets"]])),
 scene("""So how do two chips stay in sync? First: one clock. The Daisy's clock-select pin is tied to ground, so it has no clock of its own.
 When the firmware finds a Daisy, it turns on the Cyton chip's clock output, and both chips count the very same 2.048 megahertz ticks.
 8,192 ticks make one sample, so both finish every sample at the same instant.""",
  S(0, cam="side", daisy="lifted", fadeD=0.35, flows=["vclock"], keep=["U6", "Daisy U1"], panel="clock", labels=[["U6", "2.048 MHz out on CLK"], ["Daisy U1", "no clock of its own"]])),
 scene("""Second: one start. The microcontroller pulls both chip-selects low together and sends a single START command, which both chips hear at once.
 A shared reset line restarts them together, too. At start-up, it also reads the Daisy chip's ID through CS2. If the answer is 0x3E, the firmware switches to 16 channels.""",
  S(0, cam="side", daisy="lifted", fadeD=0.35, flows=["vstart"], keep=["U6", "Daisy U1"], panel="start", labels=[["U6", "START"], ["Daisy U1", "START"]])),
 scene("""Third: one doorbell. The Daisy's data-ready pin isn't connected to anything. When the Cyton chip rings data ready, the Daisy's sample is ready too,
 so the microcontroller reads 27 bytes with CS1, then 27 bytes with CS2.""",
  S(0, cam="side", daisy="lifted", fadeD=0.35, flows=["vdrdy", "vread"], keep=["U7"], panel="drdy", labels=[["U7", "CS1: 27 bytes, then CS2: 27 bytes"]])),
 scene("""The radio link can't carry 16 channels 250 times a second. So the firmware averages each pair of samples and takes turns:
 odd packets carry channels 1 to 8, even packets carry 9 to 16. Each channel arrives 125 times a second, and the software stitches them back together.""",
  S(0, cam="part", focus="BLE1", daisy="lifted", flows=["vradio"], panel="packets", labels=[["BLE1", "odd: ch 1–8 · even: ch 9–16"]])),
 scene("""Two practical notes. The Daisy has its own SRB and BIAS pins, separate from the Cyton's. For one reference across all 16 channels,
 join the two SRB pins with a Y-splitter cable. The Daisy's bias drive goes to its own BIAS pin: you can leave it unused, and let the Cyton's bias electrode serve all 16 channels.""",
  S(0, cam="part", focus="Daisy PL1", daisy="lifted", labels=[["Daisy PL1", "own SRB and BIAS pins"]])),
])

# ---------------------------------------------------------------- 10
chapter("Putting it together", [
 scene("""Let's put it all together, with every flow running at once. Power: battery, D9, 3.3 volts, then plus and minus 2.5 volts.
 Signal: electrode, protection, amplifier, converter. Bias: the hum, inverted and pushed back. Control: the microcontroller, SPI and data ready.
 Radio: a packet every 4 milliseconds to your computer. And the Daisy, locked in step with one clock, one start and one doorbell.""",
  S(0, cam="all", daisy="lifted", flows=["signal", "power", "bias", "daisy", "daisybus", "vclock"], labels=[])),
 scene("""Now follow one single sample through its 4 milliseconds. Your brain makes a tiny voltage; the electrode picks it up, together with the hum.
 The TVS diode, the resistor and the capacitor let it through, cleaned of radio noise. The ADS1299 subtracts the reference, multiplies by 24, and converts it.
 It rings data ready. The PIC32 reads 27 bytes, adds the accelerometer, and builds a 33-byte packet. The radio sends it to the dongle.
 And on your computer, each number is multiplied by about 0.02 microvolts, to give you back the voltage on your scalp. Then, 4 milliseconds later, it all happens again.""",
  S(0, cam="part", focus="HEAD", daisy="off", flows=["signal"], labels=[["HEAD", "0 ms: brain"]]),
  S(0.2, cam="part", focus="C9", daisy="off", flows=["signal"], labels=[["C9", "protection"]]),
  S(0.38, cam="part", focus="U6", daisy="off", flows=["signal"], labels=[["U6", "×24 · convert · DRDY"]]),
  S(0.55, cam="part", focus="U7", daisy="off", flows=["signal"], labels=[["U7", "27 bytes in · 33-byte packet out"]]),
  S(0.72, cam="part", focus="PC", daisy="off", flows=["signal"], labels=[["PC", "× 0.02 µV → your EEG"]])),
 scene("""For your own board, BrainTech-8, the same flows apply, with a few changes. An ESP32-S3 replaces both the PIC32 and the radio, since it has Wi-Fi built in.
 Its Wi-Fi bursts draw around 350 milliamps, so the 3.3 volt supply has to be much stronger than the Cyton's.
 You're also planning 47 pF capacitors on the inputs instead of 1 nF, two 100 kΩ resistors in series with the bias electrode, and a lithium battery with USB charging.
 Everything else, the protection, the ADS1299 with its capacitors, and the bias loop, you now understand from the Cyton.""",
  S(0, cam="overC", daisy="off", flows=["signal", "power"], panel="bt8", labels=[["U6", "same ADS1299 front end"], ["U7", "→ ESP32-S3"]])),
 scene("""That's the Cyton and the Daisy, from battery to brain waves. Keep the 3D explorer open while you draw your own schematic:
 click any part to see where its signal comes from, and where it goes next. Good luck with BrainTech-8.""",
  S(0, cam="over", daisy="lifted", flows=["signal", "daisy"], labels=[])),
])

TTS = [("ADS1299", "A.D.S. twelve ninety-nine"), ("SPI", "S.P.I."), ("TVS", "T.V.S."), ("SRB", "S.R.B."), ("DRDY", "D.R.D.Y."), ("PIC32", "PIC 32"),
       ("AVDD", "A.V.D.D."), ("AVSS", "A.V.S.S."), ("DVDD", "D.V.D.D."), ("VREF", "V-ref"), ("VCAP", "V-cap"), ("MCLR", "M-clear"), ("BIAS_INV", "bias-inverting"),
       ("CS1", "C.S. 1"), ("CS2", "C.S. 2"), ("CS3", "C.S. 3"), ("CS4", "C.S. 4"), ("SCK", "S.C.K."), ("MOSI", "mosi"), ("MISO", "miso"), ("I²C", "I-two-C"),
       ("0x3E", "hex 3 E"), ("RFduino", "R.F.-duino"), ("EEG", "E.E.G."), ("micro SD", "micro S.D."), ("SD card", "S.D. card"), ("USB", "U.S.B."),
       ("BrainTech-8", "BrainTech 8"), ("ESP32-S3", "E.S.P. 32 S3"), ("GUI", "G.U.I."), ("RAW", "raw"), ("BLE1", "B.L.E. 1"), ("BLE", "B.L.E."),
       ("1 MΩ", "1 megohm"), ("kΩ", " kilo-ohm"), ("1 nF", "1 nanofarad"), ("47 pF", "47 picofarad"), ("18 pF", "18 picofarads"), ("100 µF", "100 microfarad"),
       ("8,192", "8 thousand 192"), ("2.048", "2 point 0 4 8")]

def tts(t):
    for a, b in TTS: t = t.replace(a, b)
    return t

# ---- end-of-chapter recaps (inserted before the __main__ block runs) ----
RECAPS = {
 1: ("""Chapter recap. On top: the electrode header, the protection resistors, the ADS1299, the PIC32 with its crystal, buttons and LED, and the black sockets.
 Underneath: the battery plug, the power chips, the radio, the SD card, and more protection parts. Every part has a name you can find in the schematic.""",
     dict(cam="overC", daisy="off", labels=[["U6", "ADS1299"], ["U7", "PIC32"], ["PL1", "header"]])),
 2: ("""Chapter recap. Battery, then D9, the one-way valve. Then U5 makes 3.3 volts for everything digital.
 U4 makes plus 2.5 volts, and U3 with VR1 makes minus 2.5 volts, for the analog side of the ADS1299. And capacitors everywhere, as little water tanks.""",
     dict(cam="bot", daisy="off", flows=["power"], labels=[["U5", "3.3 V"], ["U3", "−3.3 V"], ["VR1", "−2.5 V"], ["B1", "battery"]])),
 3: ("""Chapter recap. Electrode, then a TVS diode against static, a 2.2 kΩ resistor to limit current, and a 1 nF capacitor against radio noise.
 Then the ADS1299: subtract the reference, multiply by 24, convert to 24 bits, 250 times a second, and ring data ready.""",
     dict(cam="overC", daisy="off", flows=["signal"], labels=[["U6", "×24 · 24-bit · 250 per second"]])),
 4: ("""Chapter recap. The ADS1299 averages the electrodes to find the shared hum, inverts it, and drives it back into your body through R5, R6 and the bias electrode.
 The hum on every channel gets smaller.""",
     dict(cam="overC", daisy="off", flows=["bias"], labels=[["R5", "R5 ‖ C16"], ["HEAD", "bias electrode"]])),
 5: ("""Chapter recap. The PIC32 runs the firmware on an 8 megahertz crystal. It talks SPI to the ADS1299, the accelerometer, the SD card and the Daisy, each with its own chip-select,
 and it reads 27 bytes from the ADS1299 every time data ready rings.""",
     dict(cam="overC", daisy="off", flows=["vread1", "vdrdy", "clock"], labels=[["U7", "PIC32"], ["U6", "ADS1299"]])),
 6: ("""Chapter recap. A 33-byte packet, 250 times a second, over a serial link to the RFduino, then by radio to the USB dongle and your computer.""",
     dict(cam="overC", daisy="off", flows=["vradio"], labels=[["BLE1", "RFduino"], ["PC", "computer"]])),
 7: ("""Chapter recap. The accelerometer adds motion to every packet, with an OR gate as its earplug. And the SD card lets the board record on its own.""",
     dict(cam="overC", daisy="off", flows=["motion", "storage"], labels=[["U1", "accelerometer"], ["CONN1", "SD card"]])),
 8: ("""Chapter recap. The Daisy adds a second ADS1299 for channels 9 to 16. It gets 3.3 volts and SPI through the 8-pin Daisy bus, and plus and minus 2.5 volts through two small sockets.
 One clock, one start, and one doorbell keep both chips in step, and the radio takes turns between them.""",
     dict(cam="over", daisy="lifted", flows=["daisy", "daisybus", "daisypower"], labels=[["Daisy U1", "channels 9–16"], ["U7", "channels 1–8"]])),
}
for ci, (text, shot) in RECAPS.items():
    CH[ci]["scenes"].append(scene(text, S(0, **shot)))

if __name__ == "__main__":
    out = os.path.dirname(os.path.abspath(__file__))
    flat = []
    for ci, ch in enumerate(CH):
        for si, sc in enumerate(ch["scenes"]):
            flat.append({"ch": ci, "chTitle": ch["title"], "first": si == 0, "text": sc["text"], "tts": tts(sc["text"]), "shots": sc["shots"]})
    json.dump(flat, open(f"{out}/course.json", "w"), indent=1, ensure_ascii=False)
    n = sum(len(s["tts"]) for s in flat)
    print(len(CH), "chapters,", len(flat), "scenes,", n, "TTS characters, about", round(n / 14 / 60, 1), "minutes")

