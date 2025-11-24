-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:02 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_2 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_3 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_4 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_9 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_10 = require(game.ReplicatedStorage.Lobby.Menus.KeyBindsUI)
local v_u_11 = require(game.ReplicatedStorage.Lobby.Menus.ValueInputUI)
local v_u_12 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_13 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
local v_u_14 = require(game.ReplicatedStorage.Shared.Note2DSettings)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
local v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.NoteColorSelectV2UI)
local v_u_17 = require(game.ReplicatedStorage.PreviewGame.PreviewGameStartupMenu)
local v_u_37 = {
    ["get_2d_mode_display_icon"] = function(_, p18) --[[ Name: get_2d_mode_display_icon ]] --[[ Line: 40 ]]
        --[[ Upvalues: (copy 1): v_u_9, (copy 2): v_u_14, (copy 3): v_u_15, (copy 4): v_u_5 ]]
        local v19 = v_u_14.Skin:get_note_decal_database_id((p18._player_settings_manager:get_key(v_u_9.Key.Note2DSettingsSkin)))
        if v_u_15:singleton():get_info_for_id(v19) == nil then
            return v_u_5:important_assetid();
        else
            return v_u_15:singleton():get_info_for_id(v19):get_icon();
        end;
    end,
    ["update_note_display_mode_text"] = function(_, p_u_20, p_u_21) --[[ Name: update_note_display_mode_text ]] --[[ Line: 239 ]]
        --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_9, (copy 3): v_u_6 ]]
        local v22, v23 = pcall(function() --[[ Line: 240 ]]
            --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_12, (copy 3): p_u_20, (ref 4): v_u_9 ]]
            local l_ModeDisplay_0 = p_u_21.SurfaceGui.Frame.ModeDisplay
            local l_Icon_0 = p_u_21.SurfaceGui.Frame.Icon
            l_ModeDisplay_0.Text = v_u_12:display_mode_to_name(p_u_20._player_settings_manager:get_key(v_u_9.Key.NoteDisplayMode))
            l_Icon_0.Image = v_u_12:display_mode_to_preview_assetid(p_u_20._player_settings_manager:get_key(v_u_9.Key.NoteDisplayMode))
        end)
        if not v22 then
            v_u_6:warnf(v23)
        end;
    end,
    ["get_note_speed_display_text"] = function(_, p24) --[[ Name: get_note_speed_display_text ]] --[[ Line: 252 ]]
        return string.format("x%.2f", 1 / p24._player_settings_manager:get_note_speed_multiplier());
    end,
    ["get_note_offset_display_text"] = function(_, p25) --[[ Name: get_note_offset_display_text ]] --[[ Line: 257 ]]
        --[[ Upvalues: (copy 1): v_u_9 ]]
        local v26 = p25._player_settings_manager:get_key(v_u_9.Key.NoteOffset)
        if v26 <= 0 then
            return tostring(v26) .. "ms";
        else
            return "+" .. tostring(v26) .. "ms";
        end;
    end,
    ["create_note_speed_menu"] = function(_, p_u_27, p_u_28) --[[ Name: create_note_speed_menu ]] --[[ Line: 277 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_9, (copy 3): v_u_4 ]]
        p_u_27._menus:push_menu(v_u_11:new(p_u_27, p_u_27._spui, p_u_27._menus, p_u_27._player_settings_manager:get_key(v_u_9.Key.NoteSpeed), function(p29) --[[ Line: 280 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_27, (ref 3): v_u_9, (copy 4): p_u_28 ]]
            v_u_4:is_int(p29)
            p_u_27._player_settings_manager:set_key(v_u_9.Key.NoteSpeed, p29)
            if p_u_28 then
                p_u_28()
            end;
        end):set_value_increment(2):set_reset_value(v_u_9:get_note_speed_default()):set_range_min_max(v_u_9:get_note_speed_min(), v_u_9:get_note_speed_max()):set_title_sub_text("Adjust Note Speed", "Adjust the speed of which notes arrive."):set_value_display_info_fn(function(p30) --[[ Line: 292 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            local v31 = v_u_9:get_multiplier_for_note_speed(p30)
            local v32 = string.format("x%.2f", 1 / v31)
            return v32, string.format("Notes arrive at %s speed (%s).", v32, v31 < 1 and "Faster" or (v31 > 1 and "Slower" or "Default"));
        end))
    end,
    ["create_note_offset_menu"] = function(_, p_u_33, p_u_34) --[[ Name: create_note_offset_menu ]] --[[ Line: 308 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_9, (copy 3): v_u_4 ]]
        p_u_33._menus:push_menu(v_u_11:new(p_u_33, p_u_33._spui, p_u_33._menus, p_u_33._player_settings_manager:get_key(v_u_9.Key.NoteOffset), function(p35) --[[ Line: 311 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_33, (ref 3): v_u_9, (copy 4): p_u_34 ]]
            v_u_4:is_int(p35)
            p_u_33._player_settings_manager:set_key(v_u_9.Key.NoteOffset, p35)
            p_u_34()
        end):set_value_increment(1):set_reset_value(0):set_range_min_max(-1000, 1000):set_title_sub_text("Adjust Audio Offset", "Adjust audio offset time of music."):set_value_display_info_fn(function(p36) --[[ Line: 323 ]]
            return string.format("%dms", p36), string.format("Offset %d milliseconds (%s).", p36, p36 < 0 and "Early" or (p36 > 0 and "Late" or "Default"));
        end))
    end
}
local function f_block_until_changes_saved(p_u_38, p_u_39) --[[ Name: block_until_changes_saved ]] --[[ Line: 23 ]]
    --[[ Upvalues: (copy 1): v_u_7 ]]
    if p_u_38._player_settings_manager:has_changes() then
        local v_u_40 = p_u_38._menus:push_menu(v_u_7:new(p_u_38, p_u_38._spui, p_u_38._menus):set_text("Saving...", "Please wait..."):set_close_button_visible(false))
        p_u_38._player_settings_manager:save_changes_to_playerblob(p_u_38, function() --[[ Line: 26 ]]
            --[[ Upvalues: (copy 1): p_u_38, (copy 2): v_u_40, (copy 3): p_u_39 ]]
            p_u_38._menus:remove_menu(v_u_40)
            p_u_38._player_settings_manager:clear_changes()
            if p_u_39 then
                p_u_39()
            end;
        end)
    elseif p_u_39 then
        p_u_39()
    end;
end;
v_u_37.show_note_display_2d_settings_menu = function(_, p_u_41, p42, p_u_43, p_u_44, p_u_45) --[[ Name: show_note_display_2d_settings_menu ]] --[[ Line: 49 ]]
    --[[ Upvalues: (copy 1): v_u_13, (copy 2): v_u_5, (copy 3): v_u_14, (copy 4): v_u_15, (copy 5): v_u_4, (copy 6): f_block_until_changes_saved, (copy 7): v_u_37 ]]
    local v_u_46 = p42 == nil and true or p42
    local function f_create_settings_menu_for_enum_and_playersettings_key(p_u_47, p_u_48) --[[ Name: create_settings_menu_for_enum_and_playersettings_key ]] --[[ Line: 58 ]]
        --[[ Upvalues: (copy 1): p_u_41, (ref 2): v_u_13, (copy 3): p_u_44, (ref 4): v_u_5, (ref 5): v_u_14, (ref 6): v_u_15, (ref 7): v_u_4, (ref 8): v_u_46, (ref 9): f_block_until_changes_saved, (copy 10): p_u_43, (copy 11): p_u_45 ]]
        p_u_41._menus:push_menu(v_u_13:new(p_u_41, p_u_41._spui, p_u_41._menus, function(p49) --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): p_u_44, (copy 2): p_u_47 ]]
            if p_u_44 then
                p_u_44(p49)
            end;
            p49:set_header_text(p_u_47:get_setting_name())
            for _, v50 in p_u_47:key_itr() do
                p49:get_element_list():push_back(v50)
            end;
        end, function(p51, p52, p53, _) --[[ Line: 72 ]]
            --[[ Upvalues: (copy 1): p_u_47, (ref 2): p_u_41, (copy 3): p_u_48, (ref 4): v_u_5, (ref 5): v_u_14, (ref 6): v_u_15 ]]
            p52.Text = p_u_47:get_name(p51)
            if p_u_41._player_settings_manager:get_key(p_u_48) == p51 then
                p52.Text = p52.Text .. " [Selected]"
            end;
            p53.Image = v_u_5:gear_assetid()
            if p_u_47 == v_u_14.Skin then
                local v54 = v_u_14.Skin:get_note_decal_database_id(p51)
                if v_u_15:singleton():get_info_for_id(v54) ~= nil then
                    p53.Image = v_u_15:singleton():get_info_for_id(v54):get_icon()
                end;
            end;
        end, function(p55) --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_47, (ref 3): p_u_41, (copy 4): p_u_48, (ref 5): v_u_46, (ref 6): f_block_until_changes_saved ]]
            if v_u_4:test_enum_member(p55, p_u_47) then
                p_u_41._player_settings_manager:set_key(p_u_48, p55)
            end;
            if v_u_46 == true then
                f_block_until_changes_saved(p_u_41)
            end;
        end, nil, (function() --[[ Line: 94 ]]
            --[[ Upvalues: (ref 1): p_u_43 ]]
            if p_u_43 == nil then
                return nil;
            else
                return p_u_43:Clone();
            end;
        end)()):set_fn_on_remove(function() --[[ Line: 96 ]]
            --[[ Upvalues: (ref 1): p_u_45 ]]
            if p_u_45 then
                p_u_45()
            end;
        end))
    end;
    p_u_41._menus:push_menu(v_u_13:new(p_u_41, p_u_41._spui, p_u_41._menus, function(p56) --[[ Line: 108 ]]
        --[[ Upvalues: (copy 1): p_u_44, (ref 2): v_u_14 ]]
        if p_u_44 then
            p_u_44(p56)
        end;
        p56:set_header_text("2D Note Options:")
        p56:get_element_list():push_back(v_u_14.Skin)
        p56:get_element_list():push_back(v_u_14.Width)
        p56:get_element_list():push_back(v_u_14.Position)
        p56:get_element_list():push_back(v_u_14.Background)
    end, function(p57, p58, p59, _) --[[ Line: 117 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_41, (ref 3): v_u_14, (ref 4): v_u_37 ]]
        p59.Image = v_u_5:important_assetid()
        if p57 then
            p58.Text = string.format("%s: (%s)", p57:get_setting_name(), p57:get_name(p_u_41._player_settings_manager:get_key(v_u_14:enum_class_to_playersettings_key(p57))))
            if p57 == v_u_14.Skin then
                p59.Image = v_u_37:get_2d_mode_display_icon(p_u_41)
            end;
        end;
    end, function(p60) --[[ Line: 131 ]]
        --[[ Upvalues: (copy 1): f_create_settings_menu_for_enum_and_playersettings_key, (ref 2): v_u_14 ]]
        if p60 then
            f_create_settings_menu_for_enum_and_playersettings_key(p60, v_u_14:enum_class_to_playersettings_key(p60))
        end;
    end, nil, (function() --[[ Line: 137 ]]
        --[[ Upvalues: (copy 1): p_u_43 ]]
        if p_u_43 == nil then
            return nil;
        else
            return p_u_43:Clone();
        end;
    end)()):set_close_on_element_select(false):set_fn_on_remove(function() --[[ Line: 140 ]]
        --[[ Upvalues: (copy 1): p_u_45 ]]
        if p_u_45 then
            p_u_45()
        end;
    end))
