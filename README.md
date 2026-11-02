# Blend-Zen: Blender <-> ZenGin (Gothic II) Toolkit

A Blender addon and Python export/import library for building Gothic II
levels in Blender, instead of placing every VOB and waypoint by hand in
Spacer. Originally a single-script prototype for exporting vob metadata
(by jaxub); now a full addon covering VOB authoring, native lights, export,
and reading an uncompiled ZEN back into Blender.

This README is the single documentation file for the repo.

**Contents:** [Repo layout](#whats-in-this-repo) - [Setup](#setup) -
[Using the addon](#using-the-addon) - [Naming conventions](#scene-naming-conventions) -
[Mesh directories & catalogs](#mesh-directories-and-searchable-name-catalogs) -
[Interactive objects](#interactive-objects-the-ocmob-family) -
[VOB types](#vob-types) - [Blender -> Spacer workflow](#blender---spacer-workflow) -
[End-to-end test plan](#end-to-end-test-plan) - [Architecture](#architecture) -
[Coordinate transform](#coordinate-transform) - [Testing](#testing) -
[Status & roadmap](#status-limitations-and-roadmap) - [Git checklist](#cross-machine-git-checklist)

## What's in this repo

- **`addons/zen_waypoint_tools/`** - the Blender addon (adds a "ZenGin"
  tab to the 3D viewport sidebar), split into focused modules.
- **`modules/zen_gin_export/`** - the underlying export/import library.
  Usable independently of the addon; the parts with no Blender dependency
  (coordinate math, archive parsing/verification) can be tested outside
  Blender entirely.
- **`asset_catalog/`** - `gothic2_meshes.json` is a one-time generated
  snapshot of available Gothic meshes, superseded at runtime by the live
  directory scan in Preferences and kept only as a static reference.
  `item_mesh_map.json` is different: the actively-read, hand-maintained
  instance-name -> mesh-filename lookup the `oCItem` name search depends
  on. `materials_levels.blend` + `blender_assets.cats.txt` are a generated
  Blender material asset library: one material per NewWorld/OldWorld level
  texture (from `GothicBlenderAssets-master/TEXTURES/LEVELS`), each marked
  as an asset and filed into a catalog guessed from its filename
  (Wood/Stone/Wall/Roof/Nature/etc. - see `texture_classify.py`). Regenerate
  with `blender --background --python generate_material_catalog.py` (edit
  `TEXTURE_ROOT` at the top first if your checkout lives elsewhere). To
  browse it, add `asset_catalog/` as an Asset Library in Preferences > File
  Paths > Asset Libraries, then select-all + "Generate Previews" in the
  Asset Browser. Texture images are linked, not packed - use File >
  External Data > Find Missing Files if the path moves. Classification is a
  best-effort heuristic (~5% land in `Misc`); re-file in the Asset Browser
  rather than editing the script.
- **`tests/`** - pytest suite for the Blender-independent parts.
- **`tooling/pipeline/`** - headless helpers: `export_headless.py` (export
  without the UI), `build_compass_test_level.py`, `deploy_and_launch.ps1`.
- **`blender_work_dir/`** - sample/test scenes (`G2ISLAND_WEB`,
  `compass_test_level`, room scenes, reference ZENs) plus
  `select_material_boundary.py`.

### Related project: KIT

The Gothic modular building kit lives in its own repo, `KIT`
(`https://github.com/jaxub96/KIT`). It expects to be checked out as a
sibling of this repo and reads `asset_catalog/materials_levels.blend` and
`blender_work_dir/G2ISLAND_WEB.blend`. Keep those paths stable, or update
KIT's README and `kit_lib.py` if they move.

## Setup

1. Check out this repo somewhere on disk.
2. In Blender: Preferences > File Paths > Script Directories, add this
   repo's root (it has the `addons/` and `modules/` subfolders Blender
   expects).
3. Restart Blender, then enable **Zen Waypoint Tools** in Preferences >
   Add-ons.
4. Also install and enable **KrxImpExp** (needed for mesh import/export).
5. In Preferences > Add-ons > Zen Waypoint Tools, add your Gothic II
   install's mesh directory under **Mesh directories**.

Preferences are per-machine and not stored in git - repeat on each machine.

### KrxImpExp version note

There isn't one canonical KrxImpExp: at least two meaningfully different
versions are in circulation, with different operator names (`krxmrmimp` vs.
GUI-wrapped `krxmrmimpgui`) and different format support (a working raw
`.3ds` importer exists in one, not the other). The addon resolves the
installed module dynamically and calls the plain Python functions each
exposes (`Krx3dsImp`, `KrxMrmImp`) instead of a specific `bpy.ops` name -
see `krximpexp_bridge.py`. If mesh import breaks after updating KrxImpExp,
check that bridge first. The bridge has only been thoroughly tested against
one (rolled-back) build.

## Using the addon

The "ZenGin" sidebar tab has:

- **Waypoint tools** - add (chaining from the active waypoint), link,
  unlink, and toggle the in-viewport link display.
- **Add Other VOBs** - create any supported VOB type at the 3D cursor. For
  `zCVob` props the name field autocompletes against your mesh directories;
  for `oCItem` it autocompletes against item instance names. For the
  interactive `oCMob*` types, selecting the new object shows a properties
  box in the same tab (see [Interactive objects](#interactive-objects-the-ocmob-family)).
- **Export Uncompiled ZEN** - writes the scene out; every export is
  automatically verified for structural correctness (object-index
  contiguity) before reporting success.
- **Export Level Package** - one click produces a ready-to-drop
  `_work/Data/Meshes/Level/<mod>/` + `_work/Data/Worlds/<mod>/` structure
  (mesh + uncompiled ZEN), auto-creating the `zCVobLevelCompo:` reference
  if missing.
- **Import Uncompiled ZEN** - reads an uncompiled ZEN (produced by this
  exporter) back into Blender: vobs, waypoints and links, and best-effort
  loading of the level mesh if found next to the file.

For props and items, you can add an Empty via Add VOB (exported by name and
transform only) or drag real geometry from the Gothic asset libraries
(`Props.blend`, `Items_*.blend`). Empties give a degenerate bounding box; a
vob with mesh geometry parented under it gets a real one.

## Scene naming conventions

Object names encode the VOB type and its data via the prefix before the
first colon. A dot (`.`) and everything after it is ignored, so a duplicate
(`zCVob:NW_CITY_DECO_SWORDFISH_01.001`) exports like the original. Objects
with no matching prefix (e.g. the level mesh) are ignored by the exporter,
so level mesh and vob empties can share a `.blend`.

| Prefix | Object name means... | Notes |
|---|---|---|
| `zCVob:` | Mesh filename, no extension | e.g. `zCVob:NW_CITY_DECO_SWORDFISH_01` uses `NW_CITY_DECO_SWORDFISH_01.3DS`/`.MRM` |
| `oCItem:` | The item's script instance name | e.g. `oCItem:ITMI_BROOM`. Instance name generally differs from the mesh filename - see `item_mesh_map.json` below |
| `zCVobSpot:` | Freepoint name | Used by NPCs during `TA_Stand_*` routines |
| `zCVobStartpoint:` | Player/NPC start position name | Only one per playable world |
| `zCVobLevelCompo:` | World mesh filename, no extension | Reference only - see the Spacer workflow |
| `zCWaypoint:` | Waypoint name | Links edited via the addon's link slots, not by name |
| `zCVobLight:` | Light name | A real Blender Light - edit type/range/cone/color in Blender's Light Properties tab |
| `zCVobSound:` | The sound's script instance name | |
| `oCMobContainer:`, `oCMobDoor:`, `oCMobBed:`, `oCMobSwitch:`, `oCMobLadder:`, `oCMobWheel:`, `oCMobFire:`, `oCMobInter:` | This instance's unique in-game name (`vobName`) | **Not** a mesh name - the model is a separate "Visual Name" property |

The Add VOB dialog builds `Prefix:Name` for you; the table matters if
you rename things by hand or read an existing scene.

## Mesh directories and searchable name catalogs

**Preferences > Add-ons > Zen Waypoint Tools** has a directory list
(`ZenWaypointToolsPreferences` in `preferences.py`): **Add path**,
**Add path with subpaths** (recursively adds every subdirectory - the fast
way to register a whole `_compiled` tree), **Remove path**, **Remove all
paths**.

The Add VOB Name field autocompletes against three window-manager
collections populated by scanning those directories (not a static file):

- `wm.zen_mesh_catalog` - every non-item `.MRM`, for `zCVob:` prop names.
- `wm.zen_item_catalog` - every `.MRM` matching Gothic's `ITxx_...` item
  naming, kept separate so item meshes don't clutter the prop dropdown.
- `wm.zen_item_instance_catalog` - every key in `item_mesh_map.json`, for
  `oCItem:` **instance names** (not mesh names).

Click the refresh icon next to "Add Other VOBs" (`ZEN_OT_refresh_mesh_catalog`,
`mesh_catalog.py`) whenever the directory list or its contents change -
there's no file-watching.

`item_mesh_map.json` is the actively-read source of truth for item
instance -> mesh resolution (see `item_mesh_map.py` for the accepted JSON
shape). It starts empty and grows as you discover mappings; it can't be
derived automatically since it comes from Gothic's compiled Daedalus
scripts. The instance name and mesh filename are genuinely different
namespaces (confirmed in Spacer) - don't confuse them when checking an
item in-game.

## Interactive objects (the oCMOB family)

How to make a chest, door, bed, switch, ladder, wheel or fire source
*behave* in-game, not just export.

### What makes these different from a plain prop

A plain `zCVob` prop's object name doubles as its mesh filename. **oCMOB
objects don't:**

1. The name is the object's unique in-game identity (`vobName`) - what a
   trigger's `triggerTarget` addresses. Five chests need five names.
2. The appearance comes from a **shared, already-animated model** - a
   `.MDS` (ModelScript), e.g. every chest can use
   `CHESTBIG_OCCRATELARGE.MDS`, every human bed `BED_HUM.MDS`. The MDS
   defines the object's states (`s_S0` closed, `s_S1` open) and the
   transition animation (`t_S0_2_S1`).

Same split as `oCItem`, resolved differently: each oCMOB instance has its
own **Visual Name** custom property naming the MDS. Blank = falls back to
the object's own name (only correct for a one-off asset named after
itself).

Blend-Zen can place these objects but **cannot create the animated
model** (that's a 3ds Max + Gothic animation SDK workflow). In practice you
reuse one of the game's existing assets. The addon also can't import
skeletal MDS models, so you won't see the real shape in the viewport - you
place/orient an Empty and trust the Visual Name; double-check its spelling
against a real file.

**Finding an MDS name:** browse `_work\Data\Anims\_compiled\` (or unpacked
`Anims.vdf`) for `<NAME>.MDS` (`BED_HUM`, `CHESTBIG_OCCRATELARGE`,
`DOOR_WOOD_01`, `SWITCH_LEVER_01`, `MINEWHEEL_01`, ...), or open a vanilla
world in Spacer/a decompiler and read an existing object's `visual` field.

### Placing one

1. **Add Other VOBs > Type**, pick e.g. "Interactive: Bed". Give it a
   unique instance name (e.g. `BED_TAVERN_ROOM_01`), not a mesh name.
2. With it selected, the sidebar shows an "oCMobBed properties" box. Set
   **Visual Name** to the real MDS base name, e.g. `BED_HUM`.
3. Fill in other fields as needed (table below); defaults give a plain
   working object.
4. Position/orient the Empty. With no mesh parented the exported bbox is a
   degenerate point, which is fine (cosmetic/LOD only).
5. Export, open in Spacer, compile, test.

### Worked example: a sleepable bed

1. A plain `zCVob:` is never interactive (no state machine). Rename/re-add
   it as `oCMobBed:BED_TAVERN_ROOM_01`.
2. Set **Visual Name** to `BED_HUM` (or another real bed MDS).
3. Leave everything else default - `oCMobBed` adds no fields beyond the
   generic ones, and you do **not** need `trigger_target` for plain
   sleeping.
4. Export, compile, test: the player should be able to use the bed via the
   engine's built-in `oCMobInter` logic plus the MDS's baked animations -
   no Daedalus needed.
5. Getting an *NPC* to sleep there on a schedule is separate: it's the
   NPC's routine script (`Rtn_ExchangeRoutine` / `TA_Sleep`) referencing
   the bed by name.

This is inferred from ZenGin documentation and **not yet confirmed** with a
real Spacer/in-game round-trip; verify with one object before building
several.

### Field reference

Plain custom (ID) properties, editable from the sidebar box or Object
Properties > Custom Properties. Defaults/descriptions live in
`mob_props.py`; mapping to archive properties in `zen_gin_zcvob_ocmob*.py`.

| Field | Applies to | Meaning |
|---|---|---|
| Visual Name | all | Base filename (no extension) of the shared MDS model |
| Focus Name | all | Text shown when the player looks at it |
| Hitpoints / Damage | all | Leave 0 for ordinary furniture |
| Moveable / Takeable | all | Can the player drag / pick it up |
| Sound Material | all | WOOD, STONE, METAL, LEATHER, CLAY, GLAS |
| Owner / Owner Guild | all | Script instance/guild that owns it, for theft detection |
| Trigger Target | all | Vob name to send OnTrigger to when used (e.g. switch -> door) |
| Use With Item | all | Item instance that must be *held* to interact |
| Condition/On-State Function | all | Daedalus function names, for custom scripted behavior |
| State Count | all | Leave 0 unless the MDS defines a different count |
| Rewind | all | Fire the trigger every use, not only the first |
| Locked / Key Item / Picklock Combination | Chest, Door | Key Item opens it; Picklock Combination (e.g. `RRLRL`) enables lockpicking, empty disables |
| Contains | Chest | `ITEM_INSTANCE:count` comma list, e.g. `ITFO_APPLE:3,ITMW_1H_SHORTSWORD1` |
| Fire Slot / Fire Vobtree | Fire | Bone name for the flame, and fire-effect template ZEN (e.g. `FIRETREE_MEDIUM.ZEN`) |

## VOB types

Researched from ZenKit's docs (`zk.gothickit.dev`) and the OpenGothic VOB
reference, cross-checked against `OCVobTree.__create_vob()` and `WayNet`.

### Implemented

| VOB | Definition | In-game application |
|---|---|---|
| `zCVob` | Generic base, used for a plain static mesh instance | World decoration: rocks, furniture, crates, barrels |
| `oCItem` | Pickupable item tied to a Daedalus script instance | Loot hand-placed in the world |
| `zCVobSpot` | Named position/orientation marker, no mesh | NPC routine targets - `TA_Stand`, `TA_Sit`, work spots, guard posts |
| `zCVobStartpoint` | A named spawn transform | Where the player/NPC appears on load |
| `zCVobLevelCompo` | Reference to the level's compiled mesh/BSP | Wrapper vob for the world geometry, needed for a valid archive |
| `zCWaypoint` (+ `WayNet`) | Navigation graph node linked via "ways" | NPC pathing backbone |
| `zCVobLight` | Static/dynamic point/spot light | Torches, lamps, magic glow |
| `zCVobSound` | Ambient sound emitter | Environmental audio (volume/radius/cone fields not yet exported) |
| `oCMobInter` | Generic interactive object | Base for the below; custom "use" props |
| `oCMobContainer` | Lootable container, contents, optional lock | Chests, barrels, sacks |
| `oCMobDoor` | Door with lock, key, picklock difficulty | Doors, gates |
| `oCMobBed` | Sleepable bed | NPC sleep schedules; player resting |
| `oCMobSwitch` | Activatable lever/switch | Puzzle levers, gate releases |
| `oCMobLadder` | Climbable ladder | Vertical connections |
| `oCMobWheel` | Rotating wheel | Winches, waterwheels |
| `oCMobFire` | Usable fire source with NPC seating slots | Campfires |

### Not yet implemented

**Triggers / level logic:** `zCTrigger` (generic relay: pressure plates,
area-entry), `zCTriggerList`, `zCCodeMaster` (multi-switch puzzles),
`zCMover` (drawbridges, elevators) + `zCMoverController`,
`oCTriggerScript` (calls a Daedalus function), `oCTriggerChangeLevel`
(world transitions), `zCTriggerWorldStart`, `zCTriggerUntouch`,
`zCTriggerTeleport`, `zCMessageFilter`, `zCTouchDamage`/`oCTouchDamage`
(lava, traps).

**Zones / atmosphere:** `oCZoneMusic(Default)`, `zCZoneZFog(Default)`,
`zCZoneVobFarPlane(Default)`.

**Cinematics & effects:** `zCCSCamera` (+ `zCCamTrj_KeyFrame`),
`zCPFXController` (particles), `zCVobAnimate`, `zCVobLensFlare`,
`zCEarthquake`, `zCVobScreenFX`.

**Sound variant:** `zCVobSoundDaytime` (separate day/night instances).

**NPC:** `oCNpc` - usually spawned via Daedalus (`Wld_InsertNpc`) and only
a vob in save-game state, so a weak fit for this tool.

Sources: ZenKit docs (`zk.gothickit.dev/engine/objects/` - zCVob, zCTrigger,
oCMOB, oCMobInter, oCMobLockable, oCMobContainer, oCMobBed, oCMobFire),
the OpenGothic wiki "VOBS & Triggers", and the Gothic Modding Community
pages for zCVob, oCMobInter and ModelScript (MDS).

## Blender -> Spacer workflow

### Compiled vs. uncompiled ZEN

* **Compiled ZEN** - game-ready: baked world mesh, BSP tree, lightmaps,
  materials, VOB tree, waynet.
* **Uncompiled ZEN** - everything *except* the baked geometry: VOB tree,
  waynet, and (via `zCVobLevelCompo`) a *reference* to the `.3ds` mesh to
  compile in. No BSP tree; not loadable as a playable world.

`zen_gin_export` only produces the **uncompiled** kind, and that is the
intended handoff format, not a limitation: Spacer's "Compile World" takes
an uncompiled ZEN, resolves the referenced mesh, bakes the geometry, and
**merges it with the VOB tree and waynet already in that file** - nothing
placed in Blender is lost. Nobody outside Piranha Bytes has published a way
to write baked BSP/lightmap data (even ZenKit only writes VOB-tree data),
so compiling always happens in Spacer.

### Manual path to a playable level

1. **Model the level mesh** in Blender (no prefix needed).
2. **Export the mesh to `.3ds`** with KrxImpExp into
   `<Gothic II>\_work\Data\Meshes\...`.
3. In the same `.blend` add a `zCVobLevelCompo:<meshname>` empty (matching
   the `.3ds` name), your `zCWaypoint:` chain, a `zCVobStartpoint:`, and
   any other vobs. (**Export Level Package** automates steps 2-4.)
4. **Export** to an uncompiled ZEN (default `UNCOMPILED_EXPORT.ZEN`) in
   `_work\Data\Worlds\Plugin` or wherever configured.
5. **Spacer -> File -> Open** the uncompiled ZEN directly (not "Import
   mesh" - the file references the mesh via `zCVobLevelCompo`).
6. **World -> Compile World** (Outdoor/Indoor), Editor mode **off**.
7. **World -> Compile Light.**
8. **File -> Save as** a compiled ZEN into `_work\Data\Worlds\`.
9. Point the mod's startup world at it and launch Gothic II.

Limits: triangle limits per Gothic rules (submeshes under ~50k; split and
use Spacer's macro system to join); a vob with no mesh child exports a
degenerate bbox.

Possible future integration: one-click "Add Level Compo Reference"
operator; more VOB types; investigating whether Spacer's compile step
can be scripted from outside its UI (unconfirmed).

## End-to-end test plan

Manual test of the whole pipeline: Blender -> Spacer -> deployed ->
playable. It needs Windows with Gothic II and Spacer, so it can't run in
CI. Prerequisites: Gothic II with Spacer.exe, KrxImpExp and this addon set
up, and a mod/`_work` folder you can overwrite.

**Tiers.** *Smoke* (~10-15 min): phases 1-6 with a trivial scene (one small
mesh, one waypoint pair, one prop, one item, one oCMob). Run after changes
to `zen_gin_export`, `panel.py`, or `viewport_draw.py`. *Full regression*
(~1-2 hrs): every phase, every vob/oCMob type, both placement methods.
Run before a release or after touching coordinate transforms, bbox code or
the archive format. Keep one reusable test-level `.blend`.

1. **Level mesh & materials.** Use materials from
   `asset_catalog/materials_levels.blend` so texture names round-trip via
   KrxImpExp. Check: every face has a Gothic-named material.
2. **VOBs, mobs, items, assets.** Place at least one each of:
   `zCVobStartpoint:`; a `zCVob:` prop via Add VOB and one dragged from
   `Props.blend`; an `oCItem:` via Add VOB and one from `Items_ITMW.blend`;
   a `zCVobSpot:`; a `zCVobLight:` with real type/range/color; every
   `oCMob*` type with a real Visual Name (smoke tier: one, Bed is
   simplest); a `zCVobSound:` if relevant. Check: the oCMob properties box
   shows correct fields per type and values persist after reselecting.
3. **Waynet.** Chain a few `zCWaypoint:`s, link/unlink a pair by hand,
   toggle link display and orbit. Check: lines match the sidebar link
   slots and don't stutter.
4. **Uncompiled export.** Select the level mesh, run **Export Level
   Package**. Check the report says "verified OK" (stop if not) and the
   layout is `<blend dir>\export\_work\Data\Meshes\Level\<mod>\<level>.3DS`
   + `...\Worlds\<mod>\<level>_uncompiled.zen`.
5. **Round-trip import** (optional): in a fresh scene, import the ZEN from
   step 4; check vob/waypoint/link counts match and the mesh status is
   `imported` or a clearly explained `found_not_importable`/`not_found`.
6. **Spacer compile.** Copy `export\_work\...` into the install, open the
   uncompiled ZEN, Compile World (Editor mode off), check the log for
   missing-texture/degenerate warnings, Compile Light, Save As compiled.
   Spot-check vob order in the object list.
7. **Deploy & startup world.** Place the compiled ZEN (and new assets) in
   the real `Data\Worlds\...` (or `_work` override), set `ZSTART=` under
   `[INFO]` in the ini your loader reads (`Gothic.ini`, `SystemPack.ini`,
   `Union.ini`). Back up the ini first.
8. **Launch & verify load.** Correct level loads, no pink missing-texture
   checkerboards, no new errors in the engine log vs. a known-good baseline.
9. **In-game control.** Walk the waynet; interact with every `oCMob*`
   (chest **Contains**, door, bed sleep, switch **Trigger Target**, ladder,
   wheel, fire); pick up the `oCItem:` and check its in-game name matches
   the real instance (not the `item_mesh_map.json` mesh name); check light
   type/range/color/cone; confirm collision on static props.

**Regression checklist:** `OCVobTree` sort order (`zCVobLevelCompo` first,
`oCItem`/`zCVobSpot`/`zCVobSound` grouped, in Spacer's object list); panel
layout after reload (every button fires its operator); viewport link-draw
cache (orbiting is smooth, add/unlink updates lines immediately); Add VOB
vs. asset-drag parity (identical in-game except the dragged asset has real
collision geometry where the empty has a degenerate bbox - expected).

**Streamlining.** Keep one canonical test `.blend`; point the export root at
the real `_work` folder so Export Level Package writes in place; keep a
known-good ini backup; default to the smoke tier.

**Automation.**

| Step | Automatable? | How |
|---|---|---|
| Blender export | Yes | `export_zen_to_path()` (`export_ops.py`) has no UI dependency; run via `blender --background --python`. Confirm KrxImpExp's mesh export doesn't hit a GUI-only path before trusting it headless. |
| Spacer compile | No known way | Closed source, no CLI/scripting; compiled-ZEN writing can't be reimplemented. Community forks may have a batch flag - check. UI automation is fragile. |
| Deploy compiled ZEN + assets | Yes | File copy |
| Set `ZSTART=` | Yes | Targeted line replace (don't round-trip the ini through a generic parser) |
| Launch game | Yes | Process launch |
| Confirm level loaded | Partially | Grep the engine log; filename/patterns vary - best-effort only |
| Play the level | No | That's the actual test |

Starter scripts in `tooling/pipeline/`: `export_headless.py` and
`deploy_and_launch.ps1` (copies assets, patches `ZSTART=`, launches, tails
the log). Both are unverified starting points - fill in the config block,
dry-run the `.ps1` with `-WhatIf`, and refine the log patterns.

## Architecture

Internals of `zen_gin_export`, as a starting point for extensions. More on
the format: https://zk.gothickit.dev/engine/overview/

### Layers

```
ZenArchive                     <- top-level document: header + one oCWorld block
    |-- OCVobTree              <- walks all Blender objects, builds the vob list
    |     |-- ZCVob subclasses <- one class per supported vob type
    |-- WayNet                 <- walks all Blender objects, builds the waynet
ZenGinDataPrinter               <- generic ASCII block/property syntax
Printer (Console/File)          <- where the text actually goes
```

**Layer 1 - `Printer` / `ZenGinDataPrinter`.** `Printer` is a one-method
interface (`print(*content)`) with `ConsolePrinter` and `FilePrinter`.
`ZenGinDataPrinter` knows only the generic ZenGin ASCII syntax -
`[type1 type2 trianglesLimit objectIndex]` ... `[]` blocks and
`name=type:value` properties, with automatic indentation.

**Layer 2 - the `ZCVob` hierarchy** (the layer you'll touch most). `ZCVob`
(`zen_gin_zcvob.py`) does the Blender-to-ZenGin translation: reads
name/location/rotation, converts coordinates and rotation, and writes the
standard vob block (`pack`, `bbox3DWS`, `trafoOSToWSRot`, `trafoOSToWSPos`,
`vobName`, `visual`, `showVisual`, collision flags, ...) plus a nested
`visual` sub-block and an empty `ai` sub-block. Subclasses override:

* `_type_name` - the class name in the block header, e.g.
  `"zCVobStartpoint:zCVob"`.
* `_visual()` - the `visual` property (default `vobName + ".3DS"`; return
  `""` for non-visual vobs).
* `_show_visual`, `_static`, `_collision` - flag overrides.
* `_print_additional_data()` - extra type-specific properties (`OCItem`'s
  `itemInstance`, `ZCVobLight`'s light struct, the oCMOB fields). Call
  `super()` first in multi-level hierarchies (see
  `zen_gin_zcvob_ocmob_inter.py` / `_lockable.py`).

`NoVisualObjectVob` is the intermediate base for vobs with no mesh
(`ZCVobSpot`, `ZCVobStartpoint`, `OCItem`): `_visual_object_type_2 = "%"`,
no separate object index for the visual sub-block.

**Layer 3 - `OCVobTree` / `WayNet`.** Two independent trees, each taking the
whole Blender object list and filtering itself:

* `OCVobTree.__create_vob()` matches name prefixes against a
  `prefix -> class` dict, constructs the class, silently drops anything
  unmatched, sorts, and prints a flat list of children under one implicit
  root (no real nesting despite the name).
* `WayNet` (`zen_gin_waynet.py`) filters `zCWaypoint:` objects and reads
  links from the `zen_waypoint_links` PropertyGroup registered by the
  `zen_waypoint_tools` addon - the one runtime dependency of
  `zen_gin_export` on the addon.

**Layer 4 - `ZenArchive`.** The entry point: builds the header (format
markers, fixed fake date, object count), wraps one `oCWorld:zCWorld` block
around the vob tree + waynet, and closes with an `EndMarker`.

### The object-index thread

Every object block needs a globally unique sequential index, threaded
through all layers as an integer passed in and a new value returned:
`ZCVob.print(object_index)` -> `updated_object_index()` ->
`OCVobTree.print()` accumulates -> `ZenArchive` adds the world object and
the waynet's count. **Easy to get subtly wrong:** if a new subclass emits a
different number of `[type ...]...[]` blocks than `_objects_count` claims,
every later index is off and Spacer/the game may misparse or drop objects.
The per-export verifier checks contiguity against the header count.

### Adding a new VOB type

1. New file; subclass `ZCVob` or `NoVisualObjectVob` (no mesh).
2. Set `_type_name` to the real ZenGin class string: `"YourType:zCVob"` for
   a direct child of `zCVob`, or the full most-derived-first chain, e.g.
   `"oCMobInter:oCMOB:zCVob"` (`oCVob` is NOT part of the persisted chain).
3. Override `_visual()`, `_show_visual`, `_static`, `_collision`.
4. For extra properties, override `_print_additional_data()` and bump
   `_objects_count` if you add sub-blocks.
5. Register the prefix in `OCVobTree.__create_vob()` (and the addon's
   `vob_types.py` for the Add VOB dialog).

For per-instance tunable data (a light's color, an oCMOB's lock state),
read a flat custom (ID) property via `self._custom(key, default)` on the
`ZCVob` base - NOT through `zen_waypoint_tools` PropertyGroups. That keeps
`zen_gin_export` usable from plain Python with a test double (see
`tests/test_ocmob_export.py`); the addon side (`mob_props.py`,
`light_props.py`) only populates defaults and UI descriptions.

### Bounding boxes

`ZCVob.__bounding_box()` walks the vob object's children recursively,
collects `bound_box` corners (world space via `matrix_world`) from every
mesh, and reports the true min/max extent in Gothic space. Every vob is
authored as an Empty, so a real box only appears once a mesh is parented
under it. A vob with no mesh child - and always `zCVobSpot`/
`zCVobStartpoint`, which are visual-less - falls back to a single-point box
(`start == end`).

### Present but not fully solid

* **`FilePrinter` writes on `__del__`**, relying on GC to flush rather than
  an explicit `save()`/`close()` - testing needed a manual `del` and
  `gc.collect()`.
* **No export-time validation** of malformed/duplicate names or
  unmatched prefixes - silently accepted or ignored, with no report to the
  user about what was skipped.
* The archive header hardcodes `date 1.1.1970 12:0:0` (cosmetic `# TODO`).
* `OCVobTree`'s per-type sort ordering was reported not to fully work (an
  `isinstance` check order issue) - doesn't corrupt output; the E2E
  regression checklist verifies the current order in Spacer.
* `zCVobSound` writes only the base vob block - no sound-specific fields.

## Coordinate transform

Blender is right-handed, Z-up. ZenGin is Y-up and **left-handed** relative
to Blender - confirmed empirically 2026-09-16, overturning an earlier
assumption. Both formulas are empirically confirmed in Spacer, not just
derived. In `modules/zen_gin_export/coordinate_transform.py`:

```
Gothic_X = Blender_X * 100
Gothic_Y = Blender_Z * 100
Gothic_Z = Blender_Y * 100      # plain axis swap, no sign flip

Gothic_w =  Blender_w
Gothic_x = -Blender_x
Gothic_y = -Blender_z
Gothic_z = -Blender_y
```

The position map is a pure Y<->Z swap (determinant -1: a handedness flip,
not a rotation). The rotation formula is derived from it: a rotation matrix
conjugates across any orthogonal change of basis as
`M_gothic = R @ M_blender @ R.T`; expanding that for the Y<->Z swap and
converting back to a quaternion gives the formula above (derivation in
`blender_quaternion_to_gothic`'s docstring). Covered by
`tests/test_coordinate_transform.py`. All four call sites route through
these two functions: `ZCVob.__location`/`__rotation` and
`WayNet.__waypoint_location`/`__waypoint_rotation_vec3`.

### How it was verified: the "Compass Cross" test

A freepoint-only export test can't work: an uncompiled ZEN is plain text,
so Spacer just parses back whatever our exporter wrote - there's no
independent check. The fix is a second, independent conversion in the same
compile: KrxImpExp's `.3ds` export applies zero axis conversion, and the
real Blender->Gothic conversion for geometry happens inside Spacer's own
Compile World step - a different code path from `coordinate_transform.py`.

The scene is a plaza with 5 arms of 5 different lengths (3/5/7/9/11 m), one
per direction (+X/-X/+Y/-Y/+Z), with a freepoint at each tip. After
compiling, each freepoint must land on its same-length arm. This settled
the axis-sign question: two freepoints computed with the old formula landed
clearly wrong, in exactly the pattern the fix predicts.

**Rotation** uses the same scene, checked differently: both rotation test
freepoints sit at the plaza center and use our formula either way, so the
arms act as a shared landmark identical in Blender and Spacer - note which
arm each freepoint points at before export and compare after compiling.
Confirmed 2026-09-16: `TEST_ROTATION_PLUS90Z` turns 90 degrees
counterclockwise relative to `TEST_ROTATION_REFERENCE` in both.

Rebuild the scene with `tooling/pipeline/build_compass_test_level.py`
(see its docstring) and re-check in Spacer whenever the formulas change or
in-game positioning looks wrong.

## Testing

Run `pytest` from the repo root (the `mathutils/` fake stub makes the
Blender-free parts testable).

- `tests/test_coordinate_transform.py`, `tests/test_archive_verifier.py` -
  pure Python; guard against the mirror-reflection bug that once shipped
  unnoticed.
- `tests/test_zen_export.py` - the original prototype's end-to-end export.
- `tests/test_zcvob_bounding_box.py` - `bbox3DWS`: degenerate-point
  fallback with no mesh, and a real box from a fake mesh's
  `bound_box`/`matrix_world`.
- `tests/test_ocmob_export.py` - oCMOB field mapping and the
  `oCMobX:oCMOB:zCVob` type-name chains.
- `tests/test_mob_props.py` - `mob_props.py`'s custom-property schema (no
  `bpy` dependency, imported directly).

There is no CI; nothing runs the suite automatically yet.

## Status, limitations and roadmap

**Built and verified:** export of 16 VOB types (above); tested coordinate
transform, including two real bugs found and fixed via Spacer round-trips
(a mirror reflection and a rotation-direction sign); automatic
object-index self-check on every export; ZEN importer (vobs/waynet with
links, inverse transform); native Blender Light <-> `zCVobLight` mapping;
modular addon (waypoint authoring, Add VOB dialog with catalogs and the
oCMOB properties box, Export Level Package, item instance -> mesh map with
869 entries, configurable mesh directories, KrxImpExp bridge, real bounding
boxes); pure-Python test suite.

**Known limitations**

- **No compiled-ZEN writing** - BSP construction and lightmap baking are
  proprietary algorithms; Spacer is required for compiling.
- Import doesn't reconstruct waypoint *facing direction* (position only;
  deliberately deferred) and only searches the ZEN's own directory for the
  level mesh.
- `zCVobLight`'s `lightType`/`lightQuality` enum ordinals are inferred from
  documented names, not confirmed against a real compiled light.
- **oCMOB in-game behavior is unverified** - the property schema and the
  "no scripting needed for basic use" claims come from documentation
  research, not a Spacer/in-game round-trip.
- `item_mesh_map.json` only knows instances added by hand so far.
- **The KrxImpExp Mac/Linux `.TGA` case-sensitivity fix lives outside this
  repo**, in the installed addon's files, and is lost on reinstall/update;
  not yet reported upstream.
- Two-machine git workflow has produced real divergence before (an
  `oCItem` regression via an independent manual edit; a checkout missing a
  module entirely) - see the checklist below.
- The `zCVobLevelCompo` reference has no dedicated button outside Export
  Level Package.
- No true nested vob hierarchies (output is one flat generation), and
  merging Blender vobs into an *existing* Spacer-made ZEN isn't supported -
  only fresh archives are written.

**Potential directions**

- Report the KrxImpExp `.TGA` bug upstream.
- More VOB types (triggers, zones, cutscene cameras) following the oCMOB
  pattern - see [Not yet implemented](#not-yet-implemented).
- Verify the oCMOB family and the light enums against a real Spacer/in-game
  round-trip, with the same rigor as the coordinate-transform fixes.
- CI running pytest; a clearer cross-machine git discipline.

## Cross-machine git checklist

Worked on from two machines under one contributor (`jaxub96-WINDOWS`,
`jeanKoby-MAC`). The remote is named `github` (not `origin`); the sibling
`KIT` repo is separate and uses `origin`, with the same checklist.

**Before starting work**

1. `git status` - deal with leftover uncommitted work first (commit, stash,
   or discard on purpose).
2. `git fetch github`, then `git log HEAD..github/main --oneline` to see
   what's incoming; non-empty means this machine was behind.
3. Pull and read the diff of what came in - especially anything touching
   `addons/` or `modules/`; an unrecognized new file/module is the
   missing-module scenario repeating.

**Before switching away**

4. Commit or stash (`git stash -u` for untracked files) - never leave real
   work uncommitted.
5. `git push` - an unpushed commit is the other machine's next surprise.

**Periodically**

6. `git branch -a` - no stray diverging branches; this repo lives on `main`.
7. If a machine was behind for a while, grep the missed commits for
   anything that changes how you work (a renamed API like
   `zen_waypoint_links` replacing the old `modifiers`-based link storage).
