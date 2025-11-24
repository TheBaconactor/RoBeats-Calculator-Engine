-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:48 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Lobby.UI.SPUITextInput)
local v_u_4 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v5 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_6 = nil
local v_u_7 = nil
local v_u_8 = nil
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
v5:require_client(function() --[[ Line: 23 ]]
    --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7, (ref 3): v_u_8, (ref 4): v_u_9, (ref 5): v_u_10, (ref 6): v_u_11 ]]
    v_u_6 = require(game.ReplicatedStorage.Lobby.Menus.ColorSelectUI)
    v_u_7 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_8 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
    v_u_9 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
    v_u_10 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_11 = require(game.ReplicatedStorage.Lobby.Menus.ValueInputUI)
end)
return {
    ["new"] = function(_, p_u_12, p_u_13, p_u_14) --[[ Name: new ]] --[[ Line: 34 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_1, (ref 3): v_u_10, (copy 4): v_u_2, (copy 5): v_u_4, (copy 6): v_u_3 ]]
        local function f_show_menu_for_track_enum(p_u_15) --[[ Name: show_menu_for_track_enum ]] --[[ Line: 35 ]]
            --[[ Upvalues: (copy 1): p_u_14, (ref 2): v_u_7, (copy 3): p_u_12, (ref 4): v_u_1, (ref 5): v_u_10, (copy 6): p_u_13 ]]
            local v_u_16 = nil
            v_u_16 = p_u_14:push_menu(v_u_7:new(p_u_12, p_u_12._spui, p_u_12._menus, function(p17) --[[ Line: 42 ]]
                --[[ Upvalues: (ref 1): p_u_12, (copy 2): p_u_15 ]]
                p17:set_header_text(string.format("Keybinds for Track %d", p_u_12._input:get_key_to_track_index():get(p_u_15)))
                p17:get_element_list():push_back(-1)
                for _, v18 in p_u_12._input:get_controller_track_enum_to_keycodes():list_of(p_u_15):key_itr() do
                    p17:get_element_list():push_back(v18)
                end;
            end, function(p19, p20, p21, _, p22) --[[ Line: 49 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): p_u_12 ]]
                if p19 == -1 then
                    p20.Text = "Add Keybind"
                    p21.Image = v_u_1:gear_assetid()
                    p22:set_select_button_text("Add")
                    p22:set_select_button_enabled(true)
                else
                    p20.Text = p_u_12._input:button_keycode_to_name(p19)
                    p21.Image = v_u_1:important_assetid()
                    p22:set_select_button_text("-")
                    p22:set_select_button_enabled(false)
                end;
            end, function(p23) --[[ Line: 62 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_10, (ref 3): p_u_13, (ref 4): p_u_14, (copy 5): p_u_15, (ref 6): v_u_16 ]]
                if p23 ~= nil then
                    if p23 == -1 then
                        local v_u_24 = nil
                        v_u_24 = p_u_12._menus:push_menu(v_u_10:new(p_u_12, p_u_13, p_u_14):set_text("Press a key...", string.format("Press a key to bind to Track %d", p_u_12._input:get_key_to_track_index():get(p_u_15)))):set_update_fn(function() --[[ Line: 70 ]]
                            --[[ Upvalues: (ref 1): p_u_12, (ref 2): p_u_15, (ref 3): v_u_16, (ref 4): p_u_14, (ref 5): v_u_24 ]]
                            if p_u_12._input:has_recorded_controller_keycode_input() == true then
                                p_u_12._player_settings_manager:add_controller_track_index_keybind(p_u_12, p_u_15, p_u_12._input:get_recorded_controller_keycode())
                                p_u_12._input:cancel_record_next_controller_keycode_input()
                                v_u_16:refresh()
                                p_u_14:remove_menu(v_u_24)
                            end;
                        end)
                        p_u_12._input:record_next_controller_keycode_input()
                    end;
                end;
            end, nil, game.ReplicatedStorage.LobbyElementProtos.PreviewGameUIProto.PreviewGameSettingsListUI:Clone())):set_close_on_element_select(false)
        end;
        local function f_show_menu_for_controller_enable_virtual_cursor_button() --[[ Name: show_menu_for_controller_enable_virtual_cursor_button ]] --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_14, (ref 3): v_u_7, (copy 4): p_u_12, (ref 5): v_u_1, (ref 6): v_u_10, (copy 7): p_u_13 ]]
            local v_u_25 = v_u_2:new():add_set_from_table_list({ Enum.KeyCode.ButtonA, Enum.KeyCode.ButtonY })
            local v_u_26 = nil
            v_u_26 = p_u_14:push_menu(v_u_7:new(p_u_12, p_u_12._spui, p_u_12._menus, function(p27) --[[ Line: 100 ]]
                --[[ Upvalues: (ref 1): p_u_12 ]]
                p27:set_header_text(string.format("Keybinds for Show Virtual Cursor"))
                p27:get_element_list():push_back(-1)
                for _, v28 in p_u_12._input:get_controller_enable_virtual_cursor_keycode_list():key_itr() do
                    p27:get_element_list():push_back(v28)
                end;
            end, function(p29, p30, p31, _, p32) --[[ Line: 107 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): p_u_12 ]]
                if p29 == -1 then
                    p30.Text = "Add Keybind"
                    p31.Image = v_u_1:gear_assetid()
                    p32:set_select_button_text("Add")
                    p32:set_select_button_enabled(true)
                else
                    p30.Text = p_u_12._input:button_keycode_to_name(p29)
                    p31.Image = v_u_1:important_assetid()
                    p32:set_select_button_text("-")
                    p32:set_select_button_enabled(false)
                end;
            end, function(p33) --[[ Line: 120 ]]
                --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_10, (ref 3): p_u_13, (ref 4): p_u_14, (copy 5): v_u_25, (ref 6): v_u_26 ]]
                if p33 ~= nil then
                    if p33 == -1 then
                        local v_u_34 = nil
                        v_u_34 = p_u_12._menus:push_menu(v_u_10:new(p_u_12, p_u_13, p_u_14):set_text("Press a key...", string.format("Press a key to bind for Show Virtual Cursor"))):set_update_fn(function() --[[ Line: 128 ]]
                            --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_25, (ref 3): v_u_10, (ref 4): p_u_13, (ref 5): p_u_14, (ref 6): v_u_26, (ref 7): v_u_34 ]]
                            if p_u_12._input:has_recorded_controller_keycode_input() == true then
                                if v_u_25:contains((p_u_12._input:get_recorded_controller_keycode())) == false then
                                    p_u_12._player_settings_manager:add_controller_show_cursor_keybind(p_u_12, p_u_12._input:get_recorded_controller_keycode())
                                else
                                    p_u_12._menus:push_menu(v_u_10:new(p_u_12, p_u_13, p_u_14):set_text("Failed", "Cannot bind this button to Show Virtual Cursor."))
                                end;
                                p_u_12._input:cancel_record_next_controller_keycode_input()
                                v_u_26:refresh()
                                p_u_14:remove_menu(v_u_34)
                            end;
                        end)
                        p_u_12._input:record_next_controller_keycode_input()
                    end;
                end;
            end, nil, game.ReplicatedStorage.LobbyElementProtos.PreviewGameUIProto.PreviewGameSettingsListUI:Clone())):set_close_on_element_select(false)
        end;
        local v_u_35 = nil
        v_u_35 = v_u_7:new(p_u_12, p_u_12._spui, p_u_12._menus, function(p36) --[[ Line: 157 ]]
            --[[ Upvalues: (ref 1): v_u_4 ]]
            p36:set_header_text("Controller Keybinds")
            for _, v37 in v_u_4:get_track_index_list():key_itr() do
                p36:get_element_list():push_back(v37)
            end;
            p36:get_element_list():push_back(-2)
            p36:get_element_list():push_back(-1)
        end, function(p38, p39, p40, _, p41) --[[ Line: 165 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_1, (ref 3): v_u_3 ]]
            if p_u_12._input:get_track_index_set():contains(p38) then
                p39.Text = string.format("Track %d", p_u_12._input:get_key_to_track_index():get(p38))
                p40.Image = v_u_1:important_assetid()
                local v42 = v_u_3:new()
                for _, v43 in p_u_12._input:get_controller_track_enum_to_keycodes():list_of(p38):key_itr() do
                    v42:push_back(p_u_12._input:button_keycode_to_name(v43))
                end;
                if v42:count() == 0 then
                    p41:get_description_display().Text = "(None)"
                else
                    p41:get_description_display().Text = v_u_1:string_join(v42:get_table(), ", ")
                end;
            elseif p38 == -2 then
                p39.Text = "Show Virtual Cursor"
                p40.Image = v_u_1:important_assetid()
                local v44 = v_u_3:new()
                for _, v45 in p_u_12._input:get_controller_enable_virtual_cursor_keycode_list():key_itr() do
                    v44:push_back(p_u_12._input:button_keycode_to_name(v45))
                end;
                if v44:count() == 0 then
                    p41:get_description_display().Text = "(None)"
                else
                    p41:get_description_display().Text = v_u_1:string_join(v44:get_table(), ", ")
                end;
            else
                if p38 == -1 then
                    p39.Text = "Reset to Default"
                    p40.Image = v_u_1:gear_assetid()
                end;
                return;
            end;
        end, function(p46) --[[ Line: 198 ]]
            --[[ Upvalues: (copy 1): p_u_12, (copy 2): p_u_14, (ref 3): v_u_10, (copy 4): p_u_13, (ref 5): v_u_35, (copy 6): f_show_menu_for_controller_enable_virtual_cursor_button, (copy 7): f_show_menu_for_track_enum ]]
            if p46 == nil then
                if p_u_12._player_settings_manager:has_changes() then
                    local v_u_47 = p_u_14:push_menu(v_u_10:new(p_u_12, p_u_13, p_u_14):set_text("Saving", "Please wait...")):set_close_button_visible(false)
                    p_u_12._player_settings_manager:save_changes_to_playerblob(p_u_12, function() --[[ Line: 202 ]]
                        --[[ Upvalues: (ref 1): p_u_12, (ref 2): p_u_14, (copy 3): v_u_47 ]]
                        p_u_12._player_settings_manager:clear_changes()
                        p_u_14:remove_menu(v_u_47)
                    end)
                end;
                p_u_14:remove_menu(v_u_35)
                return;
            elseif p46 == -1 then
                p_u_12._player_settings_manager:reset_default_controller_keybinds(p_u_12)
                v_u_35:refresh()
                return;
            elseif p46 == -2 then
                f_show_menu_for_controller_enable_virtual_cursor_button()
            elseif p_u_12._input:get_track_index_set():contains(p46) == true then
                f_show_menu_for_track_enum(p46)
            end;
        end, nil, game.ReplicatedStorage.LobbyElementProtos.PreviewGameUIProto.PreviewGameSettingsListUI:Clone()):set_close_on_element_select(false)
        return v_u_35;
    end
};
