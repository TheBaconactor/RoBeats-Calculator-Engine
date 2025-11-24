-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:00 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Pets.PetInfoBase)
local v_u_2 = require(game.ReplicatedStorage.Avatar.GearStats)
local v3 = v_u_1:new()
v3.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 6 ]]
    return "Ushi-chan";
end;
v3.get_description = function(_) --[[ Name: get_description ]] --[[ Line: 8 ]]
    return "A character from the art of naruto2413\'s track \'AI Bomb (On Vocal)\', a vocal cover of his chiptune classic. From the artist: When I showed this character to the vocalist Aya Majiro, she said \"I want to use this avatar too.\". We named the character \"Ushi-chan\" (Ushi is cow in Japanese, and her horns resemble those of a cow).";
end;
v3.create_character = function(_, p4, p5, p_u_6) --[[ Name: create_character ]] --[[ Line: 10 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    v_u_1:spawn_pet_npc_from_name("MiniAIBomb", p5, p4, function(p7, p8) --[[ Line: 11 ]]
        --[[ Upvalues: (copy 1): p_u_6 ]]
        p_u_6(p7, p8)
    end)
end;
v3.get_base_statmodifierobj = function(_) --[[ Name: get_base_statmodifierobj ]] --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return {
        [v_u_2.Type.FeverTime] = 6
    };
end;
v3.get_color_statmodifierobj = function(_) --[[ Name: get_color_statmodifierobj ]] --[[ Line: 22 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return {
        [v_u_2.Type.ColorOrange] = 11,
        [v_u_2.Type.ColorGreen] = 3
    };
end;
v3.get_icon = function(_) --[[ Name: get_icon ]] --[[ Line: 29 ]]
    return "rbxassetid://11110258933";
end;
v3.get_rarity = function(_) --[[ Name: get_rarity ]] --[[ Line: 33 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return v_u_1.Rarity.Tier1;
end;
return v3;
