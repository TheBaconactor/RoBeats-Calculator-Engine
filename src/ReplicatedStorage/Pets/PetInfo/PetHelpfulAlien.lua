-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:57 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Pets.PetInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_3 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v4 = v_u_1:new()
v4.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 7 ]]
    return "Helpful Alien";
end;
v4.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 8 ]]
    return "A friendly alien who\'s always available to help you get started. Want to change your note speed or keybinds? This alien\'s got you covered!";
end;
v4.create_character = function(_, p5, p6, p_u_7) --[[ Name: create_character ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1 ]]
    v_u_1:spawn_pet_npc_from_name(not v_u_3.LoadDebugPetAssetForHelpfulAlien and "NPCHelpfulAlien" or v_u_3.DebugPetAssetName, p6, p5, function(p8, p9) --[[ Line: 16 ]]
        --[[ Upvalues: (copy 1): p_u_7 ]]
        p_u_7(p8, p9)
    end)
end;
v4.get_base_statmodifierobj = function(_) --[[ Name: get_base_statmodifierobj ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return {
        [v_u_2.Type.ComboMultiplier] = 5
    };
end;
v4.get_color_statmodifierobj = function(_) --[[ Name: get_color_statmodifierobj ]] --[[ Line: 27 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return {
        [v_u_2.Type.ColorRed] = 10,
        [v_u_2.Type.ColorPurple] = 5
    };
end;
v4.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 34 ]]
    return "rbxassetid://8678749570";
end;
v4.get_rarity = function(_) --[[ Name: get_rarity ]] --[[ Line: 38 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return v_u_1.Rarity.Tier1;
end;
return v4;
