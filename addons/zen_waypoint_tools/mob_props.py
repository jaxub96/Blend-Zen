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
        "", "The game model this object uses, e.g. 'CHESTBIG_NW_NORMAL_LOCKED' "
        "(.MDS assumed) or 'BEDHIGH_NW_NORMAL_01.ASC' (other extensions are "
        "kept). Must exist in the game - Spacer crashes on a missing one. "
        "Use Apply Preset for vanilla models.",
        _INTER,
    ),
    "focus_name": (
        "", "Name shown when the player focuses it: a script string constant "
        "such as MOBNAME_CHEST (Text.d), or plain text.", _INTER,
    ),
    "hitpoints": (
        10, "Hitpoints (vanilla worlds use 10 for every interactive object).", _INTER,
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
        "", "Script function the engine calls as <name>_S1 when the object is "
        "used, e.g. SLEEPABIT (bed: sleep dialog), POTIONALCHEMY, MAKERUNE, "
        "PrayShrine.", _INTER,
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
        False, "Locked. Needs a Key Instance and/or a Picklock Str, otherwise "
        "it can never be opened.", _LOCKABLE,
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

# Per-type defaults; must match zen_gin_export.vob_fields.TYPE_DEFAULTS
# (checked by tests/test_mob_props.py). visual_name defaults are vanilla
# models known to load in Spacer and work in-game.
TYPE_DEFAULTS = {
    "oCMobContainer": {"focus_name": "MOBNAME_CHEST"},
    "oCMobDoor": {"focus_name": "MOBNAME_DOOR"},
    "oCMobBed": {"focus_name": "MOBNAME_BED", "on_state_func": "SLEEPABIT"},
    "oCMobSwitch": {"focus_name": "MOBNAME_SWITCH"},
    "oCMobWheel": {"focus_name": "MOBNAME_WHEEL"},
}
VISUAL_DEFAULTS = {
    "oCMobContainer": "CHESTBIG_NW_NORMAL_LOCKED",
    "oCMobDoor": "DOOR_NW_NORMAL_01",
    "oCMobBed": "BEDHIGH_NW_NORMAL_01.ASC",
    "oCMobLadder": "LADDER_3.ASC",
}

# Ready-made setups copied from vanilla Gothic II worlds (model, focus name,
# script function, required item). id -> (label, vob type, values).
MOB_PRESETS = {
    "CHEST_BIG": ("Big chest", "oCMobContainer", {"visual_name": "CHESTBIG_NW_NORMAL_LOCKED"}),
    "CHEST_BIG_RICH": ("Big chest, rich", "oCMobContainer", {"visual_name": "CHESTBIG_NW_RICH_OPEN"}),
    "CHEST_SMALL": ("Small chest", "oCMobContainer", {"visual_name": "CHESTSMALL_NW_POOR_LOCKED"}),
    "CHEST_SMALL_OPEN": ("Small chest, open", "oCMobContainer", {"visual_name": "CHESTSMALL_NW_POOR_OPEN"}),
    "DOOR_NORMAL": ("Door", "oCMobDoor", {"visual_name": "DOOR_NW_NORMAL_01"}),
    "DOOR_POOR": ("Door, poor", "oCMobDoor", {"visual_name": "DOOR_NW_POOR_01"}),
    "BED_NORMAL": ("Bed", "oCMobBed", {"visual_name": "BEDHIGH_NW_NORMAL_01.ASC"}),
    "BED_PSI": ("Bed, swamp camp", "oCMobBed", {"visual_name": "BEDHIGH_PSI.ASC"}),
    "BED_PC": ("Bed, player's", "oCMobBed", {"visual_name": "BEDHIGH_PC.ASC"}),
    "LADDER": ("Ladder", "oCMobLadder", {"visual_name": "LADDER_3.ASC"}),
    "LAB": ("Alchemy table", "oCMobInter", {
        "visual_name": "LAB_PSI.ASC", "focus_name": "MOBNAME_LAB",
        "on_state_func": "POTIONALCHEMY", "use_with_item": "ITMI_FLASK"}),
    "RUNEMAKER": ("Rune table", "oCMobInter", {
        "visual_name": "RMAKER_1.MDS", "focus_name": "MOBNAME_RUNEMAKER",
        "on_state_func": "MAKERUNE", "use_with_item": "ITMI_RUNEBLANK"}),
    "SHRINE": ("Innos shrine", "oCMobInter", {
        "visual_name": "INNOS_NW_MISC_01.ASC", "focus_name": "MOBNAME_INNOS",
        "on_state_func": "PrayShrine"}),
    "CAULDRON": ("Cauldron", "oCMobInter", {
        "visual_name": "CAULDRON_OC.ASC", "focus_name": "MOBNAME_CAULDRON",
        "use_with_item": "ITMI_SCOOP"}),
    "STOVE": ("Stove", "oCMobInter", {
        "visual_name": "STOVE_NW_CITY_01.ASC", "focus_name": "MOBNAME_STOVE",
        "use_with_item": "ITFOMUTTONRAW"}),
    "PAN": ("Campfire pan", "oCMobInter", {
        "visual_name": "PAN_OC.MDS", "focus_name": "MOBNAME_PAN",
        "use_with_item": "ITFOMUTTONRAW"}),
    "SAW": ("Tree saw", "oCMobInter", {
        "visual_name": "BAUMSAEGE_1.ASC", "focus_name": "MOBNAME_SAW",
        "use_with_item": "ITMI_SAW"}),
    "WATERPIPE": ("Water pipe", "oCMobInter", {
        "visual_name": "SMOKE_WATERPIPE.MDS", "focus_name": "MOBNAME_WATERPIPE"}),
    "BENCH": ("Bench", "oCMobInter", {"visual_name": "BENCH_NW_CITY_01.ASC", "focus_name": "MOBNAME_BENCH"}),
    "CHAIR": ("Chair", "oCMobInter", {"visual_name": "CHAIR_NW_NORMAL_01.ASC", "focus_name": "MOBNAME_CHAIR"}),
}


def default_for(vob_type, key):
    """The default value of a field for this type."""
    if key == "visual_name" and vob_type in VISUAL_DEFAULTS:
        return VISUAL_DEFAULTS[vob_type]
    return TYPE_DEFAULTS.get(vob_type, {}).get(key, MOB_PROPERTIES[key][0])


def presets_for(vob_type):
    """[(id, label)] of the presets for this type."""
    return [(pid, label) for pid, (label, t, _) in MOB_PRESETS.items() if t == vob_type]


def apply_preset(obj, preset_id):
    """Set a preset's values (and its type's defaults for the fields it
    doesn't name, so switching e.g. from the alchemy table to a bench
    clears the script function)."""
    _, vob_type, values = MOB_PRESETS[preset_id]
    for key in fields_for(vob_type):
        if key in values:
            obj[key] = values[key]
        elif key in ("focus_name", "on_state_func", "use_with_item", "condition_func"):
            obj[key] = default_for(vob_type, key)


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
        _, description, _ = MOB_PROPERTIES[key]
        obj[key] = default_for(vob_type, key)
        obj.id_properties_ui(key).update(description=description)
