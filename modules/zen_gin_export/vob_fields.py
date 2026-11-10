"""
The one table of every vob type Blend-Zen can write and read.

Per-instance data is stored as flat custom (ID) properties on the Blender
object and read with obj.get(), so this package stays independent of the
addon. The same tables drive the exporter (print_fields), the importer
(custom_properties_from_block) and the addon's sidebar (which builds its
widgets from VOB_SPECS; labels and tooltips live in the addon's
vob_ui_schema.py, and tests check the two agree).

Field = (archive name, archive type, custom key, default). A custom key of
None is a constant: always written with its default, never read.
Archive types: string, int, float, bool, enum, color (4 ints), vec3
(3 floats), rawFloat (n floats).

Class chains, versions, property order and default flags were surveyed
from the ASCII part-worlds shipped with Gothic II (NewWorld / Addon /
OldWorld, ~43,000 vobs).
"""

from dataclasses import dataclass, field as _dc_field

ENUMS = {
    "soundMaterial": ("WOOD", "STONE", "METAL", "LEATHER", "CLAY", "GLAS"),
    "sndMode": ("LOOP", "ONCE", "RANDOM"),
    "sndVolType": ("SPHERE", "ELLIPSOID"),
    "visualCamAlign": ("NONE", "YAW", "FULL"),
    "visualAniMode": ("NONE", "WIND", "WIND2"),
    "dynShadow": ("NONE", "BLOB"),
    "lightQuality": ("HIGH", "MEDIUM", "LOW"),
    "decalAlphaFunc": ("MAT_DEFAULT", "NONE", "BLEND", "ADD", "SUB", "MUL", "MUL2"),
    "moverBehavior": ("TOGGLE", "TRIGGER_CONTROL", "OPEN_TIMED", "LOOP", "SINGLE_KEYS"),
    "posLerpType": ("LINEAR", "CURVE"),
    "speedType": ("CONST", "SLOW_START_END", "SLOW_START", "SLOW_END",
                  "SEG_SLOW_START_END", "SEG_SLOW_START", "SEG_SLOW_END"),
    "listProcess": ("ALL", "NEXT_ONE", "RAND_ONE"),
    "onTrigger": ("NONE", "TRIGGER", "UNTRIGGER", "ENABLE", "DISABLE", "TOGGLE_ENABLED"),
    "onUntrigger": ("NONE", "TRIGGER", "UNTRIGGER", "ENABLE", "DISABLE", "TOGGLE_ENABLED"),
    "damageCollType": ("NONE", "BOX", "POINT"),
}

# -- zCVob base -----------------------------------------------------------------
# Written for every vob, around bbox/transform/name/visual (see ZCVob.print).
# Their defaults come from the type (VobSpec.flags), not from this table.
BASE_FIELDS = (
    ("presetName", "string", "preset_name", ""),
    ("showVisual", "bool", "show_visual", True),
    ("visualCamAlign", "enum", "cam_align", "NONE"),
    ("visualAniMode", "enum", "ani_mode", "NONE"),
    ("visualAniModeStrength", "float", "ani_strength", 0.0),
    ("vobFarClipZScale", "float", "far_clip_scale", 1.0),
    ("cdStatic", "bool", "cd_static", False),
    ("cdDyn", "bool", "cd_dyn", False),
    ("staticVob", "bool", "static_vob", False),
    ("dynShadow", "enum", "dyn_shadow", "NONE"),
    ("zbias", "int", "zbias", 0),
    ("isAmbient", "bool", "is_ambient", False),
)
BASE_KEYS = tuple(f[2] for f in BASE_FIELDS)

