"""Sound emitters. sndName is the `sound_name` custom property (blank =
the vob's own name); the bbox is a cube of sndRadius around the vob, as
Spacer writes it. zCVobSoundDaytime plays sndName between sndStartTime and
sndEndTime (hours) and sndName2 the rest of the day."""

from .zen_gin_zcvob import _named

ZCVobSound = _named("ZCVobSound", "zCVobSound")
ZCVobSoundDaytime = _named("ZCVobSoundDaytime", "zCVobSoundDaytime")
