"""Run the addon's own Export Uncompiled ZEN / Export Level Package
operators from Blender's command line, with no UI - the automatable
leg of documentation/E2E_TEST_PLAN.md's pipeline (everything up to
Spacer, which has no known scripting interface).

Requires "Zen Waypoint Tools" to already be enabled for the Blender
profile this runs under (enabled-addon state is stored in Blender's
user preferences, which --background mode loads the same as a normal
session) - this script does not enable it for you.

Usage (zen-only export, always safe - see E2E_TEST_PLAN.md's
automation table on why the mesh-export leg below is unconfirmed):

    blender <path-to.blend> --background --python export_headless.py -- \
        zen <output_uncompiled.zen>

Usage (full level package - mesh .3DS + zCVobLevelCompo + zen, same as
clicking "Export Level Package" - UNCONFIRMED headless-safe, see
E2E_TEST_PLAN.md, because it also drives KrxImpExp's mesh exporter):

    blender <path-to.blend> --background --python export_headless.py -- \
        package <level_name> <mod_name>

Either form calls the exact same operator the UI button calls
(bpy.ops.zen.export_zen / bpy.ops.zen.quick_export_package), executed
directly rather than through invoke() - operator reports print to
stdout in background mode, so failures are visible in the calling
script's captured output.
"""
import sys

import bpy


def _script_args():
    argv = sys.argv
    if "--" not in argv:
        return []
    return argv[argv.index("--") + 1:]


def main():
    args = _script_args()
    if not args:
        raise SystemExit(__doc__)

    mode = args[0]

    if mode == "zen":
        if len(args) != 2:
            raise SystemExit("Usage: ... -- zen <output_uncompiled.zen>")
        output_path = args[1]
        result = bpy.ops.zen.export_zen(filepath=output_path)
        if result != {'FINISHED'}:
            raise SystemExit(f"[export_headless] zen export did not finish: {result}")
        print(f"[export_headless] Exported uncompiled ZEN to {output_path}")

    elif mode == "package":
        if len(args) != 3:
            raise SystemExit("Usage: ... -- package <level_name> <mod_name>")
        level_name, mod_name = args[1], args[2]

        mesh_objs = [o for o in bpy.context.selected_objects if o.type == 'MESH']
        if not mesh_objs:
            raise SystemExit(
                "[export_headless] No mesh objects selected in the .blend's saved "
                "selection state - Export Level Package needs the level mesh "
                "object(s) selected. Save the .blend with them selected, or switch "
                "to the 'zen' mode above and handle the .3DS export separately."
            )

        result = bpy.ops.zen.quick_export_package(level_name=level_name, mod_name=mod_name)
        if result != {'FINISHED'}:
            raise SystemExit(f"[export_headless] package export did not finish: {result}")
        print(f"[export_headless] Exported level package for '{level_name}' (mod '{mod_name}')")

    else:
        raise SystemExit(f"Unknown mode '{mode}' - expected 'zen' or 'package'")


main()
