-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:42 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_5 = require(game.ReplicatedStorage.Shared.WaitForFinish)
local v6 = v_u_1:new()
v6.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 10 ]]
    return "Skylate\'s Hoodie";
end;
v6.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.SHIRT;
end;
v6.apply_appearance = function(_, _) end;
v6.requires_apply_appearance_async = function(_) --[[ Name: requires_apply_appearance_async ]] --[[ Line: 18 ]]
    return true;
end;
v6.apply_appearance_async = function(_, p_u_7, p_u_8) --[[ Name: apply_appearance_async ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_1, (copy 3): v_u_4 ]]
    local v_u_9 = v_u_5.Builder:new()
    v_u_9:begin()
    v_u_1:load_accessory_from_modelloaddbasset(v_u_4.Accessory.SkylateHoodie, function(p10) --[[ Line: 23 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_7, (copy 3): v_u_9 ]]
        if p10 then
            v_u_1:attach_character_accessory(p_u_7, p10)
        end;
        v_u_9:finish()
    end)
    v_u_9:wait_for_finish(function() --[[ Line: 30 ]]
        --[[ Upvalues: (copy 1): p_u_8 ]]
        p_u_8()
    end)
    v_u_1:shirt_base_apply(p_u_7, "rbxassetid://16562469346")
end;
v6.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 36 ]]
    return 50;
end;
v6.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 39 ]]
    return 2;
end;
v6.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 42 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorPurple] = 13,
        [v_u_3.Type.ColorBlue] = 5,
        [v_u_3.Type.FeverMultiplier] = 7
    };
end;
v6.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 49 ]]
    return "rbxassetid://17422041439";
end;
return v6;
