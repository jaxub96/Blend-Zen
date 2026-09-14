from .vector import Vector


class Matrix(tuple):
    """Minimal stand-in for bpy's mathutils.Matrix, just enough for the
    pure-Python test suite (no Blender install) to exercise real
    matrix/vector math: construction from rows, Identity/Translation/
    Diagonal, and `@` for both Matrix@Matrix and Matrix@Vector."""

    def __new__(cls, rows=None):
        if rows is None:
            rows = Matrix.Identity(4)
        # Rows are stored as given (not coerced to plain float tuples):
        # Quaternion.to_matrix() below builds a Matrix out of Vector rows,
        # and callers rely on iterating it back into Vector-like rows
        # (see ZCVob.convert_vector). Only the classmethods below build
        # matrices meant for real indexed math (__matmul__).
        return super().__new__(cls, tuple(rows))

    @classmethod
    def Identity(cls, size=4):
        return cls(tuple(tuple(1.0 if i == j else 0.0 for j in range(size)) for i in range(size)))

    @classmethod
    def Translation(cls, vec):
        x, y, z = vec
        return cls((
            (1.0, 0.0, 0.0, x),
            (0.0, 1.0, 0.0, y),
            (0.0, 0.0, 1.0, z),
            (0.0, 0.0, 0.0, 1.0),
        ))

    @classmethod
    def Diagonal(cls, values):
        n = len(values)
        return cls(tuple(tuple(values[i] if i == j else 0.0 for j in range(n)) for i in range(n)))

    def __matmul__(self, other):
        size = len(self)
        if isinstance(other, Matrix):
            return Matrix(tuple(
                tuple(sum(self[i][k] * other[k][j] for k in range(size)) for j in range(size))
                for i in range(size)
            ))
        homogeneous = (other.x, other.y, other.z, 1.0)[:size]
        result = [sum(self[i][k] * homogeneous[k] for k in range(size)) for i in range(size)]
        return Vector(result[:3])
