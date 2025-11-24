-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:41 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Lobby.UI.SPUITextInput)
local v_u_8 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_10 = require(game.ReplicatedStorage.Lobby.Menus.KeyBindsUIController)
local v_u_11 = {
    ["BindButton"] = {}
}
local v_u_12 = v_u_1:get_news_pageitem_unselected_assetid()
local v_u_13 = v_u_1:get_news_pageitem_selected_assetid()
v_u_11.BindButton.new = function(_, p_u_14, p15, p_u_16) --[[ Name: new ]] --[[ Line: 22 ]]
    --[[ Upvalues: (copy 1): v_u_13, (copy 2): v_u_12 ]]
    local v18 = {
        ["cons"] = function(p17) --[[ Name: cons ]] --[[ Line: 28 ]]
            p17:update_display(false)
        end
    }
    local l_ImageLabel_0 = p15.SurfaceGui.Frame.ImageLabel
    local l_TextLabel_0 = p15.SurfaceGui.Frame.TextLabel
    v18.update_display = function(_, p19) --[[ Name: update_display ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): l_ImageLabel_0, (ref 2): v_u_13, (copy 3): l_TextLabel_0, (ref 4): v_u_12, (copy 5): p_u_14, (copy 6): p_u_16 ]]
        if p19 == true then
            l_ImageLabel_0.Image = v_u_13
            l_TextLabel_0.Text = "Press Key..."
        else
            l_ImageLabel_0.Image = v_u_12
            l_TextLabel_0.Text = p_u_14._input:get_key_display_str(p_u_16)
        end;
    end;
    v18.get_key = function(_) --[[ Name: get_key ]] --[[ Line: 42 ]]
        --[[ Upvalues: (copy 1): p_u_16 ]]
        return p_u_16;
    end;
    v18:cons()
    return v18;
