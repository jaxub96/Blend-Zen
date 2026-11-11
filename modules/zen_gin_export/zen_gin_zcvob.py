"""
The vob writer. Every vob type is the same block shape - base properties
(pack, bbox3DWS, trafoOSToWSRot/Pos, vobName, visual, flags...), a `visual`
sub-block, an empty `ai` sub-block, then the type's own properties - and
all of it is driven by the tables in vob_fields.py. Subclasses only exist
where a type needs logic of its own (lights) or as named handles.

The Blender object's name is `<vob type>:<vob name>`; everything else is
read from flat custom properties with obj.get().
"""

import re

from .coordinate_transform import (
    blender_matrix_to_gothic,
    blender_position_to_gothic,
    encode_rotation_matrix_hex,
    encode_mover_keyframes,
)
from .vob_fields import (
    BASE_FIELDS, DECAL_FIELDS, VOB_SPECS, VISUAL_BLOCKS, LIST_SLOTS,
    TRIGGER_FLAG_BITS, TRIGGER_FILTER_BITS, TRIGGER_IS_ENABLED_BIT,
    MOVER_MOTION_FIELDS, MOVER_KEY_PROPERTY,
    field_default, base_default, print_field, print_fields, visual_extension, format_float,
)

_DUPLICATE_SUFFIX_RE = re.compile(r"\.\d{3,}$")


def vob_name_from_object_name(name):
    """'zCVob:ROCK_01.003' -> 'ROCK_01': everything after the type prefix,
    minus Blender's numeric duplicate suffix. Other dots are kept."""
    _, _, rest = name.partition(":")
    return _DUPLICATE_SUFFIX_RE.sub("", rest)


def vob_type_of(blender_object):
    """The vob type an object's name prefix names, or None."""
    try:
        prefix, sep, _ = blender_object.name.partition(":")
    except (AttributeError, ReferenceError):
        return None
    return prefix if sep and prefix in VOB_SPECS else None


def _format_vec3(values):
    # Rounded so float noise (7.5e-08, 1100.0000000000002) doesn't reach
    # the file; "+ 0.0" turns -0.0 into 0.0.
    return " ".join(str(round(v, 6) + 0.0) for v in values)


def _world_point(matrix, x, y, z):
    return blender_position_to_gothic(
        matrix[0][0] * x + matrix[0][1] * y + matrix[0][2] * z + matrix[0][3],
        matrix[1][0] * x + matrix[1][1] * y + matrix[1][2] * z + matrix[1][3],
        matrix[2][0] * x + matrix[2][1] * y + matrix[2][2] * z + matrix[2][3],
    )


def _aabb(points):
    xs, ys, zs = zip(*points)
    return _format_vec3((min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)))


def mover_keyframe_objects(blender_object):
    """A mover's keyframe empties (children carrying MOVER_KEY_PROPERTY),
    in keyframe order."""
    keyed = []
    for child in getattr(blender_object, "children", ()):
        getter = getattr(child, "get", None)
        index = getter(MOVER_KEY_PROPERTY, None) if getter else None
        if index is not None:
            keyed.append((int(index), child.name, child))
    return [child for _, _, child in sorted(keyed, key=lambda k: k[:2])]