end;
v_u_37.create_note_display_settings_button = function(_, p_u_61, p62, p63, p_u_64) --[[ Name: create_note_display_settings_button ]] --[[ Line: 146 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_12, (copy 3): v_u_37, (copy 4): v_u_2, (copy 5): v_u_1, (copy 6): v_u_3, (copy 7): v_u_8, (copy 8): v_u_13, (copy 9): v_u_9, (copy 10): v_u_5, (copy 11): v_u_16, (copy 12): f_block_until_changes_saved ]]
    v_u_4:is_true(v_u_4:test_enum_member(-1, v_u_12) ~= true)
    v_u_37:update_note_display_mode_text(p_u_61, p_u_64)
    return p63:add_cycle_element(p_u_61, 1, v_u_2:new(v_u_1:new(p63, p62.PrimaryPart, p_u_64), p_u_61._spui, function() --[[ Line: 157 ]]
        --[[ Upvalues: (copy 1): p_u_61, (ref 2): v_u_3, (ref 3): v_u_8, (ref 4): v_u_13, (ref 5): v_u_12, (ref 6): v_u_9, (ref 7): v_u_5, (ref 8): v_u_37, (ref 9): v_u_16, (ref 10): f_block_until_changes_saved, (ref 11): v_u_4, (copy 12): p_u_64 ]]
        p_u_61._sfx_manager:play_sfx(v_u_3.SFX_MENU_OPEN)
        if v_u_8.NoteDisplayGoToPreviewGame == true then
            return p_u_61._spectate_manager:start_preview_game();
        end;
        p_u_61._menus:push_menu(v_u_13:new(p_u_61, p_u_61._spui, p_u_61._menus, function(p65) --[[ Line: 164 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_61, (ref 3): v_u_9, (ref 4): v_u_5 ]]
            p65:set_header_text("Configure note display...")
            p65:get_element_list():push_back(-3)
            p65:get_element_list():push_back(v_u_12.Default)
            p65:get_element_list():push_back(v_u_12.DecalDown)
            p65:get_element_list():push_back(v_u_12.DecalUp)
            if p_u_61._player_settings_manager:get_key(v_u_9.Key.NoteDisplayMode) ~= v_u_12.Default then
                p65:get_element_list():push_back(-1)
            end;
            if v_u_5:is_mobile() then
                p65:get_element_list():push_back(-4)
            end;
        end, function(p66, p67, p68, _, p69) --[[ Line: 177 ]]
            --[[ Upvalues: (ref 1): v_u_37, (ref 2): p_u_61, (ref 3): v_u_5, (ref 4): v_u_9, (ref 5): v_u_12 ]]
            if p66 == -1 then
                p67.Text = "2D Note Options"
                p68.Image = v_u_37:get_2d_mode_display_icon(p_u_61)
                p69:set_select_button_text("Open")
                return;
            elseif p66 == -2 then
                p67.Text = "Configure Colors"
                p68.Image = v_u_5:gear_assetid()
                p69:set_select_button_text("Open")
                return;
            elseif p66 == -3 then
                p67.Text = "Preview Game Settings"
                p68.Image = v_u_5:get_double_arrow_icon_assetid()
                p69:set_select_button_text("Open")
                return;
            elseif p66 == -4 then
                local v70 = "Mobile Fullscreen: "
                local v71
                if p_u_61._player_settings_manager:get_key(v_u_9.Key.MobileFullScreenUI) == true then
                    v71 = v70 .. "On"
                else
                    v71 = v70 .. "Off"
                end;
                p67.Text = v71
                p68.Image = v_u_5:important_assetid()
                p69:set_select_button_text("Toggle")
            else
                p67.Text = v_u_12:display_mode_to_name(p66)
                if p_u_61._player_settings_manager:get_key(v_u_9.Key.NoteDisplayMode) == p66 then
                    p67.Text = p67.Text .. " [Selected]"
                end;
                p68.Image = v_u_12:display_mode_to_preview_assetid(p66)
                p69:set_select_button_text("Select")
            end;
        end, function(p72, p_u_73) --[[ Line: 209 ]]
            --[[ Upvalues: (ref 1): v_u_37, (ref 2): p_u_61, (ref 3): v_u_16, (ref 4): v_u_9, (ref 5): f_block_until_changes_saved, (ref 6): v_u_4, (ref 7): v_u_12, (ref 8): p_u_64 ]]
            if p72 == -1 then
                v_u_37:show_note_display_2d_settings_menu(p_u_61)
                return;
            elseif p72 == -2 then
                p_u_61._menus:push_menu(v_u_16:new(p_u_61, p_u_61._spui, p_u_61._menus))
                return;
            elseif p72 == -3 then
                p_u_61._spectate_manager:start_preview_game()
                return;
            elseif p72 == -4 then
                p_u_61._player_settings_manager:set_key(v_u_9.Key.MobileFullScreenUI, not p_u_61._player_settings_manager:get_key(v_u_9.Key.MobileFullScreenUI))
                f_block_until_changes_saved(p_u_61, function() --[[ Line: 218 ]]
                    --[[ Upvalues: (copy 1): p_u_73 ]]
                    p_u_73:refresh()
                end)
            else
                if v_u_4:test_enum_member(p72, v_u_12) then
                    p_u_61._player_settings_manager:set_key(v_u_9.Key.NoteDisplayMode, p72)
                end;
                f_block_until_changes_saved(p_u_61, function() --[[ Line: 227 ]]
                    --[[ Upvalues: (copy 1): p_u_73, (ref 2): v_u_37, (ref 3): p_u_61, (ref 4): p_u_64 ]]
                    p_u_73:refresh()
                    v_u_37:update_note_display_mode_text(p_u_61, p_u_64)
                end)
            end;
        end):set_close_on_element_select(false))
    end)):set_auto_zoffset_behaviour(true);
