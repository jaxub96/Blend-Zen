"""
Build the Gothic II sky as an equirectangular HDR for use as a Blender
studio light / World environment, by rendering the game's real skydome.

Gothic has no HDRI: the sky is Skydome_ColorLayer.3ds (a vertex-coloured
hemisphere, colours driven per time of day) plus Skydome_Layer1..3.3ds (flat
cloud caps with tiled planar UVs) textured with SkyDay_*_Layer*_A0.tga. This
script parses those .3ds files, rebuilds the dome in Blender with an
elevation colour gradient matched to a Spacer screenshot, and renders an
equirectangular panorama from the dome centre (Cycles, emission only).

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

# Below the horizon Gothic shows black (the dome ends there); keep the picture
# faithful. Brightness for lit scenes comes from the preview sun instead
# (see zen_waypoint_tools/gothic_sky.py), not from changing this image.
GROUND = (0, 0, 0)

# (elevation degrees, sRGB 0-255) sampled from Spacer; below the last stop is black.
GRADIENT = [
    (90, (70, 95, 165)), (40, (70, 92, 145)), (25, (70, 90, 135)), (16, (110, 130, 170)),
    (8, (145, 171, 194)), (4.6, (154, 172, 172)), (2.3, (152, 157, 135)), (0, (133, 124, 81)),
    (-2, (98, 70, 33)), (-4, (48, 25, 7)), (-7, GROUND), (-90, GROUND),
]
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
print("WROTE", OUT)
