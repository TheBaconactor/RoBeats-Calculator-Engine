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
    return "Legendary Rush Chieftan\'s Hat";
end;
v6.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 12 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v6.apply_appearance = function(p7, p8) --[[ Name: apply_appearance ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): v_u_5 ]]
    local v9, v10, v11 = v_u_1:create_accessory_base(p8, p7:get_name(), v_u_2:slot_to_attachment_name(p7:get_avatar_slot()), "rbxassetid://4502956312", "http://www.roblox.com/asset/?id=4502956625")
    v9.AttachmentForward = Vector3.new(0, 0, -1)
    v9.AttachmentPos = Vector3.new(0, 0, 0)
    v9.AttachmentRight = Vector3.new(1, 0, 0)
    v9.AttachmentUp = Vector3.new(0, 1, 0)
    v10.Orientation = Vector3.new(0, 0, 0)
    v10.Position = Vector3.new(0, 0.417, 0)
    v11.Offset = Vector3.new(0, 0, 0)
    v11.Scale = Vector3.new(0.969, 0.983, 0.969)
    v_u_1:attach_character_accessory(p8, v9)
    v_u_4:attach_color_particle(v_u_5.Red, p8)
end;
v6.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 38 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorRed] = 16,
        [v_u_3.Type.ColorGreen] = 9,
        [v_u_3.Type.PerfectPoints] = 4,
        [v_u_3.Type.ComboMultiplier] = 6
    };
end;
v6.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 46 ]]
    return 50;
end;
v6.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 49 ]]
    return 3;
end;
v6.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 52 ]]
    return "rbxassetid://5555604123";
end;
return v6;
