"""
"Gothic Sky" viewport lighting preset.

Gothic has no HDRI; its default sky is the skydome (Skydome_ColorLayer +
cloud layers). asset_catalog/sky/gothic_sky.hdr is that dome rendered to an
equirectangular panorama (see tooling/pipeline/build_gothic_sky.py). This
operator installs it as a Blender studio light and selects it in the current
viewport (Material Preview / Solid shading lighting), and switches the scene to
the Standard view transform, which is what Gothic displays (no tone mapping).
"""

import os
import shutil
import bpy

SKY_HDR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "asset_catalog", "sky", "gothic_sky.hdr",
)
STUDIO_LIGHT_NAME = "gothic_sky.hdr"


def install_studio_light():
    if not os.path.isfile(SKY_HDR):
        raise FileNotFoundError(f"Missing {SKY_HDR}")
    dest_dir = bpy.utils.user_resource('DATAFILES', path="studiolights/world", create=True)
    shutil.copyfile(SKY_HDR, os.path.join(dest_dir, STUDIO_LIGHT_NAME))
    bpy.context.preferences.studio_lights.refresh()


class ZEN_OT_use_gothic_sky(bpy.types.Operator):
    bl_idname = "zen.use_gothic_sky"
    bl_label = "Use Gothic Sky Lighting"
    bl_description = (
        "Install the Gothic skydome as a Blender studio light and use it in this "
        "viewport (Material Preview), with the Standard view transform, so lit "
        "scenes look like they do in Spacer"
    )
    bl_options = {'REGISTER'}

    def execute(self, context):
        try:
            install_studio_light()
        except Exception as e:
            self.report({'ERROR'}, f"Could not install Gothic sky: {e}")
            return {'CANCELLED'}

        space = context.space_data
        if space is not None and space.type == 'VIEW_3D':
            shading = space.shading
            shading.type = 'MATERIAL'
            shading.use_scene_world = False
            shading.use_scene_lights = True
            shading.studio_light = STUDIO_LIGHT_NAME
        context.scene.view_settings.view_transform = 'Standard'
        context.scene.view_settings.look = 'None'
        self.report({'INFO'}, "Gothic sky studio light installed and selected")
        return {'FINISHED'}
