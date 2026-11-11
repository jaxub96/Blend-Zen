"""Builds the showcase level: a 30 x 30 m forest hollow that looks like a
piece of a Gothic world and uses every kind of vob Blend-Zen writes.

    blender --background --python tooling/pipeline/build_showcase_level.py -- \
        blender_work_dir/showcase_level.blend [LEVEL_NAME MOD_NAME]

Run it with your normal Blender profile (no --factory-startup): it needs
"Zen Waypoint Tools" enabled, the Gothic Game Folder set (names are checked
against the game files) and, for the preview meshes, the Gothic asset
library. With a level and mod name it also runs Export Level Package.

The place (+Y is north, the player starts at the south end of the path):

  the hollow      grass floor with a dirt path, ringed by rock and firs.
                  Trees, bushes, ferns and grass are plain props: their wind
                  and collision settings are the vanilla defaults per mesh.
  hermit's hut    north-west. A door, a bed, a locked chest (key on a grave,
                  or pick LRL), an alchemy table with its flask, a bookstand;
                  a wall torch with flame, flare, light and sound as child
                  vobs; a static light; a cobweb decal. Xardas' theme plays
                  inside (music zone), the default theme outside.
  campfire        centre. Fire and smoke effects, a preset light, a looping
                  sound, fire damage if you step in (touch damage), benches,
                  a cauldron, a pan, food and gold to pick up, freepoints.
  graveyard       south-west. Gravestones with focus names, a standing lamp
                  to light, ground fog, a crow now and then (random sound),
                  thick green fog (fog zone) and a short view distance
                  (far-plane zone); defaults for both elsewhere.
  shrine          north-east. Walking up to it fires a script trigger
                  (teleport ring + sound). The winch starts a trigger list:
                  fire on the altar at once, an earthquake 2 s later. Both
                  levers together (code master) light the second fire. A
                  lens flare, a flag and a swaying bush (morph meshes).
  gate            east. The lever raises the gate (mover, two keyframes,
                  gate sounds); the passage behind it loads another world
                  (level change trigger).
  around          birds by day, frogs by night (day/night sound), birds
                  that fly up when the world starts (world-start trigger ->
                  effect), butterflies where you enter the meadow (touch
                  trigger -> effect), herbs to pick, a waynet.

Not in it: cutscene cameras (unsupported), message filter and untouch
trigger (they only make sense inside a larger script setup).
"""

import math
import os
import random
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

from zen_waypoint_tools import vob_ops, vob_ui, vob_preview, game_bridge
from zen_waypoint_tools.waypoint_links import add_directed_link, setup_waypoint_empty

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MATERIAL_LIBRARY = os.path.join(_REPO, "asset_catalog", "materials_levels.blend")
SKY_HDR = os.path.join(_REPO, "asset_catalog", "sky", "gothic_sky.hdr")
LEVEL_MESH_NAME = "SHOWCASE_LEVEL"

SIZE = 30.0                 # metres, the whole level
HALF = SIZE / 2.0
STEP = 1.0                  # terrain quad size
RIM_START = 10.5            # the ground starts to rise this far from the centre
RIM_HEIGHT = 5.5

MATERIALS = {               # slot -> material in materials_levels.blend
    "grass": "NW_Nature_Grass_01",
    "path": "NW_Nature_Waldboden_03",
    "rock": "NW_Nature_DarkWood_Fels_01",
    "wall": "NW_City_StoneWall_01",
    "floor": "NW_City_BodenDielen_01",
    "roof": "NW_City_Roof_01",
    "beam": "NW_City_WoodBeam_01",
}
SLOTS = list(MATERIALS)

# Hut: outer footprint and the door gap in its south wall.
HUT_X0, HUT_X1, HUT_Y0, HUT_Y1 = -10.0, -4.0, 3.5, 8.5
HUT_FLOOR = 0.12
WALL_HEIGHT, WALL_THICK = 3.0, 0.4
DOOR_X, DOOR_WIDTH, DOOR_HEIGHT = -7.0, 1.3, 2.3

CAMPFIRE = Vector((3.0, -2.0))
GRAVEYARD = Vector((-8.0, -8.0))
SHRINE = Vector((7.5, 8.5))
GATE_X = 12.5
GATE_HALF_WIDTH = 3.2          # EVT_GATE_SMALL_01 is 6.4 m wide, 4 m high
GATE_HEIGHT = 4.0

# Dirt paths, as polylines.
PATHS = [
    [(0.0, -14.0), (0.0, -5.0), (2.0, -3.2)],                      # entrance -> campfire
    [(0.0, -5.0), (-5.0, 0.5), (-7.0, 3.3)],                        # -> hut door
    [(2.0, -3.2), (7.0, -0.5), (15.0, 0.0)],                        # campfire -> gate
    [(2.0, -3.2), (4.5, 3.0), (7.0, 6.5)],                          # campfire -> shrine
    [(0.0, -5.0), (-4.0, -7.0), (-7.0, -7.0)],                      # -> graveyard
]
PATH_HALF_WIDTH = 1.15


# -- terrain ----------------------------------------------------------------------

