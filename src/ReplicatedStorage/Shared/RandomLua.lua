-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:03 PM
-- Cached decompilation

local l_floor_0 = math.floor
local function _(p1) --[[ Name: normalize ]] --[[ Line: 10 ]]
    return p1 % 2147483648;
end;
local function f_bit_and(p2, p3) --[[ Name: bit_and ]] --[[ Line: 14 ]]
    local v4 = 0
    for v5 = 0, 31 do
        if p2 % 2 == 1 and p3 % 2 == 1 then
            v4 = v4 + 2 ^ v5
        end;
        if p2 % 2 ~= 0 then
            p2 = p2 - 1
        end;
        if p3 % 2 ~= 0 then
            p3 = p3 - 1
        end;
        p2 = p2 / 2
        p3 = p3 / 2
    end;
    return v4 % 2147483648;
end;
local function _(p6, p7) --[[ Name: bit_or ]] --[[ Line: 26 ]]
    local v8 = 0
    for v9 = 0, 31 do
        if p6 % 2 == 1 or p7 % 2 == 1 then
            v8 = v8 + 2 ^ v9
        end;
        if p6 % 2 ~= 0 then
            p6 = p6 - 1
        end;
        if p7 % 2 ~= 0 then
            p7 = p7 - 1
        end;
        p6 = p6 / 2
        p7 = p7 / 2
    end;
    return v8 % 2147483648;
end;
local function f_bit_xor(p10, p11) --[[ Name: bit_xor ]] --[[ Line: 38 ]]
    local v12 = 0
    for v13 = 0, 31 do
        if p10 % 2 ~= p11 % 2 then
            v12 = v12 + 2 ^ v13
        end;
        if p10 % 2 ~= 0 then
            p10 = p10 - 1
        end;
        if p11 % 2 ~= 0 then
            p11 = p11 - 1
        end;
        p10 = p10 / 2
        p11 = p11 / 2
    end;
    return v12 % 2147483648;
end;
local function _() --[[ Name: seed ]] --[[ Line: 50 ]]
    return os.time() % 2147483648;
end;
mersenne_twister = {}
mersenne_twister.__index = mersenne_twister
mersenne_twister.randomseed = function(p14, p15) --[[ Name: randomseed ]] --[[ Line: 59 ]]
    --[[ Upvalues: (copy 1): f_bit_xor, (copy 2): l_floor_0 ]]
    p14.mt[0] = (p15 or os.time() % 2147483648) % 2147483648
    for v16 = 1, 623 do
        p14.mt[v16] = (1812433253 * f_bit_xor(p14.mt[v16 - 1], (l_floor_0(p14.mt[v16 - 1] / 1073741824))) + v16) % 2147483648
    end;
end;
mersenne_twister.random = function(p17, p18, p19) --[[ Name: random ]] --[[ Line: 67 ]]
    --[[ Upvalues: (copy 1): f_bit_xor, (copy 2): l_floor_0, (copy 3): f_bit_and ]]
    if p17.index == 0 then
        for v20 = 0, 623 do
            local v21 = p17.mt[(v20 + 1) % 624] % 2147483648
            p17.mt[v20] = f_bit_xor(p17.mt[(v20 + 397) % 624], (l_floor_0(v21 / 2)))
            if v21 % 2 ~= 0 then
                p17.mt[v20] = f_bit_xor(p17.mt[v20], 2567483615)
            end;
        end;
    end;
    local l_mt_0 = p17.mt[p17.index]
    local v22 = f_bit_xor(l_mt_0, (l_floor_0(l_mt_0 / 2048)))
    local v23 = f_bit_xor(v22, (f_bit_and(v22 * 128 % 2147483648, 2636928640)))
    local v24 = f_bit_xor(v23, (f_bit_and(v23 * 32768 % 2147483648, 4022730752)))
    local v25 = f_bit_xor(v24, (l_floor_0(v24 / 262144)))
    p17.index = (p17.index + 1) % 624
    if p18 then
        if p19 then
            return p18 + v25 % (p19 - p18 + 1);
        elseif p18 == 0 then
            return v25;
        else
            return 1 + v25 % p18;
        end;
    else
        return v25 / 2147483648;
    end;
end;
twister = function(p26) --[[ Name: twister ]] --[[ Line: 93 ]]
    local v_u_27 = {
        ["mt"] = {},
        ["index"] = 0
    }
    setmetatable(v_u_27, mersenne_twister)
    v_u_27:randomseed(p26)
    v_u_27.rand_rangei = function(_, p28, p29) --[[ Name: rand_rangei ]] --[[ Line: 100 ]]
        --[[ Upvalues: (copy 1): v_u_27 ]]
        return math.floor(v_u_27:random(0) / 65536 * (p29 - p28)) + p28;
    end;
    v_u_27.rand_rangef = function(_, p30, p31) --[[ Name: rand_rangef ]] --[[ Line: 104 ]]
        --[[ Upvalues: (copy 1): v_u_27 ]]
        return v_u_27:random(0) / 65536 * (p31 - p30) + p30;
    end;
    return v_u_27;
