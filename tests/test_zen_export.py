"""End-to-end export through the real ZenArchive writer, checked with the
same verifier that runs on every real export, plus waynet details."""

import pytest

from conftest import FakeObject, world_matrix
from modules import zen_gin_export
from modules.zen_gin_export import parse_archive, find_block


def _export(tmp_path, objects, name="TEST.ZEN"):
    path = tmp_path / name
    with zen_gin_export.FilePrinter(str(path)) as printer:
        zen_gin_export.ZenArchive(objects, printer).print()
    result = zen_gin_export.verify_archive_file(str(path))
    assert result.ok, result.issues
    return path.read_text(encoding="windows-1250")


def _waynet(text):
    world = parse_archive(text)[0]
    return find_block(world, type1="WayNet").children[0]


def test_full_scene_export_produces_a_structurally_valid_archive(tmp_path):
    wp_1, wp_2, wp_3, wp_4 = (FakeObject(f"zCWaypoint:WP_0{i}") for i in range(1, 5))
    wp_1.link_to(wp_2, wp_4)
    wp_2.link_to(wp_3)

    _export(tmp_path, [
        FakeObject("zCVob:vob1"),
        FakeObject("filtering"),
        FakeObject("oCItem:ITFO_APPLE.001"),
        FakeObject("zCVobSpot:FP_ALCHEMIST_01"),
        FakeObject("zCVob:vob1.001"),
        FakeObject("zCVobLight:LIGHT_01"),
        FakeObject("zCVobSound:OW_COASTLIGHT"),
        FakeObject("zCVobStartpoint:START"),
        FakeObject("oCMobContainer:CHEST_01"),
        FakeObject("oCMobFire:FIRE_01"),
        FakeObject("zCVobLevelCompo:SUKIENNICE_13"),
        wp_1, wp_2, wp_3, wp_4,
    ])


def test_unlinked_waypoints_are_exported_in_the_waypoint_list(tmp_path):
    """Spacer writes waypoints that belong to no way as waypointN blocks
    before the ways (see blender_work_dir/DieGestrandeten.zen); they used
    to be dropped entirely."""
    wp_1, wp_2 = FakeObject("zCWaypoint:WP1"), FakeObject("zCWaypoint:WP2")
    orphan = FakeObject("zCWaypoint:ORPHAN", location=(1, 2, 3))
    wp_1.link_to(wp_2)

    waynet = _waynet(_export(tmp_path, [wp_1, wp_2, orphan]))

    assert waynet.get("numWaypoints") == "1"
    assert waynet.get("numWays") == "1"
    assert [c.type1 for c in waynet.children] == ["waypoint0", "wayl0", "wayr0"]
    assert waynet.children[0].get("wpName") == "ORPHAN"
    assert waynet.children[0].get("position") == "100.0 300.0 200.0"
    assert waynet.children[0].property_types["underWater"] == "bool"


def test_link_stored_on_both_ends_is_written_once_and_dangling_links_are_skipped(tmp_path):
    wp_1, wp_2 = FakeObject("zCWaypoint:WP1"), FakeObject("zCWaypoint:WP2")
    not_exported = FakeObject("zCWaypoint:OTHER_SCENE")
    wp_1.link_to(wp_2, not_exported, FakeObject("zCVob:NOT_A_WAYPOINT"))
    wp_2.link_to(wp_1)

    waynet = _waynet(_export(tmp_path, [wp_1, wp_2]))

    assert waynet.get("numWays") == "1"


def test_waypoint_position_and_direction_come_from_the_world_matrix(tmp_path):
    """The green Y arrow is `direction`; a 90 degree turn about Blender Z
    faces Blender -X (Gothic -X). Position is world space, so parented
    waypoints are correct too."""
    wp_1 = FakeObject("zCWaypoint:WP1")
    turned = ((0.0, -1.0, 0.0), (1.0, 0.0, 0.0), (0.0, 0.0, 1.0))
    wp_2 = FakeObject("zCWaypoint:WP2", matrix_world=world_matrix((4, 5, 6), turned))
    wp_1.link_to(wp_2)

    left, right = _waynet(_export(tmp_path, [wp_1, wp_2])).children

    assert left.get("direction") == "0.0 0.0 1.0"
    assert right.get("direction") == "-1.0 0.0 0.0"
    assert right.get("position") == "400.0 600.0 500.0"


def test_failed_export_leaves_the_previous_file_untouched(tmp_path):
    path = tmp_path / "KEEP.ZEN"
    path.write_text("previous good export")

    class Broken(FakeObject):
        @property
        def matrix_world(self):
            raise RuntimeError("boom")

        @matrix_world.setter
        def matrix_world(self, value):
            pass

    with pytest.raises(RuntimeError):
        with zen_gin_export.FilePrinter(str(path)) as printer:
            zen_gin_export.ZenArchive([Broken("zCVob:X")], printer).print()

    assert path.read_text() == "previous good export"
    assert list(tmp_path.iterdir()) == [path]


def test_unencodable_name_fails_cleanly(tmp_path):
    path = tmp_path / "BAD.ZEN"
    with pytest.raises(UnicodeEncodeError):
        with zen_gin_export.FilePrinter(str(path)) as printer:
            zen_gin_export.ZenArchive([FakeObject("zCVob:☃")], printer).print()
    assert list(tmp_path.iterdir()) == []
