"""Builds the check level: four stations, one for each thing in TODO.md that
can only be judged by eye in Spacer or in the game.

    blender --background --python tooling/pipeline/build_check_level.py -- \
        blender_work_dir/bz_check.blend [LEVEL_NAME MOD_NAME]

Run it with your normal Blender profile (no --factory-startup): it needs
"Zen Waypoint Tools" and KrxImpExp enabled and the Gothic Game Folder set.
With a level and mod name (e.g. BZ_CHECK MOD) it also exports the level
package and writes three things into the game's scripts, each replaced on
a re-run:

  Story/Text.d            the signs' texts (between two marker comments)
  Story/NPC/BZ_Check_Align.d   four test NPCs
  Story/Startup.d         STARTUP_/INIT_<LEVEL_NAME>, which insert them
                          (between two marker comments)

Rebuild the scripts afterwards ("gothic build").

What to look at (every station has a sign with the same instruction):

  1  Spacer         Open the uncompiled ZEN in Spacer. It must load without
                    an error box. The script also checks the file itself and
                    prints PASS/FAIL: floats have no trailing ".0", static
                    lights carry no dynamic fields, freepoints have zbias 1.
  2  Lights         The dark hall has three white static lights of 3, 5 and
                    7 m range, 2 m above the floor. Left and right of each
                    stand two barrels exactly where its light reaches zero
                    on the floor. In Spacer (after Compile Light) and in the
                    game the floor must be lit up to the barrels and dark
                    beyond. Compare the brightness with the reference picture
                    the script renders next to the .blend
                    (<name>_lights_reference.png), or with the Blender
                    viewport in Rendered mode with the roof hidden.
  3  Waypoints      Four men stand on four waypoints. Each must face the
                    barrel in front of him: that is where the waypoint's
                    green Y arrow points in Blender.
  4  Scale          The same barrel at half, normal and double size and
                    stretched to double height. The top of each must be level
                    with the stone post beside it.
  5  Plants         Props dropped in with no settings of their own. Walk the
                    lane: the sign says for each plant whether it must sway
                    and whether it must stop you (the vanilla defaults for
                    that mesh). The barrel at the end stops you.
"""

import math
import os
import re
import sys

import bmesh
import bpy
from mathutils import Vector

from zen_waypoint_tools import vob_ops, vob_preview
from zen_waypoint_tools.waypoint_links import aim_waypoint_at, setup_waypoint_empty

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MATERIAL_LIBRARY = os.path.join(_REPO, "asset_catalog", "materials_levels.blend")
SKY_HDR = os.path.join(_REPO, "asset_catalog", "sky", "gothic_sky.hdr")

MATERIALS = {
    "ground": "NW_Nature_Waldboden_03",
    "floor": "NW_Seq_Nature_WhiteSand_01",      # bright and even: shows light falloff
    "wall": "NW_City_StoneWall_01",
}
SLOTS = list(MATERIALS)

GROUND_X, GROUND_Y = 22.0, 18.0            # half size of the ground, metres
# The dark hall (inner space), its door in the south wall, and the lights.
HALL_X0, HALL_X1, HALL_Y0, HALL_Y1, HALL_HEIGHT = -18.5, 18.5, 5.0, 16.0, 4.0
WALL = 0.4
DOOR_HALF, DOOR_HEIGHT = 1.5, 2.6
LIGHT_Y, LIGHT_HEIGHT = 10.5, 2.0
LIGHTS = ((-12.5, 3.0), (-3.0, 5.0), (10.5, 7.0))          # (x, range in metres)

BARREL = "NW_HARBOUR_BARREL_01"
ALIGN_CENTRE = Vector((-12.0, -6.0))
ALIGN_HEADINGS = (0.0, -90.0, 135.0, 60.0)     # degrees about Z; 0 = north (+Y), -90 = east
SCALE_ROW_Y, SCALE_ROW_X = -2.5, 5.0
SCALES = ((0.5, 0.5, 0.5), (1.0, 1.0, 1.0), (2.0, 2.0, 2.0), (1.0, 1.0, 2.0))
PLANT_ROW_Y, PLANT_ROW_X = -10.5, 4.0
PLANTS = ("NW_NATURE_GRASSGROUP_01", "NW_NATURE_BUSH_25P", "NW_NATURE_FARN_102P", "NW_NATURE_TANNE_75P")


# -- level mesh -----------------------------------------------------------------------

