"""
Ready-made setups for interactive objects, and small helpers around the
vob settings stored as flat custom (ID) properties (obj["key"]).

The settings themselves - which type has which key, defaults, archive
mapping - are defined once in zen_gin_export.vob_fields; the sidebar reads
and writes them through vob_ui.py. A key that is absent means "the type's
default", so objects only carry what was changed.

No bpy import, so it is testable outside Blender.
"""


def _vob_fields():
    from zen_gin_export import vob_fields
    return vob_fields


# Vanilla models known to load in Spacer and work in-game, used when a mob
# has no Visual of its own (new mobs get them explicitly).
VISUAL_DEFAULTS = {
    "oCMobContainer": "CHESTBIG_NW_NORMAL_LOCKED",
    "oCMobDoor": "DOOR_NW_NORMAL_01",
    "oCMobBed": "BEDHIGH_NW_NORMAL_01.ASC",
    "oCMobLadder": "LADDER_3.ASC",
    "oCMobSwitch": "LEVER_1_OC.MDS",
    "oCMobWheel": "VWHEEL_1_OC.MDS",
    "oCMobFire": "FIREPLACE_HIGH2.ASC",
    "oCMOB": "NW_MISC_SIGN_01.3DS",
}

# Ready-made setups copied from vanilla Gothic II worlds (model, focus name,
# script function, required item). id -> (label, vob type, values).
MOB_PRESETS = {
    "CHEST_BIG": ("Big chest", "oCMobContainer", {"visual_name": "CHESTBIG_NW_NORMAL_LOCKED"}),
    "CHEST_BIG_OPEN": ("Big chest, unlocked look", "oCMobContainer", {"visual_name": "CHESTBIG_NW_NORMAL_OPEN"}),
    "CHEST_BIG_RICH": ("Big chest, rich", "oCMobContainer", {"visual_name": "CHESTBIG_NW_RICH_OPEN"}),
    "CHEST_SMALL": ("Small chest", "oCMobContainer", {"visual_name": "CHESTSMALL_NW_POOR_LOCKED"}),
    "CHEST_SMALL_OPEN": ("Small chest, unlocked look", "oCMobContainer", {"visual_name": "CHESTSMALL_NW_POOR_OPEN"}),
    "DOOR_NORMAL": ("Door", "oCMobDoor", {"visual_name": "DOOR_NW_NORMAL_01"}),
    "DOOR_POOR": ("Door, poor", "oCMobDoor", {"visual_name": "DOOR_NW_POOR_01"}),
    "BED_NORMAL": ("Bed", "oCMobBed", {"visual_name": "BEDHIGH_NW_NORMAL_01.ASC"}),
    "BED_PSI": ("Bed, swamp camp", "oCMobBed", {"visual_name": "BEDHIGH_PSI.ASC"}),
    "BED_PC": ("Bed, player's", "oCMobBed", {"visual_name": "BEDHIGH_PC.ASC"}),
    "LADDER": ("Ladder", "oCMobLadder", {"visual_name": "LADDER_3.ASC"}),
    "LEVER": ("Lever", "oCMobSwitch", {"visual_name": "LEVER_1_OC.MDS"}),
    "TOUCHPLATE": ("Touch plate", "oCMobSwitch", {
        "visual_name": "TOUCHPLATE_STONE.MDS", "focus_name": "", "cd_dyn": False,
        "cd_static": False, "static_vob": False}),
    "WHEEL": ("Winch", "oCMobWheel", {"visual_name": "VWHEEL_1_OC.MDS"}),
    "FIRE_LAMP": ("Standing lamp", "oCMobFire", {
        "visual_name": "FIREPLACE_NW_LAMP_01.ASC", "fire_vobtree_name": "FIRETREE_LAMP.ZEN"}),
    "FIRE_HIGH": ("Fire bowl on a stand", "oCMobFire", {
        "visual_name": "FIREPLACE_HIGH2.ASC", "fire_vobtree_name": "FIRETREE_MEDIUM.ZEN"}),
    "TORCH_HOLDER": ("Wall torch holder", "oCMobFire", {
        "visual_name": "OC_LOB_TORCHHOLDER_FILLED.3DS", "fire_vobtree_name": "FIRETREE_LARGE.ZEN"}),
    "LAB": ("Alchemy table", "oCMobInter", {
        "visual_name": "LAB_PSI.ASC", "focus_name": "MOBNAME_LAB",
        "on_state_func": "POTIONALCHEMY", "use_with_item": "ITMI_FLASK"}),
    "RUNEMAKER": ("Rune table", "oCMobInter", {
        "visual_name": "RMAKER_1.MDS", "focus_name": "MOBNAME_RUNEMAKER",
        "on_state_func": "MAKERUNE", "use_with_item": "ITMI_RUNEBLANK"}),
    "SHRINE": ("Innos shrine", "oCMobInter", {
        "visual_name": "INNOS_NW_MISC_01.ASC", "focus_name": "MOBNAME_INNOS",
        "on_state_func": "PrayShrine"}),
    "BOOKSTAND": ("Bookstand", "oCMobInter", {
        "visual_name": "BOOK_NW_CITY_CUPBOARD_01.ASC", "focus_name": "MOBNAME_BOOKSBOARD"}),
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
    "THRONE": ("Armchair", "oCMobInter", {"visual_name": "THRONE_NW_CITY_01.ASC", "focus_name": "MOBNAME_ARMCHAIR"}),
    "SIGN": ("Sign", "oCMOB", {"visual_name": "NW_MISC_SIGN_01.3DS", "focus_name": "MOBNAME_CITY"}),
    "GRAVESTONE": ("Gravestone", "oCMOB", {"visual_name": "NW_MISC_GRAVESTONE_01.3DS", "focus_name": "MOBNAME_GRAVE_01"}),
}

