"""
Builds the EEG cap product concept in Blender and renders it.

    blender -b -P design/build_cap.py -- [--samples 96] [--res 1600 1200] [--no-render]

Saves design/eeg_cap_concept.blend and design/render_*.png.
Units: 1 Blender unit = 10 cm (head half-width ~8 cm).
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

HERE = os.path.dirname(os.path.abspath(__file__))
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
SAMPLES = int(argv[argv.index("--samples") + 1]) if "--samples" in argv else 96
RES = (int(argv[argv.index("--res") + 1]), int(argv[argv.index("--res") + 2])) if "--res" in argv else (1600, 1200)
RENDER = "--no-render" not in argv

R = Vector((0.80, 1.00, 0.95))  # head radii: x = ear to ear, y = front/back, z = height

# ---------------------------------------------------------------- scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
col = scene.collection


def link(obj):
    col.objects.link(obj)
    return obj


def smooth(obj):
    for p in obj.data.polygons:
        p.use_smooth = True


def mat(name, color, rough=0.5, metal=0.0, sheen=0.0, coat=0.0, emit=None, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")

    def put(key, val):
        if key in b.inputs:
            b.inputs[key].default_value = val
    put("Base Color", (*color, 1))
    put("Roughness", rough)
    put("Metallic", metal)
    put("Sheen Weight", sheen)
    put("Coat Weight", coat)
    put("Alpha", alpha)
    if emit:
        put("Emission Color", (*emit, 1))
        put("Emission Strength", 6.0)
    return m


def hexc(h):
    h = h.lstrip("#")
    srgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in srgb)


M = {
    "mannequin": mat("Mannequin", hexc("#c4c8cc"), rough=0.55),
    "cap": mat("Cap knit", hexc("#21474b"), rough=0.85, sheen=0.6),
    "band": mat("Cap band", hexc("#2b2f33"), rough=0.7),
    "holder": mat("Holder", hexc("#2b2f33"), rough=0.45, coat=0.3),
    "dry": mat("Dry electrode", hexc("#2a6fd0"), rough=0.3, metal=0.6),
    "pin": mat("Pins", hexc("#d9dde1"), rough=0.2, metal=1.0),
    "gold": mat("Gold cup", hexc("#d4a548"), rough=0.18, metal=1.0),
    "empty": mat("Holder insert", hexc("#8e979f"), rough=0.5),
    "shell": mat("Case shell", hexc("#ebe8e2"), rough=0.42, coat=0.2),
    "lid": mat("Case lid", hexc("#2b2f33"), rough=0.35, coat=0.4),
    "accent": mat("Teal accent", hexc("#2c8a8f"), rough=0.3),
    "orange": mat("Connector", hexc("#e85d3a"), rough=0.35),
    "lead": mat("Braided lead", hexc("#33373c"), rough=0.6),
    "led": mat("LED", hexc("#3d7cff"), emit=hexc("#3d7cff")),
    "text": mat("Emboss", hexc("#d9d6cf"), rough=0.5),
    "floor": mat("Studio", hexc("#d9dcdf"), rough=0.9),
}

# knit texture on the cap: a fine brick bump
cap_nodes = M["cap"].node_tree
tex = cap_nodes.nodes.new("ShaderNodeTexBrick")
tex.inputs["Scale"].default_value = 140.0
bump = cap_nodes.nodes.new("ShaderNodeBump")
bump.inputs["Strength"].default_value = 0.25
cap_nodes.links.new(tex.outputs["Fac"], bump.inputs["Height"])
cap_nodes.links.new(bump.outputs["Normal"], cap_nodes.nodes["Principled BSDF"].inputs["Normal"])


def direction(theta, phi):
    """10-20 style direction: theta from the vertex (deg), phi azimuth (0 = front, +90 = subject's left)."""
    t, p = math.radians(theta), math.radians(phi)
    return Vector((math.sin(t) * math.sin(p), -math.sin(t) * math.cos(p), math.cos(t)))


def on_head(d, lift=0.0, scale=1.0):
    k = 1 / math.sqrt((d.x / R.x) ** 2 + (d.y / R.y) ** 2 + (d.z / R.z) ** 2)
    p = d * k * scale
    n = Vector((p.x / R.x ** 2, p.y / R.y ** 2, p.z / R.z ** 2)).normalized()
    return p + n * lift, n


def frame(n, up=Vector((0, 0, 1))):
    """Rotation whose local z = n and local y points 'up' along the surface."""
    z = n.normalized()
    y = (up - z * up.dot(z))
    if y.length < 1e-4:
        y = Vector((0, 1, 0)) - z * z.y
    y.normalize()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed().to_4x4()


def add_mesh(name, verts_fn, material):
    bpy.ops.object.select_all(action="DESELECT")
    verts_fn()
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(material)
    return o


def cyl(name, r1, r2, depth, material, verts=48):
    return add_mesh(name, lambda: bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2, depth=depth),
                    material)


