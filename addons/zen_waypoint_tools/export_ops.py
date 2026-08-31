import bpy

from bpy_extras.io_utils import ExportHelper


class ZEN_OT_export_zen(bpy.types.Operator, ExportHelper):
    bl_idname = "zen.export_zen"
    bl_label = "Export Uncompiled ZEN"
    bl_description = (
        "Export the current scene's vobs, waypoints and startpoint as an "
        "uncompiled .ZEN file (open it in Spacer, compile world/light, "
        "then save as compiled to get a playable world)"
    )
    bl_options = {'REGISTER'}

    filename_ext = ".ZEN"
    filter_glob: bpy.props.StringProperty(
        default="*.ZEN;*.zen",
        options={'HIDDEN'},
    )
    filepath: bpy.props.StringProperty(
        default="UNCOMPILED_EXPORT.ZEN",
        subtype='FILE_PATH',
    )

    def execute(self, context):
        try:
            from zen_gin_export import ZenArchive, FilePrinter
        except ImportError as e:
            self.report(
                {'ERROR'},
                f"Could not import zen_gin_export ({e}). Check that its "
                f"Script Directory is set up and Blender has been restarted "
                f"since it was added.",
            )
            return {'CANCELLED'}

        printer = FilePrinter(self.filepath)
        archive = ZenArchive(bpy.data.objects, printer)
        archive.print()
        printer.close()

        # Structural self-check: verifies object-index contiguity against
        # the header's claimed count. This is the same check that was
        # originally written ad hoc while debugging a real exported file -
        # now it runs automatically on every export instead of only when
        # someone happens to go looking for a problem.
        try:
            from zen_gin_export import verify_archive_file
            verification = verify_archive_file(self.filepath)
        except Exception as e:
            self.report({'WARNING'}, f"Export finished, but the verify step itself failed: {e}")
            return {'FINISHED'}

        if verification.ok:
            self.report(
                {'INFO'},
                f"Exported uncompiled ZEN to {self.filepath} "
                f"({verification.header_object_count} objects, verified OK)",
            )
        else:
            self.report(
                {'WARNING'},
                f"Exported to {self.filepath}, but the archive verifier found "
                f"issues: {'; '.join(verification.issues)}",
            )
        return {'FINISHED'}


from bpy_extras.io_utils import ImportHelper
from . import zen_import


class ZEN_OT_import_zen(bpy.types.Operator, ImportHelper):
    bl_idname = "zen.import_zen"
    bl_label = "Import Uncompiled ZEN"
    bl_description = (
        "Reconstruct vobs and the waynet from an uncompiled .ZEN file "
        "(produced by this package's own exporter) as Blender objects. "
        "Level mesh loading is best-effort: only looks in the ZEN's own "
        "directory, and only compiled .MRM meshes can actually be "
        "imported - a found .3ds is reported but not loaded."
    )
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".ZEN"
    filter_glob: bpy.props.StringProperty(
        default="*.ZEN;*.zen",
        options={'HIDDEN'},
    )

    def execute(self, context):
        try:
            report = zen_import.import_zen(context, self.filepath)
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {e}")
            return {'CANCELLED'}

        message = "Imported {} vob(s), {} waypoint(s), {} link(s)".format(
            report["vobs_created"], report["waypoints_created"], report["ways_linked"],
        )
        status = report["level_mesh_status"]
        if status == "imported":
            message += f" - level mesh loaded from {report['level_mesh_path']}"
        elif status == "found_not_importable":
            message += (
                f" - level mesh found ({report['level_mesh_path']}) but "
                f"couldn't be imported (no working importer for this format)"
            )
        elif status == "not_found":
            message += " - referenced level mesh not found next to the ZEN"

        self.report({'INFO'}, message)
        return {'FINISHED'}
