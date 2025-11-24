-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:45 PM
-- Time elapsed: 9 milliseconds

local v1 = {}
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict):new():add_set_from_table_list({
    2140,
    2141,
    2142,
    2143,
    2144,
    2145,
    2146,
    2147,
    2148,
    2149,
    2150
})
v1.songkey_is_new = function(_, p3) --[[ Name: songkey_is_new ]] --[[ Line: 208 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2:contains(p3);
end;
return v1;
