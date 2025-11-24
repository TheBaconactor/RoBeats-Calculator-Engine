-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:14 PM
-- Cached decompilation

require(game.ReplicatedStorage.Server.DebugOut)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
require(game.ReplicatedStorage.Shared.APICooldown)
local v_u_5 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.WaitForFinish)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_8 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_9 = require(game.ReplicatedStorage.EditorGame.Data.EditorGamePlayInfo)
local _ = game:GetService("DataStoreService")
local v10 = {}
local v_u_18 = {
    ["new"] = function(_, p_u_11, p_u_12) --[[ Name: new ]] --[[ Line: 22 ]]
        --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_5, (copy 3): v_u_8 ]]
        local v13 = {}
        v13.get_player_id = function(_) --[[ Name: get_player_id ]] --[[ Line: 25 ]]
            --[[ Upvalues: (copy 1): p_u_11 ]]
            return p_u_11;
        end;
        v13.get_saved_map_info = function(_) --[[ Name: get_saved_map_info ]] --[[ Line: 26 ]]
            --[[ Upvalues: (copy 1): p_u_12 ]]
            return p_u_12;
        end;
        local v_u_14 = v_u_9:new()
        v_u_14:set_rewarded_play(true)
        v13.get_editor_game_play_info = function(_) --[[ Name: get_editor_game_play_info ]] --[[ Line: 30 ]]
            --[[ Upvalues: (copy 1): v_u_14 ]]
            return v_u_14;
        end;
        local v_u_15 = true
        v13.is_playing = function(_) --[[ Name: is_playing ]] --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15;
        end;
        v13.set_playing = function(_, p16) --[[ Name: set_playing ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_15 ]]
            v_u_5:is_bool(p16)
            v_u_15 = p16
        end;
        v13.update = function(_, p17) --[[ Name: update ]] --[[ Line: 39 ]]
            --[[ Upvalues: (ref 1): v_u_15, (copy 2): v_u_14, (ref 3): v_u_8 ]]
            if v_u_15 then
                v_u_14:set_time_played_sec(v_u_14:get_time_played_sec() + v_u_8:TimescaleToDeltaTime(p17))
            end;
        end;
        return v13;
    end
}
v10.new = function(_, p_u_19, p20) --[[ Name: new ]] --[[ Line: 48 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_18, (copy 4): v_u_4, (copy 5): v_u_9, (copy 6): v_u_2, (copy 7): v_u_7, (copy 8): v_u_6 ]]
    local v21 = {}
    local v_u_22 = v_u_1:new()
    v21.start = function(_) --[[ Name: start ]] --[[ Line: 53 ]]
        --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_3, (copy 3): v_u_22, (ref 4): v_u_18, (ref 5): v_u_4, (ref 6): v_u_9 ]]
        p_u_19._evt:wait_on_event(v_u_3.EVT_EditorGame_ClientNotifyPlayStart, function(p23, p24) --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_18, (ref 3): v_u_4 ]]
            v_u_22:add(p23.UserId, v_u_18:new(p23.UserId, v_u_4.SavedMapInfo:from_table(p24)))
        end)
        p_u_19._evt:wait_on_event(v_u_3.EVT_EditorGame_ClientRequestPlayEnd, function(p_u_25, p26) --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): p_u_19, (ref 3): v_u_3, (ref 4): v_u_4, (ref 5): v_u_22 ]]
            local function f_response(p27, p28) --[[ Name: response ]] --[[ Line: 59 ]]
                --[[ Upvalues: (ref 1): v_u_9, (ref 2): p_u_19, (ref 3): v_u_3, (copy 4): p_u_25 ]]
                if p28 == nil then
                    p28 = v_u_9:new()
                end;
                p_u_19._evt:fire_event_to_client(v_u_3.EVT_EditorGame_ServerResponsePlayEnd, p_u_25, p27, p28:to_table())
            end;
            local v29 = v_u_4.SavedMapInfo:from_table(p26)
            if v_u_22:contains(p_u_25.UserId) ~= true then
                return f_response(false);
            end;
            local v30 = v_u_22:get(p_u_25.UserId)
            if v30:get_saved_map_info():get_custom_map_data_key() ~= v29:get_custom_map_data_key() then
                return f_response(false);
            end;
            if v30:is_playing() ~= true then
                return f_response(false);
            end;
            v30:set_playing(false)
            return f_response(true, v30:get_editor_game_play_info());
        end)
    end;
    v21.on_playerid_added_like_to_saved_map_info = function(_, p_u_31, p32, p_u_33) --[[ Name: on_playerid_added_like_to_saved_map_info ]] --[[ Line: 79 ]]
        --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_2, (copy 3): v_u_22, (ref 4): v_u_7, (ref 5): v_u_9, (ref 6): v_u_6 ]]
        local v_u_34 = p_u_19._player_manager:id_to_player(p_u_31)
        if v_u_34 == nil then
            return p_u_33(false);
        end;
        local function f_send_chat_message_to_player(p35) --[[ Name: send_chat_message_to_player ]] --[[ Line: 83 ]]
            --[[ Upvalues: (ref 1): p_u_19, (copy 2): v_u_34, (ref 3): v_u_2 ]]
            p_u_19._chat:get_chat_service():send_system_message_to_player_for_channel(v_u_34, p_u_19._chat:get_chat_service():get_channel(p_u_19._chat:get_chat_service():get_server_system_channel_id()), p35, function(p36) --[[ Line: 88 ]]
                --[[ Upvalues: (ref 1): v_u_2 ]]
                p36:set_channel_name("")
                p36:set_icon(v_u_2:important_assetid())
            end)
        end;
        if v_u_22:contains(p_u_31) ~= true then
            f_send_chat_message_to_player("Error: Not currently playing any map. Mission progress was not updated.")
            return p_u_33(false);
        end;
        local v37 = v_u_22:get(p_u_31)
        if v37:get_saved_map_info():get_custom_map_data_key() ~= p32:get_custom_map_data_key() then
            f_send_chat_message_to_player("Error: Not currently playing this map. Mission progress was not updated.")
            return p_u_33(false);
        end;
        if v_u_7.LikeMapMissionPerformAllChecks == true then
            if v37:get_saved_map_info():get_creator_rbxid() == v_u_34.UserId then
                f_send_chat_message_to_player("No mission progress was granted for liking your own map.")
                return p_u_33(false);
            end;
            if v37:get_editor_game_play_info():get_time_played_sec() < v_u_9:get_minimum_reward_time_play_sec() then
                f_send_chat_message_to_player(string.format("You must play the map for at least %ds before liking to get mission progress.", v_u_9:get_minimum_reward_time_play_sec()))
                return p_u_33(false);
            end;
        end;
        p_u_19._player_blob_manager:get_verified_cached_blob(p_u_31, function(p38) --[[ Line: 118 ]]
            --[[ Upvalues: (copy 1): p_u_33, (ref 2): p_u_19, (copy 3): f_send_chat_message_to_player, (copy 4): p_u_31, (ref 5): v_u_6 ]]
            if p38 == nil then
                return p_u_33(false);
            end;
            local v39, v40 = p_u_19._mission_manager:apply_custom_map_like_to_mission_for_player_blob(p38)
            if v39 ~= true then
                return p_u_33(false);
            end;
            if v40 > 0 then
                f_send_chat_message_to_player(string.format("You\'ve liked %d custom map(s) today! Mission progress was updated.", v40))
            end;
            p_u_19._player_blob_manager:enqueue_blob_sync_request(p_u_31, v_u_6.PlayerBlobRequestType.Write, function(_) --[[ Line: 134 ]]
                --[[ Upvalues: (ref 1): p_u_33 ]]
                p_u_33(true)
            end)
        end)
    end;
    p20:register_fn_on_update(function(p41) --[[ Line: 142 ]]
        --[[ Upvalues: (copy 1): v_u_22 ]]
        for _, v42 in v_u_22:key_itr() do
            v42:update(p41)
        end;
    end)
    p20:register_fn_on_disconnect(function(p43) --[[ Line: 148 ]]
        --[[ Upvalues: (copy 1): v_u_22 ]]
        v_u_22:remove(p43)
    end)
    return v21;
end;
return v10;
