import pytest

from conftest import FakeObject, exported_properties, world_matrix
from modules.zen_gin_export.zen_gin_zcvob import ZCVob

UNIT_CUBE = [
    (-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1),
    (1, -1, -1), (1, -1, 1), (1, 1, 1), (1, 1, -1),
]


def mesh(matrix_world=None, bound_box=UNIT_CUBE):
    return FakeObject("child mesh", type="MESH", bound_box=bound_box,
                      matrix_world=matrix_world or world_matrix())


def _bbox(vob_object):
    value = exported_properties(ZCVob, vob_object)["bbox3DWS"].split(":", 1)[1]
    return tuple(float(v) for v in value.split())


def test_no_mesh_falls_back_to_a_point_at_the_vob():
    minx, miny, minz, maxx, maxy, maxz = _bbox(FakeObject("zCVob:NoMesh", location=(1, 2, 3)))
    assert (minx, miny, minz) == (maxx, maxy, maxz) == (100, 300, 200)


def test_child_mesh_gives_a_real_box():
    vob = FakeObject("zCVob:WithMesh", children=(mesh(),))
    assert _bbox(vob) == pytest.approx((-100, -100, -100, 100, 100, 100))


def test_box_follows_the_child_world_transform():
    scaled_and_shifted = world_matrix((5, 0, 0), ((2, 0, 0), (0, 2, 0), (0, 0, 2)))
    vob = FakeObject("zCVob:Offset", children=(mesh(scaled_and_shifted),))
    minx, _, _, maxx, _, _ = _bbox(vob)
    assert (minx, maxx) == pytest.approx((300, 700))


def test_object_that_is_itself_a_mesh_uses_its_own_geometry():
    """An asset dragged in from Props.blend is the mesh itself."""
    vob = FakeObject("zCVob:Dragged", location=(1, 0, 0), type="MESH", bound_box=UNIT_CUBE)
    minx, _, _, maxx, _, _ = _bbox(vob)
    assert (minx, maxx) == pytest.approx((0, 200))
