-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:01 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_5 = require(game.ReplicatedStorage.Shared.DanceClubQueuedSongVote)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
return {
    ["new"] = function(_, p_u_7) --[[ Name: new ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_6, (copy 3): v_u_1, (copy 4): v_u_4, (copy 5): v_u_3, (copy 6): v_u_5 ]]
        local v_u_8 = {}
        local v_u_9 = -1
        local v_u_10 = 0
        local v_u_11 = 0
        local v_u_12 = ""
        local v_u_13 = 0
        local v_u_14 = 0
        local v_u_15 = 0
        local v_u_16 = false
        v_u_8.get_current_song_info = function(_) --[[ Name: get_current_song_info ]] --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10, (ref 3): v_u_11, (ref 4): v_u_12, (ref 5): v_u_13, (ref 6): v_u_14, (ref 7): v_u_15, (ref 8): v_u_16 ]]
            return v_u_9, v_u_10, v_u_11, v_u_12, v_u_13, v_u_14, v_u_15, v_u_16;
        end;
        local v_u_17 = -1
        local v_u_18 = ""
        local v_u_19 = 0
        v_u_8.get_next_song_info = function(_) --[[ Name: get_next_song_info ]] --[[ Line: 28 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_18, (ref 3): v_u_19 ]]
            return v_u_17, v_u_18, v_u_19;
        end;
        local v_u_20 = -1
        local v_u_21 = -1
        v_u_8.get_queued_song_info = function(_) --[[ Name: get_queued_song_info ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_21 ]]
            return v_u_20, v_u_21;
        end;
        local v_u_22 = tick()
        v_u_8.get_synced_time = function(_) --[[ Name: get_synced_time ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22;
        end;
        local function _() --[[ Name: cons ]] --[[ Line: 37 ]]
            --[[ Upvalues: (copy 1): p_u_7, (ref 2): v_u_2, (copy 3): v_u_8 ]]
            p_u_7._evt:wait_on_event(v_u_2.EVT_DanceClub_ServerPushCurrentSongInfo, function(p23) --[[ Line: 38 ]]
                --[[ Upvalues: (ref 1): v_u_8 ]]
                v_u_8:handle_info_table(p23)
            end)
            v_u_8:request_current_song_info()
        end;
        v_u_8.request_current_song_info = function(_) --[[ Name: request_current_song_info ]] --[[ Line: 44 ]]
            --[[ Upvalues: (copy 1): p_u_7, (ref 2): v_u_2 ]]
            p_u_7._evt:fire_event_to_server(v_u_2.EVT_DanceClub_ClientRequestCurrentSongInfo)
        end;
        v_u_8.handle_info_table = function(_, p_u_24) --[[ Name: handle_info_table ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_9, (ref 3): v_u_10, (ref 4): v_u_11, (ref 5): v_u_12, (ref 6): v_u_13, (ref 7): v_u_14, (ref 8): v_u_15, (ref 9): v_u_16, (ref 10): v_u_17, (ref 11): v_u_18, (ref 12): v_u_19, (ref 13): v_u_20, (ref 14): v_u_21, (ref 15): v_u_22, (ref 16): v_u_1 ]]
            local v25, v26 = pcall(function() --[[ Line: 49 ]]
                --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_24 ]]
                v_u_6:is_table(p_u_24)
                v_u_6:is_int(p_u_24.CurrentSongKey)
                v_u_6:is_number(p_u_24.CurrentSongTimeSec)
                v_u_6:is_number(p_u_24.CurrentSongLength)
                v_u_6:is_string(p_u_24.CurrentSongQueuedBy)
                v_u_6:is_number(p_u_24.CurrentSongUpVotes)
                v_u_6:is_number(p_u_24.CurrentSongDownVotes)
                v_u_6:is_number(p_u_24.CurrentSongVotesToSkip)
                v_u_6:is_bool(p_u_24.CurrentSongCanVote)
                v_u_6:is_int(p_u_24.NextSongKey)
                v_u_6:is_string(p_u_24.NextSongQueuedBy)
                v_u_6:is_int(p_u_24.QueuedSongsCount)
                v_u_6:is_int(p_u_24.QueuedSongKey)
            end)
            if v25 then
                v_u_9 = p_u_24.CurrentSongKey
                v_u_10 = p_u_24.CurrentSongTimeSec
                v_u_11 = p_u_24.CurrentSongLength
                v_u_12 = p_u_24.CurrentSongQueuedBy
                v_u_13 = p_u_24.CurrentSongUpVotes
                v_u_14 = p_u_24.CurrentSongDownVotes
                v_u_15 = p_u_24.CurrentSongVotesToSkip
                v_u_16 = p_u_24.CurrentSongCanVote
                v_u_17 = p_u_24.NextSongKey
                v_u_18 = p_u_24.NextSongQueuedBy
                v_u_19 = p_u_24.QueuedSongsCount
                v_u_20 = p_u_24.QueuedSongKey
                v_u_21 = p_u_24.QueuedSongIndex
                v_u_22 = tick()
            else
                v_u_1:warnf("LocalDanceClubManager:handle_info_table error(%s)", (tostring(v26)))
            end;
        end;
        v_u_8.update = function(_, p27) --[[ Name: update ]] --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_9, (ref 3): v_u_10, (ref 4): v_u_3 ]]
            if v_u_4:singleton():contains_key(v_u_9) then
                v_u_10 = v_u_10 + v_u_3:TimescaleToDeltaTime(p27)
            end;
        end;
        v_u_8.queue_song = function(p_u_28, p29, p_u_30) --[[ Name: queue_song ]] --[[ Line: 94 ]]
            --[[ Upvalues: (copy 1): p_u_7, (ref 2): v_u_2 ]]
            p_u_7._evt:wait_on_event_once(v_u_2.EVT_DanceClub_ServerQueueSongResponse, function(p_u_31, _, p32, p_u_33) --[[ Line: 95 ]]
                --[[ Upvalues: (copy 1): p_u_28, (ref 2): p_u_7, (copy 3): p_u_30 ]]
                if p_u_31 == true then
                    p_u_28:handle_info_table(p32)
                    p_u_7._player_blob_manager:do_sync(function() --[[ Line: 98 ]]
                        --[[ Upvalues: (ref 1): p_u_30, (copy 2): p_u_31, (copy 3): p_u_33 ]]
                        p_u_30(p_u_31, p_u_33)
                    end)
                end;
            end)
            p_u_7._evt:fire_event_to_server(v_u_2.EVT_DanceClub_ClientQueueSong, p29)
        end;
        v_u_8.vote_current_song = function(p_u_34, p35, p_u_36) --[[ Name: vote_current_song ]] --[[ Line: 106 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_5, (copy 3): p_u_7, (ref 4): v_u_2, (ref 5): v_u_1 ]]
            v_u_6:is_enum_member(p35, v_u_5)
            p_u_7._evt:wait_on_event_once(v_u_2.EVT_DanceClub_ServerVoteResponse, function(p_u_37, p_u_38, p39, p_u_40) --[[ Line: 108 ]]
                --[[ Upvalues: (copy 1): p_u_34, (ref 2): p_u_7, (copy 3): p_u_36, (ref 4): v_u_1 ]]
                if p_u_37 == true then
                    p_u_34:handle_info_table(p39)
                    p_u_7._player_blob_manager:do_sync(function() --[[ Line: 111 ]]
                        --[[ Upvalues: (ref 1): p_u_36, (copy 2): p_u_37, (copy 3): p_u_38, (copy 4): p_u_40 ]]
                        p_u_36(p_u_37, p_u_38, p_u_40)
                    end)
                else
                    v_u_1:warnf("LocalDanceClubManager:vote_current_song response fail(%s)", (tostring(p_u_38)))
                    p_u_36(false, tostring(p_u_38), 0)
                end;
            end)
            p_u_7._evt:fire_event_to_server(v_u_2.EVT_DanceClub_ClientVote, p35)
        end;
        p_u_7._evt:wait_on_event(v_u_2.EVT_DanceClub_ServerPushCurrentSongInfo, function(p41) --[[ Line: 38 ]]
            --[[ Upvalues: (copy 1): v_u_8 ]]
            v_u_8:handle_info_table(p41)
        end)
        v_u_8:request_current_song_info()
        return v_u_8;
    end
};
