# Blend-Zen: Blender <-> ZenGin (Gothic II) Toolkit

# Perganum
A Blender addon and Python export/import library for building Gothic II
levels in Blender, instead of placing every VOB and waypoint by hand in
Spacer. Originally a single-script prototype for exporting vob metadata;
now a full addon covering VOB authoring, mesh preview, native lights,
export, and reading an uncompiled ZEN back into Blender.

See `documentation/WORKFLOW.md` for the full Blender -> Spacer ->
compiled-ZEN -> in-game pipeline this fits into, and *why* an "uncompiled"
ZEN is the right handoff format rather than a limitation to work around.

## What's in this repo

- **`addons/zen_waypoint_tools/`** - the Blender addon (adds a "ZenGin"
  tab to the 3D viewport sidebar). Split into focused modules - see
  `documentation/ARCHITECTURE.md` if you're extending it.
- **`modules/zen_gin_export/`** - the underlying export/import library.
  Usable independently of the addon, and the parts with no Blender
  dependency (coordinate math, archive parsing/verification) can even be
  tested outside Blender entirely (see Testing, below).
- **`documentation/`** - deeper docs:
  - `ARCHITECTURE.md` - internals, the object-index bookkeeping, and how
    to add a new VOB type.
  - `WORKFLOW.md` - the Blender -> Spacer -> Gothic pipeline and the
    compiled/uncompiled ZEN distinction.
  - `USAGE_mesh_preview.md` - the mesh browsing/preview workflow.
  - `PLAN_vob_mesh_preview.md` - feature plan for mesh preview; partially
    implemented (level-compo and prop mesh loading both work now; item
    mesh resolution is still open, see Known Issues).
- **`asset_catalog/`** - a generated snapshot of available Gothic meshes.
  Superseded at runtime by the live directory scan in Preferences; kept
  as a static reference.
- **`tests/`** - pytest suite for the Blender-independent parts of
  `zen_gin_export`.
- **`exports/`** - real sample `.blend`/`.ZEN` files generated during
  development testing, kept here (not deleted) so they can be reviewed
  or reused.

## Setup

1. Check out this repo somewhere on disk.
2. In Blender: Preferences > File Paths > Script Directories, add this
   repo's root (it already has the `addons/` and `modules/` subfolders
   Blender expects).
3. Restart Blender, then enable **Zen Waypoint Tools** in
   Preferences > Add-ons.
4. Also install and enable **KrxImpExp** (needed for mesh import/export -
   see the version note below).
5. In Preferences > Add-ons > Zen Waypoint Tools, add your Gothic II
   install's mesh directory under **Mesh directories** - this drives the
   mesh-name search when adding props and the "Load Mesh Preview" button.

Since preferences (mesh directories, KrxImpExp setup) are per-machine and
not stored in git, this step needs repeating on each machine you work
from.

## Using the addon

The "ZenGin" sidebar tab has:

- **Waypoint tools** - add/link/unlink waypoints, toggle the in-viewport
  link display.
- **Add Other VOBs** - create any supported VOB type at the 3D cursor.
  For `zCVob` props, the name field autocompletes against your
  configured mesh directories.
- **Load Mesh Preview** - imports the real Gothic mesh for the active
  prop and parents it as a (locked, non-selectable) preview, so you can
  see what a level looks like before ever opening Spacer.
- **Export Uncompiled ZEN** - writes the scene out. Every export is
  automatically checked for structural correctness (object-index
  contiguity) before reporting success.
- **Import Uncompiled ZEN** - reads an existing uncompiled ZEN (produced
  by this exporter) back into Blender, reconstructing vobs, waypoints and
  their links, and best-effort loading the level mesh if one is
  referenced and found next to the file.

## Scene naming conventions

Object names encode both the VOB type and its data, using the prefix
before the first colon. A dot (`.`) and everything after it is ignored,
so duplicating an object (`zCVob:NW_CITY_DECO_SWORDFISH_01.001`) exports
identically to the original.

