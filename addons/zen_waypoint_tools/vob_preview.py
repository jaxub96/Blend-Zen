"""
Preview meshes for vobs that are empties (everything Import ZEN creates).

The empty stays what it is - same name, same settings, same export - and is
only told to draw a mesh: it instances a small collection holding that mesh
(Object Properties > Instancing > Collection). Those collections are named
"ZenPreview:<name>", are not part of the scene and are shared by all vobs
with the same visual, so a forest of 300 trees stores one tree.

Where the mesh comes from, in order:
  1. the asset libraries from Blender's preferences: an object named like
     the vob ("zCVob:NW_HARBOUR_BARREL_01", "oCItem:ITFO_APPLE") or like
     its visual. The mesh is linked, not copied;
  2. optionally the game's source meshes (<game>/_work/Data/Meshes/**/X.3DS),
     loaded with KrxImpExp. Slower, one import per distinct visual.
Animated models (.ASC / .MDS mobs) only exist compiled in the game files and
cannot be loaded; they preview only when an asset library has them.
"""

import glob
import os

import bpy
import mathutils

from .mob_props import vob_type_of
from .preferences import get_gothic_settings
from .krximpexp_bridge import get_krx_3ds_importer

PREVIEW_PREFIX = "ZenPreview:"
_NO_MESH_EXTENSIONS = (".PFX", ".TGA")
_LIBRARY_PREFIXES = ("zCVob:", "oCItem:", "oCMob", "oCMOB:", "zCMover:")

_library_index = None        # NAME -> (blend path, object name in that file)
_game_mesh_index = None      # STEM -> path of a .3DS
_game_mesh_folder = None


def reset_indexes():
    global _library_index, _game_mesh_index
    _library_index = None
    _game_mesh_index = None


def library_index():
    """Vob-named object assets in all asset libraries, by upper-case name."""
    global _library_index
    if _library_index is not None:
        return _library_index
    _library_index = {}
    for library in bpy.context.preferences.filepaths.asset_libraries:
        pattern = os.path.join(bpy.path.abspath(library.path), "**", "*.blend")
        for blend in sorted(glob.glob(pattern, recursive=True)):
            try:
                with bpy.data.libraries.load(blend, assets_only=True) as (source, _):
                    names = list(source.objects)
            except Exception:
                continue                    # unreadable or newer-version file
            for name in names:
                if name.startswith(_LIBRARY_PREFIXES):
                    _library_index.setdefault(name.upper(), (blend, name))
    return _library_index


def game_mesh_index(context=None):
    """Source .3DS meshes of the configured game folder, by upper-case stem."""
    global _game_mesh_index, _game_mesh_folder
    folder, _ = get_gothic_settings(context)
    if _game_mesh_index is not None and folder == _game_mesh_folder:
        return _game_mesh_index
    _game_mesh_index, _game_mesh_folder = {}, folder
    try:
        from zen_gin_export.game_data import find_data_dir
    except ImportError:
        return _game_mesh_index
    data = find_data_dir(folder) if folder else None
    if data:
        for root, _dirs, files in os.walk(data):
            if os.path.basename(root).lower() == "level":
                _dirs[:] = []               # level meshes are not vob visuals
                continue
            for filename in files:
                stem, extension = os.path.splitext(filename)
                if extension.lower() == ".3ds":
                    _game_mesh_index.setdefault(stem.upper(), os.path.join(root, filename))
    return _game_mesh_index


def visual_of(obj):
    """(vob name, visual stem, visual extension) for a vob object; the stem
    is None when the vob shows no mesh."""
    from zen_gin_export.zen_gin_zcvob import vob_name_from_object_name
    from zen_gin_export.vob_fields import VOB_SPECS
    name = vob_name_from_object_name(obj.name)
    visual = str(obj.get("visual_name", "") or "").strip()
    if not visual:
        # As on export: only props and items are named after their visual.
        vob_type = vob_type_of(obj)
        if vob_type != "oCItem" and VOB_SPECS[vob_type].visual not in ("name", "custom"):
            return name, None, ""
        visual = name
    stem, extension = os.path.splitext(visual)
    extension = extension.upper()
    if extension in _NO_MESH_EXTENSIONS or not stem:
        return name, None, extension
    if extension and len(extension) != 4:   # a dot inside a name, not an extension
        stem, extension = visual, ""
    return name, stem, extension


def _candidate_keys(vob_type, name, stem):
    keys = [f"{vob_type}:{name}"]
    if stem:
        keys += [f"{vob_type}:{stem}", f"zCVob:{stem}"]
    return [key.upper() for key in dict.fromkeys(keys)]


def _new_collection(key):
    return bpy.data.collections.new(PREVIEW_PREFIX + key)


def _collection_from_library(key, blend, object_name):
    with bpy.data.libraries.load(blend, link=True) as (source, target):
        if object_name not in source.objects:
            return None
        target.objects = [object_name]
    linked = target.objects[0]
    if linked is None or linked.data is None:
        return None
    # A local object around the linked mesh, so it can sit at the origin
    # whatever the asset's own location is. Rotation and scale are the
    # asset's: that is what dragging it into a scene would give.
    preview = bpy.data.objects.new(PREVIEW_PREFIX + key, linked.data)
    matrix = linked.matrix_basis.copy()
    matrix.translation = (0.0, 0.0, 0.0)
    preview.matrix_basis = matrix
    if linked.users == 0:
        bpy.data.objects.remove(linked)
    collection = _new_collection(key)
    collection.objects.link(preview)
    return collection


