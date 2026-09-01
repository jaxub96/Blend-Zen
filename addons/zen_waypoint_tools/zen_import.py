"""
Import an uncompiled ZEN (as produced by our own zen_gin_export package)
back into Blender - the reverse of the export pipeline. Reconstructs vobs
and the waynet as the same kind of Empties the addon itself creates, so a
round trip (export -> import) should reproduce the original scene.

Scope for now, per the initial version of this feature: vob/waynet
reconstruction is the real focus. Level mesh loading is best-effort - it
only looks in the same directory as the ZEN (not any configured search
path), but both compiled .MRM and raw .3ds meshes can be imported, via
KrxImpExp's plain-callable functions (see krximpexp_bridge.py).
"""

import os
import bpy
import mathutils

from zen_gin_export import (
    parse_archive,
    find_block,
    parse_vec3,
    gothic_position_to_blender,
    gothic_matrix_to_blender_matrix,
    decode_rotation_matrix_hex,
)

from .vob_types import VOB_DISPLAY
from .waypoint_links import add_directed_link
from .krximpexp_bridge import get_krx_3ds_importer, get_krx_mrm_importer
from .mesh_preview import get_preview_collection
from .light_props import create_light_object


# Real ZenGin class name -> Blender name prefix. Mirrors the mapping in
# zen_gin_ocvobtree.py's __create_vob(), in reverse.
_REAL_TYPE_TO_PREFIX = {
    "zCVob": "zCVob:",
    "zCVobLevelCompo": "zCVobLevelCompo:",
    "zCVobStartpoint": "zCVobStartpoint:",
    "zCVobSpot": "zCVobSpot:",
    "zCVobLight": "zCVobLight:",
    "zCVobSound": "zCVobSound:",
    "oCItem": "oCItem:",
}

_LIGHT_TYPE_NAMES = {0: "POINT", 1: "SPOT"}


def _set_transform(obj, position_prop, rotation_prop):
    if position_prop:
        gx, gy, gz = parse_vec3(position_prop)
        bx, by, bz = gothic_position_to_blender(gx, gy, gz)
        obj.location = (bx, by, bz)

    if rotation_prop:
        gothic_matrix = decode_rotation_matrix_hex(rotation_prop)
        blender_matrix = gothic_matrix_to_blender_matrix(gothic_matrix)
        m = mathutils.Matrix(blender_matrix).to_4x4()
        obj.rotation_mode = 'QUATERNION'
        obj.rotation_quaternion = m.to_quaternion()


def _create_vob_object(context, real_type, block):
    if real_type == "zCVobLevelCompo":
        # ZCVobLevelCompo's exporter always writes vobName as the fixed
        # placeholder "LEVEL-VOB" (see zen_gin_zcvob_level_compo.py's
        # _printed_vob_name override) - the real per-instance name lives
        # in the visual property (the referenced mesh filename) instead.
        import os as _os
        vob_name = _os.path.splitext(block.get("visual", ""))[0]
    else:
        vob_name = block.get("vobName", "")
    prefix = _REAL_TYPE_TO_PREFIX.get(real_type, f"{real_type}:")
    full_name = f"{prefix}{vob_name}"

    if real_type == "zCVobLight":
        light_type = _LIGHT_TYPE_NAMES.get(int(block.get("lightType", "0")), "POINT")
        range_cm = float(block.get("range", "1000.0"))
        spot_cone_angle = float(block.get("spotConeAngle", "0.0"))
        color_parts = [int(v) for v in block.get("color", "255 255 255 255").split()]
        color_rgb = tuple(color_parts[:3]) if len(color_parts) >= 3 else (255, 255, 255)
        color_a = color_parts[3] if len(color_parts) >= 4 else 255
        light_static = block.get("lightStatic", "1") == "1"
        obj = create_light_object(
            full_name, light_type=light_type, range_cm=range_cm,
            spot_cone_angle_deg=spot_cone_angle, color_rgb=color_rgb,
            color_a=color_a, light_static=light_static,
        )
    else:
        obj = bpy.data.objects.new(full_name, None)
        display_type, display_size = VOB_DISPLAY.get(prefix.rstrip(":"), ('PLAIN_AXES', 0.3))
        obj.empty_display_type = display_type
        obj.empty_display_size = display_size

    _set_transform(obj, block.get("trafoOSToWSPos"), block.get("trafoOSToWSRot"))

    context.scene.collection.objects.link(obj)

    return obj


