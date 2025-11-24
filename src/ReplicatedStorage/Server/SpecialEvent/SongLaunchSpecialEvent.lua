-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:18 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.PlayerInfo.SongLaunchEventInfo)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v6 = {}
local v7 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_8 = nil
v7:require_server(function() --[[ Line: 14 ]]
    --[[ Upvalues: (ref 1): v_u_8 ]]
    v_u_8 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
v6.new = function(_, p_u_9) --[[ Name: new ]] --[[ Line: 18 ]]
    --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_5, (copy 3): v_u_3, (copy 4): v_u_4, (copy 5): v_u_1, (copy 6): v_u_2 ]]
    local v10 = v_u_8.EventBase:new()
    p_u_9._evt:wait_on_event(v_u_5.EVT_SongLaunchEvent_ClaimReward_Client, function(p_u_11) --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_5, (ref 3): v_u_3, (ref 4): v_u_4 ]]
        local function f_D(p12, p13) --[[ Name: D ]] --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_5, (copy 3): p_u_11 ]]
            p_u_9._evt:fire_event_to_client(v_u_5.EVT_SongLaunchEvent_ClaimReward_Server, p_u_11, p12, p13)
        end;
        p_u_9._player_blob_manager:get_verified_cached_blob(p_u_11.UserId, function(p14) --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_9, (copy 3): f_D, (ref 4): v_u_4, (copy 5): p_u_11, (ref 6): v_u_5 ]]
            local v15, v16 = v_u_3:is_song_launch_event_active(p_u_9._api:get_day_event_list())
            if v15 ~= true then
                return f_D(false, "SongLaunchEvent is not active");
            end;
            if v_u_3:playerblob_eventid_reward_available(p14, v16) ~= true then
                return f_D(false, "SongLaunchEvent rewards already claimed");
            end;
            if v_u_3:playerblob_get_remaining_songs_count_for_event_id(p14, v16) > 0 then
                return f_D(false, "SongLaunchEvent has remaining songs to claim");
            end;
            p14.SongLaunchClaimedID = v16
            if v_u_3:get_event_reward_currency_type_for_event_id(v16) == v_u_4.CurrencyType.Stars then
                v_u_4:set_star_currency(p14, v_u_4:get_star_currency(p14) + v_u_3:get_event_reward_currency_amount_for_event_id(v16))
            end;
            p_u_9._player_blob_manager:enqueue_blob_sync_request(p_u_11.UserId, v_u_4.PlayerBlobRequestType.Write, function(_) --[[ Line: 39 ]]
                --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_5, (ref 3): p_u_11 ]]
                p_u_9._evt:fire_event_to_client(v_u_5.EVT_SongLaunchEvent_ClaimReward_Server, p_u_11, true, "")
            end)
        end)
    end)
    v10.write_special_event_data_for_play = function(_, _, p_u_17, _, _, p18, p19, p20) --[[ Name: write_special_event_data_for_play ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_2, (copy 3): p_u_9, (ref 4): v_u_3, (ref 5): v_u_4 ]]
        if p18._event_info == v_u_1.EventMission.SongLaunchSpecialEvent then
            if v_u_2:test_enum_member(p18._event_info, v_u_1.EventMission) == true then
                local v21 = p_u_9._player_blob_manager:get_cached_blob(p18._id)
                if v21 ~= nil then
                    local v22, v23 = v_u_3:is_song_launch_event_active(p_u_9._api:get_day_event_list())
                    if v22 and (v_u_3:get_song_set_for_event_id(v23):contains(p_u_17) and (v_u_3:songkey_include_reward(p_u_17) and v_u_4:get_song_key_owned_count(v21, p_u_17) == 0)) then
                        p19:push_back(function(p24) --[[ Line: 59 ]]
                            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_17 ]]
                            v_u_4:add_song(p24, p_u_17)
                        end)
                        p20.ShowSongAcquiredPopup = true
                        p20.AcquiredSongKey = p_u_17
                    end;
                end;
            else
                return;
            end;
        else
            return;
        end;
    end;
    return v10;
end;
return v6;
