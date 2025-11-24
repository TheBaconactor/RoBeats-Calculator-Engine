-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:38 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Avatar.ColorGearParticles)
require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_4 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
require(game.ReplicatedStorage.Shared.WaitForFinish)
local v5 = v_u_1:new()
v5.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 11 ]]
    return "Santa\'s Helper Hood";
end;
v5.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 14 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v5.apply_appearance = function(_, _) end;
v5.requires_apply_appearance_async = function(_) --[[ Name: requires_apply_appearance_async ]] --[[ Line: 19 ]]
    return true;
end;
v5.apply_appearance_async = function(_, p_u_6, p_u_7) --[[ Name: apply_appearance_async ]] --[[ Line: 20 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4 ]]
    v_u_1:load_accessory_from_modelloaddbasset(v_u_4.Accessory.XmasHood, function(p8) --[[ Line: 21 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_6, (copy 3): p_u_7 ]]
        if p8 then
            v_u_1:attach_character_accessory(p_u_6, p8)
        end;
        local _, _, v9, v10 = v_u_1:create_particle_emitter_accessory(p_u_6, "HatAttachment", Vector3.new(2, 2, 0.05), "rbxassetid://11830408557")
        v9.Color = ColorSequence.new({ ColorSequenceKeypoint.new(0, Color3.fromRGB(255, 255, 255)), ColorSequenceKeypoint.new(1, Color3.fromRGB(255, 255, 255)) })
        v9.Size = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.25), NumberSequenceKeypoint.new(1, 0.25) })
        v9.Transparency = NumberSequence.new({ NumberSequenceKeypoint.new(0, 0.5), NumberSequenceKeypoint.new(1, 1) })
        v9.EmissionDirection = Enum.NormalId.Back
        v9.ZOffset = 0
        v9.Acceleration = Vector3.new(0, 0, -0.05)
        v9.Drag = 0.5
        v9.Lifetime = NumberRange.new(1, 3)
        v9.Rate = 4
        v9.Rotation = NumberRange.new(0, 0)
        v9.RotSpeed = NumberRange.new(0, 0)
        v9.Speed = NumberRange.new(1, 2)
        v9.SpreadAngle = Vector2.new(0, 45)
        v9.Enabled = true
        v10.Enabled = false
        p_u_7()
    end)
end;
v5.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 60 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorGreen] = 14,
        [v_u_3.Type.ColorPurple] = 12,
        [v_u_3.Type.FeverTime] = 3
    };
end;
v5.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 67 ]]
    return 50;
end;
v5.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 70 ]]
    return 3;
end;
v5.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 73 ]]
    return "rbxassetid://11830324759";
end;
return v5;
