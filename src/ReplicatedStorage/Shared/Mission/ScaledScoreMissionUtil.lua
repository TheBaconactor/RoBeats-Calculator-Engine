-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:12 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.MissionDifficulty)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v5 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_6 = nil
local v_u_7 = nil
v5:require_shared(function() --[[ Line: 9 ]]
    --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_7 ]]
    v_u_6 = require(game.ReplicatedStorage.Shared.MissionInfo)
    v_u_7 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
end)
local v_u_13 = {
    ["new"] = function(_, p_u_8, p_u_9) --[[ Name: new ]] --[[ Line: 35 ]]
        local v10 = {}
        local v_u_11 = -1
        v10.get_naked_max_multiplier = function(_) --[[ Name: get_naked_max_multiplier ]] --[[ Line: 38 ]]
            --[[ Upvalues: (copy 1): p_u_8 ]]
            return p_u_8;
        end;
        v10.get_reward_scale = function(_) --[[ Name: get_reward_scale ]] --[[ Line: 39 ]]
            --[[ Upvalues: (copy 1): p_u_9 ]]
            return p_u_9;
        end;
        v10.get_tier_id = function(_) --[[ Name: get_tier_id ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11;
        end;
        v10.set_tier_id = function(_, p12) --[[ Name: set_tier_id ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            v_u_11 = p12
        end;
        return v10;
    end
}
local v_u_16 = v3:new({
    v_u_13:new(0, 1),
    v_u_13:new(0.5, 1.05),
    v_u_13:new(0.75, 1.1),
    v_u_13:new(0.9, 1.15),
    v_u_13:new(1, 1.2),
    v_u_13:new(1.2, 1.35),
    v_u_13:new(1.4, 1.5),
    v_u_13:new(2, 1.75),
    v_u_13:new(2.8, 2),
    v_u_13:new(3.8, 2.35),
    v_u_13:new(5, 2.65),
    v_u_13:new(6.4, 2.9),
    v_u_13:new(8, 3.15),
    v_u_13:new(9.8, 3.35),
    v_u_13:new(11.8, 3.55),
    v_u_13:new(14, 3.7),
    v_u_13:new(16.4, 3.85),
    v_u_13:new(19, 3.9),
    v_u_13:new(21.8, 3.95),
    (function(p14, p15) --[[ Name: create_tier ]] --[[ Line: 47 ]]
        --[[ Upvalues: (copy 1): v_u_13 ]]
        return v_u_13:new(p14, p15);
    end)(25, 4)
})
local v_u_17 = v_u_6
local v_u_18 = v_u_7
local v_u_20 = {
    ["mission_difficulty_to_required_accuracy"] = function(_, p19) --[[ Name: mission_difficulty_to_required_accuracy ]] --[[ Line: 16 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_1 ]]
        return v_u_2.ScaledScoreMissionDebug and 0.05 or (p19 == v_u_1.Beginner and 0.5 or (p19 == v_u_1.Novice and 0.65 or (p19 == v_u_1.Amateur and 0.8 or (p19 == v_u_1.Pro and 0.875 or 0.925))));
    end
}
for v21, v22 in v_u_16:key_itr() do
    v22:set_tier_id(v21)
end;
v_u_20.mission_data_get_score_tier_id = function(_, p23, p24) --[[ Name: mission_data_get_score_tier_id ]] --[[ Line: 77 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    local v25 = p23:get_song_naked_max_score()
    local v26 = 1
    for v27, _ in v_u_16:key_itr() do
        local v28 = v27 + 1
        if v_u_16:count() < v28 then
            return v27;
        end;
        if p24 < v25 * v_u_16:get(v28):get_naked_max_multiplier() then
            v26 = v27
            break;
        end;
        v26 = v27
    end;
    return v26;
end;
v_u_20.mission_data_get_tier_id_score = function(_, p29, p30) --[[ Name: mission_data_get_tier_id_score ]] --[[ Line: 92 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    return math.floor(p29:get_song_naked_max_score() * v_u_16:get(p30):get_naked_max_multiplier());
end;
v_u_20.get_tier_id_reward_scale = function(_, p31) --[[ Name: get_tier_id_reward_scale ]] --[[ Line: 98 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    return v_u_16:get(p31):get_reward_scale();
end;
v_u_20.get_next_tier_id = function(_, p32) --[[ Name: get_next_tier_id ]] --[[ Line: 102 ]]
    --[[ Upvalues: (copy 1): v_u_16 ]]
    if p32 < v_u_16:count() then
        return true, p32 + 1;
    else
        return false, p32;
    end;
end;
v_u_20.get_scaled_amount_for_multiplier = function(_, p33, p34) --[[ Name: get_scaled_amount_for_multiplier ]] --[[ Line: 110 ]]
    --[[ Upvalues: (copy 1): v_u_4 ]]
    return v_u_4:round_to_nearest(p33 * p34, 5);
end;
v_u_20.get_playerblob_mission_data_timeframe_reward_desc_info_list_scaled = function(_, p35, p36, p37, p38) --[[ Name: get_playerblob_mission_data_timeframe_reward_desc_info_list_scaled ]] --[[ Line: 114 ]]
    --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_17, (copy 3): v_u_20 ]]
    local v39 = v_u_18.RewardInfo:table_to_list(v_u_18.RewardInfo:list_to_table(p38))
    local v40 = v_u_20:get_tier_id_reward_scale((v_u_20:mission_data_get_score_tier_id(p36, (v_u_17:playerblob_missionid_get_count(p35, p37, p36:get_id())))))
    for _, v41 in v39:key_itr() do
        if v41:get_type() == v_u_18.RewardType.Coins then
            v41:set_amount(v_u_20:get_scaled_amount_for_multiplier(v41:get_amount(), v40))
        elseif v_u_18.RewardType:is_type_team_contribution_points(v41:get_type()) then
            v41:set_amount(v_u_20:get_scaled_amount_for_multiplier(v41:get_amount(), v40))
        end;
    end;
    return v39;
end;
return v_u_20;
