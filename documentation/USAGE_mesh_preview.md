# Using Mesh Preview + Building a Gothic Asset Library

## How it works

"Load Mesh Preview" works on both `zCVob:` props and `oCItem:` items
(`_PREVIEWABLE_PREFIXES` in `mesh_preview.py`). Three things happen in
order:

1. **Name resolution.**
   - `zCVob:` - the vob's name (minus the prefix, minus anything after a
     dot) **is** the mesh filename - exactly the same convention the
     exporter itself uses for the `visual` property.
     `zCVob:NW_CITY_CANDLE_01` looks for `NW_CITY_CANDLE_01.MRM`.
   - `oCItem:` - the vob's name is the item's *script instance name*
     (e.g. `ITMW_1H_PAL_SWORD`), which is generally a **different**
     string from its mesh filename (e.g. `ITMW_030_1H_PAL_SWORD_02`) -
     confirmed via a real Spacer test (see `zen_gin_zcvob_ocitem.py`).
     This gets resolved through `item_mesh_map.py`, a user-maintained
     JSON lookup at `asset_catalog/item_mesh_map.json` (instance name ->
     mesh filename, case-insensitive, re-read on every lookup so edits
     take effect immediately). If the instance has no entry yet, you get
     a warning telling you to add one - it doesn't fall back to guessing.
2. **Search.** The resolved mesh name is searched for, case-insensitively,
   across your **configured mesh directories** (Preferences > Add-ons >
   Zen Waypoint Tools > Mesh directories - see below), first configured
   directory wins. `.MRM` is Gothic's *compiled* mesh format - what
   shipped assets actually are - not `.3ds` (the editable source format,
   mostly relevant only for your own in-progress custom meshes).
3. **Import + parent.** The real mesh is imported via KrxImpExp's own
   importer, then parented under the vob empty so it inherits the vob's
   position/rotation automatically.

The imported mesh is a **completely separate object** from the vob
empty - it lives in its own `"Zen VOB Previews"` collection, is tagged
with a `zen_is_preview` custom property, and gets a `(preview)` suffix.
This is deliberate: the vob empty is the only thing the exporter ever
reads (name + transform), so nothing about the preview system can affect
what actually gets written to the uncompiled ZEN. You can delete, hide,
or ignore preview objects freely - re-running "Load Mesh Preview"
replaces the old preview rather than duplicating it.

**Batch operators.** Next to "Load Mesh Preview" are two scene-wide
buttons (`mesh_preview.py`):
- **Load All** (`ZEN_OT_load_all_vob_meshes`) - loads a preview for every
  `zCVob:`/`oCItem:` in the scene that doesn't already have one. Safe to
  re-run any time you've added a few new vobs - already-previewed
  objects are skipped by default. A source mesh changed on disk? Run it
  once, then open the redo panel (bottom-left of the viewport, or F9)
  and tick **Force Reload** to redo everything instead of only what's
  missing.
- **Clear All** (`ZEN_OT_clear_vob_previews`) - removes every
  `zen_is_preview`-tagged object in the scene in one go, vob empties
  untouched.

Either one reports a summary popup (`Loaded N/M preview(s)`); if any
individual object failed, the popup says how many and the full per-object
reason goes to Blender's system console (**Window > Toggle System
Console** on Windows) rather than a batch run failing outright on the
first miss.

**Not covered:** the oCMOB interactive-object family (chest, door, bed,
switch, ladder, wheel, fire) has no preview support at all - they use
animated `.MDS` models, not static `.MRM` meshes, which this mechanism
doesn't know how to import. See `USAGE_interactive_objects.md`.

## Configuring mesh directories (Preferences)

**Preferences > Add-ons > Zen Waypoint Tools** has a real directory list
(`ZenWaypointToolsPreferences` in `preferences.py`) - not a hardcoded
path. **Add path** (file browser, single directory), **Add path with
subpaths** (recursively adds every subdirectory beneath the one you
pick - the fast way to register a whole `_compiled` tree at once),
**Remove path**, and **Remove all paths**. This same directory list
drives both mesh preview's search (above) and the live catalog scan
(below) - one place to configure it, no separate per-feature settings.

