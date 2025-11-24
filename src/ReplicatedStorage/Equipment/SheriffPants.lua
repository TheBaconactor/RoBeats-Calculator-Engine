-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:32 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
require(game.ReplicatedStorage.Avatar.GearStats)
local v3 = v_u_1:new()
v3.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 7 ]]
    return "Sheriff\'s Chaps";
end;
v3.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.PANTS;
end;
v3.apply_appearance = function(_, p4) --[[ Name: apply_appearance ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    v_u_1:pants_base_apply(p4, "http://www.roblox.com/asset/?id=7189816097")
end;
v3.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 16 ]]
    return {};
end;
v3.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 20 ]]
    return 0;
end;
v3.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 23 ]]
    return 2;
end;
v3.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 26 ]]
    return "http://www.roblox.com/asset/?id=7234742851";
end;
return v3;
