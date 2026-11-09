"""
Per-instance vob fields stored as flat custom (ID) properties on the
Blender object, and how each maps onto an archive property.

One table drives both directions: the exporter writes these properties
(print_fields) and the importer turns a parsed block back into custom
properties (custom_properties_from_block). The addon's mob_props.py adds
UI descriptions for the same keys; tests/test_mob_props.py checks the two
agree.

Field = (archive name, archive type, custom key, default). A custom key of
None is a constant: always written with its default, never read.
Archive property order matters - it follows real Spacer-saved worlds.
"""

ENUMS = {
    "soundMaterial": ("WOOD", "STONE", "METAL", "LEATHER", "CLAY", "GLAS"),
    "sndMode": ("LOOP", "ONCE", "RANDOM"),
    "sndVolType": ("SPHERE", "ELLIPSOID"),
}

OCMOB_FIELDS = (
    ("focusName", "string", "focus_name", ""),
    ("hitpoints", "int", "hitpoints", 10),
    ("damage", "int", "damage", 0),
    ("moveable", "bool", "moveable", False),
    ("takeable", "bool", "takeable", False),
    ("focusOverride", "bool", None, False),
    ("soundMaterial", "enum", "sound_material", "WOOD"),
    ("visualDestroyed", "string", None, ""),
    ("owner", "string", "owner", ""),
    ("ownerGuild", "string", "owner_guild", ""),
    ("isDestroyed", "bool", None, False),
)

INTER_FIELDS = (
    ("stateNum", "int", "state_num", 1),
    ("triggerTarget", "string", "trigger_target", ""),
    ("useWithItem", "string", "use_with_item", ""),
    ("conditionFunc", "string", "condition_func", ""),
    ("onStateFunc", "string", "on_state_func", ""),
    ("rewind", "bool", "rewind", False),
)

LOCKABLE_FIELDS = (
    ("locked", "bool", "locked", False),
    ("keyInstance", "string", "key_instance", ""),
    ("pickLockStr", "string", "picklock_str", ""),
)

CONTAINER_FIELDS = (
    ("contains", "string", "contains", ""),
)

FIRE_FIELDS = (
    ("fireSlot", "string", "fire_slot", ""),
    ("fireVobtreeName", "string", "fire_vobtree_name", ""),
)

# sndName follows these and is the vob's own name (see ZCVobSound).
SOUND_FIELDS = (
    ("sndVolume", "float", "sound_volume", 100.0),
    ("sndMode", "enum", "sound_mode", "LOOP"),
    ("sndRandDelay", "float", "sound_random_delay", 5.0),
    ("sndRandDelayVar", "float", None, 2.0),
    ("sndStartOn", "bool", "sound_start_on", True),
    ("sndAmbient3D", "bool", "sound_ambient_3d", False),
    ("sndObstruction", "bool", None, False),
    ("sndConeAngle", "float", None, 0.0),
    ("sndVolType", "enum", None, "SPHERE"),
    ("sndRadius", "float", "sound_radius", 1500.0),
)

_INTER = OCMOB_FIELDS + INTER_FIELDS

# Per-type defaults that replace a field's generic default, taken from
# vanilla worlds and the game scripts. A bed needs onStateFunc SLEEPABIT:
# the engine calls <onStateFunc>_S1 when it's used, and SLEEPABIT_S1
# (Story/Dialog_Mobsis/SleepABit.d) opens the sleep dialog. focusName is a
# script string constant (MOBNAME_* in Text.d) the engine resolves.
TYPE_DEFAULTS = {
    "oCMobContainer": {"focus_name": "MOBNAME_CHEST"},
    "oCMobDoor": {"focus_name": "MOBNAME_DOOR"},
    "oCMobBed": {"focus_name": "MOBNAME_BED", "on_state_func": "SLEEPABIT"},
    "oCMobSwitch": {"focus_name": "MOBNAME_SWITCH"},
    "oCMobWheel": {"focus_name": "MOBNAME_WHEEL"},
}


def field_default(vob_type, key, generic_default):
    return TYPE_DEFAULTS.get(vob_type, {}).get(key, generic_default)

FIELDS_BY_TYPE = {
    "oCMobInter": _INTER,
    "oCMobBed": _INTER,
    "oCMobSwitch": _INTER,
    "oCMobLadder": _INTER,
    "oCMobWheel": _INTER,
    "oCMobDoor": _INTER + LOCKABLE_FIELDS,
    "oCMobContainer": _INTER + LOCKABLE_FIELDS + CONTAINER_FIELDS,
    "oCMobFire": _INTER + FIRE_FIELDS,
    "zCVobSound": SOUND_FIELDS,
}


def _enum_ordinal(archive_name, value):
    names = ENUMS[archive_name]
    if isinstance(value, str):
        upper = value.strip().upper()
        return names.index(upper) if upper in names else 0
    try:
        ordinal = int(value)
    except (TypeError, ValueError):
        return 0
    return ordinal if 0 <= ordinal < len(names) else 0


def print_fields(data_printer, fields, get_custom, vob_type=None):
    """Write `fields` in order. get_custom(key, default) reads one custom
    property; a missing one uses the (per-type) default, and bad values
    (e.g. text in an int field) fall back to it rather than failing the
    whole export."""
    for archive_name, archive_type, key, default in fields:
        default = field_default(vob_type, key, default)
        value = default if key is None else get_custom(key, default)
        if archive_type == "enum":
            data_printer.print_enum_property(archive_name, _enum_ordinal(archive_name, value))
            continue
        try:
            if archive_type == "int":
                data_printer.print_int_property(archive_name, int(value))
            elif archive_type == "float":
                data_printer.print_float_property(archive_name, float(value))
            elif archive_type == "bool":
                data_printer.print_bool_property(archive_name, bool(value))
            else:
                data_printer.print_string_property(archive_name, str(value))
        except (TypeError, ValueError):
            data_printer.print_property(archive_name, archive_type, default if archive_type != "bool" else int(default))


def custom_properties_from_block(vob_type, properties):
    """Inverse of print_fields for the importer: {custom key: value} from a
    parsed block's properties (strings), for every non-constant field of
    `vob_type` present in the block. Unknown types give {}."""
    result = {}
    for archive_name, archive_type, key, default in FIELDS_BY_TYPE.get(vob_type, ()):
        if key is None or archive_name not in properties:
            continue
        raw = properties[archive_name].strip()
        try:
            if archive_type == "int":
                value = int(raw)
            elif archive_type == "float":
                value = float(raw)
            elif archive_type == "bool":
                value = raw == "1"
            elif archive_type == "enum":
                names = ENUMS[archive_name]
                ordinal = int(raw)
                value = names[ordinal] if 0 <= ordinal < len(names) else default
            else:
                value = properties[archive_name]
        except ValueError:
            value = default
        result[key] = value
    return result
