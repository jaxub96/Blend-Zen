from zen_waypoint_tools.item_mesh_map import resolve_item_mesh_name
from .zen_gin_zcvob_no_visual import NoVisualObjectVob


class OCItem(NoVisualObjectVob):
    _type_name = "oCItem:zCVob"
    _triangles_limit = 0
    _static = False
    _show_visual = False

    def _visual(self):
        return ""

    def _print_additional_data(self):
        item_instance = self._vob_name()
        mesh_name = resolve_item_mesh_name(item_instance)

        if mesh_name is None:
            raise ValueError(
                f"No mesh mapping found for oCItem instance "
                f"'{item_instance}'"
            )

        self._data_printer.print_string_property(
            "itemInstance",
            mesh_name + ".3ds",
        )