from .zen_gin_zcvob_ocmob import OCMob


class OCMobInter(OCMob):
    """
    Generic interactive object (oCMobInter) - anything the player/NPCs
    can "use", sending an OnTrigger event to `triggerTarget` when they
    do. Addable directly for a custom interactive prop that doesn't fit
    one of the more specific subclasses below (OCMobDoor, OCMobBed,
    etc.) - those all inherit this same set of fields.

    Property names/order match the real archive struct (source:
    zk.gothickit.dev/engine/objects/oCMobInter/):

        int stateNum; string triggerTarget; string useWithItem;
        string conditionFunc; string onStateFunc; bool rewind;
    """

    _type_name = "oCMobInter:oCMOB:zCVob"

    def _print_additional_data(self):
        super()._print_additional_data()
        self._data_printer.print_int_property("stateNum", int(self._custom("state_num", 0)))
        self._data_printer.print_string_property("triggerTarget", str(self._custom("trigger_target", "")))
        self._data_printer.print_string_property("useWithItem", str(self._custom("use_with_item", "")))
        self._data_printer.print_string_property("conditionFunc", str(self._custom("condition_func", "")))
        self._data_printer.print_string_property("onStateFunc", str(self._custom("on_state_func", "")))
        self._data_printer.print_bool_property("rewind", bool(self._custom("rewind", False)))
