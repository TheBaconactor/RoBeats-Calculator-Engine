-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:06 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_16 = {
    ["is_number"] = function(_, p3) --[[ Name: is_number ]] --[[ Line: 31 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        if typeof(p3) ~= "number" then
            v_u_1:errf("AssertType:is_number(%s)", (tostring(p3)))
        end;
    end,
    ["is_non_nil"] = function(_, p4, p5) --[[ Name: is_non_nil ]] --[[ Line: 37 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        if p4 == nil then
            if p5 ~= nil then
                v_u_1:errf("AssertType:is_non_nil(%s) [%s]", tostring(p4), (tostring(p5)))
                return;
            end;
            v_u_1:errf("AssertType:is_non_nil(%s)", (tostring(p4)))
        end;
    end,
    ["is_string"] = function(_, p6) --[[ Name: is_string ]] --[[ Line: 47 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        if typeof(p6) ~= "string" then
            v_u_1:errf("AssertType:is_string(%s)", (tostring(p6)))
        end;
    end,
    ["is_color3"] = function(_, p7) --[[ Name: is_color3 ]] --[[ Line: 53 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        if typeof(p7) ~= "Color3" then
            v_u_1:errf("AssertType:is_color3(%s)", (tostring(p7)))
        end;
    end,
    ["is_bool"] = function(_, p8) --[[ Name: is_bool ]] --[[ Line: 66 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        if typeof(p8) ~= "boolean" then
            v_u_1:errf("AssertType:is_bool(%s)", (tostring(p8)))
        end;
    end,
    ["is_table"] = function(_, p9) --[[ Name: is_table ]] --[[ Line: 72 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        if typeof(p9) ~= "table" then
            v_u_1:errf("AssertType:is_table(%s)", (tostring(p9)))
        end;
    end,
    ["is_cframe"] = function(_, p10) --[[ Name: is_cframe ]] --[[ Line: 78 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        if typeof(p10) ~= "CFrame" then
            v_u_1:errf("AssertType:is_cframe(%s)", (tostring(p10)))
        end;
    end,
    ["is_true"] = function(_, p11, p12) --[[ Name: is_true ]] --[[ Line: 84 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        if p11 ~= true then
            if p12 ~= nil then
                v_u_1:errf("AssertType:is_true(%s)", (tostring(p12)))
                return;
            end;
            v_u_1:errf("AssertType:is_true(%s)", (tostring(p11)))
        end;
    end,
    ["is_false"] = function(_, p13, p14) --[[ Name: is_false ]] --[[ Line: 94 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        if p13 ~= false then
            if p14 ~= nil then
                v_u_1:errf("AssertType:is_false(%s)", (tostring(p14)))
                return;
            end;
            v_u_1:errf("AssertType:is_false(%s)", (tostring(p13)))
        end;
    end,
    ["is_function"] = function(_, p15) --[[ Name: is_function ]] --[[ Line: 134 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        if typeof(p15) ~= "function" then
            v_u_1:errf("AssertType:is_function(%s)", (tostring(p15)))
        end;
    end
}
v_u_16.is_int = function(_, p17) --[[ Name: is_int ]] --[[ Line: 6 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_1 ]]
    v_u_16:is_number(p17)
    if math.floor(p17) ~= p17 then
        v_u_1:errf("AssertType:is_int(%s)", (tostring(p17)))
    end;
end;
v_u_16.is_positive = function(_, p18) --[[ Name: is_positive ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_1 ]]
    v_u_16:is_number(p18)
    if p18 < 0 then
        v_u_1:errf("AssertType:is_positive(%s)", (tostring(p18)))
    end;
end;
v_u_16.is_int_in_range = function(_, p19, p20, p21) --[[ Name: is_int_in_range ]] --[[ Line: 20 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_1 ]]
    v_u_16:is_int(p19)
    if p19 < p20 or p21 < p19 then
        v_u_1:errf("AssertType:is_int_in_range(%s)", (tostring(p19)))
    end;
end;
v_u_16.is_int_greater_than = function(_, p22, p23) --[[ Name: is_int_greater_than ]] --[[ Line: 27 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    v_u_16:is_int_in_range(p22, p23, p22)
end;
v_u_16.is_nonempty_string = function(_, p24) --[[ Name: is_nonempty_string ]] --[[ Line: 59 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_1 ]]
    v_u_16:is_string(p24)
    if #p24 == 0 then
        v_u_1:errf("AssertType:is_nonempty_string(%s)", (tostring(p24)))
    end;
end;
local v_u_25 = v_u_2:new()
v_u_16.test_enum_member = function(_, p26, p27) --[[ Name: test_enum_member ]] --[[ Line: 105 ]]
    --[[ Upvalues: (copy 1): v_u_25, (copy 2): v_u_2 ]]
    if p26 == nil then
        return false;
    end;
    if v_u_25:contains(p27) ~= true then
        local v28 = v_u_2:new()
        for v29, v30 in pairs(p27) do
            if typeof(v30) == "number" or typeof(v30) == "string" then
                v28:add(v30, v29)
            end;
        end;
        v_u_25:add(p27, v28)
    end;
    return v_u_25:get(p27):contains(p26) == true;
end;
v_u_16.is_enum_member = function(_, p31, p32) --[[ Name: is_enum_member ]] --[[ Line: 124 ]]
    --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_1 ]]
    if v_u_16:test_enum_member(p31, p32) ~= true then
        v_u_1:errf("AssertType:is_enum_member(%s)", (tostring(p31)))
    end;
end;
v_u_16.is_classname = function(_, p33, p34) --[[ Name: is_classname ]] --[[ Line: 130 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    v_u_16:is_true(p33.ClassName == p34)
end;
v_u_16.is_table_same_format = function(_, p35, p36) --[[ Name: is_table_same_format ]] --[[ Line: 140 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    for v37, _ in pairs(p35) do
        v_u_16:is_true(typeof(p35[v37]) == typeof(p36[v37]))
    end;
    for v38, _ in pairs(p36) do
        v_u_16:is_true(typeof(p35[v38]) == typeof(p36[v38]))
    end;
end;
return v_u_16;
