"""
Pre-export scene checks: things the writer would silently skip or that
Spacer/the game would trip over. Returns human-readable warnings; never
blocks the export. Pure Python (reads name/type/data.type only).
"""

import re
from collections import Counter

from .zen_gin_ocvobtree import VOB_CLASSES
from .zen_gin_zcvob import vob_name_from_object_name, mover_keyframe_objects
from .zen_gin_waynet import WAYPOINT_PREFIX
from .vob_fields import field_default, keyed_fields

# Looks like a ZenGin class name (zCSomething / oCSomething).
_CLASS_LIKE_RE = re.compile(r"^[zo]C[A-Za-z]+$")

# Types whose vobName is an identity that something else refers to by name
# (routines, triggers, the start position) - duplicates are a bug. Props
# and items legitimately repeat.
_UNIQUE_NAME_TYPES = {"zCVobSpot", "zCVobStartpoint"} | {
    t for t in VOB_CLASSES if t.startswith("oCMob") or "Trigger" in t
} | {"zCMover", "zCMessageFilter", "zCCodeMaster"}

# Custom keys that hold the vob name of another vob.
_TARGET_KEYS = ("trigger_target", "trigger_target_failure") + tuple(
    f"{prefix}{i}" for prefix in ("list_target_", "slave_") for i in range(6))
# Vanilla worlds use these as "no target".
_NO_TARGET = ("", "NULL")


def _limited(names, limit=5):
    shown = ", ".join(sorted(names)[:limit])
    return shown + (f" (+{len(names) - limit} more)" if len(names) > limit else "")


def scene_warnings(blender_objects):
    warnings = []
    unknown = []
    identities = Counter()
    has_level_compo = False
    point_lights = []
    no_visual, unopenable, no_sleep = [], [], []
    all_names = set()
    targets = []            # (object name, target vob name)
    bad_music, no_effect, static_movers = [], [], []

    for obj in blender_objects:
        prefix, sep, _ = obj.name.partition(":")
        if not sep:
            continue
        if obj.name.startswith(WAYPOINT_PREFIX):
            continue
        if prefix not in VOB_CLASSES:
            if _CLASS_LIKE_RE.match(prefix):
                unknown.append(obj.name)
            continue
        if prefix == "zCVobLevelCompo":
            has_level_compo = True
        get = getattr(obj, "get", lambda key, default=None: default)
        vob_name = vob_name_from_object_name(obj.name)
        all_names.add(vob_name.upper())
        type_keys = {key for _, _, key, _ in keyed_fields(prefix)}
        for key in _TARGET_KEYS:
            if key in type_keys:
                target = str(get(key, "") or "").strip()
                if target.upper() not in _NO_TARGET:
                    targets.append((obj.name, target))
        if prefix in ("oCZoneMusic", "oCZoneMusicDefault") and not vob_name.partition("_")[2]:
            bad_music.append(obj.name)
        if prefix == "zCVob" and str(get("visual_name", "")).strip().upper() in (".PFX", ".TGA"):
            no_effect.append(obj.name)
        if prefix == "zCPFXControler" and not str(get("pfx_name", "")).strip() and not vob_name:
            no_effect.append(obj.name)
        if prefix == "zCMover" and len(mover_keyframe_objects(obj)) == 1:
            static_movers.append(obj.name)
        if prefix in _UNIQUE_NAME_TYPES:
            name = vob_name_from_object_name(obj.name)
            if name:  # unnamed mobs are common (vanilla worlds) and fine
                identities[(prefix, name)] += 1
        if prefix.startswith("oCMob"):
            if not str(get("visual_name", "")).strip():
                no_visual.append(obj.name)
            if (prefix in ("oCMobContainer", "oCMobDoor") and get("locked", False)
                    and not str(get("key_instance", "")).strip()
                    and not str(get("picklock_str", "")).strip()):
                unopenable.append(obj.name)
            if prefix == "oCMobBed" and not str(
                    get("on_state_func", field_default(prefix, "on_state_func", ""))).strip():
                no_sleep.append(obj.name)
        if prefix == "zCVobLight" and getattr(obj, "type", None) == "LIGHT":
            if obj.data.type in ("SUN", "AREA"):
                point_lights.append(obj.name)

    if unknown:
        warnings.append(f"Not exported, unknown vob type: {_limited(unknown)}")
    duplicates = [f"{t}:{n}" for (t, n), count in identities.items() if count > 1]
    if duplicates:
        warnings.append(f"Duplicate names (must be unique): {_limited(duplicates)}")
    if no_visual:
        warnings.append("No Visual, model falls back to <name>.MDS (Spacer crashes "
                        f"loading a mob whose model doesn't exist): {_limited(no_visual)}")
    if unopenable:
        warnings.append("Locked with no Key Instance or Picklock Str, can never be "
                        f"opened: {_limited(unopenable)}")
    if no_sleep:
        warnings.append(f"Bed without On State Func SLEEPABIT, no sleep dialog: {_limited(no_sleep)}")
    missing = sorted({f"{name} -> {target}" for name, target in targets
                      if target.upper() not in all_names})
    if missing:
        warnings.append(f"Trigger target is not the name of any vob: {_limited(missing)}")
    if bad_music:
        warnings.append("Music zone name must be <PLACE>_<THEME> (e.g. CAMP_XAR), no music "
                        f"plays: {_limited(bad_music)}")
    if no_effect:
        warnings.append(f"No effect/texture chosen: {_limited(no_effect)}")
    if static_movers:
        warnings.append(f"Mover with a single keyframe never moves: {_limited(static_movers)}")
    if point_lights:
        warnings.append(f"Sun/area lights exported as point lights: {_limited(point_lights)}")
    if not has_level_compo:
        warnings.append("No zCVobLevelCompo: Spacer has no level mesh to compile")
    return warnings
