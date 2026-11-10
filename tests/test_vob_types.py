"""The vob types added with the reference-world survey: layouts as in the
vanilla ASCII worlds (NewWorld_Part_Xardas_01 and the other part-worlds)."""

import pytest

from conftest import FakeObject, RecordingPrinter, exported_properties, print_vob, world_matrix
from modules.zen_gin_export.archive_parser import parse_archive
from modules.zen_gin_export.coordinate_transform import (
    decode_mover_keyframes, decode_rotation_matrix_hex, encode_mover_keyframes,
)
from modules.zen_gin_export.vob_fields import custom_properties_from_block
from modules.zen_gin_export.zen_gin_data_printer import ZenGinDataPrinter
from modules.zen_gin_export.zen_gin_ocvobtree import OCVobTree, VOB_CLASSES
from modules.zen_gin_export.zen_gin_waynet import orient_ways


def _props(vob_type, name="X", **kwargs):
    return exported_properties(VOB_CLASSES[vob_type], FakeObject(f"{vob_type}:{name}", **kwargs))


def _header(vob_type):
    return print_vob(VOB_CLASSES[vob_type], FakeObject(f"{vob_type}:X"))[0]


def test_class_headers_match_the_vanilla_worlds():
    assert _header("zCVobSoundDaytime") == "[% zCVobSoundDaytime:zCVobSound:zCVob 12289 0]"
    assert _header("oCZoneMusic") == "[% oCZoneMusic:zCVob 0 0]"
    assert _header("oCZoneMusicDefault") == "[% oCZoneMusicDefault:oCZoneMusic:zCVob 0 0]"
    assert _header("zCZoneZFog") == "[% zCZoneZFog:zCVob 5505 0]"
    assert _header("zCZoneVobFarPlaneDefault") == \
        "[% zCZoneVobFarPlaneDefault:zCZoneVobFarPlane:zCVob 52224 0]"
    assert _header("oCMOB") == "[% oCMOB:zCVob 47105 0]"
    assert _header("oCMobFire") == "[% oCMobFire:oCMobInter:oCMOB:zCVob 18433 0]"
    assert _header("zCTrigger") == "[% zCTrigger:zCVob 47105 0]"
    assert _header("oCTriggerScript") == "[% oCTriggerScript:zCTrigger:zCVob 24577 0]"
    assert _header("oCTriggerChangeLevel") == "[% oCTriggerChangeLevel:zCTrigger:zCVob 24577 0]"
    assert _header("zCTriggerList") == "[% zCTriggerList:zCTrigger:zCVob 5505 0]"
    assert _header("zCMover") == "[% zCMover:zCTrigger:zCVob 39936 0]"
    assert _header("oCTouchDamage") == "[% oCTouchDamage:zCTouchDamage:zCVob 36865 0]"


def test_base_flags_are_per_instance_with_per_type_defaults():
    prop = _props("zCVob", "ROCK")
    assert (prop["cdStatic"], prop["cdDyn"], prop["staticVob"]) == ("bool:1", "bool:1", "bool:1")
    plant = _props("zCVob", "BUSH", cd_dyn=False, cd_static=False, ani_mode="WIND",
                   ani_strength=0.01, far_clip_scale=1.4, zbias=1)
    assert (plant["cdStatic"], plant["cdDyn"]) == ("bool:0", "bool:0")
    assert (plant["visualAniMode"], plant["visualAniModeStrength"]) == ("enum:1", "float:0.01")
    assert (plant["vobFarClipZScale"], plant["zbias"]) == ("float:1.4", "int:1")
    # Freepoints carry zbias 1 in every vanilla world; triggers need cdDyn to be touched.
    assert _props("zCVobSpot")["zbias"] == "int:1"
    assert _props("oCTriggerScript")["cdDyn"] == "bool:1"
    assert _props("oCItem")["showVisual"] == "bool:0"


def test_decal_writes_its_settings_inside_the_visual_block():
    lines = print_vob(VOB_CLASSES["zCVob"], FakeObject(
        "zCVob:FLARE", visual_name="ZFLARE6.TGA", cam_align="YAW", decal_dim=[40.0, 40.0],
        decal_alpha_weight=200), 3)
    text = "\n".join(line.lstrip() for line in lines)
    assert "visual=string:ZFLARE6.TGA" in text and "visualCamAlign=enum:1" in text
    assert ("[visual zCDecal 53505 4]\nname=string:ZFLARE6.TGA\ndecalDim=rawFloat:40 40 \n"
            "decalOffset=rawFloat:0 0 \ndecal2Sided=bool:1\ndecalAlphaFunc=enum:3\n"
            "decalTexAniFPS=float:0\ndecalAlphaWeight=int:200\nignoreDayLight=bool:0\n[]") in text

    block = parse_archive("END\nEND\n" + "\n".join(lines))[0]
    restored = custom_properties_from_block("zCVob", block.properties, block.children[0].properties)
    assert restored["decal_dim"] == [40.0, 40.0] and restored["decal_alpha_weight"] == 200


