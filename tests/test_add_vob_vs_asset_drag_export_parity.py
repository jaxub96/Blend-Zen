"""Answers a real question: does the exported uncompiled ZEN differ
between a vob created via the addon's "Add VOB" dialog (an Empty, no
mesh preview loaded - mesh preview is obsolete now that props/items are
placed from the Blender asset library instead) and the same vob placed
by dragging a real asset out of Items_ITMW.blend/Props.blend (a real
Mesh object, transform/name transferred by asset_library.py's
populate_asset_with_mesh - see ASSET_LIBRARY_HANDOFF.md)?
"""
import pytest
from mathutils import Matrix, Quaternion

from conftest import RecordingPrinter, FakeLocation
from modules.zen_gin_export.zen_gin_data_printer import ZenGinDataPrinter
from modules.zen_gin_export.zen_gin_zcvob import ZCVob
from modules.zen_gin_export.zen_gin_zcvob_ocitem import OCItem
from test_zcvob_bounding_box import FakeVobObject, UNIT_CUBE


class FakeAssetDragObject:
    """Stands in for a real asset-library object dropped straight into a
    level scene: the placed object itself IS the mesh (type='MESH', real
    bound_box) - unlike the Add VOB flow's empty. rotation_mode is
    irrelevant to the fake (the exporter only ever reads
    rotation_quaternion directly), but real asset_library.py objects are
    always left in 'QUATERNION' mode (see populate_asset_with_mesh)."""
    type = "MESH"
    children = ()

    def __init__(self, name, location, bound_box=UNIT_CUBE):
        self.name = name
        self.location = location
        self.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
        self.bound_box = bound_box
        self.matrix_world = Matrix((
            (1.0, 0.0, 0.0, location.x),
            (0.0, 1.0, 0.0, location.y),
            (0.0, 0.0, 1.0, location.z),
            (0.0, 0.0, 0.0, 1.0),
        ))


def _exported_properties(vob_class, blender_object):
    printer = RecordingPrinter()
    data_printer = ZenGinDataPrinter(printer)
    vob_class(blender_object, printer, data_printer).print(0)

    properties = {}
    for line in printer.lines:
        stripped = line.strip()
        if "=" not in stripped or stripped.startswith("["):
            continue
        name, value = stripped.split("=", 1)
        properties[name] = value
    return properties


@pytest.mark.parametrize("vob_class,prefix", [(ZCVob, "zCVob"), (OCItem, "oCItem")])
def test_add_vob_and_asset_drag_export_identically_except_bounding_box(vob_class, prefix):
    name = f"{prefix}:SAME_NAME"
    location = FakeLocation(1, 2, 3)

    # Add VOB, as vob_ops.py actually creates it today: an Empty with no
    # mesh preview loaded (Load Mesh Preview only supports zCVob:/oCItem:,
    # and that whole flow is obsolete now that these types come from the
    # asset library instead - see mesh_preview.py's _PREVIEWABLE_PREFIXES).
    add_vob_empty = FakeVobObject(name, location)

    # Same vob, placed by dragging the asset-library equivalent in.
    asset_drag_object = FakeAssetDragObject(name, location)

    add_vob_props = _exported_properties(vob_class, add_vob_empty)
    asset_drag_props = _exported_properties(vob_class, asset_drag_object)

    assert add_vob_props.keys() == asset_drag_props.keys()

    differing = {
        key: (add_vob_props[key], asset_drag_props[key])
        for key in add_vob_props
        if add_vob_props[key] != asset_drag_props[key]
    }

    # bbox3DWS is the one field that's genuinely, correctly different:
    # the Add VOB empty has no geometry to size a box against (degenerate
    # single point), while the asset-drag object carries its own real
    # mesh (a true world-space AABB). Everything else - name, position,
    # rotation, itemInstance/visual, static/collision/shadow flags - must
    # be byte-identical, or the two placement methods would silently
    # produce different in-game behavior for what should be the same vob.
    assert set(differing) == {"bbox3DWS"}, (
        f"Unexpected export differences beyond bbox3DWS: {differing}"
    )

    add_min = tuple(float(v) for v in add_vob_props["bbox3DWS"].split(":", 1)[1].split()[:3])
    add_max = tuple(float(v) for v in add_vob_props["bbox3DWS"].split(":", 1)[1].split()[3:])
    assert add_min == add_max, "Add VOB with no preview should fall back to a degenerate point"

    asset_min = tuple(float(v) for v in asset_drag_props["bbox3DWS"].split(":", 1)[1].split()[:3])
    asset_max = tuple(float(v) for v in asset_drag_props["bbox3DWS"].split(":", 1)[1].split()[3:])
    assert asset_min != asset_max, "Asset-drag object has real geometry and should get a real box"