class ZCVob:
    _vob_type = "zCVob"

    def __init__(self, blender_object, data_printer):
        self._object = blender_object
        self._data_printer = data_printer
        self._spec = VOB_SPECS[self._vob_type]

    # -- names and custom properties ------------------------------------------

    def _vob_name(self):
        return vob_name_from_object_name(self._object.name)

    def _printed_vob_name(self):
        return "LEVEL-VOB" if self._vob_type == "zCVobLevelCompo" else self._vob_name()

    def _custom(self, key, default):
        """A flat custom (ID) property on the Blender object, or default."""
        getter = getattr(self._object, "get", None)
        return getter(key, default) if getter is not None else default

    def _visual(self):
        spec = self._spec
        if spec.visual == "none":
            return ""
        if spec.visual == "name":
            base = self._vob_name()
        else:
            base = str(self._custom("visual_name", "")).strip()
            if not base and spec.visual == "custom":
                base = self._vob_name()
        if not base:
            return ""
        return base if "." in base else base + spec.default_extension

    def _keeps_scale(self):
        """True for vobs with a visual: only those write the object's scale
        into their matrix (a scaled zone is a bigger box, a scaled spot or
        light is just a bigger gizmo in Blender)."""
        return self._spec.volume is None and bool(self._visual())

    def _visual_block(self):
        """(class, version) of the visual sub-block, or None for `[visual % 0 0]`."""
        visual = self._visual()
        if not visual:
            return None
        if self._vob_type == "zCVobLevelCompo":
            return ("zCMesh", 53505)
        return VISUAL_BLOCKS.get(visual_extension(visual), VISUAL_BLOCKS[".3DS"])

    @property
    def _objects_count(self):
        """Object-index slots this vob uses (main block + a real visual)."""
        return 1 if self._visual_block() is None else 2

    # -- geometry ---------------------------------------------------------------

    def _radius(self):
        key = self._spec.volume
        default = next(d for _, _, k, d in self._spec.fields if k == key)
        try:
            return float(self._custom(key, default))
        except (TypeError, ValueError):
            return float(default)

    def _bounding_box(self, position):
        """bbox3DWS in Gothic space: the object's own cube for box volumes
        (zones, triggers), a cube around the position for radius volumes
        (sounds, lights), else the world-space AABB of the meshes in this
        object's hierarchy, else a point."""
        volume = self._spec.volume
        obj = self._object
        if volume == "box":
            corners = getattr(obj, "bound_box", None) if getattr(obj, "type", None) == "MESH" else None
            if not corners:
                size = float(getattr(obj, "empty_display_size", 1.0))
                corners = [(x, y, z) for x in (-size, size) for y in (-size, size) for z in (-size, size)]
            return _aabb([_world_point(obj.matrix_world, *c) for c in corners])
        if volume is not None:
            radius = self._radius()
            return _format_vec3([p - radius for p in position] + [p + radius for p in position])

        points = []
        for mesh in _own_meshes(obj):
            points += [_world_point(mesh.matrix_world, *c) for c in mesh.bound_box]
        if not points:
            # An empty showing a preview mesh (vob_preview): the instanced
            # collection's meshes sit at the empty's transform.
            collection = getattr(obj, "instance_collection", None)
            for mesh in (collection.all_objects if collection is not None else ()):
                if mesh.type == "MESH":
                    matrix = obj.matrix_world @ mesh.matrix_basis
                    points += [_world_point(matrix, *c) for c in mesh.bound_box]
        if not points:
            return f"{_format_vec3(position)} {_format_vec3(position)}"
        return _aabb(points)

    # -- output -------------------------------------------------------------------

    def _print_base_field(self, entry):
        archive_name, archive_type, key, _ = entry
        default = base_default(self._vob_type, key)
        print_field(self._data_printer, archive_name, archive_type, self._custom(key, default), default)

    def _print_visual_block(self, object_index):
        p = self._data_printer
        block = self._visual_block()
        if block is None:
            p.start_object_block(type_1="visual")
        else:
            p.start_object_block(type_1="visual", type_2=block[0], triangles_limit=block[1],
                                 object_index=object_index + 1)
            if block[0] == "zCDecal":
                p.print_string_property("name", self._visual())
                print_fields(p, DECAL_FIELDS, self._custom)
        p.end_object_block()

    def _trigger_byte(self, bits, extra=0):
        byte = extra
        for key, mask, default in bits:
            if self._custom(key, field_default(self._vob_type, key, default)):
                byte |= mask
        return byte

    def _print_slots(self, count_name, slot_fields):
        """A counted list (trigger list targets, code master slaves): the
        filled slots, compacted. slot_fields: [(archive name fmt, type, key fmt, default)]."""
        p = self._data_printer
        filled = [i for i in range(LIST_SLOTS)
                  if str(self._custom(slot_fields[0][2].format(i), "")).strip()]
        p.print_int_property(count_name, len(filled))
        for out_index, slot in enumerate(filled):
            for name_fmt, archive_type, key_fmt, default in slot_fields:
                print_field(p, name_fmt.format(out_index), archive_type,
                            self._custom(key_fmt.format(slot), default), default)

    def _print_mover_keyframes(self):
        p = self._data_printer
        keys = mover_keyframe_objects(self._object)
        p.print_int_property("numKeyframes", len(keys))
        if not keys:
            return
        print_fields(p, MOVER_MOTION_FIELDS, self._custom, self._vob_type)
        p.print_property("keyframes", "raw", encode_mover_keyframes(
            [blender_matrix_to_gothic(key.matrix_world) for key in keys]))

    def _print_additional_data(self):
        p = self._data_printer
        for entry in self._spec.fields:
            archive_name, archive_type, key, default = entry
            if archive_type == "vobName":
                p.print_string_property(archive_name, self._vob_name())
            elif archive_type == "triggerFlags":
                byte = self._trigger_byte(TRIGGER_FLAG_BITS)
                if byte & 0x01:
                    byte |= TRIGGER_IS_ENABLED_BIT
                p.print_property(archive_name, "raw", f"{byte:02x}")
            elif archive_type == "triggerFilter":
                p.print_property(archive_name, "raw", f"{self._trigger_byte(TRIGGER_FILTER_BITS):02x}")
            elif archive_type == "triggerList":
                self._print_slots(archive_name, (("triggerTarget{}", "string", "list_target_{}", ""),
                                                 ("fireDelay{}", "float", "list_delay_{}", 0.0)))
            elif archive_type == "codeMasterSlaves":
                self._print_slots(archive_name, (("slaveVobName{}", "string", "slave_{}", ""),))
            elif archive_type == "moverKeyframes":
                self._print_mover_keyframes()
            elif key in ("sound_name", "pfx_name") and not str(self._custom(key, "")).strip():
                # blank = named by the vob itself (how older scenes store sounds)
                p.print_string_property(archive_name, self._vob_name())
            else:
                print_fields(p, (entry,), self._custom, self._vob_type)

    def print(self, object_index):
        p = self._data_printer
        position, rotation = blender_matrix_to_gothic(
            self._object.matrix_world, keep_scale=self._keeps_scale())

        p.start_object_block(type_2=self._spec.chain, triangles_limit=self._spec.version,
                             object_index=object_index)
        p.print_int_property("pack", 0)
        self._print_base_field(BASE_FIELDS[0])                      # presetName
        p.print_raw_float_property("bbox3DWS", self._bounding_box(position))
        p.print_raw_rotation_property("trafoOSToWSRot", encode_rotation_matrix_hex(rotation))
        p.print_vec3_property("trafoOSToWSPos", _format_vec3(position))
        p.print_string_property("vobName", self._printed_vob_name())
        p.print_string_property("visual", self._visual())
        for entry in BASE_FIELDS[1:]:
            self._print_base_field(entry)

        self._print_visual_block(object_index)
        p.start_object_block(type_1="ai")
        p.end_object_block()

        self._print_additional_data()
        p.end_object_block()
        return object_index + self._objects_count


def _own_meshes(obj):
    """The object if it is a mesh, plus mesh descendants - stopping at
    children that are vobs themselves (they write their own bbox)."""
    if getattr(obj, "type", None) == "MESH" and getattr(obj, "bound_box", None):
        yield obj
    for child in getattr(obj, "children", ()):
        if vob_type_of(child) is None:
            yield from _own_meshes(child)


def _named(class_name, vob_type):
    return type(class_name, (ZCVob,), {"_vob_type": vob_type, "__doc__": f"{vob_type} (see vob_fields.VOB_SPECS)."})


ZCVobLevelCompo = _named("ZCVobLevelCompo", "zCVobLevelCompo")
ZCVobSpot = _named("ZCVobSpot", "zCVobSpot")
ZCVobStartpoint = _named("ZCVobStartpoint", "zCVobStartpoint")
# itemInstance is the Daedalus script instance name (the vob's own name,
# e.g. ITMW_1H_PAL_SWORD), not a mesh filename - confirmed in Spacer.
OCItem = _named("OCItem", "oCItem")
