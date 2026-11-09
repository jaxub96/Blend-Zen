# TODO

Open work, ordered by priority. The README stays the only documentation
file; tick items off (or delete them) as they land.

Done in the 2026-11-09 review: world-space transforms (`matrix_world`) for
all vobs and waypoints; atomic `FilePrinter` (no partial files, no
`__del__`); lazy `zen_gin_export` imports; duplicate-suffix handling that
keeps other dots; importer support for oCMob*/sound settings, Spacer
`waypointN` entries and skipped-type reporting; isolated waypoints
exported; pre-export scene warnings; scene-only export; platform-aware
Spacer launch; draw handler at register time (persistent across file
loads); no `save_userpref()` side effect; no mesh-directory scan at
startup; `Counter` in the verifier; `zCVobSound` fields; class chains and
versions matched to real Spacer worlds; dead preview/catalog code and the
`mathutils` stub removed; CI.

## P1 - Verify in Spacer / in-game

- [ ] Re-run the smoke tier of the README "End-to-end test plan" after this
  review: class versions and the `oCMobContainer`/`oCMobDoor` chain
  changed (now `oCMobX:oCMobInter:oCMOB:zCVob`, as in vanilla worlds), and
  the `zCModel` visual block version is now 0.
- [x] Spacer loads lockable mobs with real models; `DOOR_NW_NORMAL_01`
  opens in-game (2026-11-09). A missing mob model crashes Spacer - now an
  export warning.
- [ ] Bed with `SLEEPABIT` opens the sleep dialog (`oCMobBed`; vanilla
  mostly saves beds as `oCMobDoor` - try that if `oCMobBed` doesn't work).
- [ ] Each preset in `mob_props.MOB_PRESETS` works in-game; find vanilla
  models for switch, wheel and fire.
- [ ] `zCVobSound` settings (mode, radius, volume) play as expected.
- [ ] Lights: calibrated viewport power vs. Spacer, `lightType` /
  `lightQuality` ordinals, `lightStatic` baking; make `lightQuality`
  configurable.
- [ ] Waypoint `direction`: NPC with `AI_AlignToWP` faces the green Y arrow.
- [ ] Class versions for `oCMobSwitch` / `oCMobWheel` / `oCMobFire` (not in
  the sample worlds; currently `oCMobInter`'s 35585).

## P2 - Gaps found in the reference worlds

Survey of `blender_work_dir/G2ISLAND_WEB.ZEN` + `DieGestrandeten.zen`
(2,952 vobs). Counts are across both files. Import then export of
G2ISLAND_WEB currently loses everything below.

### Unsupported (skipped on import, can't be authored)

- [ ] `oCZoneMusicDefault:oCZoneMusic:zCVob` (2, version 0) - `enabled`,
  `priority`, `ellipsoid`, `reverbLevel`, `volumeLevel`, `loop`.
- [ ] `zCZoneZFogDefault:zCZoneZFog:zCVob` (1, version 5505) -
  `fogRangeCenter`, `innerRangePerc`, `fogColor`, `fadeOutSky`,
  `overrideColor`.
- [ ] `zCZoneVobFarPlaneDefault:zCZoneVobFarPlane:zCVob` (1, version 52224)
  - `vobFarPlaneZ`, `innerRangePerc`.
- [ ] Decal vobs (21): `zCVob` with a `.TGA` visual, `visualCamAlign=1`
  and a `[visual zCDecal 53505 n]` sub-block (`name`, `decalDim`,
  `decalOffset`, `decal2Sided`, `decalAlphaFunc`, `decalTexAniFPS`). We
  always write `<name>.3DS` + `zCProgMeshProto`.
- [ ] Particle-effect vobs (6): `zCVob` with a `.pfx` visual (`FIRE.pfx`,
  `GROUNDFOG1_INDOOR_MID.pfx`, `ORE_GLOW.pfx`) and a
  `[visual zCParticleFX 0 n]` sub-block.
- [ ] Props with non-`.3DS` visuals: a `zCVob:` name always becomes
  `<name>.3DS`, so `.ASC`/`.MDS` static vobs can't be expressed (mobs
  handle this via Visual Name).
- [ ] Vob hierarchy: 49 vobs have children (`childsN>0`). Export writes a
  flat list and import flattens. Parenting could map to Blender parents.
- [ ] Triggers, movers, cameras and `zCVobSoundDaytime` (none in the
  samples; see README "Not yet implemented").

### Partly supported (exported with fixed values, lost on import)

- [ ] **Lights:** all 31 vanilla lights use a preset (`presetName` /
  `lightPresetInUse`, e.g. `FIRESMALL`), 27 flicker (`rangeAniScale`,
  `rangeAniFPS`, `colorAniList` like `(255 139 83) (255 104 53)`,
  `colorAniFPS`). We write no preset and no animation, and
  `lightQuality` is fixed at 2. Sun/area Blender lights become points.
- [ ] **Base vob fields** written as constants: `zbias` is 1 on every
  vanilla freepoint (254) and startpoint, 345 items and 38 props (we
  write 0); `visualAniMode` / `visualAniModeStrength` (wind sway) on 16
  props; `visualCamAlign` on decals; `dynShadow` on 1 prop.
- [ ] **Flags per type, not per instance:** `cdStatic`, `cdDyn`,
  `staticVob`, `showVisual` come from the class. A vanilla prop without
  collision imports and re-exports with collision.
- [ ] **zCVobSound:** `sndRandDelayVar`, `sndObstruction`, `sndConeAngle`,
  `sndVolType` (ellipsoid) are constants; not editable or imported.
- [ ] **oCMOB:** `focusOverride`, `visualDestroyed`, `isDestroyed` are
  constants.
- [ ] **Waypoints:** `waterDepth` / `underWater` always 0 (not imported).
  Waypoints have 3 link slots, so importing a node whose neighbours are
  also full drops the link (reported, none in the samples).
- [ ] **Shared visuals:** Spacer writes repeated visuals as `§` references
  (1,348 blocks); we write a fresh visual block per vob. Valid, but larger
  files - low priority.

## P3 - Features

- [ ] Trigger family and cutscene cameras (zones are listed above).
- [ ] "Add Level Compo" operator (Export Level Package covers the main path).
- [ ] Import: keep the Spacer vob hierarchy (parenting) instead of
  flattening.

## P4 - Cleanup / tooling

- [ ] Decide whether `asset_catalog/item_mesh_map.json` and
  `gothic2_meshes.json` are still wanted (nothing reads them now).
- [ ] Optional CI job running the addon headless with the `bpy` wheel
  (`tooling/pipeline/check_waypoint_direction.py`).
- [ ] Report the KrxImpExp `.TGA` case-sensitivity bug upstream.

## Pending housekeeping

- [ ] Force-push the filtered history (`git push --force github main`) and
  re-clone on the other machine.
