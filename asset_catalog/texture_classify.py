"""Keyword-based texture -> material-category classifier for the Gothic
level texture set (see generate_material_catalog.py).

Pure Python, no bpy dependency, so the classification rules can be
inspected or unit tested independently of Blender.
"""

# Ordered rule tiers: earlier tiers win, and within a tier the first
# matching keyword wins. Keywords are matched as case-insensitive
# substrings against the texture's base filename (spaces normalized to
# underscores). This is a best-effort heuristic derived from the actual
# NewWorld/OldWorld filenames in TEXTURES/LEVELS, not a formal taxonomy -
# expect some assets to land in the wrong catalog. Reassign those by
# dragging them to a different catalog in Blender's Asset Browser.
RULES = [
    ("Water", ["water", "lake", "unterwater", "underwater", "welle"]),
    ("Ice_Snow", ["ice", "snow", "eis"]),
    ("Fire_Lava", ["fire", "lava", "volcano", "ember"]),
    ("Sand_Desert", ["sand", "desert", "wasteland", "dune"]),
    ("Stair", ["stair", "steps", "treppe"]),
    ("Roof", ["roof", "dach", "straw", "stroh"]),
    ("Door", ["door", "tuer", "gate", "tor"]),
    ("Window", ["window", "fenster"]),
    ("Brick", ["brick", "ziegel"]),
    ("Metal", ["iron", "metal", "chain", "kette", "wheel", "canon", "zaun",
                "shield"]),
    ("Fabric", ["carpet", "sail", "flag", "rope", "net", "cloth", "fahne"]),
    ("Furniture", ["bed", "table", "chair", "throne", "chest", "cupboard",
                    "stove", "shelf", "lamp", "barrel", "crate"]),
    ("Decal", ["decal", "blood", "spiderweb", "web"]),
    ("Ornament", ["statue", "ornament", "gravestone", "relief", "picture",
                   "sign", "totem", "flag"]),
    ("Ship", ["ship", "hull", "boat"]),
    ("Wood", ["wood", "holz", "bark", "plank", "beam", "fachwerk"]),
    ("Nature", ["nature", "tree", "leave", "leaf", "branch", "grass", "gras",
                 "bush", "plant", "flower", "farn", "moss", "ivy", "berry",
                 "root", "pilz", "cactus", "palm", "pine", "seerose",
                 "swamp", "acker", "weed", "bamboo", "bambus"]),
    ("Rock_Cave", ["rock", "fels", "stein", "boulder", "mountain", "cliff",
                    "canyon", "cave", "dungeon", "höhle", "mine", "ore"]),
    ("Ground", ["ground", "floor", "boden", "path", "weg", "trans",
                 "pflasterstein"]),
    ("Wall", ["wall", "mauer", "wand", "ceiling"]),
    ("Stone", ["stone"]),
]

FALLBACK = "Misc"

# Stable, ordered list of every category this classifier can produce -
# used to generate catalogs in a consistent order even for categories
# that end up with zero matches in a given run.
ALL_CATEGORIES = [name for name, _ in RULES] + [FALLBACK]


def classify(basename: str) -> str:
    name = basename.lower().replace(" ", "_")
    for category, keywords in RULES:
        for kw in keywords:
            if kw in name:
                return category
    return FALLBACK
