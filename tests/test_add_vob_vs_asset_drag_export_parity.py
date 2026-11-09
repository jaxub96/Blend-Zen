"""A vob added as an Empty (Add VOB) and the same vob dragged in as a
real mesh from an asset library must export identically except for
bbox3DWS (an Empty has no geometry to size against)."""

import pytest

from conftest import FakeObject, exported_properties
from modules.zen_gin_export.zen_gin_zcvob import ZCVob, OCItem
from test_zcvob_bounding_box import UNIT_CUBE


@pytest.mark.parametrize("vob_class,prefix", [(ZCVob, "zCVob"), (OCItem, "oCItem")])
def test_add_vob_and_asset_drag_export_identically_except_bounding_box(vob_class, prefix):
    name = f"{prefix}:SAME_NAME"
    empty = exported_properties(vob_class, FakeObject(name, location=(1, 2, 3)))
    dragged = exported_properties(
        vob_class, FakeObject(name, location=(1, 2, 3), type="MESH", bound_box=UNIT_CUBE))

    assert empty.keys() == dragged.keys()
    assert {k for k in empty if empty[k] != dragged[k]} == {"bbox3DWS"}
