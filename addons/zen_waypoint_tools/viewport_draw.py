"""
Viewport display of waypoint links.

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

from .waypoint_links import is_waypoint, get_link_targets

_draw_handle = None
_cached_connections = None


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


def _draw_waypoint_links():
    global _cached_connections
    scene = bpy.context.scene
    if scene is None or not getattr(scene, "zen_show_waypoint_links", False):
        return

    if _cached_connections is None:
        _cached_connections = collect_unique_connections(scene.objects)
    try:
        positions = [
            tuple(obj.matrix_world.translation)
            for pair in _cached_connections for obj in pair
        ]
    except ReferenceError:  # an object was deleted since the last rebuild
        _cached_connections = None
        return
    if not positions:
        return

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


@persistent
def _invalidate_cache(*_args):
    global _cached_connections
    _cached_connections = None


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