def _grid(bm, uv_layer, origin, u_axis, v_axis, slot, step=1.0, tile=2.5):
    """A rectangle spanned by u_axis and v_axis from origin, cut into quads
    of about `step` metres: Gothic lights outdoor geometry per vertex, so a
    wall needs vertices to show a light's falloff."""
    origin, u_axis, v_axis = Vector(origin), Vector(u_axis), Vector(v_axis)
    nu = max(1, round(u_axis.length / step))
    nv = max(1, round(v_axis.length / step))
    verts = [[bm.verts.new(origin + u_axis * (i / nu) + v_axis * (j / nv)) for j in range(nv + 1)]
             for i in range(nu + 1)]
    for i in range(nu):
        for j in range(nv):
            face = bm.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][j + 1], verts[i][j + 1]))
            face.material_index = SLOTS.index(slot)
            for loop in face.loops:
                offset = loop.vert.co - origin
                loop[uv_layer].uv = (offset.dot(u_axis.normalized()) / tile,
                                     offset.dot(v_axis.normalized()) / tile)


def _box(bm, uv_layer, low, high, slot, step=1.0):
    """A closed box with outward faces, each cut into ~step quads."""
    x0, y0, z0 = low
    x1, y1, z1 = high
    dx, dy, dz = (x1 - x0, 0, 0), (0, y1 - y0, 0), (0, 0, z1 - z0)
    grid = lambda origin, u, v: _grid(bm, uv_layer, origin, u, v, slot, step)
    grid((x0, y0, z0), dy, dx)          # bottom
    grid((x0, y0, z1), dx, dy)          # top
    grid((x0, y0, z0), dx, dz)          # south
    grid((x1, y1, z0), tuple(-c for c in dx), dz)   # north
    grid((x1, y0, z0), dy, dz)          # east
    grid((x0, y1, z0), tuple(-c for c in dy), dz)   # west


def _mesh_object(name, build, collection):
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    build(bm, uv_layer)
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    for material in _materials():
        mesh.materials.append(material)
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    return obj


_loaded_materials = None


def _materials():
    global _loaded_materials
    if _loaded_materials is None:
        with bpy.data.libraries.load(MATERIAL_LIBRARY, link=False) as (source, target):
            missing = [name for name in MATERIALS.values() if name not in source.materials]
            if missing:
                raise SystemExit(f"Not in {MATERIAL_LIBRARY}: {missing}")
            target.materials = list(MATERIALS.values())
        _loaded_materials = list(target.materials)
    return _loaded_materials


POSTS = []          # (x, y, height): filled by the scale station, built into the level mesh


def build_level_mesh():
    collection = _collection("Level Mesh")

    def ground_and_hall(bm, uv_layer):
        # Ground outside, stone floor inside the hall (separate grids that
        # share the hall's outline, so there is no hidden ground under it).
        x0, x1 = HALL_X0 - WALL, HALL_X1 + WALL
        y0, y1 = HALL_Y0 - WALL, HALL_Y1 + WALL
        flat = lambda low, high, slot: _grid(
            bm, uv_layer, (low[0], low[1], 0.0), (high[0] - low[0], 0, 0), (0, high[1] - low[1], 0), slot)
        flat((-GROUND_X, -GROUND_Y), (GROUND_X, y0), "ground")
        flat((-GROUND_X, y0), (x0, y1), "ground")
        flat((x1, y0), (GROUND_X, y1), "ground")
        flat((-GROUND_X, y1), (GROUND_X, GROUND_Y), "ground")
        flat((x0, y0), (x1, y1), "floor")
        # Walls: south with the door gap, north, west, east.
        _box(bm, uv_layer, (x0, y0, 0.0), (-DOOR_HALF, HALL_Y0, HALL_HEIGHT), "wall")
        _box(bm, uv_layer, (DOOR_HALF, y0, 0.0), (x1, HALL_Y0, HALL_HEIGHT), "wall")
        _box(bm, uv_layer, (-DOOR_HALF, y0, DOOR_HEIGHT), (DOOR_HALF, HALL_Y0, HALL_HEIGHT), "wall")
        _box(bm, uv_layer, (x0, HALL_Y1, 0.0), (x1, y1, HALL_HEIGHT), "wall")
        _box(bm, uv_layer, (x0, HALL_Y0, 0.0), (HALL_X0, HALL_Y1, HALL_HEIGHT), "wall")
        _box(bm, uv_layer, (HALL_X1, HALL_Y0, 0.0), (x1, HALL_Y1, HALL_HEIGHT), "wall")
        # A wall across the doorway inside keeps daylight off the test floor.
        _box(bm, uv_layer, (-3.0, HALL_Y0 + 2.2, 0.0), (3.0, HALL_Y0 + 2.2 + WALL, HALL_HEIGHT), "wall")
        for x, y, post_height in POSTS:
            _box(bm, uv_layer, (x - 0.12, y - 0.12, 0.0), (x + 0.12, y + 0.12, post_height), "wall", step=4.0)

    def roof(bm, uv_layer):
        _box(bm, uv_layer, (HALL_X0 - WALL, HALL_Y0 - WALL, HALL_HEIGHT),
             (HALL_X1 + WALL, HALL_Y1 + WALL, HALL_HEIGHT + 0.3), "wall", step=2.0)

    level = _mesh_object("BZ_CHECK_LEVEL", ground_and_hall, collection)
    hall_roof = _mesh_object("BZ_CHECK_ROOF", roof, collection)     # hide it to look into the hall
    return level, hall_roof


