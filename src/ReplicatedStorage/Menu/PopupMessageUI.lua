-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:03 PM
-- Time elapsed: 12 milliseconds

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
local v_u_11 = {
    ["Type"] = "PopupMessageUI",
    ["remove_loading_menu"] = function(_, p9, p10) --[[ Name: remove_loading_menu ]] --[[ Line: 237 ]]
        p9._menus:remove_menu(p10)
    end
}
v_u_11.new = function(_, p_u_12, p_u_13, p_u_14, p_u_15) --[[ Name: new ]] --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_11, (copy 3): v_u_7, (copy 4): v_u_4, (copy 5): v_u_3, (copy 6): v_u_1, (copy 7): v_u_6, (copy 8): v_u_8, (copy 9): v_u_5 ]]
    local v16 = v_u_2:new(p_u_13, p_u_14)
    v16.Type = v_u_11.Type
    local v_u_17 = 1
    local v_u_18 = 1
    local v_u_19 = nil
    local v_u_20 = nil
    local v_u_21 = nil
    local v_u_22 = nil
    local v_u_23 = nil
    local v_u_24 = nil
    local v_u_25 = nil
    local v_u_26 = nil
    local v_u_27 = nil
    v16.cons = function(p_u_28) --[[ Name: cons ]] --[[ Line: 35 ]]
        --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_7, (ref 3): v_u_19, (copy 4): p_u_12, (ref 5): v_u_4, (ref 6): v_u_3, (copy 7): p_u_13, (ref 8): v_u_21, (ref 9): v_u_24, (ref 10): v_u_26, (ref 11): v_u_25, (ref 12): v_u_27, (ref 13): v_u_1 ]]
        if p_u_15 == nil then
            p_u_15 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Util.PopupMessageV2UI:Clone()
        end;
        p_u_15.Parent = v_u_7:get_world_ui_folder()
        p_u_28._native_size = p_u_15.PrimaryPart.Size
        p_u_28._size = p_u_28._native_size
        v_u_19 = p_u_28:add_cycle_element(p_u_12, 1, v_u_4:new(v_u_3:new(p_u_28, p_u_15.PrimaryPart, p_u_15.BackButtonSurface), p_u_13, function() --[[ Line: 47 ]]
            --[[ Upvalues: (copy 1): p_u_28 ]]
            p_u_28:on_back_button()
        end))
        v_u_21 = p_u_28:add_cycle_element(p_u_12, 1, v_u_4:new(v_u_3:new(p_u_28, p_u_15.PrimaryPart, p_u_15.OkayButtonSurface), p_u_13, function() --[[ Line: 53 ]]
            --[[ Upvalues: (copy 1): p_u_28 ]]
            p_u_28:on_okay_button()
        end))
        v_u_21:set_visible(false)
        v_u_24 = p_u_15.MainSurface.SurfaceGui.Frame.Title
        v_u_26 = p_u_15.MainSurface.SurfaceGui.Frame.Sub
        v_u_25 = v_u_24.TextLabel
        v_u_27 = v_u_26.TextLabel
        v_u_24.Name = v_u_1:r_set_alpha_generate_name({
            ["BackgroundAlpha"] = 0.35
        }, "Title")
        v_u_26.Name = v_u_1:r_set_alpha_generate_name({
            ["BackgroundAlpha"] = 0.35
        }, "Sub")
        p_u_28:reset_selected_item()
        p_u_28:transition_update_visual(0)
        p_u_28:layout()
    end;
    v16.set_on_close_fn = function(p29, p30) --[[ Name: set_on_close_fn ]] --[[ Line: 70 ]]
        --[[ Upvalues: (ref 1): v_u_20 ]]
        v_u_20 = p30
        return p29;
    end;
    v16.set_close_button_visible = function(p31, p32) --[[ Name: set_close_button_visible ]] --[[ Line: 75 ]]
        --[[ Upvalues: (ref 1): v_u_19 ]]
        v_u_19:set_visible(p32)
        return p31;
    end;
    local v_u_33 = true
    v16.is_active = function(_) --[[ Name: is_active ]] --[[ Line: 81 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        return v_u_33;
    end;
    v16.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 83 ]]
        --[[ Upvalues: (ref 1): v_u_20, (ref 2): p_u_15, (ref 3): v_u_33 ]]
        if v_u_20 ~= nil then
            v_u_20()
            v_u_20 = nil
        end;
        p_u_15:Destroy()
        v_u_33 = false
    end;
    v16.set_text = function(p34, p35, p36) --[[ Name: set_text ]] --[[ Line: 92 ]]
        --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_27 ]]
        v_u_25.Text = tostring(p35)
        v_u_27.Text = tostring(p36)
        return p34;
    end;
    v16.set_rich_text = function(p37, p38, p39) --[[ Name: set_rich_text ]] --[[ Line: 98 ]]
        --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_27 ]]
        v_u_25.RichText = true
        v_u_27.RichText = true
        v_u_25.Text = tostring(p38)
        v_u_27.Text = tostring(p39)
        return p37;
    end;
    v16.set_title_sub_visible = function(p40, p41) --[[ Name: set_title_sub_visible ]] --[[ Line: 106 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_26, (ref 3): v_u_1, (ref 4): p_u_15, (ref 5): v_u_17 ]]
        v_u_24.Visible = p41
        v_u_26.Name = v_u_1:r_set_alpha_generate_name({
            ["BackgroundAlpha"] = p41 and 0.65 or 0
        }, "Sub")
        v_u_1:r_set_alpha(p_u_15, v_u_17)
        return p40;
    end;
    v16.on_back_button = function(p42) --[[ Name: on_back_button ]] --[[ Line: 117 ]]
        --[[ Upvalues: (copy 1): p_u_14, (copy 2): p_u_12, (ref 3): v_u_6, (ref 4): v_u_23, (ref 5): v_u_20 ]]
        p_u_14:remove_menu(p42)
        if p_u_12 ~= nil then
            p_u_12._sfx_manager:play_sfx(v_u_6.SFX_MENU_CLOSE)
        end;
        if v_u_23 ~= nil then
            v_u_23()
            v_u_23 = nil
        end;
        if v_u_20 ~= nil then
            v_u_20()
            v_u_20 = nil
        end;
    end;
    local v_u_43 = nil
    v16.set_update_fn = function(p44, p45) --[[ Name: set_update_fn ]] --[[ Line: 133 ]]
        --[[ Upvalues: (ref 1): v_u_43 ]]
        v_u_43 = p45
        return p44;
    end;
    v16.set_okay_button_fn = function(p46, p47) --[[ Name: set_okay_button_fn ]] --[[ Line: 138 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_22 ]]
        v_u_21:set_visible(true)
        v_u_22 = p47
        return p46;
    end;
    v16.set_cancel_button_fn = function(p48, p49) --[[ Name: set_cancel_button_fn ]] --[[ Line: 144 ]]
        --[[ Upvalues: (ref 1): v_u_23 ]]
        v_u_23 = p49
        return p48;
    end;
    v16.on_okay_button = function(p50) --[[ Name: on_okay_button ]] --[[ Line: 149 ]]
        --[[ Upvalues: (copy 1): p_u_14, (copy 2): p_u_12, (ref 3): v_u_6, (ref 4): v_u_22 ]]
        p_u_14:remove_menu(p50)
        if p_u_12 ~= nil then
            p_u_12._sfx_manager:play_sfx(v_u_6.SFX_MENU_OPEN)
        end;
        if v_u_22 ~= nil then
            v_u_22()
            v_u_22 = nil
        end;
    end;
    local v_u_51 = true
    v16.set_visible = function(p52, p53) --[[ Name: set_visible ]] --[[ Line: 161 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        v_u_51 = p53
        return p52;
    end;
    local v_u_54 = 0
    v16.behaviour_update = function(p55, p56, _) --[[ Name: behaviour_update ]] --[[ Line: 167 ]]
        --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_43, (ref 3): v_u_19, (ref 4): v_u_54, (ref 5): v_u_8, (ref 6): v_u_5 ]]
        p55:behaviour_update_base(p56, p_u_12)
        if v_u_43 ~= nil then
            v_u_43(p56, p55)
        end;
        if v_u_19 and v_u_19:get_visible() == false then
            v_u_54 = v_u_54 + v_u_8:TimescaleToDeltaTime(p56)
            if v_u_54 > 10 then
                v_u_5:warnf("PopupMessageUI with close button hidden timed out, showing close button")
                v_u_54 = 0
                p55:set_close_button_visible(true)
            end;
        end;
    end;
    v16.layout = function(p57) --[[ Name: layout ]] --[[ Line: 182 ]]
        --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_18, (ref 3): p_u_15 ]]
        p_u_13:uiobj_rescale_to_max_nxy(p57, 0.85, 0.75, v_u_18)
        p_u_15:SetPrimaryPartCFrame(p_u_13:get_cframe({
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p57:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        }))
    end;
    v16.set_alpha = function(_, p58) --[[ Name: set_alpha ]] --[[ Line: 191 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_1, (ref 3): p_u_15 ]]
        if v_u_17 ~= p58 then
            v_u_17 = p58
            v_u_1:r_set_alpha(p_u_15, v_u_17)
        end;
    end;
    v16.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 197 ]]
        --[[ Upvalues: (ref 1): v_u_17 ]]
        return v_u_17;
    end;
    v16.set_scale = function(_, p59) --[[ Name: set_scale ]] --[[ Line: 198 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        v_u_18 = p59
    end;
    v16.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 199 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        return v_u_18;
    end;
    v16.get_native_size = function(p60) --[[ Name: get_native_size ]] --[[ Line: 201 ]]
        return p60._native_size;
    end;
    v16.get_size = function(p61) --[[ Name: get_size ]] --[[ Line: 204 ]]
        return p61._size;
    end;
    v16.set_size = function(p62, p63) --[[ Name: set_size ]] --[[ Line: 207 ]]
        --[[ Upvalues: (ref 1): p_u_15 ]]
        p62._size = p63
        p_u_15.PrimaryPart.Size = Vector3.new(p63.X, p63.Y, 0)
    end;
    v16.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 211 ]]
        --[[ Upvalues: (ref 1): p_u_15 ]]
        return p_u_15.PrimaryPart.Position;
    end;
    v16.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 214 ]]
        --[[ Upvalues: (ref 1): p_u_15 ]]
        return p_u_15.PrimaryPart.SurfaceGui;
    end;
    v16.set_showing = function(_, p64) --[[ Name: set_showing ]] --[[ Line: 217 ]]
        --[[ Upvalues: (ref 1): v_u_51, (ref 2): p_u_15, (ref 3): v_u_7 ]]
        if p64 and v_u_51 == true then
            p_u_15.Parent = v_u_7:get_world_ui_folder()
        else
            p_u_15.Parent = nil
        end;
    end;
    v16:cons()
    return v16;
end;
v_u_11.loading_menu = function(_, p65) --[[ Name: loading_menu ]] --[[ Line: 229 ]]
    --[[ Upvalues: (copy 1): v_u_11 ]]
    return p65._menus:push_menu(v_u_11:new(p65, p65._spui, p65._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false));
end;
return v_u_11;
