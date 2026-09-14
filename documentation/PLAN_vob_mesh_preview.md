# Plan: VOB Mesh Preview

**Status: mostly built.** This is kept as the original planning record,
not rewritten to match what shipped - see `USAGE_mesh_preview.md` for
current, accurate usage instructions. Quick scorecard against the build
order below:

- Step 1 (`zCVob:` single-object preview) - **done**, `mesh_preview.py`.
- Step 2 (configurable Preferences path list) - **done**,
  `preferences.py` (a real `AddonPreferences` UI, not the hardcoded list
  this plan assumed as a starting point). The **batch operator**
  (`ZEN_OT_load_all_vob_meshes` below) was **not** built - "Load Mesh
  Preview" only ever operates on the single active object.
- Step 3 (`oCItem:` support) - **done**, but landed as *only* Tier 2
  (`item_mesh_map.json`) below, skipping the Tier 1 name-heuristic - it
  goes straight to the lookup table and reports a warning (not a
  fallback guess) when an instance has no entry yet.
- Step 4 (batch load, clear-previews operator) - **done**:
  `ZEN_OT_load_all_vob_meshes` ("Load All") scans the scene for every
  `zCVob:`/`oCItem:` without a preview yet (skip-if-loaded by default,
  a `Force Reload` toggle in the redo panel to redo everything), and
  `ZEN_OT_clear_vob_previews` ("Clear All") removes every
  `zen_is_preview`-tagged object scene-wide. Per-object failures during
  a batch run are summarized in the report popup and detailed in the
  system console rather than failing the whole run. The one thing still
  missing from this step: no persistent "N/M previews loaded" status
  label in the panel - just the one-shot report popup each operator run
  already gives you.
- Step 5 / stretch (`zCVobLevelCompo`/`krxwrdimp` whole-world preview,
  full Daedalus-based item resolution) - **not built**, as expected for
  a stretch goal.
- Both "Open questions" at the bottom were answered as this shipped:
  `item_mesh_map.json` lives in the repo (`asset_catalog/`), and "Load
  Meshes" stayed a deliberate, separate step rather than running
  automatically on `zen.add_vob`.

The oCMOB interactive-object family (chest/door/bed/etc., added later)
is explicitly **out of scope** for this plan and has no mesh preview
support - see `USAGE_interactive_objects.md`.

---

Goal: when a vob is added in Blender (a `zCVob:` prop, an `oCItem:` item,
eventually the level mesh itself), automatically locate and import its
real Gothic mesh so it's visible in the viewport before ever opening
Spacer - turning Blender into a genuine preview of the finished world
instead of just an empty-and-icon placeholder scene.

## What was confirmed before writing this plan

Checked directly against the installed `krximpexp` addon rather than
assumed:

* `import_scene.krxmrmimp` imports `.MRM` files (`filter_glob = "*.MRM;"`).
  MRM is Gothic's **compiled** runtime mesh format - this is what shipped
  items and props actually exist as, not raw `.3ds` (which is normally
  only the editable source format for *your own* in-progress custom
  assets, before compiling). This is the right importer to target for
  "preview an existing game asset."
* Its operator signature is `filepath` / `directory` / `filter_glob` -
  a plain single-file import, no name-based search built in.
* `import_scene.krxwrdimp` imports `*.MSH;*.ZEN;` - a whole world mesh.
  Not needed for the core feature, but worth knowing it exists: a
  possible later add-on is "load the surrounding compiled world for
  spatial reference" using this operator directly on an existing ZEN.
* KrxImpExp's own addon preferences (`texture_directories`) are
  texture-search paths only. There is **no existing mesh search-path
  system** to reuse - this plan has to build one.
* `krxpref.add_path` / `remove_path` operators only manage the texture
  path collection above - do not repurpose them for meshes; build a
  separate preference collection instead (same UI pattern, different
  data).

## Scope: which vob types actually apply

| Type | Has a mesh? | Resolution |
|---|---|---|
| `zCVob:` | Yes | Object name **is** the mesh filename (already true for export - `_visual()` returns `vobname + ".3DS"`). Same name, `.MRM` extension, for preview. |
| `oCItem:` | Yes, indirectly | Object name is the **item instance name**, not the mesh filename. These are often different (e.g. an item may reuse an existing world-prop mesh). This is the hard part - see below. |
| `zCVobLevelCompo:` | Yes, but huge | Out of core scope. Possible later use of `krxwrdimp` if useful; treat as its own future feature, not part of this one. |
| `zCVobSpot:`, `zCVobStartpoint:`, `zCVobLight:` | No | Out of scope - these already have distinct viewport icons and were never meant to carry mesh geometry. |

So the real work is `zCVob:` (straightforward) and `oCItem:` (needs a
resolution strategy, phased below).

## Architecture: previews stay separate from the authoritative vob empties

The vob's Empty is the thing the exporter reads (name, position,
rotation) - nothing about mesh preview should risk touching that. Plan:

* Imported mesh becomes a **separate object**, parented to the vob
  empty (`preview_obj.parent = vob_empty`, keeping transforms in sync
  automatically - moving the empty moves its preview).
* Preview objects go into a dedicated collection, e.g. `"Zen VOB
  Previews"`, kept visually distinct and easy to hide/exclude from the
  view layer without touching the real vob data.
* Preview objects get a custom property `zen_is_preview = True` and a
  name suffix (e.g. `LIGHT_001 (preview)`) so cleanup/batch operations
  can find them unambiguously, and so they can never accidentally match
  one of the exporter's name-prefix checks.
