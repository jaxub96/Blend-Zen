"""
Build the Gothic II sky as an equirectangular HDR for use as a Blender
studio light / World environment, by rendering the game's real skydome.

Gothic has no HDRI: the sky is Skydome_ColorLayer.3ds (a vertex-coloured
hemisphere, colours driven per time of day) plus Skydome_Layer1..3.3ds (flat
cloud caps with tiled planar UVs) textured with SkyDay_*_Layer*_A0.tga. This
script parses those .3ds files, rebuilds the dome in Blender with an
elevation colour gradient matched to a Spacer screenshot, and renders an
equirectangular panorama from the dome centre (Cycles, emission only). The
sun is then painted in as a very bright disc so the image is a complete light
source, and the area below the horizon fades into neutral grey.

Usage:
  blender --background --python tooling/pipeline/build_gothic_sky.py -- \
      "<Gothic II folder>" <output.hdr> [width]
"""
import struct, sys, math
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
GAME, OUT = argv[0], argv[1]
WIDTH = int(argv[2]) if len(argv) > 2 else 1024
MESHES = f"{GAME}/_work/Data/Meshes/_intern"
SKY_TEX = f"{GAME}/_work/Data/Textures/Effects/Environment/Sky/nomip"

# Below the horizon the game shows nothing useful (the dome just ends), so the
# haze fades into a neutral grey there. It reads as "no ground yet" instead of
# a black hole, and it bounces some light back up like real terrain would.
GROUND = (126, 129, 132)

# (elevation degrees, sRGB 0-255) sampled from Spacer down to the horizon;
# below it the haze blends into GROUND.
GRADIENT = [
    (90, (70, 95, 165)), (40, (70, 92, 145)), (25, (70, 90, 135)), (16, (110, 130, 170)),
    (8, (145, 171, 194)), (4.6, (154, 172, 178)), (2.3, (152, 166, 170)), (0, (146, 156, 158)),
    (-3, (136, 142, 145)), (-8, GROUND), (-90, GROUND),
]

# The sun is part of the picture, so the panorama lights a scene on its own
# (no Sun object needed). EEVEE turns the bright disc into a shadow-casting
# sun (World > Settings > Sun threshold); the wide glow around it stays soft
# fill light. Values are linear radiance; the numbers printed at the end of a
# build say how bright a white surface ends up.
SUN_ELEVATION_DEG = 50.0
SUN_U = 0.52                      # horizontal place in the panorama, a cloud-free patch
SUN_COLOR = (1.0, 0.92, 0.74)     # warm, so sun + blue sky add up to a near-white daylight
SUN_DISC_DEG = 2.0                # radius of the bright core
SUN_DISC_RADIANCE = 680.0
SUN_GLOW = ((4.0, 3.0), (30.0, 0.32))   # (width in degrees, peak radiance) haloes
CLOUD_STRENGTH = 0.85
# Shift the whole gradient (except the zenith/nadir ends) down by this many
# degrees, so the bright horizon band sits a little below eye level.
HORIZON_OFFSET_DEG = -3.0


def lin(c):
    c = c / 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def parse_3ds(path):
    d = open(path, "rb").read(); objs = {}
    def walk(off, end, cur):
        while off < end:
            cid, ln = struct.unpack_from("<HI", d, off); body = off + 6; nend = off + ln
            if cid in (0x4D4D, 0x3D3D, 0x4100): walk(body, nend, cur)
            elif cid == 0x4000:
                z = d.index(b"\0", body); name = d[body:z].decode("latin1"); objs[name] = {}; walk(z + 1, nend, name)
            elif cid == 0x4110:
                n, = struct.unpack_from("<H", d, body); objs[cur]["v"] = [struct.unpack_from("<3f", d, body + 2 + 12 * i) for i in range(n)]
            elif cid == 0x4120:
                n, = struct.unpack_from("<H", d, body); objs[cur]["f"] = [struct.unpack_from("<3H", d, body + 2 + 8 * i)[:3] for i in range(n)]
            elif cid == 0x4140:
                n, = struct.unpack_from("<H", d, body); objs[cur]["uv"] = [struct.unpack_from("<2f", d, body + 2 + 8 * i) for i in range(n)]
            off = nend
    walk(0, len(d), None)
    return next(iter(objs.values()))


