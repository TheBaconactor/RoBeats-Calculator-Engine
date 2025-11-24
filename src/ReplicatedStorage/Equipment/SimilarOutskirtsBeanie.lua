-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:38 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 7 ]]
    return "Similar Outskirts Beanie";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v_u_1:define_as_hair(v4)
v4.apply_appearance = function(_, p5) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v6, v7, v8 = v_u_1:create_accessory_base(p5, "Hair", "HairAttachment", "rbxassetid://5049551885", "rbxassetid://8846474645")
    v6.AttachmentForward = Vector3.new(0.0000000000000030299813, 0.00000000000000041444258, 1)
    v6.AttachmentPos = Vector3.new(-0.043783188, 0.20209026, 0.03650093)
    v6.AttachmentRight = Vector3.new(-1, -0.0000000078713756, 0.0000000000000030299813)
    v6.AttachmentUp = Vector3.new(-0.0000000078713756, 1, -0.00000000000000041444255)
    v7.Orientation = Vector3.new(0.000000000000023719274, -180, -0.0000004515071)
    v7.Position = Vector3.new(-0.02331543, 0.18100071, 0.05557251)
    v8.Offset = Vector3.new(0, 0, 0)
    v8.Scale = Vector3.new(0.775, 0.7, 1.05)
    v8.VertexColor = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p5, v6)
    local v9, v10, v11 = v_u_1:create_accessory_base(p5, "Hat", "HairAttachment", "rbxassetid://8846517208", "rbxassetid://8842522525")
    v9.AttachmentForward = Vector3.new(-0, -0, -1)
    v9.AttachmentPos = Vector3.new(0, 0, 0)
    v9.AttachmentRight = Vector3.new(1, 0, 0)
    v9.AttachmentUp = Vector3.new(0, 1, 0)
    v10.Orientation = Vector3.new(-9.755785, 0.025510972, -0.1505524)
    v10.Position = Vector3.new(-0.000579834, -0.012371063, -0.20865631)
    v11.Offset = Vector3.new(0, 0, 0)
    v11.Scale = Vector3.new(0.097, 0.095, 0.1)
    v11.VertexColor = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p5, v9)
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 63 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorOrange] = 11,
        [v_u_3.Type.ColorBlue] = 7,
        [v_u_3.Type.FeverTime] = 3,
        [v_u_3.Type.FeverMultiplier] = 2
    };
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 71 ]]
    return 0;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 74 ]]
    return 2;
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 77 ]]
    return "rbxassetid://11716181076";
end;
return v4;
