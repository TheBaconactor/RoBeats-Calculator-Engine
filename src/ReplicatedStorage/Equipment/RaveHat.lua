-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:41 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 7 ]]
    return "Party Mode: Rave Hat!";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v4.apply_appearance = function(_, p5) --[[ Name: apply_appearance ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v6, v7, v8 = v_u_1:create_accessory_base(p5, "RaveHat", "HatAttachment", "rbxassetid://11831658166", "rbxassetid://11831658403")
    v6.AttachmentForward = Vector3.new(1, 0.00000000000000041444258, -0.0000000000000030299813)
    v6.AttachmentPos = Vector3.new(0.09662676, 1.976692, -0.009363174)
    v6.AttachmentRight = Vector3.new(0.0000000000000030299813, -0.0000000078713756, 1)
    v6.AttachmentUp = Vector3.new(-0.00000000000000041444255, 1, 0.0000000078713756)
    v7.Orientation = Vector3.new(-0.000000000000000000100096034, 90, 0.000000000000000000003017629)
    v7.Position = Vector3.new(0, -0.17989159, 0)
    v8.Offset = Vector3.new(0, 0, 0)
    v8.Scale = Vector3.new(1.15, 1.15, 1.15)
    v8.VertexColor = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p5, v6)
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 36 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorBlue] = 15,
        [v_u_3.Type.ColorRed] = 4,
        [v_u_3.Type.ComboMultiplier] = 4
    };
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 43 ]]
    return 35;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 46 ]]
    return 3;
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 49 ]]
    return "rbxassetid://14827926615";
end;
return v4;