end;
v_u_11.new = function(_, p_u_20, p_u_21, p_u_22) --[[ Name: new ]] --[[ Line: 48 ]]
    --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_3, (copy 3): v_u_2, (copy 4): v_u_1, (copy 5): v_u_7, (copy 6): v_u_5, (copy 7): v_u_4, (copy 8): v_u_6, (copy 9): v_u_8, (copy 10): v_u_9, (copy 11): v_u_11 ]]
    if p_u_20._input:is_controller_active() then
        return v_u_10:new(p_u_20, p_u_21, p_u_22);
    end;
    local v_u_23 = v_u_3:new(p_u_21, p_u_22)
    local v_u_24 = nil
    local v_u_25 = 1
    local v_u_26 = 1
    local v_u_27 = v_u_2:new()
    local v_u_28 = nil
    local function _(p29) --[[ Name: get_bind_button_for_key ]] --[[ Line: 60 ]]
        --[[ Upvalues: (copy 1): v_u_27 ]]
        for v30 = 1, v_u_27:count() do
            if v_u_27:get(v30):get_key() == p29 then
                return v_u_27:get(v30);
            end;
        end;
        return nil;
    end;
    local v_u_31 = nil
    v_u_23.set_on_close_fn = function(p32, p33) --[[ Name: set_on_close_fn ]] --[[ Line: 70 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        v_u_31 = p33
        return p32;
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 75 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_1, (ref 3): v_u_7, (copy 4): v_u_23, (copy 5): p_u_20, (ref 6): v_u_5, (ref 7): v_u_4, (copy 8): p_u_21, (copy 9): p_u_22, (ref 10): v_u_6, (ref 11): v_u_31, (ref 12): v_u_8, (ref 13): v_u_9 ]]
        v_u_24 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.KeyBindsUI:Clone()
        v_u_24.Name = v_u_1:gen_name(v_u_24.Name)
        v_u_24.Parent = v_u_7:get_world_ui_folder()
        v_u_23._native_size = v_u_24.PrimaryPart.Size
        v_u_23._size = v_u_23._native_size
        v_u_23:add_cycle_element(p_u_20, 1, v_u_5:new(v_u_4:new(v_u_23, v_u_24.PrimaryPart, v_u_24.BackButtonSurface), p_u_21, function() --[[ Line: 86 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_23, (ref 3): p_u_20, (ref 4): v_u_6, (ref 5): v_u_31 ]]
            p_u_22:remove_menu(v_u_23)
            p_u_20._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
            if v_u_31 then
                v_u_31()
            end;
        end))
        v_u_23:add_cycle_element(p_u_20, 1, v_u_5:new(v_u_4:new(v_u_23, v_u_24.PrimaryPart, v_u_24.ResetButton), p_u_21, function() --[[ Line: 98 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23:reset_keybinds()
        end))
        v_u_23:create_bind_button(v_u_24.IngameChatButton, v_u_8.KEY_MENU_MATCHMAKING_CHAT_FOCUS)
        v_u_23:create_bind_button(v_u_24.ChatWindowButton, v_u_8.KEY_CHAT_WINDOW_FOCUS)
        v_u_23:create_bind_button(v_u_24.Track1Button, v_u_8.KEY_TRACK1)
        v_u_23:create_bind_button(v_u_24.Track2Button, v_u_8.KEY_TRACK2)
        v_u_23:create_bind_button(v_u_24.Track3Button, v_u_8.KEY_TRACK3)
        v_u_23:create_bind_button(v_u_24.Track4Button, v_u_8.KEY_TRACK4)
        if v_u_9.PowerBarManualEnabled == true then
            v_u_23:create_bind_button(v_u_24.ManualFeverButton, v_u_8.KEY_POWERBAR_TRIGGER)
        else
            v_u_24.ManualFeverButton.Parent = nil
            v_u_24.PrimaryPart.SurfaceGui.Frame.IngameLabels.ManualFeverLabel.Visible = false
        end;
        v_u_23:update_bind_buttons()
        v_u_23:reset_selected_item()
        v_u_23:transition_update_visual(0)
        v_u_23:layout()
    end;
    v_u_23.create_bind_button = function(p_u_34, p35, p36) --[[ Name: create_bind_button ]] --[[ Line: 123 ]]
        --[[ Upvalues: (ref 1): v_u_11, (copy 2): p_u_20, (copy 3): v_u_27, (ref 4): v_u_5, (ref 5): v_u_4, (ref 6): v_u_24, (copy 7): p_u_21 ]]
        local v_u_37 = v_u_11.BindButton:new(p_u_20, p35, p36)
        v_u_27:push_back(v_u_37)
        p_u_34:add_cycle_element(p_u_20, 1, v_u_5:new(v_u_4:new(p_u_34, v_u_24.PrimaryPart, p35), p_u_21, function() --[[ Line: 129 ]]
            --[[ Upvalues: (copy 1): p_u_34, (copy 2): v_u_37 ]]
            p_u_34:bind_button_pressed(v_u_37)
        end))
    end;
    v_u_23.update_bind_buttons = function(_) --[[ Name: update_bind_buttons ]] --[[ Line: 135 ]]
        --[[ Upvalues: (copy 1): v_u_27, (ref 2): v_u_28 ]]
        for v38 = 1, v_u_27:count() do
            local v39 = v_u_27:get(v38)
            v39:update_display(v39 == v_u_28)
        end;
    end;
    v_u_23.bind_button_pressed = function(p40, p41) --[[ Name: bind_button_pressed ]] --[[ Line: 142 ]]
        --[[ Upvalues: (ref 1): v_u_28, (copy 2): p_u_20 ]]
        v_u_28 = p41
        p_u_20._input:record_next_keycode_input()
        p40:update_bind_buttons()
    end;
    v_u_23.reset_keybinds = function(p42) --[[ Name: reset_keybinds ]] --[[ Line: 148 ]]
        --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_28 ]]
        p_u_20._input:cancel_record_next_keycode_input()
        p_u_20._player_settings_manager:reset_keybinds(p_u_20)
        v_u_28 = nil
        p42:update_bind_buttons()
    end;
    v_u_23.behaviour_update = function(p43, p44, _) --[[ Name: behaviour_update ]] --[[ Line: 155 ]]
        --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_28 ]]
        p43:behaviour_update_base(p44, p_u_20)
        if v_u_28 ~= nil and p_u_20._input:has_recorded_keycode_input() == true then
            local v45 = p_u_20._input:get_recorded_keycode()
            p_u_20._input:cancel_record_next_keycode_input()
            p_u_20._player_settings_manager:set_keybind(p_u_20, v_u_28:get_key(), v45)
            v_u_28 = nil
            p43:update_bind_buttons()
        end;
    end;
    v_u_23.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 168 ]]
        --[[ Upvalues: (ref 1): v_u_24, (copy 2): p_u_20 ]]
        v_u_24:Destroy()
        p_u_20._input:cancel_record_next_keycode_input()
    end;
    v_u_23.layout = function(p46) --[[ Name: layout ]] --[[ Line: 173 ]]
        --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_26, (ref 3): v_u_24 ]]
        p46:opt_rescale_to_max_nxy(p_u_21, 0.7, 0.7, v_u_26)
        local v47, v48 = p46:opt_update_cframe_params(p_u_21, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p46:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v47 == true then
            v_u_24:SetPrimaryPartCFrame(v48)
        end;
    end;
    v_u_23.set_alpha = function(_, p49) --[[ Name: set_alpha ]] --[[ Line: 185 ]]
        --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_1, (ref 3): v_u_24 ]]
        if v_u_25 ~= p49 then
            v_u_25 = p49
            v_u_1:r_set_alpha(v_u_24, v_u_25)
        end;
    end;
    v_u_23.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 191 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        return v_u_25;
    end;
    v_u_23.set_scale = function(_, p50) --[[ Name: set_scale ]] --[[ Line: 192 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        v_u_26 = p50
    end;
    v_u_23.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 193 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26;
    end;
    v_u_23.get_native_size = function(p51) --[[ Name: get_native_size ]] --[[ Line: 195 ]]
        return p51._native_size;
    end;
    v_u_23.get_size = function(p52) --[[ Name: get_size ]] --[[ Line: 198 ]]
        return p52._size;
    end;
    v_u_23.set_size = function(p53, p54) --[[ Name: set_size ]] --[[ Line: 201 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        p53._size = p54
        v_u_24.PrimaryPart.Size = Vector3.new(p54.X, p54.Y, 0)
    end;
    v_u_23.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 205 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24.PrimaryPart.Position;
    end;
    v_u_23.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 208 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24.PrimaryPart.SurfaceGui;
    end;
    f_cons()
    return v_u_23;
end;
return v_u_11;
