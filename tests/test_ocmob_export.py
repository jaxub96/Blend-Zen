from mathutils import Quaternion

from conftest import RecordingPrinter, FakeLocation
from modules.zen_gin_export.zen_gin_data_printer import ZenGinDataPrinter
from modules.zen_gin_export.zen_gin_zcvob_ocmob_inter import OCMobInter
from modules.zen_gin_export.zen_gin_zcvob_ocmob_container import OCMobContainer
from modules.zen_gin_export.zen_gin_zcvob_ocmob_door import OCMobDoor
from modules.zen_gin_export.zen_gin_zcvob_ocmob_fire import OCMobFire


class FakeBlenderObject:
    """A bare test double with no Blender/bpy dependency - only what
    ZCVob/OCMob actually touch: name, location, rotation_quaternion, and
    dict-style custom-property access via .get(), mirroring the flat ID
    properties zen_waypoint_tools' mob_props.py sets on the real object."""

    rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
    location = FakeLocation()

    def __init__(self, name, **custom_properties):
        self.name = name
        self._custom_properties = custom_properties

    def get(self, key, default=None):
        return self._custom_properties.get(key, default)


def _exported_properties(vob_object_class, blender_object):
    printer = RecordingPrinter()
    data_printer = ZenGinDataPrinter(printer)
    vob_object_class(blender_object, printer, data_printer).print(0)

    properties = {}
    for line in printer.lines:
        stripped = line.strip()
        if "=" not in stripped or stripped.startswith("["):
            continue
        name, value = stripped.split("=", 1)
        properties[name] = value
    return properties


def test_ocmob_base_fields_default_when_no_custom_properties_set():
    obj = FakeBlenderObject("oCMobInter:UNCONFIGURED")
    props = _exported_properties(OCMobInter, obj)

    assert props["focusName"] == "string:"
    assert props["hitpoints"] == "int:0"
    assert props["damage"] == "int:0"
    assert props["moveable"] == "bool:0"
    assert props["takeable"] == "bool:0"
    assert props["soundMaterial"] == "enum:0"  # WOOD
    assert props["isDestroyed"] == "bool:0"
    # No visual_name override -> falls back to the vob's own name.
    assert props["visual"] == "string:UNCONFIGURED.MDS"


def test_ocmob_inter_fields_read_custom_properties():
    obj = FakeBlenderObject(
        "oCMobSwitch:LEVER_GATE_01",
        trigger_target="GATE_MOVER_01",
        condition_func="ZS_GateCondition",
        on_state_func="ZS_GateUse",
        rewind=True,
    )
    props = _exported_properties(OCMobInter, obj)

    assert props["triggerTarget"] == "string:GATE_MOVER_01"
    assert props["conditionFunc"] == "string:ZS_GateCondition"
    assert props["onStateFunc"] == "string:ZS_GateUse"
    assert props["rewind"] == "bool:1"


def test_ocmob_container_is_lockable_and_has_contains():
    obj = FakeBlenderObject(
        "oCMobContainer:CHEST_CITY_01",
        visual_name="CHESTBIG_OCCRATELARGE",
        locked=True,
        key_instance="ITKE_CHEST_CITY_01",
        picklock_str="RRLRL",
        contains="ITFO_APPLE:3,ITMW_1H_SHORTSWORD1",
    )
    props = _exported_properties(OCMobContainer, obj)

    assert props["visual"] == "string:CHESTBIG_OCCRATELARGE.MDS"
    assert props["locked"] == "bool:1"
    assert props["keyInstance"] == "string:ITKE_CHEST_CITY_01"
    assert props["pickLockStr"] == "string:RRLRL"
    assert props["contains"] == "string:ITFO_APPLE:3,ITMW_1H_SHORTSWORD1"


def test_ocmob_door_has_lock_fields_but_no_contains():
    obj = FakeBlenderObject("oCMobDoor:DOOR_CHAPEL_01", locked=True)
    props = _exported_properties(OCMobDoor, obj)

    assert props["locked"] == "bool:1"
    assert "contains" not in props


def test_ocmob_fire_adds_fire_slot_and_vobtree():
    obj = FakeBlenderObject(
        "oCMobFire:CAMPFIRE_01",
        fire_slot="BIP01 FIRE",
        fire_vobtree_name="FIRETREE_MEDIUM.ZEN",
    )
    props = _exported_properties(OCMobFire, obj)

    assert props["fireSlot"] == "string:BIP01 FIRE"
    assert props["fireVobtreeName"] == "string:FIRETREE_MEDIUM.ZEN"


def test_ocmob_type_name_chain_matches_real_archive_convention():
    """Real example confirmed from a decompiled ZEN: `oCMobInter:oCMOB:zCVob`
    (oCVob is NOT part of the persisted class-name chain) - this pins that
    convention down the whole oCMOB hierarchy so it can't silently drift."""
    assert OCMobInter._type_name == "oCMobInter:oCMOB:zCVob"
    assert OCMobContainer._type_name == "oCMobContainer:oCMobLockable:oCMobInter:oCMOB:zCVob"
    assert OCMobDoor._type_name == "oCMobDoor:oCMobLockable:oCMobInter:oCMOB:zCVob"