def _smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def _noise(x, y):
    return (math.sin(x * 0.9 + 1.3) * math.cos(y * 0.7 - 0.4)
            + 0.5 * math.sin(x * 2.1 - y * 1.7)) / 1.5


def _in_gate_passage(x, y):
    return x > 8.0 and abs(y) < GATE_HALF_WIDTH


def _flat_weight(x, y):
    """1 where the ground must be level (hut, gate passage), fading to 0."""
    dx = max(HUT_X0 - x, 0.0, x - HUT_X1)
    dy = max(HUT_Y0 - y, 0.0, y - HUT_Y1)
    hut = 1.0 - _smooth(math.hypot(dx, dy) / 2.0)
    gate = (1.0 - _smooth((abs(y) - GATE_HALF_WIDTH) / 1.5)) * _smooth((x - 7.0) / 2.0)
    return max(hut, gate)


def height(x, y):
    """Ground height in metres: a gently uneven floor inside a rock rim."""
    distance = max(abs(x), abs(y))
    rim = _smooth((distance - RIM_START) / (HALF - RIM_START)) * RIM_HEIGHT
    rim *= 1.0 + 0.2 * _noise(x * 0.45, y * 0.45)
    floor = 0.18 * _noise(x, y)
    return (floor + rim) * (1.0 - _flat_weight(x, y))


def _distance_to_paths(x, y):
    point = Vector((x, y))
    best = 1e9
    for line in PATHS:
        for a, b in zip(line, line[1:]):
            a, b = Vector(a), Vector(b)
            t = max(0.0, min(1.0, (point - a).dot(b - a) / (b - a).length_squared))
            best = min(best, (point - (a + (b - a) * t)).length)
    return best


def _add_terrain(bm, uv_layer):
    count = int(SIZE / STEP)
    verts = [[bm.verts.new((-HALF + i * STEP, -HALF + j * STEP,
                            height(-HALF + i * STEP, -HALF + j * STEP)))
              for j in range(count + 1)] for i in range(count + 1)]
    for i in range(count):
        for j in range(count):
            face = bm.faces.new((verts[i][j], verts[i + 1][j], verts[i + 1][j + 1], verts[i][j + 1]))
            centre = face.calc_center_median()
            face.normal_update()
            steep = face.normal.z < 0.8
            if steep:
                slot = "rock"
            elif _distance_to_paths(centre.x, centre.y) < PATH_HALF_WIDTH:
                slot = "path"
            else:
                slot = "grass"
            face.material_index = SLOTS.index(slot)
            for loop in face.loops:
                co = loop.vert.co
                # Rock faces are steep: map them along the slope, not from above.
                loop[uv_layer].uv = ((co.x + co.y) / 3.0, co.z / 3.0) if steep else (co.x / 2.5, co.y / 2.5)


