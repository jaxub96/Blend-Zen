"""
How each vob setting is presented in the sidebar: label, tooltip, whether
it sits in the collapsed Advanced section, when it is relevant, and which
game-file list feeds its dropdown.

Pure data, no bpy and no zen_gin_export import, so it is testable outside
Blender; tests/test_vob_ui_schema.py checks every custom key of
zen_gin_export.vob_fields has an entry here and vice versa.

FIELD_UI[key] = (label, tooltip, options). options:
  adv     True = Advanced section (values that are the same on practically
          every vanilla vob)
  when    callable(value_of, vob_type) -> bool: show only when relevant
  source  game_data.GameIndex category, or "scene" for names of vobs in
          the scene, feeding the field's dropdown
"""

_SLOTS = 6


def _is(key, *values):
    return lambda v, t: v(key) in values


def _not(key, *values):
    return lambda v, t: v(key) not in values


def _on(key):
    return lambda v, t: bool(v(key))


def _extension(v):
    visual = str(v("visual_name") or "")
    return visual[visual.rfind("."):].upper() if "." in visual else ""


def _decal(v, t):
    return t == "zCVob" and _extension(v) == ".TGA"


def _dynamic_light(v, t):
    return not v("light_static")


def _slot_visible(prefix, index):
    """A list slot shows when it or the one before it is filled."""
    def visible(v, t):
        return index == 0 or bool(str(v(f"{prefix}{index}") or "").strip()) \
            or bool(str(v(f"{prefix}{index - 1}") or "").strip())
    return visible


