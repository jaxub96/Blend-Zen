"""
Pure-math Gothic <-> Blender light property conversion.

Zero Blender dependency, same design principle as coordinate_transform.py.
Gothic's zCVobLight range/color have a natural, if approximate, mapping
onto Blender's native Light properties (cutoff_distance and color) - this
keeps that mapping in one place so the export side (zen_gin_zcvob_light.py)
and the creation/import side (zen_waypoint_tools/light_props.py) can't
drift apart the way the position/rotation transform once did.
"""

import math


def gothic_range_to_blender_distance(range_cm, scale=100):
    """Gothic range (cm) -> Blender light.cutoff_distance (meters)."""
    return range_cm / scale


def blender_distance_to_gothic_range(distance_m, scale=100):
    """Inverse of gothic_range_to_blender_distance()."""
    return distance_m * scale


def gothic_cone_angle_to_blender_spot_size(angle_degrees):
    """Gothic spotConeAngle (degrees) -> Blender light.spot_size (radians)."""
    return math.radians(angle_degrees)


def blender_spot_size_to_gothic_cone_angle(spot_size_radians):
    """Inverse of gothic_cone_angle_to_blender_spot_size()."""
    return math.degrees(spot_size_radians)


def gothic_color_to_blender(r, g, b):
    """Gothic color channels (0-255 ints) -> Blender light.color (0.0-1.0 floats)."""
    return (r / 255.0, g / 255.0, b / 255.0)


def blender_color_to_gothic(color):
    """Inverse of gothic_color_to_blender(). Returns (r, g, b) as 0-255 ints."""
    return tuple(int(round(c * 255)) for c in color)
