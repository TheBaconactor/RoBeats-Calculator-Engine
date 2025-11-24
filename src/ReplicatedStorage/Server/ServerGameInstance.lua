-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:14 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
require(game.ReplicatedStorage.Shared.FlashEvery)
require(game.ReplicatedStorage.Shared.NoteResult)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_6 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_7 = require(game.ReplicatedStorage.Server.Spectate.ServerPlayerNoteSequenceInfo)
local v_u_8 = require(game.ReplicatedStorage.Server.Spectate.ServerMatchSpectator)
require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_9 = require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
local v_u_10 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_11 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstanceMode)
local v_u_12 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstance_Util)
local v_u_13 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstance_MatchMaking)
local v_u_14 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstance_VotePick)
local v_u_15 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstance_SoundLoad)
local v_u_16 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstance_Game)
local v_u_17 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstance_GameEnding)
local v_u_18 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstance_GameEnded)
return {
    ["new"] = function(_, p19, p_u_20) --[[ Name: new ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_5, (copy 3): v_u_11, (copy 4): v_u_6, (copy 5): v_u_12, (copy 6): v_u_13, (copy 7): v_u_14, (copy 8): v_u_15, (copy 9): v_u_16, (copy 10): v_u_17, (copy 11): v_u_18, (copy 12): v_u_2, (copy 13): v_u_9, (copy 14): v_u_1, (copy 15): v_u_8, (copy 16): v_u_7, (copy 17): v_u_4, (copy 18): v_u_10 ]]
        local v29 = {
            ["_slots"] = v_u_3:new(),
            ["_player_note_sequence_info"] = v_u_3:new(),
            ["_game_id"] = p19,
            ["_selected_song_key"] = v_u_5:invalid_songkey(),
            ["_current_mode"] = v_u_11.MatchMaking,
            ["_num_leavers"] = 0,
            ["_match_start_countdown"] = v_u_6.MATCH_START_COUNTDOWN,
            ["_sound_length_ms"] = 0,
            ["_playback_time_ms"] = 0,
            ["_util"] = v_u_12:new(p_u_20, v29),
            ["_match_making"] = v_u_13:new(p_u_20, v29),
            ["_votepick"] = v_u_14:new(p_u_20, v29),
            ["_sound_load"] = v_u_15:new(p_u_20, v29),
            ["_game"] = v_u_16:new(p_u_20, v29),
            ["_game_ending"] = v_u_17:new(p_u_20, v29),
            ["_game_ended"] = v_u_18:new(p_u_20, v29),
            ["_spectators"] = v_u_2:new(),
            ["_has_gameending_player_info_data"] = false,
            ["_cached_gameending_player_info_data"] = {},
            ["_spectators_waiting_for_gameending_player_info_data"] = v_u_2:new(),
            ["set_gameend_data"] = function(p21, p22) --[[ Name: set_gameend_data ]] --[[ Line: 73 ]]
                p21._has_gameending_player_info_data = true
                p21._cached_gameending_player_info_data = p22
            end,
            ["spectate_client_finished"] = function(p23, p24) --[[ Name: spectate_client_finished ]] --[[ Line: 166 ]]
                local v25, _ = p23._util:is_player_spectating_gameinstance(p24)
                if v25 then
                    p23._spectators_waiting_for_gameending_player_info_data:push_back(v25)
                end;
                return v25;
            end,
            ["valid_player_count"] = function(p26) --[[ Name: valid_player_count ]] --[[ Line: 224 ]]
                local v_u_27 = 0
                p26._util:slots_foreach(function(p28, _) --[[ Line: 226 ]]
                    --[[ Upvalues: (ref 1): v_u_27 ]]
                    if p28._did_leave ~= true then
                        v_u_27 = v_u_27 + 1
                    end;
                end)
                return v_u_27;
            end
        }
        local v_u_30 = false
        v29.frame_had_join_evt = function(_) --[[ Name: frame_had_join_evt ]] --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            return v_u_30;
        end;
        local v_u_31 = false
        v29.frame_had_leave_evt = function(_) --[[ Name: frame_had_leave_evt ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_31 ]]
            return v_u_31;
        end;
        p_u_20._chat:create_channel_for_gameid(v29._game_id)
        v29.add_player_to_slot = function(p32, p33, p34) --[[ Name: add_player_to_slot ]] --[[ Line: 80 ]]
            --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_9, (ref 3): v_u_30 ]]
            p32._slots:add(p33, p34)
            local v_u_35 = p_u_20._player_manager:id_to_player(p34._id)
            if v_u_35 ~= nil and p_u_20._chat:add_player_to_channel_for_gameid(v_u_35, p32._game_id) then
                p_u_20._chat:gameid_send_system_message(p32._game_id, string.format("%s has joined the match.", v_u_35.Name), function(p36, _) --[[ Line: 94 ]]
                    --[[ Upvalues: (ref 1): p_u_20, (copy 2): v_u_35, (ref 3): v_u_9 ]]
                    local v37 = p_u_20._player_blob_manager:get_cached_blob(v_u_35.UserId)
                    if v37 ~= nil then
                        p36:set_icon(v_u_9:playerblob_get_chat_icon(v37))
                    end;
                end)
            end;
            v_u_30 = true
        end;
        v29.remove_player_from_slot = function(p38, p39) --[[ Name: remove_player_from_slot ]] --[[ Line: 107 ]]
            --[[ Upvalues: (ref 1): v_u_31 ]]
            local v40 = p38._slots:get(p39)
            p38._slots:remove(p39)
            p38._player_note_sequence_info:remove(p39)
            if v40 ~= nil and v40._did_leave ~= true then
                p38:remove_playerid_from_game_chat_channel(v40._id)
            end;
            v_u_31 = true
        end;
        v29.remove_playerid_from_game_chat_channel = function(p41, p42) --[[ Name: remove_playerid_from_game_chat_channel ]] --[[ Line: 119 ]]
            --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_9, (ref 3): v_u_1 ]]
            local v_u_43 = p_u_20._player_manager:id_to_player(p42)
            if v_u_43 == nil then
                v_u_1:warnf("ServerGameInstance:remove_player_from_slot player_target is nil")
            elseif p_u_20._chat:remove_player_from_channel_for_gameid(v_u_43, p41._game_id) then
                p_u_20._chat:gameid_send_system_message(p41._game_id, string.format("%s has left the match.", v_u_43.Name), function(p44) --[[ Line: 130 ]]
                    --[[ Upvalues: (ref 1): p_u_20, (copy 2): v_u_43, (ref 3): v_u_9 ]]
                    local v45 = p_u_20._player_blob_manager:get_cached_blob(v_u_43.UserId)
                    if v45 ~= nil then
                        p44:set_icon(v_u_9:playerblob_get_chat_icon(v45))
                    end;
                end)
                return;
            end;
        end;
        v29.spectator_joined = function(p46, p47, p48) --[[ Name: spectator_joined ]] --[[ Line: 143 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_20 ]]
            local v49 = false
            for v50 = 1, p46._spectators:count() do
                if p47 == p46._spectators:get(v50):get_player_id() then
                    v49 = true
                    break;
                end;
            end;
            if v49 == false then
                p46._spectators:push_back((v_u_8:new(p_u_20, p46, p47, p48)))
            end;
            local v51 = p_u_20._player_manager:id_to_player(p47)
            if v51 ~= nil and p_u_20._chat:add_player_to_channel_for_gameid(v51, p46._game_id) then
                p_u_20._chat:gameid_send_system_message(p46._game_id, string.format("%s is now spectating.", v51.Name))
            end;
        end;
        v29.spectator_leave = function(p52, p53) --[[ Name: spectator_leave ]] --[[ Line: 174 ]]
            --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_1 ]]
            local v54 = p_u_20._player_manager:id_to_player(p53)
            if v54 == nil then
                v_u_1:warnf("ServerGameInstance:spectator_leave tar_player nil")
            elseif p_u_20._chat:remove_player_from_channel_for_gameid(v54, p52._game_id) then
                p_u_20._chat:gameid_send_system_message(p52._game_id, string.format("%s has stopped spectating.", v54.Name))
            end;
            local v55, v56 = p52._util:is_player_spectating_gameinstance(p53)
            if v55 then
                p52._spectators:remove_at(v56)
            else
                v_u_1:warnf("ServerGameInstance:spectator_leave cannot find")
            end;
            p52:set_frame_push_update_game_info()
            return v55;
        end;
        v29.select_song = function(p_u_57, p_u_58) --[[ Name: select_song ]] --[[ Line: 198 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_20 ]]
            p_u_57._selected_song_key = p_u_58
            p_u_57._util:update_player_gear_info()
            p_u_57._util:slots_foreach(function(p59, p60) --[[ Line: 205 ]]
                --[[ Upvalues: (copy 1): p_u_57, (ref 2): v_u_7, (ref 3): p_u_20, (copy 4): p_u_58 ]]
                p_u_57._player_note_sequence_info:add(p60, v_u_7:new(p_u_20, p_u_57, p59, p_u_58))
            end)
        end;
        local v_u_61 = false
        v29.set_frame_push_update_matchmaking_info = function(_) --[[ Name: set_frame_push_update_matchmaking_info ]] --[[ Line: 211 ]]
            --[[ Upvalues: (ref 1): v_u_61 ]]
            v_u_61 = true
        end;
        local v_u_62 = false
        v29.set_frame_push_update_game_info = function(_) --[[ Name: set_frame_push_update_game_info ]] --[[ Line: 216 ]]
            --[[ Upvalues: (ref 1): v_u_62 ]]
            v_u_62 = true
        end;
        v29.on_remove = function(p63) --[[ Name: on_remove ]] --[[ Line: 220 ]]
            --[[ Upvalues: (copy 1): p_u_20 ]]
            p_u_20._chat:remove_channel_for_gameid(p63._game_id)
        end;
        local v_u_64 = 0
        v29.update = function(p_u_65, p_u_66) --[[ Name: update ]] --[[ Line: 235 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_64, (ref 3): v_u_10, (ref 4): v_u_6, (ref 5): v_u_1, (ref 6): v_u_11, (ref 7): v_u_61, (ref 8): v_u_62, (ref 9): v_u_30, (ref 10): v_u_31 ]]
            v_u_4:ptry(function() --[[ Line: 236 ]]
                --[[ Upvalues: (ref 1): v_u_64, (ref 2): v_u_10, (copy 3): p_u_66, (copy 4): p_u_65, (ref 5): v_u_6, (ref 6): v_u_1, (ref 7): v_u_11, (ref 8): v_u_61, (ref 9): v_u_62, (ref 10): v_u_30, (ref 11): v_u_31 ]]
                v_u_64 = v_u_64 + v_u_10:TimescaleToDeltaTime(p_u_66)
                if p_u_65:valid_player_count() == 0 and p_u_65._spectators:count() == 0 or v_u_64 > v_u_6.SERVER_GAME_INSTANCE_SANITY_SEC_TIME_SEC then
                    if v_u_64 > v_u_6.SERVER_GAME_INSTANCE_SANITY_SEC_TIME_SEC then
                        v_u_1:warnf("ServerGameInstance:update game_instance_lifetime_sec(%d) > SERVER_GAME_INSTANCE_SANITY_SEC_TIME_SEC(%d), force removing game instance", v_u_64, v_u_6.SERVER_GAME_INSTANCE_SANITY_SEC_TIME_SEC)
                    end;
                    p_u_65._util:slots_foreach(function(_, p67) --[[ Line: 244 ]]
                        --[[ Upvalues: (ref 1): p_u_65 ]]
                        p_u_65:remove_player_from_slot(p67)
                    end)
                    p_u_65._current_mode = v_u_11.DoRemove
                end;
                for v68 = 1, p_u_65._spectators:count() do
                    p_u_65._spectators:get(v68):update(p_u_66)
                end;
                if p_u_65._current_mode == v_u_11.MatchMaking then
                    p_u_65._match_making:update(p_u_66)
                elseif p_u_65._current_mode == v_u_11.VotePick then
                    p_u_65._votepick:update(p_u_66)
                elseif p_u_65._current_mode == v_u_11.SoundLoad then
                    p_u_65._sound_load:update(p_u_66)
                elseif p_u_65._current_mode == v_u_11.Game then
                    p_u_65._game:update(p_u_66)
                elseif p_u_65._current_mode == v_u_11.GameEnding then
                    p_u_65._game_ending:update(p_u_66)
                elseif p_u_65._current_mode == v_u_11.GameEnded then
                    p_u_65._game_ended:update(p_u_66)
                end;
                if v_u_61 == true then
                    v_u_61 = false
                    p_u_65._match_making:send_update_matchmaking_info()
                end;
                if v_u_62 == true then
                    v_u_62 = false
                    p_u_65._util:send_update_player_info()
                end;
                v_u_30 = false
                v_u_31 = false
                if p_u_65._has_gameending_player_info_data == true and p_u_65._spectators_waiting_for_gameending_player_info_data:count() > 0 then
                    for v69 = 1, p_u_65._spectators_waiting_for_gameending_player_info_data:count() do
                        p_u_65._spectators_waiting_for_gameending_player_info_data:get(v69):send_gameending_player_info_data(p_u_65._cached_gameending_player_info_data)
                    end;
                    p_u_65._spectators_waiting_for_gameending_player_info_data:clear()
                end;
            end)
        end;
        v29.flag_removed_players_and_spectators_as_did_leave = function(p_u_70, p_u_71) --[[ Name: flag_removed_players_and_spectators_as_did_leave ]] --[[ Line: 296 ]]
            --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_1 ]]
            p_u_70._util:slots_foreach(function(p72) --[[ Line: 297 ]]
                --[[ Upvalues: (ref 1): p_u_20, (ref 2): v_u_1, (copy 3): p_u_71, (copy 4): p_u_70 ]]
                if p72 == nil then
                    return;
                elseif p72._did_leave ~= true then
                    local l__id_0 = p72._id
                    if p_u_20._player_manager:id_to_player(l__id_0) == nil then
                        p72._did_leave = true
                        v_u_1:warnf("ServerGameInstance:flag_removed_players_and_spectators_as_did_leave playerid(%d) has no player, setting as did_leave", l__id_0)
                    end;
                    local v73 = p_u_71:get(l__id_0)
                    if v73 ~= nil and v73 ~= p_u_70 then
                        p72._did_leave = true
                        v_u_1:warnf("ServerGameInstance:flag_removed_players_and_spectators_as_did_leave playerid(%d) is in another gameinstance, setting as did_leave", l__id_0)
                    end;
                end;
            end)
            for v74 = p_u_70._spectators:count(), 1, -1 do
                local v75 = p_u_70._spectators:get(v74):get_player_id()
                if p_u_20._player_manager:id_to_player(v75) == nil then
                    p_u_70._spectators:remove_at(v74)
                    v_u_1:warnf("ServerGameInstance:flag_removed_players_and_spectators_as_did_leave spectator_player_id(%d) has no player, removing", v75)
                elseif p_u_71:contains(v75) == true then
                    p_u_70._spectators:remove_at(v74)
                    v_u_1:warnf("ServerGameInstance:flag_removed_players_and_spectators_as_did_leave spectator_player_id(%d) is in another gameinstance, removing", v75)
                end;
            end;
        end;
        return v29;
    end
};