# Inside the `[visual zCDecal]` sub-block of a vob whose visual is a .TGA.
DECAL_FIELDS = (
    ("decalDim", "rawFloat", "decal_dim", (25.0, 25.0)),
    ("decalOffset", "rawFloat", "decal_offset", (0.0, 0.0)),
    ("decal2Sided", "bool", "decal_two_sided", True),
    ("decalAlphaFunc", "enum", "decal_alpha_func", "ADD"),
    ("decalTexAniFPS", "float", "decal_tex_ani_fps", 0.0),
    ("decalAlphaWeight", "int", "decal_alpha_weight", 255),
    ("ignoreDayLight", "bool", "decal_ignore_daylight", False),
)

# -- oCMOB family -----------------------------------------------------------------
OCMOB_FIELDS = (
    ("focusName", "string", "focus_name", ""),
    ("hitpoints", "int", "hitpoints", 10),
    ("damage", "int", "damage", 0),
    ("moveable", "bool", "moveable", False),
    ("takeable", "bool", "takeable", False),
    ("focusOverride", "bool", "focus_override", False),
    ("soundMaterial", "enum", "sound_material", "WOOD"),
    ("visualDestroyed", "string", "visual_destroyed", ""),
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
    ("fireSlot", "string", "fire_slot", "BIP01 FIRE"),
    ("fireVobtreeName", "string", "fire_vobtree_name", "FIRETREE_MEDIUM.ZEN"),
)

_INTER = OCMOB_FIELDS + INTER_FIELDS

# -- sounds -------------------------------------------------------------------------
# sound_name empty means "the vob's own name" (how older scenes store it).
SOUND_FIELDS = (
    ("sndVolume", "float", "sound_volume", 100.0),
    ("sndMode", "enum", "sound_mode", "LOOP"),
    ("sndRandDelay", "float", "sound_random_delay", 5.0),
    ("sndRandDelayVar", "float", "sound_random_delay_var", 2.0),
    ("sndStartOn", "bool", "sound_start_on", True),
    ("sndAmbient3D", "bool", "sound_ambient_3d", False),
    ("sndObstruction", "bool", "sound_obstruction", False),
    ("sndConeAngle", "float", "sound_cone_angle", 0.0),
    ("sndVolType", "enum", "sound_vol_type", "SPHERE"),
    ("sndRadius", "float", "sound_radius", 1500.0),
    ("sndName", "string", "sound_name", ""),
)

SOUND_DAYTIME_FIELDS = SOUND_FIELDS + (
    ("sndStartTime", "float", "sound_start_time", 6.0),
    ("sndEndTime", "float", "sound_end_time", 20.0),
    ("sndName2", "string", "sound_name_2", ""),
)

# -- lights ---------------------------------------------------------------------------
# lightType, range, color and spotConeAngle come from the Blender light
# itself (see ZCVobLight); these are the settings Blender has no equivalent
# for. The fields after lensflareFX are only written for dynamic lights
# (lightStatic=0), as the engine does.
LIGHT_FIELDS = (
    ("lightPresetInUse", "string", "light_preset", ""),
    ("lightStatic", "bool", "light_static", True),
    ("lightQuality", "enum", "light_quality", "LOW"),
    ("lensflareFX", "string", "lensflare_fx", ""),
)
LIGHT_DYNAMIC_FIELDS = (
    ("turnedOn", "bool", "light_turned_on", True),
    ("rangeAniScale", "string", "range_ani_scale", ""),
    ("rangeAniFPS", "float", "range_ani_fps", 0.0),
    ("rangeAniSmooth", "bool", "range_ani_smooth", True),
    ("colorAniList", "string", "color_ani_list", ""),
    ("colorAniFPS", "float", "color_ani_fps", 0.0),
    ("colorAniSmooth", "bool", "color_ani_smooth", True),
    ("canMove", "bool", "light_can_move", False),
)

# -- zones ------------------------------------------------------------------------------
MUSIC_ZONE_FIELDS = (
    ("enabled", "bool", "zone_enabled", True),
    ("priority", "int", "zone_priority", 1),
    ("ellipsoid", "bool", "zone_ellipsoid", False),
    ("reverbLevel", "float", "zone_reverb_level", -3.219),
    ("volumeLevel", "float", "zone_volume_level", 1.0),
    ("loop", "bool", "zone_loop", True),
)

