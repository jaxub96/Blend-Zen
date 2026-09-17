"""Builds the "Compass Cross" scene for verifying the Blender<->Gothic
coordinate transform in Spacer. See documentation/transform_investigation.md
for why this design (mesh-anchored, not freepoint-only) is the one that
actually proves anything.

Builds one mesh object ("COMPASS_TEST_LEVEL"): a plaza with 5 arms of 5
different lengths (so each is identifiable on sight, no measuring), plus
a freepoint at each arm's tip and a rotation reference pair at the
center:

    +X arm 3m   -X arm 5m   +Y arm 7m   -Y arm 9m   +Z pillar 11m
    TEST_<ARM>_TIP freepoints, one per arm, at the exact tip coordinate
    TEST_ROTATION_REFERENCE / TEST_ROTATION_PLUS90Z at the plaza center

Usage: run in Blender's Scripting tab in a saved .blend with "Zen
Waypoint Tools" enabled, then select COMPASS_TEST_LEVEL and use "Export
Level Package". Or headless, exporting in the same step:

    blender <file.blend> --background --python build_compass_test_level.py -- <level_name> <mod_name>

After exporting: copy into the Gothic install, open the uncompiled ZEN
in Spacer, compile world + light (E2E_TEST_PLAN.md Phase 6), then check:
each tip freepoint should sit exactly on its same-length arm, and
TEST_ROTATION_PLUS90Z should point from wherever TEST_ROTATION_REFERENCE
points towards the +Y arm.
"""
import math
import sys

import bpy
import bmesh
import mathutils


ARM_WIDTH = 1.0
ARM_HEIGHT = 0.3
PLAZA_SIZE = 1.0
PILLAR_WIDTH = 0.5
PILLAR_LENGTH = 11.0

# (name, direction, length) - lengths are all different on purpose, so
# every arm is identifiable purely by how long it is.
ARMS = [
    ("PLUS_X", (1, 0), 3.0),
    ("MINUS_X", (-1, 0), 5.0),
    ("PLUS_Y", (0, 1), 7.0),
    ("MINUS_Y", (0, -1), 9.0),
]


def _add_box(bm, center, size):
    box = bmesh.ops.create_cube(bm, size=1.0)
    sx, sy, sz = size
    cx, cy, cz = center
    for v in box["verts"]:
        v.co.x = v.co.x * sx + cx
        v.co.y = v.co.y * sy + cy
        v.co.z = v.co.z * sz + cz


def build_compass_mesh():
    """Returns (mesh_object, {arm_name: tip_location})."""
    bm = bmesh.new()
    _add_box(bm, (0, 0, 0), (PLAZA_SIZE, PLAZA_SIZE, ARM_HEIGHT))

    half_plaza = PLAZA_SIZE / 2
    tips = {}
    for name, (dx, dy), length in ARMS:
        center = (dx * (half_plaza + length / 2), dy * (half_plaza + length / 2), 0)
        size = (length, ARM_WIDTH, ARM_HEIGHT) if dx else (ARM_WIDTH, length, ARM_HEIGHT)
        _add_box(bm, center, size)
        tips[name] = (center[0] + dx * length / 2, center[1] + dy * length / 2, 0)

    pillar_z = ARM_HEIGHT / 2 + PILLAR_LENGTH / 2
    _add_box(bm, (0, 0, pillar_z), (PILLAR_WIDTH, PILLAR_WIDTH, PILLAR_LENGTH))
    tips["PLUS_Z"] = (0, 0, pillar_z + PILLAR_LENGTH / 2)

    mesh = bpy.data.meshes.new("COMPASS_TEST_LEVEL")
    bm.to_mesh(mesh)
    bm.free()

    obj = bpy.data.objects.new("COMPASS_TEST_LEVEL", mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj, tips


def _add_freepoint(name, location, rotation_quat=(1, 0, 0, 0)):
    bpy.context.scene.cursor.location = location
    bpy.ops.zen.add_vob(vob_type='zCVobSpot', vob_name=name)
    obj = bpy.context.view_layer.objects.active
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = rotation_quat


def build_test_vobs(tips):
    for name, tip in tips.items():
        _add_freepoint(f"TEST_{name}_TIP", tip)

    center = (0, 0, ARM_HEIGHT / 2 + 0.3)
    quat_plus90z = mathutils.Quaternion((0.0, 0.0, 1.0), math.radians(90))
    _add_freepoint("TEST_ROTATION_REFERENCE", center)
    _add_freepoint("TEST_ROTATION_PLUS90Z", center, tuple(quat_plus90z))


def _script_args():
    argv = sys.argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def main():
    mesh_obj, tips = build_compass_mesh()
    build_test_vobs(tips)

    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = mesh_obj
    print(f"[build_compass_test_level] Built COMPASS_TEST_LEVEL and {len(tips) + 2} vobs.")

    args = _script_args()
    if not args:
        return
    if len(args) != 2:
        raise SystemExit("Usage: ... -- <level_name> <mod_name>")
    level_name, mod_name = args
    result = bpy.ops.zen.quick_export_package(level_name=level_name, mod_name=mod_name)
    if result != {'FINISHED'}:
        raise SystemExit(f"[build_compass_test_level] export did not finish: {result}")
    print(f"[build_compass_test_level] Exported level package '{level_name}' (mod '{mod_name}')")


main()
