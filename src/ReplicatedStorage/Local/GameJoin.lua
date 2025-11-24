-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:25 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_1 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_3 = require(game.ReplicatedStorage.Local.GameLocal)
local v_u_4 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.LocalShared.BGMManager)
require(game.ReplicatedStorage.LocalShared.AdornPool)
local v_u_6 = require(game.ReplicatedStorage.Tutorial.TutorialData)
local v_u_7 = require(game.ReplicatedStorage.Local.GameJoinProtocol)
local v_u_8 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_9 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
local v_u_10 = require(game.ReplicatedStorage.Shared.GameDanceInfo)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_12 = require(game.ReplicatedStorage.GameStage.GameStageDatabase)
local v_u_13 = require(game.ReplicatedStorage.Shared.MatchMakingSettings)
local v_u_14 = require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
local v15 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
local v_u_19 = nil
local v_u_20 = nil
local v_u_21 = nil
v15:require_client(function() --[[ Line: 31 ]]
    --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_18, (ref 4): v_u_19, (ref 5): v_u_20, (ref 6): v_u_21 ]]
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.GameStartV2UI)
    v_u_18 = require(game.ReplicatedStorage.GameUI.SpectateUI)
    v_u_19 = require(game.ReplicatedStorage.PreviewGame.PreviewGameLocal)
    v_u_20 = require(game.ReplicatedStorage.EditorGame.Game.EditorGameLocal)
    v_u_21 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
