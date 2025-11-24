-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:21 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_2 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassUtils)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
local v_u_10 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v11 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_12 = nil
v11:require_server(function() --[[ Line: 16 ]]
    --[[ Upvalues: (ref 1): v_u_12 ]]
    v_u_12 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
return {
    ["new"] = function(_, p_u_13, p_u_14, p_u_15, p_u_16) --[[ Name: new ]] --[[ Line: 22 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_3, (copy 3): v_u_2, (copy 4): v_u_1, (copy 5): v_u_7, (copy 6): v_u_8, (copy 7): v_u_4, (copy 8): v_u_10, (copy 9): v_u_9, (ref 10): v_u_12, (copy 11): v_u_6 ]]
        local v17 = {}
        v17.get_focused_slot = function(_) --[[ Name: get_focused_slot ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): p_u_16 ]]
            return p_u_16;
        end;
        v17.get_player_id = function(_) --[[ Name: get_player_id ]] --[[ Line: 26 ]]
            --[[ Upvalues: (copy 1): p_u_15 ]]
            return p_u_15;
        end;
        local v_u_18 = 0
        v17.get_cheer_count = function(_) --[[ Name: get_cheer_count ]] --[[ Line: 29 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            return v_u_18;
        end;
        local v_u_19 = 0
        v17.update = function(p20, p21) --[[ Name: update ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_5, (ref 3): v_u_3 ]]
            v_u_19 = v_u_19 + v_u_5:TimescaleToDeltaTime(p21)
            if v_u_19 > v_u_3.SPECTATE_PUSH_DATA_EVERY_SEC then
                v_u_19 = 0
                p20:push_spectate_info_to_player()
            end;
        end;
        local v_u_22 = 0
        v17.push_spectate_info_to_player = function(p23) --[[ Name: push_spectate_info_to_player ]] --[[ Line: 41 ]]
            --[[ Upvalues: (copy 1): p_u_13, (copy 2): p_u_15, (ref 3): v_u_2, (copy 4): p_u_14, (ref 5): v_u_22, (ref 6): v_u_1 ]]
            local v24 = p_u_13._player_manager:id_to_player(p_u_15)
            if v24 == nil then
                v_u_2:warnf("ServerMatchSpectator:push_spectate_info_to_player player nil(%d)", p_u_15)
                return;
            else
                local v25 = p_u_14._player_note_sequence_info:get((p23:get_focused_slot()))
                if v25 ~= nil then
                    local v26 = p_u_14._slots:get(p23:get_focused_slot())
                    local v27 = -1
                    if v26 then
                        v27 = v26._id
                    else
                        v_u_2:warnf("ServerMatchSpectator:push_spectate_info_to_player spectated_player nil slot(%d)", p23:get_focused_slot())
                    end;
                    local v28, v29 = v25:get_serialized_note_sequence_table_list_starting_at(v_u_22)
                    v_u_22 = v29
                    p_u_13._evt:fire_event_to_client(v_u_1.EVT_Spectate_ServerPushInfo, v24, p_u_14._game_id, {
                        ["FocusedSlot"] = p23:get_focused_slot(),
                        ["NoteSequences"] = v28,
                        ["TargetPlayerID"] = v27,
                        ["SpectateCooldownMS"] = p_u_13._game_instance_manager:get_cheer_cooldown_ms_for_player_id(p_u_15)
                    })
                end;
            end;
        end;
        v17.change_focused_slot = function(_, p30) --[[ Name: change_focused_slot ]] --[[ Line: 73 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_19, (ref 3): v_u_3, (ref 4): v_u_22 ]]
            p_u_16 = p30
            v_u_19 = v_u_3.SPECTATE_PUSH_DATA_EVERY_SEC
            v_u_22 = 0
        end;
        v17.send_gameending_player_info_data = function(p31, p32) --[[ Name: send_gameending_player_info_data ]] --[[ Line: 79 ]]
            --[[ Upvalues: (copy 1): p_u_13, (copy 2): p_u_15, (ref 3): v_u_2, (ref 4): v_u_1, (ref 5): v_u_3 ]]
            local v33 = p_u_13._player_manager:id_to_player(p_u_15)
            if v33 == nil then
                v_u_2:warnf("ServerMatchSpectator:send_gameending_player_info_data player nil")
            else
                p_u_13._evt:fire_event_to_client(v_u_1.EVT_Spectate_ServerResponseClientFinished, v33, {
                    ["PlayerInfoData"] = p32,
                    ["CheerCount"] = p31:get_cheer_count(),
                    ["CheerCoinReward"] = p31:get_cheer_count() * v_u_3.SPECTATE_CHEER_COIN_AMOUNT
                })
            end;
        end;
        v17.cheer_for_playerid = function(_, _) --[[ Name: cheer_for_playerid ]] --[[ Line: 92 ]]
            --[[ Upvalues: (copy 1): p_u_13, (copy 2): p_u_15, (ref 3): v_u_2, (ref 4): v_u_18, (ref 5): v_u_3 ]]
            local v34 = p_u_13._game_instance_manager:get_cheer_cooldown_ms_for_player_id(p_u_15)
            if v34 > 0 then
                v_u_2:warnf("ServerMatchSpectator:cheer_for_playerid _cheer_cooldown_ms(%.2f)", v34)
            else
                v_u_18 = v_u_18 + 1
                p_u_13._game_instance_manager:set_cheer_cooldown_ms_for_player_id(p_u_15, v_u_3.SPECTATE_CHEER_COOLDOWN_MS)
            end;
        end;
        local v_u_35 = false
        v17.apply_spectator_cheer_reward = function(p_u_36, p_u_37) --[[ Name: apply_spectator_cheer_reward ]] --[[ Line: 104 ]]
            --[[ Upvalues: (copy 1): p_u_13, (copy 2): p_u_15, (ref 3): v_u_35, (ref 4): v_u_3, (ref 5): v_u_7, (ref 6): v_u_8, (copy 7): p_u_14, (ref 8): v_u_4, (ref 9): v_u_10, (ref 10): v_u_9, (ref 11): v_u_12, (ref 12): v_u_6 ]]
            local v_u_38 = p_u_13._player_manager:id_to_player(p_u_15)
            if v_u_38 == nil then
                return p_u_37();
            elseif v_u_35 == true then
                p_u_37()
            else
                v_u_35 = true
                local v39 = p_u_36:get_cheer_count() * v_u_3.SPECTATE_CHEER_COIN_AMOUNT
                local v_u_40 = v39 < 0 and 0 or v39
                p_u_13._player_blob_manager:get_verified_cached_blob(p_u_15, function(p41) --[[ Line: 113 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (copy 2): p_u_36, (ref 3): v_u_40, (ref 4): v_u_7, (ref 5): v_u_8, (ref 6): p_u_14, (copy 7): v_u_38, (ref 8): v_u_4, (ref 9): v_u_10, (ref 10): v_u_9, (ref 11): p_u_15, (ref 12): v_u_12, (ref 13): v_u_6, (copy 14): p_u_37 ]]
                    p_u_13._mission_manager:apply_cheer_count_to_mission_for_player_blob(p41, p_u_36:get_cheer_count())
                    p41.CoinCurrency = p41.CoinCurrency + v_u_40
                    for _ = 1, p_u_36:get_cheer_count() do
                        v_u_7:playerblob_apply_action(p41, v_u_7.ActionType.Cheer)
                    end;
                    if p_u_36:get_cheer_count() > 0 then
                        local v42, v43 = v_u_8:is_event_active(p_u_13._api:get_day_event_list())
                        if v42 and v_u_8:get_event_point_reward_song_set(v43):contains(p_u_14._selected_song_key) then
                            local v44 = p_u_36:get_cheer_count() * v_u_8:get_cheer_event_point_count()
                            v_u_8:playerblob_validate_event_info(p41, v43)
                            v_u_8:playerblob_set_event_points(p41, v_u_8:playerblob_get_event_points(p41) + v44)
                            local v45 = p_u_13._chat:get_chat_service()
                            v45:send_system_message_to_player_for_channel(v_u_38, v45:get_channel(v45:get_server_system_channel_id()), string.format("You have earned %d event points for cheering.", v44), function(p46) --[[ Line: 134 ]]
                                --[[ Upvalues: (ref 1): v_u_4 ]]
                                p46:set_icon(v_u_4:important_assetid())
                            end)
                        end;
                        if v_u_10.UseChallengePassV2 == true then
                            p_u_13._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_9.DailyMissionType.CheerSpectate, p41)
                        end;
                        p_u_13._special_event_manager:write_special_event_data_for_player_action(p_u_15, v_u_12.PlayerActionEvent.CheerPlayer, {
                            ["Count"] = p_u_36:get_cheer_count()
                        })
                    end;
                    p_u_13._player_blob_manager:enqueue_blob_sync_request(p_u_15, v_u_6.PlayerBlobRequestType.Write, function(_) --[[ Line: 149 ]]
                        --[[ Upvalues: (ref 1): p_u_37 ]]
                        p_u_37()
                    end)
                end)
            end;
        end;
        return v17;
    end
};
