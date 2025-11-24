-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:19 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.LeaderboardSongInfo)
local v_u_8 = require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_9 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.EventLeaderboardRewards)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_12 = require(game.ReplicatedStorage.Shared.EventLeaderboardInfo)
local v_u_13 = require(game.ReplicatedStorage.Shared.FlashEvery)
require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_15 = require(game.ReplicatedStorage.Shared.HUDNotification)
local v_u_16 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_17 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
local v18 = {}
local v_u_19 = nil
v18.singleton = function(_) --[[ Name: singleton ]] --[[ Line: 25 ]]
    --[[ Upvalues: (ref 1): v_u_19 ]]
    return v_u_19;
end;
v18.new = function(_, p_u_20) --[[ Name: new ]] --[[ Line: 29 ]]
    --[[ Upvalues: (ref 1): v_u_19, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_6, (copy 5): v_u_8, (copy 6): v_u_4, (copy 7): v_u_7, (copy 8): v_u_12, (copy 9): v_u_10, (copy 10): v_u_11, (copy 11): v_u_5, (copy 12): v_u_17, (copy 13): v_u_14, (copy 14): v_u_1, (copy 15): v_u_16, (copy 16): v_u_13, (copy 17): v_u_9 ]]
    local v21 = {}
    v_u_19 = v21
    local v_u_22 = v_u_2:new()
    local v_u_23 = 0
    local v_u_24 = 0
    local v_u_25 = v_u_3:new()
    local function _() --[[ Name: rand_gen_start_next_leaderboard_at_time ]] --[[ Line: 38 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_6, (ref 3): v_u_8 ]]
        v_u_24 = v_u_6:rand_rangei(v_u_8.EVENT_LEADERBOARD_START_MIN_TIME, v_u_8.EVENT_LEADERBOARD_START_MAX_TIME)
    end;
    local v_u_26 = v_u_6:rand_rangei(v_u_8.EVENT_LEADERBOARD_START_MIN_TIME, v_u_8.EVENT_LEADERBOARD_START_MAX_TIME)
    v21.start = function(_) --[[ Name: start ]] --[[ Line: 43 ]]
        --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_4, (copy 3): v_u_22, (ref 4): v_u_7, (ref 5): v_u_12, (ref 6): v_u_10, (ref 7): v_u_6, (ref 8): v_u_11, (ref 9): v_u_5, (ref 10): v_u_17, (ref 11): v_u_14, (ref 12): v_u_1, (ref 13): v_u_23, (ref 14): v_u_26 ]]
        p_u_20._evt:wait_on_event(v_u_4.EVT_LeaderboardEvent_ClientRequestLeaderboardData, function(p_u_27) --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_7, (ref 3): v_u_12, (ref 4): v_u_10, (ref 5): p_u_20, (ref 6): v_u_4, (ref 7): v_u_6, (ref 8): v_u_11, (ref 9): v_u_5, (ref 10): v_u_17, (ref 11): v_u_14 ]]
            local v_u_28 = {}
            for _, v29 in v_u_22:key_itr() do
                v_u_28[#v_u_28 + 1] = v29:to_table()
            end;
            local v_u_30 = v_u_7:invalid_songkey()
            local v_u_31 = 0
            local v_u_32 = 0
            local v_u_33 = 0
            for _, v34 in v_u_22:key_itr() do
                if v34:get_state() == v_u_12.State.Ended then
                    local v35 = v34:get_member_places()
                    for _, v36 in v35:key_itr() do
                        if v36:get_rbxid() == p_u_27.UserId and v36:has_claimed_reward() == false then
                            v36:claim_reward()
                            v_u_31 = v_u_31 + v_u_10:get_event_point_reward_for_place_and_player_count(v36:get_place(), v35:count())
                            v_u_32 = v36:get_place()
                            v_u_30 = v34:get_song_key()
                            v_u_33 = v35:count()
                        end;
                    end;
                end;
            end;
            local function _(p37, p38) --[[ Name: response ]] --[[ Line: 71 ]]
                --[[ Upvalues: (ref 1): p_u_20, (ref 2): v_u_4, (copy 3): p_u_27, (copy 4): v_u_28 ]]
                p_u_20._evt:fire_event_to_client(v_u_4.EVT_LeaderboardEvent_ServerRequestLeaderboardDataResponse, p_u_27, v_u_28, p37, p38)
            end;
            if v_u_31 > 0 then
                p_u_20._player_blob_manager:get_verified_cached_blob(p_u_27.UserId, function(p39) --[[ Line: 76 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_32, (ref 3): v_u_33, (ref 4): v_u_7, (ref 5): v_u_30, (ref 6): v_u_31, (ref 7): p_u_20, (copy 8): p_u_27, (ref 9): v_u_11, (ref 10): v_u_5, (ref 11): v_u_17, (ref 12): v_u_14, (ref 13): v_u_4, (copy 14): v_u_28 ]]
                    local v_u_40 = string.format("For getting %s of %d entries in the event leaderboard for \"%s\", you have earned %d event points.", v_u_6:num_placify(v_u_32), v_u_33, v_u_7:singleton():get_title_for_key(v_u_30), v_u_31)
                    local v41 = p_u_20._chat:get_chat_service()
                    v41:send_system_message_to_player_for_channel(p_u_27, v41:get_channel(v41:get_server_system_channel_id()), v_u_40, function(p42) --[[ Line: 89 ]]
                        --[[ Upvalues: (ref 1): v_u_6 ]]
                        p42:set_icon(v_u_6:get_leaderboard_icon())
                    end)
                    v_u_11:playerblob_set_event_points(p39, v_u_11:playerblob_get_event_points(p39) + v_u_31)
                    if v_u_5.UseChallengePassV2 == true then
                        p_u_20._challengepass_manager:challengepassv2_weekly_mission_playerblob_claim(v_u_17.WeeklyMissionType.CompeteInEventLeaderboard, p39)
                    end;
                    p_u_20._player_blob_manager:enqueue_blob_sync_request(p_u_27.UserId, v_u_14.PlayerBlobRequestType.Write, function(_) --[[ Line: 103 ]]
                        --[[ Upvalues: (copy 1): v_u_40, (ref 2): p_u_20, (ref 3): v_u_4, (ref 4): p_u_27, (ref 5): v_u_28 ]]
                        p_u_20._evt:fire_event_to_client(v_u_4.EVT_LeaderboardEvent_ServerRequestLeaderboardDataResponse, p_u_27, v_u_28, true, v_u_40)
                    end)
                end)
            else
                p_u_20._evt:fire_event_to_client(v_u_4.EVT_LeaderboardEvent_ServerRequestLeaderboardDataResponse, p_u_27, v_u_28, false, "")
            end;
        end)
        p_u_20._evt:wait_on_event(v_u_4.EVT_LeaderboardEvent_ClientDebugLeaderboard, function(p43) --[[ Line: 114 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_1, (ref 3): v_u_22, (ref 4): v_u_12, (ref 5): v_u_23, (ref 6): v_u_26, (ref 7): p_u_20, (ref 8): v_u_4 ]]
            if v_u_5.DebugEventLeaderboardKey ~= true then
                return v_u_1:errf("EVT_LeaderboardEvent_ClientDebugLeaderboard DebugEventLeaderboardKey not enabled");
            end;
            local v44 = v_u_22:get(v_u_22:count())
            local v45 = v44 == nil
            if v44 ~= nil then
                if v44:get_state() == v_u_12.State.Active then
                    v44:set_time_remaining(6)
                elseif v44:get_state() == v_u_12.State.Closing then
                    v44:set_closing_time_remaining(6)
                else
                    v45 = v44:get_state() == v_u_12.State.Ended and true or v45
                end;
            end;
            if v45 then
                v_u_23 = v_u_26 - 5
            end;
            p_u_20._evt:fire_event_to_client(v_u_4.EVT_LeaderboardEvent_ServerDebugLeaderboardResponse, p43)
        end)
    end;
    v21.player_disconnecting = function(_, p46) --[[ Name: player_disconnecting ]] --[[ Line: 143 ]]
        --[[ Upvalues: (copy 1): v_u_22, (ref 2): v_u_12 ]]
        for _, v47 in v_u_22:key_itr() do
            if v47:get_state() == v_u_12.State.Active or v47:get_state() == v_u_12.State.Closing then
                v47:remove_member_rbxid(p46)
            end;
        end;
    end;
    v21.rbxid_add_play_for_song_key = function(_, p48, p49, p50, p51, p52) --[[ Name: rbxid_add_play_for_song_key ]] --[[ Line: 152 ]]
        --[[ Upvalues: (copy 1): p_u_20, (copy 2): v_u_22, (ref 3): v_u_7, (ref 4): v_u_12, (ref 5): v_u_16, (ref 6): v_u_6 ]]
        local v53 = p_u_20._player_manager:id_to_player(p49)
        if v53 == nil then
            return;
        end;
        for _, v54 in v_u_22:key_itr() do
            local v55 = v_u_7:singleton():key_get_audiomod(v54:get_song_key())
            local v56 = v_u_7:singleton():key_get_audiomod(p50)
            if (v54:get_state() == v_u_12.State.Active or v54:get_state() == v_u_12.State.Closing) and (v_u_7:singleton():get_all_modes_of_songkey(v54:get_song_key()):contains(p50) and v_u_16:mod_to_compare_value(v55) >= v_u_16:mod_to_compare_value(v56)) then
                local v57, v58 = v54:add_member_play(p49, v53.Name, p51, p52, v56)
                local v59 = v57 and p_u_20._chat:gameid_get_channel(p48._game_id)
                if v59 then
                    p_u_20._chat:get_chat_service():send_system_message_to_player_for_channel(v53, v59, string.format("Your play of \"%s\" with score %s has ranked you %s in the server event leaderboard.", v_u_7:singleton():get_title_for_key(p50), v_u_6:comma_value(p51), v_u_6:num_placify(v58)), function(p60) --[[ Line: 177 ]]
                        --[[ Upvalues: (ref 1): v_u_6 ]]
                        p60:set_icon(v_u_6:important_assetid())
                    end)
                    return;
                end;
                break;
            end;
        end;
    end;
    local function f_start_new_leaderboard() --[[ Name: start_new_leaderboard ]] --[[ Line: 188 ]]
        --[[ Upvalues: (ref 1): v_u_11, (copy 2): p_u_20, (ref 3): v_u_12, (ref 4): v_u_7, (ref 5): v_u_16, (copy 6): v_u_25, (ref 7): v_u_8, (ref 8): v_u_6, (ref 9): v_u_5, (copy 10): v_u_22, (ref 11): v_u_26 ]]
        local v61, v62, _, _ = v_u_11:is_event_active(p_u_20._api:get_day_event_list())
        if v61 == true then
            local v63 = v_u_12:new()
            v63:set_song_key(v_u_11:get_playable_song_set(v62):remove_if(function(_, p64) --[[ Line: 192 ]]
                --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_16, (ref 3): v_u_25 ]]
                return v_u_7:singleton():key_get_audiomod(p64) == v_u_16.Easy and true or v_u_25:contains(p64);
            end):key_list():random())
            v_u_25:clear()
            v_u_25:add_set_from_table_list(v_u_7:singleton():get_all_modes_of_songkey(v63:get_song_key()):key_list():get_table())
            v63:set_time_remaining(v_u_8.FLASH_LEADERBOARD_DURATION)
            v63:set_closing_time_remaining(v_u_7:singleton():songkey_get_approx_length_sec(v63:get_song_key()) + v_u_8.FLASH_LEADERBOARD_CLOSING_BUFFER_TIME_SEC)
            v63:set_state(v_u_12.State.Active)
            p_u_20._chat:send_system_server_chat_message(string.format("An event leaderboard for the song \"%s\" has started!", v_u_7:singleton():get_title_for_key(v63:get_song_key())), function(p65) --[[ Line: 212 ]]
                --[[ Upvalues: (ref 1): v_u_6 ]]
                p65:set_icon(v_u_6:get_leaderboard_icon())
            end)
            p_u_20._chat:send_system_server_chat_message("Check the leaderboard tab in the event page for more details.", function(p66) --[[ Line: 218 ]]
                --[[ Upvalues: (ref 1): v_u_6 ]]
                p66:set_icon(v_u_6:get_leaderboard_icon())
            end)
            if v_u_5.DebugExtraFlashLeaderboardPlayers == true then
                for v67 = 1, v_u_6:rand_rangei(3, 30) do
                    v63:add_member_play(v67, string.format("Test%d", v67), v_u_6:rand_rangei(1, 1000000), 1)
                end;
            end;
            v_u_22:push_back(v63)
            v_u_26 = v_u_6:rand_rangei(v_u_8.EVENT_LEADERBOARD_START_MIN_TIME, v_u_8.EVENT_LEADERBOARD_START_MAX_TIME)
        end;
    end;
    local v_u_68 = v_u_13:new(30)
    v21.update = function(_, p69) --[[ Name: update ]] --[[ Line: 236 ]]
        --[[ Upvalues: (copy 1): v_u_22, (ref 2): v_u_12, (ref 3): v_u_11, (copy 4): p_u_20, (ref 5): v_u_23, (ref 6): v_u_9, (ref 7): v_u_26, (copy 8): f_start_new_leaderboard, (ref 9): v_u_8, (ref 10): v_u_7, (ref 11): v_u_6, (copy 12): v_u_68 ]]
        local v70 = true
        for _, v71 in v_u_22:key_itr() do
            if v71:get_state() == v_u_12.State.Active or v71:get_state() == v_u_12.State.Closing then
                v70 = false
                break;
            end;
        end;
        if v70 == true then
            local v72, _, _, v73 = v_u_11:is_event_active(p_u_20._api:get_day_event_list())
            if v72 ~= true then
                v70 = false
            end;
            if v70 == true and (v73 == 0 and p_u_20._api:get_time_to_next_day_sec() <= 1200) then
                v70 = false
            end;
        end;
        if v70 == true then
            v_u_23 = v_u_23 + v_u_9:TimescaleToDeltaTime(p69)
            if v_u_26 <= v_u_23 then
                f_start_new_leaderboard()
                v_u_23 = 0
            end;
        else
            v_u_23 = 0
        end;
        if v_u_22:count() > v_u_8.KEEP_LEADERBOARD_QUEUE_SIZE then
            v_u_22:pop_front()
        end;
        for _, v74 in v_u_22:key_itr() do
            local v75 = v74:get_state()
            v74:update(p69)
            if v75 ~= v74:get_state() then
                if v74:get_state() == v_u_12.State.Closing then
                    p_u_20._chat:send_system_server_chat_message(string.format("The event leaderboard for song \"%s\" is closing!", v_u_7:singleton():get_title_for_key(v74:get_song_key())), function(p76) --[[ Line: 281 ]]
                        --[[ Upvalues: (ref 1): v_u_6 ]]
                        p76:set_icon(v_u_6:get_leaderboard_icon())
                    end)
                    p_u_20._chat:send_system_server_chat_message("Please wait until the server leaderboard ends to view the final results.", function(p77) --[[ Line: 287 ]]
                        --[[ Upvalues: (ref 1): v_u_6 ]]
                        p77:set_icon(v_u_6:get_leaderboard_icon())
                    end)
                elseif v74:get_state() == v_u_12.State.Ended then
                    p_u_20._chat:send_system_server_chat_message(string.format("The event leaderboard for song \"%s\" has ended!", v_u_7:singleton():get_title_for_key(v74:get_song_key())), function(p78) --[[ Line: 297 ]]
                        --[[ Upvalues: (ref 1): v_u_6 ]]
                        p78:set_icon(v_u_6:get_leaderboard_icon())
                    end)
                    p_u_20._chat:send_system_server_chat_message("Check the leaderboard tab in the event page to claim any rewards.", function(p79) --[[ Line: 303 ]]
                        --[[ Upvalues: (ref 1): v_u_6 ]]
                        p79:set_icon(v_u_6:get_leaderboard_icon())
                    end)
                end;
            end;
        end;
        v_u_68:update(p69)
        v_u_68:do_flash()
    end;
    v21.rbxid_get_unentered_open_leaderboard_count = function(_, p80) --[[ Name: rbxid_get_unentered_open_leaderboard_count ]] --[[ Line: 324 ]]
        --[[ Upvalues: (copy 1): v_u_22, (ref 2): v_u_12 ]]
        local v81 = 0
        for _, v82 in v_u_22:key_itr() do
            if v82:get_state() == v_u_12.State.Active then
                local v83 = false
                for _, v84 in v82:get_member_places():key_itr() do
                    if v84:get_rbxid() == p80 then
                        v83 = true
                        break;
                    end;
                end;
                if v83 == false then
                    v81 = v81 + 1
                end;
            end;
        end;
        return v81;
    end;
    v21.rbxid_get_claimable_leaderboard_count = function(_, p85) --[[ Name: rbxid_get_claimable_leaderboard_count ]] --[[ Line: 344 ]]
        --[[ Upvalues: (copy 1): v_u_22, (ref 2): v_u_12 ]]
        local v86 = 0
        for _, v87 in v_u_22:key_itr() do
            if v87:get_state() == v_u_12.State.Ended then
                for _, v88 in v87:get_member_places():key_itr() do
                    if v88:get_rbxid() == p85 and v88:has_claimed_reward() ~= true then
                        v86 = v86 + 1
                    end;
                end;
            end;
        end;
        return v86;
    end;
    v21.get_active_event_songkey = function(_) --[[ Name: get_active_event_songkey ]] --[[ Line: 359 ]]
        --[[ Upvalues: (copy 1): v_u_22, (ref 2): v_u_12, (ref 3): v_u_7 ]]
        for _, v89 in v_u_22:key_itr() do
            if v89:get_state() == v_u_12.State.Active then
                return v89:get_song_key();
            end;
        end;
        return v_u_7:invalid_songkey();
    end;
    return v21;
end;
v18.rbxid_get_notification_list = function(_, p90) --[[ Name: rbxid_get_notification_list ]] --[[ Line: 371 ]]
    --[[ Upvalues: (copy 1): v_u_2, (ref 2): v_u_19, (copy 3): v_u_15 ]]
    local v91 = v_u_2:new()
    if v_u_19 == nil then
        return v91;
    end;
    local v92 = 0 + v_u_19:rbxid_get_unentered_open_leaderboard_count(p90) + v_u_19:rbxid_get_claimable_leaderboard_count(p90)
    if v92 > 0 then
        v91:push_back(v_u_15:new(v_u_15.Type.ArtistEventButton, v92))
    end;
    return v91;
end;
return v18;
