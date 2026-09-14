# Usage: Interactive Objects (the oCMOB family)

A guide to actually making a chest, door, bed, switch, ladder, wheel or
fire source work in-game once you've placed one with the addon - not
just export correctly, but *behave* correctly for the player. See
`VOB_TYPES.md` for what each type is, and `ARCHITECTURE.md` for how the
exporter classes fit together.

## The one thing that makes this different from a plain prop

A plain `zCVob` prop's Blender object name doubles as its mesh filename
(`zCVob:NW_CITY_DECO_SWORDFISH_01` -> `NW_CITY_DECO_SWORDFISH_01.3DS`).
**oCMOB objects don't work that way.** Two things are true at once:

1. The object's name is its unique in-game identity (`vobName`) - what a
   trigger's `triggerTarget` would use to address it, and what has to be
   unique per instance (you can have five chests, each needs its own
   name).
2. Its actual appearance comes from a **shared, reused, already-animated
   model** - a `.MDS` ("ModelScript"), not a plain static mesh. Every
   chest in the game can point at the same `CHESTBIG_OCCRATELARGE.MDS`;
   every human bed can point at the same `BED_HUM.MDS`. That MDS file is
   what actually defines the object's states (e.g. "closed" / "open")
   and the animations that play when it switches between them - Gothic
   calls this out explicitly as `s_S0` (closed), `s_S1` (open), and a
   transition animation like `t_S0_2_S1` (opening) tied together by the
   MDS.

This is exactly the same split `oCItem` already has (script instance
name vs. mesh filename - see `zen_gin_zcvob_ocitem.py`), just with a
different resolution mechanism: instead of a global lookup table
(`item_mesh_map.json`), each oCMOB instance has its own **"Visual Name"**
custom property naming the MDS it should use. Leave it blank and the
object falls back to using its own name as the mesh name - only correct
if you're pointing at a genuinely one-off custom asset named after
itself.

**This means Blend-Zen can place these objects correctly, but it cannot
create the animated model itself.** Authoring a brand-new piece of
animated furniture (new mesh + skeleton + `S0`/`S1`/transition
animations, compiled to `.MDS`/`.MDH`/`.MDM`) is a 3ds Max + Gothic
animation SDK workflow, well outside what this addon (or KrxImpExp's
plain mesh import) does. In practice this doesn't matter for most level
design: you reuse one of the game's existing animated furniture assets
(there are dozens already covering chests, doors, beds, switches,
levers, wheels) rather than making a new one.

**Known limitation:** "Load Mesh Preview" (`mesh_preview.py`) does not
support oCMOB objects yet - it only knows how to import static `.MRM`
meshes for `zCVob:`/`oCItem:` props, not skeletal MDS-driven models. You
won't see the real furniture shape in the Blender viewport; you're
placing/orienting an Empty and trusting the "Visual Name" you typed is
correct. Double-check the spelling against a real file before exporting.

## Finding a real MDS name to use

You need the base filename (no extension) of an existing animated
model. Two practical ways to find one:
- Browse your Gothic II install's `_work\Data\Anims\_compiled\` (or the
  original `Anims.vdf`, unpacked) for `<NAME>.MDS` files - furniture
  ones are usually self-descriptive (`BED_HUM`, `CHESTBIG_OCCRATELARGE`,
  `DOOR_WOOD_01`, `SWITCH_LEVER_01`, `MINEWHEEL_01`, ...).
- Open an existing vanilla world in Spacer/a decompiler and inspect a
  chest/door/bed already placed there - its `visual` field is exactly
  the string you want.

## Step by step: placing one from the addon

1. **ZenGin sidebar > Add Other VOBs > Type**, pick the interactive type
   you need (e.g. "Interactive: Bed"). Give it a real, unique name for
   *this instance* - not a mesh name (e.g. `BED_TAVERN_ROOM_01`).
2. With the new object still selected, the sidebar panel now shows an
   "oCMobBed properties" box (or the matching type). Set **Visual Name**
   to the real MDS base name, e.g. `BED_HUM`.
3. Fill in whatever else applies to this type (see the table below) -
   everything else can be left at its default for a plain, working
   object.
