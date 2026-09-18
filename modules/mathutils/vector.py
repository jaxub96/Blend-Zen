class Vector:
    """Minimal stand-in for bpy's mathutils.Vector, just enough for the
    pure-Python test suite (no Blender install) to exercise real vector
    math (see zen_gin_zcvob.py's bounding-box code, the first user of
    actual Vector construction/iteration outside Blender)."""

    def __init__(self, seq=(0.0, 0.0, 0.0)):
        self.x, self.y, self.z = (float(v) for v in seq)

    def __iter__(self):
        yield self.x
        yield self.y
        yield self.z
