-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:22 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_2 = require(game.ReplicatedStorage.Server.Spectate.SpectateServerDebug)
local v_u_3 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstanceMode)
local v_u_4 = require(game.ReplicatedStorage.Server.DebugOut)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_6 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_7 = require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_9 = require(game.ReplicatedStorage.Shared.CurveUtil)
return {
    ["new"] = function(_, p_u_10) --[[ Name: new ]] --[[ Line: 14 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_5, (copy 3): v_u_1, (copy 4): v_u_3, (copy 5): v_u_6, (copy 6): v_u_4, (copy 7): v_u_7, (copy 8): v_u_8, (copy 9): v_u_9 ]]
        local v11 = {}
        local v_u_12 = v_u_2:new(p_u_10)
        local v_u_13 = v_u_5:new()
        local v_u_14 = v_u_5:new()
        v11.start = function(p_u_15) --[[ Name: start ]] --[[ Line: 21 ]]
            --[[ Upvalues: (copy 1): v_u_12, (copy 2): p_u_10, (ref 3): v_u_1, (ref 4): v_u_3, (copy 5): v_u_14, (ref 6): v_u_6, (ref 7): v_u_4, (copy 8): v_u_13, (ref 9): v_u_7 ]]
            v_u_12:start()
            p_u_10._evt:wait_on_event(v_u_1.EVT_LobbySpectate_ClientRequestJoinPlayerId, function(p16, p17) --[[ Line: 24 ]]
                --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_1, (ref 3): v_u_3, (ref 4): v_u_14, (ref 5): v_u_6 ]]
                local v18 = p_u_10._player_manager:get_player_gameinstance(p17)
                if v18 == nil then
                    p_u_10._evt:fire_event_to_client(v_u_1.EVT_LobbySpectate_ServerResponseRequestJoinPlayerId, p16, false, "Match not found.")
                    return;
                else
                    local v19 = false
                    if v18._current_mode == v_u_3.Game or v18._current_mode == v_u_3.SoundLoad then
                        v19 = v18._selected_song_key ~= nil and true or v19
                    end;
                    if v19 == true then
                        local v20 = v18._util:get_player_slot(p17)
                        if v20 == nil then
                            p_u_10._evt:fire_event_to_client(v_u_1.EVT_LobbySpectate_ServerResponseRequestJoinPlayerId, p16, false, "Match could not be joined, player has left.")
                            return;
                        elseif v_u_14:contains(p16.UserId) then
                            p_u_10._evt:fire_event_to_client(v_u_1.EVT_LobbySpectate_ServerResponseRequestJoinPlayerId, p16, false, string.format("%.2f seconds until you can spectate another match.", v_u_14:get(p16.UserId)))
                        else
                            v_u_14:add(p16.UserId, v_u_6.SPECTATE_JOIN_COOLDOWN_SEC)
                            v18:spectator_joined(p16.UserId, v20)
                            p_u_10._evt:fire_event_to_client(v_u_1.EVT_LobbySpectate_ServerResponseRequestJoinPlayerId, p16, true, "", {
                                ["SelectedSongKey"] = v18._selected_song_key,
                                ["FocusedSlot"] = v20,
                                ["GameId"] = v18._game_id
                            }, v18._util:get_player_info_data(), v18._util:get_player_gear_info(), v18._util:get_player_note_skin_info():to_table(), v18._util:get_player_dance_info():to_table())
                        end;
                    else
                        p_u_10._evt:fire_event_to_client(v_u_1.EVT_LobbySpectate_ServerResponseRequestJoinPlayerId, p16, false, "Match could not be joined.")
                        return;
                    end;
                end;
            end)
            p_u_10._evt:wait_on_event(v_u_1.EVT_Spectate_ClientSwitchFocusedPlayer, function(p21, p22) --[[ Line: 75 ]]
                --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_3 ]]
                local v23 = p_u_10._player_manager:get_player_gameinstance(p22)
                if v23 == nil then
                    return;
                end;
                if v23._current_mode ~= v_u_3.Game then
                    return;
                end;
                local v24 = nil
                for v25 = 1, v23._spectators:count() do
                    local v26 = v23._spectators:get(v25)
                    if v26:get_player_id() == p21.UserId then
                        v24 = v26
                        break;
                    end;
                end;
                if v24 ~= nil then
                    v24:change_focused_slot((v23._util:get_player_slot(p22)))
                end;
            end)
            p_u_10._evt:wait_on_event(v_u_1.EVT_Spectate_ClientRequestApplySpectatorCheerReward, function(p_u_27) --[[ Line: 100 ]]
                --[[ Upvalues: (copy 1): p_u_15, (ref 2): p_u_10, (ref 3): v_u_1 ]]
                local _, v28, _ = p_u_15:get_player_id_spectate_gameinstance(p_u_27.UserId)
                if v28 ~= nil then
                    v28:apply_spectator_cheer_reward(function() --[[ Line: 103 ]]
                        --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_1, (copy 3): p_u_27 ]]
                        p_u_10._evt:fire_event_to_client(v_u_1.EVT_Spectate_ServerAppliedSpectatorCheerReward, p_u_27)
                    end)
                end;
            end)
            p_u_10._evt:wait_on_event(v_u_1.EVT_Spectate_ClientFinished, function(p29) --[[ Line: 109 ]]
                --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_4 ]]
                local v30, _, _ = p_u_15:get_player_id_spectate_gameinstance(p29.UserId)
                if v30 == nil then
                    v_u_4:warnf("EVT_Spectate_ClientFinished itr_gameinstance is nil")
                else
                    v30:spectate_client_finished(p29.UserId)
                end;
            end)
            p_u_10._evt:wait_on_event(v_u_1.EVT_Spectate_ClientLeave, function(p31) --[[ Line: 118 ]]
                --[[ Upvalues: (copy 1): p_u_15, (ref 2): v_u_4 ]]
                local v32, _, _ = p_u_15:get_player_id_spectate_gameinstance(p31.UserId)
                if v32 == nil then
                    v_u_4:warnf("EVT_Spectate_ClientLeave cannot find gameinstance")
                else
                    v32:spectator_leave(p31.UserId)
                end;
            end)
            p_u_10._evt:wait_on_event(v_u_1.EVT_Spectate_ClientCheerPlayerId, function(p_u_33, p34) --[[ Line: 127 ]]
                --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_1, (ref 3): v_u_13, (ref 4): v_u_7, (ref 5): v_u_4, (ref 6): v_u_6, (ref 7): v_u_3 ]]
                local function _(p35, p36) --[[ Name: response ]] --[[ Line: 128 ]]
                    --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_1, (copy 3): p_u_33 ]]
                    p_u_10._evt:fire_event_to_client(v_u_1.EVT_Spectate_ServerResponseCheerPlayerId, p_u_33, p35, p36)
                end;
                if v_u_13:contains(p_u_33.UserId) then
                    p_u_10._api:api_report_evt(v_u_7.ReportEvt_CheerSanityCheckFail, p_u_33.UserId, v_u_13:get(p_u_33.UserId), "")
                    v_u_4:warnf("Cheer Sanity Cooldown failed UserId(%s)", (tostring(p_u_33.UserId)))
                    return;
                end;
                v_u_13:add(p_u_33.UserId, v_u_6.SPECTATE_CHEER_SANITY_TEST_SEC)
                local v37 = p_u_10._player_manager:get_player_gameinstance(p34)
                if v37 == nil then
                    v_u_4:warnf("EVT_Spectate_ClientCheerPlayerId target_gameinstance nil")
                    p_u_10._evt:fire_event_to_client(v_u_1.EVT_Spectate_ServerResponseCheerPlayerId, p_u_33, false, 0)
                    return;
                end;
                if v37._current_mode ~= v_u_3.Game then
                    v_u_4:warnf("EVT_Spectate_ClientCheerPlayerId gamemode(%d)", v37._current_mode)
                    p_u_10._evt:fire_event_to_client(v_u_1.EVT_Spectate_ServerResponseCheerPlayerId, p_u_33, false, 0)
                    return;
                end;
                local v38 = nil
                for v39 = 1, v37._spectators:count() do
                    local v40 = v37._spectators:get(v39)
                    if v40:get_player_id() == p_u_33.UserId then
                        v38 = v40
                        break;
                    end;
                end;
                if v38 == nil then
                    v_u_4:warnf("EVT_Spectate_ClientCheerPlayerId tar_spectator nil")
                    p_u_10._evt:fire_event_to_client(v_u_1.EVT_Spectate_ServerResponseCheerPlayerId, p_u_33, false, 0)
                    return;
                else
                    local v41 = v37._slots:get((v37._util:get_player_slot(p34)))
                    if v41 == nil then
                        v_u_4:warnf("EVT_Spectate_ClientCheerPlayerId tar_player nil")
                        p_u_10._evt:fire_event_to_client(v_u_1.EVT_Spectate_ServerResponseCheerPlayerId, p_u_33, false, 0)
                    else
                        v41._like_count = v41._like_count + 1
                        v38:cheer_for_playerid(p34)
                        p_u_10._evt:fire_event_to_client(v_u_1.EVT_Spectate_ServerResponseCheerPlayerId, p_u_33, true, v41._like_count)
                    end;
                end;
            end)
        end;
        v11.get_player_id_spectate_gameinstance = function(_, p42) --[[ Name: get_player_id_spectate_gameinstance ]] --[[ Line: 179 ]]
            --[[ Upvalues: (copy 1): p_u_10 ]]
            for v43 = 1, p_u_10._game_instances:count() do
                local v44 = p_u_10._game_instances:get(v43)
                local v45, v46 = v44._util:is_player_spectating_gameinstance(p42)
                if v45 ~= nil then
                    return v44, v45, v46;
                end;
            end;
            return nil, nil, -1;
        end;
        local v_u_47 = v_u_8:new()
        v11.update = function(_, p48) --[[ Name: update ]] --[[ Line: 191 ]]
            --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_47, (copy 3): v_u_13, (ref 4): v_u_9, (copy 5): v_u_14 ]]
            v_u_12:update(p48)
            v_u_47:clear()
            local v49 = v_u_47
            for v50, v51 in v_u_13:key_itr() do
                local v52 = v51 - v_u_9:TimescaleToDeltaTime(p48)
                v_u_13:add(v50, v52)
                if v52 <= 0 then
                    v49:push_back(v50)
                end;
            end;
            for v53 = 1, v49:count() do
                v_u_13:remove(v49:get(v53))
            end;
            v_u_47:clear()
            local v54 = v_u_47
            for v55, v56 in v_u_14:key_itr() do
                local v57 = v56 - v_u_9:TimescaleToDeltaTime(p48)
                v_u_14:add(v55, v57)
                if v57 <= 0 then
                    v54:push_back(v55)
                end;
            end;
            for v58 = 1, v54:count() do
                v_u_14:remove(v54:get(v58))
            end;
        end;
        return v11;
    end
};
