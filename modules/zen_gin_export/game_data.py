"""
Reads the names a level designer picks from - sounds, particle effects,
music themes, items, focus names, light presets, models, textures - out
of a Gothic II game folder, so the addon can offer them as dropdowns.

Sources, all under <game>/_work/Data (found case-insensitively):
  Scripts/System/SFX/*.d      INSTANCE X (C_SFX_DEF)          -> sounds
  Scripts/System/PFX/*.d      INSTANCE X (C_PARTICLEFX)       -> effects (X.PFX)
  Scripts/System/Music/*.d    INSTANCE XXX_Day_Std (C_MUSICTHEME...) -> zone suffixes
  Scripts/Content/**/*.d      C_Item / C_Npc instances, MOBNAME_* constants,
                              GIL_* guilds, <func>_S1 mob functions, EVT_* functions
  Presets/LightPresets.zen    light presets with their values
  Presets/Lensflare.zen       lensflare effects
  Meshes/_compiled/*.MRM      static meshes (X.3DS)
  Anims/_compiled/*.MDL|MDS   mob models (X.ASC / X.MDS), *.MMB -> X.MMS
  Textures/_compiled/*-C.TEX  textures (X.TGA)
  Worlds/*.ZEN                vob-tree templates (fire trees)

The Daedalus sources are read rather than the compiled .DAT files, so a
mod's own instances show up as soon as they are written. A game folder
with only .vdf archives (no unpacked _work/Data) simply yields empty
lists. Pure Python, no Blender dependency.
"""

import os
import re

from .archive_parser import parse_archive, read_archive_text

CATEGORIES = (
    "sfx", "pfx", "music_themes", "items", "keys", "npcs", "guilds", "focus_names",
    "mob_functions", "event_functions", "light_presets", "lensflares", "meshes",
    "mob_models", "morph_meshes", "textures", "vob_trees", "worlds",
)

_INSTANCE_RE = re.compile(
    r"^[ \t]*(?:instance|prototype)[ \t]+([^(/\n]+?)[ \t]*\([ \t]*(\w+)[ \t]*\)", re.I | re.M)
_CONST_STRING_RE = re.compile(r"^[ \t]*const[ \t]+string[ \t]+(MOBNAME_\w+)", re.I | re.M)
_CONST_GUILD_RE = re.compile(r"^[ \t]*const[ \t]+int[ \t]+(GIL_\w+)", re.I | re.M)
_FUNC_RE = re.compile(r"^[ \t]*func[ \t]+void[ \t]+(\w+)[ \t]*\([ \t]*\)", re.I | re.M)
_COMMENT_BLOCK_RE = re.compile(r"/\*.*?\*/", re.S)
_COMMENT_LINE_RE = re.compile(r"//[^\n]*")
_MUSIC_THEME_RE = re.compile(r"^(\w+?)_(?:DAY|NGT)_(?:STD|THR|FGT)$", re.I)
_GUILD_SKIP = ("GIL_SEPERATOR", "GIL_MAX", "GIL_PUBLIC")


def _child(directory, name):
    """directory/name, matching name case-insensitively (game folders mix
    Sound/SOUND, Content/CONTENT); None if missing."""
    if directory is None:
        return None
    exact = os.path.join(directory, name)
    if os.path.exists(exact):
        return exact
    try:
        for entry in os.listdir(directory):
            if entry.lower() == name.lower():
                return os.path.join(directory, entry)
    except OSError:
        pass
    return None


def _path(root, *parts):
    for part in parts:
        root = _child(root, part)
    return root


def find_data_dir(game_folder):
    """<game>/_work/Data for a game folder, a _work folder or the Data
    folder itself; None if there is none."""
    if not game_folder or not os.path.isdir(game_folder):
        return None
    for parts in (("_work", "Data"), ("Data",), ()):
        candidate = _path(game_folder, *parts)
        if candidate and _child(candidate, "Scripts") or candidate and _child(candidate, "Worlds"):
            return candidate
    return None


def _read(path):
    try:
        with open(path, "r", encoding="windows-1250", errors="replace") as f:
            text = f.read()
    except OSError:
        return ""
    return _COMMENT_LINE_RE.sub("", _COMMENT_BLOCK_RE.sub("", text))


def _script_files(directory):
    if not directory:
        return
    for root, _dirs, files in os.walk(directory):
        for filename in sorted(files):
            if filename.lower().endswith(".d"):
                yield os.path.join(root, filename)


def _instances(text):
    """[(instance name, class)] - `instance A, B (C_X)` declares both."""
    for names, class_name in _INSTANCE_RE.findall(text):
        for name in names.split(","):
            name = name.strip()
            if re.fullmatch(r"\w+", name):
                yield name, class_name.upper()


def _files_with_extension(directory, extensions, suffix=""):
    """Upper-case stems of the files in directory with one of extensions,
    with `suffix` stripped from the stem's end."""
    stems = set()
    if not directory:
        return stems
    try:
        entries = os.listdir(directory)
    except OSError:
        return stems
    for entry in entries:
        stem, ext = os.path.splitext(entry)
        if ext.upper() in extensions:
            stem = stem.upper()
            if suffix and stem.endswith(suffix):
                stem = stem[:-len(suffix)]
            stems.add(stem)
    return stems


def _unique_sorted(names):
    seen = {}
    for name in names:
        seen.setdefault(name.upper(), name)
    return [seen[key] for key in sorted(seen)]


def read_light_presets(path):
    """{preset name: {archive property: string value}} from LightPresets.zen."""
    presets = {}
    if not path:
        return presets
    try:
        roots = parse_archive(read_archive_text(path))
    except OSError:
        return presets
    for block in roots:
        name = block.get("presetName", "").strip()
        if name:
            presets[name] = dict(block.properties)
    return presets


