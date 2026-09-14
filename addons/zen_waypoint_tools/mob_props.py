"""
Custom (ID) property schema for the oCMOB / oCMobInter family (chests,
doors, beds, switches, ladders, wheels, fire sources).

These are plain flat custom properties directly on the Blender object
(obj["key"] = value) - NOT a registered PropertyGroup. The exporter
(zen_gin_export's OCMob and its subclasses, see
modules/zen_gin_export/zen_gin_zcvob_ocmob.py) reads them back the same
addon-independent way ZCVobLight already reads light_static/color_a, so
zen_gin_export has zero dependency on this addon and keeps working from
plain Python/pytest. This module is only what CREATES those properties
(with a helpful description via id_properties_ui, so Blender's own
Object Properties > Custom Properties panel is self-documenting) when a
VOB of one of these types is added.

See documentation/USAGE_interactive_objects.md for the end-to-end guide
this schema is designed around.
"""

_INTER = (
    'oCMobInter', 'oCMobContainer', 'oCMobDoor', 'oCMobBed',
    'oCMobSwitch', 'oCMobLadder', 'oCMobWheel', 'oCMobFire',
)
_LOCKABLE = ('oCMobContainer', 'oCMobDoor')

# key -> (default_value, ui_description, vob_types_it_applies_to)
MOB_PROPERTIES = {
    "visual_name": (
        "", "Base filename (no extension) of the shared animated model "
        "this vob uses in-game, e.g. 'CHESTBIG_OCCRATELARGE' or "
        "'BED_HUM' - almost always a reused asset, NOT unique to this "
        "instance. Leave empty to reuse this object's own name (only "
        "correct for a one-off custom asset named after itself).",
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
        0, "Number of states the object's model script defines (0 = "
        "use the model's own default - almost always correct).", _INTER,
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
}

# Longest-name-first so a prefix check can't match a shorter type whose
# name happens to be a prefix of a longer one.
_KNOWN_MOB_TYPES = tuple(sorted(
    {t for _, _, types in MOB_PROPERTIES.values() for t in types},
    key=len, reverse=True,
))


def fields_for(vob_type):
    """Ordered list of custom-property keys relevant to this VOB type
    (insertion order of MOB_PROPERTIES, which mirrors the archive
    struct field order)."""
    return [key for key, (_, _, types) in MOB_PROPERTIES.items() if vob_type in types]


def mob_type_of(obj):
    """The oCMOB type prefix of a Blender object's name, or None if it
    isn't one of this family."""
    if obj is None:
        return None
    for vob_type in _KNOWN_MOB_TYPES:
        if obj.name.startswith(vob_type + ":"):
            return vob_type
    return None


def init_mob_properties(obj, vob_type):
    """Set every custom property this VOB type needs to a sensible
    default, with a UI description - but only for keys that don't
    already exist, so re-running this (e.g. from the sidebar panel,
    every draw) never clobbers a value you've already tuned by hand."""
    for key in fields_for(vob_type):
        if key in obj.keys():
            continue
        default, description, _ = MOB_PROPERTIES[key]
        obj[key] = default
        obj.id_properties_ui(key).update(description=description)
