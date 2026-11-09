"""
The oCMOB family: interactive objects (chests, doors, beds, switches,
ladders, wheels, fire sources).

The Blender object name is the instance's unique vobName (what a
triggerTarget addresses); the model is a shared, already-animated .MDS
named by the `visual_name` custom property (blank = the vob's own name;
an explicit .ASC/.3DS extension is kept).
Every other field is a flat custom property - see vob_fields.py.

Class chains and versions are copied from real Spacer-saved worlds:
oCMobLockable is NOT part of the persisted chain (`oCMobDoor:oCMobInter:
oCMOB:zCVob`), and the `zCModel` visual block has version 0. Switch,
wheel and fire don't appear in the sample worlds; they use oCMobInter's
version (35585), unverified.
"""

from .zen_gin_zcvob import ZCVob
from .vob_fields import FIELDS_BY_TYPE, print_fields


class OCMobInter(ZCVob):
    _type_name = "oCMobInter:oCMOB:zCVob"
    _class_version = 35585
    _visual_type = "zCModel"
    _visual_version = 0

    @classmethod
    def _base_type(cls):
        return cls._type_name.split(":", 1)[0]

    def _visual(self):
        """visual_name with its extension if it has one (vanilla mobs also
        use .ASC models and static .3DS meshes), else <name>.MDS."""
        visual_name = str(self._custom("visual_name", "")).strip() or self._vob_name()
        return visual_name if "." in visual_name else visual_name + ".MDS"

    def print(self, object_index):
        # A static .3DS mesh gets a zCProgMeshProto visual block, as in Spacer.
        if self._visual().upper().endswith(".3DS"):
            self._visual_type, self._visual_version = "zCProgMeshProto", 53505
        return super().print(object_index)

    def _print_additional_data(self):
        print_fields(self._data_printer, FIELDS_BY_TYPE[self._base_type()], self._custom)


class OCMobContainer(OCMobInter):
    _type_name = "oCMobContainer:oCMobInter:oCMOB:zCVob"
    _class_version = 64513


class OCMobDoor(OCMobInter):
    _type_name = "oCMobDoor:oCMobInter:oCMOB:zCVob"
    _class_version = 64513


class OCMobBed(OCMobInter):
    _type_name = "oCMobBed:oCMobInter:oCMOB:zCVob"
    _class_version = 61440


class OCMobLadder(OCMobInter):
    _type_name = "oCMobLadder:oCMobInter:oCMOB:zCVob"


class OCMobSwitch(OCMobInter):
    _type_name = "oCMobSwitch:oCMobInter:oCMOB:zCVob"


class OCMobWheel(OCMobInter):
    _type_name = "oCMobWheel:oCMobInter:oCMOB:zCVob"


class OCMobFire(OCMobInter):
    _type_name = "oCMobFire:oCMobInter:oCMOB:zCVob"
