bl_info = {
    "name": "Zen Waypoint Tools",
    "author": "jaxub",
    "version": (2, 7, 0),
    "blender": (5, 2, 0),
    "location": "View3D > Sidebar > ZenGin",
    "description": "Place, link, and visualize zCWaypoint objects, add other ZenGin VOBs, and export to an uncompiled ZEN",
    "category": "Object",
}

import bpy  # pyright: ignore[reportMissingImports]

from . import preferences
from . import waypoint_links
from . import viewport_draw
from . import waypoint_ops
from . import vob_ops
from . import gothic_sky
from . import export_ops
from . import quick_export
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
    waypoint_ops.ZEN_OT_add_waypoint,
    waypoint_ops.ZEN_OT_link_waypoints,
    waypoint_ops.ZEN_OT_unlink_waypoints,
    waypoint_ops.ZEN_OT_toggle_waypoint_links,
    waypoint_ops.ZEN_OT_update_waypoint_display,
    vob_ops.ZEN_OT_add_vob,
    vob_ops.ZEN_OT_init_vob_properties,
    vob_ops.ZEN_OT_apply_mob_preset,
    gothic_sky.ZEN_OT_use_gothic_sky,
    export_ops.ZEN_OT_export_zen,
    export_ops.ZEN_OT_import_zen,
    quick_export.ZEN_OT_quick_export_package,
    panel.ZEN_PT_waypoint_tools,
    panel.ZEN_PT_zen_add_vob,
    panel.ZEN_PT_zen_export,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.zen_waypoint_links = bpy.props.PointerProperty(type=waypoint_links.ZenWaypointLinks)
    bpy.types.Scene.zen_show_waypoint_links = bpy.props.BoolProperty(
        name="Show Waypoint Links",
        description="Display waypoint links in the 3D viewport",
        default=True,
    )
    viewport_draw.register()


def unregister():
    viewport_draw.unregister()
    del bpy.types.Scene.zen_show_waypoint_links
    del bpy.types.Object.zen_waypoint_links
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
