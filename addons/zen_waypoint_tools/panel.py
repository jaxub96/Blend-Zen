import bpy

from .waypoint_links import is_waypoint, get_links, get_effective_neighbors
from .mob_props import mob_type_of, fields_for, missing_fields


class ZEN_PT_waypoint_tools(bpy.types.Panel):
    """Root panel: waypoint authoring plus the active object's own
    settings - both relevant on every selection change, so always visible."""
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

        vob_type = mob_type_of(active)
        if vob_type is not None:
            layout.separator()
            box = layout.box()
            box.label(text=f"{vob_type} properties:")
            # Panels can't write ID properties while drawing, so objects
            # made by hand/older versions get a button to add the fields.
            if missing_fields(active, vob_type):
                box.operator("zen.init_vob_properties", icon='ADD')
            col = box.column(align=True)
            for key in fields_for(vob_type):
                if key in active.keys():
                    col.prop(active, f'["{key}"]', text=key.replace("_", " ").title())


class ZEN_PT_zen_add_vob(bpy.types.Panel):
    bl_label = "Add Other VOBs"
    bl_idname = "ZEN_PT_zen_add_vob"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZenGin"
    bl_parent_id = "ZEN_PT_waypoint_tools"

    def draw(self, context):
        layout = self.layout
        layout.operator("zen.add_vob", icon='ADD')
        layout.operator("zen.use_gothic_sky", icon='LIGHT_SUN')


class ZEN_PT_zen_export(bpy.types.Panel):
    bl_label = "Export / Import"
    bl_idname = "ZEN_PT_zen_export"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZenGin"
    bl_parent_id = "ZEN_PT_waypoint_tools"

    def draw(self, context):
        layout = self.layout
        layout.operator("zen.export_zen", icon='EXPORT')
        layout.operator("zen.import_zen", icon='IMPORT')
        layout.separator()
        layout.operator("zen.quick_export_package", icon='PACKAGE')
