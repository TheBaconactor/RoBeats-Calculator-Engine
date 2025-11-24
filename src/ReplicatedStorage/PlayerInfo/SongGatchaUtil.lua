-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:07 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v2 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = {
    ["Tiers"] = {
        ["Tier0"] = 0,
        ["Tier1"] = 1,
        ["Tier2"] = 2,
        ["Tier3"] = 3,
        ["Tier4"] = 4
    }
}
v_u_6.tier_get_min_max_difficulty = function(_, p7) --[[ Name: tier_get_min_max_difficulty ]] --[[ Line: 19 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    if p7 == v_u_6.Tiers.Tier0 then
        return 1, 99;
    elseif p7 == v_u_6.Tiers.Tier1 then
        return 1, 5;
    elseif p7 == v_u_6.Tiers.Tier2 then
        return 5, 10;
    elseif p7 == v_u_6.Tiers.Tier3 then
        return 10, 16;
    else
        return 16, 99;
    end;
end;
v_u_6.tier_get_desc = function(_, p8) --[[ Name: tier_get_desc ]] --[[ Line: 33 ]]
    --[[ Upvalues: (copy 1): v_u_6 ]]
    if p8 == v_u_6.Tiers.Tier0 then
        return "All";
    end;
    if p8 == v_u_6.Tiers.Tier4 then
        return "16+";
    end;
    local v9, v10 = v_u_6:tier_get_min_max_difficulty(p8)
    return string.format("%d-%d", v9, v10);
end;
local v_u_11 = v1:new()
local v_u_12 = v1:new()
for _, v13 in pairs(v_u_6.Tiers) do
    local v14, v15 = v_u_6:tier_get_min_max_difficulty(v13)
    local v16 = v2:singleton():all_keys()
    for v17 = 1, v16:count() do
        local v18 = v16:get(v17)
        local v19 = v2:singleton():get_difficulty_for_key(v18)
        if v14 <= v19 and (v19 <= v15 and v2:singleton():get_songkey_should_grant(v18)) then
            local v20 = v2:singleton():key_get_audiomod(v18)
            if v20 == v2.MOD_NORMAL then
                v_u_11:push_back_to(v13, v18)
            elseif v20 == v2.MOD_HARDMODE then
                v_u_12:push_back_to(v13, v18)
            end;
        end;
    end;
end;
v_u_6.tier_get_available_normal_hard_songs = function(_, p21) --[[ Name: tier_get_available_normal_hard_songs ]] --[[ Line: 70 ]]
    --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_12 ]]
    return v_u_11:list_of(p21), v_u_12:list_of(p21);
end;
v_u_6.tier_get_hardmode_roll_percentage_d100 = function(_, p22) --[[ Name: tier_get_hardmode_roll_percentage_d100 ]] --[[ Line: 74 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_5 ]]
    local v23, v24 = v_u_6:tier_get_available_normal_hard_songs(p22)
    return v_u_5:clamp(v24:count() / (v23:count() * 20 + v24:count()) * 100, 0, 5);
end;
v_u_6.playerblob_get_tier_new_song_new_hardmode_d100 = function(_, p25, p26, p27) --[[ Name: playerblob_get_tier_new_song_new_hardmode_d100 ]] --[[ Line: 80 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_3, (copy 3): v_u_4 ]]
    local v28, v29 = v_u_6:tier_get_available_normal_hard_songs(p26)
    local v30 = v_u_3:new()
    local v31 = v_u_3:new()
    for v32 = 1, v28:count() do
        local v33 = v28:get(v32)
        if v_u_4:get_song_key_owned_count_including_collection(p25, v33, p27) == 0 then
            v30:push_back(v33)
        end;
    end;
    for v34 = 1, v29:count() do
        local v35 = v29:get(v34)
        if v_u_4:get_song_key_owned_count_including_collection(p25, v35, p27) == 0 then
            v31:push_back(v35)
        end;
    end;
    return v28:count() == 0 and 0 or v30:count() / v28:count() * 100, v29:count() == 0 and 0 or v31:count() / v29:count() * v_u_6:tier_get_hardmode_roll_percentage_d100(p26);
end;
return v_u_6;
