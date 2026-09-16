# Coordinate Transform Investigation: Status

An open question about `coordinate_transform.py`'s Blender<->Gothic
conversion is unresolved. This document has everything needed to finish
it - no need to re-derive anything already worked out here.

## The current formula (what's live in code right now)

`modules/zen_gin_export/coordinate_transform.py`:

```
Gothic_X = Blender_X * 100
Gothic_Y = Blender_Z * 100
Gothic_Z = -Blender_Y * 100
```

Matrix form (ignoring scale): `[[1,0,0],[0,0,1],[0,-1,0]]`,
determinant = **+1** (a proper rotation, not a mirror, under the
assumption both Blender and Gothic are right-handed).

Rotation (quaternion, Blender's w,x,y,z order):
```
Gothic_w =  Blender_w
Gothic_x = -Blender_x
Gothic_y = -Blender_z
Gothic_z =  Blender_y
```

## Exact code locations

**This repo:**

| What | File | Line |
|---|---|---|
| `blender_position_to_gothic()` definition | `modules/zen_gin_export/coordinate_transform.py` | 24 |
| its `return` statement (the actual formula) | same file | 31 |
| `blender_quaternion_to_gothic()` definition | `modules/zen_gin_export/coordinate_transform.py` | 34 |
| its `return` statement (the actual formula) | same file | 65 |
| `ZCVob.__location()` (calls position transform) | `modules/zen_gin_export/zen_gin_zcvob.py` | 121 (call at 122) |
| `ZCVob.__rotation()` (calls rotation transform) | `modules/zen_gin_export/zen_gin_zcvob.py` | 146 (call at 148) |
| `WayNet.__waypoint_location()` (duplicate, waypoints) | `modules/zen_gin_export/zen_gin_waynet.py` | 61 (call at 62) |
| `WayNet.__waypoint_rotation_vec3()` (duplicate) | `modules/zen_gin_export/zen_gin_waynet.py` | 68 (call at 74) |

All four call sites route through the same two functions in
`coordinate_transform.py` - that's deliberate, so there's exactly one
place to fix if either formula changes.

**KrxImpExp** (installed addon, hash-suffixed folder name will differ if
reinstalled):
`...\Blender\5.2\scripts\addons\krximpexp-c20f0350a528e53f9bddc158f3cc18b6bfec61c1\`

| What | File | Line |
|---|---|---|
| `zenginWorldLoader.__read_vertices()` definition | `KrxMshImp.py` | 105 |
| the `x, z, y = verts_pos[...]` unpacking | same file | 111 |
| the `verts.append([x, y, z])` reassembly | same file | 115 |
| `T3DSFileSaver.__write_vertices_list()` (dead end, see below) | `Krx3dsExp.py` | 227 |
| the unconverted `vert = vert @ transform` | same file | 232 |
| the raw `WriteFloat(vert.x...)` calls | same file | 234 |

## Honest history: there is no canonical source for any of this

Worth being direct about, since it's easy to assume a spec exists
somewhere that was simply "found." It wasn't. The actual process:

1. The starting formula was **pre-existing, unsourced code** already in
   the repo before this project's involvement (two axes negated instead
   of one - a mirror-reflection bug, det=-1).
2. The position fix came from a **generic, non-Gothic-specific**
   reference (the Verge3D wiki's documented Blender->Y-up-engine
   formula: X->X, Y->-Z, Z->Y) plus a determinant check confirming it
   restores a proper rotation. Applying a generic engine's convention to
   Gothic specifically was itself an assumption.
3. It was verified against **real empirical data** (comparing our
   exported values to Spacer's own displayed bounding box for a real
   test file) - genuine ground truth, but only for position, and only
   for that one file's geometry.
4. The rotation-direction fix has the **weakest evidence of anything in
   this project**: inferred purely from one real Spacer test (a prop
   rotated 90 degrees about Blender's vertical axis came out facing
   backwards), with no independent source at all, and - important - the
   fixed formula has never actually been re-tested in Spacer since being
   applied. Only the original bug was observed; the fix was reasoned out
   and never empirically re-confirmed.

## What this session found: a real, unresolved disagreement

`KrxMshImp.py`'s `__read_vertices()` - the code that reads a
**compiled** world mesh's raw vertex chunk back into Blender - implies:

```
Gothic_X = Blender_X   <- agrees with current code
Gothic_Y = Blender_Z   <- agrees with current code
Gothic_Z = Blender_Y   <- DISAGREES: current code says -Blender_Y
```

X and Y match. **Z is a real, direct contradiction.**

`Krx3dsExp.py` was checked as a possible independent cross-check and
ruled out: its vertex writer emits Blender's raw x/y/z with **zero axis
conversion** - `.3ds` is a generic, Gothic-agnostic interchange format,
the real conversion only happens later inside Spacer's own compiler.
Don't retry this route.

## The remaining possible transformations (not an open-ended space)

Given `Gothic_X = Blender_X` and `Gothic_Y = Blender_Z` are locked, and
every formula seen anywhere in this investigation - the original buggy
code, the generic Verge3D reference, and the KrxMshImp reader - has been
a **clean axis permutation with sign changes only, never a mixed/rotated
combination** - it's reasonable (though an assumption, not a proof) to
constrain the remaining hypothesis space to that same form.

Under that constraint the math is rigid: `Blender_X` is already claimed
by `Gothic_X`, `Blender_Z` is already claimed by `Gothic_Y`. For the
mapping to be a valid bijection, **`Blender_Y` is the only axis left for
`Gothic_Z`** - there is no remaining freedom in *which* axis, only in
its *sign*. Exactly two candidates exist:

- **Candidate A (current code):** `Gothic_Z = -Blender_Y`. Determinant
  **+1** (proper rotation, assuming both sides right-handed).
- **Candidate B (KrxMshImp-implied):** `Gothic_Z = +Blender_Y`.
  Determinant **-1** under the same assumption - meaning either Gothic
  is actually **left-handed** (in which case this is the correct,
  shape-preserving map and *our* sign flip is the bug), or something
  else differs between compiled mesh vertices and vob positions.

## Important correction: rotation conjugation is NOT guaranteed to work the same way for both candidates

Earlier guidance in this project stated that a rotation quaternion's
scalar part `w` "never changes sign for any coordinate change." **That
claim is only true for proper (determinant +1) transforms.**

- If **Candidate A** is confirmed: the current rotation formula's
  derivation (permute the vector part the same way as position, negate
  it, leave `w` alone) remains valid *in form* - though see above, it
  has never actually been re-verified in Spacer since being applied, and
  should still be tested (Phase 2 below).
- If **Candidate B** is confirmed: the position transform is a
  determinant -1 map under a right-handed assumption, which most likely
  means Gothic is left-handed. Converting a rotation across a
  **handedness change** (not just a proper rotation) follows genuinely
  different conjugation rules than the ones used to derive the current
  formula - simply "permute and negate the vector part, keep w" is a
  proper-transform-only trick, and w is *not* guaranteed to stay
  unchanged when the transform includes a handedness flip. The whole
  rotation formula would need re-deriving from first principles for the
  left-handed case, not patched by flipping one more sign. This is real
  additional work, not a footnote - budget for it if Candidate B wins.

## Step-by-step test plan

### Design principles (why the test is built this way)

1. **Isolate one axis at a time.** Each test object should have exactly
   one non-zero coordinate. A combined point like `(3, 7, 2)` (used
   earlier) works but forces you to mentally decompose the result -
   single-axis offsets make a sign error immediately, visually obvious
   with no arithmetic required.
2. **Avoid any symmetric geometry for visual judgment.** A cube or
   symmetric room can look "correct" whether mirrored or not. Anything
   requiring a visual (not numeric) check needs a genuinely asymmetric
   shape or a single clear directional cue.
3. **Self-describing names.** Name each test object after exactly what
   it tests (e.g. `TEST_Y_AXIS`), so there's no ambiguity re-matching
   Spacer's vob list back to your prediction table.
4. **Write predictions down before looking at the result.** Compute
   both candidates' predicted values first (tables below already do
   this), so there's no risk of unconsciously reading the result as
   whichever one you expected.
5. **Position before rotation, always.** The rotation formula's
   correctness depends on which position candidate wins (see the
   correction above) - testing rotation first risks having to redo it.

### Phase 1: Position (resolves Candidate A vs. B)

Create three separate objects (e.g. `zCVobStartpoint`, via the Add VOB
dialog), each with exactly one non-zero Blender coordinate:

| Object name | Blender location | Tests |
|---|---|---|
| `TEST_X_AXIS` | `(5, 0, 0)` | `Gothic_X = Blender_X` (uncontested - sanity check) |
| `TEST_Y_AXIS` | `(0, 5, 0)` | **The actual open question** |
| `TEST_Z_AXIS` | `(0, 0, 5)` | `Gothic_Y = Blender_Z` (uncontested - sanity check) |

Export to an uncompiled ZEN (no compiling needed - Spacer can open and
display vob properties directly, as already done for every earlier test
in this project). Predicted `trafoOSToWSPos` for each:

| Object | Candidate A predicts | Candidate B predicts |
|---|---|---|
| `TEST_X_AXIS` | `500, 0, 0` | `500, 0, 0` (both agree) |
| `TEST_Y_AXIS` | `0, 0, -500` | `0, 0, +500` |
| `TEST_Z_AXIS` | `0, 500, 0` | `0, 500, 0` (both agree) |

**How to spot success/error:**
- `TEST_X_AXIS` or `TEST_Z_AXIS` NOT matching their (agreed) prediction
  means something is broken beyond this investigation - stop and
  re-check the export pipeline itself before going further.
- `TEST_Y_AXIS`'s third number is the entire answer: **-500 confirms
  Candidate A** (no code change needed), **+500 confirms Candidate B**
  (position formula needs the Z-sign fixed, and the rotation formula
  needs re-deriving per the correction above).

### Phase 2: Rotation (only run after Phase 1 is resolved)

Only proceed once Candidate A or B is confirmed - the correct rotation
formula depends on that answer, and testing rotation first risks wasted
work.

1. Create one more test object, rotated exactly **90 degrees about
   Blender's Z axis** (matching the original real-world bug report, so
   there's a known prior data point to sanity-check against) and
   nothing else - no position offset, no other rotation.
2. Export it. Before opening anything else, **decode the raw
   `trafoOSToWSRot` hex value directly** (the same `hex_to_float`/
   `decode_rotation_matrix_hex` functions already in
   `coordinate_transform.py` can do this) to get the exact resulting
   3x3 matrix as pure numbers - no Spacer needed for this numeric step.
3. Separately, open the export in Spacer (or, better, an actual
   in-game/compiled test if practical) and visually note which way the
   object's forward direction actually points, relative to the room/
   reference geometry.
4. Cross-reference: does the *numeric* matrix from step 2 correspond to
   a rotation that visually matches step 3's real-world observation?
   This closes the loop between pure math and observable behavior, which
   is what actually settles the rotation question - internal
   self-consistency (which the current formula already has, verified via
   round-trip export/import testing) is not the same as being correct
   against Gothic's real convention.

**How to spot success/error:** if the object visually faces the
direction implied by a proper +90 degree turn matching Blender's own
rotation direction (mentally compare: which way would this object face
if you'd rotated it +90 degrees in Blender and looked at it from
Blender's own default view), that's success. Facing the opposite way -
matching the original bug report exactly - is the error state; if that
happens even after Phase 1 and Phase 2 fixes, the rotation formula needs
the full re-derivation described in the correction above, not another
single sign flip.
