import pytest

from conftest import FakeObject, exported_properties, print_vob
from modules.zen_gin_export.archive_parser import parse_archive
from modules.zen_gin_export.vob_fields import FIELDS_BY_TYPE, custom_properties_from_block
from modules.zen_gin_export.zen_gin_ocvobtree import VOB_CLASSES
from modules.zen_gin_export.zen_gin_zcvob_ocmob import (
    OCMobInter, OCMobContainer, OCMobDoor, OCMobBed, OCMobLadder, OCMobFire,
)
from modules.zen_gin_export.zen_gin_zcvob_sound import ZCVobSound


def test_ocmob_fields_default_when_no_custom_properties_set():
    props = exported_properties(OCMobInter, FakeObject("oCMobInter:UNCONFIGURED"))

    assert props["focusName"] == "string:"
    assert props["hitpoints"] == "int:0"
    assert props["soundMaterial"] == "enum:0"  # WOOD
    assert props["isDestroyed"] == "bool:0"
    assert props["stateNum"] == "int:1"  # what vanilla mobs use (108 of 109)
    # No visual_name -> falls back to the vob's own name.
    assert props["visual"] == "string:UNCONFIGURED.MDS"


def test_ocmob_inter_fields_read_custom_properties():
    props = exported_properties(OCMobInter, FakeObject(
        "oCMobSwitch:LEVER_GATE_01", trigger_target="GATE_MOVER_01",
        condition_func="ZS_GateCondition", rewind=True, sound_material="metal",
    ))

    assert props["triggerTarget"] == "string:GATE_MOVER_01"
    assert props["conditionFunc"] == "string:ZS_GateCondition"
    assert props["rewind"] == "bool:1"
    assert props["soundMaterial"] == "enum:2"


def test_bad_custom_value_falls_back_instead_of_failing_the_export():
    props = exported_properties(OCMobInter, FakeObject("oCMobInter:X", hitpoints="lots"))
    assert props["hitpoints"] == "int:0"


def test_container_has_lock_fields_and_contains_door_has_no_contains():
    chest = exported_properties(OCMobContainer, FakeObject(
        "oCMobContainer:CHEST_CITY_01", visual_name="CHESTBIG_OCCRATELARGE",
        locked=True, picklock_str="RRLRL", contains="ITFO_APPLE:3,ITMW_1H_SHORTSWORD1",
    ))
    door = exported_properties(OCMobDoor, FakeObject("oCMobDoor:DOOR_01", locked=True))

    assert chest["visual"] == "string:CHESTBIG_OCCRATELARGE.MDS"
    assert chest["locked"] == "bool:1"
    assert chest["pickLockStr"] == "string:RRLRL"
    assert chest["contains"] == "string:ITFO_APPLE:3,ITMW_1H_SHORTSWORD1"
    assert door["locked"] == "bool:1"
    assert "contains" not in door


def test_fire_adds_fire_slot_and_vobtree():
    props = exported_properties(OCMobFire, FakeObject(
        "oCMobFire:CAMPFIRE_01", fire_slot="BIP01 FIRE", fire_vobtree_name="FIRETREE_MEDIUM.ZEN"))
    assert props["fireSlot"] == "string:BIP01 FIRE"
    assert props["fireVobtreeName"] == "string:FIRETREE_MEDIUM.ZEN"


def test_class_headers_match_real_spacer_worlds():
    """From blender_work_dir/G2ISLAND_WEB.ZEN: oCMobLockable is not in the
    persisted chain, the class versions differ per type, and the zCModel
    visual block has version 0."""
    assert print_vob(OCMobContainer, FakeObject("oCMobContainer:C"), 5)[0] == \
        "[% oCMobContainer:oCMobInter:oCMOB:zCVob 64513 5]"
    assert print_vob(OCMobDoor, FakeObject("oCMobDoor:D"))[0] == \
        "[% oCMobDoor:oCMobInter:oCMOB:zCVob 64513 0]"
    assert print_vob(OCMobBed, FakeObject("oCMobBed:B"))[0] == \
        "[% oCMobBed:oCMobInter:oCMOB:zCVob 61440 0]"
    assert print_vob(OCMobLadder, FakeObject("oCMobLadder:L"))[0] == \
        "[% oCMobLadder:oCMobInter:oCMOB:zCVob 35585 0]"
    assert "\t[visual zCModel 0 6]" in print_vob(OCMobInter, FakeObject("oCMobInter:I"), 5)


def test_sound_writes_sound_fields_in_spacer_order():
    lines = print_vob(ZCVobSound, FakeObject("zCVobSound:OW_COASTLIGHT", sound_radius=2500))
    assert lines[0] == "[% zCVobSound:zCVob 12289 0]"
    names = [l.strip().split("=")[0] for l in lines if l.strip().startswith("snd")]
    assert names == [
        "sndVolume", "sndMode", "sndRandDelay", "sndRandDelayVar", "sndStartOn",
        "sndAmbient3D", "sndObstruction", "sndConeAngle", "sndVolType", "sndRadius", "sndName",
    ]
    props = exported_properties(ZCVobSound, FakeObject("zCVobSound:OW_COASTLIGHT", sound_radius=2500))
    assert props["sndRadius"] == "float:2500.0"
    assert props["sndName"] == "string:OW_COASTLIGHT"


@pytest.mark.parametrize("vob_type", sorted(FIELDS_BY_TYPE))
def test_custom_properties_round_trip_through_export_and_parse(vob_type):
    """What the importer restores is what was exported."""
    custom = {}
    for _, archive_type, key, default in FIELDS_BY_TYPE[vob_type]:
        if key is None:
            continue
        custom[key] = {
            "int": 7, "float": 12.5, "bool": not default, "string": f"{key}_VALUE",
        }.get(archive_type, default)
    custom.update({k: v for k, v in (("sound_material", "STONE"), ("sound_mode", "RANDOM")) if k in custom})

    lines = print_vob(VOB_CLASSES[vob_type], FakeObject(f"{vob_type}:X", **custom))
    block = parse_archive("END\nEND\n" + "\n".join(lines))[0]

    assert custom_properties_from_block(vob_type, block.properties) == custom
