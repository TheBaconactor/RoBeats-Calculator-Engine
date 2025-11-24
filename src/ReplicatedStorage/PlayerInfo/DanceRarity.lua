-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:06 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = {
    ["Default"] = 0,
    ["Common"] = 1,
    ["Rare"] = 2,
    ["Epic"] = 3
}
v_u_2.rarity_to_color = function(_, p3) --[[ Name: rarity_to_color ]] --[[ Line: 8 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
    if p3 == v_u_2.Default then
        return v_u_1:color3(189, 196, 195);
    elseif p3 == v_u_2.Common then
        return v_u_1:color3(234, 255, 98);
    elseif p3 == v_u_2.Rare then
        return v_u_1:color3(24, 234, 252);
    else
        return v_u_1:color3(238, 130, 238);
    end;
end;
return v_u_2;
