import math
import sys
from pathlib import Path

import pytest

# Keep the tests importable when the project is opened/run outside an
# installed environment (for example, by the editor's test analyzer).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from modules.zen_gin_export.coordinate_transform import (
    blender_position_to_gothic,
    blender_quaternion_to_gothic,
    is_proper_rotation,
)


def test_position_known_regression_value():
    """Locks in the axis mapping confirmed against real Spacer geometry
    by the "Compass Cross" test (documentation/transform_investigation.md)."""
    bx, by, bz = 2, 3, 5
    gx, gy, gz = blender_position_to_gothic(bx, by, bz)

    assert gx == pytest.approx(bx*100)
    assert gy == pytest.approx(bz*100)
    assert gz == pytest.approx(by*100)


def test_position_is_scale_independent_shape():
    """The axis mapping shouldn't depend on the scale factor."""
    x, y, z = 1.0, 2.0, 3.0
    gx1, gy1, gz1 = blender_position_to_gothic(x, y, z, scale=1)
    gx100, gy100, gz100 = blender_position_to_gothic(x, y, z, scale=100)

    assert gx100 == pytest.approx(gx1 * 100)
    assert gy100 == pytest.approx(gy1 * 100)
    assert gz100 == pytest.approx(gz1 * 100)


def test_position_transform_matches_confirmed_matrix():
    """Asserts the exact matrix rather than checking determinant sign -
    both the old bug and the confirmed-correct formula happen to be
    determinant -1, so the sign alone doesn't distinguish them."""
    def transform(v):
        return blender_position_to_gothic(*v, scale=1)

    col_x = transform((1, 0, 0))
    col_y = transform((0, 1, 0))
    col_z = transform((0, 0, 1))
    matrix = (
        (col_x[0], col_y[0], col_z[0]),
        (col_x[1], col_y[1], col_z[1]),
        (col_x[2], col_y[2], col_z[2]),
    )

    assert matrix == ((1, 0, 0), (0, 0, 1), (0, 1, 0))


def test_quaternion_identity_stays_identity():
    gw, gx, gy, gz = blender_quaternion_to_gothic(1.0, 0.0, 0.0, 0.0)
    assert (gw, gx, gy, gz) == (1.0, 0.0, 0.0, 0.0)


@pytest.mark.parametrize("w", [0.0, 0.5, -0.5, 1.0, 0.70710678])
def test_quaternion_scalar_part_never_changes(w):
    """w stays fixed regardless of the coordinate change's determinant -
    see blender_quaternion_to_gothic's docstring for why."""
    gw, _, _, _ = blender_quaternion_to_gothic(w, 0.1, 0.2, 0.3)
    assert gw == w


def test_quaternion_vector_part_is_negated_position_axis_mapping():
    """Ties the two functions together: the rotation vector part is the
    negated position mapping. Catches them silently drifting apart."""
    x, y, z = 0.3, -0.7, 1.1
    pos_gx, pos_gy, pos_gz = blender_position_to_gothic(x, y, z, scale=1)
    _, quat_gx, quat_gy, quat_gz = blender_quaternion_to_gothic(0.0, x, y, z)

    assert quat_gx == pytest.approx(-pos_gx)
    assert quat_gy == pytest.approx(-pos_gy)
    assert quat_gz == pytest.approx(-pos_gz)


def test_quaternion_bookshelf_regression_value():
    """Real Spacer regression: a +90 degree Blender-Z rotation once came
    out facing backwards in-game under the wrong sign here."""
    # 90 degrees about Blender Z: w=cos(45), z=sin(45), x=y=0
    w, x, y, z = 0.70710678, 0.0, 0.0, 0.70710678
    gw, gx, gy, gz = blender_quaternion_to_gothic(w, x, y, z)

    assert gw == pytest.approx(0.70710678)
    assert gx == pytest.approx(0.0)
    assert gy == pytest.approx(-0.70710678)
    assert gz == pytest.approx(0.0)


def _quaternion_to_matrix(w, x, y, z):
    """Plain-math quaternion -> 3x3 rotation matrix, kept local to this
    test file (coordinate_transform.py deliberately has zero
    Blender/mathutils dependency, so it doesn't expose this itself)."""
    return (
        (1 - 2*(y*y+z*z), 2*(x*y-w*z), 2*(x*z+w*y)),
        (2*(x*y+w*z), 1 - 2*(x*x+z*z), 2*(y*z-w*x)),
        (2*(x*z-w*y), 2*(y*z+w*x), 1 - 2*(x*x+y*y)),
    )


@pytest.mark.parametrize("w,x,y,z", [
    (1.0, 0.0, 0.0, 0.0),
    (math.cos(math.radians(45)), 0.0, 0.0, math.sin(math.radians(45))),
    (0.5, 0.5, 0.5, 0.5),
    (0.1, 0.6, -0.2, 0.7),
])
def test_quaternion_output_is_always_a_proper_rotation(w, x, y, z):
    """A rotation stays a proper rotation even though the coordinate
    change itself is improper (determinant -1) - see is_proper_rotation's
    docstring."""
    norm = math.sqrt(w*w + x*x + y*y + z*z)
    w, x, y, z = w / norm, x / norm, y / norm, z / norm

    gw, gx, gy, gz = blender_quaternion_to_gothic(w, x, y, z)
    matrix = _quaternion_to_matrix(gw, gx, gy, gz)
    assert is_proper_rotation(matrix)
