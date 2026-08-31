import bpy

from .waypoint_links import (
    is_waypoint,
    get_links,
    get_effective_neighbors,
    get_waypoint_display_name,
    LINK_SLOT_COUNT,
)
from .viewport_draw import start_draw_handler, is_draw_handler_active


class ZEN_PT_waypoint_tools(bpy.types.Panel):
    bl_label = "Zen Waypoints"
    bl_idname = "ZEN_PT_waypoint_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZenGin"

    def draw(self, context):
        if context.scene.zen_show_waypoint_links and not is_draw_handler_active():
            start_draw_handler()

        layout = self.layout
        waypoints = [o for o in bpy.data.objects if is_waypoint(o)]

        layout.label(text=f"Waypoints in file: {len(waypoints)}")

        layout.operator("zen.add_waypoint", icon='ADD')

        row = layout.row(align=True)
        row.operator("zen.link_waypoints", icon='LINKED')
        row.operator("zen.unlink_waypoints", icon='UNLINKED')

        layout.separator()

        row = layout.row()
        icon = 'HIDE_OFF' if context.scene.zen_show_waypoint_links else 'HIDE_ON'
        text = "Hide Link Display" if context.scene.zen_show_waypoint_links else "Show Link Display"
        row.operator("zen.toggle_waypoint_links", text=text, icon=icon)

        active = context.active_object
        if is_waypoint(active):
            layout.separator()
            links = get_links(active)
            if links is not None:
                col = layout.column(align=True)
                col.label(text="Link slots (drag objects in directly):")
                col.prop(links, "link_a", text="A")
                col.prop(links, "link_b", text="B")
                col.prop(links, "link_c", text="C")

            neighbors = get_effective_neighbors(active)
            layout.label(text=f"Links: {len(neighbors)}/{LINK_SLOT_COUNT}")
            for target in neighbors:
                layout.label(text=f"- {get_waypoint_display_name(target)}", icon='FORWARD')

        layout.separator()
        row = layout.row(align=True)
        row.label(text="Add Other VOBs:")
        row.operator("zen.refresh_mesh_catalog", text="", icon='FILE_REFRESH')
        layout.operator("zen.add_vob", icon='ADD')

        layout.separator()
        layout.operator("zen.load_vob_mesh", icon='MESH_DATA')

        layout.separator()
        layout.operator("zen.export_zen", icon='EXPORT')
        layout.operator("zen.import_zen", icon='IMPORT')
