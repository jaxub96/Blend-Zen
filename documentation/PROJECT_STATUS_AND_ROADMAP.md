# Blend-Zen: Features, Limitations, and Potential Directions

A planning reference for scoping further development. See
ARCHITECTURE.md for internals, WORKFLOW.md for the Spacer pipeline,
ASSET_LIBRARY_HANDOFF.md for the in-progress asset library specifically
(note: as of writing, ASSET_LIBRARY_HANDOFF.md and the asset_library.py
module it describes exist only on the Mac checkout - pull before
working on that feature from this machine).

## Features (built and verified working)

**Export / import library (`zen_gin_export`)**
- Uncompiled ZEN export covering 16 VOB types: `zCVob`, `oCItem`,
  `zCVobSpot`, `zCVobStartpoint`, `zCVobLevelCompo`, `zCWaypoint`,
  `zCVobLight`, `zCVobSound`, and the full oCMOB family - `oCMobInter`,
  `oCMobContainer`, `oCMobDoor`, `oCMobBed`, `oCMobSwitch`,
  `oCMobLadder`, `oCMobWheel`, `oCMobFire` (see VOB_TYPES.md for what
  each is and USAGE_interactive_objects.md for how to make one actually
  work in-game, not just export)
- Correct, tested coordinate transform (position + rotation), including
  two real bugs found and fixed via actual Spacer round-trips: a mirror-
  reflection bug and a separate rotation-direction sign bug
- Automatic structural self-check on every export (object-index
  contiguity vs. header count)
- ZEN importer: reconstructs vobs/waynet (with links) from an existing
  uncompiled ZEN back into Blender, inverse coordinate transform included
- Native Blender Light <-> `zCVobLight` property mapping (type, range,
  cone angle, color) - edit in Blender's own Light Properties tab,
  export reads it directly
- Pure-Python test suite (coordinate transform + archive verification),
  runs with no Blender install

**Blender addon (`zen_waypoint_tools`)**
- Modular package (10+ single-purpose files, not one monolith)
- Waypoint authoring: add/link/unlink/toggle display
- Generic "Add VOB" dialog for all 16 types, with mesh-name search
  autocomplete for props, a *real* (not prototype) item-instance-name
  search dropdown for `oCItem` sourced from `item_mesh_map.json`, and a
  properties box (in the same sidebar tab) for the oCMOB family's
  per-instance fields (locked state, trigger target, contents, the real
  shared model to use, ...)
- Real mesh preview (props and items) via KrxImpExp, locked/non-
  selectable so it can't be accidentally desynced from the real vob data
- Item instance -> mesh filename mapping (869 real entries) - the two
  are genuinely different namespaces, confirmed via a real Spacer test
- Configurable mesh search directories and asset library root
  (Preferences), no hardcoded machine-specific paths
- "Export Level Package": one click produces a ready-to-drop
  `_work/Data/Meshes/Level/<mod>/` + `_work/Data/Worlds/<mod>/`
  structure (mesh + uncompiled ZEN together)
- KrxImpExp version-compatibility bridge - resolves the addon's hash-
  suffixed module name dynamically and calls its plain Python functions
  instead of brittle `bpy.ops` paths, so it survives KrxImpExp being
  reinstalled/updated with a different internal structure
- Asset library builder - transplants real mesh + texture + catalog +
  rendered thumbnail onto marked-as-asset objects for the native Asset
  Browser (in progress, Mac-only checkout currently, see
  ASSET_LIBRARY_HANDOFF.md)
- **Real bounding-box computation from actual object dimensions** -
  `bbox3DWS` is now a true world-space AABB, computed by walking each
  vob's Blender children for mesh geometry (i.e. a loaded "Load Mesh
  Preview" mesh) and transforming its `bound_box` corners into Gothic
  space. A vob with no mesh loaded anywhere in its hierarchy (no
  preview loaded yet, or a genuinely visual-less type like
  `zCVobSpot`/`zCVobStartpoint`) still falls back to the previous
  degenerate single-point box - there is nothing to size against. See
  ARCHITECTURE.md for the mechanism and `tests/test_zcvob_bounding_box.py`
  for coverage.

