"""
Populate the Gothic asset library: for every marked-as-asset Empty
object representing an oCItem (still lacking real geometry), import its
real mesh via KrxImpExp and transplant it onto the same asset identity,
then generate a real preview thumbnail and assign a catalog.

Key API findings worth remembering (verified against a live Blender
session, not assumed):

* Object.data on an EMPTY can only ever be None or an Image - there is
  no way to convert an Empty into a Mesh by reassigning .data in place.
  The correct approach is to import the mesh as its own object, then
  transfer the identity (name, transform, asset metadata, collection
  membership) onto it and delete the old Empty.
* bpy.ops.asset.mark_single() and bpy.ops.ed.lib_id_generate_preview_
  from_object() are context-driven operators with no exposed
  parameters. Run from a script (no real UI event), their poll()
  requires context.id to be explicitly overridden via
  bpy.context.temp_override(id=obj, ...) - active_object/selected_objects
  alone are not enough.
* Preview rendering is an asynchronous background job. Checking pixel
  data immediately after the operator call, in the same script
  execution, will read a still-blank image - Blender's main thread
  can't process the job's completion callback while the script itself
  is still running. This resolves on its own once that script execution
  returns control to Blender's normal event loop - but that is exactly
  why populate_asset_with_mesh() must never be called more than once
  per event-loop tick: doing so from a synchronous loop over multiple
  items queues overlapping async preview jobs before any of them
  finish, which reliably **crashes Blender** (confirmed via a real UI
  button click, not just via script - this is not a theoretical risk).
  ZEN_OT_populate_asset_library_file works around this by never looping
  synchronously: execute() only builds the target list and registers a
  bpy.app.timers callback that processes exactly one item per tick,
  returning a delay so Blender's event loop - and each item's preview
  job - fully settles before the next item starts.

Catalog assignment: blender_assets.cats.txt (a plain, documented text
format - see Blender's developer docs) lives at the asset library root.
Catalog UUIDs are generated deterministically (uuid5 with a fixed
namespace) from the catalog path, so re-running this on the same file
never creates duplicate catalog entries.
"""

import os
import uuid as uuid_module
import bpy

from .item_mesh_map import resolve_item_mesh_name
from .mesh_preview import find_mesh_file
from .krximpexp_bridge import get_krx_mrm_importer
from .preferences import get_asset_library_root

_CATALOG_NAMESPACE = uuid_module.UUID("f1e2d3c4-b5a6-4788-9900-aabbccddeeff")
_NIL_UUID = "00000000-0000-0000-0000-000000000000"


def _catalog_uuid_for_path(path):
    return str(uuid_module.uuid5(_CATALOG_NAMESPACE, path))


def find_library_root(filepath):
    """Prefers the explicitly configured Asset Library Root preference
    (Preferences > Add-ons > Zen Waypoint Tools). Falls back to walking
    upward from filepath looking for an existing blender_assets.cats.txt
    (useful once the library already has one), and finally to the file's
    own directory if neither is available."""
    configured = get_asset_library_root()
    if configured and os.path.isdir(configured):
        return configured

    current = os.path.dirname(os.path.abspath(filepath))
    fallback = current
    for _ in range(6):
        if os.path.isfile(os.path.join(current, "blender_assets.cats.txt")):
            return current
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent
    return fallback


def derive_catalog_path(filepath, library_root):
    """Items/Items_ITMW.blend -> "Items/ITMW" (strips a repeated parent
    folder name prefix from the file's own name, a common convention)."""
    rel = os.path.relpath(filepath, library_root)
    rel_no_ext = os.path.splitext(rel)[0]
    parts = rel_no_ext.replace(os.sep, "/").split("/")
    if len(parts) >= 2 and parts[-1].startswith(parts[-2] + "_"):
        parts[-1] = parts[-1][len(parts[-2]) + 1:]
    return "/".join(parts)


