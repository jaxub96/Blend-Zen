import bpy
import os

from .preferences import get_mesh_directories
from .item_mesh_map import get_item_mesh_map

# Item meshes follow Gothic's "ITxx_..." naming convention (ITMW = melee
# weapon, ITAR = armor, ITRU = rune, ITSC = scroll, ITMI = misc, etc.) -
# every category code starts with "IT". This is used to split the
# scanned .MRM files into two separate search catalogs: one for zCVob
# static props, one for oCItem pickupables, so item meshes don't clutter
# the prop dropdown (and vice versa).
_ITEM_MESH_PREFIX = "IT"


def _is_item_mesh(name):
    return name.upper().startswith(_ITEM_MESH_PREFIX)


class ZenMeshCatalogItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()


def refresh_mesh_catalog():
    """(Re)populate the searchable prop-mesh and item-mesh name lists by
    scanning every directory configured in Preferences > Add-ons > Zen
    Waypoint Tools for .MRM files, split by the ITxx item-mesh naming
    convention. Safe to call any time the directory list or its contents
    change. Returns (prop_count, item_count)."""
    wm = bpy.context.window_manager
    wm.zen_mesh_catalog.clear()
    wm.zen_item_catalog.clear()

    prop_count = 0
    item_count = 0
    seen_props = set()
    seen_items = set()

    for directory in get_mesh_directories():
        if not os.path.isdir(directory):
            continue
        for filename in os.listdir(directory):
            if not filename.lower().endswith(".mrm"):
                continue
            name = os.path.splitext(filename)[0]

            if _is_item_mesh(name):
                if name in seen_items:
                    continue
                seen_items.add(name)
                item = wm.zen_item_catalog.add()
                item.name = name
                item_count += 1
            else:
                if name in seen_props:
                    continue
                seen_props.add(name)
                item = wm.zen_mesh_catalog.add()
                item.name = name
                prop_count += 1

    return prop_count, item_count


class ZEN_OT_refresh_mesh_catalog(bpy.types.Operator):
    bl_idname = "zen.refresh_mesh_catalog"
    bl_label = "Refresh Asset Catalog"
    bl_description = "Rescan configured mesh directories for the prop and item name search lists"
    bl_options = {'REGISTER'}

    def execute(self, context):
        prop_count, item_count = refresh_mesh_catalog()
        self.report(
            {'INFO'},
            f"Loaded {prop_count} prop mesh name(s) and {item_count} item mesh name(s) "
            f"from configured directories",
        )
        return {'FINISHED'}

def refresh_item_instance_catalog():
    wm = bpy.context.window_manager
    wm.zen_item_instance_catalog.clear()

    for instance_name in sorted(get_item_mesh_map()):
        item = wm.zen_item_instance_catalog.add()
        item.name = instance_name


_GENERIC_MESH_DIRS = ("_compiled", "_intern")
PROP_FALLBACK_CATEGORY = "Mobs/Uncategorized"


def _category_for_dir(directory):
    """Everything after the last "Meshes" path segment, e.g.
    ".../Data/Meshes/Mobs/Misc/" -> "Mobs/Misc". Returns None for
    directories with no real categorization value: outside any
    "Meshes" tree, the bare Meshes root itself, or one of the flat
    aggregate dump folders (_compiled/_intern - these hold every
    *compiled* .mrm with no subfolder structure at all; the real
    per-category info only lives on the uncompiled .3ds sources under
    Mobs/Level/Magic/etc, which is what this is for)."""
    parts = os.path.normpath(directory).split(os.sep)
    lowered = [p.lower() for p in parts]
    if "meshes" not in lowered:
        return None
    idx = len(lowered) - 1 - lowered[::-1].index("meshes")
    rel = parts[idx + 1:]
    if not rel or rel[0] in _GENERIC_MESH_DIRS:
        return None
    return "/".join(rel)


def build_prop_category_map(names):
    """Maps each of `names` (case-insensitive) to a "Mobs/Misc"-style
    catalog path, by matching it against a same-named file (any
    extension - Gothic's compiled .mrm meshes are dumped flatly with no
    folders, but the uncompiled .3ds sources they're modeled from are
    organized into meaningful subfolders) anywhere under the configured
    mesh directories. Names with no such match (e.g. INVISIBLE_ZCVOB,
    SKYDOME_LAYER1, CAMERA - engine markers with no real prop folder)
    are simply absent from the returned dict; look up with
    dict.get(name.upper(), PROP_FALLBACK_CATEGORY)."""
    name_set = {n.upper() for n in names}
    mapping = {}
    for directory in get_mesh_directories():
        category = _category_for_dir(directory)
        if category is None or not os.path.isdir(directory):
            continue
        for filename in os.listdir(directory):
            base = os.path.splitext(filename)[0].upper()
            if base in name_set and base not in mapping:
                mapping[base] = category
    return mapping