"""
"Gothic Sky" viewport lighting preset.

Gothic has no HDRI; its default sky is the skydome (Skydome_ColorLayer +
cloud layers). asset_catalog/sky/gothic_sky.hdr is that dome rendered to an
equirectangular panorama (see tooling/pipeline/build_gothic_sky.py). This
operator installs it as a Blender studio light and selects it in the current
viewport (Material Preview / Solid shading lighting), and switches the scene to
the Standard view transform, which is what Gothic displays (no tone mapping).
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

# The HDR is the sky as it *looks*, at strength 1, so the background matches
# Gothic. On its own it is a weak light (a white up-facing surface gets ~0.14
# linear) because it has no sun in it. Gothic's outdoor light is mostly the sun,
# so add one as a real Blender Sun light for preview. It is a plain object
# without a ZenGin prefix, so the exporter ignores it, and the HDR/background
# stay untouched.
SKY_LIGHT_INTENSITY = 1.0
SUN_OBJECT_NAME = "GothicSun_preview"
SUN_STRENGTH = 0.8                     # sun-facing white ~0.6 + sky 0.14 linear
SUN_COLOR = (1.0, 0.93, 0.80)          # warm daylight
SUN_ELEVATION_DEG = 50.0
SUN_AZIMUTH_DEG = 135.0


def ensure_preview_sun(context):
    """Create (or update) the preview-only Sun light. Returns the object."""
    obj = bpy.data.objects.get(SUN_OBJECT_NAME)
    if obj is None or obj.type != 'LIGHT':
        data = bpy.data.lights.new(SUN_OBJECT_NAME, 'SUN')
        obj = bpy.data.objects.new(SUN_OBJECT_NAME, data)
        context.scene.collection.objects.link(obj)
    elif obj.name not in context.scene.objects:
        context.scene.collection.objects.link(obj)
    data = obj.data
    data.type = 'SUN'
    data.energy = SUN_STRENGTH
    data.color = SUN_COLOR
    data.angle = math.radians(0.5)
    obj.rotation_mode = 'XYZ'
    # A sun shines along its local -Z: tilt it down from straight up.
    obj.rotation_euler = (math.radians(90.0 - SUN_ELEVATION_DEG), 0.0, math.radians(SUN_AZIMUTH_DEG))
    obj["zen_preview_only"] = True
    return obj


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
        "viewport (Material Preview, Standard view transform) and add a preview-only "
        "Sun light (GothicSun_preview, never exported) so lit scenes look like Spacer"
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
        ensure_preview_sun(context)
        context.scene.view_settings.view_transform = 'Standard'
        context.scene.view_settings.look = 'None'
        self.report({'INFO'}, "Gothic sky studio light installed and selected")
        return {'FINISHED'}
