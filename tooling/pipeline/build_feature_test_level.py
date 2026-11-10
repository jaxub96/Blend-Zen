"""Builds the feature test level: one station for every item under
"P1 - Verify in Spacer / in-game" in TODO.md, saves it as a .blend and
(optionally) runs Export Level Package.

    blender --background --python tooling/pipeline/build_feature_test_level.py -- \
        blender_work_dir/feature_test_level.blend [LEVEL_NAME MOD_NAME]

Run it with your normal Blender profile (no --factory-startup): it needs
"Zen Waypoint Tools" and KrxImpExp enabled, and Export Level Package
writes into the Gothic Game Folder from the add-on preferences.

Every station has a sign (an oCMOB whose focus name is the instruction),
so in-game you look at the sign and do what it says. Stations, by row
(the player starts at the south edge facing north; +Y is north):

Row A, y = +6: level logic
  A1  lever -> gate           oCMobSwitch (lever) -> zCMover, 2 keyframes, gate sounds
  A2  touch plate -> gate     oCMobSwitch (touch plate, no collision) -> zCMover; the
                              winch next to it triggers the same gate
  A3  script trigger          oCTriggerScript -> EVT_TELEPORTSTATION_FUNC (teleport ring + sound)
  A4  trigger list            lever -> zCTriggerList -> fire effect (zCPFXControler) at once,
                              earthquake (zCEarthquake) 2 s later
  A5  touch damage            oCTouchDamage box, 5 fire damage every 2 s
  A6  code master             both levers -> zCCodeMaster -> fire effect
  A7  level change            oCTriggerChangeLevel -> MOD\\PR_TEST.ZEN at PC_START (far east,
                              so you don't walk into it by accident)

Row B, y = +16: zones (walk into each 10 m box)
  B1  music zone              oCZoneMusic MUSIC_XAR (Xardas theme); oCZoneMusicDefault elsewhere
  B2  fog zone                zCZoneZFog, green fog at 15 m; zCZoneZFogDefault elsewhere
  B3  view distance zone      zCZoneVobFarPlane 15 m: the props around vanish; default elsewhere

Row C, y = -6: lights, effects, sounds
  C1  static light            white, baked by Compile Light
  C2  flickering light        dynamic, range + colour animation
  C3  preset light            light preset FIRESMALL applied from LightPresets.zen
  C4  particle effect         zCVob with FIRE.PFX
  C5  decals                  ZFLARE6.TGA facing the camera, a two-sided cobweb
  C6  torch with children     wall torch prop with flame, flare, light and sound as child vobs
  C7  looping sound           TORCH_BURN, radius 6 m
  C8  random sound            OW_CROW every 4 +/- 2 s, radius 10 m
  C9  day / night sound       OW_BIRD8 from 6 to 20 h, INSECTSFROGS_NIGHT otherwise
  C10 lens flare + morph mesh zCVobLensFlare TORCHFX01, zCVobAnimate NW_MORPH_SKATE_01

Row D, y = -14: interactive objects, props, items
  D1  locked chest            key ITKE_BANDIT (lying next to it) or picklock LRL; gold + apples
  D2  door                    DOOR_NW_NORMAL_01
  D3  bed                     sleep dialog (SLEEPABIT)
  D4  alchemy table           needs ITMI_FLASK (lying next to it)
  D5  fires                   standing lamp, fire bowl, wall torch holder - light them
  D6  bookstand, gravestone   presets
  D7  props                   table with collision, bush without collision and with wind sway
  D8  items                   gold, health potion

Waynet: WP_START .. WP_05 run west to east along y = 0, with freepoints
FP_STAND_01 / FP_ROAM_01. For the waypoint-direction check add an NPC that
calls AI_AlignToWP in its routine (script side, see README "Waypoint
direction"); it should face the waypoint's green Y arrow.
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Vector

from zen_waypoint_tools import vob_ops, vob_ui
from zen_waypoint_tools.mob_props import apply_preset
from zen_waypoint_tools.waypoint_links import add_directed_link, setup_waypoint_empty

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MATERIAL_LIBRARY = os.path.join(_REPO, "asset_catalog", "materials_levels.blend")
FLOOR_MATERIAL = "NW_City_DungeonFloor_03"
FLOOR_NAME = "FEATURE_TEST_FLOOR"

FLOOR_X, FLOOR_Y = 70.0, 50.0       # metres
TILE = 2.5                          # floor quad size: vertex lighting needs vertices
ROW_A, ROW_B, ROW_C, ROW_D = 6.0, 16.0, -6.0, -14.0


# -- helpers ----------------------------------------------------------------------

def add(type_id, name, location, rotation_z=0.0, preset=None, parent=None, box=None, **settings):
    """A vob through the same code path as the Add VOB dialog, then its
    settings as custom properties. box: half extents in metres."""
    context = bpy.context
    context.scene.cursor.location = location
    obj = vob_ops.create_vob(context, type_id, name, preset)
    if rotation_z:
        obj.rotation_mode = 'XYZ'
        obj.rotation_euler = (0.0, 0.0, math.radians(rotation_z))
    if box:
        obj.scale = box
    for key, value in settings.items():
        obj[key] = value
    if parent is not None:
        context.view_layer.update()
        world = obj.matrix_world.copy()
        obj.parent = parent
        obj.matrix_parent_inverse = parent.matrix_world.inverted()
        obj.matrix_world = world
    return obj


def sign(station, text, x, y):
    """The station's instruction, shown as the focus name of a sign."""
    return add("oCMOB", f"SIGN_{station}", (x, y - 2.0, 0.0), preset="SIGN",
               focus_name=f"{station}: {text}")