* A vob keeps a reference to its own preview (custom property storing
  the preview object's name, or a direct object pointer property) so
  re-running "load mesh" on the same vob replaces rather than
  duplicates it.

This mirrors the same "don't let tooling touch the authoritative data"
principle already used for waypoint links (a dedicated PropertyGroup,
not raw IDProperties) - keeps the export path's assumptions intact no
matter what the preview system does.

## Mesh search paths (new addon preference)

Add a `ZenGinExportPreferences` (`AddonPreferences`) to
`zen_waypoint_tools`, with a `CollectionProperty` of search directories -
same UI shape as KrxImpExp's texture path list (Add Path / Remove Path
buttons), but for meshes. Suggested defaults to seed the list with, based
on standard Gothic II layout:

* `_work/Data/Meshes/_compiled/` (primary - compiled `.MRM`s, searched
  first)
* `_work/Data/Meshes/` (recursive fallback - catches custom/WIP meshes
  not yet compiled, in case an `.MRM` isn't found)

Resolution for a given vob name: walk the configured directories in
order (first configured = highest priority), case-insensitively matching
`<name>.MRM` (fallback `<name>.3ds` if no `.MRM` found anywhere). First
hit wins. No match -> reported, not a hard failure (see error handling).

## The `oCItem:` problem, and a phased answer

Item instance name often isn't the mesh filename. Three tiers, cheapest
first:

1. **Heuristic (default, zero setup):** try `<instance_name>.MRM`
   directly. Works whenever the item's mesh does happen to share its
   instance name (common enough for custom/simple items to be worth
   trying first).
2. **User-maintained lookup table (recommended core solution):** a
   small JSON file, e.g. `item_mesh_map.json` in the repo, mapping
   `ITEM_INSTANCE -> MESH_FILENAME`. Checked *before* the heuristic. The
   tool doesn't need to populate this automatically - it starts empty,
   and you add entries as you discover exceptions while working. Low
   implementation cost, and it only grows the set of items you actually
   use.
3. **Full Daedalus/`GOTHIC.DAT` parsing (stretch goal, not in this
   plan's core):** actually resolving every item's real `MESH=` field
   would need a compiled-script parser (or shelling out to an existing
   decompiler). Meaningfully bigger undertaking than the rest of this
   feature combined - worth revisiting only if the lookup table proves
   too tedious to maintain by hand.

## Operators to build

* `ZEN_OT_load_vob_mesh` - operates on the active/selected vob
  object(s). For each: resolve name -> file path (per the rules above),
  call `bpy.ops.import_scene.krxmrmimp(filepath=...)` (needs testing
  whether this runs cleanly outside its normal file-browser invocation -
  likely needs a context override or `'EXEC_DEFAULT'` context, to be
  confirmed when building this), parent the imported object(s) to the
  vob, move to the preview collection, tag with `zen_is_preview`.
* `ZEN_OT_load_all_vob_meshes` - batch version, scans the whole scene
  for `zCVob:`/`oCItem:` objects without an existing preview, runs the
  above for each, and reports a summary (`N loaded, M not found`) rather
  than failing the whole batch on the first miss.
* `ZEN_OT_clear_vob_previews` - removes every object tagged
  `zen_is_preview`, leaving vob empties untouched. Useful before a clean
  export, or to force a refresh after mesh files change on disk.

## UI additions

* Addon Preferences panel: the new mesh search-path list (mirrors
  KrxImpExp's texture path UI).
* Main tool panel: a "Load Meshes" section with "Load Selected" / "Load
  All" / "Clear Previews" buttons, plus a small "N/M previews loaded"
  status label.

## Error handling

* Missing file: report `{'WARNING'}` (per vob), don't hard-fail a batch
  run. `ZEN_OT_load_all_vob_meshes` should keep going and summarize.
* Ambiguous match (same filename found in two configured search
  directories): use the first configured directory's match and mention
  the shadowing in the report, rather than silently picking one with no
  explanation.
* Already-loaded preview: default to skip (fast re-runs of "Load All"
  after adding a few new vobs); expose a "force reload" option for
  cases where the source mesh changed on disk.

## Suggested build order

1. `zCVob:` only, single-object operator, hardcoded default search
   paths (no preferences UI yet) - smallest possible slice that proves
   the `krxmrmimp` call actually works when driven from a script instead
   of the file browser. This is the real technical risk in the whole
   plan and should be de-risked first.
2. Addon Preferences with the configurable path list; batch operator;
   proper preview-collection/parenting/tagging structure.
3. `oCItem:` support - heuristic first, then the JSON lookup table.
4. Clear-previews operator, status label, polish.
5. (Stretch, separate plan if pursued) `zCVobLevelCompo:` /
   `krxwrdimp`-based whole-world preview; Daedalus-based item mesh
   resolution.

## Open questions for you to decide before/while building

* Where should `item_mesh_map.json` live - in the git repo next to
  `zen_gin_export`, or somewhere per-machine/local so it's not
  version-controlled? (Repo is probably right, since it's exactly the
  kind of knowledge worth sharing across your two machines - same
  reasoning as everything else that ended up in git.)
* Should "Load Meshes" ever run automatically when `zen.add_vob` creates
  a new object, or should it always stay a separate, deliberate step?
  Leaning toward deliberate/separate to start, since auto-importing on
  every add could get slow with many objects and makes failures noisier
  mid-flow - but worth deciding once step 1 above shows how fast/slow a
  single import actually is in practice.