FOG_ZONE_FIELDS = (
    ("fogRangeCenter", "float", "fog_range_center", 12000.0),
    ("innerRangePerc", "float", "inner_range_perc", 0.7),
    ("fogColor", "color", "fog_color", (120, 120, 120, 255)),
    ("fadeOutSky", "bool", "fog_fade_out_sky", False),
    ("overrideColor", "bool", "fog_override_color", False),
)

FAR_PLANE_ZONE_FIELDS = (
    ("vobFarPlaneZ", "float", "vob_far_plane_z", 12000.0),
    ("innerRangePerc", "float", "inner_range_perc", 0.7),
)

# -- triggers -----------------------------------------------------------------------------
# `flags` and `filterFlags` are one packed byte each in the archive; the
# exporter builds them from these keys (TRIGGER_FLAG_BITS / _FILTER_BITS).
TRIGGER_FLAG_BITS = (
    ("trigger_start_enabled", 0x01, True),
    ("trigger_send_untrigger", 0x04, True),
)
TRIGGER_IS_ENABLED_BIT = 0x02       # runtime state, written equal to startEnabled
TRIGGER_FILTER_BITS = (
    ("react_to_on_trigger", 0x01, True),
    ("react_to_on_touch", 0x02, True),
    ("react_to_on_damage", 0x04, False),
    ("respond_to_object", 0x08, False),
    ("respond_to_pc", 0x10, True),
    ("respond_to_npc", 0x20, False),
)

TRIGGER_FIELDS = (
    ("triggerTarget", "string", "trigger_target", ""),
    ("flags", "triggerFlags", None, None),
    ("filterFlags", "triggerFilter", None, None),
    ("respondToVobName", "string", "respond_to_vob_name", ""),
    ("numCanBeActivated", "int", "num_can_be_activated", -1),
    ("retriggerWaitSec", "float", "retrigger_wait_sec", 0.0),
    ("damageThreshold", "float", "damage_threshold", 0.0),
    ("fireDelaySec", "float", "fire_delay_sec", 0.0),
)

TRIGGER_SCRIPT_FIELDS = TRIGGER_FIELDS + (
    ("scriptFunc", "string", "script_func", ""),
)

TRIGGER_CHANGE_LEVEL_FIELDS = TRIGGER_FIELDS + (
    ("levelName", "string", "level_name", ""),
    ("startVobName", "string", "start_vob_name", ""),
)

LIST_SLOTS = 6      # engine limit for zCTriggerList targets and zCCodeMaster slaves

TRIGGER_LIST_FIELDS = TRIGGER_FIELDS + (
    ("listProcess", "enum", "list_process", "ALL"),
    ("numTarget", "triggerList", None, None),
)

MOVER_FIELDS = TRIGGER_FIELDS + (
    ("moverBehavior", "enum", "mover_behavior", "TOGGLE"),
    ("touchBlockerDamage", "float", "touch_blocker_damage", 0.0),
    ("stayOpenTimeSec", "float", "stay_open_time_sec", 2.0),
    ("moverLocked", "bool", "mover_locked", False),
    ("autoLinkEnabled", "bool", "auto_link_enabled", False),
    ("autoRotate", "bool", "auto_rotate", False),
    ("numKeyframes", "moverKeyframes", None, None),
    ("sfxOpenStart", "string", "sfx_open_start", ""),
    ("sfxOpenEnd", "string", "sfx_open_end", ""),
    ("sfxMoving", "string", "sfx_moving", ""),
    ("sfxCloseStart", "string", "sfx_close_start", ""),
    ("sfxCloseEnd", "string", "sfx_close_end", ""),
    ("sfxLock", "string", "sfx_lock", ""),
    ("sfxUnlock", "string", "sfx_unlock", ""),
    ("sfxUseLocked", "string", "sfx_use_locked", ""),
)
# Written between numKeyframes and the keyframes blob, only when there are
# keyframes (as the engine does).
MOVER_MOTION_FIELDS = (
    ("moveSpeed", "float", "move_speed", 0.3),
    ("posLerpType", "enum", "pos_lerp_type", "CURVE"),
    ("speedType", "enum", "speed_type", "SLOW_START_END"),
)
MOVER_KEY_PROPERTY = "zen_mover_key"     # custom property on a keyframe empty: its index

