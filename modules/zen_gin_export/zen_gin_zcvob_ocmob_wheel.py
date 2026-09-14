from .zen_gin_zcvob_ocmob_inter import OCMobInter


class OCMobWheel(OCMobInter):
    """A four-state rotating wheel mechanism (winches, waterwheels).
    Adds no fields of its own beyond OCMobInter - see
    zen_gin_zcvob_ocmob_inter.py."""

    _type_name = "oCMobWheel:oCMobInter:oCMOB:zCVob"
