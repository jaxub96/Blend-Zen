from .zen_gin_zcvob_no_visual import NoVisualObjectVob


class ZCVobSound(NoVisualObjectVob):
    _type_name = "zCVobSound:zCVob"
    _triangles_limit = 0
    _static = False
    _collision = False

    def _visual(self):
        return ""
