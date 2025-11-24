-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:06 PM
-- Cached decompilation

local v1 = {
    ["OnMiss"] = 0,
    ["Standard"] = 1,
    ["Combo"] = 2,
    ["Idle"] = 3
}
local v_u_2 = {
    [v1.OnMiss] = "Miss",
    [v1.Standard] = "Normal",
    [v1.Combo] = "Fever",
    [v1.Idle] = "Idle"
}
v1.type_to_string = function(_, p3) --[[ Name: type_to_string ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    local v4 = v_u_2[p3]
    return v4 == nil and "???" or v4;
end;
return v1;
