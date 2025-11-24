-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:11 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_10 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_11 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_12 = require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
local v_u_13 = require(game.ReplicatedStorage.Shared.WaitForFinish)
local v_u_14 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_15 = require(game.ReplicatedStorage.Lobby.UI.UIToggleGroup)
local v_u_16 = require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
local v_u_17 = require(game.ReplicatedStorage.LocalShared.CharacterCulling)
local v18 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_19 = nil
local v_u_20 = nil
local v_u_21 = nil
local v_u_22 = nil
local v_u_23 = nil
local v_u_24 = nil
local v_u_25 = nil
local v_u_26 = nil
local v_u_27 = nil
local v_u_28 = nil
v18:require_client(function() --[[ Line: 33 ]]
    --[[ Upvalues: (ref 1): v_u_19, (ref 2): v_u_20, (ref 3): v_u_21, (ref 4): v_u_22, (ref 5): v_u_23, (ref 6): v_u_24, (ref 7): v_u_25, (ref 8): v_u_26, (ref 9): v_u_27, (ref 10): v_u_28 ]]
    v_u_19 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_20 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
    v_u_21 = require(game.ReplicatedStorage.EditorGame.UI.Element.EditorNoteTrackDisplay)
    v_u_22 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI_SongProgressSection)
    v_u_23 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI_TimingPointMenu)
    v_u_24 = require(game.ReplicatedStorage.EditorGame.UI.SavedMapInfoListUI)
    v_u_25 = require(game.ReplicatedStorage.Menu.ScreenGuiTextBoxUI)
    v_u_26 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_27 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI_Util)
    v_u_28 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI_Publish)