FIELD_UI = {
    # -- every vob ----------------------------------------------------------
    "visual_name": ("Visual", "The game file shown for this vob: a mesh (.3DS), an animated model "
                    "(.MDS / .ASC), a morph mesh (.MMS), a decal texture (.TGA) or a particle "
                    "effect (.PFX). Must exist in the game - Spacer crashes on a missing mob model",
                    {"source": "visual"}),
    "cd_dyn": ("Collision", "Blocks the player, NPCs and other moving objects (cdDyn)", {}),
    "cd_static": ("Collide With World", "Collides with the level mesh when it moves (cdStatic)", {}),
    "static_vob": ("Static", "Never moves: included in the static light bake (staticVob)", {"adv": True}),
    "show_visual": ("Show Visual", "Draw the vob's visual in-game", {"adv": True}),
    "ani_mode": ("Wind Sway", "Sway in the wind, for plants and trees (visualAniMode)", {}),
    "ani_strength": ("Sway Strength", "How far it sways; vanilla uses 0.001 to 0.01",
                     {"when": _not("ani_mode", "NONE")}),
    "cam_align": ("Face Camera", "Billboard: turn towards the camera (visualCamAlign). "
                  "Flares and smoke decals use YAW or FULL", {"adv": True}),
    "far_clip_scale": ("Far Clip Scale", "Multiplies the distance at which this vob is "
                       "culled (vobFarClipZScale)", {"adv": True}),
    "dyn_shadow": ("Dynamic Shadow", "Blob shadow under the vob (dynShadow)", {"adv": True}),
    "zbias": ("Z Bias", "Depth offset against z-fighting (zbias)", {"adv": True}),
    "is_ambient": ("Ambient", "Marks the vob as ambient decoration (isAmbient)", {"adv": True}),
    "preset_name": ("Vob Preset", "Spacer preset this vob was made from (presetName); "
                    "informational", {"adv": True}),

    # -- decals ---------------------------------------------------------------
    "decal_dim": ("Size", "Half width and half height of the decal in cm", {"when": _decal}),
    "decal_offset": ("Offset", "Offset of the texture on the decal in cm", {"when": _decal, "adv": True}),
    "decal_two_sided": ("Two Sided", "Visible from both sides", {"when": _decal}),
    "decal_alpha_func": ("Blending", "How the texture is blended: BLEND uses its alpha "
                         "channel, ADD brightens (fire, flares)", {"when": _decal}),
    "decal_tex_ani_fps": ("Animation FPS", "Speed of an animated texture (NAME_A0, _A1, ...); "
                          "0 for a still one", {"when": _decal}),
    "decal_alpha_weight": ("Opacity", "0 (invisible) to 255 (opaque)", {"when": _decal}),
    "decal_ignore_daylight": ("Ignore Daylight", "Keep full brightness at night (fire, flares)",
                              {"when": _decal}),

    # -- oCMOB ------------------------------------------------------------------
    "focus_name": ("Focus Name", "Name shown when the player looks at it. Must be a script string "
                   "constant such as MOBNAME_CHEST (Text.d): plain text shows nothing in-game",
                   {"source": "focus_names"}),
    "hitpoints": ("Hitpoints", "Vanilla worlds use 10 everywhere", {"adv": True}),
    "damage": ("Damage", "Damage dealt by the object (unused by vanilla mobs)", {"adv": True}),
    "moveable": ("Moveable", "Can be pushed around", {"adv": True}),
    "takeable": ("Takeable", "Can be picked up", {"adv": True}),
    "focus_override": ("Focus Override", "Take the focus even when other objects are closer",
                       {"adv": True}),
    "sound_material": ("Sound Material", "Impact sound when it is hit", {"adv": True}),
    "visual_destroyed": ("Destroyed Visual", "Visual shown after the object is destroyed",
                         {"adv": True, "source": "meshes"}),
    "owner": ("Owner", "NPC instance that owns it: using it in sight of the owner is theft",
              {"source": "npcs"}),
    "owner_guild": ("Owner Guild", "Guild that owns it, e.g. GIL_MIL", {"source": "guilds"}),
    "state_num": ("States", "Number of states of the model's script; 1 for nearly "
                  "everything", {"adv": True}),
    "trigger_target": ("Trigger Target", "Vob name of the vob that is triggered (a mover, "
                       "a trigger list, a script trigger...)", {"source": "scene"}),
    "use_with_item": ("Needs Item", "Item instance the player must carry to use it, "
                      "e.g. ITMI_FLASK for an alchemy table", {"source": "items"}),
    "condition_func": ("Condition Function", "Script function that decides whether it can "
                       "be used", {"adv": True}),
    "on_state_func": ("Script Function", "Called as <name>_S1 when it is used, e.g. SLEEPABIT "
                      "(sleep dialog), POTIONALCHEMY, MAKERUNE", {"source": "mob_functions"}),
    "rewind": ("Rewind", "Fire the trigger on every use instead of only the first",
               {"adv": True}),
    "locked": ("Locked", "Needs a key and/or a picklock combination to open", {}),
    "key_instance": ("Key", "Item instance of the key that opens it",
                     {"when": _on("locked"), "source": "keys"}),
    "picklock_str": ("Picklock", "Left/right sequence, e.g. LRRLR. Empty = cannot "
                     "be picked", {"when": _on("locked")}),
    "contains": ("Contains", "Comma-separated ITEM:count list, e.g. ItMi_Gold:35,ItFo_Apple",
                 {}),
    "fire_slot": ("Fire Bone", "Bone of the model the fire is attached to", {"adv": True}),
    "fire_vobtree_name": ("Fire Effect", "Vob tree placed at the fire bone when lit",
                          {"source": "vob_trees"}),

    # -- sounds -------------------------------------------------------------------
    "sound_name": ("Sound", "Sound instance (SfxInst.d). Blank = the vob's own name",
                   {"source": "sfx"}),
    "sound_volume": ("Volume", "0 to 100", {}),
    "sound_radius": ("Radius", "Distance in cm at which it becomes inaudible", {}),
    "sound_mode": ("Mode", "LOOP plays continuously, ONCE a single time, RANDOM repeats "
                   "after a random pause", {}),
    "sound_random_delay": ("Random Delay", "Average pause in seconds between repeats",
                           {"when": _is("sound_mode", "RANDOM")}),
    "sound_random_delay_var": ("Delay Variation", "Random +/- seconds added to the pause",
                               {"when": _is("sound_mode", "RANDOM")}),
    "sound_start_on": ("Start Playing", "Plays from the start; off = waits for a trigger", {}),
    "sound_ambient_3d": ("Ambient 3D", "Diffuse surround sound without a clear direction", {}),
    "sound_obstruction": ("Obstruction", "Muffled behind walls", {}),
    "sound_cone_angle": ("Cone Angle", "Directional sound cone in degrees; 0 = all "
                         "directions", {"adv": True}),
    "sound_vol_type": ("Volume Shape", "Sphere, or an ellipsoid flattened in height",
                       {"adv": True}),
    "sound_start_time": ("Start Hour", "Hour of day (0-24) from which Sound plays", {}),
    "sound_end_time": ("End Hour", "Hour of day (0-24) from which Night Sound plays", {}),
    "sound_name_2": ("Night Sound", "Sound instance played outside Start-End Hour",
                     {"source": "sfx"}),

    # -- lights -------------------------------------------------------------------
    "light_preset": ("Preset", "Light preset (Presets/LightPresets.zen). Picking one from "
                     "the list applies its range, colour and flicker", {"source": "light_presets"}),
    "light_static": ("Static", "Baked into the level's lightmaps when the world is compiled; "
                     "off = a dynamic light that can flicker", {}),
    "light_quality": ("Quality", "Lighting precision: LOW is the usual choice", {}),
    "lensflare_fx": ("Lensflare", "Lensflare effect, e.g. TORCHFX01", {"adv": True, "source": "lensflares"}),
    "light_turned_on": ("Turned On", "Lit from the start", {"when": _dynamic_light}),
    "range_ani_scale": ("Range Flicker", "Range multipliers cycled through, e.g. "
                        "'1.0 0.9 1.1'. Blank = steady", {"when": _dynamic_light}),
    "range_ani_fps": ("Range Flicker FPS", "Steps per second", {"when": _dynamic_light}),
    "range_ani_smooth": ("Smooth Range", "Blend between the steps", {"when": _dynamic_light, "adv": True}),
    "color_ani_list": ("Colour Flicker", "Colours cycled through, e.g. "
                       "'(255 80 0) (200 50 0)'. Blank = steady", {"when": _dynamic_light}),
    "color_ani_fps": ("Colour Flicker FPS", "Steps per second", {"when": _dynamic_light}),
    "color_ani_smooth": ("Smooth Colour", "Blend between the steps", {"when": _dynamic_light, "adv": True}),
    "light_can_move": ("Can Move", "The light is moved at runtime", {"when": _dynamic_light, "adv": True}),

    # -- zones --------------------------------------------------------------------
    "zone_enabled": ("Enabled", "The zone is active", {"adv": True}),
    "zone_priority": ("Priority", "Where zones overlap, the higher priority wins", {}),
    "zone_ellipsoid": ("Ellipsoid", "Zone is an ellipsoid inside the box", {"adv": True}),
    "zone_reverb_level": ("Reverb Level", "Reverb in dB", {"adv": True}),
    "zone_volume_level": ("Volume", "Music volume, 0 to 1", {"adv": True}),
    "zone_loop": ("Loop", "Loop the theme", {"adv": True}),
    "fog_range_center": ("Fog Range", "Distance in cm at which the fog is solid", {}),
    "inner_range_perc": ("Inner Range", "Fraction of the box (0-1) inside which the zone "
                         "is at full strength", {}),
    "fog_color": ("Fog Colour", "Used when Override Colour is on", {}),
    "fog_fade_out_sky": ("Fade Out Sky", "Fade the sky into the fog colour", {}),
    "fog_override_color": ("Override Colour", "Use Fog Colour instead of the sky's", {}),
    "vob_far_plane_z": ("View Distance", "Distance in cm beyond which vobs are not drawn", {}),

    # -- triggers -----------------------------------------------------------------
    "trigger_start_enabled": ("Start Enabled", "Reacts from the start", {}),
    "trigger_send_untrigger": ("Send Untrigger", "Also pass on the untrigger event (the "
                               "player leaving the box)", {"adv": True}),
    "react_to_on_trigger": ("React To Trigger", "Fires when another vob triggers it", {}),
    "react_to_on_touch": ("React To Touch", "Fires when something enters its box", {}),
    "react_to_on_damage": ("React To Damage", "Fires when it is hit", {"adv": True}),
    "respond_to_object": ("Respond To Objects", "Vobs (other triggers, movers) can set it off", {"adv": True}),
    "respond_to_pc": ("Respond To Player", "The player can set it off", {}),
    "respond_to_npc": ("Respond To NPCs", "NPCs can set it off", {}),
    "respond_to_vob_name": ("Only Respond To", "Vob name of the only vob that can set it "
                            "off", {"adv": True, "source": "scene"}),
    "num_can_be_activated": ("Max Activations", "How often it fires; -1 = unlimited", {}),
    "retrigger_wait_sec": ("Retrigger Wait", "Seconds before it can fire again", {"adv": True}),
    "damage_threshold": ("Damage Threshold", "Minimum damage for React To Damage",
                         {"adv": True, "when": _on("react_to_on_damage")}),
    "fire_delay_sec": ("Fire Delay", "Seconds between the event and firing", {"adv": True}),
    "script_func": ("Script Function", "Daedalus function that is called, e.g. "
                    "EVT_MYTRIGGER_FUNC", {"source": "event_functions"}),
    "level_name": ("Level", "World to load, relative to Worlds, e.g. "
                   "NEWWORLD\\NEWWORLD.ZEN", {"source": "worlds"}),
    "start_vob_name": ("Arrive At", "Vob name of the startpoint or waypoint the player "
                       "arrives at in that world", {}),
    "list_process": ("Fire", "ALL targets at once, the NEXT one each time, or a RANDOM one", {}),
    "mover_behavior": ("Behaviour", "TOGGLE flips open/closed on each trigger; "
                       "TRIGGER_CONTROL opens on trigger and closes on untrigger; OPEN_TIMED "
                       "closes by itself; LOOP cycles all keyframes; SINGLE_KEYS moves key by key", {}),
    "touch_blocker_damage": ("Blocker Damage", "Damage to whatever blocks the mover", {"adv": True}),
    "stay_open_time_sec": ("Stay Open", "Seconds it stays open",
                           {"when": _is("mover_behavior", "OPEN_TIMED")}),
    "mover_locked": ("Locked", "Cannot be moved until unlocked by script", {"adv": True}),
    "auto_link_enabled": ("Auto Link", "Things standing on it move along (lifts)", {}),
    "auto_rotate": ("Auto Rotate", "Turn into the direction of travel", {"adv": True}),
    "move_speed": ("Speed", "Movement speed in cm per millisecond; doors and gates "
                   "use about 0.05 to 0.3", {}),
    "pos_lerp_type": ("Path", "Straight lines or a curve through the keyframes", {}),
    "speed_type": ("Easing", "Constant speed or slowing at the start/end", {}),
    "sfx_open_start": ("Open Start SFX", "Sound when it starts to open", {"source": "sfx"}),
    "sfx_open_end": ("Open End SFX", "Sound when it is fully open", {"source": "sfx"}),
    "sfx_moving": ("Moving SFX", "Looped while it moves", {"source": "sfx"}),
    "sfx_close_start": ("Close Start SFX", "Sound when it starts to close", {"source": "sfx"}),
    "sfx_close_end": ("Close End SFX", "Sound when it is fully closed", {"source": "sfx"}),
    "sfx_lock": ("Lock SFX", "Sound when it is locked", {"adv": True, "source": "sfx"}),
    "sfx_unlock": ("Unlock SFX", "Sound when it is unlocked", {"adv": True, "source": "sfx"}),
    "sfx_use_locked": ("Use Locked SFX", "Sound when it is used while locked", {"adv": True, "source": "sfx"}),
    "on_trigger": ("On Trigger Send", "Message passed on when it is triggered", {}),
    "on_untrigger": ("On Untrigger Send", "Message passed on when it is untriggered", {}),
    "order_relevant": ("Order Matters", "The slaves must fire in slot order", {}),
    "first_false_is_failure": ("First Mistake Fails", "A wrong slave fails the code at once", {}),
    "trigger_target_failure": ("Failure Target", "Vob triggered when the code fails",
                               {"source": "scene"}),
    "untrigger_cancels": ("Untrigger Cancels", "An untrigger from a slave takes it back", {"adv": True}),
    "fire_only_first_time": ("Only First Time", "Fire only the first time the world is "
                             "entered", {}),
    "touch_damage": ("Damage", "Damage per hit", {}),
    "damage_barrier": ("Barrier", "Damage type", {"adv": True}),
    "damage_blunt": ("Blunt", "Damage type", {}),
    "damage_edge": ("Edge", "Damage type", {}),
    "damage_fire": ("Fire", "Damage type", {}),
    "damage_fly": ("Fly", "Damage type: knocks the victim away", {}),
    "damage_magic": ("Magic", "Damage type", {}),
    "damage_point": ("Point", "Damage type", {}),
    "damage_fall": ("Fall", "Damage type", {"adv": True}),
    "damage_repeat_delay_sec": ("Repeat Delay", "Seconds between hits while touching", {}),
    "damage_vol_down_scale": ("Volume Scale", "Shrinks the damaging box (0-1)", {"adv": True}),
    "damage_coll_type": ("Collision Shape", "Test against the box or the vob's centre", {"adv": True}),

    # -- effects ------------------------------------------------------------------
    "pfx_name": ("Effect", "Particle effect that is started (PfxInst.d)", {"source": "pfx"}),
    "kill_vob_when_done": ("Remove When Done", "Delete the vob after the effect ended", {}),
    "pfx_start_on": ("Start Playing", "Plays from the start; off = waits for a trigger", {}),
    "animate_start_on": ("Start Playing", "Animates from the start; off = waits for a trigger", {}),
    "quake_radius": ("Radius", "Radius in cm in which the screen shakes", {}),
    "quake_time_sec": ("Duration", "Seconds", {}),
    "quake_amplitude": ("Amplitude", "Shake strength in cm per axis", {}),
}

