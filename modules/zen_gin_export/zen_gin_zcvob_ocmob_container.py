from .zen_gin_zcvob_ocmob_lockable import OCMobLockable


class OCMobContainer(OCMobLockable):
    """
    A lootable container (chest, barrel, sack). Property name/order
    matches the real archive struct (source:
    zk.gothickit.dev/engine/objects/oCMobContainer/):

        string contains;

    (`NumOfEntries` also exists on this class, but only in save-game
    archives, not a freshly authored world - see the class docs.)
    """

    _type_name = "oCMobContainer:oCMobLockable:oCMobInter:oCMOB:zCVob"

    def _print_additional_data(self):
        super()._print_additional_data()
        self._data_printer.print_string_property("contains", str(self._custom("contains", "")))
