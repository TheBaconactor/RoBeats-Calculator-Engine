-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:07 PM
-- Cached decompilation

local v_u_29 = {
    ["__type"] = "LVector3",
    ["TYPE_LVECTOR3"] = "LVector3",
    ["set"] = function(p1, p2, p3, p4) --[[ Name: set ]] --[[ Line: 142 ]]
        if type(p2) == "table" and (p2.__type and p2.__type == "LVector3") then
            p1.x = p2.x
            p1.y = p2.y
            p1.z = p2.z
            return p1;
        else
            p1.x = p2 or 0
            p1.y = p3 or 0
            p1.z = p4 or 0
            return p1;
        end;
    end,
    ["set_zero"] = function(p5) --[[ Name: set_zero ]] --[[ Line: 155 ]]
        p5:set(0, 0, 0)
    end,
    ["from_vector3"] = function(p6, p7) --[[ Name: from_vector3 ]] --[[ Line: 161 ]]
        if typeof(p7) == "Vector2" then
            return p6:set(p7.X, p7.Y, 0);
        else
            return p6:set(p7.X, p7.Y, p7.Z);
        end;
    end,
    ["scale"] = function(p8, p9) --[[ Name: scale ]] --[[ Line: 173 ]]
        p8.x = p8.x * p9
        p8.y = p8.y * p9
        p8.z = p8.z * p9
        return p8;
    end,
    ["store_add_result"] = function(p10, p11, p12) --[[ Name: store_add_result ]] --[[ Line: 180 ]]
        local v13 = type(p11) == "table" and (p11.__type and p11.__type == "LVector3") and true or typeof(p11) == "Vector3"
        local v14 = type(p12) == "table" and (p12.__type and p12.__type == "LVector3") and true or typeof(p12) == "Vector3"
        if v13 and v14 then
            return p10:set(p11.x + p12.x, p11.y + p12.y, p11.z + p12.z);
        elseif v14 then
            local v15 = type(p11)
            if v15 == "table" then
                v15 = p11.__type or v15
            end;
            error("bad argument #1 to \'?\' (LVector3 expected, got " .. v15 .. ")")
        elseif v13 then
            local v16 = type(p12)
            if v16 == "table" then
                v16 = p12.__type or v16
            end;
            error("bad argument #2 to \'?\' (LVector3 expected, got " .. v16 .. ")")
        end;
    end,
    ["store_sub_result"] = function(p17, p18, p19) --[[ Name: store_sub_result ]] --[[ Line: 198 ]]
        local v20 = type(p18) == "table" and (p18.__type and p18.__type == "LVector3") and true or typeof(p18) == "Vector3"
        local v21 = type(p19) == "table" and (p19.__type and p19.__type == "LVector3") and true or typeof(p19) == "Vector3"
        if v20 and v21 then
            return p17:set(p18.x - p19.x, p18.y - p19.y, p18.z - p19.z);
        elseif v21 then
            local v22 = type(p18)
            if v22 == "table" then
                v22 = p18.__type or v22
            end;
            error("bad argument #1 to \'?\' (LVector3 expected, got " .. v22 .. ")")
        elseif v20 then
            local v23 = type(p19)
            if v23 == "table" then
                v23 = p19.__type or v23
            end;
            error("bad argument #2 to \'?\' (LVector3 expected, got " .. v23 .. ")")
        end;
    end,
    ["store_cross_result"] = function(p24, p25, p26) --[[ Name: store_cross_result ]] --[[ Line: 223 ]]
        local l___type_0 = p25.__type
        if l___type_0 then
            l___type_0 = p26.__type == "LVector3"
        end;
        local l___type_1 = p26.__type
        if l___type_1 then
            l___type_1 = p26.__type == "LVector3"
        end;
        if l___type_0 and l___type_1 then
            p24:set(p25.y * p26.z - p25.z * p26.y, p25.z * p26.x - p25.x * p26.z, p25.x * p26.y - p25.y * p26.x)
        else
            error("bad argument #1 to \'Cross\' (LVector3 expected, got ?)")
        end;
    end,
    ["Dot"] = function(p27, p28) --[[ Name: Dot ]] --[[ Line: 272 ]]
        local l___type_2 = p28.__type
        if l___type_2 then
            l___type_2 = p28.__type == "LVector3"
        end;
        if l___type_2 then
            return p27.x * p28.x + p27.y * p28.y + p27.z * p28.z;
        end;
        error("bad argument #1 to \'Dot\' (LVector3 expected, got number)")
    end
}
local v_u_46 = {
    ["__index"] = v_u_29,
    ["__add"] = function(p30, p31) --[[ Name: __add ]] --[[ Line: 75 ]]
        --[[ Upvalues: (copy 1): v_u_29 ]]
        local v32 = v_u_29.new()
        v32:store_add_result(p30, p31)
        return v32;
    end,
    ["__eq"] = function(p33, p34) --[[ Name: __eq ]] --[[ Line: 81 ]]
        if (type(p33) == "table" and (p33.__type and p33.__type == "LVector3") and true or typeof(p33) == "Vector3") and (type(p34) == "table" and (p34.__type and p34.__type == "LVector3") and true or typeof(p34) == "Vector3") then
            local v35
            if p33.x == p34.x and p33.y == p34.y then
                v35 = p33.z == p34.z
            else
                v35 = false
            end;
            return v35;
        end;
        error("Compare not both LVector3")
    end,
    ["__sub"] = function(p36, p37) --[[ Name: __sub ]] --[[ Line: 91 ]]
        --[[ Upvalues: (copy 1): v_u_29 ]]
        local v38 = v_u_29.new()
        v38:store_sub_result(p36, p37)
        return v38;
    end,
    ["__mul"] = function(p39, p40) --[[ Name: __mul ]] --[[ Line: 97 ]]
        --[[ Upvalues: (copy 1): v_u_29 ]]
        if type(p39) == "number" then
            return v_u_29.new(p39 * p40.x, p39 * p40.y, p39 * p40.z);
        end;
        if type(p40) == "number" then
            return v_u_29.new(p39.x * p40, p39.y * p40, p39.z * p40);
        end;
        if p39.__type and (p39.__type == "LVector3" and (p40.__type and p40.__type == "LVector3")) then
            return v_u_29.new(p39.x * p40.x, p39.y * p40.y, p39.z * p40.z);
        end;
        error("attempt to multiply a LVector3 with an incompatible value type or nil")
    end,
    ["__div"] = function(p41, p42) --[[ Name: __div ]] --[[ Line: 109 ]]
        --[[ Upvalues: (copy 1): v_u_29 ]]
        if type(p41) == "number" then
            return v_u_29.new(p41 / p42.x, p41 / p42.y, p41 / p42.z);
        end;
        if type(p42) == "number" then
            return v_u_29.new(p41.x / p42, p41.y / p42, p41.z / p42);
        end;
        if p41.__type and (p41.__type == "LVector3" and (p42.__type and p42.__type == "LVector3")) then
            return v_u_29.new(p41.x / p42.x, p41.y / p42.y, p41.z / p42.z);
        end;
        error("attempt to divide a LVector3 with an incompatible value type or nil")
    end,
    ["__unm"] = function(p43) --[[ Name: __unm ]] --[[ Line: 121 ]]
        --[[ Upvalues: (copy 1): v_u_29 ]]
        return v_u_29.new(-p43.x, -p43.y, -p43.z);
    end,
    ["__tostring"] = function(p44) --[[ Name: __tostring ]] --[[ Line: 125 ]]
        return p44.x .. ", " .. p44.y .. ", " .. p44.z;
    end,
    ["__metatable"] = false,
    ["to_vector3"] = function(p45) --[[ Name: to_vector3 ]] --[[ Line: 157 ]]
        return Vector3.new(p45.x, p45.y, p45.z);
    end
}
local l_sqrt_0 = math.sqrt
local function _(p47) --[[ Name: calcMagnitude ]] --[[ Line: 18 ]]
    --[[ Upvalues: (copy 1): l_sqrt_0 ]]
    return l_sqrt_0(p47.x ^ 2 + p47.y ^ 2 + p47.z ^ 2);
