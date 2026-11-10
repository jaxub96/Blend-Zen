from .vob_fields import VOB_SPECS
from .zen_gin_zcvob import ZCVob, vob_type_of
from .zen_gin_zcvob_light import ZCVobLight

# Vob type (the Blender name prefix before the first ":") -> vob class.
VOB_CLASSES = {
    vob_type: type(f"Vob_{vob_type}", (ZCVob,), {"_vob_type": vob_type})
    for vob_type in VOB_SPECS
}
VOB_CLASSES["zCVob"] = ZCVob
VOB_CLASSES["zCVobLight"] = ZCVobLight


def vob_class_for(blender_object):
    """The vob class for an object's name prefix, or None (not exported)."""
    vob_type = vob_type_of(blender_object)
    return VOB_CLASSES[vob_type] if vob_type else None


class _Node:
    def __init__(self, vob):
        self.vob = vob
        self.children = []


class OCVobTree:
    """The VobTree block. Blender parenting is the vob hierarchy: a vob
    whose nearest exported vob ancestor is P is written as P's child (a
    torch with its flame, light and sound). Siblings are grouped by type
    (level compo first, then props/mobs/lights, items, freepoints, sounds).

    Format: `childsN=int:count` after node N-1's block says how many of the
    following vobs are its children; node 0 is the implicit root.
    """

    def __init__(self, blender_objects, data_printer):
        self._data_printer = data_printer
        nodes = {}
        for obj in blender_objects:
            vob_class = vob_class_for(obj)
            if vob_class is not None:
                nodes[id(obj)] = _Node(vob_class(obj, data_printer))

        self._roots = []
        for obj in blender_objects:
            node = nodes.get(id(obj))
            if node is None:
                continue
            parent = getattr(obj, "parent", None)
            while parent is not None and id(parent) not in nodes:
                parent = getattr(parent, "parent", None)
            (nodes[id(parent)].children if parent is not None else self._roots).append(node)

        self._nodes = list(nodes.values())
        for siblings in [self._roots] + [n.children for n in self._nodes]:
            siblings.sort(key=lambda n: n.vob._spec.order)     # stable: keeps scene order

    def objects_count(self):
        return sum(node.vob._objects_count for node in self._nodes)

    def print(self, object_index):
        p = self._data_printer
        p.start_object_block(type_1="VobTree")
        p.print_int_property("childs0", len(self._roots))
        counter = 1
        # Depth-first, without recursion (deep parent chains are legal).
        stack = list(reversed(self._roots))
        while stack:
            node = stack.pop()
            object_index = node.vob.print(object_index)
            p.print_int_property(f"childs{counter}", len(node.children))
            counter += 1
            stack.extend(reversed(node.children))
        p.end_object_block()
        return object_index
