import bpy
import os

from .preferences import get_mesh_directories

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
