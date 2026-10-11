"""Crop a plotted layer PNG to the board (non-white area) with a small margin. Usage: crop_png.py in.png out.png"""
import sys
from PIL import Image, ImageOps
im = Image.open(sys.argv[1]).convert("RGBA")
bg = Image.new("RGBA", im.size, "white"); bg.alpha_composite(im); im = bg.convert("RGB")
box = ImageOps.invert(im).getbbox()
m = 20
im = im.crop((max(box[0] - m, 0), max(box[1] - m, 0), box[2] + m, box[3] + m))
im.thumbnail((1400, 1400))
im.save(sys.argv[2])
print(sys.argv[2], im.size)