end;
linear_congruential_generator = {}
linear_congruential_generator.__index = linear_congruential_generator
linear_congruential_generator.random = function(p32, p33, p34) --[[ Name: random ]] --[[ Line: 115 ]]
    local v35 = (p32.a * p32.x + p32.c) % p32.m
    p32.x = v35
    if p33 then
        if p34 then
            return p33 + v35 % (p34 - p33 + 1);
        elseif p33 == 0 then
            return v35;
        else
            return 1 + v35 % p33;
        end;
    else
        return v35 / 65536;
    end;
end;
linear_congruential_generator.randomseed = function(p36, p37) --[[ Name: randomseed ]] --[[ Line: 127 ]]
    p36.x = (p37 or os.time() % 2147483648) % 2147483648
end;
lcg = function(p38, p39) --[[ Name: lcg ]] --[[ Line: 132 ]]
    local v_u_40 = {
        ["a"] = 1103515245,
        ["c"] = 12345,
        ["m"] = 65536
    }
    setmetatable(v_u_40, linear_congruential_generator)
    if p39 then
        if p39 == "nr" then
            v_u_40.a = 1664525
            v_u_40.c = 1013904223
            v_u_40.m = 65536
        elseif p39 == "mvc" then
            v_u_40.a = 214013
            v_u_40.c = 2531011
            v_u_40.m = 65536
        end;
    end;
    v_u_40:randomseed(p38)
    v_u_40.rand_rangei = function(_, p41, p42) --[[ Name: rand_rangei ]] --[[ Line: 142 ]]
        --[[ Upvalues: (copy 1): v_u_40 ]]
        return math.floor(v_u_40:random(0) / 65536 * (p42 - p41)) + p41;
    end;
    v_u_40.rand_rangef = function(_, p43, p44) --[[ Name: rand_rangef ]] --[[ Line: 146 ]]
        --[[ Upvalues: (copy 1): v_u_40 ]]
        return v_u_40:random(0) / 65536 * (p44 - p43) + p43;
    end;
    return v_u_40;
end;
multiply_with_carry = {}
multiply_with_carry.__index = multiply_with_carry
multiply_with_carry.random = function(p45, p46, p47) --[[ Name: random ]] --[[ Line: 157 ]]
    --[[ Upvalues: (copy 1): l_floor_0 ]]
    local l_m_0 = p45.m
    local v48 = p45.a * p45.x + p45.c
    local v49 = v48 % l_m_0
    p45.x = v49
    p45.c = l_floor_0(v48 / l_m_0)
    if p46 then
        if p47 then
            return p46 + v49 % (p47 - p46 + 1);
        elseif p46 == 0 then
            return v49;
        else
            return 1 + v49 % p46;
        end;
    else
        return v49 / 65536;
    end;
end;
multiply_with_carry.randomseed = function(p50, p51) --[[ Name: randomseed ]] --[[ Line: 172 ]]
    local v52 = p51 or os.time() % 2147483648
    p50.c = p50.ic
    p50.x = v52 % 2147483648
end;
mwc = function(p53, p54) --[[ Name: mwc ]] --[[ Line: 178 ]]
    local v_u_55 = {
        ["a"] = 1103515245,
        ["c"] = 12345,
        ["m"] = 65536
    }
    setmetatable(v_u_55, multiply_with_carry)
    if p54 then
        if p54 == "nr" then
            v_u_55.a = 1664525
            v_u_55.c = 1013904223
            v_u_55.m = 65536
        elseif p54 == "mvc" then
            v_u_55.a = 214013
            v_u_55.c = 2531011
            v_u_55.m = 65536
        end;
    end;
    v_u_55.ic = v_u_55.c
    v_u_55:randomseed(p53)
    v_u_55.rand_rangei = function(_, p56, p57) --[[ Name: rand_rangei ]] --[[ Line: 189 ]]
        --[[ Upvalues: (copy 1): v_u_55 ]]
        return math.floor(v_u_55:random(0) / 65536 * (p57 - p56)) + p56;
    end;
    v_u_55.rand_rangef = function(_, p58, p59) --[[ Name: rand_rangef ]] --[[ Line: 193 ]]
        --[[ Upvalues: (copy 1): v_u_55 ]]
        return v_u_55:random(0) / 65536 * (p59 - p58) + p58;
    end;
    return v_u_55;
end;
return {
    ["mwc"] = mwc,
    ["lcg"] = lcg,
    ["twister"] = twister
};
