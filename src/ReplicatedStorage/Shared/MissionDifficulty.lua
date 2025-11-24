-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:05 PM
-- Cached decompilation

local v_u_1 = {
    ["Beginner"] = 0,
    ["Novice"] = 1,
    ["Amateur"] = 2,
    ["Pro"] = 3,
    ["Star"] = 4
}
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList):new():push_back_table_list({
    v_u_1.Beginner,
    v_u_1.Novice,
    v_u_1.Amateur,
    v_u_1.Pro,
    v_u_1.Star
})
v_u_1.all_difficulty_asc_list = function(_) --[[ Name: all_difficulty_asc_list ]] --[[ Line: 12 ]]
    --[[ Upvalues: (copy 1): v_u_2 ]]
    return v_u_2;
end;
v_u_1.difficulty_to_string = function(_, p3) --[[ Name: difficulty_to_string ]] --[[ Line: 16 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return p3 == v_u_1.Beginner and "Beginner" or (p3 == v_u_1.Novice and "Novice" or (p3 == v_u_1.Amateur and "Amateur" or (p3 == v_u_1.Pro and "Pro" or (p3 == v_u_1.Star and "Star" or "???"))));
end;
v_u_1.difficulty_upgrade = function(_, p4) --[[ Name: difficulty_upgrade ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    if p4 == v_u_1.Beginner then
        return v_u_1.Novice;
    elseif p4 == v_u_1.Novice then
        return v_u_1.Amateur;
    elseif p4 == v_u_1.Amateur then
        return v_u_1.Pro;
    elseif p4 == v_u_1.Pro then
        return v_u_1.Star;
    else
        return p4;
    end;
end;
v_u_1.is_max_difficulty = function(_, p5) --[[ Name: is_max_difficulty ]] --[[ Line: 44 ]]
    --[[ Upvalues: (copy 1): v_u_1 ]]
    return p5 == v_u_1.Star;
end;
return v_u_1;