end;
local function f_store_normalized(p48, p49) --[[ Name: store_normalized ]] --[[ Line: 22 ]]
    --[[ Upvalues: (copy 1): l_sqrt_0 ]]
    local v50 = l_sqrt_0(p49.x ^ 2 + p49.y ^ 2 + p49.z ^ 2)
    if v50 > 0 then
        return p48:set(p49.x / v50, p49.y / v50, p49.z / v50);
    else
        return p48:set(0, 0, 0);
    end;
end;
local v_u_51 = {
    ["X"] = "x",
    ["Y"] = "y",
    ["Z"] = "z",
    ["Magnitude"] = "magnitude",
    ["Unit"] = "unit"
}
v_u_46.__index = function(p52, p53) --[[ Name: __index ]] --[[ Line: 43 ]]
    --[[ Upvalues: (copy 1): v_u_51, (copy 2): v_u_29, (copy 3): f_store_normalized, (copy 4): l_sqrt_0, (copy 5): v_u_46 ]]
    if v_u_51[p53] ~= nil then
        p53 = v_u_51[p53]
    end;
    if p53 == "unit" then
        return f_store_normalized(v_u_29.new(), p52);
    end;
    if p53 == "magnitude" then
        return l_sqrt_0(p52.x ^ 2 + p52.y ^ 2 + p52.z ^ 2);
    end;
    if v_u_29[p53] then
        return v_u_29[p53];
    end;
    if rawget(p52, "proxy")[p53] then
        return rawget(p52, "proxy")[p53];
    end;
    if typeof((rawget(v_u_46, p53))) == "function" then
        return rawget(v_u_46, p53);
    end;
    error(p53 .. " is not a valid member of LVector3")
