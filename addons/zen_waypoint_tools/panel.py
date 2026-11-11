import bpy

from .waypoint_links import is_waypoint, get_links, get_effective_neighbors


class ZEN_PT_waypoint_tools(bpy.types.Panel):
    """Root panel: waypoint authoring. The active vob's settings are the
    VOB Settings sub-panel (vob_ui.py)."""
    bl_label = "Zen Waypoints"
    bl_idname = "ZEN_PT_waypoint_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZenGin"

    def draw(self, context):
        layout = self.layout
        scene_objects = context.scene.objects
        waypoints = [o for o in scene_objects if is_waypoint(o)]

        layout.label(text=f"Waypoints in scene: {len(waypoints)}")
        layout.operator("zen.add_waypoint", icon='ADD')
        row = layout.row(align=True)
        row.operator("zen.link_waypoints", icon='LINKED')
        row.operator("zen.unlink_waypoints", icon='UNLINKED')

        layout.separator()
        shown = context.scene.zen_show_waypoint_links
        layout.operator("zen.toggle_waypoint_links",
                        text="Hide Link Display" if shown else "Show Link Display",
                        icon='HIDE_OFF' if shown else 'HIDE_ON')

        # Only offered while older-style (pre-csys) waypoints remain.
        if any(o.type == 'EMPTY' and o.empty_display_type != 'ARROWS' for o in waypoints):
            layout.operator("zen.update_waypoint_display", icon='ORIENTATION_GLOBAL')

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
            neighbors = get_effective_neighbors(active, waypoints)
            layout.label(text=f"Connected to {len(neighbors)} waypoint(s):")
            for target in neighbors:
                layout.label(text=f"- {target.name}", icon='FORWARD')


class ZEN_PT_zen_add_vob(bpy.types.Panel):
    bl_label = "Add Other VOBs"
    bl_idname = "ZEN_PT_zen_add_vob"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZenGin"
    bl_parent_id = "ZEN_PT_waypoint_tools"
    bl_order = 1

    def draw(self, context):
        layout = self.layout
        layout.operator("zen.add_vob", icon='ADD')
        layout.prop(context.scene, "zen_show_trigger_links")
        layout.operator("zen.load_vob_previews", icon='MESH_DATA')
        layout.operator("zen.use_gothic_sky", icon='LIGHT_SUN')
        layout.operator("zen.reload_game_data", icon='FILE_REFRESH')


class ZEN_PT_zen_export(bpy.types.Panel):
    bl_label = "Export / Import"
    bl_idname = "ZEN_PT_zen_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZenGin"
    bl_parent_id = "ZEN_PT_waypoint_tools"
    bl_order = 2

    def draw(self, context):
        layout = self.layout
        layout.operator("zen.export_zen", icon='EXPORT')
        layout.operator("zen.import_zen", icon='IMPORT')
        layout.separator()
        layout.operator("zen.quick_export_package", icon='PACKAGE')
