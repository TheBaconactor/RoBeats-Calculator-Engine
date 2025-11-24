-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:01 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_27 = {
    ["remove_if"] = function(_, p2, p3) --[[ Name: remove_if ]] --[[ Line: 104 ]]
        local v4 = p2:key_list()
        for v5 = 1, v4:count() do
            local v6 = v4:get(v5)
            if p3(p2:get(v6), v6) == true then
                p2:remove(v6)
            end;
        end;
        return p2;
    end,
    ["set_equals"] = function(_, p7, p8) --[[ Name: set_equals ]] --[[ Line: 115 ]]
        for v9, _ in p7:key_itr() do
            if p8:contains(v9) ~= true then
                return false;
            end;
        end;
        for v10, _ in p8:key_itr() do
            if p7:contains(v10) ~= true then
                return false;
            end;
        end;
        return true;
    end,
    ["counter_increment"] = function(_, p11, p12, p13) --[[ Name: counter_increment ]] --[[ Line: 125 ]]
        local v14 = p13 == nil and 1 or p13
        if p11:contains(p12) ~= true then
            p11:add(p12, 0)
        end;
        p11:add(p12, p11:get(p12) + v14)
    end,
    ["counter_get"] = function(_, p15, p16) --[[ Name: counter_get ]] --[[ Line: 135 ]]
        return not p15:contains(p16) and 0 or p15:get(p16);
    end,
    ["random_key_value"] = function(_, p17) --[[ Name: random_key_value ]] --[[ Line: 181 ]]
        local v18 = p17:key_list():random()
        return v18, p17:get(v18);
    end,
    ["for_each_key_value_sorted"] = function(_, p19, p20, p21) --[[ Name: for_each_key_value_sorted ]] --[[ Line: 187 ]]
        local v22 = p19:key_list()
        if p21 then
            v22:sort(p21)
        else
            v22:sort(function(p23, p24) --[[ Line: 192 ]]
                return p23 < p24;
            end)
        end;
        for v25 = 1, v22:count() do
            local v26 = v22:get(v25)
            p20(v26, p19:get(v26), v25)
        end;
    end
}
v_u_27.new = function(_, p28) --[[ Name: new ]] --[[ Line: 5 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_27 ]]
    local v_u_29 = p28 == nil and {} or p28
    local v42 = {
        ["_table"] = v_u_29,
        ["count"] = function(p30) --[[ Name: count ]] --[[ Line: 34 ]]
            local v31 = 0
            for _, _ in p30:key_itr() do
                v31 = v31 + 1
            end;
            return v31;
        end,
        ["add_table"] = function(p32, p33) --[[ Name: add_table ]] --[[ Line: 56 ]]
            for v34, v35 in pairs(p33) do
                p32:add(v34, v35)
            end;
            return p32;
        end,
        ["add_set_from_table_list"] = function(p36, p37) --[[ Name: add_set_from_table_list ]] --[[ Line: 62 ]]
            for v38 = 1, #p37 do
                local v39 = p37[v38]
                if v39 ~= nil then
                    p36:add_set(v39)
                end;
            end;
            return p36;
        end,
        ["add_set"] = function(p40, p41) --[[ Name: add_set ]] --[[ Line: 71 ]]
            p40:add(p41, true)
        end
    }
    v42.get_table = function(_) --[[ Name: get_table ]] --[[ Line: 11 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29;
    end;
    v42.set_table = function(p43, p44) --[[ Name: set_table ]] --[[ Line: 12 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        v_u_29 = p44
        p43._table = v_u_29
    end;
    v42.add = function(_, p45, p46) --[[ Name: add ]] --[[ Line: 17 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        v_u_29[p45] = p46
        return p46;
    end;
    v42.remove = function(p47, p48) --[[ Name: remove ]] --[[ Line: 21 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        if not p47:contains(p48) then
            return false;
        end;
        v_u_29[p48] = nil
        return true;
    end;
    v42.get = function(_, p49) --[[ Name: get ]] --[[ Line: 28 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29[p49];
    end;
    v42.contains = function(_, p50) --[[ Name: contains ]] --[[ Line: 31 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29[p50] ~= nil;
    end;
    local function _(p51) --[[ Name: table_clear ]] --[[ Line: 39 ]]
        for v52, _ in pairs(p51) do
            p51[v52] = nil
        end;
    end;
    v42.clear = function(p53) --[[ Name: clear ]] --[[ Line: 42 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        local v54 = v_u_29
        for v55, _ in pairs(v54) do
            v54[v55] = nil
        end;
        return p53;
    end;
    v42.key_itr = function(_) --[[ Name: key_itr ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return pairs(v_u_29);
    end;
    v42.key_list = function(p56) --[[ Name: key_list ]] --[[ Line: 49 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        local v57 = v_u_1:new()
        for v58, _ in p56:key_itr() do
            v57:push_back(v58)
        end;
        return v57;
    end;
    v42.json_encode_copy = function(_) --[[ Name: json_encode_copy ]] --[[ Line: 75 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        local v59 = {}
        for v60, v61 in pairs(v_u_29) do
            if typeof(v60) == "number" then
                v59[string.format("#%s", (tostring(v60)))] = v61
            else
                v59[v60] = v61
            end;
        end;
        return v59;
    end;
    v42.copy = function(p62) --[[ Name: copy ]] --[[ Line: 87 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        local v63 = v_u_27:new()
        for v64, v65 in p62:key_itr() do
            v63:add(v64, v65)
        end;
        return v63;
    end;
    v42.remove_if = function(p66, p67) --[[ Name: remove_if ]] --[[ Line: 96 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27:remove_if(p66, p67);
    end;
    return v42;
end;
v_u_27.set_union = function(_, p68, p69, p70) --[[ Name: set_union ]] --[[ Line: 143 ]]
    --[[ Upvalues: (copy 1): v_u_27 ]]
    if p70 == nil then
        p70 = v_u_27:new()
    end;
    if p68 then
        for v71, _ in p68:key_itr() do
            p70:add_set(v71)
        end;
    end;
    if p69 then
        for v72, _ in p69:key_itr() do
            p70:add_set(v72)
        end;
    end;
    return p70;
end;
v_u_27.set_intersection = function(_, p73, p74, p75) --[[ Name: set_intersection ]] --[[ Line: 160 ]]
    --[[ Upvalues: (copy 1): v_u_27 ]]
    if p75 == nil then
        p75 = v_u_27:new()
    end;
    if p73 then
        for v76, _ in p73:key_itr() do
            if p74:contains(v76) then
                p75:add_set(v76)
            end;
        end;
    end;
    if p74 then
        for v77, _ in p74:key_itr() do
            if p73:contains(v77) then
                p75:add_set(v77)
            end;
        end;
    end;
    return p75;
end;
return v_u_27;
