import bpy

from .waypoint_links import (
    is_waypoint,
    get_empty_link_slot,
    find_next_waypoint_name,
    add_directed_link,
    has_link,
    remove_directed_link,
    get_waypoint_display_name,
    LINK_SLOT_COUNT,
)
from .viewport_draw import tag_viewports_redraw, start_draw_handler, stop_draw_handler


class ZEN_OT_add_waypoint(bpy.types.Operator):
    bl_idname = "zen.add_waypoint"
    bl_label = "Add Waypoint at Cursor"
    bl_description = "Add a new zCWaypoint at the 3D cursor, linked from the active waypoint"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        return context.mode == 'OBJECT'

    def execute(self, context):
        prev = context.active_object if is_waypoint(context.active_object) else None

        # Only prev needs a free slot - the new waypoint always has all 3 free.
        if prev is not None and get_empty_link_slot(prev) is None:
            self.report(
                {'ERROR'},
                f"{prev.name} already has {LINK_SLOT_COUNT} links",
            )
            return {'CANCELLED'}

        cursor_loc = context.scene.cursor.location.copy()
        name = find_next_waypoint_name()

        obj = bpy.data.objects.new(name, None)
        obj.empty_display_type = 'PLAIN_AXES'
        obj.empty_display_size = 0.15
        obj.location = cursor_loc
        obj.rotation_mode = 'QUATERNION'

        target_collection = context.collection or context.scene.collection
        target_collection.objects.link(obj)

        if prev is not None:
            if not add_directed_link(prev, obj):
                bpy.data.objects.remove(obj, do_unlink=True)
                self.report({'ERROR'}, "Unable to allocate waypoint link slot")
                return {'CANCELLED'}

        for selected_obj in context.view_layer.objects:
            selected_obj.select_set(False)

        obj.select_set(True)
        context.view_layer.objects.active = obj

        tag_viewports_redraw()
        self.report({'INFO'}, f"Added {name}")
        return {'FINISHED'}


class ZEN_OT_link_waypoints(bpy.types.Operator):
    bl_idname = "zen.link_waypoints"
    bl_label = "Link Selected Waypoints"
    bl_description = "Connect the active waypoint to the other selected waypoint"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode != 'OBJECT':
            return False

        selected = [o for o in context.selected_objects if is_waypoint(o)]
        return len(selected) == 2 and is_waypoint(context.active_object)

    def execute(self, context):
        active = context.active_object
        other = next(
            o for o in context.selected_objects
            if o != active and is_waypoint(o)
        )

        if active == other:
            self.report({'ERROR'}, "A waypoint cannot link to itself")
            return {'CANCELLED'}

        if has_link(active, other):
            self.report({'WARNING'}, "These waypoints are already linked")
            return {'CANCELLED'}

        if not add_directed_link(active, other):
            self.report({'ERROR'}, f"{active.name} already has {LINK_SLOT_COUNT} links")
            return {'CANCELLED'}

        tag_viewports_redraw()
        self.report(
            {'INFO'},
            f"Linked {get_waypoint_display_name(active)} -> {get_waypoint_display_name(other)}",
        )
        return {'FINISHED'}


class ZEN_OT_unlink_waypoints(bpy.types.Operator):
    bl_idname = "zen.unlink_waypoints"
    bl_label = "Unlink Selected Waypoints"
    bl_description = "Remove any link between two selected waypoints, checked on both sides"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        if context.mode != 'OBJECT':
            return False

        selected = [o for o in context.selected_objects if is_waypoint(o)]
        return len(selected) == 2

    def execute(self, context):
        a, b = [o for o in context.selected_objects if is_waypoint(o)][:2]

        removed = (
            remove_directed_link(a, b)
            + remove_directed_link(b, a)
        )

        if removed == 0:
            self.report({'WARNING'}, "No link found between selected waypoints")
        else:
            tag_viewports_redraw()
            self.report({'INFO'}, f"Removed {removed} link(s)")

        return {'FINISHED'}


class ZEN_OT_toggle_waypoint_links(bpy.types.Operator):
    bl_idname = "zen.toggle_waypoint_links"
    bl_label = "Toggle Link Display"
    bl_description = "Show or hide waypoint links in the 3D viewport"
    bl_options = {'REGISTER'}

    def execute(self, context):
        context.scene.zen_show_waypoint_links = not context.scene.zen_show_waypoint_links

        if context.scene.zen_show_waypoint_links:
            start_draw_handler()
        else:
            stop_draw_handler()

        tag_viewports_redraw()
        return {'FINISHED'}
