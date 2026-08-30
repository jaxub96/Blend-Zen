import bpy
import os

from .preferences import get_mesh_directories


class ZenMeshCatalogItem(bpy.types.PropertyGroup):
    name: bpy.props.StringProperty()


def refresh_mesh_catalog():
    """(Re)populate the searchable mesh-name list by scanning every
    directory configured in Preferences > Add-ons > Zen Waypoint Tools
    for .MRM files. Safe to call any time the directory list or its
    contents change."""
    wm = bpy.context.window_manager
    wm.zen_mesh_catalog.clear()

    count = 0
    seen = set()
    for directory in get_mesh_directories():
        if not os.path.isdir(directory):
            continue
        for filename in os.listdir(directory):
            if not filename.lower().endswith(".mrm"):
                continue
            name = os.path.splitext(filename)[0]
            if name in seen:
                continue
            seen.add(name)
            item = wm.zen_mesh_catalog.add()
            item.name = name
            count += 1
    return count


class ZEN_OT_refresh_mesh_catalog(bpy.types.Operator):
    bl_idname = "zen.refresh_mesh_catalog"
    bl_label = "Refresh Asset Catalog"
    bl_description = "Rescan configured mesh directories for the name search list"
    bl_options = {'REGISTER'}

    def execute(self, context):
        count = refresh_mesh_catalog()
        self.report({'INFO'}, f"Loaded {count} mesh names from configured directories")
        return {'FINISHED'}
