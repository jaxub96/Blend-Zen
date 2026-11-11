"""
Round-trip check: import a ZEN into Blender, export it again and compare
every vob and waypoint property with the original.

    blender --background --factory-startup --python tooling/pipeline/roundtrip_check.py -- \
        reference/_VOBS_NEWWORLD_PART_XARDAS_01.ZEN [exported.zen]

Prints what differs, grouped by vob class and property, and exits 1 if
anything unexpected does. Differences that are by design are not counted:

  - bbox3DWS of vobs with a mesh visual (imported as empties, no geometry;
    Spacer recomputes it from the visual when it loads the world)
  - position/rotation of box volumes (zones, triggers): only their box
    matters, and they are re-centred on it
  - an empty vobName where Blend-Zen names the object after its visual,
    item or sound (props, items, sounds)
  - visual blocks Spacer wrote as `§` references to an earlier, identical
    visual; we write each one out
  - bools Spacer wrote as -1
  - waypoint directions that were not unit length
  - bbox3DWS of ellipsoid sounds (we write the sphere's box)
"""

import os
import re
import sys
from collections import Counter, defaultdict

_REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
for sub in ("modules", "addons"):
    path = os.path.join(_REPO, sub)
    if path not in sys.path:
        sys.path.insert(0, path)

from zen_gin_export import parse_archive, read_archive_text, find_block  # noqa: E402
from zen_gin_export.vob_fields import VOB_SPECS  # noqa: E402

FLOAT_TOLERANCE = 2e-3
_NUMERIC = ("float", "vec3", "rawFloat", "int", "color")


def _vob_blocks(path):
    world = parse_archive(read_archive_text(path))[0]
    tree = find_block(world, type1="VobTree")
    return world, tree


def _parents(tree):
    """block index -> parent index (None for roots), from the childsN counts."""
    parents, stack = {}, [[None, int(tree.get("childs0", "0"))]]
    for index, _block in enumerate(tree.children):
        while len(stack) > 1 and stack[-1][1] <= 0:
            stack.pop()
        parents[index] = stack[-1][0]
        stack[-1][1] -= 1
        count = int(tree.get(f"childs{index + 1}", "0"))
        if count > 0:
            stack.append([index, count])
    return parents


def _numbers(value):
    return [float(v) for v in value.split()]


def _hex_floats(value):
    import struct
    value = value.strip()
    return [struct.unpack("<f", bytes.fromhex(value[i:i + 8]))[0] for i in range(0, len(value) - 7, 8)]


def _same(name, ptype, a, b):
    if a == b:
        return True
    if ptype == "bool":
        return (a.strip() not in ("0", "")) == (b.strip() not in ("0", ""))
    if ptype == "string":
        return a.strip().upper() == b.strip().upper()
    try:
        if ptype in _NUMERIC or ptype == "enum":
            xs, ys = _numbers(a), _numbers(b)
        elif ptype == "raw" and name in ("trafoOSToWSRot", "keyframes"):
            xs, ys = _hex_floats(a), _hex_floats(b)
        else:
            return a.strip().lower() == b.strip().lower()
    except ValueError:
        return False
    return len(xs) == len(ys) and all(
        abs(x - y) <= FLOAT_TOLERANCE * max(1.0, abs(x)) for x, y in zip(xs, ys))


def _where(block):
    real_type = block.type2.split(":")[0]
    spec = VOB_SPECS.get(real_type)
    box = spec is not None and spec.volume == "box"
    return _numbers(block.get("bbox3DWS" if box else "trafoOSToWSPos", "0 0 0"))


def _is_rotation(hex_value):
    m = _hex_floats(hex_value)
    return len(m) == 9 and all(
        abs(sum(m[r * 3 + c] ** 2 for c in range(3)) - 1.0) < 1e-3 for r in range(3))


def _is_sheared(hex_value):
    m = _hex_floats(hex_value)
    columns = [(m[c], m[3 + c], m[6 + c]) for c in range(3)]
    def cos(a, b):
        dot = sum(x * y for x, y in zip(a, b))
        return abs(dot) / ((sum(x * x for x in a) * sum(y * y for y in b)) ** 0.5 or 1.0)
    return max(cos(columns[0], columns[1]), cos(columns[0], columns[2]), cos(columns[1], columns[2])) > 1e-3


def _expected_difference(block, name, original, exported):
    real_type = block.type2.split(":")[0]
    spec = VOB_SPECS[real_type]
    if name == "bbox3DWS":
        if block.get("sndVolType", "0").strip() == "1":
            return True
        return spec.volume is None and real_type != "zCVobLight"
    if name in ("trafoOSToWSPos", "trafoOSToWSRot") and spec.volume == "box":
        return True
    if name == "trafoOSToWSRot":
        # Only mesh vobs keep a scaled matrix; and a sheared one cannot be
        # held by a Blender object at all.
        return not _is_rotation(original) and (
            not block.get("visual", "").strip() or _is_sheared(original))
    if name == "vobName":
        return original == "" and real_type in ("zCVob", "oCItem", "zCVobSound", "zCVobSoundDaytime")
    return False


