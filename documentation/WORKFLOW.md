# Blender -> Spacer Workflow

This document explains how `zen_waypoint_tools` (the Blender addon) and
`zen_gin_export` (the Python export package) fit into the standard Gothic 2
modding pipeline, and how to manually test the full path from a Blender
scene to a playable, compiled `.ZEN` world.

It is written for **manual testing today**. A later goal is to fold more of
these steps into the Blender addon itself (see "Future integration" at the
end), but nothing described here depends on that happening first.

## The core mechanic: compiled vs. uncompiled ZEN

A `.ZEN` file is ZenGin's archive format, and it can hold two very
different things depending on how it was saved:

* **Compiled ZEN** - a full, game-ready level: baked world mesh, BSP tree,
  lightmaps, materials, the VOB tree, and the waynet. This is what the game
  actually loads and renders.
* **Uncompiled ZEN** - everything *except* the baked geometry. It stores
  the VOB tree, the waynet, and (via a `zCVobLevelCompo` object) a
  *reference* to the `.3ds` mesh file that should be compiled in. It has
  no BSP tree and cannot be loaded as a playable world on its own.

`zen_gin_export` only ever produces the **uncompiled** kind (compare the
`UNCOMPILED_EXPORT.ZEN` name used in its example script). That is not a
limitation to work around - it is the intended handoff format. Spacer's
"Compile World" step is specifically built to take an uncompiled ZEN,
resolve the mesh it references, bake the geometry, and **merge it with the
VOB tree and waynet already stored in that same file**. Nothing placed in
Blender gets lost or has to be re-placed by hand in Spacer.

Nobody outside Piranha Bytes has published a way to write the baked
BSP/lightmap data itself - even ZenKit, the most actively maintained
open-source reimplementation of the ZenGin formats, only supports writing
VOB-tree data, not compiled world geometry. So the compile step always
has to happen in Spacer; the addon's job is only to avoid hand-placing
every VOB there.

## Naming conventions (recap)

Objects in the Blender scene are matched purely by name prefix
(see the main `README.md` for the full list). The ones relevant to a
level test:

| Prefix              | Meaning                                              |
|---------------------|-------------------------------------------------------|
| `zCVobLevelCompo:`   | Reference to the level's `.3ds` mesh. Object name (minus this prefix) must match the mesh filename without `.3ds`. |
| `zCWaypoint:`        | A waynet node. Links are stored via the addon's link slots. |
| `zCVobStartpoint:`   | Player/NPC start position. |
| `zCVob:` / `zCVobSpot:` / `oCItem:` | Static props, freepoints, items - see `README.md`. |

Plain mesh objects with no matching prefix are ignored by the exporter -
this is why the level mesh and the VOB empties can safely live in the same
`.blend` file.

## End-to-end manual test

1. **Model the level mesh** as normal geometry in Blender - no prefix
   needed, since non-prefixed objects are skipped by the exporter.
2. **Export the mesh to `.3ds`** using KrxImpExp, into
   `<Gothic II install>\_work\Data\Meshes\...` (subfolders are fine).
3. **In the same `.blend`**, add:
   - one `zCVobLevelCompo:<meshname>` empty, named to match the `.3ds`
     file from step 2 (without the extension)
   - your `zCWaypoint:` chain (via `zen.add_waypoint` / `zen.link_waypoints`)
   - a `zCVobStartpoint:` empty at the intended spawn location
   - any other `zCVob:` / `zCVobSpot:` / `oCItem:` objects
4. **Run the export script** (adjust `gothic_directory` as needed). This
   writes an uncompiled ZEN, by default `UNCOMPILED_EXPORT.ZEN`, into
   `_work\Data\Worlds\Plugin` (or wherever the script is configured to
   write).
5. **Open Spacer -> File -> Open** and pick that uncompiled ZEN directly
   (not "Import mesh" - the file already references the mesh through the
   `zCVobLevelCompo` entry, and Spacer resolves it from the Meshes path).
6. **World -> Compile World.** Choose Outdoor or Indoor as appropriate,
   and make sure Editor mode is **off** (Editor mode is for touching up
   materials/portals on the raw mesh before it's a world - not what we
   want here since our mesh should already be finished).
7. **World -> Compile Light.**
8. **File -> Save as** a compiled ZEN into `_work\Data\Worlds\`. This
   file now contains the baked geometry *and* every VOB/waypoint/startpoint
   authored in Blender.
9. **Point a mod's startup world** at this ZEN (however your mod loader /
   Ikarus config normally selects the start world) and launch Gothic 2 to
   test in-game.

## Known limits of this manual process today

* The addon has no button yet for creating a `zCVobLevelCompo` reference -
  it has to be added as a plain empty and renamed by hand.
* Triangle limits still apply per the usual Gothic rules (keep submeshes
  under roughly 50k triangles; split larger meshes and rely on Spacer's
  macro system to join them, same as vanilla Gothic worlds do).
* Bounding boxes generated by the exporter reflect a loaded mesh preview
  (the addon's "Load Mesh Preview" button - see `USAGE_mesh_preview.md`)
  - a VOB placed without loading its preview first still exports a
  degenerate single-point box, since there's no geometry in Blender to
  size it against. See `ARCHITECTURE.md` for the mechanism.

## Future integration

Once this manual path has been tested and confirmed working end to end,
candidates for folding into the addon itself include:

* A one-click "Add Level Compo Reference" operator, so step 3's
  `zCVobLevelCompo` object doesn't have to be created and renamed by hand.
* Exposing more VOB types (`oCMobInter`, `zCVobLight`,
  `oCZoneMusicDefault`, ...) the same way waypoints and the startpoint
  were added.
* Investigating whether Spacer's compile step could be scripted/automated
  from outside Spacer's UI, to shorten the loop further - unconfirmed
  whether Spacer exposes anything scriptable for this.