def make_mesh(name, data):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x * 0.01, y * 0.01, z * 0.01) for x, y, z in data["v"]], [], data["f"])
    me.update()
    if "uv" in data:
        uv = me.uv_layers.new(name="UVMap")
        for loop in me.loops:
            uv.data[loop.index].uv = data["uv"][loop.vertex_index]
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = 8; sc.cycles.device = "CPU"
sc.view_settings.view_transform = "Standard"
sc.render.resolution_x = WIDTH; sc.render.resolution_y = WIDTH // 2; sc.render.resolution_percentage = 100
sc.world = bpy.data.worlds.new("black"); sc.world.use_nodes = True
# the colour dome stops ~13 deg below the horizon; beyond it show the ground colour
# (the gradient has already reached that colour by then, so there is no seam)
sc.world.node_tree.nodes["Background"].inputs["Color"].default_value = (lin(GROUND[0]), lin(GROUND[1]), lin(GROUND[2]), 1)

# --- colour dome -----------------------------------------------------------
dome = make_mesh("ColorLayer", parse_3ds(f"{MESHES}/Skydome_ColorLayer.3ds"))
m = bpy.data.materials.new("dome"); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
geo = nt.nodes.new("ShaderNodeNewGeometry"); sep = nt.nodes.new("ShaderNodeSeparateXYZ")
nrm = nt.nodes.new("ShaderNodeVectorMath"); nrm.operation = "NORMALIZE"
elev = nt.nodes.new("ShaderNodeMath"); elev.operation = "ARCSINE"
deg = nt.nodes.new("ShaderNodeMath"); deg.operation = "DEGREES"
mapr = nt.nodes.new("ShaderNodeMapRange"); mapr.inputs["From Min"].default_value = -90; mapr.inputs["From Max"].default_value = 90
ramp = nt.nodes.new("ShaderNodeValToRGB"); ramp.color_ramp.interpolation = "LINEAR"
stops = sorted(
    [(e if abs(e) == 90 else e + HORIZON_OFFSET_DEG, c) for e, c in GRADIENT], key=lambda s: s[0])
els = ramp.color_ramp.elements
while len(els) < len(stops): els.new(0.5)
for el, (e, c) in zip(els, stops):
    el.position = (e + 90) / 180.0; el.color = (lin(c[0]), lin(c[1]), lin(c[2]), 1)
em = nt.nodes.new("ShaderNodeEmission"); out = nt.nodes.new("ShaderNodeOutputMaterial")
nt.links.new(geo.outputs["Position"], nrm.inputs[0]); nt.links.new(nrm.outputs["Vector"], sep.inputs[0])
nt.links.new(sep.outputs["Z"], elev.inputs[0]); nt.links.new(elev.outputs[0], deg.inputs[0])
nt.links.new(deg.outputs[0], ramp.inputs["Fac"]) if False else None
# ramp position = (deg+90)/180
div = nt.nodes.new("ShaderNodeMath"); div.operation = "MULTIPLY_ADD"
div.inputs[1].default_value = 1 / 180.0; div.inputs[2].default_value = 0.5
nt.links.new(deg.outputs[0], div.inputs[0]); nt.links.new(div.outputs[0], ramp.inputs["Fac"])
nt.links.new(ramp.outputs["Color"], em.inputs["Color"]); nt.links.new(em.outputs[0], out.inputs[0])
dome.data.materials.append(m)

