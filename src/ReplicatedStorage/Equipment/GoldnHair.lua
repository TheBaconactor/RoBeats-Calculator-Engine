-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:35 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v5 = v_u_1:new()
v5.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 9 ]]
    return "Goldn\'s Braids";
end;
v5.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 12 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.HAT;
end;
v_u_1:define_as_hair(v5)
v5.apply_appearance = function(_, _) end;
v5.requires_apply_appearance_async = function(_) --[[ Name: requires_apply_appearance_async ]] --[[ Line: 18 ]]
    return true;
end;
v5.apply_appearance_async = function(_, p_u_6, p_u_7) --[[ Name: apply_appearance_async ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4 ]]
    v_u_1:load_accessory_from_modelloaddbasset(v_u_4.Accessory.GoldnBraids, function(p8) --[[ Line: 21 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_6, (copy 3): p_u_7 ]]
        if p8 then
            v_u_1:attach_character_accessory(p_u_6, p8)
        end;
        p_u_7()
    end)
end;
v5.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 48 ]]
    return 50;
end;
v5.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 51 ]]
    return 3;
end;
v5.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 54 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorPurple] = 10,
        [v_u_3.Type.ColorBlue] = 8,
        [v_u_3.Type.FeverTime] = 3,
        [v_u_3.Type.FeverFillRate] = 3
    };
end;
v5.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 62 ]]
    return "rbxassetid://9173312718";
end;
return v5;
