import bpy
import gpu

from gpu_extras.batch import batch_for_shader

from .waypoint_links import is_waypoint, get_link_targets

DRAW_HANDLER = None


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
