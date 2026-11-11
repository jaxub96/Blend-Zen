from zen_gin_export import vob_fields as vf
from zen_gin_export.vanilla_survey import visual_defaults, unused_fields, normalize_visual
from zen_gin_export.visual_rules import visuals_for

SURVEY = {
    "oCMobContainer": ["CHESTBIG_NW_RICH_LOCKED.MDS", "CHESTBIG_NW_RICH_LOCKED.ASC"],
    "oCMobDoor": ["BEDHIGH_NW_NORMAL_01.ASC", "DOOR_WOODEN.MDS"],
    "oCMobInter": ["CHAIR_NW_NORMAL_01.ASC", "RMAKER_1.MDS"],
    "oCMobFire": ["FIREPLACE_HIGH2.ASC", "OC_BIGLIGHTER_01.3DS"],
    "oCMOB": ["NW_MISC_SIGN_01.3DS"],
}
MODELS = [
    "CHESTBIG_NW_RICH_LOCKED.MDS", "CHESTBIG_NW_RICH_LOCKED.ASC", "CHESTSMALL_MOD.MDS", "CHESTSMALL_MOD.ASC",
    "DOOR_WOODEN.MDS", "DOOR_WOODEN.ASC", "BEDHIGH_NW_NORMAL_01.ASC", "BED_1_OC.ASC",
    "CHAIR_NW_NORMAL_01.ASC", "CHAIR_1_OC.ASC", "RMAKER_1.MDS", "RMAKER_1.ASC", "ARMOR_BODY.ASC",
    "FIREPLACE_HIGH2.ASC", "FIREPLACE_HIGH2.MDS", "LEVER_1_OC.MDS",
]
MESHES = ["A_ROCK.3DS", "NW_MISC_SIGN_01.3DS"]


def test_chests_and_doors_offer_only_their_model_scripts():
    assert visuals_for("oCMobContainer", MODELS, MESHES, SURVEY) == [
        "CHESTBIG_NW_RICH_LOCKED.MDS", "CHESTSMALL_MOD.MDS"]
    assert visuals_for("oCMobDoor", MODELS, MESHES, SURVEY) == ["DOOR_WOODEN.MDS"]
    assert visuals_for("oCMobSwitch", MODELS, MESHES, SURVEY) == ["LEVER_1_OC.MDS"]


def test_beds_and_chairs_offer_plain_models():
    assert visuals_for("oCMobBed", MODELS, MESHES, SURVEY) == ["BEDHIGH_NW_NORMAL_01.ASC", "BED_1_OC.ASC"]
    generic = visuals_for("oCMobInter", MODELS, MESHES, SURVEY)
    assert generic == ["CHAIR_NW_NORMAL_01.ASC", "RMAKER_1.MDS", "CHAIR_1_OC.ASC"]


def test_a_model_in_both_forms_keeps_the_one_vanilla_uses():
    assert visuals_for("oCMobFire", MODELS, MESHES, SURVEY) == ["FIREPLACE_HIGH2.ASC", "OC_BIGLIGHTER_01.3DS"]


def test_static_classes_offer_meshes_vanilla_first_and_other_types_have_no_rule():
    assert visuals_for("oCMOB", MODELS, MESHES, SURVEY) == ["NW_MISC_SIGN_01.3DS", "A_ROCK.3DS"]
    assert visuals_for("zCVob", MODELS, MESHES, SURVEY) is None


def test_a_prop_takes_its_visuals_vanilla_settings_as_defaults():
    grass = "NW_NATURE_GRASSGROUP_01"
    assert normalize_visual(grass) == "NW_NATURE_GRASSGROUP_01.3DS"
    assert visual_defaults("zCVob", grass)["ani_mode"] == "WIND2"
    assert vf.base_default("zCVob", "cd_dyn", grass) is False
    assert vf.base_default("zCVob", "cd_dyn") is True                 # a plain prop collides
    assert vf.base_default("zCVob", "cd_dyn", "SOME_NEW_MESH") is True
    assert visual_defaults("oCMOB", grass) == {}                      # props only


def test_import_keeps_a_value_that_differs_from_the_visuals_default():
    block = {"visual": "NW_NATURE_GRASSGROUP_01.3DS", "cdDyn": "1", "visualAniMode": "2",
             "visualAniModeStrength": "0.001"}
    custom = vf.custom_properties_from_block("zCVob", block)
    assert custom.get("cd_dyn") is True          # vanilla grass does not collide; this one does
    assert "ani_mode" not in custom              # same as the visual's default


def test_fields_vanilla_never_changes():
    assert "hitpoints" in unused_fields("oCMobContainer")
    assert "locked" not in unused_fields("oCMobContainer")
    assert unused_fields("zCVobSpot") == frozenset()
