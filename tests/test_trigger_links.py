from zen_gin_export.trigger_links import trigger_link_pairs


class Vob:
    def __init__(self, name, **custom):
        self.name = name
        self._custom = custom

    def get(self, key, default=None):
        return self._custom.get(key, default)


def names(pairs):
    return sorted((a.name, b.name) for a, b in pairs)


def test_trigger_target_points_from_the_trigger_to_its_target():
    switch = Vob("oCMobSwitch:LEVER_01", trigger_target="gate_mover")
    mover = Vob("zCMover:GATE_MOVER")
    other = Vob("zCMover:OTHER")
    assert names(trigger_link_pairs([switch, mover, other])) == [
        ("oCMobSwitch:LEVER_01", "zCMover:GATE_MOVER")]


def test_list_targets_slaves_and_duplicate_names():
    trigger_list = Vob("zCTriggerList:LIST", list_target_0="A", list_target_2="B")
    a1, a2 = Vob("zCMover:A"), Vob("zCMover:A.001")          # Blender duplicate, same vob name
    b = Vob("zCTrigger:B", respond_to_vob_name="LIST")       # same pair again, once
    master = Vob("zCCodeMaster:MASTER", slave_0="B")
    pairs = names(trigger_link_pairs([trigger_list, a1, a2, b, master]))
    assert pairs == [
        ("zCTrigger:B", "zCCodeMaster:MASTER"),
        ("zCTriggerList:LIST", "zCMover:A"),
        ("zCTriggerList:LIST", "zCMover:A.001"),
        ("zCTriggerList:LIST", "zCTrigger:B"),
    ]


def test_objects_that_are_not_vobs_and_unknown_names_are_ignored():
    trigger = Vob("zCTrigger:T", trigger_target="NOWHERE")
    mesh = Vob("Cube", trigger_target="T")
    assert trigger_link_pairs([trigger, mesh]) == []
