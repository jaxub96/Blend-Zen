"""
Which vob triggers which: the pairs behind the trigger-link display.

A vob points at another by vob name. Most fields name the vob that gets
triggered (`trigger_target`, a trigger list's targets); a few name the vob
that does the triggering (a code master's slaves, "Only Respond To"). Either
way the pair is returned as (the one that fires, the one that reacts).
"""

from .vob_fields import LIST_SLOTS
from .zen_gin_zcvob import vob_name_from_object_name, vob_type_of

# Custom properties naming the vob this one triggers.
OUTGOING_KEYS = ("trigger_target", "trigger_target_failure") + tuple(
    f"list_target_{i}" for i in range(LIST_SLOTS))
# Custom properties naming a vob that triggers this one.
INCOMING_KEYS = ("respond_to_vob_name",) + tuple(f"slave_{i}" for i in range(LIST_SLOTS))


def _name_of(value):
    return str(value or "").strip().upper()


def trigger_link_pairs(objects):
    """[(source, target)] among objects, each pair once. A name shared by
    several vobs links to all of them, as the engine triggers them all."""
    vobs = [obj for obj in objects if vob_type_of(obj) is not None]
    by_name = {}
    for obj in vobs:
        name = _name_of(vob_name_from_object_name(obj.name))
        if name:
            by_name.setdefault(name, []).append(obj)

    pairs, seen = [], set()

    def add(source, target):
        key = (id(source), id(target))
        if source is not target and key not in seen:
            seen.add(key)
            pairs.append((source, target))

    for obj in vobs:
        for key in OUTGOING_KEYS:
            for other in by_name.get(_name_of(obj.get(key)), ()):
                add(obj, other)
        for key in INCOMING_KEYS:
            for other in by_name.get(_name_of(obj.get(key)), ()):
                add(other, obj)
    return pairs
