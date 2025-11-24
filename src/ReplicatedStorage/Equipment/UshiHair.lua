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
    return "Ushi-chan\'s Horns";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v_u_1:define_as_hair(v4)
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, v8, v9 = v_u_1:create_accessory_base(p6, p5:get_name(), "HairAttachment", "rbxassetid://11110142800", "rbxassetid://9947722589")
    v7.Name = "Hair"
    v7.AttachmentForward = Vector3.new(-1, 0, 0)
    v7.AttachmentPos = Vector3.new(0, 0, 0)
    v7.AttachmentRight = Vector3.new(-0, -0, -1)
    v7.AttachmentUp = Vector3.new(0, 1, 0)
    v8.Orientation = Vector3.new(-0, -180, 0)
    v8.Position = Vector3.new(0.008, 0.473, 0.027)
    v9.Offset = Vector3.new(0, 0, 0)
    v9.Scale = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p6, v7)
    local v10, v11, v12 = v_u_1:create_accessory_base(p6, p5:get_name(), "HairAttachment", "rbxassetid://9947723714", "rbxassetid://9947723941")
    v10.Name = "Horns"
    v10.AttachmentForward = Vector3.new(-1, 0, 0)
    v10.AttachmentPos = Vector3.new(0, 0, 0)
    v10.AttachmentRight = Vector3.new(-0, -0, -1)
    v10.AttachmentUp = Vector3.new(0, 1, 0)
    v11.Orientation = Vector3.new(-0, 0, 0)
    v11.Position = Vector3.new(-0.04, 0, 0)
    v12.Offset = Vector3.new(0, 0, 0)
    v12.Scale = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p6, v10)
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 65 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 68 ]]
    return 2;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 71 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorOrange] = 12,
        [v_u_3.Type.ColorGreen] = 5,
        [v_u_3.Type.ComboMultiplier] = 3,
        [v_u_3.Type.FeverMultiplier] = 3
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 79 ]]
    return "rbxassetid://11110892197";
end;
return v4;