end;
v_u_37.update_note_speed_display = function(_, p_u_74, p_u_75) --[[ Name: update_note_speed_display ]] --[[ Line: 268 ]]
    --[[ Upvalues: (copy 1): v_u_37, (copy 2): v_u_6 ]]
    local v76, v77 = pcall(function() --[[ Line: 269 ]]
        --[[ Upvalues: (copy 1): p_u_75, (ref 2): v_u_37, (copy 3): p_u_74 ]]
        p_u_75.SurfaceGui.Frame.TimeDisplay.Text = v_u_37:get_note_speed_display_text(p_u_74)
    end)
    if not v76 then
        v_u_6:warnf(v77)
    end;
end;
v_u_37.create_note_speed_button = function(_, p_u_78, p79, p80, p_u_81) --[[ Name: create_note_speed_button ]] --[[ Line: 336 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_3, (copy 4): v_u_8, (copy 5): v_u_17, (copy 6): v_u_37, (copy 7): f_block_until_changes_saved ]]
    local v82 = p79:add_cycle_element(p_u_78, 1, v_u_2:new(v_u_1:new(p79, p80.PrimaryPart, p_u_81), p_u_78._spui, function() --[[ Line: 340 ]]
        --[[ Upvalues: (copy 1): p_u_78, (ref 2): v_u_3, (ref 3): v_u_8, (ref 4): v_u_17, (ref 5): v_u_37, (ref 6): f_block_until_changes_saved, (copy 7): p_u_81 ]]
        p_u_78._sfx_manager:play_sfx(v_u_3.SFX_MENU_OPEN)
        if v_u_8.NoteDisplayGoToPreviewGame == true then
            return p_u_78._spectate_manager:start_preview_game(v_u_17.NoteSpeed);
        end;
        v_u_37:create_note_speed_menu(p_u_78, function() --[[ Line: 346 ]]
            --[[ Upvalues: (ref 1): f_block_until_changes_saved, (ref 2): p_u_78, (ref 3): v_u_37, (ref 4): p_u_81 ]]
            f_block_until_changes_saved(p_u_78, function() --[[ Line: 347 ]]
                --[[ Upvalues: (ref 1): v_u_37, (ref 2): p_u_78, (ref 3): p_u_81 ]]
                v_u_37:update_note_speed_display(p_u_78, p_u_81)
            end)
        end)
    end)):set_auto_zoffset_behaviour(true)
    v_u_37:update_note_speed_display(p_u_78, p_u_81)
    return v82;