def bevel(o, w=0.01, seg=4):
    m = o.modifiers.new("Bevel", "BEVEL")
    m.width, m.segments, m.limit_method = w, seg, "ANGLE"
    smooth(o)
    o.data.shade_auto_smooth() if hasattr(o.data, "shade_auto_smooth") else None


# ---------------------------------------------------------------- mannequin
head = add_mesh("Head", lambda: bpy.ops.mesh.primitive_uv_sphere_add(segments=96, ring_count=64, radius=1), M["mannequin"])
head.scale = R
smooth(head)
nose = add_mesh("Nose", lambda: bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.14), M["mannequin"])
nose.scale = (0.7, 1.0, 1.3)
nose.location = (0, -0.98, -0.2)
smooth(nose)
for s in (1, -1):
    ear = add_mesh("Ear", lambda: bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=0.17), M["mannequin"])
    ear.scale = (0.35, 0.6, 1.0)
    ear.location = (s * 0.79, 0.02, -0.12)
    smooth(ear)
neck = cyl("Neck", 0.46, 0.4, 0.9, M["mannequin"], 64)
neck.location = (0, 0.1, -1.05)
smooth(neck)
shoulders = add_mesh("Shoulders", lambda: bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1), M["mannequin"])
shoulders.scale = (1.55, 0.75, 0.45)
shoulders.location = (0, 0.1, -1.75)
smooth(shoulders)

# ---------------------------------------------------------------- cap shell (sphere cut below the brow line)
bpy.ops.mesh.primitive_uv_sphere_add(segments=128, ring_count=80, radius=1.03)
cap = bpy.context.active_object
cap.name = "Cap"


def edge_theta(phi_rad):
    """Cap edge angle from the vertex: ~92 deg at the brow, ~86 above the ears, ~116 at the nape."""
    c = math.cos(phi_rad)
    return 86 + 6 * max(0.0, c) + 30 * max(0.0, -c) ** 1.2


def angles(v):
    d = v.normalized()
    theta = math.degrees(math.acos(max(-1.0, min(1.0, d.z))))
    phi = math.atan2(d.x, -d.y)
    return theta, phi


bm = bmesh.new()
bm.from_mesh(cap.data)
bmesh.ops.delete(bm, geom=[v for v in bm.verts if angles(v.co)[0] > edge_theta(angles(v.co)[1])], context="VERTS")
bm.to_mesh(cap.data)
bm.free()
cap.scale = R
cap.data.materials.append(M["cap"])
sol = cap.modifiers.new("Thickness", "SOLIDIFY")
sol.thickness = 0.018
smooth(cap)

# edge band: a tube following the cap edge
band_pts = []
for i in range(0, 361, 4):
    ph = math.radians(i)
    th = math.radians(edge_theta(ph))
    u = Vector((math.sin(th) * math.sin(ph), -math.sin(th) * math.cos(ph), math.cos(th))) * 1.04
    band_pts.append(Vector((u.x * R.x, u.y * R.y, u.z * R.z)))
