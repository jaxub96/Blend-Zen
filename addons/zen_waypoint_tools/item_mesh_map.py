"""
oCItem script-instance-name -> mesh-filename lookup, for mesh preview.

An item's Daedalus script instance name (e.g. "ITMW_1H_PAL_SWORD") is
generally a DIFFERENT string from its actual mesh filename (e.g.
"ITMW_030_1H_PAL_SWORD_02"). Confirmed via a real Spacer test: exporting
an oCItem using the mesh name as its itemInstance resolved no in-game
visual at all, while the real instance name correctly resolved to that
mesh (visible in Spacer's own vob-list export). There is no way to
derive this mapping from the name alone - it comes from Gothic's
compiled Daedalus scripts - so this reads a small, user-maintained JSON
file instead of guessing.
"""

import os
import json

ITEM_MESH_MAP_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "asset_catalog", "item_mesh_map.json",
)

_cache = None


def get_item_mesh_map():
    global _cache
    if _cache is None:
        _cache = {}
        if os.path.isfile(ITEM_MESH_MAP_PATH):
            with open(ITEM_MESH_MAP_PATH, "r") as f:
                data = json.load(f)
            _cache = {k: v for k, v in data.items() if not k.startswith("_")}
    return _cache


def resolve_item_mesh_name(instance_name):
    """Returns the mesh filename (no extension) mapped to this item
    instance name, or None if no mapping is known yet."""
    return get_item_mesh_map().get(instance_name)


def reload_item_mesh_map():
    global _cache
    _cache = None
    return get_item_mesh_map()
