"""
Survey the vanilla ASCII worlds and write what Blend-Zen learns from them to
modules/zen_gin_export/vanilla_survey.json:

  visual_defaults  per prop visual, the collision / wind settings vanilla
                   gives it most often, where they differ from a plain prop
                   (so a tree dropped into a scene sways and a bush does not
                   block the player, without setting anything)
  class_visuals    per vob class with a model, the visuals vanilla uses with
                   it, most used first (chests use chest models, ...)
  unused_fields    per vob class, the fields vanilla never changes from their
                   default: the settings panel shows them under Advanced

Plain Python, no Blender needed:

    python3 tooling/pipeline/survey_vanilla_worlds.py "<Gothic II folder>"

Reads every ASCII .zen under _work/Data/Worlds except the MOD folder.
"""

import json
import os
import statistics
import sys
from collections import Counter, defaultdict

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(REPO, "modules"))

from zen_gin_export import parse_archive, read_archive_text, find_block  # noqa: E402
from zen_gin_export.game_data import find_data_dir                       # noqa: E402
from zen_gin_export import vob_fields as vf                              # noqa: E402

OUTPUT = os.path.join(REPO, "modules", "zen_gin_export", "vanilla_survey.json")
# Settings a prop's visual decides in practice.
VISUAL_KEYS = ("cd_static", "cd_dyn", "static_vob", "ani_mode", "ani_strength")
MIN_INSTANCES_FOR_UNUSED = 15      # fewer than this says nothing about a class
# Vanilla is inconsistent about wind (the same fir sways in one valley and
# not in the next), so a visual sways by default once this share of its
# instances does.
WIND_SHARE = 0.3
SLOT_PREFIXES = ("list_target_", "list_delay_", "slave_")
PROP = "zCVob"


def world_files(game_folder):
    worlds = None
    data = find_data_dir(game_folder)
    for name in os.listdir(data):
        if name.lower() == "worlds":
            worlds = os.path.join(data, name)
    for root, dirs, files in os.walk(worlds):
        dirs[:] = [d for d in dirs if d.upper() != "MOD"]
        for filename in sorted(files):
            path = os.path.join(root, filename)
            if filename.lower().endswith(".zen") and os.path.dirname(path) != worlds:
                with open(path, "rb") as handle:
                    if b"ASCII" in handle.read(300):
                        yield path


def survey(paths):
    by_visual = defaultdict(lambda: defaultdict(Counter))    # visual -> key -> value counts
    wind_strength = defaultdict(list)
    class_visuals = defaultdict(Counter)
    class_count = Counter()
    changed = defaultdict(Counter)                           # class -> key -> times not default
    for path in paths:
        world = parse_archive(read_archive_text(path))[0]
        tree = find_block(world, type1="VobTree")
        for block in (tree.children if tree else ()):
            vob_type = block.type2.split(":")[0]
            if vob_type not in vf.VOB_SPECS:
                continue
            properties = block.properties
            visual = properties.get("visual", "").strip().upper()
            visual_block = find_block(block, type1="visual")
            class_count[vob_type] += 1

            base = {}
            for archive_name, archive_type, key, default in vf.BASE_FIELDS:
                if archive_name in properties:
                    base[key] = vf.parse_value(archive_name, archive_type, properties[archive_name], default)
            custom = vf.custom_properties_from_block(
                vob_type, properties, visual_block.properties if visual_block else None)
            for _, _, key, _ in vf.keyed_fields(vob_type):
                if key in custom and key != "visual_name" and custom[key] != _as_stored(vf.default_for(vob_type, key)):
                    changed[vob_type][key] += 1

            if visual and vob_type != PROP and vf.VOB_SPECS[vob_type].visual in ("custom", "custom_only"):
                class_visuals[vob_type][visual] += 1
            if visual and vob_type == PROP and not visual.endswith((".PFX", ".TGA")):
                for key in VISUAL_KEYS:
                    if key in base and key != "ani_strength":
                        by_visual[visual][key][base[key]] += 1
                if base.get("ani_mode", "NONE") != "NONE":
                    wind_strength[visual].append(float(base.get("ani_strength", 0.0)))

    visual_defaults = {}
    for visual, keys in sorted(by_visual.items()):
        entry = {}
        for key, counts in keys.items():
            value = counts.most_common(1)[0][0]
            if key == "ani_mode":
                windy = Counter({mode: n for mode, n in counts.items() if mode != "NONE"})
                share = sum(windy.values()) / sum(counts.values())
                value = windy.most_common(1)[0][0] if windy and share >= WIND_SHARE else "NONE"
            if value != vf.base_default(PROP, key):
                entry[key] = value
        if entry.get("ani_mode"):
            entry["ani_strength"] = round(statistics.median(wind_strength[visual]), 3)
        if entry:
            visual_defaults[visual] = entry

    unused = {}
    for vob_type, count in sorted(class_count.items()):
        if count < MIN_INSTANCES_FOR_UNUSED:
            continue
        keys = [key for _, _, key, _ in vf.keyed_fields(vob_type)
                if key != "visual_name" and not key.startswith(SLOT_PREFIXES)
                and not changed[vob_type][key]]
        if keys:
            unused[vob_type] = keys
    return {
        "worlds": sorted(os.path.basename(p) for p in paths),
        "instances": dict(sorted(class_count.items())),
        "visual_defaults": visual_defaults,
        "class_visuals": {c: [v for v, _ in counts.most_common()] for c, counts in sorted(class_visuals.items())},
        "unused_fields": unused,
    }


def _as_stored(value):
    return list(value) if isinstance(value, tuple) else value


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    paths = list(world_files(sys.argv[1]))
    result = survey(paths)
    with open(OUTPUT, "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=1, sort_keys=False)
        handle.write("\n")
    print(f"{len(paths)} worlds, {sum(result['instances'].values())} vobs -> {OUTPUT}")
    print(f"{len(result['visual_defaults'])} visuals with their own defaults")
    for vob_type, keys in result["unused_fields"].items():
        print(f"  {vob_type} ({result['instances'][vob_type]}): never changed: {', '.join(keys)}")


if __name__ == "__main__":
    main()