# ---------------------------------------------------------------- electrodes at 10-20 sites
SITES = [
    ("Fp1", 72, 18, "gold"), ("Fp2", 72, -18, "gold"), ("C3", 36, 90, "gold"), ("C4", 36, -90, "gold"),
    ("O1", 72, 162, "dry"), ("Oz", 72, 180, "dry"),
    ("Fz", 36, 0, "empty"), ("Cz", 0, 0, "empty"), ("Pz", 36, 180, "empty"), ("F3", 45, 45, "empty"),
    ("F4", 45, -45, "empty"), ("P3", 45, 135, "empty"), ("P4", 45, -135, "empty"), ("T7", 72, 90, "empty"),
    ("T8", 72, -90, "empty"), ("O2", 72, -162, "empty"), ("F7", 72, 54, "empty"), ("F8", 72, -54, "empty"),
    ("P7", 72, 126, "empty"), ("P8", 72, -126, "empty"),
]
electrode_tops = {}
for name, th, ph, kind in SITES:
    p, n = on_head(direction(th, ph), lift=0.03, scale=1.03)
    base = Matrix.Translation(p) @ frame(n)
    holder = cyl(f"Holder {name}", 0.085, 0.075, 0.035, M["holder"])
    holder.matrix_world = base
    bevel(holder, 0.006)
    if kind == "empty":
        ins = cyl(f"Insert {name}", 0.045, 0.045, 0.012, M["empty"])
        ins.matrix_world = base @ Matrix.Translation((0, 0, 0.02))
        electrode_tops[name] = p
    elif kind == "gold":
        cup = cyl(f"Gold cup {name}", 0.06, 0.052, 0.04, M["gold"])
        cup.matrix_world = base @ Matrix.Translation((0, 0, 0.035))
        bevel(cup, 0.006)
        stem = cyl(f"Gold stem {name}", 0.014, 0.014, 0.05, M["gold"], 16)
        stem.matrix_world = base @ Matrix.Translation((0, 0, 0.075))
        boot = cyl(f"Lead boot {name}", 0.02, 0.016, 0.04, M["orange"], 16)
        boot.matrix_world = base @ Matrix.Translation((0, 0, 0.115))
        electrode_tops[name] = (base @ Matrix.Translation((0, 0, 0.13))).to_translation()
    else:
        body = cyl(f"Dry electrode {name}", 0.065, 0.06, 0.05, M["dry"])
        body.matrix_world = base @ Matrix.Translation((0, 0, 0.04))
        bevel(body, 0.008)
        top = cyl(f"Dry cap {name}", 0.032, 0.042, 0.05, M["dry"])
        top.matrix_world = base @ Matrix.Translation((0, 0, 0.09))
        bevel(top, 0.006)
        ring = add_mesh(f"Dry ring {name}", lambda: bpy.ops.mesh.primitive_torus_add(
            major_radius=0.064, minor_radius=0.006, major_segments=48, minor_segments=8), M["pin"])
        ring.matrix_world = base @ Matrix.Translation((0, 0, 0.066))
        boot = cyl(f"Lead boot {name}", 0.02, 0.016, 0.04, M["orange"], 16)
        boot.matrix_world = base @ Matrix.Translation((0, 0, 0.13))
        electrode_tops[name] = (base @ Matrix.Translation((0, 0, 0.15))).to_translation()

# ---------------------------------------------------------------- case on the back
anchor, an = on_head(direction(104, 180), lift=0.04, scale=1.03)
CASE = Matrix.Translation(anchor) @ frame(an)
W, H, D = 0.75, 0.75, 0.30  # 75 x 75 x 30 mm


def case_part(name, maker, material, local, bev=0.0):
    o = add_mesh(name, maker, material)
    o.matrix_world = CASE @ local
    if bev:
        bevel(o, bev, 5)
    return o


shell = case_part("Case shell", lambda: bpy.ops.mesh.primitive_cube_add(size=1), M["shell"],
                  Matrix.Translation((0, 0, D / 2)) @ Matrix.Diagonal((W, H, D, 1)), 0.0)
shell.scale = (W, H, D)
bevel(shell, 0.06, 6)
lid = case_part("Case lid", lambda: bpy.ops.mesh.primitive_cube_add(size=1), M["lid"],
                Matrix.Translation((0, 0, D + 0.006)))
