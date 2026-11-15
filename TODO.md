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

The open items below each have a station in the check level
(`tooling/pipeline/build_check_level.py`, exported as `MOD/BZ_CHECK`).

Everything below round-trips against vanilla data but has not been loaded
in Spacer or played yet.

- [x] Open a 3.0 export in Spacer: static lights now omit the dynamic
  fields (as vanilla does), freepoints write `zbias=1`, floats are written
  without a trailing `.0`.
- [x] Switch -> mover: `oCMobSwitch` (lever and touch plate presets) with a
  `zCMover` target and two keyframes; check direction of travel, speed and
  the sounds.
- [x] `oCTriggerScript` fires its function when the player walks in;
  `oCTriggerChangeLevel` loads the other world.
- [x] Music zone + default music zone play the chosen theme; fog and
  view-distance zones take effect.
- [x] Particle-effect and decal vobs show (FIRE.PFX, ZFLARE6.TGA with Face
  Camera).
- [x] Dynamic light flicker (range/colour lists) and a light preset.
- [x] `zCVobSoundDaytime` switches at the set hours; `zCVobSound` mode,
  radius, volume.
- [x] Fire mob presets light up with their fire tree; lever, winch,
  bookstand, sign presets.
- [x] A torch as a parent vob with flame, light and sound children keeps
  its children in place in Spacer.
- [x] Lights: calibrated viewport power vs. Spacer (2026-11-16, check level).
  Reach and brightness match. On the 1 m test floor the edge of a light
  shows a sawtooth: Gothic lights outdoor geometry per vertex.
- [x] Waypoint `direction`: NPC with `AI_AlignToWP` faces the green Y arrow.
- [x] Spacer loads lockable mobs with real models; `DOOR_NW_NORMAL_01`
  opens in-game; bed (`SLEEPABIT`), lockable chest/door and the alchemy
  table work in-game (2026-11-09).

## P2 - Gaps

- [ ] Cutscene cameras: `zCCSCamera` with `zCCamTrj_KeyFrame` children
  (skipped on import, reported). Also `zCMoverControler`,
  `zCTriggerTeleport`, `zCVobScreenFX`, `zCVobStair`.
- [ ] Ellipsoid sounds (`sndVolType=1`): Spacer stores a hand-set bounding
  box; we write the sphere's.
- [x] Vobs saved with a scaled rotation matrix round-trip; a scaled vob
  with a visual exports its scale (2026-11-11). In-game (2026-11-16) the
  engine does not draw the visual any bigger: scale in the matrix has no
  visible effect, so do not rely on it.
- [x] Dropped-in plants take the vanilla wind / collision defaults in-game
  (2026-11-16, check level).
- [x] Waypoints: `waterDepth` / `underWater` are kept as custom properties
  when set (2026-11-11).
- [ ] Shared visuals: Spacer writes repeated visuals as `§` references; we
  write a fresh visual block per vob. Valid, but larger files.
- [x] Viewport preview: vob empties instance the matching asset-library
  mesh, optionally the game's `.3DS` (2026-11-11). Check it in a real
  viewport.
- [ ] Preview for mob models (`.ASC` / `.MDS`: only compiled `.MDL`/`.MDM`
  in the game files, no importer) and for decals.

## P3 - Features

- [ ] Game bridge: read `.vdf` archives so installs without an unpacked
  `_work/Data` get dropdowns too; item names/descriptions as dropdown hints.
- [ ] "Add Level Compo" operator (Export Level Package covers the main path).
- [x] Draw trigger-target links in the viewport (2026-11-11). Check it in
  a real viewport.

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
