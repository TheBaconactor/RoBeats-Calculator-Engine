-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:36 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Shaii\'s Cut";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v_u_1:define_as_hair(v4)
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, v8, v9 = v_u_1:create_accessory_base(p6, p5:get_name(), "HairAttachment", "rbxassetid://9424871017", "rbxassetid://9424871116")
    v7.AttachmentForward = Vector3.new(-0, 0, -1)
    v7.AttachmentPos = Vector3.new(-0.025, 0.385, 0.53)
    v7.AttachmentRight = Vector3.new(-1, 0, 0)
    v7.AttachmentUp = Vector3.new(0, 1, 0)
    v8.Orientation = Vector3.new(0, 0, 0)
    v8.Position = Vector3.new(0, 1.628, -0.419)
    v9.Offset = Vector3.new(0, 0, 0)
    v9.Scale = Vector3.new(1.1, 1.1, 1.1)
    v_u_1:attach_character_accessory(p6, v7)
    local v10, v11, v12 = v_u_1:create_accessory_base(p6, p5:get_name() .. "Accs", "HairAttachment", "rbxassetid://9424868330", "rbxassetid://9424868446")
    v10.AttachmentForward = Vector3.new(-0, 0, 1)
    v10.AttachmentPos = Vector3.new(-0.025, 0.385, 0.53)
    v10.AttachmentRight = Vector3.new(-1, 0, 0)
    v10.AttachmentUp = Vector3.new(0, 1, 0)
    v11.Orientation = Vector3.new(0, 0, 0)
    v11.Position = Vector3.new(-0.125, 0.232, 0.373)
    v12.Offset = Vector3.new(0, 0, 0)
    v12.Scale = Vector3.new(1.1, 1.1, 1.1)
    v_u_1:attach_character_accessory(p6, v10)
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 63 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 66 ]]
    return 2;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 69 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorPurple] = 12,
        [v_u_3.Type.ColorGreen] = 5,
        [v_u_3.Type.FeverTime] = 3,
        [v_u_3.Type.FeverMultiplier] = 4
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 77 ]]
    return "rbxassetid://9858814739";
end;
return v4;
