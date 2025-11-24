-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:21 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
require(game.ReplicatedStorage.Shared.FlashEvery)
require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstanceMode)
local v_u_9 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_10 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_11 = require(game.ReplicatedStorage.Server.ServerAPIManager)
require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_12 = require(game.ReplicatedStorage.Shared.MatchMakingSettings)
local v_u_13 = require(game.ReplicatedStorage.GameStage.GameStageUtil)
local v14 = {}
local v_u_15 = {
    ["Voting"] = 1,
    ["DebugWait"] = 2,
    ["Finished"] = 3
}
v14.new = function(_, p_u_16, p_u_17) --[[ Name: new ]] --[[ Line: 29 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_9, (copy 3): v_u_15, (copy 4): v_u_12, (copy 5): v_u_13, (copy 6): v_u_3, (copy 7): v_u_7, (copy 8): v_u_5, (copy 9): v_u_8, (copy 10): v_u_6, (copy 11): v_u_4, (copy 12): v_u_1, (copy 13): v_u_11, (copy 14): v_u_10 ]]
    local v18 = {}
    local v_u_19 = v_u_2:new({ 236 })
    local l_VOTEPICK_TIMEOUT_MS_0 = v_u_9.VOTEPICK_TIMEOUT_MS
    local l_Voting_0 = v_u_15.Voting
    local v_u_20 = 0
    v18.start_vote_pick = function(p21) --[[ Name: start_vote_pick ]] --[[ Line: 38 ]]
        --[[ Upvalues: (copy 1): p_u_17, (copy 2): p_u_16, (ref 3): v_u_12, (ref 4): v_u_13, (ref 5): v_u_3, (ref 6): v_u_7, (ref 7): v_u_19, (ref 8): v_u_5, (ref 9): v_u_8, (ref 10): v_u_6, (ref 11): l_VOTEPICK_TIMEOUT_MS_0, (ref 12): v_u_4 ]]
        p_u_17._util:slots_foreach(function(p22, _) --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): p_u_16, (ref 2): v_u_12, (ref 3): v_u_13 ]]
            local v23 = p_u_16._game_instance_manager:get_server_queued_player_for_id(p22._id)
            if v23 then
                p22._match_mode = v23:get_match_mode()
                if v_u_12:get_auto_equip_best_loadout(v23:get_matchmaking_settings()) then
                    p22._should_auto_equip_best_loadout = true
                end;
                local v24 = p_u_16._player_blob_manager:get_cached_blob(p22._id)
                local v25 = p_u_16._api:get_day_event_list()
                local l__event_info_0 = p22._event_info
                if v24 then
                    p22._stage_id = v_u_13:resolve_stage_id_for_playerblob_day_event_list_and_event_info(v_u_12:get_selected_game_stage(v23:get_matchmaking_settings()), v24, v25, l__event_info_0, p_u_16._collection_manager:get_collection_info_for_player_id_playerblob(v24.UserId, v24))
                end;
            end;
        end)
        p_u_16._game_instance_manager:remove_gameinstance_from_queue(p_u_17)
        local v_u_26 = v_u_3:new()
        p_u_17._util:slots_foreach(function(p27, _) --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_26 ]]
            if v_u_7:singleton():contains_key(p27._requested_song_key) then
                v_u_26:add(p27._requested_song_key, true)
            end;
        end)
        v_u_19 = v_u_26:key_list()
        if v_u_19:count() == 0 then
            v_u_19:push_back(236)
        end;
        if v_u_19:count() == 1 and v_u_5.AlwaysShowVotePick == false then
            p_u_17._current_mode = v_u_8.SoundLoad
            local v28 = p21:get_most_voted_song()
            p_u_17._sound_load:start_load(v28)
            p_u_16._chat:gameid_send_system_message(p_u_17._game_id, string.format("Now playing: %s by %s. (Difficulty: %d)", v_u_7:singleton():get_title_for_key(v28), v_u_7:singleton():get_artist_for_key(v28), v_u_7:singleton():get_difficulty_for_key(v28)), function(p29) --[[ Line: 90 ]]
                --[[ Upvalues: (ref 1): v_u_6 ]]
                p29:set_icon(v_u_6:get_double_arrow_icon_assetid())
            end)
        else
            p_u_17._util:slots_foreach(function(p30, _) --[[ Line: 96 ]]
                --[[ Upvalues: (ref 1): l_VOTEPICK_TIMEOUT_MS_0, (ref 2): p_u_16, (ref 3): v_u_19, (ref 4): v_u_4 ]]
                p30._timeout = l_VOTEPICK_TIMEOUT_MS_0
                local v31 = p_u_16._player_manager:id_to_player(p30._id)
                if v31 ~= nil and v_u_19 ~= nil then
                    p_u_16._evt:fire_event_to_client(v_u_4.EVT_GameLoad_ServerNotifyVotePickStart, v31, v_u_19:table_copy())
                end;
            end)
            p_u_16._chat:gameid_send_system_message(p_u_17._game_id, "Voting has started!")
        end;
        p_u_17._match_making:push_update_matchmaking_info()
    end;
    v18.player_notify_votepick_select = function(p32, p33, p34) --[[ Name: player_notify_votepick_select ]] --[[ Line: 117 ]]
        --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_1 ]]
        if p_u_17._util:player_in_game(p33) == false then
            v_u_1:errf("ServerGameInstanceplayer_notify_votepick_select gameid(%d) does not contain userid(%d)", p32._game_id, p33)
        else
            p_u_17._util:get_player(p33)._votepick_song_key = p34
            p_u_17._match_making:push_update_matchmaking_info()
        end;
    end;
    v18.player_notify_vote_match_mode = function(_, p35, p36) --[[ Name: player_notify_vote_match_mode ]] --[[ Line: 127 ]]
        --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_8 ]]
        if p_u_17._util:player_in_game(p35) == false then
            return;
        elseif p_u_17._current_mode == v_u_8.VotePick then
            local v37 = p_u_17._util:get_player(p35)
            if v37._match_mode ~= p36 then
                v37._match_mode = p36
                p_u_17._match_making:push_update_matchmaking_info()
            end;
        end;
    end;
    v18.all_players_voted = function(_) --[[ Name: all_players_voted ]] --[[ Line: 137 ]]
        --[[ Upvalues: (copy 1): p_u_17 ]]
        local v_u_38 = true
        p_u_17._util:slots_foreach(function(p39, _) --[[ Line: 139 ]]
            --[[ Upvalues: (ref 1): v_u_38 ]]
            if p39._votepick_song_key == nil then
                v_u_38 = false
            end;
        end)
        return v_u_38;
    end;
    v18.get_most_voted_song = function(_) --[[ Name: get_most_voted_song ]] --[[ Line: 147 ]]
        --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_19, (copy 3): p_u_17, (ref 4): v_u_1, (copy 5): p_u_16, (ref 6): v_u_11, (ref 7): v_u_6, (ref 8): v_u_2 ]]
        local v_u_40 = v_u_3:new()
        if v_u_19 ~= nil then
            for v41 = 1, v_u_19:count() do
                v_u_40:add(v_u_19:get(v41), 0)
            end;
        end;
        p_u_17._util:slots_foreach(function(p42, _) --[[ Line: 155 ]]
            --[[ Upvalues: (copy 1): v_u_40, (ref 2): v_u_1, (ref 3): p_u_16, (ref 4): v_u_11, (ref 5): v_u_6, (ref 6): p_u_17 ]]
            if p42._votepick_song_key ~= nil then
                if v_u_40:contains(p42._votepick_song_key) == false then
                    v_u_1:warnf("VotePick:get_most_voted_song() vote_counts does not contain(%d)", p42._votepick_song_key)
                    p_u_16._api:api_report_evt(v_u_11.ReportEvt_VotePick_NotFound, 0, 0, v_u_6:json_encode({
                        ["Slots"] = p_u_17._slots:json_encode_copy(),
                        ["GameId"] = p_u_17._game_id,
                        ["VotePickSongKey"] = p42._votepick_song_key,
                        ["VoteCounts"] = v_u_40:json_encode_copy()
                    }))
                    v_u_40:add(p42._votepick_song_key, 0)
                end;
                if p42._votepick_song_key ~= nil then
                    v_u_40:add(p42._votepick_song_key, v_u_40:get(p42._votepick_song_key) + 1)
                end;
            end;
        end)
        local v43 = -1
        for _, v44 in v_u_40:key_itr() do
            if v43 < v44 then
                v43 = v44
            end;
        end;
        local v45 = v_u_2:new()
        for v46, v47 in v_u_40:key_itr() do
            if v47 == v43 then
                v45:push_back(v46)
            end;
        end;
        return v45:count() <= 0 and 236 or v45:random();
    end;
    v18.update = function(p48, p49) --[[ Name: update ]] --[[ Line: 202 ]]
        --[[ Upvalues: (ref 1): l_VOTEPICK_TIMEOUT_MS_0, (ref 2): v_u_10, (copy 3): p_u_17, (ref 4): v_u_19, (ref 5): l_Voting_0, (ref 6): v_u_15, (ref 7): v_u_5, (ref 8): v_u_20, (ref 9): v_u_1, (copy 10): p_u_16, (ref 11): v_u_7, (ref 12): v_u_6, (ref 13): v_u_8 ]]
        l_VOTEPICK_TIMEOUT_MS_0 = l_VOTEPICK_TIMEOUT_MS_0 - v_u_10:TimescaleToDeltaTime(p49) * 1000
        p_u_17._util:slots_foreach(function(p50, _) --[[ Line: 204 ]]
            --[[ Upvalues: (ref 1): l_VOTEPICK_TIMEOUT_MS_0, (ref 2): v_u_19 ]]
            p50._timeout = l_VOTEPICK_TIMEOUT_MS_0
            if p50._timeout <= 0 and p50._votepick_song_key == nil then
                if v_u_19 == nil then
                    p50._votepick_song_key = 236
                    return;
                end;
                p50._votepick_song_key = v_u_19:random()
            end;
        end)
        if l_Voting_0 == v_u_15.Voting then
            if p48:all_players_voted() then
                if v_u_5.AlwaysShowVotePick == true then
                    v_u_20 = 100
                    l_Voting_0 = v_u_15.DebugWait
                    v_u_1:puts("AlwaysShowVotePick debug wait(100)")
                else
                    l_Voting_0 = v_u_15.Finished
                end;
            end;
        elseif l_Voting_0 == v_u_15.DebugWait then
            v_u_20 = v_u_20 - p49
            v_u_1:puts("AlwaysShowVotePick debug wait(%.1f)", v_u_20)
            if v_u_20 < 0 then
                l_Voting_0 = v_u_15.Finished
                return;
            end;
        elseif l_Voting_0 == v_u_15.Finished then
            local v51 = p48:get_most_voted_song()
            p_u_16._chat:gameid_send_system_message(p_u_17._game_id, string.format("Voting has finished."))
            p_u_16._chat:gameid_send_system_message(p_u_17._game_id, string.format("Now playing: %s by %s. (Difficulty: %d)", v_u_7:singleton():get_title_for_key(v51), v_u_7:singleton():get_artist_for_key(v51), v_u_7:singleton():get_difficulty_for_key(v51)), function(p52) --[[ Line: 242 ]]
                --[[ Upvalues: (ref 1): v_u_6 ]]
                p52:set_icon(v_u_6:get_double_arrow_icon_assetid())
            end)
            p_u_17._current_mode = v_u_8.SoundLoad
            p_u_17._sound_load:start_load(v51)
        end;
    end;
    return v18;
end;
return v14;