def mover(name, location, lift, visual="OC_LOB_GATE_BIG", **settings):
    """A mover with its closed keyframe at `location` and the open one
    `lift` metres above."""
    obj = add("zCMover", name, location, visual_name=visual, move_speed=0.1,
              sfx_open_start="GATE_START", sfx_open_end="GATE_STOP", sfx_moving="GATE_LOOP",
              sfx_close_start="GATE_START", sfx_close_end="GATE_STOP", **settings)
    bpy.context.view_layer.update()
    keys = vob_ui.mover_keyframes(obj)
    keys[1].matrix_basis = Matrix.Translation((0.0, 0.0, lift))
    return obj


def build_floor():
    bm = bmesh.new()
    bmesh.ops.create_grid(bm, x_segments=int(FLOOR_X / TILE), y_segments=int(FLOOR_Y / TILE), size=0.5)
    uv_layer = bm.loops.layers.uv.new("UVMap")
    for vert in bm.verts:
        vert.co.x *= FLOOR_X
        vert.co.y *= FLOOR_Y
    for face in bm.faces:
        for loop in face.loops:
            loop[uv_layer].uv = (loop.vert.co.x / TILE, loop.vert.co.y / TILE)
    mesh = bpy.data.meshes.new(FLOOR_NAME)
    bm.to_mesh(mesh)
    bm.free()

    with bpy.data.libraries.load(MATERIAL_LIBRARY, link=False) as (source, target):
        if FLOOR_MATERIAL not in source.materials:
            raise SystemExit(f"{FLOOR_MATERIAL} not in {MATERIAL_LIBRARY}")
        target.materials = [FLOOR_MATERIAL]
    mesh.materials.append(target.materials[0])

    obj = bpy.data.objects.new(FLOOR_NAME, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def build_waynet():
    names = ["WP_START", "WP_01", "WP_02", "WP_03", "WP_04", "WP_05"]
    previous = None
    for index, name in enumerate(names):
        obj = bpy.data.objects.new(f"zCWaypoint:{name}", None)
        setup_waypoint_empty(obj)
        obj.location = (-25.0 + index * 10.0, 0.0, 0.0)
        bpy.context.scene.collection.objects.link(obj)
        if previous is not None:
            add_directed_link(previous, obj)        # auto-aims previous at obj
        previous = obj
    # The last one has nothing to aim at: point it north on purpose, so the
    # direction check has a waypoint that does not face along the path.
    previous.rotation_euler = (0.0, 0.0, 0.0)
    add("zCVobSpot", "FP_STAND_01", (-25.0, 2.0, 0.0), rotation_z=-90.0)
    add("zCVobSpot", "FP_ROAM_01", (5.0, 2.0, 0.0))


# -- stations -----------------------------------------------------------------------

def row_a_logic():
    y = ROW_A
    x = -30.0
    sign("A1", "Pull the lever - the gate behind it opens, pull again to close", x, y)
    add("oCMobSwitch", "LEVER_GATE_01", (x, y, 0.0), preset="LEVER", trigger_target="EVT_GATE_01")
    mover("EVT_GATE_01", (x, y + 4.0, 0.0), lift=5.8)

    x = -20.0
    sign("A2", "Step on the plate or turn the winch - the gate opens", x, y)
    add("oCMobSwitch", "PLATE_GATE_02", (x, y, 0.0), preset="TOUCHPLATE", trigger_target="EVT_GATE_02")
    add("oCMobWheel", "WINCH_GATE_02", (x + 2.0, y, 0.0), preset="WHEEL", trigger_target="EVT_GATE_02")
    mover("EVT_GATE_02", (x, y + 4.0, 0.0), lift=5.8)

    x = -10.0
    sign("A3", "Walk into the box behind this sign - teleport ring and sound", x, y)
    add("oCTriggerScript", "EVT_SCRIPT_01", (x, y + 2.0, 1.5), box=(1.5, 1.5, 1.5),
        script_func="EVT_TELEPORTSTATION_FUNC")

    x = 0.0
    sign("A4", "Pull the lever - fire starts at once, earthquake 2 s later", x, y)
    add("oCMobSwitch", "LEVER_LIST_01", (x, y, 0.0), preset="LEVER", trigger_target="EVT_LIST_01")
    add("zCTriggerList", "EVT_LIST_01", (x, y + 1.0, 2.0),
        list_target_0="EVT_PFX_01", list_target_1="EVT_QUAKE_01", list_delay_1=2.0)
    add("zCPFXControler", "EVT_PFX_01", (x, y + 3.0, 0.2), pfx_name="FIRE.PFX",
        pfx_start_on=False, kill_vob_when_done=False)
    add("zCEarthquake", "EVT_QUAKE_01", (x, y + 3.0, 0.0), quake_radius=1500.0, quake_time_sec=3.0)

    x = 10.0
    sign("A5", "Walk into the box behind this sign - 5 fire damage every 2 s", x, y)
    add("oCTouchDamage", "DAMAGE_01", (x, y + 2.0, 1.0), box=(1.5, 1.5, 1.0),
        touch_damage=5.0, damage_point=False, damage_fire=True)

    x = 20.0
    sign("A6", "Pull both levers - only then the fire starts (code master)", x, y)
    add("oCMobSwitch", "LEVER_CODE_A", (x - 1.0, y, 0.0), preset="LEVER", trigger_target="EVT_CODE_01")
    add("oCMobSwitch", "LEVER_CODE_B", (x + 1.0, y, 0.0), preset="LEVER", trigger_target="EVT_CODE_01")
    add("zCCodeMaster", "EVT_CODE_01", (x, y + 1.0, 2.0), trigger_target="EVT_PFX_02",
        slave_0="LEVER_CODE_A", slave_1="LEVER_CODE_B")
    add("zCPFXControler", "EVT_PFX_02", (x, y + 3.0, 0.2), pfx_name="FIRE.PFX",
        pfx_start_on=False, kill_vob_when_done=False)

    x = 31.0
    sign("A7", "Walk into the box behind this sign - loads the world PR_TEST", x, y)
    add("oCTriggerChangeLevel", "EVT_LEVELCHANGE_01", (x, y + 3.0, 1.5), box=(1.5, 1.5, 1.5),
        level_name="MOD\\PR_TEST.ZEN", start_vob_name="PC_START")


def row_b_zones():
    y = ROW_B
    half = (5.0, 5.0, 4.0)
    sign("B1", "Music zone ahead - Xardas theme inside, default theme outside", -20.0, y - 4.0)
    add("oCZoneMusic", "MUSIC_XAR", (-20.0, y + 3.0, 4.0), box=half, zone_priority=2)
    add("oCZoneMusicDefault", "DEFAULT_DEF", (-33.0, 23.0, 1.0))

    sign("B2", "Fog zone ahead - thick green fog inside", 0.0, y - 4.0)
    add("zCZoneZFog", "FOG_01", (0.0, y + 3.0, 4.0), box=half, fog_range_center=1500.0,
        inner_range_perc=0.5, fog_color=[60, 110, 60, 255], fog_override_color=True,
        fog_fade_out_sky=True)
    add("zCZoneZFogDefault", "", (-32.0, 23.0, 1.0))

    sign("B3", "View distance zone ahead - distant props vanish inside", 20.0, y - 4.0)
    add("zCZoneVobFarPlane", "FARPLANE_01", (20.0, y + 3.0, 4.0), box=half,
        vob_far_plane_z=1500.0, inner_range_perc=0.5)
    add("zCZoneVobFarPlaneDefault", "", (-31.0, 23.0, 1.0))


def _dynamic_light(name, location, colour, parent=None):
    light = add("zCVobLight", name, location, parent=parent, light_static=False,
                range_ani_scale="1.0 0.85 1.1 0.9", range_ani_fps=4.0,
                color_ani_list="(255 150 60) (255 100 30) (240 170 80)", color_ani_fps=3.0)
    light.data.color = colour
    light.data.cutoff_distance = 6.0
    light.data.use_shadow = False
    return light


def row_c_lights_effects_sounds():
    y = ROW_C
    xs = [-31.0 + 7.0 * i for i in range(10)]

    sign("C1", "Static white light (baked by Compile Light)", xs[0], y)
    light = add("zCVobLight", "LIGHT_STATIC", (xs[0], y, 2.5))
    light.data.cutoff_distance = 6.0

    sign("C2", "Flickering orange light (dynamic)", xs[1], y)
    _dynamic_light("LIGHT_FLICKER", (xs[1], y, 2.5), (1.0, 0.55, 0.2))

    sign("C3", "Light from preset FIRESMALL", xs[2], y)
    preset_light = add("zCVobLight", "LIGHT_PRESET", (xs[2], y, 2.5))
    preset_light.zen_vob.light_preset = "FIRESMALL"      # applies the preset's values

    sign("C4", "Particle effect: fire", xs[3], y)
    add("zCVob@PFX", "PFX_FIRE", (xs[3], y, 0.2), visual_name="FIRE.PFX")

    sign("C5", "Decals: flare that faces you, cobweb that does not", xs[4], y)
    add("zCVob@DECAL", "DECAL_FLARE", (xs[4] - 1.0, y, 1.8), visual_name="ZFLARE6.TGA",
        cam_align="FULL", decal_dim=[40.0, 40.0], decal_alpha_func="ADD",
        decal_ignore_daylight=True)
    add("zCVob@DECAL", "DECAL_WEB", (xs[4] + 1.0, y, 1.8), visual_name="OWDISPIDERWEB.TGA",
        cam_align="NONE", decal_dim=[80.0, 80.0], decal_alpha_func="BLEND")

    sign("C6", "Torch with flame, flare, light and sound as child vobs", xs[5], y)
    torch = add("zCVob", "OW_MISC_WALL_TORCH_01", (xs[5], y, 1.5), cd_dyn=False, cd_static=False)
    top = Vector((xs[5], y, 1.9))
    add("zCVob@PFX", "TORCH_FLAME", top, parent=torch, visual_name="FIRE.PFX")
    add("zCVob@DECAL", "TORCH_FLARE", top, parent=torch, visual_name="ZFLARE6.TGA",
        cam_align="FULL", decal_dim=[25.0, 25.0], decal_alpha_weight=200, decal_ignore_daylight=True)
    _dynamic_light("TORCH_LIGHT", top, (1.0, 0.55, 0.2), parent=torch)
    add("zCVobSound", "TORCH_SOUND", top, parent=torch, sound_name="TORCH_BURN", sound_radius=600.0)

    sign("C7", "Looping sound: burning torch, 6 m radius", xs[6], y)
    add("zCVobSound", "SOUND_LOOP", (xs[6], y, 1.0), sound_name="TORCH_BURN", sound_radius=600.0)

    sign("C8", "Random sound: crow every 4 s or so, 10 m radius", xs[7], y)
    add("zCVobSound", "SOUND_RANDOM", (xs[7], y, 1.0), sound_name="OW_CROW", sound_mode="RANDOM",
        sound_random_delay=4.0, sound_random_delay_var=2.0, sound_radius=1000.0)

    sign("C9", "Day/night sound: birds 6-20 h, frogs at night (set time: 'set time 23 0')", xs[8], y)
    add("zCVobSoundDaytime", "SOUND_DAYNIGHT", (xs[8], y, 1.0), sound_name="OW_BIRD8",
        sound_name_2="INSECTSFROGS_NIGHT", sound_start_time=6.0, sound_end_time=20.0,
        sound_radius=1000.0, sound_ambient_3d=True)

    sign("C10", "Lens flare (left) and animated morph mesh (right)", xs[9], y)
    add("zCVobLensFlare", "FLARE_01", (xs[9] - 1.0, y, 2.0), lensflare_fx="TORCHFX01")
    add("zCVobAnimate", "ANIMATE_01", (xs[9] + 1.0, y, 1.0), visual_name="NW_MORPH_SKATE_01")


def row_d_mobs_props_items():
    y = ROW_D
    xs = [-30.0 + 8.0 * i for i in range(8)]

    sign("D1", "Locked chest: key lies beside it, or pick LRL. 50 gold, 3 apples", xs[0], y)
    add("oCMobContainer", "CHEST_LOCKED", (xs[0], y, 0.0), preset="CHEST_BIG", locked=True,
        key_instance="ITKE_BANDIT", picklock_str="LRL", contains="ItMi_Gold:50,ItFo_Apple:3")
    add("oCItem", "ITKE_BANDIT", (xs[0] + 1.2, y, 0.1))
    add("oCItem", "ITKE_LOCKPICK", (xs[0] + 1.6, y, 0.1))

    sign("D2", "Door: opens and closes", xs[1], y)
    add("oCMobDoor", "DOOR_01", (xs[1], y, 0.0), preset="DOOR_NORMAL")

    sign("D3", "Bed: sleep dialog", xs[2], y)
    add("oCMobBed", "BED_01", (xs[2], y, 0.0), preset="BED_NORMAL")

    sign("D4", "Alchemy table: take the flask beside it first", xs[3], y)
    add("oCMobInter", "LAB_01", (xs[3], y, 0.0), preset="LAB")
    add("oCItem", "ITMI_FLASK", (xs[3] + 1.5, y, 0.1))

    sign("D5", "Fires: light the lamp, the fire bowl and the wall torch holder", xs[4], y)
    add("oCMobFire", "FIRE_LAMP", (xs[4] - 2.0, y, 0.0), preset="FIRE_LAMP")
    add("oCMobFire", "FIRE_BOWL", (xs[4], y, 0.0), preset="FIRE_HIGH")
    add("oCMobFire", "FIRE_TORCH", (xs[4] + 2.0, y, 1.5), preset="TORCH_HOLDER")

    sign("D6", "Bookstand (left) and gravestone with a focus name (right)", xs[5], y)
    add("oCMobInter", "BOOKSTAND_01", (xs[5] - 1.0, y, 0.0), preset="BOOKSTAND")
    add("oCMOB", "GRAVE_01", (xs[5] + 1.5, y, 0.0), preset="GRAVESTONE")

    sign("D7", "Props: the table blocks you, the bush does not and sways in the wind", xs[6], y)
    add("zCVob", "DT_TABLE_V3", (xs[6] - 1.5, y, 0.0))
    add("zCVob", "NW_NATURE_BUSH_300P", (xs[6] + 1.5, y, 0.0), cd_dyn=False, cd_static=False,
        ani_mode="WIND", ani_strength=0.01)

    sign("D8", "Items: gold and a health potion to pick up", xs[7], y)
    add("oCItem", "ITMI_GOLD", (xs[7] - 0.5, y, 0.1))
    add("oCItem", "ITPO_HEALTH_01", (xs[7] + 0.5, y, 0.1))


# -- entry point ------------------------------------------------------------------------

def build():
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)
    floor = build_floor()
    add("zCVobStartpoint", "PC_START", (-30.0, 0.0, 0.2), rotation_z=-90.0)
    build_waynet()
    row_a_logic()
    row_b_zones()
    row_c_lights_effects_sounds()
    row_d_mobs_props_items()

    bpy.context.view_layer.update()
    for obj in bpy.context.scene.objects:
        obj.select_set(obj is floor)
    bpy.context.view_layer.objects.active = floor
    return floor


def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(args) not in (1, 3):
        raise SystemExit(__doc__)
    blend_path = os.path.abspath(args[0])

    build()
    bpy.ops.wm.save_as_mainfile(filepath=blend_path)
    vobs = sum(1 for o in bpy.context.scene.objects if ":" in o.name)
    print(f"[feature_test_level] saved {blend_path} ({vobs} vobs and waypoints)")

    if len(args) == 3:
        level_name, mod_name = args[1], args[2]
        result = bpy.ops.zen.quick_export_package(level_name=level_name, mod_name=mod_name)
        if result != {'FINISHED'}:
            raise SystemExit(f"[feature_test_level] export did not finish: {result}")
        bpy.ops.wm.save_mainfile()      # keeps the level compo the export created
        print(f"[feature_test_level] exported level package {mod_name}/{level_name}")


main()
