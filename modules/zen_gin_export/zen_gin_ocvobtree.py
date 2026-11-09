from .zen_gin_zcvob import ZCVob, OCItem, ZCVobSpot, ZCVobStartpoint, ZCVobLevelCompo
from .zen_gin_zcvob_light import ZCVobLight
from .zen_gin_zcvob_sound import ZCVobSound
from .zen_gin_zcvob_ocmob import (
    OCMobInter, OCMobContainer, OCMobDoor, OCMobBed,
    OCMobSwitch, OCMobLadder, OCMobWheel, OCMobFire,
)

# Blender name prefix (before the first ":") -> vob class.
VOB_CLASSES = {
    "zCVob": ZCVob,
    "oCItem": OCItem,
    "zCVobSpot": ZCVobSpot,
    "zCVobStartpoint": ZCVobStartpoint,
    "zCVobLevelCompo": ZCVobLevelCompo,
    "zCVobLight": ZCVobLight,
    "zCVobSound": ZCVobSound,
    "oCMobContainer": OCMobContainer,
    "oCMobDoor": OCMobDoor,
    "oCMobBed": OCMobBed,
    "oCMobSwitch": OCMobSwitch,
    "oCMobLadder": OCMobLadder,
    "oCMobWheel": OCMobWheel,
    "oCMobFire": OCMobFire,
    "oCMobInter": OCMobInter,
}

# Output order: level compo first, then grouped by type; everything not
# listed (props, lights, startpoints, mobs) shares the generic slot 1.
_VOB_ORDER = {ZCVobLevelCompo: 0, OCItem: 2, ZCVobSpot: 3, ZCVobSound: 4}


def vob_class_for(blender_object):
    """The vob class for an object's name prefix, or None (not exported)."""
    prefix, sep, _ = blender_object.name.partition(":")
    return VOB_CLASSES.get(prefix) if sep else None


class OCVobTree:
    """Flat list of vobs under one VobTree block (no nesting)."""

    def __init__(self, blender_objects, data_printer):
        self._data_printer = data_printer
        vobs = []
        for obj in blender_objects:
            vob_class = vob_class_for(obj)
            if vob_class is not None:
                vobs.append(vob_class(obj, data_printer))
        vobs.sort(key=lambda vob: _VOB_ORDER.get(type(vob), 1))
        self._vobs = vobs

    def objects_count(self):
        return sum(vob._objects_count for vob in self._vobs)

    def print(self, object_index):
        p = self._data_printer
        p.start_object_block(type_1="VobTree")
        for index, vob in enumerate(self._vobs):
            # childs0 on the implicit root holds the vob count; every vob
            # is a leaf (childsN=0).
            p.print_int_property(f"childs{index}", len(self._vobs) if index == 0 else 0)
            object_index = vob.print(object_index)
        p.print_int_property(f"childs{len(self._vobs)}", 0)
        p.end_object_block()
        return object_index
