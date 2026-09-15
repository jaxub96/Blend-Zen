import bpy


WAYPOINT_PREFIX = "zCWaypoint:"
LINK_SLOT_NAMES = ("link_a", "link_b", "link_c")
LINK_SLOT_COUNT = len(LINK_SLOT_NAMES)


# ---------------------------------------------------------------------------
# Link storage
#
# Each waypoint object gets a `zen_waypoint_links` PropertyGroup (registered
# in __init__.py) with three PointerProperty(type=bpy.types.Object) slots.
# This is a native, documented Blender mechanism for storing object
# references as custom data - unlike an earlier version of this tool, which
# stored links as custom values on a Geometry Nodes modifier attached to
# each waypoint (a trick to get free "pick an object" UI fields without
# writing a PropertyGroup). That trick broke starting around Blender 5.2:
# the modifier's dict-style value access (`mod.get(...)`, `mod[...]`,
# `mod.keys()`) started raising
# "TypeError: this type doesn't support IDProperties" outright, meaning the
# underlying storage model for Geometry Nodes modifier inputs is no longer
# compatible with that approach. PointerProperty on a PropertyGroup doesn't
# depend on Geometry Nodes internals at all, so it isn't exposed to the same
# kind of breakage.
#
# Storage stays SINGLE-DIRECTIONAL on purpose: each connection is written
# on exactly ONE endpoint. This matches the exporter's WayNet class, which
# emits one "way" per stored link it finds while scanning all waypoints -
# storing the same connection on both ends would export it twice (doubling
# numWays and writing duplicate way pairs into the archive). It also means
# each waypoint's 3 link slots can hold 3 *real* distinct neighbors, instead
# of burning 2 slots just to keep a simple chain connected both ways.
#
# The UI still *feels* bidirectional: get_effective_neighbors() below unions
# a waypoint's own outgoing links with any incoming links found by scanning
# other waypoints, so the panel and the viewport wires show the full picture
# regardless of which side a given connection happened to be stored on.
# ---------------------------------------------------------------------------

class ZenWaypointLinks(bpy.types.PropertyGroup):
    link_a: bpy.props.PointerProperty(type=bpy.types.Object, name="Link A")
    link_b: bpy.props.PointerProperty(type=bpy.types.Object, name="Link B")
    link_c: bpy.props.PointerProperty(type=bpy.types.Object, name="Link C")


def is_waypoint(obj):
    """A waypoint is defined solely by its export name prefix.

    This intentionally matches the exporter's own check
    (`blender_object.name.startswith("zCWaypoint:")`) exactly, so this tool
    can never disagree with what actually gets written to the .ZEN file.
    """
    return obj is not None and obj.name.startswith(WAYPOINT_PREFIX)


def get_waypoint_display_name(obj):
    return obj.name


def get_links(obj):
    """Return the ZenWaypointLinks PropertyGroup for obj, or None if unavailable."""
    return getattr(obj, "zen_waypoint_links", None)


def _is_freed(obj):
    """True if obj is a stale reference to an Object Blender has since freed.

    Deleting a waypoint via the viewport (X) does not reliably clear the
    PointerProperty slots that other waypoints hold pointing at it - the
    slot can be left holding a dangling reference. Accessing any attribute
    on one raises ReferenceError; that's the only way to detect it.
    """
    try:
        obj.name
    except ReferenceError:
        return True
    return False


def get_link_targets(obj):
    """Return (slot_name, target) tuples for this object's own occupied link slots.

    Self-heals: a slot pointing at a freed Object (its target waypoint was
    deleted) is cleared here, so the link stops being drawn/counted on the
    very next read instead of surviving until the file is reloaded.
    """
    links = get_links(obj)
    if links is None:
        return []

    result = []
    for slot in LINK_SLOT_NAMES:
        target = getattr(links, slot, None)
        if target is None:
            continue
        if _is_freed(target):
            setattr(links, slot, None)
            continue
        result.append((slot, target))
    return result


def get_empty_link_slot(obj):
    links = get_links(obj)
    if links is None:
        return None

    for slot in LINK_SLOT_NAMES:
        if getattr(links, slot, None) is None:
            return slot
    return None


def has_link(source, target):
    """True if a connection exists between source and target, stored on either side."""
    if any(t == target for _, t in get_link_targets(source)):
        return True
    if any(t == source for _, t in get_link_targets(target)):
        return True
    return False


def add_directed_link(source, target):
    """Store one link on source's next free slot. Returns False if source is full or invalid."""
    links = get_links(source)
    if links is None:
        return False

    slot = get_empty_link_slot(source)
    if slot is None:
        return False

    setattr(links, slot, target)
    return True


def remove_directed_link(source, target):
    """Remove every occurrence of target from source's own slots. Returns number removed."""
    links = get_links(source)
    if links is None:
        return 0

    removed = 0
    for slot in LINK_SLOT_NAMES:
        if getattr(links, slot, None) == target:
            setattr(links, slot, None)
            removed += 1
    return removed


def get_effective_neighbors(obj):
    """All waypoints connected to obj, regardless of which side stores the link."""
    neighbors = []
    seen = set()

    for _, target in get_link_targets(obj):
        key = target.as_pointer()
        if key not in seen:
            seen.add(key)
            neighbors.append(target)

    for other in bpy.data.objects:
        if other == obj or not is_waypoint(other):
            continue
        for _, target in get_link_targets(other):
            if target == obj:
                key = other.as_pointer()
                if key not in seen:
                    seen.add(key)
                    neighbors.append(other)

    return neighbors


def count_links(obj):
    """Effective neighbor count (outgoing + incoming), for capacity/display purposes."""
    return len(get_effective_neighbors(obj))


def find_next_waypoint_name():
    existing_numbers = set()

    for obj in bpy.data.objects:
        if not is_waypoint(obj):
            continue

        suffix = obj.name[len(WAYPOINT_PREFIX):].split(".")[0]
        if suffix.startswith("WP_"):
            num_part = suffix[3:]
            if num_part.isdigit():
                existing_numbers.add(int(num_part))

    next_num = 1
    while next_num in existing_numbers:
        next_num += 1

    return f"{WAYPOINT_PREFIX}WP_{next_num:03d}"
