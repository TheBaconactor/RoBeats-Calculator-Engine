-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:20 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_10 = require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_11 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_12 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_13 = require(game.ReplicatedStorage.Pets.PetAssignmentInfo)
local v_u_14 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_15 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_16 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_17 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
local v_u_18 = require(game.ReplicatedStorage.Shared.APICooldown)
local s_DataStoreService_0 = game:GetService("DataStoreService")
local v_u_19 = {}
local v_u_20 = v_u_9:new()
local v_u_21 = nil
v_u_3:ptry(function() --[[ Line: 32 ]]
    --[[ Upvalues: (ref 1): v_u_21, (copy 2): s_DataStoreService_0 ]]
    v_u_21 = s_DataStoreService_0:GetDataStore("PetAssignmentPlayerData")
end)
local function _(p22) --[[ Name: key_player_id ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    if v_u_3:is_dev_build() then
        return string.format("d_p%d", p22);
    else
        return string.format("p_%d", p22);
    end;
end;
v_u_19.datastore_write_player_assignment_data = function(_, p23, p24, p25, p_u_26) --[[ Name: datastore_write_player_assignment_data ]] --[[ Line: 39 ]]
    --[[ Upvalues: (ref 1): v_u_21, (copy 2): v_u_3 ]]
    local l__datastore_api_0 = p23._datastore_api
    local v27 = v_u_21
    local v28
    if v_u_3:is_dev_build() then
        v28 = string.format("d_p%d", p24)
    else
        v28 = string.format("p_%d", p24)
    end;
    l__datastore_api_0:do_datastore_set(v27, v28, p25:to_table(), function() --[[ Line: 40 ]]
        --[[ Upvalues: (copy 1): p_u_26 ]]
        if p_u_26 then
            p_u_26()
        end;
    end)
end;
v_u_19.datastore_get_player_assignment_data = function(_, p29, p_u_30, p_u_31) --[[ Name: datastore_get_player_assignment_data ]] --[[ Line: 44 ]]
    --[[ Upvalues: (copy 1): v_u_20, (ref 2): v_u_21, (copy 3): v_u_3, (copy 4): v_u_13 ]]
    if v_u_20:contains(p_u_30) then
        return p_u_31(v_u_20:get(p_u_30));
    end;
    local l__datastore_api_1 = p29._datastore_api
    local v32 = v_u_21
    local v33
    if v_u_3:is_dev_build() then
        v33 = string.format("d_p%d", p_u_30)
    else
        v33 = string.format("p_%d", p_u_30)
    end;
    l__datastore_api_1:do_datastore_get(v32, v33, function(_, p_u_34) --[[ Line: 49 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_13, (ref 3): v_u_20, (copy 4): p_u_30, (copy 5): p_u_31 ]]
        local v_u_35 = nil
        if typeof(p_u_34) == "table" then
            v_u_3:ptry(function() --[[ Line: 52 ]]
                --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_13, (copy 3): p_u_34 ]]
                v_u_35 = v_u_13.PlayerAssignmentData:from_table(p_u_34)
            end)
        end;
        if v_u_35 == nil then
            v_u_35 = v_u_13.PlayerAssignmentData:new()
        end;
        v_u_20:add(p_u_30, v_u_35)
        p_u_31(v_u_35)
    end)
