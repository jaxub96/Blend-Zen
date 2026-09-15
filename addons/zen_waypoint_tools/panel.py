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
    """Root panel: waypoint authoring plus the active object's own
    properties - the two things relevant on every single selection
    change, so they stay always-visible rather than tucked into a
    collapsible section like the less-frequent tool groups below."""
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


class ZEN_PT_zen_add_vob(bpy.types.Panel):
    bl_label = "Add Other VOBs"
    bl_idname = "ZEN_PT_zen_add_vob"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZenGin"
    bl_parent_id = "ZEN_PT_waypoint_tools"

    def draw(self, context):
        layout = self.layout
        row = layout.row(align=True)
        row.operator("zen.refresh_mesh_catalog", text="", icon='FILE_REFRESH')
        layout.operator("zen.add_vob", icon='ADD')


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


class ZEN_PT_zen_mesh_preview(bpy.types.Panel):
    """Collapsed by default: "Load Mesh Preview" only ever targeted
    zCVob:/oCItem: objects, and those are placed from the Blender asset
    library (Items_ITMW.blend/Props.blend - real geometry already, no
    preview step needed) rather than through Add VOB now. Left in,
    collapsed, for the one case it's still useful: reviewing an imported
    ZEN's vobs (zen_import.py) before matching them to real library
    assets."""
    bl_label = "Mesh Preview (legacy zCVob:/oCItem: review)"
    bl_idname = "ZEN_PT_zen_mesh_preview"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZenGin"
    bl_parent_id = "ZEN_PT_waypoint_tools"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.operator("zen.load_vob_mesh", icon='MESH_DATA')
        row = layout.row(align=True)
        row.operator("zen.load_all_vob_meshes", text="Load All", icon='IMPORT')
        row.operator("zen.clear_vob_previews", text="Clear All", icon='TRASH')


class ZEN_PT_zen_asset_library(bpy.types.Panel):
    """Collapsed by default: one-off asset-library maintenance, not part
    of everyday level authoring - see documentation/ASSET_LIBRARY_HANDOFF.md."""
    bl_label = "Asset Library Tools"
    bl_idname = "ZEN_PT_zen_asset_library"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZenGin"
    bl_parent_id = "ZEN_PT_waypoint_tools"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.operator("zen.populate_asset_library_file", icon='ASSET_MANAGER')
        layout.operator("zen.populate_props_from_catalog", icon='ASSET_MANAGER')
