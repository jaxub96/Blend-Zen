import bpy
import os
import mathutils

from .preferences import get_mesh_directories
from .krximpexp_bridge import get_krx_mrm_importer
from .item_mesh_map import resolve_item_mesh_name

# ---------------------------------------------------------------------------
# VOB mesh preview - imports the real .MRM for a zCVob prop or oCItem via
# KrxImpExp's importer and parents it as a preview under the vob.
#
# zCVob: object name IS the mesh filename directly (matches the
# exporter's own convention).
# oCItem: object name is the script instance name, which is NOT
# generally the mesh filename - resolved via item_mesh_map.json instead.
# See item_mesh_map.py for why this can't just be inferred from the name.
# ---------------------------------------------------------------------------

PREVIEW_COLLECTION_NAME = "Zen VOB Previews"
_PREVIEWABLE_PREFIXES = ("zCVob:", "oCItem:")


def find_mesh_file(mesh_name):
    """Case-insensitive search for <mesh_name>.MRM across the directories
    configured in Preferences > Add-ons > Zen Waypoint Tools, first
    configured directory wins. Returns a path or None."""
    target = f"{mesh_name}.mrm".lower()
    for directory in get_mesh_directories():
        if not os.path.isdir(directory):
            continue
        for filename in os.listdir(directory):
            if filename.lower() == target:
                return os.path.join(directory, filename)
    return None


def get_preview_collection(context):
    coll = bpy.data.collections.get(PREVIEW_COLLECTION_NAME)
    if coll is None:
        coll = bpy.data.collections.new(PREVIEW_COLLECTION_NAME)
        context.scene.collection.children.link(coll)
    return coll


def clear_existing_preview(vob_obj):
    """Remove any previously-loaded preview mesh(es) for this vob, so
    reloading replaces rather than duplicates."""
    for child in list(vob_obj.children):
        if child.get("zen_is_preview"):
            bpy.data.objects.remove(child, do_unlink=True)


def _has_preview(vob_obj):
    return any(child.get("zen_is_preview") for child in vob_obj.children)


def load_preview_for_vob(context, vob_obj):
    """Core of "Load Mesh Preview", shared by the single-object and batch
    operators below. Returns (status, message):

      status is 'loaded', 'no_mapping', 'not_found', or 'import_failed'.
      message is a ready-to-report string - the full helpful text for the
      failure cases, or "Loaded preview for X (N object(s))" on success.

    Leaves scene selection untouched (krxmrmimp changes it) - callers that
    want the vob re-selected afterward (the single-object operator) do
    that themselves, since a batch run doesn't want a different object
    ending up active after every single import.
    """
    # same name convention as the exporter's own _vob_name(): strip the
    # prefix and anything from the first dot onward
    prefix = next(p for p in _PREVIEWABLE_PREFIXES if vob_obj.name.startswith(p))
    raw_name = vob_obj.name[len(prefix):].split(".")[0]

    if prefix == "oCItem:":
        mesh_name = resolve_item_mesh_name(raw_name)
        if mesh_name is None:
            return "no_mapping", (
                f"No known mesh mapping for item instance '{raw_name}' - "
                f"add one to asset_catalog/item_mesh_map.json (instance "
                f"name -> mesh filename, no extension)"
            )
    else:
        mesh_name = raw_name

    filepath = find_mesh_file(mesh_name)
    if filepath is None:
        return "not_found", f"No mesh file found for '{mesh_name}' in configured search paths"

    clear_existing_preview(vob_obj)

    # The installed KrxImpExp version wraps its bpy.ops entry point
    # (krxmrmimpgui) in an interactive external GUI dialog that can't
    # be driven headlessly - so this calls the plain Python function
    # the addon exposes for exactly this purpose instead. It creates
    # objects directly with no return value, so we diff
    # bpy.data.objects before/after to find what was created.
    before = set(bpy.data.objects.keys())
    try:
        krx_mrm_imp = get_krx_mrm_importer()
        krx_mrm_imp(filename=filepath, scale=0.01)
    except Exception as e:
        return "import_failed", f"MRM import failed for '{mesh_name}': {e}"
    after = set(bpy.data.objects.keys())
    new_object_names = after - before

    if not new_object_names:
        return "import_failed", f"Import of '{mesh_name}' ran but no new objects were created"

    preview_collection = get_preview_collection(context)
    for name in new_object_names:
        imported_obj = bpy.data.objects[name]
        for coll in list(imported_obj.users_collection):
            coll.objects.unlink(imported_obj)
        preview_collection.objects.link(imported_obj)

        # imported mesh always spawns at world origin - we want it to
        # inherit the vob's transform, not preserve its own (identity)
        # world position, so parent_inverse stays identity here
        imported_obj.parent = vob_obj
        imported_obj.matrix_parent_inverse = mathutils.Matrix.Identity(4)
        imported_obj["zen_is_preview"] = True
        if not imported_obj.name.endswith("(preview)"):
            imported_obj.name = f"{imported_obj.name} (preview)"

        # Prevent the preview from ever being selected/moved directly -
        # it's purely a visual, and the vob empty is the only thing the
        # exporter reads. Without this, clicking the visible mesh in
        # the viewport selects the preview instead of the vob, and an
        # accidental grab-move would desync what you see from what
        # actually gets exported, with no warning.
        imported_obj.hide_select = True
        imported_obj.lock_location = (True, True, True)
        imported_obj.lock_rotation = (True, True, True)
        imported_obj.lock_scale = (True, True, True)

    return "loaded", f"Loaded preview for {mesh_name} ({len(new_object_names)} object(s))"


