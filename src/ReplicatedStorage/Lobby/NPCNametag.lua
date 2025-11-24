-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:35 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.MissionInfo)
return {
    ["new"] = function(_, p_u_4) --[[ Name: new ]] --[[ Line: 10 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_2 ]]
        local v5 = {}
        local v_u_6 = nil
        local v_u_7 = nil
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
        local v_u_18 = false
        local function _() end;
        v5.create_nametag_on_character = function(p19, p20, p21, p22) --[[ Name: create_nametag_on_character ]] --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_6, (ref 3): v_u_7, (ref 4): v_u_14, (ref 5): v_u_3, (ref 6): v_u_15, (ref 7): v_u_1, (ref 8): v_u_11, (ref 9): v_u_10, (ref 10): v_u_8, (ref 11): v_u_9, (ref 12): v_u_18 ]]
            v_u_17 = p20
            v_u_6 = game.ReplicatedStorage.LobbyElementProtos.CharacterOverlay.NPCNametag:Clone()
            v_u_7 = v_u_6.Part
            v_u_6.Parent = v_u_17
            v_u_14 = v_u_3:first_child_of_type(v_u_17, "Humanoid")
            if v_u_14 ~= nil then
                v_u_14.DisplayDistanceType = Enum.HumanoidDisplayDistanceType.None
                v_u_14.HealthDisplayType = Enum.HumanoidHealthDisplayType.AlwaysOff
            end;
            v_u_15 = v_u_14.RootPart
            if v_u_15 == nil then
                v_u_1:warnf("NPCNametag(%s) humanoid root is nil", v_u_14.Parent.Name)
            end;
            p19:update_humanoid_root_position()
            v_u_11 = v_u_6.Part.SurfaceGui
            local l_Frame_0 = v_u_6.Part.SurfaceGui.Frame
            v_u_10 = l_Frame_0
            v_u_8 = l_Frame_0.NameDisplay
            v_u_9 = l_Frame_0.DescriptionDisplay
            v_u_8.Text = p21
            v_u_9.Text = p22
            v_u_9.TextColor3 = v_u_8.TextColor3
            v_u_11.Enabled = false
            v_u_18 = false
        end;
        v5.update_humanoid_root_position = function(_) --[[ Name: update_humanoid_root_position ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16 ]]
            if v_u_15 then
                v_u_16 = v_u_15.Position
            end;
        end;
        v5.get_name_display = function(_) --[[ Name: get_name_display ]] --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): v_u_8 ]]
            return v_u_8;
        end;
        v5.get_description_display = function(_) --[[ Name: get_description_display ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9;
        end;
        local v_u_23 = Vector3.new(0, 1.5, 0)
        v5.set_position_offset = function(p24, p25) --[[ Name: set_position_offset ]] --[[ Line: 74 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23 = p25
            return p24;
        end;
        local v_u_26 = true
        v5.set_override_gui_enabled = function(_, p27) --[[ Name: set_override_gui_enabled ]] --[[ Line: 80 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            v_u_26 = p27
        end;
        local v_u_28 = nil
        v5.off_frame_index_check_root_part_position = function(_) --[[ Name: off_frame_index_check_root_part_position ]] --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_15, (ref 3): v_u_16, (ref 4): v_u_28 ]]
            local v29 = false
            if v_u_18 and v_u_15 then
                v_u_16 = v_u_15.Position
                v29 = v_u_16 ~= v_u_28 and true or v29
                v_u_28 = v_u_16
            end;
            return v29;
        end;
        local v_u_30 = 100
        v5.set_dist_max = function(p31, p32) --[[ Name: set_dist_max ]] --[[ Line: 99 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            v_u_30 = p32
            return p31;
        end;
        v5.nametag_update_visual = function(_, p33) --[[ Name: nametag_update_visual ]] --[[ Line: 104 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_16, (ref 3): v_u_23, (ref 4): v_u_30, (ref 5): v_u_26, (ref 6): v_u_18, (ref 7): v_u_11, (ref 8): v_u_2, (ref 9): v_u_12, (ref 10): v_u_8, (ref 11): v_u_9, (copy 12): p_u_4, (ref 13): v_u_13, (ref 14): v_u_7 ]]
            local v34 = v_u_3:get_camera_cframe()
            local v35 = v_u_16 + v_u_23
            local v36 = v35 - v34.p
            local v37 = v36:Dot(v34.lookVector)
            local l_magnitude_0 = v36.magnitude
            local v38 = v_u_30 >= l_magnitude_0 and (v37 >= 0 and v_u_26 ~= false)
            if v38 ~= v_u_18 then
                v_u_18 = v38
                v_u_11.Enabled = v_u_18
            end;
            local v39 = v_u_2:expt_sec(v_u_12, v_u_30 < l_magnitude_0 and 0 or (l_magnitude_0 < 5 and 0.25 or 1), 1, p33)
            if v_u_12 ~= v39 then
                v_u_12 = v39
                local v40 = v_u_3:tra(v_u_12)
                v_u_8.TextTransparency = v40
                v_u_8.TextStrokeTransparency = v40
                v_u_9.TextTransparency = v40
                v_u_9.TextStrokeTransparency = v40
            end;
            if v37 > 0 and l_magnitude_0 < v_u_30 then
                local v41 = v_u_3:lookat_camera_cframe(v35, p_u_4._spui)
                local v42 = false
                if v_u_13 == nil then
                    v42 = true
                    v_u_13 = v41
                elseif v_u_3:cframe_delta(v_u_13, v41) > 0.001 then
                    v42 = true
                    v_u_13 = v41
                end;
                if v42 == true and v_u_7 then
                    v_u_7.CFrame = v41
                end;
            end;
        end;
        v5.get_display = function(_) --[[ Name: get_display ]] --[[ Line: 159 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_9 ]]
            return v_u_8, v_u_9;
        end;
        v5.update = function(p43, p44) --[[ Name: update ]] --[[ Line: 161 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            v_u_3:profilebegin("NPCNametag:update")
            p43:nametag_update_visual(p44)
            v_u_3:profileend()
        end;
        v5.do_remove = function(_) --[[ Name: do_remove ]] --[[ Line: 167 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_6, (ref 3): v_u_7, (ref 4): v_u_8, (ref 5): v_u_9, (ref 6): v_u_10, (ref 7): v_u_11, (ref 8): v_u_13, (ref 9): v_u_14, (ref 10): v_u_15, (ref 11): v_u_16, (ref 12): v_u_17 ]]
            v_u_3:ptry(function() --[[ Line: 168 ]]
                --[[ Upvalues: (ref 1): v_u_6 ]]
                v_u_6:Destroy()
            end)
            v_u_6 = nil
            v_u_7 = nil
            v_u_8 = nil
            v_u_9 = nil
            v_u_10 = nil
            v_u_11 = nil
            v_u_13 = nil
            v_u_14 = nil
            v_u_15 = nil
            v_u_16 = nil
            v_u_17 = nil
        end;
        return v5;
    end
};