for _i in range(_SLOTS):
    FIELD_UI[f"list_target_{_i}"] = (
        f"Target {_i + 1}", "Vob name of a vob this list triggers",
        {"source": "scene", "when": _slot_visible("list_target_", _i)})
    FIELD_UI[f"list_delay_{_i}"] = (
        f"Delay {_i + 1}", "Seconds before this target is triggered",
        {"when": lambda v, t, i=_i: bool(str(v(f"list_target_{i}") or "").strip())})
    FIELD_UI[f"slave_{_i}"] = (
        f"Slave {_i + 1}", "Vob name of a vob that must trigger this code master",
        {"source": "scene", "when": _slot_visible("slave_", _i)})

# Base settings shown in the main section (not Advanced) for these types.
MAIN_BASE_KEYS = {
    "zCVob": ("cd_dyn", "cd_static", "ani_mode", "ani_strength"),
    "zCMover": ("cd_dyn",),
    "oCMOB": ("cd_dyn", "cd_static"),
}
for _mob in ("oCMobInter", "oCMobContainer", "oCMobDoor", "oCMobBed", "oCMobSwitch",
             "oCMobLadder", "oCMobWheel", "oCMobFire"):
    MAIN_BASE_KEYS[_mob] = ("cd_dyn", "cd_static")