end)
return {
    ["new"] = function(_, p_u_22) --[[ Name: new ]] --[[ Line: 42 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_9, (copy 3): v_u_1, (copy 4): v_u_10, (copy 5): v_u_5, (copy 6): v_u_3, (copy 7): v_u_8, (copy 8): v_u_11, (copy 9): v_u_6, (copy 10): v_u_7, (ref 11): v_u_17, (copy 12): v_u_2, (ref 13): v_u_18, (copy 14): v_u_13, (ref 15): v_u_16, (copy 16): v_u_12, (ref 17): v_u_19, (copy 18): v_u_14, (ref 19): v_u_20, (ref 20): v_u_21 ]]
        local v23 = {}
        local v_u_24 = nil
        local v_u_25 = false
        local v_u_26 = v_u_4:invalid_songkey()
        v23.set_last_loaded_songkey = function(_, p27) --[[ Name: set_last_loaded_songkey ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            v_u_26 = p27
        end;
        v23.get_last_loaded_songkey = function(_, _) --[[ Name: get_last_loaded_songkey ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            return v_u_26;
        end;
        v23.get_game = function(_) --[[ Name: get_game ]] --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            return v_u_24;
        end;
        v23.load_game = function(p28, _, p29, p30, p31, p32, p33, p34, p35, p36, p37) --[[ Name: load_game ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_9, (ref 3): v_u_1, (ref 4): v_u_10, (copy 5): p_u_22, (ref 6): v_u_5, (ref 7): v_u_24, (ref 8): v_u_3, (ref 9): v_u_8, (ref 10): v_u_11 ]]
            v_u_26 = p29
            if p34 == nil then
                p34 = v_u_9:new()
                v_u_1:warnf("GameJoin:load_game game_note_skin_info is nil")
            end;
            if p35 == nil then
                p35 = v_u_10:get_default_dance_info()
                v_u_1:warnf("GameJoin:load_game game_dance_info is nil")
            end;
            p_u_22._bgm_manager:stop_bgm()
            v_u_5:set_mode(v_u_5.Mode.Game)
            p_u_22._input:set_keyboard_focused_mode(true)
            v_u_24 = v_u_3:new(p_u_22, v_u_5:get_game_environment_center_cframe(), p28)
            if p33 then
                v_u_24:set_as_tutorial()
            end;
            if v_u_8:test_enum_member(p36, v_u_11.EventMission) == true then
                v_u_24:set_event_info(p36)
            end;
            if p37 then
                p37(v_u_24)
            end;
            v_u_24:es_gamelocal_get_audiomanager():load_song(p29)
            v_u_24:setup_world(p30, p31, p32, p34, p35)
            p_u_22._adorn_pool:shuffle()
        end;
        v23.start_game_tutorial_mode = function(_, _) --[[ Name: start_game_tutorial_mode ]] --[[ Line: 97 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7, (copy 3): p_u_22, (ref 4): v_u_17 ]]
            local v38 = v_u_6:get_tutorial_play_songkey()
            local v39, v40 = v_u_6:get_player_info_data()
            local v41 = v_u_6:get_gear_info_data()
            local v42 = v_u_7:new(p_u_22)
            v42:set_networked(false)
            v42:set_tutorial(true)
            v42:set_slot(v39)
            v42:set_player_info(v40)
            v42:set_gear_info(v41)
            v42:set_selected_song_key(v38)
            v42:set_mode(v_u_7.Mode.ServerNotifyClientDoPreload)
            v_u_6:game_join_protocol_initialize(v42)
            p_u_22._menus:push_menu(v_u_17:new(p_u_22, p_u_22._spui, p_u_22._menus, v42))
        end;
        v23.teardown_game = function(_, _) --[[ Name: teardown_game ]] --[[ Line: 116 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25 ]]
            if v_u_24 ~= nil then
                v_u_25 = false
                v_u_24:teardown_game()
                v_u_24 = nil
            end;
        end;
        v23.exit_to_lobby = function(p43, p_u_44) --[[ Name: exit_to_lobby ]] --[[ Line: 123 ]]
            --[[ Upvalues: (ref 1): v_u_24, (copy 2): p_u_22, (ref 3): v_u_2 ]]
            if v_u_24 ~= nil then
                if v_u_24:is_networked() == true then
                    p_u_22._evt:fire_event_to_server(v_u_2.EVT_Game_ClientNotifyLeaveEndedGame)
                end;
                p43:teardown_game()
                p_u_22._lobby_join:setup_lobby(p_u_22)
                if p_u_44 and p_u_22._lobby_join:get_lobby() then
                    p_u_22._lobby_join:get_lobby():enqueue_loaded_callback(function() --[[ Line: 134 ]]
                        --[[ Upvalues: (copy 1): p_u_44, (ref 2): p_u_22 ]]
                        p_u_44(p_u_22)
                    end)
                end;
                p_u_22._lobby_join:start_lobby(p_u_22)
            end;
        end;
        v23.is_game_audio_loaded = function(_) --[[ Name: is_game_audio_loaded ]] --[[ Line: 142 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            if v_u_24 == nil then
                return false;
            else
                return v_u_24:es_gamelocal_get_audiomanager():is_ready_to_play();
            end;
        end;
        v23.is_game_images_loaded = function(_) --[[ Name: is_game_images_loaded ]] --[[ Line: 147 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            return v_u_5:get_image_loader():get_preload_game_asset_count() > 0;
        end;
        v23.is_game_stage_loaded = function(_) --[[ Name: is_game_stage_loaded ]] --[[ Line: 152 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            if v_u_24 == nil then
                return false;
            else
                return v_u_24:es_gamelocal_get_worldeffectmanager():is_game_stage_loaded();
            end;
        end;
        v23.load_retry = function(_) --[[ Name: load_retry ]] --[[ Line: 157 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            if v_u_24 then
                v_u_24:es_gamelocal_get_audiomanager():load_retry()
            end;
        end;
        v23.is_game_finished = function(_) --[[ Name: is_game_finished ]] --[[ Line: 163 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            if v_u_24 == nil then
                return false;
            else
                return v_u_24:es_gamelocal_get_audiomanager():is_finished();
            end;
        end;
        v23.is_game_early_quit = function(_) --[[ Name: is_game_early_quit ]] --[[ Line: 168 ]]
            --[[ Upvalues: (ref 1): v_u_24 ]]
            if v_u_24 == nil then
                return false;
            else
                return v_u_24:es_gamelocal_get_audiomanager():did_early_quit();
            end;
        end;
        v23.start_game = function(_, p45) --[[ Name: start_game ]] --[[ Line: 173 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25, (ref 3): v_u_5 ]]
            if v_u_24 ~= nil then
                v_u_24:start_game(p45)
                v_u_25 = true
                v_u_5:should_load_textures(false)
            end;
        end;
        v23.start_game_spectate = function(p_u_46, _, p47, p48, p49, p50, p_u_51, p52, p53) --[[ Name: start_game_spectate ]] --[[ Line: 182 ]]
            --[[ Upvalues: (ref 1): v_u_8, (copy 2): p_u_22, (ref 3): v_u_9, (ref 4): v_u_10, (ref 5): v_u_24, (ref 6): v_u_1, (ref 7): v_u_18, (ref 8): v_u_25, (ref 9): v_u_5 ]]
            v_u_8:is_table(p_u_22)
            v_u_8:is_int(p47)
            v_u_8:is_table(p48)
            v_u_8:is_int(p49)
            v_u_8:is_table(p50)
            v_u_8:is_int(p_u_51)
            v_u_8:is_true(p52.Type == v_u_9.Type)
            v_u_8:is_true(p53.Type == v_u_10.Type)
            p_u_46:load_game(p_u_22, p47, p49, p48, p50, false, p52, p53, nil, function(p54) --[[ Line: 202 ]]
                p54:set_as_spectate()
            end)
            local v_u_55 = v_u_24
            spawn(function() --[[ Line: 208 ]]
                --[[ Upvalues: (copy 1): p_u_46, (ref 2): v_u_24, (copy 3): v_u_55, (ref 4): v_u_1, (ref 5): p_u_22, (ref 6): v_u_18, (copy 7): p_u_51, (ref 8): v_u_25, (ref 9): v_u_5 ]]
                while p_u_46:is_game_stage_loaded() ~= true do
                    wait(0.1)
                end;
                if v_u_24 ~= v_u_55 then
                    return v_u_1:warnf("GameJoin:start_game_spectate _game does not match current_preview_game");
                end;
                v_u_24:start_spectate_manager(p_u_22._menus:push_menu(v_u_18:new(v_u_24, p_u_22._spui, p_u_22._menus)), p_u_51)
                v_u_25 = true
                v_u_5:should_load_textures(true)
            end)
        end;
        v23.start_preview_game = function(p_u_56, p57) --[[ Name: start_preview_game ]] --[[ Line: 220 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_13, (ref 3): v_u_16, (ref 4): v_u_12, (ref 5): v_u_9, (copy 6): p_u_22, (ref 7): v_u_10, (ref 8): v_u_5, (ref 9): v_u_24, (ref 10): v_u_19, (ref 11): v_u_4, (ref 12): v_u_26, (ref 13): v_u_1, (ref 14): v_u_25 ]]
            local v60, v61, _ = v_u_6:get_player_info_data(function(p58) --[[ Line: 221 ]]
                --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_16, (ref 3): v_u_12 ]]
                local v59 = v_u_13:get_selected_game_stage(v_u_16:get_local_matchmaking_settings())
                if v_u_12:singleton():contains_stageid(v59) then
                    p58._stage_id = v59
                end;
            end)
            local v62 = v_u_9:new()
            local v63 = p_u_22._player_blob_manager:get_player_blob()
            v62:add_playerblob_to_slot(v63, v60)
            local v64 = v_u_10:get_default_dance_info()
            v64:add_playerblob_to_slot(v63, v60)
            p_u_22._bgm_manager:stop_bgm()
            v_u_5:set_mode(v_u_5.Mode.Game)
            p_u_22._input:set_keyboard_focused_mode(true)
            v_u_24 = v_u_19:new(p_u_22, v_u_5:get_game_environment_center_cframe(), p_u_56, p57)
            local v_u_65 = v_u_24
            local v66 = not v_u_4:singleton():contains_key(v_u_26) and 236 or v_u_26
            v_u_24:es_gamelocal_get_audiomanager():load_song(v66)
            v_u_24:setup_world(v60, v61, v_u_6:get_gear_info_data_for_playerblob(v63, p_u_22._player_blob_manager:get_day_id(), p_u_22._player_blob_manager:get_week_id()), v62, v64)
            p_u_22._adorn_pool:shuffle()
            v_u_24._camera_manager:finish_camera_transition()
            spawn(function() --[[ Line: 259 ]]
                --[[ Upvalues: (copy 1): p_u_56, (ref 2): v_u_24, (copy 3): v_u_65, (ref 4): v_u_1, (ref 5): v_u_25, (ref 6): v_u_5 ]]
                while p_u_56:is_game_audio_loaded() ~= true do
                    wait(0.1)
                end;
                while p_u_56:is_game_stage_loaded() ~= true do
                    wait(0.1)
                end;
                if v_u_24 ~= v_u_65 then
                    return v_u_1:warnf("GameJoin:start_preview_game _game does not match current_preview_game");
                end;
                v_u_24:start_game(-1)
                v_u_25 = true
                v_u_5:should_load_textures(false)
                v_u_24:set_skip_to_time_ms(0)
            end)
            return v66;
        end;
        v23.start_editor_custom_map_game = function(p_u_67, p68, p69, p70) --[[ Name: start_editor_custom_map_game ]] --[[ Line: 275 ]]
            --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_6, (ref 3): v_u_13, (ref 4): v_u_16, (ref 5): v_u_12, (ref 6): v_u_14, (ref 7): v_u_9, (ref 8): v_u_10, (ref 9): v_u_5, (ref 10): v_u_24, (ref 11): v_u_20, (ref 12): v_u_21, (ref 13): v_u_1, (ref 14): v_u_25 ]]
            local v_u_71 = p_u_22._player_blob_manager:get_player_blob()
            local v74, v75, _ = v_u_6:get_player_info_data(function(p72) --[[ Line: 277 ]]
                --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_16, (ref 3): v_u_12, (ref 4): v_u_14, (copy 5): v_u_71 ]]
                local v73 = v_u_13:get_selected_game_stage(v_u_16:get_local_matchmaking_settings())
                if v_u_12:singleton():contains_stageid(v73) then
                    p72._stage_id = v73
                end;
                v_u_14:copy_icon_and_title_from_playerblob(p72, v_u_71, false, nil)
            end)
            local v76 = v_u_9:new()
            v76:add_playerblob_to_slot(v_u_71, v74)
            local v77 = v_u_10:get_default_dance_info()
            v77:add_playerblob_to_slot(v_u_71, v74)
            p_u_22._bgm_manager:stop_bgm()
            v_u_5:set_mode(v_u_5.Mode.Game)
            p_u_22._input:set_keyboard_focused_mode(true)
            v_u_24 = v_u_20:new(p_u_22, v_u_5:get_game_environment_center_cframe(), p68, p69, p70)
            local v_u_78 = v_u_24
            v_u_24:es_gamelocal_get_audiomanager():load_song_key_with_custom_data(p68:get_source_songkey(), p69)
            v_u_24:setup_world(v74, v75, v_u_6:get_gear_info_data_for_playerblob(v_u_71, p_u_22._player_blob_manager:get_day_id(), p_u_22._player_blob_manager:get_week_id()), v76, v77)
            p_u_22._adorn_pool:shuffle()
            local v_u_79 = nil
            v_u_79 = p_u_22._menus:push_menu(v_u_21:new(p_u_22, p_u_22._spui, p_u_22._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false):set_update_fn(function() --[[ Line: 316 ]]
                --[[ Upvalues: (copy 1): p_u_67, (ref 2): p_u_22, (ref 3): v_u_79 ]]
                if p_u_67:is_game_audio_loaded() == true and p_u_67:is_game_stage_loaded() == true then
                    p_u_22._menus:remove_menu(v_u_79)
                end;
            end):set_on_close_fn(function() --[[ Line: 321 ]]
                --[[ Upvalues: (ref 1): v_u_24, (copy 2): v_u_78, (ref 3): v_u_1, (ref 4): v_u_25, (ref 5): v_u_5 ]]
                if v_u_24 ~= v_u_78 then
                    return v_u_1:warnf("GameJoin:start_editor_custom_map_game _game does not match current_preview_game");
                end;
                v_u_24:start_game(-1)
                v_u_25 = true
                v_u_5:should_load_textures(false)
            end))
        end;
        v23.update = function(_, p80) --[[ Name: update ]] --[[ Line: 332 ]]
            --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_24 ]]
            if v_u_25 and v_u_24 then
                v_u_24:update(p80)
            end;
        end;
        v23.post_update = function(_, p81) --[[ Name: post_update ]] --[[ Line: 338 ]]
            --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_24 ]]
            if v_u_25 and v_u_24 then
                v_u_24:post_update(p81)
            end;
        end;
        return v23;
    end
};
