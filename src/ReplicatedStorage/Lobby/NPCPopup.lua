-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:35 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRect)
local v_u_5 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Local.SFXManager)
return {
    ["new"] = function(_, p_u_6) --[[ Name: new ]] --[[ Line: 13 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_2, (copy 4): v_u_1, (copy 5): v_u_5 ]]
        local v7 = {
            ["cons"] = function(_) end
        }
        local v_u_8 = nil
        local v_u_9 = nil
        local v_u_10 = nil
        local v_u_11 = nil
        local v_u_12 = 0
        local v_u_13 = nil
        local v_u_14 = nil
        local v_u_15 = nil
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = nil
        local v_u_19 = v_u_3:new(5)
        local v_u_20 = v_u_4:new(0, 0, 0, 0)
        local v_u_21 = nil
        local v_u_22 = 1
        local v_u_23 = 0
        local v_u_24 = true
        v7.create_popup_on_character = function(_, p25, p26) --[[ Name: create_popup_on_character ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_21, (ref 5): v_u_11, (ref 6): v_u_10, (ref 7): v_u_15, (ref 8): v_u_2, (ref 9): v_u_16, (ref 10): v_u_17 ]]
            v_u_18 = p26
            v_u_8 = p25:Clone()
            v_u_9 = v_u_8.Part
            v_u_8.Parent = v_u_18
            v_u_21 = v_u_8.Part.Size
            v_u_11 = v_u_8.Part.SurfaceGui
            v_u_10 = v_u_8.Part.SurfaceGui.Frame
            v_u_15 = v_u_2:first_child_of_type(v_u_18, "Humanoid")
            v_u_16 = v_u_15 and v_u_15.RootPart
            if v_u_16 then
                v_u_17 = v_u_16.Position
            end;
            v_u_11.Enabled = false
        end;
        local v_u_27 = Vector3.new(0, 6, 0)
        v7.set_position_offset = function(p28, p29) --[[ Name: set_position_offset ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            v_u_27 = p29
            return p28;
        end;
        local v_u_30 = 25
        v7.set_dist_max = function(p31, p32) --[[ Name: set_dist_max ]] --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            v_u_30 = p32
            return p31;
        end;
        v7.popup_update_visual = function(p33, p34) --[[ Name: popup_update_visual ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_17, (ref 3): v_u_2, (ref 4): v_u_27, (copy 5): p_u_6, (ref 6): v_u_30, (ref 7): v_u_24, (ref 8): v_u_9, (ref 9): v_u_23, (ref 10): v_u_13, (ref 11): v_u_21, (ref 12): v_u_22, (ref 13): v_u_14, (copy 14): v_u_19, (copy 15): v_u_20, (ref 16): v_u_1, (ref 17): v_u_12 ]]
            if v_u_16 ~= nil then
                v_u_17 = v_u_16.Position
                local v35 = v_u_2:get_camera_cframe()
                local v36 = v_u_17 + v_u_27
                local v37 = v36 - v35.p
                local v38 = v37:Dot(v35.lookVector)
                local l_magnitude_0 = v37.magnitude
                local l_magnitude_1 = (v36 - v_u_2:get_localplayer_cframe().p).magnitude
                local v39 = p_u_6._menus:get_top_element()
                local v40 = v39 == nil and true or v39:swallows_input()
                local v41 = p_u_6._lobby_join:get_lobby()
                local v42
                if v38 > 0 and (l_magnitude_1 < v_u_30 and (v40 == false and (v_u_24 == true and v41 ~= nil))) then
                    v42 = v41:transition_local_camera_cframe_finished()
                else
                    v42 = false
                end;
                local v43 = false
                if v42 == true and v_u_9 then
                    local v44 = v_u_2:lookat_camera_cframe(v36, p_u_6._spui) * CFrame.fromAxisAngle(Vector3.new(0, 0, 1), v_u_2:deg_to_rad(v_u_23))
                    local l_Size_0 = v_u_9.Size
                    local v45 = v44 + v44.upVector.unit * (l_Size_0.Y * 0.35)
                    local v46 = false
                    if v_u_13 == nil then
                        v46 = true
                        v_u_13 = v45
                    elseif v_u_2:cframe_delta(v_u_13, v45) > 0.001 then
                        v46 = true
                        v_u_13 = v45
                    end;
                    if v46 == true then
                        v_u_9.CFrame = v45
                    end;
                    local v47 = v_u_21 * v_u_22
                    if (v47 - l_Size_0).magnitude > 0.01 then
                        v_u_9.Size = v47
                    else
                        v47 = l_Size_0
                    end;
                    if v_u_14 == nil or v_u_2:cframe_delta(v35, v_u_14) > 0.001 then
                        v_u_14 = v35
                        v_u_19:set_focus_plane_from_position(v36)
                        v_u_19:layout()
                        local v48 = v_u_2:pos_to_nxy(v_u_9.Position)
                        local v49 = v_u_19:get_size_nxy_from_uiplane_xy(v47.X, v47.Y)
                        if v_u_2:is_finite(v48.X) and (v_u_2:is_finite(v48.Y) and (v_u_2:is_finite(v49.X) and v_u_2:is_finite(v49.Y))) then
                            v_u_20:set_centerxy_wid_hei(v48.X, v48.Y, v49.X, v49.Y)
                        else
                            v_u_20:set(0, 0, 0, 0)
                        end;
                    end;
                    if p_u_6._input:get_has_frame_focused_element() == false and v_u_20:contains_vec2((v_u_19:get_cursor_nxy())) then
                        p_u_6._input:set_has_frame_focused_element(true)
                        v43 = true
                    end;
                    p33:input_update(v43, p34)
                else
                    v_u_22 = 1
                    v_u_23 = 0
                    v_u_13 = nil
                end;
                p33:set_alpha((v_u_1:expt_sec(v_u_12, v42 == false and 0 or (v43 == true and 0.85 or (l_magnitude_0 < 5 and 0.25 or 0.75)), 0.5, p34)))
            end;
        end;
        local v_u_50 = 0
        v7.input_update = function(p51, p52, p53) --[[ Name: input_update ]] --[[ Line: 174 ]]
            --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_1, (copy 3): p_u_6, (ref 4): v_u_22, (ref 5): v_u_23, (ref 6): v_u_2, (ref 7): v_u_5 ]]
            v_u_50 = v_u_1:incr_wrap(v_u_50, v_u_1:SecondsToTick(1.25) * p53, 1)
            local v54 = false
            if p_u_6._lobby_join and p_u_6._lobby_join:get_lobby() then
                local v55 = p_u_6._lobby_join:get_lobby()
                v54 = v55:transition_local_camera_cframe_finished() and (v55._ui_manager and v55._ui_manager:swallow_control_input() ~= true) and true or v54
            end;
            if p52 == true and v54 == true then
                v_u_22 = v_u_1:expt_sec(v_u_22, 1.25, 0.25, p53)
                v_u_23 = v_u_1:expt_sec(v_u_23, math.sin(v_u_50 * 3.141592653589793 * 2) * 10, 0.3, p53)
                local v56
                if v_u_2:is_mobile() then
                    v56 = p_u_6._input:control_just_released(v_u_5.KEY_CLICK)
                    if v56 then
                        v56 = p_u_6._input:get_touch_move_count() < 10
                    end;
                else
                    v56 = p_u_6._input:control_just_pressed(v_u_5.KEY_CLICK)
                end;
                if v56 then
                    v_u_22 = 1.5
                    p51:trigger_action()
                    return;
                end;
            else
                v_u_22 = v_u_1:expt_sec(v_u_22, 1, 0.5, p53)
                v_u_23 = v_u_1:expt_sec(v_u_23, 0, 0.25, p53)
            end;
        end;
        v7.set_enabled = function(p57, p58) --[[ Name: set_enabled ]] --[[ Line: 207 ]]
            --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_22 ]]
            v_u_24 = p58
            if p58 ~= true then
                p57:set_alpha(0)
                v_u_22 = 1
            end;
        end;
        v7.set_alpha = function(p59, p60) --[[ Name: set_alpha ]] --[[ Line: 216 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_2, (ref 3): v_u_8 ]]
            if v_u_12 ~= p60 then
                v_u_12 = p60
                if v_u_12 <= 0 then
                    p59:set_gui_enabled(false)
                else
                    p59:set_gui_enabled(true)
                end;
                v_u_2:r_set_alpha(v_u_8, v_u_12)
            end;
        end;
        local v_u_61 = false
        v7.set_gui_enabled = function(_, p62) --[[ Name: set_gui_enabled ]] --[[ Line: 229 ]]
            --[[ Upvalues: (ref 1): v_u_61, (ref 2): v_u_11 ]]
            if p62 ~= v_u_61 then
                v_u_61 = p62
                v_u_11.Enabled = v_u_61
            end;
        end;
        local v_u_63 = nil
        v7.set_trigger_callback = function(_, p64) --[[ Name: set_trigger_callback ]] --[[ Line: 237 ]]
            --[[ Upvalues: (ref 1): v_u_63 ]]
            v_u_63 = p64
        end;
        v7.trigger_action = function(_) --[[ Name: trigger_action ]] --[[ Line: 241 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_63 ]]
            if v_u_18 ~= nil and v_u_18:IsDescendantOf(workspace) == true then
                if v_u_63 ~= nil then
                    v_u_63()
                end;
            end;
        end;
        v7.update = function(p65, p66) --[[ Name: update ]] --[[ Line: 246 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_18, (ref 3): v_u_15, (ref 4): v_u_16, (ref 5): v_u_17 ]]
            v_u_2:profilebegin("NPCPopup:update")
            v_u_15 = v_u_18 and v_u_15 == nil and v_u_2:first_child_of_type(v_u_18, "Humanoid")
            if v_u_15 then
                v_u_16 = v_u_15.RootPart
                v_u_17 = v_u_16.Position
            end;
            p65:popup_update_visual(p66)
            v_u_2:profileend()
        end;
        v7.do_remove = function(_) --[[ Name: do_remove ]] --[[ Line: 260 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_8, (ref 3): v_u_9, (ref 4): v_u_10, (ref 5): v_u_11, (ref 6): v_u_13, (ref 7): v_u_14, (ref 8): v_u_15, (ref 9): v_u_16, (ref 10): v_u_17, (ref 11): v_u_18 ]]
            v_u_2:ptry(function() --[[ Line: 261 ]]
                --[[ Upvalues: (ref 1): v_u_8 ]]
                v_u_8:Destroy()
            end)
            v_u_8 = nil
            v_u_9 = nil
            v_u_10 = nil
            v_u_11 = nil
            v_u_13 = nil
            v_u_14 = nil
            v_u_15 = nil
            v_u_16 = nil
            v_u_17 = nil
            v_u_18 = nil
        end;
        v7:cons()
        return v7;
    end
};
