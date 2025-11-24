-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:35 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Slynk\'s Funky Fresh Hat";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v4.apply_appearance = function(_, p5) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v6, v7, v8, _ = v_u_1:create_accessory_base(p5, "SlynkHat", "HatAttachment", "rbxassetid://8277173462", "rbxassetid://8276953565")
    v6.AttachmentForward = Vector3.new(0, 0, -1)
    v6.AttachmentPos = Vector3.new(0, 0, 0)
    v6.AttachmentRight = Vector3.new(1, 0, 0)
    v6.AttachmentUp = Vector3.new(0, 1, 0)
    v7.Position = Vector3.new(0, 0, 0)
    v8.Offset = Vector3.new(0, 0.1, -0.25)
    v8.Scale = Vector3.new(0.04, 0.04, 0.04)
    v_u_1:attach_character_accessory(p5, v6)
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 37 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorGreen] = 10,
        [v_u_3.Type.ColorPurple] = 7,
        [v_u_3.Type.FeverMultiplier] = 3,
        [v_u_3.Type.FeverTime] = 2
    };
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 45 ]]
    return 25;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 48 ]]
    return 2;
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 51 ]]
    return "rbxassetid://8644450979";
end;
return v4;