| Prefix | Object name means... | Notes |
|---|---|---|
| `zCVob:` | Mesh filename, without extension | e.g. `zCVob:NW_CITY_DECO_SWORDFISH_01` uses `NW_CITY_DECO_SWORDFISH_01.3DS`/`.MRM` |
| `oCItem:` | The item's script instance name | e.g. `oCItem:ITMI_BROOM`. Instance name isn't generally the mesh filename - see Known Issues |
| `zCVobSpot:` | Freepoint name | Used by NPCs during `TA_Stand_*` routines |
| `zCVobStartpoint:` | Player/NPC start position name | Only one should exist per playable world |
| `zCVobLevelCompo:` | World mesh filename, without extension | Reference only - see `WORKFLOW.md` for why this doesn't embed real geometry |
| `zCWaypoint:` | Waypoint name | Links are edited via the addon's link slots, not by name |
| `zCVobLight:` | Light name | Created as a real Blender Light - edit type/range/cone-angle/color via Blender's own Light Properties tab, not custom properties |
| `zCVobSound:` | The sound's script instance name | |

Adding VOBs through the addon's "Add Other VOBs" dialog handles the
`Prefix:Name` construction for you - the table above matters mainly if
you're renaming things by hand or reading an existing scene.

## KrxImpExp version note

There isn't one canonical version of KrxImpExp in circulation - at least
two meaningfully different ones have shown up during this project's
development, with different registered operator names (plain
`krxmrmimp` vs. GUI-wrapped `krxmrmimpgui`) and different mesh-format
support (a working raw `.3ds` importer exists in one version, not the
other). To stay compatible either way, this addon resolves KrxImpExp's
installed module dynamically and calls the plain Python functions each
version exposes "for calling outside KrxImpExp" (`Krx3dsImp`,
`KrxMrmImp`) rather than depending on a specific `bpy.ops` name - see
`krximpexp_bridge.py`. If mesh import/preview stops working after
updating KrxImpExp, that bridge module is the first place to check.

## Testing

- `tests/test_coordinate_transform.py`, `tests/test_archive_verifier.py` -
  pure-Python, no Blender required. Run `pytest` from the repo root
  (uses the `mathutils/` fake stub the same way `test_zen_export.py`
  does). These specifically guard against the coordinate-transform bug
  that once shipped unnoticed (a mirror reflection instead of a proper
  rotation) - see `ARCHITECTURE.md` for the story.
- `tests/test_zen_export.py` - the original prototype's test, exercising
  more of the export pipeline end to end.
- `exports/` - real generated `.blend`/`.ZEN` samples from manual
  testing sessions, kept for reference rather than deleted.

## Known issues / limitations

- Bounding boxes are always a single point, not sized to the object -
  can affect LOD behavior in-game.
- `OCVobTree`'s intended per-type sort ordering doesn't fully work (an
  `isinstance` check order issue) - doesn't corrupt output, just doesn't
  sort the way the code appears to intend. See `ARCHITECTURE.md`.
- ZEN import only searches the ZEN file's own directory for a
  referenced level mesh (no configured search path yet), and doesn't
  reconstruct waypoint *facing direction* - only position.
- `zCVobLight`'s `lightType`/`lightQuality` enum ordinals are inferred
  from documented option names, not independently confirmed against a
  real compiled light.
- `oCItem` mesh preview isn't wired up yet - an item's script instance
  name generally isn't its mesh filename, unlike props. See
  `PLAN_vob_mesh_preview.md`.

## Project history

Started as a single-script prototype (`example_zen_export.py`,
export-only, five VOB types) by jaxub. Since extended into the current
addon: a searchable VOB creation UI, real mesh preview via KrxImpExp,
native Blender lights mapped to `zCVobLight`, automatic export
verification, an uncompiled-ZEN importer, and a modular addon structure
kept in sync across two machines via git.
