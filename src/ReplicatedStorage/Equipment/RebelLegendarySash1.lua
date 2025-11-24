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
    return "Legendary Rebel\'s Sash";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.BACK;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, v8, v9 = v_u_1:create_accessory_base(p6, p5:get_name(), "BodyFrontAttachment", "rbxassetid://2621357267", "rbxassetid://2369509812")
    v9.Offset = Vector3.new(-0.1, 0.15, 0.5)
    v9.Scale = Vector3.new(0.8, 0.8, 1.1)
    v8.CFrame = CFrame.Angles(0, 0, 0.785)
    v_u_1:attach_character_accessory(p6, v7)
    local v10, _, v11 = v_u_1:create_accessory_base(p6, p5:get_name() .. "(Belt)", "WaistCenterAttachment", "rbxassetid://2391146336", "rbxassetid://2391164652")
    v11.Offset = Vector3.new(0, 0.2, 0)
    v11.Scale = Vector3.new(0.014, 0.014, 0.014)
    v_u_1:attach_character_accessory(p6, v10)
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 48 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 51 ]]
    return 3;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 54 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorOrange] = 13,
        [v_u_3.Type.ColorBlue] = 11,
        [v_u_3.Type.PerfectPoints] = 11,
        [v_u_3.Type.FeverMultiplier] = 3
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 62 ]]
    return "rbxassetid://2623560782";
end;
return v4;
