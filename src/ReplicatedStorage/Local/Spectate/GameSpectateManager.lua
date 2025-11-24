-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:28 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_2 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_4 = require(game.ReplicatedStorage.Local.GameLocalMode)
local v_u_5 = require(game.ReplicatedStorage.Shared.NotePlaybackSequence)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_8 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.PowerBarState)
require(game.ReplicatedStorage.Lobby.Menus.GameEndV2UI)
local v_u_10 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_12 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_13 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_14 = {
    ["ScoreCheckpoint"] = {}
}
v_u_14.ScoreCheckpoint.new = function(_, p_u_15, p_u_16, p_u_17, p_u_18) --[[ Name: new ]] --[[ Line: 20 ]]
    local v19 = {}
    v19.get_index = function(_) --[[ Name: get_index ]] --[[ Line: 22 ]]
        --[[ Upvalues: (copy 1): p_u_15 ]]
        return p_u_15;
    end;
    v19.get_time_ms = function(_) --[[ Name: get_time_ms ]] --[[ Line: 23 ]]
        --[[ Upvalues: (copy 1): p_u_16 ]]
        return p_u_16;
    end;
    v19.get_score = function(_) --[[ Name: get_score ]] --[[ Line: 24 ]]
        --[[ Upvalues: (copy 1): p_u_17 ]]
        return p_u_17;
    end;
    v19.get_combo = function(_) --[[ Name: get_combo ]] --[[ Line: 25 ]]
        --[[ Upvalues: (copy 1): p_u_18 ]]
        return p_u_18;
    end;
    return v19;
