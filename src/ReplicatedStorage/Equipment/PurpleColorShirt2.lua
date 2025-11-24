-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:31 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_4 = require(game.ReplicatedStorage.Avatar.ColorGearParticles)
local v_u_5 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v6 = v_u_1:new()
v6.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 9 ]]
    return "Legendary Flow Commander\'s Jumpsuit";
end;
v6.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 12 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.SHIRT;
end;
v6.apply_appearance = function(p7, p8) --[[ Name: apply_appearance ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_5 ]]
    v_u_1:shirt_base_apply(p8, "rbxassetid://5513008562")
    local v9, v10, v11 = v_u_1:create_accessory_base(p8, p7:get_name() .. "ShoulderLeft", "LeftShoulderRigAttachment", "rbxassetid://5263376872", "rbxassetid://5513008651")
    v9.AttachmentForward = Vector3.new(0, 0, -1)
    v9.AttachmentPos = Vector3.new(0, 0, 0)
    v9.AttachmentRight = Vector3.new(1, 0, 0)
    v9.AttachmentUp = Vector3.new(0, 1, 0)
    v10.Orientation = Vector3.new(0, 0, 0)
    v10.Position = Vector3.new(0, 0, 0)
    v11.Offset = Vector3.new(-0.5, 0.175, 0)
    v11.Scale = Vector3.new(0.03, 0.045, 0.05)
    v_u_1:attach_character_accessory(p8, v9)
    local v12, v13, v14 = v_u_1:create_accessory_base(p8, p7:get_name() .. "ShoulderRight", "RightShoulderRigAttachment", "rbxassetid://5263376872", "rbxassetid://5513008651")
    v12.AttachmentForward = Vector3.new(0, 0, -1)
    v12.AttachmentPos = Vector3.new(0, 0, 0)
    v12.AttachmentRight = Vector3.new(1, 0, 0)
    v12.AttachmentUp = Vector3.new(0, 1, 0)
    v13.Orientation = Vector3.new(-0, 180, -0)
    v13.Position = Vector3.new(0, 0, 0)
    v14.Offset = Vector3.new(-0.5, 0.175, 0)
    v14.Scale = Vector3.new(0.03, 0.045, 0.05)
    v_u_1:attach_character_accessory(p8, v12)
    local v15, v16, v17 = v_u_1:create_accessory_base(p8, p7:get_name() .. "HandLeft", "LeftWristRigAttachment", "rbxassetid://5263322788", "rbxassetid://5513008134")
    v15.AttachmentForward = Vector3.new(0, 0, -1)
    v15.AttachmentPos = Vector3.new(0, 0, 0)
    v15.AttachmentRight = Vector3.new(1, 0, 0)
    v15.AttachmentUp = Vector3.new(0, 1, 0)
    v16.Orientation = Vector3.new(-0, 0, -0)
    v16.Position = Vector3.new(0, 0, 0)
    v17.Offset = Vector3.new(0, 0.25, 0)
    v17.Scale = Vector3.new(0.03, 0.013, 0.03)
    v_u_1:attach_character_accessory(p8, v15)
    local v18, v19, v20 = v_u_1:create_accessory_base(p8, p7:get_name() .. "HandRight", "RightWristRigAttachment", "rbxassetid://5263322788", "rbxassetid://5513008134")
    v18.AttachmentForward = Vector3.new(0, 0, -1)
    v18.AttachmentPos = Vector3.new(0, 0, 0)
    v18.AttachmentRight = Vector3.new(1, 0, 0)
    v18.AttachmentUp = Vector3.new(0, 1, 0)
    v19.Orientation = Vector3.new(-0, 0, -0)
    v19.Position = Vector3.new(0, 0, 0)
    v20.Offset = Vector3.new(0, 0.25, 0)
    v20.Scale = Vector3.new(0.03, 0.013, 0.03)
    v_u_1:attach_character_accessory(p8, v18)
    v_u_4:attach_color_particle(v_u_5.Purple, p8)
end;
v6.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 107 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorPurple] = 21,
        [v_u_3.Type.ColorBlue] = 10,
        [v_u_3.Type.FeverMultiplier] = 8
    };
end;
v6.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 114 ]]
    return 50;
end;
v6.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 117 ]]
    return 3;
end;
v6.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 120 ]]
    return "rbxassetid://5555603444";
end;
return v6;
