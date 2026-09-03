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
    """Real value from the GROMRUZ test scene (WP_001), confirmed by hand
    against Spacer's own displayed trafoOSToWSPos after the mirror-bug
    fix. If this ever changes unexpectedly, something regressed."""
    bx, by, bz = 2,3, 5
    gx, gy, gz = blender_position_to_gothic(bx, by, bz)

    assert gx == pytest.approx(bx*100)
    assert gy == pytest.approx(bz*100)
    assert gz == pytest.approx(-by*100)


def test_position_is_scale_independent_shape():
    """The axis mapping shouldn't depend on the scale factor."""
    x, y, z = 1.0, 2.0, 3.0
    gx1, gy1, gz1 = blender_position_to_gothic(x, y, z, scale=1)
    gx100, gy100, gz100 = blender_position_to_gothic(x, y, z, scale=100)

    assert gx100 == pytest.approx(gx1 * 100)
    assert gy100 == pytest.approx(gy1 * 100)
    assert gz100 == pytest.approx(gz1 * 100)


def test_position_transform_is_a_proper_rotation_not_a_mirror():
    """The core regression guard: this exact bug (determinant -1, a
    mirror reflection instead of a rotation) shipped unnoticed and was
    only caught by a real Spacer test. This test makes sure it can never
    silently happen again."""
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

    assert is_proper_rotation(matrix), (
        "blender_position_to_gothic is a mirror reflection (determinant -1), "
        "not a proper rotation - this is exactly the bug that caused the "
        "whole scene to appear mirrored in Spacer."
    )


def test_quaternion_identity_stays_identity():
    gw, gx, gy, gz = blender_quaternion_to_gothic(1.0, 0.0, 0.0, 0.0)
    assert (gw, gx, gy, gz) == (1.0, 0.0, 0.0, 0.0)


@pytest.mark.parametrize("w", [0.0, 0.5, -0.5, 1.0, 0.70710678])
def test_quaternion_scalar_part_never_changes(w):
    """w (the rotation-angle component) is basis-independent for a
    proper coordinate change - mixing it into a spatial slot was exactly
    the second bug found and fixed alongside the position mirror bug."""
    gw, _, _, _ = blender_quaternion_to_gothic(w, 0.1, 0.2, 0.3)
    assert gw == w


def test_quaternion_vector_part_is_negated_position_axis_mapping():
    """The rotation transform's vector part uses the same axis
    permutation as the position transform, but negated (inverting the
    rotation angle while keeping the same rotation axis) - see
    blender_quaternion_to_gothic's docstring for why. This ties the two
    functions together as a single consistency check, so they can't
    silently drift apart from each other again."""
    x, y, z = 0.3, -0.7, 1.1
    pos_gx, pos_gy, pos_gz = blender_position_to_gothic(x, y, z, scale=1)
    _, quat_gx, quat_gy, quat_gz = blender_quaternion_to_gothic(0.0, x, y, z)

    assert quat_gx == pytest.approx(-pos_gx)
    assert quat_gy == pytest.approx(-pos_gy)
    assert quat_gz == pytest.approx(-pos_gz)


def test_quaternion_bookshelf_regression_value():
    """Real value from a Spacer test: a prop rotated +90 degrees about
    Blender's vertical (Z) axis was reported as facing the opposite
    direction in-game. This asserts the corrected, negated output for
    that exact input, so a future accidental revert to the old sign is
    caught immediately instead of requiring another real Spacer test to
    notice."""
    # 90 degrees about Blender Z: w=cos(45), z=sin(45), x=y=0
    w, x, y, z = 0.70710678, 0.0, 0.0, 0.70710678
    gw, gx, gy, gz = blender_quaternion_to_gothic(w, x, y, z)

    assert gw == pytest.approx(0.70710678)
    assert gx == pytest.approx(0.0)
    assert gy == pytest.approx(-0.70710678)
    assert gz == pytest.approx(0.0)
