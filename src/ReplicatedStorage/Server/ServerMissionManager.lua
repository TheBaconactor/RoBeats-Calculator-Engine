-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:14 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Shared.ProdEnvSelector)
require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_9 = require(game.ReplicatedStorage.Shared.MissionType)
local v_u_10 = require(game.ReplicatedStorage.Shared.MissionDifficulty)
local v_u_11 = require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_12 = require(game.ReplicatedStorage.Shared.MissionTimeframe)
local v_u_13 = require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_14 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassUtils)
require(game.ReplicatedStorage.Crafting.CraftingRewardCategories)
require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_16 = require(game.ReplicatedStorage.Shared.Mission.MissionActiveData)
local v_u_17 = require(game.ReplicatedStorage.Shared.Mission.MissionServerPreprocess)
local v_u_18 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_19 = require(game.ReplicatedStorage.Shared.Mission.ScaledScoreMissionUtil)
local v_u_20 = require(game.ReplicatedStorage.Shared.Mission.MissionLeaderboardEntry)
local v_u_21 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_22 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_23 = require(game.ReplicatedStorage.Shared.WaitForFinish)
local v_u_24 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
local v_u_25 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_26 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v27 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_28 = nil
v27:require_server(function() --[[ Line: 36 ]]
    --[[ Upvalues: (ref 1): v_u_28 ]]
    v_u_28 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
return {
    ["new"] = function(_, p_u_29) --[[ Name: new ]] --[[ Line: 42 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_3, (copy 3): v_u_9, (copy 4): v_u_12, (copy 5): v_u_2, (copy 6): v_u_18, (copy 7): v_u_5, (copy 8): v_u_24, (copy 9): v_u_10, (copy 10): v_u_16, (copy 11): v_u_6, (copy 12): v_u_19, (ref 13): v_u_28, (copy 14): v_u_4, (copy 15): v_u_26, (copy 16): v_u_14, (copy 17): v_u_20, (copy 18): v_u_7, (copy 19): v_u_23, (copy 20): v_u_1, (copy 21): v_u_25, (copy 22): v_u_15, (copy 23): v_u_13, (copy 24): v_u_8, (copy 25): v_u_22, (copy 26): v_u_21, (copy 27): v_u_17 ]]
        local v_u_30 = {}
        local function _(p31, p32) --[[ Name: mission_write_info ]] --[[ Line: 45 ]]
            --[[ Upvalues: (ref 1): v_u_11, (copy 2): p_u_29 ]]
            return v_u_11.MissionWriteInfo:new(p31, p32, p_u_29._api:get_day_id(), p_u_29._api:get_week_id());
        end;
        local v_u_33 = v_u_3:new():add_set_from_table_list({
            v_u_9.Score,
            v_u_9.Rank,
            v_u_9.ScaledScore,
            v_u_9.NoMiss
        })
        local v_u_34 = v_u_3:new():add_set_from_table_list({ v_u_9.PointTotal })
        v_u_30.start = function(p_u_35) --[[ Name: start ]] --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_2, (ref 3): v_u_18, (ref 4): v_u_11, (ref 5): v_u_5, (copy 6): p_u_29, (copy 7): v_u_33, (ref 8): v_u_24, (ref 9): v_u_9, (copy 10): v_u_34, (ref 11): v_u_10, (ref 12): v_u_16, (ref 13): v_u_6, (ref 14): v_u_19, (ref 15): v_u_28, (ref 16): v_u_4, (ref 17): v_u_26, (ref 18): v_u_14, (ref 19): v_u_20, (ref 20): v_u_7, (ref 21): v_u_23, (ref 22): v_u_3, (ref 23): v_u_1 ]]
            local function _() --[[ Name: create_mission_claim_response_data ]] --[[ Line: 62 ]]
                --[[ Upvalues: (ref 1): v_u_12 ]]
                return {
                    ["DidPlayerBlobUpgradeDifficulty"] = false,
                    ["RemainingMissionsToRankUpgrade"] = -1,
                    ["RewardDescriptionInfoTable"] = {},
                    ["MissionCompletedCount"] = 0,
                    ["RankupMissionID"] = 1,
                    ["RankupMissionTimeframe"] = v_u_12.Daily
                };
            end;
            local function _(p36, p37) --[[ Name: response_data_append_reward_params ]] --[[ Line: 73 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_18 ]]
                v_u_2:new(p36.RewardDescriptionInfoTable):push_back_from_list(v_u_2:new(v_u_18.RewardInfo:list_to_table(v_u_18:reward_params_get_resolved_reward_list(p37))))
            end;
            local function f_claim_mission_complete(p_u_38, p39, p40, p_u_41, p42, p43, p44) --[[ Name: claim_mission_complete ]] --[[ Line: 79 ]]
                --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_5, (ref 3): p_u_29, (ref 4): v_u_33, (ref 5): v_u_12, (ref 6): v_u_24, (ref 7): v_u_9, (ref 8): v_u_34, (ref 9): v_u_10, (ref 10): v_u_16, (ref 11): v_u_6, (ref 12): v_u_19, (ref 13): v_u_28 ]]
                local v45 = nil
                if v_u_11:playerblob_missiondata_missionid_is_completeable(p_u_41, p42, p40, p39) or v_u_11:playerblob_get_missionid_completed(p_u_41, p40, p39) == false and v_u_5.MissionDebugAlwaysClaim == true then
                    local v46 = p43:get_mission_data_for_timeframe_and_id(p40, p39)
                    if v46 then
                        local v47 = v46:get_difficulty()
                        local v48 = v_u_11:playerblob_get_mission_difficulty(p_u_41)
                        local v49 = v46:get_type()
                        v_u_11:playerblob_missionid_set_completed(p_u_41, v_u_11.MissionWriteInfo:new(p40, p39, p_u_29._api:get_day_id(), p_u_29._api:get_week_id()), true)
                        if v_u_33:contains(v49) and p40 == v_u_12.Daily then
                            local v50 = 0
                            for _, v51 in p43:get_mission_list_for_timeframe(v_u_12.Daily):key_itr() do
                                if v_u_33:contains(v51:get_type()) and v_u_11:playerblob_get_missionid_completed(p_u_41, p40, v51:get_id()) then
                                    v50 = v50 + 1
                                end;
                            end;
                            if v50 >= 1 then
                                p_u_29._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_24.DailyMissionType.Complete1DailyMission, p_u_41)
                            end;
                            if v50 >= 3 then
                                p_u_29._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_24.DailyMissionType.Complete3DailyMission, p_u_41)
                            end;
                            if v50 >= 6 then
                                p_u_29._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_24.DailyMissionType.Complete6DailyMission, p_u_41)
                            end;
                            if v49 == v_u_9.NoMiss then
                                p_u_29._challengepass_manager:challengepassv2_weekly_mission_playerblob_claim(v_u_24.WeeklyMissionType.CompleteChallengeMission, p_u_41)
                            end;
                        elseif v_u_34:contains(v49) and p40 == v_u_12.Weekly then
                            p_u_29._challengepass_manager:challengepassv2_weekly_mission_playerblob_claim(v_u_24.WeeklyMissionType.CompleteWeeklyMission, p_u_41)
                        end;
                        if p40 == v_u_12.Daily and (v48 == v47 and v_u_10:is_max_difficulty(v48) ~= true) then
                            local v52 = v_u_16:playerblob_get_remaining_missions_of_playerblob_difficulty_to_rank_upgrade(p43, p_u_41)
                            if v52 <= 0 then
                                v_u_11:playerblob_upgrade_mission_difficulty(p_u_41)
                                p44.DidPlayerBlobUpgradeDifficulty = true
                                p44.RankupMissionID = p39
                                p44.RankupMissionTimeframe = p40
                                v_u_6:ptry(function() --[[ Line: 145 ]]
                                    --[[ Upvalues: (ref 1): v_u_11, (copy 2): p_u_41, (ref 3): p_u_29, (copy 4): p_u_38, (ref 5): v_u_10 ]]
                                    local v_u_53 = v_u_11:playerblob_get_mission_difficulty(p_u_41)
                                    local v54 = p_u_29._chat:get_chat_service()
                                    v54:send_system_message_to_player_for_channel(p_u_38, v54:get_channel(v54:get_server_system_channel_id()), string.format("You have reached \'%s\' rank!", v_u_10:difficulty_to_string(v_u_53)), function(p55) --[[ Line: 152 ]]
                                        --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_53 ]]
                                        p55:set_channel_name("")
                                        p55:set_icon(v_u_11:difficulty_to_icon(v_u_53))
                                    end)
                                end)
                            end;
                            p44.RemainingMissionsToRankUpgrade = math.min(p44.RemainingMissionsToRankUpgrade, v52)
                        end;
                        p44.MissionCompletedCount = p44.MissionCompletedCount + 1
                        v45 = v46:get_reward_desc_info_list()
                        if v46:get_type() == v_u_9.ScaledScore then
                            v45 = v_u_19:get_playerblob_mission_data_timeframe_reward_desc_info_list_scaled(p_u_41, v46, p40, v45)
                        end;
                        p_u_29._special_event_manager:write_special_event_data_for_player_action(p_u_38.UserId, v_u_28.PlayerActionEvent.CompleteMission, v46)
                    end;
                end;
                return v45;
            end;
            p_u_29._evt:wait_on_event(v_u_4.EVT_Mission_ClientClaimMissionComplete, function(p_u_56, p_u_57, p_u_58) --[[ Line: 176 ]]
                --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_4, (copy 3): p_u_35, (ref 4): v_u_12, (copy 5): f_claim_mission_complete, (ref 6): v_u_18, (ref 7): v_u_2 ]]
                local function f_response(p59, p60) --[[ Name: response ]] --[[ Line: 177 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_4, (copy 3): p_u_56 ]]
                    return p_u_29._evt:fire_event_to_client(v_u_4.EVT_Mission_ServerClaimMissionCompleteResponse, p_u_56, p59, p60);
                end;
                p_u_29._player_blob_manager:get_verified_cached_blob(p_u_56.UserId, function(p_u_61) --[[ Line: 181 ]]
                    --[[ Upvalues: (ref 1): p_u_35, (ref 2): v_u_12, (ref 3): f_claim_mission_complete, (copy 4): p_u_56, (copy 5): p_u_57, (copy 6): p_u_58, (ref 7): v_u_18, (ref 8): p_u_29, (ref 9): v_u_2, (ref 10): v_u_4, (copy 11): f_response ]]
                    p_u_35:get_mission_data(function(p62, p63) --[[ Line: 182 ]]
                        --[[ Upvalues: (ref 1): v_u_12, (ref 2): f_claim_mission_complete, (ref 3): p_u_56, (ref 4): p_u_57, (ref 5): p_u_58, (copy 6): p_u_61, (ref 7): v_u_18, (ref 8): p_u_29, (ref 9): v_u_2, (ref 10): v_u_4, (ref 11): f_response ]]
                        local v_u_64 = {
                            ["DidPlayerBlobUpgradeDifficulty"] = false,
                            ["RemainingMissionsToRankUpgrade"] = -1,
                            ["RewardDescriptionInfoTable"] = {},
                            ["MissionCompletedCount"] = 0,
                            ["RankupMissionID"] = 1,
                            ["RankupMissionTimeframe"] = v_u_12.Daily
                        }
                        local v65 = f_claim_mission_complete(p_u_56, p_u_57, p_u_58, p_u_61, p62, p63, v_u_64)
                        if v65 == nil then
                            return f_response(false, {});
                        end;
                        local v66 = v_u_18:claim_reward_info_list_to_playerblob(p_u_29, p_u_61, v65)
                        v_u_2:new(v_u_64.RewardDescriptionInfoTable):push_back_from_list(v_u_2:new(v_u_18.RewardInfo:list_to_table(v_u_18:reward_params_get_resolved_reward_list(v66))))
                        v_u_18:server_sync_reward_params(p_u_29, p_u_56, v66, function() --[[ Line: 203 ]]
                            --[[ Upvalues: (copy 1): v_u_64, (ref 2): p_u_29, (ref 3): v_u_4, (ref 4): p_u_56 ]]
                            p_u_29._evt:fire_event_to_client(v_u_4.EVT_Mission_ServerClaimMissionCompleteResponse, p_u_56, true, v_u_64)
                        end)
                    end)
                end)
            end)
            p_u_29._evt:wait_on_event(v_u_4.EVT_Mission_ClientClaimAllMissionComplete, function(p_u_67) --[[ Line: 215 ]]
                --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_4, (ref 3): v_u_5, (copy 4): p_u_35, (ref 5): v_u_2, (ref 6): v_u_11, (ref 7): v_u_26, (ref 8): v_u_12, (copy 9): f_claim_mission_complete, (ref 10): v_u_18 ]]
                local function f_response(p68, p69) --[[ Name: response ]] --[[ Line: 216 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_4, (copy 3): p_u_67 ]]
                    return p_u_29._evt:fire_event_to_client(v_u_4.EVT_Mission_ServerClaimAllMissionCompleteResponse, p_u_67, p68, p69 == nil and {} or p69);
                end;
                if v_u_5.ClaimAllMissionRewardsEnabled ~= true then
                    return f_response(false);
                end;
                p_u_29._player_blob_manager:get_verified_cached_blob(p_u_67.UserId, function(p_u_70) --[[ Line: 222 ]]
                    --[[ Upvalues: (ref 1): p_u_35, (ref 2): v_u_2, (ref 3): v_u_11, (ref 4): v_u_26, (ref 5): v_u_12, (ref 6): f_claim_mission_complete, (copy 7): p_u_67, (ref 8): v_u_18, (ref 9): p_u_29, (ref 10): v_u_4 ]]
                    p_u_35:get_mission_data(function(p_u_71, p72) --[[ Line: 223 ]]
                        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_11, (copy 3): p_u_70, (ref 4): v_u_26, (ref 5): v_u_12, (ref 6): f_claim_mission_complete, (ref 7): p_u_67, (ref 8): v_u_18, (ref 9): p_u_29, (ref 10): v_u_4 ]]
                        local function _(p_u_73) --[[ Name: get_claimable_timeframe_mission_ids ]] --[[ Line: 225 ]]
                            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_11, (ref 3): p_u_70, (copy 4): p_u_71 ]]
                            local v_u_74 = v_u_2:new()
                            v_u_11:playerblob_missiondata_available_foreach(p_u_70, p_u_71, p_u_73, function(p75) --[[ Line: 227 ]]
                                --[[ Upvalues: (ref 1): v_u_11, (ref 2): p_u_70, (ref 3): p_u_71, (copy 4): p_u_73, (copy 5): v_u_74 ]]
                                local v76 = v_u_11:mission_get_id(p75)
                                if v_u_11:playerblob_missiondata_missionid_is_completeable(p_u_70, p_u_71, p_u_73, v76) then
                                    v_u_74:push_back(v76)
                                end;
                            end)
                            return v_u_74;
                        end;
                        local v_u_77 = v_u_26:new()
                        for _, v_u_78 in v_u_12:get_all():key_itr() do
                            local v79 = v_u_77:list_of(v_u_78)
                            local v_u_80 = v_u_2:new()
                            v_u_11:playerblob_missiondata_available_foreach(p_u_70, p_u_71, v_u_78, function(p81) --[[ Line: 227 ]]
                                --[[ Upvalues: (ref 1): v_u_11, (ref 2): p_u_70, (copy 3): p_u_71, (copy 4): v_u_78, (copy 5): v_u_80 ]]
                                local v82 = v_u_11:mission_get_id(p81)
                                if v_u_11:playerblob_missiondata_missionid_is_completeable(p_u_70, p_u_71, v_u_78, v82) then
                                    v_u_80:push_back(v82)
                                end;
                            end)
                            v79:push_back_from_list(v_u_80)
                        end;
                        local v_u_83 = {
                            ["DidPlayerBlobUpgradeDifficulty"] = false,
                            ["RemainingMissionsToRankUpgrade"] = -1,
                            ["RewardDescriptionInfoTable"] = {},
                            ["MissionCompletedCount"] = 0,
                            ["RankupMissionID"] = 1,
                            ["RankupMissionTimeframe"] = v_u_12.Daily
                        }
                        local v84 = v_u_2:new()
                        local v85 = true
                        local function f_get_next_timeframe_mission_id_to_claim() --[[ Name: get_next_timeframe_mission_id_to_claim ]] --[[ Line: 241 ]]
                            --[[ Upvalues: (copy 1): v_u_77 ]]
                            for v86, v87 in v_u_77:key_itr() do
                                if v87:count() > 0 then
                                    return true, v86, v87:pop_back();
                                end;
                            end;
                            return false;
                        end;
                        while v85 do
                            local v88, v89
                            v85, v88, v89 = f_get_next_timeframe_mission_id_to_claim()
                            if v85 then
                                local v90 = f_claim_mission_complete(p_u_67, v89, v88, p_u_70, p_u_71, p72, v_u_83)
                                if v90 ~= nil then
                                    v84:push_back_from_list(v90)
                                end;
                            end;
                        end;
                        local v91 = v_u_18:claim_reward_info_list_to_playerblob(p_u_29, p_u_70, v84)
                        v_u_2:new(v_u_83.RewardDescriptionInfoTable):push_back_from_list(v_u_2:new(v_u_18.RewardInfo:list_to_table(v_u_18:reward_params_get_resolved_reward_list(v91))))
                        v_u_18:server_sync_reward_params(p_u_29, p_u_67, v91, function() --[[ Line: 282 ]]
                            --[[ Upvalues: (copy 1): v_u_83, (ref 2): p_u_29, (ref 3): v_u_4, (ref 4): p_u_67 ]]
                            local v92 = v_u_83
                            p_u_29._evt:fire_event_to_client(v_u_4.EVT_Mission_ServerClaimAllMissionCompleteResponse, p_u_67, true, v92 == nil and {} or v92)
                        end)
                    end)
                end)
            end)
            p_u_29._evt:wait_on_event(v_u_4.EVT_Mission_ClientRequestMissionLeaderboardData, function(p_u_93, p94, p95, p96) --[[ Line: 290 ]]
                --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_20, (ref 3): v_u_7, (ref 4): p_u_29, (ref 5): v_u_4 ]]
                v_u_14:is_enum_member(p94, v_u_20.LeaderboardType)
                v_u_14:is_true(v_u_7:singleton():contains_key(p95))
                v_u_14:is_int(p96)
                local function _(p97, p98) --[[ Name: response ]] --[[ Line: 295 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_4, (copy 3): p_u_93 ]]
                    return p_u_29._evt:fire_event_to_client(v_u_4.EVT_Mission_ServerRequestMissionLeaderboardDataResponse, p_u_93, p97, p98);
                end;
                p_u_29._datastore_api:get_mission_leaderboard_entry_list_for_type_songkey_weekid(p94, p95, p96, function(p99) --[[ Line: 298 ]]
                    --[[ Upvalues: (ref 1): v_u_20, (ref 2): p_u_29, (ref 3): v_u_4, (copy 4): p_u_93 ]]
                    p_u_29._evt:fire_event_to_client(v_u_4.EVT_Mission_ServerRequestMissionLeaderboardDataResponse, p_u_93, true, (v_u_20:list_to_table(p99)))
                end)
            end)
            p_u_29._evt:wait_on_event(v_u_4.EVT_Mission_ClientClaimMissionLeaderboardReward, function(p_u_100) --[[ Line: 303 ]]
                --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_4, (copy 3): p_u_35, (ref 4): v_u_2, (ref 5): v_u_9, (ref 6): v_u_23, (ref 7): v_u_20, (ref 8): v_u_7, (ref 9): v_u_3, (ref 10): v_u_6, (ref 11): v_u_1, (ref 12): v_u_18 ]]
                local function _(p101, p102, p103, p104, p105, p106) --[[ Name: response ]] --[[ Line: 304 ]]
                    --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_4, (copy 3): p_u_100 ]]
                    return p_u_29._evt:fire_event_to_client(v_u_4.EVT_Mission_ServerClaimMissionLeaderboardRewardResponse, p_u_100, p101, p102, p103, p104, p105, p106);
                end;
                p_u_35:get_previous_week_mission_data(function(p107) --[[ Line: 317 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_9, (ref 3): v_u_23, (ref 4): p_u_29, (ref 5): v_u_20, (ref 6): v_u_7, (ref 7): v_u_3, (copy 8): p_u_100, (ref 9): v_u_6, (ref 10): v_u_1, (ref 11): v_u_18, (ref 12): v_u_4 ]]
                    local v108 = v_u_2:new()
                    for _, v109 in p107:get_weekly_missions():key_itr() do
                        if v109:get_type() == v_u_9.PointTotal then
                            v108:push_back(v109:get_target_song())
                        end;
                    end;
                    local v_u_110 = v_u_23.Builder:new()
                    local v_u_111 = v_u_2:new()
                    local v_u_112 = p_u_29._api:get_week_id() - 1
                    for _, v_u_113 in v108:key_itr() do
                        for _, v_u_114 in v_u_20.LeaderboardType:all_types_list():key_itr() do
                            v_u_110:begin()
                            p_u_29._datastore_api:get_mission_leaderboard_entry_list_for_type_songkey_weekid(v_u_114, v_u_113, v_u_112, function(p115) --[[ Line: 332 ]]
                                --[[ Upvalues: (copy 1): v_u_111, (ref 2): v_u_20, (copy 3): v_u_114, (copy 4): v_u_113, (copy 5): v_u_112, (copy 6): v_u_110 ]]
                                v_u_111:push_back(v_u_20.LeaderboardInfo:new(v_u_114, v_u_113, v_u_112, p115))
                                v_u_110:finish()
                            end)
                        end;
                    end;
                    v_u_110:wait_for_finish(function() --[[ Line: 338 ]]
                        --[[ Upvalues: (copy 1): v_u_111, (ref 2): v_u_7, (ref 3): v_u_20, (ref 4): v_u_3, (ref 5): p_u_100, (ref 6): v_u_6, (ref 7): v_u_1, (ref 8): p_u_29, (copy 9): v_u_112, (ref 10): v_u_2, (ref 11): v_u_18, (ref 12): v_u_4 ]]
                        v_u_111:sort(function(p116, p117) --[[ Line: 341 ]]
                            --[[ Upvalues: (ref 1): v_u_7 ]]
                            local v118 = v_u_7:singleton():get_difficulty_for_key(p116:get_song_key())
                            local v119 = v_u_7:singleton():get_difficulty_for_key(p117:get_song_key())
                            if v118 == v119 then
                                return p116:get_leaderboard_type() < p117:get_leaderboard_type();
                            else
                                return v118 < v119;
                            end;
                        end)
                        local l_PLACE_NOT_FOUND_0 = v_u_20.LeaderboardInfo.PLACE_NOT_FOUND
                        local v_u_120 = v_u_7:invalid_songkey()
                        local v_u_121 = v_u_3:new()
                        local l_UserId_0 = p_u_100.UserId
                        local v_u_122 = -1
                        for _, v123 in v_u_111:key_itr() do
                            local v124 = v123:get_playerid_place(l_UserId_0)
                            if v124 ~= v_u_20.LeaderboardInfo.PLACE_NOT_FOUND then
                                local v125 = v123:get_leaderboard_type()
                                if l_PLACE_NOT_FOUND_0 == v_u_20.LeaderboardInfo.PLACE_NOT_FOUND or v124 < l_PLACE_NOT_FOUND_0 then
                                    l_PLACE_NOT_FOUND_0 = math.min(l_PLACE_NOT_FOUND_0, v124)
                                    v_u_120 = v123:get_song_key()
                                    v_u_122 = v125
                                end;
                                if v_u_121:contains(v125) then
                                    v_u_121:add(v125, (math.min(v124, v_u_121:get(v125))))
                                else
                                    v_u_121:add(v125, v124)
                                end;
                            end;
                        end;
                        if v_u_6:is_dev_build() then
                            v_u_1:puts("EVT_Mission_ClientClaimMissionLeaderboardReward top_place: %d, top_place_songkey: %d, top_place_leaderboard_type: %d", l_PLACE_NOT_FOUND_0, v_u_120, v_u_122)
                        end;
                        p_u_29._datastore_api:do_mission_leaderboard_rewards_claimed_for_weekid_playerid(v_u_112, l_UserId_0, function(p126) --[[ Line: 379 ]]
                            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_20, (ref 3): l_PLACE_NOT_FOUND_0, (copy 4): v_u_121, (ref 5): p_u_29, (ref 6): p_u_100, (ref 7): v_u_18, (ref 8): v_u_120, (ref 9): v_u_122, (ref 10): v_u_111, (ref 11): v_u_4, (ref 12): v_u_7 ]]
                            local v_u_127 = v_u_2:new()
                            if p126 == true then
                                v_u_127 = v_u_20:leaderboard_place_to_reward_desc_info_list(l_PLACE_NOT_FOUND_0, v_u_121)
                            end;
                            if v_u_127:count() > 0 then
                                p_u_29._player_blob_manager:get_verified_cached_blob(p_u_100.UserId, function(p128) --[[ Line: 385 ]]
                                    --[[ Upvalues: (ref 1): v_u_18, (ref 2): p_u_29, (ref 3): v_u_127, (ref 4): p_u_100, (ref 5): l_PLACE_NOT_FOUND_0, (ref 6): v_u_120, (ref 7): v_u_122, (ref 8): v_u_20, (ref 9): v_u_111, (ref 10): v_u_4 ]]
                                    v_u_18:server_sync_reward_params(p_u_29, p_u_100, v_u_18:claim_reward_info_list_to_playerblob(p_u_29, p128, v_u_127), function(_, _, p129) --[[ Line: 387 ]]
                                        --[[ Upvalues: (ref 1): l_PLACE_NOT_FOUND_0, (ref 2): v_u_120, (ref 3): v_u_122, (ref 4): v_u_18, (ref 5): v_u_20, (ref 6): v_u_111, (ref 7): p_u_29, (ref 8): v_u_4, (ref 9): p_u_100 ]]
                                        p_u_29._evt:fire_event_to_client(v_u_4.EVT_Mission_ServerClaimMissionLeaderboardRewardResponse, p_u_100, true, l_PLACE_NOT_FOUND_0, v_u_120, v_u_122, v_u_18.RewardInfo:list_to_table(p129), (v_u_20.LeaderboardInfo:list_to_table(v_u_111)))
                                    end)
                                end)
                            else
                                p_u_29._evt:fire_event_to_client(v_u_4.EVT_Mission_ServerClaimMissionLeaderboardRewardResponse, p_u_100, false, v_u_20.LeaderboardInfo.PLACE_NOT_FOUND, v_u_7:invalid_songkey(), -1, v_u_18.RewardInfo:list_to_table(v_u_127), (v_u_20.LeaderboardInfo:list_to_table(v_u_111)))
                            end;
                        end)
                    end)
                end)
            end)
        end;
        local function _(p_u_130, p_u_131) --[[ Name: apply_mission_fn_to_player_blob ]] --[[ Line: 414 ]]
            --[[ Upvalues: (copy 1): v_u_30, (ref 2): v_u_12, (ref 3): v_u_11 ]]
            v_u_30:get_mission_data(function(p132) --[[ Line: 415 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_11, (copy 3): p_u_130, (copy 4): p_u_131 ]]
                local v133 = v_u_12:get_all()
                for v134 = 1, v133:count() do
                    local v_u_135 = v133:get(v134)
                    v_u_11:playerblob_missiondata_available_foreach(p_u_130, p132, v_u_135, function(p136) --[[ Line: 419 ]]
                        --[[ Upvalues: (ref 1): v_u_11, (ref 2): p_u_130, (copy 3): v_u_135, (ref 4): p_u_131 ]]
                        local v137 = v_u_11:mission_get_id(p136)
                        local v138 = v_u_11:playerblob_missionid_get_count(p_u_130, v_u_135, v137)
                        v_u_11:mission_get_count(p136)
                        p_u_131(p136, v_u_135, v137, v138)
                    end)
                end;
            end)
        end;
        v_u_30.apply_cheer_count_to_mission_for_player_blob = function(_, p_u_139, p_u_140) --[[ Name: apply_cheer_count_to_mission_for_player_blob ]] --[[ Line: 431 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_9, (copy 3): p_u_29, (copy 4): v_u_30, (ref 5): v_u_12 ]]
            local function v_u_145(p141, p142, p143, p144) --[[ Line: 432 ]]
                --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_9, (copy 3): p_u_139, (ref 4): p_u_29, (copy 5): p_u_140 ]]
                if v_u_11:mission_get_type(p141) == v_u_9.Cheer then
                    v_u_11:playerblob_missionid_set_count(p_u_139, v_u_11.MissionWriteInfo:new(p142, p143, p_u_29._api:get_day_id(), p_u_29._api:get_week_id()), p144 + p_u_140)
                end;
            end;
            v_u_30:get_mission_data(function(p146) --[[ Line: 415 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_11, (copy 3): p_u_139, (copy 4): v_u_145 ]]
                local v147 = v_u_12:get_all()
                for v148 = 1, v147:count() do
                    local v_u_149 = v147:get(v148)
                    v_u_11:playerblob_missiondata_available_foreach(p_u_139, p146, v_u_149, function(p150) --[[ Line: 419 ]]
                        --[[ Upvalues: (ref 1): v_u_11, (ref 2): p_u_139, (copy 3): v_u_149, (ref 4): v_u_145 ]]
                        local v151 = v_u_11:mission_get_id(p150)
                        local v152 = v_u_11:playerblob_missionid_get_count(p_u_139, v_u_149, v151)
                        v_u_11:mission_get_count(p150)
                        v_u_145(p150, v_u_149, v151, v152)
                    end)
                end;
            end)
        end;
        v_u_30.apply_star_machine_count_to_mission_for_player_blob = function(_, p_u_153, p_u_154) --[[ Name: apply_star_machine_count_to_mission_for_player_blob ]] --[[ Line: 439 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_9, (copy 3): p_u_29, (copy 4): v_u_30, (ref 5): v_u_12 ]]
            local function v_u_159(p155, p156, p157, p158) --[[ Line: 440 ]]
                --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_9, (copy 3): p_u_153, (ref 4): p_u_29, (copy 5): p_u_154 ]]
                if v_u_11:mission_get_type(p155) == v_u_9.StarMachine then
                    v_u_11:playerblob_missionid_set_count(p_u_153, v_u_11.MissionWriteInfo:new(p156, p157, p_u_29._api:get_day_id(), p_u_29._api:get_week_id()), p158 + p_u_154)
                end;
            end;
            v_u_30:get_mission_data(function(p160) --[[ Line: 415 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_11, (copy 3): p_u_153, (copy 4): v_u_159 ]]
                local v161 = v_u_12:get_all()
                for v162 = 1, v161:count() do
                    local v_u_163 = v161:get(v162)
                    v_u_11:playerblob_missiondata_available_foreach(p_u_153, p160, v_u_163, function(p164) --[[ Line: 419 ]]
                        --[[ Upvalues: (ref 1): v_u_11, (ref 2): p_u_153, (copy 3): v_u_163, (ref 4): v_u_159 ]]
                        local v165 = v_u_11:mission_get_id(p164)
                        local v166 = v_u_11:playerblob_missionid_get_count(p_u_153, v_u_163, v165)
                        v_u_11:mission_get_count(p164)
                        v_u_159(p164, v_u_163, v165, v166)
                    end)
                end;
            end)
        end;
        v_u_30.apply_note_machine_count_to_mission_for_player_blob = function(_, p_u_167, p_u_168) --[[ Name: apply_note_machine_count_to_mission_for_player_blob ]] --[[ Line: 447 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_9, (copy 3): p_u_29, (copy 4): v_u_30, (ref 5): v_u_12 ]]
            local function v_u_173(p169, p170, p171, p172) --[[ Line: 448 ]]
                --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_9, (copy 3): p_u_167, (ref 4): p_u_29, (copy 5): p_u_168 ]]
                if v_u_11:mission_get_type(p169) == v_u_9.NoteMachine then
                    v_u_11:playerblob_missionid_set_count(p_u_167, v_u_11.MissionWriteInfo:new(p170, p171, p_u_29._api:get_day_id(), p_u_29._api:get_week_id()), p172 + p_u_168)
                end;
            end;
            v_u_30:get_mission_data(function(p174) --[[ Line: 415 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_11, (copy 3): p_u_167, (copy 4): v_u_173 ]]
                local v175 = v_u_12:get_all()
                for v176 = 1, v175:count() do
                    local v_u_177 = v175:get(v176)
                    v_u_11:playerblob_missiondata_available_foreach(p_u_167, p174, v_u_177, function(p178) --[[ Line: 419 ]]
                        --[[ Upvalues: (ref 1): v_u_11, (ref 2): p_u_167, (copy 3): v_u_177, (ref 4): v_u_173 ]]
                        local v179 = v_u_11:mission_get_id(p178)
                        local v180 = v_u_11:playerblob_missionid_get_count(p_u_167, v_u_177, v179)
                        v_u_11:mission_get_count(p178)
                        v_u_173(p178, v_u_177, v179, v180)
                    end)
                end;
            end)
        end;
        v_u_30.apply_upgrade_gear_count_to_mission_for_player_blob = function(_, p_u_181, p_u_182) --[[ Name: apply_upgrade_gear_count_to_mission_for_player_blob ]] --[[ Line: 455 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_9, (copy 3): p_u_29, (copy 4): v_u_30, (ref 5): v_u_12 ]]
            local function v_u_187(p183, p184, p185, p186) --[[ Line: 456 ]]
                --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_9, (copy 3): p_u_181, (ref 4): p_u_29, (copy 5): p_u_182 ]]
                if v_u_11:mission_get_type(p183) == v_u_9.UpgradeGear then
                    v_u_11:playerblob_missionid_set_count(p_u_181, v_u_11.MissionWriteInfo:new(p184, p185, p_u_29._api:get_day_id(), p_u_29._api:get_week_id()), p186 + p_u_182)
                end;
            end;
            v_u_30:get_mission_data(function(p188) --[[ Line: 415 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_11, (copy 3): p_u_181, (copy 4): v_u_187 ]]
                local v189 = v_u_12:get_all()
                for v190 = 1, v189:count() do
                    local v_u_191 = v189:get(v190)
                    v_u_11:playerblob_missiondata_available_foreach(p_u_181, p188, v_u_191, function(p192) --[[ Line: 419 ]]
                        --[[ Upvalues: (ref 1): v_u_11, (ref 2): p_u_181, (copy 3): v_u_191, (ref 4): v_u_187 ]]
                        local v193 = v_u_11:mission_get_id(p192)
                        local v194 = v_u_11:playerblob_missionid_get_count(p_u_181, v_u_191, v193)
                        v_u_11:mission_get_count(p192)
                        v_u_187(p192, v_u_191, v193, v194)
                    end)
                end;
            end)
        end;
        v_u_30.apply_combine_song_count_to_mission_for_player_blob = function(_, p_u_195, p_u_196) --[[ Name: apply_combine_song_count_to_mission_for_player_blob ]] --[[ Line: 463 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_9, (copy 3): p_u_29, (copy 4): v_u_30, (ref 5): v_u_12 ]]
            local function v_u_201(p197, p198, p199, p200) --[[ Line: 464 ]]
                --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_9, (copy 3): p_u_195, (ref 4): p_u_29, (copy 5): p_u_196 ]]
                if v_u_11:mission_get_type(p197) == v_u_9.CombineSong then
                    v_u_11:playerblob_missionid_set_count(p_u_195, v_u_11.MissionWriteInfo:new(p198, p199, p_u_29._api:get_day_id(), p_u_29._api:get_week_id()), p200 + p_u_196)
                end;
            end;
            v_u_30:get_mission_data(function(p202) --[[ Line: 415 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_11, (copy 3): p_u_195, (copy 4): v_u_201 ]]
                local v203 = v_u_12:get_all()
                for v204 = 1, v203:count() do
                    local v_u_205 = v203:get(v204)
                    v_u_11:playerblob_missiondata_available_foreach(p_u_195, p202, v_u_205, function(p206) --[[ Line: 419 ]]
                        --[[ Upvalues: (ref 1): v_u_11, (ref 2): p_u_195, (copy 3): v_u_205, (ref 4): v_u_201 ]]
                        local v207 = v_u_11:mission_get_id(p206)
                        local v208 = v_u_11:playerblob_missionid_get_count(p_u_195, v_u_205, v207)
                        v_u_11:mission_get_count(p206)
                        v_u_201(p206, v_u_205, v207, v208)
                    end)
                end;
            end)
        end;
        v_u_30.apply_custom_map_like_to_mission_for_player_blob = function(_, p_u_209) --[[ Name: apply_custom_map_like_to_mission_for_player_blob ]] --[[ Line: 471 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_9, (copy 3): p_u_29, (copy 4): v_u_30, (ref 5): v_u_12 ]]
            local v_u_210 = false
            local v_u_211 = 0
            local function v_u_216(p212, p213, p214, p215) --[[ Line: 474 ]]
                --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_9, (ref 3): v_u_210, (ref 4): v_u_211, (copy 5): p_u_209, (ref 6): p_u_29 ]]
                if v_u_11:mission_get_type(p212) == v_u_9.LikeCustomMap then
                    v_u_210 = true
                    v_u_211 = p215 + 1
                    v_u_11:playerblob_missionid_set_count(p_u_209, v_u_11.MissionWriteInfo:new(p213, p214, p_u_29._api:get_day_id(), p_u_29._api:get_week_id()), v_u_211)
                end;
            end;
            v_u_30:get_mission_data(function(p217) --[[ Line: 415 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_11, (copy 3): p_u_209, (copy 4): v_u_216 ]]
                local v218 = v_u_12:get_all()
                for v219 = 1, v218:count() do
                    local v_u_220 = v218:get(v219)
                    v_u_11:playerblob_missiondata_available_foreach(p_u_209, p217, v_u_220, function(p221) --[[ Line: 419 ]]
                        --[[ Upvalues: (ref 1): v_u_11, (ref 2): p_u_209, (copy 3): v_u_220, (ref 4): v_u_216 ]]
                        local v222 = v_u_11:mission_get_id(p221)
                        local v223 = v_u_11:playerblob_missionid_get_count(p_u_209, v_u_220, v222)
                        v_u_11:mission_get_count(p221)
                        v_u_216(p221, v_u_220, v222, v223)
                    end)
                end;
            end)
            return v_u_210, v_u_211;
        end;
        v_u_30.match_end_update_playerblob = function(p_u_224, p_u_225, p_u_226, p_u_227) --[[ Name: match_end_update_playerblob ]] --[[ Line: 484 ]]
            --[[ Upvalues: (copy 1): p_u_29, (ref 2): v_u_14, (ref 3): v_u_5, (ref 4): v_u_24, (ref 5): v_u_25, (ref 6): v_u_15, (ref 7): v_u_6, (ref 8): v_u_12, (ref 9): v_u_11, (ref 10): v_u_9, (ref 11): v_u_13, (ref 12): v_u_19, (ref 13): v_u_16, (ref 14): v_u_8 ]]
            p_u_29._player_blob_manager:get_verified_cached_blob(p_u_225.UserId, function(p_u_228) --[[ Line: 485 ]]
                --[[ Upvalues: (copy 1): p_u_227, (copy 2): p_u_226, (ref 3): v_u_14, (ref 4): v_u_5, (ref 5): p_u_29, (ref 6): v_u_24, (ref 7): v_u_25, (ref 8): v_u_15, (copy 9): p_u_225, (ref 10): v_u_6, (copy 11): p_u_224, (ref 12): v_u_12, (ref 13): v_u_11, (ref 14): v_u_9, (ref 15): v_u_13, (ref 16): v_u_19, (ref 17): v_u_16, (ref 18): v_u_8 ]]
                if p_u_228 == nil then
                    p_u_227()
                else
                    local l_CoinRewardTotal_0 = p_u_226.CoinRewardTotal
                    local v_u_229
                    if l_CoinRewardTotal_0 > 0 then
                        p_u_228.CoinCurrency = p_u_228.CoinCurrency + l_CoinRewardTotal_0
                        v_u_229 = true
                    else
                        v_u_229 = false
                    end;
                    if p_u_226.PlayerBlobUpdateCallbacks ~= nil then
                        local l_PlayerBlobUpdateCallbacks_0 = p_u_226.PlayerBlobUpdateCallbacks
                        for v230 = 1, l_PlayerBlobUpdateCallbacks_0:count() do
                            l_PlayerBlobUpdateCallbacks_0:get(v230)(p_u_228)
                            v_u_229 = true
                        end;
                    end;
                    local l_SongKey_0 = p_u_226.SongKey
                    local l_Place_0 = p_u_226.Place
                    local l_PlayerCount_0 = p_u_226.PlayerCount
                    local l_Score_0 = p_u_226.Score
                    local l_Accuracy_0 = p_u_226.Accuracy
                    local l_Misses_0 = p_u_226.Misses
                    local l_TotalScore_0 = p_u_226.TotalScore
                    local l_GameInstance_0 = p_u_226.GameInstance
                    v_u_14:is_int(l_TotalScore_0)
                    if v_u_5.UseChallengePassV2 == true then
                        if l_PlayerCount_0 >= 3 then
                            p_u_29._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_24.DailyMissionType.Play3PlayerMatch, p_u_228)
                        end;
                        local v231, v232 = v_u_25:is_event_active(p_u_29._api:get_day_event_list())
                        if v231 and v_u_25:get_event_point_reward_song_set(v232):contains(l_SongKey_0) then
                            p_u_29._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_24.DailyMissionType.PlayEventSong, p_u_228)
                        end;
                    elseif l_PlayerCount_0 == 1 then
                        v_u_15:playerblob_apply_action(p_u_228, v_u_15.ActionType.PlaySong1P)
                    elseif l_PlayerCount_0 == 2 then
                        v_u_15:playerblob_apply_action(p_u_228, v_u_15.ActionType.PlaySong2P)
                    elseif l_PlayerCount_0 == 3 then
                        v_u_15:playerblob_apply_action(p_u_228, v_u_15.ActionType.PlaySong3P)
                    elseif l_PlayerCount_0 == 4 then
                        v_u_15:playerblob_apply_action(p_u_228, v_u_15.ActionType.PlaySong4P)
                    end;
                    local function f_send_message_to_player(p233) --[[ Name: send_message_to_player ]] --[[ Line: 536 ]]
                        --[[ Upvalues: (ref 1): p_u_29, (copy 2): l_GameInstance_0, (ref 3): p_u_225, (ref 4): v_u_6 ]]
                        local v234 = p_u_29._chat:get_chat_service()
                        local v235
                        if l_GameInstance_0 then
                            v235 = p_u_29._chat:gameid_get_channel(l_GameInstance_0._game_id)
                        else
                            v235 = nil
                        end;
                        if v235 then
                            v234:send_system_message_to_player_for_channel(p_u_225, v235, p233, function(p236) --[[ Line: 548 ]]
                                --[[ Upvalues: (ref 1): v_u_6 ]]
                                p236:set_channel_name("")
                                p236:set_icon(v_u_6:important_assetid())
                            end)
                        end;
                    end;
                    p_u_224:get_mission_data(function(p237) --[[ Line: 556 ]]
                        --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_11, (copy 3): p_u_228, (copy 4): l_SongKey_0, (copy 5): l_PlayerCount_0, (ref 6): v_u_9, (ref 7): p_u_29, (ref 8): v_u_229, (copy 9): l_Place_0, (copy 10): l_Score_0, (ref 11): v_u_13, (copy 12): l_Accuracy_0, (copy 13): l_TotalScore_0, (ref 14): v_u_19, (ref 15): v_u_16, (copy 16): f_send_message_to_player, (copy 17): l_Misses_0, (ref 18): p_u_225, (ref 19): v_u_8, (ref 20): p_u_227 ]]
                        for _, v_u_238 in v_u_12:get_all():key_itr() do
                            v_u_11:playerblob_missiondata_available_foreach(p_u_228, p237, v_u_238, function(p239) --[[ Line: 558 ]]
                                --[[ Upvalues: (ref 1): v_u_11, (ref 2): l_SongKey_0, (ref 3): l_PlayerCount_0, (ref 4): p_u_228, (copy 5): v_u_238, (ref 6): v_u_9, (ref 7): p_u_29, (ref 8): v_u_229, (ref 9): l_Place_0, (ref 10): l_Score_0, (ref 11): v_u_13, (ref 12): l_Accuracy_0, (ref 13): l_TotalScore_0, (ref 14): v_u_19, (ref 15): v_u_16, (ref 16): f_send_message_to_player, (ref 17): l_Misses_0 ]]
                                local v240 = v_u_11:mission_get_targetsong(p239)
                                local v241 = v_u_11:mission_get_id(p239)
                                if v240 == l_SongKey_0 or v_u_11:mission_is_any_song(p239) ~= false then
                                    if l_PlayerCount_0 < v_u_11:mission_get_playersrequired(p239) then
                                        return;
                                    else
                                        local v242 = v_u_11:playerblob_missionid_get_count(p_u_228, v_u_238, v241)
                                        v_u_11:mission_get_count(p239)
                                        local v243 = v_u_11:mission_get_difficulty(p239)
                                        if v_u_11:mission_get_type(p239) == v_u_9.CompleteMatch then
                                            v_u_11:playerblob_missionid_set_count(p_u_228, v_u_11.MissionWriteInfo:new(v_u_238, v241, p_u_29._api:get_day_id(), p_u_29._api:get_week_id()), v242 + 1)
                                            v_u_229 = true
                                        elseif v_u_11:mission_get_type(p239) == v_u_9.WinMatch then
                                            if l_Place_0 == 1 then
                                                v_u_11:playerblob_missionid_set_count(p_u_228, v_u_11.MissionWriteInfo:new(v_u_238, v241, p_u_29._api:get_day_id(), p_u_29._api:get_week_id()), v242 + 1)
                                                v_u_229 = true
                                                return;
                                            end;
                                        elseif v_u_11:mission_get_type(p239) == v_u_9.Score then
                                            if v242 < l_Score_0 then
                                                v_u_11:playerblob_missionid_set_count(p_u_228, v_u_11.MissionWriteInfo:new(v_u_238, v241, p_u_29._api:get_day_id(), p_u_29._api:get_week_id()), l_Score_0)
                                                v_u_229 = true
                                                return;
                                            end;
                                        elseif v_u_11:mission_get_type(p239) == v_u_9.Rank then
                                            local v244 = v_u_13:rank_value_to_index(v_u_13:accuracy_to_rank_value(l_Accuracy_0))
                                            if v242 < v244 then
                                                v_u_11:playerblob_missionid_set_count(p_u_228, v_u_11.MissionWriteInfo:new(v_u_238, v241, p_u_29._api:get_day_id(), p_u_29._api:get_week_id()), v244)
                                                v_u_229 = true
                                                return;
                                            end;
                                        elseif v_u_11:mission_get_type(p239) == v_u_9.PointTotal then
                                            if v242 < l_TotalScore_0 then
                                                v_u_11:playerblob_missionid_set_count(p_u_228, v_u_11.MissionWriteInfo:new(v_u_238, v241, p_u_29._api:get_day_id(), p_u_29._api:get_week_id()), l_TotalScore_0)
                                                v_u_229 = true
                                                return;
                                            end;
                                        elseif v_u_11:mission_get_type(p239) == v_u_9.ScaledScore then
                                            if v_u_19:mission_difficulty_to_required_accuracy(v243) <= l_Accuracy_0 then
                                                local v245 = v_u_19:get_tier_id_reward_scale((v_u_19:mission_data_get_score_tier_id(v_u_16.MissionData:from_table(p239), l_Score_0)))
                                                if v242 < l_Score_0 then
                                                    v_u_11:playerblob_missionid_set_count(p_u_228, v_u_11.MissionWriteInfo:new(v_u_238, v241, p_u_29._api:get_day_id(), p_u_29._api:get_week_id()), l_TotalScore_0)
                                                    v_u_229 = true
                                                    f_send_message_to_player(string.format("Mission complete! For your score, you got x%.2f the rewards.", v245))
                                                    return;
                                                end;
                                            end;
                                        elseif v_u_11:mission_get_type(p239) == v_u_9.NoMiss then
                                            if l_Misses_0 == 0 then
                                                v_u_11:playerblob_missionid_set_count(p_u_228, v_u_11.MissionWriteInfo:new(v_u_238, v241, p_u_29._api:get_day_id(), p_u_29._api:get_week_id()), 1)
                                                v_u_229 = true
                                                f_send_message_to_player("Mission complete! You completed this song with no misses.")
                                                return;
                                            end;
                                            f_send_message_to_player(string.format("You got %d miss(es) on this play... better luck next time!", l_Misses_0))
                                        end;
                                    end;
                                else
                                    return;
                                end;
                            end)
                        end;
                        if v_u_229 == true then
                            p_u_29._player_blob_manager:enqueue_blob_sync_request(p_u_225.UserId, v_u_8.PlayerBlobRequestType.Write, p_u_227)
                        else
                            p_u_227(p_u_228)
                        end;
                    end)
                end;
            end)
        end;
        local function f_create_mission_leaderboard_entry_from_game_instance(p246) --[[ Name: create_mission_leaderboard_entry_from_game_instance ]] --[[ Line: 645 ]]
            --[[ Upvalues: (copy 1): p_u_29, (ref 2): v_u_20, (ref 3): v_u_22, (ref 4): v_u_21 ]]
            local l__selected_song_key_0 = p246._selected_song_key
            p_u_29._api:get_day_id()
            p_u_29._api:get_week_id()
            local v_u_247 = v_u_20:new()
            p246._util:slots_foreach(function(p248, p249) --[[ Line: 651 ]]
                --[[ Upvalues: (copy 1): v_u_247, (ref 2): v_u_22, (copy 3): l__selected_song_key_0, (ref 4): v_u_21 ]]
                local v250 = v_u_247:get_player_by_slot(p249)
                v250:set_name(p248._name)
                v250:set_id(p248._id)
                v250:set_score(p248._score)
                v250:set_naked_score(p248._naked_score)
                v250:set_gear_power((v_u_21:statsdict_get_gear_power(p248._gear_stats, true, (v_u_22:songkey_get_color_list(l__selected_song_key_0)))))
                v_u_247:set_has_player_in_slot(p249)
            end)
            return v_u_247;
        end;
        v_u_30.on_game_instance_ended = function(p_u_251, p_u_252) --[[ Name: on_game_instance_ended ]] --[[ Line: 672 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_1, (ref 3): v_u_12, (ref 4): v_u_11, (ref 5): v_u_9, (copy 6): f_create_mission_leaderboard_entry_from_game_instance, (copy 7): p_u_29 ]]
            local v262, v263 = v_u_6:try(function() --[[ Line: 673 ]]
                --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_1, (copy 3): p_u_252, (copy 4): p_u_251, (ref 5): v_u_12, (ref 6): v_u_11, (ref 7): v_u_9, (ref 8): f_create_mission_leaderboard_entry_from_game_instance, (ref 9): p_u_29 ]]
                if v_u_6:is_dev_build() then
                    v_u_1:puts("ServerMissionManager:on_game_instance_ended(%d)", p_u_252._selected_song_key)
                end;
                local v253 = p_u_252._util:players_count()
                local v_u_254 = 0
                local v_u_255 = 0
                p_u_252._util:slots_foreach(function(p256, _) --[[ Line: 680 ]]
                    --[[ Upvalues: (ref 1): v_u_255, (ref 2): v_u_254 ]]
                    v_u_255 = v_u_255 + p256._score
                    if p256._early_quit == true then
                        v_u_254 = v_u_254 + 1
                    end;
                end)
                if v253 > v_u_254 then
                    p_u_251:get_mission_data(function(p257) --[[ Line: 688 ]]
                        --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_11, (ref 3): v_u_9, (ref 4): p_u_252, (ref 5): v_u_255, (ref 6): f_create_mission_leaderboard_entry_from_game_instance, (ref 7): p_u_29, (ref 8): v_u_6 ]]
                        for _, v258 in v_u_12:get_all():key_itr() do
                            v_u_11:missiondata_foreach(p257, v258, function(p259) --[[ Line: 690 ]]
                                --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_9, (ref 3): p_u_252, (ref 4): v_u_255, (ref 5): f_create_mission_leaderboard_entry_from_game_instance, (ref 6): p_u_29, (ref 7): v_u_6 ]]
                                if v_u_11:mission_get_type(p259) == v_u_9.PointTotal and (p_u_252._selected_song_key == v_u_11:mission_get_targetsong(p259) and v_u_11:mission_get_count(p259) < v_u_255) then
                                    p_u_29._datastore_api:write_point_total_mission_leaderboard_entry(p_u_252._selected_song_key, f_create_mission_leaderboard_entry_from_game_instance(p_u_252), function(p260) --[[ Line: 698 ]]
                                        --[[ Upvalues: (ref 1): p_u_29, (ref 2): p_u_252, (ref 3): v_u_6 ]]
                                        p_u_29._chat:gameid_send_system_message(p_u_252._game_id, p260, function(p261) --[[ Line: 699 ]]
                                            --[[ Upvalues: (ref 1): v_u_6 ]]
                                            p261:set_icon(v_u_6:important_assetid())
                                        end)
                                    end)
                                end;
                            end)
                        end;
                    end)
                end;
            end)
            if v262 == false then
                v_u_1:errf("ServerMissionManager:on_game_instance_ended() failed: %s", v_u_6:table_to_string(v263))
            end;
        end;
        local v_u_264 = false
        local v_u_265 = v_u_2:new()
        local v_u_266 = v_u_16:new(0, 0)
        v_u_30.get_mission_data = function(_, p_u_267) --[[ Name: get_mission_data ]] --[[ Line: 719 ]]
            --[[ Upvalues: (ref 1): v_u_266, (ref 2): v_u_264, (copy 3): v_u_265, (copy 4): p_u_29, (ref 5): v_u_16, (ref 6): v_u_17 ]]
            local function f_on_completed() --[[ Name: on_completed ]] --[[ Line: 720 ]]
                --[[ Upvalues: (copy 1): p_u_267, (ref 2): v_u_266 ]]
                p_u_267(v_u_266:to_table(), v_u_266)
            end;
            if v_u_264 == false then
                local v268 = v_u_265:count() == 0
                v_u_265:push_back(f_on_completed)
                if v268 then
                    p_u_29._api:api_get_mission_info(function(p269) --[[ Line: 729 ]]
                        --[[ Upvalues: (ref 1): v_u_266, (ref 2): v_u_16, (ref 3): v_u_17, (ref 4): v_u_264, (ref 5): v_u_265 ]]
                        v_u_266 = v_u_16:from_table(p269)
                        v_u_17:preprocess_mission_data(v_u_266)
                        v_u_264 = true
                        for _, v270 in v_u_265:key_itr() do
                            v270()
                        end;
                        v_u_265:clear()
                    end)
                    return;
                end;
            else
                p_u_267(v_u_266:to_table(), v_u_266)
            end;
        end;
        local v_u_271 = -1
        local v_u_272 = v_u_2:new()
        local v_u_273 = v_u_16:new(0, 0)
        v_u_30.get_previous_week_mission_data = function(_, p_u_274) --[[ Name: get_previous_week_mission_data ]] --[[ Line: 751 ]]
            --[[ Upvalues: (ref 1): v_u_273, (copy 2): p_u_29, (ref 3): v_u_271, (copy 4): v_u_272, (ref 5): v_u_16 ]]
            local function f_on_completed() --[[ Name: on_completed ]] --[[ Line: 752 ]]
                --[[ Upvalues: (copy 1): p_u_274, (ref 2): v_u_273 ]]
                p_u_274(v_u_273)
            end;
            local v_u_275 = p_u_29._api:get_day_id() - 7
            if v_u_271 == v_u_275 then
                p_u_274(v_u_273)
            else
                local v276 = v_u_272:count() == 0
                v_u_272:push_back(f_on_completed)
                if v276 then
                    p_u_29._api:api_get_mission_info_for_day(v_u_275, function(p277) --[[ Line: 759 ]]
                        --[[ Upvalues: (ref 1): v_u_273, (ref 2): v_u_16, (ref 3): v_u_271, (copy 4): v_u_275, (ref 5): v_u_272 ]]
                        v_u_273 = v_u_16:from_table(p277)
                        v_u_271 = v_u_275
                        for _, v278 in v_u_272:key_itr() do
                            v278()
                        end;
                        v_u_272:clear()
                    end)
                    return;
                end;
            end;
        end;
        v_u_30.day_update = function(_) --[[ Name: day_update ]] --[[ Line: 774 ]]
            --[[ Upvalues: (ref 1): v_u_264 ]]
            v_u_264 = false
        end;
        v_u_30:start()
        return v_u_30;
    end
};
