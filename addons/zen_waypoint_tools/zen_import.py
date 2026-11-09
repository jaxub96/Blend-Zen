"""
Import an uncompiled ZEN back into Blender: vobs (with their custom
settings), waypoints with their facing direction, and links - as the same
kind of objects the addon creates, so export -> import -> export
round-trips. Also reads Spacer-saved worlds (free `waypointN` waynet
entries, vobs whose name lives in `visual`/`itemInstance`), though their
vob hierarchy is flattened and unsupported vob types are skipped.

The level mesh referenced by zCVobLevelCompo is searched, in order:
  1. the ZEN's own directory;
  2. _work/Data/Meshes/Level/*/ when the ZEN sits in a _work tree (the
     Export Level Package layout - Worlds and Meshes are siblings);
  3. the mesh directories configured in the add-on preferences.
.MRM is preferred over .3DS; both load through KrxImpExp.
"""

import os
from collections import Counter

import bpy
import mathutils

from zen_gin_export import (
    parse_archive,
    read_archive_text,
    find_block,
    parse_vec3,
    gothic_position_to_blender,
    gothic_matrix_to_blender_matrix,
    decode_rotation_matrix_hex,
    gothic_direction_to_blender,
    waypoint_rotation_from_blender_direction,
    custom_properties_from_block,
)

from .vob_types import VOB_DISPLAY
from .waypoint_links import add_directed_link, setup_waypoint_empty, auto_aim_suppressed
from .krximpexp_bridge import get_krx_3ds_importer, get_krx_mrm_importer
from .light_props import create_light_object
from .mob_props import init_mob_properties
from .preferences import get_mesh_directories

SUPPORTED_TYPES = {
    "zCVob", "zCVobLevelCompo", "zCVobStartpoint", "zCVobSpot", "zCVobLight",
    "zCVobSound", "oCItem", "oCMobInter", "oCMobContainer", "oCMobDoor",
    "oCMobBed", "oCMobSwitch", "oCMobLadder", "oCMobWheel", "oCMobFire",
}
_LIGHT_TYPE_NAMES = {0: "POINT", 1: "SPOT"}
LEVEL_MESH_COLLECTION_NAME = "Zen Level Mesh"


def _stem(filename):
    return os.path.splitext(filename)[0]


def _vob_name(real_type, block):
    """The Blender-side name, mirroring how the exporter derives fields
    from it. Spacer often leaves vobName empty, so fall back to the field
    the exporter would have generated from the name."""
    if real_type == "zCVobLevelCompo":
        return _stem(block.get("visual", ""))      # vobName is always LEVEL-VOB
    if real_type == "oCItem":
        return block.get("itemInstance") or block.get("vobName", "")
    if real_type == "zCVobSound":
        return block.get("sndName") or block.get("vobName", "")
    name = block.get("vobName", "")
    if real_type == "zCVob":
        return name or _stem(block.get("visual", ""))
    return name


def _set_transform(obj, position_prop, rotation_prop):
    if position_prop:
        obj.location = gothic_position_to_blender(*parse_vec3(position_prop))
    if rotation_prop:
        matrix = gothic_matrix_to_blender_matrix(decode_rotation_matrix_hex(rotation_prop))
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = mathutils.Matrix(matrix).to_quaternion()


def _create_light(name, block):
    color = [int(v) for v in block.get("color", "255 255 255 255").split()]
    color += [255] * (4 - len(color))
    return create_light_object(
        name,
        light_type=_LIGHT_TYPE_NAMES.get(int(block.get("lightType", "0")), "POINT"),
        range_cm=float(block.get("range", "1000.0")),
        spot_cone_angle_deg=float(block.get("spotConeAngle", "0.0")),
        color_rgb=tuple(color[:3]),
        color_a=color[3],
        light_static=block.get("lightStatic", "1") == "1",
    )


def _create_vob_object(context, real_type, block):
    full_name = f"{real_type}:{_vob_name(real_type, block)}"
    if real_type == "zCVobLight":
        obj = _create_light(full_name, block)
    else:
        obj = bpy.data.objects.new(full_name, None)
        obj.empty_display_type, obj.empty_display_size = VOB_DISPLAY.get(real_type, ('PLAIN_AXES', 0.3))

    if real_type.startswith("oCMob"):
        visual = block.get("visual", "")
        obj["visual_name"] = _stem(visual) if visual.upper().endswith(".MDS") else visual
    for key, value in custom_properties_from_block(real_type, block.properties).items():
        obj[key] = value
    init_mob_properties(obj, real_type)  # descriptions + any missing keys

    _set_transform(obj, block.get("trafoOSToWSPos"), block.get("trafoOSToWSRot"))
    context.scene.collection.objects.link(obj)
    return obj


def _create_waypoint_object(context, block):
    obj = bpy.data.objects.new(f"zCWaypoint:{block.get('wpName', '')}", None)
    rotation = None
    if block.get("direction"):
        direction = gothic_direction_to_blender(*parse_vec3(block.get("direction")))
        rotation = waypoint_rotation_from_blender_direction(*direction)
    setup_waypoint_empty(obj, rotation)
    if block.get("position"):
        obj.location = gothic_position_to_blender(*parse_vec3(block.get("position")))
    context.scene.collection.objects.link(obj)
    return obj


# -- level mesh ---------------------------------------------------------------

