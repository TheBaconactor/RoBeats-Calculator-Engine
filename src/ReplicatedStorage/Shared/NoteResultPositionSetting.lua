-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:11 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.SPDict)
local v2 = require(game.ReplicatedStorage.Shared.SPList)
local v3 = {
    ["Default"] = 1,
    ["Top"] = 2,
    ["Middle"] = 3,
    ["Hidden"] = 4
}
local v_u_4 = v1:new()
for v5, v6 in pairs(v3) do
    v_u_4:add(v6, v5)
end;
v3.key_to_name = function(_, p7) --[[ Name: key_to_name ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_4 ]]
    return v_u_4:get(p7);
end;
local v_u_8 = v2:new({
    v3.Default,
    v3.Top,
    v3.Middle,
    v3.Hidden
})
v3.keys_list = function(_) --[[ Name: keys_list ]] --[[ Line: 25 ]]
    --[[ Upvalues: (copy 1): v_u_8 ]]
    return v_u_8;
end;
return v3;
