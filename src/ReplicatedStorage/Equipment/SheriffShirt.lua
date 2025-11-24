-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:32 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v3 = v_u_1:new()
v3.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 6 ]]
    return "Sheriff\'s Coat";
end;
v3.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 9 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.SHIRT;
end;
v3.apply_appearance = function(p4, p5) --[[ Name: apply_appearance ]] --[[ Line: 12 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v6, v7, v8 = v_u_1:create_accessory_base(p5, p4:get_name(), "BodyFrontAttachment", "rbxassetid://7189831488", "http://www.roblox.com/asset/?id=7189825085")
    v7.Position = Vector3.new(0, -0.7, 1.1)
    v7.Orientation = Vector3.new(0, 180, 0)
    v8.Offset = Vector3.new(0, -0.7, 0.6)
    v8.Scale = Vector3.new(1, 0.7, 1)
    v_u_1:attach_character_accessory(p5, v6)
    local v9, _, v10 = v_u_1:create_accessory_base(p5, p4:get_name() .. "(Left)", "LeftWristRigAttachment", "rbxassetid://7163583339", "rbxassetid://7163583408")
    v10.Offset = Vector3.new(0, 0.25, 0)
    v10.Scale = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p5, v9)
    local v11, _, v12 = v_u_1:create_accessory_base(p5, p4:get_name() .. "(Right)", "RightWristRigAttachment", "rbxassetid://7163589705", "rbxassetid://7163589755")
    v12.Offset = Vector3.new(0, 0.25, 0)
    v12.Scale = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p5, v11)
    v_u_1:shirt_base_apply(p5, "http://www.roblox.com/asset/?id=7189815788")
end;
v3.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 64 ]]
    return 0;
end;
v3.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 67 ]]
    return -1;
end;
v3.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 70 ]]
    return {};
end;
v3.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 74 ]]
    return "http://www.roblox.com/asset/?id=7234743271";
end;
return v3;