end;
v_u_37.create_keybinds_button = function(_, p_u_83, p84, p85, p86) --[[ Name: create_keybinds_button ]] --[[ Line: 358 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_3, (copy 4): v_u_8, (copy 5): v_u_17, (copy 6): v_u_10, (copy 7): f_block_until_changes_saved ]]
    return p84:add_cycle_element(p_u_83, 1, v_u_2:new(v_u_1:new(p84, p85.PrimaryPart, p86), p_u_83._spui, function() --[[ Line: 362 ]]
        --[[ Upvalues: (copy 1): p_u_83, (ref 2): v_u_3, (ref 3): v_u_8, (ref 4): v_u_17, (ref 5): v_u_10, (ref 6): f_block_until_changes_saved ]]
        p_u_83._sfx_manager:play_sfx(v_u_3.SFX_MENU_OPEN)
        if v_u_8.NoteDisplayGoToPreviewGame == true then
            return p_u_83._spectate_manager:start_preview_game(v_u_17.Keybinds);
        end;
        p_u_83._menus:push_menu(v_u_10:new(p_u_83, p_u_83._spui, p_u_83._menus):set_on_close_fn(function() --[[ Line: 368 ]]
            --[[ Upvalues: (ref 1): f_block_until_changes_saved, (ref 2): p_u_83 ]]
            f_block_until_changes_saved(p_u_83)
        end))
    end)):set_auto_zoffset_behaviour(true);
