-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:09 PM
-- Time elapsed: 11 milliseconds

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_2 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_3 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_4 = require(game.ReplicatedStorage.Shared.MissionDifficulty)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_7 = require(game.ReplicatedStorage.Shared.GuildRank)
local v_u_8 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v9 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
v9:require_shared(function() --[[ Line: 14 ]]
    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_11, (ref 3): v_u_12 ]]
    v_u_10 = require(game.ReplicatedStorage.Shared.GuildData)
    v_u_11 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
    v_u_12 = require(game.ReplicatedStorage.PlayerInfo.LeaderboardRewards)
end)
local v_u_29 = {
    ["Status"] = {
        ["Offline"] = 0,
        ["OnlineDifferentServer"] = 1,
        ["OnlineSameServer"] = 2
    },
    ["not_in_guild_id"] = function(_) --[[ Name: not_in_guild_id ]] --[[ Line: 28 ]]
        return -1;
    end,
    ["invalid_rbxid"] = function(_) --[[ Name: invalid_rbxid ]] --[[ Line: 29 ]]
        return 0;
    end,
    ["get_guild_creation_cost"] = function(_) --[[ Name: get_guild_creation_cost ]] --[[ Line: 30 ]]
        return 5;
    end,
    ["get_guild_change_name_cost"] = function(_) --[[ Name: get_guild_change_name_cost ]] --[[ Line: 31 ]]
        return 25;
    end,
    ["get_guild_creation_cost_type"] = function(_) --[[ Name: get_guild_creation_cost_type ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1.CurrencyType.Stars;
    end,
    ["guild_name_min_length"] = function(_) --[[ Name: guild_name_min_length ]] --[[ Line: 33 ]]
        return 3;
    end,
    ["guild_name_max_length"] = function(_) --[[ Name: guild_name_max_length ]] --[[ Line: 34 ]]
        return 32;
    end,
    ["guild_message_max_length"] = function(_) --[[ Name: guild_message_max_length ]] --[[ Line: 35 ]]
        return 256;
    end,
    ["get_max_guild_players"] = function(_) --[[ Name: get_max_guild_players ]] --[[ Line: 36 ]]
        return 25;
    end,
    ["get_weekly_player_contribution_cap"] = function(_) --[[ Name: get_weekly_player_contribution_cap ]] --[[ Line: 37 ]]
        return 25000;
    end,
    ["get_guild_enter_weekly_contribution_leaderboard_cost_for_guild_data"] = function(_, p13) --[[ Name: get_guild_enter_weekly_contribution_leaderboard_cost_for_guild_data ]] --[[ Line: 39 ]]
        --[[ Upvalues: (ref 1): v_u_10 ]]
        return math.max(0, v_u_10:get_member_count_with_join_date_older_than_current_week(p13) - 1) * 1 + 5;
    end,
    ["get_guild_enter_weekly_contribution_leaderboard_cost_type"] = function(_) --[[ Name: get_guild_enter_weekly_contribution_leaderboard_cost_type ]] --[[ Line: 43 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        return v_u_1.CurrencyType.Stars;
    end,
    ["playerblob_get_team_buff_weekid"] = function(_, p14) --[[ Name: playerblob_get_team_buff_weekid ]] --[[ Line: 45 ]]
        return p14.TeamBuffWeekID;
    end,
    ["playerblob_get_team_buff_color"] = function(_, p15) --[[ Name: playerblob_get_team_buff_color ]] --[[ Line: 46 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2 ]]
        local l_TeamBuffColor_0 = p15.TeamBuffColor
        if v_u_3:test_enum_member(l_TeamBuffColor_0, v_u_2) ~= true then
            l_TeamBuffColor_0 = v_u_2.Blue
        end;
        return l_TeamBuffColor_0;
    end,
    ["playerblob_get_team_buff_level"] = function(_, p16) --[[ Name: playerblob_get_team_buff_level ]] --[[ Line: 53 ]]
        return p16.TeamBuffLevel;
    end,
    ["ContributionSource"] = {
        ["DonateStars"] = 1,
        ["LeaderboardClaim"] = 2,
        ["DailyMissionClaim"] = 3,
        ["WeeklyMissionClaim"] = 4,
        ["ChallengePassClaim"] = 5
    },
    ["contribution_entry_to_buff_level"] = function(_, p17) --[[ Name: contribution_entry_to_buff_level ]] --[[ Line: 118 ]]
        local v18
        if p17:is_entered() then
            local v19 = p17:get_rank()
            if v19 == 0 then
                return 6;
            end;
            if v19 < 5 then
                return 5;
            end;
            if v19 < 10 then
                return 4;
            end;
            if v19 < 20 then
                return 3;
            end;
            if v19 < 50 then
                return 2;
            end;
            v18 = 1
        else
            v18 = 0
        end;
        return v18;
    end,
    ["contribution_entry_to_reward_list"] = function(_, p20) --[[ Name: contribution_entry_to_reward_list ]] --[[ Line: 139 ]]
        --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_11, (ref 3): v_u_12 ]]
        local v21 = v_u_5:new()
        if p20:is_entered() then
            local v22 = p20:get_rank()
            if v22 == 0 then
                v21:push_back(v_u_11.RewardInfo:new(v_u_11.RewardType.CraftingMaterials, 35, v_u_12:get_leaderboard_ticket_material_id()))
                return v21;
            end;
            if v22 < 5 then
                v21:push_back(v_u_11.RewardInfo:new(v_u_11.RewardType.CraftingMaterials, 25, v_u_12:get_leaderboard_ticket_material_id()))
                return v21;
            end;
            if v22 < 10 then
                v21:push_back(v_u_11.RewardInfo:new(v_u_11.RewardType.CraftingMaterials, 20, v_u_12:get_leaderboard_ticket_material_id()))
                return v21;
            end;
            if v22 < 20 then
                v21:push_back(v_u_11.RewardInfo:new(v_u_11.RewardType.CraftingMaterials, 15, v_u_12:get_leaderboard_ticket_material_id()))
                return v21;
            end;
            if v22 < 50 then
                v21:push_back(v_u_11.RewardInfo:new(v_u_11.RewardType.CraftingMaterials, 10, v_u_12:get_leaderboard_ticket_material_id()))
                return v21;
            end;
            v21:push_back(v_u_11.RewardInfo:new(v_u_11.RewardType.CraftingMaterials, 5, v_u_12:get_leaderboard_ticket_material_id()))
        end;
        return v21;
    end,
    ["playerblob_get_team_bonus_weekid"] = function(_, p23) --[[ Name: playerblob_get_team_bonus_weekid ]] --[[ Line: 160 ]]
        return p23.TeamBonusWeekID;
    end,
    ["get_max_team_contribution_point_cap_from_daily_song_missions"] = function(_) --[[ Name: get_max_team_contribution_point_cap_from_daily_song_missions ]] --[[ Line: 168 ]]
        return 2000;
    end,
    ["playerblob_get_current_day_team_contribution_point_amount_from_daily_song_missions"] = function(_, p24, p25) --[[ Name: playerblob_get_current_day_team_contribution_point_amount_from_daily_song_missions ]] --[[ Line: 169 ]]
        return p24.TeamContCapDaySongMissionDayID ~= p25 and 0 or p24.TeamContCapDaySongMission;
    end,
    ["playerblob_set_current_day_team_contribution_point_amount_from_daily_song_missions"] = function(_, p26, p27, p28) --[[ Name: playerblob_set_current_day_team_contribution_point_amount_from_daily_song_missions ]] --[[ Line: 176 ]]
        p26.TeamContCapDaySongMission = p27
        p26.TeamContCapDaySongMissionDayID = p28
    end
}
local v_u_30 = {
    ["DonateStars"] = 1,
    ["LeaderboardClaim"] = 2,
    ["DailyMissionClaim"] = 3,
    ["WeeklyMissionClaim"] = 4,
    ["ChallengePassClaim"] = 5
}
local function f_contribution_source_to_points(p31, p32) --[[ Name: contribution_source_to_points ]] --[[ Line: 63 ]]
    --[[ Upvalues: (copy 1): v_u_30, (copy 2): v_u_4 ]]
    if p31 == v_u_30.DonateStars then
        return 5 * p32;
    else
        return p31 == v_u_30.LeaderboardClaim and (p32 <= 1 and 1500 or (p32 <= 20 and 1000 or (p32 <= 50 and 750 or (p32 <= 200 and 500 or 250)))) or (p31 == v_u_30.DailyMissionClaim and (p32 == v_u_4.Star and 65 or (p32 == v_u_4.Pro and 55 or (p32 == v_u_4.Amateur and 45 or (p32 == v_u_4.Novice and 35 or 25)))) or (p31 == v_u_30.WeeklyMissionClaim and (p32 == v_u_4.Star and 500 or (p32 == v_u_4.Pro and 350 or (p32 == v_u_4.Amateur and 250 or (p32 == v_u_4.Novice and 150 or 100)))) or (p31 ~= v_u_30.ChallengePassClaim and 0 or 50 * p32)));
    end;
end;
v_u_29.contribution_source_to_points = function(_, p33, p34) --[[ Name: contribution_source_to_points ]] --[[ Line: 110 ]]
    --[[ Upvalues: (copy 1): f_contribution_source_to_points, (copy 2): v_u_8 ]]
    local v35 = f_contribution_source_to_points(p33, p34)
    if v_u_8.DebugContributionPointMultiplier ~= 1 then
        v35 = v35 * v_u_8.DebugContributionPointMultiplier
    end;
    return v35;
end;
v_u_29.is_name_valid = function(_, p36) --[[ Name: is_name_valid ]] --[[ Line: 162 ]]
    --[[ Upvalues: (copy 1): v_u_29 ]]
    if #p36 < v_u_29:guild_name_min_length() or #p36 > v_u_29:guild_name_max_length() then
        return false, "Invalid team name (length)";
    elseif p36:match("%W") == nil then
        return true, "";
    else
        return false, "Invalid team name (invalid characters)";
    end;
end;
v_u_29.validate_guild_data = function(_, p37) --[[ Name: validate_guild_data ]] --[[ Line: 181 ]]
    --[[ Upvalues: (copy 1): v_u_29, (copy 2): v_u_6, (copy 3): v_u_7 ]]
    if p37:get_guildid() == v_u_29:invalid_rbxid() then
        return false;
    end;
    if p37:get_total_members() > v_u_29:get_max_guild_players() then
        return false;
    end;
    if p37:get_star_currency() < 0 then
        return false;
    end;
    local v38 = v_u_6:new()
    for _, v39 in p37:get_member_infos():key_itr() do
        if v38:contains(v39:get_rbxid()) == true then
            return false;
        end;
        v38:add_set(v39:get_rbxid())
    end;
    if p37:get_total_members() > 0 then
        local v40 = 0
        for _, v41 in p37:get_member_infos():key_itr() do
            if v41:get_rank() == v_u_7.Owner then
                v40 = v40 + 1
            end;
        end;
        if v40 ~= 1 then
            return false;
        end;
    end;
    return true;
end;
return v_u_29;
