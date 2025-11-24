-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:17 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.PlatformPlayerRewardInfo)
local v_u_5 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_6 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugOut)
local v9 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
v9:require_server(function() --[[ Line: 26 ]]
    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11, (ref 3): v_u_12, (ref 4): v_u_13, (ref 5): v_u_14, (ref 6): v_u_15, (ref 7): v_u_16, (ref 8): v_u_17, (ref 9): v_u_18 ]]
    v_u_10 = require(game.ReplicatedStorage.Server.SpecialEvent.ArtistSpecialEvent)
    v_u_11 = require(game.ReplicatedStorage.Server.SpecialEvent.GenericArtistSpecialEvent)
    v_u_12 = require(game.ReplicatedStorage.Server.SpecialEvent.GenericArtistP2SpecialEvent)
    v_u_13 = require(game.ReplicatedStorage.Server.SpecialEvent.GenericArtistP3SpecialEvent)
    v_u_14 = require(game.ReplicatedStorage.Server.SpecialEvent.JumpChallengeSpecialEvent)
    v_u_15 = require(game.ReplicatedStorage.Server.SpecialEvent.SummerCarnivalSpecialEvent)
    v_u_16 = require(game.ReplicatedStorage.Server.SpecialEvent.SummerBeachSpecialEvent)
    v_u_17 = require(game.ReplicatedStorage.Server.SpecialEvent.AutumnSpecialEvent)
    v_u_18 = require(game.ReplicatedStorage.Server.SpecialEvent.MiscSpecialEvent)
end)
local v_u_19 = {
    ["PlayerActionEvent"] = {
        ["QueueSongRadio"] = 1,
        ["VoteSongRadio"] = 2,
        ["SpeakPlayerNPCRewards"] = 3,
        ["CheerPlayer"] = 4,
        ["CompleteMission"] = 5
    },
    ["EventBase"] = {}
}
v_u_19.EventBase.new = function(_) --[[ Name: new ]] --[[ Line: 66 ]]
    return {
        ["write_special_event_data_for_play"] = function(_, _, _, _, _, _, _, _) end,
        ["player_connecting"] = function(_, _) end,
        ["player_disconnecting"] = function(_, _) end,
        ["update"] = function(_, _) end,
        ["can_playerid_start_songkey"] = function(_, _, _, _) --[[ Name: can_playerid_start_songkey ]] --[[ Line: 72 ]]
            return false;
        end,
        ["handle_player_action_event"] = function(_, _, _, _) end
    };
end;
v_u_19.EventBase.event_play_table_add_fn_post_sync = function(_, p20, p21) --[[ Name: event_play_table_add_fn_post_sync ]] --[[ Line: 77 ]]
    p20.FnPostSync = p21
end;
v_u_19.EventBase.event_play_table_get_fn_post_sync = function(_, p22) --[[ Name: event_play_table_get_fn_post_sync ]] --[[ Line: 81 ]]
    local v23
    if p22.FnPostSync then
        v23 = p22.FnPostSync
        p22.FnPostSync = nil
    else
        v23 = nil
    end;
    return v23;
