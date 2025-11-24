-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:24 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Legendary Musketeer\'s Trousers";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.PANTS;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, _, v8 = v_u_1:create_accessory_base(p6, p5:get_name() .. "(Right)", "RightAnkleRigAttachment", "rbxassetid://2621418830", "rbxassetid://2369515399")
    v8.Offset = Vector3.new(0, 0.125, -0.4)
    v8.Scale = Vector3.new(0.375, 0.225, 0.405)
    v_u_1:attach_character_accessory(p6, v7)
    local v9, _, v10 = v_u_1:create_accessory_base(p6, p5:get_name() .. "(Left)", "LeftAnkleRigAttachment", "rbxassetid://2621418830", "rbxassetid://2369515399")
    v10.Offset = Vector3.new(0, 0.125, -0.4)
    v10.Scale = Vector3.new(0.375, 0.225, 0.405)
    v_u_1:attach_character_accessory(p6, v9)
    v_u_1:pants_base_apply(p6, "rbxassetid://2621466036")
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 50 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 53 ]]
    return 3;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 56 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorPurple] = 14,
        [v_u_3.Type.ColorGreen] = 13,
        [v_u_3.Type.ComboMultiplier] = 9,
        [v_u_3.Type.FeverMultiplier] = 3
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 64 ]]
    return "rbxassetid://2623570847";
end;
return v4;
