from .zen_gin_ocvobtree import OCVobTree
from .zen_gin_waynet import WayNet
from .printer import Printer
from .zen_gin_data_printer import ZenGinDataPrinter


class ZenArchive:
    """An uncompiled ZEN: header, then one oCWorld block holding the vob
    tree and the waynet. Object indices are threaded through every block
    (vob tree first, then waynet) and the header states the total."""

    def __init__(self, blender_objects, printer: Printer):
        blender_objects = list(blender_objects)
        self._printer = printer
        self._data_printer = ZenGinDataPrinter(printer)
        self._vob_tree = OCVobTree(blender_objects, self._data_printer)
        self._way_net = WayNet(blender_objects, self._data_printer)

    def objects_count(self):
        return 1 + self._vob_tree.objects_count() + self._way_net.objects_count

    def print(self):
        for line in (
            "ZenGin Archive", "ver 1", "zCArchiverGeneric", "ASCII", "saveGame 0",
            # Fixed date keeps exports byte-identical between runs (diffable).
            "date 1.1.1970 12:0:0",
            "user BlenderZenGinExportPlugin", "END",
            f"objects {self.objects_count()}", "END", "",
        ):
            self._printer.print(line)

        p = self._data_printer
        p.start_object_block(type_2="oCWorld:zCWorld", triangles_limit=36865, object_index=0)
        object_index = self._vob_tree.print(object_index=1)
        self._way_net.print(object_index=object_index)
        p.start_object_block(type_1="EndMarker")
        p.end_object_block()
        p.end_object_block()
