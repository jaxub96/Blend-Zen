import pytest
from mathutils import Matrix, Quaternion

from conftest import RecordingPrinter, FakeLocation
from modules.zen_gin_export.zen_gin_data_printer import ZenGinDataPrinter
from modules.zen_gin_export.zen_gin_zcvob import ZCVob


class FakeMeshData:
    vertices = [object()]


class FakeMeshObject:
    """Stands in for the KrxImpExp preview mesh zen_waypoint_tools'
    mesh_preview.py parents under a vob Empty (see mesh_preview.py:
    ZEN_OT_load_vob_mesh)."""
    type = "MESH"
    children = ()

    def __init__(self, bound_box, matrix_world=Matrix.Identity(4)):
        self.bound_box = bound_box
        self.matrix_world = matrix_world
        self.data = FakeMeshData()


class FakeVobObject:
    """Stands in for the Empty object a vob actually is in Blender - no
    geometry of its own, real geometry (if any) lives on mesh children."""
    rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))

    def __init__(self, name, location, children=()):
        self.name = name
        self.location = location
        self.children = children


UNIT_CUBE = [
    (-1, -1, -1), (-1, -1, 1), (-1, 1, 1), (-1, 1, -1),
    (1, -1, -1), (1, -1, 1), (1, 1, 1), (1, 1, -1),
]


def _exported_bbox(vob_object):
    printer = RecordingPrinter()
    data_printer = ZenGinDataPrinter(printer)
    ZCVob(vob_object, printer, data_printer).print(0)
    bbox_line = next(line for line in printer.lines if line.strip().startswith("bbox3DWS"))
    _, value = bbox_line.split(":", 1)
    return tuple(float(v) for v in value.split())


def test_no_mesh_children_falls_back_to_degenerate_point():
    """A vob with no preview mesh loaded (or a genuinely visual-less
    type like a freepoint) has nothing to size a box against - this
    preserves the old single-point behavior rather than crashing."""
    vob = FakeVobObject("zCVob:NoPreview", FakeLocation(1, 2, 3))

    minx, miny, minz, maxx, maxy, maxz = _exported_bbox(vob)

    assert (minx, miny, minz) == (maxx, maxy, maxz)


def test_preview_mesh_produces_a_real_sized_box():
    """Once a preview mesh is loaded (mesh_preview.py), the box should
    span the mesh's actual world-space extent, not a single point."""
    preview = FakeMeshObject(bound_box=UNIT_CUBE)
    vob = FakeVobObject("zCVob:WithPreview", FakeLocation(0, 0, 0), children=(preview,))

    minx, miny, minz, maxx, maxy, maxz = _exported_bbox(vob)

    # Blender (x, y, z) -> Gothic (x, z, -y) at scale 100 (see
    # coordinate_transform.blender_position_to_gothic); a +/-1m cube
    # centered on the origin becomes a +/-100cm box on every axis.
    assert minx == pytest.approx(-100)
    assert maxx == pytest.approx(100)
    assert miny == pytest.approx(-100)
    assert maxy == pytest.approx(100)
    assert minz == pytest.approx(-100)
    assert maxz == pytest.approx(100)


def test_preview_mesh_box_follows_child_world_transform():
    """The preview mesh's own matrix_world (parented under the vob, so
    this already includes the vob's position) determines the box, not
    the vob Empty's location directly - regression guard against
    accidentally reading the vob's own location instead."""
    # scale by 2 on every axis, then shift +5 on X (row-major, applied as
    # matrix_world @ Vector - see mathutils/matrix.py's __matmul__)
    offset = Matrix((
        (2.0, 0.0, 0.0, 5.0),
        (0.0, 2.0, 0.0, 0.0),
        (0.0, 0.0, 2.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
    ))
    preview = FakeMeshObject(bound_box=UNIT_CUBE, matrix_world=offset)
    vob = FakeVobObject("zCVob:Offset", FakeLocation(0, 0, 0), children=(preview,))

    minx, miny, minz, maxx, maxy, maxz = _exported_bbox(vob)

    # local cube corners at x=+-1 scaled by 2 and shifted by +5 -> [3, 7]
    # on Blender X, which maps straight through to Gothic X.
    assert minx == pytest.approx(300)
    assert maxx == pytest.approx(700)
