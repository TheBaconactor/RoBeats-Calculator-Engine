-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:23 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Legendary Marshall\'s Shoulderpads";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.BACK;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, _, v8 = v_u_1:create_accessory_base(p6, p5:get_name() .. "(Left)", "LeftShoulderRigAttachment", "rbxassetid://2623403554", "rbxassetid://2369558491")
    v8.Offset = Vector3.new(-0.5, 0.5, 0)
    v8.Scale = Vector3.new(0.5, 0.65, 0.55)
    v_u_1:attach_character_accessory(p6, v7)
    local v9, v10, v11 = v_u_1:create_accessory_base(p6, p5:get_name() .. "(Right)", "RightShoulderRigAttachment", "rbxassetid://2623403554", "rbxassetid://2369558491")
    v11.Offset = Vector3.new(-0.5, 0.5, 0)
    v11.Scale = Vector3.new(0.5, 0.65, 0.55)
    v10.CFrame = CFrame.Angles(0, 3.14, 0)
    v_u_1:attach_character_accessory(p6, v9)
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 47 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 50 ]]
    return 3;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 53 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorRed] = 12,
        [v_u_3.Type.ColorBlue] = 12,
        [v_u_3.Type.FeverMultiplier] = 6,
        [v_u_3.Type.FeverFillRate] = 5
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 61 ]]
    return "rbxassetid://2623566496";
end;
return v4;