def _add_box(bm, uv_layer, low, high, slot, tile=2.5):
    """An axis-aligned box with box-mapped UVs (texture repeats every `tile` m)."""
    x0, y0, z0 = low
    x1, y1, z1 = high
    corners = [bm.verts.new(c) for c in (
        (x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
        (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for indices, axes in (((0, 3, 2, 1), (0, 1)), ((4, 5, 6, 7), (0, 1)),      # bottom, top
                          ((0, 1, 5, 4), (0, 2)), ((2, 3, 7, 6), (0, 2)),      # south, north
                          ((1, 2, 6, 5), (1, 2)), ((3, 0, 4, 7), (1, 2))):     # east, west
        face = bm.faces.new([corners[i] for i in indices])
        face.material_index = SLOTS.index(slot)
        for loop in face.loops:
            loop[uv_layer].uv = (loop.vert.co[axes[0]] / tile, loop.vert.co[axes[1]] / tile)


def _add_hut(bm, uv_layer):
    t, h = WALL_THICK, WALL_HEIGHT
    box = lambda low, high, slot: _add_box(bm, uv_layer, low, high, slot)
    box((HUT_X0, HUT_Y0, 0.0), (HUT_X1, HUT_Y1, HUT_FLOOR), "floor")
    # South wall with the door gap, then west, east (broken down to a stump
    # at its south end: this is a ruin) and north.
    door0, door1 = DOOR_X - DOOR_WIDTH / 2.0, DOOR_X + DOOR_WIDTH / 2.0
    box((HUT_X0, HUT_Y0, 0.0), (door0, HUT_Y0 + t, h), "wall")
    box((door1, HUT_Y0, 0.0), (HUT_X1, HUT_Y0 + t, h), "wall")
    box((door0, HUT_Y0, DOOR_HEIGHT), (door1, HUT_Y0 + t, h), "wall")
    box((HUT_X0, HUT_Y0 + t, 0.0), (HUT_X0 + t, HUT_Y1, h), "wall")
    box((HUT_X1 - t, HUT_Y0 + t, 0.0), (HUT_X1, HUT_Y0 + 1.8, 1.1), "wall")
    box((HUT_X1 - t, HUT_Y0 + 1.8, 0.0), (HUT_X1, HUT_Y0 + 2.6, 2.0), "wall")
    box((HUT_X1 - t, HUT_Y0 + 2.6, 0.0), (HUT_X1, HUT_Y1, h), "wall")
    box((HUT_X0 + t, HUT_Y1 - t, 0.0), (HUT_X1 - t, HUT_Y1, h), "wall")
    # Roof over the back (north) two thirds, on three beams.
    roof_y0 = HUT_Y0 + 1.7
    for x in (HUT_X0 + 0.2, (HUT_X0 + HUT_X1) / 2.0 - 0.1, HUT_X1 - 0.4):
        box((x, HUT_Y0, h), (x + 0.2, HUT_Y1 + 0.3, h + 0.2), "beam")
    box((HUT_X0 - 0.3, roof_y0, h + 0.2), (HUT_X1 + 0.3, HUT_Y1 + 0.4, h + 0.32), "roof")


def _add_gate_frame(bm, uv_layer):
    """Two stone posts and a lintel for the gate to slide in."""
    for side in (-1.0, 1.0):
        y = side * (GATE_HALF_WIDTH + 0.45)
        _add_box(bm, uv_layer, (GATE_X - 0.45, y - 0.45, 0.0), (GATE_X + 0.45, y + 0.45, GATE_HEIGHT + 0.3), "wall")
    _add_box(bm, uv_layer, (GATE_X - 0.45, -GATE_HALF_WIDTH - 0.9, GATE_HEIGHT + 0.3),
             (GATE_X + 0.45, GATE_HALF_WIDTH + 0.9, GATE_HEIGHT + 0.9), "wall")


def build_level_mesh():
    bm = bmesh.new()
    uv_layer = bm.loops.layers.uv.new("UVMap")
    _add_terrain(bm, uv_layer)
    _add_hut(bm, uv_layer)
    _add_gate_frame(bm, uv_layer)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    mesh = bpy.data.meshes.new(LEVEL_MESH_NAME)
    bm.to_mesh(mesh)
    bm.free()

    with bpy.data.libraries.load(MATERIAL_LIBRARY, link=False) as (source, target):
        missing = [name for name in MATERIALS.values() if name not in source.materials]
        if missing:
            raise SystemExit(f"Not in {MATERIAL_LIBRARY}: {missing}")
        target.materials = list(MATERIALS.values())
    for material in target.materials:
        mesh.materials.append(material)

    obj = bpy.data.objects.new(LEVEL_MESH_NAME, mesh)
    _collection("Level Mesh").objects.link(obj)
    return obj


# -- vob helpers ------------------------------------------------------------------

_current_collection = None


def _collection(name):
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def area(name):
    """Vobs added from now on go into this collection (tidy outliner)."""
    global _current_collection
    _current_collection = _collection(name)


def ground(x, y, lift=0.0):
    return Vector((x, y, height(x, y) + lift))


def add(type_id, name, location, rotation_z=0.0, preset=None, parent=None, box=None, **settings):
    """A vob through the same code path as the Add VOB dialog, then its
    settings as custom properties. location: (x, y) puts it on the ground,
    (x, y, z) is absolute. box: half extents in metres."""
    context = bpy.context
    if len(location) == 2:
        location = ground(*location)
    context.scene.cursor.location = location
    obj = vob_ops.create_vob(context, type_id, name, preset)
    if preset:                                   # presets lift levers and bookstands
        obj.location.z = location[2] + obj.location.z - context.scene.cursor.location.z
    if rotation_z:
        obj.rotation_mode = 'XYZ'
        obj.rotation_euler = (0.0, 0.0, math.radians(rotation_z))
    if box:
        obj.scale = box
    for key, value in settings.items():
        obj[key] = value
    if _current_collection is not None:
        for user in list(obj.users_collection):
            user.objects.unlink(obj)
        _current_collection.objects.link(obj)
    if parent is not None:
        context.view_layer.update()
        world = obj.matrix_world.copy()
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
        obj.matrix_world = world
    return obj


_base_cache = {}


def _base_below_origin(obj):
    """How far the vob's mesh reaches below its origin, in metres (0 when
    the mesh is not available). Many Gothic props have their origin in the
    middle, so standing them on the ground means lifting them by this."""
    key = (obj.name.partition(":")[0], str(obj.get("visual_name", "")) or obj.name.partition(":")[2].split(".")[0])
    if key not in _base_cache:
        vob_preview.apply_previews(bpy.context, [obj], use_game_files=True)
        collection = obj.instance_collection
        lows = [(mesh.matrix_basis @ Vector(corner)).z
                for mesh in (collection.objects if collection else ()) for corner in mesh.bound_box]
        tops = [(mesh.matrix_basis @ Vector(corner)).z
                for mesh in (collection.objects if collection else ()) for corner in mesh.bound_box]
        # Trees keep their roots in the ground: that is what the part below
        # the origin is for.
        _base_cache[key] = 0.0 if not lows or max(tops) > 6.0 else max(0.0, -min(lows))
    return _base_cache[key]


def prop(visual, location, rotation_z=0.0, on_ground=True, **settings):
    """A plain prop. on_ground: lift it so its mesh stands on `location`."""
    obj = add("zCVob", visual, location, rotation_z=rotation_z, **settings)
    if on_ground:
        obj.location.z += _base_below_origin(obj) - 0.03
    return obj


def dynamic_light(name, location, colour, reach=6.0, parent=None):
    light = add("zCVobLight", name, location, parent=parent, light_static=False,
                range_ani_scale="1.0 0.85 1.1 0.9", range_ani_fps=4.0,
                color_ani_list="(255 150 60) (255 100 30) (240 170 80)", color_ani_fps=3.0)
    light.data.color = colour
    light.data.cutoff_distance = reach
    light.data.use_shadow = False
    return light


# -- the places ---------------------------------------------------------------------

def place_hut():
    area("Hut")
    floor = HUT_FLOOR
    add("oCMobDoor", "DOOR_HUT", (DOOR_X, HUT_Y0 + WALL_THICK / 2.0, floor), preset="DOOR_NORMAL")
    add("oCMobBed", "BED_HUT", (HUT_X0 + 1.3, HUT_Y1 - 1.6, floor), rotation_z=90.0, preset="BED_NORMAL")
    add("oCMobContainer", "CHEST_HUT", (HUT_X1 - 1.2, HUT_Y1 - 1.0, floor), rotation_z=180.0,
        preset="CHEST_BIG", locked=True, key_instance="ITKE_BANDIT", picklock_str="LRL",
        contains="ItMi_Gold:80,ItPo_Health_01:2,ItFo_Wine:1")
    add("oCMobInter", "LAB_HUT", (HUT_X0 + 1.2, HUT_Y0 + 1.3, floor), rotation_z=90.0, preset="LAB")
    add("oCItem", "ITMI_FLASK", (HUT_X0 + 2.2, HUT_Y0 + 1.0, floor + 0.05))
    add("oCMobInter", "BOOKSTAND_HUT", (HUT_X1 - 1.6, HUT_Y1 - 2.6, floor), rotation_z=-90.0,
        preset="BOOKSTAND")
    prop("NW_CITY_TABLE_PEASANT_01", (-7.0, HUT_Y1 - 1.3, floor))
    add("oCItem", "ITFO_CHEESE", (-7.2, HUT_Y1 - 1.3, floor + 0.85))
    add("oCItem", "ITFO_BREAD", (-6.7, HUT_Y1 - 1.2, floor + 0.85))

    torch_at = Vector((-7.0, HUT_Y1 - WALL_THICK - 0.05, 1.9))
    torch = prop("OW_MISC_WALL_TORCH_01", torch_at, rotation_z=180.0, cd_dyn=False, cd_static=False)
    flame = torch_at + Vector((0.0, -0.25, 0.4))
    add("zCVob@PFX", "TORCH_FLAME", flame, parent=torch, visual_name="FIRE.PFX")
    add("zCVob@DECAL", "TORCH_FLARE", flame, parent=torch, visual_name="ZFLARE6.TGA",
        cam_align="FULL", decal_dim=[25.0, 25.0], decal_alpha_weight=200, decal_ignore_daylight=True)
    dynamic_light("TORCH_LIGHT", flame, (1.0, 0.55, 0.2), parent=torch)
    add("zCVobSound", "TORCH_SOUND", flame, parent=torch, sound_name="TORCH_BURN", sound_radius=500.0)

    lamp = add("zCVobLight", "HUT_LIGHT", (HUT_X0 + 1.5, HUT_Y0 + 1.5, 2.4))
    lamp.data.color = (1.0, 0.85, 0.65)
    lamp.data.cutoff_distance = 4.0
    add("zCVob@DECAL", "HUT_COBWEB", (HUT_X0 + 0.75, HUT_Y1 - 0.75, 2.5), rotation_z=45.0,
        visual_name="OWDISPIDERWEB.TGA", cam_align="NONE", decal_dim=[70.0, 70.0],
        decal_alpha_func="BLEND")

    centre = ((HUT_X0 + HUT_X1) / 2.0, (HUT_Y0 + HUT_Y1) / 2.0, 1.8)
    add("oCZoneMusic", "HUT_XAR", centre,
        box=((HUT_X1 - HUT_X0) / 2.0, (HUT_Y1 - HUT_Y0) / 2.0, 1.8), zone_priority=2)
    # Outside: barrels, a wood pile, a crate against the wall.
    prop("NW_HARBOUR_BARREL_01", (HUT_X1 + 0.7, HUT_Y0 + 3.6), rotation_z=20.0)
    prop("OC_BARREL_V1", (HUT_X1 + 0.8, HUT_Y0 + 4.5), rotation_z=75.0)
    prop("NW_HARBOUR_CRATE_01", (HUT_X0 + 1.2, HUT_Y0 - 0.8), rotation_z=12.0)
    prop("OC_SACK_V01", (HUT_X0 + 2.3, HUT_Y0 - 0.6), rotation_z=140.0)


def place_campfire():
    area("Campfire")
    x, y = CAMPFIRE
    prop("OC_FIREPLACE_V1", (x, y))
    fire = ground(x, y, 0.25)
    add("zCVob@PFX", "CAMP_FIRE", fire, visual_name="FIRE.PFX")
    add("zCVob@PFX", "CAMP_SMOKE", fire + Vector((0.0, 0.0, 0.6)), visual_name="FIRE_SMOKE.PFX")
    light = add("zCVobLight", "CAMP_LIGHT", fire + Vector((0.0, 0.0, 0.8)))
    light.zen_vob.light_preset = "FIRESMALL"                 # copies the preset's values
    add("zCVobSound", "CAMP_SOUND", fire, sound_name="CAMPFIRE_BURN", sound_radius=900.0)
    add("oCTouchDamage", "CAMP_BURN", fire + Vector((0.0, 0.0, 0.3)), box=(0.5, 0.5, 0.5),
        touch_damage=5.0, damage_point=False, damage_fire=True)

    add("oCMobInter", "CAMP_BENCH_01", (x - 2.0, y + 0.4), rotation_z=-100.0, preset="BENCH")
    add("oCMobInter", "CAMP_BENCH_02", (x + 0.6, y + 2.0), rotation_z=170.0, preset="BENCH")
    add("oCMobInter", "CAMP_CAULDRON", (x + 1.9, y - 0.6), rotation_z=60.0, preset="CAULDRON")
    add("oCMobInter", "CAMP_PAN", (x - 0.4, y - 1.7), rotation_z=10.0, preset="PAN")
    add("zCVobSpot", "FP_CAMPFIRE_SHOW_01", (x - 1.2, y - 1.2), rotation_z=-45.0)
    add("zCVobSpot", "FP_CAMPFIRE_SHOW_02", (x + 1.3, y + 1.0), rotation_z=135.0)
    add("zCVobSpot", "FP_ROAM_SHOW_01", (x + 4.0, y - 4.5))

    prop("NW_HARBOUR_CRATEPILE_01", (x + 4.0, y - 3.4), rotation_z=25.0)
    prop("NW_HARBOUR_BARREL_01", (x + 5.2, y - 2.2), rotation_z=40.0)
    prop("DT_TABLE_V3", (x + 3.2, y + 0.9), rotation_z=-30.0)
    prop("OC_SACK_V02", (x + 2.6, y - 2.6), rotation_z=80.0)
    for item, dx, dy in (("ITFO_BACON", -1.6, 0.9), ("ITFO_BEER", 0.9, 1.5),
                         ("ITFO_APPLE", 1.1, 1.7), ("ITMI_GOLD", 2.3, -2.3)):
        add("oCItem", item, ground(x + dx, y + dy, 0.05))


def place_graveyard():
    area("Graveyard")
    x, y = GRAVEYARD
    for index, (dx, dy, turn) in enumerate(((-1.6, 0.6, 8.0), (0.0, 0.9, -6.0), (1.6, 0.5, 14.0))):
        add("oCMOB", f"GRAVE_SHOW_{index + 1:02d}", ground(x + dx, y + dy, 0.6), rotation_z=turn,
            preset="GRAVESTONE")
    add("oCItem", "ITKE_BANDIT", ground(x + 0.1, y + 0.3, 0.05))
    add("oCMobFire", "GRAVE_LAMP", (x + 2.6, y - 1.2), preset="FIRE_LAMP")
    prop("NW_NATURE_FENCE_01", (x - 0.2, y - 2.4), rotation_z=4.0)
    prop("NW_NATURE_BAUMSTUMPF_115P", (x - 2.8, y - 1.3), rotation_z=50.0)
    add("zCVob@PFX", "GRAVE_GROUNDFOG", ground(x, y, 0.2), visual_name="GROUNDFOG.PFX")
    add("zCVobSound", "GRAVE_CROW", ground(x, y, 3.0), sound_name="OW_CROW", sound_mode="RANDOM",
        sound_random_delay=6.0, sound_random_delay_var=3.0, sound_radius=1200.0)

    half = (3.6, 3.4, 2.5)
    add("zCZoneZFog", "FOG_GRAVES", ground(x, y, 2.0), box=half, fog_range_center=1200.0,
        inner_range_perc=0.4, fog_color=[70, 105, 75, 255], fog_override_color=True,
        fog_fade_out_sky=True)
    add("zCZoneVobFarPlane", "FARPLANE_GRAVES", ground(x, y, 2.0), box=half,
        vob_far_plane_z=1500.0, inner_range_perc=0.4)


def place_shrine():
    area("Shrine")
    x, y = SHRINE
    add("oCMobInter", "SHRINE_SHOW", (x, y), rotation_z=-145.0, preset="SHRINE")
    prop("NW_NATURE_STONE_CULT_STAND_01", (x + 2.2, y + 1.4), rotation_z=30.0)
    prop("NW_NATURE_STONE_CULT_STAND_01", (x - 1.2, y + 2.6), rotation_z=115.0)
    add("zCVobLensFlare", "SHRINE_FLARE", ground(x, y, 2.6), lensflare_fx="TORCHFX01")

    # Walking up to the shrine: the script function plays the teleport ring.
    add("oCTriggerScript", "EVT_SHRINE_SCRIPT", ground(x - 1.4, y - 1.6, 1.2), box=(1.0, 1.0, 1.2),
        script_func="EVT_TELEPORTSTATION_FUNC")

    # Winch -> trigger list -> fire now, earthquake two seconds later.
    add("oCMobWheel", "WINCH_SHRINE", (x - 3.4, y + 0.8), rotation_z=-90.0, preset="WHEEL",
        trigger_target="EVT_SHRINE_LIST")
    add("zCTriggerList", "EVT_SHRINE_LIST", ground(x - 3.4, y + 0.8, 2.4),
        list_target_0="EVT_SHRINE_FIRE", list_target_1="EVT_SHRINE_QUAKE", list_delay_1=2.0)
    add("zCPFXControler", "EVT_SHRINE_FIRE", ground(x - 0.9, y + 1.2, 0.3), pfx_name="FIRE.PFX",
        pfx_start_on=False, kill_vob_when_done=False)
    add("zCEarthquake", "EVT_SHRINE_QUAKE", ground(x, y), quake_radius=1500.0, quake_time_sec=3.0)

    # Two levers -> code master -> the second fire (only with both pulled).
    add("oCMobSwitch", "LEVER_SHRINE_A", (x + 2.4, y - 2.6), rotation_z=-120.0, preset="LEVER",
        trigger_target="EVT_SHRINE_CODE")
    add("oCMobSwitch", "LEVER_SHRINE_B", (x - 0.2, y - 3.6), rotation_z=-170.0, preset="LEVER",
        trigger_target="EVT_SHRINE_CODE")
    add("zCCodeMaster", "EVT_SHRINE_CODE", ground(x + 1.1, y - 3.1, 2.4),
        trigger_target="EVT_SHRINE_FIRE_2", slave_0="LEVER_SHRINE_A", slave_1="LEVER_SHRINE_B")
    add("zCPFXControler", "EVT_SHRINE_FIRE_2", ground(x + 0.9, y + 1.0, 0.3), pfx_name="FIRE.PFX",
        pfx_start_on=False, kill_vob_when_done=False)

    add("zCVobAnimate", "SHRINE_FLAG", ground(x + 3.2, y - 0.4, 2.2), visual_name="FLAG_MESH")
    add("zCVobAnimate", "SHRINE_BUSH", (x - 2.6, y + 2.8), visual_name="BUSH_MESH")


def place_gate():
    area("Gate")
    # The gate mesh has its origin in the middle: half its height up.
    gate = add("zCMover", "EVT_SHOW_GATE", (GATE_X, 0.0, GATE_HEIGHT / 2.0), rotation_z=90.0,
               visual_name="EVT_GATE_SMALL_01", move_speed=0.1,
               sfx_open_start="GATE_START", sfx_open_end="GATE_STOP", sfx_moving="GATE_LOOP",
               sfx_close_start="GATE_START", sfx_close_end="GATE_STOP")
    bpy.context.view_layer.update()
    vob_ui.mover_keyframes(gate)[1].matrix_basis = Matrix.Translation((0.0, 0.0, GATE_HEIGHT - 0.2))
    add("oCMobSwitch", "LEVER_SHOW_GATE", (GATE_X - 2.4, -GATE_HALF_WIDTH + 0.5), rotation_z=90.0,
        preset="LEVER", trigger_target="EVT_SHOW_GATE")
    add("oCTriggerChangeLevel", "EVT_SHOW_LEVELCHANGE", (14.3, 0.0, 1.5), box=(0.6, 2.6, 1.5),
        level_name="MOD\\FEATURE_TEST_04.ZEN", start_vob_name="PC_START")
    torch = add("oCMobFire", "GATE_TORCH", (GATE_X - 0.6, GATE_HALF_WIDTH + 0.45, 1.7), rotation_z=90.0,
                preset="TORCH_HOLDER")
    return gate, torch


def place_surroundings():
    area("Ambience")
    add("zCVobStartpoint", "PC_START", ground(0.0, -11.5, 0.2))
    add("oCZoneMusicDefault", "DEFAULT_DEF", ground(-13.0, -13.0, 7.0))
    add("zCZoneZFogDefault", "", ground(-12.0, -13.0, 7.0))
    add("zCZoneVobFarPlaneDefault", "", ground(-11.0, -13.0, 7.0))
    add("zCVobSoundDaytime", "BIRDS_AND_FROGS", ground(-2.0, 2.0, 2.0), sound_name="OW_BIRD8",
        sound_name_2="INSECTSFROGS_NIGHT", sound_start_time=6.0, sound_end_time=20.0,
        sound_radius=2500.0, sound_ambient_3d=True)
    add("zCVobSound", "WIND_IN_TREES", ground(-11.0, 11.0, 6.0), sound_name="OW_WINDHIGH1",
        sound_radius=1500.0)

    # World start -> birds fly up from the trees behind the hut.
    add("zCTriggerWorldStart", "EVT_SHOW_START", ground(-12.0, 12.0, 7.0),
        trigger_target="EVT_SHOW_BIRDS")
    add("zCPFXControler", "EVT_SHOW_BIRDS", ground(-11.0, 11.0, 5.0), pfx_name="BIRDFLY.PFX",
        pfx_start_on=False)
    # Walking into the meadow -> butterflies.
    add("zCTrigger", "EVT_SHOW_MEADOW", ground(0.0, -7.5, 1.2), box=(1.5, 1.0, 1.2),
        trigger_target="EVT_SHOW_BUTTERFLIES")
    add("zCPFXControler", "EVT_SHOW_BUTTERFLIES", ground(-2.5, -3.0, 0.6), pfx_name="BUTTERFLY.PFX",
        pfx_start_on=False, kill_vob_when_done=False)
    for item, x, y in (("ITPL_HEALTH_HERB_01", -3.0, -2.2), ("ITPL_MANA_HERB_01", -2.2, -3.6),
                       ("ITPL_MUSHROOM_01", 9.5, -7.5), ("ITPL_FORESTBERRY", -11.0, 0.5)):
        add("oCItem", item, ground(x, y, 0.03))


def _free_spot(x, y, margin):
    """Not on a path, in the hut, at a place of interest or in the gate passage."""
    if max(abs(x), abs(y)) > HALF - 1.2:
        return False
    if _distance_to_paths(x, y) < PATH_HALF_WIDTH + margin:
        return False
    if HUT_X0 - margin - 0.5 < x < HUT_X1 + margin + 1.5 and HUT_Y0 - margin - 1.2 < y < HUT_Y1 + margin:
        return False
    if _in_gate_passage(x, y) or abs(y) < GATE_HALF_WIDTH + 1.0 and x > 9.0:
        return False
    here = Vector((x, y))
    for centre, radius in ((CAMPFIRE, 3.4), (GRAVEYARD, 3.2), (SHRINE, 4.2),
                           (CAMPFIRE + Vector((4.4, -2.8)), 2.0)):
        if (here - centre).length < radius + margin:
            return False
    return True


def scatter_nature():
    area("Nature")
    rng = random.Random(7)
    placed = []

    def scatter(visuals, count, low, high, spacing, margin, keep_view=False):
        """count props at a distance low..high from the centre (square rings).
        keep_view: none in the south, where you enter and look in."""
        tries = 0
        done = 0
        while done < count and tries < count * 80:
            tries += 1
            x, y = rng.uniform(-HALF + 0.8, HALF - 0.8), rng.uniform(-HALF + 0.8, HALF - 0.8)
            distance = max(abs(x), abs(y))
            if not low <= distance <= high or not _free_spot(x, y, margin):
                continue
            if keep_view and y < -8.0 and abs(x) < 7.0:
                continue
            if any((Vector((x, y)) - p).length < spacing for p in placed):
                continue
            placed.append(Vector((x, y)))
            prop(rng.choice(visuals), (x, y), rotation_z=rng.uniform(0.0, 360.0))
            done += 1

    # Firs on the rim, a few slender trees further in, then undergrowth.
    scatter(["NW_NATURE_TANNE_75P", "NW_NATURE_HOHETANNE_59P", "NW_NATURE_HOHETANNE_59P"],
            11, 11.5, 14.0, 4.0, 1.0, keep_view=True)
    scatter(["NW_NATURE_SMALLTREE_79P", "NW_NATURE_SMALLTREE_103P"], 3, 8.5, 11.0, 5.0, 1.5, keep_view=True)
    scatter(["NW_NATURE_STONE_BIGHIGH_01"], 2, 11.5, 13.5, 8.0, 1.5, keep_view=True)
    scatter(["NW_NATURE_BUSH_56P", "NW_NATURE_BUSH_300P", "NW_NATURE_BUSH_300P"], 12, 5.0, 12.5, 2.2, 0.8)
    scatter(["NW_NATURE_FARN_102P", "NW_NATURE_FARN_SMALL_102P"], 7, 6.0, 12.0, 3.0, 1.2)
    scatter(["NW_NATURE_PLANT_01"], 8, 3.0, 11.0, 2.5, 0.8)
    scatter(["NW_NATURE_GRASSGROUP_01"], 6, 4.0, 10.0, 5.0, 2.2)


def build_waynet():
    area("Waynet")
    points = {
        "SHOW_START": (0.0, -11.0), "SHOW_CROSSING": (0.0, -5.0), "SHOW_CAMP": (1.6, -3.4),
        "SHOW_HUT_DOOR": (-6.6, 2.4), "SHOW_HUT": (-7.0, 5.4), "SHOW_GRAVES": (-6.4, -7.0),
        "SHOW_SHRINE": (6.4, 6.0), "SHOW_GATE": (9.5, -0.3),
    }
    objects = {}
    for name, (x, y) in points.items():
        obj = bpy.data.objects.new(f"zCWaypoint:{name}", None)
        setup_waypoint_empty(obj)
        obj.location = (x, y, HUT_FLOOR if name == "SHOW_HUT" else height(x, y))
        _current_collection.objects.link(obj)
        objects[name] = obj
    for source, target in (("SHOW_START", "SHOW_CROSSING"), ("SHOW_CROSSING", "SHOW_CAMP"),
                           ("SHOW_CROSSING", "SHOW_HUT_DOOR"), ("SHOW_HUT_DOOR", "SHOW_HUT"),
                           ("SHOW_CROSSING", "SHOW_GRAVES"), ("SHOW_CAMP", "SHOW_SHRINE"),
                           ("SHOW_CAMP", "SHOW_GATE")):
        add_directed_link(objects[source], objects[target])       # aims source at target


# -- checks and presentation ------------------------------------------------------------

def check_names():
    """Every visual, sound, effect, item and function used must exist in the
    game files. Returns the list of problems (empty without a game folder)."""
    index = game_bridge.get_index(bpy.context)
    if index is None or not index.found:
        return ["no Gothic Game Folder set: names were not checked"]
    known = {source: {n.upper() for n in getattr(index, source)} for source in (
        "meshes", "mob_models", "morph_meshes", "pfx", "textures", "sfx", "items",
        "event_functions", "light_presets", "lensflares", "music_themes")}
    from zen_gin_export.zen_gin_zcvob import vob_name_from_object_name, vob_type_of
    problems = []

    def check(obj, what, name, *sources):
        name = str(name or "").strip().upper()
        if name and not any(name in known[s] for s in sources):
            problems.append(f"{obj.name}: {what} {name} is not in the game files")

    for obj in bpy.context.scene.objects:
        vob_type = vob_type_of(obj)
        if vob_type is None:
            continue
        name = vob_name_from_object_name(obj.name)
        visual = str(obj.get("visual_name", "") or "").strip().upper()
        if vob_type == "zCVob" and not visual:
            visual = name.upper()
        if visual:
            if "." not in visual:
                visual += {"zCVobAnimate": ".MMS", "zCVob": ".3DS", "zCMover": ".3DS",
                           "oCMOB": ".3DS"}.get(vob_type, ".MDS")
            check(obj, "visual", visual, "meshes", "mob_models", "morph_meshes", "pfx", "textures")
        if vob_type == "oCItem":
            check(obj, "item", name, "items")
        if vob_type in ("oCZoneMusic", "oCZoneMusicDefault"):
            check(obj, "music theme", name.rpartition("_")[2], "music_themes")
        for key in obj.keys():
            if key.startswith("sfx_") or key in ("sound_name", "sound_name_2"):
                check(obj, key, obj[key], "sfx")
            elif key == "pfx_name":
                check(obj, key, obj[key], "pfx")
            elif key == "script_func":
                check(obj, key, obj[key], "event_functions")
            elif key == "lensflare_fx":
                check(obj, key, obj[key], "lensflares")
            elif key in ("key_instance", "use_with_item"):
                check(obj, key, obj[key], "items")
    return problems


def setup_presentation(level_mesh):
    """Make the file open looking right: Gothic sky as the world, Standard
    view transform, Material Preview in the 3D viewports, a camera."""
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

    camera = bpy.data.objects.new("ShowcaseCamera", bpy.data.cameras.new("ShowcaseCamera"))
    camera.data.lens = 24.0
    camera.location = (1.0, -17.5, 10.5)
    camera.rotation_euler = (Vector((-0.5, 1.5, 0.0)) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    _collection("Level Mesh").objects.link(camera)
    scene.camera = camera

    for screen in bpy.data.screens:
        for space in (s for a in screen.areas for s in a.spaces if s.type == 'VIEW_3D'):
            space.shading.type = 'MATERIAL'
            space.shading.use_scene_world = True
            space.shading.use_scene_lights = True
            space.clip_end = 500.0

    for obj in scene.objects:
        obj.select_set(obj is level_mesh)
    bpy.context.view_layer.objects.active = level_mesh


def build():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    level_mesh = build_level_mesh()
    place_surroundings()
    place_hut()
    place_campfire()
    place_graveyard()
    place_shrine()
    place_gate()
    scatter_nature()
    build_waynet()
    bpy.context.view_layer.update()
    return level_mesh


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) not in (1, 3):
        raise SystemExit(__doc__)
    blend_path = os.path.abspath(args[0])

    level_mesh = build()
    problems = check_names()
    for problem in problems:
        print(f"[showcase_level] CHECK {problem}")
    previews = vob_preview.apply_previews(bpy.context, list(bpy.context.scene.objects), use_game_files=True)
    print(f"[showcase_level] previews: {vob_preview.summary(previews)}")
    setup_presentation(level_mesh)
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    vobs = sum(1 for o in bpy.context.scene.objects if ":" in o.name)
    print(f"[showcase_level] saved {blend_path} ({vobs} vobs and waypoints, {len(problems)} name problem(s))")

    if len(args) == 3:
        level_name, mod_name = args[1], args[2]
        result = bpy.ops.zen.quick_export_package(level_name=level_name, mod_name=mod_name)
        if result != {'FINISHED'}:
            raise SystemExit(f"[showcase_level] export did not finish: {result}")
        bpy.ops.wm.save_mainfile()      # keeps the level compo the export created
        print(f"[showcase_level] exported level package {mod_name}/{level_name}")


main()
