# End-to-End Test Plan: Blender to Playable Gothic Level

A manual (for now - see "Streamlining" and "Automation" below) test
procedure covering the *entire* pipeline this repo is part of: modeling
a level in Blender, placing every vob/mob/item type the addon supports,
exporting, compiling in Spacer, deploying into a real Gothic II install,
and playing it. Nothing here can run in CI (it needs a Windows machine
with Gothic II and Spacer installed) - this is the manual counterpart to
`pytest` for the parts that only exist once Blender, Spacer, and the
game engine are all in the loop together.

Prerequisites: a Gothic II install with Spacer.exe, KrxImpExp and this
addon set up per `README.md`'s Setup section, and a mod/`_work` folder
you're allowed to overwrite freely.

## Test tiers

Running every phase below for every change is overkill. Pick a tier:

- **Smoke test** (~10-15 min): Phases 1-6 with a trivial scene (one
  small mesh, one waypoint pair, one prop, one item, one oCMob type).
  Confirms the pipeline isn't structurally broken. Run this after any
  change to `zen_gin_export`, `panel.py`, or `viewport_draw.py`.
- **Full regression** (~1-2 hrs): every phase, every vob/oCMob type at
  least once, both placement methods (Add VOB and asset-library drag)
  for props/items. Run before a release, or after any change touching
  coordinate transforms, the bounding-box mechanism, or the archive
  format itself.

Keep one reusable test-level `.blend` around rather than rebuilding
from scratch each run (see "Streamlining" below) - most of the value
here is repeatability.

## Phase 1 - Level mesh, materials, textures

1. Model or reuse a small level mesh (a room is enough for a smoke
   test). No object-name prefix needed - the exporter ignores
   unprefixed objects (`WORKFLOW.md`).
2. Assign materials from the generated Gothic material asset library
   (`asset_catalog/materials_levels.blend` - see README's `asset_catalog/`
   section) rather than ad hoc Blender materials, so texture names
   round-trip correctly through KrxImpExp's `.3ds` export.
3. **Check:** every face has a Gothic-named material assigned (no
   default/Blender-default material slots left over - these export as
   missing or wrong textures).

## Phase 2 - VOBs, mobs, items, assets

Place at least one of each, mixing both placement methods so the parity
this session's `test_add_vob_vs_asset_drag_export_parity.py` covers in
isolation also gets a real in-game look:

- `zCVobLevelCompo:` referencing the mesh from Phase 1 (created for you
  automatically by **Export Level Package**, see Phase 4).
- `zCVobStartpoint:` at the intended spawn.
- One `zCVob:` prop **via Add VOB** (legacy path, still valid for
  hand-placed one-offs) and one **dragged from `Props.blend`** (asset
  library - the now-standard path).
- One `oCItem:` **via Add VOB** and one **dragged from
  `Items_ITMW.blend`**.
- One `zCVobSpot:` (freepoint) and one `zCVobLight:` (set a real
  type/range/color in Blender's own Light Properties tab, not just
  defaults).
- One of **every** `oCMob*` type (Container, Door, Bed, Switch, Ladder,
  Wheel, Fire, generic Inter) with a real **Visual Name** pointing at an
  existing `.MDS` in your install's `_work\Data\Anims\_compiled\` - see
  `USAGE_interactive_objects.md`. For the smoke tier, one is enough
  (Bed is the simplest real behavior to verify - sleep needs no script).
- One `zCVobSound:` if your test scene has anything worth giving a
  sound instance name to.

**Check:** the sidebar's oCMob properties box shows the right fields per
type (per the table in `USAGE_interactive_objects.md`), and nothing
silently reverted to a default after reselecting the object.

## Phase 3 - Waynet

1. Add a short chain of `zCWaypoint:` objects (`zen.add_waypoint`,
   chaining from the active waypoint).
2. Link at least one pair by hand with **Link Selected Waypoints** /
   **Unlink Selected Waypoints** to exercise both operators, not just
   the auto-chain.
3. Toggle **Show/Hide Link Display** on and off; orbit the viewport with
   it on.
4. **Check:** the drawn lines match the link slots shown in the sidebar
   for the active waypoint, and orbiting/panning with link display on
   doesn't visibly stutter (this is what `viewport_draw.py`'s connection
   cache exists to keep cheap - see "Regression checklist" below).

## Phase 4 - Uncompiled ZEN export

1. Select the level mesh object(s) and run **Export Level Package**
   (`quick_export.py`) - this also auto-creates the `zCVobLevelCompo:`
   reference if you don't already have one.
2. **Check the operator's report message**: it must say "verified OK".
   If it reports verifier issues, stop here - nothing downstream will
   work correctly.
