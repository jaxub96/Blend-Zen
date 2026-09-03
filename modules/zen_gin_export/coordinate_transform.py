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

    The vector part uses the same per-axis permutation as
    blender_position_to_gothic (X->X, Z->Y, Y->-Z), but NEGATED - i.e.
    the rotation angle is inverted while the rotation axis stays the
    same physical line. The scalar part (w) does not change sign, since
    w = cos(angle/2) is identical for +angle and -angle.

    Why the negation: a determinant check alone (is this a proper
    rotation vs a mirror) cannot catch "rotating the correct axis by the
    wrong sign" - both a +90 and a -90 degree rotation about the same
    axis are valid proper rotations (determinant +1). The unnegated
    version was mathematically self-consistent (verified by round-trip
    testing) but empirically produced the wrong direction in a real
    Spacer test: a prop rotated +90 degrees about Blender's vertical
    axis (a bookshelf) came out facing the opposite direction in-game,
    while un-rotated props in the same scene were unaffected - exactly
    the signature of a rotation-direction sign error rather than a
    handedness/mirror error (identity rotations are unaffected by
    negating the angle, since -0 == 0).

    This fix is inferred from that empirical evidence, not derived from
    an independent authoritative spec of ZenGin's rotation convention -
    if a future test shows rotations are wrong in some other way, this
    is the first place to revisit.

    Returns (gw, gx, gy, gz) in the same (w, x, y, z) order.
    """
    return (w, -x, -z, y)


def is_proper_rotation(matrix_3x3):
    """True if a 3x3 matrix (as 3 row tuples) has determinant +1 (a
    proper rotation) rather than -1 (a mirror reflection). Used by tests
    to assert the coordinate transform above can never regress into a
    mirror again.
    """
    (a, b, c), (d, e, f), (g, h, i) = matrix_3x3
    det = a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)
    return abs(det - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# Inverse direction: Gothic (Y-up) -> Blender (right-handed, Z-up), used by
# the ZEN importer. Verified to round-trip correctly (see test suite) by
# constructing the forward transform matrix and confirming
# gothic_matrix_to_blender_matrix(forward(M)) == M for both identity and a
# real 90-degree rotation.
# ---------------------------------------------------------------------------

def gothic_position_to_blender(gx, gy, gz, scale=100):
    """Inverse of blender_position_to_gothic()."""
    return (gx / scale, -gz / scale, gy / scale)


# The forward linear map (scale=1) as a plain 3x3 matrix: R @ v_blender = v_gothic
_FORWARD_MATRIX = (
    (1, 0, 0),
    (0, 0, 1),
    (0, -1, 0),
)


def _matmul_3x3(a, b):
    return tuple(
        tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3))
        for i in range(3)
    )


def gothic_matrix_to_blender_matrix(matrix_3x3):
    """Inverse of the change of basis applied to a rotation matrix by the
    coordinate transform. `matrix_3x3` is a Gothic-space rotation matrix
    (3 row tuples); returns the equivalent Blender-space matrix, same
    shape. Since the forward matrix R is orthogonal, R^-1 == R^T, so this
    computes R^T @ matrix_3x3 @ R.
    """
    r = _FORWARD_MATRIX
    r_transpose = tuple(zip(*r))
    return _matmul_3x3(_matmul_3x3(r_transpose, matrix_3x3), r)


def hex_to_float(hex_str_8chars):
    """Inverse of ZCVob.float_to_hex(): decode one 8-hex-char, byte-swapped
    IEEE754 float back to a Python float."""
    import struct
    pairs = [hex_str_8chars[i:i + 2] for i in range(0, 8, 2)]
    original_order = pairs[3] + pairs[2] + pairs[1] + pairs[0]
    uint_value = int(original_order, 16)
    return struct.unpack("<f", struct.pack("<I", uint_value))[0]


def decode_rotation_matrix_hex(hex_string):
    """Decode a trafoOSToWSRot raw hex string (72 hex chars = 9 floats,
    row-major 3x3) back into a plain 3x3 tuple-of-tuples matrix."""
    floats = [hex_to_float(hex_string[i:i + 8]) for i in range(0, 72, 8)]
    return (
        tuple(floats[0:3]),
        tuple(floats[3:6]),
        tuple(floats[6:9]),
    )
