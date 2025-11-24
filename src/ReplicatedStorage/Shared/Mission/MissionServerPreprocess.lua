-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:12 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPList)
local v_u_1 = require(game.ReplicatedStorage.Shared.MissionTimeframe)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.Shared.MissionType)
local v_u_3 = require(game.ReplicatedStorage.Shared.MissionDifficulty)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_5 = require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_8 = require(game.ReplicatedStorage.Shared.Mission.GearPowerScoreMultiplierCalculation)
local v_u_9 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.BoxInfo)
local v_u_11 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_12 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.MissionMPRewardFlag)
local v14 = {}
local function f_convert_to_rank_mission(p15) --[[ Name: convert_to_rank_mission ]] --[[ Line: 20 ]]
    --[[ Upvalues: (copy 1): v_u_7, (copy 2): v_u_3, (copy 3): v_u_2 ]]
    local l_RankAPlus_0 = v_u_7.Value.RankAPlus
    if p15:get_difficulty() == v_u_3.Beginner then
        l_RankAPlus_0 = v_u_7.Value.RankD
    elseif p15:get_difficulty() == v_u_3.Novice then
        l_RankAPlus_0 = v_u_7.Value.RankC
    elseif p15:get_difficulty() == v_u_3.Amateur then
        l_RankAPlus_0 = v_u_7.Value.RankB
    elseif p15:get_difficulty() == v_u_3.Pro then
        l_RankAPlus_0 = v_u_7.Value.RankA
    elseif p15:get_difficulty() == v_u_3.Star then
        l_RankAPlus_0 = v_u_7.Value.RankAPlus
    end;
    p15:set_type(v_u_2.Rank)
    p15:set_count(v_u_7:rank_value_to_index(l_RankAPlus_0))
