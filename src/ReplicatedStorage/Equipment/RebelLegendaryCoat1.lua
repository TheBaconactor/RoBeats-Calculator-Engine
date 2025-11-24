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
    return "Legendary Rebel\'s Coat";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.SHIRT;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, _, v8 = v_u_1:create_accessory_base(p6, p5:get_name(), "BodyFrontAttachment", "rbxassetid://2491044811", "rbxassetid://2491032092")
    v8.Offset = Vector3.new(0, -0.6, 0.6)
    v8.Scale = Vector3.new(0.035, 0.035, 0.038)
    v_u_1:attach_character_accessory(p6, v7)
    local v9, _, v10 = v_u_1:create_accessory_base(p6, p5:get_name() .. "(Left)", "LeftWristRigAttachment", "rbxassetid://2465220955", "rbxassetid://2391164333")
    v10.Offset = Vector3.new(0, 0.25, 0)
    v10.Scale = Vector3.new(0.023, 0.01, 0.023)
    v_u_1:attach_character_accessory(p6, v9)
    local v11, _, v12 = v_u_1:create_accessory_base(p6, p5:get_name() .. "(Right)", "RightWristRigAttachment", "rbxassetid://2465220955", "rbxassetid://2391164333")
    v12.Offset = Vector3.new(0, 0.25, 0)
    v12.Scale = Vector3.new(0.023, 0.01, 0.023)
    v_u_1:attach_character_accessory(p6, v11)
    v_u_1:shirt_base_apply(p6, "rbxassetid://2621400312")
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 63 ]]
    return 50;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 66 ]]
    return 3;
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 69 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorOrange] = 14,
        [v_u_3.Type.ColorBlue] = 14,
        [v_u_3.Type.PerfectPoints] = 10,
        [v_u_3.Type.PerfectTime] = 2
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 77 ]]
    return "rbxassetid://2623560739";
end;
return v4;