MESSAGE_FILTER_FIELDS = (
    ("triggerTarget", "string", "trigger_target", ""),
    ("onTrigger", "enum", "on_trigger", "TRIGGER"),
    ("onUntrigger", "enum", "on_untrigger", "UNTRIGGER"),
)

CODE_MASTER_FIELDS = (
    ("triggerTarget", "string", "trigger_target", ""),
    ("orderRelevant", "bool", "order_relevant", False),
    ("firstFalseIsFailure", "bool", "first_false_is_failure", False),
    ("triggerTargetFailure", "string", "trigger_target_failure", ""),
    ("untriggerCancels", "bool", "untrigger_cancels", False),
    ("numSlaves", "codeMasterSlaves", None, None),
)

WORLD_START_FIELDS = (
    ("triggerTarget", "string", "trigger_target", ""),
    ("fireOnlyFirstTime", "bool", "fire_only_first_time", True),
)

UNTOUCH_FIELDS = (
    ("triggerTarget", "string", "trigger_target", ""),
)

TOUCH_DAMAGE_FIELDS = (
    ("damage", "float", "touch_damage", 1000.0),
    ("Barrier", "bool", "damage_barrier", False),
    ("Blunt", "bool", "damage_blunt", False),
    ("Edge", "bool", "damage_edge", False),
    ("Fire", "bool", "damage_fire", False),
    ("Fly", "bool", "damage_fly", False),
    ("Magic", "bool", "damage_magic", False),
    ("Point", "bool", "damage_point", True),
    ("Fall", "bool", "damage_fall", False),
    ("damageRepeatDelaySec", "float", "damage_repeat_delay_sec", 2.0),
    ("damageVolDownScale", "float", "damage_vol_down_scale", 1.0),
    ("damageCollType", "enum", "damage_coll_type", "BOX"),
)

# -- effects ------------------------------------------------------------------------------
PFX_CONTROLER_FIELDS = (
    ("pfxName", "string", "pfx_name", ""),
    ("killVobWhenDone", "bool", "kill_vob_when_done", True),
    ("pfxStartOn", "bool", "pfx_start_on", True),
)

ANIMATE_FIELDS = (
    ("startOn", "bool", "animate_start_on", True),
)

LENS_FLARE_FIELDS = (
    ("lensflareFX", "string", "lensflare_fx", ""),
)

EARTHQUAKE_FIELDS = (
    ("radius", "float", "quake_radius", 1000.0),
    ("timeSec", "float", "quake_time_sec", 5.0),
    ("amplitudeCM", "vec3", "quake_amplitude", (2.0, 10.0, 2.0)),
)

ITEM_FIELDS = (
    ("itemInstance", "vobName", None, None),
)


# -- vob types ----------------------------------------------------------------------------

@dataclass(frozen=True)
class VobSpec:
    chain: str                       # "oCMobDoor:oCMobInter:oCMOB:zCVob"
    version: int                     # class version in the block header
    fields: tuple = ()
    # Where the `visual` string comes from:
    #   "none"   - no visual
    #   "name"   - the vob's own name + default_extension (props, level compo)
    #   "custom" - the visual_name custom property (blank = the vob's name),
    #              default_extension added when it has none
    #   "custom_only" - visual_name only; blank means no visual
    visual: str = "none"
    default_extension: str = ""
    # Volume the bbox describes: None (meshes, else a point), "box" (the
    # object's own cube: zones, triggers), or the custom key of a radius.
    volume: str = None
    flags: dict = _dc_field(default_factory=dict)   # BASE_FIELDS defaults by custom key
    defaults: dict = _dc_field(default_factory=dict)  # per-type field defaults by custom key
    order: int = 1                   # sort slot among siblings in the vob tree

    @property
    def type_name(self):
        return self.chain.split(":", 1)[0]