# Fields vanilla does use now and then, but that a typical vob of the class
# leaves alone; shown under Advanced like the never-used ones.
RARELY_USED = {
    # A mover is the end of a chain (lever -> gate); its own target is only
    # for chaining a further vob off it (6% of vanilla movers).
    "zCMover": frozenset({"trigger_target"}),
}

ENUM_LABELS = {
    "GLAS": "Glass", "MAT_DEFAULT": "Material Default", "MUL2": "Multiply x2", "MUL": "Multiply",
    "SUB": "Subtract", "YAW": "Yaw Only", "FULL": "Fully", "WIND2": "Wind (strong)",
    "TOGGLE_ENABLED": "Toggle Enabled", "NEXT_ONE": "Next One", "RAND_ONE": "Random One",
    "TRIGGER_CONTROL": "Trigger Control", "OPEN_TIMED": "Open Timed", "SINGLE_KEYS": "Single Keys",
    "SLOW_START_END": "Slow Start + End", "SLOW_START": "Slow Start", "SLOW_END": "Slow End",
    "SEG_SLOW_START_END": "Per Segment: Slow Start + End", "SEG_SLOW_START": "Per Segment: Slow Start",
    "SEG_SLOW_END": "Per Segment: Slow End", "CONST": "Constant",
}


def enum_label(identifier):
    return ENUM_LABELS.get(identifier, identifier.replace("_", " ").title())


