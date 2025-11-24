-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:30 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_7 = require(game.ReplicatedStorage.Menu.SPUIDisplay)
local v_u_8 = require(game.ReplicatedStorage.Menu.SPUIButton)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_9 = require(game.ReplicatedStorage.Local.GameLocalMode)
local v_u_10 = require(game.ReplicatedStorage.Shared.Constants)
return {
    ["new"] = function(_, p_u_11, p_u_12, p13) --[[ Name: new ]] --[[ Line: 19 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_6, (copy 4): v_u_8, (copy 5): v_u_7, (copy 6): v_u_10, (copy 7): v_u_5, (copy 8): v_u_4, (copy 9): v_u_9, (copy 10): v_u_2 ]]
        local v14 = v_u_3:new(p_u_12, p13)
        local v_u_15 = nil
        local v_u_16 = 1
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = nil
        local v_u_27 = 1
        v14.cons = function(p28) --[[ Name: cons ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_1, (ref 3): v_u_6, (ref 4): v_u_19, (copy 5): p_u_11, (ref 6): v_u_8, (copy 7): p_u_12, (ref 8): v_u_20, (ref 9): v_u_27, (ref 10): v_u_21, (ref 11): v_u_22, (ref 12): v_u_23, (ref 13): v_u_24, (ref 14): v_u_7, (ref 15): v_u_25, (ref 16): v_u_26, (ref 17): v_u_10, (ref 18): v_u_17, (ref 19): v_u_18 ]]
            v_u_15 = game.ReplicatedStorage.WorldUIProto.SpectateUI:Clone()
            v_u_15.Name = v_u_1:gen_name(v_u_15.Name)
            v_u_15.Parent = v_u_6:get_world_ui_folder()
            v_u_19 = p28:add_cycle_element(p_u_11, 1, v_u_8:new(v_u_15.BackButtonSurface, p_u_12, function() --[[ Line: 47 ]]
                --[[ Upvalues: (ref 1): p_u_11 ]]
                if p_u_11:get_spectate_manager() then
                    p_u_11:get_spectate_manager():spectate_leave()
                end;
            end):set_anchor_rnxy(0.5, 0.5):set_position_nxy(0.925, 0.1):set_max_nxy(0.2, 0.15))
            v_u_20 = p28:add_cycle_element(p_u_11, 1, v_u_8:new(v_u_15.CheerButtonSurface, p_u_12, function() --[[ Line: 56 ]]
                --[[ Upvalues: (ref 1): p_u_11, (ref 2): v_u_27 ]]
                p_u_11:get_spectate_manager():cheer_focused_slot(function(p29) --[[ Line: 57 ]]
                    --[[ Upvalues: (ref 1): v_u_27 ]]
                    if p29 then
                        v_u_27 = 0
                    end;
                end)
            end):set_anchor_rnxy(0.5, 0.5):set_position_nxy(0.75, 0.11499999999999999):set_max_nxy(0.1, 0.1))
            v_u_21 = v_u_1:get_list_of_children_of_classname(v_u_15.CheerButtonSurface, "ImageLabel")
            v_u_22 = v_u_1:get_list_of_children_of_classname(v_u_15.CheerButtonSurface, "TextLabel")
            v_u_23 = v_u_15.CheerButtonSurface.PrimaryPart.SurfaceGui.Frame.TextDisplay
            v_u_24 = v_u_7:new(v_u_15.CheerCoinRewardSurface, p_u_12, true):set_anchor_rnxy(0.5, 0.5):set_position_nxy(0.75, 0.11499999999999999)
            v_u_25 = v_u_1:get_list_of_children_of_classname(v_u_15.CheerCoinRewardSurface, "ImageLabel")
            v_u_26 = v_u_1:get_list_of_children_of_classname(v_u_15.CheerCoinRewardSurface, "TextLabel")
            v_u_15.CheerCoinRewardSurface.PrimaryPart.SurfaceGui.Frame.TextDisplay.Text = string.format("+%d", v_u_10.SPECTATE_CHEER_COIN_AMOUNT)
            p28:update_coin_reward_anim()
            v_u_17 = v_u_7:new(v_u_15.StatusTextSurface, p_u_12):set_position_nxy(0, 0):set_anchor_rnxy(0, 0)
            v_u_18 = v_u_15.StatusTextSurface.PrimaryPart.SurfaceGui.Frame.TextLabel
            v_u_18.Text = ""
            p28._native_size = v_u_15.PrimaryPart.Size
            p28._size = p28._native_size
            p28:layout()
        end;
        v14.set_status_text = function(_, p30) --[[ Name: set_status_text ]] --[[ Line: 92 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_18 ]]
            if v_u_5.SpectateUIDebugText == true then
                v_u_18.Text = p30
            else
                v_u_18.Text = ""
            end;
        end;
        local v_u_31 = -1
        local function f_set_cheer_button_enabled_visual(p32) --[[ Name: set_cheer_button_enabled_visual ]] --[[ Line: 101 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_1, (ref 3): v_u_21, (ref 4): v_u_22, (ref 5): v_u_23, (ref 6): v_u_15 ]]
            if p32 ~= v_u_31 then
                v_u_31 = p32
                if v_u_31 then
                    v_u_1:list_set_alpha_name(v_u_21, {
                        ["ImageAlpha"] = 1
                    })
                    v_u_1:list_set_alpha_name(v_u_22, {
                        ["TextAlpha"] = 1
                    })
                    v_u_23.Text = "Cheer"
                else
                    v_u_1:list_set_alpha_name(v_u_21, {
                        ["ImageAlpha"] = 0.25
                    })
                    v_u_1:list_set_alpha_name(v_u_22, {
                        ["TextAlpha"] = 0.75
                    })
                end;
                v_u_1:r_set_alpha(v_u_15.CheerButtonSurface, 1)
            end;
        end;
        local v_u_33 = -1
        v14.update_coin_reward_anim = function(_) --[[ Name: update_coin_reward_anim ]] --[[ Line: 117 ]]
            --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_27, (ref 3): v_u_4, (ref 4): v_u_1, (ref 5): v_u_25, (ref 6): v_u_26, (ref 7): v_u_15, (ref 8): v_u_24 ]]
            if v_u_33 ~= v_u_27 then
                v_u_33 = v_u_27
                local v34 = v_u_4:BezierYForT(0, 0, 0, 1.5, 1, 1, 1, 0, v_u_27)
                v_u_1:list_set_alpha_name(v_u_25, {
                    ["ImageAlpha"] = v34
                })
                v_u_1:list_set_alpha_name(v_u_26, {
                    ["TextAlpha"] = v34
                })
                v_u_1:r_set_alpha(v_u_15.CheerCoinRewardSurface, 1)
                local v35 = v_u_4:BezierYForT(0, 1.25, 0, 1, 1, 1, 1, 0, v_u_27)
                v_u_24:set_scale(v35, v35)
            end;
        end;
        v14.behaviour_update = function(p36, p37, p38) --[[ Name: behaviour_update ]] --[[ Line: 143 ]]
            --[[ Upvalues: (copy 1): p_u_11, (ref 2): v_u_9, (ref 3): v_u_20, (copy 4): f_set_cheer_button_enabled_visual, (ref 5): v_u_23, (ref 6): v_u_1, (ref 7): v_u_27, (ref 8): v_u_4 ]]
            p36:behaviour_update_base(p37, p38)
            if p_u_11:get_current_mode() == v_u_9.Spectate then
                v_u_20:set_visible(true)
                local v39, v40 = p_u_11:get_spectate_manager():can_cheer()
                if v39 then
                    v_u_20:set_selectable(true)
                    f_set_cheer_button_enabled_visual(true)
                else
                    v_u_20:set_selectable(false)
                    f_set_cheer_button_enabled_visual(false)
                    v_u_23.Text = v_u_1:format_ms_time(v40)
                end;
            else
                v_u_20:set_visible(false)
            end;
            v_u_27 = v_u_4:IncrementClamp(v_u_27, v_u_4:SecondsToTick(1.1) * p37, 0, 1)
            p36:update_coin_reward_anim()
        end;
        v14.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 198 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            v_u_15:Destroy()
        end;
        local v_u_41 = v_u_2:cframe_params_default()
        v_u_41.PositionNXY:set(0.5, 0.5)
        v14.layout = function(p42) --[[ Name: layout ]] --[[ Line: 204 ]]
            --[[ Upvalues: (copy 1): v_u_41, (ref 2): v_u_15, (copy 3): p_u_12, (ref 4): v_u_17, (ref 5): v_u_1, (ref 6): v_u_24 ]]
            v_u_41.OffsetXYZ:from_vector3(p42:anchored_offset(0.5, 0.5))
            v_u_15:SetPrimaryPartCFrame(p_u_12:get_cframe(v_u_41))
            p_u_12:uiobj_rescale_to_max_nxy(v_u_17, 0.25, 0.35, 1)
            v_u_17:set_position_nxy(120 / v_u_1:screen_size().X, 0)
            v_u_17:layout()
            v_u_24:layout()
        end;
        local v_u_43 = -1
        v14.set_alpha = function(_, p44) --[[ Name: set_alpha ]] --[[ Line: 216 ]]
            --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_1, (ref 3): v_u_15 ]]
            if v_u_43 ~= p44 then
                v_u_43 = p44
                v_u_1:r_set_alpha(v_u_15, v_u_43)
            end;
        end;
        v14.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 221 ]]
            --[[ Upvalues: (ref 1): v_u_43 ]]
            return v_u_43;
        end;
        v14.set_scale = function(_, p45) --[[ Name: set_scale ]] --[[ Line: 222 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            v_u_16 = p45
        end;
        v14.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 223 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            return v_u_16;
        end;
        v14.get_native_size = function(p46) --[[ Name: get_native_size ]] --[[ Line: 225 ]]
            return p46._native_size;
        end;
        v14.get_size = function(p47) --[[ Name: get_size ]] --[[ Line: 228 ]]
            return p47._size;
        end;
        v14.set_size = function(p48, p49) --[[ Name: set_size ]] --[[ Line: 231 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            p48._size = p49
            v_u_15.PrimaryPart.Size = Vector3.new(p49.X, p49.Y, 0)
        end;
        v14.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 235 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15.PrimaryPart.Position;
        end;
        v14.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 238 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15.PrimaryPart.SurfaceGui;
        end;
        v14:cons()
        return v14;
    end
};