lid.scale = (W - 0.03, H - 0.03, 0.02)
bevel(lid, 0.02, 5)
stripe = case_part("Accent stripe", lambda: bpy.ops.mesh.primitive_cube_add(size=1), M["accent"],
                   Matrix.Translation((0, -H / 2 + 0.1, D + 0.018)))
stripe.scale = (W - 0.16, 0.018, 0.005)
led = case_part("Status LED", lambda: bpy.ops.mesh.primitive_uv_sphere_add(radius=0.016), M["led"],
                Matrix.Translation((W / 2 - 0.1, -H / 2 + 0.1, D + 0.02)))
switch = case_part("Power switch", lambda: bpy.ops.mesh.primitive_cube_add(size=1), M["accent"],
                   Matrix.Translation((W / 2 + 0.004, -0.04, D * 0.55)))
switch.scale = (0.03, 0.09, 0.04)
bevel(switch, 0.004)
rst = case_part("Reset button", lambda: bpy.ops.mesh.primitive_cylinder_add(radius=0.012, depth=0.02), M["lid"],
                Matrix.Translation((W / 2 + 0.004, 0.06, D * 0.55)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
gland = case_part("Cable gland", lambda: bpy.ops.mesh.primitive_cylinder_add(radius=0.06, depth=0.07), M["lead"],
                  Matrix.Translation((0, H / 2 + 0.015, D * 0.55)) @ Matrix.Rotation(math.pi / 2, 4, "X"))
smooth(gland)
bpy.ops.object.text_add()
txt = bpy.context.active_object
txt.data.body = "BRAINTECH"
txt.data.align_x = "CENTER"
txt.data.size = 0.075
txt.data.extrude = 0.002
txt.data.materials.append(M["text"])
txt.matrix_world = CASE @ Matrix.Translation((0, 0.05, D + 0.017))

# ---------------------------------------------------------------- harness (bezier tubes over the cap)
def surface_path(d0, d1, lift, steps):
    pts = []
    for i in range(steps + 1):
        t = i / steps
        d = d0.lerp(d1, t).normalized()
        pts.append(on_head(d, lift, 1.03)[0])
    return pts


def tube(name, pts, radius, material):
    cu = bpy.data.curves.new(name, "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = radius
    cu.bevel_resolution = 4
    cu.use_fill_caps = True
    sp = cu.splines.new("NURBS")
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (*p, 1)
    sp.use_endpoint_u = True
    sp.order_u = 4
    o = link(bpy.data.objects.new(name, cu))
    o.data.materials.append(material)
    return o


band = tube("Cap band", band_pts, 0.022, M["band"])
# chin strap: from the band above each ear, in front of the ear, under the chin, with a buckle
for s_ in (1, -1):
    pts = [Vector((s_ * 0.80, -0.05, 0.03)), Vector((s_ * 0.79, -0.22, -0.30)), Vector((s_ * 0.66, -0.42, -0.58)),
           Vector((s_ * 0.36, -0.60, -0.78)), Vector((s_ * 0.06, -0.66, -0.83))]
    tube("Chin strap", pts, 0.02, M["band"])
buckle = add_mesh("Buckle", lambda: bpy.ops.mesh.primitive_cube_add(size=1), M["orange"])
buckle.scale = (0.12, 0.05, 0.05)
buckle.location = (0, -0.665, -0.835)
buckle.rotation_euler = (0.5, 0, 0)
bevel(buckle, 0.012)
band.data.splines[0].use_cyclic_u = True

exit_dir = direction(90, 180)
gland_top = (CASE @ Matrix.Translation((0, H / 2 + 0.05, D * 0.55))).to_translation()
exit_pt = on_head(exit_dir, 0.035, 1.03)[0]
tube("Harness bundle", [exit_pt, exit_pt.lerp(gland_top, 0.5) + Vector((0, 0.06, 0)), gland_top], 0.028, M["lead"])
for name in ("O1", "Oz", "C3", "C4", "Fp1", "Fp2"):
    end = electrode_tops[name]
    d1 = end.normalized()
    if name[0] in "CF":
        left = name in ("C3", "Fp1")
        via = direction(22 if name.startswith("Fp") else 30, 60 if left else -60)
        pts = surface_path(exit_dir, via, 0.028, 24) + surface_path(via, d1, 0.028, 24)[1:]
    else:
        pts = surface_path(exit_dir, d1, 0.028, 16)
    pts[-1] = end
    tube(f"Lead {name}", pts, 0.0075, M["lead"])

for s, label in ((1, "SRB"), (-1, "BIAS")):
    clip = add_mesh(f"{label} ear clip", lambda: bpy.ops.mesh.primitive_cube_add(size=1), M["lead"])
    clip.scale = (0.05, 0.07, 0.11)
    clip.location = (s * 0.82, 0.05, -0.3)
    bevel(clip, 0.012)
    tip = add_mesh(f"{label} clip accent", lambda: bpy.ops.mesh.primitive_cube_add(size=1), M["orange"])
    tip.scale = (0.052, 0.072, 0.02)
    tip.location = (s * 0.82, 0.05, -0.23)
    pts = surface_path(exit_dir, direction(100, s * 100), 0.028, 14)
    pts += [Vector((s * 0.86, 0.06, -0.12)), Vector((s * 0.84, 0.05, -0.2))]
    tube(f"Lead {label}", pts, 0.01, M["lead"])

# ---------------------------------------------------------------- studio: sweep, lights, cameras
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, -2.2))
floor = bpy.context.active_object
floor.data.materials.append(M["floor"])
bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 9, 8), rotation=(math.pi / 2, 0, 0))
wall = bpy.context.active_object
wall.data.materials.append(M["floor"])

