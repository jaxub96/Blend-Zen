import mob_props  # noqa: E402 (path set up by conftest.py)
import vob_ui_schema
from zen_gin_export import vob_fields


class FakeBlenderObject:
    """Just enough of bpy.types.Object's ID-property interface."""

    def __init__(self, name="", **existing):
        self.name = name
        self._data = dict(existing)

    def __setitem__(self, key, value):
        self._data[key] = value

    def __getitem__(self, key):
        return self._data[key]

    def __delitem__(self, key):
        del self._data[key]

    def keys(self):
        return self._data.keys()


def test_fields_for_only_returns_fields_relevant_to_that_type():
    bed_fields = mob_props.fields_for("oCMobBed")
    container_fields = mob_props.fields_for("oCMobContainer")

    assert "contains" in container_fields and "contains" not in bed_fields
    assert "locked" in container_fields and "locked" not in bed_fields
    assert "trigger_target" in bed_fields and "trigger_target" in container_fields
    assert "script_func" in mob_props.fields_for("oCTriggerScript")
    assert "decal_dim" in mob_props.fields_for("zCVob")


def test_vob_type_of_matches_the_name_prefix():
    assert mob_props.vob_type_of(FakeBlenderObject("oCMobDoor:DOOR_CHAPEL_01")) == "oCMobDoor"
    assert mob_props.vob_type_of(FakeBlenderObject("zCVob:SOME_PROP")) == "zCVob"
    assert mob_props.vob_type_of(FakeBlenderObject("zCWaypoint:WP")) is None
    assert mob_props.vob_type_of(FakeBlenderObject("Cube")) is None
    assert mob_props.vob_type_of(None) is None


def test_every_setting_has_ui_metadata_and_every_type_a_menu_entry():
    """vob_ui_schema (labels, tooltips, dropdown sources) and
    zen_gin_export.vob_fields (archive mapping) describe the same keys."""
    keys = set(vob_fields.BASE_KEYS)
    for vob_type in vob_fields.VOB_SPECS:
        keys |= {key for _, _, key, _ in vob_fields.keyed_fields(vob_type)}
        assert vob_ui_schema.type_info(vob_type), vob_type
    assert keys == set(vob_ui_schema.FIELD_UI)

    for type_id in vob_ui_schema.VOB_TYPE_INFO:
        assert vob_ui_schema.split_type_id(type_id)[0] in vob_fields.VOB_SPECS, type_id
    # Props and items come from the asset libraries, not from Add VOB.
    assert "zCVob" not in vob_ui_schema.VOB_TYPE_INFO and "oCItem" not in vob_ui_schema.VOB_TYPE_INFO


def test_irrelevant_settings_are_hidden():
    """`when` conditions: only what matters for the current values shows."""
    def visible(key, vob_type, **values):
        when = vob_ui_schema.FIELD_UI[key][2].get("when")
        return when is None or when(lambda k: values.get(k, vob_fields.default_for(vob_type, k)
                                                         if k != "visual_name" else ""), vob_type)

    assert not visible("key_instance", "oCMobContainer")
    assert visible("key_instance", "oCMobContainer", locked=True)
    assert not visible("sound_random_delay", "zCVobSound")
    assert visible("sound_random_delay", "zCVobSound", sound_mode="RANDOM")
    assert not visible("color_ani_list", "zCVobLight")
    assert visible("color_ani_list", "zCVobLight", light_static=False)
    assert not visible("decal_dim", "zCVob", visual_name="ROCK.3DS")
    assert visible("decal_dim", "zCVob", visual_name="ZFLARE6.TGA")
    assert not visible("list_target_2", "zCTriggerList", list_target_0="A")
    assert visible("list_target_1", "zCTriggerList", list_target_0="A")
    # Values that never vary in vanilla worlds sit in Advanced.
    for key in ("hitpoints", "damage", "moveable", "takeable", "sound_cone_angle", "zbias"):
        assert vob_ui_schema.FIELD_UI[key][2].get("adv"), key


def test_presets_only_set_fields_their_type_has_and_give_a_model():
    for preset_id, (label, vob_type, values) in mob_props.MOB_PRESETS.items():
        allowed = set(mob_props.fields_for(vob_type)) | set(vob_fields.BASE_KEYS)
        assert set(values) <= allowed, preset_id
        assert values["visual_name"], preset_id


def test_new_mobs_get_a_working_vanilla_model_and_presets_switch_cleanly():
    bed = FakeBlenderObject("oCMobBed:BED")
    mob_props.init_new_vob(bed, "oCMobBed")
    assert bed["visual_name"] == "BEDHIGH_NW_NORMAL_01.ASC"
    assert mob_props.default_for("oCMobBed", "on_state_func") == "SLEEPABIT"

    table = FakeBlenderObject("oCMobInter:T")
    mob_props.apply_preset(table, "LAB")
    assert (table["on_state_func"], table["use_with_item"]) == ("POTIONALCHEMY", "ITMI_FLASK")
    mob_props.apply_preset(table, "BENCH")
    assert (table["visual_name"], table["on_state_func"], table["use_with_item"]) == \
        ("BENCH_NW_CITY_01.ASC", "", "")

    plate = FakeBlenderObject("oCMobSwitch:S")
    mob_props.apply_preset(plate, "TOUCHPLATE")
    assert plate["cd_dyn"] is False             # you walk onto it
    mob_props.apply_preset(plate, "LEVER")
    assert "cd_dyn" not in plate.keys()         # back to the type's default
