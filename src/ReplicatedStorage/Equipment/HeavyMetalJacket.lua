-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:43 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
local v_u_5 = require(game.ReplicatedStorage.Shared.WaitForFinish)
local v6 = v_u_1:new()
v6.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 10 ]]
    return "Heavy Metal Starlet\'s Jacket";
end;
v6.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 13 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.SHIRT;
end;
v6.apply_appearance = function(_, _) end;
v6.requires_apply_appearance_async = function(_) --[[ Name: requires_apply_appearance_async ]] --[[ Line: 17 ]]
    return true;
end;
v6.apply_appearance_async = function(_, p_u_7, p_u_8) --[[ Name: apply_appearance_async ]] --[[ Line: 18 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_5 ]]
    v_u_1:load_accessory_from_modelloaddbasset(v_u_4.Accessory.XmasCape, function(_) --[[ Line: 19 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_7, (ref 3): v_u_5, (ref 4): v_u_4, (copy 5): p_u_8 ]]
        v_u_1:shirt_base_apply(p_u_7, "http://www.roblox.com/asset/?id=5673463802")
        local v_u_9 = v_u_5.Builder:new()
        v_u_9:begin()
        v_u_1:load_accessory_from_modelloaddbasset(v_u_4.Accessory.RockJacket, function(p10) --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): p_u_7, (copy 3): v_u_9 ]]
            if p10 then
                v_u_1:attach_character_accessory(p_u_7, p10)
            end;
            v_u_9:finish()
        end)
        v_u_9:wait_for_finish(function() --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): p_u_8 ]]
            p_u_8()
        end)
    end)
end;
v6.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 37 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorOrange] = 15,
        [v_u_3.Type.ColorGreen] = 6,
        [v_u_3.Type.FeverFillRate] = 2,
        [v_u_3.Type.FeverMultiplier] = 5
    };
end;
v6.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 45 ]]
    return 35;
end;
v6.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 48 ]]
    return 2;
end;
v6.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 51 ]]
    return "rbxassetid://94394636172091";
end;
return v6;
