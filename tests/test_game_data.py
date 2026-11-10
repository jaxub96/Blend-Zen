"""The game-files bridge on a miniature game folder."""

from modules.zen_gin_export.game_data import GameIndex, find_data_dir


def _write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="windows-1250")


def _game(tmp_path):
    data = tmp_path / "_work" / "Data"
    _write(data / "Scripts" / "System" / "SFX" / "SfxInst.d", """
        INSTANCE TORCH_BURN (C_SFX_DEF) {file="torch.wav"; vol=100;};
        instance   OW_Crow,OW_Crow_A1 (C_SFX_DEF) {};
        // INSTANCE COMMENTED_OUT (C_SFX_DEF) {};
        /* INSTANCE ALSO_OUT (C_SFX_DEF) {}; */
    """)
    _write(data / "Scripts" / "System" / "SFX" / "SfxInstSpeech.d", "INSTANCE SVM_1_Hi (C_SFX_DEF) {};")
    _write(data / "Scripts" / "System" / "PFX" / "PfxInst.d",
           "INSTANCE Fire (C_PARTICLEFX) {};\nINSTANCE Proto (C_ParticleFXProto) {};")
    _write(data / "Scripts" / "System" / "Music" / "MusicInst.d", """
        INSTANCE XAR_Day_Std (C_MUSICTHEME_STANDARD) {};
        INSTANCE XAR_Ngt_Fgt (C_MUSICTHEME_FIGHT) {};
        INSTANCE SYS_Menu (C_MUSICTHEME) {};
    """)
    # Mixed-case folder names, as in real installs.
    _write(data / "Scripts" / "CONTENT" / "Items" / "Keys.d", """
        INSTANCE ItKe_Xardas (C_Item) {};
        instance ItMi_Gold(C_Item) {};
        PROTOTYPE Npc_Default (C_Npc) {};
        instance PC_Hero (Npc_Default) {};
    """)
    _write(data / "Scripts" / "CONTENT" / "Story" / "Text.d", """
        CONST STRING MOBNAME_CHEST = "Chest";
        const int GIL_PAL = 1; const int GIL_MAX = 66;
        func void SLEEPABIT_S1 () {};
        FUNC VOID EVT_GATE_FUNC () {};
        func void Not_A_Mob_Func () {};
    """)
    _write(data / "Presets" / "LIGHTPRESETS.ZEN", """ZenGin Archive
END
objects 1
END

numVobLightPresets=int:1
[% zCVobLightPreset 0 0]
\tpresetName=string:FIRESMALL
\trange=float:300
\tcolor=color:255 139 83 255
\tlightStatic=bool:0
\tcolorAniList=string:(255 139 83) (255 104 53)
[]
""")
    for folder, name in (("Meshes/_compiled", "OC_LOB_GATE_BIG.MRM"), ("Anims/_compiled", "CHEST.MSB"),
                         ("Anims/_compiled", "CHEST.MDL"), ("Anims/_compiled", "BED.MDL"),
                         ("Anims/_compiled", "FLAG.MMB"),
                         ("Textures/_compiled", "ZFLARE6-C.TEX"), ("Worlds", "FIRETREE_LAMP.ZEN"),
                         ("Worlds/MOD", "LEVEL_001.ZEN")):
        _write(data / folder / name, "")
    return tmp_path


def test_index_reads_scripts_presets_and_asset_folders(tmp_path):
    index = GameIndex(str(_game(tmp_path)))

    assert index.found
    assert index.sfx == ["OW_Crow", "TORCH_BURN"]          # no comments, speech or _A1 variations
    assert index.pfx == ["FIRE.PFX"]
    assert index.music_themes == ["XAR"]
    assert index.items == ["ItKe_Xardas", "ItMi_Gold"] and index.keys == ["ItKe_Xardas"]
    assert index.npcs == ["Npc_Default", "PC_Hero"]
    assert index.focus_names == ["MOBNAME_CHEST"] and index.guilds == ["GIL_PAL"]
    assert index.mob_functions == ["SLEEPABIT"] and index.event_functions == ["EVT_GATE_FUNC"]
    assert index.light_presets == ["FIRESMALL"]
    assert index.light_preset_values["FIRESMALL"]["colorAniList"] == "(255 139 83) (255 104 53)"
    assert index.meshes == ["OC_LOB_GATE_BIG.3DS"]
    assert index.mob_models == ["BED.ASC", "CHEST.MDS"] and index.morph_meshes == ["FLAG.MMS"]
    assert index.textures == ["ZFLARE6.TGA"]
    assert index.vob_trees == ["FIRETREE_LAMP.ZEN"] and index.worlds == ["MOD\\LEVEL_001.ZEN"]


def test_missing_or_packed_game_folder_gives_empty_lists(tmp_path):
    (tmp_path / "Data").mkdir()                     # only .vdf archives, nothing unpacked
    for folder in (None, "", str(tmp_path / "nope"), str(tmp_path)):
        index = GameIndex(folder)
        assert not index.found and index.sfx == [] and index.light_preset_values == {}
    assert find_data_dir(str(tmp_path)) is None
