"""
Shared test infrastructure for the Blender-free test suite: path setup and
small stand-ins for Blender objects. zen_gin_export reads only plain
attributes (name, type, matrix_world rows, bound_box, children, data) and
custom properties via .get(), so no Blender or mathutils is needed.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT))
# mob_props.py has no bpy dependency, so tests import it directly.
sys.path.insert(0, str(_REPO_ROOT / "addons" / "zen_waypoint_tools"))

from modules.zen_gin_export.printer import Printer  # noqa: E402
from modules.zen_gin_export.zen_gin_data_printer import ZenGinDataPrinter  # noqa: E402


class RecordingPrinter(Printer):
    def __init__(self):
        self.lines = []

    def print(self, *content):
        self.lines.append("".join(content))


def world_matrix(location=(0.0, 0.0, 0.0), rows=((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))):
    """4x4 row tuples: a 3x3 linear part plus a translation."""
    return tuple(tuple(rows[i]) + (float(location[i]),) for i in range(3)) + ((0.0, 0.0, 0.0, 1.0),)


class FakeLinks:
    """Same shape as the addon's zen_waypoint_links PropertyGroup."""

    def __init__(self, link_a=None, link_b=None, link_c=None):
        self.link_a, self.link_b, self.link_c = link_a, link_b, link_c


class FakeObject:
    """A Blender object as zen_gin_export sees it. Extra keyword arguments
    become custom (ID) properties."""

    def __init__(self, name, location=(0.0, 0.0, 0.0), matrix_world=None, type="EMPTY",
                 children=(), bound_box=None, data=None, **custom):
        self.name = name
        self.type = type
        self.matrix_world = matrix_world or world_matrix(location)
        self.children = children
        self.bound_box = bound_box
        self.data = data
        self.zen_waypoint_links = None
        self._custom = custom

    def get(self, key, default=None):
        return self._custom.get(key, default)

    def link_to(self, *targets):
        self.zen_waypoint_links = FakeLinks(*targets)


def print_vob(vob_class, blender_object, object_index=0):
    printer = RecordingPrinter()
    vob_class(blender_object, ZenGinDataPrinter(printer)).print(object_index)
    return printer.lines


def exported_properties(vob_class, blender_object):
    """{property name: "type:value"} of a single vob block."""
    properties = {}
    for line in print_vob(vob_class, blender_object):
        stripped = line.strip()
        if "=" in stripped and not stripped.startswith("["):
            name, value = stripped.split("=", 1)
            properties[name] = value
    return properties
