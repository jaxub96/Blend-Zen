"""
The oCMOB family: focusable objects (oCMOB: signs, gravestones) and
interactive ones (chests, doors, beds, switches, ladders, wheels, fires).

The Blender object name is the instance's vobName (what a triggerTarget
addresses); the model is the `visual_name` custom property (blank = the
vob's own name; .MDS is assumed for interactive mobs and .3DS for oCMOB,
an explicit .ASC/.3DS/.MDS extension is kept). Every other field is a flat
custom property - see vob_fields.py.

Class chains and versions are those of the vanilla worlds: oCMobLockable is
not part of the persisted chain (`oCMobDoor:oCMobInter:oCMOB:zCVob`), and
the `zCModel` visual block has version 0.
"""

from .zen_gin_zcvob import _named

OCMob = _named("OCMob", "oCMOB")
OCMobInter = _named("OCMobInter", "oCMobInter")
OCMobContainer = _named("OCMobContainer", "oCMobContainer")
OCMobDoor = _named("OCMobDoor", "oCMobDoor")
OCMobBed = _named("OCMobBed", "oCMobBed")
OCMobLadder = _named("OCMobLadder", "oCMobLadder")
OCMobSwitch = _named("OCMobSwitch", "oCMobSwitch")
OCMobWheel = _named("OCMobWheel", "oCMobWheel")
OCMobFire = _named("OCMobFire", "oCMobFire")
