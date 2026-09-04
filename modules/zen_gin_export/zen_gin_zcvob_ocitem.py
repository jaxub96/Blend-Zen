from .zen_gin_zcvob_no_visual import NoVisualObjectVob


class OCItem(NoVisualObjectVob):
    _type_name = "oCItem:zCVob"
    _triangles_limit = 0
    _static = False
    _show_visual = False

    def _visual(self):
        return ""

    def _print_additional_data(self):
        # itemInstance must be the real Daedalus script instance name
        # (the vob's own name - e.g. "ITMW_1H_PAL_SWORD"), NOT a mesh
        # filename. Confirmed via a real Spacer test: a mesh-filename-like
        # string here resolves no visual at all in-game, while the real
        # instance name correctly resolves to its mesh (visible in
        # Spacer's own vob-list export). The mesh lookup used by "Load
        # Mesh Preview" (zen_waypoint_tools/item_mesh_map.py) is a
        # Blender-preview-only concern - it must not be involved here,
        # both because it would reintroduce that exact bug, and because
        # this file (zen_gin_export) is meant to work independently of
        # the addon, even outside Blender entirely - importing from
        # zen_waypoint_tools here would break that.
        self._data_printer.print_string_property("itemInstance", self._vob_name())
