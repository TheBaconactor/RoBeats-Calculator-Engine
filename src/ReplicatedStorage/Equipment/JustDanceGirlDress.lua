-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:34 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 7 ]]
    return "Just Dance Coach\'s Stockings";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.PANTS;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    v_u_1:pants_base_apply(p6, "rbxassetid://7971204399")
    local v7, v8, v9 = v_u_1:create_accessory_base(p6, p5:get_name(), "WaistCenterAttachment", "rbxassetid://7959082449", "rbxassetid://7959082490")
    v7.AttachmentForward = Vector3.new(0, 0, -1)
    v7.AttachmentPos = Vector3.new(0.024, 0.301, -0.04)
    v7.AttachmentRight = Vector3.new(1, 0, 0)
    v7.AttachmentUp = Vector3.new(0, 1, 0)
    v8.Orientation = Vector3.new(0, -180, 0)
    v8.Position = Vector3.new(0.027, 0.301, -0.039)
    v9.Offset = Vector3.new(0, 0.15, 0)
    v9.Scale = Vector3.new(1.25, 1.25, 1.25)
    v_u_1:attach_character_accessory(p6, v7)
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 38 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorPurple] = 10,
        [v_u_3.Type.ColorGreen] = 7,
        [v_u_3.Type.FeverMultiplier] = 5
    };
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 45 ]]
    return 0;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 48 ]]
    return 3;
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 51 ]]
    return "rbxassetid://8100404162";
end;
return v4;
