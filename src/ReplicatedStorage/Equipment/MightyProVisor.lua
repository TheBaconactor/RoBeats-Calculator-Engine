-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:22 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Mighty\'s Pro BunnyVisor";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
    local v7, v8, v9 = v_u_1:create_accessory_base(p6, p5:get_name(), v_u_2:slot_to_attachment_name(p5:get_avatar_slot()), "http://www.roblox.com/asset/?id=227430350", "http://www.roblox.com/asset/?id=227430412")
    v7.AttachmentForward = Vector3.new(0, -0.124, -0.992)
    v7.AttachmentPos = Vector3.new(0, -0.675, 0.45)
    v7.AttachmentRight = Vector3.new(1, 0, 0)
    v7.AttachmentUp = Vector3.new(0, 0.992, -0.124)
    v8.Position = Vector3.new(0, -0.576, 0.437)
    v8.Orientation = Vector3.new(-7.125, -0, -0)
    v9.Scale = Vector3.new(2.5, 2.5, 2.5)
    v9.Offset = Vector3.new(0, 0, 0)
    v_u_1:attach_character_accessory(p6, v7)
    local v10, v11, v12 = v_u_1:create_accessory_base(p6, p5:get_name(), v_u_2:slot_to_attachment_name(p5:get_avatar_slot()), "http://www.roblox.com/asset/?id=1081088", "http://www.roblox.com/asset/?id=20264549")
    v10.AttachmentForward = Vector3.new(0, 0, -1)
    v10.AttachmentPos = Vector3.new(0, 0.09, 0.18)
    v10.AttachmentRight = Vector3.new(1, 0, 0)
    v10.AttachmentUp = Vector3.new(0, 1, 0)
    v11.Position = Vector3.new(0, 0.19, 0.18)
    v12.Scale = Vector3.new(1.02, 1.02, 1.02)
    v_u_1:attach_character_accessory(p6, v10)
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 56 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorGreen] = 14,
        [v_u_3.Type.ColorBlue] = 4,
        [v_u_3.Type.PerfectTime] = -1
    };
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 63 ]]
    return 35;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 66 ]]
    return 2;
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 69 ]]
    return "https://www.roblox.com/Thumbs/Asset.ashx?width=110&height=110&assetId=20264649";
end;
return v4;
