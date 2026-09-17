# Coordinate Transform: Architecture & Verification Workflow

Blender is right-handed and Z-up. ZenGin (Gothic's engine) is Y-up and
**left-handed** relative to Blender - confirmed empirically 2026-09-16
(see "How this was verified" below), overturning an earlier assumption
that both spaces were right-handed. Both the position and rotation
formulas below are now empirically confirmed in Spacer, not just
derived.

## The formulas

`modules/zen_gin_export/coordinate_transform.py`:

```
Gothic_X = Blender_X * 100
Gothic_Y = Blender_Z * 100
Gothic_Z = Blender_Y * 100      # plain axis swap, no sign flip

Gothic_w =  Blender_w
Gothic_x = -Blender_x
Gothic_y = -Blender_z
Gothic_z = -Blender_y
```

The position map is a pure Y<->Z swap (determinant -1 - a handedness
flip, not a rotation). The rotation formula is *derived* from that, not
guessed: a rotation matrix conjugates across any change of basis as
`M_gothic = R @ M_blender @ R.T`, which holds for any orthogonal `R`
regardless of determinant. Expanding that for our `R` (the Y<->Z swap)
and converting back to a quaternion gives the formula above - see the
derivation in `blender_quaternion_to_gothic`'s docstring if it ever
needs re-deriving for a different `R`.

Both are covered by `tests/test_coordinate_transform.py`.

**Call sites** (all four route through these two functions - one place
to fix if either formula ever changes): `ZCVob.__location`/`__rotation`
in `zen_gin_zcvob.py`, and `WayNet.__waypoint_location`/
`__waypoint_rotation_vec3` in `zen_gin_waynet.py`.

## How this was verified: the "Compass Cross" test

**Why a freepoint-only export test doesn't work:** an uncompiled ZEN is
plain text. Opening it in Spacer just parses back whatever number our
own exporter wrote - there's no independent check, so a test built that
way can only confirm the export pipeline transcribes correctly, never
whether the formula itself matches Gothic's real convention. (An earlier
attempt at this test looked conclusive and wasn't - worth remembering
before reaching for a quick freepoint check again.)

**The fix: get a second, independent conversion into the same compile.**
KrxImpExp's `.3ds` mesh exporter applies zero axis conversion (raw
Blender coordinates out); the real Blender->Gothic conversion for
geometry happens opaquely inside **Spacer's own World -> Compile World**
step - a completely different code path from `coordinate_transform.py`.
If a freepoint vob (converted by our formula) and a mesh feature
(converted by Spacer's compiler) claim the same Blender-space point and
land in the same place after compiling, that's real, non-circular
evidence.

**The test scene:** a plaza with 5 arms of 5 *different* lengths (3/5/7/
9/11 m), one per direction (+X/-X/+Y/-Y/+Z), so each arm is identifiable
purely by length - no math, no ambiguity. A freepoint sits at each arm's
tip. After compiling in Spacer, each freepoint should land exactly on
its same-length arm; landing on a different-length arm (or floating
free) pinpoints exactly what's wrong. This settled the open axis-sign
question decisively: two of the freepoints (computed with the
old, since-fixed formula) landed clearly short of / past the wrong
arms' tips, in exactly the pattern the current fix predicts.

**Rotation** reuses the same scene, but checked differently: since both
`TEST_ROTATION_REFERENCE` and `TEST_ROTATION_PLUS90Z` sit at the plaza
center and are converted by our own formula either way, the compass
arms can't serve as an independent oracle here the way they do for
position - there's no second, independent rotation implementation to
compare against. Instead the arms serve as a **shared landmark that
exists identically in Blender and in Spacer**: note which arm each
freepoint points at in the source `.blend` (before export), then check
the same in Spacer after compiling. Matching arms in both = the
rotation survives the export/compile pipeline correctly.

**Confirmed 2026-09-16:** `TEST_ROTATION_PLUS90Z` turns 90 degrees
counterclockwise relative to `TEST_ROTATION_REFERENCE`, identically in
both Blender and Spacer. Both formulas (position and rotation) are now
empirically confirmed, not just derived.

## Reusable test tool

`tooling/pipeline/build_compass_test_level.py` builds the full Compass
Cross scene (mesh + all freepoints) in one script run - see its
docstring for usage. Run it and re-check in Spacer any time the
formulas above change, or if in-game positioning/orientation looks
wrong again.

Full manual compile/deploy steps (Spacer has no scripting interface for
this part): `documentation/E2E_TEST_PLAN.md` Phase 6.
