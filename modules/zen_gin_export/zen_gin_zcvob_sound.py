from .zen_gin_zcvob import NoVisualObjectVob
from .vob_fields import SOUND_FIELDS, print_fields


class ZCVobSound(NoVisualObjectVob):
    """Ambient sound emitter. sndName is the vob's own name (the sound's
    script instance, e.g. OW_COASTLIGHT); volume, mode, delay and radius
    come from custom properties (vob_fields.SOUND_FIELDS). Defaults and
    field order follow real Spacer-saved worlds."""
    _type_name = "zCVobSound:zCVob"
    _class_version = 12289
    _static = False
    _collision = False

    def _print_additional_data(self):
        print_fields(self._data_printer, SOUND_FIELDS, self._custom)
        self._data_printer.print_string_property("sndName", self._vob_name())
