-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:04 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_5 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_7 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_8 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_58 = {
    ["new"] = function(_, p_u_9, p_u_10) --[[ Name: new ]] --[[ Line: 15 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1, (copy 3): v_u_7, (copy 4): v_u_4, (copy 5): v_u_3, (copy 6): v_u_6, (copy 7): v_u_8, (copy 8): v_u_5 ]]
        local l__spui_0 = p_u_9._spui
        local l__menus_0 = p_u_9._menus
        local v_u_11 = v_u_2:new(l__spui_0, l__menus_0)
        local v_u_12 = nil
        local v_u_13 = nil
        local v_u_14 = nil
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = Vector2.new()
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = nil
        v_u_11.get_title_display = function(_) --[[ Name: get_title_display ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            return v_u_21;
        end;
        v_u_11.get_sub_text_display = function(_) --[[ Name: get_sub_text_display ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            return v_u_22;
        end;
        v_u_11.get_text_box = function(_) --[[ Name: get_text_box ]] --[[ Line: 38 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23;
        end;
        v_u_11.eval = function(p25, p26) --[[ Name: eval ]] --[[ Line: 39 ]]
            p26(p25)
            return p25;
        end;
        local function _() --[[ Name: update_screen_gui_frame_scale ]] --[[ Line: 46 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_19, (ref 3): v_u_20 ]]
            local v27 = v_u_1:screen_size()
            v_u_20.Scale = math.min(1, 1 / math.max(v_u_19.X / v27.X / 0.85, v_u_19.Y / v27.Y / 0.75))
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_7, (copy 3): v_u_11, (ref 4): v_u_12, (copy 5): p_u_9, (ref 6): v_u_4, (ref 7): v_u_3, (copy 8): l__spui_0, (copy 9): l__menus_0, (ref 10): v_u_6, (ref 11): v_u_16, (ref 12): v_u_14, (ref 13): v_u_15, (ref 14): v_u_17, (ref 15): v_u_18, (ref 16): v_u_19, (ref 17): v_u_20, (ref 18): v_u_21, (ref 19): v_u_22, (ref 20): v_u_23, (ref 21): v_u_24, (ref 22): v_u_1 ]]
            if p_u_10 == nil then
                p_u_10 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Util.ScreenGuiTextBoxUI:Clone()
            end;
            p_u_10.Parent = v_u_7:get_world_ui_folder()
            v_u_11._native_size = p_u_10.PrimaryPart.Size
            v_u_11._size = v_u_11._native_size
            v_u_12 = v_u_11:add_cycle_element(p_u_9, 1, v_u_4:new(v_u_3:new(v_u_11, p_u_10.PrimaryPart, p_u_10.BackButtonSurface), l__spui_0, function() --[[ Line: 67 ]]
                --[[ Upvalues: (ref 1): l__menus_0, (ref 2): v_u_11, (ref 3): p_u_9, (ref 4): v_u_6, (ref 5): v_u_16 ]]
                l__menus_0:remove_menu(v_u_11)
                if p_u_9 ~= nil then
                    p_u_9._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
                end;
                if v_u_16 ~= nil then
                    v_u_16()
                    v_u_16 = nil
                end;
            end))
            v_u_14 = v_u_11:add_cycle_element(p_u_9, 1, v_u_4:new(v_u_3:new(v_u_11, p_u_10.PrimaryPart, p_u_10.OkayButtonSurface), l__spui_0, function() --[[ Line: 82 ]]
                --[[ Upvalues: (ref 1): l__menus_0, (ref 2): v_u_11, (ref 3): p_u_9, (ref 4): v_u_6, (ref 5): v_u_15 ]]
                l__menus_0:remove_menu(v_u_11)
                if p_u_9 ~= nil then
                    p_u_9._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
                end;
                if v_u_15 ~= nil then
                    v_u_15(v_u_11)
                    v_u_15 = nil
                end;
            end))
            v_u_14:set_visible(false)
            v_u_17 = Instance.new("ScreenGui")
            v_u_17.ZIndexBehavior = Enum.ZIndexBehavior.Sibling
            v_u_17.Name = "ScreenGuiTextBoxUI"
            v_u_18 = p_u_10.ScreenGuiFrame
            v_u_19 = v_u_18.AbsoluteSize
            v_u_18.Parent = v_u_17
            v_u_20 = Instance.new("UIScale")
            v_u_20.Scale = 1
            v_u_20.Parent = v_u_18
            v_u_21 = v_u_18.TitleDisplay
            v_u_22 = v_u_18.SubTextDisplay
            v_u_23 = v_u_18.TextBoxSection.TextBox
            v_u_21.Text = ""
            v_u_22.Text = ""
            v_u_23.Text = ""
            v_u_24 = v_u_18.TextBoxSection.EmptyLabel
            v_u_24.Text = ""
            v_u_24.Visible = false
            v_u_1:ptry(function() --[[ Line: 119 ]]
                --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_1 ]]
                v_u_17.Parent = v_u_1:get_local_player().PlayerGui
            end)
            local v28 = v_u_1:screen_size()
            v_u_20.Scale = math.min(1, 1 / math.max(v_u_19.X / v28.X / 0.85, v_u_19.Y / v28.Y / 0.75))
            v_u_11:reset_selected_item()
            v_u_11:transition_update_visual(0)
            v_u_11:layout()
        end;
        v_u_11.set_okay_button_fn = function(p29, p30) --[[ Name: set_okay_button_fn ]] --[[ Line: 130 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_15 ]]
            v_u_14:set_visible(true)
            v_u_15 = p30
            return p29;
        end;
        v_u_11.set_cancel_button_fn = function(p31, p32) --[[ Name: set_cancel_button_fn ]] --[[ Line: 136 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            v_u_16 = p32
            return p31;
        end;
        v_u_11.select_all_text_box = function(_) --[[ Name: select_all_text_box ]] --[[ Line: 141 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23:CaptureFocus()
            v_u_23.SelectionStart = 1
            v_u_23.CursorPosition = #v_u_23.Text + 1
        end;
        local v_u_33 = nil
        v_u_11.set_max_length = function(_, p_u_34) --[[ Name: set_max_length ]] --[[ Line: 148 ]]
            --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_23 ]]
            if v_u_33 ~= nil then
                v_u_33:Disconnect()
                v_u_33 = nil
            end;
            v_u_33 = v_u_23:GetPropertyChangedSignal("Text"):Connect(function() --[[ Line: 153 ]]
                --[[ Upvalues: (ref 1): v_u_23, (copy 2): p_u_34 ]]
                if p_u_34 < #v_u_23.Text then
                    v_u_23.Text = string.sub(v_u_23.Text, 1, p_u_34)
                end;
            end)
        end;
        v_u_11.set_text_box_empty_text = function(p35, p36) --[[ Name: set_text_box_empty_text ]] --[[ Line: 160 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_23 ]]
            v_u_24.TextSize = v_u_23.TextSize
            v_u_24.Text = p36
            local function _() --[[ Name: update_empty_text_visible ]] --[[ Line: 163 ]]
                --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24 ]]
                if #v_u_23.Text == 0 then
                    v_u_24.Visible = true
                else
                    v_u_24.Visible = false
                end;
            end;
            if #v_u_23.Text == 0 then
                v_u_24.Visible = true
            else
                v_u_24.Visible = false
            end;
            v_u_23:GetPropertyChangedSignal("Text"):Connect(function() --[[ Line: 171 ]]
                --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24 ]]
                if #v_u_23.Text == 0 then
                    v_u_24.Visible = true
                else
                    v_u_24.Visible = false
                end;
            end)
            return p35;
        end;
        v_u_11.set_on_close_fn = function(p37, p38) --[[ Name: set_on_close_fn ]] --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            v_u_13 = p38
            return p37;
        end;
        v_u_11.set_close_button_visible = function(p39, p40) --[[ Name: set_close_button_visible ]] --[[ Line: 183 ]]
            --[[ Upvalues: (ref 1): v_u_12 ]]
            v_u_12:set_visible(p40)
            return p39;
        end;
        v_u_11.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 188 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_17, (ref 3): v_u_13, (ref 4): p_u_10 ]]
            v_u_18.Parent = nil
            v_u_17.Parent = nil
            v_u_17 = nil
            if v_u_13 ~= nil then
                v_u_13()
                v_u_13 = nil
            end;
            p_u_10:Destroy()
        end;
        local v_u_41 = nil
        v_u_11.set_update_fn = function(p42, p43) --[[ Name: set_update_fn ]] --[[ Line: 201 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            v_u_41 = p43
            return p42;
        end;
        local v_u_44 = 0
        v_u_11.behaviour_update = function(p45, p46, _) --[[ Name: behaviour_update ]] --[[ Line: 207 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_41, (ref 3): v_u_12, (ref 4): v_u_44, (ref 5): v_u_8, (ref 6): v_u_5 ]]
            p45:behaviour_update_base(p46, p_u_9)
            if v_u_41 ~= nil then
                v_u_41(p46, p45)
            end;
            if v_u_12 and v_u_12:get_visible() == false then
                v_u_44 = v_u_44 + v_u_8:TimescaleToDeltaTime(p46)
                if v_u_44 > 10 then
                    v_u_5:warnf("ScreenGuiTextBoxUI with close button hidden timed out, showing close button")
                    v_u_44 = 0
                    p45:set_close_button_visible(true)
                end;
            end;
        end;
        local v_u_47 = 1
        local v_u_48 = 1
        v_u_11.layout = function(p49) --[[ Name: layout ]] --[[ Line: 224 ]]
            --[[ Upvalues: (copy 1): l__spui_0, (ref 2): v_u_48, (ref 3): p_u_10, (ref 4): v_u_1, (ref 5): v_u_19, (ref 6): v_u_20 ]]
            l__spui_0:uiobj_rescale_to_max_nxy(p49, 0.85, 0.75, v_u_48)
            p_u_10:SetPrimaryPartCFrame(l__spui_0:get_cframe({
                ["PositionNXY"] = Vector2.new(0.5, 0.5),
                ["OffsetXYZ"] = p49:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            }))
            if l__spui_0:is_layout_updated() then
                local v50 = v_u_1:screen_size()
                v_u_20.Scale = math.min(1, 1 / math.max(v_u_19.X / v50.X / 0.85, v_u_19.Y / v50.Y / 0.75))
            end;
        end;
        v_u_11.set_alpha = function(_, p51) --[[ Name: set_alpha ]] --[[ Line: 237 ]]
            --[[ Upvalues: (ref 1): v_u_47, (ref 2): v_u_1, (ref 3): p_u_10, (ref 4): v_u_18 ]]
            if v_u_47 ~= p51 then
                v_u_47 = p51
                v_u_1:r_set_alpha_v2(p_u_10, v_u_47)
                if v_u_18 ~= nil then
                    v_u_18.GroupTransparency = v_u_1:tra(p51)
                end;
            end;
        end;
        v_u_11.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 246 ]]
            --[[ Upvalues: (ref 1): v_u_47 ]]
            return v_u_47;
        end;
        v_u_11.set_scale = function(_, p52) --[[ Name: set_scale ]] --[[ Line: 247 ]]
            --[[ Upvalues: (ref 1): v_u_48 ]]
            v_u_48 = p52
        end;
        v_u_11.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 248 ]]
            --[[ Upvalues: (ref 1): v_u_48 ]]
            return v_u_48;
        end;
        v_u_11.get_native_size = function(p53) --[[ Name: get_native_size ]] --[[ Line: 250 ]]
            return p53._native_size;
        end;
        v_u_11.get_size = function(p54) --[[ Name: get_size ]] --[[ Line: 253 ]]
            return p54._size;
        end;
        v_u_11.set_size = function(p55, p56) --[[ Name: set_size ]] --[[ Line: 256 ]]
            --[[ Upvalues: (ref 1): p_u_10 ]]
            p55._size = p56
            p_u_10.PrimaryPart.Size = Vector3.new(p56.X, p56.Y, 0)
        end;
        v_u_11.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 260 ]]
            --[[ Upvalues: (ref 1): p_u_10 ]]
            return p_u_10.PrimaryPart.Position;
        end;
        v_u_11.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 263 ]]
            --[[ Upvalues: (ref 1): p_u_10 ]]
            return p_u_10.PrimaryPart.SurfaceGui;
        end;
        v_u_11.set_showing = function(_, p57) --[[ Name: set_showing ]] --[[ Line: 266 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_7 ]]
            if p57 then
                p_u_10.Parent = v_u_7:get_world_ui_folder()
            else
                p_u_10.Parent = nil
            end;
        end;
        f_cons()
        return v_u_11;
    end
}
v_u_58.show_message_box_ui = function(_, p59, p_u_60, p_u_61, p_u_62) --[[ Name: show_message_box_ui ]] --[[ Line: 278 ]]
    --[[ Upvalues: (copy 1): v_u_58 ]]
    return p59._menus:push_menu(v_u_58:new(p59):eval(function(p63) --[[ Line: 281 ]]
        --[[ Upvalues: (copy 1): p_u_60, (copy 2): p_u_61, (copy 3): p_u_62 ]]
        p63:get_title_display().Text = p_u_60
        p63:get_sub_text_display().Text = p_u_61
        p63:get_text_box().Text = p_u_62
        p63:get_text_box().TextEditable = false
    end));
end;
v_u_58.show_text_input_box_ui = function(_, p64, p_u_65, p_u_66, p_u_67, p_u_68) --[[ Name: show_text_input_box_ui ]] --[[ Line: 290 ]]
    --[[ Upvalues: (copy 1): v_u_58 ]]
    return p64._menus:push_menu(v_u_58:new(p64):eval(function(p_u_69) --[[ Line: 293 ]]
        --[[ Upvalues: (copy 1): p_u_65, (copy 2): p_u_66, (copy 3): p_u_67, (copy 4): p_u_68 ]]
        p_u_69:get_title_display().Text = p_u_65
        p_u_69:get_sub_text_display().Text = p_u_66
        p_u_69:get_text_box().Text = p_u_67
        p_u_69:get_text_box().TextEditable = true
        p_u_69:get_text_box():CaptureFocus()
        p_u_69:set_okay_button_fn(function() --[[ Line: 299 ]]
            --[[ Upvalues: (copy 1): p_u_69, (ref 2): p_u_68 ]]
            p_u_68(p_u_69:get_text_box().Text)
        end)
    end));
end;
return v_u_58;
