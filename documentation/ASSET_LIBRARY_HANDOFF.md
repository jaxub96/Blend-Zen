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

- **`Items/Items_ITMW.blend`**: 160 `oCItem:` objects total. Exactly
  **1** has been fully processed and verified end-to-end:
  `oCItem:ITMW_1H_BAU_AXE` - real mesh (38 verts, 2 materials), marked as
  a Blender asset, catalog `Items/ITMW` assigned, real rendered preview
  thumbnail confirmed (not blank). **The other 159 in this file are
  still empty placeholders** (asset-marked Empties with no geometry).
- **No other category file has been touched yet** (there are ~30+ more
  under `Items/`, plus separate Mobs/Props/etc. categories planned but
  not started).
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
testing.

## Known gotchas hit during development (read before continuing)

1. **AddonPreferences reset when the addon is reloaded via
   `del sys.modules[...]` + reimport** (not via a normal UI toggle) -
   `mesh_directories` and `asset_library_root` both need re-setting
   after this kind of reload. If picking this up in a fresh Blender
   session (not a reload), preferences should already be intact from
   whatever was last saved via "Save Preferences" - check before
   assuming they're empty.
2. **Save frequently.** Blender crashed once during this work and all
   unsaved progress (5 populated assets) was lost, reverting to a clean
   160-Empty baseline. Only the single asset populated *after* that
   crash, verified, and immediately saved actually persisted. Don't
   accumulate a large unsaved batch - save every 10-20 items if running
   interactively.
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

## Immediate next step

Finish `Items_ITMW.blend`: open it, confirm `mesh_directories` and
`asset_library_root` preferences are set, click "Populate Asset Previews
(This File)" (or use `max_count` for a smaller test batch first), verify
a few thumbnails look right, save. Then repeat per category file across
the rest of `Items/`.

## Longer-term / not started

- Mobs/props categories (only Items/ has begun).
- No UI yet for running the populate operator across *all* category
  files in one go - currently one file at a time, opened manually.
- The plan doc `PLAN_vob_mesh_preview.md` covers the earlier live-scene
  mesh-preview feature (a different, related but distinct feature from
  this asset library) - don't confuse the two.
