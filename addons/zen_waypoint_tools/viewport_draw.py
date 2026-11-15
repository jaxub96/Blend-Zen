"""
Viewport display of waypoint links (blue lines) and trigger links (orange
arrows from the vob that fires to the vob that reacts).

The set of linked pairs only changes on add/link/unlink/delete, so it is
cached and rebuilt after a depsgraph update instead of on every redraw
(orbiting a big level stays cheap); positions are read fresh each draw.
The handlers are installed at register time and survive file loads; the
cache is dropped on load so it never holds objects from another file.
"""

import bpy
import gpu
from bpy.app.handlers import persistent
from gpu_extras.batch import batch_for_shader
from mathutils import Vector

from .waypoint_links import is_waypoint, get_link_targets

_draw_handle = None
_cached_connections = None
_cached_trigger_links = None

WAYPOINT_LINK_COLOR = (0.15, 0.7, 1.0, 0.9)
TRIGGER_LINK_COLOR = (1.0, 0.55, 0.1, 0.9)
ARROW_HEAD_LENGTH = 0.35           # metres, shortened for short links


def collect_unique_connections(objects):
    """Unique undirected (source, target) waypoint pairs among objects."""
    connections = {}
    for source in objects:
        if not is_waypoint(source):
            continue
        for _, target in get_link_targets(source):
            if target == source or not is_waypoint(target):
                continue
            a, b = source.as_pointer(), target.as_pointer()
            connections.setdefault((min(a, b), max(a, b)), (source, target))
    return list(connections.values())


def arrow_segments(start, end, head_length=ARROW_HEAD_LENGTH):
    """Line-list points for an arrow from start to end: the shaft plus a
    four-barbed head at the end (visible from any side)."""
    start, end = Vector(start), Vector(end)
    shaft = end - start
    length = shaft.length
    if length < 1e-6:
        return []
    direction = shaft / length
    head = min(head_length, length * 0.4)
    side = direction.cross(Vector((0.0, 0.0, 1.0)))
    if side.length < 1e-4:
        side = direction.cross(Vector((1.0, 0.0, 0.0)))
    side.normalize()
    up = direction.cross(side)
    base = end - direction * head
    points = [start, end]
    for barb in (side, -side, up, -up):
        points += [end, base + barb * head * 0.4]
    return [tuple(p) for p in points]


def collect_trigger_links(objects):
    """(source, target) vob pairs, or [] while the exporter library is not
    importable (it is loaded lazily)."""
    try:
        from zen_gin_export.trigger_links import trigger_link_pairs
    except ImportError:
        return []
    return trigger_link_pairs(objects)


def _draw_lines(positions, color, width):
    if not positions:
        return
    shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    batch = batch_for_shader(shader, 'LINES', {"pos": positions})
    try:
        gpu.state.blend_set('ALPHA')
        gpu.state.depth_test_set('LESS_EQUAL')
        gpu.state.line_width_set(width)
        shader.bind()
        shader.uniform_float("color", color)
        batch.draw(shader)
    finally:
        gpu.state.line_width_set(1.0)
        gpu.state.depth_test_set('NONE')
        gpu.state.blend_set('NONE')


def _draw_waypoint_links():
    global _cached_connections, _cached_trigger_links
    scene = bpy.context.scene
    if scene is None:
        return

    if getattr(scene, "zen_show_waypoint_links", False):
        if _cached_connections is None:
            _cached_connections = collect_unique_connections(scene.objects)
        try:
            positions = [
                tuple(obj.matrix_world.translation)
                for pair in _cached_connections for obj in pair
            ]
        except ReferenceError:  # an object was deleted since the last rebuild
            _cached_connections = None
            positions = []
        _draw_lines(positions, WAYPOINT_LINK_COLOR, 2.5)

    if getattr(scene, "zen_show_trigger_links", False):
        if _cached_trigger_links is None:
            _cached_trigger_links = collect_trigger_links(scene.objects)
        try:
            positions = []
            for source, target in _cached_trigger_links:
                positions += arrow_segments(
                    source.matrix_world.translation, target.matrix_world.translation)
        except ReferenceError:
            _cached_trigger_links = None
            positions = []
        _draw_lines(positions, TRIGGER_LINK_COLOR, 2.0)


@persistent
def _invalidate_cache(*_args):
    global _cached_connections, _cached_trigger_links
    _cached_connections = None
    _cached_trigger_links = None


_HANDLER_LISTS = (bpy.app.handlers.depsgraph_update_post, bpy.app.handlers.load_pre)


def register():
    global _draw_handle
    if _draw_handle is None:
        _draw_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_waypoint_links, (), 'WINDOW', 'POST_VIEW')
    for handlers in _HANDLER_LISTS:
        if _invalidate_cache not in handlers:
            handlers.append(_invalidate_cache)


def unregister():
    global _draw_handle
    if _draw_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_draw_handle, 'WINDOW')
        _draw_handle = None
    for handlers in _HANDLER_LISTS:
        if _invalidate_cache in handlers:
            handlers.remove(_invalidate_cache)
    _invalidate_cache()


def tag_viewports_redraw():
    _invalidate_cache()
    wm = bpy.context.window_manager
    for window in (wm.windows if wm else ()):
        if window.screen is None:
            continue
        for area in window.screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
