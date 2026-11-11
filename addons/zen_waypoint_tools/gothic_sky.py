"""
"Gothic Sky" viewport lighting preset.

Gothic has no HDRI; its default sky is the skydome (Skydome_ColorLayer +
cloud layers). asset_catalog/sky/gothic_sky.hdr is that dome rendered to an
equirectangular panorama (see tooling/pipeline/build_gothic_sky.py). This
operator installs it as a Blender studio light and selects it in the current
viewport (Material Preview / Solid shading lighting), and switches the scene to
the Standard view transform, which is what Gothic displays (no tone mapping).
The panorama includes the sun and fades to neutral grey below the horizon.
"""

import math
import os
import shutil
import bpy

SKY_HDR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "asset_catalog", "sky", "gothic_sky.hdr",
)
STUDIO_LIGHT_NAME = "gothic_sky.hdr"

# The HDR carries its own sun (a bright disc painted into the panorama), so it
# lights a scene by itself: EEVEE turns the disc into a shadow-casting sun and
# the rest of the sky into soft fill. Nothing is added to the scene.
SKY_LIGHT_INTENSITY = 1.0
# Turn the sky so the sun comes in diagonally and box sides shade differently.
SKY_ROTATION_DEG = 40.0
# Earlier versions lit the scene with a real Sun object of this name.
OLD_SUN_OBJECT_NAME = "GothicSun_preview"


def remove_old_preview_sun():
    """Delete the Sun object older versions added; it would double the light."""
    obj = bpy.data.objects.get(OLD_SUN_OBJECT_NAME)
    if obj is None or obj.type != 'LIGHT' or not obj.get("zen_preview_only"):
        return False
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if data.users == 0:
        bpy.data.lights.remove(data)
    return True


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
        "Install the Gothic skydome as a Blender studio light, use it in this "
        "viewport (Material Preview, Standard view transform). The sun is part of "
        "the sky image, so no light object is added to the scene"
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
            shading.studiolight_intensity = SKY_LIGHT_INTENSITY
            shading.studiolight_rotate_z = math.radians(SKY_ROTATION_DEG)
        removed = remove_old_preview_sun()
        context.scene.view_settings.view_transform = 'Standard'
        context.scene.view_settings.look = 'None'
        note = " (old GothicSun_preview light removed)" if removed else ""
        self.report({'INFO'}, "Gothic sky studio light installed and selected" + note)
        return {'FINISHED'}