end;
v_u_19.new = function(_, p_u_24) --[[ Name: new ]] --[[ Line: 90 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (ref 3): v_u_10, (ref 4): v_u_11, (ref 5): v_u_12, (ref 6): v_u_13, (ref 7): v_u_17, (ref 8): v_u_18, (copy 9): v_u_3, (copy 10): v_u_5, (copy 11): v_u_4, (copy 12): v_u_6, (copy 13): v_u_7, (copy 14): v_u_19, (copy 15): v_u_8 ]]
    local v25 = {}
    local v_u_26 = v_u_2:new()
    local v_u_27 = v_u_1:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 96 ]]
        --[[ Upvalues: (copy 1): v_u_26, (ref 2): v_u_10, (copy 3): p_u_24, (ref 4): v_u_11, (ref 5): v_u_12, (ref 6): v_u_13, (ref 7): v_u_17, (ref 8): v_u_18, (ref 9): v_u_3, (ref 10): v_u_5, (ref 11): v_u_4, (ref 12): v_u_6 ]]
        v_u_26:push_back(v_u_10:new(p_u_24))
        v_u_26:push_back(v_u_11:new(p_u_24))
        v_u_26:push_back(v_u_12:new(p_u_24))
        v_u_26:push_back(v_u_13:new(p_u_24))
        v_u_26:push_back(v_u_17:new(p_u_24))
        v_u_26:push_back(v_u_18:new(p_u_24))
        p_u_24._evt:wait_on_event(v_u_3.EVT_SpecialEvent_ClientClaimPlatformReward, function(p_u_28, p_u_29) --[[ Line: 117 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_4, (ref 3): p_u_24, (ref 4): v_u_3, (ref 5): v_u_6 ]]
            v_u_5:is_enum_member(p_u_29, v_u_4.Platform)
            local function f_response(p30, p31, p32) --[[ Name: response ]] --[[ Line: 120 ]]
                --[[ Upvalues: (ref 1): p_u_24, (ref 2): v_u_3, (copy 3): p_u_28 ]]
                p_u_24._evt:fire_event_to_client(v_u_3.EVT_SpecialEvent_ServerClaimPlatformRewardResponse, p_u_28, p30, p31, p32 == nil and {} or p32)
            end;
            p_u_24._player_blob_manager:get_verified_cached_blob(p_u_28.UserId, function(p33) --[[ Line: 125 ]]
                --[[ Upvalues: (copy 1): f_response, (ref 2): v_u_4, (copy 3): p_u_29, (ref 4): v_u_6, (ref 5): p_u_24, (copy 6): p_u_28, (ref 7): v_u_3 ]]
                if p33 == nil then
                    return f_response(false, "Playerblob nil");
                end;
                if v_u_4:playerblob_has_claimed_reward_for_platform(p33, p_u_29) then
                    return f_response(false, "Reward already claimed.");
                end;
                local v34 = v_u_4:platform_get_reward_desc_info_list(p_u_29)
                if v34 == nil or v34:count() == 0 then
                    return f_response(false, "Reward not found.");
                end;
                v_u_6:server_sync_reward_params(p_u_24, p_u_28, v_u_6:claim_reward_info_list_to_playerblob(p_u_24, p33, v34), function(p35, _, p36) --[[ Line: 137 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_24, (ref 3): v_u_3, (ref 4): p_u_28 ]]
                    local v37 = v_u_6.RewardInfo:list_to_table(p36)
                    p_u_24._evt:fire_event_to_client(v_u_3.EVT_SpecialEvent_ServerClaimPlatformRewardResponse, p_u_28, true, p35, v37 == nil and {} or v37)
                end)
            end)
        end)
    end;
    v25.player_connecting = function(_, p38) --[[ Name: player_connecting ]] --[[ Line: 145 ]]
        --[[ Upvalues: (copy 1): v_u_27, (ref 2): v_u_1, (copy 3): v_u_26 ]]
        if v_u_27:contains(p38) ~= true then
            v_u_27:add(p38, v_u_1:new())
        end;
        for _, v39 in v_u_26:key_itr() do
            v39:player_connecting(p38)
        end;
    end;
    v25.player_disconnecting = function(_, p40) --[[ Name: player_disconnecting ]] --[[ Line: 154 ]]
        --[[ Upvalues: (copy 1): v_u_26, (copy 2): v_u_27 ]]
        for _, v41 in v_u_26:key_itr() do
            v41:player_disconnecting(p40)
        end;
        v_u_27:remove(p40)
    end;
    v25.get_eventdata_for_playerid = function(_, p42) --[[ Name: get_eventdata_for_playerid ]] --[[ Line: 161 ]]
        --[[ Upvalues: (copy 1): p_u_24, (ref 2): v_u_1, (copy 3): v_u_27 ]]
        if p_u_24._player_manager:id_to_player(p42) == nil then
            return v_u_1:new();
        end;
        if v_u_27:contains(p42) ~= true then
            v_u_27:add(p42, v_u_1:new())
        end;
        return v_u_27:get(p42);
    end;
    v25.send_updated_eventdata_to_playerid = function(p43, p44) --[[ Name: send_updated_eventdata_to_playerid ]] --[[ Line: 169 ]]
        --[[ Upvalues: (copy 1): p_u_24, (ref 2): v_u_3 ]]
        local v45 = p_u_24._player_manager:id_to_player(p44)
        if v45 then
            p_u_24._evt:fire_event_to_client(v_u_3.EVT_SpecialEvent_ServerNotifyPlayerDataUpdated, v45, p43:get_eventdata_for_playerid(p44):get_table())
        end;
    end;
    v25.write_special_event_data_for_play = function(_, p_u_46, p_u_47, p_u_48, p_u_49, p_u_50, p_u_51) --[[ Name: write_special_event_data_for_play ]] --[[ Line: 176 ]]
        --[[ Upvalues: (copy 1): v_u_26, (ref 2): v_u_7 ]]
        local v_u_52 = {}
        for v_u_53 = 1, v_u_26:count() do
            v_u_7:ptry(function() --[[ Line: 179 ]]
                --[[ Upvalues: (ref 1): v_u_26, (copy 2): v_u_53, (copy 3): p_u_46, (copy 4): p_u_47, (copy 5): p_u_48, (copy 6): p_u_49, (copy 7): p_u_50, (copy 8): p_u_51, (copy 9): v_u_52 ]]
                v_u_26:get(v_u_53):write_special_event_data_for_play(p_u_46, p_u_47, p_u_48, p_u_49, p_u_50, p_u_51, v_u_52)
            end)
        end;
        return v_u_52;
    end;
    v25.write_special_event_data_for_player_action = function(_, p_u_54, p_u_55, p_u_56) --[[ Name: write_special_event_data_for_player_action ]] --[[ Line: 194 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_19, (ref 3): v_u_8, (copy 4): v_u_26, (ref 5): v_u_7 ]]
        if v_u_5:test_enum_member(p_u_55, v_u_19.PlayerActionEvent) ~= true then
            return v_u_8:errf("write_special_event_data_for_player_action invalid player_action_event %s", (tostring(p_u_55)));
        end;
        for _, v_u_57 in v_u_26:key_itr() do
            v_u_7:ptry(function() --[[ Line: 197 ]]
                --[[ Upvalues: (copy 1): v_u_57, (copy 2): p_u_54, (copy 3): p_u_55, (copy 4): p_u_56 ]]
                v_u_57:handle_player_action_event(p_u_54, p_u_55, p_u_56)
            end)
        end;
    end;
    v25.test_event_if_playerid_can_start_songkey = function(_, p58, p59, p60) --[[ Name: test_event_if_playerid_can_start_songkey ]] --[[ Line: 203 ]]
        --[[ Upvalues: (copy 1): v_u_26 ]]
        for _, v61 in v_u_26:key_itr() do
            if v61:can_playerid_start_songkey(p58, p59, p60) then
                return true;
            end;
        end;
        return false;
    end;
    v25.update = function(_, p62) --[[ Name: update ]] --[[ Line: 212 ]]
        --[[ Upvalues: (copy 1): v_u_26 ]]
        for _, v63 in v_u_26:key_itr() do
            v63:update(p62)
        end;
    end;
    f_cons()
    return v25;
end;
return v_u_19;