# Fields a preset resets to the type's default when it doesn't name them,
# so switching e.g. from the alchemy table to a bench clears the function.
_PRESET_RESET_KEYS = ("focus_name", "on_state_func", "use_with_item", "condition_func")


def vob_type_of(obj):
    """The vob type an object's name prefix names, or None."""
    if obj is None:
        return None
    try:
        prefix, sep, _ = obj.name.partition(":")
    except ReferenceError:
        return None
    return prefix if sep and prefix in _vob_fields().VOB_SPECS else None


def fields_for(vob_type):
    """Ordered custom-property keys of this vob type's own settings
    (archive order; base vob flags not included)."""
    return [key for _, _, key, _ in _vob_fields().keyed_fields(vob_type)]


def default_for(vob_type, key):
    """The default value of a setting for this type."""
    if key == "visual_name":
        return VISUAL_DEFAULTS.get(vob_type, "")
    return _vob_fields().default_for(vob_type, key)


def presets_for(vob_type):
    """[(id, label)] of the presets for this type."""
    return [(pid, label) for pid, (label, t, _) in MOB_PRESETS.items() if t == vob_type]


def apply_preset(obj, preset_id):
    """Set a preset's values, and the type's defaults for the fields it
    doesn't name."""
    _, vob_type, values = MOB_PRESETS[preset_id]
    for key in fields_for(vob_type):
        if key in values:
            obj[key] = values[key]
        elif key in _PRESET_RESET_KEYS:
            obj[key] = default_for(vob_type, key)
    for key in _vob_fields().BASE_KEYS:
        if key in values:
            obj[key] = values[key]
        elif key in obj.keys():
            del obj[key]


def init_new_vob(obj, vob_type):
    """What a freshly added vob needs beyond the type's defaults: a model
    that exists in the game, so it loads in Spacer straight away."""
    if vob_type in VISUAL_DEFAULTS and "visual_name" not in obj.keys():
        obj["visual_name"] = VISUAL_DEFAULTS[vob_type]
