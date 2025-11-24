-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:20 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.Override)
local v_u_10 = require(game.ReplicatedStorage.Shared.AudioRank)
require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_11 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.RBGamesEventInfo)
require(game.ReplicatedStorage.Server.ServerDataStoreAPIManager)
local v_u_13 = require(game.ReplicatedStorage.Shared.MissionType)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.FeverIconInfo)
local v_u_15 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v17 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_18 = nil
v17:require_server(function() --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_18 ]]
    v_u_18 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
local s_BadgeService_0 = game:GetService("BadgeService")
local s_DataStoreService_0 = game:GetService("DataStoreService")
local v19 = {}
local v_u_30 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 33 ]]
        --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_2 ]]
        local v20 = {}
        local v_u_21 = 0
        v20.get_multiplayer_song_complete_count = function(_) --[[ Name: get_multiplayer_song_complete_count ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21;
        end;
        v20.increment_multiplayer_song_complete_count = function(_) --[[ Name: increment_multiplayer_song_complete_count ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21 = v_u_21 + 1
        end;
        local v_u_22 = 0
        v20.get_song_complete_count = function(_) --[[ Name: get_song_complete_count ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22;
        end;
        v20.increment_song_complete_count = function(_) --[[ Name: increment_song_complete_count ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            v_u_22 = v_u_22 + 1
        end;
        local v_u_23 = v_u_12.PlayerProgress:new()
        local v_u_24 = true
        local v_u_25 = v_u_2:new()
        v20.update_cached_player_progress = function(_, p26) --[[ Name: update_cached_player_progress ]] --[[ Line: 47 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24, (copy 3): v_u_25 ]]
            v_u_23 = p26
            v_u_24 = false
            for _, v27 in v_u_25:key_itr() do
                v27(v_u_23)
            end;
            v_u_25:clear()
        end;
        v20.get_player_progress = function(_, p28) --[[ Name: get_player_progress ]] --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_24, (copy 2): v_u_25, (ref 3): v_u_23 ]]
            if v_u_24 == true then
                v_u_25:push_back(p28)
            else
                p28(v_u_23)
            end;
        end;
        v20.get_cached_player_progress = function(_) --[[ Name: get_cached_player_progress ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23;
        end;
        v20.flag_waiting_player_progress_update = function(_) --[[ Name: flag_waiting_player_progress_update ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            v_u_24 = true
        end;
        v20.reset_data = function(p29) --[[ Name: reset_data ]] --[[ Line: 68 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_22 ]]
            v_u_21 = 0
            v_u_22 = 0
            p29:flag_waiting_player_progress_update()
        end;
        v20.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 74 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_22 ]]
            return {
                ["MultiplayerSongCompleteCount"] = v_u_21,
                ["SongCompleteCount"] = v_u_22
            };
        end;
        return v20;
    end
}
v19.new = function(_, p_u_31) --[[ Name: new ]] --[[ Line: 84 ]]
    --[[ Upvalues: (ref 1): v_u_18, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_7, (copy 5): v_u_12, (copy 6): v_u_11, (copy 7): v_u_16, (copy 8): v_u_1, (copy 9): v_u_2, (copy 10): s_BadgeService_0, (copy 11): v_u_8, (copy 12): v_u_5, (copy 13): v_u_14, (copy 14): v_u_15, (copy 15): v_u_9, (copy 16): v_u_30, (copy 17): v_u_10, (copy 18): v_u_6, (copy 19): v_u_13, (copy 20): s_DataStoreService_0 ]]
    local v_u_32 = v_u_18.EventBase:new()
    local v_u_33 = v_u_3:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 89 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_31, (ref 3): v_u_7, (ref 4): v_u_12, (copy 5): v_u_33, (copy 6): v_u_32, (ref 7): v_u_3, (ref 8): v_u_11, (ref 9): v_u_16, (ref 10): v_u_1, (ref 11): v_u_2, (ref 12): s_BadgeService_0, (ref 13): v_u_8, (ref 14): v_u_5, (ref 15): v_u_14, (ref 16): v_u_15 ]]
        v_u_4:puts("RBGamesSpecialEvent cons")
        p_u_31._evt:wait_on_event(v_u_7.EVT_SpecialEvent_RBGames_GetData_Client, function(p_u_34) --[[ Line: 92 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_7, (ref 3): v_u_12, (ref 4): v_u_4, (ref 5): v_u_33 ]]
            local function _(p35, p36) --[[ Name: response ]] --[[ Line: 93 ]]
                --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_7, (copy 3): p_u_34 ]]
                p_u_31._evt:fire_event_to_client(v_u_7.EVT_SpecialEvent_RBGames_GetData_Server, p_u_34, p35:to_table(), p36:to_table())
            end;
            local l_UserId_0 = p_u_34.UserId
            if v_u_12:day_event_list_playerblob_is_event_active(p_u_31._api:get_day_event_list(), p_u_31._player_blob_manager:get_cached_blob(l_UserId_0)) ~= true then
                return v_u_4:warnf("EVT_SpecialEvent_RBGames_GetData_Client event not active");
            end;
            if v_u_33:contains(l_UserId_0) ~= true then
                return v_u_4:warnf("EVT_SpecialEvent_RBGames_GetData_Client player not found _playerid_to_event_player_tracked_server_info");
            end;
            local v_u_37 = v_u_33:get(l_UserId_0)
            v_u_37:get_player_progress(function(p38) --[[ Line: 101 ]]
                --[[ Upvalues: (copy 1): v_u_37, (ref 2): p_u_31, (ref 3): v_u_7, (copy 4): p_u_34 ]]
                p_u_31._evt:fire_event_to_client(v_u_7.EVT_SpecialEvent_RBGames_GetData_Server, p_u_34, p38:to_table(), v_u_37:to_table())
            end)
        end)
        p_u_31._evt:wait_on_event(v_u_7.EVT_SpecialEvent_RBGames_ResetData_Client, function(p_u_39) --[[ Line: 106 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_31, (ref 3): v_u_4, (ref 4): v_u_33, (ref 5): v_u_32, (ref 6): v_u_7 ]]
            local l_UserId_1 = p_u_39.UserId
            if v_u_12:day_event_list_playerblob_is_event_active(p_u_31._api:get_day_event_list(), p_u_31._player_blob_manager:get_cached_blob(l_UserId_1)) ~= true then
                return v_u_4:warnf("EVT_SpecialEvent_RBGames_ResetData_Client event not active");
            end;
            if v_u_33:contains(l_UserId_1) ~= true then
                return v_u_4:warnf("EVT_SpecialEvent_RBGames_ResetData_Client player not found _playerid_to_event_player_tracked_server_info");
            end;
            local v_u_40 = v_u_33:get(l_UserId_1)
            v_u_40:reset_data()
            v_u_32:datastore_write_player_progress(l_UserId_1, v_u_12.PlayerProgress:new(), function(p41) --[[ Line: 112 ]]
                --[[ Upvalues: (copy 1): v_u_40, (ref 2): p_u_31, (ref 3): v_u_7, (copy 4): p_u_39 ]]
                v_u_40:update_cached_player_progress(p41)
                p_u_31._evt:fire_event_to_client(v_u_7.EVT_SpecialEvent_RBGames_ResetData_Server, p_u_39)
            end)
        end)
        local v_u_42 = v_u_3:new({
            [v_u_12.ProgressFlags.Quest1] = 173523987621458,
            [v_u_12.ProgressFlags.Quest2] = 3189416353042801,
            [v_u_12.ProgressFlags.Quest3] = 4256186018262030,
            [v_u_12.ProgressFlags.Item1] = 367480310369072,
            [v_u_12.ProgressFlags.Item2] = 2535724711331359,
            [v_u_12.ProgressFlags.Item3] = 750021456160606,
            [v_u_12.ProgressFlags.Item4] = 3903612469312832,
            [v_u_12.ProgressFlags.Item5] = 3587876891658455
        })
        local v_u_43 = v_u_3:new():add_set_from_table_list({
            v_u_12.ProgressFlags.Item1,
            v_u_12.ProgressFlags.Item2,
            v_u_12.ProgressFlags.Item3,
            v_u_12.ProgressFlags.Item4,
            v_u_12.ProgressFlags.Item5
        })
        local v_u_44 = v_u_3:new():add_set_from_table_list({ v_u_12.ProgressFlags.Quest1, v_u_12.ProgressFlags.Quest2, v_u_12.ProgressFlags.Quest3 })
        local function f_player_progress_flag_is_member_of_set_and_all_in_set_are_claimed(p45, p46, p47) --[[ Name: player_progress_flag_is_member_of_set_and_all_in_set_are_claimed ]] --[[ Line: 153 ]]
            if p47:contains(p46) ~= true then
                return false;
            end;
            for v48, _ in p47:key_itr() do
                if p45:get_progress_flag(v48) ~= true then
                    return false;
                end;
            end;
            return true;
        end;
        local v_u_49 = v_u_11.RewardInfo:new(v_u_11.RewardType.Gear, 1, 235)
        local v_u_50 = v_u_11.RewardInfo:new(v_u_11.RewardType.Gear, 1, 236)
        local v_u_51 = v_u_11.RewardInfo:new(v_u_11.RewardType.Titles, 1, 133)
        local v_u_52 = v_u_11.RewardInfo:new(v_u_11.RewardType.CraftingMaterials, 1, v_u_16:singleton():get_fevericon_for_id(200):get_material_id())
        p_u_31._evt:wait_on_event(v_u_7.EVT_SpecialEvent_RBGames_ClaimProgress_Client, function(p_u_53, p_u_54) --[[ Line: 173 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_12, (ref 3): p_u_31, (ref 4): v_u_7, (ref 5): v_u_11, (ref 6): v_u_4, (ref 7): v_u_33, (ref 8): v_u_2, (copy 9): v_u_42, (ref 10): s_BadgeService_0, (ref 11): v_u_8, (copy 12): v_u_44, (ref 13): v_u_5, (copy 14): v_u_51, (copy 15): f_player_progress_flag_is_member_of_set_and_all_in_set_are_claimed, (copy 16): v_u_43, (ref 17): v_u_14, (copy 18): v_u_52, (ref 19): v_u_15, (copy 20): v_u_50, (copy 21): v_u_49, (ref 22): v_u_32 ]]
            v_u_1:is_enum_member(p_u_54, v_u_12.ProgressFlags)
            local function _(p55, p56, p57) --[[ Name: response ]] --[[ Line: 176 ]]
                --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_7, (copy 3): p_u_53, (ref 4): v_u_11 ]]
                p_u_31._evt:fire_event_to_client(v_u_7.EVT_SpecialEvent_RBGames_ClaimProgress_Server, p_u_53, p55, p56, v_u_11.RewardInfo:list_to_table(p57))
            end;
            local l_UserId_2 = p_u_53.UserId
            if v_u_12:day_event_list_playerblob_is_event_active(p_u_31._api:get_day_event_list(), p_u_31._player_blob_manager:get_cached_blob(l_UserId_2)) ~= true then
                return v_u_4:warnf("EVT_SpecialEvent_RBGames_ClaimProgress_Client event not active");
            end;
            if v_u_33:contains(l_UserId_2) ~= true then
                return v_u_4:warnf("EVT_SpecialEvent_RBGames_ClaimProgress_Client player not found _playerid_to_event_player_tracked_server_info");
            end;
            v_u_33:get(l_UserId_2):get_player_progress(function(p_u_58) --[[ Line: 184 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_12, (copy 3): p_u_54, (ref 4): v_u_42, (ref 5): s_BadgeService_0, (copy 6): l_UserId_2, (ref 7): v_u_8, (ref 8): p_u_31, (ref 9): v_u_44, (ref 10): v_u_5, (ref 11): v_u_51, (ref 12): f_player_progress_flag_is_member_of_set_and_all_in_set_are_claimed, (ref 13): v_u_43, (ref 14): v_u_14, (ref 15): v_u_52, (ref 16): v_u_15, (ref 17): v_u_50, (ref 18): v_u_49, (copy 19): p_u_53, (ref 20): v_u_11, (ref 21): v_u_7, (ref 22): v_u_32 ]]
                local v_u_59 = v_u_2:new()
                local v_u_60, v61
                if v_u_12:player_progress_can_claim_event_flag(p_u_58, p_u_54) == true then
                    p_u_58:set_progress_flag(p_u_54)
                    spawn(function() --[[ Line: 190 ]]
                        --[[ Upvalues: (ref 1): v_u_42, (ref 2): p_u_54, (ref 3): s_BadgeService_0, (ref 4): l_UserId_2 ]]
                        if v_u_42:contains(p_u_54) then
                            s_BadgeService_0:AwardBadge(l_UserId_2, v_u_42:get(p_u_54))
                        end;
                    end)
                    v_u_60 = string.format("Completed: %s Badge has been awarded!", v_u_12:get_progress_flag_to_description():get(p_u_54))
                    v_u_8:ptry(function() --[[ Line: 198 ]]
                        --[[ Upvalues: (ref 1): p_u_31, (ref 2): l_UserId_2, (ref 3): v_u_44, (ref 4): p_u_54, (ref 5): v_u_5, (copy 6): v_u_59, (ref 7): v_u_51, (ref 8): f_player_progress_flag_is_member_of_set_and_all_in_set_are_claimed, (copy 9): p_u_58, (ref 10): v_u_43, (ref 11): v_u_14, (ref 12): v_u_52, (ref 13): v_u_15, (ref 14): v_u_50, (ref 15): v_u_12, (ref 16): v_u_49 ]]
                        local v62 = p_u_31._player_blob_manager:get_cached_blob(l_UserId_2)
                        if v_u_44:contains(p_u_54) and v_u_5:owns_title_id(v62, 133) ~= true then
                            v_u_59:push_back(v_u_51)
                        end;
                        if f_player_progress_flag_is_member_of_set_and_all_in_set_are_claimed(p_u_58, p_u_54, v_u_43) and v_u_14:get_playerblob_fevericon_owned_set(v62, 0, p_u_31._collection_manager:get_collection_info_for_player_id_playerblob(l_UserId_2, v62)):contains(200) ~= true then
                            v_u_59:push_back(v_u_52)
                        end;
                        if f_player_progress_flag_is_member_of_set_and_all_in_set_are_claimed(p_u_58, p_u_54, v_u_44) and v_u_15:playerblob_get_owned_count_of_equipmentid(v62, 236) == 0 then
                            v_u_59:push_back(v_u_50)
                        end;
                        if p_u_54 == v_u_12.ProgressFlags.CompleteAll and v_u_15:playerblob_get_owned_count_of_equipmentid(v62, 235) == 0 then
                            v_u_59:push_back(v_u_49)
                        end;
                    end)
                    v61 = true
                else
                    v_u_60 = "Already claimed!"
                    v61 = false
                end;
                local function f_finish() --[[ Name: finish ]] --[[ Line: 237 ]]
                    --[[ Upvalues: (copy 1): v_u_59, (ref 2): p_u_31, (ref 3): p_u_53, (ref 4): v_u_11, (ref 5): v_u_60, (ref 6): v_u_7 ]]
                    if v_u_59:count() > 0 then
                        p_u_31._player_blob_manager:get_verified_cached_blob(p_u_53.UserId, function(p63) --[[ Line: 239 ]]
                            --[[ Upvalues: (ref 1): v_u_11, (ref 2): p_u_31, (ref 3): v_u_59, (ref 4): p_u_53, (ref 5): v_u_60, (ref 6): v_u_7 ]]
                            local v_u_64 = v_u_11:claim_reward_info_list_to_playerblob(p_u_31, p63, v_u_59)
                            v_u_11:server_sync_reward_params(p_u_31, p_u_53, v_u_64, function() --[[ Line: 241 ]]
                                --[[ Upvalues: (ref 1): v_u_60, (ref 2): v_u_11, (copy 3): v_u_64, (ref 4): p_u_31, (ref 5): v_u_7, (ref 6): p_u_53 ]]
                                p_u_31._evt:fire_event_to_client(v_u_7.EVT_SpecialEvent_RBGames_ClaimProgress_Server, p_u_53, true, v_u_60, v_u_11.RewardInfo:list_to_table((v_u_11:reward_params_get_resolved_reward_list(v_u_64))))
                            end)
                        end)
                    else
                        p_u_31._evt:fire_event_to_client(v_u_7.EVT_SpecialEvent_RBGames_ClaimProgress_Server, p_u_53, true, v_u_60, v_u_11.RewardInfo:list_to_table(v_u_59))
                    end;
                end;
                if v61 then
                    v_u_32:datastore_write_player_progress(l_UserId_2, p_u_58, function() --[[ Line: 251 ]]
                        --[[ Upvalues: (copy 1): f_finish ]]
                        f_finish()
                    end)
                else
                    f_finish()
                end;
            end)
        end)
    end;
    v_u_9:get_base_fn(v_u_32, "player_connecting")
    v_u_32.player_connecting = function(p65, p66) --[[ Name: player_connecting ]] --[[ Line: 262 ]]
        --[[ Upvalues: (ref 1): v_u_30, (copy 2): v_u_33 ]]
        local v_u_67 = v_u_30:new()
        v_u_33:add(p66, v_u_67)
        p65:datastore_get_player_progress(p66, function(p68) --[[ Line: 265 ]]
            --[[ Upvalues: (copy 1): v_u_67 ]]
            v_u_67:update_cached_player_progress(p68)
        end)
    end;
    v_u_9:get_base_fn(v_u_32, "player_disconnecting")
    v_u_32.player_disconnecting = function(_, p69) --[[ Name: player_disconnecting ]] --[[ Line: 271 ]]
        --[[ Upvalues: (copy 1): v_u_33 ]]
        v_u_33:remove(p69)
    end;
    v_u_9:get_base_fn(v_u_32, "can_playerid_start_songkey")
    v_u_32.can_playerid_start_songkey = function(_, _, _, _) --[[ Name: can_playerid_start_songkey ]] --[[ Line: 276 ]]
        return false;
    end;
    local function f_log_task_complete_message(p70, p71, p72) --[[ Name: log_task_complete_message ]] --[[ Line: 280 ]]
        --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_4, (ref 3): v_u_12 ]]
        local v73 = p_u_31._player_manager:id_to_player(p70)
        if v73 == nil then
            return v_u_4:warnf("log_task_complete_message-1");
        end;
        local v74 = v_u_12:get_task_flag_to_name():get(p72)
        if v74 == nil then
            return v_u_4:warnf("log_task_complete_message-2");
        end;
        p_u_31._chat:get_chat_service():send_system_message_to_player_for_channel(v73, p_u_31._chat:get_chat_service():get_channel(p_u_31._chat:get_chat_service():get_server_system_channel_id()), string.format("Completed The Games event task: %s - Current points: %d", v74, p71:calculate_task_points()), function(p75) --[[ Line: 289 ]]
            p75:set_channel_name("")
            p75:set_icon("rbxassetid://18686397838")
        end)
    end;
    local function _(p76, p77, p78, p79) --[[ Name: write_player_id_player_progress_task_flag_if_available ]] --[[ Line: 296 ]]
        --[[ Upvalues: (copy 1): f_log_task_complete_message ]]
        if p77:get_task_flag(p78) ~= true then
            p77:set_task_flag(p78)
            f_log_task_complete_message(p76, p77, p78)
            if p79 then
                p79(p76, p77, p78)
            end;
        end;
    end;
    v_u_9:get_base_fn(v_u_32, "write_special_event_data_for_play")
    v_u_32.write_special_event_data_for_play = function(p80, _, p81, p82, p83, p84, _, _) --[[ Name: write_special_event_data_for_play ]] --[[ Line: 305 ]]
        --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_31, (copy 3): v_u_33, (copy 4): f_log_task_complete_message, (ref 5): v_u_10, (ref 6): v_u_6 ]]
        local l__id_0 = p84._id
        if v_u_12:day_event_list_playerblob_is_event_active(p_u_31._api:get_day_event_list(), p_u_31._player_blob_manager:get_cached_blob(l__id_0)) == true then
            if v_u_33:contains(l__id_0) == true then
                local v85 = v_u_33:get(l__id_0)
                v85:increment_song_complete_count()
                if p83 >= 3 then
                    v85:increment_multiplayer_song_complete_count()
                end;
                local v86 = v85:get_cached_player_progress()
                local v_u_87 = false
                if v85:get_multiplayer_song_complete_count() >= 3 then
                    local l_Complete3MultiplayerSongs_0 = v_u_12.TaskFlags.Complete3MultiplayerSongs
                    local function v88() --[[ Line: 320 ]]
                        --[[ Upvalues: (ref 1): v_u_87 ]]
                        v_u_87 = true
                    end;
                    if v86:get_task_flag(l_Complete3MultiplayerSongs_0) ~= true then
                        v86:set_task_flag(l_Complete3MultiplayerSongs_0)
                        f_log_task_complete_message(l__id_0, v86, l_Complete3MultiplayerSongs_0)
                        if v88 then
                            v88(l__id_0, v86, l_Complete3MultiplayerSongs_0)
                        end;
                    end;
                end;
                if p83 >= 3 and p82 == 1 then
                    local l_WinMultiplayerMatch_0 = v_u_12.TaskFlags.WinMultiplayerMatch
                    local function v89() --[[ Line: 325 ]]
                        --[[ Upvalues: (ref 1): v_u_87 ]]
                        v_u_87 = true
                    end;
                    if v86:get_task_flag(l_WinMultiplayerMatch_0) ~= true then
                        v86:set_task_flag(l_WinMultiplayerMatch_0)
                        f_log_task_complete_message(l__id_0, v86, l_WinMultiplayerMatch_0)
                        if v89 then
                            v89(l__id_0, v86, l_WinMultiplayerMatch_0)
                        end;
                    end;
                end;
                if v85:get_song_complete_count() >= 5 then
                    local l_Complete5Songs_0 = v_u_12.TaskFlags.Complete5Songs
                    local function v90() --[[ Line: 330 ]]
                        --[[ Upvalues: (ref 1): v_u_87 ]]
                        v_u_87 = true
                    end;
                    if v86:get_task_flag(l_Complete5Songs_0) ~= true then
                        v86:set_task_flag(l_Complete5Songs_0)
                        f_log_task_complete_message(l__id_0, v86, l_Complete5Songs_0)
                        if v90 then
                            v90(l__id_0, v86, l_Complete5Songs_0)
                        end;
                    end;
                end;
                if v85:get_song_complete_count() >= 10 then
                    local l_Complete10Songs_0 = v_u_12.TaskFlags.Complete10Songs
                    local function v91() --[[ Line: 335 ]]
                        --[[ Upvalues: (ref 1): v_u_87 ]]
                        v_u_87 = true
                    end;
                    if v86:get_task_flag(l_Complete10Songs_0) ~= true then
                        v86:set_task_flag(l_Complete10Songs_0)
                        f_log_task_complete_message(l__id_0, v86, l_Complete10Songs_0)
                        if v91 then
                            v91(l__id_0, v86, l_Complete10Songs_0)
                        end;
                    end;
                end;
                if p84._accuracy >= v_u_10:rank_value_to_accuracy(v_u_10.Value.RankB) then
                    local v92 = v_u_6:singleton():get_difficulty_for_key(p81)
                    local v93 = v_u_6:singleton():key_is_vip(p81)
                    if v92 >= 1 and v92 <= 10 then
                        local l_CompleteSongDiffA_0 = v_u_12.TaskFlags.CompleteSongDiffA
                        local function v94() --[[ Line: 346 ]]
                            --[[ Upvalues: (ref 1): v_u_87 ]]
                            v_u_87 = true
                        end;
                        if v86:get_task_flag(l_CompleteSongDiffA_0) ~= true then
                            v86:set_task_flag(l_CompleteSongDiffA_0)
                            f_log_task_complete_message(l__id_0, v86, l_CompleteSongDiffA_0)
                            if v94 then
                                v94(l__id_0, v86, l_CompleteSongDiffA_0)
                            end;
                        end;
                    end;
                    if v92 >= 11 and v92 <= 21 then
                        local l_CompleteSongDiffB_0 = v_u_12.TaskFlags.CompleteSongDiffB
                        local function v95() --[[ Line: 351 ]]
                            --[[ Upvalues: (ref 1): v_u_87 ]]
                            v_u_87 = true
                        end;
                        if v86:get_task_flag(l_CompleteSongDiffB_0) ~= true then
                            v86:set_task_flag(l_CompleteSongDiffB_0)
                            f_log_task_complete_message(l__id_0, v86, l_CompleteSongDiffB_0)
                            if v95 then
                                v95(l__id_0, v86, l_CompleteSongDiffB_0)
                            end;
                        end;
                    end;
                    if v92 >= 22 then
                        local l_CompleteSongDiffC_0 = v_u_12.TaskFlags.CompleteSongDiffC
                        local function v96() --[[ Line: 356 ]]
                            --[[ Upvalues: (ref 1): v_u_87 ]]
                            v_u_87 = true
                        end;
                        if v86:get_task_flag(l_CompleteSongDiffC_0) ~= true then
                            v86:set_task_flag(l_CompleteSongDiffC_0)
                            f_log_task_complete_message(l__id_0, v86, l_CompleteSongDiffC_0)
                            if v96 then
                                v96(l__id_0, v86, l_CompleteSongDiffC_0)
                            end;
                        end;
                    end;
                    if v93 then
                        local l_CompleteExtendedCut_0 = v_u_12.TaskFlags.CompleteExtendedCut
                        local function v97() --[[ Line: 361 ]]
                            --[[ Upvalues: (ref 1): v_u_87 ]]
                            v_u_87 = true
                        end;
                        if v86:get_task_flag(l_CompleteExtendedCut_0) ~= true then
                            v86:set_task_flag(l_CompleteExtendedCut_0)
                            f_log_task_complete_message(l__id_0, v86, l_CompleteExtendedCut_0)
                            if v97 then
                                v97(l__id_0, v86, l_CompleteExtendedCut_0)
                            end;
                        end;
                    end;
                end;
                if v85:get_multiplayer_song_complete_count() >= 10 then
                    local l_Complete10MultiplayerSongs_0 = v_u_12.TaskFlags.Complete10MultiplayerSongs
                    local function v98() --[[ Line: 368 ]]
                        --[[ Upvalues: (ref 1): v_u_87 ]]
                        v_u_87 = true
                    end;
                    if v86:get_task_flag(l_Complete10MultiplayerSongs_0) ~= true then
                        v86:set_task_flag(l_Complete10MultiplayerSongs_0)
                        f_log_task_complete_message(l__id_0, v86, l_Complete10MultiplayerSongs_0)
                        if v98 then
                            v98(l__id_0, v86, l_Complete10MultiplayerSongs_0)
                        end;
                    end;
                end;
                if v_u_87 then
                    p80:datastore_write_player_progress(l__id_0, v86)
                end;
            end;
        else
            return;
        end;
    end;
    local v_u_99 = v_u_3:new({
        [v_u_18.PlayerActionEvent.QueueSongRadio] = v_u_12.TaskFlags.QueueSongRadio,
        [v_u_18.PlayerActionEvent.VoteSongRadio] = v_u_12.TaskFlags.VoteSongRadio,
        [v_u_18.PlayerActionEvent.SpeakPlayerNPCRewards] = v_u_12.TaskFlags.SpeakPlayerNPC,
        [v_u_18.PlayerActionEvent.CheerPlayer] = v_u_12.TaskFlags.SpectateCheerPlayer
    })
    v_u_9:get_base_fn(v_u_32, "handle_player_action_event")
    v_u_32.handle_player_action_event = function(p100, p101, p102, p_u_103) --[[ Name: handle_player_action_event ]] --[[ Line: 386 ]]
        --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_31, (copy 3): v_u_33, (ref 4): v_u_18, (ref 5): v_u_8, (ref 6): v_u_13, (copy 7): f_log_task_complete_message, (copy 8): v_u_99 ]]
        if v_u_12:day_event_list_playerblob_is_event_active(p_u_31._api:get_day_event_list(), p_u_31._player_blob_manager:get_cached_blob(p101)) == true then
            if v_u_33:contains(p101) == true then
                local v104 = v_u_33:get(p101):get_cached_player_progress()
                local v_u_105 = false
                if p102 == v_u_18.PlayerActionEvent.CompleteMission then
                    local v_u_106 = nil
                    v_u_8:ptry(function() --[[ Line: 395 ]]
                        --[[ Upvalues: (ref 1): v_u_106, (copy 2): p_u_103 ]]
                        v_u_106 = p_u_103:get_type()
                    end)
                    if v_u_106 == v_u_13.Score or (v_u_106 == v_u_13.Rank or v_u_106 == v_u_13.ScaledScore) then
                        local l_CompleteSongMission_0 = v_u_12.TaskFlags.CompleteSongMission
                        local function v107() --[[ Line: 399 ]]
                            --[[ Upvalues: (ref 1): v_u_105 ]]
                            v_u_105 = true
                        end;
                        if v104:get_task_flag(l_CompleteSongMission_0) ~= true then
                            v104:set_task_flag(l_CompleteSongMission_0)
                            f_log_task_complete_message(p101, v104, l_CompleteSongMission_0)
                            if v107 then
                                v107(p101, v104, l_CompleteSongMission_0)
                            end;
                        end;
                    elseif v_u_106 == v_u_13.NoMiss then
                        local l_CompleteNoMissMission_0 = v_u_12.TaskFlags.CompleteNoMissMission
                        local function v108() --[[ Line: 403 ]]
                            --[[ Upvalues: (ref 1): v_u_105 ]]
                            v_u_105 = true
                        end;
                        if v104:get_task_flag(l_CompleteNoMissMission_0) ~= true then
                            v104:set_task_flag(l_CompleteNoMissMission_0)
                            f_log_task_complete_message(p101, v104, l_CompleteNoMissMission_0)
                            if v108 then
                                v108(p101, v104, l_CompleteNoMissMission_0)
                            end;
                        end;
                    end;
                elseif v_u_99:contains(p102) then
                    local v109 = v_u_99:get(p102)
                    local function v110() --[[ Line: 410 ]]
                        --[[ Upvalues: (ref 1): v_u_105 ]]
                        v_u_105 = true
                    end;
                    if v104:get_task_flag(v109) ~= true then
                        v104:set_task_flag(v109)
                        f_log_task_complete_message(p101, v104, v109)
                        if v110 then
                            v110(p101, v104, v109)
                        end;
                    end;
                end;
                if v_u_105 then
                    p100:datastore_write_player_progress(p101, v104)
                end;
            end;
        else
            return;
        end;
    end;
    local v_u_111 = nil
    v_u_8:ptry(function() --[[ Line: 422 ]]
        --[[ Upvalues: (ref 1): v_u_111, (ref 2): s_DataStoreService_0 ]]
        v_u_111 = s_DataStoreService_0:GetDataStore("RBGames_Player_Progress")
    end)
    local function _(p112) --[[ Name: key_player_id ]] --[[ Line: 425 ]]
        --[[ Upvalues: (ref 1): v_u_8 ]]
        if v_u_8:is_dev_build() then
            return string.format("d_player_%d", p112);
        else
            return string.format("player_%d", p112);
        end;
    end;
    v_u_32.datastore_write_player_progress = function(_, p113, p_u_114, p_u_115) --[[ Name: datastore_write_player_progress ]] --[[ Line: 429 ]]
        --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_111, (ref 3): v_u_8 ]]
        local v116 = p_u_114:to_table()
        local l__datastore_api_0 = p_u_31._datastore_api
        local v117 = v_u_111
        local v118
        if v_u_8:is_dev_build() then
            v118 = string.format("d_player_%d", p113)
        else
            v118 = string.format("player_%d", p113)
        end;
        l__datastore_api_0:do_datastore_set(v117, v118, v116, function() --[[ Line: 431 ]]
            --[[ Upvalues: (copy 1): p_u_115, (copy 2): p_u_114 ]]
            if p_u_115 then
                p_u_115(p_u_114)
            end;
        end)
    end;
    v_u_32.datastore_get_player_progress = function(_, p119, p_u_120) --[[ Name: datastore_get_player_progress ]] --[[ Line: 435 ]]
        --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_111, (ref 3): v_u_8, (ref 4): v_u_12 ]]
        local l__datastore_api_1 = p_u_31._datastore_api
        local v121 = v_u_111
        local v122
        if v_u_8:is_dev_build() then
            v122 = string.format("d_player_%d", p119)
        else
            v122 = string.format("player_%d", p119)
        end;
        l__datastore_api_1:do_datastore_get(v121, v122, function(_, p_u_123) --[[ Line: 436 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_12, (copy 3): p_u_120 ]]
            local v_u_124 = nil
            if typeof(p_u_123) == "table" then
                v_u_8:ptry(function() --[[ Line: 439 ]]
                    --[[ Upvalues: (ref 1): v_u_124, (ref 2): v_u_12, (copy 3): p_u_123 ]]
                    v_u_124 = v_u_12.PlayerProgress:from_table(p_u_123)
                end)
            end;
            if v_u_124 == nil then
                v_u_124 = v_u_12.PlayerProgress:new()
            end;
            p_u_120(v_u_124)
        end)
    end;
    f_cons()
    return v_u_32;
end;
return v19;
