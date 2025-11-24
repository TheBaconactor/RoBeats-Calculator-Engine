-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:43 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
require(game.ReplicatedStorage.Shared.WaitForFinish)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPList)
local v5 = v_u_1:new()
v5.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 12 ]]
    return "Snail-chan\'s Shell";
end;
v5.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.BACK;
end;
v5.apply_appearance = function(_, _) end;
v5.requires_apply_appearance_async = function(_) --[[ Name: requires_apply_appearance_async ]] --[[ Line: 20 ]]
    return true;
end;
v5.apply_appearance_async = function(_, p_u_6, p_u_7) --[[ Name: apply_appearance_async ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4 ]]
    v_u_1:load_accessory_from_modelloaddbasset(v_u_4.Accessory.UjicoBack, function(p8) --[[ Line: 22 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_6, (copy 3): p_u_7 ]]
        if p8 then
            v_u_1:attach_character_accessory(p_u_6, p8)
        end;
        p_u_7()
    end)
end;
v5.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 30 ]]
    return 50;
end;
v5.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 33 ]]
    return 2;
end;
v5.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 36 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorPurple] = 9,
        [v_u_3.Type.ColorBlue] = 8,
        [v_u_3.Type.FeverTime] = 10
    };
end;
v5.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 43 ]]
    return "rbxassetid://104992073159159";
end;
return v5;
