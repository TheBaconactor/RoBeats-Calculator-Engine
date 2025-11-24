-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:39 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_5 = require(game.ReplicatedStorage.Shared.WaitForFinish)
local v6 = v_u_1:new()
v6.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 10 ]]
    return "Sound Space Speaker Ears";
end;
v6.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v6.apply_appearance = function(_, _) end;
v6.requires_apply_appearance_async = function(_) --[[ Name: requires_apply_appearance_async ]] --[[ Line: 18 ]]
    return true;
end;
v6.apply_appearance_async = function(_, p_u_7, p_u_8) --[[ Name: apply_appearance_async ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_1, (copy 3): v_u_4 ]]
    local v_u_9 = v_u_5:new(4, function() --[[ Line: 20 ]]
        --[[ Upvalues: (copy 1): p_u_8 ]]
        p_u_8()
    end)
    v_u_1:load_accessory_from_modelloaddbasset(v_u_4.Accessory.SoundSpaceEarLeft, function(p10) --[[ Line: 23 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_7, (copy 3): v_u_9 ]]
        if p10 then
            v_u_1:attach_character_accessory(p_u_7, p10)
        end;
        v_u_9:finish()
    end)
    v_u_1:load_accessory_from_modelloaddbasset(v_u_4.Accessory.SoundSpaceEarRight, function(p11) --[[ Line: 29 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_7, (copy 3): v_u_9 ]]
        if p11 then
            v_u_1:attach_character_accessory(p_u_7, p11)
        end;
        v_u_9:finish()
    end)
    v_u_1:load_accessory_from_modelloaddbasset(v_u_4.Accessory.SoundSpaceSpeakerLeft, function(p12) --[[ Line: 35 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_7, (copy 3): v_u_9 ]]
        if p12 then
            v_u_1:attach_character_accessory(p_u_7, p12)
        end;
        v_u_9:finish()
    end)
    v_u_1:load_accessory_from_modelloaddbasset(v_u_4.Accessory.SoundSpaceSpeakerRight, function(p13) --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_7, (copy 3): v_u_9 ]]
        if p13 then
            v_u_1:attach_character_accessory(p_u_7, p13)
        end;
        v_u_9:finish()
    end)
end;
v6.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 49 ]]
    return 50;
end;
v6.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 52 ]]
    return 3;
end;
v6.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 55 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorPurple] = 12,
        [v_u_3.Type.ColorBlue] = 8,
        [v_u_3.Type.FeverTime] = 5,
        [v_u_3.Type.FeverMultiplier] = 4
    };
end;
v6.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 63 ]]
    return "rbxassetid://12101287561";
end;
return v6;
