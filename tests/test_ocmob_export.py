import pytest

from conftest import FakeObject, exported_properties, print_vob
from modules.zen_gin_export.archive_parser import parse_archive
from modules.zen_gin_export.vob_fields import (
    BASE_FIELDS, ENUMS, custom_properties_from_block, default_for, keyed_fields,
)
from modules.zen_gin_export.zen_gin_ocvobtree import VOB_CLASSES
from modules.zen_gin_export.zen_gin_zcvob_ocmob import (
    OCMobInter, OCMobContainer, OCMobDoor, OCMobBed, OCMobLadder, OCMobFire,
)
from modules.zen_gin_export.zen_gin_zcvob_sound import ZCVobSound


def test_ocmob_fields_default_when_no_custom_properties_set():
    props = exported_properties(OCMobInter, FakeObject("oCMobInter:UNCONFIGURED"))

    assert props["focusName"] == "string:"
    assert props["hitpoints"] == "int:10"  # vanilla value for every mob
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
    assert props["hitpoints"] == "int:10"


def test_type_defaults_make_a_bare_bed_sleepable():
    """The engine calls <onStateFunc>_S1; SLEEPABIT_S1 opens the sleep
    dialog. Without it a bed is usable but nothing happens (seen in-game)."""
    bed = exported_properties(OCMobBed, FakeObject("oCMobBed:B"))
    chest = exported_properties(OCMobContainer, FakeObject("oCMobContainer:C"))
    assert bed["onStateFunc"] == "string:SLEEPABIT"
    assert bed["focusName"] == "string:MOBNAME_BED"
    assert chest["focusName"] == "string:MOBNAME_CHEST"
    assert chest["onStateFunc"] == "string:"
    # An explicit value still wins.
    assert exported_properties(OCMobBed, FakeObject("oCMobBed:B", on_state_func=""))["onStateFunc"] == "string:"


def test_container_has_lock_fields_and_contains_door_has_no_contains():
    chest = exported_properties(OCMobContainer, FakeObject(
        "oCMobContainer:CHEST_CITY_01", visual_name="CHESTBIG_NW_NORMAL_LOCKED",
        locked=True, picklock_str="RRLRL", contains="ITFO_APPLE:3,ITMW_1H_SHORTSWORD1",
    ))
    door = exported_properties(OCMobDoor, FakeObject("oCMobDoor:DOOR_01", locked=True))

    assert chest["visual"] == "string:CHESTBIG_NW_NORMAL_LOCKED.MDS"
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
    """From a Spacer-saved world: oCMobLockable is not in the
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
    assert props["sndRadius"] == "float:2500"
    assert props["sndName"] == "string:OW_COASTLIGHT"       # blank sound_name = the vob's name
    named = exported_properties(ZCVobSound, FakeObject("zCVobSound:TORCH_A", sound_name="TORCH_BURN"))
    assert (named["vobName"], named["sndName"]) == ("string:TORCH_A", "string:TORCH_BURN")
    # The bbox is the audible sphere's box, as Spacer writes it.
    assert props["bbox3DWS"] == "rawFloat:-2500.0 -2500.0 -2500.0 2500.0 2500.0 2500.0"


_SAMPLE_VALUES = {"int": 7, "float": 12.5, "string": "VALUE", "color": [10, 20, 30, 255],
                  "vec3": [1.0, 2.0, 3.0], "rawFloat": [4.0, 5.0]}


@pytest.mark.parametrize("vob_type", sorted(VOB_CLASSES))
def test_custom_properties_round_trip_through_export_and_parse(vob_type):
    """What the importer restores is what was exported, for every setting
    of every vob type (base flags, type fields, trigger bits, list slots)."""
    custom = {}
    for archive_name, archive_type, key, default in BASE_FIELDS + keyed_fields(vob_type):
        if key in ("visual_name", "light_static") or key.startswith("decal_"):
            continue
        if archive_type == "enum":
            custom[key] = ENUMS[archive_name][-1]
        elif archive_type == "bool":
            custom[key] = not default_for(vob_type, key)
        else:
            custom[key] = _SAMPLE_VALUES[archive_type]
    if vob_type == "zCVobLight":
        custom["light_static"] = False          # dynamic: the flicker fields are written
    if vob_type == "zCMover":
        del custom["move_speed"], custom["pos_lerp_type"], custom["speed_type"]  # need keyframes

    lines = print_vob(VOB_CLASSES[vob_type], FakeObject(f"{vob_type}:X", **custom))
    block = parse_archive("END\nEND\n" + "\n".join(lines))[0]

    assert custom_properties_from_block(vob_type, block.properties) == custom


def test_only_changed_base_flags_are_imported():
    """A vanilla vob at its type's defaults comes in without flag clutter."""
    lines = print_vob(VOB_CLASSES["zCVob"], FakeObject("zCVob:ROCK", cd_dyn=False))
    block = parse_archive("END\nEND\n" + "\n".join(lines))[0]
    assert custom_properties_from_block("zCVob", block.properties) == {"cd_dyn": False}


def test_spacer_minus_one_is_a_true_bool():
    assert custom_properties_from_block("oCMobContainer", {"locked": "-1"}) == {"locked": True}


def test_mob_visual_keeps_an_explicit_extension():
    """Vanilla mobs also use .ASC models and static .3DS meshes
    (a Spacer-saved world: BEDHIGH_NW_NORMAL_01.ASC); a .3DS gets a
    zCProgMeshProto visual block."""
    asc = exported_properties(OCMobBed, FakeObject("oCMobBed:B", visual_name="BEDHIGH_NW_NORMAL_01.ASC"))
    assert asc["visual"] == "string:BEDHIGH_NW_NORMAL_01.ASC"
    lines = print_vob(OCMobInter, FakeObject("oCMobInter:I", visual_name="LAB_TABLE.3DS"), 5)
    assert "\t[visual zCProgMeshProto 53505 6]" in lines
