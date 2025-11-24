-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:03 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_26 = {
    ["new"] = function(_, p2, p3, p4) --[[ Name: new ]] --[[ Line: 12 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v19 = {
            ["_x"] = p2,
            ["_y"] = p3,
            ["_z"] = p4,
            ["add_scaled"] = function(p5, p6, p7) --[[ Name: add_scaled ]] --[[ Line: 19 ]]
                p5._x = p5._x + p6._x * p7
                p5._y = p5._y + p6._y * p7
                p5._z = p5._z + p6._z * p7
            end,
            ["set"] = function(p8, p9, p10, p11) --[[ Name: set ]] --[[ Line: 24 ]]
                if p9 ~= nil then
                    p8._x = p9
                end;
                if p10 ~= nil then
                    p8._y = p10
                end;
                if p11 ~= nil then
                    p8._z = p11
                end;
                return p8;
            end,
            ["magnitude"] = function(p12) --[[ Name: magnitude ]] --[[ Line: 36 ]]
                return math.sqrt(math.pow(p12._x == nil and 0 or p12._x, 2) + math.pow(p12._y == nil and 0 or p12._y, 2) + math.pow(p12._z == nil and 0 or p12._z, 2));
            end,
            ["distance_to"] = function(p13, p14) --[[ Name: distance_to ]] --[[ Line: 47 ]]
                return math.sqrt(math.pow((p14._x == nil and 0 or p14._x) - (p13._x == nil and 0 or p13._x), 2) + math.pow((p14._y == nil and 0 or p14._y) - (p13._y == nil and 0 or p13._y), 2) + math.pow((p14._z == nil and 0 or p14._z) - (p13._z == nil and 0 or p13._z), 2));
            end,
            ["to_color3"] = function(p15) --[[ Name: to_color3 ]] --[[ Line: 86 ]]
                return Color3.new(p15._x / 255, p15._y / 255, p15._z / 255);
            end,
            ["to_vector2"] = function(p16) --[[ Name: to_vector2 ]] --[[ Line: 89 ]]
                return Vector2.new(p16._x, p16._y);
            end,
            ["to_vector3"] = function(p17) --[[ Name: to_vector3 ]] --[[ Line: 92 ]]
                return Vector3.new(p17._x, p17._y, p17._z);
            end,
            ["to_string"] = function(p18) --[[ Name: to_string ]] --[[ Line: 95 ]]
                return string.format("{%s, %s, %s}", tostring(p18._x), tostring(p18._y), (tostring(p18._z)));
            end
        }
        v19.expt_to = function(p20, p21, p22, p23, p24, p25) --[[ Name: expt_to ]] --[[ Line: 65 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            p20._x = v_u_1:Expt(p20._x, p21, v_u_1:NormalizedDefaultExptValueInSeconds(p24), p25)
            p20._y = v_u_1:Expt(p20._y, p22, v_u_1:NormalizedDefaultExptValueInSeconds(p24), p25)
            p20._z = v_u_1:Expt(p20._z, p23, v_u_1:NormalizedDefaultExptValueInSeconds(p24), p25)
        end;
        return v19;
    end
}
v_u_26.from_vec3 = function(_, p27) --[[ Name: from_vec3 ]] --[[ Line: 5 ]]
    --[[ Upvalues: (copy 1): v_u_26 ]]
    return v_u_26:new(p27.X, p27.Y, p27.Z);
end;
v_u_26.from_vec2 = function(_, p28) --[[ Name: from_vec2 ]] --[[ Line: 8 ]]
    --[[ Upvalues: (copy 1): v_u_26 ]]
    return v_u_26:new(p28.X, p28.Y);
end;
return v_u_26;