# -- vob types --------------------------------------------------------------------
# id -> (menu label, tooltip, empty display type, display size, default name
# label, default box half-size in metres or None). Ids are vob types; an
# "@KIND" suffix is a ready-made zCVob variant. zCVob props and oCItem are
# not offered in Add VOB: they are dragged in from the asset libraries.
VOB_TYPE_INFO = {
    "zCVobLevelCompo": ("Level Compo (World Mesh Ref)", "Reference to the level mesh - the name "
                        "must match the .3DS filename, without extension", 'PLAIN_AXES', 1.0, "LEVEL", None),
    "zCVobStartpoint": ("Startpoint", "Where the player starts", 'PLAIN_AXES', 2.0, "PC_START", None),
    "zCVobSpot": ("Freepoint", "Spot NPCs use in their routines; the name prefix says for "
                  "what (FP_STAND_, FP_ROAM_, FP_SIT_, FP_ITEM_...)", 'ARROWS', 1.2, "FP_STAND", None),
    "zCVobLight": ("Light", "Point or spot light, created as a real Blender light", 'CONE', 0.3, "LIGHT", None),
    "zCVobSound": ("Sound", "Ambient sound emitter", 'SPHERE', 1.0, "SOUND", None),
    "zCVobSoundDaytime": ("Sound: Day / Night", "Plays one sound by day and another at night",
                          'SPHERE', 1.0, "SOUND_DAY", None),
    "zCVob@PFX": ("Particle Effect", "Fire, smoke, fog, sparks... (a zCVob with a .PFX visual)",
                  'SPHERE', 0.3, "PFX", None),
    "zCVob@DECAL": ("Decal", "A flat textured quad: flares, cobwebs, flames (a zCVob with a "
                    ".TGA visual)", 'IMAGE', 0.5, "DECAL", None),
    "zCVobAnimate": ("Animated Mesh", "A morph mesh that plays its animation (flags, water plants)",
                     'SPHERE', 0.5, "ANIMATE", None),
    "zCVobLensFlare": ("Lens Flare", "A lensflare effect", 'SPHERE', 0.2, "FLARE", None),

    "oCMobContainer": ("Interactive: Container", "Chest with contents, lock and key", 'CUBE', 0.5, "CHEST", None),
    "oCMobDoor": ("Interactive: Door", "A door, optionally locked", 'CUBE', 0.4, "DOOR", None),
    "oCMobBed": ("Interactive: Bed", "A bed the player can sleep in", 'CUBE', 0.6, "BED", None),
    "oCMobSwitch": ("Interactive: Switch", "Lever, button or touch plate that triggers "
                    "another vob", 'CONE', 0.25, "SWITCH", None),
    "oCMobLadder": ("Interactive: Ladder", "A climbable ladder", 'PLAIN_AXES', 1.5, "LADDER", None),
    "oCMobWheel": ("Interactive: Wheel", "A winch that triggers another vob", 'CIRCLE', 0.5, "WHEEL", None),
    "oCMobFire": ("Interactive: Fire", "Torch holder or fireplace that can be lit", 'SPHERE', 0.3, "FIRE", None),
    "oCMobInter": ("Interactive: Generic", "Anything usable: alchemy table, anvil, bench, "
                   "bookstand...", 'CUBE', 0.4, "INTERACTIVE", None),
    "oCMOB": ("Focusable Object", "A static object with a name the player can focus: "
              "signs, gravestones", 'CUBE', 0.4, "SIGN", None),

    "oCZoneMusic": ("Zone: Music", "Box in which a music theme plays", 'CUBE', 1.0, "ZONE", 10.0),
    "oCZoneMusicDefault": ("Zone: Default Music", "Music everywhere outside music zones "
                           "(one per world)", 'SPHERE', 1.0, "DEFAULT", None),
    "zCZoneZFog": ("Zone: Fog", "Box with its own fog", 'CUBE', 1.0, "FOG", 10.0),
    "zCZoneZFogDefault": ("Zone: Default Fog", "Fog everywhere outside fog zones (one per "
                          "world)", 'SPHERE', 1.0, "FOG_DEFAULT", None),
    "zCZoneVobFarPlane": ("Zone: View Distance", "Box with its own vob view distance", 'CUBE', 1.0, "FARPLANE", 10.0),
    "zCZoneVobFarPlaneDefault": ("Zone: Default View Distance", "Vob view distance everywhere "
                                 "else (one per world)", 'SPHERE', 1.0, "FARPLANE_DEFAULT", None),

    "oCTriggerScript": ("Trigger: Script", "Calls a script function when the player enters "
                        "the box or another vob triggers it", 'CUBE', 1.0, "EVT_SCRIPT", 2.0),
    "zCTrigger": ("Trigger", "Triggers another vob when touched or triggered", 'CUBE', 1.0, "EVT_TRIGGER", 2.0),
    "oCTriggerChangeLevel": ("Trigger: Change Level", "Loads another world when the player "
                             "enters the box", 'CUBE', 1.0, "EVT_LEVELCHANGE", 2.0),
    "zCTriggerList": ("Trigger: List", "Triggers up to 6 vobs, with delays", 'SINGLE_ARROW', 1.0, "EVT_LIST", None),
    "zCMover": ("Mover", "A mesh that moves between keyframes when triggered: gates, "
                "secret doors, lifts", 'CUBE', 0.5, "EVT_MOVER", None),
    "zCMessageFilter": ("Trigger: Message Filter", "Turns a trigger/untrigger into another "
                        "message (enable, disable, toggle...)", 'SINGLE_ARROW', 1.0, "EVT_FILTER", None),
    "zCCodeMaster": ("Trigger: Code Master", "Fires when all its slaves have triggered it "
                     "(combination puzzles)", 'SINGLE_ARROW', 1.0, "EVT_CODEMASTER", None),
    "zCTriggerWorldStart": ("Trigger: World Start", "Triggers a vob when the world is loaded",
                            'SINGLE_ARROW', 1.0, "EVT_WORLDSTART", None),
    "zCTriggerUntouch": ("Trigger: Untouch", "Triggers a vob when something leaves the box",
                         'CUBE', 1.0, "EVT_UNTOUCH", 2.0),
    "oCTouchDamage": ("Touch Damage", "Box that hurts whatever touches it: spikes, lava",
                      'CUBE', 1.0, "DAMAGE", 2.0),
    "zCPFXControler": ("Particle Effect Trigger", "Starts a particle effect when triggered",
                       'SPHERE', 0.3, "EVT_PFX", None),
    "zCEarthquake": ("Earthquake", "Shakes the screen when triggered", 'SPHERE', 1.0, "EVT_QUAKE", None),
}

