"""
Bridge to the Gothic II game files: one cached zen_gin_export GameIndex for
the Gothic Game Folder set in the add-on preferences, and the search
callbacks that feed the sidebar's dropdowns from it.

The index is read on first use (well under a second) and again after
Reload Game Data or when the folder changes.
"""

import bpy

from .preferences import get_gothic_settings

_index = None
_index_folder = None


def get_index(context=None):
    """The GameIndex for the configured game folder (empty when none is
    set or the library is missing)."""
    global _index, _index_folder
    folder, _ = get_gothic_settings(context)
    if _index is None or folder != _index_folder:
        try:
            from zen_gin_export.game_data import GameIndex
        except ImportError:
            return None
        _index, _index_folder = GameIndex(folder), folder
    return _index


def reload_index():
    global _index
    _index = None
    return get_index()


def _scene_vob_names(context):
    from .mob_props import vob_type_of
    from zen_gin_export.zen_gin_zcvob import vob_name_from_object_name
    names = set()
    scene = getattr(context, "scene", None)
    for obj in (scene.objects if scene else ()):
        vob_type = vob_type_of(obj)
        if vob_type and vob_type not in ("zCVob", "oCItem", "zCVobLevelCompo"):
            name = vob_name_from_object_name(obj.name)
            if name:
                names.add(name)
    return sorted(names)


def candidates(source, context, obj=None):
    """The names a field with this `source` picks from."""
    if source == "scene":
        return _scene_vob_names(context)
    index = get_index(context)
    if index is None:
        return []
    if source == "visual":
        from .mob_props import vob_type_of
        vob_type = vob_type_of(obj)
        if vob_type == "zCVob":
            current = str(obj.get("visual_name", "")).upper()
            if current.endswith(".PFX"):
                return index.pfx
            if current.endswith(".TGA"):
                return index.textures
            return index.meshes + index.pfx
        if vob_type in ("zCMover", "oCMOB"):
            return index.meshes
        if vob_type == "zCVobAnimate":
            return index.morph_meshes
        return index.mob_models + index.meshes
    if source == "keys":
        return index.keys or index.items
    return getattr(index, source, [])


def search(source, context, edit_text, obj=None, limit=400):
    """Names of `source` containing edit_text (case-insensitive), names
    that start with it first."""
    needle = edit_text.strip().upper()
    names = candidates(source, context, obj)
    if not needle:
        return names[:limit]
    starts = [n for n in names if n.upper().startswith(needle)]
    contains = [n for n in names if needle in n.upper() and not n.upper().startswith(needle)]
    return (starts + contains)[:limit]


class ZEN_OT_reload_game_data(bpy.types.Operator):
    bl_idname = "zen.reload_game_data"
    bl_label = "Reload Game Data"
    bl_description = (
        "Re-read the sounds, effects, items, presets and models offered in the "
        "dropdowns from the Gothic Game Folder (after changing scripts or files)"
    )

    def execute(self, context):
        index = reload_index()
        if index is None:
            self.report({'ERROR'}, "zen_gin_export is not available")
            return {'CANCELLED'}
        if not index.found:
            self.report({'WARNING'}, "No _work/Data found - set Gothic Game Folder in the "
                                     "add-on preferences. Fields still accept typed names")
            return {'CANCELLED'}
        counts = index.counts()
        self.report({'INFO'}, "Game data: {sfx} sounds, {pfx} effects, {items} items, "
                              "{mob_models} models, {meshes} meshes, {light_presets} light "
                              "presets".format(**counts))
        return {'FINISHED'}
