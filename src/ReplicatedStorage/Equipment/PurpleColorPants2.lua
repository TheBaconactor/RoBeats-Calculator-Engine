-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:30 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_4 = require(game.ReplicatedStorage.Avatar.ColorGearParticles)
local v_u_5 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v6 = v_u_1:new()
v6.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 9 ]]
    return "Legendary Flow Commander\'s Jumpsuit Pants";
end;
v6.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 12 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.PANTS;
end;
v6.apply_appearance = function(p7, p8) --[[ Name: apply_appearance ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_5 ]]
    v_u_1:pants_base_apply(p8, "rbxassetid://5513008480")
    local v9, v10, v11 = v_u_1:create_accessory_base(p8, p7:get_name() .. "LegLeft", "LeftAnkleRigAttachment", "rbxassetid://5263362019", "rbxassetid://5513008409")
    v9.AttachmentForward = Vector3.new(0, 0, -1)
    v9.AttachmentPos = Vector3.new(0, 0, 0)
    v9.AttachmentRight = Vector3.new(1, 0, 0)
    v9.AttachmentUp = Vector3.new(0, 1, 0)
    v10.Orientation = Vector3.new(0, 0, 0)
    v10.Position = Vector3.new(0, 0, 0)
    v11.Offset = Vector3.new(0, 0.65, -0.1)
    v11.Scale = Vector3.new(0.03, 0.025, 0.03)
    v_u_1:attach_character_accessory(p8, v9)
    local v12, v13, v14 = v_u_1:create_accessory_base(p8, p7:get_name() .. "LegRight", "RightAnkleRigAttachment", "rbxassetid://5263362019", "rbxassetid://5513008409")
    v12.AttachmentForward = Vector3.new(0, 0, -1)
    v12.AttachmentPos = Vector3.new(0, 0, 0)
    v12.AttachmentRight = Vector3.new(1, 0, 0)
    v12.AttachmentUp = Vector3.new(0, 1, 0)
    v13.Orientation = Vector3.new(0, 0, 0)
    v13.Position = Vector3.new(0, 0, 0)
    v14.Offset = Vector3.new(0, 0.65, -0.1)
    v14.Scale = Vector3.new(0.03, 0.025, 0.03)
    v_u_1:attach_character_accessory(p8, v12)
    v_u_4:attach_color_particle(v_u_5.Purple, p8)
end;
v6.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 59 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorPurple] = 19,
        [v_u_3.Type.ColorBlue] = 11,
        [v_u_3.Type.FeverMultiplier] = 9
    };
end;
v6.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 66 ]]
    return 50;
end;
v6.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 69 ]]
    return 3;
end;
v6.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 72 ]]
    return "rbxassetid://5555603374";
end;
return v6;
