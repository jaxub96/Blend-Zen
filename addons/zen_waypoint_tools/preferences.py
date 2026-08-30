import os
import bpy


class ZenMeshDirectory(bpy.types.PropertyGroup):
    """One configured mesh search directory. Mirrors KrxImpExp's own
    TextureDirectory pattern (path stored in `name`, trailing separator
    normalized on add) for a consistent, familiar UX."""
    name: bpy.props.StringProperty(name="Path")


class ZenWaypointToolsPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    mesh_directories: bpy.props.CollectionProperty(
        name="Mesh directories",
        description="Directories searched for .MRM mesh files, used by "
                    "'Load Mesh Preview' and the Add VOB mesh-name search",
        type=ZenMeshDirectory,
    )

    selected_mesh_dir_entry: bpy.props.IntProperty(
        name="Selected mesh directory",
        default=-1,
        min=-1,
    )

    def draw(self, context):
        layout = self.layout

        total = f"Mesh directories: {len(self.mesh_directories)}"
        if self.selected_mesh_dir_entry in range(len(self.mesh_directories)):
            total += f" | Selected: {self.selected_mesh_dir_entry + 1}"
        layout.label(text=total, icon='OUTLINER')

        split = layout.split(factor=0.70)
        split.scale_y = 1.3

        col_list = split.column()
        col_list.template_list(
            listtype_name="ZEN_UL_mesh_directories",
            list_id="",
            dataptr=self,
            propname="mesh_directories",
            active_dataptr=self,
            active_propname="selected_mesh_dir_entry",
            rows=6,
            maxrows=10,
        )

        col_buttons = split.column()
        col_buttons.operator("zen.add_mesh_path", text="Add path", icon='ADD')
        col_buttons.operator("zen.add_mesh_path_with_subpaths", text="Add path with subpaths", icon='PLUS')
        col_buttons.operator("zen.remove_mesh_path", text="Remove path", icon='REMOVE')
        col_buttons.operator("zen.remove_all_mesh_paths", text="Remove all paths", icon='X')

        layout.separator()
        layout.operator("zen.refresh_mesh_catalog", icon='FILE_REFRESH')


class ZEN_UL_mesh_directories(bpy.types.UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_property, index=0, flt_flag=0):
        layout.label(text=item.name, icon='FILE_FOLDER')


def get_mesh_directories(context=None):
    """Flat list of configured mesh directory paths (strings), for use by
    mesh_catalog.py and mesh_preview.py. Single source of truth."""
    context = context or bpy.context
    prefs = context.preferences.addons[__package__].preferences
    return [d.name for d in prefs.mesh_directories]


def _add_path(context, path):
    if not path:
        return
    path = os.path.join(path, "")  # normalize trailing separator, matches KrxImpExp
    prefs = context.preferences.addons[__package__].preferences
    existing = {d.name for d in prefs.mesh_directories}
    if path not in existing:
        item = prefs.mesh_directories.add()
        item.name = path
        prefs.selected_mesh_dir_entry = len(prefs.mesh_directories) - 1


class ZEN_OT_add_mesh_path(bpy.types.Operator):
    bl_idname = "zen.add_mesh_path"
    bl_label = "Add Mesh Directory"
    bl_description = "Add a directory to search for .MRM mesh files"

    directory: bpy.props.StringProperty(name="Directory Path", subtype='DIR_PATH')

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        _add_path(context, self.directory)
        bpy.ops.wm.save_userpref()
        return {'FINISHED'}


class ZEN_OT_add_mesh_path_with_subpaths(bpy.types.Operator):
    bl_idname = "zen.add_mesh_path_with_subpaths"
    bl_label = "Add Mesh Directory (with subpaths)"
    bl_description = "Add a directory and every subdirectory beneath it"

    directory: bpy.props.StringProperty(name="Directory Path", subtype='DIR_PATH')

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

    def execute(self, context):
        if self.directory:
            for root, _dirs, _files in os.walk(self.directory, followlinks=True):
                _add_path(context, root)
        bpy.ops.wm.save_userpref()
        return {'FINISHED'}


class ZEN_OT_remove_mesh_path(bpy.types.Operator):
    bl_idname = "zen.remove_mesh_path"
    bl_label = "Remove Mesh Directory"
    bl_description = "Remove the selected mesh directory from the list"

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        index = prefs.selected_mesh_dir_entry
        if index in range(len(prefs.mesh_directories)):
            prefs.mesh_directories.remove(index)
            if prefs.selected_mesh_dir_entry >= len(prefs.mesh_directories):
                prefs.selected_mesh_dir_entry = len(prefs.mesh_directories) - 1
        bpy.ops.wm.save_userpref()
        return {'FINISHED'}


class ZEN_OT_remove_all_mesh_paths(bpy.types.Operator):
    bl_idname = "zen.remove_all_mesh_paths"
    bl_label = "Remove All Mesh Directories"
    bl_description = "Remove every configured mesh directory"

    def execute(self, context):
        prefs = context.preferences.addons[__package__].preferences
        prefs.mesh_directories.clear()
        prefs.selected_mesh_dir_entry = -1
        bpy.ops.wm.save_userpref()
        return {'FINISHED'}
