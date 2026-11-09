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
- [ ] oCMOB behavior (bed, chest, door, switch) and `stateNum=1` default.
- [ ] `zCVobSound` settings (mode, radius, volume) play as expected.
- [ ] Lights: calibrated viewport power vs. Spacer, `lightType` /
  `lightQuality` ordinals, `lightStatic` baking; make `lightQuality`
  configurable.
- [ ] Waypoint `direction`: NPC with `AI_AlignToWP` faces the green Y arrow.
- [ ] Class versions for `oCMobSwitch` / `oCMobWheel` / `oCMobFire` (not in
  the sample worlds; currently `oCMobInter`'s 35585).

## P2 - Features

- [ ] More VOB types: zones (`oCZoneMusic`, `zCZoneZFog`,
  `zCZoneVobFarPlane` - examples in `blender_work_dir/G2ISLAND_WEB.ZEN`),
  the trigger family, cutscene cameras.
- [ ] "Add Level Compo" operator (Export Level Package covers the main path).
- [ ] Import: keep the Spacer vob hierarchy (parenting) instead of
  flattening.

## P3 - Cleanup / tooling

- [ ] Decide whether `asset_catalog/item_mesh_map.json` and
  `gothic2_meshes.json` are still wanted (nothing reads them now).
- [ ] Optional CI job running the addon headless with the `bpy` wheel
  (`tooling/pipeline/check_waypoint_direction.py`).
- [ ] Report the KrxImpExp `.TGA` case-sensitivity bug upstream.

## Pending housekeeping

- [ ] Force-push the filtered history (`git push --force github main`) and
  re-clone on the other machine.
