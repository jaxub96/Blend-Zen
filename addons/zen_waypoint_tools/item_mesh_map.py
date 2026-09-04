"""
oCItem script-instance-name -> mesh-filename lookup, for mesh preview.

An item's Daedalus script instance name (e.g. "ITMW_1H_PAL_SWORD") is
generally a DIFFERENT string from its actual mesh filename (e.g.
"ITMW_030_1H_PAL_SWORD_02"). Confirmed via a real Spacer test: exporting
an oCItem using the mesh name as its itemInstance resolved no in-game
visual at all, while the real instance name correctly resolved to that
mesh (visible in Spacer's own vob-list export). There is no way to
derive this mapping from the name alone - it comes from Gothic's
compiled Daedalus scripts - so this reads a user-maintained JSON file
instead of guessing.

The JSON is expected to look like real extracted Daedalus data, grouped
by source script file:

    {
      "IT_Addon_Amulette.d": {
        "ItAm_Addon_Health": "ItAm_Hp_01.3ds",
        ...
      },
      ...
    }

A flat { "instance_name": "mesh_filename.3ds", ... } shape (no script
file grouping) is also accepted, for smaller hand-maintained files.
Lookups are case-insensitive, since Daedalus identifiers are used
inconsistently in casing even within real extracted data.

No caching: this file can be edited and grow throughout a session, and
a stale in-memory copy caused real confusion once already - re-reading
it (a fast, small JSON parse) on every lookup avoids that class of bug
entirely rather than requiring a manual reload step.
"""

import os
import json

ITEM_MESH_MAP_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "asset_catalog", "item_mesh_map.json",
)


def _load_item_mesh_map():
    """Flattens either the grouped-by-script-file shape or a flat shape
    into a single instance_name (uppercased) -> mesh_name (no
    extension) dict."""
    flat = {}
    if not os.path.isfile(ITEM_MESH_MAP_PATH):
        return flat

    with open(ITEM_MESH_MAP_PATH, "r") as f:
        data = json.load(f)

    for key, value in data.items():
        if key.startswith("_"):
            continue
        if isinstance(value, dict):
            for instance_name, mesh_filename in value.items():
                flat[instance_name.upper()] = os.path.splitext(mesh_filename)[0]
        elif isinstance(value, str):
            flat[key.upper()] = os.path.splitext(value)[0]

    return flat


def get_item_mesh_map():
    return _load_item_mesh_map()


def resolve_item_mesh_name(instance_name):
    """Returns the mesh filename (no extension) mapped to this item
    instance name, or None if no mapping is known yet. Case-insensitive."""
    return _load_item_mesh_map().get(instance_name.upper())
