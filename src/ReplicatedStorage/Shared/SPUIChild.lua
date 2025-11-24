-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:03 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_4 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
return {
    ["new"] = function(_, p_u_6, p_u_7, p_u_8) --[[ Name: new ]] --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2, (copy 3): v_u_5, (copy 4): v_u_3, (copy 5): v_u_1 ]]
        v_u_4:is_non_nil(p_u_6)
        v_u_4:is_non_nil(p_u_7)
        v_u_4:is_non_nil(p_u_8)
        local v9 = v_u_2:SPUIObjectBase()
        v9.get_parent_ui_obj = function(_) --[[ Name: get_parent_ui_obj ]] --[[ Line: 22 ]]
            --[[ Upvalues: (copy 1): p_u_6 ]]
            return p_u_6;
        end;
        v9.get_parent_part = function(_) --[[ Name: get_parent_part ]] --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): p_u_7 ]]
            return p_u_7;
        end;
        v9.get_child_part = function(_) --[[ Name: get_child_part ]] --[[ Line: 24 ]]
            --[[ Upvalues: (copy 1): p_u_8 ]]
            return p_u_8;
        end;
        local v_u_10 = p_u_6:get_alloc_child_id()
        v9.get_child_id = function(_) --[[ Name: get_child_id ]] --[[ Line: 27 ]]
            --[[ Upvalues: (copy 1): v_u_10 ]]
            return v_u_10;
        end;
        local v_u_11 = 1
        local v_u_12 = 0
        v9.get_alloc_child_id = function(_) --[[ Name: get_alloc_child_id ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_11, (copy 3): v_u_10, (ref 4): v_u_12 ]]
            if v_u_5.DoZOffsetChildren ~= true then
                return 0;
            end;
            local v13 = v_u_11
            v_u_11 = v_u_11 + 1
            return v13 + v_u_10 + v_u_12;
        end;
        local v14 = p_u_8:FindFirstChild("SurfaceGui")
        if v14 then
            v_u_12 = v14.ZOffset
            v14.ZOffset = v_u_12 + v_u_10
        end;
        local v_u_15 = 1
        local v_u_16 = 1
        local v_u_17 = Vector3.new(0, 0, 0)
        local v_u_18 = Vector3.new(0, 0, 0)
        local v_u_19 = nil
        v9.cons = function(p20) --[[ Name: cons ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_19, (copy 2): p_u_8 ]]
            v_u_19 = p_u_8.Size
            p20:update_basis_offset()
        end;
        v9.set_parent_part = function(p21, p22) --[[ Name: set_parent_part ]] --[[ Line: 63 ]]
            --[[ Upvalues: (ref 1): p_u_7 ]]
            p_u_7 = p22
            p21:update_basis_offset()
            return p21;
        end;
        v9.get_native_size = function(_) --[[ Name: get_native_size ]] --[[ Line: 69 ]]
            --[[ Upvalues: (ref 1): v_u_19 ]]
            return v_u_19;
        end;
        v9.get_size = function(_) --[[ Name: get_size ]] --[[ Line: 70 ]]
            --[[ Upvalues: (copy 1): p_u_8 ]]
            return p_u_8.Size;
        end;
        v9.set_size = function(_, _) --[[ Name: set_size ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            v_u_3:errf("SPUIChild Cannot set size")
        end;
        v9.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 72 ]]
            --[[ Upvalues: (copy 1): p_u_8 ]]
            return p_u_8.Position;
        end;
        local v_u_23 = nil
        v9.set_sgui = function(p24, p25) --[[ Name: set_sgui ]] --[[ Line: 75 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23 = p25
            return p24;
        end;
        v9.set_default_sgui = function(p26) --[[ Name: set_default_sgui ]] --[[ Line: 79 ]]
            --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_23, (ref 3): v_u_1 ]]
            if p_u_8 then
                v_u_23 = v_u_1:first_child_of_type(p_u_8, "SurfaceGui")
            end;
            return p26;
        end;
        v9.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            return v_u_23;
        end;
        v9.set_visible = function(_, p27) --[[ Name: set_visible ]] --[[ Line: 87 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            if v_u_23 then
                v_u_23.Enabled = p27
            end;
        end;
        v9.update_basis_offset = function(p28) --[[ Name: update_basis_offset ]] --[[ Line: 93 ]]
            --[[ Upvalues: (ref 1): p_u_7, (ref 2): v_u_2, (copy 3): p_u_8, (ref 4): v_u_18 ]]
            if p_u_7 ~= nil then
                local v29, v30 = v_u_2:part_get_front_xy_basis(p_u_7)
                local v31 = p_u_8.Position - p_u_7.Position
                v_u_18 = Vector3.new(v31:Dot(v29), v31:Dot(v30), 0)
                p28:layout()
            end;
        end;
        v9.set_position = function(p32, p33) --[[ Name: set_position ]] --[[ Line: 109 ]]
            --[[ Upvalues: (copy 1): p_u_8 ]]
            p_u_8.Position = p33
            p32:update_basis_offset()
        end;
        v9.update_basis_offset_scaled = function(p34) --[[ Name: update_basis_offset_scaled ]] --[[ Line: 115 ]]
            --[[ Upvalues: (ref 1): p_u_7, (ref 2): v_u_2, (copy 3): p_u_8, (ref 4): v_u_18 ]]
            if p_u_7 ~= nil then
                local v35 = p34:get_parent_scale()
                local v36, v37 = v_u_2:part_get_front_xy_basis(p_u_7)
                local v38 = p_u_8.Position - p_u_7.Position
                v_u_18 = Vector3.new(v38:Dot(v36) / v35.X, v38:Dot(v37) / v35.Y, 0)
                p34:layout()
            end;
        end;
        v9.set_position_scaled_offset = function(p39, p40, p41) --[[ Name: set_position_scaled_offset ]] --[[ Line: 130 ]]
            --[[ Upvalues: (copy 1): p_u_8 ]]
            p_u_8.Position = p40
            p39:update_basis_offset_scaled()
            local v42 = p39:get_child_relative_xy()
            p39:set_child_relative_xy(v42.X + p41.X, v42.Y + p41.Y)
            p39:layout()
        end;
        v9.get_position = function(_) --[[ Name: get_position ]] --[[ Line: 138 ]]
            --[[ Upvalues: (copy 1): p_u_8 ]]
            return p_u_8.Position;
        end;
        v9.set_scale = function(p43, p44) --[[ Name: set_scale ]] --[[ Line: 142 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16 ]]
            v_u_15 = p44
            v_u_16 = p44
            return p43;
        end;
        v9.set_scale_x = function(_, p45) --[[ Name: set_scale_x ]] --[[ Line: 147 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            v_u_15 = p45
        end;
        v9.set_scale_y = function(_, p46) --[[ Name: set_scale_y ]] --[[ Line: 148 ]]
            --[[ Upvalues: (ref 1): v_u_16 ]]
            v_u_16 = p46
        end;
        v9.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 150 ]]
            --[[ Upvalues: (ref 1): v_u_15 ]]
            return v_u_15;
        end;
        v9.get_rotation = function(_) --[[ Name: get_rotation ]] --[[ Line: 154 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            return v_u_17;
        end;
        v9.set_rotation_x = function(_, p47) --[[ Name: set_rotation_x ]] --[[ Line: 157 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17 = Vector3.new(p47, v_u_17.Y, v_u_17.Z)
        end;
        v9.set_rotation_z = function(_, p48) --[[ Name: set_rotation_z ]] --[[ Line: 160 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17 = Vector3.new(v_u_17.X, v_u_17.Y, p48)
        end;
        v9.set_rotation = function(_, p49) --[[ Name: set_rotation ]] --[[ Line: 163 ]]
            --[[ Upvalues: (ref 1): v_u_17 ]]
            v_u_17 = Vector3.new(p49, 0, 0)
        end;
        v9.set_child_relative_xy = function(p50, p51, p52) --[[ Name: set_child_relative_xy ]] --[[ Line: 167 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            v_u_18 = Vector3.new(p51, p52, 0)
            return p50;
        end;
        v9.get_child_relative_xy = function(_) --[[ Name: get_child_relative_xy ]] --[[ Line: 175 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            return v_u_18;
        end;
        local v_u_53 = Vector3.new()
        v9.get_parent_scale = function(_) --[[ Name: get_parent_scale ]] --[[ Line: 180 ]]
            --[[ Upvalues: (copy 1): p_u_6, (ref 2): v_u_53 ]]
            local v54 = p_u_6:get_native_size()
            if v54 == nil then
                v54 = Vector2.new()
            end;
            local v55 = p_u_6:get_size()
            if v55 == nil then
                v55 = v54
            end;
            v_u_53 = Vector3.new(v55.X / v54.X, v55.Y / v54.Y, 0)
            return v_u_53;
        end;
        local v_u_56 = false
        local v_u_57 = Vector3.new()
        local v_u_58 = CFrame.new()
        v9.layout = function(p59) --[[ Name: layout ]] --[[ Line: 202 ]]
            --[[ Upvalues: (ref 1): p_u_7, (ref 2): v_u_1, (ref 3): v_u_19, (ref 4): v_u_15, (ref 5): v_u_16, (ref 6): v_u_57, (copy 7): p_u_8, (ref 8): v_u_2, (ref 9): v_u_18, (ref 10): v_u_17, (ref 11): v_u_58 ]]
            if p_u_7 ~= nil then
                v_u_1:profilebegin("SPUIChild:layout(CFrame)")
                local v60 = p59:get_parent_scale()
                local v61 = Vector3.new(v_u_19.X * v60.X * v_u_15, v_u_19.Y * v60.Y * v_u_16, 0)
                if v_u_57 ~= v61 then
                    v_u_57 = v61
                    p_u_8.Size = v_u_57
                end;
                local v62, v63 = v_u_2:part_get_front_xy_basis(p_u_7)
                local v64 = CFrame.new(p_u_7.Position + v62 * v_u_18.X * v60.X + v63 * v_u_18.Y * v60.Y) * v_u_1:angles_vec3(p_u_7.Rotation) * v_u_1:angles_vec3(v_u_17)
                v_u_58 = v64
                p_u_8.CFrame = v64
                v_u_1:profileend()
                return p59;
            end;
        end;
        v9.set_debug = function(p65) --[[ Name: set_debug ]] --[[ Line: 247 ]]
            --[[ Upvalues: (ref 1): v_u_56 ]]
            v_u_56 = true
            return p65;
        end;
        v9:cons()
        return v9;
    end
};
