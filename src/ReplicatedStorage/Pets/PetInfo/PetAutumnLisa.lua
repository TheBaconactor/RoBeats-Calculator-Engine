-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:03 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Pets.PetInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.GearStats)
local v3 = v_u_1:new()
v3.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 6 ]]
    return "Autumn Festival Lisa";
end;
v3.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 7 ]]
    return "With the falling of leaves and a brisk chill in the air, Autumn has arrived! Preferrably with hot drink in hand, celebrate the new season with our fall playlist, Autumn Festival Lisa and our all-new \"Autumn Abode\" stage. Don\'t forget a jacket!";
end;
v3.create_character = function(_, p4, p5, p_u_6) --[[ Name: create_character ]] --[[ Line: 9 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    v_u_1:spawn_pet_npc_from_name("MiniAutumnLisa", p5, p4, function(p7, p8) --[[ Line: 10 ]]
        --[[ Upvalues: (copy 1): p_u_6 ]]
        p_u_6(p7, p8)
    end)
end;
v3.get_base_statmodifierobj = function(_) --[[ Name: get_base_statmodifierobj ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return {
        [v_u_2.Type.FeverTime] = 8
    };
end;
v3.get_color_statmodifierobj = function(_) --[[ Name: get_color_statmodifierobj ]] --[[ Line: 21 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return {
        [v_u_2.Type.ColorOrange] = 12,
        [v_u_2.Type.ColorRed] = 7
    };
end;
v3.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 28 ]]
    return "rbxassetid://15000572524";
end;
v3.get_rarity = function(_) --[[ Name: get_rarity ]] --[[ Line: 32 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return v_u_1.Rarity.Tier2;
end;
return v3;
