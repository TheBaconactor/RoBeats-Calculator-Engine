-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:05 PM
-- Cached decompilation

local v_u_1 = {
    ["count"] = function(_, ...) --[[ Name: count ]] --[[ Line: 78 ]]
        return select("#", ...);
    end
}
local function _(p2) --[[ Name: sparse_num_to_str_format ]] --[[ Line: 4 ]]
    return "__" .. tostring(p2);
end;
local function _(p3) --[[ Name: sparse_str_to_num_format ]] --[[ Line: 8 ]]
    if string.sub(p3, 1, 2) == "__" then
        return tonumber((string.sub(p3, 3)));
    else
        return nil;
    end;
end;
local function f_sparse_array_convert(p4) --[[ Name: sparse_array_convert ]] --[[ Line: 15 ]]
    if typeof(p4) ~= "table" then
        return p4;
    end;
    local v5 = false
    for v6, _ in pairs(p4) do
        if typeof(v6) == "number" then
            v5 = true
            break;
        end;
    end;
    if v5 == false then
        return p4;
    end;
    local v7 = {}
    for v8, v9 in pairs(p4) do
        if typeof(v8) == "number" then
            v7["__" .. tostring(v8)] = v9
        else
            v7[v8] = v9
        end;
    end;
    return v7;
end;
local function f_sparse_array_deconvert(p10) --[[ Name: sparse_array_deconvert ]] --[[ Line: 45 ]]
    if typeof(p10) ~= "table" then
        return p10;
    end;
    local v11 = false
    for v12, _ in pairs(p10) do
        local v13
        if string.sub(v12, 1, 2) == "__" then
            v13 = tonumber((string.sub(v12, 3)))
        else
            v13 = nil
        end;
        if v13 ~= nil then
            v11 = true
            break;
        end;
    end;
    if v11 == false then
        return p10;
    end;
    local v14 = {}
    for v15, v16 in pairs(p10) do
        local v17
        if string.sub(v15, 1, 2) == "__" then
            v17 = tonumber((string.sub(v15, 3)))
        else
            v17 = nil
        end;
        if v17 == nil then
            v14[v15] = v16
        else
            v14[v17] = v16
        end;
    end;
    return v14;
end;
v_u_1.sparse_array_convert = function(_, p18) --[[ Name: sparse_array_convert ]] --[[ Line: 75 ]]
    --[[ Upvalues: (copy 1): f_sparse_array_convert ]]
    return f_sparse_array_convert(p18);
end;
v_u_1.sparse_array_deconvert = function(_, p19) --[[ Name: sparse_array_deconvert ]] --[[ Line: 76 ]]
    --[[ Upvalues: (copy 1): f_sparse_array_deconvert ]]
    return f_sparse_array_deconvert(p19);
end;
local function f__tmap(p20, p21, p22, ...) --[[ Name: _tmap ]] --[[ Line: 82 ]]
    --[[ Upvalues: (copy 1): f__tmap ]]
    if p21 > 0 then
        return p20(p22), f__tmap(p20, p21 - 1, ...);
    end;
end;
local function f_tmap(p23, ...) --[[ Name: tmap ]] --[[ Line: 87 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): f__tmap ]]
    return f__tmap(p23, v_u_1:count(...), ...);
end;
v_u_1.arg_convert = function(_, ...) --[[ Name: arg_convert ]] --[[ Line: 92 ]]
    --[[ Upvalues: (copy 1): f_tmap, (copy 2): f_sparse_array_convert ]]
    return f_tmap(f_sparse_array_convert, ...);
end;
v_u_1.arg_deconvert = function(_, ...) --[[ Name: arg_deconvert ]] --[[ Line: 95 ]]
    --[[ Upvalues: (copy 1): f_tmap, (copy 2): f_sparse_array_deconvert ]]
    return f_tmap(f_sparse_array_deconvert, ...);
end;
return v_u_1;
