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


# Gothic's lighting is (approximately) linear: a vob light adds
# colour * (1 - distance/range), reaching 0 at `range`, with no inverse-square
# falloff, and the engine does that maths directly on display (gamma-encoded)
# values. Blender's point lights are inverse-square on linear values with a
# filmic/AgX view transform, so a naive port (the old "power = range * 2")
# came out roughly 10x too bright and far too hot near the light.
#
# We can't change Blender's falloff curve, so match the two at half range,
# where Gothic gives 0.5 (display value). Calibrated with Cycles (white
# diffuse plane, Raw view): radiance L = P / (16 * pi * d^2) for a point
# light of P watts at distance d facing the surface.
GOTHIC_MATCH_FRACTION = 0.5     # distance (as a fraction of range) to match at
GOTHIC_DISPLAY_GAMMA = 2.2      # Gothic maths is on display values, Blender's on linear


def gothic_range_to_blender_power(range_cm, scale=100):
    """Point-light power in watts that gives the same brightness as a Gothic
    light of this range (cm) at half range, with the Standard view transform."""
    distance_m = (range_cm / scale) * GOTHIC_MATCH_FRACTION
    target_display = 1.0 - GOTHIC_MATCH_FRACTION
    target_linear = target_display ** GOTHIC_DISPLAY_GAMMA
    return 16.0 * math.pi * distance_m ** 2 * target_linear


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
