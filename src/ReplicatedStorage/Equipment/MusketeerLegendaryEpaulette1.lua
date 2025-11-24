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
    return "Legendary Musketeer\'s Epaulette";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.BACK;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, _, v8 = v_u_1:create_accessory_base(p6, p5:get_name(), "LeftShoulderRigAttachment", "rbxassetid://2465139337", "rbxassetid://2369512157")
    v8.Offset = Vector3.new(-0.6, 0.2, 0)
    v8.Scale = Vector3.new(0.011, 0.008, 0.011)
    v_u_1:attach_character_accessory(p6, v7)
    local v9, v10, v11 = v_u_1:create_accessory_base(p6, p5:get_name() .. "(Belt)", "WaistCenterAttachment", "rbxassetid://2465074677", "rbxassetid://2391139417")
    v11.Offset = Vector3.new(0.25, 0.25, 0)
    v11.Scale = Vector3.new(0.03, 0.025, 0.025)
    v10.CFrame = CFrame.Angles(0, 0, -0.785)
    v_u_1:attach_character_accessory(p6, v9)
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
        [v_u_3.Type.ColorPurple] = 13,
        [v_u_3.Type.ColorGreen] = 12,
        [v_u_3.Type.ComboMultiplier] = 6,
        [v_u_3.Type.PerfectPoints] = 4
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 62 ]]
    return "rbxassetid://2623570906";
end;
return v4;
