from .zen_gin_zcvob_no_visual import NoVisualObjectVob


class ZCVobStartpoint(NoVisualObjectVob):
    _type_name = "zCVobStartpoint:zCVob"
    _triangles_limit = 52224
    _static = False
    _collision = False

    def _visual(self):
        return ""
