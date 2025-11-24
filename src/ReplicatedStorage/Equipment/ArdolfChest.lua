-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:37 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Ardolf\'s Lycanthrope Scruff";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.SHIRT;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, v8, v9 = v_u_1:create_accessory_base(p6, p5:get_name() .. " (BodyFront)", "BodyFrontAttachment", "rbxassetid://10307078079", "rbxassetid://10307078624")
    v7.AttachmentForward = Vector3.new(-1, 0, 0)
    v7.AttachmentPos = Vector3.new(0, 0, 0)
    v7.AttachmentRight = Vector3.new(0, 0, -1)
    v7.AttachmentUp = Vector3.new(0, 1, 0)
    v8.Orientation = Vector3.new(0, 90, -0)
    v8.Position = Vector3.new(0.142, -0.329, 0)
    v9.Scale = Vector3.new(0.8, 0.8, 0.8)
    v_u_1:attach_character_accessory(p6, v7)
    local v10, v11, v12 = v_u_1:create_accessory_base(p6, p5:get_name() .. " (LeftUpperArm)", "LeftShoulderRigAttachment", "rbxassetid://10307086610", "rbxassetid://10307087586")
    v10.AttachmentForward = Vector3.new(-1, 0, 0)
    v10.AttachmentPos = Vector3.new(0, 0, 0)
    v10.AttachmentRight = Vector3.new(0, 0, -1)
    v10.AttachmentUp = Vector3.new(0, 1, 0)
    v11.Orientation = Vector3.new(0, 90, -0)
    v11.Position = Vector3.new(-0.003, 0.074, -0.399)
    v12.Scale = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p6, v10)
    local v13, v14, v15 = v_u_1:create_accessory_base(p6, p5:get_name() .. " (RightUpperArm)", "RightShoulderRigAttachment", "rbxassetid://10307090962", "rbxassetid://10307091498")
    v13.AttachmentForward = Vector3.new(-1, 0, 0)
    v13.AttachmentPos = Vector3.new(0, 0, 0)
    v13.AttachmentRight = Vector3.new(0, 0, -1)
    v13.AttachmentUp = Vector3.new(0, 1, 0)
    v14.Orientation = Vector3.new(0, 90, -0)
    v14.Position = Vector3.new(-0.023, 0.077, 0.356)
    v15.Scale = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p6, v13)
    v_u_1:shirt_base_apply(p6, "rbxassetid://10307271473")
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 81 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 84 ]]
    return 2;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 87 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorPurple] = 11,
        [v_u_3.Type.ColorOrange] = 6,
        [v_u_3.Type.FeverMultiplier] = 5
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 94 ]]
    return "rbxassetid://11184530126";
end;
return v4;