3. **Check** the output layout matches
   `<blend dir>\export\_work\Data\Meshes\Level\<mod>\<level>.3DS` and
   `...\Worlds\<mod>\<level>_uncompiled.zen`.

## Phase 5 - Round-trip import check (extra regression coverage)

Not part of the "happy path" to a playable level, but cheap and catches
importer/exporter drift early:

1. In a **fresh** scene, **Import Uncompiled ZEN** the file from Phase 4.
2. **Check** the report's vob/waypoint/link counts match what you placed
   in Phases 2-3, and that the level mesh status line says `imported` or
   a clearly-explained `found_not_importable`/`not_found` (see
   `export_ops.py`) - not a silent zero.
3. Discard this scene; it's a verification step, not part of the deploy.

## Phase 6 - Spacer: compile

1. Copy `<blend dir>\export\_work\...` into your actual Gothic II
   install's `_work` folder (or point your `.blend`'s export root at it
   directly - see "Streamlining").
2. **Spacer -> File -> Open**, pick the uncompiled ZEN directly (not
   "Import mesh").
3. **World -> Compile World** (Outdoor/Indoor as appropriate, Editor
   mode **off**).
4. **Check the Spacer log/console** for missing-texture or
   degenerate-geometry warnings.
5. **World -> Compile Light.**
6. **File -> Save As** a compiled ZEN.
7. **Check:** open the compiled ZEN's object list in Spacer and spot-
   check vob order against what Phase 2 placed - this is the one place
   `OCVobTree`'s per-type sort order (fixed this session, see "Regression
   checklist") is externally visible.

## Phase 7 - Deploy + configure startup world

1. Place the compiled ZEN (and any new textures/meshes it references)
   into your install's real `Data\Worlds\...` path (or `_work` override,
   whichever your loader reads - vanilla Gothic reads packed VDFs by
   default, most dev setups use an unpacked `_work` override instead;
   confirm which applies to your install once and keep using it).
2. Point the startup world at your ZEN. The usual lever is the
   `ZSTART=` key under `[INFO]` in whichever ini your loader reads
   (`Gothic.ini`, or a `SystemPack.ini`/`Union.ini` if you're running a
   community patch/loader) - confirm the exact filename for your setup
   once, since it varies by which mod loader is installed.
3. **Check:** the ini edit is the *only* change from your last-known-good
   config - keep a backup so a bad test run is a one-file revert, not a
   reinstall.

## Phase 8 - Launch and verify load

1. Launch `Gothic2.exe` (or your loader's launcher, e.g. SystemPack's).
2. **Check:** the correct level loads (title/loading screen names your
   ZEN), no "missing texture" pink checkerboards, and the engine's log
   file (name/location varies by patch - find it once, e.g.
   `System.log`/`Gothic.log` next to the exe) has no new error lines
   compared to a known-good baseline run.

## Phase 9 - In-game control (manual, the actual point of the exercise)

Everything above is plumbing for this phase - it's the only place a
human genuinely has to play the game to know if it worked:

