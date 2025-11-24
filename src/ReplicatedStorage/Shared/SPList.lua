-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:01 PM
-- Time elapsed: 13 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.RandomLua)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_18 = {
    ["END"] = -1,
    ["list_end"] = function(_) --[[ Name: list_end ]] --[[ Line: 8 ]]
        return -1;
    end,
    ["for_each"] = function(_, p3, p4) --[[ Name: for_each ]] --[[ Line: 187 ]]
        for v5 = 1, p3:count() do
            if p4(p3:get(v5), v5) == false then
                break;
            end;
        end;
    end,
    ["remove_if"] = function(_, p6, p7) --[[ Name: remove_if ]] --[[ Line: 197 ]]
        for v8 = p6:count(), 1, -1 do
            if p7(p6:get(v8), v8) == true then
                p6:remove_at(v8)
            end;
        end;
        return p6;
    end,
    ["sort_fast"] = function(_, p9, p10) --[[ Name: sort_fast ]] --[[ Line: 206 ]]
        table.sort(p9._table, p10)
    end,
    ["push_if_not_nil"] = function(_, p11, p12) --[[ Name: push_if_not_nil ]] --[[ Line: 235 ]]
        if p12 ~= nil then
            p11:push_back(p12)
        end;
    end,
    ["make_unique"] = function(_, p13) --[[ Name: make_unique ]] --[[ Line: 239 ]]
        local v14 = {}
        local v15 = true
        for v16 = p13:count(), 1, -1 do
            local v17 = p13:get(v16)
            if v14[v17] then
                p13:remove_at(v16)
                v15 = false
            else
                v14[v17] = true
            end;
        end;
        return v15;
    end
}
local function v_u_21(p19, p20) --[[ Line: 10 ]]
    return p19 == p20;