# --- cloud layer -----------------------------------------------------------
cloud = make_mesh("Layer1", parse_3ds(f"{MESHES}/Skydome_Layer1.3ds"))
img = bpy.data.images.load(f"{SKY_TEX}/SkyDay_NewWorld_Layer0_A0.tga"); img.alpha_mode = "STRAIGHT"
m2 = bpy.data.materials.new("clouds"); m2.use_nodes = True; nt = m2.node_tree; nt.nodes.clear()
tex = nt.nodes.new("ShaderNodeTexImage"); tex.image = img; tex.extension = "REPEAT"
em = nt.nodes.new("ShaderNodeEmission"); tr = nt.nodes.new("ShaderNodeBsdfTransparent")
mix = nt.nodes.new("ShaderNodeMixShader"); out = nt.nodes.new("ShaderNodeOutputMaterial")
sa = nt.nodes.new("ShaderNodeMath"); sa.operation = "MULTIPLY"; sa.inputs[1].default_value = CLOUD_STRENGTH
nt.links.new(tex.outputs["Color"], em.inputs["Color"]); nt.links.new(tex.outputs["Alpha"], sa.inputs[0])
nt.links.new(sa.outputs[0], mix.inputs["Fac"]); nt.links.new(tr.outputs[0], mix.inputs[1])
nt.links.new(em.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs[0])
cloud.data.materials.append(m2)

# --- panoramic camera at the dome centre, Z up, looking along +Y -------------
cam = bpy.data.objects.new("cam", bpy.data.cameras.new("cam")); sc.collection.objects.link(cam); sc.camera = cam
cam.data.type = "PANO"; cam.data.panorama_type = "EQUIRECTANGULAR"
cam.rotation_euler = (math.radians(90), 0, 0)
cam.location = (0, 0, 0)

sc.render.image_settings.file_format = "HDR"
sc.render.filepath = OUT
bpy.ops.render.render(write_still=True)

# --- paint the sun into the panorama ----------------------------------------
import numpy as np

img = bpy.data.images.load(OUT)
w, h = img.size
px = np.empty(w * h * 4, dtype=np.float32)
img.pixels.foreach_get(px)
px = px.reshape(h, w, 4)                       # row 0 is the bottom of the image

# Direction of every pixel, the way Blender maps an equirectangular world.
u = (np.arange(w) + 0.5) / w
v = (np.arange(h) + 0.5) / h
lon = (u - 0.5) * 2 * math.pi
lat = (v - 0.5) * math.pi
lon, lat = np.meshgrid(lon, lat)
dirs = np.stack([-np.cos(lat) * np.cos(lon), np.cos(lat) * np.sin(lon), np.sin(lat)], axis=-1)

s_lon = (SUN_U - 0.5) * 2 * math.pi
s_lat = math.radians(SUN_ELEVATION_DEG)
sun_dir = np.array([-math.cos(s_lat) * math.cos(s_lon), math.cos(s_lat) * math.sin(s_lon), math.sin(s_lat)])
angle = np.degrees(np.arccos(np.clip(dirs @ sun_dir, -1, 1)))

edge = 0.35                                    # soft rim so the disc is not aliased
sun = SUN_DISC_RADIANCE * np.clip((SUN_DISC_DEG + edge - angle) / (2 * edge), 0, 1)
for width, peak in SUN_GLOW:
    sun += peak * np.exp(-((angle / width) ** 2))
sun *= (lat > math.radians(-4))                # nothing shines through the ground
px[..., :3] += sun[..., None] * np.array(SUN_COLOR, dtype=np.float32)

img.pixels.foreach_set(px.ravel())
img.file_format = "HDR"
img.filepath_raw = OUT
img.save()

# How bright does a white, matte surface get under this sky? (1.0 = full white)
solid = (np.cos(lat) * (math.pi / h) * (2 * math.pi / w))[..., None]
def lit(normal, light=px[..., :3]):
    cos = np.clip(dirs @ np.array(normal), 0, None)[..., None]
    return (light * cos * solid).sum(axis=(0, 1)) / math.pi
shade = px[..., :3] - (SUN_DISC_RADIANCE * (angle < SUN_DISC_DEG + edge))[..., None] * np.array(SUN_COLOR)
shade = np.clip(shade, 0, None)
print("white facing up      ", lit((0, 0, 1)).round(3))
print("white facing the sun ", lit(tuple(sun_dir)).round(3))
print("white up, in shadow  ", lit((0, 0, 1), shade).round(3))
print("white wall, away     ", lit((-sun_dir[0], -sun_dir[1], 0) / np.hypot(sun_dir[0], sun_dir[1])).round(3))
print("WROTE", OUT)
