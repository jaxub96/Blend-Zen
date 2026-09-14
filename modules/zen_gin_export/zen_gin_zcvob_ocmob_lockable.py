from .zen_gin_zcvob_ocmob_inter import OCMobInter


class OCMobLockable(OCMobInter):
    """
    Base for oCMOB types that can be locked (oCMobContainer, oCMobDoor).
    Not directly addable - it exists purely so both subclasses share one
    definition of these fields.

    Property names/order match the real archive struct (source:
    zk.gothickit.dev/engine/objects/oCMobLockable/):

        bool locked; string keyInstance; string pickLockStr;
    """

    def _print_additional_data(self):
        super()._print_additional_data()
        self._data_printer.print_bool_property("locked", bool(self._custom("locked", False)))
        self._data_printer.print_string_property("keyInstance", str(self._custom("key_instance", "")))
        self._data_printer.print_string_property("pickLockStr", str(self._custom("picklock_str", "")))