end;
v_u_37.create_note_offset_button = function(_, p_u_87, p88, p89, p90) --[[ Name: create_note_offset_button ]] --[[ Line: 376 ]]
    --[[ Upvalues: (copy 1): v_u_37, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_3, (copy 5): v_u_8, (copy 6): v_u_17 ]]
    local l_TimeDisplay_0 = p90.SurfaceGui.Frame.TimeDisplay
    local function _() --[[ Name: update_note_offset_display ]] --[[ Line: 378 ]]
        --[[ Upvalues: (copy 1): l_TimeDisplay_0, (ref 2): v_u_37, (copy 3): p_u_87 ]]
        l_TimeDisplay_0.Text = v_u_37:get_note_offset_display_text(p_u_87)
    end;
    local v91 = p88:add_cycle_element(p_u_87, 1, v_u_2:new(v_u_1:new(p88, p89.PrimaryPart, p90), p_u_87._spui, function() --[[ Line: 384 ]]
        --[[ Upvalues: (copy 1): p_u_87, (ref 2): v_u_3, (ref 3): v_u_8, (ref 4): v_u_17, (ref 5): v_u_37, (copy 6): l_TimeDisplay_0 ]]
        p_u_87._sfx_manager:play_sfx(v_u_3.SFX_MENU_OPEN)
        if v_u_8.NoteDisplayGoToPreviewGame == true then
            return p_u_87._spectate_manager:start_preview_game(v_u_17.NoteOffset);
        end;
        v_u_37:create_note_offset_menu(p_u_87, function() --[[ Line: 390 ]]
            --[[ Upvalues: (ref 1): l_TimeDisplay_0, (ref 2): v_u_37, (ref 3): p_u_87 ]]
            l_TimeDisplay_0.Text = v_u_37:get_note_offset_display_text(p_u_87)
        end)
    end)):set_auto_zoffset_behaviour(true)
    l_TimeDisplay_0.Text = v_u_37:get_note_offset_display_text(p_u_87)
    return v91;
end;
return v_u_37;
