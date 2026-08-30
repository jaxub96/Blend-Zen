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
