from conftest import FakeObject, RecordingPrinter
from modules.zen_gin_export.zen_gin_data_printer import ZenGinDataPrinter
from modules.zen_gin_export.zen_gin_ocvobtree import OCVobTree


def _printed_vob_names(blender_objects):
    printer = RecordingPrinter()
    OCVobTree(blender_objects, ZenGinDataPrinter(printer)).print(0)
    return [line.strip().split("vobName=string:", 1)[1]
            for line in printer.lines if line.strip().startswith("vobName=")]


def test_vob_tree_sorts_level_compo_first_and_groups_items_spots_sounds():
    names = _printed_vob_names([
        FakeObject("zCVobSound:SOUND01"),
        FakeObject("oCItem:ITEM01"),
        FakeObject("oCMobDoor:DOOR01"),
        FakeObject("zCVobLevelCompo:LEVEL01"),
        FakeObject("zCVobSpot:SPOT01"),
        FakeObject("zCVob:PLAIN01"),
        FakeObject("zCVobUnknown:IGNORED"),
        FakeObject("NO_PREFIX"),
    ])

    # Unlisted types share the generic slot and keep input order (stable sort).
    assert names == ["LEVEL-VOB", "DOOR01", "PLAIN01", "ITEM01", "SPOT01", "SOUND01"]
