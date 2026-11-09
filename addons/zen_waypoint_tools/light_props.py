"""
Blender-side helper for creating a properly-configured zCVobLight object.

Creates a real Blender Light (not an Empty), so it actually illuminates
the scene and can be tuned via Blender's own native Light Properties tab.
The exporter (zen_gin_export's ZCVobLight) reads back from these same
native properties, so what you see in the viewport is what gets exported.

Used by both ZEN_OT_add_vob (new light creation) and zen_import.py
(reconstructing a light from a parsed ZEN) - one place for this so they
can't drift apart. Shares its unit-conversion math with the export side
via zen_gin_export.light_conversion.
"""

import bpy

DEFAULT_RANGE_CM = 1000.0
DEFAULT_SPOT_CONE_ANGLE_DEG = 35.0

_LIGHT_TYPE_TO_BLENDER = {"POINT": 'POINT', "SPOT": 'SPOT'}


def create_light_object(name, light_type="POINT", range_cm=DEFAULT_RANGE_CM,
                         spot_cone_angle_deg=DEFAULT_SPOT_CONE_ANGLE_DEG,
                         color_rgb=(255, 255, 255), color_a=255, light_static=True):
    from zen_gin_export import (
        gothic_range_to_blender_distance,
        gothic_range_to_blender_power,
        gothic_cone_angle_to_blender_spot_size,
        gothic_color_to_blender,
    )

    blender_type = _LIGHT_TYPE_TO_BLENDER.get(light_type, 'POINT')
    light_data = bpy.data.lights.new(name=name, type=blender_type)

    light_data.use_custom_distance = True
    light_data.cutoff_distance = gothic_range_to_blender_distance(range_cm)
    light_data.color = gothic_color_to_blender(*color_rgb)

    # Viewport-only brightness, calibrated so the light looks like it does
    # in Spacer/in-game (see gothic_range_to_blender_power). Never read for
    # export; adjust by hand freely.
    light_data.energy = gothic_range_to_blender_power(range_cm)
    light_data.shadow_soft_size = 0.0   # Gothic lights are points
    # Static lights are baked into lightmaps (shadowed); dynamic ones are not.
    light_data.use_shadow = bool(light_static)

    if blender_type == 'SPOT':
        light_data.spot_size = gothic_cone_angle_to_blender_spot_size(spot_cone_angle_deg)

    obj = bpy.data.objects.new(name, light_data)
    obj["light_static"] = light_static
    obj["color_a"] = color_a
    return obj
