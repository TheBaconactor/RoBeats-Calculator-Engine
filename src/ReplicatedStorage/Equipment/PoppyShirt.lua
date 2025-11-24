-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:33 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Poppy\'s Flux Shirt";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.SHIRT;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, v8, v9, _ = v_u_1:create_accessory_base(p6, p5:get_name() .. " (UpperTorso)", "BodyFrontAttachment", "rbxassetid://7523103733", "rbxassetid://7523103786")
    v9.Offset = Vector3.new(0, 0.3, -0.35)
    v9.Scale = Vector3.new(1.25, 1.25, 1.25)
    v8.Orientation = Vector3.new(0, -180, 0)
    v8.Position = Vector3.new(0.027, 0.301, -0.039)
    v_u_1:attach_character_accessory(p6, v7)
    local v10, v11, v12, _ = v_u_1:create_accessory_base(p6, p5:get_name() .. " (UpperLeftArm)", "LeftShoulderRigAttachment", "rbxassetid://7523102980", "rbxassetid://7523103096")
    v12.Offset = Vector3.new(0.35, 0, 0)
    v12.Scale = Vector3.new(1.1, 1.1, 1.1)
    v11.Orientation = Vector3.new(0, -180, 0)
    v11.Position = Vector3.new(0.027, 0.301, -0.039)
    v_u_1:attach_character_accessory(p6, v10)
    local v13, v14, v15, _ = v_u_1:create_accessory_base(p6, p5:get_name() .. " (LowerLeftArm)", "LeftElbowRigAttachment", "rbxassetid://7523103226", "rbxassetid://7523103304")
    v15.Offset = Vector3.new(0.25, 0, 0)
    v15.Scale = Vector3.new(1.1, 1.1, 1.1)
    v14.Orientation = Vector3.new(0, -180, 0)
    v14.Position = Vector3.new(0.027, 0.301, -0.039)
    v_u_1:attach_character_accessory(p6, v13)
    local v16, v17, v18, _ = v_u_1:create_accessory_base(p6, p5:get_name() .. " (UpperRightArm)", "RightShoulderRigAttachment", "rbxassetid://7523102980", "rbxassetid://7523103096")
    v18.Offset = Vector3.new(0.35, 0, 0)
    v18.Scale = Vector3.new(1.1, 1.1, 1.1)
    v17.Orientation = Vector3.new(0, 0, 0)
    v17.Position = Vector3.new(0.027, 0.301, -0.039)
    v_u_1:attach_character_accessory(p6, v16)
    local v19, v20, v21, _ = v_u_1:create_accessory_base(p6, p5:get_name() .. " (LowerRightArm)", "RightElbowRigAttachment", "rbxassetid://7523103226", "rbxassetid://7523103304")
    v21.Offset = Vector3.new(0.25, 0, 0)
    v21.Scale = Vector3.new(1.1, 1.1, 1.1)
    v20.Orientation = Vector3.new(0, 0, 0)
    v20.Position = Vector3.new(0.027, 0.301, -0.039)
    v_u_1:attach_character_accessory(p6, v19)
    v_u_1:shirt_base_apply(p6, "rbxassetid://7522788108")
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 113 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 116 ]]
    return 3;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 119 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorPurple] = 10,
        [v_u_3.Type.ColorRed] = 5,
        [v_u_3.Type.PerfectPoints] = 6,
        [v_u_3.Type.PerfectTime] = 1
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 127 ]]
    return "http://www.roblox.com/asset/?id=7534852273";
end;
return v4;
