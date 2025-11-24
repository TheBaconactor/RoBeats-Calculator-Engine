-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:35 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Slynk\'s Funky Fresh Jeans and Sneakers";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.PANTS;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, _, v8 = v_u_1:create_accessory_base(p6, p5:get_name() .. "(Right)", "RightAnkleRigAttachment", "rbxassetid://8309532478", "rbxassetid://8309532715")
    v8.Offset = Vector3.new(-0.075, -0.05, -0.2)
    v8.Scale = Vector3.new(0.03, 0.03, 0.035)
    v_u_1:attach_character_accessory(p6, v7)
    local v9, _, v10 = v_u_1:create_accessory_base(p6, p5:get_name() .. "(Left)", "LeftAnkleRigAttachment", "rbxassetid://8309532478", "rbxassetid://8309532715")
    v10.Offset = Vector3.new(0.075, -0.05, -0.2)
    v10.Scale = Vector3.new(0.03, 0.03, 0.035)
    v_u_1:attach_character_accessory(p6, v9)
    v_u_1:pants_base_apply(p6, "http://www.roblox.com/asset/?id=8309628749")
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 46 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 49 ]]
    return 2;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 52 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorGreen] = 11,
        [v_u_3.Type.ColorPurple] = 6,
        [v_u_3.Type.FeverMultiplier] = 2,
        [v_u_3.Type.FeverTime] = 3
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 60 ]]
    return "rbxassetid://8644451175";
end;
return v4;
