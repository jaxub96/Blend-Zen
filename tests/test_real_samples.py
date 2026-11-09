"""The parser on real Spacer-saved worlds (blender_work_dir/). These are
compiled worlds with a binary mesh section, so they also guard the
tolerant decoding."""

from pathlib import Path

import pytest

from modules.zen_gin_export import parse_archive, find_block, read_archive_text

SAMPLE = Path(__file__).resolve().parents[1] / "blender_work_dir" / "DieGestrandeten.zen"


@pytest.mark.skipif(not SAMPLE.exists(), reason="sample world not checked out")
def test_spacer_world_parses_vobs_and_free_waypoints():
    world = parse_archive(read_archive_text(str(SAMPLE)))[0]

    vob_types = {block.type2.split(":")[0] for block in find_block(world, type1="VobTree").children}
    assert {"zCVobLevelCompo", "oCItem", "zCVobSpot", "zCVobLight", "oCMobContainer"} <= vob_types

    waynet = find_block(world, type1="WayNet").children[0]
    free = [c for c in waynet.children if c.type1.startswith("waypoint")]
    assert len(free) == int(waynet.get("numWaypoints")) == 4
    assert free[0].get("wpName") == "MONSTER1"
