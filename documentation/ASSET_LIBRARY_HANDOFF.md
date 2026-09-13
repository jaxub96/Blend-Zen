# Asset Library Feature: Handoff Status

This document exists so work on the Gothic asset library can continue in
a fresh session (Claude Code or otherwise) without needing this project's
full chat history - see the main README/ARCHITECTURE.md for the rest of
Blend-Zen, this file is specifically about the asset library work.

## What this feature is

A real Blender Asset Library (native Asset Browser, not a custom UI) of
Gothic II items/mobs/props with real meshes, textures, and thumbnail
previews, built by importing each real mesh via KrxImpExp and marking it
as a Blender asset - so placing objects into a level scene becomes drag-
and-drop from the Asset Browser instead of manual naming/importing.

## Where things live (two separate locations - important)

- **This repo** (`Blend-Zen`): the addon code that builds the library
  (`addons/zen_waypoint_tools/asset_library.py` and its dependencies).
  Git-tracked, synced across machines as usual.
- **The asset library itself** (NOT in this repo, deliberately - binary
  mesh/texture/preview data doesn't belong in git):
  `/Users/jakubjaworski/Creativity/Blender Projects/GothicBlenderAssets-master/Blender_Asset_Library_Gothic`
  Contains category `.blend` files (`Items/Items_ITMW.blend`, etc.) and
  `blender_assets.cats.txt` (the catalog definitions, plain text,
  documented Blender format).

## Current state (as of last save)

- **`Items/Items_ITMW.blend`**: **DONE - all 160/160** `oCItem:` objects
  have real geometry, are asset-marked, have a catalog assigned, and
  have a real (non-blank) rendered preview thumbnail. Verified via
  script: 0 remaining Empties, 160/160 meshes with `asset_data` set, 0
  missing textures across all 16 images in the file.
- A stray, non-asset-marked mesh object named `ITMW_007_1H_SICKLE_01`
  sits in the Scene Collection, left over from an earlier crashed run
  (predates this handoff). It doesn't correspond to any of the 160 real
  items - harmless clutter, flagged for cleanup but not yet removed
  (ask before deleting; hasn't been confirmed as safe to remove).
- **No other category file has been touched yet** (there are ~30+ more
  under `Items/`, plus separate Mobs/Props/etc. categories planned but
  not started). The next one should go much faster now that the crash
  below is fixed - see "Immediate next step".
- `blender_assets.cats.txt` currently has exactly one catalog entry:
  `Items/ITMW`.
- `asset_catalog/item_mesh_map.json` in this repo already has ~869 real
  instance-name -> mesh-filename mappings (user-provided, not something
  to regenerate).

## The core mechanism (already built, working, and tested)

`addons/zen_waypoint_tools/asset_library.py` - read this file's own
module docstring first, it documents several non-obvious Blender API
findings that took real trial-and-error to nail down:

- `Object.data` on an Empty can only ever be `None` or an `Image` - you
  CANNOT convert an Empty to a Mesh by reassigning `.data`. The working
  approach: import the mesh as a new object, then transfer identity
  (name, transform, asset metadata, collection membership) onto it and
  delete the old Empty.
- `bpy.ops.asset.mark_single()` and
  `bpy.ops.ed.lib_id_generate_preview_from_object()` need
  `bpy.context.temp_override(..., id=obj)` when called from a script -
  `active_object`/`selected_objects` alone are not enough; their poll()
  specifically checks `context.id`.
- Preview rendering is an **async background job**. Checking pixel data
  immediately after the operator call in the same script execution
  reads a still-blank image - this resolves on its own once the script
  returns control to Blender's normal event loop. Not a problem for a
  real button click; only matters if driving this via a rapid scripted
  loop.
- `asset_data.catalog_simple_name` is **read-only** (auto-derived from
  `catalog_id` by looking up the loaded catalog definitions) - only
  `catalog_id` is ever settable directly.

The operator: **"Populate Asset Previews (This File)"** button in the
ZenGin sidebar panel (`zen.populate_asset_library_file`), processes
every asset-marked Empty named `oCItem:...` in the *currently open*
file. Has a `max_count` property (0 = unlimited) for controlled batch
testing, and a `save_every` property (default 15) that auto-saves
periodically during a run.

**Runs as a background timer job, not a synchronous loop - this is
load-bearing, not a style choice.** An earlier version looped over all
targets synchronously inside `execute()`, calling
`lib_id_generate_preview_from_object()` back-to-back for each item with
no gap between calls. This reliably **crashed Blender outright**
(confirmed via a real UI button click with as few as 3 items, not just
when driven by a script) - almost certainly because it queued multiple
async preview-render jobs before any of them got a chance to finish, and
Blender's preview job system isn't built for that. The fix:
`execute()` only builds the target list and kicks off
`bpy.app.timers.register()`; a module-level callback
(`_process_next_asset` in `asset_library.py`) processes exactly **one**
item per timer tick and returns a delay (0.5s) for the next tick,
letting Blender's event loop fully settle - and each async preview job
complete - between items. Progress and failures print to the system
console (self.report can't be used from a timer callback since the
operator has already returned by the time it fires). If you ever need
to change this operator's internals again: do not go back to a
synchronous multi-item loop, and if you add any other per-item
Blender-UI-driven step (not just previews), assume it may need the same
one-per-tick treatment.

## Known gotchas hit during development (read before continuing)

1. **AddonPreferences reset on more reload paths than originally
   thought.** Confirmed to reset `mesh_directories` and
   `asset_library_root` via: `del sys.modules[...]` + reimport, AND
   `bpy.ops.preferences.addon_disable()` + `addon_enable()` (this
   contradicts an earlier version of this doc that assumed the normal
   UI disable/enable toggle was safe - it was tested via scripted
   `bpy.ops` calls, not an actual UI click, and turned out to reset
   preferences either way). **The safe way to pick up a code change to
   an already-loaded addon module without touching preferences**:
   `importlib.reload()` the specific submodule directly, then
   `bpy.utils.unregister_class()` / `register_class()` just the classes
   that changed - never disable/re-enable the whole addon and never rely
   on `bpy.ops.script.reload()` (which in one observed case silently did
   *not* pick up an edited submodule at all). If preferences do end up
   empty, they can be restored via the same `bpy.context.preferences
   .addons["zen_waypoint_tools"].preferences` API, as long as the
   previous values were read and saved somewhere first - always read
   and log current preference values before doing any reload.
2. **Save frequently, and don't assume "Empty response from Blender" /
   a dropped MCP connection means Blender is fine and just slow** - it
   can mean an actual crash. One clear signal either way: check
   `bpy.data.is_dirty` and the file's byte size right after reconnecting;
   if they match the last save exactly, in-memory progress since that
   save is gone. This happened twice during this work: once losing 5
   unsaved populated assets (reverting to a clean 160-Empty baseline),
   and once losing 1 unsaved populated asset - in both cases only work
   that had already been explicitly saved survived. Don't accumulate a
   large unsaved batch. (The `save_every` property on
   `zen.populate_asset_library_file`, default 15, exists specifically for
   this - see "Runs as a background timer job" above for why the
   operator needed a deeper fix than just saving more often.)
3. **A real, separate bug was found and fixed in KrxImpExp itself**
   (not this repo): `material.py`'s texture indexing used
   `Path(dir).glob("*.tga")`, which is case-SENSITIVE on macOS/Linux
   (only case-insensitive on Windows). Real Gothic textures are almost
   always uppercase `.TGA`, so this silently failed to find them on
   Mac. Fixed by replacing the glob with a directory scan + case-
   insensitive suffix check. **This patch lives in the installed
   KrxImpExp addon's own files, NOT in this repo** - if KrxImpExp is
   ever reinstalled/updated, this fix will be silently lost and
   textures will start going missing again. Worth reporting upstream to
   KrxImpExp's author. The exact patched function is `load_image()` in
   KrxImpExp's `material.py`.
4. **A broken image reference can outlive the bug that caused it.**
   `oCItem:ITMW_1H_BAU_AXE` (imported before gotcha #3's fix existed)
   had its `ITMELEEBLADES.TGA` image datablock saved with a bare
   filename and no directory - `Image.filepath` doesn't get
   automatically re-resolved just because the underlying import bug
   later got fixed; the broken reference sits in the `.blend` file
   until something explicitly repoints it. Fixed here by scanning
   `bpy.data.images` for any `source == 'FILE'` image whose
   `bpy.path.abspath(filepath)` doesn't exist on disk, resolving the
   correct path with a case-insensitive filename search across the
   KrxImpExp addon's own `texture_directories` preference, then setting
   `.filepath` and calling `.reload()`. Worth a quick scan like this on
   any file imported before the KrxImpExp fix landed, if a texture ever
   looks wrong.

## Immediate next step

`Items_ITMW.blend` is done (see "Current state" above). Move to the
next category file under `Items/`: open it, confirm `mesh_directories`
and `asset_library_root` preferences are set (see gotcha #1 if not),
click "Populate Asset Previews (This File)" (or use `max_count` for a
smaller test batch first - the operator is now crash-safe at any batch
size, but starting small on a new file is still a reasonable way to
catch a per-file surprise early), verify a few thumbnails look right,
confirm it auto-saved (or save manually). Then repeat across the rest of
`Items/`.

Also still pending: a stray, non-asset-marked leftover object named
`ITMW_007_1H_SICKLE_01` in `Items_ITMW.blend`'s Scene Collection (debris
from an earlier crash, unrelated to any of the 160 real items) - flagged
for cleanup but not yet deleted; get confirmation before removing it.

## Longer-term / not started

- Mobs/props categories (only Items/ has begun).
- No UI yet for running the populate operator across *all* category
  files in one go - currently one file at a time, opened manually.
- The plan doc `PLAN_vob_mesh_preview.md` covers the earlier live-scene
  mesh-preview feature (a different, related but distinct feature from
  this asset library) - don't confuse the two.
