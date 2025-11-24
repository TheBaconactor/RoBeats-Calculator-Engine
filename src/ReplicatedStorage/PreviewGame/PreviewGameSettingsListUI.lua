-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:09 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_6 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_7 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_8 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_9 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_10 = require(game.ReplicatedStorage.PreviewGame.PreviewGameStartupMenu)
local v_u_11 = require(game.ReplicatedStorage.Shared.NoteResultPositionSetting)
local v_u_12 = require(game.ReplicatedStorage.Shared.NoteResultSpreadSetting)
local v13 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
local v_u_17 = nil
local v_u_18 = nil
v13:require_client(function() --[[ Line: 27 ]]
    --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15, (ref 3): v_u_16, (ref 4): v_u_17, (ref 5): v_u_18 ]]
    v_u_14 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_15 = require(game.ReplicatedStorage.LocalShared.LocalSharedSettingsUIUtil)
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.NoteColorSelectV2UI)
    v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.KeyBindsUI)
    v_u_18 = require(game.ReplicatedStorage.Lobby.Menus.ValueInputUI)
end)
return {
    ["new"] = function(_, p_u_19, p_u_20) --[[ Name: new ]] --[[ Line: 37 ]]
        --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_1, (copy 3): v_u_4, (copy 4): v_u_5, (copy 5): v_u_3, (copy 6): v_u_2, (ref 7): v_u_17, (ref 8): v_u_14, (ref 9): v_u_15, (copy 10): v_u_7, (ref 11): v_u_16, (copy 12): v_u_11, (copy 13): v_u_8, (copy 14): v_u_12, (ref 15): v_u_18, (copy 16): v_u_6, (copy 17): v_u_10 ]]
        local v_u_21 = nil
        local function f_refresh_note_display_mode() --[[ Name: refresh_note_display_mode ]] --[[ Line: 42 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_9, (ref 3): v_u_21 ]]
            p_u_19._spui:force_layout_updated()
            local v22 = p_u_19:get_local_game_slot()
            local v23 = p_u_19:es_gamelocal_get_local_tracksystem()
            if v23 then
                local v24 = v_u_9:new()
                local v25 = p_u_19._player_blob_manager:get_player_blob()
                p_u_19._player_settings_manager:local_write_settings_to_playerblob(v25)
                v24:add_playerblob_to_slot(v25, v22)
                v23:set_game_noteskin_info(v24, v22)
                v23:on_switch_focus_slot()
            end;
            p_u_19._characters:update_show_characters()
            p_u_19._ui_manager:get_decal_ui_manager():calculate_screen_constants()
            v_u_21:refresh()
        end;
        local function f_set_list_select_ui_fill_transparent(p_u_26) --[[ Name: set_list_select_ui_fill_transparent ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_4, (copy 3): p_u_19, (ref 4): v_u_5, (ref 5): v_u_3, (ref 6): v_u_2 ]]
            local v27 = p_u_26:get_ui_root():FindFirstChild("Fill")
            if v27 then
                v_u_1:obj_set_alpha(v27, v_u_1:tra(v27.ImageTransparency), 1)
            end;
            local v28 = p_u_26:get_ui_root():FindFirstChild("SettingsSection")
            local v29 = v28 and v28:FindFirstChild("DialogueWindowFill")
            if v29 then
                v_u_1:obj_set_alpha(v29, v_u_1:tra(v29.ImageTransparency), 1)
            end;
            if p_u_26:get_settings_buttons():count() >= 1 then
                p_u_26:set_settings_section_visible()
                local v_u_30 = p_u_26:get_settings_buttons():pop_front()
                local function f_update_button_text() --[[ Name: update_button_text ]] --[[ Line: 78 ]]
                    --[[ Upvalues: (copy 1): p_u_26, (ref 2): v_u_4, (copy 3): v_u_30, (ref 4): v_u_1 ]]
                    if p_u_26:is_enabled() then
                        v_u_4:set_button_text(v_u_30, "Preview")
                    else
                        v_u_4:set_button_text(v_u_30, "Exit")
                    end;
                    v_u_1:r_set_alpha(v_u_30:get_part(), 1)
                end;
                v_u_30:bind_data(function() --[[ Line: 89 ]]
                    --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_5, (copy 3): p_u_26, (copy 4): f_update_button_text, (ref 5): v_u_3, (ref 6): v_u_1, (ref 7): v_u_2 ]]
                    p_u_19._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
                    local v31 = not p_u_26:is_enabled()
                    if v31 == false then
                        p_u_26:set_alpha(0)
                    else
                        p_u_26:set_alpha(1)
                    end;
                    p_u_26:set_enabled(v31)
                    f_update_button_text()
                    if v31 == true then
                        local v32 = p_u_19:get_tracked_note_results()
                        local v33 = v_u_3:new()
                        local v34 = ""
                        for _, v35 in v_u_1:noteresult_list():key_itr() do
                            v33:push_front(v35)
                        end;
                        for v36, v37 in v33:key_itr() do
                            v34 = v34 .. string.format("%s: %d", v_u_1:noteresult_to_string(v37), (v_u_2:counter_get(v32, v37)))
                            if v36 < v33:count() then
                                v34 = v34 .. " "
                            end;
                        end;
                        p_u_26:set_sub_text(v34)
                    else
                        p_u_19:reset_tracked_note_results()
                    end;
                end)
                v_u_30:set_visible(true)
                f_update_button_text()
                p_u_26:get_settings_buttons():clear()
            end;
        end;
        local function _() --[[ Name: show_keybinds_menu ]] --[[ Line: 127 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_17, (copy 3): f_refresh_note_display_mode ]]
            p_u_19._menus:push_menu(v_u_17:new(p_u_19, p_u_19._spui, p_u_19._menus, function() --[[ Line: 128 ]]
                --[[ Upvalues: (ref 1): f_refresh_note_display_mode ]]
                f_refresh_note_display_mode()
            end))
        end;
        local function f_show_note_speed_menu() --[[ Name: show_note_speed_menu ]] --[[ Line: 133 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_14, (copy 3): f_set_list_select_ui_fill_transparent, (ref 4): v_u_15, (ref 5): v_u_1, (ref 6): v_u_7, (copy 7): f_refresh_note_display_mode ]]
            p_u_19._menus:push_menu(v_u_14:new(p_u_19, p_u_19._spui, p_u_19._menus, function(p38) --[[ Line: 141 ]]
                --[[ Upvalues: (ref 1): f_set_list_select_ui_fill_transparent ]]
                f_set_list_select_ui_fill_transparent(p38)
                p38:set_header_text("Configure Note Speed")
                p38:get_element_list():push_back(-1)
                p38:get_element_list():push_back(-2)
            end, function(p39, p40, p41, _, p42) --[[ Line: 147 ]]
                --[[ Upvalues: (ref 1): v_u_15, (ref 2): p_u_19, (ref 3): v_u_1, (ref 4): v_u_7 ]]
                p42:get_description_display().Text = ""
                if p39 == -1 then
                    p40.Text = string.format("Set Note Speed (%s)", v_u_15:get_note_speed_display_text(p_u_19))
                    p41.Image = v_u_1:get_double_arrow_icon_assetid()
                    p42:get_description_display().Text = "Set the speed of which notes arrive."
                elseif p39 == -2 then
                    local v43 = p_u_19._player_settings_manager:get_key(v_u_7.Key.FixedNoteSpeed)
                    p40.Text = "Note Speed Fixed: " .. (v43 and "On" or "Off")
                    p41.Image = v_u_1:important_assetid()
                    if v43 == true then
                        p42:get_description_display().Text = "Note speed will be the same for all songs."
                        return;
                    end;
                    p42:get_description_display().Text = "Note speed will vary based on the song\'s intensity."
                end;
            end, function(p44, p45) --[[ Line: 164 ]]
                --[[ Upvalues: (ref 1): v_u_15, (ref 2): p_u_19, (ref 3): f_refresh_note_display_mode, (ref 4): v_u_7 ]]
                if p44 == -1 then
                    v_u_15:create_note_speed_menu(p_u_19, function() --[[ Line: 166 ]]
                        --[[ Upvalues: (ref 1): f_refresh_note_display_mode ]]
                        f_refresh_note_display_mode()
                    end)
                elseif p44 == -2 then
                    p_u_19._player_settings_manager:set_key(v_u_7.Key.FixedNoteSpeed, not p_u_19._player_settings_manager:get_key(v_u_7.Key.FixedNoteSpeed))
                    p45:refresh()
                    f_refresh_note_display_mode()
                end;
            end, nil, game.ReplicatedStorage.LobbyElementProtos.PreviewGameUIProto.PreviewGameSettingsListUI:Clone()):set_close_on_element_select(false))
        end;
        local function _() --[[ Name: show_note_offset_menu ]] --[[ Line: 182 ]]
            --[[ Upvalues: (ref 1): v_u_15, (copy 2): p_u_19, (copy 3): f_refresh_note_display_mode ]]
            v_u_15:create_note_offset_menu(p_u_19, function() --[[ Line: 183 ]]
                --[[ Upvalues: (ref 1): f_refresh_note_display_mode ]]
                f_refresh_note_display_mode()
            end)
        end;
        local function _() --[[ Name: show_note_color_menu ]] --[[ Line: 188 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_16, (copy 3): f_refresh_note_display_mode ]]
            p_u_19._menus:push_menu(v_u_16:new(p_u_19, p_u_19._spui, p_u_19._menus, function() --[[ Line: 189 ]]
                --[[ Upvalues: (ref 1): f_refresh_note_display_mode ]]
                f_refresh_note_display_mode()
            end))
        end;
        local function f_show_note_result_position_menu() --[[ Name: show_note_result_position_menu ]] --[[ Line: 194 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_14, (copy 3): f_set_list_select_ui_fill_transparent, (ref 4): v_u_11, (ref 5): v_u_1, (ref 6): v_u_7, (ref 7): v_u_8 ]]
            p_u_19._menus:push_menu(v_u_14:new(p_u_19, p_u_19._spui, p_u_19._menus, function(p46) --[[ Line: 200 ]]
                --[[ Upvalues: (ref 1): f_set_list_select_ui_fill_transparent, (ref 2): v_u_11 ]]
                f_set_list_select_ui_fill_transparent(p46)
                p46:set_header_text("Note Result Position")
                p46:get_element_list():push_back_from_list(v_u_11:keys_list())
            end, function(p47, p48, p49, _, p50) --[[ Line: 205 ]]
                --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_1, (ref 3): p_u_19, (ref 4): v_u_7 ]]
                p48.Text = v_u_11:key_to_name(p47)
                p49.Image = v_u_1:important_assetid()
                if p47 == p_u_19._player_settings_manager:get_key(v_u_7.Key.NoteResultPositionSetting) then
                    p50:get_description_display().Text = "Selected"
                else
                    p50:get_description_display().Text = ""
                end;
            end, function(p51, _) --[[ Line: 214 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_11, (ref 3): p_u_19, (ref 4): v_u_7 ]]
                if v_u_8:test_enum_member(p51, v_u_11) then
                    p_u_19._player_settings_manager:set_key(v_u_7.Key.NoteResultPositionSetting, p51)
                end;
            end, nil, game.ReplicatedStorage.LobbyElementProtos.PreviewGameUIProto.PreviewGameSettingsListUI:Clone()))
        end;
        local function f_show_note_result_spread_menu() --[[ Name: show_note_result_spread_menu ]] --[[ Line: 225 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_14, (copy 3): f_set_list_select_ui_fill_transparent, (ref 4): v_u_12, (ref 5): v_u_1, (ref 6): v_u_7, (ref 7): v_u_8 ]]
            p_u_19._menus:push_menu(v_u_14:new(p_u_19, p_u_19._spui, p_u_19._menus, function(p52) --[[ Line: 231 ]]
                --[[ Upvalues: (ref 1): f_set_list_select_ui_fill_transparent, (ref 2): v_u_12 ]]
                f_set_list_select_ui_fill_transparent(p52)
                p52:set_header_text("Note Result Spread")
                p52:get_element_list():push_back_from_list(v_u_12:keys_list())
            end, function(p53, p54, p55, _, p56) --[[ Line: 236 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_1, (ref 3): p_u_19, (ref 4): v_u_7 ]]
                p54.Text = v_u_12:key_to_name(p53)
                p55.Image = v_u_1:important_assetid()
                if p53 == p_u_19._player_settings_manager:get_key(v_u_7.Key.NoteResultSpreadSetting) then
                    p56:get_description_display().Text = "Selected"
                else
                    p56:get_description_display().Text = ""
                end;
            end, function(p57, _) --[[ Line: 245 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_12, (ref 3): p_u_19, (ref 4): v_u_7 ]]
                if v_u_8:test_enum_member(p57, v_u_12) then
                    p_u_19._player_settings_manager:set_key(v_u_7.Key.NoteResultSpreadSetting, p57)
                end;
            end, nil, game.ReplicatedStorage.LobbyElementProtos.PreviewGameUIProto.PreviewGameSettingsListUI:Clone()))
        end;
        local function f_show_additional_settings_menu() --[[ Name: show_additional_settings_menu ]] --[[ Line: 256 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_14, (copy 3): f_set_list_select_ui_fill_transparent, (ref 4): v_u_7, (ref 5): v_u_1, (ref 6): v_u_11, (ref 7): v_u_12, (copy 8): f_refresh_note_display_mode, (copy 9): f_show_note_result_position_menu, (copy 10): f_show_note_result_spread_menu ]]
            p_u_19._menus:push_menu(v_u_14:new(p_u_19, p_u_19._spui, p_u_19._menus, function(p58) --[[ Line: 268 ]]
                --[[ Upvalues: (ref 1): f_set_list_select_ui_fill_transparent ]]
                f_set_list_select_ui_fill_transparent(p58)
                p58:set_header_text("Additional Settings")
                p58:get_element_list():push_back(-1)
                p58:get_element_list():push_back(-2)
                p58:get_element_list():push_back(-3)
                p58:get_element_list():push_back(-4)
                p58:get_element_list():push_back(-5)
            end, function(p59, p60, p61, _, p62) --[[ Line: 277 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_7, (ref 3): v_u_1, (ref 4): v_u_11, (ref 5): v_u_12 ]]
                p62:get_description_display().Text = ""
                if p59 == -1 then
                    p60.Text = "Show Character: " .. (p_u_19._player_settings_manager:get_key(v_u_7.Key.GameShowCharacters) and "On" or "Off")
                    p61.Image = v_u_1:important_assetid()
                    p62:get_description_display().Text = "Show characters in-game."
                    return;
                elseif p59 == -2 then
                    p60.Text = "Show Held Note Tail: " .. (p_u_19._player_settings_manager:get_key(v_u_7.Key.ShowHeldNoteTail) and "On" or "Off")
                    p61.Image = v_u_1:important_assetid()
                    p62:get_description_display().Text = "Show the ends of held notes."
                    return;
                elseif p59 == -3 then
                    p60.Text = "Transparent Held Note: " .. (p_u_19._player_settings_manager:get_key(v_u_7.Key.HeldNoteTransparent) and "On" or "Off")
                    p61.Image = v_u_1:important_assetid()
                    p62:get_description_display().Text = "If the body of held notes should be transparent."
                    return;
                elseif p59 == -4 then
                    p60.Text = "Hit Result Position"
                    p61.Image = v_u_1:important_assetid()
                    p62:get_description_display().Text = v_u_11:key_to_name(p_u_19._player_settings_manager:get_key(v_u_7.Key.NoteResultPositionSetting))
                elseif p59 == -5 then
                    p60.Text = "Hit Result Spread"
                    p61.Image = v_u_1:important_assetid()
                    p62:get_description_display().Text = v_u_12:key_to_name(p_u_19._player_settings_manager:get_key(v_u_7.Key.NoteResultSpreadSetting))
                end;
            end, function(p63, p64) --[[ Line: 309 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_7, (ref 3): f_refresh_note_display_mode, (ref 4): f_show_note_result_position_menu, (ref 5): f_show_note_result_spread_menu ]]
                if p63 == -1 then
                    p_u_19._player_settings_manager:set_key(v_u_7.Key.GameShowCharacters, not p_u_19._player_settings_manager:get_key(v_u_7.Key.GameShowCharacters))
                    p64:refresh()
                    f_refresh_note_display_mode()
                    return;
                elseif p63 == -2 then
                    p_u_19._player_settings_manager:set_key(v_u_7.Key.ShowHeldNoteTail, not p_u_19._player_settings_manager:get_key(v_u_7.Key.ShowHeldNoteTail))
                    p64:refresh()
                    f_refresh_note_display_mode()
                    return;
                elseif p63 == -3 then
                    p_u_19._player_settings_manager:set_key(v_u_7.Key.HeldNoteTransparent, not p_u_19._player_settings_manager:get_key(v_u_7.Key.HeldNoteTransparent))
                    p64:refresh()
                    f_refresh_note_display_mode()
                    return;
                elseif p63 == -4 then
                    f_show_note_result_position_menu()
                elseif p63 == -5 then
                    f_show_note_result_spread_menu()
                end;
            end, nil, game.ReplicatedStorage.LobbyElementProtos.PreviewGameUIProto.PreviewGameSettingsListUI:Clone()):set_close_on_element_select(false):set_refresh_on_refocus(true))
        end;
        local function f_show_song_options_menu() --[[ Name: show_song_options_menu ]] --[[ Line: 341 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_14, (copy 3): f_set_list_select_ui_fill_transparent, (ref 4): v_u_1, (ref 5): v_u_18 ]]
            p_u_19._menus:push_menu(v_u_14:new(p_u_19, p_u_19._spui, p_u_19._menus, function(p65) --[[ Line: 350 ]]
                --[[ Upvalues: (ref 1): f_set_list_select_ui_fill_transparent ]]
                f_set_list_select_ui_fill_transparent(p65)
                p65:set_header_text("Song Options")
                p65:get_element_list():push_back(-1)
                p65:get_element_list():push_back(-2)
            end, function(p66, p67, p68, _, p69) --[[ Line: 356 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): p_u_19 ]]
                p69:get_description_display().Text = ""
                if p66 == -1 then
                    p67.Text = "Jump to Time"
                    p68.Image = v_u_1:get_iconhd_song()
                    p69:get_description_display().Text = "Jump to a specific time in the song."
                elseif p66 == -2 then
                    p67.Text = "Playback Speed"
                    p68.Image = v_u_1:get_double_arrow_icon_assetid()
                    p69:get_description_display().Text = string.format("x%.2f", p_u_19:es_gamelocal_get_audiomanager():get_playback_speed())
                end;
            end, function(p70, _) --[[ Line: 369 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_18, (ref 3): v_u_1 ]]
                if p70 == -1 then
                    p_u_19._menus:push_menu(v_u_18:new(p_u_19, p_u_19._spui, p_u_19._menus, math.floor(math.floor((p_u_19:es_gamelocal_get_audiomanager():get_current_time_ms())) / 5000) * 5000, function(p71) --[[ Line: 377 ]]
                        --[[ Upvalues: (ref 1): p_u_19 ]]
                        p_u_19:es_gamelocal_get_scoremanager():reset()
                        p_u_19:es_gamelocal_get_tracksystems():get(p_u_19:get_local_game_slot()):reset()
                        p_u_19:set_skip_to_time_ms(p71)
                    end):set_value_increment(5000):set_reset_value(0):set_range_min_max(0, p_u_19:es_gamelocal_get_audiomanager():get_song_length_ms()):set_title_sub_text("Jump to Song Time.", "Jump to a specific time (ms) in the previewed song."):set_value_display_info_fn(function(p72) --[[ Line: 389 ]]
                        --[[ Upvalues: (ref 1): v_u_1 ]]
                        return v_u_1:format_ms_time(p72), "Song Time";
                    end))
                elseif p70 == -2 then
                    p_u_19._menus:push_menu(v_u_18:new(p_u_19, p_u_19._spui, p_u_19._menus, p_u_19:es_gamelocal_get_audiomanager():get_playback_speed() * 100, function(p73) --[[ Line: 396 ]]
                        --[[ Upvalues: (ref 1): p_u_19 ]]
                        p_u_19:es_gamelocal_get_audiomanager():set_playback_speed(p73 / 100)
                    end):set_value_increment(10):set_reset_value(100):set_range_min_max(10, 400):set_title_sub_text("Playback Speed", "Set the playback speed of the previewed song."):set_value_display_info_fn(function(p74) --[[ Line: 406 ]]
                        return string.format("x%.2f", p74 / 100), "Speed Multiplier";
                    end))
                end;
            end, nil, game.ReplicatedStorage.LobbyElementProtos.PreviewGameUIProto.PreviewGameSettingsListUI:Clone()):set_close_on_element_select(false))
        end;
        v_u_21 = v_u_14:new(p_u_19, p_u_19._spui, p_u_19._menus, function(p75) --[[ Line: 430 ]]
            --[[ Upvalues: (copy 1): f_set_list_select_ui_fill_transparent, (ref 2): v_u_6, (copy 3): p_u_19, (ref 4): v_u_7, (ref 5): v_u_1 ]]
            f_set_list_select_ui_fill_transparent(p75)
            p75:set_header_text("Game Settings")
            p75:get_element_list():push_back(v_u_6.Default)
            p75:get_element_list():push_back(v_u_6.DecalDown)
            p75:get_element_list():push_back(v_u_6.DecalUp)
            if p_u_19._player_settings_manager:get_key(v_u_7.Key.NoteDisplayMode) ~= v_u_6.Default then
                p75:get_element_list():push_back(-1)
            end;
            p75:get_element_list():push_back(-3)
            if v_u_1:is_mobile() then
                p75:get_element_list():push_back(-5)
            end;
            if v_u_1:is_mobile() ~= true then
                p75:get_element_list():push_back(-6)
            end;
            p75:get_element_list():push_back(-8)
            p75:get_element_list():push_back(-2)
            p75:get_element_list():push_back(-4)
            p75:get_element_list():push_back(-7)
        end, function(p76, p77, p78, _, p79) --[[ Line: 452 ]]
            --[[ Upvalues: (ref 1): v_u_15, (copy 2): p_u_19, (ref 3): v_u_1, (ref 4): v_u_7, (ref 5): v_u_8, (ref 6): v_u_6 ]]
            p79:get_description_display().Text = ""
            if p76 == -1 then
                p77.Text = "2D Note Options"
                p78.Image = v_u_15:get_2d_mode_display_icon(p_u_19)
                p79:set_select_button_text("Open")
                p79:get_description_display().Text = "Configure 2D note appearance."
                return;
            elseif p76 == -2 then
                p77.Text = "Configure Note Colors"
                p78.Image = v_u_1:important_assetid()
                p79:set_select_button_text("Open")
                return;
            elseif p76 == -3 then
                p77.Text = "Configure Note Speed"
                p78.Image = v_u_1:get_double_arrow_icon_assetid()
                p79:set_select_button_text("Open")
                p79:get_description_display().Text = v_u_15:get_note_speed_display_text(p_u_19)
                return;
            elseif p76 == -4 then
                p77.Text = "Configure Audio Offset"
                p78.Image = v_u_1:get_question_assetid()
                p79:set_select_button_text("Open")
                p79:get_description_display().Text = v_u_15:get_note_offset_display_text(p_u_19)
                return;
            elseif p76 == -5 then
                local v80 = "Touch Fullscreen: "
                local v81
                if p_u_19._player_settings_manager:get_key(v_u_7.Key.MobileFullScreenUI) == true then
                    v81 = v80 .. "On"
                else
                    v81 = v80 .. "Off"
                end;
                p77.Text = v81
                p78.Image = v_u_1:important_assetid()
                p79:set_select_button_text("Toggle")
            elseif p76 == -6 then
                p77.Text = "Configure Keybinds"
                p78.Image = v_u_1:get_icon_keybinds_assetid()
                p79:set_select_button_text("Open")
                if v_u_1:is_mobile() ~= true then
                    p79:get_description_display().Text = "Press \"Preview\" to test your keybinds!"
                    return;
                end;
            else
                if p76 == -7 then
                    p77.Text = "Additional Settings"
                    p78.Image = v_u_1:gear_assetid()
                    p79:set_select_button_text("Open")
                    return;
                end;
                if p76 == -8 then
                    p77.Text = "Song Options"
                    p78.Image = v_u_1:get_iconhd_song()
                    p79:set_select_button_text("Open")
                    p79:get_description_display().Text = "Change song speed and jump to any time in the song."
                    return;
                end;
                if v_u_8:test_enum_member(p76, v_u_6) then
                    p77.Text = "Note Display: " .. v_u_6:display_mode_to_name(p76)
                    if p_u_19._player_settings_manager:get_key(v_u_7.Key.NoteDisplayMode) == p76 then
                        p79:get_description_display().Text = "Selected"
                    end;
                    p78.Image = v_u_6:display_mode_to_preview_assetid(p76)
                    p79:set_select_button_text("Select")
                end;
            end;
        end, function(p82) --[[ Line: 518 ]]
            --[[ Upvalues: (ref 1): v_u_15, (copy 2): p_u_19, (copy 3): f_set_list_select_ui_fill_transparent, (copy 4): f_refresh_note_display_mode, (ref 5): v_u_16, (copy 6): f_show_note_speed_menu, (ref 7): v_u_7, (ref 8): v_u_17, (copy 9): f_show_additional_settings_menu, (copy 10): f_show_song_options_menu, (ref 11): v_u_8, (ref 12): v_u_6 ]]
            if p82 == -1 then
                v_u_15:show_note_display_2d_settings_menu(p_u_19, false, game.ReplicatedStorage.LobbyElementProtos.PreviewGameUIProto.PreviewGameSettingsListUI:Clone(), function(p83) --[[ Line: 524 ]]
                    --[[ Upvalues: (ref 1): f_set_list_select_ui_fill_transparent ]]
                    f_set_list_select_ui_fill_transparent(p83)
                end, function() --[[ Line: 527 ]]
                    --[[ Upvalues: (ref 1): f_refresh_note_display_mode ]]
                    f_refresh_note_display_mode()
                end)
                return;
            elseif p82 == -2 then
                p_u_19._menus:push_menu(v_u_16:new(p_u_19, p_u_19._spui, p_u_19._menus, function() --[[ Line: 189 ]]
                    --[[ Upvalues: (ref 1): f_refresh_note_display_mode ]]
                    f_refresh_note_display_mode()
                end))
                return;
            elseif p82 == -3 then
                f_show_note_speed_menu()
                return;
            elseif p82 == -4 then
                v_u_15:create_note_offset_menu(p_u_19, function() --[[ Line: 183 ]]
                    --[[ Upvalues: (ref 1): f_refresh_note_display_mode ]]
                    f_refresh_note_display_mode()
                end)
                return;
            elseif p82 == -5 then
                p_u_19._player_settings_manager:set_key(v_u_7.Key.MobileFullScreenUI, not p_u_19._player_settings_manager:get_key(v_u_7.Key.MobileFullScreenUI))
                f_refresh_note_display_mode()
                return;
            elseif p82 == -6 then
                p_u_19._menus:push_menu(v_u_17:new(p_u_19, p_u_19._spui, p_u_19._menus, function() --[[ Line: 128 ]]
                    --[[ Upvalues: (ref 1): f_refresh_note_display_mode ]]
                    f_refresh_note_display_mode()
                end))
                return;
            elseif p82 == -7 then
                f_show_additional_settings_menu()
                return;
            elseif p82 == -8 then
                f_show_song_options_menu()
            elseif v_u_8:test_enum_member(p82, v_u_6) then
                p_u_19._player_settings_manager:set_key(v_u_7.Key.NoteDisplayMode, p82)
                f_refresh_note_display_mode()
            end;
        end, nil, game.ReplicatedStorage.LobbyElementProtos.PreviewGameUIProto.PreviewGameSettingsListUI:Clone()):set_close_on_element_select(false):set_fn_on_remove(function() --[[ Line: 565 ]]
            --[[ Upvalues: (copy 1): p_u_20 ]]
            p_u_20()
        end)
        local v_u_84 = v_u_2:new({
            [v_u_10.Keybinds] = -6,
            [v_u_10.NoteSpeed] = -3,
            [v_u_10.NoteOffset] = -4,
            [v_u_10.NoteColor] = -2
        })
        local v85 = v_u_2
        local v86 = {
            [v_u_10.NoteSpeed] = function() --[[ Line: 579 ]]
                --[[ Upvalues: (copy 1): f_show_note_speed_menu ]]
                f_show_note_speed_menu()
            end
        }
        v86[v_u_10.Keybinds] = function() --[[ Line: 576 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_17, (copy 3): f_refresh_note_display_mode ]]
            p_u_19._menus:push_menu(v_u_17:new(p_u_19, p_u_19._spui, p_u_19._menus, function() --[[ Line: 128 ]]
                --[[ Upvalues: (ref 1): f_refresh_note_display_mode ]]
                f_refresh_note_display_mode()
            end))
        end
        v86[v_u_10.NoteOffset] = function() --[[ Line: 582 ]]
            --[[ Upvalues: (ref 1): v_u_15, (copy 2): p_u_19, (copy 3): f_refresh_note_display_mode ]]
            v_u_15:create_note_offset_menu(p_u_19, function() --[[ Line: 183 ]]
                --[[ Upvalues: (ref 1): f_refresh_note_display_mode ]]
                f_refresh_note_display_mode()
            end)
        end
        v86[v_u_10.NoteColor] = function() --[[ Line: 585 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_16, (copy 3): f_refresh_note_display_mode ]]
            p_u_19._menus:push_menu(v_u_16:new(p_u_19, p_u_19._spui, p_u_19._menus, function() --[[ Line: 189 ]]
                --[[ Upvalues: (ref 1): f_refresh_note_display_mode ]]
                f_refresh_note_display_mode()
            end))
        end
        local v_u_87 = v85:new(v86)
        v_u_21.run_startup_menu = function(_, p88) --[[ Name: run_startup_menu ]] --[[ Line: 589 ]]
            --[[ Upvalues: (copy 1): v_u_84, (ref 2): v_u_21, (copy 3): v_u_87 ]]
            if v_u_84:contains(p88) then
                local v89 = v_u_21:get_list_adapter()
                v89:go_to_page((v89:get_page_of_element((v_u_84:get(p88)))))
            end;
            if v_u_87:contains(p88) then
                v_u_87:get(p88)()
            end;
        end;
        return v_u_21;
    end
};
