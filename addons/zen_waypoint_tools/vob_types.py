import bpy


VOB_TYPE_ITEMS = (
    ('zCVobLevelCompo', "Level Compo (World Mesh Ref)",
     "Reference to the compiled level mesh - name must match the .3ds filename, without extension"),
    ('zCVobStartpoint', "Startpoint",
     "Player/NPC start position"),
    ('zCVob', "Vob (Mesh Prop)",
     "Generic static prop - name must match its .3ds mesh filename, without extension"),
    ('zCVobSpot', "Vob Spot (Freepoint)",
     "Freepoint used by NPCs during TA_Stand_* routines"),
    ('oCItem', "Item",
     "Pickupable item - name must match the item's script instance name"),
    ('zCVobLight', "Light",
     "Point or spot light source. Tune range/color/type via Custom Properties on the created empty"),
    ('zCVobSound', "Sound",
     "Sound source - name must match the sound's script instance name"),
)

VOB_DISPLAY = {
    'zCVobLevelCompo': ('PLAIN_AXES', 1.0),
    'zCVobStartpoint': ('PLAIN_AXES', 0.5),
    'zCVob': ('SPHERE', 0.2),
    'zCVobSpot': ('ARROWS', 0.25),
    'oCItem': ('CUBE', 0.2),
    'zCVobLight': ('CONE', 0.3),
    'zCVobSound': ('SPHERE', 1.0),
}

VOB_DEFAULT_LABEL = {
    'zCVobLevelCompo': "LEVEL",
    'zCVobStartpoint': "START",
    'zCVob': "PROP",
    'zCVobSpot': "FREEPOINT",
    'oCItem': "ITEM",
    'zCVobLight': "LIGHT",
    'zCVobSound': "SOUND",
}


def find_next_vob_name(vob_type):
    """Generic name generator, mirrors find_next_waypoint_name() in waypoint_links.py."""
    label = VOB_DEFAULT_LABEL.get(vob_type, "VOB")
    prefix = f"{vob_type}:{label}_"

    existing_numbers = set()
    for obj in bpy.data.objects:
        if not obj.name.startswith(prefix):
            continue
        suffix = obj.name[len(prefix):].split(".")[0]
        if suffix.isdigit():
            existing_numbers.add(int(suffix))

    next_num = 1
    while next_num in existing_numbers:
        next_num += 1

    return f"{label}_{next_num:03d}"
