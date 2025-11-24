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
    return "Lisa\'s Beret";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, v8, v9 = v_u_1:create_accessory_base(p6, p5:get_name(), "HatAttachment", "rbxassetid://1683586254", "rbxassetid://1683704486")
    v9.Scale = Vector3.new(0.307, 0.305, 0.307)
    v8.Orientation = Vector3.new(-15, 15, -15)
    if v_u_1:character_has_hair(p6) then
        v8.Position = Vector3.new(0.15, -0.3, -0.15)
    else
        v8.Position = Vector3.new(0.15, -0.15, -0.15)
    end;
    v_u_1:attach_character_accessory(p6, v7)
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 37 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 40 ]]
    return 2;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 43 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorRed] = 4,
        [v_u_3.Type.ColorBlue] = 12,
        [v_u_3.Type.ComboMultiplier] = 4,
        [v_u_3.Type.FeverTime] = 3
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 51 ]]
    return "rbxassetid://8765628785";
end;
return v4;
