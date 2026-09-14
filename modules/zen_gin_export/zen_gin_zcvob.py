from mathutils import Quaternion
from mathutils import Vector
import struct
from textwrap import wrap
from .printer import Printer
from .coordinate_transform import blender_position_to_gothic, blender_quaternion_to_gothic


class ZCVob:
    _objects_count = 2
    _type_name = "zCVob"
    _triangles_limit = 52224
    _visual_object_type_2 = "zCProgMeshProto"
    _visual_object_triangles_limit = 53505
    _static = True
    _show_visual = True
    _collision = True
    __3ds_extension = ".3DS"

    def __init__(self, blender_object, printer: Printer, data_printer):
        self.__blender_object = blender_object
        self.__printer = printer
        self._data_printer = data_printer

    def updated_object_index(self, object_index):
        return object_index + self._objects_count

    def __start_main_object_block(self, object_index):
        self._data_printer.start_object_block(
            type_2=self._type_name,
            triangles_limit=self._triangles_limit,
            object_index=object_index
        )

    @staticmethod
    def _visual_object_index(object_index):
        return object_index + 1

    def _print_additional_data(self):
        pass

    def _blender_object(self):
        """Protected accessor so subclasses can read custom Blender
        properties (e.g. per-instance light settings) without needing
        direct access to the name-mangled __blender_object."""
        return self.__blender_object

    def __print_visual_block(self, object_index):
        self._data_printer.start_object_block(
            type_1="visual",
            type_2=self._visual_object_type_2,
            triangles_limit=self._visual_object_triangles_limit,
            object_index=self._visual_object_index(object_index)
        )
        self._data_printer.end_object_block()

    def __print_ai(self):
        self._data_printer.start_object_block(type_1="ai")
        self._data_printer.end_object_block()

    def _vob_name(self):
        return self.__blender_object.name.split(":")[-1].split(".")[0]

    def _printed_vob_name(self):
        return self._vob_name()

    def _visual(self):
        return self._vob_name() + self.__3ds_extension

    def __bounding_box(self):
        corners = self.__world_bound_box_corners()
        if not corners:
            # No mesh geometry anywhere in this vob's hierarchy (no
            # preview loaded, or a genuinely visual-less vob like a
            # freepoint) - fall back to the old degenerate single-point
            # box, since there's nothing to size against.
            point = self.__location()
            return "{start} {end}".format(start=point, end=point)
        gothic_points = [
            blender_position_to_gothic(corner.x, corner.y, corner.z)
            for corner in corners
        ]
        mins = [min(point[axis] for point in gothic_points) for axis in range(3)]
        maxs = [max(point[axis] for point in gothic_points) for axis in range(3)]
        return "{minx} {miny} {minz} {maxx} {maxy} {maxz}".format(
            minx=mins[0], miny=mins[1], minz=mins[2],
            maxx=maxs[0], maxy=maxs[1], maxz=maxs[2],
        )

    def __world_bound_box_corners(self):
        """Collect mesh bounding-box corners, in Blender world space,
        from this vob's own object and every mesh descendant - notably
        the KrxImpExp preview mesh that zen_waypoint_tools' mesh-preview
        feature parents under the vob Empty (see mesh_preview.py). The
        vob object itself carries no geometry (it's an Empty), so the
        real bounding box lives entirely on preview children when one
        has been loaded.
        """
        corners = []
        for obj in ZCVob.__self_and_descendants(self.__blender_object):
            bound_box = getattr(obj, "bound_box", None)
            if getattr(obj, "type", None) == "MESH" and bound_box:
                matrix_world = obj.matrix_world
                corners.extend(matrix_world @ Vector(corner) for corner in bound_box)
        return corners

    @staticmethod
    def __self_and_descendants(obj):
        yield obj
        for child in getattr(obj, "children", ()):
            yield from ZCVob.__self_and_descendants(child)

    def __location(self):
        gx, gy, gz = blender_position_to_gothic(
            self.__blender_object.location.x,
            self.__blender_object.location.y,
            self.__blender_object.location.z,
        )
        return "{x} {y} {z}".format(x=gx, y=gy, z=gz)

    @staticmethod
    def float_to_hex(to_convert: float):
        r = round(to_convert, 6)
        h = hex(struct.unpack('<I', struct.pack('<f', r))[0]).split("0x")[1]
        if h == "0":
            return "00000000"
        h_a = wrap(h, 2)
        return h_a[3] + h_a[2] + h_a[1] + h_a[0]

    @staticmethod
    def convert_vector(vector: Vector):
        return "".join([
            ZCVob.float_to_hex(vector.x),
            ZCVob.float_to_hex(vector.y),
            ZCVob.float_to_hex(vector.z)
        ])

    def __rotation(self):
        qt: Quaternion = self.__blender_object.rotation_quaternion
        gw, gx, gy, gz = blender_quaternion_to_gothic(qt[0], qt[1], qt[2], qt[3])
        new_qt = Quaternion((gw, gx, gy, gz))
        return "".join(map(ZCVob.convert_vector, new_qt.to_matrix()))

    def __print_vob_data(self):
        self._data_printer.print_int_property(name="pack", value_int=0)
        self._data_printer.print_string_property(name="presetName", value_string="")
        self._data_printer.print_raw_float_property(name="bbox3DWS", value=self.__bounding_box())
        self._data_printer.print_raw_rotation_property(name="trafoOSToWSRot", value_quaternion=self.__rotation())
        self._data_printer.print_vec3_property(name="trafoOSToWSPos", value_vector=self.__location())
        self._data_printer.print_string_property(name="vobName", value_string=self._printed_vob_name())
        self._data_printer.print_string_property(name="visual", value_string=self._visual())
        self._data_printer.print_bool_property(name="showVisual", value_bool=self._show_visual)
        self._data_printer.print_enum_property(name="visualCamAlign", value_enum_ordinal=0)
        self._data_printer.print_enum_property(name="visualAniMode", value_enum_ordinal=0)
        self._data_printer.print_float_property(name="visualAniModeStrength", value_float=0)
        self._data_printer.print_float_property(name="vobFarClipZScale", value_float=1)
        self._data_printer.print_bool_property(name="cdStatic", value_bool=self._collision)
        self._data_printer.print_bool_property(name="cdDyn", value_bool=self._collision)
        self._data_printer.print_bool_property(name="staticVob", value_bool=self._static)
        self._data_printer.print_enum_property(name="dynShadow", value_enum_ordinal=0)
        self._data_printer.print_int_property(name="zbias", value_int=0)
        self._data_printer.print_bool_property(name="isAmbient", value_bool=False)

    def print(self, object_index):
        self.__start_main_object_block(object_index)
        self.__print_vob_data()
        self.__print_visual_block(object_index=object_index)
        self.__print_ai()
        self._print_additional_data()
        self._data_printer.end_object_block()
        return self.updated_object_index(object_index)
