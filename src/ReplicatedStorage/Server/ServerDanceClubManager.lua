-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:16 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.ProdEnvSelector)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_9 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_11 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_12 = require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.PlayerInfo.ChallengePassUtils)
local v_u_13 = require(game.ReplicatedStorage.Shared.DanceClubQueuedSongVote)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_15 = require(game.ReplicatedStorage.AudioData.AudioMod)
require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
local v17 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_18 = nil
v17:require_server(function() --[[ Line: 25 ]]
    --[[ Upvalues: (ref 1): v_u_18 ]]
    v_u_18 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
local v19 = {}
local v_u_30 = {
    ["new"] = function(_, p_u_20, p_u_21) --[[ Name: new ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_9, (copy 3): v_u_13 ]]
        local v22 = {}
        local v_u_23 = v_u_3:new()
        v22.get_player_id = function(_) --[[ Name: get_player_id ]] --[[ Line: 37 ]]
            --[[ Upvalues: (copy 1): p_u_20 ]]
            return p_u_20;
        end;
        v22.get_song_id = function(_) --[[ Name: get_song_id ]] --[[ Line: 38 ]]
            --[[ Upvalues: (copy 1): p_u_21 ]]
            return p_u_21;
        end;
        v22.can_playerid_vote = function(_, p24) --[[ Name: can_playerid_vote ]] --[[ Line: 40 ]]
            --[[ Upvalues: (copy 1): p_u_20, (copy 2): v_u_23 ]]
            if p24 == p_u_20 then
                return false;
            else
                return v_u_23:contains(p24) ~= true;
            end;
        end;
        v22.playerid_vote = function(_, p25, p26) --[[ Name: playerid_vote ]] --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_13, (copy 3): v_u_23 ]]
            v_u_9:is_enum_member(p26, v_u_13)
            v_u_23:add(p25, p26)
        end;
        v22.get_vote_count = function(_) --[[ Name: get_vote_count ]] --[[ Line: 48 ]]
            --[[ Upvalues: (copy 1): v_u_23, (ref 2): v_u_13 ]]
            local v27 = 0
            local v28 = 0
            for _, v29 in v_u_23:key_itr() do
                if v29 == v_u_13.UpVote then
                    v27 = v27 + 1
                elseif v29 == v_u_13.DownVote then
                    v28 = v28 + 1
                end;
            end;
            return v27, v28;
        end;
        return v22;
    end
}
v19.new = function(_, p_u_31) --[[ Name: new ]] --[[ Line: 66 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_7, (copy 3): v_u_3, (copy 4): v_u_4, (copy 5): v_u_9, (copy 6): v_u_10, (copy 7): v_u_30, (copy 8): v_u_12, (copy 9): v_u_5, (copy 10): v_u_16, (ref 11): v_u_18, (copy 12): v_u_1, (copy 13): v_u_8, (copy 14): v_u_13, (copy 15): v_u_6, (copy 16): v_u_14, (copy 17): v_u_15, (copy 18): v_u_11 ]]
    local v32 = {}
    local v_u_33 = v_u_2:new()
    local v_u_34 = nil
    local v_u_35 = 0
    v32.get_active_queued_song = function(_) --[[ Name: get_active_queued_song ]] --[[ Line: 73 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_34 ]]
        local v36 = v_u_7:invalid_songkey()
        if v_u_34 ~= nil then
            v36 = v_u_34:get_song_id()
        end;
        return v36;
    end;
    local v_u_37 = v_u_3:new()
    local function f_get_queue_reward_cooldown_for_playerid(p38) --[[ Name: get_queue_reward_cooldown_for_playerid ]] --[[ Line: 82 ]]
        --[[ Upvalues: (copy 1): v_u_37 ]]
        return not v_u_37:contains(p38) and 0 or v_u_37:get(p38);
    end;
    v32.start = function(p_u_39) --[[ Name: start ]] --[[ Line: 90 ]]
        --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_4, (ref 3): v_u_9, (ref 4): v_u_7, (ref 5): v_u_10, (copy 6): v_u_33, (ref 7): v_u_30, (ref 8): v_u_12, (ref 9): v_u_5, (ref 10): v_u_16, (ref 11): v_u_18, (copy 12): v_u_37, (ref 13): v_u_1, (copy 14): f_get_queue_reward_cooldown_for_playerid, (ref 15): v_u_8, (ref 16): v_u_13, (ref 17): v_u_34, (ref 18): v_u_6 ]]
        p_u_31._evt:wait_on_event(v_u_4.EVT_DanceClub_ClientQueueSong, function(p_u_40, p_u_41) --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_7, (ref 3): p_u_31, (ref 4): v_u_10, (ref 5): v_u_4, (copy 6): p_u_39, (ref 7): v_u_33, (ref 8): v_u_30, (ref 9): v_u_12, (ref 10): v_u_5, (ref 11): v_u_16, (ref 12): v_u_18, (ref 13): v_u_37, (ref 14): v_u_1, (ref 15): f_get_queue_reward_cooldown_for_playerid, (ref 16): v_u_8 ]]
            v_u_9:is_true(v_u_7:singleton():contains_key(p_u_41))
            local l_UserId_0 = p_u_40.UserId
            local v_u_42 = p_u_31._player_blob_manager:get_cached_blob(l_UserId_0)
            if (v_u_10:playerblob_has_access_to_song(v_u_42, p_u_41, p_u_31._api:get_day_id(), p_u_31._collection_manager:get_collection_info_for_player_id_playerblob(l_UserId_0, v_u_42)) and true or false) ~= true then
                return p_u_31._evt:fire_event_to_client(v_u_4.EVT_DanceClub_ServerQueueSongResponse, p_u_40, false, "Song not owned", p_u_39:get_info_table_for_playerid(l_UserId_0), 0);
            end;
            local _, v43 = p_u_39:get_queued_song_for_player_id(l_UserId_0)
            if v43 ~= -1 then
                v_u_33:remove_at(v43)
            end;
            v_u_33:push_back(v_u_30:new(l_UserId_0, p_u_41))
            p_u_31._player_blob_manager:get_verified_cached_blob(l_UserId_0, function(p44) --[[ Line: 118 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_31, (ref 3): v_u_4, (copy 4): p_u_40, (ref 5): p_u_39, (copy 6): l_UserId_0, (ref 7): v_u_5, (ref 8): v_u_16, (copy 9): v_u_42, (ref 10): v_u_18, (copy 11): p_u_41, (ref 12): v_u_37, (ref 13): v_u_1, (ref 14): f_get_queue_reward_cooldown_for_playerid, (ref 15): v_u_8 ]]
                local l_DANCECLUB_QUEUE_REWARD_COIN_AMOUNT_0 = v_u_12.DANCECLUB_QUEUE_REWARD_COIN_AMOUNT
                local function f_on_finish() --[[ Name: on_finish ]] --[[ Line: 120 ]]
                    --[[ Upvalues: (ref 1): p_u_31, (ref 2): v_u_4, (ref 3): p_u_40, (ref 4): p_u_39, (ref 5): l_UserId_0, (ref 6): l_DANCECLUB_QUEUE_REWARD_COIN_AMOUNT_0 ]]
                    p_u_31._evt:fire_event_to_client(v_u_4.EVT_DanceClub_ServerQueueSongResponse, p_u_40, true, "", p_u_39:get_info_table_for_playerid(l_UserId_0), l_DANCECLUB_QUEUE_REWARD_COIN_AMOUNT_0)
                    p_u_39:push_song_info_to_all_players(function(p45) --[[ Line: 129 ]]
                        --[[ Upvalues: (ref 1): l_UserId_0 ]]
                        return p45 ~= l_UserId_0;
                    end)
                end;
                local v46
                if v_u_5.UseChallengePassV2 == true then
                    v46 = p_u_31._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_16.DailyMissionType.QueueDJ, v_u_42)
                else
                    v46 = false
                end;
                p_u_31._special_event_manager:write_special_event_data_for_player_action(l_UserId_0, v_u_18.PlayerActionEvent.QueueSongRadio, {
                    ["SongKey"] = p_u_41
                })
                if l_DANCECLUB_QUEUE_REWARD_COIN_AMOUNT_0 <= 0 and v46 == false then
                    f_on_finish()
                else
                    local v47 = l_UserId_0
                    if (not v_u_37:contains(v47) and 0 or v_u_37:get(v47)) > 0 then
                        l_DANCECLUB_QUEUE_REWARD_COIN_AMOUNT_0 = 0
                        v_u_1:warnf("SPRemoteEvent.EVT_DanceClub_ClientQueueSong queue_reward_cooldown trigger player(%d) cooldown(%d)", l_UserId_0, f_get_queue_reward_cooldown_for_playerid(l_UserId_0))
                    else
                        v_u_37:add(l_UserId_0, v_u_12.DANCECLUB_QUEUE_REWARD_COOLDOWN_MS)
                    end;
                    p44.CoinCurrency = p44.CoinCurrency + l_DANCECLUB_QUEUE_REWARD_COIN_AMOUNT_0
                    p_u_31._player_blob_manager:enqueue_blob_sync_request(l_UserId_0, v_u_8.PlayerBlobRequestType.Write, function() --[[ Line: 153 ]]
                        --[[ Upvalues: (copy 1): f_on_finish ]]
                        f_on_finish()
                    end)
                end;
            end)
        end)
        p_u_31._evt:wait_on_event(v_u_4.EVT_DanceClub_ClientRequestCurrentSongInfo, function(p48) --[[ Line: 161 ]]
            --[[ Upvalues: (copy 1): p_u_39 ]]
            p_u_39:push_song_info_to_playerid(p48.UserId)
        end)
        p_u_31._evt:wait_on_event(v_u_4.EVT_DanceClub_ClientVote, function(p_u_49, p_u_50) --[[ Line: 165 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_13, (ref 3): v_u_34, (ref 4): p_u_31, (ref 5): v_u_12, (copy 6): p_u_39, (ref 7): v_u_4, (ref 8): v_u_6, (ref 9): v_u_5, (ref 10): v_u_16, (ref 11): v_u_18, (ref 12): v_u_8 ]]
            v_u_9:is_enum_member(p_u_50, v_u_13)
            local l_UserId_1 = p_u_49.UserId
            local v_u_51 = false
            local v_u_52 = ""
            local v_u_53 = 0
            local v_u_54
            if v_u_34 == nil then
                v_u_54 = nil
                v_u_52 = "No active queued song"
            else
                if v_u_34:can_playerid_vote(l_UserId_1) then
                    v_u_34:playerid_vote(l_UserId_1, p_u_50)
                    local v55
                    v_u_53, v55 = v_u_34:get_vote_count()
                    v_u_51 = true
                else
                    v_u_52 = "Player has already voted"
                end;
                v_u_54 = p_u_31._player_manager:id_to_player(v_u_34:get_player_id())
            end;
            local v_u_56 = (v_u_51 ~= true or p_u_50 ~= v_u_13.UpVote) and 0 or v_u_12.DANCECLUB_VOTE_REWARD_COIN_AMOUNT
            local function f_on_finish() --[[ Name: on_finish ]] --[[ Line: 191 ]]
                --[[ Upvalues: (ref 1): v_u_51, (ref 2): p_u_39, (copy 3): l_UserId_1, (ref 4): p_u_31, (ref 5): v_u_4, (copy 6): p_u_49, (ref 7): v_u_52, (ref 8): v_u_56, (ref 9): v_u_54, (copy 10): p_u_50, (ref 11): v_u_13, (ref 12): v_u_53, (ref 13): v_u_6 ]]
                if v_u_51 then
                    p_u_39:push_song_info_to_all_players(function(p57) --[[ Line: 193 ]]
                        --[[ Upvalues: (ref 1): l_UserId_1 ]]
                        return p57 ~= l_UserId_1;
                    end)
                end;
                p_u_31._evt:fire_event_to_client(v_u_4.EVT_DanceClub_ServerVoteResponse, p_u_49, v_u_51, v_u_52, p_u_39:get_info_table_for_playerid(l_UserId_1), v_u_56)
                if v_u_51 == true and (v_u_54 and p_u_50 == v_u_13.UpVote) then
                    p_u_31._chat:get_chat_service():send_system_message_to_player_for_channel(v_u_54, p_u_31._chat:get_chat_service():get_channel(p_u_31._chat:get_chat_service():get_server_system_channel_id()), string.format("%s voted for the song you queued on the DJ! Total votes: %d", p_u_49.Name, v_u_53), function(p58) --[[ Line: 212 ]]
                        --[[ Upvalues: (ref 1): v_u_6 ]]
                        p58:set_icon(v_u_6:get_song_icon())
                    end)
                end;
            end;
            if v_u_56 <= 0 then
                f_on_finish()
            else
                p_u_31._player_blob_manager:get_verified_cached_blob(l_UserId_1, function(p59) --[[ Line: 222 ]]
                    --[[ Upvalues: (ref 1): v_u_56, (ref 2): v_u_5, (ref 3): p_u_31, (ref 4): v_u_16, (ref 5): v_u_34, (copy 6): l_UserId_1, (ref 7): v_u_18, (ref 8): v_u_8, (copy 9): f_on_finish ]]
                    p59.CoinCurrency = p59.CoinCurrency + v_u_56
                    if v_u_5.UseChallengePassV2 == true then
                        p_u_31._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_16.DailyMissionType.VoteDJ, p59)
                    end;
                    if v_u_34 ~= nil then
                        p_u_31._special_event_manager:write_special_event_data_for_player_action(l_UserId_1, v_u_18.PlayerActionEvent.VoteSongRadio, {
                            ["SongKey"] = v_u_34:get_song_id()
                        })
                    end;
                    p_u_31._player_blob_manager:enqueue_blob_sync_request(l_UserId_1, v_u_8.PlayerBlobRequestType.Write, function() --[[ Line: 233 ]]
                        --[[ Upvalues: (ref 1): f_on_finish ]]
                        f_on_finish()
                    end)
                end)
            end;
        end)
    end;
    local function _(p60) --[[ Name: get_length_for_song_key ]] --[[ Line: 243 ]]
        --[[ Upvalues: (ref 1): v_u_7 ]]
        return v_u_7:singleton():songkey_get_approx_length_sec(p60);
    end;
    local v_u_61 = true
    v32.update = function(p_u_62, p63) --[[ Name: update ]] --[[ Line: 253 ]]
        --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_34, (copy 3): v_u_33, (ref 4): v_u_2, (ref 5): v_u_61, (ref 6): v_u_14, (copy 7): p_u_31, (ref 8): v_u_7, (ref 9): v_u_15, (ref 10): v_u_30, (ref 11): v_u_1, (ref 12): v_u_35, (ref 13): v_u_11, (ref 14): v_u_12, (copy 15): v_u_37 ]]
        local v70, v71 = v_u_6:try(function() --[[ Line: 254 ]]
            --[[ Upvalues: (ref 1): v_u_34, (copy 2): p_u_62, (ref 3): v_u_33, (ref 4): v_u_2, (ref 5): v_u_61, (ref 6): v_u_14, (ref 7): p_u_31, (ref 8): v_u_7, (ref 9): v_u_15, (ref 10): v_u_30 ]]
            if v_u_34 == nil and (p_u_62:get_queued_song_for_player_id(-99) == nil and v_u_33:count() == 0) then
                local v64 = v_u_2:new()
                if not v_u_61 then
                    local v65, v66 = v_u_14:is_event_active(p_u_31._api:get_day_event_list())
                    if v65 then
                        v64:push_back_from_list(v_u_14:get_playable_song_set(v66):key_list())
                    end;
                end;
                if v_u_61 then
                    local v67 = p_u_31._shop_manager:get_cached_shop_info()
                    if typeof(v67) == "table" and #v67.AvailableItems > 0 then
                        for _, v68 in pairs(v67.AvailableItems) do
                            v64:push_back_from_list(v_u_7:singleton():get_all_modes_of_songkey(v68.SongKey):key_list())
                        end;
                    end;
                end;
                v64:remove_if(function(p69) --[[ Line: 274 ]]
                    --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_15 ]]
                    return (v_u_7:singleton():contains_key(p69) ~= true or (v_u_7:singleton():key_is_remix_flagged(p69) == true or (v_u_7:singleton():get_songkey_priority(p69) ~= v_u_7.SongPriority.Normal or (v_u_7:singleton():key_get_audiomod(p69) == v_u_15.Easy or v_u_7:singleton():key_get_audiomod(p69) == v_u_15.Normal)))) and true or v_u_7:singleton():key_is_vip(p69) == true;
                end)
                if v64:count() > 0 then
                    v_u_33:push_back(v_u_30:new(-99, v64:random()))
                    p_u_62:push_song_info_to_all_players()
                end;
                v_u_61 = not v_u_61
            end;
        end)
        if v70 ~= true then
            v_u_1:warnf(v71)
        end;
        if v_u_34 == nil and v_u_33:count() > 0 then
            v_u_34 = v_u_33:pop_front()
            v_u_35 = 0
            p_u_62:push_song_info_to_all_players()
        end;
        if v_u_34 ~= nil then
            v_u_35 = v_u_35 + v_u_11:TimescaleToDeltaTime(p63)
            local v72 = v_u_7:singleton():songkey_get_approx_length_sec((v_u_34:get_song_id()))
            if p_u_62:get_votes_to_skip() <= 0 and v_u_35 > v_u_12.DANCECLUB_SKIP_MIN_TIME_SEC then
                v_u_35 = v72 + 1
            end;
            if v72 < v_u_35 then
                v_u_34 = nil
                if v_u_33:count() == 0 then
                    p_u_62:push_song_info_to_all_players()
                end;
            end;
        end;
        for v73, v74 in v_u_37:key_itr() do
            if typeof(v74) == "number" then
                v_u_37:add(v73, (v_u_11:IncrementClamp(v74, -v_u_11:TimescaleToDeltaTime(p63) * 1000, 0, v_u_12.DANCECLUB_QUEUE_REWARD_COOLDOWN_MS)))
            end;
        end;
    end;
    v32.push_song_info_to_all_players = function(p75, p76) --[[ Name: push_song_info_to_all_players ]] --[[ Line: 328 ]]
        --[[ Upvalues: (copy 1): p_u_31 ]]
        for v77, _ in p_u_31._player_manager:players_key_itr() do
            if p76 == nil or p76 ~= nil and p76(v77) == true then
                p75:push_song_info_to_playerid(v77)
            end;
        end;
    end;
    v32.get_info_table_for_playerid = function(p78, p79) --[[ Name: get_info_table_for_playerid ]] --[[ Line: 337 ]]
        --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_7, (copy 3): p_u_31, (copy 4): v_u_33, (ref 5): v_u_5, (ref 6): v_u_35 ]]
        local v80 = "???"
        local v81, v82
        if v_u_34 == nil then
            v81 = -1
            v82 = 0
        else
            v81 = v_u_34:get_song_id()
            v82 = v_u_7:singleton():songkey_get_approx_length_sec((v_u_34:get_song_id()))
            if v_u_34:get_player_id() == -99 then
                v80 = "DJ Hiku"
            else
                local v83 = p_u_31._player_manager:id_to_player(v_u_34:get_player_id())
                if v83 then
                    v80 = v83.Name
                end;
            end;
        end;
        local v84 = "???"
        local v85
        if v_u_33:count() > 0 then
            local v86 = v_u_33:get(1)
            v85 = v86:get_song_id()
            if v86:get_player_id() == -99 then
                v84 = "DJ Hiku"
            else
                local v87 = p_u_31._player_manager:id_to_player(v86:get_player_id())
                if v87 then
                    v84 = v87.Name
                end;
            end;
        else
            v85 = -1
        end;
        local v88, v89 = p78:get_queued_song_for_player_id(p79)
        local v90 = not v88 and -1 or v88:get_song_id()
        local v91 = false
        local v92, v93
        if v_u_34 == nil then
            v92 = 0
            v93 = 0
        else
            v92, v93 = v_u_34:get_vote_count()
            if v_u_5.DJClubCanVoteOwnSong == true then
                v91 = v_u_34:can_playerid_vote(p79)
            elseif v_u_34:get_player_id() ~= p79 then
                v91 = v_u_34:can_playerid_vote(p79)
            end;
        end;
        return {
            ["CurrentSongKey"] = v81,
            ["CurrentSongTimeSec"] = v_u_35,
            ["CurrentSongLength"] = v82,
            ["CurrentSongQueuedBy"] = v80,
            ["CurrentSongUpVotes"] = v92,
            ["CurrentSongDownVotes"] = v93,
            ["CurrentSongVotesToSkip"] = p78:get_votes_to_skip(),
            ["CurrentSongCanVote"] = v91,
            ["NextSongKey"] = v85,
            ["NextSongQueuedBy"] = v84,
            ["QueuedSongsCount"] = v_u_33:count(),
            ["QueuedSongKey"] = v90,
            ["QueuedSongIndex"] = v89
        };
    end;
    v32.get_votes_to_skip = function(_) --[[ Name: get_votes_to_skip ]] --[[ Line: 406 ]]
        --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_5, (copy 3): p_u_31 ]]
        if v_u_34 == nil then
            return -1;
        end;
        if v_u_5.DJClubSingleVoteSkip == true then
            local _, v94 = v_u_34:get_vote_count()
            return v94 > 0 and 0 or 1;
        end;
        local v95, v96 = v_u_34:get_vote_count()
        local v97 = math.ceil(p_u_31._id_to_player:count() / 12)
        return math.max((v97 < 3 and 3 or v97) - v96 + v95, 0);
    end;
    v32.push_song_info_to_playerid = function(p98, p99) --[[ Name: push_song_info_to_playerid ]] --[[ Line: 428 ]]
        --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_4 ]]
        local v100 = p_u_31._player_manager:id_to_player(p99)
        if v100 ~= nil then
            p_u_31._evt:fire_event_to_client(v_u_4.EVT_DanceClub_ServerPushCurrentSongInfo, v100, p98:get_info_table_for_playerid(p99))
        end;
    end;
    v32.get_queued_song_for_player_id = function(_, p101) --[[ Name: get_queued_song_for_player_id ]] --[[ Line: 434 ]]
        --[[ Upvalues: (copy 1): v_u_33 ]]
        local v102 = nil
        local v103 = -1
        for v104 = 1, v_u_33:count() do
            local v105 = v_u_33:get(v104)
            if v105:get_player_id() == p101 then
                return v105, v104;
            end;
        end;
        return v102, v103;
    end;
    v32.player_disconnecting = function(p106, p107) --[[ Name: player_disconnecting ]] --[[ Line: 448 ]]
        --[[ Upvalues: (copy 1): v_u_37, (copy 2): v_u_33 ]]
        v_u_37:remove(p107)
        local _, v108 = p106:get_queued_song_for_player_id(p107)
        if v108 ~= -1 then
            v_u_33:remove_at(v108)
            p106:push_song_info_to_all_players()
        end;
    end;
    v32.is_songkey_danceclub_active_song = function(_, p109) --[[ Name: is_songkey_danceclub_active_song ]] --[[ Line: 457 ]]
        --[[ Upvalues: (copy 1): p_u_31, (ref 2): v_u_7, (ref 3): v_u_15 ]]
        local v110 = p_u_31._danceclub_manager:get_active_queued_song()
        return v_u_7:singleton():contains_key(v110) and v_u_7:singleton():get_all_modes_of_songkey(v110):contains(p109) and v_u_15:mod_to_compare_value((v_u_7:singleton():key_get_audiomod(v110))) >= v_u_15:mod_to_compare_value((v_u_7:singleton():key_get_audiomod(p109))) and true or false;
    end;
    v32.player_started_danceclub_active_song = function(p111, p112, p113) --[[ Name: player_started_danceclub_active_song ]] --[[ Line: 472 ]]
        --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_13, (copy 3): p_u_31, (ref 4): v_u_6 ]]
        if p111:is_songkey_danceclub_active_song(p113) then
            local l_UserId_2 = p112.UserId
            local v114, v115, v116
            if v_u_34 == nil or not v_u_34:can_playerid_vote(l_UserId_2) then
                v114 = false
                v115 = nil
                v116 = 0
            else
                v_u_34:playerid_vote(l_UserId_2, v_u_13.UpVote)
                local v117
                v116, v117 = v_u_34:get_vote_count()
                v115 = p_u_31._player_manager:id_to_player(v_u_34:get_player_id())
                v114 = true
            end;
            if v114 then
                p111:push_song_info_to_all_players()
                if v115 ~= nil then
                    p_u_31._chat:get_chat_service():send_system_message_to_player_for_channel(v115, p_u_31._chat:get_chat_service():get_channel(p_u_31._chat:get_chat_service():get_server_system_channel_id()), string.format("%s is playing the song you queued on the DJ! Total votes: %d", p112.Name, v116), function(p118) --[[ Line: 494 ]]
                        --[[ Upvalues: (ref 1): v_u_6 ]]
                        p118:set_icon(v_u_6:get_song_icon())
                    end)
                end;
            end;
        end;
    end;
    return v32;
end;
return v19;
