-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:05 PM
-- Cached decompilation

require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_1 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
require(game.ReplicatedStorage.Crafting.CraftingRewardCategories)
local v6 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v_u_7 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v8 = require(game.ReplicatedStorage.PlayerInfo.BoxInfo)
local v9 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_10 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_12 = {
    ["Tier"] = {
        ["Tier1"] = 1,
        ["Tier2"] = 2,
        ["Tier3"] = 3,
        ["Tier4"] = 4,
        ["Tier5"] = 5,
        ["Tier6"] = 6
    },
    ["get_leaderboard_ticket_material_id"] = function(_) --[[ Name: get_leaderboard_ticket_material_id ]] --[[ Line: 38 ]]
        return 250;
    end,
    ["next_reward_tier_for_rank"] = function(_, p11) --[[ Name: next_reward_tier_for_rank ]] --[[ Line: 156 ]]
        return p11 <= 20 and 1 or (p11 <= 50 and 20 or (p11 <= 200 and 50 or (p11 <= 400 and 200 or 400)));
    end
}
local v_u_13 = {
    ["Tier1"] = 1,
    ["Tier2"] = 2,
    ["Tier3"] = 3,
    ["Tier4"] = 4,
    ["Tier5"] = 5,
    ["Tier6"] = 6
}
local v14 = v3:new()
local v15 = {
    [l_Tier1_0] = v16:push_back_table_list(v17),
    [l_Tier2_0] = v18:push_back_table_list(v19),
    [l_Tier3_0] = v20:push_back_table_list(v21),
    [l_Tier4_0] = v22:push_back_table_list(v23),
    [l_Tier5_0] = v24:push_back_table_list(v25),
    [l_Tier6_0] = v26:push_back_table_list(v27)
}
local l_Tier1_0 = v_u_13.Tier1
local v16 = v_u_4:new()
local v17 = {
    v_u_7.RewardInfo:new(v_u_7.RewardType.Titles, 1, 5),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 75, 250),
    v_u_7.RewardInfo:new(v_u_7.RewardType.RandomLegendaryBlueprint, 1, -1),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 2, v8:get_gem_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 2, v8:get_token_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_mini_2star_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 4, v6:singleton():get_upgrade_boost_material_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.TeamContributionPoints, v9:contribution_source_to_points(v9.ContributionSource.LeaderboardClaim, 1), -1)
}
local l_Tier2_0 = v_u_13.Tier2
local v18 = v_u_4:new()
local v19 = {
    v_u_7.RewardInfo:new(v_u_7.RewardType.Titles, 1, 6),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 50, 250),
    v_u_7.RewardInfo:new(v_u_7.RewardType.RandomLegendaryBlueprint, 1, -1),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 2, v8:get_gem_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 2, v8:get_token_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_mini_2star_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 4, v6:singleton():get_upgrade_boost_material_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.TeamContributionPoints, v9:contribution_source_to_points(v9.ContributionSource.LeaderboardClaim, 20), -1)
}
local l_Tier3_0 = v_u_13.Tier3
local v20 = v_u_4:new()
local v21 = {
    v_u_7.RewardInfo:new(v_u_7.RewardType.Titles, 1, 7),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 25, 250),
    v_u_7.RewardInfo:new(v_u_7.RewardType.RandomLegendaryBlueprint, 1, -1),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_gem_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_token_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_mini_2star_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v6:singleton():get_upgrade_boost_material_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.TeamContributionPoints, v9:contribution_source_to_points(v9.ContributionSource.LeaderboardClaim, 50), -1)
}
local l_Tier4_0 = v_u_13.Tier4
local v22 = v_u_4:new()
local v23 = {
    v_u_7.RewardInfo:new(v_u_7.RewardType.Titles, 1, 8),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 15, 250),
    v_u_7.RewardInfo:new(v_u_7.RewardType.RandomLegendaryBlueprint, 1, -1),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_gem_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_token_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_mini_2star_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.TeamContributionPoints, v9:contribution_source_to_points(v9.ContributionSource.LeaderboardClaim, 200), -1)
}
local l_Tier5_0 = v_u_13.Tier5
local v24 = v_u_4:new()
local v25 = {
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 5, 250),
    v_u_7.RewardInfo:new(v_u_7.RewardType.RandomRareBlueprint, 1, -1),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_mini_1star_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_large_note_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_medium_note_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_small_note_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.TeamContributionPoints, v9:contribution_source_to_points(v9.ContributionSource.LeaderboardClaim, 400), -1)
}
local l_Tier6_0 = v_u_13.Tier6
local v26 = v_u_4:new()
local v27 = {
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, 250),
    v_u_7.RewardInfo:new(v_u_7.RewardType.RandomRareBlueprint, 1, -1),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_mini_1star_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_large_note_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_medium_note_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.CraftingMaterials, 1, v8:get_small_note_box_id()),
    v_u_7.RewardInfo:new(v_u_7.RewardType.TeamContributionPoints, v9:contribution_source_to_points(v9.ContributionSource.LeaderboardClaim, 401), -1)
}
local v_u_28 = v14:add_table(v15)
v_u_12.get_tier_for_rank = function(_, p29) --[[ Name: get_tier_for_rank ]] --[[ Line: 136 ]]
    --[[ Upvalues: (copy 1): v_u_13 ]]
    if p29 <= 0 then
        return v_u_13.Tier6;
    elseif p29 <= 1 then
        return v_u_13.Tier1;
    elseif p29 <= 20 then
        return v_u_13.Tier2;
    elseif p29 <= 50 then
        return v_u_13.Tier3;
    elseif p29 <= 200 then
        return v_u_13.Tier4;
    elseif p29 <= 400 then
        return v_u_13.Tier5;
    else
        return v_u_13.Tier6;
    end;
