bl_info = {
    "name": "Select Material Borders",
    "author": "Custom",
    "version": (1, 0),
    "blender": (4, 0, 0),
    "category": "Mesh",
}

import bpy
import bmesh


class MESH_OT_select_material_borders(bpy.types.Operator):
    bl_idname = "mesh.select_material_borders"
    bl_label = "Select Material Borders"
    bl_description = "Select edges between faces with different materials"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return (
            context.mode == 'EDIT_MESH'
            and context.edit_object is not None
        )

    def execute(self, context):
        obj = context.edit_object
        bm = bmesh.from_edit_mesh(obj.data)

        # Switch to edge selection mode
        bpy.ops.mesh.select_mode(type='EDGE')

        # Deselect everything first
        for v in bm.verts:
            v.select = False
        for e in bm.edges:
            e.select = False
        for f in bm.faces:
            f.select = False

        # Select edges separating different materials
        for e in bm.edges:
            if len(e.link_faces) == 2:
                f1, f2 = e.link_faces

                if f1.material_index != f2.material_index:
                    e.select = True

        bmesh.update_edit_mesh(obj.data)

        return {'FINISHED'}


class VIEW3D_PT_material_borders(bpy.types.Panel):
    bl_label = "Material Borders"
    bl_idname = "VIEW3D_PT_material_borders"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Edit"

    def draw(self, context):
        layout = self.layout
        layout.operator(
            "mesh.select_material_borders",
            text="Select Material Borders",
            icon='EDGESEL'
        )


classes = (
    MESH_OT_select_material_borders,
    VIEW3D_PT_material_borders,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()