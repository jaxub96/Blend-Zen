from .zen_gin_zcvob import ZCVob


class OCMob(ZCVob):
    """
    Base class for the oCMOB family - the game's moveable/interactive
    world objects (chests, doors, beds, switches, ladders, wheels, fire
    sources). Not directly addable in the Blender addon; concrete
    subclasses (OCMobInter and further down) are what actually get used.

    Property names/order match the real archive struct (source:
    zk.gothickit.dev/engine/objects/oCMOB/):

        string focusName; int hitpoints; int damage; bool moveable;
        bool takeable; bool focusOverride; enum soundMaterial;
        string visualDestroyed; string owner; string ownerGuild;
        bool isDestroyed;

    Unlike a plain `zCVob` prop (whose Blender object name IS the mesh
    filename), an oCMOB's Blender object name is its unique in-game
    identity (the `vobName` other triggers address it by via
    `triggerTarget`), while its actual model is almost always a SHARED,
    reused animated asset (e.g. every chest in the game can point at
    "CHESTBIG_OCCRATELARGE.MDS"). This is exactly the same distinction
    `OCItem` already has to make between its script instance name and
    its mesh filename (see zen_gin_zcvob_ocitem.py and
    zen_waypoint_tools/item_mesh_map.py) - here it's resolved with a
    per-instance "visual_name" custom property instead of a lookup
    table, since there's no fixed global mapping the way there is for
    items. See documentation/VOB_TYPES.md for the full picture and
    documentation/USAGE_interactive_objects.md for a worked example.

    All fields are read as flat custom (ID) properties on the Blender
    object via `ZCVob._custom()` - the same addon-independent mechanism
    `ZCVobLight` uses - so this file has no dependency on the
    zen_waypoint_tools addon and keeps working from plain Python/pytest
    with a bare test double. zen_waypoint_tools' vob_ops.py / mob_props.py
    is what actually creates these properties (with UI descriptions, via
    Blender's native Custom Properties panel) when a VOB of one of these
    types is added.
    """

    _visual_object_type_2 = "zCModel"
    _visual_object_triangles_limit = 53505

    _SOUND_MATERIAL_ORDINALS = {
        "WOOD": 0, "STONE": 1, "METAL": 2, "LEATHER": 3, "CLAY": 4, "GLAS": 5,
    }

    def _visual(self):
        visual_name = str(self._custom("visual_name", "")).strip()
        return (visual_name or self._vob_name()) + ".MDS"

    def _print_additional_data(self):
        sound_material = str(self._custom("sound_material", "WOOD")).upper()

        self._data_printer.print_string_property("focusName", str(self._custom("focus_name", "")))
        self._data_printer.print_int_property("hitpoints", int(self._custom("hitpoints", 0)))
        self._data_printer.print_int_property("damage", int(self._custom("damage", 0)))
        self._data_printer.print_bool_property("moveable", bool(self._custom("moveable", False)))
        self._data_printer.print_bool_property("takeable", bool(self._custom("takeable", False)))
        self._data_printer.print_bool_property("focusOverride", False)
        self._data_printer.print_enum_property(
            "soundMaterial", self._SOUND_MATERIAL_ORDINALS.get(sound_material, 0)
        )
        self._data_printer.print_string_property("visualDestroyed", "")
        self._data_printer.print_string_property("owner", str(self._custom("owner", "")))
        self._data_printer.print_string_property("ownerGuild", str(self._custom("owner_guild", "")))
        self._data_printer.print_bool_property("isDestroyed", False)