def _walk(blocks):
    for block in blocks:
        yield block
        yield from _walk(block.children)


def _preset_names(path, class_name, property_name):
    """property_name of every `class_name` block in a preset archive."""
    names = []
    if path:
        try:
            for block in _walk(parse_archive(read_archive_text(path))):
                value = block.get(property_name, "").strip()
                if block.type2 == class_name and value:
                    names.append(value)
        except OSError:
            pass
    return names


class GameIndex:
    """The pickable names of one game folder. Every category is a sorted
    list of strings; light_preset_values holds the presets' settings."""

    def __init__(self, game_folder=None):
        self.game_folder = game_folder
        self.data_dir = find_data_dir(game_folder)
        self.light_preset_values = {}
        for category in CATEGORIES:
            setattr(self, category, [])
        if self.data_dir:
            self._scan()

    @property
    def found(self):
        return self.data_dir is not None

    def counts(self):
        return {category: len(getattr(self, category)) for category in CATEGORIES}

    def _scan(self):
        data = self.data_dir
        system = _path(data, "Scripts", "System")

        sfx = []
        for path in _script_files(_child(system, "SFX")):
            if "speech" in os.path.basename(path).lower():
                continue
            sfx += [name for name, cls in _instances(_read(path)) if cls == "C_SFX_DEF"]
        # FOO_A1, FOO_A2 are random variations the engine picks for FOO.
        self.sfx = _unique_sorted(n for n in sfx if not re.search(r"_A\d+$", n, re.I))

        pfx = []
        for path in _script_files(_child(system, "PFX")):
            pfx += [name for name, cls in _instances(_read(path)) if cls == "C_PARTICLEFX"]
        self.pfx = _unique_sorted(f"{name.upper()}.PFX" for name in pfx)

        themes = []
        for path in _script_files(_child(system, "Music")):
            for name, _cls in _instances(_read(path)):
                match = _MUSIC_THEME_RE.match(name)
                if match:
                    themes.append(match.group(1).upper())
        self.music_themes = _unique_sorted(themes)

        items, npcs, focus, guilds, mob_funcs, event_funcs = [], [], [], [], [], []
        for path in _script_files(_path(data, "Scripts", "Content")):
            text = _read(path)
            lowered = text.lower()
            if "instance" in lowered or "prototype" in lowered:
                for name, cls in _instances(text):
                    if cls == "C_ITEM":
                        items.append(name)
                    elif cls in ("C_NPC", "NPC_DEFAULT"):
                        npcs.append(name)
            if "mobname_" in lowered:
                focus += _CONST_STRING_RE.findall(text)
            if "gil_" in lowered:
                guilds += [g for g in _CONST_GUILD_RE.findall(text) if g.upper() not in _GUILD_SKIP]
            if "_s1" in lowered or "evt_" in lowered:
                for name in _FUNC_RE.findall(text):
                    if name.upper().endswith("_S1"):
                        mob_funcs.append(name[:-3])
                    elif name.upper().startswith("EVT_"):
                        event_funcs.append(name)
        self.items = _unique_sorted(items)
        self.keys = [name for name in self.items if name.upper().startswith("ITKE_")]
        self.npcs = _unique_sorted(npcs)
        self.focus_names = _unique_sorted(focus)
        self.guilds = _unique_sorted(guilds)
        self.mob_functions = _unique_sorted(mob_funcs)
        self.event_functions = _unique_sorted(event_funcs)

        presets = _child(data, "Presets")
        self.light_preset_values = read_light_presets(_child(presets, "LightPresets.zen"))
        self.light_presets = sorted(self.light_preset_values, key=str.upper)
        self.lensflares = _unique_sorted(_preset_names(_child(presets, "Lensflare.zen"), "zCLensFlareFX", "name"))

        self.meshes = sorted(
            f"{stem}.3DS" for stem in _files_with_extension(_path(data, "Meshes", "_compiled"), {".MRM"}))
        anims = _path(data, "Anims", "_compiled")
        # A model with a script (.MSB) is usable as X.MDS and, like any
        # compiled model (.MDL), as X.ASC - vanilla worlds use both.
        # Scripts of interactive objects have their sources in Anims/mds_mobsi;
        # the other compiled scripts are creatures and humans. Without that
        # folder (no sources installed) all of them are listed.
        scripts = _files_with_extension(anims, {".MSB"})
        mob_scripts = {stem.upper() for stem in _files_with_extension(_path(data, "Anims", "mds_mobsi"), {".MDS"})}
        if mob_scripts:
            scripts = [stem for stem in scripts if stem.upper() in mob_scripts]
        models = {f"{stem}.MDS" for stem in scripts}
        models |= {f"{stem}.ASC" for stem in _files_with_extension(anims, {".MDL"})}
        self.mob_models = sorted(models)
        self.morph_meshes = sorted(f"{stem}.MMS" for stem in _files_with_extension(anims, {".MMB"}))
        self.textures = sorted(
            f"{stem}.TGA" for stem in _files_with_extension(_path(data, "Textures", "_compiled"), {".TEX"}, "-C"))

        worlds = _child(data, "Worlds")
        self.vob_trees = sorted(f"{stem}.ZEN" for stem in _files_with_extension(worlds, {".ZEN"}))
        level_files = []
        if worlds:
            for root, _dirs, files in os.walk(worlds):
                relative = os.path.relpath(root, worlds)
                for filename in files:
                    if filename.lower().endswith(".zen") and relative != ".":
                        level_files.append(f"{relative}\\{filename}".replace("/", "\\"))
        self.worlds = sorted(level_files, key=str.upper)
