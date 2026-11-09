import bpy

from bpy_extras.io_utils import ExportHelper, ImportHelper

_MISSING_LIBRARY = (
    "Could not import zen_gin_export ({}). Check that this repo is set as a "
    "Script Directory (Preferences > File Paths) and Blender has been "
    "restarted since."
)


def export_zen_to_path(filepath, objects=None):
    """Export + verify, shared by Export Uncompiled ZEN and Export Level
    Package. Returns (report_type, message) for operator.report().

    objects: the Blender objects to export; the current scene's objects
    when None (not bpy.data, which also holds other scenes' objects).
    """
    try:
        from zen_gin_export import ZenArchive, FilePrinter, verify_archive_file, scene_warnings
    except ImportError as e:
        return 'ERROR', _MISSING_LIBRARY.format(e)

    context = bpy.context
    if objects is None:
        objects = list(context.scene.objects)
    # matrix_world of just-moved/created objects is stale until this runs.
    context.view_layer.update()

    try:
        with FilePrinter(filepath) as printer:
            ZenArchive(objects, printer).print()
    except Exception as e:
        return 'ERROR', f"Export failed, nothing written: {e}"

    try:
        verification = verify_archive_file(filepath)
    except Exception as e:
        return 'WARNING', f"Exported to {filepath}, but the verify step itself failed: {e}"
    if not verification.ok:
        return 'WARNING', (
            f"Exported to {filepath}, but the archive verifier found issues: "
            f"{'; '.join(verification.issues)}"
        )

    message = (f"Exported uncompiled ZEN to {filepath} "
               f"({verification.header_object_count} objects, verified OK)")
    warnings = scene_warnings(objects)
    if warnings:
        return 'WARNING', message + ". Check: " + "; ".join(warnings)
    return 'INFO', message


class ZEN_OT_export_zen(bpy.types.Operator, ExportHelper):
    bl_idname = "zen.export_zen"
    bl_label = "Export Uncompiled ZEN"
    bl_description = (
        "Export the current scene's vobs and waynet as an uncompiled .ZEN "
        "file (open it in Spacer, compile world/light, then save as compiled "
        "to get a playable world)"
    )
    bl_options = {'REGISTER'}

    filename_ext = ".ZEN"
    filter_glob: bpy.props.StringProperty(default="*.ZEN;*.zen", options={'HIDDEN'})
    filepath: bpy.props.StringProperty(default="UNCOMPILED_EXPORT.ZEN", subtype='FILE_PATH')

    def execute(self, context):
        report_type, message = export_zen_to_path(self.filepath)
        self.report({report_type}, message)
        return {'CANCELLED'} if report_type == 'ERROR' else {'FINISHED'}


class ZEN_OT_import_zen(bpy.types.Operator, ImportHelper):
    bl_idname = "zen.import_zen"
    bl_label = "Import Uncompiled ZEN"
    bl_description = (
        "Rebuild vobs (with their settings), waypoints and links from a .ZEN "
        "file as Blender objects. The level mesh is loaded too if found "
        "(next to the ZEN, in the matching _work/Data/Meshes/Level folder, "
        "or in the mesh directories from the add-on preferences)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    filename_ext = ".ZEN"
    filter_glob: bpy.props.StringProperty(default="*.ZEN;*.zen", options={'HIDDEN'})

    def execute(self, context):
        try:
            from . import zen_import
        except ImportError as e:
            self.report({'ERROR'}, _MISSING_LIBRARY.format(e))
            return {'CANCELLED'}
        try:
            report = zen_import.import_zen(context, self.filepath)
        except Exception as e:
            self.report({'ERROR'}, f"Import failed: {e}")
            return {'CANCELLED'}

        message = "Imported {} vob(s), {} waypoint(s), {} link(s)".format(
            report["vobs_created"], report["waypoints_created"], report["ways_linked"],
        )
        if report["ways_dropped"]:
            message += f" - {report['ways_dropped']} link(s) dropped (both waypoints already have 3)"
        if report["skipped_types"]:
            skipped = ", ".join(f"{n}x {t}" for t, n in sorted(report["skipped_types"].items()))
            message += f" - skipped unsupported: {skipped}"
        status = report["level_mesh_status"]
        if status == "imported":
            message += f" - level mesh loaded from {report['level_mesh_path']}"
        elif status == "found_not_importable":
            message += (f" - level mesh found ({report['level_mesh_path']}) but couldn't be "
                        f"imported: {report.get('level_mesh_error')}")
        elif status == "not_found":
            message += " - referenced level mesh not found"

        warn = report["skipped_types"] or report["ways_dropped"]
        self.report({'WARNING' if warn else 'INFO'}, message)
        return {'FINISHED'}
