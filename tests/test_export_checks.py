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
    assert props["range"] == "float:550.0"
    assert float(props["spotConeAngle"].split(":")[1]) == pytest.approx(40)
    assert props["color"] == "color:255 128 0 255"
    assert props["lightStatic"] == "bool:0"


def test_clean_scene_has_no_warnings():
    assert scene_warnings([
        FakeObject("zCVobLevelCompo:LEVEL"),
        FakeObject("zCVob:ROCK"), FakeObject("zCVob:ROCK.001"),       # props may repeat
        FakeObject("oCItem:ITFO_APPLE"), FakeObject("oCItem:ITFO_APPLE.001"),
        FakeObject("zCWaypoint:WP_001"), FakeObject("Level mesh"),
        FakeObject("oCMobContainer:"), FakeObject("oCMobContainer:.001"),  # unnamed mobs
    ]) == []


def test_warnings_for_unknown_types_duplicates_sun_lights_and_missing_level_compo():
    sun = FakeObject("zCVobLight:SUN", type="LIGHT", data=SimpleNamespace(type="SUN"))
    warnings = scene_warnings([
        FakeObject("zCVobSpto:TYPO"),
        FakeObject("zCVobSpot:FP_01"), FakeObject("zCVobSpot:FP_01.001"),
        FakeObject("oCMobDoor:DOOR"), FakeObject("oCMobDoor:DOOR.001"),
        sun,
    ])
    text = "\n".join(warnings)

    assert "unknown vob type: zCVobSpto:TYPO" in text
    assert "zCVobSpot:FP_01" in text and "oCMobDoor:DOOR" in text
    assert "zCVobLight:SUN" in text
    assert "No zCVobLevelCompo" in text
