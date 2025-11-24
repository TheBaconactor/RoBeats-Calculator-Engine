-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:14 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Local.AudioManager)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Local.ObjectPool)
local v_u_7 = require(game.ReplicatedStorage.Local.ScoreManager)
local v_u_8 = require(game.ReplicatedStorage.Local.TrackSystem)
local v_u_9 = require(game.ReplicatedStorage.Effects.EffectSystem)
local v_u_10 = require(game.ReplicatedStorage.Shared.GameSlot)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_11 = require(game.ReplicatedStorage.Local.RemoteInstancePlayerInfoManager)
local v_u_12 = require(game.ReplicatedStorage.Local.WorldEffectManager)
local v_u_13 = require(game.ReplicatedStorage.Local.LocalCharacterManager)
local v_u_14 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_15 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_16 = require(game.ReplicatedStorage.Avatar.GearStats)
local v17 = require(game.ReplicatedStorage.Local.GameLocalMode)
local v_u_18 = require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.Constants)
local v_u_19 = require(game.ReplicatedStorage.Local.GameCameraManager)
local v_u_20 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_21 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
require(game.ReplicatedStorage.Local.Spectate.NoteSequencePlayer)
local v_u_22 = require(game.ReplicatedStorage.Shared.GameDanceInfo)
require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_23 = require(game.ReplicatedStorage.LocalShared.GameLagDelaySync)
local v_u_24 = require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Shared.AudioRank)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.LocalShared.BGMManager)
local v_u_25 = require(game.ReplicatedStorage.EditorGame.Game.EditorGameLocalUIManager)
local v_u_26 = require(game.ReplicatedStorage.EditorGame.Game.EditorGameEndUI)
local v_u_27 = {
    ["Mode"] = v17
}
v_u_27.new = function(_, p_u_28, p_u_29, p_u_30, p_u_31, p_u_32) --[[ Name: new ]] --[[ Line: 41 ]]
    --[[ Upvalues: (copy 1): v_u_25, (copy 2): v_u_11, (copy 3): v_u_12, (copy 4): v_u_9, (copy 5): v_u_13, (copy 6): v_u_19, (copy 7): v_u_24, (copy 8): v_u_3, (copy 9): v_u_5, (copy 10): v_u_7, (copy 11): v_u_27, (copy 12): v_u_4, (copy 13): v_u_18, (copy 14): v_u_21, (copy 15): v_u_22, (copy 16): v_u_14, (copy 17): v_u_20, (copy 18): v_u_10, (copy 19): v_u_16, (copy 20): v_u_8, (copy 21): v_u_6, (copy 22): v_u_26, (copy 23): v_u_2, (copy 24): v_u_23, (copy 25): v_u_15, (copy 26): v_u_1 ]]
    local v_u_33 = p_u_28:local_services_copy()
    v_u_33._ui_manager = v_u_25:new(p_u_28._spui)
    v_u_33._players = v_u_11:new()
    v_u_33._world_effect_manager = v_u_12:new()
    v_u_33._effects = v_u_9:new()
    v_u_33._characters = v_u_13:new(v_u_33)
    v_u_33._camera_manager = v_u_19:new(v_u_33)
    local l_Casual_0 = v_u_24.Casual
    local function _() --[[ Name: cons ]] --[[ Line: 53 ]]
        --[[ Upvalues: (ref 1): l_Casual_0, (ref 2): v_u_24, (copy 3): v_u_33 ]]
        l_Casual_0 = v_u_24:get_selected_mode()
        v_u_24:set_selected_mode(v_u_24.Casual)
        v_u_33._ui_manager:init(v_u_33)
    end;
    local v_u_34 = v_u_33
    local v_u_35 = 0
    local v_u_36 = nil
    v_u_33.set_local_game_slot = function(_, p37) --[[ Name: set_local_game_slot ]] --[[ Line: 63 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        v_u_35 = p37
    end;
    local v_u_38 = v_u_3:new()
    local v_u_39 = v_u_5:new(v_u_34)
    local v_u_40 = v_u_7:new(v_u_34)
    v_u_33.es_gamelocal_get_tracksystems = function(_) --[[ Name: es_gamelocal_get_tracksystems ]] --[[ Line: 69 ]]
        --[[ Upvalues: (copy 1): v_u_38 ]]
        return v_u_38;
    end;
    v_u_33.es_gamelocal_get_audiomanager = function(_) --[[ Name: es_gamelocal_get_audiomanager ]] --[[ Line: 72 ]]
        --[[ Upvalues: (copy 1): v_u_39 ]]
        return v_u_39;
    end;
    v_u_33.es_gamelocal_get_scoremanager = function(_) --[[ Name: es_gamelocal_get_scoremanager ]] --[[ Line: 75 ]]
        --[[ Upvalues: (copy 1): v_u_40 ]]
        return v_u_40;
    end;
    v_u_33.es_gamelocal_get_worldeffectmanager = function(p41) --[[ Name: es_gamelocal_get_worldeffectmanager ]] --[[ Line: 78 ]]
        return p41._world_effect_manager;
    end;
    v_u_33.get_local_services = function(_) --[[ Name: get_local_services ]] --[[ Line: 81 ]]
        --[[ Upvalues: (copy 1): p_u_28 ]]
        return p_u_28;
    end;
    local l_Setup_0 = v_u_27.Mode.Setup
    v_u_33.get_current_mode = function(_) --[[ Name: get_current_mode ]] --[[ Line: 86 ]]
        --[[ Upvalues: (ref 1): l_Setup_0 ]]
        return l_Setup_0;
    end;
    v_u_33.set_current_mode = function(_, p42) --[[ Name: set_current_mode ]] --[[ Line: 87 ]]
        --[[ Upvalues: (ref 1): l_Setup_0 ]]
        l_Setup_0 = p42
    end;
    v_u_33.set_as_tutorial = function(_) end;
    v_u_33.is_tutorial = function(_) --[[ Name: is_tutorial ]] --[[ Line: 90 ]]
        return false;
    end;
    v_u_33.is_networked = function(_) --[[ Name: is_networked ]] --[[ Line: 91 ]]
        return false;
    end;
    v_u_33.get_spectate_manager = function(_) --[[ Name: get_spectate_manager ]] --[[ Line: 93 ]]
        return nil;
    end;
    v_u_33.set_as_spectate = function(_) end;
    v_u_33.is_spectate = function(_) --[[ Name: is_spectate ]] --[[ Line: 95 ]]
        return false;
    end;
    v_u_33.is_preview_game = function(_) --[[ Name: is_preview_game ]] --[[ Line: 96 ]]
        return false;
    end;
    v_u_33.show_fullscreen_mobile_ui = function(p43) --[[ Name: show_fullscreen_mobile_ui ]] --[[ Line: 98 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_34, (ref 3): v_u_18 ]]
        local v44 = v_u_4:is_mobile()
        if v44 then
            if p43:is_spectate() == true then
                v44 = false
            else
                v44 = v_u_34._player_settings_manager:get_key(v_u_18.Key.MobileFullScreenUI) == true
            end;
        end;
        return v44;
    end;
    local v_u_45 = v_u_21:new()
    v_u_33.get_game_note_skin_info = function(_) --[[ Name: get_game_note_skin_info ]] --[[ Line: 103 ]]
        --[[ Upvalues: (ref 1): v_u_45 ]]
        return v_u_45;
    end;
    local v_u_46 = v_u_22:get_default_dance_info()
    v_u_33.get_game_dance_info = function(_) --[[ Name: get_game_dance_info ]] --[[ Line: 106 ]]
        --[[ Upvalues: (ref 1): v_u_46 ]]
        return v_u_46;
    end;
    local v_u_47 = nil
    v_u_33.set_event_info = function(_, p48) --[[ Name: set_event_info ]] --[[ Line: 109 ]]
        --[[ Upvalues: (ref 1): v_u_47 ]]
        v_u_47 = p48
    end;
    v_u_33.get_event_info = function(_) --[[ Name: get_event_info ]] --[[ Line: 110 ]]
        --[[ Upvalues: (ref 1): v_u_47 ]]
        return v_u_47;
    end;
    v_u_33.get_game_environment_center = function(_) --[[ Name: get_game_environment_center ]] --[[ Line: 112 ]]
        --[[ Upvalues: (copy 1): p_u_29 ]]
        return p_u_29.p;
    end;
    local v_u_49 = false
    v_u_33.setup_world = function(p_u_50, p_u_51, p52, p_u_53, p54, p55) --[[ Name: setup_world ]] --[[ Line: 117 ]]
        --[[ Upvalues: (ref 1): v_u_49, (ref 2): v_u_14, (ref 3): v_u_20, (ref 4): v_u_21, (ref 5): v_u_22, (ref 6): v_u_35, (ref 7): v_u_45, (ref 8): v_u_46, (ref 9): v_u_10, (ref 10): v_u_16, (ref 11): v_u_34, (copy 12): p_u_31, (ref 13): l_Setup_0, (ref 14): v_u_27, (ref 15): v_u_36, (ref 16): v_u_8, (copy 17): v_u_38 ]]
        if v_u_49 == true then
            return v_u_14:warn("EditorGameLocal:setup_world _has_game_setup_world == true");
        end;
        v_u_49 = true
        v_u_20:is_true(p54.Type == v_u_21.Type)
        v_u_20:is_true(p55.Type == v_u_22.Type)
        v_u_35 = p_u_51
        v_u_45 = p54
        v_u_46 = p55
        v_u_10:set_world_center_position(p_u_50:get_game_environment_center())
        local v_u_56 = nil
        pcall(function() --[[ Line: 132 ]]
            --[[ Upvalues: (ref 1): v_u_56, (copy 2): p_u_53, (copy 3): p_u_51 ]]
            v_u_56 = p_u_53[p_u_51].GearStats
        end)
        if v_u_56 == nil then
            v_u_56 = v_u_16:statsdict_base()
        end;
        v_u_34:es_gamelocal_get_scoremanager():initialize_localplayer(v_u_34, v_u_56)
        p_u_50._players:update_from_player_info_data(v_u_34, p52, false)
        p_u_50._players:update_from_gear_info(v_u_34, p_u_53)
        p_u_50:es_gamelocal_get_scoremanager():set_should_local_register_hit_apply_to_powerbar(false)
        p_u_50:es_gamelocal_get_scoremanager():set_fn_override_create_note_result_popup(function(p57, p58, _, p59, p60, _, _, _, _, _, _) --[[ Line: 144 ]]
            --[[ Upvalues: (copy 1): p_u_50 ]]
            p_u_50:es_gamelocal_get_scoremanager():create_note_result_popup(p57, p58, p_u_50:get_local_game_slot(), p59, p60, 0, 0, false, 0, 0, 0)
        end)
        local v61, v62 = p_u_50:es_gamelocal_get_scoremanager():get_score_objs()
        v61:set_chain_break_gear_stats_behaviour(false)
        v62:set_chain_break_gear_stats_behaviour(false)
        v61:set_song_key_hit_count(p_u_31:get_hit_count())
        v62:set_song_key_hit_count(p_u_31:get_hit_count())
        local function f_post_stage_load_setup_world() --[[ Name: post_stage_load_setup_world ]] --[[ Line: 179 ]]
            --[[ Upvalues: (ref 1): l_Setup_0, (ref 2): v_u_27, (ref 3): v_u_14, (ref 4): v_u_34, (copy 5): p_u_50, (ref 6): v_u_36, (ref 7): v_u_8, (ref 8): v_u_35, (ref 9): v_u_45, (ref 10): v_u_38 ]]
            if l_Setup_0 == v_u_27.Mode.DoRemove then
                return v_u_14:warnf("EditorGameLocal:setup_world post_stage_load_setup_world _current_mode is DoRemove");
            end;
            v_u_34._camera_manager:camera_setup_world()
            p_u_50._characters:create_local_characters(v_u_34)
            p_u_50._ui_manager:initialize_ui(v_u_34)
            v_u_36 = v_u_8:new(v_u_34, v_u_35)
            v_u_36:set_game_noteskin_info(v_u_45, v_u_35)
            v_u_36:init()
            v_u_38:add(v_u_35, v_u_36)
        end;
        p_u_50._world_effect_manager:load_game_stage_info(v_u_34, function() --[[ Line: 192 ]]
            --[[ Upvalues: (copy 1): f_post_stage_load_setup_world ]]
            f_post_stage_load_setup_world()
        end)
    end;
    local v_u_63 = false
    v_u_33.start_game = function(_, _) --[[ Name: start_game ]] --[[ Line: 198 ]]
        --[[ Upvalues: (ref 1): v_u_63, (ref 2): v_u_14, (ref 3): v_u_34, (ref 4): l_Setup_0, (ref 5): v_u_27, (ref 6): v_u_6 ]]
        if v_u_63 == true then
            return v_u_14:warn("EditorGameLocal:start_game _has_game_started == true");
        end;
        v_u_63 = true
        v_u_34._ui_manager:get_decal_ui_manager():calculate_screen_constants()
        v_u_34:es_gamelocal_get_audiomanager():start_play()
        l_Setup_0 = v_u_27.Mode.Game
        v_u_34._sfx_manager:play_sfx(v_u_6.SFX_STARTCHEER_1)
    end;
    v_u_33.end_game = function(_) --[[ Name: end_game ]] --[[ Line: 211 ]]
        --[[ Upvalues: (ref 1): l_Setup_0, (ref 2): v_u_27 ]]
        l_Setup_0 = v_u_27.Mode.LocalEarlyQuitWaitingForServerNotifyDoEnd
    end;
    v_u_33.early_quit = function(p64) --[[ Name: early_quit ]] --[[ Line: 216 ]]
        p64:end_game()
    end;
    local v_u_65 = false
    v_u_33.create_game_end_ui = function(_) --[[ Name: create_game_end_ui ]] --[[ Line: 221 ]]
        --[[ Upvalues: (ref 1): v_u_65, (ref 2): v_u_34, (ref 3): v_u_6, (ref 4): v_u_26, (copy 5): p_u_30, (copy 6): p_u_31, (copy 7): p_u_32, (copy 8): p_u_28 ]]
        if v_u_65 ~= true then
            v_u_34._ui_manager:teardown(v_u_34)
            v_u_34._sfx_manager:play_sfx(v_u_6.SFX_ENDCHEER_1)
            v_u_34._sfx_manager:play_sfx(v_u_6.SFX_FANFARE)
            v_u_34:es_gamelocal_get_audiomanager():get_bgm():Stop()
            v_u_26:load_game_end_ui(v_u_34, p_u_30, p_u_31, p_u_32)
            v_u_65 = true
            p_u_28._chat:set_chat_visible(p_u_28._chat:get_stored_chat_visible())
        end;
    end;
    v_u_33.get_local_game_slot = function(_) --[[ Name: get_local_game_slot ]] --[[ Line: 235 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        return v_u_35;
    end;
    v_u_33.es_gamelocal_tracksystem_of_index = function(_, p66) --[[ Name: es_gamelocal_tracksystem_of_index ]] --[[ Line: 238 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        return v_u_34:es_gamelocal_get_tracksystems():get(p66);
    end;
    v_u_33.es_gamelocal_get_local_tracksystem = function(_) --[[ Name: es_gamelocal_get_local_tracksystem ]] --[[ Line: 241 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        return v_u_34:es_gamelocal_tracksystem_of_index(v_u_34:get_local_game_slot());
    end;
    local v_u_67 = {
        [v_u_2.KEY_TRACK1] = 1,
        [v_u_2.KEY_TRACK2] = 2,
        [v_u_2.KEY_TRACK3] = 3,
        [v_u_2.KEY_TRACK4] = 4
    }
    local v_u_68 = 0
    v_u_33.get_frame_count = function(_) --[[ Name: get_frame_count ]] --[[ Line: 253 ]]
        --[[ Upvalues: (ref 1): v_u_68 ]]
        return v_u_68;
    end;
    local v_u_69 = 9999
    v_u_33.get_time_since_any_pressed = function(_) --[[ Name: get_time_since_any_pressed ]] --[[ Line: 258 ]]
        --[[ Upvalues: (ref 1): v_u_69 ]]
        return v_u_69;
    end;
    local v_u_70 = false
    local v_u_71 = v_u_23:new()
    v_u_33.update = function(p72, p73) --[[ Name: update ]] --[[ Line: 266 ]]
        --[[ Upvalues: (ref 1): v_u_68, (ref 2): l_Setup_0, (ref 3): v_u_27, (ref 4): v_u_4, (ref 5): v_u_34, (ref 6): v_u_10, (ref 7): v_u_15, (copy 8): v_u_71, (ref 9): v_u_70, (ref 10): v_u_36, (copy 11): v_u_67, (ref 12): v_u_69, (ref 13): v_u_1 ]]
        v_u_68 = v_u_68 + 1
        if l_Setup_0 ~= v_u_27.Mode.DoRemove then
            v_u_4:profilebegin("GameLocal:Update")
            v_u_34._camera_manager:update(p73)
            for v74, v75 in v_u_34:es_gamelocal_get_tracksystems():key_itr() do
                if v_u_34._players._slots:contains(v74) == false then
                    v75:es_teardown()
                    v_u_34:es_gamelocal_get_tracksystems():remove(v74)
                end;
            end;
            v_u_10:set_world_center_position(p72:get_game_environment_center())
            local v76
            if v_u_15.DoGameLagDelaySync == true and l_Setup_0 == v_u_27.Mode.Game then
                v76 = v_u_71:update_game_lag_delay_sync(v_u_34, p73)
            else
                v76 = false
            end;
            local v77 = false
            if v76 ~= true and l_Setup_0 ~= v_u_27.Mode.Setup then
                if l_Setup_0 == v_u_27.Mode.Game then
                    v_u_4:profilebegin("audio_manager update")
                    v_u_34:es_gamelocal_get_audiomanager():update(p73, v_u_34)
                    v_u_4:profileend()
                    v_u_4:profilebegin("_game._tracksystems update")
                    for _, v78 in v_u_34:es_gamelocal_get_tracksystems():key_itr() do
                        v78:es_update(p73, v_u_34)
                    end;
                    v_u_4:profileend()
                    v_u_4:profilebegin("_game._input control update")
                    if v_u_34._ui_manager:is_ui_enabled() then
                        if v_u_70 == true then
                            v_u_70 = false
                            v_u_36:set_force_update_auto_player(true)
                        end;
                    elseif v_u_70 ~= true then
                        v_u_70 = true
                        v_u_36:set_force_update_auto_player(false)
                    end;
                    if v_u_70 == true then
                        for v79, v80 in pairs(v_u_67) do
                            v77 = v_u_34._input:control_pressed(v79) and true or v77
                            if v_u_34._input:control_just_pressed(v79) then
                                local v81 = v_u_34:es_gamelocal_get_local_tracksystem()
                                if v81 ~= nil then
                                    v81:es_tracksystem_press_index(v_u_34, v80)
                                end;
                            end;
                            if v_u_34._input:control_just_released(v79) then
                                local v82 = v_u_34:es_gamelocal_get_local_tracksystem()
                                if v82 ~= nil then
                                    v82:es_tracksystem_release_index(v_u_34, v80)
                                end;
                            end;
                        end;
                    end;
                    v_u_4:profileend()
                    v_u_4:profilebegin("_game._world_effect_manager update")
                    v_u_34._world_effect_manager:update(p73, v_u_34)
                    v_u_4:profileend()
                    v_u_34._world_effect_manager:post_update(p73, v_u_34)
                    v_u_34:es_gamelocal_get_scoremanager():update(p73, v_u_34)
                    v_u_34:es_gamelocal_get_scoremanager():post_update(p73)
                    v_u_34._characters:update(p73, v_u_34)
                    if v_u_34:es_gamelocal_get_audiomanager():get_just_finished() then
                        p72:end_game()
                    end;
                elseif l_Setup_0 == v_u_27.Mode.LocalEarlyQuitWaitingForServerNotifyDoEnd then
                    l_Setup_0 = v_u_27.Mode.GameEnded
                    p72:create_game_end_ui()
                end;
            end;
            if v77 then
                v_u_69 = 0
            else
                v_u_69 = v_u_69 + v_u_1:TimescaleToDeltaTime(p73)
            end;
            v_u_4:profilebegin("_game._effects update")
            v_u_34._effects:update(p73, v_u_34)
            v_u_4:profileend()
            v_u_4:profileend()
        end;
    end;
    v_u_33.post_update = function(_, p83) --[[ Name: post_update ]] --[[ Line: 382 ]]
        --[[ Upvalues: (ref 1): l_Setup_0, (ref 2): v_u_27, (ref 3): v_u_34 ]]
        if l_Setup_0 ~= v_u_27.Mode.Setup then
            if l_Setup_0 == v_u_27.Mode.Game then
                v_u_34._ui_manager:update(p83, v_u_34)
            elseif l_Setup_0 == v_u_27.Mode.Paused then
                v_u_34._ui_manager:update(p83, v_u_34)
            elseif l_Setup_0 ~= v_u_27.Mode.SpectateLoading then
                if l_Setup_0 == v_u_27.Mode.Spectate then
                    v_u_34._ui_manager:update(p83, v_u_34)
                else
                    local _ = l_Setup_0 == v_u_27.Mode.LocalEarlyQuitWaitingForServerNotifyDoEnd
                end;
            end;
        end;
        v_u_34._effects:post_update(p83, v_u_34)
    end;
    v_u_33.debug_any_press = function(_) --[[ Name: debug_any_press ]] --[[ Line: 402 ]]
        --[[ Upvalues: (ref 1): v_u_69 ]]
        v_u_69 = 0
    end;
    v_u_33.exit_to_lobby = function(_, p84) --[[ Name: exit_to_lobby ]] --[[ Line: 406 ]]
        --[[ Upvalues: (copy 1): p_u_28, (ref 2): v_u_14 ]]
        if p_u_28._game_join == nil then
            v_u_14:warnf("GameLocal:exit_to_lobby _game_join is nil")
        else
            p_u_28._game_join:exit_to_lobby(p84)
        end;
    end;
    v_u_33.teardown_game = function(_) --[[ Name: teardown_game ]] --[[ Line: 414 ]]
        --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_14, (ref 3): l_Setup_0, (ref 4): v_u_27, (ref 5): v_u_24, (ref 6): l_Casual_0 ]]
        if v_u_34 == nil then
            return v_u_14:warnf("GameLocal:teardown_game _game is already nil");
        end;
        l_Setup_0 = v_u_27.Mode.DoRemove
        for _, v85 in v_u_34:es_gamelocal_get_tracksystems():key_itr() do
            v85:es_teardown(v_u_34)
        end;
        v_u_34:es_gamelocal_get_tracksystems():clear(v_u_34)
        v_u_34:es_gamelocal_get_audiomanager():teardown(v_u_34)
        v_u_34:es_gamelocal_get_scoremanager():teardown(v_u_34)
        v_u_34._ui_manager:teardown(v_u_34)
        v_u_34._players:teardown(v_u_34)
        v_u_34._characters:teardown(v_u_34)
        v_u_34._world_effect_manager:teardown(v_u_34)
        v_u_34._effects:teardown(v_u_34)
        v_u_34 = nil
        v_u_24:set_selected_mode(l_Casual_0)
    end;
    local l_Game_0 = v_u_27.Mode.Game
    v_u_33.set_paused = function(_, p86) --[[ Name: set_paused ]] --[[ Line: 437 ]]
        --[[ Upvalues: (ref 1): l_Game_0, (ref 2): l_Setup_0, (ref 3): v_u_27, (ref 4): v_u_34 ]]
        if p86 == true then
            l_Game_0 = l_Setup_0
            l_Setup_0 = v_u_27.Mode.Paused
        else
            l_Setup_0 = l_Game_0
        end;
        v_u_34:es_gamelocal_get_audiomanager():set_paused(p86)
        v_u_34._characters:set_paused(p86)
    end;
    local v_u_87 = nil
    v_u_33.is_ingame_sfx_enabled = function(_) --[[ Name: is_ingame_sfx_enabled ]] --[[ Line: 451 ]]
        --[[ Upvalues: (ref 1): v_u_87, (ref 2): v_u_34, (ref 3): v_u_18 ]]
        if v_u_87 == nil then
            v_u_87 = v_u_34._player_settings_manager:get_key(v_u_18.Key.HitSFX)
        end;
        return v_u_87;
    end;
    v_u_33.set_skip_to_time_ms = function(_, p88) --[[ Name: set_skip_to_time_ms ]] --[[ Line: 458 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        v_u_34:es_gamelocal_get_audiomanager():set_skip_to_time_ms(p88)
    end;
    l_Casual_0 = v_u_24:get_selected_mode()
    v_u_24:set_selected_mode(v_u_24.Casual)
    v_u_33._ui_manager:init(v_u_33)
    return v_u_33;
end;
return v_u_27;
