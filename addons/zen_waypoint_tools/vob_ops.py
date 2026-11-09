import bpy

from .vob_types import VOB_TYPE_ITEMS, VOB_DISPLAY, find_next_vob_name
from .mob_props import init_mob_properties, mob_type_of, presets_for, apply_preset

# Blender needs the strings of dynamic enum items kept alive.
_preset_items_cache = {}


def _preset_items(vob_type, with_default):
    key = (vob_type, with_default)
    if key not in _preset_items_cache:
        items = [(pid, label, "") for pid, label in presets_for(vob_type)]
        if with_default:
            items.insert(0, ('DEFAULT', "Default", "The type's default model and settings"))
        _preset_items_cache[key] = items or [('NONE', "No presets", "")]
    return _preset_items_cache[key]


def _update_vob_type(self, context):
    """Live-refresh the suggested name (and reset the preset) when the
    Type dropdown changes, while the Add VOB dialog is still open."""
    self.vob_name = find_next_vob_name(self.vob_type)
    self.preset = _preset_items(self.vob_type, True)[0][0]


class ZEN_OT_add_vob(bpy.types.Operator):
    bl_idname = "zen.add_vob"
    bl_label = "Add ZenGin VOB"
    bl_description = "Add a new empty representing a ZenGin VOB, at the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}

    vob_type: bpy.props.EnumProperty(
        items=VOB_TYPE_ITEMS, name="Type", default='oCMobInter',
        update=_update_vob_type,
    )
    vob_name: bpy.props.StringProperty(name="Name", default="", options={'SKIP_SAVE'})
    preset: bpy.props.EnumProperty(
        name="Preset",
        description="Vanilla model and settings to start from",
        items=lambda self, context: _preset_items(self.vob_type, True),
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
        if presets_for(self.vob_type):
            layout.prop(self, "preset")

    def execute(self, context):
        name = self.vob_name.strip()
        if not name:
            name = find_next_vob_name(self.vob_type)

        full_name = f"{self.vob_type}:{name}"

        if self.vob_type == 'zCVobLight':
            from .light_props import create_light_object
            obj = create_light_object(full_name)
        else:
            display_type, display_size = VOB_DISPLAY.get(self.vob_type, ('PLAIN_AXES', 0.3))
            obj = bpy.data.objects.new(full_name, None)
            obj.empty_display_type = display_type
            obj.empty_display_size = display_size

        obj.location = context.scene.cursor.location.copy()
        obj.rotation_mode = 'QUATERNION'

        init_mob_properties(obj, self.vob_type)
        if self.preset not in ('DEFAULT', 'NONE') and presets_for(self.vob_type):
            apply_preset(obj, self.preset)

        target_collection = context.collection or context.scene.collection
        target_collection.objects.link(obj)

        for selected_obj in context.view_layer.objects:
            selected_obj.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj

        self.report({'INFO'}, f"Added {full_name}")
        return {'FINISHED'}


class ZEN_OT_init_vob_properties(bpy.types.Operator):
    bl_idname = "zen.init_vob_properties"
    bl_label = "Add Missing Properties"
    bl_description = (
        "Add this vob type's settings (with defaults) as custom properties - "
        "for objects renamed by hand or made with an older version"
    )
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return mob_type_of(context.active_object) is not None

    def execute(self, context):
        obj = context.active_object
        init_mob_properties(obj, mob_type_of(obj))
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
        items=lambda self, context: _preset_items(mob_type_of(context.active_object), False),
    )

    @classmethod
    def poll(cls, context):
        return bool(presets_for(mob_type_of(context.active_object)))

    def execute(self, context):
        obj = context.active_object
        if self.preset == 'NONE':
            return {'CANCELLED'}
        init_mob_properties(obj, mob_type_of(obj))
        apply_preset(obj, self.preset)
        return {'FINISHED'}
