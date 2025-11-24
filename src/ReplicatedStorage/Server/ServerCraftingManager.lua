-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:13 PM
-- Cached decompilation

require(game.ReplicatedStorage.Server.DebugOut)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.ProdEnvSelector)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_7 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_8 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_9 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_10 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v_u_11 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_12 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_14 = require(game.ReplicatedStorage.Tutorial.GearCraftingTutorialInfo)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.BoxInfo)
require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_16 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_17 = require(game.ReplicatedStorage.Crafting.CraftingRewardCategories)
local v_u_18 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
local v_u_19 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_20 = require(game.ReplicatedStorage.Pets.PetUtils)
local v21 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_22 = nil
v21:require_server(function() --[[ Line: 30 ]]
    --[[ Upvalues: (ref 1): v_u_22 ]]
    v_u_22 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
end)
return {
    ["new"] = function(_, p_u_23) --[[ Name: new ]] --[[ Line: 36 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_12, (copy 3): v_u_7, (copy 4): v_u_9, (copy 5): v_u_6, (copy 6): v_u_4, (copy 7): v_u_18, (copy 8): v_u_2, (copy 9): v_u_1, (copy 10): v_u_16, (copy 11): v_u_10, (copy 12): v_u_11, (copy 13): v_u_5, (copy 14): v_u_14, (copy 15): v_u_13, (copy 16): v_u_20, (copy 17): v_u_19, (ref 18): v_u_22, (copy 19): v_u_8, (copy 20): v_u_15, (copy 21): v_u_17 ]]
        local v24 = {}
        v24.start = function(p_u_25) --[[ Name: start ]] --[[ Line: 39 ]]
            --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_3, (ref 3): v_u_12, (ref 4): v_u_7, (ref 5): v_u_9, (ref 6): v_u_6, (ref 7): v_u_4, (ref 8): v_u_18, (ref 9): v_u_2, (ref 10): v_u_1, (ref 11): v_u_16, (ref 12): v_u_10, (ref 13): v_u_11, (ref 14): v_u_5, (ref 15): v_u_14, (ref 16): v_u_13, (ref 17): v_u_20, (ref 18): v_u_19, (ref 19): v_u_22, (ref 20): v_u_8, (ref 21): v_u_15 ]]
            p_u_23._evt:wait_on_event(v_u_3.EVT_Crafting_CraftSongClientRequest, function(p_u_26, p_u_27, p_u_28) --[[ Line: 40 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_23, (ref 3): v_u_3, (ref 4): v_u_7, (ref 5): v_u_9, (ref 6): v_u_6, (ref 7): v_u_4, (ref 8): v_u_18 ]]
                v_u_12:is_int(p_u_28)
                local function f_craft_song_server_response(p29, p30) --[[ Name: craft_song_server_response ]] --[[ Line: 43 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_26 ]]
                    p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_CraftSongServerResponse, p_u_26, p29, p30)
                end;
                if p_u_28 <= 0 or p_u_28 > 7 then
                    return f_craft_song_server_response(false, "Failed amount.");
                end;
                if v_u_7:singleton():get_song_recipe(p_u_27) == nil then
                    return f_craft_song_server_response(false, "Invalid recipe.");
                end;
                p_u_23._player_blob_manager:get_verified_cached_blob(p_u_26.UserId, function(p31) --[[ Line: 55 ]]
                    --[[ Upvalues: (copy 1): f_craft_song_server_response, (ref 2): v_u_9, (copy 3): p_u_27, (ref 4): v_u_7, (copy 5): p_u_28, (ref 6): v_u_6, (ref 7): v_u_4, (ref 8): p_u_23, (ref 9): v_u_18, (copy 10): p_u_26, (ref 11): v_u_3 ]]
                    if p31 == nil then
                        return f_craft_song_server_response(false, "Err getting playerblob.");
                    end;
                    if v_u_9:can_craft_recipe(p31, p_u_27) ~= true then
                        return f_craft_song_server_response(false, "Err does not meet recipe requirements.");
                    end;
                    local v32 = v_u_7:singleton():get_song_recipe_requirements_dict(p_u_27)
                    for v33, v34 in v32:key_itr() do
                        v32:add(v33, v34 * p_u_28)
                    end;
                    if v_u_9:can_craft_requirements_dict(p31, v32) ~= true then
                        return f_craft_song_server_response(false, "Err not enough materials.");
                    end;
                    for v35, v36 in v32:key_itr() do
                        v_u_9:add_crafting_materials_of_id(p31, v35, -v36)
                    end;
                    for _ = 1, p_u_28 do
                        v_u_6:add_song(p31, v_u_7:singleton():get_song_recipe_songkey(p_u_27))
                    end;
                    if v_u_4.UseChallengePassV2 == true then
                        p_u_23._challengepass_manager:challengepassv2_weekly_mission_playerblob_claim(v_u_18.WeeklyMissionType.CraftSong, p31)
                    end;
                    p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_26.UserId, v_u_6.PlayerBlobRequestType.Write, function(_) --[[ Line: 86 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): p_u_26 ]]
                        p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_CraftSongServerResponse, p_u_26, true, "")
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_3.EVT_Crafting_ClientCraftGatchaInfoRequest, function(p_u_37) --[[ Line: 93 ]]
                --[[ Upvalues: (copy 1): p_u_25, (ref 2): p_u_23, (ref 3): v_u_3 ]]
                p_u_25:get_updated_gatcha_info(function(p38) --[[ Line: 94 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_37 ]]
                    p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_ServerCraftGatchaInfoResponse, p_u_37, p38)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_3.EVT_Crafting_ClientCraftGatchaAttempt, function(p_u_39, p_u_40) --[[ Line: 103 ]]
                --[[ Upvalues: (copy 1): p_u_25, (ref 2): p_u_23, (ref 3): v_u_3, (ref 4): v_u_6, (ref 5): v_u_2, (ref 6): v_u_9, (ref 7): v_u_1, (ref 8): v_u_16, (ref 9): v_u_4, (ref 10): v_u_18 ]]
                p_u_25:get_updated_gatcha_info(function(p_u_41) --[[ Line: 104 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_39, (copy 4): p_u_40, (ref 5): v_u_6, (ref 6): v_u_2, (ref 7): p_u_25, (ref 8): v_u_9, (ref 9): v_u_1, (ref 10): v_u_16, (ref 11): v_u_4, (ref 12): v_u_18 ]]
                    local function f_gatcha_attempt_response(p42, p43, p44) --[[ Name: gatcha_attempt_response ]] --[[ Line: 105 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): p_u_39 ]]
                        p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_ServerCraftGatchaAttemptResponse, p_u_39, p42, p43, p44 == nil and {} or p44)
                    end;
                    p_u_23._player_blob_manager:get_verified_cached_blob(p_u_39.UserId, function(p45) --[[ Line: 116 ]]
                        --[[ Upvalues: (copy 1): f_gatcha_attempt_response, (copy 2): p_u_41, (ref 3): p_u_40, (ref 4): v_u_6, (ref 5): v_u_2, (ref 6): p_u_25, (ref 7): v_u_9, (ref 8): v_u_1, (ref 9): v_u_16, (ref 10): p_u_23, (ref 11): v_u_4, (ref 12): v_u_18, (ref 13): p_u_39, (ref 14): v_u_3 ]]
                        if p45 == nil then
                            return f_gatcha_attempt_response(false, "PlayerBlob not found.");
                        end;
                        local v46 = p_u_41[p_u_40]
                        if v46 == nil then
                            return f_gatcha_attempt_response(false, "err");
                        end;
                        local l_PriceType_0 = v46.PriceType
                        local l_PriceValue_0 = v46.PriceValue
                        local l_SpinCount_0 = v46.SpinCount
                        local v47 = false
                        if l_PriceType_0 == v_u_6.CurrencyType.Coins then
                            if l_PriceValue_0 <= p45.CoinCurrency then
                                v_u_6:add_coin_currency(p45, -l_PriceValue_0)
                                v47 = true
                            end;
                        elseif l_PriceType_0 == v_u_6.CurrencyType.Stars and l_PriceValue_0 <= p45.StarCurrency then
                            v_u_6:add_star_currency(p45, -l_PriceValue_0)
                            v47 = true
                        end;
                        if v47 ~= true then
                            return f_gatcha_attempt_response(false, "Not enough currency.");
                        end;
                        local v48 = v_u_2:new()
                        for _ = 1, l_SpinCount_0 do
                            local v49 = p_u_25:crafting_gatcha_get_roll_result_materialid(l_PriceType_0)
                            v_u_2:counter_increment(v48, v49, 1)
                            v_u_9:add_crafting_materials_of_id(p45, v49, 1)
                        end;
                        local v_u_50 = v_u_1:new()
                        for v51, v52 in v48:key_itr() do
                            v_u_50:push_back(v_u_16.RewardInfo:new(v_u_16.RewardType.CraftingMaterials, v52, v51))
                        end;
                        p_u_23._mission_manager:apply_note_machine_count_to_mission_for_player_blob(p45, l_SpinCount_0)
                        if v_u_4.UseChallengePassV2 == true then
                            p_u_23._challengepass_manager:challengepassv2_weekly_mission_playerblob_claim(v_u_18.WeeklyMissionType.RollNoteMachine, p45)
                        end;
                        p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_39.UserId, v_u_6.PlayerBlobRequestType.Write, function() --[[ Line: 172 ]]
                            --[[ Upvalues: (ref 1): v_u_16, (copy 2): v_u_50, (ref 3): p_u_23, (ref 4): v_u_3, (ref 5): p_u_39 ]]
                            local v53 = v_u_16.RewardInfo:list_to_table(v_u_50)
                            p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_ServerCraftGatchaAttemptResponse, p_u_39, true, "", v53 == nil and {} or v53)
                        end)
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_3.EVT_Crafting_CraftGearUpgradeClientRequest, function(p_u_54, p_u_55, p_u_56) --[[ Line: 181 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): v_u_10, (ref 4): v_u_11, (ref 5): v_u_9, (ref 6): v_u_4, (ref 7): v_u_18, (ref 8): v_u_6 ]]
                local function f_craft_gear_upgrade_server_response(p57, p58) --[[ Name: craft_gear_upgrade_server_response ]] --[[ Line: 182 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_54 ]]
                    p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_CraftGearUpgradeServerResponse, p_u_54, p57, p58, false)
                end;
                if v_u_10:singleton():get_equipment_upgrade_for_id(p_u_55) == nil then
                    return f_craft_gear_upgrade_server_response(false, "Invalid upgradeid");
                end;
                p_u_23._player_blob_manager:get_verified_cached_blob(p_u_54.UserId, function(p59) --[[ Line: 190 ]]
                    --[[ Upvalues: (copy 1): f_craft_gear_upgrade_server_response, (ref 2): v_u_11, (copy 3): p_u_56, (ref 4): v_u_10, (ref 5): p_u_23, (ref 6): v_u_3, (copy 7): p_u_54, (copy 8): p_u_55, (ref 9): v_u_9, (ref 10): v_u_4, (ref 11): v_u_18, (ref 12): v_u_6 ]]
                    if p59 == nil then
                        return f_craft_gear_upgrade_server_response(false, "Err getting playerblob.");
                    end;
                    local _, v60 = v_u_11:playerblob_ownedid_to_equipmentid(p59, p_u_56)
                    if v60 == nil then
                        return f_craft_gear_upgrade_server_response(false, "Cannot find gear");
                    end;
                    local v61 = v_u_11:get_ownedid_upgrade_count(p59, p_u_56)
                    if v_u_10:singleton():upgrade_count_can_upgrade(v61) ~= true then
                        return f_craft_gear_upgrade_server_response(false, string.format("Reached maximum number of upgrades for this gear (%d)", v61));
                    end;
                    if v_u_10:singleton():upgrade_count_can_safe_upgrade(v61) ~= true then
                        return p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_CraftGearUpgradeServerResponse, p_u_54, true, "", true);
                    end;
                    local v62 = v_u_10:singleton():get_requirements_dict_for_id(p_u_55)
                    if v_u_9:can_craft_requirements_dict(p59, v62) ~= true then
                        return f_craft_gear_upgrade_server_response(false, "Err not enough materials.");
                    end;
                    if v_u_11:add_upgrade_to_ownedid(p59, p_u_55, p_u_56) ~= true then
                        return f_craft_gear_upgrade_server_response(false, "Add upgrade failed(?)");
                    end;
                    for v63, v64 in v62:key_itr() do
                        v_u_9:add_crafting_materials_of_id(p59, v63, -v64)
                    end;
                    p_u_23._mission_manager:apply_upgrade_gear_count_to_mission_for_player_blob(p59, 1)
                    if v_u_4.UseChallengePassV2 == true then
                        p_u_23._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_18.DailyMissionType.UpgradeGear, p59)
                    end;
                    p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_54.UserId, v_u_6.PlayerBlobRequestType.Write, function(_) --[[ Line: 230 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): p_u_54 ]]
                        p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_CraftGearUpgradeServerResponse, p_u_54, true, "", false)
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_3.EVT_Crafting_CraftGearBoostUpgradeClientRequest, function(p_u_65, p_u_66, p_u_67, p_u_68, p_u_69) --[[ Line: 238 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): v_u_10, (ref 4): v_u_11, (ref 5): v_u_12, (ref 6): v_u_9, (ref 7): v_u_5, (ref 8): v_u_4, (ref 9): v_u_18, (ref 10): v_u_6 ]]
                local function f_craft_gear_boost_upgrade_server_response_fail(p70, p71) --[[ Name: craft_gear_boost_upgrade_server_response_fail ]] --[[ Line: 239 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_65 ]]
                    p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_CraftGearBoostUpgradeServerResponse, p_u_65, p70, p71, false, false)
                end;
                if v_u_10:singleton():get_equipment_upgrade_for_id(p_u_66) == nil then
                    return f_craft_gear_boost_upgrade_server_response_fail(false, "Invalid upgradeid");
                end;
                p_u_23._player_blob_manager:get_verified_cached_blob(p_u_65.UserId, function(p_u_72) --[[ Line: 245 ]]
                    --[[ Upvalues: (copy 1): f_craft_gear_boost_upgrade_server_response_fail, (ref 2): v_u_11, (copy 3): p_u_67, (ref 4): v_u_12, (ref 5): v_u_10, (copy 6): p_u_66, (ref 7): v_u_9, (copy 8): p_u_69, (copy 9): p_u_68, (ref 10): p_u_23, (ref 11): v_u_5, (ref 12): v_u_4, (ref 13): v_u_18, (copy 14): p_u_65, (ref 15): v_u_6, (ref 16): v_u_3 ]]
                    if p_u_72 == nil then
                        return f_craft_gear_boost_upgrade_server_response_fail(false, "Err getting playerblob.");
                    end;
                    local _, v73 = v_u_11:playerblob_ownedid_to_equipmentid(p_u_72, p_u_67)
                    if v73 == nil then
                        return f_craft_gear_boost_upgrade_server_response_fail(false, "Cannot find gear");
                    end;
                    local v74 = v_u_11:get_ownedid_upgrade_count(p_u_72, p_u_67)
                    v_u_12:is_true(v_u_10:singleton():get_max_safe_upgrade_count() <= v74)
                    if v_u_10:singleton():upgrade_count_can_upgrade(v74) ~= true then
                        return f_craft_gear_boost_upgrade_server_response_fail(false, string.format("Reached maximum number of upgrades for this gear (%d)", v74));
                    end;
                    local v75 = v_u_10:singleton():get_requirements_dict_for_id(p_u_66)
                    if v_u_9:can_craft_requirements_dict(p_u_72, v75) ~= true then
                        return f_craft_gear_boost_upgrade_server_response_fail(false, "Err not enough materials.");
                    end;
                    v_u_12:is_int_in_range(p_u_69, 0, v_u_10:singleton():get_upgrade_boost_max_count())
                    local v76 = v_u_9:get_count_of_material(p_u_72, v_u_10:singleton():get_upgrade_boost_material_id())
                    local v77 = v_u_9:get_count_of_material(p_u_72, v_u_10:singleton():get_upgrade_boost_untradeable_material_id())
                    if v76 + v77 < p_u_69 then
                        return f_craft_gear_boost_upgrade_server_response_fail(false, "Not enough boosts");
                    end;
                    v_u_12:is_int_in_range(p_u_68, 0, 1)
                    local v78 = v_u_9:get_count_of_material(p_u_72, v_u_10:singleton():get_upgrade_protect_material_id())
                    local v79 = v_u_9:get_count_of_material(p_u_72, v_u_10:singleton():get_upgrade_protect_untradeable_material_id())
                    if v78 + v79 < p_u_68 then
                        return f_craft_gear_boost_upgrade_server_response_fail(false, "Not enough protects");
                    end;
                    for v80, v81 in v75:key_itr() do
                        v_u_9:add_crafting_materials_of_id(p_u_72, v80, -v81)
                    end;
                    local function _(p82, p83, p84) --[[ Name: remove_used_count_if_any_owned ]] --[[ Line: 281 ]]
                        if p82 > 0 and p83 > 0 then
                            local v85 = math.min(p82, p83)
                            p84(-v85)
                            p82 = p82 - v85
                        end;
                        return p82;
                    end;
                    local v86 = p_u_69
                    local function v88(p87) --[[ Line: 293 ]]
                        --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_72, (ref 3): v_u_10 ]]
                        v_u_9:add_crafting_materials_of_id(p_u_72, v_u_10:singleton():get_upgrade_boost_untradeable_material_id(), p87)
                    end;
                    if v86 > 0 and v77 > 0 then
                        local v89 = math.min(v86, v77)
                        v88(-v89)
                        v86 = v86 - v89
                    end;
                    local function v91(p90) --[[ Line: 296 ]]
                        --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_72, (ref 3): v_u_10 ]]
                        v_u_9:add_crafting_materials_of_id(p_u_72, v_u_10:singleton():get_upgrade_boost_material_id(), p90)
                    end;
                    if v86 > 0 and v76 > 0 then
                        local v92 = math.min(v86, v76)
                        v91(-v92)
                        v86 = v86 - v92
                    end;
                    v_u_12:is_true(v86 == 0)
                    local v93 = p_u_68
                    local function v95(p94) --[[ Line: 303 ]]
                        --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_72, (ref 3): v_u_10 ]]
                        v_u_9:add_crafting_materials_of_id(p_u_72, v_u_10:singleton():get_upgrade_protect_untradeable_material_id(), p94)
                    end;
                    if v93 > 0 and v79 > 0 then
                        local v96 = math.min(v93, v79)
                        v95(-v96)
                        v93 = v93 - v96
                    end;
                    local function v98(p97) --[[ Line: 306 ]]
                        --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_72, (ref 3): v_u_10 ]]
                        v_u_9:add_crafting_materials_of_id(p_u_72, v_u_10:singleton():get_upgrade_protect_material_id(), p97)
                    end;
                    if v93 > 0 and v78 > 0 then
                        local v99 = math.min(v93, v78)
                        v98(-v99)
                        v93 = v93 - v99
                    end;
                    v_u_12:is_true(v93 == 0)
                    p_u_23._mission_manager:apply_upgrade_gear_count_to_mission_for_player_blob(p_u_72, 1)
                    local v100 = v_u_10:singleton():get_boost_upgrade_success_lt_d100_roll_for_upgrade_count_and_boost_count(v74, p_u_69, (v_u_11:get_pity_count_for_ownedid_upgradeid(p_u_72, p_u_67, p_u_66)))
                    local v_u_101 = v_u_5:rand_rangef(0, 100)
                    local v_u_102 = v_u_101 < v100
                    if v_u_102 then
                        if v_u_11:add_upgrade_to_ownedid(p_u_72, p_u_66, p_u_67) ~= true then
                            return f_craft_gear_boost_upgrade_server_response_fail(false, "Add upgrade failed(?)");
                        end;
                        v_u_11:update_pity_count_for_success_ownedid(p_u_72, p_u_67)
                    elseif p_u_68 == 0 then
                        for _ = 1, v74 - v_u_10:singleton():get_max_safe_upgrade_count() do
                            v_u_11:remove_last_upgrade_on_ownedid(p_u_72, p_u_67)
                        end;
                        v_u_11:update_pity_count_for_success_ownedid(p_u_72, p_u_67)
                    else
                        v_u_11:update_pity_count_for_failed_boost_count_ownedid_upgradeid(p_u_72, p_u_69, p_u_67, p_u_66)
                    end;
                    if v_u_4.UseChallengePassV2 == true then
                        p_u_23._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_18.DailyMissionType.UpgradeGear, p_u_72)
                    end;
                    p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_65.UserId, v_u_6.PlayerBlobRequestType.Write, function(_) --[[ Line: 342 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): p_u_65, (copy 4): v_u_102, (ref 5): p_u_68, (copy 6): v_u_101 ]]
                        p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_CraftGearBoostUpgradeServerResponse, p_u_65, true, "", v_u_102, p_u_68 > 0, v_u_101)
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_3.EVT_Crafting_CraftGearClientRequest, function(p_u_103, p_u_104) --[[ Line: 356 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): v_u_7, (ref 4): v_u_9, (ref 5): v_u_11, (ref 6): v_u_14, (ref 7): v_u_6 ]]
                local function f_craft_gear_server_response(p105, p106) --[[ Name: craft_gear_server_response ]] --[[ Line: 357 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_103 ]]
                    p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_CraftGearServerResponse, p_u_103, p105, p106)
                end;
                if v_u_7:singleton():get_gear_recipe(p_u_104) == nil then
                    return f_craft_gear_server_response(false, "Invalid recipe.");
                end;
                p_u_23._player_blob_manager:get_verified_cached_blob(p_u_103.UserId, function(p107) --[[ Line: 365 ]]
                    --[[ Upvalues: (copy 1): f_craft_gear_server_response, (ref 2): v_u_7, (copy 3): p_u_104, (ref 4): v_u_9, (ref 5): v_u_11, (ref 6): v_u_14, (ref 7): p_u_23, (copy 8): p_u_103, (ref 9): v_u_6, (ref 10): v_u_3 ]]
                    if p107 == nil then
                        return f_craft_gear_server_response(false, "Err getting playerblob.");
                    end;
                    local v108 = v_u_7:singleton():get_gear_recipe_requirements_dict(p_u_104)
                    if v_u_9:can_craft_requirements_dict(p107, v108) ~= true then
                        return f_craft_gear_server_response(false, "Err not enough materials.");
                    end;
                    if v_u_11:playerblob_can_add_more_gear(p107) ~= true then
                        return f_craft_gear_server_response(false, "Max number of owned gear reached.");
                    end;
                    if v_u_7:singleton():get_gear_recipe(p_u_104):is_gear_tutorial() == true and v_u_14:playerblob_is_gear_tutorial_active(p107) ~= true then
                        return f_craft_gear_server_response(false, "Cannot craft tutorial gear when not active.");
                    end;
                    for v109, v110 in v108:key_itr() do
                        v_u_9:add_crafting_materials_of_id(p107, v109, -v110)
                    end;
                    v_u_11:playerblob_grant_equipmentid(p107, v_u_7:singleton():get_gear_recipe_gear_id(p_u_104))
                    p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_103.UserId, v_u_6.PlayerBlobRequestType.Write, function(_) --[[ Line: 392 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): p_u_103 ]]
                        p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_CraftGearServerResponse, p_u_103, true, "")
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_3.EVT_Crafting_CraftNoteColorClientRequest, function(p_u_111, p_u_112, p_u_113) --[[ Line: 399 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_23, (ref 3): v_u_3, (ref 4): v_u_6 ]]
                v_u_12:is_table(p_u_112)
                v_u_12:is_table(p_u_113)
                v_u_12:is_true(#p_u_112 == 4)
                v_u_12:is_true(#p_u_113 == 4)
                for v114 = 1, 4 do
                    v_u_12:is_int(p_u_112[v114])
                    v_u_12:is_int(p_u_113[v114])
                end;
                local function f_craft_note_color_response(p115, p116) --[[ Name: craft_note_color_response ]] --[[ Line: 409 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_111 ]]
                    p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_CraftNoteColorServerResponse, p_u_111, p115, p116)
                end;
                p_u_23._player_blob_manager:get_verified_cached_blob(p_u_111.UserId, function(p117) --[[ Line: 413 ]]
                    --[[ Upvalues: (copy 1): f_craft_note_color_response, (copy 2): p_u_112, (copy 3): p_u_113, (ref 4): p_u_23, (copy 5): p_u_111, (ref 6): v_u_6, (ref 7): v_u_3 ]]
                    if p117 == nil then
                        return f_craft_note_color_response(false, "Err getting playerblob.");
                    end;
                    p117.BaseColor1 = p_u_112[1]
                    p117.BaseColor2 = p_u_112[2]
                    p117.BaseColor3 = p_u_112[3]
                    p117.BaseColor4 = p_u_112[4]
                    p117.FeverColor1 = p_u_113[1]
                    p117.FeverColor2 = p_u_113[2]
                    p117.FeverColor3 = p_u_113[3]
                    p117.FeverColor4 = p_u_113[4]
                    p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_111.UserId, v_u_6.PlayerBlobRequestType.Write, function() --[[ Line: 430 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): p_u_111 ]]
                        p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_CraftNoteColorServerResponse, p_u_111, true, "")
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_3.EVT_Crafting_SetFeverIconClient, function(p_u_118, p_u_119) --[[ Line: 437 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_13, (ref 3): p_u_23, (ref 4): v_u_3, (ref 5): v_u_9, (ref 6): v_u_6 ]]
                v_u_12:is_true(v_u_13:singleton():contains_fevericon_for_id(p_u_119))
                local function f_response() --[[ Name: response ]] --[[ Line: 439 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_118 ]]
                    return p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_SetFeverIconServer, p_u_118);
                end;
                p_u_23._player_blob_manager:get_verified_cached_blob(p_u_118.UserId, function(p120) --[[ Line: 442 ]]
                    --[[ Upvalues: (copy 1): f_response, (copy 2): p_u_119, (ref 3): v_u_9, (ref 4): p_u_23, (copy 5): p_u_118, (ref 6): v_u_6, (ref 7): v_u_3 ]]
                    if p120 == nil then
                        return f_response(false);
                    end;
                    p120.FeverIcon = p_u_119
                    v_u_9:validate_playerblob_fevericon(p120, p_u_23)
                    p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_118.UserId, v_u_6.PlayerBlobRequestType.Write, function() --[[ Line: 449 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): p_u_118, (ref 3): v_u_3 ]]
                        p_u_23._lobby_manager:push_player_info_updated(p_u_118.UserId)
                        p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_SetFeverIconServer, p_u_118)
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_3.EVT_Crafting_CraftMaterialClientRequest, function(p_u_121, p_u_122, p_u_123) --[[ Line: 457 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_5, (ref 3): p_u_23, (ref 4): v_u_3, (ref 5): v_u_7, (ref 6): v_u_9, (ref 7): v_u_6 ]]
                v_u_12:is_int_in_range(p_u_123, 0, v_u_5:input_max_number())
                local function f_craft_material_server_response(p124, p125) --[[ Name: craft_material_server_response ]] --[[ Line: 460 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_121, (copy 4): p_u_123 ]]
                    p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_CraftMaterialServerResponse, p_u_121, p124, p_u_123, p125)
                end;
                if p_u_123 == 0 then
                    return f_craft_material_server_response(false, "Cannot craft 0");
                end;
                if v_u_7:singleton():get_material_recipe(p_u_122) == nil then
                    return f_craft_material_server_response(false, "Invalid recipe.");
                end;
                p_u_23._player_blob_manager:get_verified_cached_blob(p_u_121.UserId, function(p126) --[[ Line: 472 ]]
                    --[[ Upvalues: (copy 1): f_craft_material_server_response, (ref 2): v_u_7, (copy 3): p_u_122, (copy 4): p_u_123, (ref 5): v_u_9, (ref 6): p_u_23, (copy 7): p_u_121, (ref 8): v_u_6, (ref 9): v_u_3 ]]
                    if p126 == nil then
                        return f_craft_material_server_response(false, "Err getting playerblob.");
                    end;
                    local v127 = v_u_7:singleton():get_material_recipe_requirements_dict(p_u_122, p_u_123)
                    if v_u_9:can_craft_requirements_dict(p126, v127) ~= true then
                        return f_craft_material_server_response(false, "Err not enough materials.");
                    end;
                    for v128, v129 in v127:key_itr() do
                        v_u_9:add_crafting_materials_of_id(p126, v128, -v129)
                    end;
                    v_u_9:add_crafting_materials_of_id(p126, v_u_7:singleton():get_material_recipe_material_id(p_u_122), v_u_7:singleton():get_material_recipe_result_count(p_u_122) * p_u_123)
                    p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_121.UserId, v_u_6.PlayerBlobRequestType.Write, function(_) --[[ Line: 494 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): p_u_121, (ref 4): p_u_123 ]]
                        p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_CraftMaterialServerResponse, p_u_121, true, p_u_123, "")
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_3.EVT_Crafting_RemoveUpgradeClientRequest, function(p_u_130, p_u_131, p_u_132) --[[ Line: 501 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_23, (ref 3): v_u_3, (ref 4): v_u_9, (ref 5): v_u_10, (ref 6): v_u_11, (ref 7): v_u_6 ]]
                v_u_12:is_int(p_u_131)
                v_u_12:is_int(p_u_132)
                local function f_response(p133, p134) --[[ Name: response ]] --[[ Line: 505 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_130 ]]
                    p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_RemoveUpgradeServerResponse, p_u_130, p133, p134)
                end;
                p_u_23._player_blob_manager:get_verified_cached_blob(p_u_130.UserId, function(p135) --[[ Line: 508 ]]
                    --[[ Upvalues: (copy 1): f_response, (ref 2): v_u_9, (ref 3): v_u_10, (ref 4): v_u_11, (copy 5): p_u_131, (copy 6): p_u_132, (ref 7): p_u_23, (copy 8): p_u_130, (ref 9): v_u_6, (ref 10): v_u_3 ]]
                    if p135 == nil then
                        return f_response(false, "Err getting playerblob.");
                    end;
                    if v_u_9:get_count_of_material(p135, v_u_10:singleton():get_upgrade_cleaner_material_id()) <= 0 then
                        return f_response(false, "Not enough upgrade cleaners.");
                    end;
                    local _, v136 = v_u_11:playerblob_ownedid_to_equipmentid(p135, p_u_131)
                    if v136 == nil then
                        return f_response(false, "Cannot find gear");
                    end;
                    if v_u_11:get_upgrade_on_ownedid_for_index(p135, p_u_131, p_u_132) == nil then
                        return f_response(false, "Upgrade index not found");
                    end;
                    v_u_9:add_crafting_materials_of_id(p135, v_u_10:singleton():get_upgrade_cleaner_material_id(), -1)
                    v_u_11:remove_upgrade_on_ownedid_for_index(p135, p_u_131, p_u_132)
                    p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_130.UserId, v_u_6.PlayerBlobRequestType.Write, function(_) --[[ Line: 521 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): p_u_130 ]]
                        p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_RemoveUpgradeServerResponse, p_u_130, true, "")
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_3.EVT_Pet_TrainPetClientRequest, function(p_u_137, p_u_138, p_u_139, p_u_140) --[[ Line: 528 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_5, (ref 3): v_u_7, (ref 4): p_u_23, (ref 5): v_u_3, (ref 6): v_u_9, (ref 7): v_u_20, (ref 8): v_u_19, (ref 9): v_u_22, (ref 10): v_u_6 ]]
                v_u_12:is_true(p_u_140 > 0)
                v_u_12:is_true(p_u_140 < v_u_5:input_max_number())
                v_u_12:is_true(v_u_7:singleton():contains_material(p_u_139))
                local function f_response(p141, p142) --[[ Name: response ]] --[[ Line: 533 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_137 ]]
                    p_u_23._evt:fire_event_to_client(v_u_3.EVT_Pet_TrainPetServerResponse, p_u_137, p141, p142)
                end;
                p_u_23._player_blob_manager:get_verified_cached_blob(p_u_137.UserId, function(p143) --[[ Line: 536 ]]
                    --[[ Upvalues: (copy 1): f_response, (ref 2): v_u_9, (copy 3): p_u_139, (copy 4): p_u_140, (ref 5): v_u_20, (copy 6): p_u_138, (ref 7): v_u_19, (ref 8): v_u_22, (ref 9): p_u_23, (copy 10): p_u_137, (ref 11): v_u_6, (ref 12): v_u_3 ]]
                    if p143 == nil then
                        return f_response(false, "Err getting playerblob");
                    end;
                    if v_u_9:get_count_of_material(p143, p_u_139) < p_u_140 then
                        return f_response(false, "Does not own count of material");
                    end;
                    local v144 = v_u_20:playerblob_get_pet_ownedid_ownedpet(p143, p_u_138)
                    if v144 == nil then
                        return f_response(false, "Pet not found");
                    end;
                    local v145 = v_u_20:ownedpet_get_petid(v144)
                    if v_u_19:singleton():contains_petid(v145) ~= true then
                        return f_response(false, "PetDatabase not found");
                    end;
                    local v146 = v_u_20:get_materialid_to_value_dict_of_train_consumable_materials_for_pet_id(v145, v_u_22:playerblob_has_vip_for_current_day(p143, p_u_23._api:get_day_id()))
                    if v146:contains(p_u_139) ~= true then
                        return f_response(false, "Invalid training material");
                    end;
                    v_u_9:add_crafting_materials_of_id(p143, p_u_139, -p_u_140)
                    v_u_20:ownedpet_apply_exp_gain(v144, v146:get(p_u_139) * p_u_140)
                    p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_137.UserId, v_u_6.PlayerBlobRequestType.Write, function(_) --[[ Line: 560 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): p_u_137 ]]
                        p_u_23._evt:fire_event_to_client(v_u_3.EVT_Pet_TrainPetServerResponse, p_u_137, true, "")
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_3.EVT_Pet_RankUpClientRequest, function(p_u_147, p_u_148, p149) --[[ Line: 567 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): v_u_4, (ref 4): v_u_2, (ref 5): v_u_12, (ref 6): v_u_7, (ref 7): v_u_5, (ref 8): v_u_20, (ref 9): v_u_9, (ref 10): v_u_6 ]]
                local function f_response(p150, p151) --[[ Name: response ]] --[[ Line: 568 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_147 ]]
                    p_u_23._evt:fire_event_to_client(v_u_3.EVT_Pet_RankUpServerResponse, p_u_147, p150, p151)
                end;
                if v_u_4.PetRankUpEnabled ~= true then
                    return f_response(false, "Not enabled");
                end;
                local v_u_152 = v_u_2:new(p149)
                for v153, v154 in v_u_152:key_itr() do
                    v_u_12:is_true(v_u_7:singleton():contains_material(v153))
                    v_u_12:is_int_in_range(v154, 1, v_u_5:input_max_number())
                end;
                p_u_23._player_blob_manager:get_verified_cached_blob(p_u_147.UserId, function(p155) --[[ Line: 580 ]]
                    --[[ Upvalues: (copy 1): f_response, (ref 2): v_u_20, (copy 3): p_u_148, (copy 4): v_u_152, (ref 5): v_u_9, (ref 6): p_u_23, (copy 7): p_u_147, (ref 8): v_u_6, (ref 9): v_u_3 ]]
                    if p155 == nil then
                        return f_response(false, "Err getting playerblob");
                    end;
                    local v156 = v_u_20:playerblob_get_pet_ownedid_ownedpet(p155, p_u_148)
                    if v156 == nil then
                        return f_response(false, "Pet not found");
                    end;
                    if v_u_20:ownedpet_can_rank_up(v156) ~= true then
                        return f_response(false, "Cannot rank up.");
                    end;
                    if v_u_20:ownedpet_get_materialid_to_count_dict_rank_up_point_total(v156, v_u_152) < v_u_20:ownedpet_get_rank_up_point_total_requirement(v156) then
                        return f_response(false, "Not enough points");
                    end;
                    for v157, v158 in v_u_152:key_itr() do
                        if v_u_9:get_count_of_material(p155, v157) < v158 then
                            return f_response(false, "Does not own count of material");
                        end;
                    end;
                    for v159, v160 in v_u_152:key_itr() do
                        v_u_9:add_crafting_materials_of_id(p155, v159, -v160)
                    end;
                    v_u_20:ownedpet_increment_rank(v156)
                    p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_147.UserId, v_u_6.PlayerBlobRequestType.Write, function(_) --[[ Line: 603 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): p_u_147 ]]
                        p_u_23._evt:fire_event_to_client(v_u_3.EVT_Pet_RankUpServerResponse, p_u_147, true, "")
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_3.EVT_Pet_DeleteClientRequest, function(p_u_161, p_u_162) --[[ Line: 610 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): v_u_20, (ref 4): v_u_6 ]]
                local function f_response(p163, p164) --[[ Name: response ]] --[[ Line: 611 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_161 ]]
                    p_u_23._evt:fire_event_to_client(v_u_3.EVT_Pet_DeleteServerResponse, p_u_161, p163, p164)
                end;
                p_u_23._player_blob_manager:get_verified_cached_blob(p_u_161.UserId, function(p_u_165) --[[ Line: 614 ]]
                    --[[ Upvalues: (copy 1): f_response, (ref 2): v_u_20, (copy 3): p_u_162, (ref 4): p_u_23, (copy 5): p_u_161, (ref 6): v_u_6, (ref 7): v_u_3 ]]
                    if p_u_165 == nil then
                        return f_response(false, "Err getting playerblob");
                    end;
                    if v_u_20:playerblob_get_pet_ownedid_ownedpet(p_u_165, p_u_162) == nil then
                        return f_response(false, "Pet not found");
                    end;
                    v_u_20:playerblob_unequip_pet_and_remove_from_loadouts(p_u_165, p_u_162)
                    p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_161.UserId, v_u_6.PlayerBlobRequestType.Write, function(_) --[[ Line: 622 ]]
                        --[[ Upvalues: (ref 1): v_u_20, (copy 2): p_u_165, (ref 3): p_u_162, (ref 4): p_u_23, (ref 5): p_u_161, (ref 6): v_u_6, (ref 7): v_u_3 ]]
                        v_u_20:playerblob_delete_pet_ownedid(p_u_165, p_u_162)
                        p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_161.UserId, v_u_6.PlayerBlobRequestType.Write, function(_) --[[ Line: 625 ]]
                            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): p_u_161 ]]
                            p_u_23._evt:fire_event_to_client(v_u_3.EVT_Pet_DeleteServerResponse, p_u_161, true, "")
                        end)
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_3.EVT_Pet_ClaimPetFromMaterialClientRequest, function(p_u_166, p_u_167) --[[ Line: 632 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): v_u_9, (ref 4): v_u_7, (ref 5): v_u_8, (ref 6): v_u_20, (ref 7): v_u_6 ]]
                local function f_response(p168, p169) --[[ Name: response ]] --[[ Line: 633 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_166 ]]
                    p_u_23._evt:fire_event_to_client(v_u_3.EVT_Pet_ClaimPetFromMaterialServerResponse, p_u_166, p168, p169)
                end;
                p_u_23._player_blob_manager:get_verified_cached_blob(p_u_166.UserId, function(p170) --[[ Line: 636 ]]
                    --[[ Upvalues: (copy 1): f_response, (ref 2): v_u_9, (copy 3): p_u_167, (ref 4): v_u_7, (ref 5): v_u_8, (ref 6): v_u_20, (ref 7): p_u_23, (copy 8): p_u_166, (ref 9): v_u_6, (ref 10): v_u_3 ]]
                    if p170 == nil then
                        return f_response(false, "Err getting playerblob");
                    end;
                    if v_u_9:get_count_of_material(p170, p_u_167) <= 0 then
                        return f_response(false, "Does not own count of material");
                    end;
                    if v_u_7:singleton():get_material_type(p_u_167) ~= v_u_8.Type.Pet then
                        return f_response(false, "Invalid material");
                    end;
                    local v171 = v_u_7:singleton():get_material(p_u_167):get_pet_id()
                    local v172, v173 = v_u_20:playerblob_can_add_pet_of_petid(p170, v171)
                    if v172 ~= true then
                        return f_response(false, v173);
                    end;
                    v_u_9:add_crafting_materials_of_id(p170, p_u_167, -1)
                    local v_u_174, v_u_175 = v_u_20:playerblob_add_pet_of_petid(p170, v171, true)
                    p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_166.UserId, v_u_6.PlayerBlobRequestType.Write, function(p176) --[[ Line: 651 ]]
                        --[[ Upvalues: (copy 1): v_u_174, (ref 2): v_u_20, (copy 3): v_u_175, (ref 4): p_u_23, (ref 5): p_u_166, (ref 6): v_u_6, (ref 7): v_u_3 ]]
                        if v_u_174 and v_u_20:playerblob_any_slot_free(p176) then
                            v_u_20:playerblob_equip_pet_ownedid(p176, v_u_175)
                            p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_166.UserId, v_u_6.PlayerBlobRequestType.Write, function(p177) --[[ Line: 654 ]]
                                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (ref 3): p_u_166 ]]
                                p_u_23._evt:fire_event_to_client(v_u_3.EVT_Pet_ClaimPetFromMaterialServerResponse, p_u_166, true, "")
                                p_u_23._lobby_manager:update_player_character_to_equipped_data(p_u_166, p177)
                            end)
                        else
                            p_u_23._evt:fire_event_to_client(v_u_3.EVT_Pet_ClaimPetFromMaterialServerResponse, p_u_166, true, "")
                        end;
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_3.EVT_Crafting_OpenBoxClient, function(p_u_178, p_u_179, p_u_180, p_u_181) --[[ Line: 665 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_15, (ref 3): v_u_5, (ref 4): p_u_23, (ref 5): v_u_3, (ref 6): v_u_9, (ref 7): v_u_16 ]]
                v_u_12:is_true(v_u_15:get_materialid_box_type(p_u_179) ~= v_u_15:type_invalid())
                v_u_12:is_true(p_u_181 > 0)
                v_u_12:is_true(p_u_181 < v_u_5:input_max_number())
                local function f_response(p182, p183, p184) --[[ Name: response ]] --[[ Line: 670 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_3, (copy 3): p_u_178 ]]
                    p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_OpenBoxServer, p_u_178, p182, p183, p184 == nil and {} or p184)
                end;
                p_u_23._player_blob_manager:get_verified_cached_blob(p_u_178.UserId, function(p185) --[[ Line: 674 ]]
                    --[[ Upvalues: (copy 1): f_response, (ref 2): v_u_9, (copy 3): p_u_179, (copy 4): p_u_181, (ref 5): v_u_15, (ref 6): p_u_23, (copy 7): p_u_178, (copy 8): p_u_180, (ref 9): v_u_16, (ref 10): v_u_3 ]]
                    if p185 == nil then
                        return f_response(false, "Err getting playerblob");
                    end;
                    if v_u_9:get_count_of_material(p185, p_u_179) < p_u_181 then
                        return f_response(false, "Does not own count of material");
                    end;
                    local v186 = v_u_15:server_player_get_reward_info_list_for_box_of_materialid(p_u_23, p_u_178, p_u_179, p_u_180, p_u_181)
                    v_u_9:add_crafting_materials_of_id(p185, p_u_179, -p_u_181)
                    local v_u_187 = v_u_16:claim_reward_info_list_to_playerblob(p_u_23, p185, v186)
                    v_u_16:server_sync_reward_params(p_u_23, p_u_178, v_u_187, function(p188) --[[ Line: 684 ]]
                        --[[ Upvalues: (ref 1): v_u_16, (copy 2): v_u_187, (ref 3): p_u_23, (ref 4): v_u_3, (ref 5): p_u_178 ]]
                        local v189 = v_u_16.RewardInfo:list_to_table(v_u_16:reward_params_get_resolved_reward_list(v_u_187))
                        p_u_23._evt:fire_event_to_client(v_u_3.EVT_Crafting_OpenBoxServer, p_u_178, true, p188, v189 == nil and {} or v189)
                    end)
                end)
            end)
        end;
        local v_u_190 = {
            {
                ["PriceType"] = v_u_6.CurrencyType.Coins,
                ["PriceValue"] = 100,
                ["SpinCount"] = 1
            },
            {
                ["PriceType"] = v_u_6.CurrencyType.Coins,
                ["PriceValue"] = 500,
                ["SpinCount"] = 5
            },
            {
                ["PriceType"] = v_u_6.CurrencyType.Coins,
                ["PriceValue"] = 1000,
                ["SpinCount"] = 10
            },
            {
                ["PriceType"] = v_u_6.CurrencyType.Coins,
                ["PriceValue"] = 10000,
                ["SpinCount"] = 100
            },
            {
                ["PriceType"] = v_u_6.CurrencyType.Stars,
                ["PriceValue"] = 1,
                ["SpinCount"] = 1
            },
            {
                ["PriceType"] = v_u_6.CurrencyType.Stars,
                ["PriceValue"] = 5,
                ["SpinCount"] = 5
            },
            {
                ["PriceType"] = v_u_6.CurrencyType.Stars,
                ["PriceValue"] = 10,
                ["SpinCount"] = 11,
                ["ExtraDisplay"] = 1
            },
            {
                ["PriceType"] = v_u_6.CurrencyType.Stars,
                ["PriceValue"] = 100,
                ["SpinCount"] = 115,
                ["ExtraDisplay"] = 15
            }
        }
        v24.get_updated_gatcha_info = function(_, p191) --[[ Name: get_updated_gatcha_info ]] --[[ Line: 736 ]]
            --[[ Upvalues: (copy 1): v_u_190 ]]
            p191(v_u_190)
        end;
        v24.crafting_gatcha_get_roll_result_materialid = function(_, p192) --[[ Name: crafting_gatcha_get_roll_result_materialid ]] --[[ Line: 740 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_5, (ref 3): v_u_10, (ref 4): v_u_17 ]]
            if p192 == v_u_6.CurrencyType.Stars then
                local v193 = v_u_5:rand_rangef(0, 100)
                if v193 < 5 then
                    return v_u_10:singleton():get_upgrade_boost_material_id();
                elseif v193 >= 5 and v193 < 10 then
                    return v_u_10:singleton():get_upgrade_protect_material_id();
                elseif v193 >= 10 and v193 < 20 then
                    return v_u_17:get_gem_material_ids():random();
                elseif v193 >= 20 and v193 < 40 then
                    return v_u_17:get_large_note_material_ids():random();
                else
                    return v_u_17:get_medium_note_material_ids():random();
                end;
            else
                local v194 = v_u_5:rand_rangef(0, 100)
                if v194 < 2 then
                    return v_u_10:singleton():get_upgrade_boost_material_id();
                elseif v194 >= 2 and v194 < 4 then
                    return v_u_10:singleton():get_upgrade_protect_material_id();
                elseif v194 >= 4 and v194 < 11 then
                    return v_u_17:get_gem_material_ids():random();
                elseif v194 >= 11 and v194 < 25 then
                    return v_u_17:get_large_note_material_ids():random();
                elseif v194 >= 25 and v194 < 55 then
                    return v_u_17:get_medium_note_material_ids():random();
                else
                    return v_u_17:get_small_note_material_ids():random();
                end;
            end;
        end;
        return v24;
    end
};
