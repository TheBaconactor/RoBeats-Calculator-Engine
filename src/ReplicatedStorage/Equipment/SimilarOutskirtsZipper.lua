-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:38 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 7 ]]
    return "Similar Outskirts Zipper";
end;
v4.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.NECK;
end;
v4.apply_appearance = function(p5, p6) --[[ Name: apply_appearance ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    local v7, v8, v9 = v_u_1:create_accessory_base(p6, p5:get_name(), "NeckAttachment", "rbxassetid://8842575738", "rbxassetid://10034350857")
    v7.AttachmentForward = Vector3.new(-1, 0, -0)
    v7.AttachmentPos = Vector3.new(-0.072898865, 0.11307573, -0.00030517578)
    v7.AttachmentRight = Vector3.new(0, 0, -1)
    v7.AttachmentUp = Vector3.new(0, 1, 0)
    v8.Orientation = Vector3.new(-0.000000000000000002032253, 0.0000000000000000000000000000013718274, -0.00000000003867625)
    v8.Position = Vector3.new(0, 0.4557953, 0.5934067)
    v9.Offset = Vector3.new(0, 0, 0)
    v9.Scale = Vector3.new(0.1, 0.1, 0.1)
    v9.VertexColor = Vector3.new(1, 1, 1)
    v_u_1:attach_character_accessory(p6, v7)
end;
v4.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 36 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorOrange] = 9,
        [v_u_3.Type.ColorBlue] = 7,
        [v_u_3.Type.FeverTime] = 5,
        [v_u_3.Type.FeverMultiplier] = 3
    };
end;
v4.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 44 ]]
    return 35;
end;
v4.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 47 ]]
    return 2;
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 50 ]]
    return "rbxassetid://11716070684";
end;
return v4;
