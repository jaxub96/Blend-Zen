import bpy

from .waypoint_links import (
    is_waypoint,
    get_links,
    get_effective_neighbors,
    get_waypoint_display_name,
    LINK_SLOT_COUNT,
)
from .viewport_draw import start_draw_handler, is_draw_handler_active
from .mob_props import mob_type_of, fields_for, init_mob_properties


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

        mob_type = mob_type_of(active)
        if mob_type is not None:
            layout.separator()
            fields = fields_for(mob_type)
            init_mob_properties(active, mob_type, fields)  # self-heals older/imported objects
            box = layout.box()
            box.label(text=f"{mob_type} properties:")
            col = box.column(align=True)
            for key in fields:
                col.prop(active, f'["{key}"]', text=key.replace("_", " ").title())

        layout.separator()
        row = layout.row(align=True)
        row.label(text="Add Other VOBs:")
        row.operator("zen.refresh_mesh_catalog", text="", icon='FILE_REFRESH')
        layout.operator("zen.add_vob", icon='ADD')

        layout.separator()
        layout.operator("zen.load_vob_mesh", icon='MESH_DATA')
        row = layout.row(align=True)
        row.operator("zen.load_all_vob_meshes", text="Load All", icon='IMPORT')
        row.operator("zen.clear_vob_previews", text="Clear All", icon='TRASH')

        layout.separator()
        layout.operator("zen.export_zen", icon='EXPORT')
        layout.operator("zen.import_zen", icon='IMPORT')

        layout.separator()
        layout.operator("zen.quick_export_package", icon='PACKAGE')
