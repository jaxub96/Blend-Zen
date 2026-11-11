"""
The sidebar's vob settings: real typed widgets (checkboxes, dropdowns,
colour pickers, text fields with suggestions from the game files) for the
flat custom properties the exporter reads.

Object.zen_vob is a PropertyGroup that stores nothing itself: every
property reads and writes obj["key"] through get/set callbacks. A key that
is absent reads as the type's default, and setting a value back to the
default removes the key, so objects only carry what was changed - and
props dragged in from an asset library work without any setup.

The group is built from zen_gin_export.vob_fields at register time.
"""

import bpy

from . import game_bridge
from .mob_props import vob_type_of, presets_for, VISUAL_DEFAULTS
from .vob_ui_schema import FIELD_UI, MAIN_BASE_KEYS, enum_label, type_info

_settings_class = None
_key_types = {}          # key -> (archive name, archive type)


def _vob_fields():
    from zen_gin_export import vob_fields
    return vob_fields


def _default(obj, key):
    vob_type = vob_type_of(obj)
    vf = _vob_fields()
    if key == "visual_name":
        return ""
    try:
        return vf.default_for(vob_type, key)
    except KeyError:
        # A key this type doesn't have (never drawn): any default of that key.
        for other in vf.VOB_SPECS:
            try:
                return vf.default_for(other, key)
            except KeyError:
                continue
        raise


def value_of(obj, key):
    """The effective value of a setting: the custom property or the default."""
    value = obj.get(key)
    if value is None:
        return _default(obj, key)
    return list(value) if hasattr(value, "__len__") and not isinstance(value, str) else value


def _store(obj, key, value):
    default = _default(obj, key)
    if isinstance(default, tuple):
        default = list(default)
    if value == default:
        if key in obj.keys():
            del obj[key]
    else:
        obj[key] = value
    if "target" in key or key.startswith(("slave_", "respond_to_vob")):
        from .viewport_draw import tag_viewports_redraw
        tag_viewports_redraw()         # the trigger arrows follow at once


def _apply_light_preset(obj, name):
    """Picking a known preset copies its settings onto the light."""
    index = game_bridge.get_index()
    values = index.light_preset_values.get(name) if index else None
    if not values:
        return
    from zen_gin_export import (
        custom_properties_from_block, gothic_range_to_blender_distance,
        gothic_range_to_blender_power, gothic_color_to_blender,
        gothic_cone_angle_to_blender_spot_size,
    )
    for key, value in custom_properties_from_block("zCVobLight", values).items():
        if key != "preset_name":
            _store(obj, key, value.strip() if isinstance(value, str) else value)
    if obj.type != 'LIGHT':
        return
    light = obj.data
    try:
        range_cm = float(values.get("range", "0"))
        color = [int(v) for v in values.get("color", "").split()]
        spot = float(values.get("spotConeAngle", "0"))
    except ValueError:
        return
    light.type = 'SPOT' if values.get("lightType", "0").strip() == "1" else 'POINT'
    if range_cm > 0:
        light.use_custom_distance = True
        light.cutoff_distance = gothic_range_to_blender_distance(range_cm)
        light.energy = gothic_range_to_blender_power(range_cm)
    if len(color) >= 3:
        light.color = gothic_color_to_blender(*color[:3])
        if len(color) == 4:
            obj["color_a"] = color[3]
    if light.type == 'SPOT' and spot > 0:
        light.spot_size = gothic_cone_angle_to_blender_spot_size(spot)
    light.use_shadow = bool(value_of(obj, "light_static"))


def _make_property(key, archive_name, archive_type, default):
    label, description, options = FIELD_UI[key]
    common = {"name": label, "description": description}

    def getter(self):
        return value_of(self.id_data, key)

    def setter(self, value):
        _store(self.id_data, key, value)

    if archive_type == "bool":
        return bpy.props.BoolProperty(get=lambda s: bool(getter(s)), set=setter, **common)
    if archive_type == "int":
        return bpy.props.IntProperty(get=lambda s: int(getter(s)), set=setter, **common)
    if archive_type == "float":
        return bpy.props.FloatProperty(get=lambda s: float(getter(s)), set=setter,
                                       precision=3, **common)
    if archive_type == "enum":
        names = _vob_fields().ENUMS[archive_name]
        items = [(n, enum_label(n), "") for n in names]

        def enum_get(self):
            value = str(getter(self)).upper()
            return names.index(value) if value in names else 0

        def enum_set(self, index):
            _store(self.id_data, key, names[index])

        return bpy.props.EnumProperty(items=items, get=enum_get, set=enum_set, **common)
    if archive_type == "color":
        def color_get(self):
            return [max(0.0, min(1.0, v / 255.0)) for v in getter(self)]

        def color_set(self, value):
            _store(self.id_data, key, [int(round(v * 255)) for v in value])

        return bpy.props.FloatVectorProperty(size=4, subtype='COLOR', min=0.0, max=1.0,
                                             get=color_get, set=color_set, **common)
    if archive_type in ("vec3", "rawFloat"):
        return bpy.props.FloatVectorProperty(
            size=len(default), get=lambda s: [float(v) for v in getter(s)],
            set=lambda s, value: _store(s.id_data, key, [round(float(v), 6) for v in value]),
            **common)

    def string_set(self, value):
        _store(self.id_data, key, value)
        if key == "light_preset":
            _apply_light_preset(self.id_data, value)

    kwargs = dict(get=lambda s: str(getter(s)), set=string_set, **common)
    source = options.get("source")
    if source:
        kwargs["search"] = lambda self, context, edit_text: game_bridge.search(
            source, context, edit_text, self.id_data)
        kwargs["search_options"] = {'SUGGESTION'}
    return bpy.props.StringProperty(**kwargs)


