# zen_gin_export: Architecture & Feature Overview

This document explains how `zen_gin_export` is put together internally, and
where it currently stands feature-wise. It's meant as a starting point for
designing your own extensions to it.

Find more on https://zk.gothickit.dev/engine/overview/

## Layered architecture

The package is built in four layers, each with a narrow job. Understanding
the layering is the fastest way to know *where* a change belongs.

```
ZenArchive                     <- top-level document: header + one oCWorld block
    |-- OCVobTree              <- walks all Blender objects, builds the vob list
    |     |-- ZCVob subclasses <- one class per supported vob type
    |-- WayNet                 <- walks all Blender objects, builds the waynet
ZenGinDataPrinter               <- generic ASCII block/property syntax
Printer (Console/File)          <- where the text actually goes
```

**Layer 1 - `Printer` / `ZenGinDataPrinter`.** `Printer` is a one-method
interface (`print(*content)`); `ConsolePrinter` and `FilePrinter` are the
two implementations. `ZenGinDataPrinter` sits on top and knows nothing
about Gothic vobs at all - it just knows the ZenGin ASCII archive's generic
syntax: `[type1 type2 trianglesLimit objectIndex]` ... `[]` for object
blocks, and `name=type:value` for properties, with indentation tracked
automatically. This layer would be reused unchanged even if you added
completely new object types.

**Layer 2 - the `ZCVob` class hierarchy.** This is the layer you'll touch
most. `ZCVob` (in `zen_gin_zcvob.py`) is the base class for every vob type
and does the actual Blender-to-ZenGin translation: reading the Blender
object's name/location/rotation, converting coordinates (`-100/-100/100`
axis flip + centimeter scale) and rotation (quaternion -> 3x3 matrix ->
hex-encoded floats), and writing the standard vob property block (`pack`,
`bbox3DWS`, `trafoOSToWSRot`, `trafoOSToWSPos`, `vobName`, `visual`,
`showVisual`, collision flags, etc.), followed by a nested (usually empty)
`visual` sub-block and an empty `ai` sub-block. Every subclass gets this
for free and only needs to override a handful of class attributes/methods:

* `_type_name` - the ZenGin class name written into the block header,
  e.g. `"zCVobStartpoint:zCVob"`.
* `_visual()` - what to put in the `visual` property (defaults to
  `vobName + ".3DS"`; override to return `""` for non-visual vobs).
* `_show_visual`, `_static`, `_collision` - simple flag overrides.
* `_print_additional_data()` - hook for writing any extra type-specific
  properties (the only current user of this is `OCItem`, which writes an
  `itemInstance` property).

`NoVisualObjectVob` is a small intermediate base class for vobs that don't
have a mesh at all (waypoints' cousins `ZCVobSpot`, `ZCVobStartpoint`,
`OCItem`) - it sets `_visual_object_type_2 = "%"` and skips allocating a
separate object index for the visual sub-block.

**Layer 3 - `OCVobTree` / `WayNet`.** These are the two independent
"trees" a ZenGin world actually has. Both take the *entire* list of
Blender objects and do their own filtering:

* `OCVobTree.__create_vob()` pattern-matches each object's name prefix
  (`zCVob:`, `oCItem:`, `zCVobSpot:`, `zCVobStartpoint:`,
  `zCVobLevelCompo:`) against a fixed elif chain, constructs the matching
  class, drops anything that doesn't match (plain meshes, cameras,
  lights, etc. are silently ignored), sorts the result, and prints it as
  a flat list of children under one implicit root - there's no real
  parent/child nesting despite the "tree" name.
* `WayNet` (in `zen_gin_waynet.py`) separately filters for
  `zCWaypoint:` objects and reads their link data from the
  `zen_waypoint_links` PropertyGroup - which is registered by the
  *separate* `zen_waypoint_tools` Blender addon, not by this package.
  This is the one place `zen_gin_export` has a runtime dependency on
  another addon being installed and enabled.

**Layer 4 - `ZenArchive`.** The entry point. Given the Blender object list
and a `Printer`, it builds the header (archive format markers, a fixed
fake date, a hardcoded object count), wraps one `oCWorld:zCWorld` block
around the vob tree + waynet output, and closes it with an `EndMarker`.

### The object-index thread

