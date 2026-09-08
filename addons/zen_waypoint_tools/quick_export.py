"""
One-click level export package: exports the selected level mesh
object(s) to .3DS via KrxImpExp's plain-callable exporter, and the whole
scene to an uncompiled ZEN via our own exporter, both placed into a
ready-to-drop _work/Data/... folder structure next to the .blend file.

Layout matches Gothic's real install structure, so the result can be
dragged directly into a Gothic II installation:

    export/
      _work/
        Data/
          Meshes/Level/<mod>/<level_name>.3DS
          Worlds/<mod>/<level_name>_uncompiled.zen
"""

import os
import bpy

from .krximpexp_bridge import get_krx_3ds_exporter
from .export_ops import export_zen_to_path


class ZEN_OT_quick_export_package(bpy.types.Operator):
    bl_idname = "zen.quick_export_package"
    bl_label = "Export Level Package"
    bl_description = (
        "Export the selected mesh object(s) as the level's .3DS and the "
        "whole scene as an uncompiled ZEN, both placed into a ready-to-"
        "drop _work/Data/... folder next to this .blend file"
    )
    bl_options = {'REGISTER'}

    level_name: bpy.props.StringProperty(name="Level Name", default="LEVEL_001")
    mod_name: bpy.props.StringProperty(name="Mod Folder", default="MOD")

    @classmethod
    def poll(cls, context):
        return (
            bpy.data.filepath != ""
            and any(o.type == 'MESH' for o in context.selected_objects)
        )

    @classmethod
    def description(cls, context, properties):
        if bpy.data.filepath == "":
            return "Save the .blend file first - the export folder is created next to it"
        if not any(o.type == 'MESH' for o in context.selected_objects):
            return "Select the level mesh object(s) first (e.g. walls, floor, ceiling)"
        return cls.bl_description

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        mesh_names = [o.name for o in context.selected_objects if o.type == 'MESH']
        col = layout.column()
        col.label(text="Selected level mesh object(s):")
        for name in mesh_names:
            col.label(text=f"  {name}", icon='MESH_DATA')
        layout.separator()
        layout.prop(self, "level_name")
        layout.prop(self, "mod_name")

    def execute(self, context):
        mesh_objs = [o for o in context.selected_objects if o.type == 'MESH']
        if not mesh_objs:
            self.report({'ERROR'}, "Select at least one mesh object to use as the level mesh")
            return {'CANCELLED'}

        blend_dir = os.path.dirname(bpy.data.filepath)
        export_root = os.path.join(blend_dir, "export")
        meshes_dir = os.path.join(export_root, "_work", "Data", "Meshes", "Level", self.mod_name)
        worlds_dir = os.path.join(export_root, "_work", "Data", "Worlds", self.mod_name)
        os.makedirs(meshes_dir, exist_ok=True)
        os.makedirs(worlds_dir, exist_ok=True)

        mesh_path = os.path.join(meshes_dir, f"{self.level_name}.3DS")
        zen_path = os.path.join(worlds_dir, f"{self.level_name}_uncompiled.zen")

        # 1. Export the level mesh. use_local_cs is forced False regardless
        # of object count - a level mesh needs absolute world-space
        # vertex coordinates (matching WORKFLOW.md's explanation of how
        # zCVobLevelCompo's own position is vestigial - the compiled
        # world's placement comes entirely from the mesh's own baked
        # coordinates), not the per-object local origin used for
        # exporting a single reusable prop.
        try:
            krx_3ds_exp = get_krx_3ds_exporter()
            krx_3ds_exp(
                filename=mesh_path,
                selected_objects_param=[o.name for o in mesh_objs],
                use_local_cs=False,
                scale=100,
            )
        except Exception as e:
            self.report({'ERROR'}, f"3DS export failed: {e}")
            return {'CANCELLED'}

        # 2. Make sure a matching zCVobLevelCompo exists, so the ZEN we're
        # about to write actually references the mesh we just exported -
        # easy to forget by hand, and the whole point of this button is
        # to remove manual steps.
        level_compo_name = f"zCVobLevelCompo:{self.level_name}"
        created_level_compo = False
        if level_compo_name not in bpy.data.objects:
            compo_obj = bpy.data.objects.new(level_compo_name, None)
            compo_obj.empty_display_type = 'PLAIN_AXES'
            compo_obj.empty_display_size = 1.0
            compo_obj.rotation_mode = 'QUATERNION'
            context.scene.collection.objects.link(compo_obj)
            created_level_compo = True

        # 3. Export the scene to the uncompiled ZEN, same verified path
        # as the regular Export Uncompiled ZEN button.
        report_type, message = export_zen_to_path(zen_path)

        prefix = f"Created {level_compo_name} at world origin. " if created_level_compo else ""
        self.report(
            {report_type},
            f"{prefix}3DS: {mesh_path}\nZEN: {message}",
        )
        return {'CANCELLED'} if report_type == 'ERROR' else {'FINISHED'}
