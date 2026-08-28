from .zen_gin_zcvob_no_visual import NoVisualObjectVob


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

    Per-instance tuning is done via Blender custom properties on the
    light's empty (Object Properties > Custom Properties):

        range            float         default 1000.0
        color_r/g/b/a    int (0-255)   default 255,255,255,255
        light_type       "POINT"/"SPOT"  default "POINT"
        spot_cone_angle  float         default 0.0 (SPOT only)
        light_static     bool          default True
    """

    _type_name = "zCVobLight:zCVob"
    _triangles_limit = 52224
    _static = False
    _collision = False

    _LIGHT_TYPE_ORDINALS = {"POINT": 0, "SPOT": 1}
    _LIGHT_QUALITY_ORDINALS = {"HIGH": 0, "MEDIUM": 1, "LOW_FASTEST": 2}

    def _visual(self):
        return ""

    def __custom(self, key, default):
        obj = self._blender_object()
        return obj.get(key, default) if obj is not None else default

    def _print_additional_data(self):
        light_type = str(self.__custom("light_type", "POINT")).upper()
        light_type_ordinal = self._LIGHT_TYPE_ORDINALS.get(light_type, 0)

        range_value = float(self.__custom("range", 1000.0))
        spot_cone_angle = float(self.__custom("spot_cone_angle", 0.0))
        light_static = bool(self.__custom("light_static", True))

        r = int(self.__custom("color_r", 255))
        g = int(self.__custom("color_g", 255))
        b = int(self.__custom("color_b", 255))
        a = int(self.__custom("color_a", 255))

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
