import bpy
import gpu

from gpu_extras.batch import batch_for_shader

from .waypoint_links import is_waypoint, get_link_targets

DRAW_HANDLER = None
DEPSGRAPH_HANDLER = None

# Connection topology (which waypoint pairs are linked) rarely changes -
# only add/link/unlink/delete touch it - but draw_waypoint_links() used to
# rebuild it from a full bpy.data.objects scan on every single viewport
# redraw, including pure camera orbit/pan/zoom with zero scene changes.
# In a level with hundreds of objects that's a real per-frame cost paid
# exactly while the user is actively working with waypoints. Cache it and
# only rebuild when a depsgraph update says something might have changed;
# world-space positions are still read fresh from the cached objects every
# draw, so live movement of a waypoint is unaffected.
_cached_connections = None


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
    global _cached_connections

    scene = bpy.context.scene
    if scene is None or not getattr(scene, "zen_show_waypoint_links", True):
        return

    if _cached_connections is None:
        _cached_connections = collect_unique_connections()
    connections = _cached_connections
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


def _invalidate_connections_cache(scene, depsgraph):
    global _cached_connections
    _cached_connections = None


def start_draw_handler():
    global DRAW_HANDLER, DEPSGRAPH_HANDLER

    if DRAW_HANDLER is None:
        DRAW_HANDLER = bpy.types.SpaceView3D.draw_handler_add(
            draw_waypoint_links,
            (),
            'WINDOW',
            'POST_VIEW',
        )

    if DEPSGRAPH_HANDLER is None:
        DEPSGRAPH_HANDLER = _invalidate_connections_cache
        bpy.app.handlers.depsgraph_update_post.append(DEPSGRAPH_HANDLER)


def stop_draw_handler():
    global DRAW_HANDLER, DEPSGRAPH_HANDLER, _cached_connections

    if DRAW_HANDLER is not None:
        bpy.types.SpaceView3D.draw_handler_remove(DRAW_HANDLER, 'WINDOW')
        DRAW_HANDLER = None

    if DEPSGRAPH_HANDLER is not None:
        bpy.app.handlers.depsgraph_update_post.remove(DEPSGRAPH_HANDLER)
        DEPSGRAPH_HANDLER = None

    _cached_connections = None


def is_draw_handler_active():
    return DRAW_HANDLER is not None


def tag_viewports_redraw():
    for window in bpy.context.window_manager.windows:
        screen = window.screen
        if screen is None:
            continue

        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.tag_redraw()
