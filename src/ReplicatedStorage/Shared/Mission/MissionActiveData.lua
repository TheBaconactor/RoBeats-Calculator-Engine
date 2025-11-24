-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:12 PM
-- Time elapsed: 13 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.MissionTimeframe)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.Shared.MissionType)
local v_u_5 = require(game.ReplicatedStorage.Shared.MissionDifficulty)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_7 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_8 = require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_10 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.MissionMPRewardFlag)
local v12 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_13 = nil
local v_u_14 = nil
v12:require_shared(function() --[[ Line: 16 ]]
    --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_13 ]]
    v_u_14 = require(game.ReplicatedStorage.Shared.GuildUtil)
    v_u_13 = require(game.ReplicatedStorage.Shared.Mission.ScaledScoreMissionUtil)
end)
local v_u_82 = {
    ["MissionData"] = {
        ["new"] = function(_, p_u_83) --[[ Name: new ]] --[[ Line: 27 ]]
            --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_5, (copy 4): v_u_6, (copy 5): v_u_8, (copy 6): v_u_1, (copy 7): v_u_7, (ref 8): v_u_13, (copy 9): v_u_9 ]]
            v_u_3:is_int(p_u_83)
            local v84 = {}
            local l_CompleteMatch_1 = v_u_4.CompleteMatch
            local l_Beginner_1 = v_u_5.Beginner
            local v_u_85 = v_u_6:invalid_songkey()
            local v_u_86 = 1
            local v_u_87 = 1
            local l_UseRewardDescriptionInfo_1 = v_u_8.RewardType.UseRewardDescriptionInfo
            local v_u_88 = 0
            local v_u_89 = v_u_1:new()
            local v_u_90 = 0
            v84.get_id = function(_) --[[ Name: get_id ]] --[[ Line: 42 ]]
                --[[ Upvalues: (copy 1): p_u_83 ]]
                return p_u_83;
            end;
            v84.get_type = function(_) --[[ Name: get_type ]] --[[ Line: 43 ]]
                --[[ Upvalues: (ref 1): l_CompleteMatch_1 ]]
                return l_CompleteMatch_1;
            end;
            v84.get_difficulty = function(_) --[[ Name: get_difficulty ]] --[[ Line: 44 ]]
                --[[ Upvalues: (ref 1): l_Beginner_1 ]]
                return l_Beginner_1;
            end;
            v84.get_target_song = function(_) --[[ Name: get_target_song ]] --[[ Line: 45 ]]
                --[[ Upvalues: (ref 1): v_u_85 ]]
                return v_u_85;
            end;
            v84.has_target_song = function(_) --[[ Name: has_target_song ]] --[[ Line: 46 ]]
                --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_85 ]]
                return v_u_6:singleton():contains_key(v_u_85);
            end;
            v84.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 47 ]]
                --[[ Upvalues: (ref 1): v_u_86 ]]
                return v_u_86;
            end;
            v84.get_players_required = function(_) --[[ Name: get_players_required ]] --[[ Line: 48 ]]
                --[[ Upvalues: (ref 1): v_u_87 ]]
                return v_u_87;
            end;
            v84.get_legacy_reward_type = function(_) --[[ Name: get_legacy_reward_type ]] --[[ Line: 49 ]]
                --[[ Upvalues: (ref 1): l_UseRewardDescriptionInfo_1 ]]
                return l_UseRewardDescriptionInfo_1;
            end;
            v84.get_legacy_reward_amount = function(_) --[[ Name: get_legacy_reward_amount ]] --[[ Line: 50 ]]
                --[[ Upvalues: (ref 1): v_u_88 ]]
                return v_u_88;
            end;
            v84.get_reward_desc_info_list = function(_) --[[ Name: get_reward_desc_info_list ]] --[[ Line: 51 ]]
                --[[ Upvalues: (copy 1): v_u_89 ]]
                return v_u_89;
            end;
            v84.get_song_naked_max_score = function(_) --[[ Name: get_song_naked_max_score ]] --[[ Line: 52 ]]
                --[[ Upvalues: (ref 1): v_u_90 ]]
                return v_u_90;
            end;
            v84.set_type = function(_, p91) --[[ Name: set_type ]] --[[ Line: 54 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_4, (ref 3): l_CompleteMatch_1 ]]
                v_u_3:is_enum_member(p91, v_u_4)
                l_CompleteMatch_1 = p91
            end;
            v84.set_difficulty = function(_, p92) --[[ Name: set_difficulty ]] --[[ Line: 55 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_5, (ref 3): l_Beginner_1 ]]
                v_u_3:is_enum_member(p92, v_u_5)
                l_Beginner_1 = p92
            end;
            v84.set_target_song = function(_, p93) --[[ Name: set_target_song ]] --[[ Line: 56 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_6, (ref 3): v_u_85 ]]
                v_u_3:is_true(p93 == v_u_6:invalid_songkey() and true or v_u_6:singleton():contains_key(p93))
                v_u_85 = p93
            end;
            v84.set_count = function(_, p94) --[[ Name: set_count ]] --[[ Line: 57 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_86 ]]
                v_u_3:is_int(p94)
                v_u_86 = p94
            end;
            v84.set_players_required = function(_, p95) --[[ Name: set_players_required ]] --[[ Line: 58 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_87 ]]
                v_u_3:is_int(p95)
                v_u_87 = p95
            end;
            v84.set_legacy_reward_type_and_amount = function(_, p96, p97) --[[ Name: set_legacy_reward_type_and_amount ]] --[[ Line: 59 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_8, (ref 3): l_UseRewardDescriptionInfo_1, (ref 4): v_u_88 ]]
                v_u_3:is_enum_member(p96, v_u_8.RewardType)
                v_u_3:is_int(p97)
                l_UseRewardDescriptionInfo_1 = p96
                v_u_88 = p97
            end;
            v84.push_reward_desc_info = function(_, p98) --[[ Name: push_reward_desc_info ]] --[[ Line: 65 ]]
                --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_89 ]]
                v_u_3:is_non_nil(p98.get_name)
                v_u_89:push_back(p98)
            end;
            v84.set_song_naked_max_score = function(_, p99) --[[ Name: set_song_naked_max_score ]] --[[ Line: 66 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_90 ]]
                v_u_3:is_int(p99)
                v_u_90 = p99
            end;
            v84.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 68 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_89, (copy 3): p_u_83, (ref 4): l_CompleteMatch_1, (ref 5): l_Beginner_1, (ref 6): v_u_85, (ref 7): v_u_86, (ref 8): v_u_87, (ref 9): l_UseRewardDescriptionInfo_1, (ref 10): v_u_88, (ref 11): v_u_90 ]]
                local v100 = v_u_1:new()
                for _, v101 in v_u_89:key_itr() do
                    v100:push_back(v101:to_table())
                end;
                return {
                    ["ID"] = p_u_83,
                    ["Type"] = l_CompleteMatch_1,
                    ["Difficulty"] = l_Beginner_1,
                    ["TargetSong"] = v_u_85,
                    ["Count"] = v_u_86,
                    ["PlayersRequired"] = v_u_87,
                    ["RewardType"] = l_UseRewardDescriptionInfo_1,
                    ["RewardAmount"] = v_u_88,
                    ["RewardDescInfoList"] = v100:get_table(),
                    ["SongNakedMaxScore"] = v_u_90
                };
            end;
            local function f_get_first_reward_desc_of_type(p102) --[[ Name: get_first_reward_desc_of_type ]] --[[ Line: 88 ]]
                --[[ Upvalues: (copy 1): v_u_89, (ref 2): v_u_7 ]]
                local v103 = nil
                for _, v104 in v_u_89:key_itr() do
                    if p102(v104) then
                        v103 = v104
                        break;
                    end;
                end;
                if v103 == nil then
                    v103 = v_u_7.RewardInfo:new(v_u_7.RewardType.None, 0, -1)
                end;
                return v103;
            end;
            local function _() --[[ Name: get_first_item_reward_desc ]] --[[ Line: 102 ]]
                --[[ Upvalues: (copy 1): f_get_first_reward_desc_of_type, (ref 2): v_u_7 ]]
                return f_get_first_reward_desc_of_type(function(p105) --[[ Line: 103 ]]
                    --[[ Upvalues: (ref 1): v_u_7 ]]
                    return v_u_7.RewardType:is_type_team_contribution_points(p105:get_type()) ~= true;
                end);
            end;
            v84.get_reward_image = function(_) --[[ Name: get_reward_image ]] --[[ Line: 106 ]]
                --[[ Upvalues: (copy 1): f_get_first_reward_desc_of_type, (ref 2): v_u_7 ]]
                return f_get_first_reward_desc_of_type(function(p106) --[[ Line: 103 ]]
                    --[[ Upvalues: (ref 1): v_u_7 ]]
                    return v_u_7.RewardType:is_type_team_contribution_points(p106:get_type()) ~= true;
                end):get_image();
            end;
            v84.get_reward_amount = function(_) --[[ Name: get_reward_amount ]] --[[ Line: 107 ]]
                --[[ Upvalues: (copy 1): f_get_first_reward_desc_of_type, (ref 2): v_u_7 ]]
                return f_get_first_reward_desc_of_type(function(p107) --[[ Line: 103 ]]
                    --[[ Upvalues: (ref 1): v_u_7 ]]
                    return v_u_7.RewardType:is_type_team_contribution_points(p107:get_type()) ~= true;
                end):get_amount();
            end;
            v84.get_reward_display_amount_for_playerblob_and_timeframe = function(p108, p109, p110) --[[ Name: get_reward_display_amount_for_playerblob_and_timeframe ]] --[[ Line: 108 ]]
                --[[ Upvalues: (copy 1): f_get_first_reward_desc_of_type, (ref 2): v_u_7, (ref 3): v_u_4, (ref 4): v_u_8, (ref 5): v_u_13, (ref 6): v_u_9 ]]
                local v112 = f_get_first_reward_desc_of_type(function(p111) --[[ Line: 103 ]]
                    --[[ Upvalues: (ref 1): v_u_7 ]]
                    return v_u_7.RewardType:is_type_team_contribution_points(p111:get_type()) ~= true;
                end):get_amount()
                local v113 = tostring(v112)
                if p108:get_type() == v_u_4.ScaledScore then
                    local v114 = v_u_13:get_tier_id_reward_scale((v_u_13:mission_data_get_score_tier_id(p108, (v_u_8:playerblob_missionid_get_count(p109, p110, p108:get_id())))))
                    if v114 == 1 then
                        return string.format("%s (x1)", v_u_9:comma_value(v_u_13:get_scaled_amount_for_multiplier(v112, v114)));
                    end;
                    v113 = string.format("%s (x%.2f)", v_u_9:comma_value(v_u_13:get_scaled_amount_for_multiplier(v112, v114)), v114)
                end;
                return v113;
            end;
            v84.get_first_team_contribution_point_reward_desc = function(_) --[[ Name: get_first_team_contribution_point_reward_desc ]] --[[ Line: 125 ]]
                --[[ Upvalues: (copy 1): f_get_first_reward_desc_of_type, (ref 2): v_u_7 ]]
                return f_get_first_reward_desc_of_type(function(p115) --[[ Line: 126 ]]
                    --[[ Upvalues: (ref 1): v_u_7 ]]
                    return v_u_7.RewardType:is_type_team_contribution_points(p115:get_type());
                end);
            end;
            return v84;
        end
    },
    ["new"] = function(_, p_u_48, p_u_49) --[[ Name: new ]] --[[ Line: 149 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_2 ]]
        v_u_3:is_int(p_u_48)
        v_u_3:is_int(p_u_49)
        local v55 = {
            ["get_mission_data_for_timeframe_and_id"] = function(p50, p51, p52) --[[ Name: get_mission_data_for_timeframe_and_id ]] --[[ Line: 169 ]]
                local v53 = nil
                for _, v54 in p50:get_mission_list_for_timeframe(p51):key_itr() do
                    if v54:get_id() == p52 then
                        return v54;
                    end;
                end;
                return v53;
            end
        }
        local v_u_56 = v_u_1:new()
        local v_u_57 = v_u_1:new()
        v55.get_daily_missions = function(_) --[[ Name: get_daily_missions ]] --[[ Line: 158 ]]
            --[[ Upvalues: (copy 1): v_u_56 ]]
            return v_u_56;
        end;
        v55.get_weekly_missions = function(_) --[[ Name: get_weekly_missions ]] --[[ Line: 159 ]]
            --[[ Upvalues: (copy 1): v_u_57 ]]
            return v_u_57;
        end;
        v55.get_mission_list_for_timeframe = function(_, p58) --[[ Name: get_mission_list_for_timeframe ]] --[[ Line: 161 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_57, (copy 3): v_u_56 ]]
            if p58 == v_u_2.Weekly then
                return v_u_57;
            else
                return v_u_56;
            end;
        end;
        v55.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 181 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_56, (copy 3): v_u_57, (copy 4): p_u_48, (copy 5): p_u_49 ]]
            local v59 = v_u_1:new()
            for _, v60 in v_u_56:key_itr() do
                v59:push_back(v60:to_table())
            end;
            local v61 = v_u_1:new()
            for _, v62 in v_u_57:key_itr() do
                v61:push_back(v62:to_table())
            end;
            return {
                ["Day"] = p_u_48,
                ["Week"] = p_u_49,
                ["Daily"] = v59:get_table(),
                ["Weekly"] = v61:get_table()
            };
        end;
        return v55;
    end,
    ["get_playerblob_mission_data_display_text"] = function(_, p63, p64, p65, p66) --[[ Name: get_playerblob_mission_data_display_text ]] --[[ Line: 226 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_8, (copy 3): v_u_9, (copy 4): v_u_4, (ref 5): v_u_13, (copy 6): v_u_7, (ref 7): v_u_14, (copy 8): v_u_11 ]]
        local v67 = p64:to_table()
        local v68 = ("" .. string.format("<b>Mission Rank</b>: %s\n", v_u_5:difficulty_to_string((p64:get_difficulty())))) .. string.format("<b>Description</b>: %s\n", v_u_8:get_mission_description_text(v67))
        local v69 = v_u_8:get_mission_hint_text(v67)
        if #v69 > 0 then
            v68 = v68 .. string.format("<b>Hint</b>: %s\n", v69)
        end;
        if p64:has_target_song() and p64:get_song_naked_max_score() ~= 0 then
            v68 = v68 .. string.format("<b>Song Casual Mode Max Score</b>: %s\n", v_u_9:comma_value(p64:get_song_naked_max_score()))
        end;
        local v70 = v68 .. string.format("<b>Progress</b>: %s\n", v_u_8:get_playerblob_mission_progress_text(p63, v67, p65))
        local v71
        if p64:get_type() == v_u_4.ScaledScore then
            local v72 = v_u_8:playerblob_missionid_get_count(p63, p65, p64:get_id())
            local v73 = v_u_13:get_tier_id_reward_scale((v_u_13:mission_data_get_score_tier_id(p64, v72)))
            if v72 > 0 then
                v71 = (v70 .. string.format("<b>Rewards</b>: %s\n", v_u_7:generate_only_items_description_from_rewardinfo_list((v_u_13:get_playerblob_mission_data_timeframe_reward_desc_info_list_scaled(p63, p64, p65, p64:get_reward_desc_info_list()))))) .. string.format("<b>Reward Multiplier</b>: x%.2f (Score: %s)\n", v73, v_u_9:comma_value(v72))
            else
                v71 = v70 .. string.format("<b>Rewards (Scaled to your final score)</b>: %s\n", v_u_7:generate_only_items_description_from_rewardinfo_list(p64:get_reward_desc_info_list()))
            end;
        else
            v71 = v70 .. string.format("<b>Reward(s)</b>: %s\n", v_u_7:generate_only_items_description_from_rewardinfo_list(p64:get_reward_desc_info_list()))
        end;
        if p64:get_first_team_contribution_point_reward_desc():get_type() == v_u_7.RewardType.TeamContributionPointsFromDailySongMission then
            v71 = v71 .. string.format("<b>Daily Team Contribution Points from Song Missions</b>: %d / %d", v_u_14:playerblob_get_current_day_team_contribution_point_amount_from_daily_song_missions(p63, p66), v_u_14:get_max_team_contribution_point_cap_from_daily_song_missions())
        end;
        local v74 = p64:get_reward_desc_info_list()
        if v74:count() > 0 then
            local v75 = v74:get(1)
            if v75:get_type() == v_u_7.RewardType.MissionMPReward then
                v71 = v71 .. string.format("<b>Claimed for today</b>: %s\n", (tostring(v_u_11:playerblob_has_flag_set(p63, v75:get_id(), p66))))
            end;
        end;
        return v71;
    end,
    ["playerblob_get_remaining_missions_of_playerblob_difficulty_to_rank_upgrade"] = function(_, p76, p77) --[[ Name: playerblob_get_remaining_missions_of_playerblob_difficulty_to_rank_upgrade ]] --[[ Line: 283 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_8 ]]
        local l_Daily_0 = v_u_2.Daily
        local v78 = v_u_8:playerblob_get_mission_difficulty(p77)
        local v79 = 0
        local v80 = 0
        for _, v81 in p76:get_mission_list_for_timeframe(l_Daily_0):key_itr() do
            if v81:get_difficulty() == v78 then
                v79 = v79 + 1
                if v_u_8:playerblob_get_missionid_completed(p77, l_Daily_0, v81:get_id()) then
                    v80 = v80 + 1
                end;
            end;
        end;
        return math.max(math.min(3, v79) - v80, 0), v80, 3;
    end
}
local v_u_116 = {
    ["new"] = function(_, p_u_83) --[[ Name: new ]] --[[ Line: 27 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_5, (copy 4): v_u_6, (copy 5): v_u_8, (copy 6): v_u_1, (copy 7): v_u_7, (ref 8): v_u_13, (copy 9): v_u_9 ]]
        v_u_3:is_int(p_u_83)
        local v84 = {}
        local l_CompleteMatch_1 = v_u_4.CompleteMatch
        local l_Beginner_1 = v_u_5.Beginner
        local v_u_85 = v_u_6:invalid_songkey()
        local v_u_86 = 1
        local v_u_87 = 1
        local l_UseRewardDescriptionInfo_1 = v_u_8.RewardType.UseRewardDescriptionInfo
        local v_u_88 = 0
        local v_u_89 = v_u_1:new()
        local v_u_90 = 0
        v84.get_id = function(_) --[[ Name: get_id ]] --[[ Line: 42 ]]
            --[[ Upvalues: (copy 1): p_u_83 ]]
            return p_u_83;
        end;
        v84.get_type = function(_) --[[ Name: get_type ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): l_CompleteMatch_1 ]]
            return l_CompleteMatch_1;
        end;
        v84.get_difficulty = function(_) --[[ Name: get_difficulty ]] --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): l_Beginner_1 ]]
            return l_Beginner_1;
        end;
        v84.get_target_song = function(_) --[[ Name: get_target_song ]] --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_85 ]]
            return v_u_85;
        end;
        v84.has_target_song = function(_) --[[ Name: has_target_song ]] --[[ Line: 46 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_85 ]]
            return v_u_6:singleton():contains_key(v_u_85);
        end;
        v84.get_count = function(_) --[[ Name: get_count ]] --[[ Line: 47 ]]
            --[[ Upvalues: (ref 1): v_u_86 ]]
            return v_u_86;
        end;
        v84.get_players_required = function(_) --[[ Name: get_players_required ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_87 ]]
            return v_u_87;
        end;
        v84.get_legacy_reward_type = function(_) --[[ Name: get_legacy_reward_type ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): l_UseRewardDescriptionInfo_1 ]]
            return l_UseRewardDescriptionInfo_1;
        end;
        v84.get_legacy_reward_amount = function(_) --[[ Name: get_legacy_reward_amount ]] --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): v_u_88 ]]
            return v_u_88;
        end;
        v84.get_reward_desc_info_list = function(_) --[[ Name: get_reward_desc_info_list ]] --[[ Line: 51 ]]
            --[[ Upvalues: (copy 1): v_u_89 ]]
            return v_u_89;
        end;
        v84.get_song_naked_max_score = function(_) --[[ Name: get_song_naked_max_score ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_90 ]]
            return v_u_90;
        end;
        v84.set_type = function(_, p91) --[[ Name: set_type ]] --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_4, (ref 3): l_CompleteMatch_1 ]]
            v_u_3:is_enum_member(p91, v_u_4)
            l_CompleteMatch_1 = p91
        end;
        v84.set_difficulty = function(_, p92) --[[ Name: set_difficulty ]] --[[ Line: 55 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_5, (ref 3): l_Beginner_1 ]]
            v_u_3:is_enum_member(p92, v_u_5)
            l_Beginner_1 = p92
        end;
        v84.set_target_song = function(_, p93) --[[ Name: set_target_song ]] --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_6, (ref 3): v_u_85 ]]
            v_u_3:is_true(p93 == v_u_6:invalid_songkey() and true or v_u_6:singleton():contains_key(p93))
            v_u_85 = p93
        end;
        v84.set_count = function(_, p94) --[[ Name: set_count ]] --[[ Line: 57 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_86 ]]
            v_u_3:is_int(p94)
            v_u_86 = p94
        end;
        v84.set_players_required = function(_, p95) --[[ Name: set_players_required ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_87 ]]
            v_u_3:is_int(p95)
            v_u_87 = p95
        end;
        v84.set_legacy_reward_type_and_amount = function(_, p96, p97) --[[ Name: set_legacy_reward_type_and_amount ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_8, (ref 3): l_UseRewardDescriptionInfo_1, (ref 4): v_u_88 ]]
            v_u_3:is_enum_member(p96, v_u_8.RewardType)
            v_u_3:is_int(p97)
            l_UseRewardDescriptionInfo_1 = p96
            v_u_88 = p97
        end;
        v84.push_reward_desc_info = function(_, p98) --[[ Name: push_reward_desc_info ]] --[[ Line: 65 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_89 ]]
            v_u_3:is_non_nil(p98.get_name)
            v_u_89:push_back(p98)
        end;
        v84.set_song_naked_max_score = function(_, p99) --[[ Name: set_song_naked_max_score ]] --[[ Line: 66 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_90 ]]
            v_u_3:is_int(p99)
            v_u_90 = p99
        end;
        v84.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 68 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_89, (copy 3): p_u_83, (ref 4): l_CompleteMatch_1, (ref 5): l_Beginner_1, (ref 6): v_u_85, (ref 7): v_u_86, (ref 8): v_u_87, (ref 9): l_UseRewardDescriptionInfo_1, (ref 10): v_u_88, (ref 11): v_u_90 ]]
            local v100 = v_u_1:new()
            for _, v101 in v_u_89:key_itr() do
                v100:push_back(v101:to_table())
            end;
            return {
                ["ID"] = p_u_83,
                ["Type"] = l_CompleteMatch_1,
                ["Difficulty"] = l_Beginner_1,
                ["TargetSong"] = v_u_85,
                ["Count"] = v_u_86,
                ["PlayersRequired"] = v_u_87,
                ["RewardType"] = l_UseRewardDescriptionInfo_1,
                ["RewardAmount"] = v_u_88,
                ["RewardDescInfoList"] = v100:get_table(),
                ["SongNakedMaxScore"] = v_u_90
            };
        end;
        local function f_get_first_reward_desc_of_type(p102) --[[ Name: get_first_reward_desc_of_type ]] --[[ Line: 88 ]]
            --[[ Upvalues: (copy 1): v_u_89, (ref 2): v_u_7 ]]
            local v103 = nil
            for _, v104 in v_u_89:key_itr() do
                if p102(v104) then
                    v103 = v104
                    break;
                end;
            end;
            if v103 == nil then
                v103 = v_u_7.RewardInfo:new(v_u_7.RewardType.None, 0, -1)
            end;
            return v103;
        end;
        local function _() --[[ Name: get_first_item_reward_desc ]] --[[ Line: 102 ]]
            --[[ Upvalues: (copy 1): f_get_first_reward_desc_of_type, (ref 2): v_u_7 ]]
            return f_get_first_reward_desc_of_type(function(p105) --[[ Line: 103 ]]
                --[[ Upvalues: (ref 1): v_u_7 ]]
                return v_u_7.RewardType:is_type_team_contribution_points(p105:get_type()) ~= true;
            end);
        end;
        v84.get_reward_image = function(_) --[[ Name: get_reward_image ]] --[[ Line: 106 ]]
            --[[ Upvalues: (copy 1): f_get_first_reward_desc_of_type, (ref 2): v_u_7 ]]
            return f_get_first_reward_desc_of_type(function(p106) --[[ Line: 103 ]]
                --[[ Upvalues: (ref 1): v_u_7 ]]
                return v_u_7.RewardType:is_type_team_contribution_points(p106:get_type()) ~= true;
            end):get_image();
        end;
        v84.get_reward_amount = function(_) --[[ Name: get_reward_amount ]] --[[ Line: 107 ]]
            --[[ Upvalues: (copy 1): f_get_first_reward_desc_of_type, (ref 2): v_u_7 ]]
            return f_get_first_reward_desc_of_type(function(p107) --[[ Line: 103 ]]
                --[[ Upvalues: (ref 1): v_u_7 ]]
                return v_u_7.RewardType:is_type_team_contribution_points(p107:get_type()) ~= true;
            end):get_amount();
        end;
        v84.get_reward_display_amount_for_playerblob_and_timeframe = function(p108, p109, p110) --[[ Name: get_reward_display_amount_for_playerblob_and_timeframe ]] --[[ Line: 108 ]]
            --[[ Upvalues: (copy 1): f_get_first_reward_desc_of_type, (ref 2): v_u_7, (ref 3): v_u_4, (ref 4): v_u_8, (ref 5): v_u_13, (ref 6): v_u_9 ]]
            local v112 = f_get_first_reward_desc_of_type(function(p111) --[[ Line: 103 ]]
                --[[ Upvalues: (ref 1): v_u_7 ]]
                return v_u_7.RewardType:is_type_team_contribution_points(p111:get_type()) ~= true;
            end):get_amount()
            local v113 = tostring(v112)
            if p108:get_type() == v_u_4.ScaledScore then
                local v114 = v_u_13:get_tier_id_reward_scale((v_u_13:mission_data_get_score_tier_id(p108, (v_u_8:playerblob_missionid_get_count(p109, p110, p108:get_id())))))
                if v114 == 1 then
                    return string.format("%s (x1)", v_u_9:comma_value(v_u_13:get_scaled_amount_for_multiplier(v112, v114)));
                end;
                v113 = string.format("%s (x%.2f)", v_u_9:comma_value(v_u_13:get_scaled_amount_for_multiplier(v112, v114)), v114)
            end;
            return v113;
        end;
        v84.get_first_team_contribution_point_reward_desc = function(_) --[[ Name: get_first_team_contribution_point_reward_desc ]] --[[ Line: 125 ]]
            --[[ Upvalues: (copy 1): f_get_first_reward_desc_of_type, (ref 2): v_u_7 ]]
            return f_get_first_reward_desc_of_type(function(p115) --[[ Line: 126 ]]
                --[[ Upvalues: (ref 1): v_u_7 ]]
                return v_u_7.RewardType:is_type_team_contribution_points(p115:get_type());
            end);
        end;
        return v84;
    end
}
v_u_116.from_table = function(_, p117) --[[ Name: from_table ]] --[[ Line: 132 ]]
    --[[ Upvalues: (copy 1): v_u_116, (copy 2): v_u_7 ]]
    local v118 = v_u_116:new(p117.ID)
    v118:set_type(p117.Type)
    v118:set_difficulty(p117.Difficulty)
    v118:set_target_song(p117.TargetSong)
    v118:set_count(p117.Count)
    v118:set_players_required(p117.PlayersRequired)
    v118:set_legacy_reward_type_and_amount(p117.RewardType, p117.RewardAmount)
    if p117.RewardDescInfoList then
        for _, v119 in pairs(p117.RewardDescInfoList) do
            v118:push_reward_desc_info(v_u_7.RewardInfo:from_table(v119))
        end;
    end;
    v118:set_song_naked_max_score(p117.SongNakedMaxScore)
    return v118;