# Types only reachable by import or asset drag (shown in the sidebar, not in Add VOB).
VOB_TYPE_INFO_HIDDEN = {
    "zCVob": ("Prop", "", 'SPHERE', 0.5, "PROP", None),
    "oCItem": ("Item", "", 'CUBE', 0.3, "ITEM", None),
}

VARIANT_VISUALS = {"PFX": "FIRE.PFX", "DECAL": "ZFLARE6.TGA"}


def type_info(vob_type_id):
    return VOB_TYPE_INFO.get(vob_type_id) or VOB_TYPE_INFO_HIDDEN.get(vob_type_id)


def split_type_id(vob_type_id):
    """'zCVob@PFX' -> ('zCVob', 'PFX'); 'zCVobSpot' -> ('zCVobSpot', None)."""
    vob_type, _, variant = vob_type_id.partition("@")
    return vob_type, variant or None


# Vob names that something refers to by name must be unique.
NAMED_TARGET_TYPES = (
    "zCMover", "zCTrigger", "oCTriggerScript", "oCTriggerChangeLevel", "zCTriggerList",
    "zCMessageFilter", "zCCodeMaster", "zCPFXControler", "zCEarthquake", "zCVobSound",
    "zCVobSoundDaytime", "zCVobLight", "zCVobAnimate", "oCMobSwitch", "oCMobWheel",
    "oCMobInter", "oCMobDoor", "oCMobContainer", "oCMobFire",
)
