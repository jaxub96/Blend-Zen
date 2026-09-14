# Gothic II ZenGin VOB Types: Implemented vs. Not Yet Implemented

A reference for scoping future VOB support, researched from ZenKit's
engine docs (`zk.gothickit.dev`) and the OpenGothic VOB/Trigger reference,
cross-checked against this repo's `OCVobTree.__create_vob()` and
`WayNet` (`modules/zen_gin_export/zen_gin_ocvobtree.py` /
`zen_gin_waynet.py`).

See `USAGE_interactive_objects.md` for a worked, end-to-end guide to the
oCMOB family below (how to make a chest/door/bed actually work in-game),
and `ARCHITECTURE.md` for how any of this is wired together internally.

## Implemented in Blend-Zen today

| VOB | Definition | In-game application |
|---|---|---|
| `zCVob` | The generic base class, used here for a plain static mesh instance with no special behavior | World decoration: rocks, furniture, crates, barrels — anything visual and non-interactive |
| `oCItem` | A pickupable item tied to a Daedalus script instance (e.g. `ITMI_APPLE`) | Loot hand-placed in the world (as opposed to container contents defined in script) |
| `zCVobSpot` (Freepoint) | A named position/orientation marker with no mesh | NPC routine AI targets — `TA_Stand`, `TA_Sit`, alchemist/smith work spots, guard posts |
| `zCVobStartpoint` | A single named spawn transform | Where the player (or an NPC entering the world) appears when the level loads |
| `zCVobLevelCompo` | A reference to the level's own compiled mesh/BSP, not a real placed instance | The wrapper vob around the world geometry itself, needed for a structurally valid archive |
| `zCWaypoint` (+ `WayNet`) | A navigation graph node, linked to others via "ways" | The backbone NPCs path along to move around the level |
| `zCVobLight` | A static or dynamic point/spot light (type, range, cone, color) | Level lighting — torches, magic glow, lamps, baked or real-time |
| `zCVobSound` | An ambient sound emitter | Environmental audio (volume/radius/cone fields not yet exported — see `ARCHITECTURE.md`) |
| `oCMobInter` | Generic interactive object: has state, a trigger target, and item/condition requirements for use | Base for everything below; also addable directly for a custom "use" prop that doesn't fit a more specific type |
| `oCMobContainer` | A lootable container with inventory contents and optional lock/key | Chests, barrels, sacks the player can loot |
| `oCMobDoor` | A door with open/closed state, lock, key instance, picklock difficulty | Building/dungeon doors, gates |
| `oCMobBed` | A sleepable bed | NPC sleep schedules; player resting/waiting |
| `oCMobSwitch` | An activatable lever/switch | Puzzle levers, gate releases, quest-triggering switches |
| `oCMobLadder` | A climbable ladder | Connecting vertical sections of a level |
| `oCMobWheel` | A rotating wheel mechanism | Mine winches, waterwheels, puzzle mechanisms |
| `oCMobFire` | A usable fire source with NPC "seating" slots | Campfires NPCs sit at and cook on; can be lit/extinguished |

The oCMOB family shares one base implementation
(`modules/zen_gin_export/zen_gin_zcvob_ocmob.py` and
`zen_gin_zcvob_ocmob_inter.py`/`_lockable.py`) - see `ARCHITECTURE.md`
for the class hierarchy and `USAGE_interactive_objects.md` for how to
actually configure one of these so it works in-game (the exporter alone
isn't enough - the object's `visual` needs to point at an existing
animated model, see that doc).

## Not yet implemented (relevant, real level-design types)

**Triggers / level logic (`zCTrigger` family)**