# -- vob helpers ----------------------------------------------------------------------

_current_collection = None


def _collection(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def station(name):
    global _current_collection
    _current_collection = _collection(name)


def add(type_id, name, location, rotation_z=0.0, preset=None, scale=None, **settings):
    """A vob through the same code path as the Add VOB dialog."""
    context = bpy.context
    location = Vector(location).to_3d() if len(location) == 2 else Vector(location)
    context.scene.cursor.location = location
    obj = vob_ops.create_vob(context, type_id, name, preset)
    if rotation_z:
        obj.rotation_mode = 'XYZ'
        obj.rotation_euler = (0.0, 0.0, math.radians(rotation_z))
    if scale:
        obj.scale = scale
    for key, value in settings.items():
        obj[key] = value
    for user in list(obj.users_collection):
        user.objects.unlink(obj)
    _current_collection.objects.link(obj)
    return obj


_bounds_cache = {}


def mesh_bounds(visual):
    """(lowest z, highest z, widest half extent in x/y) of a prop's mesh, in
    metres at scale 1; (0, 0, 0) when the mesh is not available."""
    if visual not in _bounds_cache:
        probe = bpy.data.objects.new(f"zCVob:{visual}", None)
        bpy.context.scene.collection.objects.link(probe)
        vob_preview.apply_previews(bpy.context, [probe], use_game_files=True)
        collection = probe.instance_collection
        corners = [mesh.matrix_basis @ Vector(corner)
                   for mesh in (collection.objects if collection else ()) for corner in mesh.bound_box]
        bpy.data.objects.remove(probe)
        _bounds_cache[visual] = (
            (min(c.z for c in corners), max(c.z for c in corners),
             max(max(abs(c.x), abs(c.y)) for c in corners)) if corners else (0.0, 0.0, 0.0))
    return _bounds_cache[visual]


def prop(visual, x, y, rotation_z=0.0, scale=(1.0, 1.0, 1.0)):
    """A plain prop standing on the ground, with no settings of its own."""
    low, high, _ = mesh_bounds(visual)
    base = 0.0 if high > 6.0 else -low           # trees keep their roots in the ground
    return add("zCVob", visual, (x, y, base * scale[2]), rotation_z=rotation_z,
               scale=None if scale == (1.0, 1.0, 1.0) else scale)


SIGN_TEXTS = {}


def sign(key, text, x, y, rotation_z=0.0):
    """An instruction, shown as a sign's focus name. A focus name only shows
    if it is a script string constant: these go into Text.d."""
    constant = f"MOBNAME_BZ_{key}"
    SIGN_TEXTS[constant] = text
    return add("oCMOB", f"BZ_SIGN_{key}", (x, y, 0.0), rotation_z=rotation_z, preset="SIGN",
               focus_name=constant)


# -- the stations ------------------------------------------------------------------------

def station_start():
    station("1 Spacer")
    add("zCVobStartpoint", "PC_START", (0.0, -15.0, 0.2))
    sign("START", "1: This world must have opened in Spacer without an error box", 1.5, -13.0)
    # One of each thing the file check looks at.
    add("zCVobSpot", "FP_ROAM_BZ_CHECK_01", (-2.0, -13.0, 0.0))
    add("oCZoneMusicDefault", "DEFAULT_DEF", (-20.0, -16.0, 5.0))


def station_lights():
    station("2 Lights")
    sign("LIGHTS", "2: Go in. Each light must reach its two barrels and no further", 2.6, HALL_Y0 - 1.2)
    for index, (x, reach) in enumerate(LIGHTS):
        light = add("zCVobLight", f"BZ_LIGHT_{int(reach)}M", (x, LIGHT_Y, LIGHT_HEIGHT))
        from zen_gin_export import gothic_range_to_blender_power
        light.data.use_custom_distance = True
        light.data.cutoff_distance = reach
        light.data.energy = gothic_range_to_blender_power(reach * 100.0)   # the add-on's calibration
        light.data.color = (1.0, 1.0, 1.0)
        on_floor = math.sqrt(reach ** 2 - LIGHT_HEIGHT ** 2)     # where the light reaches zero
        for side in (-1.0, 1.0):
            prop(BARREL, x + side * on_floor, LIGHT_Y, rotation_z=30.0 * index)


def station_waypoints():
    station("3 Waypoints")
    sign("ALIGN", "3: Each man must face the barrel in front of him", ALIGN_CENTRE.x, ALIGN_CENTRE.y)
    waypoints = []
    for index, heading in enumerate(ALIGN_HEADINGS):
        corner = Vector((-3.5 if index % 2 == 0 else 3.5, 3.5 if index < 2 else -3.5))
        position = ALIGN_CENTRE + corner
        angle = math.radians(heading)
        direction = Vector((-math.sin(angle), math.cos(angle)))    # where local +Y points
        marker = prop(BARREL, *(position + direction * 2.5))
        waypoint = bpy.data.objects.new(f"zCWaypoint:BZ_ALIGN_{index + 1}", None)
        setup_waypoint_empty(waypoint)
        waypoint.location = (position.x, position.y, 0.0)
        _current_collection.objects.link(waypoint)
        aim_waypoint_at(waypoint, marker)          # the same call the Link Waypoints button uses
        waypoints.append(waypoint.name.partition(":")[2])
    return waypoints


def station_scale():
    station("4 Scale")
    low, high, half_width = mesh_bounds(BARREL)
    sign("SCALE", "4: The top of each barrel must be level with its stone post", SCALE_ROW_X - 2.2, SCALE_ROW_Y)
    for index, scale in enumerate(SCALES):
        x = SCALE_ROW_X + index * 3.5
        prop(BARREL, x, SCALE_ROW_Y, scale=scale)
        POSTS.append((x + half_width * scale[0] + 0.35, SCALE_ROW_Y, (high - low) * scale[2]))


def station_plants():
    station("5 Plants")
    from zen_gin_export.vanilla_survey import visual_defaults
    from zen_gin_export.vob_fields import base_default
    parts = []
    for index, visual in enumerate(PLANTS):
        x = PLANT_ROW_X + index * 4.5
        prop(visual, x, PLANT_ROW_Y)
        sways = base_default("zCVob", "ani_mode", visual) != "NONE"
        blocks = bool(base_default("zCVob", "cd_dyn", visual))
        name = visual.split("_")[2].capitalize()
        parts.append(f"{name} {'sways' if sways else 'still'}, {'stops you' if blocks else 'walk through'}")
        if not visual_defaults("zCVob", visual):
            print(f"[check_level] note: {visual} has no vanilla defaults (plain prop settings)")
    prop(BARREL, PLANT_ROW_X + len(PLANTS) * 4.5, PLANT_ROW_Y)
    sign("PLANTS", "5: " + ". ".join(parts) + ". Barrel stops you", PLANT_ROW_X - 2.5, PLANT_ROW_Y)


# -- game scripts ---------------------------------------------------------------------

_BEGIN = b"// >>> Blend-Zen check level (generated, do not edit)"
_END = b"// <<< Blend-Zen check level"


def _replace_block(path, lines):
    """Put lines between the marker comments at the end of a script file,
    replacing an earlier block. Bytes in, bytes out: the rest of the file
    (windows-1250 text) is not touched."""
    with open(path, "rb") as handle:
        content = handle.read()
    start, end = content.find(_BEGIN), content.find(_END)
    if start >= 0 and end > start:
        content = content[:start].rstrip() + content[end + len(_END):]
    newline = b"\r\n" if b"\r\n" in content else b"\n"
    block = [_BEGIN] + [line.encode("ascii") for line in lines] + [_END]
    with open(path, "wb") as handle:
        handle.write(content.rstrip() + newline * 2 + newline.join(block) + newline)
    return content


def write_game_scripts(game_folder, level_name, waypoints):
    """Sign texts, the test NPCs and the level's startup functions. Returns
    the list of files written (empty without a game folder)."""
    from zen_gin_export.game_data import find_data_dir, _path
    data = find_data_dir(game_folder) if game_folder else None
    story = _path(data, "Scripts", "Content", "Story") if data else None
    if not story:
        return []
    written = []

    text = _path(story, "Text.d")
    if text:
        _replace_block(text, [f'CONST STRING {name} = "{value}";' for name, value in SIGN_TEXTS.items()])
        written.append(text)

    npc_dir = _path(story, "NPC")
    if npc_dir:
        lines = ["// Blend-Zen check level: one man per test waypoint. He stands with his arms",
                 "// crossed, which ends in AI_AlignToWP: he turns to the waypoint's direction.",
                 "// Generated by tooling/pipeline/build_check_level.py; overwritten on every run.", ""]
        for index, waypoint in enumerate(waypoints):
            instance = f"BZ_CHECK_ALIGN_{index + 1}"
            lines += [
                f"instance {instance} (Npc_Default)", "{",
                f'\tname\t\t\t= "Faces his barrel ({index + 1})";',
                "\tguild\t\t\t= GIL_NONE;", f"\tid\t\t\t\t= {9100 + index + 1};", "\tvoice\t\t\t= 1;",
                "\tflags\t\t\t= NPC_FLAG_IMMORTAL;", "\tnpctype\t\t\t= NPCTYPE_MAIN;", "\tlevel\t\t\t= 1;",
                "\tattribute[ATR_STRENGTH]\t\t= 10;", "\tattribute[ATR_DEXTERITY]\t= 10;",
                "\tattribute[ATR_MANA_MAX]\t\t= 10;", "\tattribute[ATR_MANA]\t\t\t= 10;",
                "\tattribute[ATR_HITPOINTS_MAX]= 40;", "\tattribute[ATR_HITPOINTS]\t= 40;",
                '\tB_SetNpcVisual\t\t(self, MALE, "HUM_HEAD_BALD", Face_N_Player, BodyTex_N, -1);',
                "\tMdl_SetModelFatness\t(self, 0);", "\tfight_tactic\t= FAI_HUMAN_STRONG;",
                "\tB_SetFightSkills\t(self, 1);", f"\tdaily_routine\t= Rtn_{instance};", "};", "",
                f"FUNC VOID Rtn_{instance}()", "{",
                f'\tTA_Stand_ArmsCrossed\t(08,00,20,00,"{waypoint}");',
                f'\tTA_Stand_ArmsCrossed\t(20,00,08,00,"{waypoint}");', "};", ""]
        path = os.path.join(npc_dir, "BZ_Check_Align.d")
        with open(path, "wb") as handle:
            handle.write("\r\n".join(lines).encode("ascii"))
        written.append(path)

    startup = _path(story, "Startup.d")
    if startup:
        name = level_name.upper()
        lines = [f"func void STARTUP_{name}()", "{"]
        lines += [f'\tWld_InsertNpc\t(BZ_CHECK_ALIGN_{i + 1}, "{wp}");' for i, wp in enumerate(waypoints)]
        lines += ["};", "", f"func void INIT_{name}()", "{", "\tB_InitMonsterAttitudes();",
                  "\tB_InitGuildAttitudes();", "\tB_InitNpcGlobals();", "};"]
        rest = _replace_block(startup, lines)
        if re.search(rb"(?i)func\s+void\s+STARTUP_" + name.encode("ascii") + rb"\s*\(", rest):
            print(f"[check_level] WARNING: Startup.d already had its own STARTUP_{name}: "
                  f"remove that one, the generated block defines it")
        written.append(startup)
    return written


# -- checks and presentation ------------------------------------------------------------

def check_exported_file(zen_path):
    """The file-level half of station 1. Prints PASS/FAIL per rule and
    returns True when all pass."""
    with open(zen_path, encoding="latin-1") as handle:
        text = handle.read()
    blocks = re.split(r"\n\s*\[% ", text)
    lights = [b for b in blocks if b.startswith("zCVobLight")]
    static = [b for b in lights if "lightStatic=bool:1" in b]
    spots = [b for b in blocks if b.startswith("zCVobSpot")]
    results = [
        ("floats have no trailing .0", not re.search(r"=float:-?\d+\.0\s", text)),
        (f"{len(static)} static light(s) carry no dynamic fields",
         bool(static) and not any("rangeAniScale" in b or "colorAniList" in b for b in static)),
        (f"{len(spots)} freepoint(s) have zbias=1", bool(spots) and all("zbias=int:1" in b for b in spots)),
    ]
    for label, passed in results:
        print(f"[check_level] {'PASS' if passed else 'FAIL'}  {label}")
    return all(passed for _, passed in results)


def setup_presentation(level, roof):
    scene = bpy.context.scene
    world = bpy.data.worlds.new("Gothic Sky")
    world.use_nodes = True
    nodes, links = world.node_tree.nodes, world.node_tree.links
    environment = nodes.new("ShaderNodeTexEnvironment")
    environment.image = bpy.data.images.load(SKY_HDR)
    mapping = nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value[2] = math.radians(40.0)
    coordinates = nodes.new("ShaderNodeTexCoord")
    links.new(coordinates.outputs["Generated"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], environment.inputs["Vector"])
    links.new(environment.outputs["Color"], nodes["Background"].inputs["Color"])
    scene.world = world
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    engines = [e.identifier for e in type(scene.render).bl_rna.properties["engine"].enum_items]
    scene.render.engine = "BLENDER_EEVEE" if "BLENDER_EEVEE" in engines else "BLENDER_EEVEE_NEXT"
    for screen in bpy.data.screens:
        for space in (s for a in screen.areas for s in a.spaces if s.type == 'VIEW_3D'):
            space.shading.type = 'MATERIAL'
            space.shading.use_scene_world = True
            space.shading.use_scene_lights = True
            space.clip_end = 500.0
    for obj in scene.objects:
        obj.select_set(obj in (level, roof))
    bpy.context.view_layer.objects.active = level


def render_lights_reference(path, roof):
    """A straight-down picture of the hall floor with the roof off and no
    sky light: what the three lights should look like in Spacer."""
    scene = bpy.context.scene
    camera = bpy.data.objects.new("LightsReferenceCamera", bpy.data.cameras.new("LightsReferenceCamera"))
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = HALL_X1 - HALL_X0 + 1.0
    camera.location = ((HALL_X0 + HALL_X1) / 2.0, (HALL_Y0 + HALL_Y1) / 2.0, 30.0)
    _collection("Level Mesh").objects.link(camera)
    scene.camera = camera
    background = scene.world.node_tree.nodes["Background"]
    strength = background.inputs["Strength"].default_value
    background.inputs["Strength"].default_value = 0.0
    roof.hide_render = True
    scene.render.resolution_x, scene.render.resolution_y = 1900, 620
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    roof.hide_render = False
    background.inputs["Strength"].default_value = strength


def build():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    station_start()
    station_lights()
    waypoints = station_waypoints()
    station_scale()
    station_plants()
    level, roof = build_level_mesh()             # after the stations: they add the posts
    bpy.context.view_layer.update()
    return level, roof, waypoints


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) not in (1, 3):
        raise SystemExit(__doc__)
    blend_path = os.path.abspath(args[0])

    level, roof, waypoints = build()
    previews = vob_preview.apply_previews(bpy.context, list(bpy.context.scene.objects), use_game_files=True)
    print(f"[check_level] previews: {vob_preview.summary(previews)}")
    setup_presentation(level, roof)
    reference = os.path.splitext(blend_path)[0] + "_lights_reference.png"
    render_lights_reference(reference, roof)
    print(f"[check_level] lights reference: {reference}")
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    print(f"[check_level] saved {blend_path}")

    if len(args) == 3:
        level_name, mod_name = args[1], args[2]
        result = bpy.ops.zen.quick_export_package(level_name=level_name, mod_name=mod_name)
        if result != {'FINISHED'}:
            raise SystemExit(f"[check_level] export did not finish: {result}")
        bpy.ops.wm.save_mainfile()      # keeps the level compo the export created
        from zen_waypoint_tools.preferences import get_gothic_settings
        game_folder = get_gothic_settings()[0]
        export_root = game_folder or os.path.join(os.path.dirname(blend_path), "export")
        zen_path = os.path.join(export_root, "_work", "Data", "Worlds", mod_name, f"{level_name}_uncompiled.zen")
        check_exported_file(zen_path)
        for path in write_game_scripts(game_folder, level_name, waypoints):
            print(f"[check_level] wrote {path}")
        print(f"[check_level] exported level package {mod_name}/{level_name}")


if __name__ == "__main__":
    main()