_PROP = {"show_visual": True, "cd_static": True, "cd_dyn": True, "static_vob": True}
_MOB = dict(_PROP)
_POINT = {"show_visual": True}                        # invisible helper vobs
_HELPER = {"show_visual": True, "zbias": 1}
_TOUCH = {"show_visual": True, "cd_dyn": True}        # cdDyn is what makes touch events fire


def _mob(type_name, version, fields=_INTER, **defaults):
    return VobSpec(f"{type_name}:oCMobInter:oCMOB:zCVob" if type_name != "oCMobInter"
                   else "oCMobInter:oCMOB:zCVob", version, fields, visual="custom",
                   default_extension=".MDS", flags=_MOB, defaults=defaults)


_SPECS = (
    VobSpec("zCVob", 52224, visual="custom", default_extension=".3DS", flags=_PROP),
    VobSpec("zCVobLevelCompo:zCVob", 52224, visual="name", default_extension=".3DS",
            flags={"show_visual": False}, order=0),
    VobSpec("zCVobSpot:zCVob", 52224, flags=_HELPER, order=3),
    # Spacer gives it the editor-only INVISIBLE_ZCVOBSTARTPOINT.3DS; it works without.
    VobSpec("zCVobStartpoint:zCVob", 52224, visual="custom_only", default_extension=".3DS",
            flags=_POINT),
    VobSpec("oCItem:zCVob", 0, ITEM_FIELDS,
            flags={"show_visual": False, "cd_static": True, "cd_dyn": True}, order=2),
    VobSpec("zCVobLight:zCVob", 39168, LIGHT_FIELDS + LIGHT_DYNAMIC_FIELDS, flags=_POINT),
    VobSpec("zCVobSound:zCVob", 12289, SOUND_FIELDS, volume="sound_radius",
            flags=_POINT, order=4),
    VobSpec("zCVobSoundDaytime:zCVobSound:zCVob", 12289, SOUND_DAYTIME_FIELDS,
            volume="sound_radius", flags={"show_visual": False}, order=4),

    VobSpec("oCMOB:zCVob", 47105, OCMOB_FIELDS, visual="custom", default_extension=".3DS",
            flags=_MOB),
    _mob("oCMobInter", 35585),
    _mob("oCMobContainer", 64513, _INTER + LOCKABLE_FIELDS + CONTAINER_FIELDS,
         focus_name="MOBNAME_CHEST"),
    _mob("oCMobDoor", 64513, _INTER + LOCKABLE_FIELDS, focus_name="MOBNAME_DOOR"),
    # A bed needs onStateFunc SLEEPABIT: the engine calls <onStateFunc>_S1
    # when it's used, and SLEEPABIT_S1 opens the sleep dialog.
    _mob("oCMobBed", 61440, focus_name="MOBNAME_BED", on_state_func="SLEEPABIT"),
    _mob("oCMobSwitch", 35585, focus_name="MOBNAME_SWITCH"),
    _mob("oCMobLadder", 35585),
    _mob("oCMobWheel", 35585, focus_name="MOBNAME_WHEEL"),
    _mob("oCMobFire", 18433, _INTER + FIRE_FIELDS),

    VobSpec("oCZoneMusic:zCVob", 0, MUSIC_ZONE_FIELDS, volume="box", flags=_POINT),
    VobSpec("oCZoneMusicDefault:oCZoneMusic:zCVob", 0, MUSIC_ZONE_FIELDS, flags=_HELPER,
            defaults={"zone_priority": 0}),
    VobSpec("zCZoneZFog:zCVob", 5505, FOG_ZONE_FIELDS, volume="box", flags=_POINT),
    VobSpec("zCZoneZFogDefault:zCZoneZFog:zCVob", 5505, FOG_ZONE_FIELDS, flags=_HELPER),
    VobSpec("zCZoneVobFarPlane:zCVob", 52224, FAR_PLANE_ZONE_FIELDS, volume="box",
            flags=_POINT),
    VobSpec("zCZoneVobFarPlaneDefault:zCZoneVobFarPlane:zCVob", 52224,
            FAR_PLANE_ZONE_FIELDS, flags=_HELPER),

    VobSpec("zCTrigger:zCVob", 47105, TRIGGER_FIELDS, volume="box", flags=_TOUCH),
    VobSpec("oCTriggerScript:zCTrigger:zCVob", 24577, TRIGGER_SCRIPT_FIELDS, volume="box",
            flags=_TOUCH),
    VobSpec("oCTriggerChangeLevel:zCTrigger:zCVob", 24577, TRIGGER_CHANGE_LEVEL_FIELDS,
            volume="box", flags=_TOUCH,
            defaults={"react_to_on_trigger": False, "trigger_send_untrigger": False}),
    VobSpec("zCTriggerList:zCTrigger:zCVob", 5505, TRIGGER_LIST_FIELDS, flags=_HELPER,
            defaults={"react_to_on_touch": False, "respond_to_object": True,
                      "trigger_send_untrigger": False}),
    VobSpec("zCMover:zCTrigger:zCVob", 39936, MOVER_FIELDS, visual="custom_only",
            default_extension=".3DS", flags=_TOUCH,
            defaults={"react_to_on_touch": False, "respond_to_object": True,
                      "respond_to_npc": True}),
    VobSpec("zCMessageFilter:zCVob", 0, MESSAGE_FILTER_FIELDS, flags=_HELPER),
    VobSpec("zCCodeMaster:zCVob", 0, CODE_MASTER_FIELDS, flags=_HELPER),
    VobSpec("zCTriggerWorldStart:zCVob", 52224, WORLD_START_FIELDS, flags=_HELPER),
    VobSpec("zCTriggerUntouch:zCVob", 193, UNTOUCH_FIELDS, volume="box", flags=_TOUCH),
    VobSpec("oCTouchDamage:zCTouchDamage:zCVob", 36865, TOUCH_DAMAGE_FIELDS, volume="box",
            flags=_TOUCH),

    VobSpec("zCPFXControler:zCVob", 52224, PFX_CONTROLER_FIELDS, flags=_POINT),
    VobSpec("zCVobAnimate:zCVob", 52224, ANIMATE_FIELDS, visual="custom",
            default_extension=".MMS", flags=_POINT),
    VobSpec("zCVobLensFlare:zCVob", 193, LENS_FLARE_FIELDS, flags=_HELPER),
    VobSpec("zCEarthquake:zCVob", 52224, EARTHQUAKE_FIELDS,
            flags={"show_visual": False, "static_vob": True, "zbias": 1}),
)

