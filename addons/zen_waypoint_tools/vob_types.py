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
     "Point or spot light source. Created as a real Blender Light - tune "
     "range/color/type in Blender's own Light Properties tab"),
    ('zCVobSound', "Sound",
     "Sound source - name must match the sound's script instance name"),
    ('oCMobContainer', "Interactive: Container",
     "Lootable chest/barrel/sack - name is this instance's unique vobName, "
     "not its mesh. Configure via Custom Properties after adding - see "
     "documentation/USAGE_interactive_objects.md"),
    ('oCMobDoor', "Interactive: Door",
     "A door - name is this instance's unique vobName, not its mesh. "
     "Configure via Custom Properties after adding"),
    ('oCMobBed', "Interactive: Bed",
     "A sleepable bed - name is this instance's unique vobName, not its "
     "mesh. Configure via Custom Properties after adding"),
    ('oCMobSwitch', "Interactive: Switch",
     "A two-state switch/lever - name is this instance's unique vobName, "
     "not its mesh. Configure via Custom Properties after adding"),
    ('oCMobLadder', "Interactive: Ladder",
     "A climbable ladder - name is this instance's unique vobName, not "
     "its mesh. Configure via Custom Properties after adding"),
    ('oCMobWheel', "Interactive: Wheel",
     "A four-state rotating wheel mechanism - name is this instance's "
     "unique vobName, not its mesh. Configure via Custom Properties after adding"),
    ('oCMobFire', "Interactive: Fire",
     "A usable fire source (campfire/forge) - name is this instance's "
     "unique vobName, not its mesh. Configure via Custom Properties after adding"),
    ('oCMobInter', "Interactive: Generic",
     "Generic interactive object for anything that doesn't fit the more "
     "specific types above - name is this instance's unique vobName, not "
     "its mesh. Configure via Custom Properties after adding"),
)

VOB_DISPLAY = {
    'zCVobLevelCompo': ('PLAIN_AXES', 1.0),
    'zCVobStartpoint': ('PLAIN_AXES', 2.0),
    'zCVob': ('SPHERE', 0.5),
    'zCVobSpot': ('ARROWS', 1.2),
    'oCItem': ('CUBE', 0.3),
    'zCVobLight': ('CONE', 0.3),
    'zCVobSound': ('SPHERE', 1.0),
    'oCMobContainer': ('CUBE', 0.5),
    'oCMobDoor': ('CUBE', 0.4),
    'oCMobBed': ('CUBE', 0.6),
    'oCMobSwitch': ('CONE', 0.25),
    'oCMobLadder': ('PLAIN_AXES', 1.5),
    'oCMobWheel': ('CIRCLE', 0.5),
    'oCMobFire': ('SPHERE', 0.3),
    'oCMobInter': ('CUBE', 0.4),
}

VOB_DEFAULT_LABEL = {
    'zCVobLevelCompo': "LEVEL",
    'zCVobStartpoint': "PC_START",
    'zCVob': "PROP",
    'zCVobSpot': "FREEPOINT",
    'oCItem': "ITEM",
    'zCVobLight': "LIGHT",
    'zCVobSound': "SOUND",
    'oCMobContainer': "CHEST",
    'oCMobDoor': "DOOR",
    'oCMobBed': "BED",
    'oCMobSwitch': "SWITCH",
    'oCMobLadder': "LADDER",
    'oCMobWheel': "WHEEL",
    'oCMobFire': "FIRE",
    'oCMobInter': "INTERACTIVE",
}


def find_next_vob_name(vob_type):
    """Generic name generator, mirrors find_next_waypoint_name() in waypoint_links.py."""
    label = VOB_DEFAULT_LABEL.get(vob_type, "VOB")
    prefix = f"{vob_type}:{label}_"
    if vob_type == "zCVobStartpoint":
        return label
    
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