def test_visual_block_follows_the_extension():
    def visual_line(vob_type, **kwargs):
        lines = print_vob(VOB_CLASSES[vob_type], FakeObject(f"{vob_type}:N", **kwargs), 7)
        return next(line.strip() for line in lines if line.strip().startswith("[visual"))

    assert visual_line("zCVob", visual_name="FIRE.PFX") == "[visual zCParticleFX 0 8]"
    assert visual_line("zCVob", visual_name="FIREPLACE_GROUND2.ASC") == "[visual zCModel 0 8]"
    assert visual_line("zCVob") == "[visual zCProgMeshProto 53505 8]"       # N.3DS
    assert visual_line("zCVobAnimate", visual_name="NW_MORPH_SKATE_01") == "[visual zCMorphMesh 0 8]"
    assert visual_line("oCMOB", visual_name="NW_MISC_SIGN_01") == "[visual zCProgMeshProto 53505 8]"
    assert visual_line("zCMover") == "[visual % 0 0]"                       # no mesh chosen
    assert visual_line("zCVobSpot") == "[visual % 0 0]"


def test_zones_and_triggers_write_their_box_as_the_bbox():
    """A cube empty of display size 1, scaled to half extents (metres)."""
    matrix = world_matrix(location=(10.0, 20.0, 5.0), rows=((4.0, 0, 0), (0, 3.0, 0), (0, 0, 2.0)))
    zone = FakeObject("oCZoneMusic:CAMP_XAR", matrix_world=matrix)
    zone.empty_display_size = 1.0
    props = exported_properties(VOB_CLASSES["oCZoneMusic"], zone)
    # Blender (x, y, z) m -> Gothic (x, z, y) cm
    assert props["bbox3DWS"] == "rawFloat:600.0 300.0 1700.0 1400.0 700.0 2300.0"
    assert props["priority"] == "int:1" and props["reverbLevel"] == "float:-3.219"
    assert _props("oCZoneMusicDefault", "DEFAULT_SYS")["priority"] == "int:0"


def test_trigger_flags_are_packed_bytes():
    script = _props("oCTriggerScript", script_func="EVT_FUNC")
    assert script["flags"] == "raw:07"            # startEnabled, isEnabled, sendUntrigger
    assert script["filterFlags"] == "raw:13"      # onTrigger, onTouch, respondToPC (vanilla)
    assert script["scriptFunc"] == "string:EVT_FUNC"
    assert script["numCanBeActivated"] == "int:-1"

    mover = _props("zCMover")
    assert mover["filterFlags"] == "raw:39"       # onTrigger, objects, PC, NPCs (vanilla)
    disabled = _props("zCTrigger", trigger_start_enabled=False, trigger_send_untrigger=False)
    assert disabled["flags"] == "raw:00"

    restored = custom_properties_from_block("zCTrigger", {"flags": "03", "filterFlags": "1b"})
    assert restored["trigger_start_enabled"] and not restored["trigger_send_untrigger"]
    assert restored["respond_to_object"] and not restored["react_to_on_damage"]


def test_trigger_list_and_code_master_write_their_filled_slots():
    props = _props("zCTriggerList", list_target_0="A", list_delay_0=1.5, list_target_2="C")
    assert props["numTarget"] == "int:2"
    assert (props["triggerTarget0"], props["fireDelay0"]) == ("string:A", "float:1.5")
    assert (props["triggerTarget1"], props["fireDelay1"]) == ("string:C", "float:0")
    assert "triggerTarget2" not in props

    master = _props("zCCodeMaster", trigger_target="DOOR", slave_0="S1", slave_1="S2", order_relevant=True)
    assert master["numSlaves"] == "int:2" and master["slaveVobName1"] == "string:S2"
    assert master["orderRelevant"] == "bool:1"


def test_mover_keyframes_come_from_its_keyframe_children():
    mover = FakeObject("zCMover:GATE", location=(1.0, 2.0, 3.0), visual_name="OC_LOB_GATE_BIG")
    FakeObject("MoverKey2", location=(1.0, 2.0, 8.0), parent=mover, zen_mover_key=1)
    FakeObject("MoverKey1", location=(1.0, 2.0, 3.0), parent=mover, zen_mover_key=0)
    FakeObject("some mesh", parent=mover, type="MESH")
    props = exported_properties(VOB_CLASSES["zCMover"], mover)

    assert props["visual"] == "string:OC_LOB_GATE_BIG.3DS"
    assert props["numKeyframes"] == "int:2"
    keyframes = decode_mover_keyframes(props["keyframes"].split(":", 1)[1])
    assert [k[0] for k in keyframes] == [(100.0, 300.0, 200.0), (100.0, 800.0, 200.0)]
    names = list(props)
    assert names[names.index("numKeyframes"):names.index("sfxOpenStart")] == \
        ["numKeyframes", "moveSpeed", "posLerpType", "speedType", "keyframes"]

    # Without keyframes the motion fields are left out, as the engine does.
    still = _props("zCMover")
    assert still["numKeyframes"] == "int:0" and "moveSpeed" not in still and "keyframes" not in still


