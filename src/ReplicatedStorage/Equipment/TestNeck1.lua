-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:19 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v3 = v_u_1:new()
v3.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "TestNeck1";
end;
v3.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.NECK;
end;
v3.apply_appearance = function(p4, p5) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
    local v6, v7 = v_u_1:create_accessory_base(p5, p4:get_name(), v_u_2:slot_to_attachment_name(p4:get_avatar_slot()), "http://www.roblox.com/asset/?id=49763150", "rbxassetid://49763125")
    v6.AttachmentForward = Vector3.new(0, 0, -1)
    v6.AttachmentPos = Vector3.new(0, 1.3, 0)
    v6.AttachmentRight = Vector3.new(1, 0, 0)
    v6.AttachmentUp = Vector3.new(0, 1, 0)
    v7.Position = Vector3.new(-0, 0.3, 0.15)
    v_u_1:attach_character_accessory(p5, v6)
end;
v3.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 33 ]]
    return 0;
end;
v3.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 36 ]]
    return -1;
end;
v3.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 39 ]]
    return {};
end;
v3.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 43 ]]
    return "https://www.roblox.com/Thumbs/Asset.ashx?width=110&height=110&assetId=159199178";
end;
v3.is_debug = function(_) --[[ Name: is_debug ]] --[[ Line: 46 ]]
    return true;
end;
return v3;
