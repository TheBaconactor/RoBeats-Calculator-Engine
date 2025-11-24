-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:04 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPRect)
local v_u_6 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Local.SFXManager)
return {
    ["new"] = function(_, p_u_7, p_u_8, p_u_9) --[[ Name: new ]] --[[ Line: 16 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_5, (copy 3): v_u_1, (copy 4): v_u_3, (copy 5): v_u_2, (copy 6): v_u_6 ]]
        local v_u_10 = {}
        local v_u_11 = v_u_4:new(5)
        local v_u_12 = v_u_5:new(0, 0, 0, 0)
        local v_u_13 = v_u_1:new()
        local v_u_14 = v_u_1:new()
        local function _() --[[ Name: cons ]] --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_3, (copy 3): p_u_8, (ref 4): v_u_14, (copy 5): v_u_10 ]]
            v_u_13 = v_u_3:get_list_of_children_of_classname(p_u_8:get_child_part(), "TextLabel")
            v_u_14 = v_u_3:get_list_of_children_of_classname(p_u_8:get_child_part(), "ImageLabel")
            return v_u_10;
        end;
        local v_u_15 = 0
        local v_u_16 = 0
        v_u_10.update = function(p17, p18) --[[ Name: update ]] --[[ Line: 32 ]]
            --[[ Upvalues: (copy 1): p_u_8, (copy 2): p_u_7, (copy 3): v_u_11, (ref 4): v_u_3, (copy 5): v_u_12, (ref 6): v_u_15, (ref 7): v_u_2, (ref 8): v_u_16, (ref 9): v_u_6, (copy 10): p_u_9 ]]
            p_u_8:layout()
            local v19 = false
            if p_u_7._lobby_join and p_u_7._lobby_join:get_lobby() then
                local v20 = p_u_7._lobby_join:get_lobby()
                v19 = v20:transition_local_camera_cframe_finished() and (v20._ui_manager and v20._ui_manager:swallow_control_input() ~= true) and true or v19
            end;
            if v19 == true then
                local v21 = p_u_8:get_child_part()
                if v21 ~= nil then
                    local l_Position_0 = v21.Position
                    local l_Size_0 = v21.Size
                    v_u_11:set_focus_plane_from_position(l_Position_0)
                    v_u_11:layout()
                    local v22 = v_u_3:pos_to_nxy(l_Position_0)
                    local v23 = v_u_11:get_size_nxy_from_uiplane_xy(l_Size_0.X, l_Size_0.Y)
                    if v_u_3:is_finite(v22.X) and (v_u_3:is_finite(v22.Y) and (v_u_3:is_finite(v23.X) and v_u_3:is_finite(v23.Y))) then
                        v_u_12:set_centerxy_wid_hei(v22.X, v22.Y, v23.X, v23.Y)
                    else
                        v_u_12:set(0, 0, 0, 0)
                    end;
                    local v24
                    if p17:get_enabled() == true and (p17:get_enabled() == true and (p_u_7._input:get_has_frame_focused_element() == false and v_u_12:contains_vec2((v_u_11:get_cursor_nxy())))) then
                        p_u_7._input:set_has_frame_focused_element(true)
                        v24 = true
                    else
                        v24 = false
                    end;
                    if v24 then
                        v_u_15 = v_u_2:incr_wrap(v_u_15, v_u_2:SecondsToTick(1.25) * p18, 1)
                        p_u_8:set_scale(v_u_2:expt_sec(p_u_8:get_scale(), 1.25, 0.5, p18))
                        v_u_16 = v_u_2:expt_sec(v_u_16, math.sin(v_u_15 * 3.141592653589793 * 2) * 10, 0.3, p18)
                        local v25
                        if v_u_3:is_mobile() then
                            v25 = p_u_7._input:control_just_released(v_u_6.KEY_CLICK)
                            if v25 then
                                v25 = p_u_7._input:get_touch_move_count() < 10
                            end;
                        else
                            v25 = p_u_7._input:control_just_pressed(v_u_6.KEY_CLICK)
                        end;
                        if v25 then
                            p_u_8:set_scale(1.5)
                            v_u_3:ptry(function() --[[ Line: 87 ]]
                                --[[ Upvalues: (ref 1): p_u_9 ]]
                                if p_u_9 ~= nil then
                                    p_u_9()
                                end;
                            end)
                        end;
                    else
                        v_u_15 = 0
                        p_u_8:set_scale(v_u_2:expt_sec(p_u_8:get_scale(), 1, 0.5, p18))
                        v_u_16 = v_u_2:expt_sec(v_u_16, 0, 0.25, p18)
                    end;
                    if math.abs(v_u_16) > 0 then
                        v21.CFrame = v21.CFrame * CFrame.fromAxisAngle(Vector3.new(0, 0, 1), v_u_3:deg_to_rad(v_u_16))
                    end;
                end;
            else
                return;
            end;
        end;
        local v_u_26 = nil
        local v_u_27 = true
        v_u_10.set_fn_set_visible = function(p28, p29) --[[ Name: set_fn_set_visible ]] --[[ Line: 108 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            v_u_26 = p29
            return p28;
        end;
        v_u_10.get_visible = function(_) --[[ Name: get_visible ]] --[[ Line: 109 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27;
        end;
        v_u_10.set_visible = function(p30, p31) --[[ Name: set_visible ]] --[[ Line: 110 ]]
            --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_26 ]]
            v_u_27 = p31
            if v_u_26 then
                v_u_26(p31)
            end;
            return p30;
        end;
        local v_u_32 = true
        v_u_10.get_enabled = function(_) --[[ Name: get_enabled ]] --[[ Line: 117 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            return v_u_32;
        end;
        v_u_10.set_enabled = function(p33, p34) --[[ Name: set_enabled ]] --[[ Line: 118 ]]
            --[[ Upvalues: (ref 1): v_u_32, (ref 2): v_u_13, (ref 3): v_u_3, (ref 4): v_u_14 ]]
            if v_u_32 ~= p34 then
                v_u_32 = p34
                local v35 = v_u_32 and 1 or 0.25
                for _, v36 in v_u_13:key_itr() do
                    v_u_3:obj_apply_suffix_alpha_attribute(v36, "SPUIChildUniqueSystemButton_Enabled", v35)
                end;
                for _, v37 in v_u_14:key_itr() do
                    v_u_3:obj_apply_suffix_alpha_attribute(v37, "SPUIChildUniqueSystemButton_Enabled", v35)
                end;
                return p33;
            end;
        end;
        v_u_13 = v_u_3:get_list_of_children_of_classname(p_u_8:get_child_part(), "TextLabel")
        v_u_14 = v_u_3:get_list_of_children_of_classname(p_u_8:get_child_part(), "ImageLabel")
        return v_u_10;
    end
};
