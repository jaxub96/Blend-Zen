"""
Pure-math Blender<->ZenGin coordinate conversion.

Deliberately has ZERO dependency on Blender or mathutils - every function
here takes and returns plain numbers/tuples (a Blender `matrix_world` is
read through plain `m[row][col]` indexing), so it's testable with plain
pytest.

Blender is right-handed and Z-up; ZenGin is Y-up AND LEFT-HANDED
(confirmed by the "Compass Cross" test, README.md "Coordinate transform" - don't re-derive this again). So the
conversion is a plain Y<->Z axis swap with NO sign flip - determinant
-1, a handedness flip, not a rotation. See the doc for how that was
verified (an independent, non-circular comparison against real compiled
mesh geometry in Spacer) and for the rotation-formula derivation below.
"""

import math
import struct


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


# The forward linear map (scale=1) as a plain 3x3 matrix: R @ v_blender = v_gothic.
# R is symmetric and its own inverse, so the same conjugation R @ M @ R
# converts a rotation matrix in either direction.
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


def _change_basis(matrix_3x3):
    r = _FORWARD_MATRIX
    return _matmul_3x3(_matmul_3x3(r, matrix_3x3), r)


def gothic_matrix_to_blender_matrix(matrix_3x3):
    """Gothic-space rotation matrix (3 row tuples) -> the equivalent
    Blender-space matrix, same shape: R^T @ M @ R (R^T == R here)."""
    return _change_basis(matrix_3x3)


def blender_matrix_to_gothic(matrix_world, scale=100):
    """Blender 4x4 world matrix (row-indexable, e.g. `obj.matrix_world`) ->
    (Gothic position (gx, gy, gz), Gothic 3x3 rotation as row tuples).

    Reading the world matrix rather than `location`/`rotation_quaternion`
    makes this independent of rotation mode (Euler or quaternion) and
    includes parent transforms. Object scale is removed from the rotation
    (each axis column is normalized). Equivalent to
    blender_quaternion_to_gothic() for a pure rotation - see the tests.
    """
    m = matrix_world
    position = blender_position_to_gothic(m[0][3], m[1][3], m[2][3], scale=scale)
    columns = []
    for j in range(3):
        column = _normalize(m[0][j], m[1][j], m[2][j]) or tuple(float(i == j) for i in range(3))
        columns.append(column)
    blender_rotation = tuple(tuple(columns[j][i] for j in range(3)) for i in range(3))
    return position, _change_basis(blender_rotation)


def float_to_hex(value):
    """One float as ZenGin's `raw` encoding: the IEEE754 single's 4 bytes,
    little-endian, as 8 hex chars (1.0 -> "0000803f"). Rounded to 6
    decimals first so float noise like 1e-17 writes as a clean 0."""
    return struct.pack("<f", round(value, 6)).hex()


def hex_to_float(hex_str_8chars):
    """Inverse of float_to_hex()."""
    return struct.unpack("<f", bytes.fromhex(hex_str_8chars))[0]


def encode_rotation_matrix_hex(matrix_3x3):
    """3x3 rotation (row tuples) -> trafoOSToWSRot raw hex string
    (9 floats, row-major)."""
    return "".join(float_to_hex(v) for row in matrix_3x3 for v in row)


def decode_rotation_matrix_hex(hex_string):
    """Inverse of encode_rotation_matrix_hex(): 72 hex chars -> 3x3 rows."""
    floats = [hex_to_float(hex_string[i:i + 8]) for i in range(0, 72, 8)]
    return (
        tuple(floats[0:3]),
        tuple(floats[3:6]),
        tuple(floats[6:9]),
    )


# ---------------------------------------------------------------------------
# Waypoint facing direction.
#
# A zCWaypoint has no rotation matrix in the archive - only a `direction`
# vec3 (the waypoint's "at" vector: where an NPC faces after
# AI_AlignToWP, or after being spawned/teleported onto it). In Blender a
# waypoint is an ARROWS ("csys") empty whose local +Y axis IS that
# direction, so the visible green Y arrow is what gets exported - the same
# forward axis as every other vob (Gothic's local "at" axis +Z maps to
# Blender local +Y), so waypoints and freepoints read alike.
#
# A direction is an ordinary (polar) vector, so it converts with the same
# verified Y<->Z swap as a position, just unscaled and normalized.
# ---------------------------------------------------------------------------

def _normalize(x, y, z):
    length = (x * x + y * y + z * z) ** 0.5
    if length < 1e-9:
        return None
    return (x / length, y / length, z / length)


# Used only when a direction is degenerate (zero-length): Gothic world +Z
# (Blender +Y), i.e. an unrotated waypoint.
_FALLBACK_GOTHIC_DIRECTION = (0.0, 0.0, 1.0)


def blender_direction_to_gothic(x, y, z):
    """Blender world-space direction -> normalized ZenGin direction."""
    n = _normalize(x, y, z)
    if n is None:
        return _FALLBACK_GOTHIC_DIRECTION
    return blender_position_to_gothic(*n, scale=1)


def gothic_direction_to_blender(gx, gy, gz):
    """Inverse of blender_direction_to_gothic()."""
    n = _normalize(gx, gy, gz)
    if n is None:
        n = _FALLBACK_GOTHIC_DIRECTION
    return gothic_position_to_blender(*n, scale=1)


def waypoint_direction_from_matrix(matrix_world):
    """Blender world-space facing direction of a waypoint empty: its local
    +Y axis, i.e. column 1 of the world matrix (row-indexable, rows of at
    least 3 values - a mathutils.Matrix or plain nested tuples). Reading
    matrix_world rather than rotation_quaternion makes this independent of
    rotation_mode (Euler or quaternion) and includes parent rotation."""
    return (matrix_world[0][1], matrix_world[1][1], matrix_world[2][1])


def waypoint_rotation_from_blender_direction(x, y, z):
    """3x3 Blender rotation matrix (3 row tuples) whose local +Y axis
    points along (x, y, z) and whose local +Z stays as close to world up
    as possible (no roll). Used by the importer to turn a waypoint's
    `direction` back into a visible orientation. Falls back to facing
    Blender +Y for a zero vector, and keeps local +X as world +X for a
    purely vertical direction (where "no roll" is undefined)."""
    fx, fy, fz = _normalize(x, y, z) or gothic_position_to_blender(
        *_FALLBACK_GOTHIC_DIRECTION, scale=1
    )
    # side (local X) = forward x up, with up = world +Z
    side = _normalize(fy, -fx, 0.0)
    if side is None:
        side = (1.0, 0.0, 0.0)
    sx, sy, sz = side
    # up (local Z) = side x forward
    ux = sy * fz - sz * fy
    uy = sz * fx - sx * fz
    uz = sx * fy - sy * fx
    # columns are (side, forward, up) = local (X, Y, Z)
    return (
        (sx, fx, ux),
        (sy, fy, uy),
        (sz, fz, uz),
    )


def waypoint_yaw_towards(dx, dy):
    """Rotation about Blender Z (radians) that turns a waypoint's local +Y
    (its facing axis) towards a horizontal offset (dx, dy). After a yaw t
    local +Y is (-sin t, cos t), so t = atan2(-dx, dy). Returns None when
    the offset is (near) zero - the target is directly above/below, so
    there is no heading to aim at."""
    if dx * dx + dy * dy < 1e-12:
        return None
    return math.atan2(-dx, dy)
