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

`test.js` is the automated test (run in headless Chrome): it selects all 84 parts, checks all 177 links,
runs all 37 tour steps, clicks the panel controls and clicks parts on the 3D board from the top and from underneath.
Last run: all pass, no JavaScript errors.
