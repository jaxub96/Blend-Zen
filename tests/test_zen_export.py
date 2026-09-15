from modules import zen_gin_export
from mathutils import Quaternion


class DummyBlenderLocation:
    x = 25.0
    y = 15.0
    z = 0.0


class FakeWaypointLinks:
    """Mirrors the real zen_waypoint_links PropertyGroup's shape (see
    addons/zen_waypoint_tools/waypoint_links.py) - WayNet reads exactly
    this attribute name and these three slot names."""

    def __init__(self, link_a=None, link_b=None, link_c=None):
        self.link_a = link_a
        self.link_b = link_b
        self.link_c = link_c


class DummyBlenderObject:
    rotation_quaternion = Quaternion((0.0, 0.0, 0.0, 0.0))
    location = DummyBlenderLocation()
    zen_waypoint_links = None

    def __init__(self, name):
        self.name = name

    def link_to(self, *targets):
        """Occupy this waypoint's own link slots, exactly like the addon's
        add_directed_link() does - a link is stored on one endpoint only."""
        self.zen_waypoint_links = FakeWaypointLinks(*targets)


def test_full_scene_export_produces_a_structurally_valid_archive(tmp_path):
    """End-to-end integration test the per-vob unit tests can't be: a
    mixed scene (props, items, freepoints, level compo, an unrecognized
    object name to be filtered out, and a linked 4-node waynet) goes
    through the real ZenArchive writer, then gets checked with the same
    archive_verifier.py self-check that runs on every real export - so
    a future vob type or waynet-linking change that breaks object-index
    sequencing across a whole scene fails here, not silently in Spacer.
    """
    wp_1 = DummyBlenderObject("zCWaypoint:WAYPOINT_01")
    wp_2 = DummyBlenderObject("zCWaypoint:WAYPOINT_02")
    wp_3 = DummyBlenderObject("zCWaypoint:WAYPOINT_03")
    wp_4 = DummyBlenderObject("zCWaypoint:WAYPOINT_04")
    wp_1.link_to(wp_2, wp_4)
    wp_2.link_to(wp_3)

    output_path = tmp_path / "TEST.ZEN"
    printer = zen_gin_export.FilePrinter(str(output_path))
    zen_gin_export.ZenArchive(
        blender_objects=[
            DummyBlenderObject("zCVob:vob1"),
            DummyBlenderObject("filtering"),
            DummyBlenderObject("oCItem:ITFO_APPLE.001"),
            DummyBlenderObject("zCVobSpot:FP_ALCHEMIST_01"),
            DummyBlenderObject("zCVob:vob1.001"),
            DummyBlenderObject("zCVobSpot:FP_ALCHEMIST_02"),
            DummyBlenderObject("oCItem:ITFO_APPLE"),
            DummyBlenderObject("zCVobLevelCompo:SUKIENNICE_13"),
            wp_1,
            wp_2,
            wp_3,
            wp_4,
        ],
        printer=printer,
    ).print()
    printer.close()

    result = zen_gin_export.verify_archive_file(output_path)
    assert result.ok, result.issues


def test_unlinked_waypoint_does_not_inflate_the_header_count(tmp_path):
    """Regression guard: WayNet used to count every zCWaypoint:-named
    object toward the header's total, but only waypoints that appear in
    at least one link (source or target) are ever printed in the body -
    a waypoint placed but not yet linked (a normal mid-edit state) used
    to overstate the header count and fail archive_verifier's own
    header-vs-body check."""
    wp_1 = DummyBlenderObject("zCWaypoint:WP1")
    wp_2 = DummyBlenderObject("zCWaypoint:WP2")
    orphan = DummyBlenderObject("zCWaypoint:ORPHAN")
    wp_1.link_to(wp_2)

    output_path = tmp_path / "ORPHAN.ZEN"
    printer = zen_gin_export.FilePrinter(str(output_path))
    zen_gin_export.ZenArchive(
        blender_objects=[wp_1, wp_2, orphan],
        printer=printer,
    ).print()
    printer.close()

    result = zen_gin_export.verify_archive_file(output_path)
    assert result.ok, result.issues
