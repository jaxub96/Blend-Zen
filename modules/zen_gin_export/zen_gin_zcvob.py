"""
zCVob and the simple vob types that only override flags.

A vob writes its base block (pack, bbox3DWS, trafoOSToWSRot/Pos, vobName,
visual, flags...), a `visual` sub-block, an empty `ai` sub-block, then any
type-specific properties (_print_additional_data). Header class versions
and flags follow real Spacer-saved worlds (blender_work_dir/*.ZEN).
"""

import re

from .coordinate_transform import (
    blender_matrix_to_gothic,
    blender_position_to_gothic,
    encode_rotation_matrix_hex,
)

_DUPLICATE_SUFFIX_RE = re.compile(r"\.\d{3,}$")


def vob_name_from_object_name(name):
    """'zCVob:ROCK_01.003' -> 'ROCK_01': everything after the type prefix,
    minus Blender's numeric duplicate suffix. Other dots are kept."""
    _, _, rest = name.partition(":")
    return _DUPLICATE_SUFFIX_RE.sub("", rest)


def _format_vec3(values):
    # Rounded so float noise (7.5e-08, 1100.0000000000002) doesn't reach
    # the file; "+ 0.0" turns -0.0 into 0.0.
    return " ".join(str(round(v, 6) + 0.0) for v in values)


class ZCVob:
    _type_name = "zCVob"
    _class_version = 52224
    # Number of object-index slots this vob uses (main block + visual).
    _objects_count = 2
    _visual_type = "zCProgMeshProto"
    _visual_version = 53505
    _visual_extension = ".3DS"
    _static = True
    _show_visual = True
    _collision = True

    def __init__(self, blender_object, data_printer):
        self._object = blender_object
        self._data_printer = data_printer

    # -- overridable pieces -------------------------------------------------

    def _vob_name(self):
        return vob_name_from_object_name(self._object.name)

    def _printed_vob_name(self):
        return self._vob_name()

    def _visual(self):
        return self._vob_name() + self._visual_extension

    def _visual_object_index(self, object_index):
        return object_index + 1

    def _print_additional_data(self):
        pass

    def _custom(self, key, default):
        """A flat custom (ID) property on the Blender object, or default.
        This is how per-instance data (light/mob/sound settings) is read,
        keeping this package independent of the addon's PropertyGroups."""
        getter = getattr(self._object, "get", None)
        return getter(key, default) if getter is not None else default

    # -- geometry -----------------------------------------------------------

    def _bounding_box(self, position):
        """World-space AABB of every mesh in this object's hierarchy (the
        object itself if it is a mesh, plus mesh children), in Gothic
        space. Falls back to a single point at the vob's position."""
        xs, ys, zs = [], [], []
        for obj in _self_and_descendants(self._object):
            bound_box = getattr(obj, "bound_box", None)
            if getattr(obj, "type", None) != "MESH" or not bound_box:
                continue
            m = obj.matrix_world
            for cx, cy, cz in bound_box:
                wx = m[0][0] * cx + m[0][1] * cy + m[0][2] * cz + m[0][3]
                wy = m[1][0] * cx + m[1][1] * cy + m[1][2] * cz + m[1][3]
                wz = m[2][0] * cx + m[2][1] * cy + m[2][2] * cz + m[2][3]
                gx, gy, gz = blender_position_to_gothic(wx, wy, wz)
                xs.append(gx)
                ys.append(gy)
                zs.append(gz)
        if not xs:
            return f"{_format_vec3(position)} {_format_vec3(position)}"
        return _format_vec3((min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)))

    # -- output -------------------------------------------------------------

    def print(self, object_index):
        p = self._data_printer
        position, rotation = blender_matrix_to_gothic(self._object.matrix_world)

        p.start_object_block(type_2=self._type_name, triangles_limit=self._class_version,
                             object_index=object_index)
        p.print_int_property("pack", 0)
        p.print_string_property("presetName", "")
        p.print_raw_float_property("bbox3DWS", self._bounding_box(position))
        p.print_raw_rotation_property("trafoOSToWSRot", encode_rotation_matrix_hex(rotation))
        p.print_vec3_property("trafoOSToWSPos", _format_vec3(position))
        p.print_string_property("vobName", self._printed_vob_name())
        p.print_string_property("visual", self._visual())
        p.print_bool_property("showVisual", self._show_visual)
        p.print_enum_property("visualCamAlign", 0)
        p.print_enum_property("visualAniMode", 0)
        p.print_float_property("visualAniModeStrength", 0)
        p.print_float_property("vobFarClipZScale", 1)
        p.print_bool_property("cdStatic", self._collision)
        p.print_bool_property("cdDyn", self._collision)
        p.print_bool_property("staticVob", self._static)
        p.print_enum_property("dynShadow", 0)
        p.print_int_property("zbias", 0)
        p.print_bool_property("isAmbient", False)

        p.start_object_block(type_1="visual", type_2=self._visual_type,
                             triangles_limit=self._visual_version,
                             object_index=self._visual_object_index(object_index))
        p.end_object_block()
        p.start_object_block(type_1="ai")
        p.end_object_block()

        self._print_additional_data()
        p.end_object_block()
        return object_index + self._objects_count


def _self_and_descendants(obj):
    yield obj
    for child in getattr(obj, "children", ()):
        yield from _self_and_descendants(child)


class NoVisualObjectVob(ZCVob):
    """Base for vobs without a mesh: `[visual % 0 0]`, one index slot."""
    _objects_count = 1
    _visual_type = "%"
    _visual_version = 0

    def _visual(self):
        return ""

    def _visual_object_index(self, object_index):
        return 0


class ZCVobLevelCompo(ZCVob):
    """Reference to the level mesh; Spacer compiles the named .3DS in."""
    _type_name = "zCVobLevelCompo:zCVob"
    _visual_type = "zCMesh"
    _static = False
    _collision = False
    _show_visual = False

    def _printed_vob_name(self):
        return "LEVEL-VOB"


class ZCVobSpot(NoVisualObjectVob):
    _type_name = "zCVobSpot:zCVob"
    _static = False
    _collision = False


class ZCVobStartpoint(NoVisualObjectVob):
    _type_name = "zCVobStartpoint:zCVob"
    _static = False
    _collision = False


class OCItem(NoVisualObjectVob):
    """itemInstance is the Daedalus script instance name (the vob's own
    name, e.g. ITMW_1H_PAL_SWORD), not a mesh filename - confirmed in
    Spacer: a mesh name here resolves no visual in-game."""
    _type_name = "oCItem:zCVob"
    _class_version = 0
    _static = False
    _show_visual = False

    def _print_additional_data(self):
        self._data_printer.print_string_property("itemInstance", self._vob_name())