end;
v_u_14.new = function(_, p_u_20, p_u_21, p_u_22, p_u_23) --[[ Name: new ]] --[[ Line: 29 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_11, (copy 3): v_u_5, (copy 4): v_u_7, (copy 5): v_u_3, (copy 6): v_u_12, (copy 7): v_u_9, (copy 8): v_u_1, (copy 9): v_u_14, (copy 10): v_u_4, (copy 11): v_u_13, (copy 12): v_u_6, (copy 13): v_u_8, (copy 14): v_u_10 ]]
    local v24 = {}
    local function _() --[[ Name: get_spectate_player_id ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_2, (ref 3): v_u_11 ]]
        local v25 = p_u_21._players._slots:get(p_u_21:get_local_game_slot())
        if v25 ~= nil then
            return v25._id, v25;
        end;
        v_u_2:warnf("Invalid GameSpectateManager:get_spectate_player_id")
        return v_u_11.PlayerIDInvalid;
    end;
    local v_u_26 = 0
    local v_u_27 = v_u_5:new()
    local v_u_28 = v_u_7:new()
    v24.get_score_index_checkpoints = function(_) --[[ Name: get_score_index_checkpoints ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        return v_u_28;
    end;
    v24.get_active_note_sequence = function(_) --[[ Name: get_active_note_sequence ]] --[[ Line: 47 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27;
    end;
    local l_SPECTATE_CHEER_COOLDOWN_MS_0 = v_u_3.SPECTATE_CHEER_COOLDOWN_MS
    local v_u_29 = v_u_12:get_selected_mode()
    local function f_sync_scoremanager_state_to_slot_tar_player(p30) --[[ Name: sync_scoremanager_state_to_slot_tar_player ]] --[[ Line: 53 ]]
        --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_9 ]]
        if p30 then
            local v31, v32 = p_u_21:es_gamelocal_get_scoremanager():get_score_objs()
            v31:es_playerscore_set_score(p30._score)
            v31:set_chain(p30._chain)
            v31:es_playerscore_set_powerbar_state(v_u_9:active_bool_to_state(p30._power_bar_active), p30._fever_percentage)
            v32:es_playerscore_set_score(p30._naked_score)
            v32:set_chain(p30._naked_chain)
            v32:es_playerscore_set_powerbar_state(v_u_9:active_bool_to_state(p30._naked_power_bar_active), p30._naked_fever_percentage)
        end;
    end;
    v24.start = function(p_u_33) --[[ Name: start ]] --[[ Line: 72 ]]
        --[[ Upvalues: (copy 1): p_u_21, (copy 2): v_u_29, (ref 3): v_u_12, (ref 4): v_u_1, (copy 5): p_u_23, (ref 6): v_u_2, (ref 7): v_u_27, (ref 8): v_u_28, (ref 9): v_u_14, (ref 10): v_u_5, (ref 11): v_u_26, (ref 12): v_u_3, (ref 13): v_u_4, (ref 14): l_SPECTATE_CHEER_COOLDOWN_MS_0, (copy 15): f_sync_scoremanager_state_to_slot_tar_player ]]
        local v34, _ = p_u_21:es_gamelocal_get_scoremanager():get_score_objs()
        v34:set_apply_hit_to_powerbar(false)
        if p_u_21._players._slots:contains(p_u_21:get_local_game_slot()) then
            local l__match_mode_0 = p_u_21._players._slots:get(p_u_21:get_local_game_slot())._match_mode
            if l__match_mode_0 ~= v_u_29 then
                v_u_12:set_selected_mode(l__match_mode_0)
            end;
        end;
        p_u_21._evt:clear_pending_on(v_u_1.EVT_Spectate_ServerPushInfo)
        p_u_21._evt:wait_on_event(v_u_1.EVT_Spectate_ServerPushInfo, function(p35, p36) --[[ Line: 87 ]]
            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_2, (ref 3): p_u_21, (ref 4): v_u_27, (ref 5): v_u_28, (ref 6): v_u_14, (ref 7): v_u_5, (ref 8): v_u_26, (ref 9): v_u_3, (ref 10): v_u_4, (ref 11): l_SPECTATE_CHEER_COOLDOWN_MS_0, (copy 12): p_u_33, (ref 13): f_sync_scoremanager_state_to_slot_tar_player ]]
            if p35 == p_u_23 then
                if p36.FocusedSlot == p_u_21:get_local_game_slot() then
                    local l_NoteSequences_0 = p36.NoteSequences
                    if #l_NoteSequences_0 == 0 then
                        return;
                    else
                        local v37 = v_u_27:get_events():count()
                        v_u_28:add(v37, v_u_14.ScoreCheckpoint:new(v37, v_u_27:get_time_end(), v_u_27:get_score_end(), v_u_27:get_combo_end()))
                        for v38 = 1, #l_NoteSequences_0 do
                            local v39 = v_u_5:deserialize_from_table(l_NoteSequences_0[v38], true)
                            if v_u_26 == 0 then
                                v_u_27:set_time_start(v39:get_time_start())
                                v_u_27:set_score_start(v39:get_score_start())
                                v_u_27:set_combo_start(v39:get_combo_start())
                                local v40, _ = p_u_21:es_gamelocal_get_scoremanager():get_score_objs()
                                v40:es_playerscore_set_score(v39:get_score_start())
                                v40:set_chain(v39:get_combo_start())
                            end;
                            v_u_27:append_notesequence(v39)
                            v_u_26 = v_u_26 + 1
                        end;
                        if v_u_26 >= v_u_3.SERVER_PLAYER_NOTE_SEQUENCE_QUEUE_SIZE then
                            if p_u_21:get_current_mode() ~= v_u_4.Spectate then
                                v_u_2:puts("EVT_Spectate_ServerPushInfo starting spectate")
                                l_SPECTATE_CHEER_COOLDOWN_MS_0 = p36.SpectateCooldownMS
                                p_u_33:start_playback()
                                f_sync_scoremanager_state_to_slot_tar_player((p_u_21._players._slots:get(p_u_21:get_local_game_slot())))
                            end;
                        end;
                    end;
                else
                    return;
                end;
            else
                return v_u_2:warnf("EVT_Spectate_ServerPushInfo ignored (gameid does not match)");
            end;
        end)
        p_u_21._evt:clear_pending_on(v_u_1.EVT_Game_ServerUpdatePlayerInfo)
        p_u_21._evt:wait_on_event(v_u_1.EVT_Game_ServerUpdatePlayerInfo, function(p41, p42, p43) --[[ Line: 145 ]]
            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_2, (copy 3): p_u_33 ]]
            if p41 == p_u_23 then
                p_u_33:enqueue_player_info_data_at_time(p42, p43)
            else
                v_u_2:warnf("EVT_Game_ServerUpdatePlayerInfo unexpected game_id got(%d) expected(%d)", p41, p_u_23)
            end;
        end)
    end;
    v24.start_playback = function(_) --[[ Name: start_playback ]] --[[ Line: 154 ]]
        --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_21, (ref 3): v_u_4, (ref 4): v_u_2, (ref 5): v_u_27 ]]
        v_u_13:singleton():get_data_for_key(p_u_21:es_gamelocal_get_audiomanager():get_song_key(), function() --[[ Line: 155 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_4, (ref 3): v_u_2, (ref 4): v_u_27 ]]
            if p_u_21:get_current_mode() == v_u_4.SpectateEnded then
                return v_u_2:warnf("SongDatabase get_data_for_key from GameSpectateManager:start_playback but GameLocalMode was SpectateEnded");
            end;
            p_u_21:set_current_mode(v_u_4.Spectate)
            p_u_21:set_skip_to_time_ms(v_u_27:get_time_start())
        end)
    end;
    local v_u_44 = v_u_6:new()
    v24.enqueue_player_info_data_at_time = function(_, p45, p46) --[[ Name: enqueue_player_info_data_at_time ]] --[[ Line: 167 ]]
        --[[ Upvalues: (copy 1): v_u_44 ]]
        v_u_44:push_back({
            ["TimeMS"] = p46,
            ["PlayerInfo"] = p45
        })
    end;
    v24.update = function(p47, p48) --[[ Name: update ]] --[[ Line: 174 ]]
        --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_4, (copy 3): v_u_44 ]]
        if p_u_21:get_current_mode() == v_u_4.Spectate then
            local v49, _ = p_u_21:es_gamelocal_get_scoremanager():get_score_objs()
            v49:update(p48, false, false)
            if v_u_44:count() > 0 then
                local v50 = v_u_44:get(1)
                local l_TimeMS_0 = v50.TimeMS
                local l_PlayerInfo_0 = v50.PlayerInfo
                if l_TimeMS_0 <= p_u_21:es_gamelocal_get_audiomanager():get_song_time_position_ms() then
                    p_u_21._players:update_from_player_info_data(p_u_21, l_PlayerInfo_0, true)
                    v_u_44:remove_at(1)
                    if p_u_21._players._slots:contains(p_u_21:get_local_game_slot()) ~= true then
                        p47:focused_player_left_switch_any_slot()
                    end;
                end;
            end;
            if p_u_21:get_current_mode() == v_u_4.Spectate then
                local v51 = false
                for _, v52 in p_u_21._players._slots:key_itr() do
                    if v52._finished == false then
                        v51 = true
                    end;
                end;
                if v51 == false then
                    p47:just_finished()
                end;
            end;
        end;
        p47:update_cheer(p48)
    end;
    v24.focused_player_left_switch_any_slot = function(p53) --[[ Name: focused_player_left_switch_any_slot ]] --[[ Line: 208 ]]
        --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_2 ]]
        local v54 = nil
        for v55 = 1, 4 do
            if p_u_21._players._slots:contains(v55) then
                v54 = v55
                break;
            end;
        end;
        if v54 == nil then
            v_u_2:warnf("GameSpectateManager:focused_player_left_switch_any_slot tar nil")
            p53:spectate_leave()
        else
            p53:switch_to_focus_slot(v54)
        end;
    end;
    v24.switch_to_focus_slot = function(_, p56) --[[ Name: switch_to_focus_slot ]] --[[ Line: 225 ]]
        --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_2, (ref 3): v_u_12, (copy 4): f_sync_scoremanager_state_to_slot_tar_player, (ref 5): v_u_26, (ref 6): v_u_27, (ref 7): v_u_5, (ref 8): v_u_28, (ref 9): v_u_7, (ref 10): v_u_1 ]]
        if p_u_21._players._slots:contains(p56) == true then
            local v57 = p_u_21._players._slots:get(p56)
            local l__match_mode_1 = v57._match_mode
            if l__match_mode_1 ~= v_u_12:get_selected_mode() then
                v_u_12:set_selected_mode(l__match_mode_1)
            end;
            local v58 = p_u_21:get_local_game_slot()
            p_u_21:set_local_game_slot(p56)
            p_u_21._camera_manager:focus_camera_on_game_slot(p56)
            p_u_21._world_effect_manager:on_switch_focus_slot(p_u_21)
            f_sync_scoremanager_state_to_slot_tar_player(v57)
            v_u_26 = 0
            v_u_27 = v_u_5:new()
            v_u_28 = v_u_7:new()
            local v59 = v58 ~= p56 and p_u_21:es_gamelocal_get_tracksystems():get(v58)
            if v59 then
                v59:on_switch_unfocus_slot()
            end;
            local v60 = p_u_21:es_gamelocal_get_tracksystems():get(p56)
            if v60 then
                v60:on_switch_focus_slot()
            end;
            p_u_21._ui_manager:get_decal_ui_manager():calculate_screen_constants()
            p_u_21._ui_manager._power_bar:update_particle_emitter_params_to_selected_slot()
            p_u_21._evt:fire_event_to_server(v_u_1.EVT_Spectate_ClientSwitchFocusedPlayer, v57._id)
        else
            v_u_2:warnf("GameSpectateManager:switch_to_focus_slot(%d) _players._slots does not contain", p56)
        end;
    end;
    v24.set_ui_status_text = function(_, p61) --[[ Name: set_ui_status_text ]] --[[ Line: 269 ]]
        --[[ Upvalues: (copy 1): p_u_22 ]]
        p_u_22:set_status_text(p61)
    end;
    local function f_wait_for_spectate_cheer_reward_apply_and_sync(p_u_62) --[[ Name: wait_for_spectate_cheer_reward_apply_and_sync ]] --[[ Line: 273 ]]
        --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_20, (copy 3): p_u_21, (ref 4): v_u_1, (ref 5): v_u_8 ]]
        v_u_2:puts("GameSpectateManager:wait_for_spectate_cheer_reward_apply_and_sync")
        local function v_u_63() --[[ Line: 276 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_20, (copy 3): p_u_62 ]]
            v_u_2:puts("EVT_Spectate_ServerAppliedSpectatorCheerReward")
            p_u_20._player_blob_manager:do_sync(function() --[[ Line: 278 ]]
                --[[ Upvalues: (ref 1): p_u_62 ]]
                p_u_62()
            end)
        end;
        p_u_21._evt:clear_pending_on(v_u_1.EVT_Spectate_ServerAppliedSpectatorCheerReward)
        p_u_21._evt:wait_on_event_once(v_u_1.EVT_Spectate_ServerAppliedSpectatorCheerReward, function() --[[ Line: 284 ]]
            --[[ Upvalues: (ref 1): v_u_63 ]]
            if v_u_63 then
                v_u_63()
                v_u_63 = nil
            end;
        end)
        p_u_21._evt:fire_event_to_server(v_u_1.EVT_Spectate_ClientRequestApplySpectatorCheerReward)
        p_u_20._update_enqueue_fn:enqueue_function(function() --[[ Line: 292 ]]
            --[[ Upvalues: (ref 1): v_u_63, (ref 2): v_u_2 ]]
            if v_u_63 then
                v_u_2:warnf("GameSpectateManager:wait_for_spectate_cheer_reward_apply_and_sync timed out")
                v_u_63()
                v_u_63 = nil
            end;
        end, v_u_8:DeltaTimeToTimescale(4))
    end;
    v24.spectate_leave = function(p64) --[[ Name: spectate_leave ]] --[[ Line: 301 ]]
        --[[ Upvalues: (copy 1): p_u_21, (copy 2): p_u_22, (copy 3): f_wait_for_spectate_cheer_reward_apply_and_sync, (ref 4): v_u_1 ]]
        p64:teardown()
        p_u_21._menus:remove_menu(p_u_22)
        f_wait_for_spectate_cheer_reward_apply_and_sync(function() --[[ Line: 304 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_1 ]]
            p_u_21._evt:fire_event_to_server(v_u_1.EVT_Spectate_ClientLeave)
            p_u_21:exit_to_lobby()
        end)
    end;
    v24.just_finished = function(p65) --[[ Name: just_finished ]] --[[ Line: 310 ]]
        --[[ Upvalues: (ref 1): v_u_2, (copy 2): f_wait_for_spectate_cheer_reward_apply_and_sync, (copy 3): p_u_21, (copy 4): p_u_22, (ref 5): v_u_1, (ref 6): v_u_10, (copy 7): p_u_20, (ref 8): v_u_8 ]]
        v_u_2:puts("GameSpectateManager:just_finished")
        local v_u_66 = 0
        local v_u_67 = 0
        local v_u_69 = f_wait_for_spectate_cheer_reward_apply_and_sync(function() --[[ Line: 315 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_66, (ref 3): v_u_67 ]]
            p_u_21:load_game_end_menu(function(p68) --[[ Line: 316 ]]
                --[[ Upvalues: (ref 1): v_u_66, (ref 2): v_u_67 ]]
                p68:spectate_update_rewards_and_show(v_u_66, v_u_67)
            end)
        end)
        p65:teardown()
        p_u_21._menus:remove_menu(p_u_22)
        p_u_21._evt:clear_pending_on(v_u_1.EVT_Spectate_ServerResponseClientFinished)
        p_u_21._evt:wait_on_event_once(v_u_1.EVT_Spectate_ServerResponseClientFinished, function(p70) --[[ Line: 324 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): p_u_21, (ref 3): v_u_66, (ref 4): v_u_67, (ref 5): v_u_69 ]]
            v_u_10:is_table(p70.PlayerInfoData)
            v_u_10:is_int(p70.CheerCount)
            v_u_10:is_int(p70.CheerCoinReward)
            p_u_21._players:update_from_player_info_data(p_u_21, p70.PlayerInfoData, false)
            v_u_66 = p70.CheerCount
            v_u_67 = p70.CheerCoinReward
            if v_u_69 then
                v_u_69()
                v_u_69 = nil
            end;
        end)
        p_u_21._evt:fire_event_to_server(v_u_1.EVT_Spectate_ClientFinished)
        p_u_20._update_enqueue_fn:enqueue_function(function() --[[ Line: 339 ]]
            --[[ Upvalues: (ref 1): v_u_69, (ref 2): v_u_2 ]]
            if v_u_69 then
                v_u_2:warnf("GameSpectateManager:just_finished timed out")
                v_u_69()
                v_u_69 = nil
            end;
        end, v_u_8:DeltaTimeToTimescale(4))
    end;
    v24.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 348 ]]
        --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_29, (copy 3): p_u_21, (ref 4): v_u_4, (ref 5): v_u_1 ]]
        if v_u_12:get_selected_mode() ~= v_u_29 then
            v_u_12:set_selected_mode(v_u_29)
        end;
        p_u_21:set_current_mode(v_u_4.SpectateEnded)
        p_u_21._evt:remove_waits_on(v_u_1.EVT_Spectate_ServerPushInfo)
        p_u_21._evt:remove_waits_on(v_u_1.EVT_Game_ServerUpdatePlayerInfo)
    end;
    v24.cheer_focused_slot = function(p71, p_u_72) --[[ Name: cheer_focused_slot ]] --[[ Line: 358 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): l_SPECTATE_CHEER_COOLDOWN_MS_0, (ref 3): v_u_3, (copy 4): p_u_21, (ref 5): v_u_11, (ref 6): v_u_1 ]]
        if p71:can_cheer() == true then
            l_SPECTATE_CHEER_COOLDOWN_MS_0 = v_u_3.SPECTATE_CHEER_COOLDOWN_MS
            local v_u_73 = p_u_21._players._slots:get(p_u_21:get_local_game_slot())
            local v74
            if v_u_73 == nil then
                v_u_2:warnf("Invalid GameSpectateManager:get_spectate_player_id")
                v74 = v_u_11.PlayerIDInvalid
                v_u_73 = nil
            else
                v74 = v_u_73._id
            end;
            if v74 == v_u_11.PlayerIDInvalid then
                v_u_2:warnf("cheer_focused_slot focused_playerid(%s)", (tostring(v74)))
            else
                p_u_21._evt:clear_pending_on(v_u_1.EVT_Spectate_ServerResponseCheerPlayerId)
                p_u_21._evt:wait_on_event_once(v_u_1.EVT_Spectate_ServerResponseCheerPlayerId, function(p75, p76) --[[ Line: 368 ]]
                    --[[ Upvalues: (copy 1): v_u_73, (copy 2): p_u_72, (ref 3): v_u_2 ]]
                    if p75 then
                        v_u_73._like_count = p76
                        p_u_72(p75)
                    else
                        v_u_2:warnf("EVT_Spectate_ServerResponseCheerPlayerId success false")
                    end;
                end)
                p_u_21._evt:fire_event_to_server(v_u_1.EVT_Spectate_ClientCheerPlayerId, v74)
            end;
        else
            v_u_2:warnf("GameSpectateManager:can_cheer _local_cheer_cooldown(%.2f)", l_SPECTATE_CHEER_COOLDOWN_MS_0)
            return;
        end;
    end;
    v24.can_cheer = function(_) --[[ Name: can_cheer ]] --[[ Line: 382 ]]
        --[[ Upvalues: (ref 1): l_SPECTATE_CHEER_COOLDOWN_MS_0 ]]
        return l_SPECTATE_CHEER_COOLDOWN_MS_0 <= 0, l_SPECTATE_CHEER_COOLDOWN_MS_0;
    end;
    v24.update_cheer = function(_, p77) --[[ Name: update_cheer ]] --[[ Line: 386 ]]
        --[[ Upvalues: (ref 1): l_SPECTATE_CHEER_COOLDOWN_MS_0, (ref 2): v_u_8, (ref 3): v_u_3 ]]
        l_SPECTATE_CHEER_COOLDOWN_MS_0 = v_u_8:IncrementClamp(l_SPECTATE_CHEER_COOLDOWN_MS_0, -v_u_8:TimescaleToDeltaTime(p77) * 1000, 0, v_u_3.SPECTATE_CHEER_COOLDOWN_MS)
    end;
    return v24;
end;
return v_u_14;