**Documentation**: README, ARCHITECTURE, WORKFLOW, USAGE_mesh_preview,
PLAN_vob_mesh_preview, VOB_TYPES, USAGE_interactive_objects,
ASSET_LIBRARY_HANDOFF - kept current, not just written once and
abandoned.

## Limitations (known, current)

- **No compiled-ZEN writing.** Confirmed infeasible to reimplement -
  BSP construction and lightmap baking are genuine proprietary
  algorithms, not a data format. Spacer remains required for the
  compile step. (A "graft freshly-exported vobs into an already-
  compiled ZEN, skip recompiling geometry" technique was identified as
  feasible but not built - see Potentials.)
- **Waypoint facing direction isn't reconstructed on import** - only
  position. Deliberately deferred, not a bug.
- `OCVobTree`'s intended per-type sort order doesn't actually work (an
  `isinstance` ordering issue) - harmless to output, just not doing
  what the code appears to intend.
- `zCVobLight`'s `lightType`/`lightQuality` enum ordinals are inferred
  from documented option *names*, not independently confirmed against
  a real compiled, in-game light.
- **The oCMOB family has no mesh preview support** ("Load Mesh Preview"
  only imports static `.MRM` meshes, not the skeletal/animated `.MDS`
  models these types need) **and its in-game behavior is unverified** -
  both the property schema and the "no scripting needed for basic use"
  claims come from ZenGin documentation research, not a real Spacer/
  in-game round-trip yet. See USAGE_interactive_objects.md.
- **Asset library is early**: 1 of 160 items done in one category file;
  ~30+ more Items files plus Mobs/Props categories not started. No
  batch runner across multiple files yet - one file open at a time.
- **The KrxImpExp Mac/Linux `.TGA` case-sensitivity fix lives outside
  this repo**, in the installed addon's own files - will be silently
  lost if KrxImpExp is reinstalled or updated. Not yet reported
  upstream to its author.
- Only thoroughly tested against one specific (rolled-back) KrxImpExp
  build; the bridge is designed for cross-version resilience but hasn't
  been exercised against every version in the wild.
- **Two-machine git workflow has already produced real divergence** -
  the `oCItem` export logic once got reintroduced with a regression via
  a manual edit made independently on the other machine, and (confirmed
  while writing this doc) this Windows checkout is currently missing
  the asset library module entirely. Process risk, not a code bug, but
  worth planning around - e.g. always pulling and reviewing the diff
  before starting work on a machine you haven't used in a while.
- No CI - the test suite exists and passes, but nothing runs it
  automatically on commit/push yet.

## Potentials (not built, worth scoping)

**Near-term, natural continuations**
- Finish the asset library: remaining Items files, then Mobs, then
  Props - the mechanism is proven, this is now a matter of running it
- Multi-file batch runner for the asset library (process every category
  file unattended, rather than one open file at a time)
- Report the KrxImpExp `.TGA` case-sensitivity bug upstream
- A batch "Load All" mesh-preview operator and a "clear all previews"
  button (currently "Load Mesh Preview" only ever operates on the single
  active object) - see `PLAN_vob_mesh_preview.md`'s status banner

**Medium-term feature expansion**
- Support more VOB types: the `zCTrigger` family (movers, script
  triggers, level-change triggers, code masters, ...), zone/music vobs,
  cutscene cameras - each is a bounded, well-understood addition
  following the same pattern as the oCMOB family (see VOB_TYPES.md for
  the full not-yet-implemented list and what each does)
- Verify the oCMOB family against a real Gothic II Spacer/in-game
  round-trip (compile a level with one of each new type and confirm it
  behaves as documented) - same rigor as the coordinate-transform bugs
  already caught this way; USAGE_interactive_objects.md flags this as
  unverified
- The "graft vobs into a pre-compiled ZEN" tool - real time-saver for
  iterating on vob placement without a full Spacer geometry recompile
  each time
- Fix the `OCVobTree` sort-order bug (or deliberately decide ordering
  doesn't matter and document that instead)

**Longer-term / bigger bets**
- Independently verify the `lightType`/`lightQuality` enum ordinals
  against a real compiled, in-game light
- CI setup running the pytest suite automatically
- A clearer cross-machine git discipline (e.g. a pre-work checklist:
  pull, diff review before any manual edits) to prevent repeats of the
  divergence issues already seen twice
