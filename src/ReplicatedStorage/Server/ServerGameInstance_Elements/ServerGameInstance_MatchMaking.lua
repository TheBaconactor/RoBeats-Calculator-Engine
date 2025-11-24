-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:21 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
require(game.ReplicatedStorage.Shared.FlashEvery)
require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_7 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstanceMode)
local v_u_8 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_9 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_10 = require(game.ReplicatedStorage.Server.ServerAPIManager)
require(game.ReplicatedStorage.SPChat.Shared.SPChatUtil)
require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
return {
    ["new"] = function(_, p_u_11, p_u_12) --[[ Name: new ]] --[[ Line: 20 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): v_u_6, (copy 5): v_u_7, (copy 6): v_u_8, (copy 7): v_u_1, (copy 8): v_u_10, (copy 9): v_u_3, (copy 10): v_u_9 ]]
        local v13 = {}
        v13.get_player_matchmaking_info = function(_) --[[ Name: get_player_matchmaking_info ]] --[[ Line: 23 ]]
            --[[ Upvalues: (copy 1): p_u_12 ]]
            local v_u_14 = {}
            p_u_12._util:slots_foreach(function(p15, p16) --[[ Line: 25 ]]
                --[[ Upvalues: (copy 1): v_u_14 ]]
                v_u_14[p16] = p15:get_player_matchmaking_info(p16)
            end)
            return v_u_14;
        end;
        v13.push_update_matchmaking_info = function(_) --[[ Name: push_update_matchmaking_info ]] --[[ Line: 31 ]]
            --[[ Upvalues: (copy 1): p_u_12 ]]
            p_u_12:set_frame_push_update_matchmaking_info()
        end;
        v13.send_update_matchmaking_info = function(p_u_17) --[[ Name: send_update_matchmaking_info ]] --[[ Line: 35 ]]
            --[[ Upvalues: (copy 1): p_u_12, (copy 2): p_u_11, (ref 3): v_u_4 ]]
            p_u_12._util:slots_foreach(function(p18, p19) --[[ Line: 36 ]]
                --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_4, (copy 3): p_u_17 ]]
                local v20 = p_u_11._player_manager:id_to_player(p18._id)
                if v20 ~= nil then
                    p_u_11._evt:fire_event_to_client(v_u_4.EVT_GameLoad_ServerUpdateMatchMakingInfo, v20, p_u_17:get_player_matchmaking_info(), p19)
                end;
            end)
        end;
        local v_u_21 = v_u_2:new()
        local function f_get_available_slot() --[[ Name: get_available_slot ]] --[[ Line: 50 ]]
            --[[ Upvalues: (copy 1): v_u_21, (copy 2): p_u_12, (ref 3): v_u_5, (ref 4): v_u_6 ]]
            v_u_21:clear()
            for v22 = 1, p_u_12._util.SLOTS_MAX do
                if p_u_12._slots:contains(v22) == false then
                    v_u_21:push_back(v22)
                end;
            end;
            if v_u_21:count() == 0 then
                return -1;
            elseif v_u_5.Do_OverrideAssignedSlotID and v_u_21:contains(v_u_5.OverrideAssignedSlotID) then
                return v_u_5.OverrideAssignedSlotID;
            elseif v_u_5.Do_RandomSlotAssign == true then
                return v_u_21:get(v_u_6:rand_rangei(1, v_u_21:count() + 1));
            else
                return v_u_21:get(1);
            end;
        end;
        v13.is_joinable = function(p23) --[[ Name: is_joinable ]] --[[ Line: 74 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_7, (copy 3): f_get_available_slot, (ref 4): v_u_8 ]]
            local v24
            if p_u_12._current_mode == v_u_7.MatchMaking and (p23:all_players_ready() == false and f_get_available_slot() ~= -1) then
                v24 = p_u_12._match_start_countdown >= v_u_8.MATCH_START_COUNTDOWN
            else
                v24 = false
            end;
            return v24;
        end;
        v13.request_slot_for_id = function(p25, p26, p27) --[[ Name: request_slot_for_id ]] --[[ Line: 81 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): f_get_available_slot, (copy 3): p_u_12, (copy 4): p_u_11, (ref 5): v_u_10, (ref 6): v_u_3 ]]
            if p27 == nil then
                v_u_1:errf("ServerGameInstance_Matchmaking:request_slot_for_id requested_song_key is nil")
            end;
            if p25:is_joinable() == false then
                v_u_1:warnf("ServerGameInstance request_slot_for_id NOT JOINABLE avail(%d) mode(%d)", f_get_available_slot(), p_u_12._current_mode)
                p_u_11._api:api_report_evt(v_u_10.ReportEvt_RequestSlotForId_NotJoinable)
                return -1;
            end;
            if p_u_12._util:get_player_slot(p26) ~= -1 then
                v_u_1:warnf("request_slot_for_id player already in game")
                return p_u_12._util:get_player_slot(p26);
            end;
            local v28 = p_u_11._player_manager:id_to_player(p26)
            if v28 == nil then
                v_u_1:warnf("ServerGameInstance request_slot_for_id cannot find player")
                p_u_11._api:api_report_evt(v_u_10.ReportEvt_RequestSlotForId_CannotFindPlayer)
                return -1;
            end;
            local v29 = v_u_3:new(p26, v28.Name)
            v29:set_requested_song_key(p27)
            local v30 = p_u_11._player_blob_manager:get_cached_blob(v28.UserId)
            if v30 then
                local v31, v32 = p_u_11._guild_manager:is_player_in_guild(v30.UserId)
                v_u_3:copy_icon_and_title_from_playerblob(v29, v30, v31, (p_u_11._guild_manager:get_guild_data_cached(v32)))
            end;
            local v33 = f_get_available_slot()
            p_u_12:add_player_to_slot(v33, v29)
            return v33;
        end;
        v13.player_notify_ready_state = function(p34, p35, p36) --[[ Name: player_notify_ready_state ]] --[[ Line: 121 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_1 ]]
            if p_u_12._util:player_in_game(p35) == false then
                v_u_1:errf("ServerGameInstance player_notify_ready_state gameid(%d) does not contain userid(%d)", p34._game_id, p35)
            end;
            p_u_12._util:get_player(p35)._ready = p36
            p34:push_update_matchmaking_info()
        end;
        v13.set_player_event_info = function(_, p37, p38) --[[ Name: set_player_event_info ]] --[[ Line: 127 ]]
            --[[ Upvalues: (copy 1): p_u_12 ]]
            if p_u_12._util:player_in_game(p37) == true then
                p_u_12._util:get_player(p37)._event_info = p38
            end;
        end;
        v13.all_players_ready = function(_) --[[ Name: all_players_ready ]] --[[ Line: 133 ]]
            --[[ Upvalues: (copy 1): p_u_12 ]]
            if p_u_12._util:players_count() == 0 then
                return false;
            end;
            local v_u_39 = true
            p_u_12._util:slots_foreach(function(p40, _) --[[ Line: 138 ]]
                --[[ Upvalues: (ref 1): v_u_39 ]]
                if p40._ready == false then
                    v_u_39 = false
                end;
            end)
            return v_u_39;
        end;
        v13.update = function(p41, p_u_42) --[[ Name: update ]] --[[ Line: 146 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_9, (copy 3): p_u_11, (ref 4): v_u_5, (ref 5): v_u_7, (ref 6): v_u_6, (ref 7): v_u_8 ]]
            if p_u_12._util:players_count() == p_u_12._util.SLOTS_MAX then
                p_u_12._util:slots_foreach(function(p43, _) --[[ Line: 148 ]]
                    p43._ready = true
                end)
                p41:push_update_matchmaking_info()
            end;
            if p41:all_players_ready() then
                local l__match_start_countdown_0 = p_u_12._match_start_countdown
                p_u_12._match_start_countdown = p_u_12._match_start_countdown - v_u_9:TimescaleToDeltaTime(p_u_42) * 1000
                local l__match_start_countdown_1 = p_u_12._match_start_countdown
                if p_u_12:frame_had_leave_evt() then
                    p_u_12._util:slots_foreach(function(p44, _) --[[ Line: 160 ]]
                        p44._ready = false
                    end)
                    p41:push_update_matchmaking_info()
                    p_u_11._chat:gameid_send_system_message(p_u_12._game_id, string.format("A Player has left the match. Finding another..."))
                    return;
                end;
                if p_u_12._util:players_count() == 1 and v_u_5.AlwaysShowVotePick ~= true then
                    p_u_12._current_mode = v_u_7.VotePick
                    p_u_12._votepick:start_vote_pick()
                    return;
                end;
                if l__match_start_countdown_1 <= 0 then
                    p_u_12._current_mode = v_u_7.VotePick
                    p_u_12._votepick:start_vote_pick()
                    return;
                end;
                if math.ceil(l__match_start_countdown_1 / 1000) < math.ceil(l__match_start_countdown_0 / 1000) then
                    p_u_11._chat:gameid_send_system_message(p_u_12._game_id, string.format("Game starting in %d seconds...", (math.ceil(l__match_start_countdown_1 / 1000))), function(p45) --[[ Line: 175 ]]
                        --[[ Upvalues: (ref 1): v_u_6 ]]
                        p45:set_icon(v_u_6:get_double_arrow_icon_assetid())
                    end)
                    return;
                end;
            else
                p_u_12._match_start_countdown = v_u_8.MATCH_START_COUNTDOWN
                p_u_12._util:slots_foreach(function(p46, _) --[[ Line: 189 ]]
                    --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_42 ]]
                    p46._matchmaking_time = p46._matchmaking_time + v_u_9:TimescaleToDeltaTime(p_u_42)
                end)
            end;
        end;
        return v13;
    end
};