def ensure_catalog_written(library_root, catalog_path):
    """Writes the catalog to blender_assets.cats.txt if not already
    present, and returns its UUID either way."""
    cats_file = os.path.join(library_root, "blender_assets.cats.txt")
    cuuid = _catalog_uuid_for_path(catalog_path)

    lines = []
    if os.path.isfile(cats_file):
        with open(cats_file, "r", encoding="utf-8") as f:
            lines = f.read().splitlines()

    for line in lines:
        if line.startswith(cuuid + ":"):
            return cuuid

    if not lines:
        lines = [
            "# This is an Asset Catalog Definition file for Blender.",
            "#",
            "# Empty lines and lines starting with `#` will be ignored.",
            "# The first non-ignored line should be the version indicator.",
            "# Everything else is a catalog path, ID, and simple name, colon-separated.",
            "",
            "VERSION 1",
            "",
        ]

    simple_name = catalog_path.replace("/", "-")
    lines.append(f"{cuuid}:{catalog_path}:{simple_name}")

    with open(cats_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    return cuuid


def _get_context_override():
    win = bpy.context.window_manager.windows[0]
    area = next((a for a in win.screen.areas if a.type == 'VIEW_3D'), win.screen.areas[0])
    region = next((r for r in area.regions if r.type == 'WINDOW'), None)
    return {"window": win, "screen": win.screen, "area": area, "region": region}


def populate_asset_with_mesh(obj, catalog_id=None):
    """Resolve, import, and transplant the real mesh onto obj's identity
    (name, transform, asset metadata, collection membership), mark it as
    an asset, assign the given catalog if provided, and trigger preview
    generation. Returns (ok, message)."""
    instance_name = obj.name.split(":", 1)[-1].split(".")[0]
    mesh_name = resolve_item_mesh_name(instance_name)
    if mesh_name is None:
        return False, f"no mesh mapping for '{instance_name}'"

    filepath = find_mesh_file(mesh_name)
    if filepath is None:
        return False, f"mesh file '{mesh_name}' not found in configured directories"

    before = set(bpy.data.objects.keys())
    try:
        get_krx_mrm_importer()(filename=filepath, scale=0.01)
    except Exception as e:
        return False, f"import failed: {e}"
    after = set(bpy.data.objects.keys())
    new_names = list(after - before)
    mesh_objs = [bpy.data.objects[n] for n in new_names if bpy.data.objects[n].type == 'MESH']
    if not mesh_objs:
        for n in new_names:
            bpy.data.objects.remove(bpy.data.objects[n], do_unlink=True)
        return False, "import produced no mesh object"
    imported_mesh_obj = mesh_objs[0]

    original_name = obj.name
    original_location = obj.location.copy()
    original_collections = list(obj.users_collection)
    had_asset_data = obj.asset_data is not None
    existing_catalog_id = obj.asset_data.catalog_id if had_asset_data else None
    existing_description = obj.asset_data.description if had_asset_data else None

    bpy.data.objects.remove(obj, do_unlink=True)

    imported_mesh_obj.name = original_name
    imported_mesh_obj.location = original_location
    imported_mesh_obj.rotation_mode = 'QUATERNION'

    for coll in list(imported_mesh_obj.users_collection):
        coll.objects.unlink(imported_mesh_obj)
    for coll in original_collections:
        coll.objects.link(imported_mesh_obj)

    for n in new_names:
        o = bpy.data.objects.get(n)
        if o is not None and o != imported_mesh_obj:
            bpy.data.objects.remove(o, do_unlink=True)

    imported_mesh_obj.select_set(True)
    bpy.context.view_layer.objects.active = imported_mesh_obj

    ctx = _get_context_override()
    with bpy.context.temp_override(**ctx, id=imported_mesh_obj):
        bpy.ops.asset.mark_single()

    # prefer an already-set real catalog over the derived default, so
    # re-running this doesn't clobber deliberate manual organization
    if had_asset_data and existing_catalog_id and existing_catalog_id != _NIL_UUID:
        imported_mesh_obj.asset_data.catalog_id = existing_catalog_id
    elif catalog_id:
        # catalog_simple_name is read-only (auto-derived by Blender from
        # catalog_id via the loaded catalog definitions) - only catalog_id
        # is ever settable directly
        imported_mesh_obj.asset_data.catalog_id = catalog_id
    if had_asset_data and existing_description:
        imported_mesh_obj.asset_data.description = existing_description

    with bpy.context.temp_override(**ctx, id=imported_mesh_obj, active_object=imported_mesh_obj, object=imported_mesh_obj):
        bpy.ops.ed.lib_id_generate_preview_from_object()

    return True, mesh_name


# Module-level state for the background timer job below. A single dict
# instance (not per-operator-call locals) so the timer callback - which
# Blender calls with no arguments and no operator context - can find it.
_populate_job = {"active": False}


def _process_next_asset():
    """bpy.app.timers callback: pops and processes one target per tick.

    Doing exactly one item per timer tick (instead of looping over all
    targets inside a single execute() call) is the actual fix for a real
    crash: back-to-back import + mark_single + generate_preview calls for
    multiple items in one Python call never let Blender's event loop run
    between them, which queues overlapping async preview-render jobs and
    reliably crashes Blender (confirmed via a real button click, not just
    when driven by a script). Returning a delay here instead of looping
    lets the event loop - and each item's async preview job - fully
    settle before the next import starts."""
    job = _populate_job
    targets = job["targets"]

    if not targets:
        succeeded, failed = job["succeeded"], job["failed"]
        print(f"[Zen Asset Library] Populated {len(succeeded)}/{len(succeeded) + len(failed)} "
              f"asset(s) in catalog '{job['catalog_path']}'")
        for n, m in failed:
            print(f"[Zen Asset Library]   FAILED {n}: {m}")
        bpy.ops.wm.save_mainfile()
        print("[Zen Asset Library] Final save complete.")
        job["active"] = False
        return None

    obj = targets.pop(0)
    # capture the name before calling - on success the original object is
    # deleted internally as part of the identity transfer, so obj.name
    # would be a freed reference afterward
    original_name = obj.name
    try:
        ok, msg = populate_asset_with_mesh(obj, catalog_id=job["catalog_id"])
    except Exception as e:
        ok, msg = False, f"exception: {e}"
    (job["succeeded"] if ok else job["failed"]).append((original_name, msg))

    total_done = len(job["succeeded"]) + len(job["failed"])
    print(f"[Zen Asset Library] ({total_done}/{job['total']}) {original_name}: "
          f"{'ok' if ok else 'FAILED - ' + msg}")

    if job["save_every"] and total_done % job["save_every"] == 0:
        bpy.ops.wm.save_mainfile()
        print(f"[Zen Asset Library] Progress saved ({total_done} processed so far)")

    return 0.5  # seconds until the next tick


class ZEN_OT_populate_asset_library_file(bpy.types.Operator):
    bl_idname = "zen.populate_asset_library_file"
    bl_label = "Populate Asset Previews (This File)"
    bl_description = (
        "For every marked-as-asset Empty in the current file (oCItem "
        "placeholders), import its real mesh, generate a preview "
        "thumbnail, and assign a catalog based on this file's name/folder. "
        "Runs in the background one item at a time - watch the system "
        "console for progress"
    )
    bl_options = {'REGISTER'}

    max_count: bpy.props.IntProperty(
        name="Max Count (0 = all)",
        description="Process at most this many assets, useful for testing "
                    "a small batch before running the whole file. 0 processes "
                    "everything still needing geometry.",
        default=0,
        min=0,
    )

    save_every: bpy.props.IntProperty(
        name="Save Every N Items",
        description="Auto-save the file after every N processed assets "
                    "(0 disables auto-save). Guards against losing a large "
                    "batch's progress if Blender is closed or crashes mid-run",
        default=15,
        min=0,
    )

    @classmethod
    def poll(cls, context):
        return bpy.data.filepath != "" and not _populate_job["active"]

    def execute(self, context):
        library_root = find_library_root(bpy.data.filepath)
        catalog_path = derive_catalog_path(bpy.data.filepath, library_root)
        catalog_id = ensure_catalog_written(library_root, catalog_path)

        targets = [
            o for o in list(bpy.data.objects)
            if o.asset_data is not None and o.type == 'EMPTY' and o.name.startswith("oCItem:")
        ]
        if self.max_count > 0:
            targets = targets[:self.max_count]

        if not targets:
            self.report({'INFO'}, "No placeholder assets left to populate")
            return {'FINISHED'}

        _populate_job.update(
            active=True,
            targets=targets,
            total=len(targets),
            succeeded=[],
            failed=[],
            catalog_id=catalog_id,
            catalog_path=catalog_path,
            save_every=self.save_every,
        )
        bpy.app.timers.register(_process_next_asset)
        self.report({'INFO'}, f"Started populating {len(targets)} asset(s) in the "
                               f"background - watch the system console for progress")
        return {'FINISHED'}
