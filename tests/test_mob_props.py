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
