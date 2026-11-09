"""
Waypoint link storage and helpers.

Each object has a `zen_waypoint_links` PropertyGroup (registered in
__init__.py) with three Object pointer slots. A connection is stored on
ONE endpoint only - the exporter writes one way per stored link (and
dedupes a link stored on both ends) - so a waypoint's three slots hold
three distinct neighbours. The UI still reads as bidirectional:
get_effective_neighbors() also finds links stored on the other side.

Auto-aim: storing a link source -> target turns the source to face the
target (slot update callback), so every way of linking gets it - Link
Selected Waypoints, Add Waypoint at Cursor and dragging an object into a
slot. Only the heading changes (waypoints stay level). The importer
suppresses it to keep directions read from a ZEN.
"""

from contextlib import contextmanager

import bpy

WAYPOINT_PREFIX = "zCWaypoint:"
LINK_SLOT_NAMES = ("link_a", "link_b", "link_c")
LINK_SLOT_COUNT = len(LINK_SLOT_NAMES)

_auto_aim_suppressed = 0


@contextmanager
def auto_aim_suppressed():
    global _auto_aim_suppressed
    _auto_aim_suppressed += 1
    try:
        yield
    finally:
        _auto_aim_suppressed -= 1


def aim_waypoint_at(source, target):
    """Turn source about Z so its local +Y (facing axis) points at target.
    Keeps location and scale, and works for parented objects. Returns
    False if target is straight above/below source (no heading)."""
    from mathutils import Euler, Matrix
    from zen_gin_export import waypoint_yaw_towards

    # A just-created/moved object's matrix_world is stale until the
    # depsgraph updates.
    bpy.context.view_layer.update()
    src_loc, _, src_scale = source.matrix_world.decompose()
    dst_loc = target.matrix_world.translation
    yaw = waypoint_yaw_towards(dst_loc.x - src_loc.x, dst_loc.y - src_loc.y)
    if yaw is None:
        return False
    source.matrix_world = Matrix.LocRotScale(
        src_loc, Euler((0.0, 0.0, yaw)).to_quaternion(), src_scale,
    )
    return True


def _on_link_slot_changed(slot):
    def update(self, context):
        if _auto_aim_suppressed:
            return
        source = self.id_data
        target = getattr(self, slot, None)
        if target is None or target == source or not is_waypoint(target):
            return
        aim_waypoint_at(source, target)
    return update


class ZenWaypointLinks(bpy.types.PropertyGroup):
    link_a: bpy.props.PointerProperty(type=bpy.types.Object, name="Link A",
                                      update=_on_link_slot_changed("link_a"))
    link_b: bpy.props.PointerProperty(type=bpy.types.Object, name="Link B",
                                      update=_on_link_slot_changed("link_b"))
    link_c: bpy.props.PointerProperty(type=bpy.types.Object, name="Link C",
                                      update=_on_link_slot_changed("link_c"))


def is_waypoint(obj):
    """Same test as the exporter: the name prefix alone. False for None
    and for stale references to deleted objects."""
    try:
        return obj is not None and obj.name.startswith(WAYPOINT_PREFIX)
    except ReferenceError:
        return False


def setup_waypoint_empty(obj, rotation_matrix=None):
    """ARROWS ("csys") display whose green local +Y is the exported facing
    direction; Euler rotation with X/Y locked so rotating only turns it
    about Z (NPCs only use the heading). rotation_matrix: optional 3x3 row
    tuples to start from, e.g. an imported direction."""
    obj.empty_display_type = 'ARROWS'
    obj.empty_display_size = 1.0
    obj.rotation_mode = 'XYZ'
    if rotation_matrix is not None:
        from mathutils import Matrix
        obj.rotation_euler = Matrix(rotation_matrix).to_euler('XYZ')
    obj.lock_rotation = (True, True, False)


def get_links(obj):
    """The ZenWaypointLinks PropertyGroup for obj, or None."""
    return getattr(obj, "zen_waypoint_links", None)


def get_link_targets(obj):
    """(slot_name, target) for obj's own occupied slots. A slot left
    pointing at a deleted object is cleared on the way."""
    links = get_links(obj)
    if links is None:
        return []
    result = []
    for slot in LINK_SLOT_NAMES:
        target = getattr(links, slot, None)
        if target is None:
            continue
        try:
            target.name
        except ReferenceError:
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
    """True if source and target are connected, stored on either side."""
    return (any(t == target for _, t in get_link_targets(source))
            or any(t == source for _, t in get_link_targets(target)))


def add_directed_link(source, target):
    """Store one link in source's next free slot. False if source is full."""
    links = get_links(source)
    slot = get_empty_link_slot(source)
    if links is None or slot is None:
        return False
    setattr(links, slot, target)
    return True


def remove_directed_link(source, target):
    """Clear target from source's own slots. Returns the number removed."""
    links = get_links(source)
    if links is None:
        return 0
    removed = 0
    for slot in LINK_SLOT_NAMES:
        if getattr(links, slot, None) == target:
            setattr(links, slot, None)
            removed += 1
    return removed


def get_effective_neighbors(obj, candidates=None):
    """Every waypoint connected to obj, whichever side stores the link.
    candidates: objects to scan for incoming links (default: all)."""
    neighbors = [t for _, t in get_link_targets(obj)]
    for other in bpy.data.objects if candidates is None else candidates:
        if other == obj or other in neighbors or not is_waypoint(other):
            continue
        if any(t == obj for _, t in get_link_targets(other)):
            neighbors.append(other)
    return neighbors


def find_next_waypoint_name():
    existing = set()
    for obj in bpy.data.objects:
        if not is_waypoint(obj):
            continue
        suffix = obj.name[len(WAYPOINT_PREFIX):].split(".")[0]
        if suffix.startswith("WP_") and suffix[3:].isdigit():
            existing.add(int(suffix[3:]))
    next_num = 1
    while next_num in existing:
        next_num += 1
    return f"{WAYPOINT_PREFIX}WP_{next_num:03d}"
