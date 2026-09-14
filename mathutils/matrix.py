from .vector import Vector


class Matrix(tuple):
    """Minimal stand-in for bpy's mathutils.Matrix - just enough for the
    pure-Python test suite (no Blender install) to exercise real
    matrix/vector math: construction from rows, Identity, and `@` for
    Matrix@Vector. Test fixtures needing an arbitrary transform build one
    as a literal row tuple (see test_zcvob_bounding_box.py) rather than
    through classmethods this stub doesn't need to provide."""

    def __new__(cls, rows=None):
        if rows is None:
            rows = Matrix.Identity(4)
        # Rows are stored as given (not coerced to plain float tuples):
        # Quaternion.to_matrix() below builds a Matrix out of Vector rows,
        # and callers rely on iterating it back into Vector-like rows
        # (see ZCVob.convert_vector). Only Identity() builds a matrix
        # meant for real indexed math (__matmul__).
        return super().__new__(cls, tuple(rows))

    @classmethod
    def Identity(cls, size=4):
        return cls(tuple(tuple(1.0 if i == j else 0.0 for j in range(size)) for i in range(size)))

    def __matmul__(self, other):
        size = len(self)
        homogeneous = (other.x, other.y, other.z, 1.0)[:size]
        result = [sum(self[i][k] * homogeneous[k] for k in range(size)) for i in range(size)]
        return Vector(result[:3])
