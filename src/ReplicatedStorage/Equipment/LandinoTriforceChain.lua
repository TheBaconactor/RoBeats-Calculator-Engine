-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:34 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 7 ]]
    return "Landino\'s Tri-Chain";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.NECK;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
    local v7, v8, v9 = v_u_1:create_accessory_base(p6, p5:get_name(), v_u_2:slot_to_attachment_name(p5:get_avatar_slot()), "rbxassetid://6767992222", "http://www.roblox.com/asset/?id=6767944039")
    v7.Name = "TriChain"
    v7.AttachmentForward = Vector3.new(0, 0, -1)
    v7.AttachmentPos = Vector3.new(0, 0.252, 0.128)
    v7.AttachmentRight = Vector3.new(1, 0, 0)
    v7.AttachmentUp = Vector3.new(0, 1, 0)
    v8.Orientation = Vector3.new(0, 0, 0)
    v8.Position = Vector3.new(0, 0.252, 0.128)
    v9.Offset = Vector3.new(0, 0.2, 0.1)
    v9.Scale = Vector3.new(2.25, 1.5, 1.5)
    v_u_1:attach_character_accessory(p6, v7)
    local v10, v11, v12, v13 = v_u_1:create_accessory_base(p6, p5:get_name(), v_u_2:slot_to_attachment_name(p5:get_avatar_slot()), "rbxassetid://7408542889", "")
    v10.Name = "Triforce"
    v10.AttachmentForward = Vector3.new(0, 0, -1)
    v10.AttachmentPos = Vector3.new(0, 0.252, 0.128)
    v10.AttachmentRight = Vector3.new(1, 0, 0)
    v10.AttachmentUp = Vector3.new(0, 1, 0)
    v11.Orientation = Vector3.new(90, 0, 0)
    v11.Position = Vector3.new(0, 0.252, 0.128)
    v12.Offset = Vector3.new(0, 0.85, -0.35)
    v12.Scale = Vector3.new(0.007, 0.007, 0.007)
    v13.Color = Color3.fromRGB(255, 176, 0)
    v_u_1:attach_character_accessory(p6, v10)
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 61 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorBlue] = 10,
        [v_u_3.Type.ColorGreen] = 4,
        [v_u_3.Type.PerfectPoints] = 4
    };
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 68 ]]
    return 35;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 71 ]]
    return 2;
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 74 ]]
    return "rbxassetid://7962452453";
end;
return v4;