VOB_SPECS = {spec.type_name: spec for spec in _SPECS}

# Kept for callers that only want the type-specific fields.
FIELDS_BY_TYPE = {name: spec.fields for name, spec in VOB_SPECS.items() if spec.fields}

# The visual sub-block by file extension: (class, version, own object index?).
VISUAL_BLOCKS = {
    ".3DS": ("zCProgMeshProto", 53505),
    ".MDS": ("zCModel", 0),
    ".ASC": ("zCModel", 0),
    ".MMS": ("zCMorphMesh", 0),
    ".TGA": ("zCDecal", 53505),
    ".PFX": ("zCParticleFX", 0),
}


def visual_extension(visual):
    dot = visual.rfind(".")
    return visual[dot:].upper() if dot >= 0 else ""


def is_decal(visual):
    return visual_extension(visual) == ".TGA"


# -- field access ---------------------------------------------------------------------------

def spec_for(vob_type):
    return VOB_SPECS.get(vob_type)


def keyed_fields(vob_type):
    """Every (archive name, archive type, key, default) of a type that is
    backed by a custom property: its own fields, the trigger bits, list
    slots and - for visual types - the decal fields. Base fields excluded."""
    spec = VOB_SPECS.get(vob_type)
    if spec is None:
        return ()
    result = []
    for entry in spec.fields:
        archive_name, archive_type, key, default = entry
        if archive_type == "triggerFlags":
            result += [("flags", "bool", k, d) for k, _, d in TRIGGER_FLAG_BITS]
        elif archive_type == "triggerFilter":
            result += [("filterFlags", "bool", k, d) for k, _, d in TRIGGER_FILTER_BITS]
        elif archive_type == "triggerList":
            for i in range(LIST_SLOTS):
                result.append((f"triggerTarget{i}", "string", f"list_target_{i}", ""))
                result.append((f"fireDelay{i}", "float", f"list_delay_{i}", 0.0))
        elif archive_type == "codeMasterSlaves":
            result += [(f"slaveVobName{i}", "string", f"slave_{i}", "") for i in range(LIST_SLOTS)]
        elif archive_type == "moverKeyframes":
            result += list(MOVER_MOTION_FIELDS)
        elif key is not None:
            result.append(entry)
    if spec.visual in ("custom", "custom_only"):
        result.insert(0, ("visual", "string", "visual_name", ""))
    if vob_type == "zCVob":
        result += list(DECAL_FIELDS)
    return tuple(result)


