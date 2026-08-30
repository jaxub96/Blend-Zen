import bpy

from .vob_types import VOB_TYPE_ITEMS, VOB_DISPLAY, find_next_vob_name


def _update_vob_type_name(self, context):
    """Live-refresh the suggested name when the Type dropdown changes,
    while the Add VOB dialog is still open."""
    self.vob_name = find_next_vob_name(self.vob_type)


class ZEN_OT_add_vob(bpy.types.Operator):
    bl_idname = "zen.add_vob"
    bl_label = "Add ZenGin VOB"
    bl_description = "Add a new empty representing a ZenGin VOB, at the 3D cursor"
    bl_options = {'REGISTER', 'UNDO'}

    vob_type: bpy.props.EnumProperty(
        items=VOB_TYPE_ITEMS, name="Type", default='zCVob',
        update=_update_vob_type_name,
    )
    vob_name: bpy.props.StringProperty(name="Name", default="", options={'SKIP_SAVE'})

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
        if self.vob_type == 'zCVob' and len(context.window_manager.zen_mesh_catalog) > 0:
            # searchable autocomplete against the real mesh catalog - still
            # freely editable, this only offers suggestions
            layout.prop_search(
                self, "vob_name",
                context.window_manager, "zen_mesh_catalog",
                text="Name",
            )
        else:
            layout.prop(self, "vob_name", text="Name")

    def execute(self, context):
        name = self.vob_name.strip()
        if not name:
            name = find_next_vob_name(self.vob_type)

        full_name = f"{self.vob_type}:{name}"
        display_type, display_size = VOB_DISPLAY.get(self.vob_type, ('PLAIN_AXES', 0.3))

        obj = bpy.data.objects.new(full_name, None)
        obj.empty_display_type = display_type
        obj.empty_display_size = display_size
        obj.location = context.scene.cursor.location.copy()
        obj.rotation_mode = 'QUATERNION'

        target_collection = context.collection or context.scene.collection
        target_collection.objects.link(obj)

        for selected_obj in context.view_layer.objects:
            selected_obj.select_set(False)
        obj.select_set(True)
        context.view_layer.objects.active = obj

        self.report({'INFO'}, f"Added {full_name}")
        return {'FINISHED'}
