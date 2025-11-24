-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:25 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_5 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Local.GameLocal)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_9 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
local v_u_10 = require(game.ReplicatedStorage.Shared.GameDanceInfo)
local v_u_11 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_12 = {
    ["Mode"] = {
        ["PreJoin"] = 1,
        ["MatchmakingWaiting"] = 3,
        ["DoVotepick"] = 4,
        ["Votepick"] = 5,
        ["HasVotepicked"] = 6,
        ["ServerNotifyClientDoPreload"] = 7,
        ["Preloading"] = 8,
        ["ClientDoStart"] = 9,
        ["ServerJoinTargetPlayerError"] = 10,
        ["ClientEnqueueErrorFromServer"] = 11
    }
}
v_u_12.new = function(_, p_u_13) --[[ Name: new ]] --[[ Line: 37 ]]
    --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_1, (copy 3): v_u_8, (copy 4): v_u_2, (copy 5): v_u_11, (copy 6): v_u_9, (copy 7): v_u_10, (copy 8): v_u_7, (copy 9): v_u_5, (copy 10): v_u_6, (copy 11): v_u_3, (copy 12): v_u_4 ]]
    local v14 = {}
    local l__evt_0 = p_u_13._evt
    local l_PreJoin_0 = v_u_12.Mode.PreJoin
    v14.set_mode = function(_, p15) --[[ Name: set_mode ]] --[[ Line: 42 ]]
        --[[ Upvalues: (ref 1): l_PreJoin_0 ]]
        l_PreJoin_0 = p15
    end;
    local v_u_16 = v_u_1:new()
    local v_u_17 = {}
    local v_u_18 = {}
    v14.set_player_info = function(_, p19) --[[ Name: set_player_info ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_8, (ref 3): v_u_16 ]]
        v_u_17 = p19
        v_u_8:update_dict_from_player_info_table(v_u_16, p19)
    end;
    v14.set_gear_info = function(_, p20) --[[ Name: set_gear_info ]] --[[ Line: 51 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        v_u_18 = p20
    end;
    local v_u_21 = -1
    local v_u_22 = -1
    local v_u_23 = -1
    local v_u_24 = 0
    local v_u_25 = 0
    local v_u_26 = {}
    local v_u_27 = 0
    v14.get_matchmaking_time = function(_) --[[ Name: get_matchmaking_time ]] --[[ Line: 62 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27;
    end;
    local v_u_28 = nil
    local v_u_29 = nil
    local v_u_30 = false
    local v_u_31 = "???"
    local v_u_32 = "???"
    local v_u_33 = v_u_2:new()
    local v_u_34 = v_u_11:new()
    local v_u_35 = true
    local v_u_36 = false
    local v_u_37 = v_u_9:new()
    local v_u_38 = v_u_10:get_default_dance_info()
    v14.is_networked = function(_) --[[ Name: is_networked ]] --[[ Line: 81 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        return v_u_35;
    end;
    v14.is_tutorial = function(_) --[[ Name: is_tutorial ]] --[[ Line: 82 ]]
        --[[ Upvalues: (ref 1): v_u_36 ]]
        return v_u_36;
    end;
    v14.set_networked = function(_, p39) --[[ Name: set_networked ]] --[[ Line: 83 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        v_u_35 = p39
    end;
    v14.set_tutorial = function(_, p40) --[[ Name: set_tutorial ]] --[[ Line: 84 ]]
        --[[ Upvalues: (ref 1): v_u_36 ]]
        v_u_36 = p40
    end;
    local v_u_41 = nil
    v14.set_event_info = function(_, p42) --[[ Name: set_event_info ]] --[[ Line: 87 ]]
        --[[ Upvalues: (ref 1): v_u_41 ]]
        v_u_41 = p42
    end;
    v14.get_event_info = function(_) --[[ Name: get_event_info ]] --[[ Line: 88 ]]
        --[[ Upvalues: (ref 1): v_u_41 ]]
        return v_u_41;
    end;
    v14.mmv3_join_matchmaking_shared = function(p_u_43, p44) --[[ Name: mmv3_join_matchmaking_shared ]] --[[ Line: 91 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_16, (ref 3): v_u_1, (ref 4): v_u_17, (ref 5): v_u_33, (ref 6): v_u_2, (ref 7): v_u_23, (ref 8): v_u_7, (ref 9): v_u_5, (ref 10): l_PreJoin_0, (ref 11): v_u_12, (copy 12): l__evt_0, (ref 13): v_u_6, (ref 14): v_u_8, (ref 15): v_u_22, (ref 16): v_u_3, (ref 17): v_u_24, (ref 18): v_u_25, (ref 19): v_u_26, (ref 20): v_u_29, (ref 21): v_u_28, (ref 22): v_u_18, (ref 23): v_u_37, (ref 24): v_u_9, (ref 25): v_u_38, (ref 26): v_u_10, (ref 27): v_u_32 ]]
        v_u_21 = -1
        v_u_16 = v_u_1:new()
        v_u_17 = {}
        v_u_33 = v_u_2:new()
        v_u_23 = -1
        p_u_43:remove_local_waits()
        if v_u_7:singleton():contains_key(p44) then
            if l_PreJoin_0 ~= v_u_12.Mode.PreJoin then
                v_u_5:warnf("GameJoinProtocol:try_join_game current mode is(%d)", l_PreJoin_0)
            end;
            l_PreJoin_0 = v_u_12.Mode.MatchmakingWaiting
            l__evt_0:wait_on_event(v_u_6.EVT_GameLoad_ServerUpdateMatchMakingInfo, function(p45, p46) --[[ Line: 106 ]]
                --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_8, (ref 3): v_u_16, (copy 4): p_u_43, (ref 5): l_PreJoin_0, (ref 6): v_u_12, (ref 7): v_u_22, (ref 8): v_u_5, (ref 9): v_u_3 ]]
                v_u_17 = p45
                v_u_8:update_dict_from_matchmaking_info_table(v_u_16, p45)
                p_u_43:update_time()
                local v47 = l_PreJoin_0 == v_u_12.Mode.MatchmakingWaiting
                local v48 = v_u_22
                if v47 == true then
                    v_u_22 = p46
                end;
                if v47 == false and v48 ~= p46 then
                    v_u_5:warnf("EVT_GameLoad_ServerUpdateMatchMakingInfo slot_id change to(%s) was(%s) in mode(%s)", v_u_3:num_string(p46), v_u_3:num_string(v48), v_u_3:num_string(l_PreJoin_0))
                end;
                if p46 ~= v_u_8:slot_from_player_info_table_for_id(p45, v_u_3:get_local_userid()) then
                    v_u_5:warnf("EVT_GameLoad_ServerUpdateMatchMakingInfo slot_id(%s) does not match slot_from_player_info_table_for_id(%s)", v_u_3:num_string(p46), v_u_3:num_string(v_u_8:slot_from_player_info_table_for_id(p45, v_u_3:get_local_userid())))
                end;
            end)
            l__evt_0:wait_on_event(v_u_6.EVT_GameLoad_MatchmakingV3_ServerPushMatchmakingQueueInfo, function(p49, p50) --[[ Line: 130 ]]
                --[[ Upvalues: (copy 1): p_u_43, (ref 2): v_u_23, (ref 3): v_u_24, (ref 4): v_u_25, (ref 5): v_u_26 ]]
                p_u_43:update_time()
                v_u_23 = p49.GameId
                v_u_24 = p49.PlayerCount
                v_u_25 = p49.EnqueuedPlayerCount
                v_u_26 = p50
            end)
            l__evt_0:wait_on_event_once(v_u_6.EVT_GameLoad_ServerNotifyVotePickStart, function(p51) --[[ Line: 138 ]]
                --[[ Upvalues: (ref 1): l_PreJoin_0, (ref 2): v_u_12, (ref 3): v_u_5, (ref 4): v_u_29 ]]
                if l_PreJoin_0 ~= v_u_12.Mode.MatchmakingWaiting then
                    v_u_5:errf("EVT_GameLoad_ServerNotifyVotePickStart when mode(%d)", l_PreJoin_0)
                end;
                l_PreJoin_0 = v_u_12.Mode.DoVotepick
                v_u_29 = p51
            end)
            l__evt_0:wait_on_event_once(v_u_6.EVT_GameLoad_ServerNotifyClientDoPreload, function(p52, p53, p54, p55, p56, p57, p58) --[[ Line: 145 ]]
                --[[ Upvalues: (ref 1): l__evt_0, (ref 2): v_u_6, (ref 3): v_u_22, (ref 4): v_u_28, (ref 5): v_u_17, (ref 6): v_u_18, (ref 7): v_u_37, (ref 8): v_u_9, (ref 9): v_u_5, (ref 10): v_u_38, (ref 11): v_u_10, (ref 12): v_u_8, (ref 13): v_u_16, (ref 14): l_PreJoin_0, (ref 15): v_u_12, (ref 16): v_u_3 ]]
                l__evt_0:remove_waits_on(v_u_6.EVT_GameLoad_ServerNotifyVotePickStart)
                v_u_22 = p53
                v_u_28 = p56
                v_u_17 = p52
                v_u_18 = p55
                if p57 == nil then
                    v_u_5:warnf("EVT_GameLoad_ServerNotifyClientDoPreload game_note_skin_info_tab is nil")
                else
                    v_u_37 = v_u_9:from_table(p57)
                end;
                if p58 == nil then
                    v_u_5:warnf("EVT_GameLoad_ServerNotifyClientDoPreload game_dance_info_tab is nil")
                else
                    v_u_38 = v_u_10:from_table(p58)
                end;
                v_u_8:update_dict_from_matchmaking_info_table(v_u_16, p54)
                l_PreJoin_0 = v_u_12.Mode.ServerNotifyClientDoPreload
                if v_u_8:slot_from_player_info_table_for_id(p52, v_u_3:get_local_userid()) ~= p53 then
                    v_u_5:errf("EVT_GameLoad_ServerNotifyClientDoPreload slot_id(%s) does not match slot_from_player_info_table_for_id(%s)", v_u_3:num_string(p53), v_u_3:num_string(v_u_8:slot_from_player_info_table_for_id(p52, v_u_3:get_local_userid())))
                end;
            end)
            local function _(p_u_59) --[[ Name: make_sure_is_string ]] --[[ Line: 176 ]]
                --[[ Upvalues: (ref 1): v_u_3 ]]
                if typeof(p_u_59) == "string" then
                    return p_u_59;
                end;
                local v_u_60 = nil
                if typeof(p_u_59) == "table" then
                    pcall(function() --[[ Line: 180 ]]
                        --[[ Upvalues: (ref 1): v_u_60, (ref 2): v_u_3, (copy 3): p_u_59 ]]
                        v_u_60 = v_u_3:table_to_string(p_u_59)
                    end)
                end;
                if v_u_60 == nil then
                    v_u_60 = tostring(p_u_59)
                end;
                return v_u_60;
            end;
            l__evt_0:wait_on_event_once(v_u_6.EVT_GameLoad_MatchmakingV3_ServerJoinTargetPlayerError, function(p_u_61) --[[ Line: 190 ]]
                --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_43, (ref 3): l_PreJoin_0, (ref 4): v_u_12, (ref 5): v_u_32, (ref 6): v_u_3 ]]
                v_u_5:warnf("EVT_GameLoad_MatchmakingV3_ServerJoinTargetPlayerError error(%s)", p_u_61)
                p_u_43:remove_local_waits()
                l_PreJoin_0 = v_u_12.Mode.ServerJoinTargetPlayerError
                local v_u_62
                if typeof(p_u_61) == "string" then
                    v_u_62 = p_u_61
                else
                    v_u_62 = nil
                    if typeof(p_u_61) == "table" then
                        pcall(function() --[[ Line: 180 ]]
                            --[[ Upvalues: (ref 1): v_u_62, (ref 2): v_u_3, (copy 3): p_u_61 ]]
                            v_u_62 = v_u_3:table_to_string(p_u_61)
                        end)
                    end;
                    if v_u_62 == nil then
                        v_u_62 = tostring(p_u_61)
                    end;
                end;
                v_u_32 = v_u_62
            end)
            l__evt_0:wait_on_event(v_u_6.EVT_GameLoad_MatchmakingV3_ClientEnqueueErrorFromServer, function(p_u_63) --[[ Line: 198 ]]
                --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_43, (ref 3): l_PreJoin_0, (ref 4): v_u_12, (ref 5): v_u_32, (ref 6): v_u_3 ]]
                v_u_5:warnf("EVT_GameLoad_MatchmakingV3_ClientEnqueueErrorFromServer error(%s)", p_u_63)
                p_u_43:remove_local_waits()
                l_PreJoin_0 = v_u_12.Mode.ClientEnqueueErrorFromServer
                local v_u_64
                if typeof(p_u_63) == "string" then
                    v_u_64 = p_u_63
                else
                    v_u_64 = nil
                    if typeof(p_u_63) == "table" then
                        pcall(function() --[[ Line: 180 ]]
                            --[[ Upvalues: (ref 1): v_u_64, (ref 2): v_u_3, (copy 3): p_u_63 ]]
                            v_u_64 = v_u_3:table_to_string(p_u_63)
                        end)
                    end;
                    if v_u_64 == nil then
                        v_u_64 = tostring(p_u_63)
                    end;
                end;
                v_u_32 = v_u_64
            end)
            l__evt_0:wait_on_event_once(v_u_6.EVT_GameLoad_MatchmakingV3_ServerAcknowledgeClientLeaveMatch, function() --[[ Line: 206 ]]
                --[[ Upvalues: (ref 1): v_u_33, (copy 2): p_u_43, (ref 3): l_PreJoin_0, (ref 4): v_u_12 ]]
                for v65 = 1, v_u_33:count() do
                    v_u_33:get(v65)()
                end;
                v_u_33:clear()
                p_u_43:remove_local_waits()
                l_PreJoin_0 = v_u_12.Mode.PreJoin
            end)
        else
            v_u_5:warnf("GameJoinProtocol:mmv3_enqueue_player key not found(%s)", (tostring(p44)))
        end;
    end;
    v14.getc_server_join_target_player_error = function(_) --[[ Name: getc_server_join_target_player_error ]] --[[ Line: 216 ]]
        --[[ Upvalues: (ref 1): l_PreJoin_0, (ref 2): v_u_12, (ref 3): v_u_32 ]]
        if l_PreJoin_0 ~= v_u_12.Mode.ServerJoinTargetPlayerError then
            return false, "";
        end;
        l_PreJoin_0 = v_u_12.Mode.PreJoin
        return true, v_u_32;
    end;
    v14.getc_server_client_enqueue_error = function(_) --[[ Name: getc_server_client_enqueue_error ]] --[[ Line: 224 ]]
        --[[ Upvalues: (ref 1): l_PreJoin_0, (ref 2): v_u_12, (ref 3): v_u_32 ]]
        if l_PreJoin_0 ~= v_u_12.Mode.ClientEnqueueErrorFromServer then
            return false, "";
        end;
        l_PreJoin_0 = v_u_12.Mode.PreJoin
        return true, v_u_32;
    end;
    v14.mmv3_immediate_start_singleplayer_game = function(_, _) --[[ Name: mmv3_immediate_start_singleplayer_game ]] --[[ Line: 232 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        v_u_5:warnf("GameJoinProtocol:mmv3_immediate_start_singleplayer_game not implemented")
    end;
    v14.mmv3_enqueue_player = function(p66, p67, p68) --[[ Name: mmv3_enqueue_player ]] --[[ Line: 238 ]]
        --[[ Upvalues: (copy 1): l__evt_0, (ref 2): v_u_6 ]]
        p66:mmv3_join_matchmaking_shared(p67)
        l__evt_0:fire_event_to_server(v_u_6.EVT_GameLoad_MatchmakingV3_ClientEnqueue, p67, p68, p66:get_event_info())
    end;
    v14.mmv3_join_target_player = function(p69, p70, p71, p72) --[[ Name: mmv3_join_target_player ]] --[[ Line: 243 ]]
        --[[ Upvalues: (copy 1): l__evt_0, (ref 2): v_u_6 ]]
        p69:mmv3_join_matchmaking_shared(p70)
        l__evt_0:fire_event_to_server(v_u_6.EVT_GameLoad_MatchmakingV3_ClientJoinTargetPlayer, p71, p72, p69:get_event_info())
    end;
    v14.mmv3_get_gameid = function(_) --[[ Name: mmv3_get_gameid ]] --[[ Line: 248 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        return v_u_23;
    end;
    v14.mmv3_get_matchmaking_players_count = function(_) --[[ Name: mmv3_get_matchmaking_players_count ]] --[[ Line: 249 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24;
    end;
    v14.mmv3_get_matchmaking_queued_players_count = function(_) --[[ Name: mmv3_get_matchmaking_queued_players_count ]] --[[ Line: 250 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        return v_u_25;
    end;
    v14.mmv3_get_matchmaking_gameinstance_player_info = function(_) --[[ Name: mmv3_get_matchmaking_gameinstance_player_info ]] --[[ Line: 251 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26;
    end;
    v14.mmv3_local_update_settings = function(_, p_u_73) --[[ Name: mmv3_local_update_settings ]] --[[ Line: 253 ]]
        --[[ Upvalues: (copy 1): v_u_34, (copy 2): l__evt_0, (ref 3): v_u_6 ]]
        v_u_34:on_cooldown_last(1, function() --[[ Line: 254 ]]
            --[[ Upvalues: (ref 1): v_u_34, (ref 2): l__evt_0, (ref 3): v_u_6, (copy 4): p_u_73 ]]
            v_u_34:add_cooldown_to_id(1, 1)
            l__evt_0:fire_event_to_server(v_u_6.EVT_GameLoad_MatchmakingV3_ClientUpdateSettings, p_u_73)
        end)
    end;
    v14.mmv3_player_leave = function(p74, p_u_75) --[[ Name: mmv3_player_leave ]] --[[ Line: 260 ]]
        --[[ Upvalues: (ref 1): v_u_33, (copy 2): l__evt_0, (ref 3): v_u_6, (copy 4): p_u_13, (ref 5): v_u_5, (ref 6): v_u_4 ]]
        p74:set_event_info(nil)
        v_u_33:push_back(p_u_75)
        l__evt_0:fire_event_to_server(v_u_6.EVT_GameLoad_MatchmakingV3_ClientLeaveMatch)
        p_u_13._update_enqueue_fn:enqueue_function(function() --[[ Line: 265 ]]
            --[[ Upvalues: (ref 1): v_u_33, (copy 2): p_u_75, (ref 3): v_u_5 ]]
            if v_u_33:contains(p_u_75) then
                v_u_33:remove(p_u_75)
                v_u_5:warnf("GameJoinProtocol timed out waiting for EVT_GameLoad_MatchmakingV3_ServerAcknowledgeClientLeaveMatch")
                p_u_75()
            end;
        end, v_u_4:DeltaTimeToTimescale(4))
    end;
    v14.mmv3_local_is_ready = function(_) --[[ Name: mmv3_local_is_ready ]] --[[ Line: 274 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_3 ]]
        for v76 = 1, 4 do
            local v77 = v_u_16:get(v76)
            if v77 ~= nil and v77._id == v_u_3:get_local_userid() then
                return v77._ready;
            end;
        end;
        return false;
    end;
    v14.mmv3_fire_local_ready = function(_, p78) --[[ Name: mmv3_fire_local_ready ]] --[[ Line: 284 ]]
        --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_3, (copy 3): l__evt_0, (ref 4): v_u_6 ]]
        for v79 = 1, 4 do
            local v80 = v_u_16:get(v79)
            if v80 ~= nil and v80._id == v_u_3:get_local_userid() then
                v80._ready = true
            end;
        end;
        l__evt_0:fire_event_to_server(v_u_6.EVT_GameLoad_MatchmakingV3_ClientReady, p78)
    end;
    v14.get_slots = function(_) --[[ Name: get_slots ]] --[[ Line: 295 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        return v_u_16;
    end;
    v14.set_selected_song_key = function(_, p81) --[[ Name: set_selected_song_key ]] --[[ Line: 296 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        v_u_28 = p81
    end;
    v14.get_selected_song_key = function(_) --[[ Name: get_selected_song_key ]] --[[ Line: 297 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        return v_u_28;
    end;
    v14.notify_client_do_votepick = function(_) --[[ Name: notify_client_do_votepick ]] --[[ Line: 301 ]]
        --[[ Upvalues: (ref 1): l_PreJoin_0, (ref 2): v_u_12 ]]
        return l_PreJoin_0 == v_u_12.Mode.DoVotepick;
    end;
    v14.begin_votepick = function(_) --[[ Name: begin_votepick ]] --[[ Line: 305 ]]
        --[[ Upvalues: (ref 1): l_PreJoin_0, (ref 2): v_u_12, (ref 3): v_u_5 ]]
        if l_PreJoin_0 ~= v_u_12.Mode.DoVotepick then
            v_u_5:warnf("GameJoinProtocol:begin_votepick(%d) wrong mode", l_PreJoin_0)
        end;
        l_PreJoin_0 = v_u_12.Mode.Votepick
    end;
    v14.votepick_for_key = function(_, p82) --[[ Name: votepick_for_key ]] --[[ Line: 315 ]]
        --[[ Upvalues: (ref 1): l_PreJoin_0, (ref 2): v_u_12, (ref 3): v_u_5, (copy 4): l__evt_0, (ref 5): v_u_6 ]]
        if l_PreJoin_0 == v_u_12.Mode.Votepick then
            l__evt_0:fire_event_to_server(v_u_6.EVT_GameLoad_ClientNotifyVotePickSelect, p82)
            l_PreJoin_0 = v_u_12.Mode.HasVotepicked
        else
            v_u_5:warnf("GameJoinProtocol:votepick_for_key(%d) wrong mode", l_PreJoin_0)
        end;
    end;
    v14.get_votepick_items = function(_) --[[ Name: get_votepick_items ]] --[[ Line: 330 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29;
    end;
    v14.notify_client_do_preload = function(_) --[[ Name: notify_client_do_preload ]] --[[ Line: 336 ]]
        --[[ Upvalues: (ref 1): l_PreJoin_0, (ref 2): v_u_12 ]]
        return l_PreJoin_0 == v_u_12.Mode.ServerNotifyClientDoPreload;
    end;
    v14.begin_preload = function(p_u_83) --[[ Name: begin_preload ]] --[[ Line: 340 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): l_PreJoin_0, (ref 3): v_u_17, (ref 4): v_u_35, (copy 5): l__evt_0, (ref 6): v_u_6, (ref 7): v_u_30, (ref 8): v_u_31, (ref 9): v_u_23, (ref 10): v_u_12, (copy 11): p_u_13, (ref 12): v_u_28, (ref 13): v_u_22, (ref 14): v_u_18, (ref 15): v_u_36, (ref 16): v_u_37, (ref 17): v_u_38 ]]
        if p_u_83:notify_client_do_preload() == false then
            v_u_5:warnf("begin_preload during state(%d)", l_PreJoin_0)
        end;
        if v_u_17 == nil then
            v_u_5:warnf("GameJoinProtocol:begin_preload() _player_info is nil")
        end;
        if v_u_35 then
            l__evt_0:wait_on_event_once(v_u_6.EVT_GameLoad_ServerNotifyPreloadClientBooted, function(p84) --[[ Line: 349 ]]
                --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_31, (copy 3): p_u_83, (ref 4): v_u_5 ]]
                v_u_30 = true
                v_u_31 = p84
                p_u_83:remove_local_waits()
                v_u_5:puts("SPRemoteEvent.EVT_GameLoad_ServerNotifyPreloadClientBooted")
            end)
        end;
        l__evt_0:wait_on_event_once(v_u_6.EVT_GameLoad_ServerNotifyClientDoStart, function(p85) --[[ Line: 357 ]]
            --[[ Upvalues: (ref 1): v_u_23, (copy 2): p_u_83 ]]
            v_u_23 = p85
            p_u_83:set_mode_to_client_do_start()
        end)
        l_PreJoin_0 = v_u_12.Mode.Preloading
        p_u_13._lobby_join:save_camera_position()
        p_u_13._game_join:load_game(p_u_13, v_u_28, v_u_22, v_u_17, v_u_18, v_u_36, v_u_37, v_u_38, p_u_83:get_event_info())
        p_u_13._player_blob_manager:remove_recently_acquired_songid(v_u_28)
    end;
    v14.was_preload_booted = function(_) --[[ Name: was_preload_booted ]] --[[ Line: 381 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        return v_u_30;
    end;
    v14.get_preload_booted_message = function(_) --[[ Name: get_preload_booted_message ]] --[[ Line: 382 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        return v_u_31;
    end;
    v14.is_preload_finished = function(_) --[[ Name: is_preload_finished ]] --[[ Line: 383 ]]
        --[[ Upvalues: (copy 1): p_u_13 ]]
        local v86 = p_u_13._game_join:is_game_audio_loaded() and p_u_13._game_join:is_game_images_loaded()
        if v86 then
            v86 = p_u_13._game_join:is_game_stage_loaded()
        end;
        return v86;
    end;
    v14.trigger_load_retry = function(_) --[[ Name: trigger_load_retry ]] --[[ Line: 389 ]]
        --[[ Upvalues: (copy 1): p_u_13 ]]
        p_u_13._game_join:load_retry()
    end;
    v14.fire_preload_finished = function(p87) --[[ Name: fire_preload_finished ]] --[[ Line: 391 ]]
        --[[ Upvalues: (ref 1): l_PreJoin_0, (ref 2): v_u_12, (ref 3): v_u_5, (ref 4): v_u_35, (copy 5): l__evt_0, (ref 6): v_u_6 ]]
        if l_PreJoin_0 ~= v_u_12.Mode.Preloading then
            v_u_5:warnf("fire_preload_finished during state(%d)", l_PreJoin_0)
        end;
        if v_u_35 then
            l__evt_0:fire_event_to_server(v_u_6.EVT_GameLoad_ClientNotifyPreloadFinished)
        else
            p87:set_mode_to_client_do_start()
        end;
    end;
    v14.notify_client_do_start = function(_) --[[ Name: notify_client_do_start ]] --[[ Line: 402 ]]
        --[[ Upvalues: (ref 1): l_PreJoin_0, (ref 2): v_u_12 ]]
        return l_PreJoin_0 == v_u_12.Mode.ClientDoStart;
    end;
    v14.client_do_start = function(p88) --[[ Name: client_do_start ]] --[[ Line: 406 ]]
        --[[ Upvalues: (ref 1): l_PreJoin_0, (ref 2): v_u_12, (ref 3): v_u_5, (ref 4): v_u_35, (copy 5): p_u_13, (ref 6): v_u_6, (ref 7): v_u_23 ]]
        if l_PreJoin_0 == v_u_12.Mode.ClientDoStart then
            if v_u_35 then
                p_u_13._evt:fire_event_to_server(v_u_6.EVT_Lobby_ClientNotifyLeavingLobby)
            end;
            p88:remove_local_waits()
            p_u_13._lobby_join:teardown_lobby()
            p_u_13._game_join:start_game(v_u_23)
        else
            v_u_5:warnf("client_do_start during state(%d)", l_PreJoin_0)
        end;
    end;
    v14.remove_local_waits = function(_) --[[ Name: remove_local_waits ]] --[[ Line: 422 ]]
        --[[ Upvalues: (copy 1): l__evt_0, (ref 2): v_u_6 ]]
        l__evt_0:remove_waits_on(v_u_6.EVT_GameLoad_ServerUpdateMatchMakingInfo)
        l__evt_0:remove_waits_on(v_u_6.EVT_GameLoad_ServerNotifyVotePickStart)
        l__evt_0:remove_waits_on(v_u_6.EVT_GameLoad_ServerNotifyClientDoPreload)
        l__evt_0:remove_waits_on(v_u_6.EVT_GameLoad_ServerNotifyPreloadClientBooted)
        l__evt_0:remove_waits_on(v_u_6.EVT_GameLoad_ServerNotifyClientDoStart)
        l__evt_0:remove_waits_on(v_u_6.EVT_GameLoad_MatchmakingV3_ServerPushMatchmakingQueueInfo)
        l__evt_0:remove_waits_on(v_u_6.EVT_GameLoad_MatchmakingV3_ServerJoinTargetPlayerError)
        l__evt_0:remove_waits_on(v_u_6.EVT_GameLoad_MatchmakingV3_ServerAcknowledgeClientLeaveMatch)
        l__evt_0:remove_waits_on(v_u_6.EVT_GameLoad_MatchmakingV3_ClientEnqueueErrorFromServer)
    end;
    v14.update_time = function(_) --[[ Name: update_time ]] --[[ Line: 434 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        v_u_21 = tick()
    end;
    v14.last_updated_time = function(_) --[[ Name: last_updated_time ]] --[[ Line: 435 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        return v_u_21;
    end;
    v14.has_been_updated = function(_) --[[ Name: has_been_updated ]] --[[ Line: 436 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        return v_u_21 ~= -1;
    end;
    v14.set_slot = function(_, p89) --[[ Name: set_slot ]] --[[ Line: 438 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        v_u_22 = p89
    end;
    v14.get_slot = function(_) --[[ Name: get_slot ]] --[[ Line: 439 ]]
        --[[ Upvalues: (ref 1): v_u_22 ]]
        return v_u_22;
    end;
    local function _(p90, p91) --[[ Name: decrement_player_timeout ]] --[[ Line: 443 ]]
        --[[ Upvalues: (ref 1): v_u_4 ]]
        if p90._timeout > 0 then
            p90._timeout = math.max(p90._timeout - v_u_4:TimescaleToDeltaTime(p91) * 1000, 0)
        end;
    end;
    v14.update = function(p92, p93) --[[ Name: update ]] --[[ Line: 449 ]]
        --[[ Upvalues: (copy 1): v_u_34, (ref 2): l_PreJoin_0, (ref 3): v_u_12, (ref 4): v_u_27, (ref 5): v_u_4, (ref 6): v_u_16, (ref 7): v_u_35 ]]
        v_u_34:update(p93)
        if l_PreJoin_0 == v_u_12.Mode.MatchmakingWaiting then
            v_u_27 = v_u_27 + v_u_4:TimescaleToDeltaTime(p93) * 1000
        elseif l_PreJoin_0 == v_u_12.Mode.Preloading then
            for v94 = 1, 4 do
                if v_u_16:contains(v94) then
                    local v95 = v_u_16:get(v94)
                    if v95._loaded == false and v95._timeout > 0 then
                        v95._timeout = math.max(v95._timeout - v_u_4:TimescaleToDeltaTime(p93) * 1000, 0)
                    end;
                end;
            end;
            if v_u_35 ~= true and p92:is_all_players_timedout() == true then
                p92:set_mode_to_client_do_start()
            end;
        end;
    end;
    v14.is_all_players_timedout = function(_) --[[ Name: is_all_players_timedout ]] --[[ Line: 502 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        for v96 = 1, 4 do
            if v_u_16:contains(v96) and v_u_16:get(v96)._timeout > 0 then
                return false;
            end;
        end;
        return true;
    end;
    v14.set_mode_to_client_do_start = function(_) --[[ Name: set_mode_to_client_do_start ]] --[[ Line: 514 ]]
        --[[ Upvalues: (ref 1): l_PreJoin_0, (ref 2): v_u_12 ]]
        l_PreJoin_0 = v_u_12.Mode.ClientDoStart
    end;
    return v14;
end;
return v_u_12;
