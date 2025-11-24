-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:32 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Poppy\'s Flux Dress";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.PANTS;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, v8, v9, _ = v_u_1:create_accessory_base(p6, p5:get_name() .. "(LowerTorso)", "WaistCenterAttachment", "rbxassetid://7523101067", "rbxassetid://7523101311")
    v9.Offset = Vector3.new(0, 0, 0)
    v9.Scale = Vector3.new(1.2, 1.2, 1.2)
    v8.Orientation = Vector3.new(0, -180, 0)
    v8.Position = Vector3.new(0.027, 0.301, -0.039)
    v_u_1:attach_character_accessory(p6, v7)
    v_u_1:pants_base_apply(p6, "rbxassetid://7522772100")
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 37 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 40 ]]
    return 3;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 43 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorPurple] = 10,
        [v_u_3.Type.ColorRed] = 6,
        [v_u_3.Type.PerfectPoints] = 6,
        [v_u_3.Type.PerfectTime] = 1
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 51 ]]
    return "http://www.roblox.com/asset/?id=7534852738";
end;
return v4;
