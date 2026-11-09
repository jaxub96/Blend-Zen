"""
Custom (ID) property schema for vobs with per-instance settings: the
oCMOB family (chests, doors, beds, switches, ladders, wheels, fire
sources) and zCVobSound.

These are plain flat custom properties on the object (obj["key"]), not a
PropertyGroup: zen_gin_export reads them with obj.get() (see its
vob_fields.py, which maps each key to an archive property), so the
exporter keeps working from plain Python. This module only adds the keys
with defaults and UI descriptions; tests/test_mob_props.py checks the
keys and defaults match vob_fields.py.

No bpy import, so it is testable outside Blender.
"""

_INTER = (
    'oCMobInter', 'oCMobContainer', 'oCMobDoor', 'oCMobBed',
    'oCMobSwitch', 'oCMobLadder', 'oCMobWheel', 'oCMobFire',
)
_LOCKABLE = ('oCMobContainer', 'oCMobDoor')
_SOUND = ('zCVobSound',)

# key -> (default_value, ui_description, vob_types_it_applies_to)
MOB_PROPERTIES = {
    "visual_name": (
        "", "Base filename (no extension) of the shared animated model "
        "this vob uses in-game, e.g. 'CHESTBIG_OCCRATELARGE' or "
        "'BED_HUM' - almost always a reused asset, NOT unique to this "
        "instance. Leave empty to reuse this object's own name (only "
        "correct for a one-off custom asset named after itself). Give an "
        "extension for non-MDS models, e.g. 'BEDHIGH_NW_NORMAL_01.ASC'.",
        _INTER,
    ),
    "focus_name": (
        "", "Name shown in-game when the player focuses this object.", _INTER,
    ),
    "hitpoints": (
        0, "Hitpoints before the object can be destroyed (0 = "
        "indestructible - the normal setting for furniture).", _INTER,
    ),
    "damage": (
        0, "Damage dealt by the object when used (traps/weapons only - "
        "leave 0 for furniture).", _INTER,
    ),
    "moveable": (
        False, "Can the player pick this object up and reposition it?", _INTER,
    ),
    "takeable": (
        False, "Can the player carry this object in their inventory?", _INTER,
    ),
    "sound_material": (
        "WOOD", "Impact sound material - one of WOOD, STONE, METAL, "
        "LEATHER, CLAY, GLAS.", _INTER,
    ),
    "owner": (
        "", "Script instance name of the NPC who owns this object "
        "(affects theft detection).", _INTER,
    ),
    "owner_guild": (
        "", "Guild that owns this object (affects theft detection).", _INTER,
    ),
    "trigger_target": (
        "", "vobName of another VOB to send an OnTrigger event to when "
        "this object is used.", _INTER,
    ),
    "use_with_item": (
        "", "Script instance name of the item required in inventory to "
        "interact with this object.", _INTER,
    ),
    "condition_func": (
        "", "Daedalus function deciding whether the object can "
        "currently be used.", _INTER,
    ),
    "on_state_func": (
        "", "Daedalus function called when the object is used.", _INTER,
    ),
    "state_num": (
        1, "Number of states the object's model script defines. Vanilla "
        "worlds use 1 for nearly every object.", _INTER,
    ),
    "rewind": (
        False, "Fire the trigger every time the object is used, instead "
        "of only the first time.", _INTER,
    ),
    "locked": (
        False, "Is this locked?", _LOCKABLE,
    ),
    "key_instance": (
        "", "Script instance name of the key item that unlocks this.", _LOCKABLE,
    ),
    "picklock_str": (
        "", "Picklock combination, e.g. 'RRLRL' (R/L per pick attempt). "
        "Empty means it can't be picked at all.", _LOCKABLE,
    ),
    "contains": (
        "", "Comma-separated 'ITEM_INSTANCE:count' list, e.g. "
        "'ITFO_APPLE:3,ITMW_1H_SHORTSWORD1' (':count' is optional, "
        "defaults to 1).", ('oCMobContainer',),
    ),
    "fire_slot": (
        "", "Bone name on the rigged model to attach the fire effect to.",
        ('oCMobFire',),
    ),
    "fire_vobtree_name": (
        "", "Fire effect template ZEN, e.g. 'FIRETREE_MEDIUM.ZEN'.",
        ('oCMobFire',),
    ),
    "sound_volume": (
        100.0, "Volume, 0-100.", _SOUND,
    ),
    "sound_mode": (
        "LOOP", "LOOP (continuous), ONCE, or RANDOM (repeats after a random "
        "delay).", _SOUND,
    ),
    "sound_random_delay": (
        5.0, "Seconds between repeats in RANDOM mode.", _SOUND,
    ),
    "sound_start_on": (
        True, "Playing from the start (otherwise it waits for a trigger).", _SOUND,
    ),
    "sound_ambient_3d": (
        False, "Ambient 3D sound.", _SOUND,
    ),
    "sound_radius": (
        1500.0, "Audible radius in cm (Gothic units).", _SOUND,
    ),
}

_KNOWN_MOB_TYPES = frozenset(t for _, _, types in MOB_PROPERTIES.values() for t in types)


def fields_for(vob_type):
    """Ordered list of custom-property keys relevant to this VOB type
    (insertion order of MOB_PROPERTIES, which mirrors the archive
    struct field order)."""
    return [key for key, (_, _, types) in MOB_PROPERTIES.items() if vob_type in types]


def mob_type_of(obj):
    """The vob type prefix of an object's name if that type has settings
    here (oCMOB family, zCVobSound), else None."""
    if obj is None:
        return None
    prefix, sep, _ = obj.name.partition(":")
    return prefix if sep and prefix in _KNOWN_MOB_TYPES else None


def missing_fields(obj, vob_type):
    """Keys this type needs that obj doesn't have yet."""
    return [key for key in fields_for(vob_type) if key not in obj.keys()]


def init_mob_properties(obj, vob_type, fields=None):
    """Add every custom property this type needs, with its default and a
    UI description - only keys that don't exist yet, so values already
    tuned by hand are never overwritten."""
    for key in fields if fields is not None else fields_for(vob_type):
        if key in obj.keys():
            continue
        default, description, _ = MOB_PROPERTIES[key]
        obj[key] = default
        obj.id_properties_ui(key).update(description=description)