end)
local v_u_29 = {
    ["get_restore_menu_name"] = function(_) --[[ Name: get_restore_menu_name ]] --[[ Line: 48 ]]
        return "EditorGameUI";
    end
}
local v_u_30 = v_u_16.SavedMapInfo:new()
local v_u_31 = v_u_16.CustomMapData:new()
local v_u_32 = 0
v_u_29.new = function(_, p_u_33, p_u_34, p_u_35) --[[ Name: new ]] --[[ Line: 54 ]]
    --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_30, (ref 3): v_u_31, (copy 4): v_u_16, (copy 5): v_u_10, (copy 6): v_u_3, (copy 7): v_u_29, (copy 8): v_u_2, (copy 9): v_u_17, (copy 10): v_u_9, (copy 11): v_u_5, (copy 12): v_u_4, (copy 13): v_u_7, (ref 14): v_u_21, (copy 15): v_u_11, (copy 16): v_u_12, (copy 17): v_u_15, (copy 18): v_u_1, (ref 19): v_u_23, (ref 20): v_u_25, (ref 21): v_u_19, (copy 22): v_u_8, (copy 23): v_u_6, (ref 24): v_u_28, (ref 25): v_u_27, (ref 26): v_u_22, (ref 27): v_u_32, (copy 28): v_u_13, (copy 29): v_u_14 ]]
    v_u_24:move_camera_to_editor_position(p_u_33)
    local v_u_36
    if p_u_34 == nil then
        p_u_34 = v_u_30
        v_u_36 = true
    else
        v_u_36 = false
    end;
    if p_u_35 == nil then
        p_u_35 = v_u_31
    end;
    if v_u_16:validate_saved_map_info(p_u_34) ~= true or v_u_10:singleton():key_get_audiomod(p_u_34:get_source_songkey()) ~= v_u_10.MOD_NORMAL then
        p_u_34:set_source_songkey(236)
    end;
    local l__spui_0 = p_u_33._spui
    local l__menus_0 = p_u_33._menus
    local v_u_37 = v_u_3:new(l__spui_0, l__menus_0)
    v_u_37.get_restore_name = function(_) --[[ Name: get_restore_name ]] --[[ Line: 75 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29:get_restore_menu_name();
    end;
    v_u_37.get_saved_map_info = function(_) --[[ Name: get_saved_map_info ]] --[[ Line: 77 ]]
        --[[ Upvalues: (ref 1): p_u_34 ]]
        return p_u_34;
    end;
    v_u_37.get_custom_map_data = function(_) --[[ Name: get_custom_map_data ]] --[[ Line: 78 ]]
        --[[ Upvalues: (ref 1): p_u_35 ]]
        return p_u_35;
    end;
    local v_u_38 = nil
    local v_u_39 = nil
    local v_u_40 = nil
    local v_u_41 = nil
    v_u_37.get_editor_note_track_display = function(_) --[[ Name: get_editor_note_track_display ]] --[[ Line: 85 ]]
        --[[ Upvalues: (ref 1): v_u_41 ]]
        return v_u_41;
    end;
    local v_u_42 = nil
    local v_u_43 = nil
    local v_u_44 = nil
    local v_u_45 = nil
    local v_u_46 = nil
    local function _() --[[ Name: update_song_info_map_name_display ]] --[[ Line: 93 ]]
        --[[ Upvalues: (ref 1): p_u_34, (ref 2): v_u_45 ]]
        if #p_u_34:get_custom_map_name() > 0 then
            v_u_45.Text = p_u_34:get_custom_map_name()
        else
            v_u_45.Text = p_u_34:get_default_custom_map_name()
        end;
    end;
    local function f_update_song_info_map_creator_display() --[[ Name: update_song_info_map_creator_display ]] --[[ Line: 100 ]]
        --[[ Upvalues: (ref 1): p_u_34, (ref 2): v_u_46 ]]
        if #p_u_34:get_custom_map_data_key() > 0 then
            v_u_46.Text = string.format("Creator: %s @ [%s]", p_u_34:get_creator_name(), os.date(nil, p_u_34:get_last_edit_time()))
        else
            v_u_46.Text = "Not Saved"
        end;
    end;
    local v_u_47 = v_u_2:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 113 ]]
        --[[ Upvalues: (copy 1): p_u_33, (ref 2): v_u_17, (ref 3): v_u_38, (ref 4): v_u_9, (ref 5): v_u_39, (copy 6): v_u_37, (ref 7): v_u_40, (ref 8): v_u_5, (ref 9): v_u_4, (copy 10): l__spui_0, (ref 11): v_u_24, (ref 12): v_u_7, (copy 13): l__menus_0, (ref 14): v_u_41, (ref 15): v_u_21, (ref 16): v_u_43, (ref 17): v_u_44, (ref 18): v_u_45, (ref 19): v_u_46, (ref 20): p_u_34, (copy 21): f_update_song_info_map_creator_display, (copy 22): v_u_47, (ref 23): v_u_11, (ref 24): v_u_12, (ref 25): v_u_15, (ref 26): v_u_2, (ref 27): v_u_1, (ref 28): v_u_23, (ref 29): v_u_25, (ref 30): v_u_16, (ref 31): p_u_35, (ref 32): v_u_19, (ref 33): v_u_8, (ref 34): v_u_6, (ref 35): v_u_28, (ref 36): v_u_27, (ref 37): v_u_42, (ref 38): v_u_22 ]]
        p_u_33._chat:store_chat_visible()
        p_u_33._chat:set_chat_visible(false)
        v_u_17:set_mode(v_u_17.Mode.None)
        v_u_38 = v_u_9:get_editor_game_proto_root().UI.EditorGameUI:Clone()
        v_u_39 = v_u_38.PrimaryPart.SurfaceGui
        v_u_37:set_showing(true)
        v_u_37._native_size = v_u_38.PrimaryPart.Size
        v_u_37._size = v_u_37._native_size
        v_u_40 = p_u_33._bgm_manager:begin_preview_songkey()
        p_u_33._bgm_manager:force_mute_bgm(true)
        v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, v_u_38.BackButtonSurface), l__spui_0, function() --[[ Line: 131 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): p_u_33, (ref 3): v_u_7, (ref 4): l__menus_0, (ref 5): v_u_37 ]]
            v_u_24:message_box_confirm(p_u_33, function() --[[ Line: 132 ]]
                --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_7, (ref 3): l__menus_0, (ref 4): v_u_37 ]]
                p_u_33._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
                l__menus_0:remove_menu(v_u_37)
            end)
        end))
        v_u_41 = v_u_21:new(p_u_33, v_u_38.PrimaryPart.SurfaceGui.Frame.NoteVisualizationSection, v_u_37)
        local l_Frame_0 = v_u_38.PrimaryPart.SurfaceGui.Frame
        v_u_43 = l_Frame_0.InfoDisplayTextSection.TextDisplay
        v_u_43.Text = ""
        v_u_44 = l_Frame_0.SongTimeDisplaySection.TimeDisplay
        v_u_44.Text = ""
        v_u_45 = l_Frame_0.SongInfoSection.MapNameDisplay
        v_u_46 = l_Frame_0.SongInfoSection.MapCreatorDisplay
        if #p_u_34:get_custom_map_name() > 0 then
            v_u_45.Text = p_u_34:get_custom_map_name()
        else
            v_u_45.Text = p_u_34:get_default_custom_map_name()
        end;
        f_update_song_info_map_creator_display()
        local v_u_48 = nil
        local v_u_49 = nil
        local function _() --[[ Name: fn_update_button_state ]] --[[ Line: 160 ]]
            --[[ Upvalues: (ref 1): v_u_48, (ref 2): v_u_41, (ref 3): v_u_5, (ref 4): v_u_49 ]]
            v_u_48:set_toggle(not v_u_41:is_playing())
            if v_u_41:is_playing() then
                v_u_5:set_button_text(v_u_49, "Pause")
            else
                v_u_5:set_button_text(v_u_49, "Play")
            end;
        end;
        v_u_49 = v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, v_u_38.UIButtons.PlayPauseButton), l__spui_0, function() --[[ Line: 171 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_48, (ref 3): v_u_5, (ref 4): v_u_49 ]]
            v_u_41:set_playing(not v_u_41:is_playing())
            v_u_48:set_toggle(not v_u_41:is_playing())
            if v_u_41:is_playing() then
                v_u_5:set_button_text(v_u_49, "Pause")
            else
                v_u_5:set_button_text(v_u_49, "Play")
            end;
        end)):set_auto_zoffset_behaviour(true)
        v_u_48 = v_u_5:button_bind_anim_toggle(v_u_49, function() --[[ Line: 176 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            return v_u_37:get_alpha();
        end):use_r_set_alpha_v2()
        v_u_48:set_toggle_off_alpha(0.75)
        v_u_47:push_back(function() --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11, (ref 3): v_u_41, (ref 4): v_u_49, (ref 5): v_u_48, (ref 6): v_u_5 ]]
            if p_u_33._input:control_just_pressed(v_u_11.KEY_EDITOR_PLAY_PAUSE) then
                v_u_41:set_playing(not v_u_41:is_playing())
                v_u_49:apply_triggered_scale_offset()
            end;
            if v_u_48:get_toggle() ~= not v_u_41:is_playing() then
                v_u_48:set_toggle(not v_u_41:is_playing())
                if v_u_41:is_playing() then
                    v_u_5:set_button_text(v_u_49, "Pause")
                    return;
                end;
                v_u_5:set_button_text(v_u_49, "Play")
            end;
        end)
        v_u_48:set_toggle(not v_u_41:is_playing())
        if v_u_41:is_playing() then
            v_u_5:set_button_text(v_u_49, "Pause")
        else
            v_u_5:set_button_text(v_u_49, "Play")
        end;
        local v_u_50 = nil
        local v_u_51 = nil
        local function _() --[[ Name: fn_update_button_state ]] --[[ Line: 191 ]]
            --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_41, (ref 3): v_u_5, (ref 4): v_u_51 ]]
            v_u_50:set_toggle(not v_u_41:is_autoplay_enabled())
            if v_u_41:is_autoplay_enabled() then
                v_u_5:set_button_text(v_u_51, "Auto On")
            else
                v_u_5:set_button_text(v_u_51, "Auto Off")
            end;
        end;
        v_u_51 = v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, v_u_38.UIButtons.AutoToggleButton), l__spui_0, function() --[[ Line: 202 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_50, (ref 3): v_u_5, (ref 4): v_u_51 ]]
            v_u_41:set_autoplay_enabled(not v_u_41:is_autoplay_enabled())
            v_u_50:set_toggle(not v_u_41:is_autoplay_enabled())
            if v_u_41:is_autoplay_enabled() then
                v_u_5:set_button_text(v_u_51, "Auto On")
            else
                v_u_5:set_button_text(v_u_51, "Auto Off")
            end;
        end)):set_auto_zoffset_behaviour(true)
        v_u_50 = v_u_5:button_bind_anim_toggle(v_u_51, function() --[[ Line: 207 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            return v_u_37:get_alpha();
        end):use_r_set_alpha_v2()
        v_u_50:set_toggle_off_alpha(0.75)
        v_u_47:push_back(function() --[[ Line: 209 ]]
            --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_41, (ref 3): v_u_5, (ref 4): v_u_51 ]]
            if v_u_50:get_toggle() ~= not v_u_41:is_autoplay_enabled() then
                v_u_50:set_toggle(not v_u_41:is_autoplay_enabled())
                if v_u_41:is_autoplay_enabled() then
                    v_u_5:set_button_text(v_u_51, "Auto On")
                    return;
                end;
                v_u_5:set_button_text(v_u_51, "Auto Off")
            end;
        end)
        v_u_50:set_toggle(not v_u_41:is_autoplay_enabled())
        if v_u_41:is_autoplay_enabled() then
            v_u_5:set_button_text(v_u_51, "Auto On")
        else
            v_u_5:set_button_text(v_u_51, "Auto Off")
        end;
        local v_u_52 = v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, v_u_38.UIButtons.SongProgressBackButton), l__spui_0, function() end)):set_auto_zoffset_behaviour(true):set_triggered_scale_offset(0.25)
        local v_u_53 = v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, v_u_38.UIButtons.SongProgressForwardButton), l__spui_0, function() end)):set_auto_zoffset_behaviour(true):set_triggered_scale_offset(0.25)
        local v_u_54 = false
        local function _(p55) --[[ Name: increment_song_time ]] --[[ Line: 230 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_12, (ref 3): v_u_54 ]]
            v_u_41:set_display_time_ms((math.max(v_u_41:get_display_time_ms() + p55, v_u_12:get_earliest_allowed_note_time_ms())))
            v_u_41:full_refresh_active_display_notes()
            v_u_41:update_playing_audio_state()
            v_u_54 = true
        end;
        v_u_47:push_back(function(p56) --[[ Line: 239 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): p_u_33, (ref 3): v_u_11, (ref 4): v_u_54, (ref 5): v_u_37, (copy 6): v_u_52, (ref 7): v_u_12, (copy 8): v_u_53 ]]
            local v57 = v_u_41:get_track_note_prebuffer_time_ms() * p56 * 0.035
            if p_u_33._input:control_pressed(v_u_11.KEY_EDITOR_MODIFIER_SHIFT) then
                v57 = v57 * 4
            end;
            local v58
            if p_u_33._input:control_pressed(v_u_11.KEY_EDITOR_MODIFIER_CTRL) == false then
                v58 = p_u_33._input:control_pressed(v_u_11.KEY_EDITOR_MODIFIER_ALT) == false
            else
                v58 = false
            end;
            v_u_54 = false
            if p_u_33._input:control_pressed(v_u_11.KEY_CLICK) then
                if v_u_37:get_triggered_element() == v_u_52 and v_u_37:get_frame_selected_element() == v_u_52 then
                    v_u_41:set_display_time_ms((math.max(v_u_41:get_display_time_ms() + -v57, v_u_12:get_earliest_allowed_note_time_ms())))
                    v_u_41:full_refresh_active_display_notes()
                    v_u_41:update_playing_audio_state()
                    v_u_54 = true
                elseif v_u_37:get_triggered_element() == v_u_53 and v_u_37:get_frame_selected_element() == v_u_53 then
                    v_u_41:set_display_time_ms((math.max(v_u_41:get_display_time_ms() + v57, v_u_12:get_earliest_allowed_note_time_ms())))
                    v_u_41:full_refresh_active_display_notes()
                    v_u_41:update_playing_audio_state()
                    v_u_54 = true
                end;
            elseif p_u_33._input:control_pressed(v_u_11.KEY_EDITOR_TIME_FORWARD) then
                v_u_53:apply_triggered_scale_offset()
                v_u_41:set_display_time_ms((math.max(v_u_41:get_display_time_ms() + v57, v_u_12:get_earliest_allowed_note_time_ms())))
                v_u_41:full_refresh_active_display_notes()
                v_u_41:update_playing_audio_state()
                v_u_54 = true
            elseif p_u_33._input:control_pressed(v_u_11.KEY_EDITOR_TIME_BACK) then
                v_u_52:apply_triggered_scale_offset()
                v_u_41:set_display_time_ms((math.max(v_u_41:get_display_time_ms() + -v57, v_u_12:get_earliest_allowed_note_time_ms())))
                v_u_41:full_refresh_active_display_notes()
                v_u_41:update_playing_audio_state()
                v_u_54 = true
            elseif p_u_33._input:control_pressed(v_u_11.KEY_SCROLL_UP) and v58 then
                local v59 = v57 * 4
                v_u_53:apply_triggered_scale_offset()
                v_u_41:set_display_time_ms((math.max(v_u_41:get_display_time_ms() + v59, v_u_12:get_earliest_allowed_note_time_ms())))
                v_u_41:full_refresh_active_display_notes()
                v_u_41:update_playing_audio_state()
                v_u_54 = true
            elseif p_u_33._input:control_pressed(v_u_11.KEY_SCROLL_DOWN) and v58 then
                local v60 = v57 * 4
                v_u_52:apply_triggered_scale_offset()
                v_u_41:set_display_time_ms((math.max(v_u_41:get_display_time_ms() + -v60, v_u_12:get_earliest_allowed_note_time_ms())))
                v_u_41:full_refresh_active_display_notes()
                v_u_41:update_playing_audio_state()
                v_u_54 = true
            end;
            if v_u_54 == true then
                v_u_41:flag_this_frame_as_not_playing()
            end;
        end)
        local l_ModeButtons_0 = v_u_38.UIButtons.ModeButtons
        local v61 = v_u_15
        local v62 = v_u_2:new({
            l_ModeButtons_0.ButtonRow2Element1,
            l_ModeButtons_0.ButtonRow2Element2,
            l_ModeButtons_0.ButtonRow2Element3,
            l_ModeButtons_0.ButtonRow2Element4
        })
        local v63 = v_u_2:new()
        local function v65(p64) --[[ Line: 284 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_21 ]]
            if v_u_41:get_current_mode() == v_u_21.Mode.Select then
                v_u_41:set_select_sub_mode(p64)
                return;
            elseif v_u_41:get_current_mode() == v_u_21.Mode.Add then
                v_u_41:set_add_sub_mode(p64)
            end;
        end;
        local function v66() --[[ Line: 292 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_21 ]]
            if v_u_41:get_current_mode() == v_u_21.Mode.Select then
                return v_u_41:get_select_sub_mode();
            end;
            if v_u_41:get_current_mode() == v_u_21.Mode.Add then
                return v_u_41:get_add_sub_mode();
            end;
            if v_u_41:get_current_mode() == v_u_21.Mode.Delete then
                return nil;
            end;
        end;
        local v67 = v_u_37
        local l_PrimaryPart_0 = v_u_38.PrimaryPart
        local v68 = p_u_33
        local v69 = l__spui_0
        local v70 = {
            ["UseRSetAlphaV2"] = true,
            ["NoSFX"] = true
        }
        v70.FnOnPreUpdateDisplays = function(p71) --[[ Name: FnOnPreUpdateDisplays ]] --[[ Line: 305 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_21, (ref 3): v_u_2 ]]
            if v_u_41:get_current_mode() == v_u_21.Mode.Select then
                p71:set_value_list(v_u_2:new({ v_u_21.Select_SubModes.One, v_u_21.Select_SubModes.Multiple }))
                return;
            elseif v_u_41:get_current_mode() == v_u_21.Mode.Add then
                p71:set_value_list(v_u_2:new({ v_u_21.Add_SubModes.Single, v_u_21.Add_SubModes.Hold }))
            elseif v_u_41:get_current_mode() == v_u_21.Mode.Delete then
                p71:set_value_list(v_u_2:new())
            end;
        end;
        v70.FnOnButtonUpdateDisplay = function(p72, p73) --[[ Name: FnOnButtonUpdateDisplay ]] --[[ Line: 314 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_21, (ref 3): v_u_5, (ref 4): v_u_1 ]]
            p72:set_auto_zoffset_behaviour(true)
            if v_u_41:get_current_mode() == v_u_21.Mode.Select then
                v_u_5:set_button_text(p72, v_u_1:enum_val_to_name(p73, v_u_21.Select_SubModes))
                return;
            elseif v_u_41:get_current_mode() == v_u_21.Mode.Add then
                v_u_5:set_button_text(p72, v_u_1:enum_val_to_name(p73, v_u_21.Add_SubModes))
            end;
        end;
        local v_u_74 = v61:new(v62, v63, v65, v66, v67, l_PrimaryPart_0, v68, v69, v70)
        local v75 = v_u_15
        local v76 = v_u_2:new({
            l_ModeButtons_0.ButtonRow1Element1,
            l_ModeButtons_0.ButtonRow1Element2,
            l_ModeButtons_0.ButtonRow1Element3,
            l_ModeButtons_0.ButtonRow1Element4
        })
        local v77 = v_u_2:new({
            v_u_21.Mode.Select,
            v_u_21.Mode.Add,
            v_u_21.Mode.Delete,
            v_u_21.Mode.Paste
        })
        local function v79(p78) --[[ Line: 330 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_41, (ref 3): v_u_74 ]]
            if p78 == v_u_21.Mode.Select then
                if v_u_41:get_current_mode() ~= v_u_21.Mode.Select then
                    v_u_41:set_select_sub_mode(v_u_21.Select_SubModes.One)
                end;
            elseif p78 == v_u_21.Mode.Add then
                v_u_41:get_selected_note_index_set():clear()
            elseif p78 == v_u_21.Mode.Delete then
                v_u_41:get_selected_note_index_set():clear()
            end;
            v_u_41:set_current_mode(p78)
            v_u_74:update_displays()
        end;
        local function v80() --[[ Line: 343 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            return v_u_41:get_current_mode();
        end;
        local v81 = v_u_37
        local l_PrimaryPart_1 = v_u_38.PrimaryPart
        local v82 = p_u_33
        local v83 = l__spui_0
        local v84 = {
            ["UseRSetAlphaV2"] = true,
            ["NoSFX"] = true
        }
        v84.FnOnButtonUpdateDisplay = function(p85, p86) --[[ Name: FnOnButtonUpdateDisplay ]] --[[ Line: 350 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_1, (ref 3): v_u_21 ]]
            p85:set_auto_zoffset_behaviour(true)
            v_u_5:set_button_text(p85, v_u_1:enum_val_to_name(p86, v_u_21.Mode))
        end;
        local v_u_87 = v75:new(v76, v77, v79, v80, v81, l_PrimaryPart_1, v82, v83, v84)
        local l_TextDisplay_0 = l_Frame_0.ModeSection.TextDisplay
        l_TextDisplay_0.Text = ""
        v_u_47:push_back(function() --[[ Line: 359 ]]
            --[[ Upvalues: (ref 1): v_u_41, (copy 2): l_TextDisplay_0, (ref 3): p_u_33, (ref 4): v_u_11, (ref 5): v_u_21, (ref 6): v_u_87, (ref 7): v_u_74 ]]
            local v88, v89 = v_u_41:get_loaded_note_data_stats()
            l_TextDisplay_0.Text = string.format("%d Selected (%d Single / %d Hold / %d Total)", v_u_41:get_selected_note_index_set():count(), v88, v89, v_u_41:get_loaded_note_data():count())
            if p_u_33._input:control_just_pressed(v_u_11.KEY_EDITOR_SELECT_MODE) then
                if v_u_41:get_current_mode() == v_u_21.Mode.Select then
                    if v_u_41:get_select_sub_mode() == v_u_21.Select_SubModes.One then
                        v_u_41:set_select_sub_mode(v_u_21.Select_SubModes.Multiple)
                    else
                        v_u_41:set_select_sub_mode(v_u_21.Select_SubModes.One)
                    end;
                else
                    v_u_41:set_select_sub_mode(v_u_21.Select_SubModes.One)
                end;
                v_u_87:get_selected_callback()(v_u_21.Mode.Select)
                v_u_87:get_button_for_value(v_u_21.Mode.Select):apply_triggered_scale_offset()
                v_u_87:update_displays()
                v_u_74:update_displays()
            elseif p_u_33._input:control_just_pressed(v_u_11.KEY_EDITOR_ADD_MODE) then
                if v_u_41:get_current_mode() == v_u_21.Mode.Add then
                    if v_u_41:get_add_sub_mode() == v_u_21.Add_SubModes.Single then
                        v_u_41:set_add_sub_mode(v_u_21.Add_SubModes.Hold)
                    else
                        v_u_41:set_add_sub_mode(v_u_21.Add_SubModes.Single)
                    end;
                else
                    v_u_41:set_add_sub_mode(v_u_21.Add_SubModes.Single)
                end;
                v_u_87:get_selected_callback()(v_u_21.Mode.Add)
                v_u_87:get_button_for_value(v_u_21.Mode.Add):apply_triggered_scale_offset()
                v_u_87:update_displays()
                v_u_74:update_displays()
            elseif p_u_33._input:control_just_pressed(v_u_11.KEY_EDITOR_DELETE_MODE) then
                v_u_87:get_selected_callback()(v_u_21.Mode.Delete)
                v_u_87:get_button_for_value(v_u_21.Mode.Delete):apply_triggered_scale_offset()
                v_u_87:update_displays()
            elseif p_u_33._input:control_just_pressed(v_u_11.KEY_EDITOR_PASTE_MODE) then
                v_u_87:get_selected_callback()(v_u_21.Mode.Paste)
                v_u_87:get_button_for_value(v_u_21.Mode.Paste):apply_triggered_scale_offset()
                v_u_87:update_displays()
            end;
            if v_u_41:raise_updated_mode() then
                v_u_87:update_displays()
                v_u_74:update_displays()
            end;
        end)
        local l_ActionButtons_0 = v_u_38.UIButtons.ActionButtons
        l_Frame_0.ActionSection.TextDisplay.Text = ""
        local v_u_90 = v_u_2:new({
            0.25,
            0.5,
            0.75,
            1,
            1.25,
            1.5,
            1.75,
            2
        })
        local v_u_91 = nil
        local function _() --[[ Name: update_hold_beat_length_button_text ]] --[[ Line: 424 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_91, (ref 3): v_u_41 ]]
            v_u_5:set_button_text(v_u_91, string.format("Hold x%.2f", v_u_41:get_hold_beat_length_multiplier()))
        end;
        v_u_91 = v_u_5:button_add_enabled_anim_r_set_alpha_v2(v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, l_ActionButtons_0.Button1), l__spui_0, function() --[[ Line: 431 ]]
            --[[ Upvalues: (ref 1): v_u_41, (copy 2): v_u_90, (ref 3): p_u_33, (ref 4): v_u_11, (ref 5): v_u_5, (ref 6): v_u_91 ]]
            local v92 = v_u_90:find((v_u_41:get_hold_beat_length_multiplier()))
            local v93 = v92 <= 0 and 1 or v92
            local v94
            if p_u_33._input:control_pressed(v_u_11.KEY_EDITOR_MODIFIER_SHIFT) then
                v94 = v93 - 1
                if v94 < 1 then
                    v94 = v_u_90:count()
                end;
            else
                local v95 = v93 + 1
                v94 = v_u_90:count() < v95 and 1 or v95
            end;
            v_u_41:set_hold_beat_length_multiplier(v_u_90:get(v94))
            v_u_5:set_button_text(v_u_91, string.format("Hold x%.2f", v_u_41:get_hold_beat_length_multiplier()))
        end):set_auto_zoffset_behaviour(true):set_triggered_scale_offset(0.25)), function() --[[ Line: 450 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            return v_u_37:get_alpha();
        end)
        v_u_5:set_button_text(v_u_91, string.format("Hold x%.2f", v_u_41:get_hold_beat_length_multiplier()))
        local v_u_96 = v_u_5:button_add_enabled_anim_r_set_alpha_v2(v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, l_ActionButtons_0.Button2), l__spui_0, function() --[[ Line: 457 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            v_u_41:undo_last_operation()
        end):set_auto_zoffset_behaviour(true):set_triggered_scale_offset(0.25)), function() --[[ Line: 461 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            return v_u_37:get_alpha();
        end)
        v_u_5:set_button_text(v_u_96, "Undo")
        local v_u_97 = v_u_5:button_add_enabled_anim_r_set_alpha_v2(v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, l_ActionButtons_0.Button3), l__spui_0, function() --[[ Line: 468 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            v_u_41:redo_last_operation()
        end):set_auto_zoffset_behaviour(true):set_triggered_scale_offset(0.25)), function() --[[ Line: 472 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            return v_u_37:get_alpha();
        end)
        v_u_5:set_button_text(v_u_97, "Redo")
        local v_u_98 = v_u_5:button_add_enabled_anim_r_set_alpha_v2(v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, l_ActionButtons_0.Button4), l__spui_0, function() --[[ Line: 479 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            v_u_41:copy_selected_notes()
        end):set_auto_zoffset_behaviour(true):set_triggered_scale_offset(0.25)), function() --[[ Line: 483 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            return v_u_37:get_alpha();
        end)
        v_u_5:set_button_text(v_u_98, "Copy")
        l_ActionButtons_0.Button5.Parent = nil
        v_u_47:push_back(function(_) --[[ Line: 488 ]]
            --[[ Upvalues: (copy 1): v_u_96, (ref 2): v_u_41, (copy 3): v_u_97, (ref 4): v_u_91, (ref 5): v_u_21, (ref 6): p_u_33, (ref 7): v_u_11, (copy 8): v_u_98 ]]
            v_u_96:set_enabled(v_u_41:can_undo_last_operation())
            v_u_97:set_enabled(v_u_41:can_redo_last_operation())
            local v99 = v_u_91
            local v100
            if v_u_41:get_current_mode() == v_u_21.Mode.Add then
                v100 = v_u_41:get_add_sub_mode() == v_u_21.Add_SubModes.Hold
            else
                v100 = false
            end;
            v99:set_enabled(v100)
            if p_u_33._input:control_just_pressed(v_u_11.KEY_EDITOR_UNDO) and v_u_41:can_undo_last_operation() then
                v_u_41:undo_last_operation()
                v_u_96:apply_triggered_scale_offset()
            end;
            if p_u_33._input:control_just_pressed(v_u_11.KEY_EDITOR_REDO) and v_u_41:can_redo_last_operation() then
                v_u_41:redo_last_operation()
                v_u_97:apply_triggered_scale_offset()
            end;
            if p_u_33._input:control_just_pressed(v_u_11.KEY_EDITOR_TOGGLE_HOLD_BEAT_LENGTH) then
                v_u_91:get_callback()()
                v_u_91:apply_triggered_scale_offset()
            end;
            local v101 = v_u_41:get_selected_note_index_set():count() > 0
            v_u_98:set_enabled(v101)
            if v101 and p_u_33._input:control_just_pressed(v_u_11.KEY_EDITOR_COPY) then
                v_u_98:get_callback()()
                v_u_98:apply_triggered_scale_offset()
            end;
        end)
        local l_ZoomButtons_0 = v_u_38.UIButtons.ZoomButtons
        local l_TextDisplay_1 = l_Frame_0.ZoomSection.TextDisplay
        l_TextDisplay_1.Text = ""
        local v_u_102 = v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, l_ZoomButtons_0.Button1), l__spui_0, function() --[[ Line: 521 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            v_u_41:set_track_note_prebuffer_time_ms(v_u_41:get_track_note_prebuffer_time_ms() - 100)
            v_u_41:full_refresh_active_display_notes()
        end)):set_auto_zoffset_behaviour(true):set_triggered_scale_offset(0.25)
        v_u_5:set_button_text(v_u_102, "+")
        local v_u_103 = v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, l_ZoomButtons_0.Button2), l__spui_0, function() --[[ Line: 531 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            v_u_41:set_track_note_prebuffer_time_ms(v_u_41:get_track_note_prebuffer_time_ms() + 100)
            v_u_41:full_refresh_active_display_notes()
        end)):set_auto_zoffset_behaviour(true):set_triggered_scale_offset(0.25)
        v_u_5:set_button_text(v_u_103, "-")
        v_u_47:push_back(function(_) --[[ Line: 538 ]]
            --[[ Upvalues: (copy 1): l_TextDisplay_1, (ref 2): v_u_41, (ref 3): p_u_33, (ref 4): v_u_11, (copy 5): v_u_102, (copy 6): v_u_103 ]]
            l_TextDisplay_1.Text = string.format("%d ms", v_u_41:get_track_note_prebuffer_time_ms())
            if p_u_33._input:control_pressed(v_u_11.KEY_EDITOR_MODIFIER_CTRL) then
                if p_u_33._input:control_just_pressed(v_u_11.KEY_SCROLL_UP) then
                    v_u_102:apply_triggered_scale_offset()
                    v_u_41:set_track_note_prebuffer_time_ms(v_u_41:get_track_note_prebuffer_time_ms() - 100)
                    v_u_41:full_refresh_active_display_notes()
                    v_u_41:flag_this_frame_as_not_playing()
                end;
                if p_u_33._input:control_just_pressed(v_u_11.KEY_SCROLL_DOWN) then
                    v_u_103:apply_triggered_scale_offset()
                    v_u_41:set_track_note_prebuffer_time_ms(v_u_41:get_track_note_prebuffer_time_ms() + 100)
                    v_u_41:full_refresh_active_display_notes()
                    v_u_41:flag_this_frame_as_not_playing()
                end;
            end;
        end)
        local l_SpeedButtons_0 = v_u_38.UIButtons.SpeedButtons
        local l_TextDisplay_2 = l_Frame_0.SpeedSection.TextDisplay
        l_TextDisplay_2.Text = ""
        v_u_5:set_button_text(v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, l_SpeedButtons_0.Button1), l__spui_0, function() --[[ Line: 567 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            v_u_41:set_playback_speed(v_u_41:get_playback_speed() + 0.1)
            v_u_41:full_refresh_active_display_notes()
            v_u_41:update_playing_audio_state()
        end)):set_auto_zoffset_behaviour(true):set_triggered_scale_offset(0.25), "+")
        v_u_5:set_button_text(v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, l_SpeedButtons_0.Button2), l__spui_0, function() --[[ Line: 578 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            v_u_41:set_playback_speed(v_u_41:get_playback_speed() - 0.1)
            v_u_41:full_refresh_active_display_notes()
            v_u_41:update_playing_audio_state()
        end)):set_auto_zoffset_behaviour(true):set_triggered_scale_offset(0.25), "-")
        v_u_47:push_back(function(_) --[[ Line: 586 ]]
            --[[ Upvalues: (copy 1): l_TextDisplay_2, (ref 2): v_u_41 ]]
            l_TextDisplay_2.Text = string.format("x%.2f", v_u_41:get_playback_speed())
        end)
        local l_DivisorButtons_0 = v_u_38.UIButtons.DivisorButtons
        local l_TextDisplay_3 = l_Frame_0.DivisorSection.TextDisplay
        local v_u_104 = v_u_2:new({
            1,
            2,
            3,
            4,
            5,
            6,
            7,
            8,
            9,
            10,
            12,
            16,
            32
        })
        local function f_get_current_divisor_value_index() --[[ Name: get_current_divisor_value_index ]] --[[ Line: 596 ]]
            --[[ Upvalues: (copy 1): v_u_104, (ref 2): v_u_41 ]]
            for v105 = 1, v_u_104:count() do
                if v_u_104:get(v105) == v_u_41:get_time_bar_render():get_divisor_count() then
                    return v105;
                end;
            end;
            return 1;
        end;
        local v_u_107 = v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, l_DivisorButtons_0.Button1), l__spui_0, function() --[[ Line: 608 ]]
            --[[ Upvalues: (copy 1): f_get_current_divisor_value_index, (copy 2): v_u_104, (ref 3): v_u_41 ]]
            local v106 = v_u_104:get(f_get_current_divisor_value_index() + 1)
            if v106 ~= nil then
                v_u_41:get_time_bar_render():set_divisor_count(v106)
            end;
            v_u_41:full_refresh_active_display_notes()
        end)):set_auto_zoffset_behaviour(true):set_triggered_scale_offset(0.25)
        v_u_5:set_button_text(v_u_107, "+")
        local v_u_109 = v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, l_DivisorButtons_0.Button2), l__spui_0, function() --[[ Line: 622 ]]
            --[[ Upvalues: (copy 1): f_get_current_divisor_value_index, (copy 2): v_u_104, (ref 3): v_u_41 ]]
            local v108 = v_u_104:get(f_get_current_divisor_value_index() - 1)
            if v108 ~= nil then
                v_u_41:get_time_bar_render():set_divisor_count(v108)
            end;
            v_u_41:full_refresh_active_display_notes()
        end)):set_auto_zoffset_behaviour(true):set_triggered_scale_offset(0.25)
        v_u_5:set_button_text(v_u_109, "-")
        v_u_47:push_back(function(_) --[[ Line: 633 ]]
            --[[ Upvalues: (copy 1): l_TextDisplay_3, (ref 2): v_u_41, (ref 3): p_u_33, (ref 4): v_u_11, (copy 5): v_u_107, (copy 6): v_u_109 ]]
            l_TextDisplay_3.Text = string.format("1 / %d", v_u_41:get_time_bar_render():get_divisor_count())
            if p_u_33._input:control_pressed(v_u_11.KEY_EDITOR_MODIFIER_ALT) then
                if p_u_33._input:control_just_pressed(v_u_11.KEY_SCROLL_UP) then
                    v_u_107:get_callback()()
                    v_u_107:apply_triggered_scale_offset()
                    v_u_41:flag_this_frame_as_not_playing()
                end;
                if p_u_33._input:control_just_pressed(v_u_11.KEY_SCROLL_DOWN) then
                    v_u_109:get_callback()()
                    v_u_109:apply_triggered_scale_offset()
                    v_u_41:flag_this_frame_as_not_playing()
                end;
            end;
        end)
        local l_TimingPointsButton_0 = v_u_38.UIButtons.TimingPointsButton
        local l_TextDisplay_4 = l_TimingPointsButton_0.SurfaceGui.Frame.TextDisplay
        l_TextDisplay_4.Text = ""
        v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, l_TimingPointsButton_0), l__spui_0, function() --[[ Line: 658 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): p_u_33, (ref 3): v_u_41 ]]
            v_u_23:show_menu(p_u_33, v_u_41)
        end)):set_auto_zoffset_behaviour(true):set_triggered_scale_offset(0.25)
        v_u_47:push_back(function(_) --[[ Line: 662 ]]
            --[[ Upvalues: (copy 1): l_TextDisplay_4, (ref 2): v_u_12, (ref 3): v_u_41 ]]
            l_TextDisplay_4.Text = string.format("%s bpm", v_u_12.TimingPoint:timing_point_get_display_bpm(v_u_41:get_time_bar_render():calculate_active_timing_point()))
        end)
        local v112 = v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, v_u_38.UIButtons.EditSongInfoButton), l__spui_0, function() --[[ Line: 674 ]]
            --[[ Upvalues: (ref 1): v_u_25, (ref 2): p_u_33, (ref 3): p_u_34, (ref 4): v_u_45, (ref 5): v_u_16 ]]
            v_u_25:show_text_input_box_ui(p_u_33, "Edit Map Name", "Enter updated map name.", p_u_34:get_custom_map_name(), function(p110) --[[ Line: 680 ]]
                --[[ Upvalues: (ref 1): p_u_34, (ref 2): v_u_45 ]]
                if #p110 == 0 then
                    return;
                else
                    p_u_34:set_custom_map_name(p110)
                    if #p_u_34:get_custom_map_name() > 0 then
                        v_u_45.Text = p_u_34:get_custom_map_name()
                    else
                        v_u_45.Text = p_u_34:get_default_custom_map_name()
                    end;
                end;
            end):eval(function(p111) --[[ Line: 688 ]]
                --[[ Upvalues: (ref 1): v_u_16 ]]
                p111:set_max_length(v_u_16.SavedMapInfo:get_map_name_max_length())
            end)
        end)):set_auto_zoffset_behaviour(true):set_triggered_scale_offset(0.25)
        if p_u_34:get_creator_rbxid() ~= v_u_1:get_local_userid() then
            v_u_5:button_add_enabled_anim_r_set_alpha_v2(v112, function() --[[ Line: 695 ]]
                --[[ Upvalues: (ref 1): v_u_37 ]]
                return v_u_37:get_alpha();
            end)
            v112:set_enabled(false)
        end;
        local v117 = v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, v_u_38.UIButtons.SaveDataButton), l__spui_0, function() --[[ Line: 704 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_41, (ref 3): p_u_35, (ref 4): l__menus_0, (ref 5): v_u_19, (ref 6): p_u_33, (ref 7): l__spui_0, (ref 8): v_u_8, (ref 9): v_u_1, (ref 10): v_u_6, (ref 11): p_u_34, (ref 12): v_u_16, (ref 13): v_u_45, (ref 14): f_update_song_info_map_creator_display, (ref 15): v_u_28, (ref 16): v_u_37 ]]
            v_u_21:copy_editor_note_track_display_data_to_custom_map(v_u_41, p_u_35)
            local v_u_113 = l__menus_0:push_menu(v_u_19:new(p_u_33, l__spui_0, l__menus_0):set_text("Saving...", "Please wait..."):set_close_button_visible(false))
            p_u_33._evt:wait_on_event_once(v_u_8.EVT_Editor_SaveCustomMap_Server, function(p114, p115, p116) --[[ Line: 708 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_6, (ref 3): l__menus_0, (copy 4): v_u_113, (ref 5): p_u_34, (ref 6): v_u_16, (ref 7): v_u_45, (ref 8): f_update_song_info_map_creator_display, (ref 9): v_u_28, (ref 10): p_u_33, (ref 11): v_u_37, (ref 12): p_u_35, (ref 13): v_u_19, (ref 14): l__spui_0 ]]
                if v_u_1:is_dev_build() then
                    v_u_6:puts("EVT_Editor_SaveCustomMap_Server response")
                end;
                l__menus_0:remove_menu(v_u_113)
                if p116 ~= nil then
                    p_u_34 = v_u_16.SavedMapInfo:from_table(p116)
                    if #p_u_34:get_custom_map_name() > 0 then
                        v_u_45.Text = p_u_34:get_custom_map_name()
                    else
                        v_u_45.Text = p_u_34:get_default_custom_map_name()
                    end;
                    f_update_song_info_map_creator_display()
                end;
                if p114 == true and v_u_16:validate_custom_map_key_components(p_u_34:get_custom_map_data_key()) == true then
                    v_u_28:show_map_saved_popup(p_u_33, v_u_37, p_u_34, p_u_35)
                else
                    l__menus_0:push_menu(v_u_19:new(p_u_33, l__spui_0, l__menus_0):set_text("Error", p115))
                end;
            end)
            p_u_33._evt:fire_event_to_server(v_u_8.EVT_Editor_SaveCustomMap_Client, p_u_34:to_table(), p_u_35:to_table())
        end)):set_auto_zoffset_behaviour(true)
        if p_u_34:get_creator_rbxid() ~= v_u_1:get_local_userid() then
            v_u_5:button_add_enabled_anim_r_set_alpha_v2(v117, function() --[[ Line: 729 ]]
                --[[ Upvalues: (ref 1): v_u_37 ]]
                return v_u_37:get_alpha();
            end)
            v117:set_enabled(false)
        end;
        v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, v_u_38.UIButtons.LoadDataButton), l__spui_0, function() --[[ Line: 736 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): p_u_33, (ref 3): l__menus_0, (ref 4): v_u_37 ]]
            v_u_24:message_box_confirm(p_u_33, function() --[[ Line: 737 ]]
                --[[ Upvalues: (ref 1): l__menus_0, (ref 2): v_u_37, (ref 3): v_u_24, (ref 4): p_u_33 ]]
                l__menus_0:remove_menu(v_u_37)
                v_u_24:show_player_recent_maps_ui(p_u_33)
            end)
        end)):set_auto_zoffset_behaviour(true)
        v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, v_u_38.UIButtons.ShareDataButton), l__spui_0, function() --[[ Line: 747 ]]
            --[[ Upvalues: (ref 1): p_u_34, (ref 2): l__menus_0, (ref 3): v_u_19, (ref 4): p_u_33, (ref 5): l__spui_0, (ref 6): v_u_25 ]]
            if #p_u_34:get_custom_map_data_key() == 0 then
                return l__menus_0:push_menu(v_u_19:new(p_u_33, l__spui_0, l__menus_0):set_text("Error", "Map must be saved before sharing."));
            end;
            l__menus_0:push_menu(v_u_25:new(p_u_33):eval(function(p118) --[[ Line: 754 ]]
                --[[ Upvalues: (ref 1): p_u_34 ]]
                p118:get_title_display().Text = "Share Map"
                p118:get_sub_text_display().Text = "Share this map with code:"
                p118:get_text_box().Text = p_u_34:get_custom_map_data_key()
                p118:get_text_box().TextEditable = false
                p118:get_text_box().TextSize = 32
                p118:select_all_text_box()
            end))
        end)):set_auto_zoffset_behaviour(true)
        v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, v_u_38.UIButtons.TestButton), l__spui_0, function() --[[ Line: 771 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_6, (ref 3): v_u_21, (ref 4): v_u_41, (ref 5): p_u_35, (ref 6): p_u_34 ]]
            local v119 = p_u_33._lobby_join:get_lobby()
            if v119 == nil then
                return v_u_6:warnf("EditorGameUI:load():TestButton: No lobby");
            end;
            v_u_21:copy_editor_note_track_display_data_to_custom_map(v_u_41, p_u_35)
            v119._spectate_manager:start_editor_custom_map_game(p_u_34, p_u_35)
        end)):set_auto_zoffset_behaviour(true)
        v_u_37:add_cycle_element(p_u_33, 1, v_u_5:new(v_u_4:new(v_u_37, v_u_38.PrimaryPart, v_u_38.UIButtons.SettingsButton), l__spui_0, function() --[[ Line: 783 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): p_u_33, (ref 3): v_u_37 ]]
            v_u_27:show_settings_menu(p_u_33, v_u_37)
        end)):set_auto_zoffset_behaviour(true)
        v_u_42 = v_u_22:new(p_u_33, l_Frame_0.SongProgressSection, v_u_37)
        v_u_37:transition_update_visual(0)
        v_u_37:layout()
    end;
    local function _() --[[ Name: on_load_finish ]] --[[ Line: 799 ]]
        --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_41, (ref 3): v_u_32, (ref 4): v_u_42 ]]
        if v_u_36 == true then
            v_u_41:set_display_time_ms(v_u_32)
        else
            v_u_41:set_display_time_ms(0)
        end;
        v_u_41:full_refresh_active_display_notes()
        v_u_42:render_song_time_markers()
    end;
    v_u_37.load_songdatabase_note_data = function(p120) --[[ Name: load_songdatabase_note_data ]] --[[ Line: 809 ]]
        --[[ Upvalues: (copy 1): p_u_33, (copy 2): l__menus_0, (ref 3): v_u_19, (copy 4): l__spui_0, (ref 5): v_u_41, (ref 6): v_u_13, (ref 7): p_u_34, (ref 8): v_u_10, (ref 9): v_u_21, (ref 10): p_u_35, (ref 11): v_u_36, (ref 12): v_u_32, (ref 13): v_u_42 ]]
        p_u_33._update_enqueue_fn:enqueue_function(function() --[[ Line: 811 ]]
            --[[ Upvalues: (ref 1): l__menus_0, (ref 2): v_u_19, (ref 3): p_u_33, (ref 4): l__spui_0, (ref 5): v_u_41, (ref 6): v_u_13, (ref 7): p_u_34, (ref 8): v_u_10, (ref 9): v_u_21, (ref 10): p_u_35, (ref 11): v_u_36, (ref 12): v_u_32, (ref 13): v_u_42 ]]
            local v_u_121 = l__menus_0:push_menu(v_u_19:new(p_u_33, l__spui_0, l__menus_0):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            v_u_41:push_display_message("Loading...")
            local v_u_122 = v_u_13.Builder:new()
            v_u_122:begin()
            v_u_41:load_songkey_audio(p_u_34:get_source_songkey(), function() --[[ Line: 817 ]]
                --[[ Upvalues: (copy 1): v_u_122 ]]
                v_u_122:finish()
            end)
            v_u_122:begin()
            v_u_10:singleton():get_data_for_key(p_u_34:get_source_songkey(), function(p123) --[[ Line: 822 ]]
                --[[ Upvalues: (ref 1): v_u_41, (copy 2): v_u_122 ]]
                v_u_41:load_songdatabase_note_data(p123)
                v_u_122:finish()
            end)
            v_u_122:wait_for_finish(function() --[[ Line: 827 ]]
                --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_41, (ref 3): p_u_35, (ref 4): v_u_10, (ref 5): p_u_34, (ref 6): v_u_36, (ref 7): v_u_32, (ref 8): v_u_42, (ref 9): l__menus_0, (copy 10): v_u_121 ]]
                v_u_21:copy_editor_note_track_display_data_to_custom_map(v_u_41, p_u_35)
                v_u_41:push_display_message(string.format("Loaded default song data for song (%s)", v_u_10:singleton():get_title_for_key(p_u_34:get_source_songkey())))
                if v_u_36 == true then
                    v_u_41:set_display_time_ms(v_u_32)
                else
                    v_u_41:set_display_time_ms(0)
                end;
                v_u_41:full_refresh_active_display_notes()
                v_u_42:render_song_time_markers()
                l__menus_0:remove_menu(v_u_121)
            end)
        end)
        return p120;
    end;
    v_u_37.set_custom_map_data = function(_, p124) --[[ Name: set_custom_map_data ]] --[[ Line: 838 ]]
        --[[ Upvalues: (ref 1): p_u_35 ]]
        p_u_35 = p124
    end;
    v_u_37.load_custom_map_note_data = function(p125) --[[ Name: load_custom_map_note_data ]] --[[ Line: 839 ]]
        --[[ Upvalues: (ref 1): v_u_41, (ref 2): p_u_34, (ref 3): p_u_35, (ref 4): v_u_36, (ref 5): v_u_32, (ref 6): v_u_42 ]]
        v_u_41:load_songkey_audio(p_u_34:get_source_songkey())
        v_u_41:load_songdatabase_note_data(p_u_35:to_songdatabase_note_data())
        v_u_41:push_display_message(string.format("Loaded custom map data for key (%s)", p_u_34:get_custom_map_data_key()))
        if v_u_36 == true then
            v_u_41:set_display_time_ms(v_u_32)
        else
            v_u_41:set_display_time_ms(0)
        end;
        v_u_41:full_refresh_active_display_notes()
        v_u_42:render_song_time_markers()
        return p125;
    end;
    v_u_37.on_refocus = function(_) --[[ Name: on_refocus ]] --[[ Line: 850 ]]
        --[[ Upvalues: (ref 1): v_u_41 ]]
        v_u_41:set_allow_resync_playback_sound_immediately()
    end;
    v_u_37.visual_update = function(p126, p127) --[[ Name: visual_update ]] --[[ Line: 854 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_33 ]]
        local v_u_128 = false
        v_u_1:ptry(function() --[[ Line: 856 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_128 ]]
            local v129 = p_u_33._lobby_join:get_lobby()
            if v129 and v129:transition_local_camera_cframe_finished() == false then
                v_u_128 = true
            end;
        end)
        if not v_u_128 then
            p126:visual_update_base(p127, p_u_33)
        end;
    end;
    v_u_37.behaviour_update = function(p130, p131, p132) --[[ Name: behaviour_update ]] --[[ Line: 871 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_41, (ref 3): v_u_44, (ref 4): v_u_1, (ref 5): v_u_43, (copy 6): v_u_47, (ref 7): v_u_42 ]]
        p130:behaviour_update_base(p131, p132)
        if p130._current_mode == v_u_14.MODE_OPEN then
            v_u_41:update(p131)
            v_u_44.Text = string.format("%s / %s", v_u_1:format_ms_time_hundredth(v_u_41:get_display_time_ms()), v_u_1:format_ms_time_hundredth(v_u_41:get_audio_duration_ms()))
            if v_u_41:raise_display_message() then
                v_u_43.Text = v_u_41:get_display_message()
            end;
            for v133 = 1, v_u_47:count() do
                v_u_47:get(v133)(p131)
            end;
            v_u_42:update(p131)
        end;
    end;
    v_u_37.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 893 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): p_u_34, (ref 3): v_u_31, (ref 4): p_u_35, (ref 5): v_u_32, (ref 6): v_u_41, (copy 7): p_u_33, (ref 8): v_u_40, (ref 9): v_u_38 ]]
        v_u_30 = p_u_34
        v_u_31 = p_u_35
        v_u_32 = v_u_41:get_display_time_ms()
        p_u_33._bgm_manager:force_mute_bgm(false)
        p_u_33._bgm_manager:stop_song_preview(v_u_40)
        v_u_41:cleanup()
        v_u_38:Destroy()
        p_u_33._chat:set_chat_visible(p_u_33._chat:get_stored_chat_visible())
        p_u_33._player_settings_manager:set_character_culling_mode_from_settings()
    end;
    local v_u_134 = 1
    local v_u_135 = 1
    v_u_37.layout = function(p136) --[[ Name: layout ]] --[[ Line: 909 ]]
        --[[ Upvalues: (copy 1): l__spui_0, (ref 2): v_u_135, (ref 3): v_u_38 ]]
        p136:opt_rescale_to_max_nxy(l__spui_0, 0.95, 0.9, v_u_135)
        local v137, v138 = p136:opt_update_cframe_params(l__spui_0, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p136:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v137 == true then
            v_u_38:SetPrimaryPartCFrame(v138)
        end;
    end;
    v_u_37.set_alpha = function(_, p139) --[[ Name: set_alpha ]] --[[ Line: 921 ]]
        --[[ Upvalues: (ref 1): v_u_134, (ref 2): v_u_1, (ref 3): v_u_38, (ref 4): v_u_41 ]]
        if v_u_134 ~= p139 then
            v_u_134 = p139
            v_u_1:r_set_alpha_v2(v_u_38, v_u_134)
            v_u_41:set_alpha(v_u_134)
        end;
    end;
    v_u_37.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 928 ]]
        --[[ Upvalues: (ref 1): v_u_134 ]]
        return v_u_134;
    end;
    v_u_37.set_scale = function(_, p140) --[[ Name: set_scale ]] --[[ Line: 929 ]]
        --[[ Upvalues: (ref 1): v_u_135 ]]
        v_u_135 = p140
    end;
    v_u_37.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 930 ]]
        --[[ Upvalues: (ref 1): v_u_135 ]]
        return v_u_135;
    end;
    v_u_37.get_native_size = function(p141) --[[ Name: get_native_size ]] --[[ Line: 932 ]]
        return p141._native_size;
    end;
    v_u_37.get_size = function(p142) --[[ Name: get_size ]] --[[ Line: 935 ]]
        return p142._size;
    end;
    v_u_37.set_size = function(p143, p144) --[[ Name: set_size ]] --[[ Line: 938 ]]
        --[[ Upvalues: (ref 1): v_u_38 ]]
        p143._size = p144
        v_u_38.PrimaryPart.Size = Vector3.new(p144.X, p144.Y, 0)
    end;
    v_u_37.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 942 ]]
        --[[ Upvalues: (ref 1): v_u_38 ]]
        return v_u_38.PrimaryPart.Position;
    end;
    v_u_37.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 945 ]]
        --[[ Upvalues: (ref 1): v_u_39 ]]
        return v_u_39;
    end;
    v_u_37.set_showing = function(_, p145) --[[ Name: set_showing ]] --[[ Line: 948 ]]
        --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_9 ]]
        if p145 then
            v_u_38.Parent = v_u_9:get_world_ui_folder()
        else
            v_u_38.Parent = nil
        end;
    end;
    f_cons()
    return v_u_37;
end;
return v_u_29;
