"""
Import an uncompiled ZEN back into Blender: vobs (with their settings and
their parent/child hierarchy), waypoints with their facing direction, and
links - as the same kind of objects the addon creates, so export -> import
-> export round-trips. Also reads Spacer-saved worlds (free `waypointN`
waynet entries, vobs whose name lives in `visual`/`itemInstance`). Vob
types without an entry in zen_gin_export.vob_fields (cutscene cameras)
are skipped and reported; their children are kept.

Zones and triggers are boxes: they come in as cube empties placed and
scaled to the archive's bbox3DWS. Movers get one child empty per keyframe.

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
    orient_ways,
)

from zen_gin_export.vob_fields import VOB_SPECS
from zen_gin_export.coordinate_transform import decode_mover_keyframes

from .vob_types import vob_display
from .waypoint_links import add_directed_link, setup_waypoint_empty, auto_aim_suppressed
from .krximpexp_bridge import get_krx_3ds_importer, get_krx_mrm_importer
from .light_props import create_light_object
from .preferences import get_mesh_directories

SUPPORTED_TYPES = frozenset(VOB_SPECS)
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
    name = block.get("vobName", "")
    if real_type in ("zCVobSound", "zCVobSoundDaytime"):
        return name or block.get("sndName", "")
    if real_type == "zCVob":
        return name or _stem(block.get("visual", ""))
    return name


def _world_matrix(block):
    """The vob's world matrix in Blender space (rotation + translation)."""
    matrix = mathutils.Matrix.Identity(4)
    rotation = block.get("trafoOSToWSRot")
    if rotation:
        matrix = mathutils.Matrix(
            gothic_matrix_to_blender_matrix(decode_rotation_matrix_hex(rotation))).to_4x4()
    position = block.get("trafoOSToWSPos")
    if position:
        matrix.translation = gothic_position_to_blender(*parse_vec3(position))
    return matrix


def _box_matrix(block):
    """World matrix of a cube empty (display size 1) filling bbox3DWS, or
    None when the box is empty (a point)."""
    try:
        values = [float(v) for v in block.get("bbox3DWS", "").split()]
    except ValueError:
        return None
    if len(values) != 6:
        return None
    low = gothic_position_to_blender(*values[0:3])
    high = gothic_position_to_blender(*values[3:6])
    half = [abs(h - l) / 2.0 for l, h in zip(low, high)]
    if max(half) < 1e-6:
        return None
    center = [(l + h) / 2.0 for l, h in zip(low, high)]
    return mathutils.Matrix.LocRotScale(center, None, [max(h, 1e-4) for h in half])


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
        light_static=block.get("lightStatic", "1").strip() not in ("0", ""),
    )


def _visual_name(real_type, spec, block, vob_name):
    """The visual_name custom property for a block's visual, or None when
    the exporter would derive the same visual from the name."""
    visual = block.get("visual", "").strip()
    if not visual or spec.visual not in ("custom", "custom_only"):
        return None
    stem, extension = os.path.splitext(visual)
    short = stem if extension.upper() == spec.default_extension else visual
    if spec.visual == "custom" and real_type == "zCVob" and short == vob_name:
        return None
    return short


def _set_world_matrix(obj, matrix, parent_matrix):
    """Place obj at a world matrix without relying on the depsgraph (its
    parent, if any, was created a moment ago and is not evaluated yet)."""
    obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
    obj.matrix_basis = parent_matrix.inverted_safe() @ matrix if parent_matrix else matrix