def field_default(vob_type, key, generic_default):
    spec = VOB_SPECS.get(vob_type)
    if spec is None:
        return generic_default
    if key in spec.defaults:
        return spec.defaults[key]
    return generic_default


def base_default(vob_type, key):
    """Default of a BASE_FIELDS key for this type."""
    spec = VOB_SPECS.get(vob_type)
    for _, _, base_key, default in BASE_FIELDS:
        if base_key == key:
            return spec.flags.get(key, default) if spec else default
    raise KeyError(key)


def default_for(vob_type, key):
    """Default of any custom key (base or type-specific) for this type."""
    if key in BASE_KEYS:
        return base_default(vob_type, key)
    for _, _, field_key, default in keyed_fields(vob_type):
        if field_key == key:
            return field_default(vob_type, key, default)
    raise KeyError(key)


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


def format_float(value):
    """Floats as the archive wants them: no float noise, no exponent, and
    integers without a trailing '.0' (as Spacer writes them)."""
    value = round(float(value), 6) + 0.0
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return repr(value)


def _sequence(value, default):
    try:
        values = [float(v) for v in value]
    except (TypeError, ValueError):
        values = []
    return values if len(values) == len(default) else list(default)


def print_field(data_printer, archive_name, archive_type, value, default):
    """Write one property. Bad values (e.g. text in an int field) fall back
    to the default rather than failing the whole export."""
    p = data_printer
    if archive_type == "enum":
        p.print_enum_property(archive_name, _enum_ordinal(archive_name, value))
        return
    try:
        if archive_type == "int":
            p.print_int_property(archive_name, int(value))
        elif archive_type == "float":
            p.print_property(archive_name, "float", format_float(value))
        elif archive_type == "bool":
            p.print_bool_property(archive_name, bool(value))
        elif archive_type == "color":
            p.print_color_property(archive_name, " ".join(
                str(max(0, min(255, int(round(v))))) for v in _sequence(value, default)))
        elif archive_type == "vec3":
            p.print_vec3_property(archive_name, " ".join(
                format_float(v) for v in _sequence(value, default)))
        elif archive_type == "rawFloat":
            p.print_raw_float_property(archive_name, " ".join(
                format_float(v) for v in _sequence(value, default)) + " ")
        else:
            p.print_string_property(archive_name, str(value))
    except (TypeError, ValueError):
        print_field(p, archive_name, archive_type, default, default)