def compare(original_path, exported_path):
    _, original_tree = _vob_blocks(original_path)
    _, exported_tree = _vob_blocks(exported_path)
    problems = Counter()
    examples = defaultdict(list)

    def note(kind, example):
        problems[kind] += 1
        if len(examples[kind]) < 3:
            examples[kind].append(example)

    exported_by_class = defaultdict(list)
    for index, block in enumerate(exported_tree.children):
        exported_by_class[block.type2].append((index, _where(block)))
    original_parents, exported_parents = _parents(original_tree), _parents(exported_tree)

    matched = {}
    skipped = Counter()
    for index, block in enumerate(original_tree.children):
        real_type = block.type2.split(":")[0]
        if real_type not in VOB_SPECS:
            skipped[real_type] += 1
            continue
        # The exported vob of the same class at the same place; where several
        # share a spot (a torch's flame and smoke) the one with the same visual.
        here = _where(block)
        visual = block.get("visual", "").upper()
        candidates = [
            (max(abs(a - b) for a, b in zip(here, there)),
             exported_tree.children[i].get("visual", "").upper() != visual, i)
            for i, there in exported_by_class[block.type2]
        ]
        candidates = [c for c in candidates if c[0] < 0.5]
        if not candidates:
            note(f"{block.type2}: vob missing from export", block.get("vobName") or block.get("visual"))
            continue
        best = min(candidates, key=lambda c: (c[1], c[0]))[2]
        exported_by_class[block.type2] = [e for e in exported_by_class[block.type2] if e[0] != best]
        matched[index] = best
        other = exported_tree.children[best]

        for name, value in block.properties.items():
            ptype = block.property_types[name]
            if name not in other.properties:
                note(f"{block.type2}.{name}: missing", value)
            elif not _same(name, ptype, value, other.properties[name]) \
                    and not _expected_difference(block, name, value, other.properties[name]):
                note(f"{block.type2}.{name}", f"{value!r} -> {other.properties[name]!r}")
        for name in other.properties:
            if name not in block.properties:
                note(f"{block.type2}.{name}: extra", other.properties[name])

        visual, other_visual = find_block(block, type1="visual"), find_block(other, type1="visual")
        if visual.type2 != "§":
            if visual.type2 != other_visual.type2:
                note(f"{block.type2} visual class", f"{visual.type2} -> {other_visual.type2}")
            for name, value in visual.properties.items():
                if not _same(name, visual.property_types[name], value, other_visual.properties.get(name, "")):
                    note(f"{block.type2} visual.{name}", f"{value!r} -> {other_visual.properties.get(name)!r}")

    for index, best in matched.items():
        parent = original_parents[index]
        while parent is not None and parent not in matched:      # skipped ancestor
            parent = original_parents[parent]
        expected = matched.get(parent)
        if exported_parents[best] != expected:
            note("hierarchy: different parent", original_tree.children[index].get("visual"))

    extra = sum(len(v) for v in exported_by_class.values())
    if extra:
        note("vobs only in the export", extra)
    return problems, examples, skipped, len(matched)


def _unit(vec3):
    values = _numbers(vec3)
    length = sum(v * v for v in values) ** 0.5 or 1.0
    return " ".join(str(v / length) for v in values)


def compare_waynet(original_path, exported_path):
    def waypoints(path):
        world = parse_archive(read_archive_text(path))[0]
        net = find_block(world, type1="WayNet")
        inner = net.children[0] if net and net.children else None
        points, by_index, ends = {}, {}, {}
        for entry in (inner.children if inner else ()):
            if entry.type2 != "§":
                by_index[entry.object_index] = entry.get("wpName")
                points[entry.get("wpName")] = entry
            if entry.type1.startswith("way"):
                ends[entry.type1] = by_index.get(entry.object_index)
        ways = {frozenset((ends[f"wayl{k[4:]}"], ends.get(f"wayr{k[4:]}")))
                for k in ends if k.startswith("wayl")}
        return points, ways

    a_points, a_ways = waypoints(original_path)
    b_points, b_ways = waypoints(exported_path)
    problems = []
    if set(a_points) != set(b_points):
        problems.append(f"waypoints differ: {sorted(set(a_points) ^ set(b_points))[:5]}")
    for name in set(a_points) & set(b_points):
        for prop in ("waterDepth", "underWater"):
            a, b = a_points[name].get(prop, "0"), b_points[name].get(prop, "0")
            if int(a or 0) != int(b or 0):
                problems.append(f"{name}.{prop}: {a} -> {b}")
        for prop in ("position", "direction"):
            a, b = a_points[name].get(prop), b_points[name].get(prop)
            if prop == "direction":
                a, b = _unit(a), _unit(b)
            if not _same(prop, "vec3", a, b):
                problems.append(f"{name}.{prop}: {a_points[name].get(prop)} -> {b_points[name].get(prop)}")
    if a_ways != b_ways:
        problems.append(f"ways differ: {len(a_ways - b_ways)} lost, {len(b_ways - a_ways)} new")
    return problems, len(a_points), len(a_ways)


def main():
    import bpy
    import zen_waypoint_tools

    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if not args:
        print(__doc__)
        sys.exit(2)
    source = os.path.abspath(args[0])
    target = os.path.abspath(args[1]) if len(args) > 1 else os.path.join(
        bpy.app.tempdir, "roundtrip_export.zen")

    zen_waypoint_tools.register()
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj)

    from zen_waypoint_tools import zen_import
    from zen_waypoint_tools.export_ops import export_zen_to_path
    report = zen_import.import_zen(bpy.context, source)
    print(f"imported {report['vobs_created']} vobs, {report['waypoints_created']} waypoints, "
          f"{report['ways_linked']} ways; skipped {dict(report['skipped_types'])}")
    report_type, message = export_zen_to_path(target)
    print(report_type, message[:600])

    problems, examples, skipped, matched = compare(source, target)
    way_problems, waypoint_count, way_count = compare_waynet(source, target)
    print(f"\ncompared {matched} vobs, {waypoint_count} waypoints, {way_count} ways")
    for kind, count in sorted(problems.items()):
        print(f"  {count:5d} x {kind}   e.g. {examples[kind]}")
    for problem in way_problems[:20]:
        print("  waynet:", problem)
    if skipped:
        print("  not supported (skipped):", dict(skipped))
    ok = not problems and not way_problems
    print("ROUND TRIP OK" if ok else "ROUND TRIP DIFFERS")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