4. Position/orient the Empty where the object should sit (this still
   drives `trafoOSToWSPos`/`trafoOSToWSRot`/`bbox3DWS` exactly like any
   other vob - see `ARCHITECTURE.md`'s bounding-box section; since there's
   no preview mesh loaded, the exported box will be a degenerate point,
   which is fine here since it's cosmetic/LOD-only).
5. **Export Uncompiled ZEN** as usual, open in Spacer, **World -> Compile
   Level Geometry** (or **Compile Light** if you need lighting too), and
   test in-game.

## Worked example: making an existing bed sleepable

This is the concrete case: you already added a bed via the addon and
want the player to actually be able to sleep on it.

1. If the object you already placed is a plain `zCVob:` (not
   `oCMobBed:`), it will never be interactive - `zCVob` has no state
   machine or interaction logic at all, no matter what mesh it shows.
   Rename it (or delete and re-add) so its name starts with
   `oCMobBed:`, e.g. `oCMobBed:BED_TAVERN_ROOM_01`.
2. Select it, and in the sidebar's "oCMobBed properties" box set
   **Visual Name** to `BED_HUM` (or whichever real bed MDS you're
   using).
3. Leave everything else default - `oCMobBed` adds no fields beyond the
   generic interactive-object ones (`state_num`, `trigger_target`,
   `use_with_item`, `condition_func`, `on_state_func`, `rewind`), and a
   plain sleepable bed needs none of them set. In particular you do
   **not** need `trigger_target` - that's for a bed that should also
   fire some other event when used (unusual), not for the base act of
   sleeping in it.
4. Export, compile in Spacer, and test: walking up to the bed and
   pressing the action/use key should be enough for the *player* to lie
   down and sleep, driven entirely by the engine's built-in
   `oCMobInter` interaction logic plus the animation states already
   baked into `BED_HUM.MDS` - no Daedalus script required for that part.
5. **Getting an NPC to sleep in this specific bed on a schedule is a
   separate mechanism** and out of scope for this addon: that's
   controlled by the NPC's own daily routine script
   (`Rtn_ExchangeRoutine` / `TA_Sleep`), which references the bed by
   name from Daedalus code, not by anything set here.

This player-sleep mechanism (built-in engine interaction + a
pre-animated MDS, no script needed) is inferred from ZenGin/oCMobInter
documentation and hasn't yet been independently confirmed with a real
Gothic II Spacer round-trip the way the coordinate-transform fixes in
`ARCHITECTURE.md` were. If it doesn't behave as described, that's the
first thing to re-check - the property mechanism controlled by Blend-Zen
(the `oCMobBed:` prefix + `visual_name`) is straightforward, but exactly
what the engine does with it once compiled is the part worth verifying
with one real test object before building out several.

## Field reference

Every field below is a plain custom (ID) property on the Blender object
- editable either from the sidebar box (while that object is active) or
Blender's own Object Properties > Custom Properties tab. See
`mob_props.py` for the exact defaults/descriptions and
`zen_gin_zcvob_ocmob*.py` for how each maps to the real archive
property.

| Field | Applies to | Meaning |
|---|---|---|
| Visual Name | all | Base filename (no extension) of the shared MDS model - see above |
| Focus Name | all | Text shown in-game when the player looks at the object |
| Hitpoints / Damage | all | Leave at 0 for ordinary furniture (both are for destructible/weapon-like objects) |
| Moveable / Takeable | all | Can the player drag it around / pick it up into inventory |
| Sound Material | all | Impact sound: WOOD, STONE, METAL, LEATHER, CLAY, GLAS |
| Owner / Owner Guild | all | Script instance/guild that "owns" it, for theft detection |
| Trigger Target | all | Another vob's name to send an OnTrigger event to when this is used - for a switch opening a door, not needed for a plain bed/chest |
| Use With Item | all | Item instance required in inventory to interact (e.g. a key that must be *held*, as opposed to Key Item below which is *consumed/checked* by a lock) |
| Condition/On-State Function | all | Daedalus function names, only if you need custom scripted behavior beyond the built-in state machine |
| State Count | all | Leave at 0 (use the model's own default) unless you know the MDS defines a different count |
| Rewind | all | Fire the trigger every use, instead of only the first time |
| Locked / Key Item / Picklock Combination | Chest, Door | Standard lock - Key Item is the script instance that opens it, Picklock Combination (e.g. `RRLRL`) enables lockpicking, empty disables it |
| Contains | Chest | `ITEM_INSTANCE:count` comma list, e.g. `ITFO_APPLE:3,ITMW_1H_SHORTSWORD1` |
| Fire Slot / Fire Vobtree | Fire | Bone name for the flame effect, and the fire-effect template ZEN (e.g. `FIRETREE_MEDIUM.ZEN`) |
