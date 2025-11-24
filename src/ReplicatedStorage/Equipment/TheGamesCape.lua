-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:42 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.SPAvatarSlot)
local v_u_3 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.ModelLoadDBAsset)
require(game.ReplicatedStorage.Shared.WaitForFinish)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPList)
local v7 = v_u_1:new()
v7.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 12 ]]
    return "The Games: Cape";
end;
v7.get_avatar_slot = function(_) --[[ Name: get_avatar_slot ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2.BACK;
end;
v7.apply_appearance = function(_, _) end;
v7.requires_apply_appearance_async = function(_) --[[ Name: requires_apply_appearance_async ]] --[[ Line: 20 ]]
    return true;
end;
v7.apply_appearance_async = function(_, p_u_8, p_u_9) --[[ Name: apply_appearance_async ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_4, (copy 3): v_u_5, (copy 4): v_u_6 ]]
    v_u_1:load_accessory_from_modelloaddbasset(v_u_4.Accessory.TheGamesCape, function(p_u_10) --[[ Line: 22 ]]
        --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_6, (ref 3): v_u_1, (copy 4): p_u_8, (copy 5): p_u_9 ]]
        if p_u_10 then
            v_u_5:ptry(function() --[[ Line: 24 ]]
                --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_6 ]]
                p_u_10.Handle.TextureID = v_u_6:new({
                    "rbxassetid://18686554253",
                    "rbxassetid://18686555028",
                    "rbxassetid://18686555910",
                    "rbxassetid://18686556744",
                    "rbxassetid://18686557512"
                }):random()
            end)
            v_u_1:attach_character_accessory(p_u_8, p_u_10)
        end;
        p_u_9()
    end)
end;
v7.get_gear_power = function(_) --[[ Name: get_gear_power ]] --[[ Line: 39 ]]
    return 50;
end;
v7.get_gear_tier = function(_) --[[ Name: get_gear_tier ]] --[[ Line: 42 ]]
    return 3;
end;
v7.get_gear_statmodifierobj = function(_) --[[ Name: get_gear_statmodifierobj ]] --[[ Line: 45 ]]
    --[[ Upvalues: (copy 1): v_u_3 ]]
    return {
        [v_u_3.Type.ColorGreen] = 2,
        [v_u_3.Type.FeverTime] = 5,
        [v_u_3.Type.FeverMultiplier] = 5,
        [v_u_3.Type.ComboMultiplier] = 5,
        [v_u_3.Type.FeverFillRate] = 5
    };
end;
v7.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 54 ]]
    return "rbxassetid://18686779643";
end;
return v7;