| VOB | Definition | In-game application |
|---|---|---|
| `zCTrigger` | Generic relay: receives `OnTrigger`/`OnDamage`/`OnTouch` and forwards to a named target if the source passes a filter | The backbone of almost all scripted level logic — pressure plates, area-entry events |
| `zCTriggerList` | Fires a whole list of targets, simultaneously or in sequence | One switch driving several effects at once (open door + play sound + start music) |
| `zCCodeMaster` | Requires several specific slave triggers to have fired (optionally in order) before firing its own target | Multi-switch/rune puzzles |
| `zCMover` | An animated piece of geometry following a keyframed path, with speed/sound | Drawbridges, elevators, sliding gates, moving platforms |
| `zCMoverController` | Sends start/stop/toggle commands to a `zCMover` | Letting one trigger remote-control a mover |
| `oCTriggerScript` | Calls a named Daedalus function when triggered | Arbitrary custom quest/event scripting tied to a volume |
| `oCTriggerChangeLevel` | Loads a different world file at the player's position | Zone transitions between Gothic II's world maps (e.g. city ↔ valley) |
| `zCTriggerWorldStart` | Fires once automatically on world load | One-time init logic when a level starts |
| `zCTriggerUntouch` | Fires when something *stops* touching a volume | "On-exit" logic, inverse of a normal touch trigger |
| `zCTriggerTeleport` | Teleports whatever touches it to a target location | Local teleport puzzles/shortcuts |
| `zCMessageFilter` | Filters/redirects an incoming trigger message before forwarding it | Combining or gating trigger conditions |
| `zCTouchDamage` / `oCTouchDamage` | A volume that damages (with a damage-type filter) anything touching it | Lava, thorns, trap floors |

**Zones / atmosphere**

| VOB | Definition | In-game application |
|---|---|---|
| `oCZoneMusic(Default)` | Defines a music theme + reverb for a volume | Background music/reverb changes between town, wilderness, dungeons |
| `zCZoneZFog(Default)` | Sets fog color/range within a volume | Cave fog, swamp haze, weather atmosphere |
| `zCZoneVobFarPlane(Default)` | Controls object draw distance within a volume | Performance tuning — denser view distance in town vs. open world |

**Cinematics & visual effects**

| VOB | Definition | In-game application |
|---|---|---|
| `zCCSCamera` (+ `zCCamTrj_KeyFrame`) | A scripted camera path with keyframe interpolation | In-engine cutscenes and dialogue framing |
| `zCPFXController` | Places and manages a particle-effect instance | Torch flames, magic effects, dust, waterfalls |
| `zCVobAnimate` | Plays a looping/triggerable animation on an otherwise-static mesh | Waving flags, turning wheels, simple mechanical motion |
| `zCVobLensFlare` | Attaches a lens-flare effect to a light | Sun glare, bright torch/magic glare |
| `zCEarthquake` | Triggers a radius-limited camera-shake effect | Scripted dramatic moments (explosions, story beats) |
| `zCVobScreenFX` | Triggers a full-screen post-process effect | Fades, damage-blood overlay, cutscene transitions |

**Sound variant**

| VOB | Definition | In-game application |
|---|---|---|
| `zCVobSoundDaytime` | Like `zCVobSound` but with separate day/night sound instances | Ambience that changes with time of day (birds vs. crickets/owls) |

**NPC (lower priority for a level-authoring tool)**

| VOB | Definition | In-game application |
|---|---|---|
| `oCNpc` | The actual NPC actor (state, inventory, AI) | Usually spawned dynamically via Daedalus (`Wld_InsertNpc`) rather than hand-placed in Spacer; only shows up as a vob in save-game state, so it's a weaker fit for this authoring tool than the others above |

## Sources

- [zCVob - ZenKit](https://zk.gothickit.dev/engine/objects/zCVob/)
- [zCTrigger - ZenKit](https://zk.gothickit.dev/engine/objects/zCTrigger/)
- [oCMOB - ZenKit](https://zk.gothickit.dev/engine/objects/oCMOB/)
- [oCMobInter - ZenKit](https://zk.gothickit.dev/engine/objects/oCMobInter/)
- [oCMobLockable - ZenKit](https://zk.gothickit.dev/engine/objects/oCMobLockable/)
- [oCMobContainer - ZenKit](https://zk.gothickit.dev/engine/objects/oCMobContainer/)
- [oCMobBed - ZenKit](https://zk.gothickit.dev/engine/objects/oCMobBed/)
- [oCMobFire - ZenKit](https://zk.gothickit.dev/engine/objects/oCMobFire/)
- [VOBS & Triggers - OpenGothic Wiki](https://github.com/Try/OpenGothic/wiki/VOBS-&-Triggers)
- [zCVob - Gothic Modding Community](https://gothic-modding-community.github.io/gmc/zengin/worlds/Classes/zCVob/)
- [oCMobInter - Gothic Modding Community](https://auronen.cokoliv.eu/gmc/zengin/worlds/Classes/zCVob/oCVob/oCMOB/oCMobInter/)
- [ModelScript (MDS) - Gothic Modding Community](https://gothic-modding-community.github.io/gmc/zengin/anims/mds/)
