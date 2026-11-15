from .zen_gin_zcvob import ZCVob, _format_vec3
from .vob_fields import LIGHT_DYNAMIC_FIELDS, format_float, print_field, print_fields
from .light_conversion import (
    blender_distance_to_gothic_range,
    blender_spot_size_to_gothic_cone_angle,
    blender_color_to_gothic,
)


class ZCVobLight(ZCVob):
    """
    An in-game light source. Archive order (vanilla worlds):

        lightPresetInUse, lightType, range, color, spotConeAngle,
        lightStatic, lightQuality, lensflareFX
        and, only for dynamic lights (lightStatic=0):
        turnedOn, rangeAniScale, rangeAniFPS, rangeAniSmooth,
        colorAniList, colorAniFPS, colorAniSmooth, canMove

    lightType (0 point, 1 spot), range, spotConeAngle and color are read
    from the Blender light itself (light.type, cutoff_distance, spot_size,
    color), so the viewport and the export can't disagree. Everything
    Blender has no equivalent for is a custom property (vob_fields
    LIGHT_FIELDS / LIGHT_DYNAMIC_FIELDS; color_a is the colour's alpha).

    An object that is not a Light (an Empty from an old version) falls back
    to the custom properties light_type, range, spot_cone_angle,
    color_r/g/b.
    """

    _vob_type = "zCVobLight"

    _LIGHT_TYPE_ORDINALS = {"POINT": 0, "SPOT": 1}
    _DEFAULT_RANGE = 1000.0

    def _light_values(self):
        """(light type, range in cm, spot cone angle in degrees, (r, g, b))."""
        obj = self._object
        if getattr(obj, "type", None) == 'LIGHT':
            data = obj.data
            light_type = "SPOT" if data.type == 'SPOT' else "POINT"
            range_cm = (blender_distance_to_gothic_range(data.cutoff_distance)
                        if data.use_custom_distance else self._DEFAULT_RANGE)
            spot = blender_spot_size_to_gothic_cone_angle(data.spot_size) if data.type == 'SPOT' else 0.0
            return light_type, range_cm, spot, blender_color_to_gothic(data.color)

        return (
            str(self._custom("light_type", "POINT")).upper(),
            float(self._custom("range", self._DEFAULT_RANGE)),
            float(self._custom("spot_cone_angle", 0.0)),
            tuple(int(self._custom(f"color_{c}", 255)) for c in "rgb"),
        )

    def _bounding_box(self, position):
        radius = self._light_values()[1]
        return _format_vec3([p - radius for p in position] + [p + radius for p in position])

    def _print_additional_data(self):
        p = self._data_printer
        light_type, range_cm, spot_cone_angle, (r, g, b) = self._light_values()
        static = bool(self._custom("light_static", True))

        p.print_string_property("lightPresetInUse", self._custom("light_preset", ""))
        p.print_enum_property("lightType", self._LIGHT_TYPE_ORDINALS.get(light_type, 0))
        p.print_property("range", "float", format_float(range_cm))
        p.print_color_property("color", f"{r} {g} {b} {int(self._custom('color_a', 255))}")
        p.print_property("spotConeAngle", "float", format_float(spot_cone_angle))
        p.print_bool_property("lightStatic", static)
        print_field(p, "lightQuality", "enum", self._custom("light_quality", "LOW"), "LOW")
        p.print_string_property("lensflareFX", self._custom("lensflare_fx", ""))
        if not static:
            print_fields(p, LIGHT_DYNAMIC_FIELDS, self._custom, self._vob_type)
