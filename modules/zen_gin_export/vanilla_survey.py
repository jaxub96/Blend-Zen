"""
What the vanilla worlds do, as data (vanilla_survey.json, written by
tooling/pipeline/survey_vanilla_worlds.py):

  - per prop visual, the collision / wind settings vanilla gives it, where
    they differ from a plain prop. They are the *defaults* of a `zCVob` with
    that visual: a fir dropped into a scene sways, grass does not block the
    player. Anything set on the object still wins;
  - per vob class, the visuals vanilla uses with it (the visual dropdown);
  - per vob class, the fields vanilla never changes (shown under Advanced).
"""

import json
import os

_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vanilla_survey.json")
_data = None

# Per-visual defaults apply to plain props only: mobs, movers and triggers
# need their class's collision flags to work at all.
PROP_TYPE = "zCVob"


def _survey():
    global _data
    if _data is None:
        try:
            with open(_PATH, encoding="utf-8") as handle:
                _data = json.load(handle)
        except (OSError, ValueError):
            _data = {}
    return _data


def normalize_visual(visual, default_extension=".3DS"):
    """'nw_nature_tanne_75p' -> 'NW_NATURE_TANNE_75P.3DS'."""
    visual = str(visual or "").strip().upper()
    if visual and "." not in visual:
        visual += default_extension
    return visual


def visual_defaults(vob_type, visual):
    """{base key: value} vanilla prefers for this visual; {} for other
    types and unknown visuals."""
    if vob_type != PROP_TYPE or not visual:
        return {}
    return _survey().get("visual_defaults", {}).get(normalize_visual(visual), {})


def class_visuals(vob_type):
    """Visuals vanilla uses with this class, most used first."""
    return list(_survey().get("class_visuals", {}).get(vob_type, ()))


def all_class_visuals():
    return {vob_type: list(visuals) for vob_type, visuals in _survey().get("class_visuals", {}).items()}


def unused_fields(vob_type):
    """Custom keys vanilla never changes from their default for this class."""
    return frozenset(_survey().get("unused_fields", {}).get(vob_type, ()))