def _collection_from_game_mesh(key, path):
    imported = list(get_krx_3ds_importer()(filename=path, scale=0.01).imported_objects)
    if not imported:
        return None
    collection = _new_collection(key)
    for index, obj in enumerate(imported):
        for user in list(obj.users_collection):
            user.objects.unlink(obj)
        obj.name = PREVIEW_PREFIX + key + (f".{index}" if index else "")
        collection.objects.link(obj)
    return collection


def preview_collection(context, vob_type, name, stem, extension, use_game_files, failures=None):
    """The collection to instance for this vob, created on first use; None
    when no mesh is available."""
    keys = _candidate_keys(vob_type, name, stem)
    for key in keys:
        existing = bpy.data.collections.get(PREVIEW_PREFIX + key)
        if existing is not None:
            return existing
    index = library_index()
    for key in keys:
        if key in index:
            collection = _collection_from_library(key, *index[key])
            if collection is not None:
                return collection
    if use_game_files and stem and extension in ("", ".3DS"):
        path = game_mesh_index(context).get(stem.upper())
        if path:
            try:
                return _collection_from_game_mesh(f"zCVob:{stem}".upper(), path)
            except Exception as error:      # KrxImpExp missing or a broken file
                if failures is not None:
                    failures.append(f"{os.path.basename(path)}: {error}")
    return None


def wants_preview(obj):
    """Vob empties that show a mesh in game and nothing in Blender yet."""
    if obj.type != 'EMPTY':
        return False
    vob_type = vob_type_of(obj)
    if vob_type is None or vob_type == "zCVobLevelCompo":
        return False
    try:
        from zen_gin_export.vob_fields import VOB_SPECS
    except ImportError:
        return False
    spec = VOB_SPECS[vob_type]
    return spec.volume is None and bool(spec.visual) or vob_type == "oCItem"


def apply_previews(context, objects, use_game_files=False):
    """Give each vob empty in objects its preview mesh. Returns
    {"shown": n, "missing": {visual: count}, "failures": [text]}."""
    report = {"shown": 0, "missing": {}, "failures": []}
    unavailable = set()
    for obj in objects:
        if not wants_preview(obj):
            continue
        vob_type = vob_type_of(obj)
        name, stem, extension = visual_of(obj)
        if stem is None:
            continue
        lookup = (vob_type, name.upper(), stem.upper())
        collection = None
        if lookup not in unavailable:
            collection = preview_collection(
                context, vob_type, name, stem, extension, use_game_files, report["failures"])
        if collection is None:
            unavailable.add(lookup)
            label = stem + extension
            report["missing"][label] = report["missing"].get(label, 0) + 1
            continue
        obj.instance_type = 'COLLECTION'
        obj.instance_collection = collection
        report["shown"] += 1
    return report


def clear_previews(objects):
    count = 0
    for obj in objects:
        collection = getattr(obj, "instance_collection", None)
        if obj.type == 'EMPTY' and collection is not None and collection.name.startswith(PREVIEW_PREFIX):
            obj.instance_collection = None
            obj.instance_type = 'NONE'
            count += 1
    for collection in [c for c in bpy.data.collections if c.name.startswith(PREVIEW_PREFIX) and c.users == 0]:
        for obj in list(collection.objects):
            if obj.users <= 1:
                bpy.data.objects.remove(obj)
        bpy.data.collections.remove(collection)
    return count


def summary(report):
    text = f"{report['shown']} vob(s) show a preview mesh"
    missing = report["missing"]
    if missing:
        names = sorted(missing, key=lambda n: -missing[n])
        text += f"; no mesh found for {sum(missing.values())} ({', '.join(names[:4])}"
        text += ", ...)" if len(names) > 4 else ")"
    if report["failures"]:
        text += f"; {len(report['failures'])} file(s) failed to load ({report['failures'][0]})"
    return text


class ZEN_OT_load_vob_previews(bpy.types.Operator):
    bl_idname = "zen.load_vob_previews"
    bl_label = "Show Preview Meshes"
    bl_description = (
        "Make vob empties (props, items, mobs from an imported ZEN) draw their "
        "mesh. The mesh comes from an asset library object with the same name; "
        "the empties and what they export stay unchanged"
    )
    bl_options = {'REGISTER', 'UNDO'}

    selected_only: bpy.props.BoolProperty(
        name="Selected Only", description="Only the selected objects instead of the whole scene",
        default=False)
    use_game_files: bpy.props.BoolProperty(
        name="Also Load From Game Files",
        description="For visuals no asset library has, import the game's source .3DS "
                    "with KrxImpExp (slower; one import per distinct mesh)",
        default=False)
    clear: bpy.props.BoolProperty(
        name="Remove Previews", description="Turn the vobs back into plain empties instead",
        default=False)

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        objects = list(context.selected_objects if self.selected_only else context.scene.objects)
        if self.clear:
            self.report({'INFO'}, f"Removed the preview from {clear_previews(objects)} vob(s)")
            return {'FINISHED'}
        report = apply_previews(context, objects, self.use_game_files)
        self.report({'WARNING' if report["failures"] else 'INFO'}, summary(report))
        return {'FINISHED'}
