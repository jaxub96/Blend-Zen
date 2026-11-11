# Blend-Zen: Blender <-> ZenGin (Gothic II) Toolkit

A Blender addon and Python export/import library for building Gothic II
levels in Blender instead of placing every VOB and waypoint by hand in
Spacer. It covers waypoints, freepoints, native lights, sounds, interactive
objects, zones (music, fog, view distance), triggers and movers, decals and
particle effects - each with a typed settings panel whose dropdowns are
read from your game files - plus export to an uncompiled ZEN and importing
a ZEN back into Blender.

This README is the single documentation file for the repo (open work is
tracked in `TODO.md`).

**Contents:** [Repo layout](#whats-in-this-repo) - [Setup](#setup) -
[Using the addon](#using-the-addon) - [Naming conventions](#scene-naming-conventions) -
[Game files bridge](#game-files-bridge) - [Interactive objects & sounds](#interactive-objects-and-sounds) -
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
   - **Gothic Game Folder** - the dropdowns in VOB Settings are filled from
     its scripts and assets (see [Game files bridge](#game-files-bridge)),
     and Export Level Package writes straight into its `_work/Data` instead
     of `export/` next to the `.blend`.
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
- **VOB Settings** - appears when the active object is a vob (also for
  props and items dragged in from the asset libraries). Real widgets, not
  raw custom properties: checkboxes, dropdowns for enums, a colour picker,
  and text fields that suggest names from the game files as you type.
  Only what is relevant shows (key and picklock only when Locked, random
  delay only in Random mode, flicker only for dynamic lights, decal
  settings only for a `.TGA` visual). Values that are the same on
  practically every vanilla vob (hitpoints, z-bias, far-clip scale, ...)
  sit in a collapsed **Advanced** section, which says how many of them you
  changed. A setting left at its type's default is not stored on the
  object at all.
- **Add Other VOBs** - **Add ZenGin VOB** creates any of the types in
  [VOB types](#vob-types) at the 3D cursor, set up to work as it is:
  interactive objects start from a vanilla preset, zones and triggers are
  boxes you scale, a mover comes with two keyframes. Props (`zCVob`) and
  items (`oCItem`) are not in this dialog: drag real assets in from the
  `Props.blend` / `Items_*.blend` asset libraries (they carry the right
  name and export with a real bounding box). **Reload Game Data** re-reads
  the game files after you changed scripts.
- **Use Gothic Sky Lighting** - installs `asset_catalog/sky/gothic_sky.hdr`
  as a Blender studio light and selects it in the viewport (Material
  Preview, Standard view transform). The HDR is Gothic's own skydome
  rendered to a panorama by `tooling/pipeline/build_gothic_sky.py`; the
  gradient colours are sampled from a Spacer screenshot.
  The button also adds a preview-only Sun light (`GothicSun_preview`, no ZenGin
  prefix so it is never exported): the HDR alone is a weak light because Gothic's
  outdoor light is mostly the sun. Tune `SUN_STRENGTH` / `SUN_ELEVATION_DEG` in
  `gothic_sky.py`.
- **Export Uncompiled ZEN** - writes the **current scene** (objects in other
  scenes are not exported). Every export is verified for structural
  correctness (object-index contiguity vs. the header count), and the
  report also warns about likely mistakes: unknown type prefixes (typos),
  duplicate names where names must be unique (freepoints, startpoints,
  named mobs, triggers, movers), trigger targets that name no vob, mobs
  without a model, locks nothing can open, beds without `SLEEPABIT`, music
  zones without a theme, movers with a single keyframe, sun/area lights
  (exported as point lights) and a missing `zCVobLevelCompo`. A failed export writes nothing and leaves an existing
  file untouched.
- **Export Level Package** - with the level mesh selected: writes
  `_work/Data/Meshes/Level/<mod>/<level>.3DS` (via KrxImpExp, world space)
  and `_work/Data/Worlds/<mod>/<level>_uncompiled.zen`, creates the
  `zCVobLevelCompo:<level>` reference if missing and leaves other levels'
  compos out of the ZEN. With **Open in Spacer** (needs Gothic Game Folder)
  it then runs `gothic spacernet <mod>/<level>`; the log goes to
  `~/Library/Logs/gothic-spacernet.log` on macOS, the temp folder elsewhere.
- **Import Uncompiled ZEN** - rebuilds vobs with all their settings and
  their parent/child hierarchy, waypoints with their facing direction, and
  links. Also reads Spacer-saved worlds: unnamed vobs take their name from
  `visual`/`itemInstance`/`sndName`; zones and triggers come in as boxes
  matching their bounding box; movers get one child empty per keyframe.
  Unsupported vob types (cutscene cameras) are skipped and listed in the
  report.
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
| `zCVobLight:` | Light name | A real Blender Light - type/range/cone/colour are the light's own; preset, static, quality and flicker in VOB Settings |
| `zCVobSound:`, `zCVobSoundDaytime:` | The vob's name | The sound is the **Sound** setting (blank = the vob's name, how older scenes store it) |
| `oCMobContainer:`, `oCMobDoor:`, `oCMobBed:`, `oCMobSwitch:`, `oCMobLadder:`, `oCMobWheel:`, `oCMobFire:`, `oCMobInter:`, `oCMOB:` | This instance's in-game name (`vobName`) | **Not** a mesh name - the model is the **Visual** setting. May be empty (many vanilla mobs are unnamed); otherwise must be unique |
| `oCZoneMusic:`, `oCZoneMusicDefault:` | `<PLACE>_<THEME>` | The part after the first underscore is the music theme (`CAMP_XAR` plays `XAR_Day_Std`, ...); the **Theme** dropdown sets it |
| triggers, movers, other zones, effects | The vob's name | What `Trigger Target` fields refer to; must be unique |

A `zCVob:` whose **Visual** setting is filled in uses that instead of its
name: `FIRE.PFX` makes it a particle effect, `ZFLARE6.TGA` a decal,
`X.ASC` a static model.

**Hierarchy.** Blender parenting is the vob hierarchy: a vob parented to
another vob is written as its child (a torch with its flame, light and
sound), and comes back parented on import. Objects that are not vobs (the
level mesh, mover keyframes, your own helper empties) can sit in between.

**Boxes.** Zones, triggers and touch-damage vobs are cube empties: move and
scale the cube, it is written as the vob's bounding box (rotation is
locked, the box is axis-aligned in-game). Sounds and lights write the box
of their radius/range.

## Game files bridge

With **Gothic Game Folder** set in the add-on preferences, every field
below has a dropdown button (the arrow next to it): a searchable list of
what actually exists in your game. The field itself is a normal text
field, so any name can still be typed by hand, and everything works
without a game folder:

| Field | Read from (`_work/Data/...`) |
|---|---|
| Sound, Night Sound, mover sounds | `Scripts/System/SFX/*.d` (`C_SFX_DEF` instances) |
| Particle effect visual, PFX trigger effect | `Scripts/System/PFX/*.d` (`C_PARTICLEFX`) |
| Music zone Theme | `Scripts/System/Music/*.d` (`XXX_Day_Std` -> `XXX`) |
| Needs Item, Key, Add Item to Container, item instance | `Scripts/Content/**/*.d` (`C_Item`) |
| Focus Name, Owner, Owner Guild | `MOBNAME_*` constants, `C_Npc` instances, `GIL_*` |
| Script Function (mobs / script triggers) | functions ending in `_S1` / starting with `EVT_` |
| Light Preset (picking one applies range, colour, flicker) | `Presets/LightPresets.zen` |
| Lensflare | `Presets/Lensflare.zen` |
| Visual: meshes, mob models, morph meshes, decal textures | `Meshes/_compiled`, `Anims/_compiled`, `Textures/_compiled` |
| Fire Effect, change-level Level | `Worlds/*.ZEN`, `Worlds/**/*.ZEN` |
| Trigger Target, list targets, code master slaves | the names of the vobs in the current scene |

The Daedalus sources are read (not the compiled `.DAT`), so your mod's own
sounds, items and functions show up as soon as they are written - press
**Reload Game Data** after editing scripts. The index is built on first
use (a few tenths of a second) by
`modules/zen_gin_export/game_data.py`, which has no Blender dependency. A
game folder with only `.vdf` archives and no unpacked `_work/Data` gives
empty lists.

## Interactive objects and sounds

### oCMOB objects

How to make a chest, door, bed, ladder, alchemy table and so on *work*
in-game, not just export.

A plain `zCVob` prop's name doubles as its mesh filename. **oCMOB objects
don't:**

1. The name is the object's in-game identity (`vobName`) - what a
   trigger's `triggerTarget` addresses. It may stay empty (many vanilla
   mobs are unnamed); otherwise it must be unique.
2. The model is a **shared game asset** named in **Visual**: an
   animated `.MDS` (extension optional, e.g. `CHESTBIG_NW_NORMAL_LOCKED`),
   an `.ASC` model (`BEDHIGH_NW_NORMAL_01.ASC`) or a static `.3DS` mesh -
   give the extension for anything but `.MDS`. **The model must exist in
   the game: Spacer crashes loading a mob whose model is missing**
   (`oCMobInter::Reset` access violation). Blend-Zen can't create or
   preview these models; you place an Empty.
3. What happens on use is **script-driven**: the engine calls the
   **Script Function** with `_S1` appended. A bed needs `SLEEPABIT`
   (`SLEEPABIT_S1` opens the sleep dialog), an alchemy table
   `POTIONALCHEMY`, a rune table `MAKERUNE`, a shrine `PrayShrine` (see
   `Story/Dialog_Mobsis/` in the scripts). **Needs Item** is the item
   the player must carry (e.g. `ITMI_FLASK` for alchemy). **Focus Name**
   must be a script text constant such as `MOBNAME_CHEST` (Text.d); plain
   text shows nothing in-game.
4. **Locked** chests and doors need a **Key** and/or a
   **Picklock** (e.g. `RLRRLL`); locked with neither shows "can't be
   opened" in-game.

**Presets.** Add VOB fills in a working vanilla setup for each type
(chest `CHESTBIG_NW_NORMAL_LOCKED`, door `DOOR_NW_NORMAL_01`, bed
`BEDHIGH_NW_NORMAL_01.ASC` + `SLEEPABIT`, ladder `LADDER_3.ASC`, lever
`LEVER_1_OC.MDS`, winch `VWHEEL_1_OC.MDS`, fire bowl `FIREPLACE_HIGH2.ASC`)
and has a **Preset** dropdown; VOB Settings has **Apply Preset** for
existing objects. Presets are copied from vanilla worlds: chests, doors,
beds, ladder, lever, touch plate, winch, three fires (with the fire tree
each uses in vanilla), alchemy table, rune table, Innos shrine, bookstand,
cauldron, stove, campfire pan, tree saw, water pipe, bench, chair,
armchair, sign and gravestone.

**Switch -> mover (a gate, a secret door).** Add a Mover, give it a mesh in
**Visual**, and place its two keyframe empties (closed, open). Add a
Switch and pick the mover's name in **Trigger Target**. That is the setup
of the secret door in Xardas' tower (`TOUCHPLATE_STONE.MDS` ->
`EVT_XARDAS_SECRET_01`).

**Export warnings** catch the silent failures above: a mob without
Visual, a lock nothing can open, a bed without `SLEEPABIT`, and a Trigger
Target that names no vob in the scene.

**Verified in Spacer and in-game (2026-11-09):** doors, lockable chests,
the bed's sleep dialog and the alchemy table. NPC sleeping schedules are
separate (the NPC's `TA_Sleep` routine).

### Settings reference

Every setting is a plain custom (ID) property on the object; VOB Settings
edits it through typed widgets, and a setting at its type's default is not
stored. Labels and tooltips live in `vob_ui_schema.py`; the mapping to
archive properties, the defaults and the per-type flags in
`modules/zen_gin_export/vob_fields.py` (a test keeps the two in sync).
Hover a field for its tooltip. The ones that decide whether something
works:

| Setting | Applies to | Meaning |
|---|---|---|
| Visual | mobs, movers, props | Game model: `NAME` (default extension per type) or `NAME.ASC` / `.3DS` / `.MDS` / `.PFX` / `.TGA`. Must exist |
| Collision / Collide With World | everything with a visual | `cdDyn` / `cdStatic`, per object. Props default to on; turn off for plants you can walk through |
| Wind Sway (+ Strength) | props | `visualAniMode` for plants and trees |
| Focus Name | mobs | Text shown when the player looks at it: a `MOBNAME_*` constant from Text.d (plain text shows nothing) |
| Trigger Target | mobs, triggers | Vob name that is triggered when used (switch -> mover) |
| Needs Item / Script Function | mobs | Item the player must carry; function called as `<name>_S1` on use (bed: `SLEEPABIT`) |
| Locked / Key / Picklock | chest, door | Locked needs a key and/or a combination (e.g. `LRRLR`), or it never opens |
| Contains | chest | `ITEM:count` comma list; the + button adds items from the game's scripts |
| Fire Effect | fire | Vob tree placed at the fire bone when lit (`FIRETREE_MEDIUM.ZEN`) |
| Sound / Volume / Radius / Mode | sound | Instance from `SfxInst.d`; 0-100; cm; Loop, Once or Random (+ delay) |
| Start / End Hour, Night Sound | day/night sound | Sound plays between the hours, Night Sound otherwise |
| Preset / Static / Quality / flicker lists | light | Static lights are baked; dynamic ones can flicker (range and colour lists + FPS) |
| Theme / Priority | music zone | Theme prefix from `MusicInst.d`; the higher priority wins where zones overlap |
| React To Touch / Trigger, Respond To Player / NPCs | triggers | What sets the trigger off (the packed `flags` / `filterFlags` bytes) |
| Script Function | script trigger | Daedalus function that is called |
| Level / Arrive At | change-level trigger | World to load and the startpoint to arrive at |
| Behaviour, Speed, Path, Easing, sounds | mover | How it moves between its keyframes |
| Size, Blending, Opacity | decal | The `zCDecal` visual's settings |

## VOB types

Researched from ZenKit's docs (`zk.gothickit.dev`), the OpenGothic VOB
reference, and checked against the two real Spacer-saved worlds in
`blender_work_dir/` (class chains, class versions, field order).

### Implemented

Class chains, versions, property order and default flags are those of the
ASCII part-worlds shipped with Gothic II (NewWorld, Addon, OldWorld -
about 43,000 vobs, surveyed property by property).

| VOB | What it is for |
|---|---|
| `zCVob` | Static prop; with a `.PFX` visual a particle effect, with a `.TGA` a decal (flares, cobwebs), with `.ASC`/`.MDS` a model |
| `oCItem` | Item lying in the world |
| `zCVobSpot`, `zCVobStartpoint`, `zCVobLevelCompo` | Freepoint, player start, level mesh reference |
| `zCWaypoint` (+ `zCWayNet`) | NPC navigation graph |
| `zCVobLight` | Static or dynamic point/spot light with preset, quality, range and colour flicker |
| `zCVobSound`, `zCVobSoundDaytime` | Ambient sound; day/night sound pair |
| `oCMOB` | Focusable static object: signs, gravestones |
| `oCMobInter`, `oCMobContainer`, `oCMobDoor`, `oCMobBed`, `oCMobSwitch`, `oCMobLadder`, `oCMobWheel`, `oCMobFire` | Interactive objects |
| `oCZoneMusic`, `oCZoneMusicDefault` | Music by area / everywhere else |
| `zCZoneZFog`, `zCZoneZFogDefault` | Fog by area / everywhere else |
| `zCZoneVobFarPlane`, `zCZoneVobFarPlaneDefault` | Vob view distance by area / everywhere else |
| `zCTrigger`, `oCTriggerScript`, `oCTriggerChangeLevel` | Trigger another vob / call a script function / load another world |
| `zCTriggerList`, `zCMessageFilter`, `zCCodeMaster`, `zCTriggerWorldStart`, `zCTriggerUntouch` | Trigger logic: fan-out with delays, message conversion, combinations, on world load, on leaving |
| `zCMover` | Mesh moving between keyframes: gates, secret doors, lifts |
| `oCTouchDamage` | Box that hurts on touch |
| `zCPFXControler`, `zCVobAnimate`, `zCVobLensFlare`, `zCEarthquake` | Triggered particle effect, morph-mesh animation, lens flare, screen shake |

### Not yet implemented

`zCCSCamera` (+ `zCCamTrj_KeyFrame`) cutscene cameras, `zCMoverControler`,
`zCTriggerTeleport`, `zCVobScreenFX`, `zCVobStair`, `oCNpc` (spawned by
scripts, a weak fit). Unsupported types are skipped on import and listed
in the report.

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
   with a real Visual (smoke: just a bed); a `zCVobSound:`; a music zone;
   a switch with a mover as its Trigger Target; a script trigger. Check
   VOB Settings shows the right fields and values persist.
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
   check its name; check lights (static and flickering) and sounds; confirm
   prop collision; pull the switch and watch the mover; walk into the
   script trigger and the music/fog zones.

**Feature test level.** `tooling/pipeline/build_feature_test_level.py`
builds a level with one station per item of `TODO.md` "Verify in Spacer /
in-game" (switch -> mover, triggers, zones, lights, effects, sounds, mobs,
props, items), each with a sign whose focus name says what to do, saves it
as a `.blend` and can run Export Level Package in the same step. With a
level name it also writes the signs' `MOBNAME_FT_*` texts into the game's
`Story/Text.d` (between marker comments; rebuild the scripts afterwards):

```bash
blender --background --python tooling/pipeline/build_feature_test_level.py -- blender_work_dir/feature_test_level.blend FEATURE_TEST MOD
```

The station list is in the script's docstring.

**Round-trip check.** `tooling/pipeline/roundtrip_check.py` imports a
ZEN, exports it again and compares every property of every vob and
waypoint with the original:

```bash
blender --background --factory-startup --python tooling/pipeline/roundtrip_check.py -- path/to/world.zen
```

On the vob list of `NewWorld_Part_Xardas_01` (1,430 vobs, 152 waypoints,
161 ways) it reports no differences beyond the by-design ones listed at
the top of the script.

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
  |-- OCVobTree (zen_gin_ocvobtree.py)  name prefix -> vob class; Blender parenting -> vob hierarchy
  |     |-- ZCVob                       (zen_gin_zcvob.py)   the writer for every vob type
  |     |-- ZCVobLight                  (zen_gin_zcvob_light.py)  reads the Blender light
  |-- WayNet    (zen_gin_waynet.py)     free waypoints + ways; orient_ways() for the importer
ZenGinDataPrinter (zen_gin_data_printer.py)  [type1 type2 version index] ... [] / name=type:value
Printer / ConsolePrinter / FilePrinter (printer.py)

vob_fields.py           THE table: every vob type (chain, version, flags, visual, volume) and its fields
game_data.py            GameIndex: names read from a game folder's scripts, presets and assets
coordinate_transform.py Blender <-> Gothic positions/rotations/directions, raw hex, mover keyframes
light_conversion.py     Blender light <-> zCVobLight range/color/cone
archive_parser.py       ASCII archive -> block tree (importer, tests)
archive_verifier.py     object-index check run after every export
export_checks.py        pre-export scene warnings
```

**Input objects.** Anything with `name`, `matrix_world` (4x4, indexable as
`m[row][col]`), and optionally `type`, `parent`, `children`, `bound_box`,
`empty_display_size`, `data`, `get(key, default)` for custom properties,
and `zen_waypoint_links` for waypoints. That is all the library touches,
which is why the tests can use small fakes (`tests/conftest.py`).
Transforms come from `matrix_world`, so rotation mode, parents and object
scale are all handled.

**One table, one writer.** `vob_fields.VOB_SPECS` has a `VobSpec` per vob
type: the class chain as Spacer writes it (most-derived first, e.g.
`oCMobDoor:oCMobInter:oCMOB:zCVob`; abstract bases such as `oCMobLockable`
are not part of it), the class version, where the visual comes from, what
volume the bounding box describes, the type's default base flags, and its
fields as `(archive name, archive type, custom key, default)`. `ZCVob`
writes any of them: the base block (`pack`, `presetName`, `bbox3DWS`,
`trafoOSToWSRot/Pos`, `vobName`, `visual`, then the per-instance flags), a
`visual` sub-block chosen by the visual's extension (`zCProgMeshProto`,
`zCModel`, `zCMorphMesh`, `zCParticleFX`, `zCDecal` with its settings, or
`[visual % 0 0]`), an empty `ai` sub-block, then the type's fields. A few
archive types are composite: the packed trigger `flags`/`filterFlags`
bytes, counted lists (trigger list targets, code master slaves) and mover
keyframes. The importer runs the same table in reverse
(`custom_properties_from_block`), and the addon builds its settings
widgets from it. Only `ZCVobLight` has code of its own (it reads the
Blender light).

Per-instance data is read with `self._custom(key, default)` (flat custom
properties, never addon PropertyGroups), keeping the library
addon-independent.

**The object-index thread.** Every object block needs a unique sequential
index. Each vob claims `_objects_count` slots (2 with a real visual block,
1 without), `OCVobTree` and `WayNet` continue the count, and `ZenArchive`
writes the total in the header. The verifier checks it on every export.

**Vob hierarchy.** The `VobTree` block is a flat pre-order list:
`childsN=int:count` after node N-1 says how many of the following vobs are
its children (node 0 is the implicit root). `OCVobTree` builds it from
Blender parenting (nearest exported vob ancestor), siblings grouped by
type.

**Adding a VOB type:** add a `VobSpec` (and a field tuple) to
`vob_fields.py` with the chain, version and property order from a real
world, then its labels/tooltips to `FIELD_UI` and a menu entry to
`VOB_TYPE_INFO` in `vob_ui_schema.py`. Exporter, importer, sidebar and Add
VOB pick it up; the tests fail until the UI entries exist.

**Bounding boxes.** Zones and triggers: the object's own cube. Sounds and
lights: a cube of the radius/range around the vob. Otherwise the
world-space AABB of the object itself if it is a mesh plus the meshes
among its children (not those of child vobs), converted to Gothic space;
with no mesh (an Empty, a freepoint) a single point at the vob.

**Addon side** (`addons/zen_waypoint_tools/`): `waypoint_links.py` (link
slots, auto-aim), `waypoint_ops.py`, `vob_ops.py` / `vob_types.py` (Add VOB),
`vob_ui_schema.py` (labels, tooltips, visibility rules, dropdown sources -
pure data), `vob_ui.py` (the VOB Settings panel: `Object.zen_vob`, a
PropertyGroup generated from `vob_fields` whose properties read and write
the flat custom properties through get/set callbacks, so nothing is stored
twice), `game_bridge.py` (cached `GameIndex` for the preferences' game
folder, search callbacks), `mob_props.py` (presets), `light_props.py`,
`panel.py`,
`viewport_draw.py` (link lines; the connection list is cached and rebuilt
after depsgraph updates, the handlers survive file loads),
`export_ops.py`, `quick_export.py`, `zen_import.py`, `krximpexp_bridge.py`,
`gothic_sky.py`, `preferences.py`. `zen_gin_export` is imported lazily:
without it the addon still enables, VOB Settings stays hidden and the
export/import buttons say what is missing.

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
bounding boxes and volumes, class headers and field order against the
vanilla worlds, every vob type's settings through an export -> parse ->
custom property round trip, trigger flag bytes, list slots, mover
keyframes (against the reference world's secret door), decals, the vob
hierarchy, way-link orientation, export warnings, failed-export safety,
the game-files reader on a miniature game folder, the UI schema vs. the
exporter's tables, and parsing the sample worlds.

In Blender (addon enabled), `tooling/pipeline/check_waypoint_direction.py`
adds waypoints with the real operators, rotates them, exports, checks
`direction`, re-imports and checks the old-style conversion:
`blender --background --python tooling/pipeline/check_waypoint_direction.py`
(or run it from the Text Editor; it cleans up after itself). The addon
also runs headless with the `bpy` package from PyPI (`pip install
bpy==5.2.*` on Python 3.13), registering it via `sys.path` +
`zen_waypoint_tools.register()`.

## Status, limitations and roadmap

**Built and verified:** export and import of 40 VOB types with
per-instance settings and the vob hierarchy; a round trip of a vanilla
part-world (`NewWorld_Part_Xardas_01`) with no property differences;
coordinate transform verified in Spacer (two real bugs found and fixed
that way); automatic structural check on every export plus scene
warnings; settings panel with dropdowns read from the game files; native
Blender Light <-> `zCVobLight`; Export Level Package; pytest suite in CI.

**Known limitations**

- **No compiled-ZEN writing** - Spacer is required for compiling.
- **Verified by round trip against vanilla data, not yet in Spacer /
  in-game:** everything added with the 3.0 table (zones, triggers, movers,
  decals, particle effects, day/night sounds, light presets and flicker,
  per-instance flags, hierarchy). Verified in-game earlier: doors, chests,
  the bed, the alchemy table. See `TODO.md` for the checklist.
- Cutscene cameras are not supported (skipped on import, reported).
- Zones and triggers are re-centred on their box on import (only the box
  matters in-game); ellipsoid sounds get the sphere's bounding box; the
  few vobs Spacer saved with a scaled matrix come back unscaled.
- Repeated visuals are written out per vob rather than as Spacer's `§`
  references: valid, but larger files.
- Only fresh archives are written - merging into an existing Spacer-made
  ZEN isn't supported.
- The KrxImpExp Mac/Linux `.TGA` case-sensitivity fix lives in the
  installed addon's files (lost on reinstall) and isn't reported upstream.

**Potential directions:** cutscene cameras; previewing vob visuals in the
viewport (meshes for props placed as empties, decal quads); verify the
unconfirmed items above with a Spacer/in-game round trip.

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
