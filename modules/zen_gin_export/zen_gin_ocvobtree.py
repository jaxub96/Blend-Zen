from .zen_gin_zcvob_ocitem import OCItem
from .zen_gin_zcvob_zcvobspot import ZCVobSpot
from .zen_gin_zcvob_startpoint import ZCVobStartpoint
from .zen_gin_zcvob_light import ZCVobLight
from .zen_gin_zcvob import ZCVob
from .zen_gin_zcvob_level_compo import ZCVobLevelCompo
from .printer import Printer
from .zen_gin_zcvob_sound import ZCVobSound
from .zen_gin_zcvob_ocmob_inter import OCMobInter
from .zen_gin_zcvob_ocmob_container import OCMobContainer
from .zen_gin_zcvob_ocmob_door import OCMobDoor
from .zen_gin_zcvob_ocmob_bed import OCMobBed
from .zen_gin_zcvob_ocmob_switch import OCMobSwitch
from .zen_gin_zcvob_ocmob_ladder import OCMobLadder
from .zen_gin_zcvob_ocmob_wheel import OCMobWheel
from .zen_gin_zcvob_ocmob_fire import OCMobFire

class OCVobTree:

    # prefix -> vob class. Every prefix ends in ":", so one name being a
    # textual prefix of another can't cause an ambiguous match - order
    # doesn't matter.
    _VOB_CLASSES = {
        "zCVob:": ZCVob,
        "oCItem:": OCItem,
        "zCVobSpot:": ZCVobSpot,
        "zCVobStartpoint:": ZCVobStartpoint,
        "zCVobLevelCompo:": ZCVobLevelCompo,
        "zCVobLight:": ZCVobLight,
        "zCVobSound:": ZCVobSound,
        "oCMobContainer:": OCMobContainer,
        "oCMobDoor:": OCMobDoor,
        "oCMobBed:": OCMobBed,
        "oCMobSwitch:": OCMobSwitch,
        "oCMobLadder:": OCMobLadder,
        "oCMobWheel:": OCMobWheel,
        "oCMobFire:": OCMobFire,
        "oCMobInter:": OCMobInter,
    }

    @staticmethod
    def __vob_order(vob):
        if isinstance(vob, ZCVobLevelCompo):
            return 0
        elif isinstance(vob, ZCVob):
            return 1
        elif isinstance(vob, OCItem):
            return 2
        elif isinstance(vob, ZCVobSpot):
            return 3
        elif isinstance(vob, ZCVobSound):
            return 4

    def __create_vob(self, blender_object):
        for prefix, vob_class in OCVobTree._VOB_CLASSES.items():
            if blender_object.name.startswith(prefix):
                return vob_class(blender_object, self.__printer, self.__data_printer)
        return None

    def __init__(self, blender_objects, printer: Printer, data_printer):
        self.__printer = printer
        self.__data_printer = data_printer
        mapped_vobs = list(map(self.__create_vob, blender_objects))
        filtered_vobs = [i for i in mapped_vobs if i is not None]
        filtered_vobs.sort(key=OCVobTree.__vob_order)
        self.__vob_tree = filtered_vobs

    def objects_count(self):
        object_index = 0
        for index, vob in enumerate(self.__vob_tree):
            vob: ZCVob = vob
            object_index = vob.updated_object_index(object_index)
        return object_index

    def __print_vob_tree_block_start(self):
        self.__data_printer.start_object_block(type_1="VobTree")

    def __print_vob_tree_block_end(self):
        self.__print_children_count(index=len(self.__vob_tree))
        self.__data_printer.end_object_block()

    def __print_children_count(self, index):
        children_count = len(self.__vob_tree) if index == 0 else 0
        childs_property_name = "childs{index}".format(index=index)
        self.__data_printer.print_int_property(childs_property_name, children_count)

    def __print_vob(self, vob: ZCVob, index, object_index):
        self.__print_children_count(index)
        return vob.print(object_index)

    def __print_vobs(self, object_index):
        for index, vob in enumerate(self.__vob_tree):
            object_index = self.__print_vob(vob, index, object_index)
        return object_index

    def print(self, object_index):
        self.__print_vob_tree_block_start()
        object_index = self.__print_vobs(object_index)
        self.__print_vob_tree_block_end()
        return object_index
