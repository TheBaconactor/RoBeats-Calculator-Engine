-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:33 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 7 ]]
    return "Kurante\'s DiVE Headphones";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.NECK;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, v8, v9 = v_u_1:create_accessory_base(p6, p5:get_name(), "HatAttachment", "http://www.roblox.com/asset/?id=161257299 ", "rbxassetid://7903304750")
    v7.AttachmentForward = Vector3.new(0, 0, -1)
    v7.AttachmentPos = Vector3.new(0, 0.2, 0)
    v7.AttachmentRight = Vector3.new(1, 0, 0)
    v7.AttachmentUp = Vector3.new(0, 1, 0)
    v8.Orientation = Vector3.new(0, -0, -0)
    v8.Position = Vector3.new(0, 0.3, -0)
    v9.Offset = Vector3.new(0, 0, 0)
    v9.Scale = Vector3.new(1.1, 1.1, 1.1)
    v_u_1:attach_character_accessory(p6, v7)
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorOrange] = 7,
        [v_u_3.Type.ColorGreen] = 7,
        [v_u_3.Type.ComboMultiplier] = 4,
        [v_u_3.Type.PerfectPoints] = 1
    };
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 43 ]]
    return 0;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 46 ]]
    return 2;
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 49 ]]
    return "rbxassetid://7903751620";
end;
return v4;
