-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:19 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistP3EventInfo)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_3 = require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_7 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.PlayerInfo.JumpChallengeInfo)
require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local s_BadgeService_0 = game:GetService("BadgeService")
local s_TeleportService_0 = game:GetService("TeleportService")
local v10 = {}
local v11 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_12 = nil
v11:require_server(function() --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_12 ]]
    v_u_12 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
v10.new = function(_, p_u_13) --[[ Name: new ]] --[[ Line: 27 ]]
    --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_5, (copy 5): v_u_4, (copy 6): s_BadgeService_0, (copy 7): v_u_7, (copy 8): s_TeleportService_0, (copy 9): v_u_9, (copy 10): v_u_3, (copy 11): v_u_6, (copy 12): v_u_8 ]]
    local v14 = v_u_12.EventBase:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 30 ]]
        --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_2, (ref 3): v_u_1, (ref 4): v_u_5, (ref 5): v_u_4, (ref 6): s_BadgeService_0, (ref 7): v_u_7, (ref 8): s_TeleportService_0, (ref 9): v_u_9 ]]
        p_u_13._evt:wait_on_event(v_u_2.EVT_SpecialEvent_GenericArtistP3Claim_Client, function(p_u_15) --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_2, (ref 3): v_u_1, (ref 4): v_u_5, (ref 5): v_u_4, (ref 6): s_BadgeService_0, (ref 7): v_u_7 ]]
            local function f_response(p16, p17, p18) --[[ Name: response ]] --[[ Line: 35 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_2, (copy 3): p_u_15 ]]
                p_u_13._evt:fire_event_to_client(v_u_2.EVT_SpecialEvent_GenericArtistP3Claim_Server, p_u_15, p16, p17, p18)
            end;
            if v_u_1:is_event_active(p_u_13._api:get_day_event_list()) ~= true then
                return f_response(false, "Event is not active");
            end;
            p_u_13._player_blob_manager:get_verified_cached_blob(p_u_15.UserId, function(p19) --[[ Line: 40 ]]
                --[[ Upvalues: (ref 1): p_u_13, (copy 2): p_u_15, (ref 3): v_u_1, (copy 4): f_response, (ref 5): v_u_5, (ref 6): v_u_4, (ref 7): s_BadgeService_0, (ref 8): v_u_7, (ref 9): v_u_2 ]]
                local v20 = p_u_13._collection_manager:get_collection_info_for_player_id_playerblob(p_u_15.UserId, p19)
                if v_u_1:test_playerblob_has_claimed_reward(p19, v20) then
                    return f_response(false, "Already claimed");
                end;
                if v_u_1:get_playerblob_owned_required_song_count(p19, v20) < v_u_1:get_required_song_set_owned_count() then
                    return f_response(false, "Did not collect at least %d songs", v_u_1:get_required_song_set_owned_count());
                end;
                local v21 = v_u_5:new()
                if v_u_1:test_playerblob_has_claimed_stage_reward(p19, v20) ~= true then
                    v21:push_back_from_list(v_u_1:get_reward_stage_list())
                end;
                if v_u_1:test_playerblob_has_claimed_gear_reward(p19) ~= true then
                    v21:push_back_from_list(v_u_1:get_reward_gear_list())
                end;
                local v_u_22 = v_u_4:claim_reward_info_list_to_playerblob(p_u_13, p19, v21)
                spawn(function() --[[ Line: 63 ]]
                    --[[ Upvalues: (ref 1): s_BadgeService_0, (ref 2): p_u_15, (ref 3): v_u_7 ]]
                    s_BadgeService_0:AwardBadge(p_u_15.UserId, 2153849432)
                    v_u_7:warnf("granting player(%s) robeats noscope badge", p_u_15.Name)
                end)
                v_u_4:server_sync_reward_params(p_u_13, p_u_15, v_u_22, function(p23) --[[ Line: 68 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_22, (ref 3): p_u_13, (ref 4): v_u_2, (ref 5): p_u_15 ]]
                    p_u_13._evt:fire_event_to_client(v_u_2.EVT_SpecialEvent_GenericArtistP3Claim_Server, p_u_15, true, p23, (v_u_4.RewardInfo:list_to_table(v_u_4:reward_params_get_resolved_reward_list(v_u_22))))
                end)
            end)
        end)
        p_u_13._evt:wait_on_event(v_u_2.EVT_SpecialEvent_GenericArtistP3Teleport_Client, function(p24) --[[ Line: 80 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): s_TeleportService_0 ]]
            v_u_7:puts("Teleporting player(%d) to (%d)", p24.UserId, 6407649031)
            s_TeleportService_0:TeleportAsync(6407649031, { p24 })
        end)
        p_u_13._evt:wait_on_event(v_u_2.EVT_SpecialEvent_GenericArtistP3ClaimBadgeReward_Client, function(p_u_25) --[[ Line: 87 ]]
            --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_2, (ref 3): v_u_1, (ref 4): v_u_9, (ref 5): v_u_7, (ref 6): s_BadgeService_0, (ref 7): v_u_4 ]]
            local function f_response(p26, p27, p28) --[[ Name: response ]] --[[ Line: 91 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_2, (copy 3): p_u_25 ]]
                p_u_13._evt:fire_event_to_client(v_u_2.EVT_SpecialEvent_GenericArtistP3ClaimBadgeReward_Server, p_u_25, p26, p27, p28)
            end;
            if v_u_1:is_event_active(p_u_13._api:get_day_event_list()) ~= true then
                return f_response(false, "Event is not active");
            end;
            if v_u_1:external_badge_reward_enabled() ~= true then
                return f_response(false, "External Badge reward not enabled");
            end;
            p_u_13._player_blob_manager:get_verified_cached_blob(p_u_25.UserId, function(p_u_29) --[[ Line: 96 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): p_u_13, (copy 3): p_u_25, (copy 4): f_response, (ref 5): v_u_9, (ref 6): v_u_7, (ref 7): s_BadgeService_0, (ref 8): v_u_4, (ref 9): v_u_2 ]]
                if v_u_1:test_playerblob_has_claimed_external_badge_reward(p_u_29, p_u_13._collection_manager:get_collection_info_for_player_id_playerblob(p_u_25.UserId, p_u_29)) then
                    return f_response(false, "Already claimed");
                end;
                spawn(function() --[[ Line: 99 ]]
                    --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_29, (ref 3): v_u_7, (ref 4): s_BadgeService_0, (ref 5): p_u_25, (ref 6): f_response, (ref 7): p_u_13, (ref 8): v_u_4, (ref 9): v_u_1, (ref 10): v_u_2 ]]
                    if v_u_9:is_tester_status(p_u_29) then
                        v_u_7:puts("EVT_SpecialEvent_GenericArtistP3ClaimBadgeReward_Client is_tester_status skip test")
                    elseif s_BadgeService_0:UserHasBadgeAsync(p_u_25.UserId, 2153893400) ~= true then
                        return f_response(false, "You have not gotten the badge from No-Scope Arcade.");
                    end;
                    p_u_13._post_fn:enqueue_function(function() --[[ Line: 108 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_13, (ref 3): p_u_29, (ref 4): v_u_1, (ref 5): p_u_25, (ref 6): v_u_2 ]]
                        v_u_4:server_sync_reward_params(p_u_13, p_u_25, v_u_4:claim_reward_info_list_to_playerblob(p_u_13, p_u_29, v_u_1:get_external_badge_reward_info_list()), function(p30) --[[ Line: 110 ]]
                            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_1, (ref 3): p_u_13, (ref 4): v_u_2, (ref 5): p_u_25 ]]
                            p_u_13._evt:fire_event_to_client(v_u_2.EVT_SpecialEvent_GenericArtistP3ClaimBadgeReward_Server, p_u_25, true, p30, (v_u_4.RewardInfo:list_to_table(v_u_1:get_external_badge_reward_info_list())))
                        end)
                    end)
                end)
            end)
        end)
    end;
    v_u_3:get_base_fn(v14, "can_playerid_start_songkey")
    v14.can_playerid_start_songkey = function(_, _, p31, _) --[[ Name: can_playerid_start_songkey ]] --[[ Line: 120 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_13 ]]
        if v_u_1:is_event_active(p_u_13._api:get_day_event_list()) == true then
            return v_u_1:get_playable_song_set():contains(p31);
        else
            return false;
        end;
    end;
    v_u_3:get_base_fn(v14, "write_special_event_data_for_play")
    v14.write_special_event_data_for_play = function(_, p32, p33, _, _, p34, p35, _) --[[ Name: write_special_event_data_for_play ]] --[[ Line: 126 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_13, (ref 3): v_u_6, (ref 4): v_u_7, (ref 5): v_u_9, (ref 6): v_u_8 ]]
        if v_u_1:is_event_active(p_u_13._api:get_day_event_list()) == true then
            if v_u_1:get_playable_song_set():contains(p33) == true then
                local l__id_0 = p34._id
                local v36 = p_u_13._player_manager:id_to_player(l__id_0)
                local v37 = p_u_13._player_blob_manager:get_cached_blob(l__id_0)
                if v37 == nil or v36 == nil then
                    return;
                else
                    local v38 = v_u_6:singleton():get_audiomod_to_modes_of_songkey(p33)
                    if v38:contains(v_u_6.MOD_NORMAL) == true then
                        local v_u_39 = v38:get(v_u_6.MOD_NORMAL)
                        if not v_u_1:playerblob_owns_song(v37, v_u_39, nil, p_u_13._collection_manager:get_collection_info_for_player_id_playerblob(l__id_0, v37)) then
                            p35:push_back(function(p40) --[[ Line: 150 ]]
                                --[[ Upvalues: (ref 1): v_u_9, (copy 2): v_u_39 ]]
                                v_u_9:add_song(p40, v_u_39)
                            end)
                            local v41 = p_u_13._chat:get_chat_service()
                            local v42 = p_u_13._chat:gameid_get_channel(p32._game_id)
                            if v42 then
                                v41:send_system_message_to_player_for_channel(v36, v42, string.format("For playing this song, you got a copy of \"%s\"!", v_u_6:singleton():get_title_for_key(v_u_39)), function(p43) --[[ Line: 164 ]]
                                    --[[ Upvalues: (ref 1): v_u_8 ]]
                                    p43:set_icon(v_u_8:important_assetid())
                                end)
                            end;
                        end;
                    else
                        v_u_7:warnf("songkey(%d) does not link to normal mode", p33)
                        return;
                    end;
                end;
            else
                return;
            end;
        else
            return;
        end;
    end;
    f_cons()
    return v14;
end;
return v10;
