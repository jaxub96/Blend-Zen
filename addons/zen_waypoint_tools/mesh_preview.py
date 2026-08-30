import bpy
import os
import mathutils

from .preferences import get_mesh_directories

# ---------------------------------------------------------------------------
# VOB mesh preview - imports the real .MRM for a zCVob prop via KrxImpExp's
# krxmrmimp importer and parents it as a preview under the vob.
# ---------------------------------------------------------------------------

PREVIEW_COLLECTION_NAME = "Zen VOB Previews"


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


class ZEN_OT_load_vob_mesh(bpy.types.Operator):
    bl_idname = "zen.load_vob_mesh"
    bl_label = "Load Mesh Preview"
    bl_description = (
        "Import the real .MRM mesh for the active zCVob prop and parent it "
        "as a preview (does not affect export data)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.name.startswith("zCVob:")

    def execute(self, context):
        vob_obj = context.active_object

        # same name convention as the exporter's own _vob_name(): strip the
        # prefix and anything from the first dot onward
        mesh_name = vob_obj.name[len("zCVob:"):].split(".")[0]

        filepath = find_mesh_file(mesh_name)
        if filepath is None:
            self.report(
                {'WARNING'},
                f"No mesh file found for '{mesh_name}' in configured search paths",
            )
            return {'CANCELLED'}

        clear_existing_preview(vob_obj)

        # krxmrmimp branches on len(operator.files): it needs a populated
        # `files` collection (length 1 for the single-file path) even
        # though that path then re-reads the real target from `filepath`
        # itself. Passing only `filepath` silently no-ops (confirmed by
        # reading KrxMrmImp.py directly - it hits the `else` branch and
        # loops over zero files).
        directory = os.path.dirname(filepath) + os.sep
        filename = os.path.basename(filepath)

        before = set(bpy.data.objects.keys())
        try:
            bpy.ops.import_scene.krxmrmimp(
                filepath=filepath,
                directory=directory,
                files=[{"name": filename}],
            )
        except Exception as e:
            self.report({'ERROR'}, f"krxmrmimp import failed: {e}")
            return {'CANCELLED'}
        after = set(bpy.data.objects.keys())
        new_object_names = after - before

        if not new_object_names:
            self.report({'WARNING'}, "Import ran but no new objects were created")
            return {'CANCELLED'}

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

        # krxmrmimp leaves its newly-imported object as the active/selected
        # one - restore the vob itself so this operator (and others that
        # poll on an active zCVob:) can be re-run immediately without the
        # user having to reselect it by hand.
        for o in context.view_layer.objects:
            o.select_set(False)
        vob_obj.select_set(True)
        context.view_layer.objects.active = vob_obj

        self.report(
            {'INFO'},
            f"Loaded preview for {mesh_name} ({len(new_object_names)} object(s))",
        )
        return {'FINISHED'}
