from conftest import RecordingPrinter
from modules.zen_gin_export.zen_gin_data_printer import ZenGinDataPrinter
from modules.zen_gin_export.zen_gin_ocvobtree import OCVobTree
from test_ocmob_export import FakeBlenderObject


def _printed_vob_names(blender_objects):
    printer = RecordingPrinter()
    data_printer = ZenGinDataPrinter(printer)
    OCVobTree(blender_objects, printer, data_printer).print(0)

    names = []
    for line in printer.lines:
        stripped = line.strip()
        if stripped.startswith("vobName=string:"):
            names.append(stripped.split("vobName=string:", 1)[1])
    return names


def test_vob_tree_sorts_by_type_specific_types_before_generic_zcvob():
    # Deliberately out of order and interleaved with a type
    # (oCMobDoor) that has no dedicated entry in the ordering at all.
    objects = [
        FakeBlenderObject("zCVobSound:SOUND01"),
        FakeBlenderObject("oCItem:ITEM01"),
        FakeBlenderObject("oCMobDoor:DOOR01"),
        FakeBlenderObject("zCVobLevelCompo:LEVEL01"),
        FakeBlenderObject("zCVobSpot:SPOT01"),
        FakeBlenderObject("zCVob:PLAIN01"),
    ]

    names = _printed_vob_names(objects)

    # LevelCompo always first; OCItem/ZCVobSpot/ZCVobSound are reordered
    # to their own dedicated slots instead of collapsing into the
    # generic zCVob bucket. Plain zCVob and unlisted types (oCMobDoor)
    # share the generic bucket and keep their relative input order
    # (DOOR01 came before PLAIN01 in the input - the sort is stable).
    assert names == [
        "LEVEL-VOB",  # zCVobLevelCompo -> 0 (prints a fixed vobName, not its object name)
        "DOOR01",   # oCMobDoor, unlisted -> falls into generic bucket -> 1
        "PLAIN01",  # zCVob (generic) -> 1
        "ITEM01",   # oCItem -> 2
        "SPOT01",   # zCVobSpot -> 3
        "SOUND01",  # zCVobSound -> 4
    ]