def print_fields(data_printer, fields, get_custom, vob_type=None):
    """Write plain `fields` in order. get_custom(key, default) reads one
    custom property; a missing one uses the (per-type) default."""
    for archive_name, archive_type, key, default in fields:
        default = field_default(vob_type, key, default)
        value = default if key is None else get_custom(key, default)
        print_field(data_printer, archive_name, archive_type, value, default)


def _truthy(raw):
    # Spacer writes a set bool as 1 or -1.
    return raw.strip() not in ("", "0")


def parse_value(archive_name, archive_type, raw, default):
    """One archive property string -> the custom-property value."""
    try:
        if archive_type == "int":
            return int(raw.strip())
        if archive_type == "float":
            return float(raw.strip())
        if archive_type == "bool":
            return _truthy(raw)
        if archive_type == "enum":
            names = ENUMS[archive_name]
            ordinal = int(raw.strip())
            return names[ordinal] if 0 <= ordinal < len(names) else default
        if archive_type == "color":
            values = [int(v) for v in raw.split()]
            return values if len(values) == 4 else list(default)
        if archive_type in ("vec3", "rawFloat"):
            values = [float(v) for v in raw.split()]
            return values if len(values) == len(default) else list(default)
    except ValueError:
        return list(default) if isinstance(default, tuple) else default
    return raw


def _bits_from_raw(raw, bits):
    try:
        byte = int(raw.strip()[:2], 16)
    except ValueError:
        return {}
    return {key: bool(byte & mask) for key, mask, _ in bits}


def custom_properties_from_block(vob_type, properties, visual_properties=None):
    """Inverse of the exporter for the importer: {custom key: value} from a
    parsed block's properties (strings), for every keyed field of
    `vob_type` present in the block. Base fields are only returned when
    they differ from the type's default, so objects stay uncluttered.
    visual_properties are those of the block's `visual` sub-block (decal
    settings). Unknown types give {}."""
    spec = VOB_SPECS.get(vob_type)
    if spec is None:
        return {}
    result = {}

    for archive_name, archive_type, key, default in BASE_FIELDS:
        if archive_name not in properties:
            continue
        value = parse_value(archive_name, archive_type, properties[archive_name], default)
        if value != base_default(vob_type, key):
            result[key] = value

    for archive_name, archive_type, key, default in spec.fields:
        if archive_type == "triggerFlags" and "flags" in properties:
            result.update(_bits_from_raw(properties["flags"], TRIGGER_FLAG_BITS))
        elif archive_type == "triggerFilter" and "filterFlags" in properties:
            result.update(_bits_from_raw(properties["filterFlags"], TRIGGER_FILTER_BITS))
        elif archive_type == "triggerList":
            for i in range(LIST_SLOTS):
                if f"triggerTarget{i}" in properties:
                    result[f"list_target_{i}"] = properties[f"triggerTarget{i}"]
                    result[f"list_delay_{i}"] = parse_value(
                        "", "float", properties.get(f"fireDelay{i}", "0"), 0.0)
        elif archive_type == "codeMasterSlaves":
            for i in range(LIST_SLOTS):
                if f"slaveVobName{i}" in properties:
                    result[f"slave_{i}"] = properties[f"slaveVobName{i}"]
        elif archive_type == "moverKeyframes":
            for name, type_, motion_key, motion_default in MOVER_MOTION_FIELDS:
                if name in properties:
                    result[motion_key] = parse_value(name, type_, properties[name], motion_default)
        elif key is not None and archive_name in properties:
            result[key] = parse_value(archive_name, archive_type, properties[archive_name], default)

    if visual_properties and is_decal(properties.get("visual", "")):
        for archive_name, archive_type, key, default in DECAL_FIELDS:
            if archive_name in visual_properties:
                result[key] = parse_value(
                    archive_name, archive_type, visual_properties[archive_name], default)
    return result