def _create_waypoint_object(name, position_prop, direction_prop):
    obj = bpy.data.objects.new(f"zCWaypoint:{name}", None)
    obj.empty_display_type = 'SINGLE_ARROW'
    obj.empty_display_size = 1.0
    obj.rotation_mode = 'QUATERNION'
    if position_prop:
        gx, gy, gz = parse_vec3(position_prop)
        bx, by, bz = gothic_position_to_blender(gx, gy, gz)
        obj.location = (bx, by, bz)
    # direction_prop intentionally not reconstructed into a rotation here -
    # it's a facing vector derived from a specific local-axis convention on
    # export (see WayNet.__waypoint_rotation_vec3), not a full orientation,
    # so round-tripping it exactly is left for a later pass if needed.
    bpy.context.scene.collection.objects.link(obj)
    return obj


def _find_local_mesh_file(zen_filepath, mesh_name):
    directory = os.path.dirname(zen_filepath)
    if not os.path.isdir(directory):
        return None, None
    for filename in os.listdir(directory):
        stem, ext = os.path.splitext(filename)
        if stem.lower() == mesh_name.lower() and ext.lower() in (".mrm", ".3ds"):
            return os.path.join(directory, filename), ext.lower()
    return None, None


def import_zen(context, filepath, encoding="windows-1250"):
    """Returns a report dict: vobs_created, waypoints_created,
    ways_linked, level_mesh_status (one of 'imported', 'found_not_importable',
    'not_found', or None if there was no zCVobLevelCompo at all)."""
    with open(filepath, "r", encoding=encoding) as f:
        text = f.read()

    roots = parse_archive(text)
    world_block = roots[0] if roots else None
    if world_block is None:
        raise ValueError("Could not find the top-level world block in this archive")

    report = {
        "vobs_created": 0,
        "waypoints_created": 0,
        "ways_linked": 0,
        "level_mesh_status": None,
        "level_mesh_path": None,
    }

    vob_tree_block = find_block(world_block, type1="VobTree")
    if vob_tree_block is not None:
        for vob_block in vob_tree_block.children:
            real_type = vob_block.type2.split(":")[0]
            if real_type not in _REAL_TYPE_TO_PREFIX:
                continue

            obj = _create_vob_object(context, real_type, vob_block)
            report["vobs_created"] += 1

            if real_type == "zCVobLevelCompo":
                mesh_name = os.path.splitext(vob_block.get("visual", ""))[0]
                if mesh_name:
                    found_path, ext = _find_local_mesh_file(filepath, mesh_name)
                    if found_path is None:
                        report["level_mesh_status"] = "not_found"
                    else:
                        imported_objects = []
                        try:
                            if ext == ".mrm":
                                before = set(bpy.data.objects.keys())
                                krx_mrm_imp = get_krx_mrm_importer()
                                krx_mrm_imp(filename=found_path, scale=0.01)
                                after = set(bpy.data.objects.keys())
                                imported_objects = [bpy.data.objects[n] for n in (after - before)]
                            elif ext == ".3ds":
                                krx_3ds_imp = get_krx_3ds_importer()
                                loader = krx_3ds_imp(filename=found_path, scale=0.01)
                                imported_objects = list(loader.imported_objects)

                            preview_collection = get_preview_collection(context)
                            for imported_obj in imported_objects:
                                for coll in list(imported_obj.users_collection):
                                    coll.objects.unlink(imported_obj)
                                preview_collection.objects.link(imported_obj)
                                imported_obj.parent = obj
                                imported_obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
                                imported_obj["zen_is_preview"] = True
                                imported_obj.hide_select = True
                                imported_obj.lock_location = (True, True, True)
                                imported_obj.lock_rotation = (True, True, True)
                                imported_obj.lock_scale = (True, True, True)

                            report["level_mesh_status"] = "imported"
                            report["level_mesh_path"] = found_path
                            report["level_mesh_objects"] = [o.name for o in imported_objects]
                        except Exception as e:
                            report["level_mesh_status"] = "found_not_importable"
                            report["level_mesh_path"] = found_path
                            report["level_mesh_error"] = str(e)

    way_net_outer = find_block(world_block, type1="WayNet")
    if way_net_outer is not None:
        way_net_inner = way_net_outer.children[0] if way_net_outer.children else None
        if way_net_inner is not None:
            objects_by_index = {}
            way_pairs = []

            for entry in way_net_inner.children:
                if entry.type2 == "\u00a7":
                    obj = objects_by_index.get(entry.object_index)
                else:
                    name = entry.get("wpName", "")
                    obj = _create_waypoint_object(name, entry.get("position"), entry.get("direction"))
                    objects_by_index[entry.object_index] = obj
                    report["waypoints_created"] += 1
                way_pairs.append(obj)

            for i in range(0, len(way_pairs) - 1, 2):
                left, right = way_pairs[i], way_pairs[i + 1]
                if left is not None and right is not None:
                    add_directed_link(left, right)
                    report["ways_linked"] += 1

    return report
