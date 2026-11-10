# TODO

Open work, ordered by priority. The README stays the only documentation
file; tick items off (or delete them) as they land.

Done in the 3.0 branch (`feature/vob-coverage-game-bridge`, 2026-11-10):
one table for every vob type (`vob_fields.VOB_SPECS`) surveyed from the
vanilla ASCII worlds; 24 new vob types (zones, triggers, movers, `oCMOB`,
day/night sounds, PFX controller, animate, lens flare, earthquake, touch
damage) plus decal / particle-effect / model visuals on `zCVob`;
per-instance base flags; light presets, quality and flicker; all sound
and mob fields; vob hierarchy on export and import; way links spread over
both ends (no more dropped links); the VOB Settings panel with typed
widgets, relevance rules and an Advanced section; the game-files bridge
(`game_data.GameIndex`) feeding the dropdowns; round-trip check script.

## P1 - Verify in Spacer / in-game

Everything below round-trips against vanilla data but has not been loaded
in Spacer or played yet.

- [ ] Open a 3.0 export in Spacer: static lights now omit the dynamic
  fields (as vanilla does), freepoints write `zbias=1`, floats are written
  without a trailing `.0`.
- [ ] Switch -> mover: `oCMobSwitch` (lever and touch plate presets) with a
  `zCMover` target and two keyframes; check direction of travel, speed and
  the sounds.
- [ ] `oCTriggerScript` fires its function when the player walks in;
  `oCTriggerChangeLevel` loads the other world.
- [ ] Music zone + default music zone play the chosen theme; fog and
  view-distance zones take effect.
- [ ] Particle-effect and decal vobs show (FIRE.PFX, ZFLARE6.TGA with Face
  Camera).
- [ ] Dynamic light flicker (range/colour lists) and a light preset.
- [ ] `zCVobSoundDaytime` switches at the set hours; `zCVobSound` mode,
  radius, volume.
- [ ] Fire mob presets light up with their fire tree; lever, winch,
  bookstand, sign presets.
- [ ] A torch as a parent vob with flame, light and sound children keeps
  its children in place in Spacer.
- [ ] Lights: calibrated viewport power vs. Spacer.
- [ ] Waypoint `direction`: NPC with `AI_AlignToWP` faces the green Y arrow.
- [x] Spacer loads lockable mobs with real models; `DOOR_NW_NORMAL_01`
  opens in-game; bed (`SLEEPABIT`), lockable chest/door and the alchemy
  table work in-game (2026-11-09).

## P2 - Gaps

- [ ] Cutscene cameras: `zCCSCamera` with `zCCamTrj_KeyFrame` children
  (skipped on import, reported). Also `zCMoverControler`,
  `zCTriggerTeleport`, `zCVobScreenFX`, `zCVobStair`.
- [ ] Ellipsoid sounds (`sndVolType=1`): Spacer stores a hand-set bounding
  box; we write the sphere's.
- [ ] Vobs saved with a scaled rotation matrix (5 of 874 props in the
  Xardas part-world) come back unscaled.
- [ ] Waypoints: `waterDepth` / `underWater` always 0 (not imported).
- [ ] Shared visuals: Spacer writes repeated visuals as `§` references; we
  write a fresh visual block per vob. Valid, but larger files.
- [ ] Viewport preview: imported props, decals and mobs are empties; load
  their meshes (KrxImpExp) or link the matching asset-library object.

## P3 - Features

- [ ] Game bridge: read `.vdf` archives so installs without an unpacked
  `_work/Data` get dropdowns too; item names/descriptions as dropdown hints.
- [ ] "Add Level Compo" operator (Export Level Package covers the main path).
- [ ] Draw trigger-target links in the viewport (like waypoint links).

## P4 - Cleanup / tooling

- [ ] Decide whether `asset_catalog/item_mesh_map.json` and
  `gothic2_meshes.json` are still wanted (nothing reads them; the game
  bridge now lists meshes and items live).
- [ ] Optional CI job running the addon headless with the `bpy` wheel
  (`tooling/pipeline/roundtrip_check.py`, `check_waypoint_direction.py`).
- [ ] Report the KrxImpExp `.TGA` case-sensitivity bug upstream.

## Pending housekeeping

- [ ] Force-push the filtered history (`git push --force github main`) and
  re-clone on the other machine.