end;
local function f_calculate_reward_for_timeframe_and_mission_data(p_u_16, p_u_17) --[[ Name: calculate_reward_for_timeframe_and_mission_data ]] --[[ Line: 38 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_1, (copy 5): v_u_12, (copy 6): v_u_10 ]]
    local function _() --[[ Name: has_set_rewards ]] --[[ Line: 39 ]]
        --[[ Upvalues: (copy 1): p_u_17 ]]
        return p_u_17:get_reward_desc_info_list():count() > 0;
    end;
    local function _(p18) --[[ Name: add_coins_reward ]] --[[ Line: 42 ]]
        --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_4 ]]
        p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Coins, p18, -1))
    end;
    local function _(p19) --[[ Name: add_stars_reward ]] --[[ Line: 45 ]]
        --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_4 ]]
        p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Stars, p19, -1))
    end;
    local function f_add_standard_team_contribution_point_reward() --[[ Name: add_standard_team_contribution_point_reward ]] --[[ Line: 48 ]]
        --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_2, (ref 3): v_u_3, (ref 4): v_u_4, (copy 5): p_u_16, (ref 6): v_u_1, (ref 7): v_u_12 ]]
        if p_u_17:get_type() == v_u_2.NoMiss then
            if p_u_17:get_difficulty() == v_u_3.Star then
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.TeamContributionPointsFromDailySongMission, 250, -1))
                return;
            elseif p_u_17:get_difficulty() == v_u_3.Pro then
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.TeamContributionPointsFromDailySongMission, 200, -1))
            else
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.TeamContributionPointsFromDailySongMission, 150, -1))
            end;
        elseif p_u_17:get_type() == v_u_2.CompleteMatch and p_u_17:has_target_song() ~= true then
            if p_u_17:get_players_required() > 0 then
                if p_u_17:get_difficulty() == v_u_3.Pro then
                    p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.TeamContributionPoints, 200, -1))
                    return;
                elseif p_u_17:get_difficulty() == v_u_3.Amateur then
                    p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.TeamContributionPoints, 150, -1))
                else
                    p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.TeamContributionPoints, 100, -1))
                end;
            elseif p_u_17:get_difficulty() == v_u_3.Amateur then
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.TeamContributionPoints, 100, -1))
                return;
            elseif p_u_17:get_difficulty() == v_u_3.Novice then
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.TeamContributionPoints, 50, -1))
            else
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.TeamContributionPoints, 25, -1))
            end;
        else
            local v20 = 0
            if p_u_16 == v_u_1.Daily then
                v20 = v_u_12:contribution_source_to_points(v_u_12.ContributionSource.DailyMissionClaim, p_u_17:get_difficulty())
            elseif p_u_16 == v_u_1.Weekly then
                v20 = v_u_12:contribution_source_to_points(v_u_12.ContributionSource.WeeklyMissionClaim, p_u_17:get_difficulty())
            end;
            if p_u_17:get_type() == v_u_2.Rank then
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.TeamContributionPointsFromDailySongMission, v20, -1))
            else
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.TeamContributionPoints, v20, -1))
            end;
        end;
    end;
    local function f_add_no_miss_mission_reward() --[[ Name: add_no_miss_mission_reward ]] --[[ Line: 89 ]]
        --[[ Upvalues: (copy 1): p_u_17, (ref 2): v_u_2, (ref 3): v_u_3, (ref 4): v_u_4 ]]
        if p_u_17:get_type() == v_u_2.NoMiss then
            if p_u_17:get_difficulty() == v_u_3.Star then
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 131))
                return;
            end;
            if p_u_17:get_difficulty() == v_u_3.Pro then
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 130))
                return;
            end;
            p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Titles, 1, 129))
        end;
    end;
    if p_u_17:get_reward_desc_info_list():count() > 0 ~= true then
        if p_u_17:get_type() == v_u_2.Cheer then
            p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Coins, 500, -1))
        elseif p_u_17:get_type() == v_u_2.NoteMachine then
            p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.CraftingMaterials, 1, v_u_10:get_gem_box_id()))
        elseif p_u_17:get_type() == v_u_2.StarMachine then
            p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Coins, 500, -1))
        elseif p_u_17:get_type() == v_u_2.UpgradeGear then
            p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Stars, 2, -1))
        elseif p_u_17:get_type() == v_u_2.CombineSong then
            p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Stars, 2, -1))
        elseif p_u_17:get_type() == v_u_2.PointTotal then
            p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.RandomToken, 1, -1))
        elseif p_u_17:get_type() == v_u_2.NoMiss then
            if p_u_17:get_difficulty() == v_u_3.Star then
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Coins, 400, -1))
            elseif p_u_17:get_difficulty() == v_u_3.Pro then
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Coins, 350, -1))
            else
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Coins, 300, -1))
            end;
        end;
    end;
    if p_u_17:get_reward_desc_info_list():count() > 0 ~= true then
        if p_u_17:get_difficulty() == v_u_3.Beginner then
            if p_u_17:has_target_song() then
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Coins, 100, -1))
            else
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Stars, 1, -1))
            end;
        elseif p_u_17:get_difficulty() == v_u_3.Novice then
            if p_u_17:has_target_song() then
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Coins, 125, -1))
            else
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Stars, 1, -1))
            end;
        elseif p_u_17:get_difficulty() == v_u_3.Amateur then
            if p_u_17:has_target_song() then
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Coins, 150, -1))
            else
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Stars, 2, -1))
            end;
        elseif p_u_17:get_difficulty() == v_u_3.Pro then
            if p_u_17:has_target_song() then
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Coins, 175, -1))
            else
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Stars, 3, -1))
            end;
        elseif p_u_17:get_difficulty() == v_u_3.Star then
            if p_u_17:has_target_song() then
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Coins, 200, -1))
            else
                p_u_17:push_reward_desc_info(v_u_4.RewardInfo:new(v_u_4.RewardType.Stars, 3, -1))
            end;
        end;
    end;
    f_add_standard_team_contribution_point_reward()
    f_add_no_miss_mission_reward()
end;
local function _(p21, p22) --[[ Name: convert_reward_to_reward_description_info ]] --[[ Line: 178 ]]
    --[[ Upvalues: (copy 1): f_calculate_reward_for_timeframe_and_mission_data, (copy 2): v_u_5 ]]
    f_calculate_reward_for_timeframe_and_mission_data(p21, p22)
    p22:set_legacy_reward_type_and_amount(v_u_5.RewardType.UseRewardDescriptionInfo, 0)
