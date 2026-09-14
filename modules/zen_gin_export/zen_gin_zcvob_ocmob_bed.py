from .zen_gin_zcvob_ocmob_inter import OCMobInter


class OCMobBed(OCMobInter):
    """A sleepable bed. Adds no fields of its own beyond OCMobInter -
    see zen_gin_zcvob_ocmob_inter.py. What actually makes a bed
    sleepable in-game is its `visual` model script having the right
    state animations (see documentation/USAGE_interactive_objects.md)."""

    _type_name = "oCMobBed:oCMobInter:oCMOB:zCVob"