def _create_vob_object(context, real_type, block, parent, world_matrices):
    spec = VOB_SPECS[real_type]
    vob_name = _vob_name(real_type, block)
    full_name = f"{real_type}:{vob_name}"
    if real_type == "zCVobLight":
        obj = _create_light(full_name, block)
    else:
        obj = bpy.data.objects.new(full_name, None)
        obj.empty_display_type, obj.empty_display_size = vob_display(real_type)

    visual_block = find_block(block, type1="visual")
    custom = custom_properties_from_block(
        real_type, block.properties, visual_block.properties if visual_block else None)
    for key, value in custom.items():
        obj[key] = value
    visual_name = _visual_name(real_type, spec, block, vob_name)
    if visual_name is not None:
        obj["visual_name"] = visual_name
    extension = os.path.splitext(block.get("visual", ""))[1].upper()
    if real_type == "zCVob" and extension in (".PFX", ".TGA"):
        obj.empty_display_type, obj.empty_display_size = vob_display(
            "zCVob@PFX" if extension == ".PFX" else "zCVob@DECAL")

    matrix = _world_matrix(block)
    box = _box_matrix(block) if spec.volume == "box" else None
    if box is not None:
        obj.empty_display_type, obj.empty_display_size = 'CUBE', 1.0
        obj.rotation_mode = 'XYZ'
        obj.lock_rotation = (True, True, True)
        matrix = box
    else:
        obj.rotation_mode = 'QUATERNION'

    context.scene.collection.objects.link(obj)
    if parent is not None:
        obj.parent = parent
    _set_world_matrix(obj, matrix, world_matrices.get(parent))
    world_matrices[obj] = matrix

    if real_type == "zCMover" and block.get("keyframes"):
        from .vob_ui import add_mover_keyframe
        for position, rotation in decode_mover_keyframes(block.get("keyframes")):
            key_matrix = mathutils.Matrix(gothic_matrix_to_blender_matrix(rotation)).to_4x4()
            key_matrix.translation = gothic_position_to_blender(*position)
            add_mover_keyframe(context, obj, key_matrix, matrix)
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


def _vob_blocks_with_parents(vob_tree):
    """(block, index of its parent block or None) for every vob block, from
    the flat pre-order list and the `childsN` counts (node N's children
    follow it; node 0 is the implicit root)."""
    blocks = vob_tree.children
    result = []
    # Stack of [parent index, children still to come].
    stack = [[None, int(vob_tree.get("childs0", len(blocks)) or 0)]]
    for index, block in enumerate(blocks):
        while len(stack) > 1 and stack[-1][1] <= 0:
            stack.pop()
        parent_index = stack[-1][0]
        stack[-1][1] -= 1
        result.append((block, parent_index))
        try:
            child_count = int(vob_tree.get(f"childs{index + 1}", "0"))
        except ValueError:
            child_count = 0
        if child_count > 0:
            stack.append([index, child_count])
    return result


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
    ways_dropped (no free link slot on either end), skipped_types ({type: count}), level_mesh_status ('imported',
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
    created = {}            # block index -> object (None for skipped types)
    world_matrices = {}
    for index, (block, parent_index) in enumerate(_vob_blocks_with_parents(vob_tree) if vob_tree else ()):
        # A skipped vob's children hang on its nearest imported ancestor.
        parent = created.get(parent_index)
        real_type = block.type2.split(":")[0]
        if real_type not in SUPPORTED_TYPES:
            report["skipped_types"][real_type] += 1
            created[index] = parent
            continue
        obj = _create_vob_object(context, real_type, block, parent, world_matrices)
        created[index] = obj
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
        ways = [(left, rights.get(index)) for index, left in lefts.items()]
        ways = [(left, right) for left, right in ways if left is not None and right is not None]
        # A link is stored on one end and each waypoint has 3 slots, so
        # spread them out instead of filling the left end first.
        by_name = {obj.name: obj for pair in ways for obj in pair}
        oriented, dropped = orient_ways([(a.name, b.name) for a, b in ways])
        # Keep each waypoint's direction from the ZEN (no auto-aim).
        with auto_aim_suppressed():
            for source, target in oriented:
                if add_directed_link(by_name[source], by_name[target]):
                    report["ways_linked"] += 1
                else:
                    report["ways_dropped"] += 1
        report["ways_dropped"] += len(dropped)

    return report
