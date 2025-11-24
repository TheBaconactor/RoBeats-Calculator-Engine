-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:19 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 8 ]]
    return "Gamer\'s Expensive Bowtie";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 11 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.NECK;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
    local v7, v8, v9 = v_u_1:create_accessory_base(p6, p5:get_name(), v_u_2:slot_to_attachment_name(p5:get_avatar_slot()), "http://www.roblox.com/asset/?id=16593970", "http://www.roblox.com/asset/?id=28501622")
    v7.AttachmentForward = Vector3.new(0, 0, -1)
    v7.AttachmentPos = Vector3.new(0, 1.1, 0.6)
    v7.AttachmentRight = Vector3.new(1, 0, 0)
    v7.AttachmentUp = Vector3.new(0, 1, 0)
    v8.Position = Vector3.new(0, 0.1, 0.6)
    v9.Scale = Vector3.new(0.6, 0.6, 0.6)
    v_u_1:attach_character_accessory(p6, v7)
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 34 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorOrange] = 8,
        [v_u_3.Type.ColorBlue] = 6,
        [v_u_3.Type.FeverMultiplier] = 4,
        [v_u_3.Type.ComboMultiplier] = 2
    };
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 42 ]]
    return 35;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 45 ]]
    return 2;
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 48 ]]
    return "https://www.roblox.com/Thumbs/Asset.ashx?width=110&height=110&assetId=28502997";
end;
return v4;