end;
v_u_12.get_reward_description_for_tier = function(_, p30) --[[ Name: get_reward_description_for_tier ]] --[[ Line: 170 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_12 ]]
    return v_u_7:generate_only_items_description_from_rewardinfo_list(v_u_12:get_reward_list_for_tier(p30));
end;
v_u_12.get_reward_description_for_rank = function(_, p31) --[[ Name: get_reward_description_for_rank ]] --[[ Line: 174 ]]
    --[[ Upvalues: (copy 1): v_u_12 ]]
    return v_u_12:get_reward_description_for_tier(v_u_12:get_tier_for_rank(p31));
end;
v_u_12.get_reward_list_for_tier = function(_, p32) --[[ Name: get_reward_list_for_tier ]] --[[ Line: 178 ]]
    --[[ Upvalues: (copy 1): v_u_28, (copy 2): v_u_4, (copy 3): v_u_7 ]]
    local v33 = v_u_28:get(p32)
    if v33 == nil then
        v33 = v_u_4:new()
    end;
    return v_u_7.RewardInfo:table_to_list(v_u_7.RewardInfo:list_to_table(v33));
end;
v_u_12.apply_rewards_for_claims = function(_, p34, p35, p36, p37, p38, p_u_39) --[[ Name: apply_rewards_for_claims ]] --[[ Line: 184 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_10, (copy 3): v_u_1, (copy 4): v_u_2, (copy 5): v_u_12, (copy 6): v_u_7, (copy 7): v_u_5 ]]
    local v_u_40 = v_u_4:new()
    local v41 = {}
    for v42 = 1, #p37 do
        local v43 = p37[v42]
        local l_Rank_0 = v43.Rank
        if l_Rank_0 == 0 then
            v_u_10:warnf("LeaderboardRewards:apply_rewards_for_claims claim_rank(%d)", l_Rank_0)
            l_Rank_0 = 500
            v43.Rank = l_Rank_0
        end;
        local l_Week_0 = v43.Week
        local l_SongKey_0 = v43.SongKey
        v_u_1:is_int(l_Rank_0)
        v_u_1:is_int(l_Week_0)
        v_u_1:is_true(v_u_2:singleton():contains_key(l_SongKey_0))
        p38(l_Rank_0, l_Week_0, l_SongKey_0)
        local v44 = v_u_12:get_reward_list_for_tier((v_u_12:get_tier_for_rank(l_Rank_0)))
        local v45 = v_u_4:new()
        v41.ResolvedRewardList = v45
        v_u_7:claim_reward_info_list_to_playerblob(p34, p36, v44, v41)
        v_u_40:push_back({
            ["Message"] = string.format("For placing %s in the week %d leaderboard for \"%s\", you got...", v_u_5:num_placify(v43.Rank), l_Week_0, v_u_2:singleton():get_title_for_key(l_SongKey_0)),
            ["RewardListTable"] = v_u_7.RewardInfo:list_to_table(v45)
        })
    end;
    v_u_7:server_sync_reward_params(p34, p35, v41, function() --[[ Line: 222 ]]
        --[[ Upvalues: (copy 1): p_u_39, (copy 2): v_u_40 ]]
        p_u_39(v_u_40:get_table())
    end)
end;
return v_u_12;