# -- properties that edit the object's name ---------------------------------------

def _get_vob_name(self):
    return self.id_data.name.partition(":")[2]


def _set_vob_name(self, value):
    obj = self.id_data
    obj.name = f"{obj.name.partition(':')[0]}:{value.strip()}"


def _get_music_theme(self):
    return _get_vob_name(self).partition("_")[2]


def _set_music_theme(self, value):
    label = _get_vob_name(self).partition("_")[0] or "ZONE"
    _set_vob_name(self, f"{label}_{value.strip().upper()}")


def _build_settings_class():
    vf = _vob_fields()
    annotations = {
        "vob_name": bpy.props.StringProperty(
            name="Name", description="The vob's name (vobName): what triggers, scripts and "
            "routines refer to. Shown after the type in the object's name",
            get=_get_vob_name, set=_set_vob_name),
        "item_instance": bpy.props.StringProperty(
            name="Item", description="Item script instance, e.g. ItMi_Gold",
            get=_get_vob_name, set=_set_vob_name,
            search=lambda self, context, edit_text: game_bridge.search("items", context, edit_text),
            search_options={'SUGGESTION'}),
        "music_theme": bpy.props.StringProperty(
            name="Theme", description="Music theme prefix (MusicInst.d): the part of the zone's "
            "name after the first underscore, e.g. XAR plays XAR_Day_Std, XAR_Ngt_Std...",
            get=_get_music_theme, set=_set_music_theme,
            search=lambda self, context, edit_text: game_bridge.search("music_themes", context, edit_text),
            search_options={'SUGGESTION'}),
    }
    _key_types.clear()
    fields = list(vf.BASE_FIELDS)
    for vob_type in vf.VOB_SPECS:
        fields += vf.keyed_fields(vob_type)
    for archive_name, archive_type, key, default in fields:
        if key in annotations:
            continue
        _key_types[key] = (archive_name, archive_type)
        annotations[key] = _make_property(key, archive_name, archive_type, default)
    return type("ZenVobSettings", (bpy.types.PropertyGroup,), {"__annotations__": annotations})


# -- operators ------------------------------------------------------------------------

# Settings that are not vob_fields keys but pick from the game files too.
_VIRTUAL_SOURCES = {"music_theme": "music_themes", "item_instance": "items"}
_NO_GAME_DATA = "(nothing found - set Gothic Game Folder in the add-on preferences)"
# Blender needs the strings of dynamic enum items kept alive; also maps the
# picked index back to its name.
_pick_cache = {"key": None, "names": [], "items": []}


def source_of(key):
    """The game-file list a setting picks from, or None."""
    if key in _VIRTUAL_SOURCES:
        return _VIRTUAL_SOURCES[key]
    return FIELD_UI[key][2].get("source") if key in FIELD_UI else None


def _pick_items(self, context):
    names = game_bridge.candidates(source_of(self.key), context, context.active_object)
    if _pick_cache["key"] != self.key or _pick_cache["names"] != names:
        _pick_cache.update(key=self.key, names=list(names), items=[
            (str(index), name, "") for index, name in enumerate(names)
        ] or [("-1", _NO_GAME_DATA, "")])
    return _pick_cache["items"]


class ZEN_OT_pick_game_value(bpy.types.Operator):
    """The dropdown next to a text field: a searchable list of what exists
    in the game files (or, for trigger targets, in the scene). The field
    itself still takes any typed text."""
    bl_idname = "zen.pick_game_value"
    bl_label = "Pick From Game Files"
    bl_description = (
        "Choose from the names found in the Gothic game files (type to filter). "
        "The field next to it also accepts any name typed by hand"
    )
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}
    bl_property = "value"

    key: bpy.props.StringProperty(options={'HIDDEN'})
    value: bpy.props.EnumProperty(name="Value", items=_pick_items)

    @classmethod
    def poll(cls, context):
        return vob_type_of(context.active_object) is not None

    def invoke(self, context, event):
        context.window_manager.invoke_search_popup(self)
        return {'FINISHED'}

    def execute(self, context):
        try:
            name = _pick_cache["names"][int(self.value)]
        except (ValueError, IndexError):
            return {'CANCELLED'}
        setattr(context.active_object.zen_vob, self.key, name)
        for area in context.screen.areas:
            area.tag_redraw()
        return {'FINISHED'}


