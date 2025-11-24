-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:17 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.LeaderboardSongInfo)
local v_u_7 = require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_8 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.EventLeaderboardRewards)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_11 = require(game.ReplicatedStorage.Shared.EventLeaderboardInfo)
local v_u_12 = require(game.ReplicatedStorage.Shared.FlashEvery)
require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
return {
    ["new"] = function(_, p_u_14) --[[ Name: new ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_5, (copy 3): v_u_3, (copy 4): v_u_6, (copy 5): v_u_11, (copy 6): v_u_9, (copy 7): v_u_10, (copy 8): v_u_13, (copy 9): v_u_4, (copy 10): v_u_1, (copy 11): v_u_7, (copy 12): v_u_12, (copy 13): v_u_8 ]]
        local v15 = {}
        local v_u_16 = v_u_2:new()
        local v_u_17 = 0
        local v_u_18 = 0
        local function _() --[[ Name: Y ]] --[[ Line: 28 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_5 ]]
            v_u_18 = v_u_5:rand_rangei(300, 600)
        end;
        local v_u_19 = v_u_5:rand_rangei(300, 600)
        v15.start = function(_) --[[ Name: start ]] --[[ Line: 33 ]]
            --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_3, (copy 3): v_u_16, (ref 4): v_u_6, (ref 5): v_u_11, (ref 6): v_u_9, (ref 7): v_u_5, (ref 8): v_u_10, (ref 9): v_u_13, (ref 10): v_u_4, (ref 11): v_u_1, (ref 12): v_u_17, (ref 13): v_u_19 ]]
            p_u_14._evt:wait_on_event(v_u_3.EVT_LeaderboardEvent_ClientRequestLeaderboardData, function(p_u_20) --[[ Line: 34 ]]
                --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_6, (ref 3): v_u_11, (ref 4): v_u_9, (ref 5): p_u_14, (ref 6): v_u_3, (ref 7): v_u_5, (ref 8): v_u_10, (ref 9): v_u_13 ]]
                local v_u_21 = {}
                for _, v22 in v_u_16:key_itr() do
                    v_u_21[#v_u_21 + 1] = v22:to_table()
                end;
                local v_u_23 = v_u_6:invalid_songkey()
                local v_u_24 = 0
                local v_u_25 = 0
                local v_u_26 = 0
                for _, v27 in v_u_16:key_itr() do
                    if v27:get_state() == v_u_11.State.Ended then
                        local v28 = v27:get_member_places()
                        for _, v29 in v28:key_itr() do
                            if v29:get_rbxid() == p_u_20.UserId and v29:has_claimed_reward() == false then
                                v29:claim_reward()
                                v_u_24 = v_u_24 + v_u_9:get_event_point_reward_for_place_and_player_count(v29:get_place(), v28:count())
                                v_u_25 = v29:get_place()
                                v_u_23 = v27:get_song_key()
                                v_u_26 = v28:count()
                            end;
                        end;
                    end;
                end;
                local function _(p30, p31) --[[ Name: Go ]] --[[ Line: 60 ]]
                    --[[ Upvalues: (ref 1): p_u_14, (ref 2): v_u_3, (copy 3): p_u_20, (copy 4): v_u_21 ]]
                    p_u_14._evt:fire_event_to_client(v_u_3.EVT_LeaderboardEvent_ServerRequestLeaderboardDataResponse, p_u_20, v_u_21, p30, p31)
                end;
                if v_u_24 > 0 then
                    p_u_14._player_blob_manager:get_verified_cached_blob(p_u_20.UserId, function(p32) --[[ Line: 65 ]]
                        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_25, (ref 3): v_u_26, (ref 4): v_u_6, (ref 5): v_u_23, (ref 6): v_u_24, (ref 7): v_u_10, (ref 8): p_u_14, (copy 9): p_u_20, (ref 10): v_u_13, (ref 11): v_u_3, (copy 12): v_u_21 ]]
                        local v_u_33 = string.format("For getting %s of %d entries in the event leaderboard for \"%s\", you have earned %d event points.", v_u_5:num_placify(v_u_25), v_u_26, v_u_6:singleton():get_title_for_key(v_u_23), v_u_24)
                        v_u_10:playerblob_set_event_points(p32, v_u_10:playerblob_get_event_points(p32) + v_u_24)
                        p_u_14._player_blob_manager:enqueue_blob_sync_request(p_u_20.UserId, v_u_13.PlayerBlobRequestType.Write, function(_) --[[ Line: 77 ]]
                            --[[ Upvalues: (copy 1): v_u_33, (ref 2): p_u_14, (ref 3): v_u_3, (ref 4): p_u_20, (ref 5): v_u_21 ]]
                            p_u_14._evt:fire_event_to_client(v_u_3.EVT_LeaderboardEvent_ServerRequestLeaderboardDataResponse, p_u_20, v_u_21, true, v_u_33)
                        end)
                    end)
                else
                    p_u_14._evt:fire_event_to_client(v_u_3.EVT_LeaderboardEvent_ServerRequestLeaderboardDataResponse, p_u_20, v_u_21, false, "")
                end;
            end)
            p_u_14._evt:wait_on_event(v_u_3.EVT_LeaderboardEvent_ClientDebugLeaderboard, function(p34) --[[ Line: 88 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_1, (ref 3): v_u_16, (ref 4): v_u_11, (ref 5): v_u_17, (ref 6): v_u_19, (ref 7): p_u_14, (ref 8): v_u_3 ]]
                if v_u_4.DebugEventLeaderboardKey ~= true then
                    return v_u_1:errf("EVT_LeaderboardEvent_ClientDebugLeaderboard DebugEventLeaderboardKey not enabled");
                end;
                local v35 = v_u_16:get(v_u_16:count())
                local v36 = v35 == nil
                if v35 ~= nil then
                    if v35:get_state() == v_u_11.State.Active then
                        v35:set_time_remaining(6)
                    elseif v35:get_state() == v_u_11.State.Closing then
                        v35:set_closing_time_remaining(6)
                    else
                        v36 = v35:get_state() == v_u_11.State.Ended and true or v36
                    end;
                end;
                if v36 then
                    v_u_17 = v_u_19 - 5
                end;
                p_u_14._evt:fire_event_to_client(v_u_3.EVT_LeaderboardEvent_ServerDebugLeaderboardResponse, p34)
            end)
        end;
        v15.player_disconnecting = function(_, p37) --[[ Name: player_disconnecting ]] --[[ Line: 117 ]]
            --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_11 ]]
            for _, v38 in v_u_16:key_itr() do
                if v38:get_state() == v_u_11.State.Active or v38:get_state() == v_u_11.State.Closing then
                    v38:remove_member_rbxid(p37)
                end;
            end;
        end;
        v15.rbxid_add_play_for_song_key = function(_, p39, p40, p41, p42, p43) --[[ Name: rbxid_add_play_for_song_key ]] --[[ Line: 126 ]]
            --[[ Upvalues: (copy 1): p_u_14, (copy 2): v_u_16, (ref 3): v_u_11, (ref 4): v_u_6, (ref 5): v_u_5 ]]
            local v44 = p_u_14._player_manager:id_to_player(p40)
            if v44 == nil then
                return;
            end;
            for _, v45 in v_u_16:key_itr() do
                if (v45:get_state() == v_u_11.State.Active or v45:get_state() == v_u_11.State.Closing) and v45:get_song_key() == p41 then
                    local v46, v47 = v45:add_member_play(p40, v44.Name, p42, p43)
                    local v48 = v46 and p_u_14._chat:gameid_get_channel(p39._game_id)
                    if v48 then
                        p_u_14._chat:get_chat_service():send_system_message_to_player_for_channel(v44, v48, string.format("Your play of \"%s\" with score %s has ranked you %s in the server event leaderboard.", v_u_6:singleton():get_title_for_key(v45:get_song_key()), v_u_5:comma_value(p42), v_u_5:num_placify(v47)), function(p49) --[[ Line: 148 ]]
                            --[[ Upvalues: (ref 1): v_u_5 ]]
                            p49:set_icon(v_u_5:important_assetid())
                        end)
                        return;
                    end;
                    break;
                end;
            end;
        end;
        local function f_I() --[[ Name: I ]] --[[ Line: 159 ]]
            --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_14, (ref 3): v_u_11, (ref 4): v_u_7, (ref 5): v_u_6, (ref 6): v_u_4, (ref 7): v_u_5, (copy 8): v_u_16, (ref 9): v_u_19 ]]
            local v50, v51, _, _ = v_u_10:is_event_active(p_u_14._api:get_day_event_list())
            if v50 == true then
                local v52 = v_u_11:new()
                v52:set_song_key(v_u_10:get_playable_song_set(v51):key_list():random())
                v52:set_time_remaining(v_u_7.FLASH_LEADERBOARD_DURATION)
                v52:set_closing_time_remaining(v_u_6:singleton():songkey_get_approx_length_sec(v52:get_song_key()) + v_u_7.FLASH_LEADERBOARD_CLOSING_BUFFER_TIME_SEC)
                v52:set_state(v_u_11.State.Active)
                p_u_14._chat:send_system_server_chat_message(string.format("An event leaderboard for the song \"%s\" has started!", v_u_6:singleton():get_title_for_key(v52:get_song_key())))
                p_u_14._chat:send_system_server_chat_message("Check the leaderboard tab in the event page for more details.")
                if v_u_4.DebugExtraFlashLeaderboardPlayers == true then
                    for v53 = 1, v_u_5:rand_rangei(3, 30) do
                        v52:add_member_play(v53, string.format("Test%d", v53), v_u_5:rand_rangei(1, 1000000), 1)
                    end;
                end;
                v_u_16:push_back(v52)
                v_u_19 = v_u_5:rand_rangei(300, 600)
            end;
        end;
        local v_u_54 = v_u_12:new(10)
        v15.update = function(_, p55) --[[ Name: update ]] --[[ Line: 187 ]]
            --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_11, (ref 3): v_u_17, (ref 4): v_u_8, (ref 5): v_u_19, (copy 6): f_I, (ref 7): v_u_7, (copy 8): p_u_14, (ref 9): v_u_6, (copy 10): v_u_54, (ref 11): v_u_1 ]]
            local v56 = true
            for _, v57 in v_u_16:key_itr() do
                if v57:get_state() == v_u_11.State.Active or v57:get_state() == v_u_11.State.Closing then
                    v56 = false
                    break;
                end;
            end;
            if v56 == true then
                v_u_17 = v_u_17 + v_u_8:TimescaleToDeltaTime(p55)
                if v_u_19 <= v_u_17 then
                    f_I()
                    v_u_17 = 0
                end;
            else
                v_u_17 = 0
            end;
            if v_u_16:count() > v_u_7.KEEP_LEADERBOARD_QUEUE_SIZE then
                v_u_16:pop_front()
            end;
            for _, v58 in v_u_16:key_itr() do
                local v59 = v58:get_state()
                v58:update(p55)
                if v59 ~= v58:get_state() then
                    if v58:get_state() == v_u_11.State.Closing then
                        p_u_14._chat:send_system_server_chat_message(string.format("The event leaderboard for song \"%s\" is closing!", v_u_6:singleton():get_title_for_key(v58:get_song_key())))
                        p_u_14._chat:send_system_server_chat_message("Please wait until the leaderboard ends to view the final results.")
                    elseif v58:get_state() == v_u_11.State.Ended then
                        p_u_14._chat:send_system_server_chat_message(string.format("The event leaderboard for song \"%s\" has closed!", v_u_6:singleton():get_title_for_key(v58:get_song_key())))
                        p_u_14._chat:send_system_server_chat_message("Check the leaderboard tab in the event page to claim any rewards.")
                    end;
                end;
            end;
            v_u_54:update(p55)
            if v_u_54:do_flash() then
                v_u_1:puts("#### ServerEventLeaderboardManager _count(%d) can_start_new_leaderboard(%s) _time_since_started_leaderboard(%d) _start_next_leaderboard_at_time(%d)", v_u_16:count(), tostring(v56), v_u_17, v_u_19)
            end;
        end;
        return v15;
    end
};
