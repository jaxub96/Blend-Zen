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

With "Gothic Game Folder" set in the add-on preferences the same two files
go straight into that game folder's _work/Data instead, and "Open in
Spacer" then runs `gothic spacernet <mod>/<level_name>` (gothic-wine):
Spacer.NET starts with File > Open ZEN in the world's folder (it cannot
open a world by itself; opening the uncompiled ZEN compiles it), and the
compiled save you make there becomes the mod's world.
"""

import os
import subprocess
import bpy

from .krximpexp_bridge import get_krx_3ds_exporter
from .export_ops import export_zen_to_path
from .preferences import get_gothic_settings

SPACER_LOG = os.path.expanduser("~/Library/Logs/gothic-spacernet.log")


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
    open_in_spacer: bpy.props.BoolProperty(
        name="Open in Spacer",
        description="After the export, run 'gothic spacernet <level>': Spacer.NET starts with "
                    "File > Open ZEN in the world's folder (opening the uncompiled ZEN compiles it); "
                    "your compiled save becomes the mod's world. Needs Gothic Game Folder in the "
                    "add-on preferences",
        default=False,
    )

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
        game_folder, _ = get_gothic_settings(context)
        layout.label(text="Into: " + (os.path.join(game_folder, "_work", "Data") if game_folder else "export/ next to this .blend"))
        row = layout.row()
        row.enabled = game_folder is not None
        row.prop(self, "open_in_spacer")

    def execute(self, context):
        mesh_objs = [o for o in context.selected_objects if o.type == 'MESH']
        if not mesh_objs:
            self.report({'ERROR'}, "Select at least one mesh object to use as the level mesh")
            return {'CANCELLED'}

        game_folder, gothic_command = get_gothic_settings(context)
        if game_folder:
            if not os.path.isdir(os.path.join(game_folder, "_work", "Data")):
                self.report({'ERROR'}, f"Gothic Game Folder has no _work/Data: {game_folder}")
                return {'CANCELLED'}
            export_root = game_folder
        else:
            export_root = os.path.join(os.path.dirname(bpy.data.filepath), "export")
        meshes_dir = os.path.join(export_root, "_work", "Data", "Meshes", "Level", self.mod_name)
        worlds_dir = os.path.join(export_root, "_work", "Data", "Worlds", self.mod_name)
        os.makedirs(meshes_dir, exist_ok=True)
        os.makedirs(worlds_dir, exist_ok=True)

        mesh_path = os.path.join(meshes_dir, f"{self.level_name}.3DS")
        zen_path = os.path.join(worlds_dir, f"{self.level_name}_uncompiled.zen")

        # 1. Export the level mesh. use_local_cs is forced False regardless
        # of object count - a level mesh needs absolute world-space
        # vertex coordinates (matching README.md "Blender -> Spacer workflow"'s explanation of how
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
        # as the regular Export Uncompiled ZEN button - minus the level
        # compos of other level names. Each export under a new name adds
        # one to the .blend, and each points at its own .3DS: Spacer
        # would load all of those meshes on top of this one.
        other_compos = [o.name for o in bpy.data.objects
                        if o.name.startswith("zCVobLevelCompo:") and o.name != level_compo_name]
        objects = [o for o in bpy.data.objects if o.name not in other_compos]
        report_type, message = export_zen_to_path(zen_path, objects)

        prefix = f"Created {level_compo_name} at world origin. " if created_level_compo else ""
        if other_compos:
            prefix += f"Left out other level compos (you can delete them): {', '.join(other_compos)}. "
        spacer = ""
        if report_type != 'ERROR' and self.open_in_spacer and game_folder:
            spacer = "\n" + self._open_in_spacer(gothic_command)
        self.report(
            {report_type},
            f"{prefix}3DS: {mesh_path}\nZEN: {message}{spacer}",
        )
        return {'CANCELLED'} if report_type == 'ERROR' else {'FINISHED'}

    def _open_in_spacer(self, gothic_command):
        # Runs on after Blender returns: it waits for the compiled save in Spacer,
        # so its output goes to a log and it ends with a macOS notification.
        if not os.path.isfile(gothic_command):
            return f"Not opened in Spacer: gothic command not found: {gothic_command}"
        os.makedirs(os.path.dirname(SPACER_LOG), exist_ok=True)
        with open(SPACER_LOG, "w") as log:
            subprocess.Popen(
                ["/bin/zsh", gothic_command, "spacernet", f"{self.mod_name}/{self.level_name}"],
                stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                start_new_session=True,
            )
        return (f"Starting Spacer.NET: File > Open ZEN, pick {self.level_name}_uncompiled.zen "
                f"(log: {SPACER_LOG})")
