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
    return "Legendary Marshall\'s Mask";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.FACE;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
    local v7, _, v8 = v_u_1:create_accessory_base(p6, p5:get_name(), v_u_2:slot_to_attachment_name(p5:get_avatar_slot()), "rbxassetid://2623385779", "rbxassetid://2307337722")
    v8.Offset = Vector3.new(0, 0.15, 0.09)
    v8.Scale = Vector3.new(0.14, 0.14, 0.14)
    v_u_1:attach_character_accessory(p6, v7)
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 28 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 31 ]]
    return 3;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 34 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorRed] = 14,
        [v_u_3.Type.ColorBlue] = 7,
        [v_u_3.Type.FeverMultiplier] = 7,
        [v_u_3.Type.FeverFillRate] = 6
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 42 ]]
    return "rbxassetid://2623566549";
end;
return v4;