end;
v_u_46.__newindex = function(p54, p55, p56) --[[ Name: __newindex ]] --[[ Line: 63 ]]
    --[[ Upvalues: (copy 1): v_u_51 ]]
    if v_u_51[p55] ~= nil then
        p55 = v_u_51[p55]
    end;
    if rawget(p54, "proxy")[p55] == nil then
        error(p55 .. " cannot be assigned to")
    else
        rawget(p54, "proxy")[p55] = p56
    end;
end;
v_u_29.new = function(p57, p58, p59) --[[ Name: new ]] --[[ Line: 133 ]]
    --[[ Upvalues: (copy 1): v_u_46 ]]
    local v60 = {
        ["proxy"] = {}
    }
    v60.proxy.x = p57 or 0
    v60.proxy.y = p58 or 0
    v60.proxy.z = p59 or 0
    return setmetatable(v60, v_u_46);
end;
v_u_29.store_normalized = function(p61, p62) --[[ Name: store_normalized ]] --[[ Line: 169 ]]
    --[[ Upvalues: (copy 1): f_store_normalized ]]
    return f_store_normalized(p61, p62);
end;
local v_u_63 = v_u_29.new()
v_u_29.store_lerp_result = function(p64, p65, p66, p67) --[[ Name: store_lerp_result ]] --[[ Line: 216 ]]
    --[[ Upvalues: (copy 1): v_u_63 ]]
    v_u_63:store_sub_result(p66, p65)
    v_u_63:scale(p67)
    p64:store_add_result(p65, v_u_63)
    return p64;
end;
v_u_29.FromNormalId = function(p_u_68) --[[ Name: FromNormalId ]] --[[ Line: 237 ]]
    --[[ Upvalues: (copy 1): v_u_29 ]]
    pcall(function() --[[ Line: 238 ]]
        --[[ Upvalues: (ref 1): p_u_68 ]]
        p_u_68 = p_u_68.Value or p_u_68
    end)
    if p_u_68 == 0 then
        return v_u_29.new(1, 0, 0);
    end;
    if p_u_68 == 1 then
        return v_u_29.new(0, 1, 0);
    end;
    if p_u_68 == 2 then
        return v_u_29.new(0, 0, 1);
    end;
    if p_u_68 == 3 then
        return v_u_29.new(-1, 0, 0);
    end;
    if p_u_68 == 4 then
        return v_u_29.new(0, -1, 0);
    end;
    if p_u_68 == 5 then
        return v_u_29.new(0, 0, -1);
    end;
end;
v_u_29.FromAxis = function(p_u_69) --[[ Name: FromAxis ]] --[[ Line: 254 ]]
    --[[ Upvalues: (copy 1): v_u_29 ]]
    pcall(function() --[[ Line: 255 ]]
        --[[ Upvalues: (ref 1): p_u_69 ]]
        p_u_69 = p_u_69.Value or p_u_69
    end)
    if p_u_69 == 0 then
        return v_u_29.new(1, 0, 0);
    end;
    if p_u_69 == 1 then
        return v_u_29.new(0, 1, 0);
    end;
    if p_u_69 == 2 then
        return v_u_29.new(0, 0, 1);
    end;
end;
v_u_29.Lerp = function(p70, p71, p72) --[[ Name: Lerp ]] --[[ Line: 265 ]]
    --[[ Upvalues: (copy 1): v_u_29 ]]
    local v73 = v_u_29.new()
    v73:store_lerp_result(p70, p71, p72)
    return v73;
end;
v_u_29.Cross = function(p74, p75) --[[ Name: Cross ]] --[[ Line: 281 ]]
    --[[ Upvalues: (copy 1): v_u_29 ]]
    local v76 = v_u_29.new()
    v76:store_cross_result(p74, p75)
    return v76;
end;
return v_u_29;
