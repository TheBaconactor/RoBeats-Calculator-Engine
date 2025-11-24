-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:04 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_2 = nil
v1:require_shared(function() --[[ Line: 4 ]]
    --[[ Upvalues: (ref 1): v_u_2 ]]
    v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
end)
return {
    ["new"] = function(_, p_u_3) --[[ Name: new ]] --[[ Line: 10 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        local v12 = {
            ["_obj"] = p_u_3,
            ["_x"] = p_u_3.Position.X.Offset,
            ["_y"] = p_u_3.Position.Y.Offset,
            ["_sizex"] = p_u_3.Size.X.Offset,
            ["_sizey"] = p_u_3.Size.Y.Offset,
            ["_rotation_rad"] = v_u_2:deg_to_rad(p_u_3.Rotation),
            ["_visible"] = true,
            ["get_pos"] = function(p4) --[[ Name: get_pos ]] --[[ Line: 20 ]]
                return Vector2.new(p4._x, p4._y);
            end,
            ["set_pos"] = function(p5, p6, p7) --[[ Name: set_pos ]] --[[ Line: 23 ]]
                p5._x = p6
                p5._y = p7
                p5._obj.Position = UDim2.new(0, p5._x, 0, p5._y)
                return p5;
            end,
            ["get_size"] = function(p8) --[[ Name: get_size ]] --[[ Line: 29 ]]
                return Vector2.new(p8._sizex, p8._sizey);
            end,
            ["set_size"] = function(p9, p10, p11) --[[ Name: set_size ]] --[[ Line: 32 ]]
                p9._sizex = p10
                p9._sizey = p11
                p9._obj.Size = UDim2.new(0, p9._sizex, 0, p9._sizey)
                return p9;
            end
        }
        local l_Parent_0 = p_u_3.Parent
        v12.set_visible = function(p13, p14) --[[ Name: set_visible ]] --[[ Line: 38 ]]
            --[[ Upvalues: (copy 1): p_u_3 ]]
            p13._visible = p14
            p_u_3.Visible = p14
            return p13;
        end;
        v12.set_parent = function(p15, p16) --[[ Name: set_parent ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): l_Parent_0, (copy 2): p_u_3 ]]
            l_Parent_0 = p16
            p_u_3.Parent = p16
            return p15;
        end;
        v12.set_name = function(_, p17) --[[ Name: set_name ]] --[[ Line: 48 ]]
            --[[ Upvalues: (copy 1): p_u_3 ]]
            p_u_3.Name = p17
        end;
        v12.set_rotation_rad = function(p18, p19) --[[ Name: set_rotation_rad ]] --[[ Line: 51 ]]
            --[[ Upvalues: (copy 1): p_u_3, (ref 2): v_u_2 ]]
            p18._rotation_rad = p19
            p_u_3.Rotation = v_u_2:rad_to_deg(p19)
            return p18;
        end;
        local v_u_20 = -1
        v12.set_alpha = function(_, p21, p22) --[[ Name: set_alpha ]] --[[ Line: 57 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_2, (copy 3): p_u_3 ]]
            local v23 = p22 == nil and 1 or p22
            if v_u_20 ~= p21 then
                v_u_20 = p21
                v_u_2:obj_set_alpha(p_u_3, p21, v23)
            end;
        end;
        v12.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20;
        end;
        return v12;
    end,
    ["set_xy"] = function(_, p24, p25, p26) --[[ Name: set_xy ]] --[[ Line: 68 ]]
        p24.Position = UDim2.new(0, p25, 0, p26)
    end,
    ["set_size_xy"] = function(_, p27, p28, p29) --[[ Name: set_size_xy ]] --[[ Line: 71 ]]
        p27.Size = UDim2.new(0, p28, 0, p29)
    end
};
