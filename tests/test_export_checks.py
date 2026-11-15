import math
from types import SimpleNamespace

import pytest

from conftest import FakeObject, exported_properties
from modules.zen_gin_export import scene_warnings
from modules.zen_gin_export.zen_gin_zcvob import ZCVob, vob_name_from_object_name
from modules.zen_gin_export.zen_gin_zcvob_light import ZCVobLight


@pytest.mark.parametrize("name,expected", [
    ("zCVob:ROCK_01", "ROCK_01"),
    ("zCVob:ROCK_01.003", "ROCK_01"),          # Blender duplicate suffix
    ("zCVobSpot:FP.ROAM.01", "FP.ROAM.01"),    # other dots are kept
    ("zCVobSpot:FP:EXTRA", "FP:EXTRA"),        # only the first colon splits
])
def test_vob_name_strips_only_the_type_prefix_and_duplicate_suffix(name, expected):
    assert vob_name_from_object_name(name) == expected


def test_vob_name_is_written_and_prop_visual_derived_from_it():
    props = exported_properties(ZCVob, FakeObject("zCVob:NW_ROCK_01.002"))
    assert props["vobName"] == "string:NW_ROCK_01"
    assert props["visual"] == "string:NW_ROCK_01.3DS"


def test_light_values_come_from_the_blender_light():
    data = SimpleNamespace(type="SPOT", use_custom_distance=True, cutoff_distance=5.5,
                           spot_size=math.radians(40), color=(1.0, 0.5, 0.0))
    props = exported_properties(
        ZCVobLight, FakeObject("zCVobLight:L", type="LIGHT", data=data, light_static=False))

    assert props["lightType"] == "enum:1"
    assert props["range"] == "float:550"
    assert float(props["spotConeAngle"].split(":")[1]) == pytest.approx(40)
    assert props["color"] == "color:255 128 0 255"
    assert props["lightStatic"] == "bool:0"
    assert props["bbox3DWS"] == "rawFloat:-550.0 -550.0 -550.0 550.0 550.0 550.0"


def test_static_lights_omit_the_flicker_fields_dynamic_ones_write_them():
    """As the engine does: turnedOn...canMove only exist for lightStatic=0."""
    static = exported_properties(ZCVobLight, FakeObject(
        "zCVobLight:S", light_preset="NW_STANDART_DARKBLUE", light_quality="MEDIUM"))
    assert static["lightPresetInUse"] == "string:NW_STANDART_DARKBLUE"
    assert static["lightQuality"] == "enum:1"
    assert "turnedOn" not in static and "colorAniList" not in static

    dynamic = exported_properties(ZCVobLight, FakeObject(
        "zCVobLight:D", light_static=False, color_ani_list="(255 80 0) (200 50 0)",
        color_ani_fps=2, range_ani_scale="1.0 0.9", range_ani_fps=4))
    assert dynamic["colorAniList"] == "string:(255 80 0) (200 50 0)"
    assert dynamic["colorAniFPS"] == "float:2" and dynamic["rangeAniFPS"] == "float:4"
    assert list(dynamic)[-8:] == ["turnedOn", "rangeAniScale", "rangeAniFPS", "rangeAniSmooth",
                                  "colorAniList", "colorAniFPS", "colorAniSmooth", "canMove"]


def test_clean_scene_has_no_warnings():
    assert scene_warnings([
        FakeObject("zCVobLevelCompo:LEVEL"),
        FakeObject("zCVob:ROCK"), FakeObject("zCVob:ROCK.001"),       # props may repeat
        FakeObject("oCItem:ITFO_APPLE"), FakeObject("oCItem:ITFO_APPLE.001"),
        FakeObject("zCWaypoint:WP_001"), FakeObject("Level mesh"),
        FakeObject("oCMobContainer:", visual_name="CHESTBIG_NW_NORMAL_LOCKED"),  # unnamed mobs
        FakeObject("oCMobContainer:.001", visual_name="CHESTBIG_NW_NORMAL_LOCKED"),
        FakeObject("oCMobDoor:LOCKED_PICKABLE", visual_name="DOOR_NW_POOR_01",
                   locked=True, picklock_str="RLRRLL"),
        FakeObject("oCMobBed:BED", visual_name="BEDHIGH_NW_NORMAL_01.ASC"),
    ]) == []


def test_warnings_for_unknown_types_duplicates_sun_lights_and_missing_level_compo():
    sun = FakeObject("zCVobLight:SUN", type="LIGHT", data=SimpleNamespace(type="SUN"))
    warnings = scene_warnings([
        FakeObject("zCVobSpto:TYPO"),
        FakeObject("zCVobSpot:FP_01"), FakeObject("zCVobSpot:FP_01.001"),
        FakeObject("oCMobDoor:DOOR", visual_name="DOOR_NW_NORMAL_01"),
        FakeObject("oCMobDoor:DOOR.001", visual_name="DOOR_NW_NORMAL_01"),
        sun,
    ])
    text = "\n".join(warnings)

    assert "unknown vob type: zCVobSpto:TYPO" in text
    assert "zCVobSpot:FP_01" in text and "oCMobDoor:DOOR" in text
    assert "zCVobLight:SUN" in text
    assert "No zCVobLevelCompo" in text


def test_warnings_for_mobs_that_load_or_work_wrong_in_game():
    """Each of these was hit in a real Spacer/in-game test."""
    text = "\n".join(scene_warnings([
        FakeObject("zCVobLevelCompo:L"),
        FakeObject("oCMobDoor:NO_MODEL"),                                   # Spacer crash
        FakeObject("oCMobContainer:CHEST", visual_name="X", locked=True),    # "can't be opened"
        FakeObject("oCMobBed:BED", visual_name="X", on_state_func=""),        # no sleep dialog
    ]))
    assert "No Visual, model" in text and "oCMobDoor:NO_MODEL" in text
    assert "can never be opened: oCMobContainer:CHEST" in text
    assert "no sleep dialog: oCMobBed:BED" in text


def test_warnings_for_triggers_music_zones_and_movers():
    mover = FakeObject("zCMover:GATE")
    FakeObject("MoverKey1", parent=mover, zen_mover_key=0)
    text = "\n".join(scene_warnings([
        FakeObject("zCVobLevelCompo:L"),
        FakeObject("oCMobSwitch:LEVER", visual_name="LEVER_1_OC", trigger_target="GATE"),   # fine
        FakeObject("oCTriggerScript:T", script_func="F"),
        FakeObject("zCTriggerList:LIST", list_target_0="GATE", list_target_1="NOWHERE"),
        FakeObject("zCTrigger:NULLED", trigger_target="NULL"),                          # vanilla "none"
        FakeObject("oCZoneMusic:NOTHEME"), FakeObject("oCZoneMusic:CAMP_XAR"),
        mover,
    ]))
    assert "zCTriggerList:LIST -> NOWHERE" in text
    assert "LEVER -> GATE" not in text and "NULLED" not in text
    assert "oCZoneMusic:NOTHEME" in text and "oCZoneMusic:CAMP_XAR" not in text
    assert "single keyframe never moves: zCMover:GATE" in text
