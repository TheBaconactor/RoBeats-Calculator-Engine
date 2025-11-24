-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:28 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 7 ]]
    return "Rush Chieftan\'s Garb";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.SHIRT;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    v_u_1:shirt_base_apply(p6, "rbxassetid://5512745647")
    local v7, v8, v9 = v_u_1:create_accessory_base(p6, p5:get_name() .. "ShoulderLeft", "LeftShoulderRigAttachment", "rbxassetid://5536678223", "rbxassetid://5512745229")
    v7.AttachmentForward = Vector3.new(0, 0, -1)
    v7.AttachmentPos = Vector3.new(0, 0, 0)
    v7.AttachmentRight = Vector3.new(1, 0, 0)
    v7.AttachmentUp = Vector3.new(0, 1, 0)
    v8.Orientation = Vector3.new(0, 0, 45)
    v8.Position = Vector3.new(0, 0, 0)
    v9.Offset = Vector3.new(-0.35, -0.15, 0)
    v9.Scale = Vector3.new(0.035, 0.035, 0.035)
    v_u_1:attach_character_accessory(p6, v7)
    local v10, v11, v12 = v_u_1:create_accessory_base(p6, p5:get_name() .. "ShoulderRight", "RightShoulderRigAttachment", "rbxassetid://5536678223", "rbxassetid://5512745229")
    v10.AttachmentForward = Vector3.new(0, 0, -1)
    v10.AttachmentPos = Vector3.new(0, 0, 0)
    v10.AttachmentRight = Vector3.new(1, 0, 0)
    v10.AttachmentUp = Vector3.new(0, 1, 0)
    v11.Orientation = Vector3.new(0, 0, -45)
    v11.Position = Vector3.new(0, 0, 0)
    v12.Offset = Vector3.new(0.22, -0.1, 0)
    v12.Scale = Vector3.new(0.035, 0.035, 0.035)
    v_u_1:attach_character_accessory(p6, v10)
    local v13, v14, v15 = v_u_1:create_accessory_base(p6, p5:get_name() .. "HandLeft", "LeftWristRigAttachment", "rbxassetid://5536678223", "rbxassetid://5512745229")
    v13.AttachmentForward = Vector3.new(0, 0, -1)
    v13.AttachmentPos = Vector3.new(0, 0, 0)
    v13.AttachmentRight = Vector3.new(1, 0, 0)
    v13.AttachmentUp = Vector3.new(0, 1, 0)
    v14.Orientation = Vector3.new(0, 0, 0)
    v14.Position = Vector3.new(0, 0, 0)
    v15.Offset = Vector3.new(0, 0.25, 0)
    v15.Scale = Vector3.new(0.03, 0.03, 0.03)
    v_u_1:attach_character_accessory(p6, v13)
    local v16, v17, v18 = v_u_1:create_accessory_base(p6, p5:get_name() .. "HandRight", "RightWristRigAttachment", "rbxassetid://5536678223", "rbxassetid://5512745229")
    v16.AttachmentForward = Vector3.new(0, 0, -1)
    v16.AttachmentPos = Vector3.new(0, 0, 0)
    v16.AttachmentRight = Vector3.new(1, 0, 0)
    v16.AttachmentUp = Vector3.new(0, 1, 0)
    v17.Orientation = Vector3.new(0, 0, 0)
    v17.Position = Vector3.new(0, 0, 0)
    v18.Offset = Vector3.new(0, 0.25, 0)
    v18.Scale = Vector3.new(0.03, 0.03, 0.03)
    v_u_1:attach_character_accessory(p6, v16)
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 106 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorRed] = 15,
        [v_u_3.Type.ColorGreen] = 7,
        [v_u_3.Type.PerfectPoints] = 4,
        [v_u_3.Type.ComboMultiplier] = 4
    };
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 114 ]]
    return 35;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 117 ]]
    return 2;
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 120 ]]
    return "rbxassetid://5555604313";
end;
return v4;