def test_mover_keyframe_quaternion_matches_the_reference_world():
    """EVT_XARDAS_SECRET_01: keyframe 0 is the mover's own transform."""
    raw = ("ecb3e8468fa6a045645f7ec6d66047bafdf68e3c796e0e3c89f37f3f"
           "ecb3e8468fc6b245645f7ec6d66047bafdf68e3c796e0e3c89f37f3f")
    rotation = decode_rotation_matrix_hex(
        "2dce7f3fde2f8e3ce5fd0ebd369f8ebc05f67f3fc8919fba29e20e3d7a1cef3a02d87f3f")
    keyframes = decode_mover_keyframes(raw)
    assert keyframes[1][0][1] - keyframes[0][0][1] == pytest.approx(580.0)
    for row, expected in zip(keyframes[0][1], rotation):
        assert row == pytest.approx(expected, abs=1e-5)
    again = decode_mover_keyframes(encode_mover_keyframes(keyframes))
    for (pos, rot), (pos2, rot2) in zip(keyframes, again):
        assert pos2 == pytest.approx(pos)
        for row, row2 in zip(rot, rot2):
            assert row2 == pytest.approx(row, abs=1e-5)


def test_daytime_sound_item_and_misc_fields():
    day = _props("zCVobSoundDaytime", "", sound_name="OW_BIRD8", sound_name_2="OW_OWL1",
                 sound_start_time=6, sound_end_time=21)
    assert list(day)[-4:] == ["sndName", "sndStartTime", "sndEndTime", "sndName2"]
    assert (day["sndName"], day["sndName2"], day["sndEndTime"]) == \
        ("string:OW_BIRD8", "string:OW_OWL1", "float:21")
    assert _props("oCItem", "ITMI_GOLD")["itemInstance"] == "string:ITMI_GOLD"
    assert _props("zCZoneZFog", fog_color=[50, 50, 25, 255])["fogColor"] == "color:50 50 25 255"
    assert _props("zCEarthquake")["amplitudeCM"] == "vec3:2 10 2"
    assert _props("oCTriggerChangeLevel", level_name="NEWWORLD\\NEWWORLD.ZEN",
                  start_vob_name="START")["levelName"] == "string:NEWWORLD\\NEWWORLD.ZEN"
    fire = _props("oCMobFire")
    assert (fire["fireSlot"], fire["fireVobtreeName"]) == ("string:BIP01 FIRE", "string:FIRETREE_MEDIUM.ZEN")


def test_blender_parenting_becomes_the_vob_hierarchy():
    """A torch with its flame and light as children; childsN counts follow
    each vob. Non-vob objects in between (a collection empty) are skipped."""
    compo = FakeObject("zCVobLevelCompo:LEVEL")
    torch = FakeObject("zCVob:TORCH")
    group = FakeObject("Group", parent=torch)
    flame = FakeObject("zCVob:FLAME", parent=group, visual_name="FIRE.PFX")
    light = FakeObject("zCVobLight:GLOW", parent=torch)
    spark = FakeObject("zCVob:SPARK", parent=flame, visual_name="FIRE_SPARKS.PFX")
    spot = FakeObject("zCVobSpot:FP")

    printer = RecordingPrinter()
    tree = OCVobTree([spot, spark, light, flame, group, torch, compo], ZenGinDataPrinter(printer))
    end = tree.print(1)
    sequence = [line.strip() for line in printer.lines
                if line.strip().startswith(("childs", "vobName="))]

    assert sequence == [
        "childs0=int:3",
        "vobName=string:LEVEL-VOB", "childs1=int:0",
        "vobName=string:TORCH", "childs2=int:2",
        "vobName=string:GLOW", "childs3=int:0",
        "vobName=string:FLAME", "childs4=int:1",
        "vobName=string:SPARK", "childs5=int:0",
        "vobName=string:FP", "childs6=int:0",
    ]
    assert end - 1 == tree.objects_count() == 10     # 6 vobs + 4 visual blocks


def test_way_links_are_spread_so_no_waypoint_stores_more_than_three():
    """A hub with 6 neighbours: the hub keeps 3, the rest store their own."""
    ways = [("HUB", f"N{i}") for i in range(6)]
    oriented, dropped = orient_ways(ways)
    assert not dropped and len(oriented) == 6
    assert sum(1 for source, _ in oriented if source == "HUB") <= 3

    # The last way only fits after a stored link is handed to its other end.
    chain = [("A", "B"), ("A", "C"), ("A", "D"), ("B", "E"), ("B", "F"), ("B", "G"),
             ("A", "H"), ("B", "H"), ("H", "I"), ("H", "J"), ("H", "K")]
    oriented, dropped = orient_ways(chain)
    assert not dropped and {frozenset(w) for w in oriented} == {frozenset(w) for w in chain}
    stored = {}
    for source, _ in oriented:
        stored[source] = stored.get(source, 0) + 1
    assert max(stored.values()) <= 3

    # More ways than slots in total cannot fit: K4 needs 6, 4 nodes x 1 slot hold 4.
    k4 = [(a, b) for i, a in enumerate("ABCD") for b in "ABCD"[i + 1:]]
    oriented, dropped = orient_ways(k4, capacity=1)
    assert len(oriented) == 4 and len(dropped) == 2