end;
v_u_19.new = function(_, p_u_36) --[[ Name: new ]] --[[ Line: 65 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_8, (copy 3): v_u_2, (copy 4): v_u_19, (copy 5): v_u_18, (copy 6): v_u_13, (copy 7): v_u_5, (copy 8): v_u_9, (copy 9): v_u_11, (copy 10): v_u_16, (copy 11): v_u_10, (copy 12): v_u_17, (copy 13): v_u_6, (copy 14): v_u_1, (copy 15): v_u_14, (copy 16): v_u_15, (copy 17): v_u_4, (copy 18): v_u_12, (copy 19): v_u_20, (copy 20): v_u_3 ]]
    local v37 = {}
    v37.start = function(_) --[[ Name: start ]] --[[ Line: 68 ]]
        --[[ Upvalues: (copy 1): p_u_36, (ref 2): v_u_7, (ref 3): v_u_8, (ref 4): v_u_2, (ref 5): v_u_19, (ref 6): v_u_18, (ref 7): v_u_13, (ref 8): v_u_5, (ref 9): v_u_9, (ref 10): v_u_11, (ref 11): v_u_16, (ref 12): v_u_10, (ref 13): v_u_17, (ref 14): v_u_6, (ref 15): v_u_1, (ref 16): v_u_14, (ref 17): v_u_15, (ref 18): v_u_4, (ref 19): v_u_12 ]]
        p_u_36._evt:wait_on_event(v_u_7.EVT_PetAssignment_RequestData_Client, function(p_u_38) --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_2, (ref 3): v_u_19, (ref 4): p_u_36, (ref 5): v_u_7 ]]
            if v_u_8.PetAssignmentEnabled ~= true then
                return v_u_2:errf("EVT_LeaderboardEvent_ClientDebugLeaderboard PetAssignmentEnabled not enabled");
            end;
            v_u_19:datastore_get_player_assignment_data(p_u_36, p_u_38.UserId, function(p39) --[[ Line: 72 ]]
                --[[ Upvalues: (ref 1): p_u_36, (ref 2): v_u_7, (copy 3): p_u_38 ]]
                p_u_36._evt:fire_event_to_client(v_u_7.EVT_PetAssignment_RequestData_Server, p_u_38, p39:to_table())
            end)
        end)
        local v_u_40 = v_u_18:new():set_cooldown(5)
        p_u_36._evt:wait_on_event(v_u_7.EVT_PetAssignment_SendAssignment_Client, function(p_u_41, p_u_42) --[[ Line: 79 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_2, (copy 3): v_u_40, (ref 4): p_u_36, (ref 5): v_u_7, (ref 6): v_u_13, (ref 7): v_u_19, (ref 8): v_u_5, (ref 9): v_u_9, (ref 10): v_u_11, (ref 11): v_u_16, (ref 12): v_u_10, (ref 13): v_u_17, (ref 14): v_u_6 ]]
            if v_u_8.PetAssignmentEnabled ~= true then
                return v_u_2:errf("EVT_PetAssignment_SendAssignment_Client PetAssignmentEnabled not enabled");
            end;
            v_u_40:queue_key_request(p_u_41.UserId, function() --[[ Line: 85 ]]
                --[[ Upvalues: (ref 1): p_u_36, (ref 2): v_u_7, (copy 3): p_u_41, (ref 4): v_u_13, (copy 5): p_u_42, (ref 6): v_u_19, (ref 7): v_u_5, (ref 8): v_u_9, (ref 9): v_u_11, (ref 10): v_u_16, (ref 11): v_u_10, (ref 12): v_u_17, (ref 13): v_u_6 ]]
                local function f_response(p43, p44, p45, p46) --[[ Name: response ]] --[[ Line: 86 ]]
                    --[[ Upvalues: (ref 1): p_u_36, (ref 2): v_u_7, (ref 3): p_u_41 ]]
                    if p46 == nil then
                        p46 = false
                    end;
                    p_u_36._evt:fire_event_to_client(v_u_7.EVT_PetAssignment_SendAssignment_Server, p_u_41, p43, p44, p45:to_table(), p46)
                end;
                local v_u_47 = v_u_13.AssignmentData:from_table(p_u_42)
                p_u_36._player_blob_manager:get_verified_cached_blob(p_u_41.UserId, function(p_u_48) --[[ Line: 95 ]]
                    --[[ Upvalues: (ref 1): v_u_19, (ref 2): p_u_36, (ref 3): p_u_41, (ref 4): v_u_5, (copy 5): v_u_47, (copy 6): f_response, (ref 7): v_u_13, (ref 8): v_u_9, (ref 9): v_u_11, (ref 10): v_u_16, (ref 11): v_u_10, (ref 12): v_u_17, (ref 13): v_u_6, (ref 14): v_u_7 ]]
                    v_u_19:datastore_get_player_assignment_data(p_u_36, p_u_41.UserId, function(p_u_49) --[[ Line: 96 ]]
                        --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_36, (ref 3): v_u_47, (ref 4): f_response, (ref 5): v_u_13, (ref 6): v_u_9, (ref 7): v_u_11, (copy 8): p_u_48, (ref 9): v_u_16, (ref 10): v_u_10, (ref 11): v_u_19, (ref 12): p_u_41, (ref 13): v_u_17, (ref 14): v_u_6, (ref 15): v_u_7 ]]
                        local v50, v51 = v_u_5:is_event_active(p_u_36._api:get_day_event_list())
                        if v50 ~= true or v_u_5:get_playable_song_set(v51):contains(v_u_47:get_song_key()) ~= true then
                            return f_response(false, "Song was not in active event.", p_u_49);
                        end;
                        if p_u_49:get_assignment_datas():count() >= v_u_13:get_max_player_assignments() then
                            return f_response(false, "Max assignments reached.", p_u_49);
                        end;
                        local v52 = v_u_9:new()
                        local v53 = v_u_9:new()
                        for _, v54 in p_u_49:get_assignment_datas():key_itr() do
                            v52:add_set(v54:get_song_key())
                            for v55, _ in v54:get_pet_owned_id_set():key_itr() do
                                v53:add_set(v55)
                            end;
                        end;
                        if v52:contains(v_u_47:get_song_key()) then
                            return f_response(false, "Song already assigned.", p_u_49);
                        end;
                        for v56, _ in v_u_47:get_pet_owned_id_set():key_itr() do
                            if v53:contains(v56) then
                                return f_response(false, "Pet already assigned.", p_u_49);
                            end;
                        end;
                        local v57 = v_u_47:get_pet_owned_id_set()
                        if v57:count() > v_u_13:get_max_pets_in_assignment() or v57:count() <= 0 then
                            return f_response(false, "Invalid mini count.", p_u_49);
                        end;
                        local v58 = v_u_11:playerblob_get_ownedid_to_ownedpet_dict(p_u_48)
                        local v59 = p_u_49:get_used_pet_owned_id_set()
                        local v60 = v_u_9:new():add_set_from_table_list(v_u_16:songkey_get_color_list(v_u_47:get_song_key()):get_table())
                        for v61, _ in v57:key_itr() do
                            if v58:contains(v61) ~= true then
                                return f_response(false, "Invalid pet to assign.", p_u_49);
                            end;
                            if v59:contains(v61) then
                                return f_response(false, "Pet already assigned.", p_u_49);
                            end;
                            local v62 = v_u_10:singleton():get_data_for_petid((v_u_11:ownedpet_get_petid(v58:get(v61))))
                            if v62 == nil then
                                return f_response(false, "Invalid pet to assign.", p_u_49);
                            end;
                            local v63 = false
                            for _, v64 in v62:get_active_ranked_colors_list():key_itr() do
                                if v60:contains(v64) then
                                    v63 = true
                                    break;
                                end;
                            end;
                            if v63 ~= true then
                                return f_response(false, "Mini colors do not match song.", p_u_49);
                            end;
                        end;
                        v_u_47:set_end_time(p_u_36._api:get_global_time() + v_u_13:assignment_type_to_time_sec((v_u_47:get_assignment_type())))
                        p_u_49:get_assignment_datas():push_back(v_u_47)
                        v_u_19:datastore_write_player_assignment_data(p_u_36, p_u_41.UserId, p_u_49, function() --[[ Line: 170 ]]
                            --[[ Upvalues: (ref 1): p_u_36, (ref 2): p_u_41, (ref 3): v_u_17, (ref 4): v_u_6, (copy 5): p_u_49, (ref 6): v_u_7 ]]
                            p_u_36._player_blob_manager:get_verified_cached_blob(p_u_41.UserId, function(p65) --[[ Line: 171 ]]
                                --[[ Upvalues: (ref 1): v_u_17, (ref 2): p_u_36, (ref 3): p_u_41, (ref 4): v_u_6, (ref 5): p_u_49, (ref 6): v_u_7 ]]
                                if v_u_17:can_claim_daily_mission_type_playerblob_dayid_monthid(v_u_17.DailyMissionType.SendPetTraining, p65, p_u_36._api:get_day_id(), p_u_36._api:get_month_id()) == true then
                                    p_u_36._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_17.DailyMissionType.SendPetTraining, p65)
                                    p_u_36._player_blob_manager:enqueue_blob_sync_request(p_u_41.UserId, v_u_6.PlayerBlobRequestType.Write, function() --[[ Line: 177 ]]
                                        --[[ Upvalues: (ref 1): p_u_49, (ref 2): p_u_36, (ref 3): v_u_7, (ref 4): p_u_41 ]]
                                        local v66 = p_u_49
                                        local v67 = true
                                        if v67 == nil then
                                            v67 = false
                                        end;
                                        p_u_36._evt:fire_event_to_client(v_u_7.EVT_PetAssignment_SendAssignment_Server, p_u_41, true, "", v66:to_table(), v67)
                                    end)
                                else
                                    local v68 = p_u_49
                                    local v69 = nil
                                    if v69 == nil then
                                        v69 = false
                                    end;
                                    p_u_36._evt:fire_event_to_client(v_u_7.EVT_PetAssignment_SendAssignment_Server, p_u_41, true, "", v68:to_table(), v69)
                                end;
                            end)
                        end)
                    end)
                end)
            end)
        end)
        local v_u_70 = v_u_18:new():set_cooldown(2.5)
        p_u_36._evt:wait_on_event(v_u_7.EVT_PetAssignment_CancelAssignment_Client, function(p_u_71, p_u_72) --[[ Line: 194 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_8, (ref 3): v_u_2, (copy 4): v_u_70, (ref 5): p_u_36, (ref 6): v_u_7, (ref 7): v_u_19 ]]
            v_u_1:is_int(p_u_72)
            if v_u_8.PetAssignmentEnabled ~= true then
                return v_u_2:errf("EVT_PetAssignment_CancelAssignment_Client PetAssignmentEnabled not enabled");
            end;
            v_u_70:queue_key_request(p_u_71.UserId, function() --[[ Line: 197 ]]
                --[[ Upvalues: (ref 1): p_u_36, (ref 2): v_u_7, (copy 3): p_u_71, (ref 4): v_u_19, (copy 5): p_u_72 ]]
                local function f_response(p73, p74, p75) --[[ Name: response ]] --[[ Line: 198 ]]
                    --[[ Upvalues: (ref 1): p_u_36, (ref 2): v_u_7, (ref 3): p_u_71 ]]
                    p_u_36._evt:fire_event_to_client(v_u_7.EVT_PetAssignment_CancelAssignment_Server, p_u_71, p73, p74, p75:to_table())
                end;
                v_u_19:datastore_get_player_assignment_data(p_u_36, p_u_71.UserId, function(p_u_76) --[[ Line: 202 ]]
                    --[[ Upvalues: (ref 1): p_u_72, (copy 2): f_response, (ref 3): v_u_19, (ref 4): p_u_36, (ref 5): p_u_71, (ref 6): v_u_7 ]]
                    if p_u_72 < 1 or p_u_72 > p_u_76:get_assignment_datas():count() then
                        return f_response(false, "Invalid assignment", p_u_76);
                    end;
                    p_u_76:get_assignment_datas():remove_at(p_u_72)
                    v_u_19:datastore_write_player_assignment_data(p_u_36, p_u_71.UserId, p_u_76, function() --[[ Line: 208 ]]
                        --[[ Upvalues: (copy 1): p_u_76, (ref 2): p_u_36, (ref 3): v_u_7, (ref 4): p_u_71 ]]
                        p_u_36._evt:fire_event_to_client(v_u_7.EVT_PetAssignment_CancelAssignment_Server, p_u_71, true, "", p_u_76:to_table())
                    end)
                end)
            end)
        end)
        p_u_36._evt:wait_on_event(v_u_7.EVT_PetAssignment_ClaimRewards_Client, function(p_u_77, p_u_78) --[[ Line: 216 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_8, (ref 3): v_u_2, (ref 4): p_u_36, (ref 5): v_u_7, (ref 6): v_u_19, (ref 7): v_u_16, (ref 8): v_u_14, (ref 9): v_u_11, (ref 10): v_u_15, (ref 11): v_u_4, (ref 12): v_u_5, (ref 13): v_u_13, (ref 14): v_u_9, (ref 15): v_u_10, (ref 16): v_u_12 ]]
            v_u_1:is_int(p_u_78)
            if v_u_8.PetAssignmentEnabled ~= true then
                return v_u_2:errf("EVT_PetAssignment_ClaimRewards_Client PetAssignmentEnabled not enabled");
            end;
            local function f_response(p79, p80, p81) --[[ Name: response ]] --[[ Line: 220 ]]
                --[[ Upvalues: (ref 1): p_u_36, (ref 2): v_u_7, (copy 3): p_u_77 ]]
                p_u_36._evt:fire_event_to_client(v_u_7.EVT_PetAssignment_ClaimRewards_Server, p_u_77, p79, p80, p81:to_table())
            end;
            p_u_36._player_blob_manager:get_verified_cached_blob(p_u_77.UserId, function(p_u_82) --[[ Line: 224 ]]
                --[[ Upvalues: (ref 1): v_u_19, (ref 2): p_u_36, (copy 3): p_u_77, (copy 4): p_u_78, (copy 5): f_response, (ref 6): v_u_16, (ref 7): v_u_14, (ref 8): v_u_11, (ref 9): v_u_15, (ref 10): v_u_4, (ref 11): v_u_5, (ref 12): v_u_13, (ref 13): v_u_9, (ref 14): v_u_10, (ref 15): v_u_12, (ref 16): v_u_2, (ref 17): v_u_7 ]]
                v_u_19:datastore_get_player_assignment_data(p_u_36, p_u_77.UserId, function(p_u_83) --[[ Line: 225 ]]
                    --[[ Upvalues: (ref 1): p_u_78, (ref 2): f_response, (ref 3): p_u_36, (ref 4): v_u_19, (ref 5): p_u_77, (ref 6): v_u_16, (ref 7): v_u_14, (ref 8): v_u_11, (copy 9): p_u_82, (ref 10): v_u_15, (ref 11): v_u_4, (ref 12): v_u_5, (ref 13): v_u_13, (ref 14): v_u_9, (ref 15): v_u_10, (ref 16): v_u_12, (ref 17): v_u_2, (ref 18): v_u_7 ]]
                    if p_u_78 < 1 or p_u_78 > p_u_83:get_assignment_datas():count() then
                        return f_response(false, "Invalid assignment", p_u_83);
                    end;
                    local v_u_84 = p_u_83:get_assignment_datas():get(p_u_78)
                    if v_u_84:get_end_time() > p_u_36._api:get_global_time() then
                        return f_response(false, "Assignment not completed yet.", p_u_83);
                    end;
                    p_u_83:get_assignment_datas():remove_at(p_u_78)
                    v_u_19:datastore_write_player_assignment_data(p_u_36, p_u_77.UserId, p_u_83, function() --[[ Line: 237 ]]
                        --[[ Upvalues: (ref 1): v_u_16, (copy 2): v_u_84, (ref 3): v_u_14, (ref 4): v_u_11, (ref 5): p_u_82, (ref 6): v_u_15, (ref 7): v_u_4, (ref 8): v_u_5, (ref 9): p_u_36, (ref 10): v_u_13, (ref 11): v_u_9, (ref 12): v_u_10, (ref 13): v_u_12, (ref 14): p_u_77, (ref 15): v_u_2, (copy 16): p_u_83, (ref 17): v_u_7 ]]
                        local v85 = v_u_16:songkey_get_color_list(v_u_84:get_song_key())
                        local v86 = 0
                        for v87, _ in v_u_84:get_pet_owned_id_set():key_itr() do
                            local v88 = v_u_14:statsdict_base()
                            v_u_11:playerblob_apply_pet_ownedid_statsdict(p_u_82, v87, v88)
                            v86 = v86 + v_u_15:statsdict_get_gear_power(v88, true, v85)
                        end;
                        local v89 = v_u_4:new()
                        local v90, v91 = v_u_5:is_event_active(p_u_36._api:get_day_event_list())
                        local v_u_92 = v_u_4:new()
                        local v_u_93 = v_u_13:get_exp_gain_for_assignment_type_and_gear_power(v_u_84:get_assignment_type(), v86)
                        local v_u_94 = v_u_9:new()
                        local v95 = v_u_11:playerblob_get_ownedid_to_ownedpet_dict(p_u_82)
                        for v96, _ in v_u_84:get_pet_owned_id_set():key_itr() do
                            if v95:contains(v96) then
                                local v97 = v_u_11:ownedpet_get_petid(v95:get(v96))
                                local v98 = v_u_10:singleton():get_data_for_petid(v97)
                                if v98 then
                                    local v99 = v98:get_name()
                                    v_u_92:push_back(v99)
                                    local v100
                                    if v_u_93 == v_u_93 and v90 and v_u_5:get_event_pet_ids_set(v91):contains(v97) then
                                        v100 = v_u_13:round_val(v_u_93 * 4)
                                    else
                                        v100 = v_u_93
                                    end;
                                    if v100 == v_u_93 and v_u_16:does_color_lists_match(v98:get_active_ranked_colors_list(), v85) then
                                        v100 = v_u_13:round_val(v100 * 2)
                                    end;
                                    v_u_94:add(v99, v100)
                                    v_u_11:ownedpet_apply_exp_gain(v95:get(v96), v100)
                                end;
                            end;
                        end;
                        local v_u_101 = v90 and v_u_5:get_playable_song_set(v91):contains(v_u_84:get_song_key()) ~= true and 0 or v_u_13:get_event_point_gain_for_assignment_type_and_gear_power(v_u_84:get_assignment_type(), v86)
                        if v_u_101 > 0 then
                            v89:push_back(v_u_12.RewardInfo:new(v_u_12.RewardType.EventPoints, v_u_101, -1))
                        end;
                        local v_u_102 = v_u_13:get_team_contribution_point_gain_for_assignment_type_and_gear_power(v_u_84:get_assignment_type(), v86)
                        local v103, _ = p_u_36._guild_manager:is_player_in_guild(p_u_77.UserId)
                        if v103 then
                            v89:push_back(v_u_12.RewardInfo:new(v_u_12.RewardType.TeamContributionPointsFromDailySongMission, v_u_102, -1))
                        end;
                        v_u_12:server_sync_reward_params(p_u_36, p_u_77, v_u_12:claim_reward_info_list_to_playerblob(p_u_36, p_u_82, v89), function(_, _, _) --[[ Line: 332 ]]
                            --[[ Upvalues: (ref 1): v_u_101, (copy 2): v_u_102, (copy 3): v_u_92, (copy 4): v_u_93, (copy 5): v_u_94, (ref 6): v_u_2, (ref 7): p_u_83, (ref 8): p_u_36, (ref 9): v_u_7, (ref 10): p_u_77 ]]
                            local v104 = ""
                            if v_u_101 > 0 then
                                v104 = v104 .. string.format("- %d Event Points.\n", v_u_101)
                            end;
                            if v_u_102 > 0 then
                                v104 = v104 .. string.format("- %d Team Contribution Points.\n", v_u_102)
                            end;
                            for _, v105 in v_u_92:key_itr() do
                                local v106 = v_u_93
                                if v_u_94:contains(v105) then
                                    v106 = v_u_94:get(v105)
                                else
                                    v_u_2:warnf("PetAssignmentManager:ClaimRewards pet_name(%s) not found in pet_name_to_earned_exp", v105)
                                end;
                                v104 = v104 .. string.format("- Mini \'%s\' earned %d EXP.\n", v105, v106)
                            end;
                            p_u_36._evt:fire_event_to_client(v_u_7.EVT_PetAssignment_ClaimRewards_Server, p_u_77, true, v104, p_u_83:to_table())
                        end)
                    end)
                end)
            end)
        end)
    end;
    v37.player_disconnecting = function(_, p107) --[[ Name: player_disconnecting ]] --[[ Line: 360 ]]
        --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_3, (ref 3): v_u_2 ]]
        v_u_20:remove(p107)
        if v_u_3:is_dev_build() then
            v_u_2:puts("ServerPetAssignmentManager:player_disconnecting(%d) cached(%d)", p107, v_u_20:count())
        end;
    end;
    return v37;
end;
return v_u_19;
