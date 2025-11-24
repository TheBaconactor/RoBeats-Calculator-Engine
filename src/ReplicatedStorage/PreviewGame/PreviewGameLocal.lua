-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:09 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Local.Note)
local v_u_5 = require(game.ReplicatedStorage.Local.AudioManager)
require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Local.ObjectPool)
local v_u_6 = require(game.ReplicatedStorage.Local.ScoreManager)
local v_u_7 = require(game.ReplicatedStorage.Local.TrackSystem)
local v_u_8 = require(game.ReplicatedStorage.Effects.EffectSystem)
local v_u_9 = require(game.ReplicatedStorage.Shared.GameSlot)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_10 = require(game.ReplicatedStorage.Local.RemoteInstancePlayerInfoManager)
local v_u_11 = require(game.ReplicatedStorage.Local.WorldEffectManager)
local v_u_12 = require(game.ReplicatedStorage.Local.LocalCharacterManager)
local v_u_13 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_14 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_15 = require(game.ReplicatedStorage.Avatar.GearStats)
local v16 = require(game.ReplicatedStorage.Local.GameLocalMode)
local v_u_17 = require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Local.Spectate.GameSpectateManager)
local v_u_18 = require(game.ReplicatedStorage.Local.GameCameraManager)
local v_u_19 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_20 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
local v_u_21 = require(game.ReplicatedStorage.Local.Spectate.NoteSequencePlayer)
local v_u_22 = require(game.ReplicatedStorage.Shared.GameDanceInfo)
require(game.ReplicatedStorage.Shared.EventString)
require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_23 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_24 = require(game.ReplicatedStorage.LocalShared.GameLagDelaySync)
local v_u_25 = require(game.ReplicatedStorage.PreviewGame.PreviewGameUIManager)
local v_u_26 = {
    ["Mode"] = v16
}
v_u_26.new = function(_, p_u_27, p_u_28, p_u_29, p_u_30) --[[ Name: new ]] --[[ Line: 40 ]]
    --[[ Upvalues: (copy 1): v_u_25, (copy 2): v_u_10, (copy 3): v_u_11, (copy 4): v_u_8, (copy 5): v_u_12, (copy 6): v_u_18, (copy 7): v_u_3, (copy 8): v_u_23, (copy 9): v_u_5, (copy 10): v_u_6, (copy 11): v_u_26, (copy 12): v_u_4, (copy 13): v_u_17, (copy 14): v_u_20, (copy 15): v_u_22, (copy 16): v_u_13, (copy 17): v_u_19, (copy 18): v_u_9, (copy 19): v_u_15, (copy 20): v_u_7, (copy 21): v_u_21, (copy 22): v_u_2, (copy 23): v_u_24, (copy 24): v_u_14, (copy 25): v_u_1 ]]
    local v_u_31 = p_u_27:local_services_copy()
    v_u_31._ui_manager = v_u_25:new(p_u_27._spui)
    v_u_31._players = v_u_10:new()
    v_u_31._world_effect_manager = v_u_11:new()
    v_u_31._effects = v_u_8:new()
    v_u_31._characters = v_u_12:new(v_u_31)
    v_u_31._camera_manager = v_u_18:new(v_u_31)
    local v_u_32 = nil
    v_u_31.reset_tracked_note_results = function(_) --[[ Name: reset_tracked_note_results ]] --[[ Line: 51 ]]
        --[[ Upvalues: (ref 1): v_u_32, (ref 2): v_u_3, (ref 3): v_u_23 ]]
        v_u_32 = v_u_3:new({
            [v_u_23.NoteResult_Miss] = 0,
            [v_u_23.NoteResult_Okay] = 0,
            [v_u_23.NoteResult_Great] = 0,
            [v_u_23.NoteResult_Perfect] = 0
        })
    end;
    v_u_31.get_tracked_note_results = function(_) --[[ Name: get_tracked_note_results ]] --[[ Line: 59 ]]
        --[[ Upvalues: (ref 1): v_u_32 ]]
        return v_u_32;
    end;
    v_u_31:reset_tracked_note_results()
    local function _() --[[ Name: cons ]] --[[ Line: 62 ]]
        --[[ Upvalues: (copy 1): v_u_31, (ref 2): v_u_3, (ref 3): v_u_32 ]]
        v_u_31._ui_manager:init(v_u_31)
        v_u_31:es_gamelocal_get_scoremanager():set_should_update_local_servergameinstanceplayer(false, function(p33, p34, p35) --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_3, (ref 3): v_u_32 ]]
            if p35.WhiffMiss ~= true then
                if v_u_31._ui_manager:is_ui_enabled() ~= true then
                    v_u_3:counter_increment(v_u_32, p33, 1)
                    local v36 = v_u_31:es_gamelocal_tracksystem_of_index(v_u_31:get_local_game_slot())
                    v_u_31:es_gamelocal_get_scoremanager():create_note_result_popup(v36, v36:es_get_track(p34), v_u_31:get_local_game_slot(), p34, p33, 0, 0, false, 0, 0, 0)
                end;
            end;
        end)
    end;
    local v_u_37 = v_u_31
    local v_u_38 = 0
    local v_u_39 = nil
    v_u_31.set_local_game_slot = function(_, p40) --[[ Name: set_local_game_slot ]] --[[ Line: 93 ]]
        --[[ Upvalues: (ref 1): v_u_38 ]]
        v_u_38 = p40
    end;
    local v_u_41 = v_u_3:new()
    local v_u_42 = v_u_5:new(v_u_37)
    local v_u_43 = v_u_6:new(v_u_37)
    v_u_31.es_gamelocal_get_tracksystems = function(_) --[[ Name: es_gamelocal_get_tracksystems ]] --[[ Line: 99 ]]
        --[[ Upvalues: (copy 1): v_u_41 ]]
        return v_u_41;
    end;
    v_u_31.es_gamelocal_get_audiomanager = function(_) --[[ Name: es_gamelocal_get_audiomanager ]] --[[ Line: 102 ]]
        --[[ Upvalues: (copy 1): v_u_42 ]]
        return v_u_42;
    end;
    v_u_31.es_gamelocal_get_scoremanager = function(_) --[[ Name: es_gamelocal_get_scoremanager ]] --[[ Line: 105 ]]
        --[[ Upvalues: (copy 1): v_u_43 ]]
        return v_u_43;
    end;
    v_u_31.es_gamelocal_get_worldeffectmanager = function(p44) --[[ Name: es_gamelocal_get_worldeffectmanager ]] --[[ Line: 108 ]]
        return p44._world_effect_manager;
    end;
    v_u_31.get_local_services = function(_) --[[ Name: get_local_services ]] --[[ Line: 111 ]]
        --[[ Upvalues: (copy 1): p_u_27 ]]
        return p_u_27;
    end;
    local l_Setup_0 = v_u_26.Mode.Setup
    v_u_31.get_current_mode = function(_) --[[ Name: get_current_mode ]] --[[ Line: 116 ]]
        --[[ Upvalues: (ref 1): l_Setup_0 ]]
        return l_Setup_0;
    end;
    v_u_31.set_current_mode = function(_, p45) --[[ Name: set_current_mode ]] --[[ Line: 117 ]]
        --[[ Upvalues: (ref 1): l_Setup_0 ]]
        l_Setup_0 = p45
    end;
    v_u_31.set_as_tutorial = function(_) end;
    v_u_31.is_tutorial = function(_) --[[ Name: is_tutorial ]] --[[ Line: 120 ]]
        return false;
    end;
    v_u_31.is_networked = function(_) --[[ Name: is_networked ]] --[[ Line: 121 ]]
        return false;
    end;
    v_u_31.get_spectate_manager = function(_) --[[ Name: get_spectate_manager ]] --[[ Line: 123 ]]
        return nil;
    end;
    v_u_31.set_as_spectate = function(_) end;
    v_u_31.is_spectate = function(_) --[[ Name: is_spectate ]] --[[ Line: 125 ]]
        return false;
    end;
    v_u_31.is_preview_game = function(_) --[[ Name: is_preview_game ]] --[[ Line: 126 ]]
        return true;
    end;
    v_u_31.show_fullscreen_mobile_ui = function(p46) --[[ Name: show_fullscreen_mobile_ui ]] --[[ Line: 128 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_37, (ref 3): v_u_17 ]]
        local v47 = v_u_4:is_mobile()
        if v47 then
            if p46:is_spectate() == true then
                v47 = false
            else
                v47 = v_u_37._player_settings_manager:get_key(v_u_17.Key.MobileFullScreenUI) == true
            end;
        end;
        return v47;
    end;
    local v_u_48 = v_u_20:new()
    v_u_31.get_game_note_skin_info = function(_) --[[ Name: get_game_note_skin_info ]] --[[ Line: 133 ]]
        --[[ Upvalues: (ref 1): v_u_48 ]]
        return v_u_48;
    end;
    local v_u_49 = v_u_22:get_default_dance_info()
    v_u_31.get_game_dance_info = function(_) --[[ Name: get_game_dance_info ]] --[[ Line: 136 ]]
        --[[ Upvalues: (ref 1): v_u_49 ]]
        return v_u_49;
    end;
    local v_u_50 = nil
    v_u_31.set_event_info = function(_, p51) --[[ Name: set_event_info ]] --[[ Line: 139 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        v_u_50 = p51
    end;
    v_u_31.get_event_info = function(_) --[[ Name: get_event_info ]] --[[ Line: 140 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        return v_u_50;
    end;
    v_u_31.get_game_environment_center = function(_) --[[ Name: get_game_environment_center ]] --[[ Line: 142 ]]
        --[[ Upvalues: (copy 1): p_u_28 ]]
        return p_u_28.p;
    end;
    local v_u_52 = false
    v_u_31.setup_world = function(p_u_53, p_u_54, p55, p_u_56, p57, p58) --[[ Name: setup_world ]] --[[ Line: 147 ]]
        --[[ Upvalues: (ref 1): v_u_52, (ref 2): v_u_13, (ref 3): v_u_19, (ref 4): v_u_20, (ref 5): v_u_22, (ref 6): v_u_38, (ref 7): v_u_48, (ref 8): v_u_49, (ref 9): v_u_9, (ref 10): v_u_15, (ref 11): v_u_37, (ref 12): l_Setup_0, (ref 13): v_u_26, (ref 14): v_u_39, (ref 15): v_u_7, (copy 16): v_u_41, (copy 17): p_u_30 ]]
        if v_u_52 == true then
            return v_u_13:warn("PreviewGameLocal:setup_world _has_game_setup_world == true");
        end;
        v_u_52 = true
        v_u_19:is_true(p57.Type == v_u_20.Type)
        v_u_19:is_true(p58.Type == v_u_22.Type)
        v_u_38 = p_u_54
        v_u_48 = p57
        v_u_49 = p58
        v_u_9:set_world_center_position(p_u_53:get_game_environment_center())
        local v_u_59 = nil
        pcall(function() --[[ Line: 162 ]]
            --[[ Upvalues: (ref 1): v_u_59, (copy 2): p_u_56, (copy 3): p_u_54 ]]
            v_u_59 = p_u_56[p_u_54].GearStats
        end)
        if v_u_59 == nil then
            v_u_59 = v_u_15:statsdict_base()
        end;
        v_u_37:es_gamelocal_get_scoremanager():initialize_localplayer(v_u_37, v_u_59)
        p_u_53._players:update_from_player_info_data(v_u_37, p55, false)
        p_u_53._players:update_from_gear_info(v_u_37, p_u_56)
        local function f_post_stage_load_setup_world() --[[ Name: post_stage_load_setup_world ]] --[[ Line: 171 ]]
            --[[ Upvalues: (ref 1): l_Setup_0, (ref 2): v_u_26, (ref 3): v_u_13, (ref 4): v_u_39, (ref 5): v_u_7, (ref 6): v_u_37, (ref 7): v_u_38, (ref 8): v_u_48, (ref 9): v_u_41, (copy 10): p_u_53, (ref 11): p_u_30 ]]
            if l_Setup_0 == v_u_26.Mode.DoRemove then
                return v_u_13:warnf("PreviewGameLocal:setup_world post_stage_load_setup_world _current_mode is DoRemove");
            end;
            v_u_39 = v_u_7:new(v_u_37, v_u_38)
            v_u_39:set_game_noteskin_info(v_u_48, v_u_38)
            v_u_39:init()
            v_u_41:add(v_u_38, v_u_39)
            p_u_53._characters:create_local_characters(v_u_37)
            p_u_53._ui_manager:initialize_ui(v_u_37, p_u_30)
            v_u_37._camera_manager:camera_setup_world()
        end;
        p_u_53._world_effect_manager:load_game_stage_info(v_u_37, function() --[[ Line: 186 ]]
            --[[ Upvalues: (copy 1): f_post_stage_load_setup_world ]]
            f_post_stage_load_setup_world()
        end)
    end;
    local v_u_60 = false
    v_u_31.start_game = function(p61, _) --[[ Name: start_game ]] --[[ Line: 192 ]]
        --[[ Upvalues: (ref 1): v_u_60, (ref 2): v_u_13, (ref 3): v_u_39, (ref 4): v_u_21, (ref 5): v_u_37, (ref 6): l_Setup_0, (ref 7): v_u_26 ]]
        if v_u_60 == true then
            return v_u_13:warn("PreviewGameLocal:start_game _has_game_started == true");
        end;
        v_u_60 = true
        v_u_39:tracksystem_autoplayer_init(v_u_21:new(p61, v_u_39))
        v_u_39:set_force_update_auto_player(true)
        v_u_37._ui_manager:get_decal_ui_manager():calculate_screen_constants()
        v_u_37:es_gamelocal_get_audiomanager():start_play()
        l_Setup_0 = v_u_26.Mode.Game
    end;
    v_u_31.get_local_game_slot = function(_) --[[ Name: get_local_game_slot ]] --[[ Line: 207 ]]
        --[[ Upvalues: (ref 1): v_u_38 ]]
        return v_u_38;
    end;
    v_u_31.es_gamelocal_tracksystem_of_index = function(_, p62) --[[ Name: es_gamelocal_tracksystem_of_index ]] --[[ Line: 210 ]]
        --[[ Upvalues: (ref 1): v_u_37 ]]
        return v_u_37:es_gamelocal_get_tracksystems():get(p62);
    end;
    v_u_31.es_gamelocal_get_local_tracksystem = function(_) --[[ Name: es_gamelocal_get_local_tracksystem ]] --[[ Line: 213 ]]
        --[[ Upvalues: (ref 1): v_u_37 ]]
        return v_u_37:es_gamelocal_tracksystem_of_index(v_u_37:get_local_game_slot());
    end;
    local v_u_63 = {
        [v_u_2.KEY_TRACK1] = 1,
        [v_u_2.KEY_TRACK2] = 2,
        [v_u_2.KEY_TRACK3] = 3,
        [v_u_2.KEY_TRACK4] = 4
    }
    local v_u_64 = 0
    v_u_31.get_frame_count = function(_) --[[ Name: get_frame_count ]] --[[ Line: 225 ]]
        --[[ Upvalues: (ref 1): v_u_64 ]]
        return v_u_64;
    end;
    local v_u_65 = 9999
    v_u_31.get_time_since_any_pressed = function(_) --[[ Name: get_time_since_any_pressed ]] --[[ Line: 230 ]]
        --[[ Upvalues: (ref 1): v_u_65 ]]
        return v_u_65;
    end;
    local v_u_66 = false
    local function _() --[[ Name: loop_playing_track ]] --[[ Line: 236 ]]
        --[[ Upvalues: (copy 1): v_u_43, (ref 2): v_u_37, (ref 3): v_u_38, (copy 4): v_u_31 ]]
        v_u_43:reset()
        v_u_37:es_gamelocal_get_tracksystems():get(v_u_38):reset()
        v_u_31:set_skip_to_time_ms(0)
    end;
    local v_u_67 = v_u_24:new()
    v_u_31.update = function(p68, p69) --[[ Name: update ]] --[[ Line: 244 ]]
        --[[ Upvalues: (ref 1): v_u_64, (ref 2): l_Setup_0, (ref 3): v_u_26, (ref 4): v_u_4, (ref 5): v_u_37, (ref 6): v_u_9, (ref 7): v_u_14, (copy 8): v_u_67, (ref 9): v_u_66, (ref 10): v_u_39, (copy 11): v_u_63, (copy 12): v_u_43, (ref 13): v_u_38, (copy 14): v_u_31, (ref 15): v_u_65, (ref 16): v_u_1 ]]
        v_u_64 = v_u_64 + 1
        if l_Setup_0 ~= v_u_26.Mode.DoRemove then
            v_u_4:profilebegin("GameLocal:Update")
            v_u_37._camera_manager:update(p69)
            for v70, v71 in v_u_37:es_gamelocal_get_tracksystems():key_itr() do
                if v_u_37._players._slots:contains(v70) == false then
                    v71:es_teardown()
                    v_u_37:es_gamelocal_get_tracksystems():remove(v70)
                end;
            end;
            v_u_9:set_world_center_position(p68:get_game_environment_center())
            local v72
            if v_u_14.DoGameLagDelaySync == true and l_Setup_0 == v_u_26.Mode.Game then
                v72 = v_u_67:update_game_lag_delay_sync(v_u_37, p69)
            else
                v72 = false
            end;
            local v73 = false
            if v72 ~= true and l_Setup_0 ~= v_u_26.Mode.Setup and l_Setup_0 == v_u_26.Mode.Game then
                v_u_4:profilebegin("audio_manager update")
                v_u_37:es_gamelocal_get_audiomanager():update(p69, v_u_37)
                v_u_4:profileend()
                v_u_4:profilebegin("_game._tracksystems update")
                for _, v74 in v_u_37:es_gamelocal_get_tracksystems():key_itr() do
                    v74:es_update(p69, v_u_37)
                end;
                v_u_4:profileend()
                v_u_4:profilebegin("_game._input control update")
                if v_u_37._ui_manager:is_ui_enabled() then
                    if v_u_66 == true then
                        v_u_66 = false
                        v_u_39:set_force_update_auto_player(true)
                    end;
                elseif v_u_66 ~= true then
                    v_u_66 = true
                    v_u_39:set_force_update_auto_player(false)
                end;
                if v_u_66 == true then
                    for v75, v76 in pairs(v_u_63) do
                        v73 = v_u_37._input:control_pressed(v75) and true or v73
                        if v_u_37._input:control_just_pressed(v75) then
                            local v77 = v_u_37:es_gamelocal_get_local_tracksystem()
                            if v77 ~= nil then
                                v77:es_tracksystem_press_index(v_u_37, v76)
                            end;
                        end;
                        if v_u_37._input:control_just_released(v75) then
                            local v78 = v_u_37:es_gamelocal_get_local_tracksystem()
                            if v78 ~= nil then
                                v78:es_tracksystem_release_index(v_u_37, v76)
                            end;
                        end;
                    end;
                end;
                v_u_4:profileend()
                v_u_4:profilebegin("_game._world_effect_manager update")
                v_u_37._world_effect_manager:update(p69, v_u_37)
                v_u_4:profileend()
                v_u_37._world_effect_manager:post_update(p69, v_u_37)
                v_u_37:es_gamelocal_get_scoremanager():update(p69, v_u_37)
                v_u_37:es_gamelocal_get_scoremanager():post_update(p69)
                v_u_37._characters:update(p69, v_u_37)
                if v_u_37:es_gamelocal_get_audiomanager():get_just_finished() then
                    v_u_43:reset()
                    v_u_37:es_gamelocal_get_tracksystems():get(v_u_38):reset()
                    v_u_31:set_skip_to_time_ms(0)
                end;
            end;
            if v73 then
                v_u_65 = 0
            else
                v_u_65 = v_u_65 + v_u_1:TimescaleToDeltaTime(p69)
            end;
            v_u_4:profilebegin("_game._effects update")
            v_u_37._effects:update(p69, v_u_37)
            v_u_4:profileend()
            v_u_4:profileend()
        end;
    end;
    v_u_31.post_update = function(_, p79) --[[ Name: post_update ]] --[[ Line: 356 ]]
        --[[ Upvalues: (ref 1): l_Setup_0, (ref 2): v_u_26, (ref 3): v_u_37 ]]
        if l_Setup_0 ~= v_u_26.Mode.Setup then
            if l_Setup_0 == v_u_26.Mode.Game then
                v_u_37._ui_manager:update(p79, v_u_37)
            elseif l_Setup_0 == v_u_26.Mode.Paused then
                v_u_37._ui_manager:update(p79, v_u_37)
            elseif l_Setup_0 ~= v_u_26.Mode.SpectateLoading then
                if l_Setup_0 == v_u_26.Mode.Spectate then
                    v_u_37._ui_manager:update(p79, v_u_37)
                elseif l_Setup_0 ~= v_u_26.Mode.LocalEarlyQuitWaitingForServerNotifyDoEnd and l_Setup_0 == v_u_26.Mode.GameEnded then
                    v_u_37._ui_manager:update(p79, v_u_37)
                end;
            end;
        end;
        v_u_37._effects:post_update(p79, v_u_37)
    end;
    v_u_31.debug_any_press = function(_) --[[ Name: debug_any_press ]] --[[ Line: 377 ]]
        --[[ Upvalues: (ref 1): v_u_65 ]]
        v_u_65 = 0
    end;
    v_u_31.exit_to_lobby = function(_, p80) --[[ Name: exit_to_lobby ]] --[[ Line: 381 ]]
        --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_13 ]]
        if p_u_29 == nil then
            v_u_13:warnf("GameLocal:exit_to_lobby _game_join is nil")
        else
            p_u_29:exit_to_lobby(p80)
        end;
    end;
    v_u_31.teardown_game = function(_) --[[ Name: teardown_game ]] --[[ Line: 389 ]]
        --[[ Upvalues: (ref 1): v_u_37, (ref 2): v_u_13, (ref 3): l_Setup_0, (ref 4): v_u_26, (ref 5): p_u_29 ]]
        if v_u_37 == nil then
            return v_u_13:warnf("GameLocal:teardown_game _game is already nil");
        end;
        l_Setup_0 = v_u_26.Mode.DoRemove
        for _, v81 in v_u_37:es_gamelocal_get_tracksystems():key_itr() do
            v81:es_teardown(v_u_37)
        end;
        v_u_37:es_gamelocal_get_tracksystems():clear(v_u_37)
        v_u_37:es_gamelocal_get_audiomanager():teardown(v_u_37)
        v_u_37:es_gamelocal_get_scoremanager():teardown(v_u_37)
        v_u_37._ui_manager:teardown(v_u_37)
        v_u_37._players:teardown(v_u_37)
        v_u_37._characters:teardown(v_u_37)
        v_u_37._world_effect_manager:teardown(v_u_37)
        v_u_37._effects:teardown(v_u_37)
        v_u_37 = nil
        p_u_29 = nil
    end;
    local l_Game_0 = v_u_26.Mode.Game
    v_u_31.set_paused = function(_, p82) --[[ Name: set_paused ]] --[[ Line: 412 ]]
        --[[ Upvalues: (ref 1): l_Game_0, (ref 2): l_Setup_0, (ref 3): v_u_26, (ref 4): v_u_37 ]]
        if p82 == true then
            l_Game_0 = l_Setup_0
            l_Setup_0 = v_u_26.Mode.Paused
        else
            l_Setup_0 = l_Game_0
        end;
        v_u_37:es_gamelocal_get_audiomanager():set_paused(p82)
        v_u_37._characters:set_paused(p82)
    end;
    local v_u_83 = nil
    v_u_31.is_ingame_sfx_enabled = function(_) --[[ Name: is_ingame_sfx_enabled ]] --[[ Line: 426 ]]
        --[[ Upvalues: (ref 1): v_u_83, (ref 2): v_u_37, (ref 3): v_u_17 ]]
        if v_u_83 == nil then
            v_u_83 = v_u_37._player_settings_manager:get_key(v_u_17.Key.HitSFX)
        end;
        return v_u_83;
    end;
    v_u_31.set_skip_to_time_ms = function(_, p84) --[[ Name: set_skip_to_time_ms ]] --[[ Line: 433 ]]
        --[[ Upvalues: (ref 1): v_u_37 ]]
        v_u_37:es_gamelocal_get_audiomanager():set_skip_to_time_ms(p84)
    end;
    v_u_31._ui_manager:init(v_u_31)
    v_u_31:es_gamelocal_get_scoremanager():set_should_update_local_servergameinstanceplayer(false, function(p85, p86, p87) --[[ Line: 66 ]]
        --[[ Upvalues: (copy 1): v_u_31, (ref 2): v_u_3, (ref 3): v_u_32 ]]
        if p87.WhiffMiss ~= true then
            if v_u_31._ui_manager:is_ui_enabled() ~= true then
                v_u_3:counter_increment(v_u_32, p85, 1)
                local v88 = v_u_31:es_gamelocal_tracksystem_of_index(v_u_31:get_local_game_slot())
                v_u_31:es_gamelocal_get_scoremanager():create_note_result_popup(v88, v88:es_get_track(p86), v_u_31:get_local_game_slot(), p86, p85, 0, 0, false, 0, 0, 0)
            end;
        end;
    end)
    return v_u_31;
end;
return v_u_26;
