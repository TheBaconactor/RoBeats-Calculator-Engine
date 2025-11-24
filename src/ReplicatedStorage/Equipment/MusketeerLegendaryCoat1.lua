-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:23 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Legendary Musketeer\'s Coat";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.SHIRT;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, _, v8 = v_u_1:create_accessory_base(p6, p5:get_name(), "BodyFrontAttachment", "rbxassetid://2487387385", "rbxassetid://2487391944")
    v8.Offset = Vector3.new(0, -0.6, 0.5)
    v8.Scale = Vector3.new(0.038, 0.037, 0.04)
    v_u_1:attach_character_accessory(p6, v7)
    local v9, _, v10 = v_u_1:create_accessory_base(p6, p5:get_name() .. "(Left)", "LeftWristRigAttachment", "rbxassetid://2621418585", "rbxassetid://2391139901")
    v10.Offset = Vector3.new(0, -0.25, 0)
    v10.Scale = Vector3.new(0.6, 0.22, 0.6)
    v_u_1:attach_character_accessory(p6, v9)
    local v11, _, v12 = v_u_1:create_accessory_base(p6, p5:get_name() .. "(Right)", "RightWristRigAttachment", "rbxassetid://2621418585", "rbxassetid://2391139901")
    v12.Offset = Vector3.new(0, -0.25, 0)
    v12.Scale = Vector3.new(0.6, 0.22, 0.6)
    v_u_1:attach_character_accessory(p6, v11)
    v_u_1:shirt_base_apply(p6, "rbxassetid://2487396831")
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 65 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 68 ]]
    return 3;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 71 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorPurple] = 14,
        [v_u_3.Type.ColorGreen] = 13,
        [v_u_3.Type.ComboMultiplier] = 10,
        [v_u_3.Type.PerfectTime] = 2
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 79 ]]
    return "rbxassetid://2623571119";
end;
return v4;
