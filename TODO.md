# TODO

Findings from the code review (2026-11-02). Ordered by priority. Tick items
off as they land; the README stays the only documentation file.

## P1 - Correctness bugs

- [ ] **Export world-space transforms.** `ZCVob.__rotation` reads only
  `rotation_quaternion`, so Euler-mode vobs export with identity rotation
  (waypoint direction already uses `matrix_world`). `__location` /
  `__waypoint_location` use local `location`, wrong for parented objects.
  Use `matrix_world` (translation + `to_quaternion()`); add tests for
  Euler rotation and parented objects.
- [ ] **`FilePrinter` failure handling.** `__del__` writes a partial `.ZEN`
  if `archive.print()` raises, and raises `AttributeError` if `__init__`
  failed. Drop the `__del__` write; use `close()` / a context manager.
  Build output with a list + `join` (currently quadratic `+=`).
- [ ] **Unreachable import error message.** `export_ops.py` imports
  `zen_import` (which imports `zen_gin_export`) at module level, so a missing
  Script Directory breaks addon enable with a raw traceback. Import lazily.
- [ ] **Duplicate / mangled vob names.** `.001` suffix is stripped so
  duplicates export with the same `vobName`; `_vob_name()` also truncates
  names containing `.` or extra `:`. Detect and report duplicates.
- [ ] **Importer drops oCMob* vobs silently** and doesn't restore their
  custom properties; isolated waypoints are never exported. Add oCMob types
  to `_REAL_TYPE_TO_PREFIX`, restore props, count/report skipped blocks.

## P2 - Robustness

- [ ] **Pre-export validation pass:** unknown prefixes, duplicate names, no
  startpoint, no level compo, waypoints without links; report in the export
  message instead of silently ignoring.
- [ ] **Quick export object set:** only export objects from the current
  scene / view layer (skip other scenes, hidden or excluded collections).
- [ ] **Platform-aware paths:** `SPACER_LOG` (`~/Library/Logs`), `/bin/zsh`
  and the default gothic command in `preferences.py` are macOS-specific.
- [ ] **Start the link-draw handler at register time** (currently only
  started when the panel draws or on toggle).
- [ ] **Stop `save_userpref()` side effect:** the mesh-directory buttons
  save all user preferences.
- [ ] **Startup cost:** `register()` scans all mesh directories
  synchronously; make it lazy or on-demand.
- [ ] `archive_verifier`: replace `list.count()` in loop with `Counter`
  (quadratic on large levels).

## P3 - Feature gaps

- [ ] `zCVobSound`: export sound name, volume, radius and mode (currently
  only the base vob block, so the vob does nothing in-game).
- [ ] Lights: verify the calibrated power against Spacer (and `lightStatic`/`lightQuality` baking); handle SUN/AREA explicitly (warn instead of silent POINT),
  make `lightQuality` configurable, decide how energy maps to range/color.
- [x] Importer: reconstruct waypoint facing direction.
- [ ] Verify waypoint `direction` in Spacer/in-game (NPC with `AI_AlignToWP`
  faces the green Y arrow).
- [ ] "Add Level Compo" operator (Export Level Package covers the main path).
- [ ] More VOB types: trigger family, zones, cutscene cameras (see README
  "VOB types").
- [ ] Verify against a real Spacer / in-game round-trip: oCMOB behavior
  (bed, chest, door, switch), `lightType` / `lightQuality` enum ordinals.

## P4 - Cleanup

- [ ] Delete dead preview code in `mesh_preview.py` (keep only what
  `zen_import.py` needs, or move `get_preview_collection` there).
- [ ] Remove dead `build_prop_category_map` / `PROP_FALLBACK_CATEGORY` in
  `mesh_catalog.py`, and the unused `wm.zen_item_catalog`.
- [ ] Fix stale docstrings ("mesh preview") in `item_mesh_map.py`,
  `zen_import.py`, `zen_gin_zcvob.py`, `zen_gin_zcvob_ocitem.py`.
- [ ] Bump `bl_info` version for the removed panels.
- [ ] Decide fate of `asset_catalog/gothic2_meshes.json` (static, superseded).
- [ ] `.gitignore` lists `blender_work_dir/` but ~10 files in it are tracked;
  untrack the ones not needed, or drop the ignore rule.

## Tests / tooling

- [ ] Round-trip test: export -> import -> export, compare output.
- [ ] Tests for `archive_parser`, `WayNet` export, `FilePrinter` failure
  path, and the importer.
- [ ] CI running `pytest` on push.
- [ ] Report the KrxImpExp `.TGA` case-sensitivity bug upstream.

## Pending housekeeping

- [ ] Force-push the filtered history (`git push --force github main`) and
  re-clone on the other machine.
