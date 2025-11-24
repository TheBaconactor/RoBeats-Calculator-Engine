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
    return "UNDEAD CORPORATION Akemi\'s Hair";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v_u_1:define_as_hair(v4)
v4.apply_appearance = function(_, p5) --[[ Name: apply_appearance ]] --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v6, v7, v8 = v_u_1:create_accessory_base(p5, "Hair", "HairAttachment", "rbxassetid://9521996140", "rbxassetid://9521996200")
    v6.AttachmentForward = Vector3.new(-0, -0.0000000004527898, 1)
    v6.AttachmentPos = Vector3.new(-0.025307655, 0.38478637, 0.5301056)
    v6.AttachmentRight = Vector3.new(-1, 0, 0)
    v6.AttachmentUp = Vector3.new(0, 1, -0.0000000004669395)
    v7.Orientation = Vector3.new(0.000000000000101777744, -89.99999, 0)
    v7.Position = Vector3.new(0, 0.8639393, 0)
    v8.Offset = Vector3.new(0, 0, 0)
    v8.Scale = Vector3.new(1.1, 1.1, 1.1)
    v8.VertexColor = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p5, v6)
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 40 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 43 ]]
    return 2;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 46 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorOrange] = 17,
        [v_u_3.Type.FeverMultiplier] = 5
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 52 ]]
    return "rbxassetid://14207858506";
end;
return v4;