end;
local v_u_22 = v_u_1.mwc(os.time())
v_u_18.new = function(_, p23) --[[ Name: new ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_21, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_22, (copy 5): v_u_18 ]]
    local v_u_24 = p23 == nil and {} or p23
    local v39 = {
        ["_table"] = v_u_24,
        ["push_back_table_list"] = function(p25, p26) --[[ Name: push_back_table_list ]] --[[ Line: 33 ]]
            assert(type(p26) == "table")
            for v27 = 1, #p26 do
                p25:push_back(p26[v27])
            end;
            return p25;
        end,
        ["push_back_from_list"] = function(p28, p29) --[[ Name: push_back_from_list ]] --[[ Line: 40 ]]
            for v30 = 1, p29:count() do
                p28:push_back(p29:get(v30))
            end;
            return p28;
        end,
        ["contains"] = function(p31, p32) --[[ Name: contains ]] --[[ Line: 69 ]]
            return p31:find(p32, function(p33, p34) --[[ Line: 70 ]]
                return p33 == p34;
            end) ~= -1;
        end,
        ["pop_front"] = function(p35) --[[ Name: pop_front ]] --[[ Line: 81 ]]
            local v36 = p35:get(1)
            p35:remove_at(1)
            return v36;
        end,
        ["clear"] = function(p37) --[[ Name: clear ]] --[[ Line: 101 ]]
            while p37:count() > 0 do
                p37:pop_back()
            end;
        end,
        ["copy"] = function(p38) --[[ Name: copy ]] --[[ Line: 157 ]]
            return p38:table_copy();
        end
    }
    v39.get_table = function(_) --[[ Name: get_table ]] --[[ Line: 19 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24;
    end;
    v39.set_table = function(p40, p41) --[[ Name: set_table ]] --[[ Line: 20 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        v_u_24 = p41
        p40._table = v_u_24
    end;
    v39.push_back = function(_, p42) --[[ Name: push_back ]] --[[ Line: 25 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        v_u_24[#v_u_24 + 1] = p42
        return #v_u_24;
    end;
    v39.push_front = function(_, p43) --[[ Name: push_front ]] --[[ Line: 29 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        table.insert(v_u_24, 1, p43)
        return #v_u_24;
    end;
    v39.find = function(_, p44, p45) --[[ Name: find ]] --[[ Line: 46 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        for v46 = 1, #v_u_24 do
            if p45 then
                if p45(v_u_24[v46], p44) then
                    return v46;
                end;
            elseif v_u_24[v46] == p44 then
                return v46;
            end;
        end;
        return -1;
    end;
    v39.remove = function(p47, p48, p49) --[[ Name: remove ]] --[[ Line: 60 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        if p49 == nil then
            p49 = v_u_21
        end;
        local v50 = p47:find(p48, p49)
        if v50 == -1 then
            return false;
        end;
        p47:remove_at(v50)
        return true;
    end;
    v39.back = function(_) --[[ Name: back ]] --[[ Line: 73 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24[#v_u_24];
    end;
    v39.pop_back = function(_) --[[ Name: pop_back ]] --[[ Line: 76 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        local v51 = v_u_24[#v_u_24]
        v_u_24[#v_u_24] = nil
        return v51;
    end;
    v39.get = function(_, p52) --[[ Name: get ]] --[[ Line: 86 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24[p52];
    end;
    v39.set = function(p53, p54, p55) --[[ Name: set ]] --[[ Line: 89 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_24 ]]
        if p53:count() < p54 then
            v_u_2:errf("SPList:set(%d) out of range(%d)", p54, p53:count())
        end;
        v_u_24[p54] = p55
    end;
    v39.count = function(_) --[[ Name: count ]] --[[ Line: 95 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return #v_u_24;
    end;
    v39.remove_at = function(_, p56) --[[ Name: remove_at ]] --[[ Line: 98 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        table.remove(v_u_24, p56)
    end;
    v39.sort = function(p57, p_u_58) --[[ Name: sort ]] --[[ Line: 106 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        table.sort(v_u_24, function(p59, p60) --[[ Line: 107 ]]
            --[[ Upvalues: (copy 1): p_u_58 ]]
            local v61 = p_u_58(p59, p60)
            if type(v61) == "number" then
                return v61 > 0;
            elseif type(v61) == "boolean" then
                return v61;
            else
                return false;
            end;
        end)
        return p57;
    end;
    local v_u_62 = nil
    v39.set_local_random = function(_, p63) --[[ Name: set_local_random ]] --[[ Line: 123 ]]
        --[[ Upvalues: (ref 1): v_u_62, (ref 2): v_u_1 ]]
        v_u_62 = v_u_1.mwc(p63)
    end;
    local function _() --[[ Name: get_random ]] --[[ Line: 127 ]]
        --[[ Upvalues: (ref 1): v_u_62, (ref 2): v_u_22 ]]
        if v_u_62 then
            return v_u_62;
        else
            return v_u_22;
        end;
    end;
    v39.random = function(p64) --[[ Name: random ]] --[[ Line: 135 ]]
        --[[ Upvalues: (ref 1): v_u_62, (ref 2): v_u_22 ]]
        local v65
        if v_u_62 then
            v65 = v_u_62
        else
            v65 = v_u_22
        end;
        return p64:get((v65:rand_rangei(1, p64:count() + 1)));
    end;
    local function f_deepcopy(p66) --[[ Name: deepcopy ]] --[[ Line: 140 ]]
        --[[ Upvalues: (copy 1): f_deepcopy ]]
        if type(p66) ~= "table" then
            return p66;
        end;
        local v67 = {}
        for v68, v69 in next, p66 do
            v67[f_deepcopy(v68)] = f_deepcopy(v69)
        end;
        setmetatable(v67, f_deepcopy((getmetatable(p66))))
        return v67;
    end;
    v39.table_copy = function(_) --[[ Name: table_copy ]] --[[ Line: 154 ]]
        --[[ Upvalues: (copy 1): f_deepcopy, (ref 2): v_u_24 ]]
        return f_deepcopy(v_u_24);
    end;
    v39.remove_if = function(p70, p71) --[[ Name: remove_if ]] --[[ Line: 162 ]]
        --[[ Upvalues: (ref 1): v_u_18 ]]
        return v_u_18:remove_if(p70, p71);
    end;
    v39.shuffle = function(p72) --[[ Name: shuffle ]] --[[ Line: 167 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        local v73 = p72:count()
        for v74 = v73, 1, -1 do
            local v75 = math.random(v73)
            local v76 = p72:get(v75)
            local v77 = p72:get(v74)
            v_u_24[v74] = v76
            v_u_24[v75] = v77
        end;
    end;
    v39.key_itr = function(_) --[[ Name: key_itr ]] --[[ Line: 179 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return ipairs(v_u_24);
    end;
    return v39;
end;
local function v_u_80(p78, p79) --[[ Line: 211 ]]
    return p78 < p79;
end;
v_u_18.bininsert = function(_, p81, p82, p83) --[[ Name: bininsert ]] --[[ Line: 213 ]]
    --[[ Upvalues: (copy 1): v_u_80 ]]
    if p83 == nil then
        p83 = v_u_80
    end;
    local v84 = p81:count()
    local v85 = 1
    local v86 = 1
    local v87 = 0
    while v85 <= v84 do
        v86 = math.floor((v85 + v84) / 2)
        if p83(p82, p81:get(v86)) then
            v84 = v86 - 1
            v87 = 0
        else
            v85 = v86 + 1
            v87 = 1
        end;
    end;
    table.insert(p81:get_table(), v86 + v87, p82)
    return v86 + v87;
end;
return v_u_18;
