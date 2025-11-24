-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:19 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v3 = v_u_1:new()
v3.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "TestPants1";
end;
v3.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.PANTS;
end;
v3.apply_appearance = function(_, p4) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    v_u_1:pants_base_apply(p4, "rbxassetid://17539100")
end;
v3.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 18 ]]
    return 0;
end;
v3.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 21 ]]
    return -1;
end;
v3.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 24 ]]
    return {};
end;
v3.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 28 ]]
    return "https://www.roblox.com/Thumbs/Asset.ashx?width=110&height=110&assetId=159199178";
end;
v3.is_debug = function(_) --[[ Name: is_debug ]] --[[ Line: 31 ]]
    return true;
end;
return v3;
