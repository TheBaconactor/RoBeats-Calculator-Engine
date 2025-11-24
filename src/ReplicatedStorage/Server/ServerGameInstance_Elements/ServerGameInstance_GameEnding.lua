-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:21 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
require(game.ReplicatedStorage.Shared.FlashEvery)
require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstanceMode)
require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_8 = require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
return {
    ["new"] = function(_, p_u_9, p_u_10) --[[ Name: new ]] --[[ Line: 20 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_6, (copy 3): v_u_8, (copy 4): v_u_2, (copy 5): v_u_7, (copy 6): v_u_3, (copy 7): v_u_4, (copy 8): v_u_5 ]]
        local v11 = {}
        local v_u_12 = 10000
        v11.all_players_finished = function(_) --[[ Name: all_players_finished ]] --[[ Line: 25 ]]
            --[[ Upvalues: (copy 1): p_u_10 ]]
            local v_u_13 = true
            p_u_10._util:slots_foreach(function(p14, _) --[[ Line: 27 ]]
                --[[ Upvalues: (ref 1): v_u_13 ]]
                if p14._finished == false then
                    v_u_13 = false
                end;
            end)
            return v_u_13;
        end;
        v11.single_player_game_and_early_quit = function(_) --[[ Name: single_player_game_and_early_quit ]] --[[ Line: 35 ]]
            --[[ Upvalues: (copy 1): p_u_10 ]]
            local v_u_15 = false
            if p_u_10._util:players_count() == 1 then
                p_u_10._util:slots_foreach(function(p16, _) --[[ Line: 39 ]]
                    --[[ Upvalues: (ref 1): v_u_15 ]]
                    if p16._early_quit == true then
                        v_u_15 = true
                    end;
                end)
            end;
            return v_u_15;
        end;
        v11.notify_local_finished = function(p17, p18, p19, p20) --[[ Name: notify_local_finished ]] --[[ Line: 48 ]]
            --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_1, (ref 3): v_u_6, (copy 4): p_u_9, (ref 5): v_u_8, (ref 6): v_u_2, (ref 7): v_u_7 ]]
            if p_u_10._util:player_in_game(p18) == false then
                return v_u_1:warnf("ServerGameInstance notify_local_finished gameid(%d) does not contain userid(%d)", p_u_10._game_id, p18);
            end;
            local v21, v22 = p_u_10._util:get_player(p18)
            if v21._finished == true then
                return v_u_1:warnf("ServerGameInstance_GameEnding:notify_local_finished player(%d) is already finished", p18);
            end;
            if p19 == true then
                v21._early_quit = true
            end;
            v21._finished = true
            local l_Score_0 = p20.Score
            local l_Chain_0 = p20.Chain
            local l_PerfectCount_0 = p20.PerfectCount
            local l_GreatCount_0 = p20.GreatCount
            local l_OkayCount_0 = p20.OkayCount
            local l_Accuracy_0 = p20.Accuracy
            v_u_6:is_int_greater_than(l_Score_0, -1)
            v_u_6:is_int_greater_than(l_Chain_0, -1)
            v_u_6:is_int_greater_than(l_PerfectCount_0, -1)
            v_u_6:is_int_greater_than(l_GreatCount_0, -1)
            v_u_6:is_int_greater_than(l_OkayCount_0, -1)
            v_u_6:is_int_greater_than(p20.MissCount, -1)
            v_u_6:is_int_greater_than(p20.NakedScore, -1)
            v_u_6:is_number(l_Accuracy_0)
            v_u_6:is_number(p20.FeverPercentage)
            v_u_6:is_int(p20.ComboMax)
            if l_Score_0 ~= v21._score then
                v_u_1:warnf("GameEnding:notify_local_finished mismatch scores expected(%d) sent(%d)", v21._score, l_Score_0)
            end;
            v21._chain = math.max(v21._chain, l_Chain_0)
            v21._fever_percentage = math.max(v21._fever_percentage, p20.FeverPercentage)
            v21._combo_max = math.max(v21._combo_max, p20.ComboMax)
            local v_u_23 = p19 == true and p_u_9._player_manager:id_to_player(p18)
            if v_u_23 then
                v21._score = 0
                if p_u_10._player_note_sequence_info:contains(v22) then
                    p17:on_finish_write_note_sequence_info_to_player(v21, (p_u_10._player_note_sequence_info:get(v22)))
                end;
                p_u_9._chat:gameid_send_system_message(p_u_10._game_id, string.format("%s has ended their game early.", v_u_23.Name), function(p24) --[[ Line: 113 ]]
                    --[[ Upvalues: (ref 1): p_u_9, (copy 2): v_u_23, (ref 3): v_u_8 ]]
                    local v25 = p_u_9._player_blob_manager:get_cached_blob(v_u_23.UserId)
                    if v25 ~= nil then
                        p24:set_icon(v_u_8:playerblob_get_chat_icon(v25))
                    end;
                end)
                p_u_9._evt:fire_event_to_client(v_u_2.EVT_Game_ServerNotifyDoEnd, v_u_23, (p_u_10._util:get_player_info_data()))
                local v26 = p_u_10._game_ended:get_id_to_geared_place()
                local v27 = p_u_10._game_ended:get_id_to_naked_place()
                local v28 = v26:get(p18)
                if v21._match_mode == v_u_7.Casual and v27:contains(p18) then
                    v28 = v27:get(p18)
                end;
                p_u_9._evt:fire_event_to_client(v_u_2.EVT_Game_ServerNotifyMatchEndRewards, v_u_23, {
                    ["MatchCoinReward"] = 0,
                    ["VIPCoinBonusReward"] = 0,
                    ["NoMissReward"] = 0,
                    ["MostAccurateReward"] = 0,
                    ["Place"] = v28,
                    ["PlayerCount"] = v26:count(),
                    ["QuitEarly"] = true,
                    ["SpectateCheerCount"] = 0,
                    ["SpectateCheerCoins"] = 0
                })
                p_u_9._player_status_manager:send_player_early_quit_match_end_event(p_u_10, p18)
            end;
        end;
        v11.get_server_gameending_timeout = function(_) --[[ Name: get_server_gameending_timeout ]] --[[ Line: 157 ]]
            --[[ Upvalues: (ref 1): v_u_12 ]]
            return v_u_12;
        end;
        v11.on_finish_write_note_sequence_info_to_player = function(_, p29, p30) --[[ Name: on_finish_write_note_sequence_info_to_player ]] --[[ Line: 159 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_3, (ref 3): v_u_1 ]]
            if p30 ~= nil then
                p29._score = p30:get_player_score():get_score()
                p29._naked_score = p30:get_player_naked_score():get_score()
                p29._accuracy = p30:get_player_score():get_accuracy()
                if p29._match_mode == v_u_7.Casual then
                    local v31, v32, v33, v34 = p30:get_player_naked_score():get_stat_counts()
                    p29._perfect_count = v31
                    p29._great_count = v32
                    p29._okay_count = v33
                    p29._miss_count = v34
                else
                    local v35, v36, v37, v38 = p30:get_player_score():get_stat_counts()
                    p29._perfect_count = v35
                    p29._great_count = v36
                    p29._okay_count = v37
                    p29._miss_count = v38
                end;
            end;
            p29._has_game_end_info = true
            if v_u_3:is_dev_build() then
                v_u_1:puts("ServerGameInstance_GameEnding:on_finish_write_note_sequence_info_to_player Perfect(%d) Great(%d) Okay(%d) Miss(%d) Score(%d) NakedScore(%d) Accuracy(%.2f)", p29._perfect_count, p29._great_count, p29._okay_count, p29._miss_count, p29._score, p29._naked_score, p29._accuracy)
            end;
        end;
        v11.update = function(p_u_39, p40) --[[ Name: update ]] --[[ Line: 189 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_4, (copy 3): p_u_10, (ref 4): v_u_1, (copy 5): p_u_9, (ref 6): v_u_2, (ref 7): v_u_3, (ref 8): v_u_5 ]]
            local v41 = v_u_12
            v_u_12 = v_u_12 - v_u_4:TimescaleToDeltaTime(p40) * 1000
            if v41 > 0 and v_u_12 <= 0 then
                p_u_10._util:slots_foreach(function(p42, _) --[[ Line: 193 ]]
                    p42._finished = true
                end)
                v_u_1:warnf("ServerGameInstance_GameEnding:update _selected_song_key(%s) timeout reached, forcing all players to finish", (tostring(p_u_10._selected_song_key)))
            end;
            if p_u_39:all_players_finished() then
                p_u_10._util:slots_foreach(function(p43, p44) --[[ Line: 200 ]]
                    --[[ Upvalues: (ref 1): p_u_10, (copy 2): p_u_39 ]]
                    p43._score = 0
                    if p_u_10._player_note_sequence_info:contains(p44) then
                        p_u_39:on_finish_write_note_sequence_info_to_player(p43, (p_u_10._player_note_sequence_info:get(p44)))
                    end;
                end)
                local v_u_45 = p_u_10._util:get_player_info_data()
                p_u_10:set_gameend_data(v_u_45)
                p_u_10._util:slots_foreach(function(p46, _) --[[ Line: 210 ]]
                    --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_2, (copy 3): v_u_45 ]]
                    local v47 = p_u_9._player_manager:id_to_player(p46._id)
                    if v47 then
                        if p46:did_early_quit_or_leave() then
                            return;
                        end;
                        p_u_9._evt:fire_event_to_client(v_u_2.EVT_Game_ServerNotifyDoEnd, v47, v_u_45)
                    end;
                end)
                p_u_9._chat:gameid_send_system_message(p_u_10._game_id, "The match has ended.", function(p48) --[[ Line: 228 ]]
                    --[[ Upvalues: (ref 1): v_u_3 ]]
                    p48:set_icon(v_u_3:get_double_arrow_icon_assetid())
                end)
                p_u_10._game_ended:game_has_ended()
                p_u_10._current_mode = v_u_5.GameEnded
            end;
        end;
        return v11;
    end
};
