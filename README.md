# Blend-Zen: Blender <-> ZenGin (Gothic II) Toolkit

A Blender addon and Python export/import library for building Gothic II
levels in Blender instead of placing every VOB and waypoint by hand in
Spacer. It covers waypoint and VOB authoring, native lights, sound and
interactive-object settings, export to an uncompiled ZEN, and importing a
ZEN back into Blender.

This README is the single documentation file for the repo (open work is
tracked in `TODO.md`).

**Contents:** [Repo layout](#whats-in-this-repo) - [Setup](#setup) -
[Using the addon](#using-the-addon) - [Naming conventions](#scene-naming-conventions) -
[Interactive objects & sounds](#interactive-objects-and-sounds) -
[VOB types](#vob-types) - [Blender -> Spacer workflow](#blender---spacer-workflow) -
[End-to-end test plan](#end-to-end-test-plan) - [Architecture](#architecture) -
[Coordinate transform](#coordinate-transform) - [Testing](#testing) -
[Status & roadmap](#status-limitations-and-roadmap) - [Git checklist](#cross-machine-git-checklist)

## What's in this repo

- **`addons/zen_waypoint_tools/`** - the Blender addon (a "ZenGin" tab in
  the 3D viewport sidebar).
- **`modules/zen_gin_export/`** - the export/import library. It has no
  dependency on Blender or `mathutils`: it reads plain attributes of the
  objects it's given, so the whole library runs and is tested outside
  Blender.
- **`asset_catalog/`**
  - `materials_levels.blend` + `blender_assets.cats.txt` - a generated
    material asset library: one material per NewWorld/OldWorld level
    texture (from `GothicBlenderAssets-master/TEXTURES/LEVELS`), filed into
    catalogs guessed from the filename (Wood/Stone/Wall/Roof/Nature/...,
    see `texture_classify.py`; ~5% land in `Misc` - re-file those in the
    Asset Browser). Regenerate with
    `blender --background --python generate_material_catalog.py` (edit
    `TEXTURE_ROOT` first). To browse it, add `asset_catalog/` as an Asset
    Library (Preferences > File Paths > Asset Libraries) and Generate
    Previews in the Asset Browser. Textures are linked, not packed (File >
    External Data > Find Missing Files if the path moves).
  - `sky/gothic_sky.hdr` - the Gothic skydome as an HDR panorama, used by
    **Use Gothic Sky Lighting**.
  - `item_mesh_map.json` (item script instance -> mesh filename, 869
    entries) and `gothic2_meshes.json` (a snapshot of the Gothic mesh list)
    - reference data. Nothing in the addon reads them any more.
- **`tests/`** - pytest suite (runs in CI on every push/PR to `main`).
- **`tooling/pipeline/`** - scripts run with Blender or on the game
  machine: `export_headless.py`, `check_waypoint_direction.py`,
  `build_compass_test_level.py`, `build_gothic_sky.py`,
  `deploy_and_launch.ps1`.
- **`blender_work_dir/`** - sample scenes (`G2ISLAND_WEB`,
  `compass_test_level`, room scenes), two real Spacer-saved worlds used as
  format references and test fixtures (`G2ISLAND_WEB.ZEN`,
  `DieGestrandeten.zen`), and `select_material_boundary.py`. The folder is
  in `.gitignore` so scratch files stay out; the tracked files stay tracked.

### Related project: KIT

The Gothic modular building kit lives in its own repo, `KIT`
(`https://github.com/jaxub96/KIT`). It expects to be checked out as a
sibling of this repo and reads `asset_catalog/materials_levels.blend` and
`blender_work_dir/G2ISLAND_WEB.blend`. Keep those paths stable, or update
KIT's README and `kit_lib.py` if they move.

## Setup

1. Check out this repo somewhere on disk.
2. In Blender (5.2+): Preferences > File Paths > Script Directories, add
   this repo's root (it has the `addons/` and `modules/` subfolders Blender
   expects).
3. Restart Blender, then enable **Zen Waypoint Tools** in Preferences >
   Add-ons. If `zen_gin_export` can't be found, the addon still enables and
   the export/import buttons say what's wrong.
4. Install and enable **KrxImpExp** (used for the level mesh `.3DS` export
   and for loading meshes on import).
5. Optional, in Preferences > Add-ons > Zen Waypoint Tools:
   - **Gothic Game Folder** - Export Level Package then writes straight into
     its `_work/Data` instead of `export/` next to the `.blend`.
   - **gothic Command** - the `gothic`/`gothic-wine` launcher used by
     *Open in Spacer*.
   - **Mesh directories** - extra folders the importer searches for the
     level mesh. **Add path with subpaths** adds a whole tree at once.

Preferences are per machine and not stored in git.

### KrxImpExp version note

At least two meaningfully different KrxImpExp versions are in circulation,
with different operator names (`krxmrmimp` vs. GUI-wrapped `krxmrmimpgui`)
and format support. The addon finds the installed module by name prefix and
calls the plain Python functions it exposes (`Krx3dsExp`, `Krx3dsImp`,
`KrxMrmImp`) instead of a specific `bpy.ops` name - see
`krximpexp_bridge.py`. If mesh export/import breaks after updating
KrxImpExp, check that bridge first; it has only been tested against one
build.

## Using the addon

The "ZenGin" sidebar tab has:

- **Waypoint tools** - add (chaining from the active waypoint), link,
  unlink, and toggle the in-viewport link display. Waypoints are csys
  (`ARROWS`) empties: the **green Y arrow is the facing direction** - see
  [Waypoint direction](#waypoint-direction). With a waypoint active, the
  panel shows its three link slots (drag objects in) and everything it is
  connected to.
- **Settings box for the active object** - for `oCMob*` and `zCVobSound`
  vobs, their per-instance settings (see
  [Interactive objects & sounds](#interactive-objects-and-sounds)). Objects
  renamed by hand or made with an older version get an **Add Missing
  Properties** button.
- **Add Other VOBs** - creates a level compo, startpoint, freepoint, light,
  sound or any interactive `oCMob*` type at the 3D cursor. Props (`zCVob`)
  and items (`oCItem`) are not in this dialog: drag real assets in from the
  `Props.blend` / `Items_*.blend` asset libraries (they export with a real
  bounding box), or name an Empty yourself (see the naming table).
- **Use Gothic Sky Lighting** - installs `asset_catalog/sky/gothic_sky.hdr`
  as a Blender studio light and selects it in the viewport (Material
  Preview, Standard view transform). The HDR is Gothic's own skydome
  rendered to a panorama by `tooling/pipeline/build_gothic_sky.py`; the
  gradient colours are sampled from a Spacer screenshot.
- **Export Uncompiled ZEN** - writes the **current scene** (objects in other
  scenes are not exported). Every export is verified for structural
  correctness (object-index contiguity vs. the header count), and the
  report also warns about likely mistakes: unknown type prefixes (typos),
  duplicate names where names must be unique (freepoints, startpoints,
  named mobs), sun/area lights (exported as point lights) and a missing
  `zCVobLevelCompo`. A failed export writes nothing and leaves an existing
  file untouched.
- **Export Level Package** - with the level mesh selected: writes
  `_work/Data/Meshes/Level/<mod>/<level>.3DS` (via KrxImpExp, world space)
  and `_work/Data/Worlds/<mod>/<level>_uncompiled.zen`, creates the
  `zCVobLevelCompo:<level>` reference if missing and leaves other levels'
  compos out of the ZEN. With **Open in Spacer** (needs Gothic Game Folder)
  it then runs `gothic spacernet <mod>/<level>`; the log goes to
  `~/Library/Logs/gothic-spacernet.log` on macOS, the temp folder elsewhere.
- **Import Uncompiled ZEN** - rebuilds vobs (with their light/mob/sound
  settings), waypoints with their facing direction, and links. Also reads
  Spacer-saved worlds: unnamed vobs take their name from `visual`/
  `itemInstance`/`sndName`, unsupported vob types (zones, triggers, ...)
  are skipped and listed in the report, the vob hierarchy is flattened.
  The level mesh is loaded (into a "Zen Level Mesh" collection, parented
  to the level compo and unselectable) if found next to the ZEN, in the
  sibling `_work/Data/Meshes/Level/*/` folders, or in the configured mesh
  directories.

### Waypoint direction

A `zCWaypoint` stores a position and a `direction` vector, and nothing
else. In Blender the `direction` is the empty's local **+Y** axis (green
arrow) in world space - the same forward axis as freepoints and other vobs
(Gothic's local +Z). Export reads it from `matrix_world`, so rotation mode
and parent rotation don't matter. Import rebuilds the rotation from
`direction`, so a round trip keeps it.

**Auto-aim:** linking a waypoint to another turns the first one to face
the second. This applies to Link Selected Waypoints (the active one turns),
Add Waypoint at Cursor (the waypoint it chains from turns to face the new
one, and the new one continues that heading) and dragging an object into a
link slot. Only the heading changes, so waypoints stay level. Each new link
re-aims, so set a hand-picked heading (e.g. a guard post) after linking.
Importing a ZEN doesn't re-aim.

A new unlinked waypoint faces Blender +Y, with X/Y rotation locked so `R`
only turns it around Z (unlock in the N panel if needed). Waypoints from
older files (single-arrow display) are converted by **Show Waypoint
Directions**, which appears in the panel while any remain; it keeps their
orientation.

A waypoint with no links is still exported (in the waynet's `waypointN`
list, like Spacer does). A connection stored on both ends is written once,
and links to waypoints outside the exported scene are skipped.

**What it does in game** (from the Gothic II script API, not yet checked
in-game for this exporter):

- **Not used for pathfinding.** Routes (`AI_GotoWP`, waynet A*) use only
  positions and links.
- **Used when an NPC ends up standing on it:** `AI_AlignToWP` turns the NPC
  to face the direction - this is where guards, idlers and `TA_Stand_*`
  NPCs look while at their routine waypoint.
- **Spawning/teleporting:** NPCs inserted with `Wld_InsertNpc` at a
  waypoint, or moved with `AI_Teleport`, take it as their heading.

So point the green arrow where the NPC should *look* (a guard at a gate
faces outward, a merchant faces across the counter). Transit-only waypoints
along roads don't need care; auto-aim already points them along the path.
Freepoints (`zCVobSpot`) have a full rotation, aligned with `AI_AlignToFP`;
their forward is the same Blender local **+Y**.

## Scene naming conventions

Object names encode the VOB type and its data: `Prefix:Name`. Blender's
duplicate suffix (`.001`, `.002`, ...) is ignored, so a duplicate
(`zCVob:NW_CITY_DECO_SWORDFISH_01.001`) exports like the original; other
dots in the name are kept. Objects with no known prefix (e.g. the level
mesh) are not exported, so level mesh and vobs can share a `.blend`. A
prefix that *looks* like a ZenGin class but isn't supported (e.g. a typo)
is reported in the export message.

| Prefix | Object name means... | Notes |
|---|---|---|
| `zCVob:` | Mesh filename, no extension | e.g. `zCVob:NW_CITY_DECO_SWORDFISH_01` -> visual `NW_CITY_DECO_SWORDFISH_01.3DS` |
| `oCItem:` | The item's script instance name | e.g. `oCItem:ITMI_BROOM`. Not the mesh filename - the game resolves the mesh from the script (confirmed in Spacer) |
| `zCVobSpot:` | Freepoint name | Used by NPC routines (`TA_Stand_*`, work spots). Must be unique |
| `zCVobStartpoint:` | Start position name | One per playable world |
| `zCVobLevelCompo:` | World mesh filename, no extension | Reference to the `.3DS` Spacer compiles in |
| `zCWaypoint:` | Waypoint name | Links are edited via the link slots, not by name. A `.001` suffix is kept in `wpName` (waypoint names must be unique) |
| `zCVobLight:` | Light name | A real Blender Light - edit type/range/cone/color in Blender's Light Properties |
| `zCVobSound:` | The sound's script instance name | Written as `sndName`; volume/mode/radius in the sidebar |
| `oCMobContainer:`, `oCMobDoor:`, `oCMobBed:`, `oCMobSwitch:`, `oCMobLadder:`, `oCMobWheel:`, `oCMobFire:`, `oCMobInter:` | This instance's in-game name (`vobName`) | **Not** a mesh name - the model is the **Visual Name** setting. May be empty (many vanilla mobs are unnamed); otherwise must be unique |

## Interactive objects and sounds

### oCMOB objects

How to make a chest, door, bed, switch, ladder, wheel or fire source
*behave* in-game, not just export.

A plain `zCVob` prop's name doubles as its mesh filename. **oCMOB objects
don't:**

1. The name is the object's in-game identity (`vobName`) - what a
   trigger's `triggerTarget` addresses. Five chests that are triggered need
   five names.
2. The appearance comes from a **shared, already-animated model** - an
   `.MDS` (ModelScript), e.g. every chest can use
   `CHESTBIG_OCCRATELARGE.MDS`, every human bed `BED_HUM.MDS`. The MDS
   defines the states (`s_S0` closed, `s_S1` open) and transition
   animations. Each instance names its MDS in **Visual Name** (blank = the
   object's own name, only right for a one-off asset named after itself).

Blend-Zen can place these objects but **cannot create the animated model**
(that's a 3ds Max + Gothic animation SDK workflow), and can't import
skeletal MDS models, so you place and orient an Empty and trust the Visual
Name - double-check its spelling. To find names, browse
`_work\Data\Anims\_compiled\` (or unpacked `Anims.vdf`) for `<NAME>.MDS`
(`BED_HUM`, `CHESTBIG_OCCRATELARGE`, `DOOR_WOOD_01`, ...), or read an
existing object's `visual` in a vanilla world (Import Uncompiled ZEN works
on `blender_work_dir/G2ISLAND_WEB.ZEN`).

**Placing one:** Add Other VOBs > Type, e.g. "Interactive: Bed", with a
name like `BED_TAVERN_ROOM_01` (not a mesh name). Select it, set **Visual
Name** (e.g. `BED_HUM`) in the sidebar box, adjust other fields if needed,
position it, export, compile in Spacer, test. A plain `zCVob:` is never
interactive. Using the bed needs no Daedalus (engine `oCMobInter` logic +
the MDS's animations); an NPC sleeping there on a schedule is the NPC's
routine script (`TA_Sleep`) referencing it.

This is inferred from ZenGin documentation and vanilla worlds and **not
yet confirmed** with a Spacer/in-game round trip; verify one object before
building several.

### Field reference

Plain custom (ID) properties, edited in the sidebar box (or Object
Properties > Custom Properties). Descriptions live in `mob_props.py`; the
mapping to archive properties in `modules/zen_gin_export/vob_fields.py`
(a test keeps the two in sync).

| Field | Applies to | Meaning |
|---|---|---|
| Visual Name | all mobs | Base filename (no extension) of the shared MDS model |
| Focus Name | all mobs | Text shown when the player looks at it |
| Hitpoints / Damage | all mobs | Leave 0 for ordinary furniture |
| Moveable / Takeable | all mobs | Can the player drag / pick it up |
| Sound Material | all mobs | WOOD, STONE, METAL, LEATHER, CLAY, GLAS |
| Owner / Owner Guild | all mobs | Script instance/guild that owns it, for theft detection |
| Trigger Target | all mobs | Vob name to send OnTrigger to when used (e.g. switch -> door) |
| Use With Item | all mobs | Item instance needed to interact |
| Condition/On-State Function | all mobs | Daedalus function names, for scripted behavior |
| State Num | all mobs | Default 1, as in vanilla worlds (108 of 109 mobs) |
| Rewind | all mobs | Fire the trigger every use, not only the first |
| Locked / Key Instance / Picklock Str | Chest, Door | Key opens it; a picklock combination (e.g. `RRLRL`) enables lockpicking, empty disables |
| Contains | Chest | `ITEM_INSTANCE:count` comma list, e.g. `ITFO_APPLE:3,ITMW_1H_SHORTSWORD1` |
| Fire Slot / Fire Vobtree Name | Fire | Bone name for the flame, and fire-effect template ZEN (e.g. `FIRETREE_MEDIUM.ZEN`) |
| Sound Volume / Mode / Random Delay | Sound | 0-100; LOOP, ONCE or RANDOM; seconds between RANDOM repeats |
| Sound Start On / Ambient 3D | Sound | Playing from the start; ambient 3D sound |
| Sound Radius | Sound | Audible radius in cm (default 1500, as in vanilla) |

## VOB types

Researched from ZenKit's docs (`zk.gothickit.dev`), the OpenGothic VOB
reference, and checked against the two real Spacer-saved worlds in
`blender_work_dir/` (class chains, class versions, field order).

### Implemented

| VOB | Definition | In-game application |
|---|---|---|
| `zCVob` | Generic base, a static mesh instance | Decoration: rocks, furniture, crates, barrels |
| `oCItem` | Pickupable item tied to a Daedalus instance | Loot placed in the world |
| `zCVobSpot` | Named position/orientation marker | NPC routine targets, guard posts |
| `zCVobStartpoint` | Named spawn transform | Where the player appears |
| `zCVobLevelCompo` | Reference to the level mesh | Needed for Spacer to compile the world |
| `zCWaypoint` (+ `zCWayNet`) | Navigation graph node linked by ways | NPC pathing |
| `zCVobLight` | Static/dynamic point/spot light | Torches, lamps |
| `zCVobSound` | Ambient sound emitter (name, volume, mode, radius) | Environmental audio |
| `oCMobInter` | Generic interactive object | Custom "use" objects |
| `oCMobContainer` | Lootable container, contents, optional lock | Chests, barrels |
| `oCMobDoor` | Door with lock, key, picklock | Doors, gates |
| `oCMobBed` | Sleepable bed | Player rest, NPC sleep |
| `oCMobSwitch` | Lever/switch | Puzzles, gate releases |
| `oCMobLadder` | Climbable ladder | Vertical connections |
| `oCMobWheel` | Rotating wheel | Winches |
| `oCMobFire` | Usable fire with NPC slots | Campfires, forges |

### Not yet implemented

**Triggers / level logic:** `zCTrigger`, `zCTriggerList`, `zCCodeMaster`,
`zCMover` (+ `zCMoverController`), `oCTriggerScript`,
`oCTriggerChangeLevel`, `zCTriggerWorldStart`, `zCTriggerUntouch`,
`zCTriggerTeleport`, `zCMessageFilter`, `zCTouchDamage`/`oCTouchDamage`.

**Zones / atmosphere:** `oCZoneMusic(Default)`, `zCZoneZFog(Default)`,
`zCZoneVobFarPlane(Default)` (all three appear in `G2ISLAND_WEB.ZEN`, so
that file is a ready format reference).

**Cinematics & effects:** `zCCSCamera` (+ `zCCamTrj_KeyFrame`),
`zCPFXController`, `zCVobAnimate`, `zCVobLensFlare`, `zCEarthquake`,
`zCVobScreenFX`, decals (`zCDecal` visuals). **Sound variant:**
`zCVobSoundDaytime`. **NPC:** `oCNpc` (spawned by scripts, a weak fit).

## Blender -> Spacer workflow

### Compiled vs. uncompiled ZEN

* **Compiled ZEN** - game-ready: baked world mesh, BSP tree, lightmaps,
  VOB tree, waynet.
* **Uncompiled ZEN** - the VOB tree and waynet plus (via
  `zCVobLevelCompo`) a *reference* to the `.3DS` mesh to compile in.

The exporter only writes the **uncompiled** kind, and that is the intended
handoff: Spacer's "Compile World" resolves the referenced mesh, bakes the
geometry and merges it with the VOB tree and waynet already in the file.
Nobody outside Piranha Bytes has published a way to write baked BSP/
lightmap data, so compiling always happens in Spacer.

### Manual path to a playable level

1. **Model the level mesh** in Blender (no prefix).
2. **Export the mesh to `.3DS`** with KrxImpExp into
   `<Gothic II>\_work\Data\Meshes\...`.
3. Add a `zCVobLevelCompo:<meshname>` (matching the `.3DS` name), your
   waypoints, a `zCVobStartpoint:` and other vobs. (**Export Level
   Package** automates steps 2-4.)
4. **Export** the uncompiled ZEN, e.g. into `_work\Data\Worlds\`.
5. **Spacer -> File -> Open** the uncompiled ZEN (not "Import mesh").
6. **World -> Compile World** (Outdoor/Indoor), Editor mode **off**.
7. **World -> Compile Light.**
8. **File -> Save as** a compiled ZEN into `_work\Data\Worlds\`.
9. Point the mod's startup world at it and launch Gothic II.

Gothic triangle limits apply (keep submeshes under ~50k; split and use
Spacer's macros to join). Whether Spacer's compile step can be scripted is
unknown.

## End-to-end test plan

Manual test of the whole pipeline (Blender -> Spacer -> deployed ->
playable). Needs Windows with Gothic II and Spacer, so it can't run in CI.

**Tiers.** *Smoke* (~10-15 min): phases 1-6 with one small mesh, one
waypoint pair, one prop, one item, one oCMob. Run after changes to
`zen_gin_export` or the panels. *Full regression* (~1-2 hrs): every phase,
every vob type, both placement methods; before a release or after touching
transforms, bounding boxes or the archive format.

1. **Level mesh & materials.** Use materials from
   `asset_catalog/materials_levels.blend` so texture names round-trip.
2. **VOBs.** Place at least one `zCVobStartpoint:`; a `zCVob:` via an Empty
   and one dragged from `Props.blend`; an `oCItem:` both ways; a
   `zCVobSpot:`; a `zCVobLight:` with real type/range/color; each `oCMob*`
   with a real Visual Name (smoke: just a bed); a `zCVobSound:`. Check the
   sidebar box shows the right fields and values persist.
3. **Waynet.** Chain waypoints, link/unlink a pair, leave one unlinked,
   toggle link display and orbit.
4. **Export Level Package** with the level mesh selected. The report must
   say "verified OK"; read any "Check:" warnings.
5. **Round-trip import** (optional): import the ZEN into an empty scene,
   compare counts and settings, re-export.
6. **Spacer compile.** Open the uncompiled ZEN, Compile World (Editor mode
   off), check the log for missing-texture/degenerate warnings, Compile
   Light, Save As compiled. Spot-check the object list.
7. **Deploy & startup world.** Put the compiled ZEN in `Data\Worlds\...`
   (or `_work`), set `ZSTART=` under `[INFO]` in the ini your loader reads.
   Back up the ini first.
8. **Launch.** Correct level loads, no pink textures, no new engine log
   errors.
9. **In-game.** Walk the waynet; use every `oCMob*` (chest contents, door,
   bed, switch trigger target, ladder, wheel, fire); pick up the item and
   check its name; check lights and sounds; confirm prop collision.

**Automation.** `tooling/pipeline/export_headless.py` runs the export
operators via `blender --background`; `deploy_and_launch.ps1` copies
assets, patches `ZSTART=`, launches and tails the log (both unverified
starting points - fill in the config block, dry-run the `.ps1` with
`-WhatIf`). Spacer's compile step and playing the level stay manual.

## Architecture

The library in `modules/zen_gin_export/`. Format background:
https://zk.gothickit.dev/engine/overview/

```
ZenArchive  (zen_gin_zen_archive.py)  header + one oCWorld block
  |-- OCVobTree (zen_gin_ocvobtree.py)  name prefix -> vob class, sorted flat list
  |     |-- ZCVob and simple subtypes   (zen_gin_zcvob.py)
  |     |-- ZCVobLight                  (zen_gin_zcvob_light.py)
  |     |-- ZCVobSound                  (zen_gin_zcvob_sound.py)
  |     |-- OCMobInter and subtypes     (zen_gin_zcvob_ocmob.py)
  |-- WayNet    (zen_gin_waynet.py)     free waypoints + ways
ZenGinDataPrinter (zen_gin_data_printer.py)  [type1 type2 version index] ... [] / name=type:value
Printer / ConsolePrinter / FilePrinter (printer.py)

vob_fields.py           custom property <-> archive field tables (mobs, sound)
coordinate_transform.py Blender <-> Gothic positions/rotations/directions, raw hex
light_conversion.py     Blender light <-> zCVobLight range/color/cone
archive_parser.py       ASCII archive -> block tree (importer, tests)
archive_verifier.py     object-index check run after every export
export_checks.py        pre-export scene warnings
```

**Input objects.** Anything with `name`, `matrix_world` (4x4, indexable as
`m[row][col]`), and optionally `type`, `children`, `bound_box`, `data`,
`get(key, default)` for custom properties, and `zen_waypoint_links` for
waypoints. That is all the library touches, which is why the tests can use
small fakes (`tests/conftest.py`). Transforms come from `matrix_world`, so
rotation mode, parents and object scale are all handled.

**`ZCVob`** writes the base block (`pack`, `bbox3DWS`, `trafoOSToWSRot`,
`trafoOSToWSPos`, `vobName`, `visual`, flags), a `visual` sub-block, an
empty `ai` sub-block, then `_print_additional_data()`. Subclasses set:

* `_type_name` - the class chain as Spacer writes it, most-derived first,
  e.g. `"oCMobDoor:oCMobInter:oCMOB:zCVob"` (abstract bases such as
  `oCMobLockable` and `oCVob` are not part of it).
* `_class_version` - the number after the chain in the block header (e.g.
  52224 for `zCVob`, 64513 for `oCMobContainer`); `_visual_type` /
  `_visual_version` for the visual sub-block.
* `_visual()`, `_printed_vob_name()`, `_static`, `_show_visual`,
  `_collision`, `_print_additional_data()`.

`NoVisualObjectVob` is the base for vobs without a mesh (`[visual % 0 0]`,
one index slot). Per-instance data is read with `self._custom(key,
default)` (flat custom properties, never addon PropertyGroups), keeping the
library addon-independent. For mobs and sounds the fields are tables in
`vob_fields.py`, which the importer also uses in reverse.

**The object-index thread.** Every object block needs a unique sequential
index. Each vob claims `_objects_count` slots (2 with a visual, 1
without), `OCVobTree` and `WayNet` continue the count, and `ZenArchive`
writes the total in the header. A subclass that writes a different number
of indexed blocks than `_objects_count` shifts every later index - the
verifier catches that on every export.

**Adding a VOB type:** subclass `ZCVob` / `NoVisualObjectVob`, set the
chain and version from a real Spacer-saved world if you can find one,
register the prefix in `VOB_CLASSES` (`zen_gin_ocvobtree.py`), and add it
to `vob_types.py` (Add VOB dialog) and `SUPPORTED_TYPES` in
`zen_import.py`. For settings, add a field table to `vob_fields.py` and
matching descriptions to `mob_props.py`.

**Bounding boxes.** The world-space AABB of the object itself if it is a
mesh plus every mesh in its children, converted to Gothic space. With no
mesh (an Empty, a freepoint) it is a single point at the vob.

**Addon side** (`addons/zen_waypoint_tools/`): `waypoint_links.py` (link
slots, auto-aim), `waypoint_ops.py`, `vob_ops.py` / `vob_types.py` (Add VOB),
`mob_props.py` (settings schema), `light_props.py`, `panel.py`,
`viewport_draw.py` (link lines; the connection list is cached and rebuilt
after depsgraph updates, the handlers survive file loads),
`export_ops.py`, `quick_export.py`, `zen_import.py`, `krximpexp_bridge.py`,
`gothic_sky.py`, `preferences.py`. Only the export/import operators and
the light creation need `zen_gin_export`; they import it lazily.

## Coordinate transform

Blender is right-handed, Z-up. ZenGin is Y-up and **left-handed** relative
to Blender (confirmed empirically 2026-09-16). In
`modules/zen_gin_export/coordinate_transform.py`:

```
Gothic_X = Blender_X * 100
Gothic_Y = Blender_Z * 100
Gothic_Z = Blender_Y * 100      # plain axis swap, no sign flip

Gothic_w =  Blender_w
Gothic_x = -Blender_x
Gothic_y = -Blender_z
Gothic_z = -Blender_y
```

The position map is a pure Y<->Z swap R (determinant -1: a handedness
flip, not a rotation). A rotation converts as `M_gothic = R @ M_blender @
R` (R is its own inverse), which is what the exporter does with the world
matrix (`blender_matrix_to_gothic`, scale removed); the quaternion formula
above is the same thing and is what was verified in Spacer - a test checks
the two agree. The rotation is written as 9 little-endian floats in hex
(`trafoOSToWSRot`), row-major. Waypoint `direction` uses the position map
without scale.

### How it was verified: the "Compass Cross" test

An uncompiled ZEN is plain text, so Spacer just parses back what we wrote
- no independent check. The fix is a second, independent conversion in the
same compile: KrxImpExp's `.3ds` export applies no axis conversion, and the
real conversion for geometry happens inside Spacer's Compile World.

The scene is a plaza with 5 arms of 5 lengths (3/5/7/9/11 m), one per
direction (+X/-X/+Y/-Y/+Z), with a freepoint at each tip. After compiling,
each freepoint must land on its same-length arm. Rotation uses the same
scene: two freepoints at the center, compared against the arms in Blender
and Spacer (`TEST_ROTATION_PLUS90Z` turns 90 degrees counterclockwise
relative to `TEST_ROTATION_REFERENCE` in both, confirmed 2026-09-16).
Rebuild the scene with `tooling/pipeline/build_compass_test_level.py` and
re-check in Spacer whenever the formulas change or in-game placement looks
wrong.

## Testing

```bash
pip install pytest
python -m pytest
```

Runs from the repo root without Blender, and in GitHub Actions
(`.github/workflows/tests.yml`, Python 3.10 and 3.13) on pushes and PRs to
`main`. Covers coordinate conversion (incl. the matrix path vs. the
Spacer-verified quaternion formula), full-scene exports through the
verifier, the waynet (free waypoints, dedup, world-space positions),
bounding boxes, class headers and field order against the real Spacer
worlds, light/mob/sound fields and their export -> parse -> custom
property round trip, export warnings, failed-export safety, the addon's
property schema vs. the exporter's tables, and parsing the sample worlds.

In Blender (addon enabled), `tooling/pipeline/check_waypoint_direction.py`
adds waypoints with the real operators, rotates them, exports, checks
`direction`, re-imports and checks the old-style conversion:
`blender --background --python tooling/pipeline/check_waypoint_direction.py`
(or run it from the Text Editor; it cleans up after itself). The addon
also runs headless with the `bpy` package from PyPI (`pip install
bpy==5.2.*` on Python 3.13), registering it via `sys.path` +
`zen_waypoint_tools.register()`.

## Status, limitations and roadmap

**Built and verified:** export of 16 VOB types; coordinate transform
verified in Spacer (two real bugs found and fixed that way); automatic
structural check on every export plus scene warnings; ZEN import of our
own and Spacer-saved worlds (vobs with settings, waynet, level mesh);
native Blender Light <-> `zCVobLight`; Export Level Package; pytest suite
in CI.

**Known limitations**

- **No compiled-ZEN writing** - Spacer is required for compiling.
- **Not yet confirmed in-game:** oCMOB behavior; `zCVobSound` settings;
  `zCVobLight` `lightType`/`lightQuality` ordinals; waypoint `direction`
  with `AI_AlignToWP`. Class versions for `oCMobSwitch`/`oCMobWheel`/
  `oCMobFire` are not in the sample worlds and use `oCMobInter`'s.
- Output is one flat vob list (no nested hierarchies); imports of nested
  Spacer worlds are flattened. Only fresh archives are written - merging
  into an existing Spacer-made ZEN isn't supported.
- A waypoint has three link slots; links are stored on one end, so a node
  can have more than three connections in total, but importing a Spacer
  world where both ends are full drops that link (reported).
- The KrxImpExp Mac/Linux `.TGA` case-sensitivity fix lives in the
  installed addon's files (lost on reinstall) and isn't reported upstream.

**Potential directions:** more VOB types (triggers, zones, cameras) -
`G2ISLAND_WEB.ZEN` has examples of zones; verify the unconfirmed items
above with a Spacer/in-game round trip; report the KrxImpExp `.TGA` bug.

## Cross-machine git checklist

Worked on from two machines under one contributor (`jaxub96-WINDOWS`,
`jeanKoby-MAC`). The remote is named `github` (not `origin`); the sibling
`KIT` repo uses `origin`, with the same checklist.

**Before starting work**

1. `git status` - deal with leftover uncommitted work first.
2. `git fetch github`, then `git log HEAD..github/main --oneline` to see
   what's incoming.
3. Pull and read the diff - especially anything touching `addons/` or
   `modules/`; an unrecognized new or removed module means this machine
   was behind.

**Before switching away**

4. Commit or stash (`git stash -u` for untracked files).
5. `git push`.

**Periodically**

6. `git branch -a` - no stray diverging branches; this repo lives on `main`.
7. After being behind for a while, read the missed commits for anything
   that changes how you work (renamed APIs, removed features).
