-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:40 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "garlagan\'s t0y0u Mask";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.FACE;
end;
v4.apply_appearance = function(_, p5) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v6, v7, v8 = v_u_1:create_accessory_base(p5, "GarlaganMask", "FaceCenterAttachment", "rbxassetid://9599546153", "rbxassetid://9548146288")
    v6.AttachmentForward = Vector3.new(-0.0000000000000030299813, 0.00000000000000041444258, -1)
    v6.AttachmentPos = Vector3.new(-0.00010681152, 0.030453205, 0.02331543)
    v6.AttachmentRight = Vector3.new(1, -0.0000000078713756, -0.0000000000000030299813)
    v6.AttachmentUp = Vector3.new(0.0000000078713756, 1, 0.00000000000000041444255)
    v7.Orientation = Vector3.new(0.00000000000002374578, -0.00000000000000000000018691195, -0.00000045099657)
    v7.Position = Vector3.new(0, -0.69739914, 0)
    v8.Offset = Vector3.new(0, 0, 0)
    v8.Scale = Vector3.new(0.75, 0.75, 0.75)
    v8.VertexColor = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p5, v6)
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 38 ]]
    return 25;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 41 ]]
    return 2;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 44 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorRed] = 12,
        [v_u_3.Type.ColorPurple] = 6,
        [v_u_3.Type.ComboMultiplier] = 4
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 51 ]]
    return "rbxassetid://13991399201";
end;
return v4;
