-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:39 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Birthday Alien\'s Hat";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v4.apply_appearance = function(_, p5) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v6, v7, v8 = v_u_1:create_accessory_base(p5, "BirthdayAlienHat", "HatAttachment", "http://www.roblox.com/asset/?id=35624672", "http://www.roblox.com/asset/?id=35624645")
    v6.AttachmentForward = Vector3.new(-0, -0, -1)
    v6.AttachmentPos = Vector3.new(0, -0.17, 0)
    v6.AttachmentRight = Vector3.new(1, 0, 0)
    v6.AttachmentUp = Vector3.new(0, 1, 0)
    v7.Orientation = Vector3.new(0.00000000000002374579, -0.00000000000000000000018691202, -0.00000045099657)
    v7.Position = Vector3.new(0.00000000865839, -0.07000017, -0.00027224422)
    v8.Offset = Vector3.new(0, 0, 0)
    v8.Scale = Vector3.new(1.03, 1.03, 1.03)
    v8.VertexColor = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p5, v6)
    local v9, v10, v11 = v_u_1:create_accessory_base(p5, "BirthdayPartyHat", "HatAttachment", "rbxassetid://9050541820", "rbxassetid://9050541858")
    v9.AttachmentForward = Vector3.new(-0, -0, -1)
    v9.AttachmentPos = Vector3.new(0, 0, 0)
    v9.AttachmentRight = Vector3.new(1, 0, 0)
    v9.AttachmentUp = Vector3.new(0, 1, 0)
    v10.Orientation = Vector3.new(0.0000000000017302217, -0.00000000000000000000000008836288, -0.0000000000029261105)
    v10.Position = Vector3.new(0.11325836, -0.5825882, 0.022720337)
    v11.Offset = Vector3.new(0, 0, 0)
    v11.Scale = Vector3.new(0.5, 0.5, 0.5)
    v11.VertexColor = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p5, v9)
    local _, _, v12, v13 = v_u_1:create_particle_emitter_accessory(p5, "HatAttachment", Vector3.new(2, 2, 0.05), "http://www.roblox.com/asset/?id=4780031979")
    v12.Color = ColorSequence.new({ ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 255, 255)), ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 255, 255)) })
    v12.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.25), NumberSequenceKeypoint.new(1, 0.25) })
    v12.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.5), NumberSequenceKeypoint.new(1, 1) })
    v12.EmissionDirection = Enum.NormalId.Back
    v12.ZOffset = 0
    v12.Acceleration = Vector3.new(0, 0, -0.05)
    v12.Drag = 0.5
    v12.Lifetime = NumberRange.new(1, 3)
    v12.Rate = 3
    v12.Rotation = NumberRange.new(0, 0)
    v12.RotSpeed = NumberRange.new(0, 0)
    v12.Speed = NumberRange.new(1, 2)
    v12.SpreadAngle = Vector2.new(0, 45)
    v12.Enabled = true
    v13.Enabled = false
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 95 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 98 ]]
    return 3;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 101 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorRed] = 14,
        [v_u_3.Type.ColorPurple] = 6,
        [v_u_3.Type.FeverTime] = 6
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 108 ]]
    return "rbxassetid://12719191963";
end;
return v4;
