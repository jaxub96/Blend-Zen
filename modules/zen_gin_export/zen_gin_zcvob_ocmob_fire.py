from .zen_gin_zcvob_ocmob_inter import OCMobInter


class OCMobFire(OCMobInter):
    """
    A usable fire source (campfires, forges) with NPC seating slots.
    Property names/order match the real archive struct (source:
    zk.gothickit.dev/engine/objects/oCMobFire/):

        string fireSlot; string fireVobtreeName;
    """

    _type_name = "oCMobFire:oCMobInter:oCMOB:zCVob"

    def _print_additional_data(self):
        super()._print_additional_data()
        self._data_printer.print_string_property("fireSlot", str(self._custom("fire_slot", "")))
        self._data_printer.print_string_property("fireVobtreeName", str(self._custom("fire_vobtree_name", "")))
