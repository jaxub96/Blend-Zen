import bpy

from .vob_ui_schema import VOB_TYPE_INFO, type_info, split_type_id

# zCVob (mesh props) and oCItem (items) are deliberately absent from the Add
# VOB dialog: they are placed by dragging real assets in from the Props.blend
# / Items_*.blend asset libraries, which already carry the right name.
VOB_TYPE_ITEMS = tuple(
    (type_id, label, description) for type_id, (label, description, *_rest) in VOB_TYPE_INFO.items()
)


def vob_display(vob_type_id):
    """(empty display type, display size) for a vob type or variant id."""
    info = type_info(vob_type_id)
    return (info[2], info[3]) if info else ('PLAIN_AXES', 0.3)


def default_box_size(vob_type_id):
    info = type_info(vob_type_id)
    return info[5] if info else None


def find_next_vob_name(vob_type_id):
    """Suggested name for a new vob: the type's label, numbered."""
    info = type_info(vob_type_id)
    label = info[4] if info else "VOB"
    vob_type, _ = split_type_id(vob_type_id)
    if vob_type == "zCVobStartpoint":
        return label
    if vob_type in ("oCZoneMusic", "oCZoneMusicDefault"):
        return f"{label}_DEF"       # <PLACE>_<THEME>; DEF is the vanilla default theme

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
    return f"{label}_{next_num:02d}" if label.startswith("FP_") else f"{label}_{next_num:03d}"
