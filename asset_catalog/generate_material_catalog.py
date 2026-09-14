"""Generate a Blender material asset library from the Gothic II level
textures in GothicBlenderAssets-master/TEXTURES/LEVELS/{NewWorld,OldWorld}.

For each texture: creates a material (Image Texture -> Principled BSDF
Base Color, plus Alpha if the texture has one), marks it as a Blender
asset, and files it into a catalog based on a keyword guess at its
material type (wood/stone/roof/nature/etc. - see texture_classify.py).

Run headless from this repo's asset_catalog/ directory:

    blender --background --python generate_material_catalog.py

(On Windows: "C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe")

Produces materials_levels.blend and blender_assets.cats.txt next to this
script. Add asset_catalog/ as an Asset Library in Blender's Preferences >
File Paths > Asset Libraries to browse the result.

Texture images are linked, not packed, from their location on disk at
generation time (see TEXTURE_ROOT below) - the .blend stays small, but
depends on that path still existing. TEXTURE_ROOT defaults to the
GothicBlenderAssets-master checkout that's expected to sit next to this
repo (both under the same parent directory); override it with the
GOTHIC_TEXTURE_ROOT environment variable if your layout differs. If a
previously-generated .blend has broken links (e.g. after moving either
checkout, or after copying the .blend to a different machine), just
rerun this script rather than using Blender's File > External Data >
Find Missing Files - it relinks everything from a known-good root.

Preview thumbnails are intentionally NOT generated here (headless preview
rendering is unreliable / needs a display). After opening the result,
select all assets in the Asset Browser and use "Generate Previews" from
the context menu.
"""
import os
import sys
import uuid

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from texture_classify import classify, ALL_CATEGORIES  # noqa: E402

OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_BLEND = os.path.join(OUTPUT_DIR, "materials_levels.blend")
OUTPUT_CATS = os.path.join(OUTPUT_DIR, "blender_assets.cats.txt")

# This script normally lives at <parent>/Blend-Zen/asset_catalog/, with the
# texture checkout as a sibling repo at <parent>/GothicBlenderAssets-master/.
# Three levels up from this file's directory is <parent>.
_DEFAULT_ASSETS_PARENT = os.path.dirname(
    os.path.dirname(os.path.dirname(OUTPUT_DIR))
)
TEXTURE_ROOT = os.environ.get(
    "GOTHIC_TEXTURE_ROOT",
    os.path.join(
        _DEFAULT_ASSETS_PARENT, "GothicBlenderAssets-master", "TEXTURES", "LEVELS"
    ),
)
SUBFOLDERS = ["NewWorld", "OldWorld"]


def find_textures():
    """Yield (subfolder, absolute_path) for every .tga under SUBFOLDERS."""
    for sub in SUBFOLDERS:
        root = os.path.join(TEXTURE_ROOT, sub)
        for dirpath, _dirnames, filenames in os.walk(root):
            for fn in filenames:
                if fn.lower().endswith(".tga"):
                    yield sub, os.path.join(dirpath, fn)


def _load_existing_uuids():
    """Read {category: uuid_str} from a prior OUTPUT_CATS, if any.

    Keeping catalog UUIDs stable across regenerations means the merged
    copy of this file in Blender_Asset_Library_Gothic/blender_assets.cats.txt
    doesn't need to be re-synced every time this script reruns.
    """
    if not os.path.exists(OUTPUT_CATS):
        return {}
    existing = {}
    with open(OUTPUT_CATS, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("VERSION"):
                continue
            parts = line.split(":")
            if len(parts) >= 2:
                existing[parts[1]] = parts[0]
    return existing


def build_catalogs():
    """Return {category: uuid_str} and the cats.txt file content."""
    existing = _load_existing_uuids()
    cat_uuids = {
        name: existing.get(name, str(uuid.uuid4())) for name in ALL_CATEGORIES
    }
    lines = [
        "# This is an Asset Catalog Definition file for Blender.",
        "#",
        "# Empty lines and lines starting with `#` will be ignored.",
        "# The first non-ignored line should be the version indicator.",
        "# Other lines are of the format \"UUID:catalog tree path:simple catalog name\"",
        "",
        "VERSION 1",
        "",
    ]
    for name in ALL_CATEGORIES:
        lines.append(f"{cat_uuids[name]}:{name}:{name}")
    return cat_uuids, "\n".join(lines) + "\n"


def make_material(name, image_path, subfolder, catalog_uuid):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf = nodes.get("Principled BSDF")
    if bsdf is None:
        bsdf = nodes.new("ShaderNodeBsdfPrincipled")

    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.location = (bsdf.location.x - 350, bsdf.location.y)

    image = bpy.data.images.load(image_path, check_existing=True)
    tex_node.image = image

    links.new(tex_node.outputs["Color"], bsdf.inputs["Base Color"])

    if image.depth == 32 or image.channels == 4:
        links.new(tex_node.outputs["Alpha"], bsdf.inputs["Alpha"])
        try:
            mat.blend_method = "CLIP"
        except (AttributeError, TypeError):
            pass
        try:
            mat.surface_render_method = "DITHERED"
        except (AttributeError, TypeError):
            pass

    mat.asset_mark()
    mat.asset_data.catalog_id = catalog_uuid
    mat.asset_data.description = f"{subfolder}/{name}.tga"
    try:
        mat.asset_data.tags.new("gothic-level")
        mat.asset_data.tags.new(subfolder)
    except (AttributeError, RuntimeError):
        pass

    return mat


def main():
    if not os.path.isdir(TEXTURE_ROOT):
        raise SystemExit(
            f"TEXTURE_ROOT does not exist: {TEXTURE_ROOT}\n"
            "Set the GOTHIC_TEXTURE_ROOT environment variable to the "
            "GothicBlenderAssets-master/TEXTURES/LEVELS directory on this "
            "machine, e.g.:\n"
            '  GOTHIC_TEXTURE_ROOT="/path/to/TEXTURES/LEVELS" blender '
            "--background --python generate_material_catalog.py"
        )

    bpy.ops.wm.read_factory_settings(use_empty=True)

    cat_uuids, cats_txt = build_catalogs()

    counts = {}
    total = 0
    for subfolder, path in find_textures():
        base = os.path.splitext(os.path.basename(path))[0]
        category = classify(base)
        make_material(base, path, subfolder, cat_uuids[category])
        counts[category] = counts.get(category, 0) + 1
        total += 1

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_CATS, "w", encoding="utf-8") as f:
        f.write(cats_txt)

    bpy.ops.wm.save_as_mainfile(filepath=OUTPUT_BLEND)

    print(f"Generated {total} materials across {len(counts)} catalogs:")
    for cat in ALL_CATEGORIES:
        if cat in counts:
            print(f"  {cat}: {counts[cat]}")
    print(f"Saved: {OUTPUT_BLEND}")
    print(f"Saved: {OUTPUT_CATS}")


if __name__ == "__main__":
    main()
