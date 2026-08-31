from zen_gin_export.archive_verifier import verify_archive_text


def make_header(object_count):
    return f"""ZenGin Archive
ver 1
zCArchiverGeneric
ASCII
saveGame 0
date 1.1.1970 12:0:0
user jaxub
END
objects {object_count}
END
"""


def test_valid_realistic_archive_passes():
    """Shape mirrors a real trimmed export: world + one prop + a 2-node
    waynet (1 way, one waypoint reused via the section-symbol marker)."""
    body = """[% oCWorld:zCWorld 36865 0]
	[VobTree % 0 0]
		[% zCVob:zCVob 52224 1]
			[visual % 0 0]
			[]
			[ai % 0 0]
			[]
		[]
	[]
	[WayNet % 0 0]
		[% zCWayNet 0 2]
			numWays=int:1
			[wayl0 zCWaypoint 0 3]
			[]
			[wayr0 zCWaypoint 0 4]
			[]
		[]
	[]
[]
[EndMarker % 0 0]
[]
"""
    result = verify_archive_text(make_header(5) + body)
    assert result.ok, result.issues
    assert result.header_object_count == 5
    assert result.real_object_indices == [0, 1, 2, 3, 4]


def test_valid_archive_with_reused_waypoint_reference():
    """A waypoint chain where wp2 is reused on a second way (the
    section-symbol marker) must NOT count as a new allocation."""
    body = """[% oCWorld:zCWorld 36865 0]
	[WayNet % 0 0]
		[% zCWayNet 0 1]
			numWays=int:2
			[wayl0 zCWaypoint 0 2]
			[]
			[wayr0 zCWaypoint 0 3]
			[]
			[wayl1 \u00a7 0 3]
			[]
			[wayr1 zCWaypoint 0 4]
			[]
		[]
	[]
[]
"""
    result = verify_archive_text(make_header(5) + body)
    assert result.ok, result.issues
    assert result.real_object_indices == [0, 1, 2, 3, 4]


def test_detects_duplicate_index():
    body = """[% oCWorld:zCWorld 36865 0]
	[% zCVob:zCVob 52224 1]
	[]
	[% zCVobSpot:zCVob 52224 1]
	[]
[]
"""
    result = verify_archive_text(make_header(3) + body)
    assert not result.ok
    assert any("Duplicate" in issue for issue in result.issues)


def test_detects_gap_in_indices():
    body = """[% oCWorld:zCWorld 36865 0]
	[% zCVob:zCVob 52224 1]
	[]
	[% zCVobSpot:zCVob 52224 3]
	[]
[]
"""
    result = verify_archive_text(make_header(3) + body)
    assert not result.ok
    assert any("not contiguous" in issue for issue in result.issues)


def test_detects_header_count_mismatch():
    body = """[% oCWorld:zCWorld 36865 0]
	[% zCVob:zCVob 52224 1]
	[]
[]
"""
    result = verify_archive_text(make_header(5) + body)
    assert not result.ok
    assert any("Header claims" in issue for issue in result.issues)


def test_missing_header_is_flagged():
    result = verify_archive_text("not a real archive at all\n")
    assert not result.ok
    assert any("objects N" in issue for issue in result.issues)
