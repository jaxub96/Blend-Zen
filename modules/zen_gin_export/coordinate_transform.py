"""
Pure-math Blender<->ZenGin coordinate conversion.

Deliberately has ZERO dependency on Blender or mathutils - every function
here takes and returns plain numbers/tuples, so it's testable with plain
pytest. Matrix/quaternion construction that needs mathutils lives in
zen_gin_zcvob.py / zen_gin_waynet.py, which just feed numbers in.

Blender is right-handed and Z-up; ZenGin is Y-up AND LEFT-HANDED
(confirmed by the "Compass Cross" test, documentation/
transform_investigation.md - don't re-derive this again). So the
conversion is a plain Y<->Z axis swap with NO sign flip - determinant
-1, a handedness flip, not a rotation. See the doc for how that was
verified (an independent, non-circular comparison against real compiled
mesh geometry in Spacer) and for the rotation-formula derivation below.
"""


def blender_position_to_gothic(x, y, z, scale=100):
    """Blender position -> ZenGin position, in cm by default (scale=100
    converts Blender's meters). Returns (gx, gy, gz) in vec3 print order.
    """
    return (x * scale, z * scale, y * scale)


def blender_quaternion_to_gothic(w, x, y, z):
    """Blender rotation quaternion (w, x, y, z) -> ZenGin quaternion.

    The general, re-derivable rule for converting a quaternion across
    ANY orthogonal change of basis R (this is what to redo if R above
    ever changes - not a fresh sympy session):
      - w is unchanged: trace is invariant under conjugation by any R,
        proper or not.
      - The vector part (x, y, z) is a PSEUDOVECTOR, not a plain
        position-like vector - it transforms as `det(R) * (R @ v)`,
        picking up a sign flip from det(R) that an ordinary vector
        (like a position) doesn't.

    For our R (the Y<->Z swap above, det -1): R @ (x, y, z) = (x, z, y),
    then the det(R) = -1 flips every component's sign, giving
    (-x, -z, -y). This matches a real Spacer test that first caught the
    old formula's sign as wrong (a bookshelf rotated +90 degrees about
    Blender Z came out facing backwards in-game).
    """
    return (w, -x, -z, -y)


def is_proper_rotation(matrix_3x3):
    """True if a 3x3 matrix (as 3 row tuples) has determinant +1 (a
    proper rotation) rather than -1 (a reflection).

    Not a check for blender_position_to_gothic's own matrix - that one
    is correctly -1 (Gothic is left-handed). Used instead to check the
    real invariant: a genuine rotation, conjugated into any orthogonal
    coordinate system, always stays a proper rotation regardless of that
    system's handedness - see blender_quaternion_to_gothic's tests.
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
    return (gx / scale, gz / scale, gy / scale)


# The forward linear map (scale=1) as a plain 3x3 matrix: R @ v_blender = v_gothic
_FORWARD_MATRIX = (
    (1, 0, 0),
    (0, 0, 1),
    (0, 1, 0),
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
