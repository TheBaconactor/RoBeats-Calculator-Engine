-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:39 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 7 ]]
    return "Cametek Fedora";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v4.apply_appearance = function(_, p5) --[[ Name: apply_appearance ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v6, v7, v8 = v_u_1:create_accessory_base(p5, "CametekFedora", "HatAttachment", "rbxassetid://5355967961", "http://www.roblox.com/asset/?id=5355543242")
    v6.AttachmentForward = Vector3.new(-0.0000000000000030299813, 0.00000000000000041444258, -1)
    v6.AttachmentPos = Vector3.new(0.00038551787, -0.12850475, -0.023304522)
    v6.AttachmentRight = Vector3.new(1, -0.0000000078713756, -0.0000000000000030299813)
    v6.AttachmentUp = Vector3.new(0.0000000078713756, 1, 0.00000000000000041444255)
    v7.Orientation = Vector3.new(0.00000000000002374581, 0.00000000000017360514, -0.00000045099657)
    v7.Position = Vector3.new(0.00043177995, -0.14392532, -0.026101062)
    v8.Offset = Vector3.new(0, 0, 0)
    v8.Scale = Vector3.new(1.05, 1.05, 1.05)
    v8.VertexColor = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p5, v6)
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 36 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorOrange] = 12,
        [v_u_3.Type.ColorRed] = 6,
        [v_u_3.Type.FeverFillRate] = 4,
        [v_u_3.Type.FeverTime] = 2
    };
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 44 ]]
    return 0;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 47 ]]
    return 2;
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 50 ]]
    return "rbxassetid://12361028915";
end;
return v4;