end;
v_u_82.from_table = function(_, p120) --[[ Name: from_table ]] --[[ Line: 203 ]]
    --[[ Upvalues: (copy 1): v_u_82, (copy 2): v_u_9, (copy 3): v_u_116, (copy 4): v_u_10 ]]
    local v_u_121 = v_u_82:new(p120.Day, p120.Week)
    for _, v_u_122 in pairs(p120.Daily) do
        local v123, v124 = v_u_9:try(function() --[[ Line: 207 ]]
            --[[ Upvalues: (copy 1): v_u_121, (ref 2): v_u_116, (copy 3): v_u_122 ]]
            v_u_121:get_daily_missions():push_back(v_u_116:from_table(v_u_122))
        end)
        if v123 ~= true then
            v_u_10:warnf("MissionActiveData:from_table daily err(%s)", v124)
        end;
    end;
    for _, v_u_125 in pairs(p120.Weekly) do
        local v126, v127 = v_u_9:try(function() --[[ Line: 215 ]]
            --[[ Upvalues: (copy 1): v_u_121, (ref 2): v_u_116, (copy 3): v_u_125 ]]
            v_u_121:get_weekly_missions():push_back(v_u_116:from_table(v_u_125))
        end)
        if v126 ~= true then
            v_u_10:warnf("MissionActiveData:from_table weekly err(%s)", v127)
        end;
    end;
    return v_u_121;
end;
return v_u_82;
