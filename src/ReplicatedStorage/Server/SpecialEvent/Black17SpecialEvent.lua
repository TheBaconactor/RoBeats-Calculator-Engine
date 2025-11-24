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
local v_u_11 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_12 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
require(game.ReplicatedStorage.Server.ServerDataStoreAPIManager)
require(game.ReplicatedStorage.Shared.MissionType)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.FeverIconInfo)
local v_u_14 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_16 = require(game.ReplicatedStorage.GameStage.GameStageDatabase)
require(game.ReplicatedStorage.Pets.PetDatabase)
local v_u_17 = require(game.ReplicatedStorage.GameStage.GameStageUtil)
local v_u_18 = require(game.ReplicatedStorage.Pets.PetUtils)
local v_u_19 = require(game.ServerScriptService.ServerPrivateConstants)
local v_u_20 = require(game.ServerScriptService.ServerPromoCodes)
local v_u_21 = require(game.ReplicatedStorage.PlayerInfo.BoxInfo)
local v_u_22 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_23 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_24 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.Black17EventInfo)
local v25 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_26 = nil
v25:require_server(function() --[[ Line: 33 ]]
    --[[ Upvalues: (ref 1): v_u_26 ]]
    v_u_26 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
local _ = game:GetService("BadgeService")
local s_DataStoreService_0 = game:GetService("DataStoreService")
local s_HttpService_0 = game:GetService("HttpService")
local v_u_37 = {
    ["do_external_api_request_check_claim"] = function(_, p_u_27, p_u_28) --[[ Name: do_external_api_request_check_claim ]] --[[ Line: 99 ]]
        --[[ Upvalues: (copy 1): v_u_19, (copy 2): s_HttpService_0, (copy 3): v_u_4, (copy 4): v_u_8 ]]
        local v29 = v_u_19:get_black17_api_table()
        local l_QA_URL_0 = v29.QA_URL
        local l_PROD_URL_0 = v29.PROD_URL
        local l_API_KEY_0 = v29.API_KEY
        local l_AUTH_PATH_0 = v29.AUTH_PATH
        local l_CAMPAIGN_ID_0 = v29.CAMPAIGN_ID
        spawn(function() --[[ Line: 111 ]]
            --[[ Upvalues: (copy 1): l_QA_URL_0, (copy 2): l_PROD_URL_0, (ref 3): s_HttpService_0, (copy 4): l_AUTH_PATH_0, (copy 5): l_API_KEY_0, (copy 6): p_u_27, (copy 7): l_CAMPAIGN_ID_0, (ref 8): v_u_4, (ref 9): v_u_8, (copy 10): p_u_28 ]]
            local v30 = false
            local v31 = l_PROD_URL_0
            local v32 = {
                ["Url"] = v31 .. l_AUTH_PATH_0,
                ["Method"] = "POST",
                ["Headers"] = {
                    ["Content-Type"] = "application/json",
                    ["sims-api-key"] = l_API_KEY_0
                },
                ["Body"] = v33:JSONEncode(v34)
            }
            local v33 = s_HttpService_0
            local v34 = {
                ["roblox_id"] = p_u_27,
                ["campaign_id"] = l_CAMPAIGN_ID_0
            }
            local v35 = s_HttpService_0:RequestAsync(v32)
            if v35.Success then
                local v36 = s_HttpService_0:JSONDecode(v35.Body)
                v_u_4:puts("Black17SpecialEvent[%s]:do_external_api_request_check_claim response body(%s)", v31, v_u_8:tab_to_str(v35))
                v30 = v36 and (type(v36) == "table" and v36.authorized == true) and true or v30
            else
                v_u_4:warnf("Black17SpecialEvent:do_external_api_request_check_claim failed(%s)", v_u_8:tab_to_str(v35))
            end;
            p_u_28(v30)
        end)
    end
}
local v_u_48 = {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 44 ]]
        --[[ Upvalues: (copy 1): v_u_24, (copy 2): v_u_2 ]]
        local v38 = {}
        local v_u_39 = 0
        v38.get_multiplayer_song_complete_count = function(_) --[[ Name: get_multiplayer_song_complete_count ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_39 ]]
            return v_u_39;
        end;
        v38.increment_multiplayer_song_complete_count = function(_) --[[ Name: increment_multiplayer_song_complete_count ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_39 ]]
            v_u_39 = v_u_39 + 1
        end;
        local v_u_40 = 0
        v38.get_song_complete_count = function(_) --[[ Name: get_song_complete_count ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_40 ]]
            return v_u_40;
        end;
        v38.increment_song_complete_count = function(_) --[[ Name: increment_song_complete_count ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_40 ]]
            v_u_40 = v_u_40 + 1
        end;
        local v_u_41 = v_u_24.PlayerProgress:new()
        local v_u_42 = true
        local v_u_43 = v_u_2:new()
        v38.update_cached_player_progress = function(_, p44) --[[ Name: update_cached_player_progress ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_42, (copy 3): v_u_43 ]]
            v_u_41 = p44
            v_u_42 = false
            for _, v45 in v_u_43:key_itr() do
                v45(v_u_41)
            end;
            v_u_43:clear()
        end;
        v38.get_player_progress = function(_, p46) --[[ Name: get_player_progress ]] --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_42, (copy 2): v_u_43, (ref 3): v_u_41 ]]
            if v_u_42 == true then
                v_u_43:push_back(p46)
            else
                p46(v_u_41)
            end;
        end;
        v38.get_cached_player_progress = function(_) --[[ Name: get_cached_player_progress ]] --[[ Line: 73 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            return v_u_41;
        end;
        v38.flag_waiting_player_progress_update = function(_) --[[ Name: flag_waiting_player_progress_update ]] --[[ Line: 75 ]]
            --[[ Upvalues: (ref 1): v_u_42 ]]
            v_u_42 = true
        end;
        v38.reset_data = function(p47) --[[ Name: reset_data ]] --[[ Line: 79 ]]
            --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_40 ]]
            v_u_39 = 0
            v_u_40 = 0
            p47:flag_waiting_player_progress_update()
        end;
        v38.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_40 ]]
            return {
                ["MultiplayerSongCompleteCount"] = v_u_39,
                ["SongCompleteCount"] = v_u_40
            };
        end;
        return v38;
    end
}
v_u_37.new = function(_, p_u_49) --[[ Name: new ]] --[[ Line: 146 ]]
    --[[ Upvalues: (ref 1): v_u_26, (copy 2): v_u_3, (copy 3): v_u_23, (copy 4): v_u_4, (copy 5): v_u_7, (copy 6): v_u_24, (copy 7): v_u_12, (copy 8): v_u_16, (copy 9): v_u_15, (copy 10): v_u_1, (copy 11): v_u_2, (copy 12): v_u_8, (copy 13): v_u_14, (copy 14): v_u_17, (copy 15): v_u_22, (copy 16): v_u_18, (copy 17): v_u_13, (copy 18): v_u_5, (copy 19): v_u_20, (copy 20): v_u_21, (copy 21): v_u_37, (copy 22): v_u_9, (copy 23): v_u_48, (copy 24): v_u_10, (copy 25): v_u_6, (copy 26): v_u_11, (copy 27): s_DataStoreService_0 ]]
    local v_u_50 = v_u_26.EventBase:new()
    local v_u_51 = v_u_3:new()
    local v_u_52 = v_u_3:new()
    local function _(p53) --[[ Name: add_tracking_event ]] --[[ Line: 151 ]]
        --[[ Upvalues: (copy 1): v_u_52 ]]
        if v_u_52:contains(p53) then
            v_u_52:add(p53, v_u_52:get(p53) + 1)
        else
            v_u_52:add(p53, 1)
        end;
    end;
    local v_u_54 = v_u_23:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 161 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_54, (copy 3): p_u_49, (ref 4): v_u_7, (ref 5): v_u_24, (copy 6): v_u_51, (copy 7): v_u_52, (copy 8): v_u_50, (ref 9): v_u_12, (ref 10): v_u_16, (ref 11): v_u_15, (ref 12): v_u_1, (ref 13): v_u_2, (ref 14): v_u_8, (ref 15): v_u_14, (ref 16): v_u_17, (ref 17): v_u_22, (ref 18): v_u_18, (ref 19): v_u_13, (ref 20): v_u_5, (ref 21): v_u_20, (ref 22): v_u_21, (ref 23): v_u_37 ]]
        v_u_4:puts("Black17SpecialEvent cons")
        v_u_54:add_cooldown(30)
        p_u_49._evt:wait_on_event(v_u_7.EVT_SpecialEvent_RBGames_GetData_Client, function(p_u_55) --[[ Line: 165 ]]
            --[[ Upvalues: (ref 1): p_u_49, (ref 2): v_u_7, (ref 3): v_u_24, (ref 4): v_u_4, (ref 5): v_u_51, (ref 6): v_u_52 ]]
            local function _(p56, p57) --[[ Name: response ]] --[[ Line: 166 ]]
                --[[ Upvalues: (ref 1): p_u_49, (ref 2): v_u_7, (copy 3): p_u_55 ]]
                p_u_49._evt:fire_event_to_client(v_u_7.EVT_SpecialEvent_RBGames_GetData_Server, p_u_55, p56:to_table(), p57:to_table())
            end;
            local l_UserId_0 = p_u_55.UserId
            if v_u_24:day_event_list_playerblob_is_event_active(p_u_49._api:get_day_event_list(), p_u_49._player_blob_manager:get_cached_blob(l_UserId_0)) == true then
                if v_u_51:contains(l_UserId_0) == true then
                    local v_u_58 = v_u_51:get(l_UserId_0)
                    v_u_58:get_player_progress(function(p59) --[[ Line: 174 ]]
                        --[[ Upvalues: (copy 1): v_u_58, (ref 2): p_u_49, (ref 3): v_u_7, (copy 4): p_u_55 ]]
                        p_u_49._evt:fire_event_to_client(v_u_7.EVT_SpecialEvent_RBGames_GetData_Server, p_u_55, p59:to_table(), v_u_58:to_table())
                    end)
                    if v_u_52:contains("EVT_SpecialEvent_RBGames_GetData_Client") then
                        v_u_52:add("EVT_SpecialEvent_RBGames_GetData_Client", v_u_52:get("EVT_SpecialEvent_RBGames_GetData_Client") + 1)
                    else
                        v_u_52:add("EVT_SpecialEvent_RBGames_GetData_Client", 1)
                    end;
                else
                    return v_u_4:warnf("EVT_SpecialEvent_RBGames_GetData_Client player not found _playerid_to_event_player_tracked_server_info");
                end;
            else
                return v_u_4:warnf("EVT_SpecialEvent_RBGames_GetData_Client event not active");
            end;
        end)
        p_u_49._evt:wait_on_event(v_u_7.EVT_SpecialEvent_RBGames_ResetData_Client, function(p_u_60) --[[ Line: 181 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): p_u_49, (ref 3): v_u_4, (ref 4): v_u_51, (ref 5): v_u_50, (ref 6): v_u_7 ]]
            local l_UserId_1 = p_u_60.UserId
            if v_u_24:day_event_list_playerblob_is_event_active(p_u_49._api:get_day_event_list(), p_u_49._player_blob_manager:get_cached_blob(l_UserId_1)) ~= true then
                return v_u_4:warnf("EVT_SpecialEvent_RBGames_ResetData_Client event not active");
            end;
            if v_u_51:contains(l_UserId_1) ~= true then
                return v_u_4:warnf("EVT_SpecialEvent_RBGames_ResetData_Client player not found _playerid_to_event_player_tracked_server_info");
            end;
            local v_u_61 = v_u_51:get(l_UserId_1)
            v_u_61:reset_data()
            v_u_50:datastore_write_player_progress(l_UserId_1, v_u_24.PlayerProgress:new(), function(p62) --[[ Line: 187 ]]
                --[[ Upvalues: (copy 1): v_u_61, (ref 2): p_u_49, (ref 3): v_u_7, (copy 4): p_u_60 ]]
                v_u_61:update_cached_player_progress(p62)
                p_u_49._evt:fire_event_to_client(v_u_7.EVT_SpecialEvent_RBGames_ResetData_Server, p_u_60)
            end)
        end)
        local v_u_63 = v_u_12.RewardInfo:new(v_u_12.RewardType.Gear, 1, 241)
        local v_u_64 = v_u_24:get_stage_id()
        local v_u_65 = v_u_12.RewardInfo:new(v_u_12.RewardType.CraftingMaterials, 1, v_u_16:singleton():get_stage_info_for_id(v_u_64):get_material_id())
        local v_u_66 = v_u_12.RewardInfo:new(v_u_12.RewardType.Pet, 1, 76)
        local v_u_67 = v_u_12.RewardInfo:new(v_u_12.RewardType.Gear, 1, 242)
        local v_u_68 = v_u_12.RewardInfo:new(v_u_12.RewardType.CraftingMaterials, 1, v_u_15:singleton():get_fevericon_for_id(216):get_material_id())
        local v_u_69 = v_u_12.RewardInfo:new(v_u_12.RewardType.Titles, 1, 137)
        p_u_49._evt:wait_on_event(v_u_7.EVT_SpecialEvent_RBGames_ClaimProgress_Client, function(p_u_70, p_u_71) --[[ Line: 211 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_24, (ref 3): p_u_49, (ref 4): v_u_7, (ref 5): v_u_12, (ref 6): v_u_4, (ref 7): v_u_51, (ref 8): v_u_2, (ref 9): v_u_8, (ref 10): v_u_14, (copy 11): v_u_63, (ref 12): v_u_52, (ref 13): v_u_17, (copy 14): v_u_64, (ref 15): v_u_22, (copy 16): v_u_65, (ref 17): v_u_18, (copy 18): v_u_66, (copy 19): v_u_67, (ref 20): v_u_13, (copy 21): v_u_68, (ref 22): v_u_5, (copy 23): v_u_69, (ref 24): v_u_50 ]]
            v_u_1:is_enum_member(p_u_71, v_u_24.ProgressFlags)
            local function _(p72, p73, p74) --[[ Name: response ]] --[[ Line: 214 ]]
                --[[ Upvalues: (ref 1): p_u_49, (ref 2): v_u_7, (copy 3): p_u_70, (ref 4): v_u_12 ]]
                p_u_49._evt:fire_event_to_client(v_u_7.EVT_SpecialEvent_RBGames_ClaimProgress_Server, p_u_70, p72, p73, v_u_12.RewardInfo:list_to_table(p74))
            end;
            local l_UserId_2 = p_u_70.UserId
            if v_u_24:day_event_list_playerblob_is_event_active(p_u_49._api:get_day_event_list(), p_u_49._player_blob_manager:get_cached_blob(l_UserId_2)) ~= true then
                return v_u_4:warnf("EVT_SpecialEvent_RBGames_ClaimProgress_Client event not active");
            end;
            if v_u_51:contains(l_UserId_2) ~= true then
                return v_u_4:warnf("EVT_SpecialEvent_RBGames_ClaimProgress_Client player not found _playerid_to_event_player_tracked_server_info");
            end;
            v_u_51:get(l_UserId_2):get_player_progress(function(p75) --[[ Line: 222 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_24, (copy 3): p_u_71, (ref 4): v_u_8, (ref 5): p_u_49, (copy 6): l_UserId_2, (ref 7): v_u_14, (ref 8): v_u_63, (ref 9): v_u_52, (ref 10): v_u_17, (ref 11): v_u_64, (ref 12): v_u_22, (ref 13): v_u_65, (ref 14): v_u_18, (ref 15): v_u_66, (ref 16): v_u_67, (ref 17): v_u_13, (ref 18): v_u_68, (ref 19): v_u_5, (ref 20): v_u_69, (copy 21): p_u_70, (ref 22): v_u_12, (ref 23): v_u_7, (ref 24): v_u_50 ]]
                local v_u_76 = ""
                local v_u_77 = v_u_2:new()
                local v78
                if v_u_24:player_progress_can_claim_event_flag(p75, p_u_71) == true then
                    p75:set_progress_flag(p_u_71)
                    v_u_8:ptry(function() --[[ Line: 230 ]]
                        --[[ Upvalues: (ref 1): p_u_49, (ref 2): l_UserId_2, (ref 3): p_u_71, (ref 4): v_u_24, (ref 5): v_u_14, (copy 6): v_u_77, (ref 7): v_u_63, (ref 8): v_u_52, (ref 9): v_u_17, (ref 10): v_u_64, (ref 11): v_u_22, (ref 12): v_u_65, (ref 13): v_u_18, (ref 14): v_u_66, (ref 15): v_u_67, (ref 16): v_u_13, (ref 17): v_u_68, (ref 18): v_u_5, (ref 19): v_u_69 ]]
                        local v79 = p_u_49._player_blob_manager:get_cached_blob(l_UserId_2)
                        local v80 = p_u_49._collection_manager:get_collection_info_for_player_id_playerblob(l_UserId_2, v79)
                        if p_u_71 == v_u_24.ProgressFlags.PlayAnySong and v_u_14:playerblob_get_owned_count_of_equipmentid(v79, 241) == 0 then
                            v_u_77:push_back(v_u_63)
                            local v81 = string.format("EVT_SpecialEvent_RBGames_ClaimProgress_Client_%d", v_u_24.ProgressFlags.PlayAnySong)
                            if v_u_52:contains(v81) then
                                v_u_52:add(v81, v_u_52:get(v81) + 1)
                            else
                                v_u_52:add(v81, 1)
                            end;
                        end;
                        if p_u_71 == v_u_24.ProgressFlags.EarnPoints1 and (v_u_17:playerblob_get_owned_stage_ids_set(v79, v80):contains(v_u_64) ~= true and v_u_22:get_count_of_material(v79, v_u_65:get_id()) ~= true) then
                            v_u_77:push_back(v_u_65)
                            local v82 = string.format("EVT_SpecialEvent_RBGames_ClaimProgress_Client_%d", v_u_24.ProgressFlags.EarnPoints1)
                            if v_u_52:contains(v82) then
                                v_u_52:add(v82, v_u_52:get(v82) + 1)
                            else
                                v_u_52:add(v82, 1)
                            end;
                        end;
                        if p_u_71 == v_u_24.ProgressFlags.EarnPoints2 and v_u_18:playerblob_get_owned_petid_set(v79):contains(76) ~= true then
                            v_u_77:push_back(v_u_66)
                            local v83 = string.format("EVT_SpecialEvent_RBGames_ClaimProgress_Client_%d", v_u_24.ProgressFlags.EarnPoints2)
                            if v_u_52:contains(v83) then
                                v_u_52:add(v83, v_u_52:get(v83) + 1)
                            else
                                v_u_52:add(v83, 1)
                            end;
                        end;
                        if p_u_71 == v_u_24.ProgressFlags.EarnPoints3 and v_u_14:playerblob_get_owned_count_of_equipmentid(v79, 242) == 0 then
                            v_u_77:push_back(v_u_67)
                            local v84 = string.format("EVT_SpecialEvent_RBGames_ClaimProgress_Client_%d", v_u_24.ProgressFlags.EarnPoints3)
                            if v_u_52:contains(v84) then
                                v_u_52:add(v84, v_u_52:get(v84) + 1)
                            else
                                v_u_52:add(v84, 1)
                            end;
                        end;
                        if p_u_71 == v_u_24.ProgressFlags.EarnPoints4 and v_u_13:get_playerblob_fevericon_owned_set(v79, 0, v80):contains(216) ~= true then
                            v_u_77:push_back(v_u_68)
                            local v85 = string.format("EVT_SpecialEvent_RBGames_ClaimProgress_Client_%d", v_u_24.ProgressFlags.EarnPoints4)
                            if v_u_52:contains(v85) then
                                v_u_52:add(v85, v_u_52:get(v85) + 1)
                            else
                                v_u_52:add(v85, 1)
                            end;
                        end;
                        if p_u_71 == v_u_24.ProgressFlags.PlayEverySong and v_u_5:owns_title_id(v79, 137) ~= true then
                            v_u_77:push_back(v_u_69)
                            local v86 = string.format("EVT_SpecialEvent_RBGames_ClaimProgress_Client_%d", v_u_24.ProgressFlags.PlayEverySong)
                            if v_u_52:contains(v86) then
                                v_u_52:add(v86, v_u_52:get(v86) + 1)
                                return;
                            end;
                            v_u_52:add(v86, 1)
                        end;
                    end)
                    v78 = true
                else
                    v_u_76 = "Already claimed!"
                    v78 = false
                end;
                local function f_finish() --[[ Name: finish ]] --[[ Line: 287 ]]
                    --[[ Upvalues: (copy 1): v_u_77, (ref 2): p_u_49, (ref 3): p_u_70, (ref 4): v_u_12, (ref 5): v_u_76, (ref 6): v_u_7 ]]
                    if v_u_77:count() > 0 then
                        p_u_49._player_blob_manager:get_verified_cached_blob(p_u_70.UserId, function(p87) --[[ Line: 289 ]]
                            --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_49, (ref 3): v_u_77, (ref 4): p_u_70, (ref 5): v_u_76, (ref 6): v_u_7 ]]
                            local v_u_88 = v_u_12:claim_reward_info_list_to_playerblob(p_u_49, p87, v_u_77)
                            v_u_12:server_sync_reward_params(p_u_49, p_u_70, v_u_88, function() --[[ Line: 291 ]]
                                --[[ Upvalues: (ref 1): v_u_76, (ref 2): v_u_12, (copy 3): v_u_88, (ref 4): p_u_49, (ref 5): v_u_7, (ref 6): p_u_70 ]]
                                p_u_49._evt:fire_event_to_client(v_u_7.EVT_SpecialEvent_RBGames_ClaimProgress_Server, p_u_70, true, v_u_76, v_u_12.RewardInfo:list_to_table((v_u_12:reward_params_get_resolved_reward_list(v_u_88))))
                            end)
                        end)
                    else
                        p_u_49._evt:fire_event_to_client(v_u_7.EVT_SpecialEvent_RBGames_ClaimProgress_Server, p_u_70, true, v_u_76, v_u_12.RewardInfo:list_to_table(v_u_77))
                    end;
                end;
                if v78 then
                    v_u_50:datastore_write_player_progress(l_UserId_2, p75, function() --[[ Line: 301 ]]
                        --[[ Upvalues: (copy 1): f_finish ]]
                        f_finish()
                    end)
                else
                    f_finish()
                end;
            end)
        end)
        local v89 = "__black17_c4"
        if v_u_8:is_dev_build() then
            v89 = v89 .. "_d"
        end;
        local v_u_90 = v_u_20.PromoCode:new(v89, function() --[[ Line: 314 ]]
            return true, "";
        end)
        v_u_90:add_rewards_list_from_table({
            {
                ["Type"] = v_u_12.RewardType.Stars,
                ["Id"] = -1,
                ["Amount"] = 15
            },
            {
                ["Type"] = v_u_12.RewardType.Coins,
                ["Id"] = -1,
                ["Amount"] = 250
            },
            {
                ["Type"] = v_u_12.RewardType.CraftingMaterials,
                ["Id"] = v_u_21:get_gem_box_id(),
                ["Amount"] = 3
            },
            {
                ["Type"] = v_u_12.RewardType.CraftingMaterials,
                ["Id"] = v_u_21:get_vip_song_normal_box_not_tradeable_id(),
                ["Amount"] = 1
            },
            {
                ["Type"] = v_u_12.RewardType.CraftingMaterials,
                ["Id"] = v_u_21:get_vip_song_hard_box_not_tradeable_id(),
                ["Amount"] = 1
            },
            {
                ["Type"] = v_u_12.RewardType.CraftingMaterials,
                ["Id"] = v_u_21:get_mini_2star_box_not_tradeable_id(),
                ["Amount"] = 1
            },
            {
                ["Type"] = v_u_12.RewardType.CraftingMaterials,
                ["Id"] = v_u_21:get_dance_box_not_tradeable_id(),
                ["Amount"] = 1
            }
        })
        p_u_49._evt:wait_on_event(v_u_7.EVT_SpecialEvent_RBGames_Client_Event1, function(p_u_91) --[[ Line: 325 ]]
            --[[ Upvalues: (ref 1): p_u_49, (ref 2): v_u_7, (ref 3): v_u_24, (ref 4): v_u_4, (ref 5): v_u_37, (copy 6): v_u_90, (ref 7): v_u_12, (ref 8): v_u_52 ]]
            local function f_response(p92, p93, p94) --[[ Name: response ]] --[[ Line: 326 ]]
                --[[ Upvalues: (ref 1): p_u_49, (ref 2): v_u_7, (copy 3): p_u_91 ]]
                p_u_49._evt:fire_event_to_client(v_u_7.EVT_SpecialEvent_RBGames_Server_Event1, p_u_91, p92, p93, p94 == nil and {} or p94)
            end;
            local l_UserId_3 = p_u_91.UserId
            if v_u_24:day_event_list_playerblob_is_event_active(p_u_49._api:get_day_event_list(), p_u_49._player_blob_manager:get_cached_blob(l_UserId_3)) ~= true then
                return v_u_4:warnf("EVT_SpecialEvent_RBGames_Client_Event1 event not active");
            end;
            v_u_37:do_external_api_request_check_claim(l_UserId_3, function(p95) --[[ Line: 333 ]]
                --[[ Upvalues: (ref 1): p_u_49, (copy 2): l_UserId_3, (ref 3): v_u_90, (copy 4): p_u_91, (ref 5): v_u_12, (ref 6): v_u_7, (ref 7): v_u_52, (copy 8): f_response ]]
                if not p95 then
                    if v_u_52:contains("EVT_SpecialEvent_RBGames_Client_Event1_fail") then
                        v_u_52:add("EVT_SpecialEvent_RBGames_Client_Event1_fail", v_u_52:get("EVT_SpecialEvent_RBGames_Client_Event1_fail") + 1)
                    else
                        v_u_52:add("EVT_SpecialEvent_RBGames_Client_Event1_fail", 1)
                    end;
                    return f_response(false, "Did not complete all the steps. Please check our social media for info on how to complete steps to claim this reward!");
                end;
                p_u_49._datastore_api:datastore_api_playerid_can_claim_promo_code(l_UserId_3, v_u_90, function(p96, _, _) --[[ Line: 335 ]]
                    --[[ Upvalues: (ref 1): p_u_49, (ref 2): p_u_91, (ref 3): v_u_12, (ref 4): v_u_90, (ref 5): v_u_7, (ref 6): v_u_52, (ref 7): f_response ]]
                    if not p96 then
                        return f_response(false, "Reward has already been claimed.");
                    end;
                    p_u_49._player_blob_manager:get_verified_cached_blob(p_u_91.UserId, function(p97) --[[ Line: 337 ]]
                        --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_49, (ref 3): v_u_90, (ref 4): p_u_91, (ref 5): v_u_7, (ref 6): v_u_52 ]]
                        local v_u_98 = v_u_12:claim_reward_info_list_to_playerblob(p_u_49, p97, v_u_90:get_rewards())
                        v_u_12:server_sync_reward_params(p_u_49, p_u_91, v_u_98, function() --[[ Line: 339 ]]
                            --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_98, (ref 3): p_u_49, (ref 4): v_u_7, (ref 5): p_u_91 ]]
                            local v99 = v_u_12.RewardInfo:list_to_table(v_u_12:reward_params_get_resolved_reward_list(v_u_98))
                            p_u_49._evt:fire_event_to_client(v_u_7.EVT_SpecialEvent_RBGames_Server_Event1, p_u_91, true, "", v99 == nil and {} or v99)
                        end)
                        if v_u_52:contains("EVT_SpecialEvent_RBGames_Client_Event1_success") then
                            v_u_52:add("EVT_SpecialEvent_RBGames_Client_Event1_success", v_u_52:get("EVT_SpecialEvent_RBGames_Client_Event1_success") + 1)
                        else
                            v_u_52:add("EVT_SpecialEvent_RBGames_Client_Event1_success", 1)
                        end;
                    end)
                end)
            end)
        end)
    end;
    v_u_9:get_base_fn(v_u_50, "player_connecting")
    v_u_50.player_connecting = function(p100, p101) --[[ Name: player_connecting ]] --[[ Line: 357 ]]
        --[[ Upvalues: (ref 1): v_u_48, (copy 2): v_u_51 ]]
        local v_u_102 = v_u_48:new()
        v_u_51:add(p101, v_u_102)
        p100:datastore_get_player_progress(p101, function(p103) --[[ Line: 360 ]]
            --[[ Upvalues: (copy 1): v_u_102 ]]
            v_u_102:update_cached_player_progress(p103)
        end)
    end;
    v_u_9:get_base_fn(v_u_50, "player_disconnecting")
    v_u_50.player_disconnecting = function(_, p104) --[[ Name: player_disconnecting ]] --[[ Line: 366 ]]
        --[[ Upvalues: (copy 1): v_u_51 ]]
        v_u_51:remove(p104)
    end;
    v_u_9:get_base_fn(v_u_50, "can_playerid_start_songkey")
    v_u_50.can_playerid_start_songkey = function(_, _, p105, _) --[[ Name: can_playerid_start_songkey ]] --[[ Line: 371 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24:get_all_songkeys_set():contains(p105);
    end;
    local function f_log_task_complete_message(p106, p107, p108) --[[ Name: log_task_complete_message ]] --[[ Line: 375 ]]
        --[[ Upvalues: (copy 1): p_u_49, (ref 2): v_u_4, (ref 3): v_u_24 ]]
        local v109 = p_u_49._player_manager:id_to_player(p106)
        if v109 == nil then
            return v_u_4:warnf("log_task_complete_message-1");
        end;
        local v110 = v_u_24:get_task_flag_to_name():get(p108)
        if v110 == nil then
            return v_u_4:warnf("log_task_complete_message-2");
        end;
        p_u_49._chat:get_chat_service():send_system_message_to_player_for_channel(v109, p_u_49._chat:get_chat_service():get_channel(p_u_49._chat:get_chat_service():get_server_system_channel_id()), string.format("Completed Black17 event task: %s - Current points: %d", v110, p107:calculate_task_points()), function(p111) --[[ Line: 384 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            p111:set_channel_name("")
            p111:set_icon(v_u_24:get_icon_assetid())
        end)
    end;
    local function _(p112, p113, p114, p115) --[[ Name: write_player_id_player_progress_task_flag_if_available ]] --[[ Line: 391 ]]
        --[[ Upvalues: (copy 1): f_log_task_complete_message ]]
        if p113:get_task_flag(p114) ~= true then
            p113:set_task_flag(p114)
            f_log_task_complete_message(p112, p113, p114)
            if p115 then
                p115(p112, p113, p114)
            end;
        end;
    end;
    v_u_9:get_base_fn(v_u_50, "write_special_event_data_for_play")
    v_u_50.write_special_event_data_for_play = function(p116, _, p117, _, p118, p119, _, _) --[[ Name: write_special_event_data_for_play ]] --[[ Line: 400 ]]
        --[[ Upvalues: (ref 1): v_u_24, (copy 2): p_u_49, (copy 3): v_u_51, (ref 4): v_u_10, (copy 5): v_u_52, (copy 6): f_log_task_complete_message, (ref 7): v_u_6, (ref 8): v_u_11 ]]
        local l__id_0 = p119._id
        if v_u_24:day_event_list_playerblob_is_event_active(p_u_49._api:get_day_event_list(), p_u_49._player_blob_manager:get_cached_blob(l__id_0)) == true then
            if v_u_51:contains(l__id_0) == true then
                if v_u_24:get_all_songkeys_set():contains(p117) == true then
                    if p119._accuracy >= v_u_10:rank_value_to_accuracy(v_u_10.Value.RankD) == true then
                        local v120 = v_u_51:get(l__id_0)
                        v120:increment_song_complete_count()
                        if p118 >= 3 then
                            v120:increment_multiplayer_song_complete_count()
                        end;
                        local v121 = v120:get_cached_player_progress()
                        local v_u_122 = false
                        if v120:get_multiplayer_song_complete_count() >= 1 then
                            local l_MultiplayerMatches1_0 = v_u_24.TaskFlags.MultiplayerMatches1
                            local function v124() --[[ Line: 421 ]]
                                --[[ Upvalues: (ref 1): v_u_122, (ref 2): v_u_24, (ref 3): v_u_52 ]]
                                v_u_122 = true
                                local v123 = string.format("write_player_id_player_progress_task_flag_if_available_%d", v_u_24.TaskFlags.MultiplayerMatches1)
                                if v_u_52:contains(v123) then
                                    v_u_52:add(v123, v_u_52:get(v123) + 1)
                                else
                                    v_u_52:add(v123, 1)
                                end;
                            end;
                            if v121:get_task_flag(l_MultiplayerMatches1_0) ~= true then
                                v121:set_task_flag(l_MultiplayerMatches1_0)
                                f_log_task_complete_message(l__id_0, v121, l_MultiplayerMatches1_0)
                                if v124 then
                                    v124(l__id_0, v121, l_MultiplayerMatches1_0)
                                end;
                            end;
                        end;
                        if v120:get_multiplayer_song_complete_count() >= 3 then
                            local l_MultiplayerMatches2_0 = v_u_24.TaskFlags.MultiplayerMatches2
                            local function v126() --[[ Line: 427 ]]
                                --[[ Upvalues: (ref 1): v_u_122, (ref 2): v_u_24, (ref 3): v_u_52 ]]
                                v_u_122 = true
                                local v125 = string.format("write_player_id_player_progress_task_flag_if_available_%d", v_u_24.TaskFlags.MultiplayerMatches2)
                                if v_u_52:contains(v125) then
                                    v_u_52:add(v125, v_u_52:get(v125) + 1)
                                else
                                    v_u_52:add(v125, 1)
                                end;
                            end;
                            if v121:get_task_flag(l_MultiplayerMatches2_0) ~= true then
                                v121:set_task_flag(l_MultiplayerMatches2_0)
                                f_log_task_complete_message(l__id_0, v121, l_MultiplayerMatches2_0)
                                if v126 then
                                    v126(l__id_0, v121, l_MultiplayerMatches2_0)
                                end;
                            end;
                        end;
                        if v120:get_multiplayer_song_complete_count() >= 5 then
                            local l_MultiplayerMatches3_0 = v_u_24.TaskFlags.MultiplayerMatches3
                            local function v128() --[[ Line: 433 ]]
                                --[[ Upvalues: (ref 1): v_u_122, (ref 2): v_u_24, (ref 3): v_u_52 ]]
                                v_u_122 = true
                                local v127 = string.format("write_player_id_player_progress_task_flag_if_available_%d", v_u_24.TaskFlags.MultiplayerMatches3)
                                if v_u_52:contains(v127) then
                                    v_u_52:add(v127, v_u_52:get(v127) + 1)
                                else
                                    v_u_52:add(v127, 1)
                                end;
                            end;
                            if v121:get_task_flag(l_MultiplayerMatches3_0) ~= true then
                                v121:set_task_flag(l_MultiplayerMatches3_0)
                                f_log_task_complete_message(l__id_0, v121, l_MultiplayerMatches3_0)
                                if v128 then
                                    v128(l__id_0, v121, l_MultiplayerMatches3_0)
                                end;
                            end;
                        end;
                        if v_u_24:get_songkey_to_task_flag():contains(p117) then
                            local v_u_129 = v_u_24:get_songkey_to_task_flag():get(p117)
                            local function v131() --[[ Line: 441 ]]
                                --[[ Upvalues: (ref 1): v_u_122, (copy 2): v_u_129, (ref 3): v_u_52 ]]
                                v_u_122 = true
                                local v130 = string.format("write_player_id_player_progress_task_flag_if_available_%d", v_u_129)
                                if v_u_52:contains(v130) then
                                    v_u_52:add(v130, v_u_52:get(v130) + 1)
                                else
                                    v_u_52:add(v130, 1)
                                end;
                            end;
                            if v121:get_task_flag(v_u_129) ~= true then
                                v121:set_task_flag(v_u_129)
                                f_log_task_complete_message(l__id_0, v121, v_u_129)
                                if v131 then
                                    v131(l__id_0, v121, v_u_129)
                                end;
                            end;
                        end;
                        if p119._miss_count == 0 then
                            local v132 = v_u_6:singleton():key_get_audiomod(p117)
                            if v132 == v_u_11.Normal then
                                local l_NoMissNormal_0 = v_u_24.TaskFlags.NoMissNormal
                                local function v134() --[[ Line: 450 ]]
                                    --[[ Upvalues: (ref 1): v_u_122, (ref 2): v_u_24, (ref 3): v_u_52 ]]
                                    v_u_122 = true
                                    local v133 = string.format("write_player_id_player_progress_task_flag_if_available_%d", v_u_24.TaskFlags.NoMissNormal)
                                    if v_u_52:contains(v133) then
                                        v_u_52:add(v133, v_u_52:get(v133) + 1)
                                    else
                                        v_u_52:add(v133, 1)
                                    end;
                                end;
                                if v121:get_task_flag(l_NoMissNormal_0) ~= true then
                                    v121:set_task_flag(l_NoMissNormal_0)
                                    f_log_task_complete_message(l__id_0, v121, l_NoMissNormal_0)
                                    if v134 then
                                        v134(l__id_0, v121, l_NoMissNormal_0)
                                    end;
                                end;
                            elseif v132 == v_u_11.Hard then
                                local l_NoMissHard_0 = v_u_24.TaskFlags.NoMissHard
                                local function v136() --[[ Line: 455 ]]
                                    --[[ Upvalues: (ref 1): v_u_122, (ref 2): v_u_24, (ref 3): v_u_52 ]]
                                    v_u_122 = true
                                    local v135 = string.format("write_player_id_player_progress_task_flag_if_available_%d", v_u_24.TaskFlags.NoMissHard)
                                    if v_u_52:contains(v135) then
                                        v_u_52:add(v135, v_u_52:get(v135) + 1)
                                    else
                                        v_u_52:add(v135, 1)
                                    end;
                                end;
                                if v121:get_task_flag(l_NoMissHard_0) ~= true then
                                    v121:set_task_flag(l_NoMissHard_0)
                                    f_log_task_complete_message(l__id_0, v121, l_NoMissHard_0)
                                    if v136 then
                                        v136(l__id_0, v121, l_NoMissHard_0)
                                    end;
                                end;
                            end;
                        end;
                        if v_u_122 then
                            p116:datastore_write_player_progress(l__id_0, v121)
                        end;
                        local v137 = string.format("write_special_event_data_for_play_%d", p117)
                        if v_u_52:contains(v137) then
                            v_u_52:add(v137, v_u_52:get(v137) + 1)
                        else
                            v_u_52:add(v137, 1)
                        end;
                    end;
                else
                    return;
                end;
            else
                return;
            end;
        else
            return;
        end;
    end;
    v_u_9:get_base_fn(v_u_50, "update")
    v_u_50.update = function(p138, p139) --[[ Name: update ]] --[[ Line: 470 ]]
        --[[ Upvalues: (copy 1): v_u_54, (copy 2): v_u_52 ]]
        v_u_54:update(p139)
        if v_u_54:is_on_cooldown() ~= true then
            if v_u_52:count() > 0 then
                p138:write_tracking_event_count_to_datastore()
            end;
            v_u_54:add_cooldown(30)
        end;
    end;
    local v_u_140 = nil
    v_u_8:ptry(function() --[[ Line: 485 ]]
        --[[ Upvalues: (ref 1): v_u_140, (ref 2): s_DataStoreService_0 ]]
        v_u_140 = s_DataStoreService_0:GetDataStore("Black17_Player_Progress")
    end)
    local function _(p141) --[[ Name: key_player_id ]] --[[ Line: 488 ]]
        --[[ Upvalues: (ref 1): v_u_8 ]]
        if v_u_8:is_dev_build() then
            return string.format("d_player_%d", p141);
        else
            return string.format("player_%d", p141);
        end;
    end;
    v_u_50.datastore_write_player_progress = function(_, p142, p_u_143, p_u_144) --[[ Name: datastore_write_player_progress ]] --[[ Line: 492 ]]
        --[[ Upvalues: (copy 1): p_u_49, (ref 2): v_u_140, (ref 3): v_u_8 ]]
        local v145 = p_u_143:to_table()
        local l__datastore_api_0 = p_u_49._datastore_api
        local v146 = v_u_140
        local v147
        if v_u_8:is_dev_build() then
            v147 = string.format("d_player_%d", p142)
        else
            v147 = string.format("player_%d", p142)
        end;
        l__datastore_api_0:do_datastore_set(v146, v147, v145, function() --[[ Line: 494 ]]
            --[[ Upvalues: (copy 1): p_u_144, (copy 2): p_u_143 ]]
            if p_u_144 then
                p_u_144(p_u_143)
            end;
        end)
    end;
    v_u_50.datastore_get_player_progress = function(_, p148, p_u_149) --[[ Name: datastore_get_player_progress ]] --[[ Line: 498 ]]
        --[[ Upvalues: (copy 1): p_u_49, (ref 2): v_u_140, (ref 3): v_u_8, (ref 4): v_u_24 ]]
        local l__datastore_api_1 = p_u_49._datastore_api
        local v150 = v_u_140
        local v151
        if v_u_8:is_dev_build() then
            v151 = string.format("d_player_%d", p148)
        else
            v151 = string.format("player_%d", p148)
        end;
        l__datastore_api_1:do_datastore_get(v150, v151, function(_, p_u_152) --[[ Line: 499 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_24, (copy 3): p_u_149 ]]
            local v_u_153 = nil
            if typeof(p_u_152) == "table" then
                v_u_8:ptry(function() --[[ Line: 502 ]]
                    --[[ Upvalues: (ref 1): v_u_153, (ref 2): v_u_24, (copy 3): p_u_152 ]]
                    v_u_153 = v_u_24.PlayerProgress:from_table(p_u_152)
                end)
            end;
            if v_u_153 == nil then
                v_u_153 = v_u_24.PlayerProgress:new()
            end;
            p_u_149(v_u_153)
        end)
    end;
    v_u_50.write_tracking_event_count_to_datastore = function(_) --[[ Name: write_tracking_event_count_to_datastore ]] --[[ Line: 514 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_52, (copy 3): p_u_49, (ref 4): v_u_140 ]]
        local v_u_154 = v_u_3:new()
        for v155, v156 in v_u_52:key_itr() do
            v_u_154:add(v155, v156)
        end;
        v_u_52:clear()
        p_u_49._datastore_api:do_datastore_update(v_u_140, tostring("EventTracking"), function(p157) --[[ Line: 521 ]]
            --[[ Upvalues: (copy 1): v_u_154 ]]
            local v158 = p157 == nil and {} or p157
            for v159, v160 in v_u_154:key_itr() do
                if v158[v159] == nil then
                    v158[v159] = 0
                end;
                v158[v159] = v158[v159] + v160
            end;
            return v158;
        end)
    end;
    f_cons()
    return v_u_50;
end;
return v_u_37;
