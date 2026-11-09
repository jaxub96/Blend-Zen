import mob_props  # noqa: E402 (path set up by conftest.py)


class FakeIdPropertiesUI:
    def __init__(self, descriptions, key):
        self._descriptions = descriptions
        self._key = key

    def update(self, description=""):
        self._descriptions[self._key] = description


class FakeBlenderObject:
    """Just enough of bpy.types.Object's ID-property interface for
    init_mob_properties() to operate on: dict-style __getitem__/
    __setitem__/keys(), plus id_properties_ui()."""

    def __init__(self, **existing):
        self._data = dict(existing)
        self.descriptions = {}

    def __setitem__(self, key, value):
        self._data[key] = value

    def __getitem__(self, key):
        return self._data[key]

    def keys(self):
        return self._data.keys()

    def id_properties_ui(self, key):
        return FakeIdPropertiesUI(self.descriptions, key)


def test_fields_for_only_returns_fields_relevant_to_that_type():
    bed_fields = mob_props.fields_for("oCMobBed")
    container_fields = mob_props.fields_for("oCMobContainer")

    assert "contains" in container_fields
    assert "contains" not in bed_fields
    assert "locked" in container_fields
    assert "locked" not in bed_fields
    # shared oCMOB/oCMobInter fields apply to both
    assert "trigger_target" in bed_fields
    assert "trigger_target" in container_fields


def test_mob_type_of_matches_the_name_prefix():
    obj = FakeBlenderObject()
    obj.name = "oCMobDoor:DOOR_CHAPEL_01"
    assert mob_props.mob_type_of(obj) == "oCMobDoor"

    obj.name = "zCVob:SOME_PROP"
    assert mob_props.mob_type_of(obj) is None

    assert mob_props.mob_type_of(None) is None


def test_init_mob_properties_sets_defaults_and_descriptions():
    obj = FakeBlenderObject()
    mob_props.init_mob_properties(obj, "oCMobFire")

    for key in mob_props.fields_for("oCMobFire"):
        assert key in obj.keys()
        assert obj.descriptions[key]  # every field gets a real description


def test_init_mob_properties_never_overwrites_an_existing_value():
    """Re-running this (e.g. from the sidebar panel on every draw) must
    never clobber a value the user already tuned by hand."""
    obj = FakeBlenderObject(locked=True)
    mob_props.init_mob_properties(obj, "oCMobContainer")

    assert obj["locked"] is True


def test_addon_schema_matches_the_exporter_field_table():
    """mob_props.py (UI defaults/descriptions) and zen_gin_export's
    vob_fields.py (archive mapping) describe the same keys and defaults."""
    from modules.zen_gin_export.vob_fields import FIELDS_BY_TYPE, field_default

    for vob_type, fields in FIELDS_BY_TYPE.items():
        exporter = {key: field_default(vob_type, key, default)
                    for _, _, key, default in fields if key is not None}
        addon = {key: mob_props.default_for(vob_type, key)
                 for key in mob_props.fields_for(vob_type) if key != "visual_name"}
        assert addon == exporter, vob_type


def test_presets_only_set_fields_their_type_has_and_give_a_model():
    for preset_id, (label, vob_type, values) in mob_props.MOB_PRESETS.items():
        assert set(values) <= set(mob_props.fields_for(vob_type)), preset_id
        assert values["visual_name"], preset_id


def test_new_mobs_get_a_working_vanilla_setup_and_presets_switch_cleanly():
    bed = FakeBlenderObject()
    mob_props.init_mob_properties(bed, "oCMobBed")
    assert bed["visual_name"] == "BEDHIGH_NW_NORMAL_01.ASC"
    assert bed["on_state_func"] == "SLEEPABIT"

    table = FakeBlenderObject()
    mob_props.init_mob_properties(table, "oCMobInter")
    mob_props.apply_preset(table, "LAB")
    assert (table["on_state_func"], table["use_with_item"]) == ("POTIONALCHEMY", "ITMI_FLASK")
    mob_props.apply_preset(table, "BENCH")
    assert (table["visual_name"], table["on_state_func"], table["use_with_item"]) == \
        ("BENCH_NW_CITY_01.ASC", "", "")


def test_sound_vobs_get_settings_and_missing_fields_are_reported():
    obj = FakeBlenderObject()
    obj.name = "zCVobSound:OW_COASTLIGHT"
    assert mob_props.mob_type_of(obj) == "zCVobSound"
    assert "sound_radius" in mob_props.missing_fields(obj, "zCVobSound")

    mob_props.init_mob_properties(obj, "zCVobSound")
    assert mob_props.missing_fields(obj, "zCVobSound") == []
