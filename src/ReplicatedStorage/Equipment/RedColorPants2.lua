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
    return "Legendary Rush Chieftan\'s Pants";
end;
v6.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 12 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.PANTS;
end;
v6.apply_appearance = function(p7, p8) --[[ Name: apply_appearance ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_5 ]]
    v_u_1:pants_base_apply(p8, "rbxassetid://5512745566")
    local v9, v10, v11 = v_u_1:create_accessory_base(p8, p7:get_name() .. "Belt", "WaistFrontAttachment", "rbxassetid://5536690404", "rbxassetid://5512745403")
    v9.AttachmentForward = Vector3.new(0, 0, -1)
    v9.AttachmentPos = Vector3.new(0, 0, 0)
    v9.AttachmentRight = Vector3.new(1, 0, 0)
    v9.AttachmentUp = Vector3.new(0, 1, 0)
    v10.Orientation = Vector3.new(0, 0, 0)
    v10.Position = Vector3.new(0, 0, 0)
    v11.Offset = Vector3.new(0, 0.1, 0.5)
    v11.Scale = Vector3.new(0.055, 0.05, 0.055)
    v_u_1:attach_character_accessory(p8, v9)
    local v12, v13, v14 = v_u_1:create_accessory_base(p8, p7:get_name() .. "Robe", "WaistFrontAttachment", "rbxassetid://5536690258", "rbxassetid://5512745073")
    v12.AttachmentForward = Vector3.new(0, 0, -1)
    v12.AttachmentPos = Vector3.new(0, 0, 0)
    v12.AttachmentRight = Vector3.new(1, 0, 0)
    v12.AttachmentUp = Vector3.new(0, 1, 0)
    v13.Orientation = Vector3.new(0, 0, 0)
    v13.Position = Vector3.new(0, 0, 0)
    v14.Offset = Vector3.new(0, -0.35, 0.5)
    v14.Scale = Vector3.new(0.07, 0.06, 0.07)
    v_u_1:attach_character_accessory(p8, v12)
    v_u_4:attach_color_particle(v_u_5.Red, p8)
end;
v6.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 65 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorRed] = 20,
        [v_u_3.Type.ColorGreen] = 8,
        [v_u_3.Type.PerfectPoints] = 6,
        [v_u_3.Type.ComboMultiplier] = 6
    };
end;
v6.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 73 ]]
    return 50;
end;
v6.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 76 ]]
    return 3;
end;
v6.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 79 ]]
    return "rbxassetid://5555604223";
end;
return v6;
