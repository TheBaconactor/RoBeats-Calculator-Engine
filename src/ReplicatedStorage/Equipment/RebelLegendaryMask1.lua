-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:24 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Legendary Rebel\'s Mask";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.FACE;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
    local v7, _, v8 = v_u_1:create_accessory_base(p6, p5:get_name(), v_u_2:slot_to_attachment_name(p5:get_avatar_slot()), "rbxassetid://2623375507", "rbxassetid://2307346890")
    v8.Offset = Vector3.new(0, 0.1, 0.1)
    v8.Scale = Vector3.new(0.096, 0.096, 0.096)
    v_u_1:attach_character_accessory(p6, v7)
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 31 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 34 ]]
    return 3;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 37 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorOrange] = 13,
        [v_u_3.Type.ColorBlue] = 8,
        [v_u_3.Type.PerfectPoints] = 13,
        [v_u_3.Type.PerfectTime] = 1
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 45 ]]
    return "rbxassetid://2623560901";
end;
return v4;