class ZEN_OT_add_container_item(bpy.types.Operator):
    bl_idname = "zen.add_container_item"
    bl_label = "Add Item to Container"
    bl_description = "Add an item (picked from the game's item scripts) to this container's contents"
    bl_options = {'REGISTER', 'UNDO'}

    item: bpy.props.StringProperty(
        name="Item", description="Item script instance",
        search=lambda self, context, edit_text: game_bridge.search("items", context, edit_text),
        search_options={'SUGGESTION'})
    count: bpy.props.IntProperty(name="Count", default=1, min=1)

    @classmethod
    def poll(cls, context):
        return vob_type_of(context.active_object) == "oCMobContainer"

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        item = self.item.strip()
        if not item:
            return {'CANCELLED'}
        obj = context.active_object
        entries = [e for e in str(obj.get("contains", "")).split(",") if e.strip()]
        entries.append(item if self.count == 1 else f"{item}:{self.count}")
        obj["contains"] = ",".join(entries)
        return {'FINISHED'}


class ZEN_OT_add_mover_keyframe(bpy.types.Operator):
    bl_idname = "zen.add_mover_keyframe"
    bl_label = "Add Keyframe"
    bl_description = (
        "Add a keyframe empty to this mover. Keyframe 1 is the closed/start pose, the last "
        "one the open/end pose: move and rotate the empties to set them"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return vob_type_of(context.active_object) == "zCMover"

    def execute(self, context):
        add_mover_keyframe(context, context.active_object)
        return {'FINISHED'}


def mover_keyframes(mover):
    from zen_gin_export.zen_gin_zcvob import mover_keyframe_objects
    return mover_keyframe_objects(mover)


def add_mover_keyframe(context, mover, world_matrix=None, parent_world=None):
    """A keyframe empty parented to the mover. world_matrix: its pose
    (default: the last keyframe's, or the mover's, raised 2 m for every
    keyframe after the first). parent_world: the mover's world matrix when
    it is not evaluated yet (importer)."""
    from mathutils import Matrix
    from zen_gin_export.vob_fields import MOVER_KEY_PROPERTY

    keys = mover_keyframes(mover)
    if parent_world is None:
        context.view_layer.update()
        parent_world = mover.matrix_world.copy()
    if world_matrix is None:
        world_matrix = (keys[-1].matrix_world.copy() if keys else parent_world.copy())
        if keys:
            world_matrix = Matrix.Translation((0.0, 0.0, 2.0)) @ world_matrix

    key = bpy.data.objects.new(f"MoverKey{len(keys) + 1}", None)
    key.empty_display_type = 'ARROWS'
    key.empty_display_size = 0.5
    key[MOVER_KEY_PROPERTY] = len(keys)
    for collection in (mover.users_collection or [context.scene.collection]):
        collection.objects.link(key)
    key.parent = mover
    key.matrix_parent_inverse = Matrix.Identity(4)
    key.matrix_basis = parent_world.inverted_safe() @ world_matrix
    return key


# -- drawing --------------------------------------------------------------------------

def _visible(obj, vob_type, key):
    when = FIELD_UI[key][2].get("when")
    return when is None or when(lambda k: value_of(obj, k), vob_type)


def _draw_field(layout, obj, key):
    settings = obj.zen_vob
    if source_of(key):
        # Text field (type anything, suggestions while typing) + a
        # dropdown button listing what the game files have.
        row = layout.row(align=True)
        row.prop(settings, key)
        row.operator("zen.pick_game_value", text="", icon='DOWNARROW_HLT').key = key
    elif key == "contains":
        row = layout.row(align=True)
        row.prop(settings, key)
        row.operator("zen.add_container_item", text="", icon='ADD')
    elif key == "decal_dim" or key == "decal_offset" or key == "quake_amplitude":
        layout.row().prop(settings, key)
    else:
        layout.prop(settings, key)


def _draw_light(layout, obj):
    if obj.type != 'LIGHT':
        layout.label(text="Not a Blender light: values come from custom properties", icon='INFO')
        return
    light = obj.data
    layout.prop(light, "type", text="Type")
    if light.type not in ('POINT', 'SPOT'):
        layout.label(text="Exports as a point light", icon='ERROR')
    layout.prop(light, "color", text="Colour")
    if light.use_custom_distance:
        layout.prop(light, "cutoff_distance", text="Range (m)")
    else:
        layout.prop(light, "use_custom_distance", text="Set Range (default 10 m)")
    if light.type == 'SPOT':
        layout.prop(light, "spot_size", text="Cone Angle")


def _draw_mover(layout, obj):
    keys = mover_keyframes(obj)
    row = layout.row(align=True)
    row.label(text=f"Keyframes: {len(keys)}", icon='KEYFRAME')
    row.operator("zen.add_mover_keyframe", text="", icon='ADD')
    if len(keys) < 2:
        layout.label(text="Needs 2 keyframes to move", icon='INFO')


def draw_vob_settings(layout, context, obj):
    vob_type = vob_type_of(obj)
    vf = _vob_fields()
    spec = vf.VOB_SPECS[vob_type]
    settings = obj.zen_vob
    info = type_info(vob_type)

    layout.label(text=info[0] if info else vob_type, icon='OBJECT_DATA')
    col = layout.column()
    col.use_property_split = True
    col.use_property_decorate = False

    if vob_type == "oCItem":
        _draw_field(col, obj, "item_instance")
    elif vob_type == "zCVobLevelCompo":
        col.prop(settings, "vob_name", text="Level Mesh")
    else:
        col.prop(settings, "vob_name")
    if vob_type in ("oCZoneMusic", "oCZoneMusicDefault"):
        _draw_field(col, obj, "music_theme")
        if "_" not in settings.vob_name:
            col.label(text="Name must be <PLACE>_<THEME>", icon='ERROR')
    if spec.volume == "box":
        col.label(text="Scale the box to size it", icon='INFO')

    if presets_for(vob_type):
        col.operator_menu_enum("zen.apply_mob_preset", "preset", icon='PRESET')
    if vob_type == "zCVobLight":
        _draw_light(col, obj)
    if vob_type == "zCMover":
        _draw_mover(col, obj)

    type_keys = [key for _, _, key, _ in vf.keyed_fields(vob_type)]
    main_base = MAIN_BASE_KEYS.get(vob_type, ())
    main = [k for k in type_keys if not FIELD_UI[k][2].get("adv")] + list(main_base)
    advanced = [k for k in type_keys if FIELD_UI[k][2].get("adv")]
    advanced += [k for k in vf.BASE_KEYS if k not in main_base]

    for key in main:
        if _visible(obj, vob_type, key):
            _draw_field(col, obj, key)
    if vob_type in VISUAL_DEFAULTS and not str(obj.get("visual_name", "")).strip() \
            and not settings.vob_name:
        col.label(text="No Visual: Spacer crashes on a missing model", icon='ERROR')

    wm = context.window_manager
    box = layout.box()
    row = box.row()
    row.prop(wm, "zen_show_advanced", text="Advanced", emboss=False,
             icon='TRIA_DOWN' if wm.zen_show_advanced else 'TRIA_RIGHT')
    changed = sum(1 for k in advanced if k in obj.keys())
    if changed:
        row.label(text=f"{changed} changed")
    if wm.zen_show_advanced:
        adv = box.column()
        adv.use_property_split = True
        adv.use_property_decorate = False
        for key in advanced:
            if _visible(obj, vob_type, key):
                _draw_field(adv, obj, key)


class ZEN_PT_vob_settings(bpy.types.Panel):
    bl_label = "VOB Settings"
    bl_idname = "ZEN_PT_vob_settings"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZenGin"
    bl_parent_id = "ZEN_PT_waypoint_tools"
    bl_order = 0

    @classmethod
    def poll(cls, context):
        try:
            return vob_type_of(context.active_object) is not None and _settings_class is not None
        except ImportError:
            return False

    def draw(self, context):
        draw_vob_settings(self.layout, context, context.active_object)


classes = (ZEN_OT_pick_game_value, ZEN_OT_add_container_item, ZEN_OT_add_mover_keyframe,
           ZEN_PT_vob_settings)


def register():
    """Registers the settings group (needs zen_gin_export; without it the
    addon still loads and the export buttons explain what is missing)."""
    global _settings_class
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.zen_show_advanced = bpy.props.BoolProperty(
        name="Advanced", description="Settings that are the same on practically every vanilla vob",
        default=False)
    try:
        _settings_class = _build_settings_class()
    except ImportError:
        _settings_class = None
        return
    bpy.utils.register_class(_settings_class)
    bpy.types.Object.zen_vob = bpy.props.PointerProperty(type=_settings_class)


def unregister():
    global _settings_class
    if _settings_class is not None:
        del bpy.types.Object.zen_vob
        bpy.utils.unregister_class(_settings_class)
        _settings_class = None
    del bpy.types.WindowManager.zen_show_advanced
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