Every object block in the ASCII format needs a globally unique sequential
index. This is threaded through all four layers as a plain integer that
gets passed in and a new value returned: `ZCVob.print(object_index)` ->
`updated_object_index()` -> `OCVobTree.print()` accumulates this across
every vob -> `ZenArchive` adds the world object itself and the waynet's
count on top. **This is the easiest thing to get subtly wrong when adding
a new vob type** - if a new subclass allocates a different number of
object blocks than `_objects_count` claims, every object index after it
in the file will be off, and Spacer/the game will likely misparse or
silently drop something. Always double check `_objects_count` matches
exactly how many `[type ...]...[]` blocks your `print()`/
`_print_additional_data()` actually emits.

## Feature status

### Implemented and working

* Core ASCII archive serialization (Printer / ZenGinDataPrinter / ZenArchive)
* Vob types: `zCVob` (generic mesh prop), `oCItem`, `zCVobSpot` (freepoints),
  `zCVobStartpoint`, `zCVobLevelCompo` (mesh *reference*, not embedded
  geometry - see `WORKFLOW.md` for the compiled/uncompiled distinction)
* `zCWaypoint` export via `WayNet`, fed by the `zen_waypoint_tools` addon
* `FilePrinter` / `ConsolePrinter` output backends
* Blender-side waypoint authoring: add/link/unlink/visualize, using plain
  Empty objects (no mesh or geometry-nodes dependency)

### Present but not fully solid

* **`OCVobTree.__vob_order`** has a latent bug: it checks
  `isinstance(vob, ZCVob)` before checking `OCItem`/`ZCVobSpot`
  specifically, but those are *subclasses* of `ZCVob`, so the generic
  check always matches first. In practice this means only
  `ZCVobLevelCompo` gets sorted to the front (order 0); everything else
  ends up in the same bucket (order 1) regardless of type, and the
  per-type ordering the code seems to intend never actually happens.
  Doesn't appear to break valid output, just doesn't do what it looks
  like it's meant to do.
* **Bounding boxes** are a single point repeated twice (`start == end`),
  not a real box derived from object size - documented as a known issue
  in the main README, relevant to LOD behavior.
* **`FilePrinter` writes on `__del__`**, i.e. it relies on Python's
  garbage collector to actually flush content to disk, rather than an
  explicit `save()`/`close()` call. This bit us directly during testing -
  we had to manually `del` the object and force `gc.collect()` to get the
  file to write reliably.
* **No validation at export time** - malformed names, missing/duplicate
  vob names, or an object matching no known prefix are all silently
  accepted or silently ignored; there's no reporting back to the user in
  Blender about what got skipped and why.
* The archive header hardcodes `date 1.1.1970 12:0:0` with a `# TODO` -
  cosmetic, but present in every file.

### Not yet implemented

* `zCVobLight` (static/dynamic lighting)
* `oCMobInter` and its interactive-object subclasses (doors, containers,
  switches, fires, ladders, wheels, etc.)
* Sound (`zCVobSound`, `zCVobSoundDaytime`)
* Triggers of any kind (`zCTrigger` family: movers, script triggers,
  level-change triggers, code masters, ...)
* Zones/atmosphere (`oCZoneMusic(Default)`, fog/far-plane zones)
* Cutscene cameras (`zCCSCamera`)
* NPC placement
* Merging Blender-authored vobs into an *existing* Spacer-made ZEN,
  rather than only ever writing a fresh archive from scratch - listed in
  the README as the most realistic long-term direction
* A dedicated "Add Level Compo" operator in the Blender addon (currently
  a plain empty has to be created and renamed by hand)
* True nested vob hierarchies - the underlying format supports
  parent/child nesting via the `childs{N}` counters, but nothing in this
  package currently produces more than one flat generation

## Where to start if you extend it

Adding a new simple (position/rotation-only) vob type is the smallest
unit of work and follows a consistent recipe, demonstrated by
`zCVobStartpoint`:

1. New file, subclass `ZCVob` or `NoVisualObjectVob` depending on whether
   it has a mesh.
2. Set `_type_name` to the real ZenGin class string (`"YourType:zCVob"`,
   or `"YourType:zCVob:oCMOB"` etc. for deeper native hierarchies - see
   the "polymorphic class names" note in ZenKit's archive format docs if
   you go beyond a single level of inheritance).
3. Override `_visual()`, `_show_visual`, `_static`, `_collision` as
   appropriate.
4. If the type needs extra properties beyond the standard vob block,
   override `_print_additional_data()` and bump `_objects_count`
   accordingly if you add sub-blocks.
5. Register the name prefix in `OCVobTree.__create_vob()`.

Anything with its own sub-hierarchy of properties (triggers, lights,
interactive objects) will need more thought - primarily figuring out that
type's exact property schema, which the `zk.gothickit.dev` documentation
for each class is the most reliable current source for.
