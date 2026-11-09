"""
Pre-export scene checks: things the writer would silently skip or that
Spacer/the game would trip over. Returns human-readable warnings; never
blocks the export. Pure Python (reads name/type/data.type only).
"""

import re
from collections import Counter

from .zen_gin_ocvobtree import VOB_CLASSES
from .zen_gin_zcvob import vob_name_from_object_name
from .zen_gin_waynet import WAYPOINT_PREFIX
from .vob_fields import field_default

# Looks like a ZenGin class name (zCSomething / oCSomething).
_CLASS_LIKE_RE = re.compile(r"^[zo]C[A-Za-z]+$")

# Types whose vobName is an identity that something else refers to by name
# (routines, triggers, the start position) - duplicates are a bug. Props
# and items legitimately repeat.
_UNIQUE_NAME_TYPES = {"zCVobSpot", "zCVobStartpoint"} | {
    t for t in VOB_CLASSES if t.startswith("oCMob")
}


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
        if prefix in _UNIQUE_NAME_TYPES:
            name = vob_name_from_object_name(obj.name)
            if name:  # unnamed mobs are common (vanilla worlds) and fine
                identities[(prefix, name)] += 1
        if prefix.startswith("oCMob"):
            get = getattr(obj, "get", lambda key, default=None: default)
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
        warnings.append("No Visual Name, model falls back to <name>.MDS (Spacer crashes "
                        f"loading a mob whose model doesn't exist): {_limited(no_visual)}")
    if unopenable:
        warnings.append("Locked with no Key Instance or Picklock Str, can never be "
                        f"opened: {_limited(unopenable)}")
    if no_sleep:
        warnings.append(f"Bed without On State Func SLEEPABIT, no sleep dialog: {_limited(no_sleep)}")
    if point_lights:
        warnings.append(f"Sun/area lights exported as point lights: {_limited(point_lights)}")
    if not has_level_compo:
        warnings.append("No zCVobLevelCompo: Spacer has no level mesh to compile")
    return warnings
