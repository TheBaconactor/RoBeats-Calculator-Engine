-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:32 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
require(game.ReplicatedStorage.Avatar.GearStats)
local v3 = v_u_1:new()
v3.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 7 ]]
    return "Sheriff\'s Hat";
end;
v3.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v3.apply_appearance = function(p4, p5) --[[ Name: apply_appearance ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
    local v6, v7, v8 = v_u_1:create_accessory_base(p5, p4:get_name(), v_u_2:slot_to_attachment_name(p4:get_avatar_slot()), "rbxassetid://7144134688", "http://www.roblox.com/asset/?id=7189824325")
    v6.AttachmentForward = Vector3.new(0, 0, -1)
    v6.AttachmentPos = Vector3.new(0, 0, 0)
    v6.AttachmentRight = Vector3.new(1, 0, 0)
    v6.AttachmentUp = Vector3.new(0, 1, 0)
    v7.Orientation = Vector3.new(0, 0, 0)
    v7.Position = Vector3.new(0, 0.075, -0.065)
    v8.Offset = Vector3.new(0, 0.2, -0.1)
    v8.Scale = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p5, v6)
end;
v3.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 35 ]]
    return {};
end;
v3.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 39 ]]
    return 0;
end;
v3.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 42 ]]
    return 2;
end;
v3.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 45 ]]
    return "http://www.roblox.com/asset/?id=7234743720";
end;
return v3;
