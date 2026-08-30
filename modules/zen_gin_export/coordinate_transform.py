"""
Pure-math Blender<->ZenGin coordinate conversion.

Deliberately has ZERO dependency on Blender or mathutils - every function
here takes and returns plain numbers/tuples. This is what makes it
testable with plain pytest, no fake mathutils stub, no Blender install
required. Anything that DOES need mathutils (turning a quaternion into an
actual rotation matrix) stays in zen_gin_zcvob.py / zen_gin_waynet.py,
which only need to feed the right numbers INTO that step - which is
exactly the part that was previously wrong and went unnoticed.

Background: Blender is right-handed and Z-up. ZenGin is Y-up. The
correct conversion is a single axis swap (Y<->Z) with exactly one sign
flip - this preserves handedness (a proper rotation, determinant +1).
An earlier version of this code negated two axes instead of one, which
is a mirror reflection (determinant -1) rather than a rotation. That bug
shipped unnoticed through every export until a real Spacer test showed
the whole scene mirrored. See git history / ARCHITECTURE.md for the full
story - the point of this module existing on its own is so that mistake
can't happen silently again.
"""


def blender_position_to_gothic(x, y, z, scale=100):
    """Convert a Blender-space position to ZenGin-space, in centimeters
    by default (scale=100 converts Blender's meters to Gothic's cm).

    Returns (gx, gy, gz) already in the exact order they should be
    printed as a ZenGin vec3.
    """
    return (x * scale, z * scale, -y * scale)


def blender_quaternion_to_gothic(w, x, y, z):
    """Convert a Blender rotation quaternion's components (w, x, y, z -
    matching Blender's own mathutils.Quaternion component order) to the
    equivalent quaternion in ZenGin space.

    For a proper (determinant +1) change of basis, a rotation
    quaternion's scalar part (w) is basis-independent and must stay
    untouched - only the vector part (x, y, z) transforms, using the
    identical per-axis mapping as blender_position_to_gothic (X->X,
    Z->Y, Y->-Z).

    Returns (gw, gx, gy, gz) in the same (w, x, y, z) order.
    """
    return (w, x, z, -y)


def is_proper_rotation(matrix_3x3):
    """True if a 3x3 matrix (as 3 row tuples) has determinant +1 (a
    proper rotation) rather than -1 (a mirror reflection). Used by tests
    to assert the coordinate transform above can never regress into a
    mirror again.
    """
    (a, b, c), (d, e, f), (g, h, i) = matrix_3x3
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    return abs(det - 1.0) < 1e-9