- Walk the full waynet; if any NPC routine references these waypoints,
  confirm it follows them (waypoint *facing direction* isn't
  reconstructed by the importer, only position - irrelevant here since
  this is a fresh export, not an import round-trip, but worth knowing if
  you're re-testing an imported scene).
- Interact with every placed `oCMob*`: open/close the chest and check
  **Contains** items appear; open the door; sleep in the bed; flip the
  switch and confirm **Trigger Target** fires (if set); climb the
  ladder; turn the wheel; use the fire source.
- Pick up the placed `oCItem:` and check its in-game name/icon matches
  the real instance, not the mesh-preview-only `item_mesh_map.json` name
  (see the warning in `zen_gin_zcvob_ocitem.py` about this exact
  confusion).
- Check the placed light's type/range/color/cone match what was set in
  Blender's Light Properties tab.
- Confirm collision: walk into static props (`cdStatic`/`staticVob`)
  rather than through them.

## Regression checklist (this session's changes)

Run these specifically after pulling this session's commits, in
addition to whichever tier you're doing:

- [ ] **OCVobTree sort fix** (`923a336`): in Spacer's compiled object
  list, confirm `zCVobLevelCompo` sorts first, `oCItem`/`zCVobSpot`/
  `zCVobSound` each land in their own group rather than interleaved with
  plain `zCVob`s - Phase 6 step 7 above.
- [ ] **Panel split** (`5a9ed25`): reload the addon, confirm the ZenGin
  sidebar shows Waypoints always-open, Add VOB and Export/Import
  always-open, and Mesh Preview / Asset Library Tools collapsed by
  default - and that every button under a sub-panel still fires its
  operator correctly (registration order bugs would show up as a
  missing panel or a button that silently does nothing).
- [ ] **Viewport link-draw cache** (`5a9ed25`): with link display on and
  a decent number of waypoints, orbit the viewport - should feel the
  same as with link display off. Then add/unlink a waypoint and confirm
  the drawn lines update immediately (cache invalidation working).
- [ ] **Add VOB vs. asset-drag parity**: place the same prop/item both
  ways (Phase 2), export both, and confirm they behave identically
  in-game except that the asset-dragged one has real collision geometry
  where the Add-VOB one (degenerate bbox, no preview loaded) may not -
  this is the expected, not a bug (see `test_add_vob_vs_asset_drag_export_parity.py`).

## Streamlining the manual parts

1. **Keep one canonical test-level `.blend`**, not a fresh scene per
   run - one small room mesh, one of everything from Phase 2, a short
   waynet. Re-export and re-compile it repeatedly instead of rebuilding;
   the point is pipeline coverage, not new content each time.
2. **Point the `.blend`'s export root at your real Gothic install's
   `_work` folder directly** (save the `.blend` there, or symlink) so
   **Export Level Package** writes straight into place and Phase 7's
   manual copy step disappears entirely for iterative testing.
3. **Keep a known-good ini backup** (Phase 7) so switching the startup
   world back after a test session is a file copy, not manual editing.
4. **Automate everything from "uncompiled ZEN exists" onward that
   doesn't require Spacer's GUI** - deployment, ini editing, launching,
   and a first-pass log check are all plain file/process operations with
   no GUI dependency. See "Automation" below for a starter script that
   does exactly this.
5. **Use the Smoke tier by default**; reserve Full regression for
   before a release or after a change to the coordinate-transform/
   bounding-box/archive-format code specifically (those are the parts
   most likely to break silently and only show up in-game).

## Automation: how far can this actually go?

Investigated for this session; summary below, with a starter script.

| Step | Automatable? | How |
|---|---|---|
| Blender export (Phases 1-5) | **Yes** | `export_zen_to_path()` (`export_ops.py`) is a plain function with no UI/windowing dependency - it only touches `bpy.data.objects` and does file I/O. It can run from `blender.exe --background --python <script>` with no interactive session at all. KrxImpExp's `.3ds`/mesh export functions used by `quick_export.py`/`mesh_preview.py` are the one open question - confirm they don't hit a GUI-only code path before relying on this for the mesh-export leg too (worth a quick manual headless test before trusting it in a script). |
| Spacer compile (World -> Compile World/Light, File -> Save As) | **No known way** - confirmed | Spacer is closed-source with no documented CLI/scripting interface, and this project's own research already concluded compiled-ZEN writing can't be reimplemented independently (`PROJECT_STATUS_AND_ROADMAP.md`'s "No compiled-ZEN writing" limitation). If your specific Spacer build is a community fork, check its own `/?`/readme for a batch-compile flag before assuming none exists - some forks have added one - but nothing in this repo or its research confirms one. Absent that, UI automation (Windows `UIAutomation`/`pywinauto` driving the actual File>Open / World>Compile World / World>Compile Light / File>Save As menu clicks) is the only remaining option, and it's inherently fragile (breaks on Spacer version/dialog changes) - not attempted here without a live Spacer instance to test against. |
| Deploy compiled ZEN + assets into the install | **Yes** | Plain file copy. |
| Set startup world (`ZSTART=`) | **Yes** | Plain text ini edit - a targeted line replace, not a full ini-library round-trip (Gothic's ini format doesn't always survive being reparsed and rewritten by a generic ini library cleanly). |
| Launch the game | **Yes** | Plain process launch. |
| Confirm the right level loaded / no load errors | **Partially** | The engine's log file is plain text and can be tailed/grepped for known error substrings after a timed wait - but the exact log filename/location and error-message strings vary by patch/loader and aren't confirmed for your specific install yet. Treat this as a best-effort smoke signal, not a substitute for Phase 8's manual check, until you've confirmed the log path once. |
| Playing the level (Phase 9) | **No** - and shouldn't be | This is the actual test. Automating input injection into the game process is out of scope and wouldn't validate anything a human glance doesn't already cover better. |

### Starter script

See `tooling/pipeline/`:
- `export_headless.py` - runs inside Blender (`--background --python`)
  to call `export_zen_to_path()` without opening the UI.
- `deploy_and_launch.ps1` - copies the compiled ZEN + assets into the
  install, patches the `ZSTART=` line, launches the game, and does a
  best-effort log tail.

Both are **starting points, not verified end to end** - there's no
Gothic install or Spacer in the environment this was written in to test
against. Fill in the configuration block at the top of each (install
path, ini filename, mod folder, exe name) for your machine, dry-run
`deploy_and_launch.ps1` with `-WhatIf` first, and treat the log-tail
step's error patterns as a first guess to refine once you've seen your
own install's real log output.
