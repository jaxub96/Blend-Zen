from .zen_gin_zcvob_no_visual import NoVisualObjectVob
from .light_conversion import (
    blender_distance_to_gothic_range,
    blender_spot_size_to_gothic_cone_angle,
    blender_color_to_gothic,
)


class ZCVobLight(NoVisualObjectVob):
    """
    Represents an in-game light source (zCVobLight).

    Property names/order match the real archive struct (source: ZenGin
    format issue tracker, cross-referenced with zk.gothickit.dev):

        string lightPresetInUse; enum lightType; float range; color color;
        float spotConeAngle; bool lightStatic; enum lightQuality;
        string lensflareFX; bool turnedOn; string rangeAniScale;
        float rangeAniFPS; bool rangeAniSmooth; string colorAniList;
        float colorAniFPS; bool colorAniSmooth; bool canMove;  # Gothic II only

    NOTE: lightType/lightQuality enum ORDINALS are not independently
    confirmed - only the option names are documented. POINT=0/SPOT=1 and
    HIGH=0/MEDIUM=1/LOW_FASTEST=2 are assumed from listed order. If a
    compiled light doesn't behave as expected in Spacer, this is the
    first thing to double check.

    As of the second version of this class, the corresponding Blender
    object is a real Light (created by zen.add_vob / the ZEN importer -
    see zen_waypoint_tools/light_props.py), not an Empty. lightType,
    range, spotConeAngle and color are read directly from the object's
    native Blender light data (light.type, light.cutoff_distance,
    light.spot_size, light.color) - editing the light normally in
    Blender's own Light Properties tab is what drives these values, so
    the viewport appearance and the exported values can't disagree.

    light_static and the color's alpha channel have no native Blender
    light equivalent and stay as Custom Properties on the object
    (light_static: bool, default True; color_a: int 0-255, default 255).

    Backward compatibility: if the object is NOT a Light (an older
    Empty-based light predating this change), all values fall back to
    reading Custom Properties exactly as the first version of this class
    did (light_type, range, spot_cone_angle, color_r/g/b).
    """

    _type_name = "zCVobLight:zCVob"
    _triangles_limit = 52224
    _static = False
    _collision = False

    _LIGHT_TYPE_ORDINALS = {"POINT": 0, "SPOT": 1}
    _LIGHT_QUALITY_ORDINALS = {"HIGH": 0, "MEDIUM": 1, "LOW_FASTEST": 2}
    _BLENDER_TYPE_TO_LIGHT_TYPE = {"SPOT": "SPOT"}  # anything else (POINT/SUN/AREA) -> POINT
    _DEFAULT_RANGE = 1000.0

    def _visual(self):
        return ""

    def __light_values(self):
        """Returns (light_type, range_cm, spot_cone_angle_deg, (r, g, b))."""
        obj = self._blender_object()
        if obj is not None and obj.type == 'LIGHT':
            data = obj.data
            light_type = self._BLENDER_TYPE_TO_LIGHT_TYPE.get(data.type, "POINT")
            range_cm = (
                blender_distance_to_gothic_range(data.cutoff_distance)
                if data.use_custom_distance else self._DEFAULT_RANGE
            )
            spot_cone_angle = (
                blender_spot_size_to_gothic_cone_angle(data.spot_size)
                if data.type == 'SPOT' else 0.0
            )
            r, g, b = blender_color_to_gothic(data.color)
            return light_type, range_cm, spot_cone_angle, (r, g, b)

        light_type = str(self._custom("light_type", "POINT")).upper()
        range_cm = float(self._custom("range", self._DEFAULT_RANGE))
        spot_cone_angle = float(self._custom("spot_cone_angle", 0.0))
        r = int(self._custom("color_r", 255))
        g = int(self._custom("color_g", 255))
        b = int(self._custom("color_b", 255))
        return light_type, range_cm, spot_cone_angle, (r, g, b)

    def _print_additional_data(self):
        light_type, range_value, spot_cone_angle, (r, g, b) = self.__light_values()
        light_type_ordinal = self._LIGHT_TYPE_ORDINALS.get(light_type, 0)
        light_static = bool(self._custom("light_static", True))
        a = int(self._custom("color_a", 255))

        self._data_printer.print_string_property("lightPresetInUse", "")
        self._data_printer.print_enum_property("lightType", light_type_ordinal)
        self._data_printer.print_float_property("range", range_value)
        self._data_printer.print_color_property("color", "{r} {g} {b} {a}".format(r=r, g=g, b=b, a=a))
        self._data_printer.print_float_property("spotConeAngle", spot_cone_angle)
        self._data_printer.print_bool_property("lightStatic", light_static)
        self._data_printer.print_enum_property("lightQuality", self._LIGHT_QUALITY_ORDINALS["LOW_FASTEST"])
        self._data_printer.print_string_property("lensflareFX", "")
        self._data_printer.print_bool_property("turnedOn", True)
        self._data_printer.print_string_property("rangeAniScale", "")
        self._data_printer.print_float_property("rangeAniFPS", 0.0)
        self._data_printer.print_bool_property("rangeAniSmooth", True)
        self._data_printer.print_string_property("colorAniList", "")
        self._data_printer.print_float_property("colorAniFPS", 0.0)
        self._data_printer.print_bool_property("colorAniSmooth", True)
        self._data_printer.print_bool_property("canMove", False)
