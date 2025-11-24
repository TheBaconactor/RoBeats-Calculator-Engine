-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:45 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_2 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_6 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_7 = require(game.ReplicatedStorage.Lobby.UI.SPUITextInput)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_8 = require(game.ReplicatedStorage.Shared.AssertType)
return {
    ["new"] = function(_, p_u_9, p_u_10, p_u_11, p_u_12, p_u_13, p14) --[[ Name: new ]] --[[ Line: 19 ]]
        --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_6, (copy 5): v_u_7, (copy 6): v_u_4, (copy 7): v_u_3, (copy 8): v_u_5 ]]
        local v_u_15 = p14 == nil and {} or p14
        v_u_8:is_number(p_u_12)
        v_u_8:is_function(p_u_13)
        local v_u_16 = v_u_2:new(p_u_10, p_u_11)
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = 0
        v_u_16.set_value_increment = function(p23, p24) --[[ Name: set_value_increment ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_22 ]]
            v_u_8:is_number(v_u_22)
            v_u_22 = p24
            return p23;
        end;
        local v_u_25 = -3e100
        local v_u_26 = 3e100
        v_u_16.set_range_min_max = function(p27, p28, p29) --[[ Name: set_range_min_max ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_25, (ref 3): v_u_26 ]]
            v_u_8:is_number(v_u_25)
            v_u_8:is_number(v_u_26)
            v_u_8:is_true(v_u_25 < v_u_26)
            v_u_25 = p28
            v_u_26 = p29
            return p27;
        end;
        v_u_16.set_reset_value = function(p30, p31) --[[ Name: set_reset_value ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): p_u_12, (ref 3): v_u_21 ]]
            v_u_8:is_number(p31)
            p_u_12 = p31
            v_u_21:set_empty_message((tostring(p_u_12)))
            return p30;
        end;
        local v_u_32 = nil
        v_u_16.set_fn_on_increment = function(p33, p34) --[[ Name: set_fn_on_increment ]] --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            v_u_32 = p34
            return p33;
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_1, (ref 3): v_u_6, (copy 4): v_u_16, (ref 5): v_u_18, (ref 6): v_u_21, (ref 7): v_u_7, (copy 8): p_u_9, (copy 9): p_u_10, (ref 10): v_u_15, (ref 11): p_u_12, (ref 12): v_u_25, (ref 13): v_u_26, (ref 14): v_u_4, (ref 15): v_u_3, (copy 16): p_u_11, (ref 17): v_u_5, (copy 18): p_u_13, (ref 19): v_u_19, (ref 20): v_u_22, (ref 21): v_u_32, (ref 22): v_u_20 ]]
            v_u_17 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.ValueInputUI:Clone()
            v_u_17.Name = v_u_1:gen_name(v_u_17.Name)
            v_u_17.Parent = v_u_6:get_world_ui_folder()
            v_u_16._native_size = v_u_17.PrimaryPart.Size
            v_u_16._size = v_u_16._native_size
            v_u_18 = v_u_17.MainSurface.SurfaceGui.Frame
            v_u_21 = v_u_7:new(p_u_9, v_u_18.TextSection.InputBarFrame.TextLabel, nil, v_u_16, p_u_10, v_u_15):set_send_behaviour_enabled(false)
            v_u_21:set_empty_message((tostring(p_u_12)))
            v_u_21:enforce_numeric(true, function(p35) --[[ Line: 86 ]]
                --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_1, (ref 3): v_u_25, (ref 4): v_u_26 ]]
                if v_u_15.AllowDecimals == true then
                    return v_u_1:clamp(p35, v_u_25, v_u_26);
                else
                    return v_u_1:clamp(math.floor(p35), v_u_25, v_u_26);
                end;
            end)
            v_u_16:add_cycle_element(p_u_9, 1, v_u_4:new(v_u_3:new(v_u_16, v_u_17.PrimaryPart, v_u_17.BackButtonSurface), p_u_10, function() --[[ Line: 97 ]]
                --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_16, (ref 3): p_u_9, (ref 4): v_u_5 ]]
                p_u_11:remove_menu(v_u_16)
                p_u_9._sfx_manager:play_sfx(v_u_5.SFX_MENU_CLOSE)
            end))
            v_u_16:add_cycle_element(p_u_9, 1, v_u_4:new(v_u_3:new(v_u_16, v_u_17.PrimaryPart, v_u_17.OkayButtonSurface), p_u_10, function() --[[ Line: 106 ]]
                --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_5, (ref 3): p_u_13, (ref 4): v_u_16, (ref 5): p_u_11 ]]
                p_u_9._sfx_manager:play_sfx(v_u_5.SFX_MENU_OPEN)
                p_u_13(v_u_16:get_value())
                p_u_11:remove_menu(v_u_16)
            end):set_passive_anim())
            v_u_19 = v_u_16:add_cycle_element(p_u_9, 1, v_u_4:new(v_u_3:new(v_u_16, v_u_17.PrimaryPart, v_u_17.IncrementValueButton), p_u_10, function() --[[ Line: 116 ]]
                --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_5, (ref 3): v_u_16, (ref 4): v_u_22, (ref 5): v_u_32 ]]
                p_u_9._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
                local v36 = v_u_16:get_value() + v_u_22
                if v_u_32 then
                    v36 = v_u_32(v36)
                end;
                v_u_16:set_value(v36)
            end):set_auto_zoffset_behaviour(true))
            v_u_20 = v_u_16:add_cycle_element(p_u_9, 1, v_u_4:new(v_u_3:new(v_u_16, v_u_17.PrimaryPart, v_u_17.DecrementValueButton), p_u_10, function() --[[ Line: 129 ]]
                --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_5, (ref 3): v_u_16, (ref 4): v_u_22, (ref 5): v_u_32 ]]
                p_u_9._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
                local v37 = v_u_16:get_value() - v_u_22
                if v_u_32 then
                    v37 = v_u_32(v37)
                end;
                v_u_16:set_value(v37)
            end):set_auto_zoffset_behaviour(true))
            v_u_16:add_cycle_element(p_u_9, 1, v_u_4:new(v_u_3:new(v_u_16, v_u_17.PrimaryPart, v_u_17.ResetDefaultButton), p_u_10, function() --[[ Line: 142 ]]
                --[[ Upvalues: (ref 1): p_u_9, (ref 2): v_u_5, (ref 3): v_u_16, (ref 4): p_u_12 ]]
                p_u_9._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
                v_u_16:set_value(p_u_12)
            end))
            v_u_16:set_value(p_u_12)
            v_u_16:transition_update_visual(0)
            v_u_16:layout()
        end;
        v_u_16.set_title_sub_text = function(p38, p39, p40) --[[ Name: set_title_sub_text ]] --[[ Line: 154 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            v_u_18.TextSection.TitleText.Text = p39
            v_u_18.TextSection.SubText.Text = p40
            return p38;
        end;
        local v_u_41 = nil
        v_u_16.set_value_display_info_fn = function(p42, p43) --[[ Name: set_value_display_info_fn ]] --[[ Line: 161 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            v_u_41 = p43
            p42:set_value(p42:get_value())
            return p42;
        end;
        local function f_update_value_display_info() --[[ Name: update_value_display_info ]] --[[ Line: 167 ]]
            --[[ Upvalues: (copy 1): v_u_16, (ref 2): v_u_41, (ref 3): v_u_18, (ref 4): v_u_19, (ref 5): v_u_26, (ref 6): v_u_20, (ref 7): v_u_25 ]]
            local v44 = v_u_16:get_value()
            if v_u_41 then
                local v45, v46 = v_u_41(v44)
                v_u_18.TextSection.ValueDisplay.Text = v45
                v_u_18.TextSection.ValueInfoDisplay.Text = v46
            else
                v_u_18.TextSection.ValueDisplay.Text = ""
                v_u_18.TextSection.ValueInfoDisplay.Text = ""
            end;
            v_u_19:set_visible(v44 ~= v_u_26)
            v_u_20:set_visible(v44 ~= v_u_25)
        end;
        v_u_16.set_value = function(p47, p48) --[[ Name: set_value ]] --[[ Line: 181 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_1, (ref 3): v_u_25, (ref 4): v_u_26, (ref 5): v_u_21, (copy 6): f_update_value_display_info ]]
            v_u_8:is_number(p48)
            v_u_21:set_text((tostring((v_u_1:clamp(p48, v_u_25, v_u_26)))))
            f_update_value_display_info()
            return p47;
        end;
        v_u_16.get_value = function(_) --[[ Name: get_value ]] --[[ Line: 189 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): p_u_12 ]]
            local v49 = tonumber(v_u_21:get_current_text())
            if v49 == nil then
                v49 = p_u_12
            end;
            return v49;
        end;
        v_u_16.behaviour_update = function(p50, p51, _) --[[ Name: behaviour_update ]] --[[ Line: 197 ]]
            --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_21, (copy 3): f_update_value_display_info ]]
            p50:behaviour_update_base(p51, p_u_9)
            v_u_21:update(p51)
            if v_u_21:raise_changed() then
                f_update_value_display_info()
            end;
        end;
        v_u_16.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 205 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_21 ]]
            v_u_17:Destroy()
            v_u_21:cleanup()
        end;
        v_u_16.layout = function(p52) --[[ Name: layout ]] --[[ Line: 210 ]]
            --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_17 ]]
            p52:opt_rescale_to_max_nxy(p_u_10, 0.88, 0.8, p52:get_scale())
            local v53, v54 = p52:opt_update_cframe_params(p_u_10, {
                ["PositionNXY"] = Vector2.new(0.5, 0.45),
                ["OffsetXYZ"] = p52:anchored_offset(0.5, 0.5),
                ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
            })
            if v53 == true then
                v_u_17:SetPrimaryPartCFrame(v54)
            end;
        end;
        local v_u_55 = 1
        local v_u_56 = 1
        v_u_16.set_alpha = function(_, p57) --[[ Name: set_alpha ]] --[[ Line: 224 ]]
            --[[ Upvalues: (ref 1): v_u_55, (ref 2): v_u_1, (ref 3): v_u_17 ]]
            if v_u_55 ~= p57 then
                v_u_55 = p57
                v_u_1:r_set_alpha(v_u_17, v_u_55)
            end;
        end;
        v_u_16.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 230 ]]
            --[[ Upvalues: (ref 1): v_u_55 ]]
            return v_u_55;
        end;
        v_u_16.set_scale = function(_, p58) --[[ Name: set_scale ]] --[[ Line: 231 ]]
            --[[ Upvalues: (ref 1): v_u_56 ]]
            v_u_56 = p58
        end;
        v_u_16.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 232 ]]
            --[[ Upvalues: (ref 1): v_u_56 ]]
            return v_u_56;
        end;
        v_u_16.get_native_size = function(p59) --[[ Name: get_native_size ]] --[[ Line: 234 ]]
            return p59._native_size;
        end;
        v_u_16.get_size = function(p60) --[[ Name: get_size ]] --[[ Line: 237 ]]
            return p60._size;
        end;
        v_u_16.set_size = function(p61, p62) --[[ Name: set_size ]] --[[ Line: 240 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            p61._size = p62
            v_u_17.PrimaryPart.Size = Vector3.new(p62.X, p62.Y, 0)
        end;
        v_u_16.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 244 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17.PrimaryPart.Position;
        end;
        v_u_16.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 245 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17.PrimaryPart.SurfaceGui;
        end;
        v_u_16.set_showing = function(_, p63) --[[ Name: set_showing ]] --[[ Line: 246 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_6 ]]
            if p63 then
                v_u_17.Parent = v_u_6:get_world_ui_folder()
            else
                v_u_17.Parent = nil
            end;
        end;
        f_cons()
        return v_u_16;
    end
};