def _scan_directory_for_mesh(directory, mesh_name):
    """(path, ext) of mesh_name.mrm (preferred) or .3ds directly in
    directory, case-insensitive; (None, None) if neither."""
    if not os.path.isdir(directory):
        return None, None
    match_3ds = (None, None)
    for filename in os.listdir(directory):
        stem, ext = os.path.splitext(filename)
        if stem.lower() != mesh_name.lower():
            continue
        if ext.lower() == ".mrm":
            return os.path.join(directory, filename), ".mrm"
        if ext.lower() == ".3ds":
            match_3ds = (os.path.join(directory, filename), ".3ds")
    return match_3ds


def _find_work_root(filepath, max_depth=6):
    current = os.path.dirname(os.path.abspath(filepath))
    for _ in range(max_depth):
        if os.path.basename(current).lower() == "_work":
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return None


def _candidate_mesh_dirs(zen_filepath):
    yield os.path.dirname(zen_filepath)
    work_root = _find_work_root(zen_filepath)
    if work_root:
        level_dir = os.path.join(work_root, "Data", "Meshes", "Level")
        if os.path.isdir(level_dir):
            for mod_folder in sorted(os.listdir(level_dir)):
                yield os.path.join(level_dir, mod_folder)
    yield from get_mesh_directories()


def _find_level_mesh_file(zen_filepath, mesh_name):
    for directory in _candidate_mesh_dirs(zen_filepath):
        path, ext = _scan_directory_for_mesh(directory, mesh_name)
        if path:
            return path, ext
    return None, None


def _level_mesh_collection(context):
    coll = bpy.data.collections.get(LEVEL_MESH_COLLECTION_NAME)
    if coll is None:
        coll = bpy.data.collections.new(LEVEL_MESH_COLLECTION_NAME)
        context.scene.collection.children.link(coll)
    return coll


def _import_level_mesh(context, zen_filepath, mesh_name, compo_obj, report):
    found_path, ext = _find_level_mesh_file(zen_filepath, mesh_name)
    if found_path is None:
        report["level_mesh_status"] = "not_found"
        return
    report["level_mesh_path"] = found_path
    try:
        if ext == ".mrm":
            before = set(bpy.data.objects)
            get_krx_mrm_importer()(filename=found_path, scale=0.01)
            imported = [o for o in bpy.data.objects if o not in before]
        else:
            imported = list(get_krx_3ds_importer()(filename=found_path, scale=0.01).imported_objects)
    except Exception as e:
        report["level_mesh_status"] = "found_not_importable"
        report["level_mesh_error"] = str(e)
        return

    # Parented to the level compo and unselectable: it's a reference
    # display, the exporter only reads the compo itself.
    collection = _level_mesh_collection(context)
    for obj in imported:
        for coll in list(obj.users_collection):
            coll.objects.unlink(obj)
        collection.objects.link(obj)
        obj.parent = compo_obj
        obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
        obj.hide_select = True
    report["level_mesh_status"] = "imported"


# -- entry point ----------------------------------------------------------------

def import_zen(context, filepath):
    """Returns a report dict: vobs_created, waypoints_created, ways_linked,
    ways_dropped (both ends' 3 link slots full), skipped_types ({type: count}), level_mesh_status ('imported',
    'found_not_importable', 'not_found', or None without a level compo),
    level_mesh_path, level_mesh_error."""
    roots = parse_archive(read_archive_text(filepath))
    if not roots:
        raise ValueError("Could not find the top-level world block in this archive")
    world_block = roots[0]

    report = {
        "vobs_created": 0,
        "waypoints_created": 0,
        "ways_linked": 0,
        "ways_dropped": 0,
        "skipped_types": Counter(),
        "level_mesh_status": None,
        "level_mesh_path": None,
    }

    vob_tree = find_block(world_block, type1="VobTree")
    for block in (vob_tree.children if vob_tree else ()):
        real_type = block.type2.split(":")[0]
        if real_type not in SUPPORTED_TYPES:
            report["skipped_types"][real_type] += 1
            continue
        obj = _create_vob_object(context, real_type, block)
        report["vobs_created"] += 1
        if real_type == "zCVobLevelCompo":
            mesh_name = _stem(block.get("visual", ""))
            if mesh_name:
                _import_level_mesh(context, filepath, mesh_name, obj, report)

    way_net = find_block(world_block, type1="WayNet")
    inner = way_net.children[0] if way_net and way_net.children else None
    if inner is not None:
        by_index = {}
        way_ends = []
        for entry in inner.children:
            if entry.type2 == "§":           # reference to an earlier waypoint
                way_ends.append((entry.type1, by_index.get(entry.object_index)))
                continue
            obj = _create_waypoint_object(context, entry)
            by_index[entry.object_index] = obj
            report["waypoints_created"] += 1
            if entry.type1.startswith("way"):
                way_ends.append((entry.type1, obj))

        lefts = {t[len("wayl"):]: o for t, o in way_ends if t.startswith("wayl")}
        rights = {t[len("wayr"):]: o for t, o in way_ends if t.startswith("wayr")}
        # Keep each waypoint's direction from the ZEN (no auto-aim).
        with auto_aim_suppressed():
            for index, left in lefts.items():
                right = rights.get(index)
                if left is None or right is None:
                    continue
                # Stored on whichever end still has a free slot (3 each).
                if add_directed_link(left, right) or add_directed_link(right, left):
                    report["ways_linked"] += 1
                else:
                    report["ways_dropped"] += 1

    return report
