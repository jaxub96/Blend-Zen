from .coordinate_transform import (
    blender_position_to_gothic,
    blender_direction_to_gothic,
    waypoint_direction_from_matrix,
)

WAYPOINT_PREFIX = "zCWaypoint:"
LINK_SLOT_NAMES = ("link_a", "link_b", "link_c")


def is_waypoint_object(obj):
    try:
        return obj is not None and obj.name.startswith(WAYPOINT_PREFIX)
    except ReferenceError:  # a link slot pointing at a deleted object
        return False


def linked_waypoints(blender_object):
    """Targets stored in the object's `zen_waypoint_links` slots (the
    PropertyGroup registered by the zen_waypoint_tools addon)."""
    links = getattr(blender_object, "zen_waypoint_links", None)
    if links is None:
        return []
    targets = (getattr(links, slot, None) for slot in LINK_SLOT_NAMES)
    return [t for t in targets if is_waypoint_object(t) and t is not blender_object]


def _format_vec3(values):
    # Rounded so float noise (7.5e-08, 1100.0000000000002) doesn't reach
    # the file; "+ 0.0" turns -0.0 into 0.0.
    return " ".join(str(round(v, 6) + 0.0) for v in values)


class WayNet:
    """The zCWayNet block. Like Spacer, waypoints that are part of a way
    are written inline in the way list (first use defines them, later uses
    are `§` references); waypoints with no ways go in the `waypointN` list
    first. Only links between two exported waypoints are written, and a
    connection stored on both ends is written once."""

    def __init__(self, blender_objects, data_printer):
        self._data_printer = data_printer
        waypoints = [o for o in blender_objects if is_waypoint_object(o)]
        exported = {wp.name for wp in waypoints}

        self._ways = []
        seen_pairs = set()
        for source in waypoints:
            for target in linked_waypoints(source):
                pair = frozenset((source.name, target.name))
                if target.name in exported and pair not in seen_pairs:
                    seen_pairs.add(pair)
                    self._ways.append((source, target))

        in_ways = {wp.name for way in self._ways for wp in way}
        self._free_waypoints = [wp for wp in waypoints if wp.name not in in_ways]
        self.objects_count = 1 + len(in_ways) + len(self._free_waypoints)

    def _print_waypoint_block(self, type_1, waypoint, object_index):
        p = self._data_printer
        m = waypoint.matrix_world
        position = blender_position_to_gothic(m[0][3], m[1][3], m[2][3])
        direction = blender_direction_to_gothic(*waypoint_direction_from_matrix(m))
        p.start_object_block(type_1=type_1, type_2="zCWaypoint", object_index=object_index)
        p.print_string_property("wpName", waypoint.name[len(WAYPOINT_PREFIX):])
        p.print_int_property("waterDepth", 0)
        p.print_bool_property("underWater", False)
        p.print_vec3_property("position", _format_vec3(position))
        p.print_vec3_property("direction", _format_vec3(direction))
        p.end_object_block()

    def print(self, object_index):
        p = self._data_printer
        p.start_object_block(type_1="WayNet")
        p.start_object_block(type_2="zCWayNet", object_index=object_index)
        object_index += 1
        p.print_int_property("waynetVersion", 1)

        p.print_int_property("numWaypoints", len(self._free_waypoints))
        for i, waypoint in enumerate(self._free_waypoints):
            self._print_waypoint_block(f"waypoint{i}", waypoint, object_index)
            object_index += 1

        p.print_int_property("numWays", len(self._ways))
        defined = {}
        for way_index, way in enumerate(self._ways):
            for side, waypoint in zip("lr", way):
                type_1 = f"way{side}{way_index}"
                if waypoint.name in defined:
                    p.start_object_block(type_1=type_1, type_2="§",
                                         object_index=defined[waypoint.name])
                    p.end_object_block()
                else:
                    self._print_waypoint_block(type_1, waypoint, object_index)
                    defined[waypoint.name] = object_index
                    object_index += 1

        p.end_object_block()
        p.end_object_block()
        return object_index
