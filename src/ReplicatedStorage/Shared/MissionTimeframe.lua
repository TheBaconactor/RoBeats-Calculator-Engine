-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:05 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = {
    ["Daily"] = 1,
    ["Weekly"] = 2
}
v_u_2.get_all = function(_) --[[ Name: get_all ]] --[[ Line: 8 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
    return v_u_1:new({ v_u_2.Daily, v_u_2.Weekly });
end;
return v_u_2;
