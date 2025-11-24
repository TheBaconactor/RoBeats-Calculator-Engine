-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:25 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v5 = v_u_1:new()
v5.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Onii\'s Otaku Khakis";
end;
v5.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.PANTS;
end;
v5.apply_appearance = function(_, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    v_u_1:pants_base_apply(p6, "rbxassetid://325498710")
end;
v5.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 18 ]]
    return 25;
end;
v5.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 21 ]]
    return 1;
end;
v5.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 24 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3 ]]
    return v_u_4.ColorGearStatsEnabled == true and {
        [v_u_3.Type.ColorRed] = 6,
        [v_u_3.Type.ColorPurple] = 2,
        [v_u_3.Type.ComboMultiplier] = 5,
        [v_u_3.Type.PerfectPoints] = -1
    } or {
        [v_u_3.Type.ComboMultiplier] = 5,
        [v_u_3.Type.PerfectPoints] = -1
    };
end;
v5.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 39 ]]
    return "https://www.roblox.com/Thumbs/Asset.ashx?width=110&height=110&assetId=325498712";
end;
return v5;
