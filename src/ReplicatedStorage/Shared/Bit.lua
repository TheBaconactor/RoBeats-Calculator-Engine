-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:08 PM
-- Cached decompilation

local v_u_1 = nil
v_u_1 = {
    ["Has"] = function(p2, p3) --[[ Name: Has ]] --[[ Line: 3 ]]
        return p3 <= p2 % (p3 * 2);
    end,
    ["And"] = function(p4, p5) --[[ Name: And ]] --[[ Line: 7 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        local v6 = 0
        for v7 = 0, 31 do
            v6 = v6 + (v_u_1.Has(p4, 2 ^ v7) and v_u_1.Has(p5, 2 ^ v7) and (2 ^ v7 or 0) or 0)
        end;
        return v6;
    end,
    ["Or"] = function(p8, p9) --[[ Name: Or ]] --[[ Line: 15 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        local v10 = 0
        for v11 = 0, 31 do
            v10 = v10 + ((v_u_1.Has(p8, 2 ^ v11) or v_u_1.Has(p9, 2 ^ v11)) and (2 ^ v11 or 0) or 0)
        end;
        return v10;
    end,
    ["RShift"] = function(p12, p13) --[[ Name: RShift ]] --[[ Line: 23 ]]
        return math.floor(p12 * 0.5 ^ (p13 or 1));
    end,
    ["LShift"] = function(p14, p15) --[[ Name: LShift ]] --[[ Line: 27 ]]
        return p14 * 2 ^ (p15 or 1);
    end,
    ["RRotate"] = function(p16, p17) --[[ Name: RRotate ]] --[[ Line: 31 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        local v18 = p17 or 1
        return v_u_1.Or(v_u_1.RShift(p16, v18), v_u_1.LShift(p16, 32 - v18));
    end,
    ["LRotate"] = function(p19, p20) --[[ Name: LRotate ]] --[[ Line: 36 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        local v21 = p20 or 1
        return v_u_1.Or(v_u_1.LShift(p19, v21), v_u_1.RShift(p19, 32 - v21));
    end,
    ["Not"] = function(p22) --[[ Name: Not ]] --[[ Line: 41 ]]
        return 4294967295 - p22;
    end,
    ["Xor"] = function(p23, p24) --[[ Name: Xor ]] --[[ Line: 45 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        local v25 = 0
        for v26 = 0, 31 do
            v25 = v25 + (v_u_1.Has(p23, 2 ^ v26) == v_u_1.Has(p24, 2 ^ v26) and 0 or (2 ^ v26 or 0))
        end;
        return v25;
    end
}
return v_u_1;
