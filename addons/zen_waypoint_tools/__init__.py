bl_info = {
    "name": "Zen Waypoint Tools",
    "author": "jaxub",
    "version": (2, 4, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > ZenGin",
    "description": "Place, link, and visualize zCWaypoint objects, add other ZenGin VOBs, preview their meshes, and export to an uncompiled ZEN",
    "category": "Object",
}

import bpy # pyright: ignore[reportMissingImports]

from . import preferences
from . import waypoint_links
from . import viewport_draw
from . import waypoint_ops
from . import vob_types
from . import mesh_catalog
from . import vob_ops
from . import mesh_preview
from . import export_ops
from . import panel


classes = (
    preferences.ZenMeshDirectory,
    preferences.ZenWaypointToolsPreferences,
    preferences.ZEN_UL_mesh_directories,
    preferences.ZEN_OT_add_mesh_path,
    preferences.ZEN_OT_add_mesh_path_with_subpaths,
    preferences.ZEN_OT_remove_mesh_path,
    preferences.ZEN_OT_remove_all_mesh_paths,
    waypoint_links.ZenWaypointLinks,
    mesh_catalog.ZenMeshCatalogItem,
    mesh_catalog.ZEN_OT_refresh_mesh_catalog,
    waypoint_ops.ZEN_OT_add_waypoint,
    waypoint_ops.ZEN_OT_link_waypoints,
    waypoint_ops.ZEN_OT_unlink_waypoints,
    waypoint_ops.ZEN_OT_toggle_waypoint_links,
    vob_ops.ZEN_OT_add_vob,
    export_ops.ZEN_OT_export_zen,
    export_ops.ZEN_OT_import_zen,
    mesh_preview.ZEN_OT_load_vob_mesh,
    panel.ZEN_PT_waypoint_tools,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.WindowManager.zen_mesh_catalog = bpy.props.CollectionProperty(type=mesh_catalog.ZenMeshCatalogItem)
    mesh_catalog.refresh_mesh_catalog()

    bpy.types.Object.zen_waypoint_links = bpy.props.PointerProperty(type=waypoint_links.ZenWaypointLinks)

    bpy.types.Scene.zen_show_waypoint_links = bpy.props.BoolProperty(
        name="Show Waypoint Links",
        description="Display waypoint links in the 3D viewport",
        default=True,
    )


def unregister():
    viewport_draw.stop_draw_handler()

    if hasattr(bpy.types.WindowManager, "zen_mesh_catalog"):
        del bpy.types.WindowManager.zen_mesh_catalog

    if hasattr(bpy.types.Scene, "zen_show_waypoint_links"):
        del bpy.types.Scene.zen_show_waypoint_links

    if hasattr(bpy.types.Object, "zen_waypoint_links"):
        del bpy.types.Object.zen_waypoint_links

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
