-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:45 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = {
    ["Normal"] = 0,
    ["Hard"] = 1,
    ["Easy"] = 2
}
local v_u_3 = {}
local v_u_4 = {}
for v5, v6 in pairs(v_u_2) do
    v_u_3[v6] = v5
    v_u_4[v5] = v6
end;
v_u_2.name_to_mod_itr = function(_) --[[ Name: name_to_mod_itr ]] --[[ Line: 17 ]]
    --[[ Upvalues: (copy 1): v_u_4 ]]
    return pairs(v_u_4);
end;
v_u_2.mod_to_name = function(_, p7) --[[ Name: mod_to_name ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    local v8 = v_u_3[p7]
    return v8 == nil and "?" or v8;
end;
v_u_2.mod_to_compare_value = function(_, p9) --[[ Name: mod_to_compare_value ]] --[[ Line: 25 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
    v_u_1:is_enum_member(p9, v_u_2)
    return p9 == v_u_2.Hard and 3 or (p9 == v_u_2.Normal and 2 or 1);
end;
v_u_2.mod_get_image = function(_, p10) --[[ Name: mod_get_image ]] --[[ Line: 37 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return p10 == v_u_2.Hard and "rbxassetid://7337182025" or (p10 == v_u_2.Normal and "rbxassetid://7337181851" or "rbxassetid://7337181625");
end;
return v_u_2;
