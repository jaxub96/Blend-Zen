"""
Which visuals fit which vob class - what the Visual dropdown offers.

A chest needs a model script (CHESTBIG_*.MDS: it has the open/close
animations), a chair is a plain model (CHAIR_*.ASC), a sign is a mesh
(.3DS). Offering every model for every class makes the wrong one easy to
pick, so the list is narrowed by class. Typing any name still works.

Sources: `models` (X.MDS / X.ASC found in the game files), `meshes`
(X.3DS), and the visuals vanilla uses per class (vanilla_survey).
"""

import os

from .vanilla_survey import all_class_visuals

# Model-name families that belong to one class. A model in one of these is
# only offered for that class.
CLASS_PREFIXES = {
    "oCMobContainer": ("CHEST",),
    "oCMobDoor": ("DOOR",),
    "oCMobBed": ("BED",),
    "oCMobLadder": ("LADDER",),
    "oCMobSwitch": ("LEVER", "TOUCHPLATE", "TURNSWITCH"),
    "oCMobWheel": ("VWHEEL",),
    "oCMobFire": ("FIREPLACE",),
}
# Classes that only work with a model script: without its animations a
# chest never opens (vanilla has one chest saved as .ASC, a slip).
SCRIPT_ONLY = ("oCMobContainer", "oCMobDoor", "oCMobSwitch", "oCMobWheel")
# Classes that take models; the generic one gets whatever no family claims.
GENERIC_MOB = "oCMobInter"
MODEL_CLASSES = tuple(CLASS_PREFIXES) + (GENERIC_MOB,)
# Classes whose visual is a static mesh.
MESH_CLASSES = ("oCMOB", "zCMover")


def _family_of(name):
    """The class whose name family this visual belongs to, or None."""
    upper = name.upper()
    for vob_type, prefixes in CLASS_PREFIXES.items():
        if upper.startswith(prefixes):
            return vob_type
    return None


def _preferred_forms(models, vanilla_used):
    """Drop the form nobody should pick when a model exists both as X.MDS
    and X.ASC: keep the one(s) vanilla uses, else the script (.MDS) - it is
    the .ASC plus its animations."""
    by_stem = {}
    for name in models:
        stem, extension = os.path.splitext(name.upper())
        by_stem.setdefault(stem, {})[extension] = name
    result = []
    for stem, forms in by_stem.items():
        if len(forms) > 1:
            used = [name for name in forms.values() if name.upper() in vanilla_used]
            forms = {os.path.splitext(n)[1].upper(): n for n in used} if used else (
                {".MDS": forms[".MDS"]} if ".MDS" in forms else forms)
        result += forms.values()
    return result


def visuals_for(vob_type, models, meshes, survey=None):
    """The visuals to offer for vob_type: those vanilla uses with it first
    (most used first), then the other fitting ones from the game files,
    alphabetically. None when this module has no rule for the type."""
    if vob_type not in MODEL_CLASSES and vob_type not in MESH_CLASSES:
        return None
    survey = all_class_visuals() if survey is None else survey
    vanilla_used = {name.upper() for names in survey.values() for name in names}
    own_vanilla = [name.upper() for name in survey.get(vob_type, ())]

    if vob_type in MESH_CLASSES:
        return _merge(own_vanilla, meshes)

    def fits(name):
        if vob_type in SCRIPT_ONLY and not name.upper().endswith(".MDS"):
            return False
        family = _family_of(name)
        return family == vob_type if family or vob_type != GENERIC_MOB else True

    # Vanilla quirks stay out: beds are stored as oCMobDoor there, but a
    # bed model is no door.
    first = [name for name in own_vanilla if fits(name) or (
        _family_of(name) is None and vob_type not in SCRIPT_ONLY)]
    if vob_type == "oCMobBed":
        first += [n.upper() for names in survey.values() for n in names if _family_of(n) == "oCMobBed"]

    claimed_elsewhere = {
        name.upper() for other, names in survey.items() if other != vob_type for name in names}
    generic_tokens = {name.split("_")[0] for name in own_vanilla}
    rest = []
    for name in _preferred_forms(models, vanilla_used):
        upper = name.upper()
        if not fits(upper) or (upper in claimed_elsewhere and _family_of(upper) != vob_type):
            continue
        if vob_type == GENERIC_MOB and upper.endswith(".ASC") and upper.split("_")[0] not in generic_tokens:
            continue            # creature and armour models are .ASC too
        rest.append(upper)
    return _merge(first, rest)


def _merge(first, rest):
    seen, result = set(), []
    for name in list(first) + sorted(rest):
        upper = name.upper()
        if upper not in seen:
            seen.add(upper)
            result.append(name)
    return result
