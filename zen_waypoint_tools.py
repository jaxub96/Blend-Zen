bl_info = {
    "name": "Zen Waypoint Tools",
    "author": "jaxub + patched",
    "version": (2, 0, 0),
    "blender": (5, 0, 0),
    "location": "View3D > Sidebar > ZenGin",
    "description": "Place, link, and visualize zCWaypoint objects for ZenGin waynet export",
    "category": "Object",
}

import bpy
import bmesh
import gpu

from gpu_extras.batch import batch_for_shader


WAYPOINT_PREFIX = "zCWaypoint:"
LINK_SLOT_NAMES = ("link_a", "link_b", "link_c")
LINK_SLOT_COUNT = len(LINK_SLOT_NAMES)
DRAW_HANDLER = None


# ---------------------------------------------------------------------------
# Link storage
#
# Each waypoint object gets a `zen_waypoint_links` PropertyGroup (registered
# below) with three PointerProperty(type=bpy.types.Object) slots. This is a
# native, documented Blender mechanism for storing object references as
# custom data - unlike an earlier version of this tool, which stored links
# as custom values on a Geometry Nodes modifier attached to each waypoint
# (a trick to get free "pick an object" UI fields without writing a
# PropertyGroup). That trick broke starting around Blender 5.2: the
# modifier's dict-style value access (`mod.get(...)`, `mod[...]`,
# `mod.keys()`) started raising
# "TypeError: this type doesn't support IDProperties" outright, meaning the
# underlying storage model for Geometry Nodes modifier inputs is no longer
# compatible with that approach. PointerProperty on a PropertyGroup doesn't
# depend on Geometry Nodes internals at all, so it isn't exposed to the same
# kind of breakage.
#
# Storage stays SINGLE-DIRECTIONAL on purpose: each connection is written
# on exactly ONE endpoint. This matches the exporter's WayNet class, which
# emits one "way" per stored link it finds while scanning all waypoints -
# storing the same connection on both ends would export it twice (doubling
# numWays and writing duplicate way pairs into the archive). It also means
# each waypoint's 3 link slots can hold 3 *real* distinct neighbors, instead
# of burning 2 slots just to keep a simple chain connected both ways.
#
# The UI still *feels* bidirectional: get_effective_neighbors() below unions
# a waypoint's own outgoing links with any incoming links found by scanning
# other waypoints, so the panel and the viewport wires show the full picture
# regardless of which side a given connection happened to be stored on.
# ---------------------------------------------------------------------------

class ZenWaypointLinks(bpy.types.PropertyGroup):
    link_a: bpy.props.PointerProperty(type=bpy.types.Object, name="Link A")
    link_b: bpy.props.PointerProperty(type=bpy.types.Object, name="Link B")
    link_c: bpy.props.PointerProperty(type=bpy.types.Object, name="Link C")


def is_waypoint(obj):
    """A waypoint is defined solely by its export name prefix.

    This intentionally matches the exporter's own check
    (`blender_object.name.startswith("zCWaypoint:")`) exactly, so this tool
    can never disagree with what actually gets written to the .ZEN file.
    """
    return obj is not None and obj.name.startswith(WAYPOINT_PREFIX)


def get_waypoint_display_name(obj):
    return obj.name


def get_links(obj):
    """Return the ZenWaypointLinks PropertyGroup for obj, or None if unavailable."""
    return getattr(obj, "zen_waypoint_links", None)


def get_link_targets(obj):
    """Return (slot_name, target) tuples for this object's own occupied link slots."""
    links = get_links(obj)
    if links is None:
        return []

    result = []
    for slot in LINK_SLOT_NAMES:
        target = getattr(links, slot, None)
        if target is not None:
            result.append((slot, target))
    return result


def get_empty_link_slot(obj):
    links = get_links(obj)
    if links is None:
        return None

    for slot in LINK_SLOT_NAMES:
        if getattr(links, slot, None) is None:
            return slot
    return None


def has_link(source, target):
    """True if a connection exists between source and target, stored on either side."""
    if any(t == target for _, t in get_link_targets(source)):
        return True
    if any(t == source for _, t in get_link_targets(target)):
        return True
    return False


def add_directed_link(source, target):
    """Store one link on source's next free slot. Returns False if source is full or invalid."""
    links = get_links(source)
    if links is None:
        return False

    slot = get_empty_link_slot(source)
    if slot is None:
        return False

    setattr(links, slot, target)
    return True


def remove_directed_link(source, target):
    """Remove every occurrence of target from source's own slots. Returns number removed."""
    links = get_links(source)
    if links is None:
        return 0

    removed = 0
    for slot in LINK_SLOT_NAMES:
        if getattr(links, slot, None) == target:
            setattr(links, slot, None)
            removed += 1
    return removed


def get_effective_neighbors(obj):
    """All waypoints connected to obj, regardless of which side stores the link."""
    neighbors = []
    seen = set()

    for _, target in get_link_targets(obj):
        key = target.as_pointer()
        if key not in seen:
            seen.add(key)
            neighbors.append(target)

    for other in bpy.data.objects:
        if other == obj or not is_waypoint(other):
            continue
        for _, target in get_link_targets(other):
            if target == obj:
                key = other.as_pointer()
                if key not in seen:
                    seen.add(key)
                    neighbors.append(other)

    return neighbors


def count_links(obj):
    """Effective neighbor count (outgoing + incoming), for capacity/display purposes."""
    return len(get_effective_neighbors(obj))


