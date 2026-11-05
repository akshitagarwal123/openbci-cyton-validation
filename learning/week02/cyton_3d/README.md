# Cyton board in 3D

Rotatable 3D model of the OpenBCI Cyton, built from OpenBCI's own design files:

- `positions.csv`: every part's name, package, side, centre (mils) and rotation (OBCI_V4_C Component Positions)
- `outline.gbr`: the board outline (an octagon, 2.42 in across)
- `layerTop.jpg`, `layerBottom_noMirror.jpg`: the top and bottom layer plots from docs.openbci.com

Open `index.html` through any web server (it loads three.js from a CDN and the two layer images next to it).
Live version: https://claude.ai/artifact/1jhBo5jJ9rSSQ4mTTuaEn5

Positions and rotations are exact. Part heights and package sizes are typical values, so the 3D shapes are close approximations.

## Explorer (5 Nov)

- Click any part: what it does, where its signal comes from, where it goes next (clickable links), and which flows it belongs to.
- Guided flows with 3D flow lines and moving particles, including where a line passes through the board (gold via rings):
  brain signal, power, bias loop, motion, SD card, clock, buttons and switch. Back / Next, step dots, arrow keys, Esc.
- "Show every flow at once" zooms out and draws all 7 flows.

`test.js` is the automated test (run in headless Chrome): it selects every part, checks every link,
runs all 37 tour steps, clicks the panel controls and clicks parts on the 3D board from the top and from underneath.
Last run: all pass, no JavaScript errors.

## Daisy module (5 Nov)

The Daisy (second ADS1299, channels 9–16) is built from its own design files in the same repo:
`daisy_positions.csv` (OBCI_V3-1_D component positions), `daisy_outline.gbr`, and the layer plots `daisyTop.jpg` / `daisyBottom.jpg`.
Shifted by (−2, +858) mils, its J1 sits exactly on the Cyton's J1 (Daisy port) and its PL1 exactly on the Cyton's PL1.

- "Daisy" button: lifted (exploded view), stacked (real spacing, resting on the header pins) or hidden.
- Whichever board is in the way turns see-through: pick a Cyton part under the Daisy and the Daisy fades; pick a Daisy part on its underside and the Cyton fades.
- 4 new flows: Daisy channels 9–16 (header → TVS → 2.2 kΩ → 1 nF → Daisy ADS1299 → Daisy bus → PIC32 → radio),
  Daisy bus (SPI, CS2, shared 2.048 MHz clock, RESET), Daisy power (DVDD over J1, ±2.5 V through the header), Daisy bias.
- Facts checked against the Daisy schematic and the Cyton firmware: CLKSEL tied to ground (runs on the Cyton chip's clock),
  Daisy DRDY not wired out, START unused, CONFIG3 = 0b11101100 sent to both chips (both bias amplifiers on), Daisy ID 0x3E switches the firmware to 16 channels.

Last test run: 123 parts, 259 links, 65 tour steps across 11 flows, 25 clicks on the 3D boards (both boards, both sides, including through the see-through board). All pass, no JavaScript errors.

## Closer to the real board (5 Nov)

Compared against OpenBCI's product photos (`compare_with_photo.jpg`: model on the left, photo on the right) and fixed:
- Connector gender: the Cyton's J1, J3 and J4 are black female sockets; the Daisy's J1 is 8 pins pointing down into J1.
- Mounting holes are now real holes with a plated ring.
- ADS1299 (TQFP-64) and PIC32 (SSOP-28) have their legs.
- OpenBCI gear logo on both boards, "V3 - 32" and "chipKIT™" placed as printed; cream RST / PROG buttons.
Small passives are still generic shapes with typical sizes, so very close up it is a model, not a photo.