class ZEN_OT_load_vob_mesh(bpy.types.Operator):
    bl_idname = "zen.load_vob_mesh"
    bl_label = "Load Mesh Preview"
    bl_description = (
        "Import the real .MRM mesh for the active zCVob prop or oCItem and "
        "parent it as a preview (does not affect export data)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.name.startswith(_PREVIEWABLE_PREFIXES)

    def execute(self, context):
        vob_obj = context.active_object
        status, message = load_preview_for_vob(context, vob_obj)

        if status != "loaded":
            self.report({'ERROR' if status == 'import_failed' else 'WARNING'}, message)
            return {'CANCELLED'}

        # krxmrmimp leaves its newly-imported object as the active/selected
        # one - restore the vob itself so this operator (and others that
        # poll on an active zCVob:) can be re-run immediately without the
        # user having to reselect it by hand.
        for o in context.view_layer.objects:
            o.select_set(False)
        vob_obj.select_set(True)
        context.view_layer.objects.active = vob_obj

        self.report({'INFO'}, message)
        return {'FINISHED'}


class ZEN_OT_load_all_vob_meshes(bpy.types.Operator):
    bl_idname = "zen.load_all_vob_meshes"
    bl_label = "Load All Mesh Previews"
    bl_description = (
        "Load a mesh preview for every zCVob/oCItem in the scene that "
        "doesn't already have one (enable Force Reload to redo ones that do)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    force_reload: bpy.props.BoolProperty(
        name="Force Reload",
        description="Also reload objects that already have a preview loaded "
                    "(use after a mesh file changes on disk)",
        default=False,
    )

    @classmethod
    def poll(cls, context):
        return any(o.name.startswith(_PREVIEWABLE_PREFIXES) for o in context.scene.objects)

    def execute(self, context):
        targets = [
            o for o in context.scene.objects
            if o.name.startswith(_PREVIEWABLE_PREFIXES) and (self.force_reload or not _has_preview(o))
        ]

        if not targets:
            self.report({'INFO'}, "Nothing to load - every vob already has a preview (try Force Reload)")
            return {'CANCELLED'}

        loaded = 0
        skipped = []
        for vob_obj in targets:
            status, message = load_preview_for_vob(context, vob_obj)
            if status == "loaded":
                loaded += 1
            else:
                skipped.append(f"{vob_obj.name}: {message}")

        # a long per-object failure list doesn't fit in the report popup -
        # the console gets the detail, the popup gets a count and a pointer
        if skipped:
            print("Zen Waypoint Tools - Load All Mesh Previews: skipped objects:")
            for line in skipped:
                print(f"  - {line}")

        summary = f"Loaded {loaded}/{len(targets)} preview(s)"
        if skipped:
            summary += f", {len(skipped)} skipped - see console for details"
        self.report({'INFO'} if loaded else {'WARNING'}, summary)
        return {'FINISHED'}


class ZEN_OT_clear_vob_previews(bpy.types.Operator):
    bl_idname = "zen.clear_vob_previews"
    bl_label = "Clear All Mesh Previews"
    bl_description = (
        "Remove every loaded mesh preview in the scene, leaving the real "
        "vob empties (and everything the exporter reads) untouched"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return any(o.get("zen_is_preview") for o in context.scene.objects)

    def execute(self, context):
        previews = [o for o in context.scene.objects if o.get("zen_is_preview")]
        count = len(previews)
        for obj in previews:
            bpy.data.objects.remove(obj, do_unlink=True)

        self.report({'INFO'}, f"Removed {count} mesh preview(s)")
        return {'FINISHED'}
