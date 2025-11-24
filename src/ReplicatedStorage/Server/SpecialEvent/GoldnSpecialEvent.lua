-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:19 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Pets.PetUtils)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.Override)
local v_u_7 = require(game.ReplicatedStorage.Shared.AudioRank)
require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_8 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_9 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local s_BadgeService_0 = game:GetService("BadgeService")
local v10 = {}
local v11 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_12 = nil
v11:require_server(function() --[[ Line: 22 ]]
    --[[ Upvalues: (ref 1): v_u_12 ]]
    v_u_12 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
v10.new = function(_, p_u_13) --[[ Name: new ]] --[[ Line: 26 ]]
    --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_1, (copy 5): v_u_5, (copy 6): v_u_6, (copy 7): s_BadgeService_0, (copy 8): v_u_9, (copy 9): v_u_7, (copy 10): v_u_2, (copy 11): v_u_8 ]]
    local v14 = v_u_12.EventBase:new()
    local v_u_15 = v_u_3:new()
    local function _() --[[ Name: cons ]] --[[ Line: 31 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_13, (ref 3): v_u_4, (ref 4): v_u_1, (ref 5): v_u_5 ]]
        local v_u_16 = v_u_3:new()
        p_u_13._evt:wait_on_event(v_u_4.EVT_SpecialEvent_GoldnClaimHuntIDClient, function(p_u_17, p18) --[[ Line: 33 ]]
            --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_3, (ref 3): p_u_13, (ref 4): v_u_4, (ref 5): v_u_1, (ref 6): v_u_5 ]]
            if v_u_16:contains(p_u_17.UserId) ~= true then
                v_u_16:add(p_u_17.UserId, v_u_3:new())
            end;
            local v_u_19 = v_u_16:get(p_u_17.UserId)
            local function f_response(p20, p21, p22) --[[ Name: response ]] --[[ Line: 39 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_4, (copy 3): p_u_17, (copy 4): v_u_19 ]]
                if p22 == nil then
                    p22 = false
                end;
                p_u_13._evt:fire_event_to_client(v_u_4.EVT_SpecialEvent_GoldnClaimHuntIDServer, p_u_17, p20, p21, p22, v_u_19:get_table())
            end;
            if v_u_1:is_24kgoldn_event_active(p_u_13._api:get_day_event_list()) == true then
                if v_u_1:get_24kgoldn_hunt_npc_ids_set():contains(p18) == true then
                    v_u_19:add_set(p18)
                    if v_u_3:set_equals(v_u_19, v_u_1:get_24kgoldn_hunt_npc_ids_set()) then
                        p_u_13._player_blob_manager:get_verified_cached_blob(p_u_17.UserId, function(p23) --[[ Line: 49 ]]
                            --[[ Upvalues: (ref 1): v_u_1, (copy 2): f_response, (ref 3): v_u_5, (ref 4): p_u_13, (copy 5): p_u_17 ]]
                            if v_u_1:get_24kgoldn_playerblob_has_claimed_pet(p23) then
                                return f_response(false, "Already claimed");
                            end;
                            v_u_5:server_grant_and_opt_equip_petid(p_u_13, p_u_17, v_u_1:get_24kgoldn_pet_id(), function(_) --[[ Line: 53 ]]
                                --[[ Upvalues: (ref 1): f_response ]]
                                return f_response(true, string.format("You found all the Golden Microphones!\nGot the 24kGoldn Mini."), true);
                            end)
                        end)
                    else
                        local v24, v25 = string.format("Found Golden Microphone #%d!\n%d remaining Golden Microphones to be found.", p18, v_u_1:get_24kgoldn_hunt_npc_ids_set():count() - v_u_19:count())
                        if v25 == nil then
                            v25 = false
                        end;
                        p_u_13._evt:fire_event_to_client(v_u_4.EVT_SpecialEvent_GoldnClaimHuntIDServer, p_u_17, true, v24, v25, v_u_19:get_table())
                    end;
                else
                    return f_response(false, "Invalid id");
                end;
            else
                return f_response(false, "Event is not active");
            end;
        end)
    end;
    v_u_6:get_base_fn(v14, "player_connecting")
    v14.player_connecting = function(_, p_u_26) --[[ Name: player_connecting ]] --[[ Line: 69 ]]
        --[[ Upvalues: (ref 1): s_BadgeService_0, (copy 2): v_u_15, (copy 3): p_u_13 ]]
        spawn(function() --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): s_BadgeService_0, (copy 2): p_u_26, (ref 3): v_u_15, (ref 4): p_u_13 ]]
            if s_BadgeService_0:UserHasBadgeAsync(p_u_26, 2124575372) then
                v_u_15:add(p_u_26, true)
                p_u_13._special_event_manager:get_eventdata_for_playerid(p_u_26):get_table().GoldnHasBadge = true
                p_u_13._special_event_manager:send_updated_eventdata_to_playerid(p_u_26)
            end;
        end)
    end;
    v_u_6:get_base_fn(v14, "player_disconnecting")
    v14.player_disconnecting = function(_, p27) --[[ Name: player_disconnecting ]] --[[ Line: 81 ]]
        --[[ Upvalues: (copy 1): v_u_15 ]]
        v_u_15:remove(p27)
    end;
    v_u_6:get_base_fn(v14, "can_playerid_start_songkey")
    v14.can_playerid_start_songkey = function(_, _, p28, p29) --[[ Name: can_playerid_start_songkey ]] --[[ Line: 86 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_13 ]]
        if v_u_1:is_24kgoldn_event_active(p_u_13._api:get_day_event_list()) == true then
            if p29 == v_u_1.EventMission.GoldnEvent then
                return v_u_1:get_24kgoldn_event_playable_song_set():contains(p28);
            else
                return false;
            end;
        else
            return false;
        end;
    end;
    local v_u_30 = v_u_3:new()
    v_u_6:get_base_fn(v14, "write_special_event_data_for_play")
    v14.write_special_event_data_for_play = function(_, _, p31, _, p32, p33, _, p34) --[[ Name: write_special_event_data_for_play ]] --[[ Line: 95 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_13, (ref 3): v_u_3, (copy 4): v_u_30, (ref 5): v_u_9, (ref 6): v_u_7, (ref 7): v_u_2, (ref 8): v_u_8, (ref 9): v_u_12, (copy 10): v_u_15, (ref 11): s_BadgeService_0 ]]
        if v_u_1:is_24kgoldn_event_active(p_u_13._api:get_day_event_list()) == true then
            local l__id_0 = p33._id
            local v_u_35 = p_u_13._player_manager:id_to_player(l__id_0)
            local v36 = p_u_13._player_blob_manager:get_cached_blob(l__id_0)
            if v36 ~= nil and v_u_35 ~= nil then
                if v_u_1:get_24kgoldn_event_playable_song_set():contains(p31) then
                    v_u_3:counter_increment(v_u_30, l__id_0)
                    local v37 = v_u_3:counter_get(v_u_30, l__id_0)
                    p34.GoldnPlayCount = v37
                    if p33._event_info == v_u_1.EventMission.GoldnEvent and (v_u_1:get_24kgoldn_playerblob_has_claimed_gear(v36) ~= true and (v_u_9:playerblob_can_add_more_gear(v36) and (v_u_7:rank_value_to_index(v_u_7:accuracy_to_rank_value(p33._accuracy)) >= v_u_7:rank_value_to_index(v_u_7.Value.RankB) or v37 >= 3))) then
                        local v_u_38 = v_u_2:new():push_back_table_list({ v_u_8.RewardInfo:new(v_u_8.RewardType.Gear, 1, v_u_1:get_24kgoldn_gear_id()) })
                        v_u_12.EventBase:event_play_table_add_fn_post_sync(p34, function(p39, p_u_40) --[[ Line: 118 ]]
                            --[[ Upvalues: (ref 1): v_u_8, (ref 2): p_u_13, (copy 3): v_u_38, (copy 4): v_u_35 ]]
                            v_u_8:server_sync_reward_params(p_u_13, v_u_35, v_u_8:claim_reward_info_list_to_playerblob(p_u_13, p39, v_u_38), function(_) --[[ Line: 120 ]]
                                --[[ Upvalues: (copy 1): p_u_40 ]]
                                p_u_40()
                            end)
                        end)
                        p34.PopupMessageTitle = "Got the Gear!"
                        p34.PopupMessageBody = string.format("For your play, %s", v_u_8:generate_description_from_rewardinfo_list(v_u_38))
                    end;
                end;
                if v_u_15:contains(l__id_0) ~= true and (p32 >= 2 and (v_u_1:is_24kgoldn_pet_equipped(v36) and v_u_1:is_24kgoldn_gear_equipped(v36))) then
                    v_u_15:add_set(l__id_0)
                    spawn(function() --[[ Line: 138 ]]
                        --[[ Upvalues: (ref 1): s_BadgeService_0, (copy 2): l__id_0 ]]
                        s_BadgeService_0:AwardBadge(l__id_0, 2124575372)
                    end)
                    p34.PopupMessageTitle = "You got the 24kGoldn Badge!"
                    p34.PopupMessageBody = "You got the 24kGoldn El Dorado (RoBeats) badge!\nCollect every badge in all the games to earn awesome avatar rewards."
                    p34.GoldnHasBadge = true
                end;
            end;
        else
            return;
        end;
    end;
    local v_u_41 = v_u_3:new()
    p_u_13._evt:wait_on_event(v_u_4.EVT_SpecialEvent_GoldnClaimHuntIDClient, function(p_u_42, p43) --[[ Line: 33 ]]
        --[[ Upvalues: (copy 1): v_u_41, (ref 2): v_u_3, (copy 3): p_u_13, (ref 4): v_u_4, (ref 5): v_u_1, (ref 6): v_u_5 ]]
        if v_u_41:contains(p_u_42.UserId) ~= true then
            v_u_41:add(p_u_42.UserId, v_u_3:new())
        end;
        local v_u_44 = v_u_41:get(p_u_42.UserId)
        local function f_response(p45, p46, p47) --[[ Name: response ]] --[[ Line: 39 ]]
            --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_4, (copy 3): p_u_42, (copy 4): v_u_44 ]]
            if p47 == nil then
                p47 = false
            end;
            p_u_13._evt:fire_event_to_client(v_u_4.EVT_SpecialEvent_GoldnClaimHuntIDServer, p_u_42, p45, p46, p47, v_u_44:get_table())
        end;
        if v_u_1:is_24kgoldn_event_active(p_u_13._api:get_day_event_list()) == true then
            if v_u_1:get_24kgoldn_hunt_npc_ids_set():contains(p43) == true then
                v_u_44:add_set(p43)
                if v_u_3:set_equals(v_u_44, v_u_1:get_24kgoldn_hunt_npc_ids_set()) then
                    p_u_13._player_blob_manager:get_verified_cached_blob(p_u_42.UserId, function(p48) --[[ Line: 49 ]]
                        --[[ Upvalues: (ref 1): v_u_1, (copy 2): f_response, (ref 3): v_u_5, (ref 4): p_u_13, (copy 5): p_u_42 ]]
                        if v_u_1:get_24kgoldn_playerblob_has_claimed_pet(p48) then
                            return f_response(false, "Already claimed");
                        end;
                        v_u_5:server_grant_and_opt_equip_petid(p_u_13, p_u_42, v_u_1:get_24kgoldn_pet_id(), function(_) --[[ Line: 53 ]]
                            --[[ Upvalues: (ref 1): f_response ]]
                            return f_response(true, string.format("You found all the Golden Microphones!\nGot the 24kGoldn Mini."), true);
                        end)
                    end)
                else
                    local v49, v50 = string.format("Found Golden Microphone #%d!\n%d remaining Golden Microphones to be found.", p43, v_u_1:get_24kgoldn_hunt_npc_ids_set():count() - v_u_44:count())
                    if v50 == nil then
                        v50 = false
                    end;
                    p_u_13._evt:fire_event_to_client(v_u_4.EVT_SpecialEvent_GoldnClaimHuntIDServer, p_u_42, true, v49, v50, v_u_44:get_table())
                end;
            else
                return f_response(false, "Invalid id");
            end;
        else
            return f_response(false, "Event is not active");
        end;
    end)
    return v14;
end;
return v10;
