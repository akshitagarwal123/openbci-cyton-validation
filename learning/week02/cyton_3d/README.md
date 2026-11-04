# Cyton board in 3D

Rotatable 3D model of the OpenBCI Cyton, built from OpenBCI's own design files:

- `positions.csv`: every part's name, package, side, centre (mils) and rotation (OBCI_V4_C Component Positions)
- `outline.gbr`: the board outline (an octagon, 2.42 in across)
- `layerTop.jpg`, `layerBottom_noMirror.jpg`: the top and bottom layer plots from docs.openbci.com

Open `index.html` through any web server (it loads three.js from a CDN and the two layer images next to it).
Live version: https://claude.ai/artifact/1jhBo5jJ9rSSQ4mTTuaEn5

Positions and rotations are exact. Part heights and package sizes are typical values, so the 3D shapes are close approximations.