end;
v14.preprocess_mission_data = function(_, p23) --[[ Name: preprocess_mission_data ]] --[[ Line: 183 ]]
    --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_6, (copy 4): f_convert_to_rank_mission, (copy 5): f_calculate_reward_for_timeframe_and_mission_data, (copy 6): v_u_5, (copy 7): v_u_8, (copy 8): v_u_9, (copy 9): v_u_4, (copy 10): v_u_11, (copy 11): v_u_3, (copy 12): v_u_13 ]]
    for _, v24 in v_u_1:get_all():key_itr() do
        for _, v25 in p23:get_mission_list_for_timeframe(v24):key_itr() do
            if v25:has_target_song() then
                if v25:get_type() == v_u_2.Score then
                    if v25:get_song_naked_max_score() > 0 then
                        v_u_8:calculate_score_mission(v25)
                        break;
                    end;
                    v_u_6:warnf("MissionServerPreprocess song_naked_max_score is 0 for daily mission[Type.Score](%d), converting to rank mission", v25:get_id())
                    f_convert_to_rank_mission(v25)
                    f_calculate_reward_for_timeframe_and_mission_data(v24, v25)
                    v25:set_legacy_reward_type_and_amount(v_u_5.RewardType.UseRewardDescriptionInfo, 0)
                else
                    if v25:get_type() ~= v_u_2.PointTotal then
                        break;
                    end;
                    if v_u_9.DebugDoNotConvertPointTotalMission == true then
                        v_u_6:warnf("MissionServerPreprocess DebugDoNotConvertPointTotalMission is true, not converting point total mission(%d)", v25:get_id())
                    else
                        if v25:get_song_naked_max_score() > 0 then
                            v_u_8:calculate_point_total_mission(v25)
                            break;
                        end;
                        v_u_6:warnf("MissionServerPreprocess song_naked_max_score is 0 for weekly mission[Type.PointTotal](%d), converting to rank mission", v25:get_id())
                        f_convert_to_rank_mission(v25)
                        f_calculate_reward_for_timeframe_and_mission_data(v24, v25)
                        v25:set_legacy_reward_type_and_amount(v_u_5.RewardType.UseRewardDescriptionInfo, 0)
                    end;
                end;
            else
                -- ::l6:: (Possible bug with goto)
                f_calculate_reward_for_timeframe_and_mission_data(v24, v25)
                v25:set_legacy_reward_type_and_amount(v_u_5.RewardType.UseRewardDescriptionInfo, 0)
            end;
        end;
    end;
    if v_u_9.UseScaledScoreMission then
        for _, v26 in v_u_1:get_all():key_itr() do
            for _, v27 in p23:get_mission_list_for_timeframe(v26):key_itr() do
                if v27:has_target_song() and (v27:get_type() == v_u_2.Score or (v27:get_type() == v_u_2.Rank or (v27:get_type() == v_u_2.CompleteMatch or v27:get_type() == v_u_2.ScaledScore))) then
                    if v27:get_song_naked_max_score() > 0 then
                        v27:set_type(v_u_2.ScaledScore)
                        v27:set_count(1)
                        v27:get_first_team_contribution_point_reward_desc():set_type(v_u_4.RewardType.TeamContributionPointsFromDailySongMission)
                    else
                        f_convert_to_rank_mission(v27)
                        v_u_6:puts("Mission(%s) does not have song_naked_max set, not converting to ScaledScore", v_u_11:table_to_string(v27:to_table()))
                    end;
                end;
            end;
        end;
    end;
    if v_u_9.UseMissionMPRewardFlag then
        local v28 = p23:get_mission_list_for_timeframe(v_u_1.Daily)
        local v29 = false
        local v30 = false
        local v31 = false
        for _, v32 in v28:key_itr() do
            if v32:get_type() == v_u_2.CompleteMatch and v32:get_players_required() >= 3 then
                if v32:get_difficulty() == v_u_3.Novice then
                    v32:get_reward_desc_info_list():clear()
                    v32:get_reward_desc_info_list():push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.MissionMPReward, 1, v_u_13.Flag.MissionMPReward1))
                    v29 = true
                elseif v32:get_difficulty() == v_u_3.Amateur then
                    v32:get_reward_desc_info_list():clear()
                    v32:get_reward_desc_info_list():push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.MissionMPReward, 1, v_u_13.Flag.MissionMPReward2))
                    v30 = true
                else
                    v32:get_reward_desc_info_list():clear()
                    v32:get_reward_desc_info_list():push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.MissionMPReward, 1, v_u_13.Flag.MissionMPReward3))
                    v31 = true
                end;
            elseif v32:get_type() == v_u_2.LikeCustomMap then
                if v32:get_difficulty() == v_u_3.Pro then
                    v32:get_reward_desc_info_list():clear()
                    v32:get_reward_desc_info_list():push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.MissionMPReward, 1, v_u_13.Flag.MissionMPReward3))
                elseif v32:get_difficulty() == v_u_3.Amateur then
                    v32:get_reward_desc_info_list():clear()
                    v32:get_reward_desc_info_list():push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.MissionMPReward, 1, v_u_13.Flag.MissionMPReward2))
                else
                    v32:get_reward_desc_info_list():clear()
                    v32:get_reward_desc_info_list():push_back(v_u_4.RewardInfo:new(v_u_4.RewardType.MissionMPReward, 1, v_u_13.Flag.MissionMPReward1))
                end;
            end;
        end;
        if v28:count() > 0 and not (v29 and (v30 and v31)) then
            v_u_6:warnf("MissionServerPreprocess: UseMissionMPRewardFlag Missing 3P missions for Daily timeframe, found novice: %s, amateur: %s, pro: %s", tostring(v29), tostring(v30), (tostring(v31)))
        end;
    end;
    for _, v33 in v_u_1:get_all():key_itr() do
        p23:get_mission_list_for_timeframe(v33):sort(function(p34, p35) --[[ Line: 305 ]]
            return p34:get_id() - p35:get_id();
        end)
    end;
end;
return v14;
