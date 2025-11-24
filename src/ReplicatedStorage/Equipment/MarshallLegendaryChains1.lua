-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:23 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v5 = v_u_1:new()
v5.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Legendary Marshall\'s Chains";
end;
v5.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.NECK;
end;
v5.apply_appearance = function(p6, p7) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
    local v8, _, v9 = v_u_1:create_accessory_base(p7, p6:get_name(), v_u_2:slot_to_attachment_name(p6:get_avatar_slot()), "rbxassetid://2623436718", "rbxassetid://2369558491")
    v9.Offset = Vector3.new(0, -0.15, -0.15)
    v9.Scale = Vector3.new(0.729, 0.796, 0.85)
    v_u_1:attach_character_accessory(p7, v8)
end;
v5.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 30 ]]
    return 50;
end;
v5.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 33 ]]
    return 3;
end;
v5.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 36 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_3 ]]
    return v_u_4.ColorGearStatsEnabled == true and {
        [v_u_3.Type.ColorRed] = 12,
        [v_u_3.Type.ColorBlue] = 10,
        [v_u_3.Type.FeverMultiplier] = 7,
        [v_u_3.Type.FeverFillRate] = 5
    } or {
        [v_u_3.Type.FeverMultiplier] = 7,
        [v_u_3.Type.FeverFillRate] = 5,
        [v_u_3.Type.ComboMultiplier] = 2,
        [v_u_3.Type.PerfectPoints] = -2
    };
end;
v5.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 53 ]]
    return "rbxassetid://2623566362";
end;
return v5;