## The searchable name catalogs (live scan, not a static file)

The **Add VOB** dialog's Name field autocompletes against three
window-manager-level collections, all populated by scanning your
configured mesh directories directly - not a checked-in static file:

- `wm.zen_mesh_catalog` - every non-item `.MRM` found, for `zCVob:` prop
  names.
- `wm.zen_item_catalog` - every `.MRM` matching Gothic's `ITxx_...` item
  naming convention (melee weapons, armor, runes, scrolls, misc, ...),
  kept separate so item meshes don't clutter the prop dropdown.
- `wm.zen_item_instance_catalog` - every key in `item_mesh_map.json`,
  for `oCItem:` **instance names** (not mesh names - see above).

Click the refresh icon next to "Add Other VOBs" (`ZEN_OT_refresh_mesh_catalog`,
in `mesh_catalog.py`) any time your directory list or its contents
change - there's no automatic file-watching. `asset_catalog/gothic2_meshes.json`
is a one-time generated snapshot kept only as a static reference now
that this live scan exists; don't treat it as authoritative for what's
currently searchable.

`item_mesh_map.json`, by contrast, is **not** superseded by anything -
it's the actual, actively-read source of truth for item instance -> mesh
resolution (see `item_mesh_map.py`'s module docstring for the exact JSON
shape it accepts). It starts empty and grows as you discover mappings
while working; there's no way to derive it automatically since it comes
from Gothic's compiled Daedalus scripts, not the mesh files themselves.

## How to use it, step by step

1. Add a prop with **Add Other VOBs > Vob (Mesh Prop)**, naming it
   exactly after a real mesh (autocompletes against `zen_mesh_catalog`
   once you've refreshed it) - e.g. `NW_CITY_CANDLE_01`. This creates
   `zCVob:NW_CITY_CANDLE_01`. For an item, use **Add Other VOBs > Item**
   instead and name it after the real script instance (autocompletes
   against `zen_item_instance_catalog`).
2. With that object active, click **Load Mesh Preview**.
3. The real mesh appears, parented to the empty. Move/rotate the empty
   as normal - the preview follows automatically.
4. If "no mesh found" (props) or "no known mesh mapping" (items) comes
   back as a warning, double check the directory list and, for items,
   whether `item_mesh_map.json` actually has an entry for that instance
   yet.
5. When your scene looks right, **Export Uncompiled ZEN** as usual - the
   preview objects are correctly ignored by the exporter (they don't
   have a recognized name prefix), only the real vob empties are read.

Placed a whole batch of props/items at once? Skip steps 2-4 per object
and just click **Load All** once instead - see Batch operators above.

## Quick reference: what goes where

| You want to... | Do this |
|---|---|
| Add a static prop with a real mesh | Add Other VOBs > Vob, name = mesh filename > Load Mesh Preview |
| Add a pickupable item | Add Other VOBs > Item, name = script instance name > Load Mesh Preview (needs an `item_mesh_map.json` entry) |
| Add a waypoint | Add Waypoint at Cursor (auto-links from active) |
| Add the player start | Add Other VOBs > Startpoint |
| Add a light | Add Other VOBs > Light - it's a real Blender Light, tune type/range/color/cone-angle in Blender's own Light Properties tab |
| Add an interactive object (chest/door/bed/...) | See `USAGE_interactive_objects.md` - different mechanism, no mesh preview |
| Find a mesh or item name | Refresh the catalog (Preferences or the sidebar refresh icon), then use the autocomplete in Add VOB |
| Preview every prop/item in the scene at once | Load All button |
| Remove every loaded preview at once | Clear All button |
| Configure where meshes are searched | Preferences > Add-ons > Zen Waypoint Tools > Mesh directories |
| Export for Spacer | Export Uncompiled ZEN button |
