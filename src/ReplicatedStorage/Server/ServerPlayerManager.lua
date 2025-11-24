-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:15 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.ProdEnvSelector)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_8 = require(game.ReplicatedStorage.Shared.PlayerListActivity)
local v_u_9 = require(game.ReplicatedStorage.Shared.PlayerListEntry)
local v_u_10 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_11 = require(game.ReplicatedStorage.Server.EnvironmentSetupServer)
local v_u_12 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstanceMode)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_13 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_14 = require(game.ServerScriptService.AudioPrivateKeys)
local v_u_15 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
local v_u_16 = require(game.ReplicatedStorage.Shared.FlashEvery)
local v_u_17 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_18 = require(game.ReplicatedStorage.Server.DebugPlayerListEntrySimulation)
return {
    ["new"] = function(_, p_u_19) --[[ Name: new ]] --[[ Line: 24 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_16, (copy 5): v_u_4, (copy 6): v_u_14, (copy 7): v_u_7, (copy 8): v_u_1, (copy 9): v_u_6, (copy 10): v_u_18, (copy 11): v_u_5, (copy 12): v_u_17, (copy 13): v_u_15, (copy 14): v_u_13, (copy 15): v_u_10, (copy 16): v_u_8, (copy 17): v_u_12, (copy 18): v_u_9 ]]
        local v20 = {
            ["_character_collide_group"] = v_u_11:get_player_collision_group()
        }
        local v_u_21 = v_u_2:new()
        local v_u_22 = v_u_2:new()
        local v_u_23 = false
        v20.set_is_shutting_down = function(_, p24) --[[ Name: set_is_shutting_down ]] --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23 = p24
        end;
        v20.is_shutting_down = function(_) --[[ Name: is_shutting_down ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23;
        end;
        local v_u_25 = v_u_3:new()
        local v_u_26 = nil
        local v_u_27 = v_u_3:new()
        v20.get_playerlist_subscribed_count = function(_) --[[ Name: get_playerlist_subscribed_count ]] --[[ Line: 41 ]]
            --[[ Upvalues: (copy 1): v_u_27 ]]
            return v_u_27:count();
        end;
        local v_u_28 = v_u_16:new(5)
        v20.player_joined_enqueue = function(_, p_u_29) --[[ Name: player_joined_enqueue ]] --[[ Line: 44 ]]
            --[[ Upvalues: (copy 1): p_u_19, (copy 2): v_u_25, (ref 3): v_u_4, (ref 4): v_u_14, (copy 5): v_u_21, (ref 6): v_u_7, (ref 7): v_u_1 ]]
            p_u_19._id_to_player:add(p_u_29.UserId, p_u_29)
            v_u_25:add(p_u_29.UserId, 0)
            v_u_4:server_push_update_to_player(p_u_29, v_u_14, function() --[[ Line: 48 ]]
                --[[ Upvalues: (ref 1): v_u_21, (copy 2): p_u_29 ]]
                v_u_21:push_back(p_u_29)
            end)
            if v_u_7:is_dev_build() then
                v_u_1:puts("ServerPlayerManager:player_joined_enqueued(%d)", p_u_29.UserId)
            end;
        end;
        v20.start = function(p_u_30) --[[ Name: start ]] --[[ Line: 56 ]]
            --[[ Upvalues: (copy 1): v_u_22, (ref 2): v_u_6, (ref 3): v_u_26, (ref 4): v_u_18, (copy 5): p_u_19, (ref 6): v_u_5, (ref 7): v_u_17, (copy 8): v_u_27 ]]
            game.Players.PlayerAdded:connect(function(p31) --[[ Line: 57 ]]
                --[[ Upvalues: (copy 1): p_u_30 ]]
                p_u_30:player_joined_enqueue(p31)
            end)
            game.Players.PlayerRemoving:connect(function(p32) --[[ Line: 60 ]]
                --[[ Upvalues: (ref 1): v_u_22 ]]
                v_u_22:push_back(p32)
            end)
            local v33 = game.Players:GetChildren()
            for v34 = 1, #v33 do
                p_u_30:player_joined_enqueue(v33[v34])
            end;
            if v_u_6.QueryPlayerListFakeData == true then
                v_u_26 = v_u_18:new(p_u_19)
            end;
            p_u_19._evt:wait_on_event(v_u_5.EVT_Players_ClientQueryPlayerList, function(p35) --[[ Line: 74 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_5, (copy 3): p_u_30 ]]
                p_u_19._evt:fire_event_to_client(v_u_5.EVT_Players_ServerQueryPlayerListResponse, p35, p_u_30:client_query_player_list_tab())
            end)
            p_u_19._evt:wait_on_event(v_u_5.EVT_Players_ClientSetSubscribePlayerListUpdates, function(p36, p37) --[[ Line: 78 ]]
                --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_27, (ref 3): p_u_19, (ref 4): v_u_5, (copy 5): p_u_30 ]]
                v_u_17:is_bool(p37)
                if p37 == true then
                    v_u_27:add_set(p36.UserId)
                    p_u_19._evt:fire_event_to_client(v_u_5.EVT_Players_ServerSendPlayerListUpdate, p36, p_u_30:client_query_player_list_tab())
                else
                    v_u_27:remove(p36.UserId)
                end;
            end)
        end;
        local v_u_38 = false
        v20.raise_playerlist_update_next_frame = function(_) --[[ Name: raise_playerlist_update_next_frame ]] --[[ Line: 94 ]]
            --[[ Upvalues: (ref 1): v_u_38 ]]
            v_u_38 = true
        end;
        v20.update = function(p_u_39, p40) --[[ Name: update ]] --[[ Line: 98 ]]
            --[[ Upvalues: (copy 1): v_u_21, (copy 2): p_u_19, (copy 3): v_u_22, (ref 4): v_u_1, (ref 5): v_u_7, (ref 6): v_u_15, (copy 7): v_u_25, (ref 8): v_u_13, (ref 9): v_u_26, (copy 10): v_u_28, (ref 11): v_u_38, (ref 12): v_u_3, (copy 13): v_u_27, (ref 14): v_u_5 ]]
            for _, v41 in v_u_21:key_itr() do
                p_u_19._special_event_manager:player_connecting(v41.UserId)
            end;
            v_u_21:clear()
            for v42 = 1, v_u_22:count() do
                local v43 = v_u_22:get(v42)
                local l_UserId_0 = v43.UserId
                v_u_1:puts("Player disconnected[%s](%d)", v43.Name, l_UserId_0)
                p_u_19._player_blob_manager:add_lock_to_player_id(l_UserId_0)
                local v45, v46 = v_u_7:try(function() --[[ Line: 111 ]]
                    --[[ Upvalues: (ref 1): p_u_19, (copy 2): l_UserId_0, (ref 3): v_u_15, (copy 4): p_u_39 ]]
                    p_u_19._evt:server_player_disconnecting(l_UserId_0)
                    p_u_19._trade_manager:player_disconnecting(l_UserId_0)
                    p_u_19._game_instance_manager:remove_enqueued_player(l_UserId_0)
                    p_u_19._game_instance_manager:remove_spectating_player(l_UserId_0)
                    p_u_19._game_instance_manager:player_disconnecting(l_UserId_0)
                    p_u_19._player_model_cache:remove_id_from_cache(l_UserId_0)
                    p_u_19._web_npc_manager:player_disconnecting(l_UserId_0)
                    p_u_19._player_song_stats_manager:player_disconnecting(l_UserId_0)
                    p_u_19._leaderboard_manager:player_disconnecting(l_UserId_0)
                    p_u_19._danceclub_manager:player_disconnecting(l_UserId_0)
                    p_u_19._special_event_manager:player_disconnecting(l_UserId_0)
                    p_u_19._lobby_manager:player_disconnecting(l_UserId_0)
                    p_u_19._chat:player_disconnecting(l_UserId_0)
                    p_u_19._player_status_manager:player_disconnecting(l_UserId_0)
                    p_u_19._guild_manager:player_disconnecting(l_UserId_0)
                    p_u_19._tutorial_manager:player_disconnecting(l_UserId_0)
                    p_u_19._collection_manager:player_disconnecting(l_UserId_0)
                    v_u_15:singleton():server_player_disconnecting(l_UserId_0)
                    p_u_19._editor_game_manager:player_disconnecting(l_UserId_0)
                    local v44 = p_u_39:get_player_gameinstance(l_UserId_0)
                    if v44 ~= nil then
                        v44._util:mark_player_as_left(l_UserId_0)
                    end;
                end)
                if v45 ~= true then
                    v_u_1:warnf("ServerPlayerManager _player_removed_queue error (%s)[%s]", v46.Error, v46.StackTrace)
                end;
                p_u_19._id_to_player:remove(l_UserId_0)
                p_u_19._player_blob_manager:player_disconnecting(l_UserId_0)
                v_u_25:remove(l_UserId_0)
            end;
            for v47, v48 in v_u_25:key_itr() do
                v_u_25:add(v47, v48 + v_u_13:TimescaleToDeltaTime(p40))
            end;
            v_u_22:clear()
            if v_u_26 ~= nil then
                v_u_26:update(p40)
            end;
            v_u_28:update(p40)
            if v_u_38 == true or v_u_28:do_flash() then
                if v_u_38 == true then
                    v_u_38 = false
                    v_u_28:reset()
                end;
                local v_u_49 = p_u_39:client_query_player_list_tab()
                v_u_3:remove_if(v_u_27, function(_, p50) --[[ Line: 167 ]]
                    --[[ Upvalues: (copy 1): p_u_39, (ref 2): p_u_19, (ref 3): v_u_5, (copy 4): v_u_49 ]]
                    local v51 = p_u_39:id_to_player(p50)
                    if v51 == nil then
                        return true;
                    end;
                    p_u_19._evt:fire_event_to_client(v_u_5.EVT_Players_ServerSendPlayerListUpdate, v51, v_u_49)
                    return false;
                end)
            end;
        end;
        v20.get_player_gameinstance = function(_, p52) --[[ Name: get_player_gameinstance ]] --[[ Line: 182 ]]
            --[[ Upvalues: (copy 1): p_u_19 ]]
            for v53 = 1, p_u_19._game_instances:count() do
                local v54 = p_u_19._game_instances:get(v53)
                if v54._util:player_in_game(p52) then
                    return v54;
                end;
            end;
            return nil;
        end;
        v20.id_to_player = function(_, p55) --[[ Name: id_to_player ]] --[[ Line: 192 ]]
            --[[ Upvalues: (copy 1): p_u_19 ]]
            if p_u_19._id_to_player:contains(p55) then
                return p_u_19._id_to_player:get(p55);
            else
                return nil;
            end;
        end;
        v20.players_key_itr = function(_) --[[ Name: players_key_itr ]] --[[ Line: 200 ]]
            --[[ Upvalues: (copy 1): p_u_19 ]]
            return p_u_19._id_to_player:key_itr();
        end;
        v20.client_query_player_list_tab = function(p56) --[[ Name: client_query_player_list_tab ]] --[[ Line: 204 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_19, (ref 3): v_u_10, (ref 4): v_u_8, (ref 5): v_u_12, (copy 6): v_u_25, (ref 7): v_u_9, (ref 8): v_u_26 ]]
            local v57 = v_u_2:new()
            for v58, v59 in p_u_19._id_to_player:key_itr() do
                local v60 = v_u_10:invalid_songkey()
                local v61 = p56:get_player_gameinstance(v58)
                local v62 = -1
                local v63 = 0
                local v64
                if v61 == nil then
                    if p_u_19._game_instance_manager:get_player_id_spectate_gameinstance(v58) == nil then
                        v64 = v_u_8.Lobby
                    else
                        v64 = v_u_8.Spectate
                    end;
                else
                    v63 = v61:valid_player_count()
                    if v61._match_making:is_joinable() == true then
                        v64 = v_u_8.MatchMaking
                    elseif v61._current_mode == v_u_12.GameEnding or v61._current_mode == v_u_12.GameEnded then
                        v64 = v_u_8.MatchEnded
                    elseif v61._current_mode == v_u_12.MatchMaking or v61._current_mode == v_u_12.VotePick then
                        v64 = v_u_8.Voting
                    else
                        v64 = v_u_8.Match
                        v62 = v61._playback_time_ms
                    end;
                    if v_u_10:singleton():contains_key(v61._selected_song_key) == true then
                        v60 = v61._selected_song_key
                    else
                        local v65 = v61._util:get_player(v58)
                        if v65 ~= nil then
                            v60 = v65._requested_song_key
                        end;
                    end;
                end;
                v57:push_back(v_u_9:new(v59.Name, v59.UserId, v64, v60, v62, not v_u_25:contains(v58) and 0 or v_u_25:get(v58), v63))
            end;
            if v_u_26 ~= nil then
                v57:push_back_from_list(v_u_26:client_query_player_list_fake_data_list())
            end;
            return v_u_9:list_to_table(v57);
        end;
        return v20;
    end
};
