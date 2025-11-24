-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:33 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 7 ]]
    return "Creo\'s Hoodie";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.SHIRT;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    v_u_1:shirt_base_apply(p6, "http://www.roblox.com/asset/?id=6166083608")
    local v7, v8, v9 = v_u_1:create_accessory_base(p6, p5:get_name(), "NeckAttachment", "rbxassetid://4179850886", "http://www.roblox.com/asset/?id=5577154733")
    v8.Orientation = Vector3.new(0, 0, 0)
    v8.Position = Vector3.new(-0, 0.546, -0.319)
    v9.Offset = Vector3.new(0, 0, 0)
    v9.Scale = Vector3.new(0.884, 1.061, 1.004)
    v_u_1:attach_character_accessory(p6, v7)
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 38 ]]
    return 35;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 41 ]]
    return 2;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 44 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorBlue] = 10,
        [v_u_3.Type.ColorRed] = 7,
        [v_u_3.Type.PerfectPoints] = 4,
        [v_u_3.Type.ComboMultiplier] = 3
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 52 ]]
    return "rbxassetid://10782177794";
end;
return v4;
