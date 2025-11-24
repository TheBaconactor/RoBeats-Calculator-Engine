-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:25 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Local.Note)
local v_u_5 = require(game.ReplicatedStorage.Local.AudioManager)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Local.ObjectPool)
local v_u_7 = require(game.ReplicatedStorage.Local.ScoreManager)
local v_u_8 = require(game.ReplicatedStorage.Local.UIManager)
local v_u_9 = require(game.ReplicatedStorage.Local.TrackSystem)
local v_u_10 = require(game.ReplicatedStorage.Effects.EffectSystem)
local v_u_11 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_12 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_13 = require(game.ReplicatedStorage.Local.RemoteInstancePlayerInfoManager)
local v_u_14 = require(game.ReplicatedStorage.Local.WorldEffectManager)
local v_u_15 = require(game.ReplicatedStorage.Local.LocalCharacterManager)
local v_u_16 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_17 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_18 = require(game.ReplicatedStorage.Avatar.GearStats)
local v19 = require(game.ReplicatedStorage.Local.GameLocalMode)
local v_u_20 = require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.Constants)
local v_u_21 = require(game.ReplicatedStorage.Local.Spectate.GameSpectateManager)
local v_u_22 = require(game.ReplicatedStorage.Local.GameCameraManager)
local v_u_23 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_24 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
local v_u_25 = require(game.ReplicatedStorage.Local.Spectate.NoteSequencePlayer)
local v_u_26 = require(game.ReplicatedStorage.Shared.GameDanceInfo)
local v_u_27 = require(game.ReplicatedStorage.Shared.EventString)
local v_u_28 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_29 = require(game.ReplicatedStorage.LocalShared.GameLagDelaySync)
local v_u_30 = require(game.ReplicatedStorage.LocalShared.AdornPool)
local v_u_31 = require(game.ReplicatedStorage.Lobby.Menus.GameEndV2UI)
local v_u_32 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_33 = {
    ["Mode"] = v19
}
v_u_33.new = function(_, p_u_34, p_u_35, p_u_36) --[[ Name: new ]] --[[ Line: 42 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_13, (copy 3): v_u_14, (copy 4): v_u_10, (copy 5): v_u_15, (copy 6): v_u_3, (copy 7): v_u_5, (copy 8): v_u_7, (copy 9): v_u_22, (copy 10): v_u_33, (copy 11): v_u_4, (copy 12): v_u_20, (copy 13): v_u_24, (copy 14): v_u_26, (copy 15): v_u_16, (copy 16): v_u_23, (copy 17): v_u_11, (copy 18): v_u_18, (copy 19): v_u_30, (copy 20): v_u_9, (copy 21): v_u_17, (copy 22): v_u_25, (copy 23): v_u_6, (copy 24): v_u_12, (copy 25): v_u_27, (copy 26): v_u_2, (copy 27): v_u_29, (copy 28): v_u_1, (copy 29): v_u_32, (copy 30): v_u_31, (copy 31): v_u_28, (copy 32): v_u_21 ]]
    local v_u_37 = p_u_34:local_services_copy()
    v_u_37._ui_manager = v_u_8:new(p_u_34._spui)
    v_u_37._players = v_u_13:new()
    v_u_37._world_effect_manager = v_u_14:new()
    v_u_37._effects = v_u_10:new()
    v_u_37._characters = v_u_15:new(v_u_37)
    v_u_37._ui_manager:init(v_u_37)
    local v_u_38 = v_u_37
    local v_u_39 = 0
    v_u_37.set_local_game_slot = function(_, p40) --[[ Name: set_local_game_slot ]] --[[ Line: 55 ]]
        --[[ Upvalues: (ref 1): v_u_39 ]]
        v_u_39 = p40
    end;
    local v_u_41 = v_u_3:new()
    v_u_3:new()
    v_u_3:new()
    v_u_3:new()
    v_u_3:new()
    v_u_3:new()
    local v_u_42 = v_u_3:new()
    local v_u_43 = v_u_5:new(v_u_38)
    local v_u_44 = v_u_7:new(v_u_38)
    v_u_37.es_gamelocal_get_tracksystems = function(_) --[[ Name: es_gamelocal_get_tracksystems ]] --[[ Line: 68 ]]
        --[[ Upvalues: (copy 1): v_u_41 ]]
        return v_u_41;
    end;
    v_u_37.es_gamelocal_get_audiomanager = function(_) --[[ Name: es_gamelocal_get_audiomanager ]] --[[ Line: 71 ]]
        --[[ Upvalues: (copy 1): v_u_43 ]]
        return v_u_43;
    end;
    v_u_37.es_gamelocal_get_scoremanager = function(_) --[[ Name: es_gamelocal_get_scoremanager ]] --[[ Line: 74 ]]
        --[[ Upvalues: (copy 1): v_u_44 ]]
        return v_u_44;
    end;
    v_u_37.es_gamelocal_get_worldeffectmanager = function(p45) --[[ Name: es_gamelocal_get_worldeffectmanager ]] --[[ Line: 77 ]]
        return p45._world_effect_manager;
    end;
    v_u_37.get_local_services = function(_) --[[ Name: get_local_services ]] --[[ Line: 80 ]]
        --[[ Upvalues: (copy 1): p_u_34 ]]
        return p_u_34;
    end;
    v_u_38._camera_manager = v_u_22:new(v_u_38)
    local v_u_46 = -1
    local l_Setup_0 = v_u_33.Mode.Setup
    v_u_37.get_current_mode = function(_) --[[ Name: get_current_mode ]] --[[ Line: 88 ]]
        --[[ Upvalues: (ref 1): l_Setup_0 ]]
        return l_Setup_0;
    end;
    v_u_37.set_current_mode = function(_, p47) --[[ Name: set_current_mode ]] --[[ Line: 89 ]]
        --[[ Upvalues: (ref 1): l_Setup_0 ]]
        l_Setup_0 = p47
    end;
    local v_u_48 = false
    v_u_37.set_as_tutorial = function(_) --[[ Name: set_as_tutorial ]] --[[ Line: 92 ]]
        --[[ Upvalues: (ref 1): v_u_48 ]]
        v_u_48 = true
    end;
    v_u_37.is_tutorial = function(_) --[[ Name: is_tutorial ]] --[[ Line: 93 ]]
        --[[ Upvalues: (ref 1): v_u_48 ]]
        return v_u_48;
    end;
    v_u_37.is_networked = function(p49) --[[ Name: is_networked ]] --[[ Line: 94 ]]
        --[[ Upvalues: (ref 1): v_u_48 ]]
        local v50
        if v_u_48 == false then
            v50 = p49:is_spectate() == false
        else
            v50 = false
        end;
        return v50;
    end;
    local v_u_51 = nil
    v_u_37.get_spectate_manager = function(_) --[[ Name: get_spectate_manager ]] --[[ Line: 97 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        return v_u_51;
    end;
    local v_u_52 = false
    v_u_37.set_as_spectate = function(_) --[[ Name: set_as_spectate ]] --[[ Line: 99 ]]
        --[[ Upvalues: (ref 1): v_u_52 ]]
        v_u_52 = true
    end;
    v_u_37.is_spectate = function(_) --[[ Name: is_spectate ]] --[[ Line: 100 ]]
        --[[ Upvalues: (ref 1): v_u_52 ]]
        return v_u_52;
    end;
    v_u_37.is_preview_game = function(_) --[[ Name: is_preview_game ]] --[[ Line: 101 ]]
        return false;
    end;
    v_u_37.show_fullscreen_mobile_ui = function(p53) --[[ Name: show_fullscreen_mobile_ui ]] --[[ Line: 103 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_38, (ref 3): v_u_20 ]]
        local v54 = v_u_4:is_mobile()
        if v54 then
            if p53:is_spectate() == true then
                v54 = false
            else
                v54 = v_u_38._player_settings_manager:get_key(v_u_20.Key.MobileFullScreenUI) == true
            end;
        end;
        return v54;
    end;
    local v_u_55 = v_u_24:new()
    v_u_37.get_game_note_skin_info = function(_) --[[ Name: get_game_note_skin_info ]] --[[ Line: 108 ]]
        --[[ Upvalues: (ref 1): v_u_55 ]]
        return v_u_55;
    end;
    local v_u_56 = v_u_26:get_default_dance_info()
    v_u_37.get_game_dance_info = function(_) --[[ Name: get_game_dance_info ]] --[[ Line: 111 ]]
        --[[ Upvalues: (ref 1): v_u_56 ]]
        return v_u_56;
    end;
    local v_u_57 = nil
    v_u_37.set_event_info = function(_, p58) --[[ Name: set_event_info ]] --[[ Line: 114 ]]
        --[[ Upvalues: (ref 1): v_u_57 ]]
        v_u_57 = p58
    end;
    v_u_37.get_event_info = function(_) --[[ Name: get_event_info ]] --[[ Line: 115 ]]
        --[[ Upvalues: (ref 1): v_u_57 ]]
        return v_u_57;
    end;
    v_u_37.get_game_environment_center = function(_) --[[ Name: get_game_environment_center ]] --[[ Line: 117 ]]
        --[[ Upvalues: (copy 1): p_u_35 ]]
        return p_u_35.p;
    end;
    local function f_post_stage_load_setup_world() --[[ Name: post_stage_load_setup_world ]] --[[ Line: 121 ]]
        --[[ Upvalues: (ref 1): v_u_42, (copy 2): v_u_41, (ref 3): l_Setup_0, (ref 4): v_u_33, (ref 5): v_u_16, (copy 6): v_u_37, (ref 7): v_u_38 ]]
        v_u_42 = v_u_41
        if l_Setup_0 == v_u_33.Mode.DoRemove then
            return v_u_16:warnf("GameLocal:setup_world post_stage_load_setup_world _current_mode is DoRemove");
        end;
        v_u_37._characters:create_local_characters(v_u_38)
        v_u_37._ui_manager:initialize_ui(v_u_38)
        v_u_38._camera_manager:camera_setup_world()
        v_u_42 = nil
    end;
    local v_u_59 = false
    v_u_37.setup_world = function(p60, p_u_61, p62, p_u_63, p64, p65) --[[ Name: setup_world ]] --[[ Line: 135 ]]
        --[[ Upvalues: (ref 1): v_u_59, (ref 2): v_u_16, (ref 3): v_u_42, (copy 4): v_u_41, (ref 5): v_u_23, (ref 6): v_u_24, (ref 7): v_u_26, (ref 8): v_u_39, (ref 9): v_u_55, (ref 10): v_u_56, (ref 11): v_u_11, (ref 12): v_u_38, (ref 13): v_u_18, (ref 14): v_u_30, (copy 15): f_post_stage_load_setup_world ]]
        if v_u_59 == true then
            return v_u_16:warn("GameLocal:setup_world _has_game_setup_world == true");
        end;
        v_u_59 = true
        v_u_42 = v_u_41
        v_u_23:is_true(p64.Type == v_u_24.Type)
        v_u_23:is_true(p65.Type == v_u_26.Type)
        v_u_39 = p_u_61
        v_u_55 = p64
        v_u_56 = p65
        v_u_11:set_world_center_position(p60:get_game_environment_center())
        v_u_38._camera_manager:set_camera_focus_pos(v_u_11:get_world_center_position())
        local v_u_66 = nil
        pcall(function() --[[ Line: 152 ]]
            --[[ Upvalues: (ref 1): v_u_66, (copy 2): p_u_63, (copy 3): p_u_61 ]]
            v_u_66 = p_u_63[p_u_61].GearStats
        end)
        if v_u_66 == nil then
            v_u_66 = v_u_18:statsdict_base()
        end;
        v_u_38:es_gamelocal_get_scoremanager():initialize_localplayer(v_u_38, v_u_66)
        p60._players:update_from_player_info_data(v_u_38, p62, false)
        p60._players:update_from_gear_info(v_u_38, p_u_63)
        if v_u_30:verify_all_adorns_in_folder_are_hidden() ~= true then
            v_u_16:warnf("GameLocal:setup_world AdornPool:verify_all_adorns_in_folder_are_hidden() ~= true")
        end;
        p60._world_effect_manager:load_game_stage_info(v_u_38, function() --[[ Line: 166 ]]
            --[[ Upvalues: (ref 1): f_post_stage_load_setup_world ]]
            f_post_stage_load_setup_world()
        end)
        v_u_42 = nil
    end;
    local function f_setup_tracksystems_fn() --[[ Name: setup_tracksystems_fn ]] --[[ Line: 172 ]]
        --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_9, (ref 3): v_u_4, (ref 4): v_u_17, (copy 5): v_u_37, (ref 6): v_u_25, (ref 7): v_u_55 ]]
        for v67 = 1, 4 do
            if v_u_38._players._slots:contains(v67) then
                local v68 = v_u_9:new(v_u_38, v67)
                if v_u_4:is_dev_build() and v_u_17.LocalAutoPlay then
                    -- ::l7:: (Possible bug with goto)
                    v68:tracksystem_autoplayer_init(v_u_25:new(v_u_37, v68))
                    break;
                end;
                local v69 = v_u_37:is_networked()
                if v69 then
                    v69 = v67 == v_u_37:get_local_game_slot()
                end;
                if v69 ~= true then
                    break;
                end;
                -- ::l12:: (Possible bug with goto)
                v_u_38:es_gamelocal_get_tracksystems():add(v67, v68)
                v_u_38:es_gamelocal_get_tracksystems():get(v67):set_game_noteskin_info(v_u_55, v67)
                v_u_38:es_gamelocal_get_tracksystems():get(v67):init()
            end;
        end;
    end;
    local v_u_70 = false
    v_u_37.start_game = function(p_u_71, p72) --[[ Name: start_game ]] --[[ Line: 188 ]]
        --[[ Upvalues: (ref 1): v_u_70, (ref 2): v_u_16, (ref 3): v_u_42, (copy 4): v_u_41, (ref 5): v_u_38, (copy 6): f_post_stage_load_setup_world, (ref 7): v_u_46, (ref 8): v_u_6, (copy 9): f_setup_tracksystems_fn, (ref 10): v_u_12, (ref 11): v_u_4, (ref 12): l_Setup_0, (ref 13): v_u_33, (ref 14): v_u_27 ]]
        if v_u_70 == true then
            return v_u_16:warn("GameLocal:start_game _has_game_started == true");
        end;
        v_u_70 = true
        v_u_42 = v_u_41
        if typeof(p72) ~= "number" then
            v_u_16:warnf("GameLocal:start_game bad game_id(%s)", (tostring(p72)))
            p72 = -1
        end;
        if p_u_71._world_effect_manager:is_game_stage_loaded() ~= true then
            v_u_16:warnf("force_load_default_stage (_is_game_stage_loaded was not true by time of GameLocal:start_game)")
            p_u_71._world_effect_manager:force_load_default_stage(v_u_38)
            f_post_stage_load_setup_world()
        end;
        v_u_46 = p72
        v_u_38._sfx_manager:play_sfx(v_u_6.SFX_STARTCHEER_1)
        f_setup_tracksystems_fn()
        v_u_38._ui_manager:get_decal_ui_manager():calculate_screen_constants()
        if p_u_71:is_networked() == true then
            v_u_38._evt:clear_pending_on(v_u_12.EVT_Game_ServerNotifyMatchEndRewards)
            v_u_38._evt:clear_pending_on(v_u_12.EVT_Game_ServerUpdatePlayerInfo)
            v_u_38._evt:wait_on_event(v_u_12.EVT_Game_ServerUpdatePlayerInfo, function(p73, p74, _) --[[ Line: 216 ]]
                --[[ Upvalues: (ref 1): v_u_46, (ref 2): v_u_16, (copy 3): p_u_71, (ref 4): v_u_38 ]]
                if v_u_46 == p73 then
                    p_u_71._players:update_from_player_info_data(v_u_38, p74, true)
                else
                    v_u_16:warnf("EVT_Game_ServerUpdatePlayerInfo invalid game_id expected(%d) got(%d)", v_u_46, p73)
                end;
            end)
            v_u_38._evt:clear_pending_on(v_u_12.EVT_Game_ServerNotifyDoEnd)
            v_u_38._evt:wait_on_event_once(v_u_12.EVT_Game_ServerNotifyDoEnd, function(p75) --[[ Line: 225 ]]
                --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_4, (ref 3): v_u_38, (copy 4): p_u_71, (ref 5): l_Setup_0, (ref 6): v_u_33 ]]
                v_u_16:puts("EVT_Game_ServerNotifyDoEnd %s", v_u_4:table_to_string(p75))
                if v_u_38 ~= nil then
                    p_u_71._players:update_from_player_info_data(v_u_38, p75, false)
                    l_Setup_0 = v_u_33.Mode.GameEnded
                    p_u_71:load_game_end_menu()
                end;
            end)
            v_u_38._evt:clear_pending_on(v_u_12.EVT_Spectate_ServerResyncNoteSequence)
            v_u_38._evt:wait_on_event(v_u_12.EVT_Spectate_ServerResyncNoteSequence, function(p76, p77) --[[ Line: 238 ]]
                --[[ Upvalues: (ref 1): v_u_46, (ref 2): v_u_16, (ref 3): v_u_38, (ref 4): v_u_27 ]]
                if v_u_46 == p76 then
                    v_u_38:es_gamelocal_get_scoremanager():resync_note_sequence(v_u_27:es_table_deconvert(p77))
                else
                    v_u_16:warnf("EVT_Spectate_ServerResyncNoteSequence invalid game_id expected(%d) got(%d)", v_u_46, p76)
                end;
            end)
        end;
        v_u_38:es_gamelocal_get_audiomanager():start_play()
        l_Setup_0 = v_u_33.Mode.Game
        v_u_42 = nil
    end;
    v_u_37.get_local_game_slot = function(_) --[[ Name: get_local_game_slot ]] --[[ Line: 252 ]]
        --[[ Upvalues: (ref 1): v_u_39 ]]
        return v_u_39;
    end;
    v_u_37.es_gamelocal_tracksystem_of_index = function(_, p78) --[[ Name: es_gamelocal_tracksystem_of_index ]] --[[ Line: 255 ]]
        --[[ Upvalues: (ref 1): v_u_38 ]]
        return v_u_38:es_gamelocal_get_tracksystems():get(p78);
    end;
    v_u_37.es_gamelocal_get_local_tracksystem = function(_) --[[ Name: es_gamelocal_get_local_tracksystem ]] --[[ Line: 258 ]]
        --[[ Upvalues: (ref 1): v_u_38 ]]
        return v_u_38:es_gamelocal_tracksystem_of_index(v_u_38:get_local_game_slot());
    end;
    local v_u_79 = v_u_2:get_key_to_track_index():get_table()
    local v_u_80 = 0
    v_u_37.get_frame_count = function(_) --[[ Name: get_frame_count ]] --[[ Line: 265 ]]
        --[[ Upvalues: (ref 1): v_u_80 ]]
        return v_u_80;
    end;
    local v_u_81 = 9999
    v_u_37.get_time_since_any_pressed = function(_) --[[ Name: get_time_since_any_pressed ]] --[[ Line: 270 ]]
        --[[ Upvalues: (ref 1): v_u_81 ]]
        return v_u_81;
    end;
    local v_u_82 = v_u_29:new()
    local v_u_83 = v_u_3:new()
    local v_u_84 = v_u_38
    local v_u_85 = v_u_42
    local v_u_86 = v_u_80
    local v_u_87 = v_u_51
    local v_u_88 = v_u_81
    local v_u_89 = l_Setup_0
    for _, v90 in pairs(v_u_79) do
        v_u_83:add(v90, false)
    end;
    v_u_37.update = function(p91, p92) --[[ Name: update ]] --[[ Line: 281 ]]
        --[[ Upvalues: (ref 1): v_u_86, (ref 2): v_u_89, (ref 3): v_u_33, (ref 4): v_u_85, (copy 5): v_u_41, (ref 6): v_u_4, (ref 7): v_u_84, (ref 8): v_u_11, (ref 9): v_u_17, (copy 10): v_u_82, (copy 11): v_u_79, (copy 12): v_u_83, (ref 13): v_u_2, (ref 14): v_u_87, (ref 15): v_u_88, (ref 16): v_u_1 ]]
        v_u_86 = v_u_86 + 1
        if v_u_89 ~= v_u_33.Mode.DoRemove then
            v_u_85 = v_u_41
            v_u_4:profilebegin("GameLocal:Update")
            v_u_84._camera_manager:update(p92)
            for v93, v94 in v_u_84:es_gamelocal_get_tracksystems():key_itr() do
                if v_u_84._players._slots:contains(v93) == false then
                    v94:es_teardown()
                    v_u_84:es_gamelocal_get_tracksystems():remove(v93)
                end;
            end;
            v_u_11:set_world_center_position(p91:get_game_environment_center())
            local v95
            if v_u_17.DoGameLagDelaySync == true and v_u_89 == v_u_33.Mode.Game then
                v95 = v_u_82:update_game_lag_delay_sync(v_u_84, p92)
            else
                v95 = false
            end;
            local v96 = false
            if v95 ~= true and v_u_89 ~= v_u_33.Mode.Setup then
                if v_u_89 == v_u_33.Mode.Game then
                    v_u_4:profilebegin("audio_manager update")
                    v_u_84:es_gamelocal_get_audiomanager():update(p92, v_u_84)
                    v_u_4:profileend()
                    v_u_4:profilebegin("_game._tracksystems update")
                    for _, v97 in v_u_84:es_gamelocal_get_tracksystems():key_itr() do
                        v97:es_update(p92, v_u_84)
                    end;
                    v_u_4:profileend()
                    v_u_4:profilebegin("_game._input control update")
                    for v98, v99 in pairs(v_u_79) do
                        local v100 = v_u_84._input:control_pressed(v98)
                        v96 = v100 and true or v96
                        if v_u_84._input:control_just_pressed(v98) then
                            local v101 = v_u_84:es_gamelocal_get_local_tracksystem()
                            if v101 ~= nil then
                                v101:es_tracksystem_press_index(v_u_84, v99)
                            end;
                        end;
                        local v102
                        if v100 == false then
                            v102 = v_u_83:get(v99) == true
                        else
                            v102 = false
                        end;
                        if v_u_84._input:control_just_released(v98) or v102 then
                            local v103 = v_u_84:es_gamelocal_get_local_tracksystem()
                            if v103 ~= nil then
                                v103:es_tracksystem_release_index(v_u_84, v99)
                            end;
                        end;
                        v_u_83:add(v99, v100)
                    end;
                    v_u_4:profileend()
                    v_u_4:profilebegin("_game._world_effect_manager update")
                    v_u_84._world_effect_manager:update(p92, v_u_84)
                    v_u_4:profileend()
                    v_u_84._world_effect_manager:post_update(p92, v_u_84)
                    v_u_84:es_gamelocal_get_scoremanager():update(p92, v_u_84)
                    v_u_84:es_gamelocal_get_scoremanager():post_update(p92)
                    v_u_84._characters:update(p92, v_u_84)
                    if v_u_84:es_gamelocal_get_audiomanager():get_just_finished() then
                        v_u_84:es_gamelocal_get_scoremanager():notify_local_finished()
                        p91:add_finished_popup()
                    end;
                    if v_u_4:is_dev_build() and (v_u_17.EndGameDebugKey == true and v_u_84._input:control_just_released(v_u_2.KEY_DEBUG_1)) then
                        v_u_84:es_gamelocal_get_scoremanager():notify_local_finished()
                        p91:add_finished_popup()
                    end;
                elseif v_u_89 ~= v_u_33.Mode.Paused then
                    if v_u_89 == v_u_33.Mode.SpectateLoading then
                        v_u_87:update(p92)
                    elseif v_u_89 == v_u_33.Mode.Spectate then
                        v_u_84:es_gamelocal_get_audiomanager():update(p92, v_u_84)
                        for _, v104 in v_u_84:es_gamelocal_get_tracksystems():key_itr() do
                            v104:es_update(p92, v_u_84)
                        end;
                        v_u_84._world_effect_manager:update(p92, v_u_84)
                        v_u_87:update(p92)
                        v_u_84._world_effect_manager:post_update(p92, v_u_84)
                        v_u_84._characters:update(p92, v_u_84)
                        v_u_84:es_gamelocal_get_scoremanager():update(p92, v_u_84)
                        v_u_84:es_gamelocal_get_scoremanager():post_update(p92)
                        if v_u_84:es_gamelocal_get_audiomanager():get_just_finished() then
                            p91:add_finished_popup()
                            if p91:get_spectate_manager() then
                                p91:get_spectate_manager():just_finished()
                            end;
                        end;
                    end;
                end;
            end;
            if v96 then
                v_u_88 = 0
            else
                v_u_88 = v_u_88 + v_u_1:TimescaleToDeltaTime(p92)
            end;
            v_u_4:profilebegin("_game._effects update")
            v_u_84._effects:update(p92, v_u_84)
            v_u_4:profileend()
            v_u_4:profileend()
            v_u_85 = nil
        end;
    end;
    v_u_37.post_update = function(_, p105) --[[ Name: post_update ]] --[[ Line: 421 ]]
        --[[ Upvalues: (ref 1): v_u_85, (copy 2): v_u_41, (ref 3): v_u_89, (ref 4): v_u_33, (ref 5): v_u_84 ]]
        v_u_85 = v_u_41
        if v_u_89 ~= v_u_33.Mode.Setup then
            if v_u_89 == v_u_33.Mode.Game then
                v_u_84._ui_manager:update(p105, v_u_84)
            elseif v_u_89 == v_u_33.Mode.Paused then
                v_u_84._ui_manager:update(p105, v_u_84)
            elseif v_u_89 ~= v_u_33.Mode.SpectateLoading then
                if v_u_89 == v_u_33.Mode.Spectate then
                    v_u_84._ui_manager:update(p105, v_u_84)
                elseif v_u_89 ~= v_u_33.Mode.LocalEarlyQuitWaitingForServerNotifyDoEnd and v_u_89 == v_u_33.Mode.GameEnded then
                    v_u_84._ui_manager:update(p105, v_u_84)
                end;
            end;
        end;
        v_u_84._effects:post_update(p105, v_u_84)
        v_u_85 = nil
    end;
    v_u_37.early_quit = function(p106) --[[ Name: early_quit ]] --[[ Line: 444 ]]
        --[[ Upvalues: (ref 1): v_u_89, (ref 2): v_u_33, (ref 3): v_u_84 ]]
        v_u_89 = v_u_33.Mode.LocalEarlyQuitWaitingForServerNotifyDoEnd
        v_u_84:es_gamelocal_get_audiomanager():notify_local_early_quit()
        v_u_84:es_gamelocal_get_scoremanager():notify_local_early_quit()
        p106:add_finished_popup()
    end;
    v_u_37.debug_any_press = function(_) --[[ Name: debug_any_press ]] --[[ Line: 451 ]]
        --[[ Upvalues: (ref 1): v_u_88 ]]
        v_u_88 = 0
    end;
    local v_u_107 = nil
    v_u_37.get_finished_popup = function(_) --[[ Name: get_finished_popup ]] --[[ Line: 457 ]]
        --[[ Upvalues: (ref 1): v_u_107 ]]
        return v_u_107;
    end;
    v_u_37.add_finished_popup = function(p_u_108) --[[ Name: add_finished_popup ]] --[[ Line: 458 ]]
        --[[ Upvalues: (ref 1): v_u_107, (ref 2): v_u_84, (ref 3): v_u_32, (copy 4): p_u_34, (ref 5): v_u_1, (ref 6): v_u_16 ]]
        local v_u_109 = 0
        v_u_107 = v_u_84._menus:push_menu(v_u_32:new(p_u_34, v_u_84._spui, v_u_84._menus):set_text("Loading...", "Please wait(0)..."):set_close_button_visible(false):set_update_fn(function(p110, p111) --[[ Line: 465 ]]
            --[[ Upvalues: (ref 1): v_u_84, (ref 2): v_u_107, (ref 3): p_u_34, (ref 4): v_u_109, (ref 5): v_u_1, (copy 6): p_u_108, (ref 7): v_u_16 ]]
            if v_u_84 == nil then
                if v_u_107 ~= nil then
                    p_u_34._menus:remove_menu(v_u_107)
                    v_u_107 = nil
                end;
            else
                local v112 = v_u_109
                v_u_109 = v_u_109 + v_u_1:TimescaleToDeltaTime(p110)
                p111:set_text("Loading...", string.format("Please wait(%d)...", (math.floor(v_u_109))))
                if v112 < 8 and v_u_109 >= 8 then
                    p_u_108:create_game_end_ui()
                    v_u_16:warnf("GameLocal:add_finished_popup timed out, self:create_game_end_ui")
                end;
            end;
        end))
    end;
    local v_u_113 = nil
    v_u_37.create_game_end_ui = function(_, p114) --[[ Name: create_game_end_ui ]] --[[ Line: 487 ]]
        --[[ Upvalues: (ref 1): v_u_113, (ref 2): v_u_84, (ref 3): v_u_6, (ref 4): v_u_107, (ref 5): v_u_31, (copy 6): p_u_34 ]]
        if v_u_113 == nil then
            v_u_84._sfx_manager:play_sfx(v_u_6.SFX_ENDCHEER_1)
            v_u_84._sfx_manager:play_sfx(v_u_6.SFX_FANFARE)
            if v_u_107 ~= nil then
                v_u_84._menus:remove_menu(v_u_107)
                v_u_107 = nil
            end;
            v_u_84._ui_manager:teardown(v_u_84)
            v_u_113 = v_u_31:new(p_u_34, v_u_84)
            v_u_84._menus:push_menu(v_u_113)
        end;
        if p114 ~= nil then
            p114(v_u_113)
        end;
        return v_u_113;
    end;
    v_u_37.load_game_end_menu = function(p_u_115, p_u_116) --[[ Name: load_game_end_menu ]] --[[ Line: 505 ]]
        --[[ Upvalues: (ref 1): v_u_84, (ref 2): v_u_16, (ref 3): v_u_12, (ref 4): v_u_4, (ref 5): v_u_28 ]]
        if v_u_84 == nil then
            return v_u_16:warnf("GameLocal:load_game_end_menu _game is nil");
        end;
        local function v_u_117() --[[ Line: 508 ]]
            --[[ Upvalues: (ref 1): v_u_117, (copy 2): p_u_115, (copy 3): p_u_116 ]]
            v_u_117 = nil
            return p_u_115:create_game_end_ui(p_u_116);
        end;
        if v_u_84:is_networked() then
            v_u_84._evt:wait_on_event_once(v_u_12.EVT_Game_ServerNotifyMatchEndRewards, function(p_u_118) --[[ Line: 514 ]]
                --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_4, (ref 3): v_u_84, (ref 4): v_u_117, (ref 5): v_u_28 ]]
                v_u_16:puts("EVT_Game_ServerNotifyMatchEndRewards %s", v_u_4:table_to_string(p_u_118))
                v_u_84._player_blob_manager:do_sync(function() --[[ Line: 517 ]]
                    --[[ Upvalues: (ref 1): v_u_117, (copy 2): p_u_118, (ref 3): v_u_28, (ref 4): v_u_84 ]]
                    if v_u_117 then
                        v_u_117():update_reward_info(p_u_118)
                        if p_u_118.SpecialEventData ~= nil then
                            v_u_28:push_eventmission_match_end_menu(v_u_84, p_u_118.SpecialEventData)
                        end;
                    end;
                end)
            end)
            spawn(function() --[[ Line: 527 ]]
                --[[ Upvalues: (ref 1): v_u_117 ]]
                local v119 = 0
                while v119 < 8 do
                    if v_u_117 == nil then
                        return;
                    end;
                    wait(0.5)
                    v119 = v119 + 0.5
                end;
                if v_u_117 then
                    v_u_117()
                end;
            end)
        elseif v_u_117 then
            v_u_117()
        end;
    end;
    v_u_37.exit_to_lobby = function(_, p120) --[[ Name: exit_to_lobby ]] --[[ Line: 541 ]]
        --[[ Upvalues: (ref 1): p_u_36, (ref 2): v_u_16 ]]
        if p_u_36 == nil then
            v_u_16:warnf("GameLocal:exit_to_lobby _game_join is nil")
        else
            p_u_36:exit_to_lobby(p120)
        end;
    end;
    v_u_37.teardown_game = function(_) --[[ Name: teardown_game ]] --[[ Line: 550 ]]
        --[[ Upvalues: (ref 1): v_u_84, (ref 2): v_u_16, (ref 3): v_u_85, (copy 4): v_u_41, (ref 5): v_u_89, (ref 6): v_u_33, (ref 7): v_u_87, (ref 8): v_u_12, (ref 9): p_u_36 ]]
        if v_u_84 == nil then
            return v_u_16:warnf("GameLocal:teardown_game _game is already nil");
        end;
        v_u_85 = v_u_41
        v_u_89 = v_u_33.Mode.DoRemove
        if v_u_87 then
            v_u_87:teardown()
        end;
        v_u_87 = nil
        v_u_84._evt:remove_waits_on(v_u_12.EVT_Spectate_ServerResyncNoteSequence)
        v_u_84._evt:remove_waits_on(v_u_12.EVT_Game_ServerUpdatePlayerInfo)
        v_u_84._evt:remove_waits_on(v_u_12.EVT_Game_ServerNotifyDoEnd)
        v_u_84._evt:remove_waits_on(v_u_12.EVT_Game_ServerNotifyMatchEndRewards)
        for _, v121 in v_u_84:es_gamelocal_get_tracksystems():key_itr() do
            v121:es_teardown(v_u_84)
        end;
        v_u_84:es_gamelocal_get_tracksystems():clear(v_u_84)
        v_u_84:es_gamelocal_get_audiomanager():teardown(v_u_84)
        v_u_84:es_gamelocal_get_scoremanager():teardown(v_u_84)
        v_u_84._ui_manager:teardown(v_u_84)
        v_u_84._players:teardown(v_u_84)
        v_u_84._characters:teardown(v_u_84)
        v_u_84._world_effect_manager:teardown(v_u_84)
        v_u_84._effects:teardown(v_u_84)
        v_u_84 = nil
        p_u_36 = nil
    end;
    local l_Game_0 = v_u_33.Mode.Game
    v_u_37.set_paused = function(_, p122) --[[ Name: set_paused ]] --[[ Line: 584 ]]
        --[[ Upvalues: (ref 1): l_Game_0, (ref 2): v_u_89, (ref 3): v_u_33, (ref 4): v_u_84 ]]
        if p122 == true then
            l_Game_0 = v_u_89
            v_u_89 = v_u_33.Mode.Paused
        else
            v_u_89 = l_Game_0
        end;
        v_u_84:es_gamelocal_get_audiomanager():set_paused(p122)
        v_u_84._characters:set_paused(p122)
    end;
    local v_u_123 = nil
    v_u_37.is_ingame_sfx_enabled = function(_) --[[ Name: is_ingame_sfx_enabled ]] --[[ Line: 598 ]]
        --[[ Upvalues: (ref 1): v_u_123, (ref 2): v_u_84, (ref 3): v_u_20 ]]
        if v_u_123 == nil then
            v_u_123 = v_u_84._player_settings_manager:get_key(v_u_20.Key.HitSFX)
        end;
        return v_u_123;
    end;
    v_u_37.start_spectate_manager = function(p124, p125, p126) --[[ Name: start_spectate_manager ]] --[[ Line: 605 ]]
        --[[ Upvalues: (ref 1): v_u_85, (copy 2): v_u_41, (ref 3): v_u_89, (ref 4): v_u_33, (ref 5): v_u_87, (ref 6): v_u_21, (copy 7): p_u_34, (copy 8): f_setup_tracksystems_fn ]]
        v_u_85 = v_u_41
        v_u_89 = v_u_33.Mode.SpectateLoading
        v_u_87 = v_u_21:new(p_u_34, p124, p125, p126)
        f_setup_tracksystems_fn()
        v_u_87:start()
        v_u_85 = nil
    end;
    v_u_37.set_skip_to_time_ms = function(_, p127) --[[ Name: set_skip_to_time_ms ]] --[[ Line: 615 ]]
        --[[ Upvalues: (ref 1): v_u_85, (copy 2): v_u_41, (ref 3): v_u_84 ]]
        v_u_85 = v_u_41
        v_u_84:es_gamelocal_get_audiomanager():set_skip_to_time_ms(p127)
        v_u_85 = nil
    end;
    return v_u_37;
end;
return v_u_33;
