-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:08 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v4 = {}
local v_u_5 = {
    ["Tier1"] = 1,
    ["Tier2"] = 2,
    ["Tier3"] = 3,
    ["Tier4"] = 4,
    ["Tier5"] = 5,
    ["Tier6"] = 6,
    ["Tier7"] = 7
}
local function _(p6) --[[ Name: place_to_tier ]] --[[ Line: 17 ]]
    --[[ Upvalues: (copy 1): v_u_5 ]]
    if p6 <= 1 then
        return v_u_5.Tier1;
    elseif p6 <= 2 then
        return v_u_5.Tier2;
    elseif p6 <= 5 then
        return v_u_5.Tier3;
    elseif p6 <= 10 then
        return v_u_5.Tier4;
    elseif p6 <= 15 then
        return v_u_5.Tier5;
    elseif p6 <= 25 then
        return v_u_5.Tier6;
    else
        return v_u_5.Tier7;
    end;
end;
v4.get_event_point_reward_for_place_and_player_count = function(_, p7, p8) --[[ Name: get_event_point_reward_for_place_and_player_count ]] --[[ Line: 35 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_5, (copy 3): v_u_2, (copy 4): v_u_3 ]]
    v_u_1:is_int(p7)
    v_u_1:is_int(p8)
    local v9
    if p7 <= 1 then
        v9 = v_u_5.Tier1
    elseif p7 <= 2 then
        v9 = v_u_5.Tier2
    elseif p7 <= 5 then
        v9 = v_u_5.Tier3
    elseif p7 <= 10 then
        v9 = v_u_5.Tier4
    elseif p7 <= 15 then
        v9 = v_u_5.Tier5
    elseif p7 <= 25 then
        v9 = v_u_5.Tier6
    else
        v9 = v_u_5.Tier7
    end;
    local v10 = v_u_2:YForPointOf2PtLineP1P2X(1, 100, 25, 750, v_u_3:clamp(p8, 1, 25))
    local v11
    if v9 == v_u_5.Tier1 then
        v11 = v10 * 1
    elseif v9 == v_u_5.Tier2 then
        v11 = v10 * 0.75
    elseif v9 == v_u_5.Tier3 then
        v11 = v10 * 0.5
    elseif v9 == v_u_5.Tier4 then
        v11 = v10 * 0.35
    elseif v9 == v_u_5.Tier5 then
        v11 = v10 * 0.25
    elseif v9 == v_u_5.Tier6 then
        v11 = v10 * 0.2
    else
        v11 = v10 * 0.2
    end;
    return math.floor(v11);
end;
v4.place_to_bubble_icon = function(_, p12) --[[ Name: place_to_bubble_icon ]] --[[ Line: 60 ]]
    --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_3 ]]
    local v13
    if p12 <= 1 then
        v13 = v_u_5.Tier1
    elseif p12 <= 2 then
        v13 = v_u_5.Tier2
    elseif p12 <= 5 then
        v13 = v_u_5.Tier3
    elseif p12 <= 10 then
        v13 = v_u_5.Tier4
    elseif p12 <= 15 then
        v13 = v_u_5.Tier5
    elseif p12 <= 25 then
        v13 = v_u_5.Tier6
    else
        v13 = v_u_5.Tier7
    end;
    if v13 <= v_u_5.Tier1 then
        return v_u_3:get_leaderboard_bubble_gold_assetid();
    elseif v13 <= v_u_5.Tier3 then
        return v_u_3:get_leaderboard_bubble_silver_assetid();
    elseif v13 <= v_u_5.Tier5 then
        return v_u_3:get_leaderboard_bubble_bronze_assetid();
    else
        return v_u_3:get_leaderboard_bubble_none_assetid();
    end;
end;
return v4;
