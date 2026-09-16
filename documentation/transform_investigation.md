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
   backwards), with no independent source at all. Flagged as such in
   the code comments at the time.

## What this session found: a real, unresolved disagreement

Read KrxImpExp's own `KrxMshImp.py` (`zenginWorldLoader.__read_vertices`)
- the code that reads a **compiled** world mesh's raw vertex chunk back
into Blender:

```python
def __read_vertices(self):
    ...
    for i in range(0, len(verts_pos), 3):
        x, z, y = verts_pos[i : i + 3]
        x *= self.__scale_coef
        z *= self.__scale_coef
        y *= self.__scale_coef
        self.__current_mesh.verts.append([x, y, z])
```

Calling the three floats stored in the file `field0, field1, field2` (in
that order), this code produces `Blender = [field0, field2, field1]`,
i.e. `Blender_X = field0`, `Blender_Y = field2`, `Blender_Z = field1`.

**Assuming** the file stores its floats in Gothic's own native
`(X, Y, Z)` order (a reasonable assumption, not proven by this code
alone), inverting gives:

```
Gothic_X = Blender_X   <- agrees with current code
Gothic_Y = Blender_Z   <- agrees with current code
Gothic_Z = Blender_Y   <- DISAGREES: current code says -Blender_Y
```

X and Y match. **Z is a real, direct contradiction.**

### Dead end checked and ruled out: `Krx3dsExp.py`

Hoped this would give an independent check via a fresh `.3ds` export,
but its vertex writer does this:

```python
vert = vert @ self._current_data["transform"]
self.__file.WriteFloat(vert.x * self.__scale_coef)
self.__file.WriteFloat(vert.y * self.__scale_coef)
self.__file.WriteFloat(vert.z * self.__scale_coef)
```

Writes Blender's raw x/y/z with **zero axis conversion**. `.3ds` is a
generic, Gothic-agnostic interchange format - the real Blender->Gothic
conversion only happens later, inside Spacer's own compiler. A fresh
`.3ds` export can't answer this question; ruled out, don't retry it.

## Real data already extracted, ready to finish the comparison

Using the compiled `LEVEL_001_COMP.ZEN` you uploaded earlier (from the
"can we compile without Spacer" investigation), its `0xB030 VERTICES`
chunk (file offset 9005, 48 vertices) decodes to real, clean-number
room geometry - clearly the `exports/LEVEL_001.blend` source mesh,
compiled by Spacer. `field1`'s range (-30, 0, 300, 330) is obviously a
floor-to-ceiling height, confirming it's the vertical axis as expected.

A representative non-symmetric vertex to check:

```
vertex 30: field0=415.0  field1=300.0  field2=430.0
```

## The exact test to run on Mac

1. Open `exports/LEVEL_001.blend`.
2. Find the real mesh vertex whose Blender **X** is close to `4.15` and
   whose Blender **Z** is close to `3.00` (dividing the field0/field1
   values above by the 100 scale).
3. Read that vertex's Blender **Y**, multiply by 100.
   - Result **+430** -> current formula's negation on Z is wrong, needs
     fixing.
   - Result **-430** -> current formula is correct as-is, no change.

Full decoded vertex list (all 48, for cross-checking more than one
point if the first one is ambiguous e.g. due to symmetry):

```
0:  (-400, 330, 400)    1:  (400, 330, -400)   2:  (400, 330, 400)
3:  (-400, 330, -400)   4:  (430, 300, 415)    5:  (430, 0, 415)
6:  (430, 0, -415)      7:  (430, 300, -415)   8:  (400, 300, -415)
9:  (400, 0, 415)       10: (400, 0, -415)     11: (400, 300, 415)
12: (415, 0, 400)       13: (-415, 0, 430)     14: (-415, 0, 400)
15: (415, 0, 430)       16: (415, 300, 400)    17: (-415, 300, 400)
18: (-400, 0, -400)     19: (400, 0, -400)     20: (-400, 0, 400)
21: (400, 0, 400)       22: (-400, -30, 400)   23: (-400, -30, -400)
24: (400, -30, 400)     25: (400, -30, -400)   26: (400, 300, 400)
27: (400, 300, -400)    28: (-400, 300, 400)   29: (-400, 300, -400)
30: (415, 300, 430)     31: (-415, 300, 430)   32: (-430, 0, 415)
33: (-400, 300, 415)    34: (-400, 0, 415)     35: (-430, 300, 415)
36: (-430, 0, -415)     37: (-430, 300, -415)  38: (-400, 300, -415)
39: (-400, 0, -415)     40: (415, 0, -400)     41: (415, 0, -430)
42: (-415, 0, -400)     43: (-415, 0, -430)    44: (415, 300, -430)
45: (-415, 300, -430)   46: (415, 300, -400)   47: (-415, 300, -400)
```
(each row: `field0, field1, field2`)

## Important: this isn't just "one sign to flip" if Z turns out wrong

If the test shows `Gothic_Z = +Blender_Y` (no negation), that changes
the position transform's determinant from +1 to **-1** under a
right-handed assumption for both systems - meaning either:

- Gothic is actually **left-handed**, and a plain axis swap with no
  extra sign flip is the *correct*, shape-preserving conversion (in
  which case the "generic Verge3D formula" assumption that started this
  whole investigation was wrong to apply here), or
- something else is different between how compiled mesh vertices and
  vob positions are stored (less likely, but not ruled out).

Either way, **the rotation-quaternion formula would need re-deriving
from scratch**, not just a sign tweak - it was built assuming the
current (det=+1, right-handed-preserving) position matrix, using
conjugation logic specific to that assumption. A different position
matrix needs the rotation formula re-derived to match it, the same way
`blender_quaternion_to_gothic()` was originally derived to match
`blender_position_to_gothic()`.

## Bottom line

- X and Y axis mappings: solid, corroborated by an independent source,
  not in question.
- Z axis sign: genuinely unresolved, real contradicting evidence now
  exists, resolvable with one concrete Mac-side check (above).
- Rotation direction: separately unresolved, weakest evidence in the
  project, and its correctness is entangled with whatever the Z-axis
  answer turns out to be.
