"""In-Blender check of waypoint facing direction (README.md "Waypoint
direction"): add -> rotate -> export -> parse -> import -> compare, plus
the old-style waypoint conversion button.

Needs "Zen Waypoint Tools" enabled. Safe to run in an open file: in the
UI it works in a temporary scene and removes everything it created; the
exported ZEN goes to a temp folder that is deleted afterwards.

    blender --background --python tooling/pipeline/test_waypoint_direction.py

or paste/run it in Blender's Text Editor (or through an MCP "run python"
tool). Prints one PASS/FAIL line per check and a summary; in background
mode a failure exits with code 1.
"""
import math
import os
import re
import sys
import tempfile

import bpy
from mathutils import Euler, Vector

TOL = 1e-4
results = []


def check(label, ok, detail=""):
    results.append(ok)
    print(f"[{'PASS' if ok else 'FAIL'}] {label}" + (f" - {detail}" if detail and not ok else ""))


def close(a, b):
    return all(abs(x - y) < TOL for x, y in zip(a, b))


def y_axis(obj):
    m = obj.matrix_world
    return (m[0][1], m[1][1], m[2][1])


def parse_waypoint_directions(path):
    """{wpName: (gx, gy, gz)} from an uncompiled ZEN."""
    text = open(path, encoding="windows-1250").read()
    out = {}
    for name, vec in re.findall(r"wpName=string:(\S+).*?direction=vec3:([^\n]+)", text, re.S):
        out[name] = tuple(float(v) for v in vec.split())
    return out


def run():
    if not hasattr(bpy.ops.zen, "add_waypoint"):
        raise SystemExit("Zen Waypoint Tools is not enabled")

    # With a UI window, work in a throwaway scene. In --background there's
    # no window to switch, so use the (unsaved) startup scene directly.
    window = bpy.context.window
    old_scene = window.scene if window else None
    if window:
        scene = bpy.data.scenes.new("ZEN_WAYPOINT_DIRECTION_TEST")
        window.scene = scene
    else:
        scene = bpy.context.scene
    before = set(bpy.data.objects)
    # The conversion button touches every waypoint in the file - snapshot
    # pre-existing ones so the user's own scene comes back unchanged.
    saved = [
        (o, o.empty_display_type, o.rotation_mode, o.matrix_basis.copy(), tuple(o.lock_rotation))
        for o in before if o.type == 'EMPTY' and o.name.startswith("zCWaypoint:")
    ]
    tmp_dir = tempfile.mkdtemp(prefix="zen_wp_dir_")
    try:
        _run_checks(scene, tmp_dir)
    finally:
        for obj in set(bpy.data.objects) - before:
            bpy.data.objects.remove(obj, do_unlink=True)
        for o, display, mode, basis, locks in saved:
            o.empty_display_type = display
            o.rotation_mode = mode
            o.matrix_basis = basis
            o.lock_rotation = locks
        if window and old_scene:
            window.scene = old_scene
            bpy.data.scenes.remove(scene)
        for f in os.listdir(tmp_dir):
            os.remove(os.path.join(tmp_dir, f))
        os.rmdir(tmp_dir)


def _run_checks(scene, tmp_dir):
    view_layer = bpy.context.view_layer
    for o in view_layer.objects:
        o.select_set(False)
    # nothing active, so the first new waypoint isn't linked from an
    # existing one
    view_layer.objects.active = None

    # --- 1. add waypoints via the real operator --------------------------
    yaws = (0.0, 90.0, 37.0)
    waypoints = []
    for i, yaw in enumerate(yaws):
        scene.cursor.location = (i * 3.0, 0.0, 0.0)
        assert bpy.ops.zen.add_waypoint() == {'FINISHED'}
        wp = bpy.context.view_layer.objects.active
        waypoints.append(wp)
        if i == 0:
            check("new waypoint is a csys (ARROWS) empty", wp.empty_display_type == 'ARROWS',
                  wp.empty_display_type)
            check("new waypoint uses Euler XYZ", wp.rotation_mode == 'XYZ', wp.rotation_mode)
            check("new waypoint locks X/Y rotation", tuple(wp.lock_rotation) == (True, True, False),
                  str(tuple(wp.lock_rotation)))
            check("new waypoint faces Blender +Y",
                  close(Vector(y_axis(wp)).normalized(), (0, 1, 0)), str(y_axis(wp)))
        wp.rotation_euler = Euler((0.0, 0.0, math.radians(yaw)))
    view_layer.update()

    # --- 2. export and parse direction ------------------------------------
    zen_path = os.path.join(tmp_dir, "WP_DIR_TEST.ZEN")
    res = bpy.ops.zen.export_zen(filepath=zen_path)
    check("export finished", res == {'FINISHED'}, str(res))
    directions = parse_waypoint_directions(zen_path)
    for wp, yaw in zip(waypoints, yaws):
        name = wp.name.removeprefix("zCWaypoint:")
        r = math.radians(yaw)
        # Blender local +Y after yaw = (-sin, cos, 0) -> Gothic (x, z, y)
        expected = (-math.sin(r), 0.0, math.cos(r))
        got = directions.get(name)
        check(f"export {name} yaw {yaw:g} -> direction {tuple(round(v, 3) for v in expected)}",
              got is not None and close(got, expected), f"got {got}")

    # --- 3. import back and compare orientation ---------------------------
    pre_import = set(bpy.data.objects)
    res = bpy.ops.zen.import_zen(filepath=zen_path)
    check("import finished", res == {'FINISHED'}, str(res))
    view_layer.update()
    imported = {
        o.name.removeprefix("zCWaypoint:").rsplit(".", 1)[0]: o
        for o in set(bpy.data.objects) - pre_import if o.name.startswith("zCWaypoint:")
    }
    for wp in waypoints:
        name = wp.name.removeprefix("zCWaypoint:")
        imp = imported.get(name)
        ok = imp is not None and close(y_axis(imp), y_axis(wp)) and imp.empty_display_type == 'ARROWS'
        check(f"import {name} keeps facing and csys display", ok,
              f"original {y_axis(wp)}, imported {y_axis(imp) if imp else None}")

    # --- 4. old-style waypoint conversion ---------------------------------
    old = bpy.data.objects.new("zCWaypoint:ZEN_TEST_OLD_STYLE", None)
    old.empty_display_type = 'SINGLE_ARROW'
    old.rotation_mode = 'QUATERNION'
    old.rotation_quaternion = Euler((0.0, 0.0, math.radians(45))).to_quaternion()
    scene.collection.objects.link(old)
    view_layer.update()
    facing_before = y_axis(old)
    assert bpy.ops.zen.update_waypoint_display() == {'FINISHED'}
    view_layer.update()
    check("conversion switches old waypoint to ARROWS + XYZ",
          old.empty_display_type == 'ARROWS' and old.rotation_mode == 'XYZ',
          f"{old.empty_display_type}, {old.rotation_mode}")
    check("conversion keeps old waypoint's facing", close(y_axis(old), facing_before),
          f"before {facing_before}, after {y_axis(old)}")


run()
passed = sum(results)
print(f"\nwaypoint direction check: {passed}/{len(results)} passed")
if bpy.app.background and passed != len(results):
    sys.exit(1)
