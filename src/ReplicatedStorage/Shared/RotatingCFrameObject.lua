-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:11 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
return {
    ["new"] = function(_, p_u_3, p4, p5) --[[ Name: new ]] --[[ Line: 8 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        local v6 = {}
        local v_u_7 = false
        local v8 = p4 == nil and function() --[[ Line: 14 ]]
            --[[ Upvalues: (copy 1): p_u_3 ]]
            return p_u_3.CFrame;
        end or p4
        local v_u_10 = p5 == nil and function(p9) --[[ Line: 17 ]]
            --[[ Upvalues: (copy 1): p_u_3 ]]
            p_u_3.CFrame = p9
        end or p5
        local v_u_11 = v8()
        local v_u_12, v_u_13, v_u_14 = v_u_11:ToEulerAnglesXYZ()
        v6.set_initial_cframe = function(p15, p16) --[[ Name: set_initial_cframe ]] --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_12, (ref 3): v_u_13, (ref 4): v_u_14 ]]
            v_u_11 = p16
            local v17, v18, v19 = v_u_11:ToEulerAnglesXYZ()
            v_u_12 = v17
            v_u_13 = v18
            v_u_14 = v19
            return p15;
        end;
        v6.set_initial_cframe_position = function(p20, p21) --[[ Name: set_initial_cframe_position ]] --[[ Line: 28 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_12, (ref 3): v_u_13, (ref 4): v_u_14 ]]
            v_u_11 = CFrame.new(p21) * CFrame.Angles(v_u_12, v_u_13, v_u_14)
            return p20;
        end;
        local v_u_22 = 0
        local v_u_23 = 0
        v6.set_angle = function(p24, p25) --[[ Name: set_angle ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_22 ]]
            v_u_22 = p25
            return p24;
        end;
        local v_u_26 = 0.3
        v6.set_rotate_time_sec = function(p27, p28) --[[ Name: set_rotate_time_sec ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            v_u_26 = p28
            return p27;
        end;
        local v_u_29 = Vector3.new(0, 1, 0)
        v6.set_rotation_axis = function(p30, p31) --[[ Name: set_rotation_axis ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            v_u_29 = p31
            return p30;
        end;
        local v_u_32 = 1
        local v_u_33 = 0
        local v_u_34 = true
        v6.set_frame_update_rate = function(p35, p36) --[[ Name: set_frame_update_rate ]] --[[ Line: 46 ]]
            --[[ Upvalues: (ref 1): v_u_32 ]]
            v_u_32 = p36
            return p35;
        end;
        v6.update = function(_, p37) --[[ Name: update ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_32, (ref 3): v_u_34, (ref 4): v_u_22, (ref 5): v_u_1, (ref 6): v_u_26, (ref 7): v_u_23 ]]
            if v_u_32 < v_u_33 then
                v_u_33 = v_u_33 - v_u_32
                v_u_34 = true
                v_u_22 = (v_u_22 + v_u_1:sec_to_tick(v_u_26) * 6.283185307179586 * v_u_32) % 6.283185307179586
                v_u_23 = v_u_22 / 6.283185307179586
            end;
            v_u_33 = v_u_33 + p37
        end;
        v6.update_obj_cframe = function(p38, p39) --[[ Name: update_obj_cframe ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_2, (ref 3): v_u_22, (ref 4): v_u_34, (ref 5): v_u_12, (ref 6): v_u_13, (ref 7): v_u_14, (ref 8): v_u_10, (ref 9): v_u_11, (ref 10): v_u_29, (ref 11): v_u_23 ]]
            p38:update(p39)
            if v_u_7 then
                v_u_2:puts("update_obj_cframe angle(%.2f) has_updated_cframe(%s) _initial(%.2f,%.2f,%.2f)", v_u_22, tostring(v_u_34), v_u_12, v_u_13, v_u_14)
            end;
            if v_u_34 then
                v_u_34 = false
                local v40 = p38:get_cframe()
                v_u_10(v40, v_u_11, v_u_12, v_u_13, v_u_14, v_u_22, v_u_29, p39, v_u_23)
                if v_u_7 then
                    local v41, v42, v43 = v40:ToEulerAnglesXYZ()
                    v_u_2:puts("\tout CF_XYZ(%.2f,%.2f,%.2f)", v41, v42, v43)
                end;
            end;
        end;
        v6.get_cframe = function(_) --[[ Name: get_cframe ]] --[[ Line: 77 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_12, (ref 3): v_u_22, (ref 4): v_u_29, (ref 5): v_u_13, (ref 6): v_u_14 ]]
            return CFrame.new(v_u_11.p) * CFrame.Angles(v_u_12 + v_u_22 * v_u_29.X, v_u_13 + v_u_22 * v_u_29.Y, v_u_14 + v_u_22 * v_u_29.Z);
        end;
        v6.set_debug = function(_) --[[ Name: set_debug ]] --[[ Line: 87 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_2, (ref 3): v_u_22, (ref 4): v_u_26, (ref 5): v_u_12, (ref 6): v_u_13, (ref 7): v_u_14 ]]
            v_u_7 = true
            v_u_2:puts("set_debug _angle(%.2f) _rotate_time_sec(%.2f) _initial(%.2f,%.2f,%.2f)", v_u_22, v_u_26, v_u_12, v_u_13, v_u_14)
        end;
        return v6;
    end
};