def find_next_waypoint_name():
    existing_numbers = set()

    for obj in bpy.data.objects:
        if not is_waypoint(obj):
            continue

        suffix = obj.name[len(WAYPOINT_PREFIX):].split(".")[0]
        if suffix.startswith("WP_"):
            num_part = suffix[3:]
            if num_part.isdigit():
                existing_numbers.add(int(num_part))

    next_num = 1
    while next_num in existing_numbers:
        next_num += 1

    return f"{WAYPOINT_PREFIX}WP_{next_num:03d}"


# ---------------------------------------------------------------------------
# Viewport wire visualization
# ---------------------------------------------------------------------------

def collect_unique_connections():
    """Collect unique undirected waypoint connections for viewport display."""
    connections = set()

    for source in bpy.data.objects:
        if not is_waypoint(source):
            continue

        for _, target in get_link_targets(source):
            if not is_waypoint(target) or target == source:
                continue

            a = source.as_pointer()
            b = target.as_pointer()
            key = (a, b) if a < b else (b, a)
            connections.add((key, source, target))

    return [(source, target) for _, source, target in connections]


def draw_waypoint_links():
    """Draw unique waypoint connections in the 3D viewport."""
    scene = bpy.context.scene
    if scene is None or not getattr(scene, "zen_show_waypoint_links", True):
        return

    connections = collect_unique_connections()
    if not connections:
        return

    positions = []
    for source, target in connections:
        positions.append(tuple(source.matrix_world.translation))
        positions.append(tuple(target.matrix_world.translation))

    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINES', {"pos": positions})

    try:
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.line_width_set(2.5)

        shader.bind()
        shader.uniform_float("color", (0.15, 0.7, 1.0, 0.9))
        batch.draw(shader)
    finally:
        gpu.state.line_width_set(1.0)
        gpu.state.depth_test_set('NONE')
        gpu.state.blend_set('NONE')


def start_draw_handler():
    global DRAW_HANDLER

    if DRAW_HANDLER is None:
        DRAW_HANDLER = bpy.types.SpaceView3D.draw_handler_add(
            draw_waypoint_links,
            (),
            'WINDOW',
            'POST_VIEW',
        )


def stop_draw_handler():
    global DRAW_HANDLER

    if DRAW_HANDLER is not None:
        bpy.types.SpaceView3D.draw_handler_remove(DRAW_HANDLER, 'WINDOW')
        DRAW_HANDLER = None


def tag_viewports_redraw():
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        if screen is None:
            continue

        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()


# ---------------------------------------------------------------------------
# Operators
# ---------------------------------------------------------------------------

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

        mesh = bpy.data.meshes.new(name + "_mesh")
        bm = bmesh.new()
        bmesh.ops.create_cube(bm, size=0.15)
        bm.to_mesh(mesh)
        bm.free()

        obj = bpy.data.objects.new(name, mesh)
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


# ---------------------------------------------------------------------------
# Panel
# ---------------------------------------------------------------------------

class ZEN_PT_waypoint_tools(bpy.types.Panel):
    bl_label = "Zen Waypoints"
    bl_idname = "ZEN_PT_waypoint_tools"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ZenGin"

    def draw(self, context):
        if context.scene.zen_show_waypoint_links and DRAW_HANDLER is None:
            start_draw_handler()

        layout = self.layout
        waypoints = [o for o in bpy.data.objects if is_waypoint(o)]

        layout.label(text=f"Waypoints in file: {len(waypoints)}")

        layout.operator("zen.add_waypoint", icon='ADD')

        row = layout.row(align=True)
        row.operator("zen.link_waypoints", icon='LINKED')
        row.operator("zen.unlink_waypoints", icon='UNLINKED')

        layout.separator()

        row = layout.row()
        icon = 'HIDE_OFF' if context.scene.zen_show_waypoint_links else 'HIDE_ON'
        text = "Hide Link Display" if context.scene.zen_show_waypoint_links else "Show Link Display"
        row.operator("zen.toggle_waypoint_links", text=text, icon=icon)

        active = context.active_object
        if is_waypoint(active):
            layout.separator()
            links = get_links(active)
            if links is not None:
                col = layout.column(align=True)
                col.label(text="Link slots (drag objects in directly):")
                col.prop(links, "link_a", text="A")
                col.prop(links, "link_b", text="B")
                col.prop(links, "link_c", text="C")

            neighbors = get_effective_neighbors(active)
            layout.label(text=f"Links: {len(neighbors)}/{LINK_SLOT_COUNT}")
            for target in neighbors:
                layout.label(text=f"- {get_waypoint_display_name(target)}", icon='FORWARD')


classes = (
    ZenWaypointLinks,
    ZEN_OT_add_waypoint,
    ZEN_OT_link_waypoints,
    ZEN_OT_unlink_waypoints,
    ZEN_OT_toggle_waypoint_links,
    ZEN_PT_waypoint_tools,
)


def register():
    for cls in classes:
        bpy.utils.register_class(cls)

    bpy.types.Object.zen_waypoint_links = bpy.props.PointerProperty(type=ZenWaypointLinks)

    bpy.types.Scene.zen_show_waypoint_links = bpy.props.BoolProperty(
        name="Show Waypoint Links",
        description="Display waypoint links in the 3D viewport",
        default=True,
    )


def unregister():
    stop_draw_handler()

    if hasattr(bpy.types.Scene, "zen_show_waypoint_links"):
        del bpy.types.Scene.zen_show_waypoint_links

    if hasattr(bpy.types.Object, "zen_waypoint_links"):
        del bpy.types.Object.zen_waypoint_links

    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