world = bpy.data.worlds.new("World")
scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs["Color"].default_value = (*hexc("#e4e7ea"), 1)
world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.35


def area(name, loc, energy, size, color=(1, 1, 1)):
    l = bpy.data.lights.new(name, "AREA")
    l.energy, l.size, l.color = energy, size, color
    o = link(bpy.data.objects.new(name, l))
    o.location = loc
    tc = o.constraints.new("TRACK_TO")
    tc.target = target
    return o


target = link(bpy.data.objects.new("Target", None))
target.location = (0, 0, -0.05)
area("Key", (4.5, -4.0, 4.5), 1500, 4)
area("Fill", (-5, -3, 2), 450, 6, (0.9, 0.95, 1.0))
area("Rim", (0, 6, 4), 900, 3, (1.0, 0.96, 0.9))
area("Top", (0, 0, 7), 300, 5)

scene.render.engine = "CYCLES"
scene.cycles.samples = SAMPLES
scene.cycles.use_denoising = True
scene.render.resolution_x, scene.render.resolution_y = RES
scene.render.film_transparent = False
try:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.get_devices()
    for d in prefs.devices:
        d.use = True
    scene.cycles.device = "GPU"
except Exception as e:
    print("GPU setup failed, using CPU:", e)

SHOTS = {
    "back_three_quarter": (4.2, 5.4, 2.4),
    "front_three_quarter": (-3.0, -6.2, 1.5),
    "side": (7.0, 0.3, 0.9),
}
os.makedirs(HERE, exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "eeg_cap_concept.blend"))
case_target = link(bpy.data.objects.new("Case target", None))
case_target.location = (CASE @ Matrix.Translation((0, 0, D / 2))).to_translation()
SHOTS["case_closeup"] = tuple((case_target.location + Vector((1.1, 2.4, 0.9))))
for shot, loc in SHOTS.items():
    cam_data = bpy.data.cameras.new(shot)
    cam_data.lens = 70 if shot != "case_closeup" else 60
    cam = link(bpy.data.objects.new(shot, cam_data))
    cam.location = loc
    tc = cam.constraints.new("TRACK_TO")
    tc.target = case_target if shot == "case_closeup" else target
    if shot == "case_closeup":
        cam_data.dof.use_dof = True
        cam_data.dof.focus_object = case_target
        cam_data.dof.aperture_fstop = 4.0
    scene.camera = cam
    if RENDER:
        scene.render.filepath = os.path.join(HERE, f"render_{shot}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", shot)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, "eeg_cap_concept.blend"))
print("saved", os.path.join(HERE, "eeg_cap_concept.blend"))
