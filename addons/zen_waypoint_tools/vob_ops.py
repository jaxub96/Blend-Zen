import bpy

from .vob_types import VOB_TYPE_ITEMS, vob_display, default_box_size, find_next_vob_name
from .vob_ui_schema import split_type_id, VARIANT_VISUALS
from .mob_props import (
    vob_type_of, presets_for, apply_preset, init_new_vob, VISUAL_DEFAULTS, PRESET_HEIGHTS,
)

# Blender needs the strings of dynamic enum items kept alive.
_preset_items_cache = {}


def _preset_items(vob_type, with_default):
    key = (vob_type, with_default)
    if key not in _preset_items_cache:
        items = [(pid, label, "") for pid, label in presets_for(vob_type)]
        # Only types with a default model of their own offer "Default"; a
        # generic interactive object starts from its first preset.
        if with_default and vob_type in VISUAL_DEFAULTS:
            items.insert(0, ('DEFAULT', "Default", "The type's default model and settings"))
        _preset_items_cache[key] = items or [('NONE', "No presets", "")]
    return _preset_items_cache[key]


def _update_vob_type(self, context):
    """Live-refresh the suggested name (and reset the preset) when the
    Type dropdown changes, while the Add VOB dialog is still open."""
    self.vob_name = find_next_vob_name(self.vob_type)
    self.preset = _preset_items(split_type_id(self.vob_type)[0], True)[0][0]


def create_vob(context, vob_type_id, name, preset=None):
    """A new vob object at the 3D cursor, set up so it works as it is."""
    vob_type, variant = split_type_id(vob_type_id)
    full_name = f"{vob_type}:{name}"

    if vob_type == 'zCVobLight':
        from .light_props import create_light_object
        obj = create_light_object(full_name)
    else:
        obj = bpy.data.objects.new(full_name, None)
        obj.empty_display_type, obj.empty_display_size = vob_display(vob_type_id)

    obj.location = context.scene.cursor.location.copy()
    obj.rotation_mode = 'QUATERNION'
    box = default_box_size(vob_type_id)
    if box:
        obj.scale = (box, box, box)
        obj.rotation_mode = 'XYZ'
        obj.lock_rotation = (True, True, True)      # the box is axis-aligned in-game

    if variant:
        obj["visual_name"] = VARIANT_VISUALS[variant]
        obj["cd_dyn"], obj["cd_static"], obj["static_vob"] = False, False, False
        if variant == 'DECAL':
            obj["cam_align"] = "YAW"
    init_new_vob(obj, vob_type)
    if preset and preset not in ('DEFAULT', 'NONE'):
        apply_preset(obj, preset)
        obj.location.z += PRESET_HEIGHTS.get(preset, 0.0)
    elif vob_type == 'oCMobSwitch':
        obj.location.z += PRESET_HEIGHTS["LEVER"]       # the default switch is the lever

    (context.collection or context.scene.collection).objects.link(obj)

    if vob_type == 'zCMover':
        from .vob_ui import add_mover_keyframe
        add_mover_keyframe(context, obj)        # closed
        add_mover_keyframe(context, obj)        # open: 2 m up
    return obj


class ZEN_OT_add_vob(bpy.types.Operator):
    bl_idname = "zen.add_vob"
    bl_label = "Add ZenGin VOB"
    bl_description = (
        "Add a vob at the 3D cursor: lights, sounds, interactive objects, zones, triggers, "
        "movers, effects. Props and items are dragged in from the asset libraries instead"
    )
    bl_options = {'REGISTER', 'UNDO'}

    vob_type: bpy.props.EnumProperty(
        items=VOB_TYPE_ITEMS, name="Type", default='oCMobInter',
        update=_update_vob_type,
    )
    vob_name: bpy.props.StringProperty(name="Name", default="", options={'SKIP_SAVE'})
    preset: bpy.props.EnumProperty(
        name="Preset",
        description="Vanilla model and settings to start from",
        items=lambda self, context: _preset_items(split_type_id(self.vob_type)[0], True),
    )

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def invoke(self, context, event):
        # operator properties persist across invocations in Blender, so always
        # recompute the suggestion here rather than only filling when empty
        self.vob_name = find_next_vob_name(self.vob_type)
        return context.window_manager.invoke_props_dialog(self)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "vob_type")
        layout.prop(self, "vob_name", text="Name")
        if presets_for(split_type_id(self.vob_type)[0]):
            layout.prop(self, "preset")

    def execute(self, context):
        name = self.vob_name.strip() or find_next_vob_name(self.vob_type)
        try:
            obj = create_vob(context, self.vob_type, name, self.preset)
        except ImportError as e:
            self.report({'ERROR'}, f"zen_gin_export is not available: {e}")
            return {'CANCELLED'}

        for selected_obj in context.view_layer.objects:
            selected_obj.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj

        self.report({'INFO'}, f"Added {obj.name}")
        return {'FINISHED'}


class ZEN_OT_apply_mob_preset(bpy.types.Operator):
    bl_idname = "zen.apply_mob_preset"
    bl_label = "Apply Preset"
    bl_description = (
        "Set this object's model and settings to a working vanilla setup "
        "(model, focus name, script function, required item)"
    )
    bl_options = {'REGISTER', 'UNDO'}

    preset: bpy.props.EnumProperty(
        name="Preset",
        items=lambda self, context: _preset_items(vob_type_of(context.active_object), False),
    )

    @classmethod
    def poll(cls, context):
        try:
            return bool(presets_for(vob_type_of(context.active_object)))
        except ImportError:
            return False

    def execute(self, context):
        if self.preset == 'NONE':
            return {'CANCELLED'}
        apply_preset(context.active_object, self.preset)
        return {'FINISHED'}
