"""
Shared test infrastructure for the Blender-free part of the test suite -
the sys.path bootstrap and small test doubles that were previously
copy-pasted across test_ocmob_export.py, test_zcvob_bounding_box.py, and
test_mob_props.py.
"""

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]

# Keep the tests importable when the project is opened/run outside an
# installed environment (for example, by the editor's test analyzer).
sys.path.insert(0, str(_REPO_ROOT))

# mob_props.py has zero bpy dependency (unlike the rest of
# zen_waypoint_tools, which imports bpy at module scope and can only run
# inside Blender) - this lets it be imported directly as a standalone
# module rather than through the addon package, so tests that need it
# stay Blender-free.
sys.path.insert(0, str(_REPO_ROOT / "addons" / "zen_waypoint_tools"))

from modules.zen_gin_export.printer import Printer  # noqa: E402


class RecordingPrinter(Printer):
    def __init__(self):
        self.lines = []

    def print(self, *content):
        self.lines.append("".join(content))


class FakeLocation:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x, self.y, self.z = x, y, z
