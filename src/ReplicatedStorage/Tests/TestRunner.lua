-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:09 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Pets.PetDatabase)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.QueueSequential)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.EventString)
require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_7 = require(game.ReplicatedStorage.GameStage.GameStageDatabase)
require(game.ReplicatedStorage.Local.GameLocalMode)
local v_u_8 = require(game.ReplicatedStorage.Local.GameLocal)
local v_u_9 = require(game.ReplicatedStorage.Local.GameJoinProtocol)
local v_u_10 = require(game.ReplicatedStorage.Tutorial.TutorialData)
local v_u_11 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
local v_u_12 = require(game.ReplicatedStorage.Shared.GameDanceInfo)
local v_u_13 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.Collection.OwnedIdSet)
local v_u_16 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_17 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_18 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_19 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_20 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_21 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_22 = require(game.ReplicatedStorage.Avatar.ElementalColor)
require(game.ReplicatedStorage.Tests.EditorGameDataTests)
local v_u_23 = require(game.ReplicatedStorage.PlayerInfo.MissionMPRewardFlag)
local v_u_24 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
return {
    ["run_tests"] = function(_, _) --[[ Name: run_tests ]] --[[ Line: 34 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4, (copy 3): v_u_24, (copy 4): v_u_23 ]]
        if v_u_2:is_dev_build() == true then
            if v_u_4.RunTestRunner == true then
                local v25 = v_u_24:new()
                v_u_23:playerblob_set_flag(v25, v_u_23.Flag.MissionMPReward1, 1)
                v_u_23:playerblob_set_flag(v25, v_u_23.Flag.MissionMPReward2, 1)
                v_u_23:playerblob_set_flag(v25, v_u_23.Flag.MissionMPReward3, 1)
                print(v_u_23:playerblob_has_flag_set(v25, v_u_23.Flag.MissionMPReward1, 1))
                print(v_u_23:playerblob_has_flag_set(v25, v_u_23.Flag.MissionMPReward2, 1))
                print(v_u_23:playerblob_has_flag_set(v25, v_u_23.Flag.MissionMPReward3, 1))
                v_u_23:playerblob_set_flag(v25, v_u_23.Flag.MissionMPReward2, 2)
                v_u_23:playerblob_set_flag(v25, v_u_23.Flag.MissionMPReward3, 2)
                print(v_u_23:playerblob_has_flag_set(v25, v_u_23.Flag.MissionMPReward1, 2))
                print(v_u_23:playerblob_has_flag_set(v25, v_u_23.Flag.MissionMPReward2, 2))
                print(v_u_23:playerblob_has_flag_set(v25, v_u_23.Flag.MissionMPReward3, 2))
                error("end")
            end;
        else
            return;
        end;
    end,
    ["run_stage_pet_collections_test"] = function(_, p_u_26) --[[ Name: run_stage_pet_collections_test ]] --[[ Line: 72 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_6, (copy 3): v_u_1, (copy 4): v_u_13, (copy 5): v_u_10, (copy 6): v_u_8, (copy 7): v_u_9, (copy 8): v_u_11, (copy 9): v_u_12, (copy 10): v_u_7, (copy 11): v_u_5, (copy 12): v_u_14, (copy 13): v_u_2, (copy 14): v_u_15 ]]
        local v_u_29 = v_u_3:new(function(p27, p28) --[[ Line: 73 ]]
            p27(p28)
        end)
        local function f_test_pets() --[[ Name: test_pets ]] --[[ Line: 77 ]]
            --[[ Upvalues: (copy 1): v_u_29, (ref 2): v_u_6, (ref 3): v_u_1, (ref 4): v_u_13 ]]
            v_u_29:queue_sequential(function(p30) --[[ Line: 78 ]]
                --[[ Upvalues: (ref 1): v_u_6 ]]
                v_u_6:puts("Running PetTests...")
                p30()
            end)
            for v_u_31 = 1, v_u_1:singleton():count() do
                local v_u_32 = v_u_1:singleton():get_data_for_petid(v_u_31)
                v_u_29:queue_sequential(function(p_u_33) --[[ Line: 86 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_31, (copy 3): v_u_32, (ref 4): v_u_1, (ref 5): v_u_13 ]]
                    v_u_6:puts("Testing PetID[%d](%s)", v_u_31, v_u_32:get_name())
                    v_u_32:create_character(v_u_1.DEFAULT_CREATE_PET_PARAMS, game.Workspace, function(p34) --[[ Line: 88 ]]
                        --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_33 ]]
                        v_u_13:is_true(p34.ClassName == "Model")
                        v_u_13:is_true(p34.PrimaryPart ~= nil)
                        v_u_13:is_true(p34.Humanoid ~= nil)
                        p34.Parent = nil
                        p_u_33()
                    end)
                end)
            end;
        end;
        local function _() --[[ Name: test_collections ]] --[[ Line: 141 ]]
            --[[ Upvalues: (copy 1): v_u_29, (ref 2): v_u_6, (ref 3): v_u_14, (ref 4): v_u_13, (ref 5): v_u_2, (ref 6): v_u_15 ]]
            v_u_29:queue_sequential(function(p35) --[[ Line: 142 ]]
                --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_14, (ref 3): v_u_13, (ref 4): v_u_2, (ref 5): v_u_15 ]]
                v_u_6:puts("---CollectionInfo:run_debug_tests---")
                local function f_assert_collection_types_match(p36, p37) --[[ Name: assert_collection_types_match ]] --[[ Line: 145 ]]
                    --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_13 ]]
                    for v38, v39 in v_u_14:get_collection_type_to_entries():key_itr() do
                        for v40 = 1, v39:count() do
                            local v41 = v39:get(v40):get_collection_id()
                            v_u_13:is_true(p36:get_collection_type_and_id_owned(v38, v41) == p37:get_collection_type_and_id_owned(v38, v41), string.format("a(%s,%s)[%s] != b(%s,%s)[%s]", tostring(v38), tostring(v41), tostring(p36:get_collection_type_and_id_owned(v38, v41)), tostring(v38), tostring(v41), (tostring(p37:get_collection_type_and_id_owned(v38, v41)))))
                        end;
                    end;
                end;
                local v42 = v_u_14:new()
                for v43, v44 in v_u_14:get_collection_type_to_entries():key_itr() do
                    for v45 = 1, v44:count() do
                        v42:set_collection_type_and_id_owned(v43, v44:get(v45):get_collection_id(), v_u_2:rand_rangef(0, 2) <= 1)
                    end;
                end;
                local l_Dances_0 = v_u_14.Type.Dances
                v42:set_collection_type_and_id_owned(l_Dances_0, 1, true)
                v42:set_collection_type_and_id_owned(l_Dances_0, 30, true)
                v42:set_collection_type_and_id_owned(l_Dances_0, 31, true)
                v42:set_collection_type_and_id_owned(l_Dances_0, 32, true)
                v42:set_collection_type_and_id_owned(l_Dances_0, 33, true)
                v42:set_collection_type_and_id_owned(l_Dances_0, 62, false)
                v42:set_collection_type_and_id_owned(l_Dances_0, 63, false)
                v42:set_collection_type_and_id_owned(l_Dances_0, 64, false)
                v42:set_collection_type_and_id_owned(l_Dances_0, 65, false)
                v42:set_collection_type_and_id_owned(l_Dances_0, 94, true)
                v42:set_collection_type_and_id_owned(l_Dances_0, 95, false)
                v42:set_collection_type_and_id_owned(l_Dances_0, 96, true)
                v42:set_collection_type_and_id_owned(l_Dances_0, 97, false)
                v42:set_collection_type_and_id_owned(l_Dances_0, 98, true)
                local v46 = v_u_15:new()
                v46:set_id_owned(10, true)
                v46:set_id_owned(29, true)
                v42:add_unhandled_type_owned_id_set(10, v46)
                local v47 = v42:to_json()
                v_u_6:puts("***SRC*** %s", v47)
                local v48 = v_u_14:from_json(v47)
                v_u_6:puts("***CLN*** %s", v48:to_json())
                f_assert_collection_types_match(v42, v48)
                v_u_6:puts("---CollectionInfo tests passed---")
                p35()
            end)
        end;
        (function() --[[ Name: test_stages ]] --[[ Line: 101 ]]
            --[[ Upvalues: (copy 1): v_u_29, (ref 2): v_u_6, (ref 3): v_u_10, (ref 4): v_u_8, (copy 5): p_u_26, (ref 6): v_u_9, (ref 7): v_u_11, (ref 8): v_u_12, (ref 9): v_u_7, (ref 10): v_u_5 ]]
            v_u_29:queue_sequential(function(p49) --[[ Line: 102 ]]
                --[[ Upvalues: (ref 1): v_u_6 ]]
                v_u_6:puts("Running GameStageTests...")
                p49()
            end)
            local v50 = v_u_10:get_tutorial_play_songkey()
            local v51, v52 = v_u_10:get_player_info_data()
            local v53 = v_u_10:get_gear_info_data()
            local v_u_54 = v_u_8:new(p_u_26, CFrame.new(), v_u_9:new(p_u_26))
            v_u_54:es_gamelocal_get_audiomanager():load_song(v50)
            v_u_54:setup_world(v51, v52, v53, v_u_11:new(), v_u_12:new())
            for v_u_55 = 1, v_u_7:singleton():count() do
                v_u_29:queue_sequential(function(p_u_56) --[[ Line: 117 ]]
                    --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_55, (ref 3): v_u_6, (copy 4): v_u_54 ]]
                    local v_u_57 = v_u_7:singleton():get_stage_info_for_id(v_u_55)
                    v_u_6:puts("\tTesting Stage [%d](%s)", v_u_55, v_u_57:get_name())
                    v_u_57:load_stage(function() --[[ Line: 120 ]]
                        --[[ Upvalues: (copy 1): v_u_57, (ref 2): v_u_54, (copy 3): p_u_56 ]]
                        v_u_57:setup_stage(v_u_54)
                        v_u_57:create_shine_for_slot_at_cframe(v_u_54, 1, CFrame.new())
                        v_u_57:process_character_location_for_slot(CFrame.new(), Vector3.new(1, 0, 0), Vector3.new(0, 0, 1), Vector3.new(0, 1, 0))
                        v_u_57:create_trigger_button_asset(v_u_54, 1, 1)
                        v_u_57:game_update(1, v_u_54)
                        v_u_57:teardown_stage(v_u_54)
                        p_u_56()
                    end)
                end)
            end;
            v_u_29:queue_sequential(function(p58) --[[ Line: 134 ]]
                --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_5 ]]
                v_u_6:puts("Stage Tests Complete")
                v_u_5:set_mode(v_u_5.Mode.Game)
                p58()
            end)
        end)()
        f_test_pets()
        v_u_29:queue_sequential(function(p59) --[[ Line: 142 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_14, (ref 3): v_u_13, (ref 4): v_u_2, (ref 5): v_u_15 ]]
            v_u_6:puts("---CollectionInfo:run_debug_tests---")
            local function f_assert_collection_types_match(p60, p61) --[[ Name: assert_collection_types_match ]] --[[ Line: 145 ]]
                --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_13 ]]
                for v62, v63 in v_u_14:get_collection_type_to_entries():key_itr() do
                    for v64 = 1, v63:count() do
                        local v65 = v63:get(v64):get_collection_id()
                        v_u_13:is_true(p60:get_collection_type_and_id_owned(v62, v65) == p61:get_collection_type_and_id_owned(v62, v65), string.format("a(%s,%s)[%s] != b(%s,%s)[%s]", tostring(v62), tostring(v65), tostring(p60:get_collection_type_and_id_owned(v62, v65)), tostring(v62), tostring(v65), (tostring(p61:get_collection_type_and_id_owned(v62, v65)))))
                    end;
                end;
            end;
            local v66 = v_u_14:new()
            for v67, v68 in v_u_14:get_collection_type_to_entries():key_itr() do
                for v69 = 1, v68:count() do
                    v66:set_collection_type_and_id_owned(v67, v68:get(v69):get_collection_id(), v_u_2:rand_rangef(0, 2) <= 1)
                end;
            end;
            local l_Dances_1 = v_u_14.Type.Dances
            v66:set_collection_type_and_id_owned(l_Dances_1, 1, true)
            v66:set_collection_type_and_id_owned(l_Dances_1, 30, true)
            v66:set_collection_type_and_id_owned(l_Dances_1, 31, true)
            v66:set_collection_type_and_id_owned(l_Dances_1, 32, true)
            v66:set_collection_type_and_id_owned(l_Dances_1, 33, true)
            v66:set_collection_type_and_id_owned(l_Dances_1, 62, false)
            v66:set_collection_type_and_id_owned(l_Dances_1, 63, false)
            v66:set_collection_type_and_id_owned(l_Dances_1, 64, false)
            v66:set_collection_type_and_id_owned(l_Dances_1, 65, false)
            v66:set_collection_type_and_id_owned(l_Dances_1, 94, true)
            v66:set_collection_type_and_id_owned(l_Dances_1, 95, false)
            v66:set_collection_type_and_id_owned(l_Dances_1, 96, true)
            v66:set_collection_type_and_id_owned(l_Dances_1, 97, false)
            v66:set_collection_type_and_id_owned(l_Dances_1, 98, true)
            local v70 = v_u_15:new()
            v70:set_id_owned(10, true)
            v70:set_id_owned(29, true)
            v66:add_unhandled_type_owned_id_set(10, v70)
            local v71 = v66:to_json()
            v_u_6:puts("***SRC*** %s", v71)
            local v72 = v_u_14:from_json(v71)
            v_u_6:puts("***CLN*** %s", v72:to_json())
            f_assert_collection_types_match(v66, v72)
            v_u_6:puts("---CollectionInfo tests passed---")
            p59()
        end)
        v_u_29:queue_sequential(function(p73) --[[ Line: 220 ]]
            --[[ Upvalues: (ref 1): v_u_6 ]]
            v_u_6:puts("-----Tests Complete----")
            p73()
        end)
    end,
    ["run_r_alpha_performance_tests"] = function(_) --[[ Name: run_r_alpha_performance_tests ]] --[[ Line: 226 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_6 ]]
        local l_Part_0 = Instance.new("Part")
        local l_Frame_0 = Instance.new("Frame", (Instance.new("SurfaceGui", l_Part_0)))
        l_Frame_0.BackgroundTransparency = 1
        local l_ImageLabel_0 = Instance.new("ImageLabel", l_Frame_0)
        l_ImageLabel_0.BackgroundTransparency = 1
        l_ImageLabel_0.Image = v_u_2:important_assetid()
        local l_TextLabel_0 = Instance.new("TextLabel", l_Frame_0)
        l_TextLabel_0.BackgroundTransparency = 1
        l_TextLabel_0.Text = "TEST"
        local v74 = l_Part_0:Clone()
        v74.Name = "TestRunner:run_r_alpha_performance_tests : r_set_alpha (Name)"
        v74.Parent = game.Workspace
        v_u_2:obj_set_alpha(v74, 0.5, 1, nil)
        local v75 = tick()
        local v76 = {}
        for _ = 1, 10000 do
            v_u_2:r_set_alpha(v74, v_u_2:rand_rangef(0, 1), nil, v76)
        end;
        v_u_6:puts("%s: %f", v74.Name, tick() - v75)
        v74.Parent = nil
        local v77 = l_Part_0:Clone()
        v77.Name = "TestRunner:run_r_alpha_performance_tests : obj_set_alpha"
        v77.Parent = game.Workspace
        local v78 = tick()
        for _ = 1, 10000 do
            v_u_2:obj_set_alpha(v77, v_u_2:rand_rangef(0, 1), 1)
        end;
        v_u_6:puts("%s: %f", v77.Name, tick() - v78)
        v77.Parent = nil
        local v79 = l_Part_0:Clone()
        v79.Name = "TestRunner:run_r_alpha_performance_tests : r_set_alpha (Attribute)"
        v79.Parent = game.Workspace
        for _, v80 in v_u_2:get_list_of_children_of_classname(v79, "TextLabel"):key_itr() do
            v_u_2:obj_apply_suffix_alpha_attribute(v80, "TestRunner", 0.5)
        end;
        for _, v81 in v_u_2:get_list_of_children_of_classname(v79, "ImageLabel"):key_itr() do
            v_u_2:obj_apply_suffix_alpha_attribute(v81, "TestRunner", 0.5)
        end;
        local v82 = tick()
        local v83 = v_u_2:r_set_alpha_v2_params()
        for _ = 1, 10000 do
            v_u_2:r_set_alpha(v79, v_u_2:rand_rangef(0, 1), nil, v83)
        end;
        v_u_6:puts("%s: %f", v79.Name, tick() - v82)
        v79.Parent = nil
        local v84 = l_Part_0:Clone()
        v84.Name = "TestRunner:run_r_alpha_performance_tests : obj_write_suffix_alpha_attribute_and_apply_all"
        v84.Parent = game.Workspace
        local v85 = tick()
        for _ = 1, 10000 do
            v_u_2:obj_write_suffix_alpha_attribute_and_apply_all(v84, "TestRunner", v_u_2:rand_rangef(0, 1), 1)
        end;
        v_u_6:puts("%s: %f", v84.Name, tick() - v85)
        v84.Parent = nil
    end,
    ["print_pet_gear_power_examples"] = function(_) --[[ Name: print_pet_gear_power_examples ]] --[[ Line: 310 ]]
        --[[ Upvalues: (copy 1): v_u_17, (copy 2): v_u_16, (copy 3): v_u_18, (copy 4): v_u_20, (copy 5): v_u_19, (copy 6): v_u_22, (copy 7): v_u_1, (copy 8): v_u_21 ]]
        local v86 = v_u_17:get_min_level()
        local v87 = v_u_17:get_max_level()
        local v88 = v_u_17:get_min_rank()
        local v89 = v_u_17:get_max_rank()
        local v_u_90 = v_u_16:new()
        for v91 = v86, v87 do
            for v92 = v88, v89 do
                if v91 <= v_u_17:rank_to_max_level(v92) then
                    v_u_90:add(v91, v92)
                    break;
                end;
            end;
        end;
        local v_u_93 = ""
        local function f_print_pet_gear_power_for_petid_level_songkey(p94, p95, p96) --[[ Name: print_pet_gear_power_for_petid_level_songkey ]] --[[ Line: 327 ]]
            --[[ Upvalues: (copy 1): v_u_90, (ref 2): v_u_18, (ref 3): v_u_17, (ref 4): v_u_20, (ref 5): v_u_19, (ref 6): v_u_22, (ref 7): v_u_93, (ref 8): v_u_1, (ref 9): v_u_21 ]]
            local v97 = v_u_90:get(p95)
            local v98 = v_u_18:statsdict_base()
            v_u_17:petid_level_rank_apply_statsdict(p94, p95, v97, v98)
            local v99 = v_u_20:songkey_get_color_list(p96)
            local v100 = v_u_19:statsdict_get_gear_power(v98, true, v99)
            local v101 = ""
            for v102 = 1, v99:count() do
                v101 = v101 .. v_u_22:color_to_name(v99:get(v102)) .. " "
            end;
            v_u_93 = v_u_93 .. string.format("Pet[%d](%s) Level(%d) Song(%s)[%s] GearPower(%d)\n", p94, v_u_1:singleton():get_data_for_petid(p94):get_name(), p95, v_u_21:singleton():key_to_name(p96), v101, v100)
        end;
        f_print_pet_gear_power_for_petid_level_songkey(1, 1, 693)
        f_print_pet_gear_power_for_petid_level_songkey(1, 25, 693)
        f_print_pet_gear_power_for_petid_level_songkey(1, 50, 693)
        f_print_pet_gear_power_for_petid_level_songkey(1, 1, 684)
        f_print_pet_gear_power_for_petid_level_songkey(1, 25, 684)
        f_print_pet_gear_power_for_petid_level_songkey(1, 50, 684)
        f_print_pet_gear_power_for_petid_level_songkey(2, 1, 657)
        f_print_pet_gear_power_for_petid_level_songkey(2, 25, 657)
        f_print_pet_gear_power_for_petid_level_songkey(2, 50, 657)
        f_print_pet_gear_power_for_petid_level_songkey(2, 1, 706)
        f_print_pet_gear_power_for_petid_level_songkey(2, 25, 706)
        f_print_pet_gear_power_for_petid_level_songkey(2, 50, 706)
        f_print_pet_gear_power_for_petid_level_songkey(2, 50, 674)
        f_print_pet_gear_power_for_petid_level_songkey(40, 1, 743)
        f_print_pet_gear_power_for_petid_level_songkey(40, 25, 743)
        f_print_pet_gear_power_for_petid_level_songkey(40, 50, 743)
        f_print_pet_gear_power_for_petid_level_songkey(40, 1, 670)
        f_print_pet_gear_power_for_petid_level_songkey(40, 25, 670)
        f_print_pet_gear_power_for_petid_level_songkey(40, 50, 670)
        f_print_pet_gear_power_for_petid_level_songkey(43, 1, 752)
        f_print_pet_gear_power_for_petid_level_songkey(43, 25, 752)
        f_print_pet_gear_power_for_petid_level_songkey(43, 50, 752)
        f_print_pet_gear_power_for_petid_level_songkey(43, 1, 735)
        f_print_pet_gear_power_for_petid_level_songkey(43, 25, 735)
        f_print_pet_gear_power_for_petid_level_songkey(43, 50, 735)
        f_print_pet_gear_power_for_petid_level_songkey(76, 1, 840)
        f_print_pet_gear_power_for_petid_level_songkey(76, 25, 840)
        f_print_pet_gear_power_for_petid_level_songkey(76, 50, 840)
        f_print_pet_gear_power_for_petid_level_songkey(76, 1, 678)
        f_print_pet_gear_power_for_petid_level_songkey(76, 25, 678)
        f_print_pet_gear_power_for_petid_level_songkey(76, 50, 678)
        print("*****TestRunner:print_pet_gear_power_examples()\n" .. v_u_93 .. "*****END")
    end
};
