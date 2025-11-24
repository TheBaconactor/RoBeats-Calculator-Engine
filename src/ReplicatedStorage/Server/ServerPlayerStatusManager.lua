-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:17 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.PlayerStatus)
return {
    ["new"] = function(_, p_u_8) --[[ Name: new ]] --[[ Line: 14 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_2, (copy 4): v_u_7, (copy 5): v_u_1, (copy 6): v_u_5, (copy 7): v_u_6 ]]
        local v9 = {}
        local v_u_10 = v_u_3:new()
        local v_u_11 = nil
        local v_u_12 = nil
        v9.start = function(_) --[[ Name: start ]] --[[ Line: 20 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_4, (ref 3): v_u_2, (copy 4): v_u_10, (ref 5): v_u_7, (ref 6): v_u_11, (ref 7): v_u_12 ]]
            p_u_8._evt:wait_on_event(v_u_4.EVT_PlayerStatus_ClientRequestInitial, function(p13) --[[ Line: 21 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_10, (ref 3): p_u_8, (ref 4): v_u_4, (ref 5): v_u_7 ]]
                local v14 = v_u_2:new()
                for _, v15 in v_u_10:key_itr() do
                    v14:push_back(v15)
                end;
                p_u_8._evt:fire_event_to_client(v_u_4.EVT_PlayerStatus_ServerRespondInitial, p13, v_u_7:list_to_tablelist(v14))
            end)
            local v16, v17 = v_u_7:backup_cleanup()
            v_u_11 = v16
            v_u_12 = v17
        end;
        v9.get_id_to_playerstatus = function(_) --[[ Name: get_id_to_playerstatus ]] --[[ Line: 31 ]]
            --[[ Upvalues: (copy 1): v_u_10 ]]
            return v_u_10;
        end;
        v9.player_disconnecting = function(_, p18) --[[ Name: player_disconnecting ]] --[[ Line: 33 ]]
            --[[ Upvalues: (copy 1): v_u_10 ]]
            v_u_10:remove(p18)
        end;
        local function f_update_playerstatus_list(p19) --[[ Name: update_playerstatus_list ]] --[[ Line: 37 ]]
            --[[ Upvalues: (copy 1): v_u_10, (ref 2): v_u_7, (copy 3): p_u_8, (ref 4): v_u_4 ]]
            for v20 = 1, p19:count() do
                local v21 = p19:get(v20)
                v_u_10:add(v21:get_player_id(), v21)
            end;
            local v22 = v_u_7:list_to_tablelist(p19)
            for _, v23 in p_u_8._player_manager:players_key_itr() do
                p_u_8._evt:fire_event_to_client(v_u_4.EVT_PlayerStatus_ServerUpdate, v23, v22)
            end;
        end;
        v9.send_player_lobby_load_event = function(_, p24) --[[ Name: send_player_lobby_load_event ]] --[[ Line: 49 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_1, (ref 3): v_u_7, (ref 4): v_u_2, (copy 5): f_update_playerstatus_list ]]
            local v25 = p_u_8._player_manager:id_to_player(p24)
            if v25 == nil then
                return v_u_1:warnf("ServerPlayerStatusManager nil player(%s)", (tostring(p24)));
            end;
            p_u_8._lobby_manager:cache_player_character_cframe(p24)
            local v26 = v_u_7:new(p24)
            v26:set_player_name(v25.Name)
            v26:set_mode(v_u_7.Mode.Waiting)
            v26:set_cframe(p_u_8._lobby_manager:get_playerid_cached_cframe(v26:get_player_id()))
            local v27 = v_u_2:new()
            v27:push_back(v26)
            f_update_playerstatus_list(v27)
            p_u_8._player_manager:raise_playerlist_update_next_frame()
        end;
        v9.send_player_join_matchmaking_event = function(_, p28, p29) --[[ Name: send_player_join_matchmaking_event ]] --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_8, (ref 3): v_u_2, (copy 4): f_update_playerstatus_list ]]
            local v30 = v_u_7:new(p28)
            v30:set_player_name(p_u_8._player_manager:id_to_player(p28).Name)
            v30:set_songkey(p29)
            v30:set_cframe(p_u_8._lobby_manager:get_playerid_cached_cframe(v30:get_player_id()))
            v30:set_mode(v_u_7.Mode.JoinedMatchmaking)
            local v31 = v_u_2:new()
            v31:push_back(v30)
            f_update_playerstatus_list(v31)
            p_u_8._player_manager:raise_playerlist_update_next_frame()
        end;
        local function f_game_instance_and_player_to_playing_preview_state(p32, p33, p34) --[[ Name: game_instance_and_player_to_playing_preview_state ]] --[[ Line: 79 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_8 ]]
            local v35 = v_u_7:new(p33._id)
            v35:set_player_name(p33._name)
            v35:set_songkey(p32._selected_song_key)
            v35:set_game_slot(p34)
            v35:set_playback_time_sec(p32._playback_time_ms / 1000)
            v35:set_sound_length_sec(p32._sound_length_ms / 1000)
            v35:set_cframe(p_u_8._lobby_manager:get_playerid_cached_cframe(v35:get_player_id()))
            return v35;
        end;
        v9.send_soundload_start_event = function(_, p_u_36) --[[ Name: send_soundload_start_event ]] --[[ Line: 90 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_8, (copy 3): f_game_instance_and_player_to_playing_preview_state, (ref 4): v_u_7, (copy 5): f_update_playerstatus_list ]]
            local v_u_37 = v_u_2:new()
            p_u_36._util:slots_foreach(function(p38, p39) --[[ Line: 92 ]]
                --[[ Upvalues: (ref 1): p_u_8, (ref 2): f_game_instance_and_player_to_playing_preview_state, (copy 3): p_u_36, (ref 4): v_u_7, (copy 5): v_u_37 ]]
                p_u_8._lobby_manager:cache_player_character_cframe(p38._id)
                local v40 = f_game_instance_and_player_to_playing_preview_state(p_u_36, p38, p39)
                v40:set_mode(v_u_7.Mode.MatchLoading)
                v_u_37:push_back(v40)
            end)
            f_update_playerstatus_list(v_u_37)
        end;
        v9.send_match_start_event = function(_, p_u_41) --[[ Name: send_match_start_event ]] --[[ Line: 102 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_8, (copy 3): f_game_instance_and_player_to_playing_preview_state, (ref 4): v_u_7, (copy 5): f_update_playerstatus_list ]]
            local v_u_42 = v_u_2:new()
            p_u_41._util:slots_foreach(function(p43, p44) --[[ Line: 104 ]]
                --[[ Upvalues: (ref 1): p_u_8, (ref 2): f_game_instance_and_player_to_playing_preview_state, (copy 3): p_u_41, (ref 4): v_u_7, (copy 5): v_u_42 ]]
                p_u_8._lobby_manager:cache_player_character_cframe(p43._id)
                local v45 = f_game_instance_and_player_to_playing_preview_state(p_u_41, p43, p44)
                v45:set_mode(v_u_7.Mode.MatchPlaying)
                v_u_42:push_back(v45)
            end)
            f_update_playerstatus_list(v_u_42)
            p_u_8._player_manager:raise_playerlist_update_next_frame()
        end;
        v9.send_match_end_event = function(_, p_u_46) --[[ Name: send_match_end_event ]] --[[ Line: 115 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): f_game_instance_and_player_to_playing_preview_state, (ref 3): v_u_7, (copy 4): f_update_playerstatus_list, (copy 5): p_u_8 ]]
            local v_u_47 = v_u_2:new()
            p_u_46._util:slots_foreach(function(p48, p49) --[[ Line: 117 ]]
                --[[ Upvalues: (ref 1): f_game_instance_and_player_to_playing_preview_state, (copy 2): p_u_46, (ref 3): v_u_7, (copy 4): v_u_47 ]]
                if p48._early_quit ~= true then
                    local v50 = f_game_instance_and_player_to_playing_preview_state(p_u_46, p48, p49)
                    v50:set_mode(v_u_7.Mode.MatchFinished)
                    v_u_47:push_back(v50)
                end;
            end)
            f_update_playerstatus_list(v_u_47)
            p_u_8._player_manager:raise_playerlist_update_next_frame()
        end;
        v9.send_player_early_quit_match_end_event = function(_, p51, p52) --[[ Name: send_player_early_quit_match_end_event ]] --[[ Line: 129 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_1, (ref 3): v_u_2, (ref 4): v_u_5, (copy 5): f_game_instance_and_player_to_playing_preview_state, (ref 6): v_u_7, (copy 7): f_update_playerstatus_list ]]
            if p_u_8._player_manager:id_to_player(p52) == nil then
                return v_u_1:warnf("ServerPlayerStatusManager nil player(%s)", (tostring(p52)));
            end;
            local v53 = v_u_2:new()
            local v54 = p51._util:get_player(p52)
            local v55 = p51._util:get_player_slot(p52)
            if v54 == nil then
                return v_u_1:warnf("ServerPlayerStatusManager:send_player_match_end_event nil itr_game_player(%s)", (tostring(p52)));
            end;
            if v54._early_quit ~= true then
                return v_u_1:warnf("ServerPlayerStatusManager:send_player_match_end_event itr_game_player(%s) not early quit", (tostring(p52)));
            end;
            if v_u_5:singleton():contains_key(p51._selected_song_key) ~= true then
                return v_u_1:warnf("ServerPlayerStatusManager:send_player_match_end_event invalid songkey(%s)", (tostring(p51._selected_song_key)));
            end;
            local v56 = f_game_instance_and_player_to_playing_preview_state(p51, v54, v55)
            v56:set_mode(v_u_7.Mode.MatchFinished)
            v53:push_back(v56)
            f_update_playerstatus_list(v53)
            p_u_8._player_manager:raise_playerlist_update_next_frame()
        end;
        v9.send_player_left_match_event = function(_, p_u_57, p_u_58) --[[ Name: send_player_left_match_event ]] --[[ Line: 151 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): f_game_instance_and_player_to_playing_preview_state, (ref 3): v_u_7, (copy 4): f_update_playerstatus_list, (copy 5): p_u_8 ]]
            local v_u_59 = v_u_2:new()
            p_u_58._util:slots_foreach(function(p60, p61) --[[ Line: 153 ]]
                --[[ Upvalues: (copy 1): p_u_57, (ref 2): f_game_instance_and_player_to_playing_preview_state, (copy 3): p_u_58, (ref 4): v_u_7, (copy 5): v_u_59 ]]
                if p_u_57 == p60._id then
                    local v62 = f_game_instance_and_player_to_playing_preview_state(p_u_58, p60, p61)
                    v62:set_mode(v_u_7.Mode.Waiting)
                    v_u_59:push_back(v62)
                end;
            end)
            f_update_playerstatus_list(v_u_59)
            p_u_8._player_manager:raise_playerlist_update_next_frame()
        end;
        v9.send_player_in_settings_event = function(_, p63, p64) --[[ Name: send_player_in_settings_event ]] --[[ Line: 164 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_1, (ref 3): v_u_7, (ref 4): v_u_2, (copy 5): f_update_playerstatus_list ]]
            local v65 = p_u_8._player_manager:id_to_player(p63)
            if v65 == nil then
                return v_u_1:warnf("ServerPlayerStatusManager nil player(%s)", (tostring(p63)));
            end;
            p_u_8._lobby_manager:cache_player_character_cframe(p63)
            local v66 = v_u_7:new(p63)
            v66:set_player_name(v65.Name)
            v66:set_songkey(p64)
            v66:set_mode(v_u_7.Mode.InSettings)
            v66:set_cframe(p_u_8._lobby_manager:get_playerid_cached_cframe(v66:get_player_id()))
            local v67 = v_u_2:new()
            v67:push_back(v66)
            f_update_playerstatus_list(v67)
        end;
        v9.update = function(_, p68) --[[ Name: update ]] --[[ Line: 181 ]]
            --[[ Upvalues: (copy 1): v_u_10, (ref 2): v_u_7, (ref 3): v_u_6, (ref 4): v_u_11, (ref 5): v_u_12 ]]
            for _, v69 in v_u_10:key_itr() do
                if v69:get_mode() == v_u_7.Mode.MatchPlaying then
                    v69:set_playback_time_sec((v_u_6:IncrementClamp(v69:get_playback_time_sec(), v_u_6:TimescaleToDeltaTime(p68), 0, v69:get_sound_length_sec())))
                end;
            end;
            v_u_11:update(p68)
            if v_u_11:do_flash() then
                v_u_12(v_u_10)
            end;
        end;
        return v9;
    end
};
