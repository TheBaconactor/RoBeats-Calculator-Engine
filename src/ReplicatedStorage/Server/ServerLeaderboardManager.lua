-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:14 PM
-- Time elapsed: 18 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_9 = require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_10 = require(game.ReplicatedStorage.Shared.LeaderboardSongInfo)
local v_u_11 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_12 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_13 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.LeaderboardRewards)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.LeaderboardSongPurchaseInfo)
require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.LeaderboardTicketRewardUtil)
local v_u_17 = require(game.ReplicatedStorage.Shared.Mutex)
local v_u_18 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_19 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
local v_u_20 = require(game.ReplicatedStorage.Shared.APICooldown)
local v21 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_22 = nil
v21:require_server(function() --[[ Line: 25 ]]
    --[[ Upvalues: (ref 1): v_u_22 ]]
    v_u_22 = require(game.ReplicatedStorage.Server.ServerDatastoreImpl.ServerLeaderboardDatastoreManager)
end)
return {
    ["new"] = function(_, p_u_23) --[[ Name: new ]] --[[ Line: 31 ]]
        --[[ Upvalues: (ref 1): v_u_22, (copy 2): v_u_3, (copy 3): v_u_17, (copy 4): v_u_18, (copy 5): v_u_20, (copy 6): v_u_4, (copy 7): v_u_12, (copy 8): v_u_1, (copy 9): v_u_10, (copy 10): v_u_8, (copy 11): v_u_5, (copy 12): v_u_19, (copy 13): v_u_2, (copy 14): v_u_14, (copy 15): v_u_9, (copy 16): v_u_7, (copy 17): v_u_15, (copy 18): v_u_6, (copy 19): v_u_16, (copy 20): v_u_11, (copy 21): v_u_13 ]]
        local v24 = {}
        local v_u_25 = v_u_22:new(p_u_23)
        local function _(p26, p27) --[[ Name: leaderboard_info_table_get_entry_of_song_index ]] --[[ Line: 36 ]]
            local v28 = nil
            for v29 = 1, #p26 do
                local v30 = p26[v29]
                if v30.SongIndex == p27 then
                    v28 = v30
                end;
            end;
            return v28;
        end;
        local v_u_31 = v_u_3:new()
        local function f_get_playerid_entered_leaderboard_count(p_u_32, p_u_33) --[[ Name: get_playerid_entered_leaderboard_count ]] --[[ Line: 48 ]]
            --[[ Upvalues: (copy 1): v_u_31, (copy 2): v_u_25 ]]
            if v_u_31:contains(p_u_32) then
                return p_u_33(v_u_31:get(p_u_32));
            end;
            v_u_25:dsapi_leaderboards_player_check_week_participation_count(p_u_32, function(p34) --[[ Line: 50 ]]
                --[[ Upvalues: (ref 1): v_u_31, (copy 2): p_u_32, (copy 3): p_u_33 ]]
                v_u_31:add(p_u_32, p34)
                p_u_33(p34)
            end)
        end;
        local v_u_35 = v_u_17:new()
        local v_u_36 = v_u_18:new()
        local v_u_37 = v_u_20:new():set_cooldown(1):set_max_queued_requests(8)
        v24.start = function(p_u_38) --[[ Name: start ]] --[[ Line: 61 ]]
            --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_4, (ref 3): v_u_12, (ref 4): v_u_1, (ref 5): v_u_10, (ref 6): v_u_8, (copy 7): v_u_25, (copy 8): v_u_31, (ref 9): v_u_3, (ref 10): v_u_5, (ref 11): v_u_19, (ref 12): v_u_17, (copy 13): v_u_35, (copy 14): v_u_36, (ref 15): v_u_2, (ref 16): v_u_14, (ref 17): v_u_9, (ref 18): v_u_7, (ref 19): v_u_15, (ref 20): v_u_6, (copy 21): v_u_37, (ref 22): v_u_16 ]]
            p_u_23._evt:wait_on_event(v_u_4.EVT_Leaderboard_ClientRequestDisplayInfo, function(p_u_39) --[[ Line: 62 ]]
                --[[ Upvalues: (copy 1): p_u_38, (ref 2): p_u_23, (ref 3): v_u_4 ]]
                p_u_38:get_validated_leaderboard_info(function(p40) --[[ Line: 63 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (copy 3): p_u_39 ]]
                    p_u_23._evt:fire_event_to_client(v_u_4.EVT_Leaderboard_ServerResponseDisplayInfo, p_u_39, p40)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_4.EVT_Leaderboard_ClientQuerySongIndex, function(p_u_41, p_u_42) --[[ Line: 68 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_23, (ref 3): v_u_4, (copy 4): p_u_38, (ref 5): v_u_1 ]]
                v_u_12:is_int_greater_than(p_u_42, 0)
                local function f_response(p43, p44, p45) --[[ Name: response ]] --[[ Line: 71 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (copy 3): p_u_41 ]]
                    p_u_23._evt:fire_event_to_client(v_u_4.EVT_Leaderboard_ServerResponseQuerySongIndex, p_u_41, p43, p44, p45)
                end;
                p_u_38:get_validated_leaderboard_info(function(p46) --[[ Line: 75 ]]
                    --[[ Upvalues: (copy 1): p_u_42, (ref 2): v_u_1, (copy 3): f_response, (ref 4): p_u_38, (copy 5): p_u_41, (ref 6): p_u_23, (ref 7): v_u_4 ]]
                    local v47 = p_u_42
                    local v48 = nil
                    for v49 = 1, #p46 do
                        local v50 = p46[v49]
                        if v50.SongIndex == v47 then
                            v48 = v50
                        end;
                    end;
                    if v48 == nil then
                        v_u_1:warnf("No leaderboard found for song_index(%d)", p_u_42)
                        return f_response(false);
                    end;
                    p_u_38:get_playerid_leaderboard_song_info(p_u_41.UserId, v48, p_u_42, function(p51, p52) --[[ Line: 82 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (ref 3): p_u_41 ]]
                        p_u_23._evt:fire_event_to_client(v_u_4.EVT_Leaderboard_ServerResponseQuerySongIndex, p_u_41, true, p51, p52)
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_4.EVT_Leaderboard_ClientRequestEnterLeaderboard, function(p_u_53, p_u_54) --[[ Line: 88 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_23, (ref 3): v_u_4, (copy 4): p_u_38, (ref 5): v_u_10, (ref 6): v_u_8, (ref 7): v_u_25, (ref 8): v_u_31, (ref 9): v_u_3, (ref 10): v_u_5, (ref 11): v_u_19 ]]
                v_u_12:is_int_greater_than(p_u_54, 0)
                local function f_request_response(p55, p56, p57) --[[ Name: request_response ]] --[[ Line: 90 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (copy 3): p_u_53 ]]
                    p_u_23._evt:fire_event_to_client(v_u_4.EVT_Leaderboard_ServerRequestEnterLeaderboardResponse, p_u_53, p55, p56, p57)
                end;
                p_u_38:get_validated_leaderboard_info(function(p58) --[[ Line: 94 ]]
                    --[[ Upvalues: (copy 1): p_u_54, (copy 2): f_request_response, (ref 3): p_u_38, (copy 4): p_u_53, (ref 5): v_u_10, (ref 6): p_u_23, (ref 7): v_u_8, (ref 8): v_u_25, (ref 9): v_u_31, (ref 10): v_u_3, (ref 11): v_u_5, (ref 12): v_u_19, (ref 13): v_u_4 ]]
                    local v59 = p_u_54
                    local v_u_60 = nil
                    for v61 = 1, #p58 do
                        local v62 = p58[v61]
                        if v62.SongIndex == v59 then
                            v_u_60 = v62
                        end;
                    end;
                    if v_u_60 == nil then
                        return f_request_response(false, "No leaderboard found for song_index", nil);
                    end;
                    p_u_38:get_playerid_leaderboard_song_info(p_u_53.UserId, v_u_60, p_u_54, function(p_u_63, p64) --[[ Line: 100 ]]
                        --[[ Upvalues: (ref 1): f_request_response, (ref 2): v_u_10, (ref 3): p_u_23, (ref 4): p_u_53, (ref 5): v_u_8, (ref 6): v_u_25, (copy 7): v_u_60, (ref 8): p_u_38, (ref 9): p_u_54, (ref 10): v_u_31, (ref 11): v_u_3, (ref 12): v_u_5, (ref 13): v_u_19, (ref 14): v_u_4 ]]
                        if p_u_63.IsEntered ~= false then
                            return f_request_response(false, "Player is already entered", p_u_63);
                        end;
                        if v_u_10:get_max_weekly_entries() <= p64 then
                            return f_request_response(false, "Entered max number of leaderboards for this week", p_u_63);
                        end;
                        p_u_23._player_blob_manager:get_verified_cached_blob(p_u_53.UserId, function(p_u_65) --[[ Line: 106 ]]
                            --[[ Upvalues: (copy 1): p_u_63, (ref 2): v_u_8, (ref 3): f_request_response, (ref 4): v_u_25, (ref 5): p_u_53, (ref 6): v_u_60, (ref 7): p_u_38, (ref 8): p_u_54, (ref 9): v_u_31, (ref 10): v_u_3, (ref 11): v_u_5, (ref 12): p_u_23, (ref 13): v_u_19, (ref 14): v_u_4 ]]
                            if p_u_63.EntryPriceType == v_u_8.CurrencyType.Coins then
                                if v_u_8:get_coin_currency(p_u_65) < p_u_63.EntryPrice then
                                    return f_request_response(false, "Not enough coins", p_u_63);
                                end;
                                v_u_8:set_coin_currency(p_u_65, v_u_8:get_coin_currency(p_u_65) - p_u_63.EntryPrice)
                            else
                                if p_u_63.EntryPriceType ~= v_u_8.CurrencyType.Stars then
                                    return f_request_response(false, "Invalid EntryPriceType", p_u_63);
                                end;
                                if v_u_8:get_star_currency(p_u_65) < p_u_63.EntryPrice then
                                    return f_request_response(false, "Not enough stars", p_u_63);
                                end;
                                v_u_8:set_star_currency(p_u_65, v_u_8:get_star_currency(p_u_65) - p_u_63.EntryPrice)
                            end;
                            v_u_25:dsapi_leaderboards_player_enter_leaderboard(p_u_53.UserId, v_u_60, function(p66) --[[ Line: 123 ]]
                                --[[ Upvalues: (ref 1): f_request_response, (ref 2): p_u_63, (ref 3): p_u_38, (ref 4): p_u_53, (ref 5): p_u_54, (ref 6): v_u_31, (ref 7): v_u_3, (ref 8): v_u_60, (ref 9): v_u_5, (ref 10): p_u_23, (ref 11): v_u_19, (copy 12): p_u_65, (ref 13): v_u_8, (ref 14): v_u_4 ]]
                                if p66 ~= true then
                                    return f_request_response(false, "Failed to enter leaderboard", p_u_63);
                                end;
                                p_u_38:clear_cached_playerid_leaderboard_song_info(p_u_53.UserId, p_u_54)
                                if v_u_31:contains(p_u_53.UserId) then
                                    v_u_3:counter_increment(v_u_31, p_u_53.UserId, 1)
                                end;
                                p_u_38:get_playerid_leaderboard_song_info(p_u_53.UserId, v_u_60, p_u_54, function(p_u_67) --[[ Line: 132 ]]
                                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_23, (ref 3): v_u_19, (ref 4): p_u_65, (ref 5): p_u_53, (ref 6): v_u_8, (ref 7): v_u_4 ]]
                                    if v_u_5.UseChallengePassV2 == true then
                                        p_u_23._challengepass_manager:challengepassv2_weekly_mission_playerblob_claim(v_u_19.WeeklyMissionType.EnterWeeklyLeaderboard, p_u_65)
                                    end;
                                    p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_53.UserId, v_u_8.PlayerBlobRequestType.Write, function(_) --[[ Line: 141 ]]
                                        --[[ Upvalues: (copy 1): p_u_67, (ref 2): p_u_23, (ref 3): v_u_4, (ref 4): p_u_53 ]]
                                        p_u_23._evt:fire_event_to_client(v_u_4.EVT_Leaderboard_ServerRequestEnterLeaderboardResponse, p_u_53, true, "", p_u_67)
                                    end)
                                end)
                            end)
                        end)
                    end)
                end)
            end)
            local v_u_68 = v_u_3:new()
            p_u_23._evt:wait_on_event(v_u_4.EVT_Leaderboard_ClientRequestClaimRewards, function(p_u_69) --[[ Line: 153 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_17, (ref 3): v_u_35, (ref 4): v_u_4, (copy 5): v_u_68, (ref 6): v_u_36, (ref 7): v_u_25, (ref 8): v_u_12, (ref 9): v_u_2, (ref 10): v_u_14, (ref 11): v_u_9 ]]
                local l_UserId_0 = p_u_69.UserId
                local v_u_70 = p_u_23._api:get_week_id()
                local v_u_71 = string.format("%d_%d", l_UserId_0, v_u_70)
                v_u_17:critical_section(function() --[[ Line: 166 ]]
                    --[[ Upvalues: (ref 1): v_u_35, (copy 2): l_UserId_0 ]]
                    return v_u_35:test(l_UserId_0);
                end, function() --[[ Line: 168 ]]
                    --[[ Upvalues: (ref 1): v_u_35, (copy 2): l_UserId_0 ]]
                    v_u_35:retain(l_UserId_0)
                end, function() --[[ Line: 170 ]]
                    --[[ Upvalues: (ref 1): v_u_35, (copy 2): l_UserId_0 ]]
                    v_u_35:release(l_UserId_0)
                end, function() --[[ Line: 172 ]]
                    --[[ Upvalues: (ref 1): v_u_35, (copy 2): l_UserId_0, (ref 3): p_u_23, (ref 4): v_u_4, (copy 5): p_u_69, (ref 6): v_u_68, (copy 7): v_u_71, (copy 8): v_u_70, (ref 9): v_u_36, (ref 10): v_u_25, (ref 11): v_u_12, (ref 12): v_u_2, (ref 13): v_u_14, (ref 14): v_u_9 ]]
                    v_u_35:retain(l_UserId_0)
                    local function f_response(p72, p73, p74) --[[ Name: response ]] --[[ Line: 176 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (ref 3): p_u_69, (ref 4): v_u_35, (ref 5): l_UserId_0 ]]
                        p_u_23._evt:fire_event_to_client(v_u_4.EVT_Leaderboard_ServerRequestClaimRewardsResponse, p_u_69, p72 == nil and true or p72, p73 == nil and "" or p73, p74 == nil and {} or p74)
                        v_u_35:release(l_UserId_0)
                    end;
                    if v_u_68:contains(v_u_71) then
                        return f_response(false, string.format("Leaderboard Rewards already claimed for week %d. (Status: %d)", v_u_70, v_u_68:get(v_u_71)));
                    end;
                    v_u_68:add(v_u_71, 1)
                    v_u_36:add_cooldown_to_id(v_u_71, 300)
                    v_u_36:on_cooldown_last(v_u_71, function() --[[ Line: 191 ]]
                        --[[ Upvalues: (ref 1): v_u_68, (ref 2): v_u_71 ]]
                        v_u_68:remove(v_u_71)
                    end)
                    p_u_23._datastore_api:datastore_api_get_weekly_leaderboard_can_claim(l_UserId_0, v_u_70, function(p_u_75) --[[ Line: 195 ]]
                        --[[ Upvalues: (ref 1): v_u_25, (ref 2): l_UserId_0, (ref 3): p_u_23, (ref 4): v_u_70, (ref 5): v_u_12, (ref 6): v_u_2, (ref 7): v_u_14, (ref 8): p_u_69, (copy 9): f_response, (ref 10): v_u_9, (ref 11): v_u_68, (ref 12): v_u_71 ]]
                        v_u_25:dsapi_leaderboards_player_get_pending_rewards_count(l_UserId_0, function(p_u_76) --[[ Line: 196 ]]
                            --[[ Upvalues: (copy 1): p_u_75, (ref 2): p_u_23, (ref 3): l_UserId_0, (ref 4): v_u_70, (ref 5): v_u_25, (ref 6): v_u_12, (ref 7): v_u_2, (ref 8): v_u_14, (ref 9): p_u_69, (ref 10): f_response, (ref 11): v_u_9, (ref 12): v_u_68, (ref 13): v_u_71 ]]
                            if p_u_75 == true and p_u_76 > 0 then
                                p_u_23._datastore_api:datastore_api_get_weekly_leaderboard_set_claimed(l_UserId_0, v_u_70, function() --[[ Line: 198 ]]
                                    --[[ Upvalues: (ref 1): v_u_25, (ref 2): l_UserId_0, (ref 3): v_u_12, (ref 4): p_u_23, (ref 5): v_u_2, (ref 6): v_u_14, (ref 7): p_u_69, (ref 8): f_response, (ref 9): v_u_9, (ref 10): v_u_70, (copy 11): p_u_76 ]]
                                    v_u_25:dsapi_leaderboards_player_claim_rewards(l_UserId_0, function(p_u_77) --[[ Line: 199 ]]
                                        --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_23, (ref 3): l_UserId_0, (ref 4): v_u_2, (ref 5): v_u_14, (ref 6): p_u_69, (ref 7): f_response, (ref 8): v_u_9, (ref 9): v_u_70, (ref 10): p_u_76 ]]
                                        v_u_12:is_table(p_u_77)
                                        p_u_23._player_blob_manager:get_verified_cached_blob(l_UserId_0, function(p78) --[[ Line: 201 ]]
                                            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_14, (ref 3): p_u_23, (ref 4): p_u_69, (copy 5): p_u_77, (ref 6): f_response, (ref 7): v_u_9, (ref 8): l_UserId_0, (ref 9): v_u_70, (ref 10): p_u_76 ]]
                                            local v_u_79 = v_u_2:new()
                                            v_u_14:apply_rewards_for_claims(p_u_23, p_u_69, p78, p_u_77, function(p80, p81, p82) --[[ Line: 208 ]]
                                                --[[ Upvalues: (copy 1): v_u_79, (ref 2): p_u_23 ]]
                                                v_u_79:push_back({
                                                    ["Rank"] = p80,
                                                    ["Week"] = p81,
                                                    ["SongKey"] = p82,
                                                    ["CurrentDay"] = p_u_23._api:get_day_id(),
                                                    ["OSTime"] = os.time()
                                                })
                                            end, function(p83) --[[ Line: 217 ]]
                                                --[[ Upvalues: (ref 1): f_response, (ref 2): p_u_23, (ref 3): v_u_9, (ref 4): l_UserId_0, (ref 5): v_u_70, (ref 6): p_u_76 ]]
                                                f_response(true, "", p83)
                                                p_u_23._api:api_report_evt(v_u_9.ReportEvt_WeeklyLeaderboardClaimSuccess, l_UserId_0, v_u_70, (tostring(p_u_76)))
                                            end)
                                            p_u_23._datastore_api:log_claim_weekly_leaderboard(l_UserId_0, v_u_79)
                                        end)
                                    end)
                                end)
                                return;
                            elseif p_u_75 == true or p_u_76 <= 0 then
                                if p_u_75 == false then
                                    v_u_68:add(v_u_71, 3)
                                    return f_response(false, string.format("Rewards already claimed for week %d. (Status: %d)", v_u_70, v_u_68:get(v_u_71)));
                                else
                                    v_u_68:add(v_u_71, 4)
                                    return f_response(false, string.format("No rewards to claim for week %d. (Status: %d)", v_u_70, v_u_68:get(v_u_71)));
                                end;
                            else
                                v_u_68:add(v_u_71, 2)
                                return f_response(false, string.format("Error claiming Leaderboard Rewards for week %d. (Status: %d)", v_u_70, v_u_68:get(v_u_71)));
                            end;
                        end)
                    end)
                end)
            end)
            p_u_23._evt:wait_on_event(v_u_4.EVT_Leaderboard_ClientSongBuy, function(p_u_84, p_u_85) --[[ Line: 252 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_23, (ref 3): v_u_4, (copy 4): p_u_38, (ref 5): v_u_7, (ref 6): v_u_8, (ref 7): v_u_15 ]]
                v_u_12:is_int_greater_than(p_u_85, 0)
                local function f_request_response(p86, p87, p88) --[[ Name: request_response ]] --[[ Line: 254 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (copy 3): p_u_84 ]]
                    p_u_23._evt:fire_event_to_client(v_u_4.EVT_Leaderboard_ServerSongBuyResponse, p_u_84, p86, p87, p88)
                end;
                p_u_38:get_validated_leaderboard_info(function(p89) --[[ Line: 258 ]]
                    --[[ Upvalues: (copy 1): p_u_85, (ref 2): v_u_12, (ref 3): v_u_7, (ref 4): p_u_23, (copy 5): p_u_84, (ref 6): v_u_8, (copy 7): f_request_response, (ref 8): v_u_15, (ref 9): v_u_4 ]]
                    local v90 = p_u_85
                    local v91 = nil
                    for v92 = 1, #p89 do
                        local v93 = p89[v92]
                        if v93.SongIndex == v90 then
                            v91 = v93
                        end;
                    end;
                    v_u_12:is_non_nil(v91)
                    local l_SongKey_0 = v91.SongKey
                    v_u_12:is_true(v_u_7:singleton():contains_key(l_SongKey_0))
                    p_u_23._player_blob_manager:get_verified_cached_blob(p_u_84.UserId, function(p94) --[[ Line: 263 ]]
                        --[[ Upvalues: (ref 1): v_u_8, (copy 2): l_SongKey_0, (ref 3): f_request_response, (ref 4): v_u_15, (ref 5): p_u_23, (ref 6): p_u_84, (ref 7): v_u_4 ]]
                        if v_u_8:get_song_key_owned_count(p94, l_SongKey_0) ~= 0 then
                            return f_request_response(false, "Already owned song", -1);
                        end;
                        local v95, v96 = v_u_15:get_price_for_song(l_SongKey_0)
                        if v95 == v_u_8.CurrencyType.Coins then
                            if v_u_8:get_coin_currency(p94) < v96 then
                                return f_request_response(false, "Not enough coins", -1);
                            end;
                            v_u_8:set_coin_currency(p94, v_u_8:get_coin_currency(p94) - v96)
                        else
                            if v95 ~= v_u_8.CurrencyType.Stars then
                                return f_request_response(false, "Invalid Price Type", -1);
                            end;
                            if v_u_8:get_star_currency(p94) < v96 then
                                return f_request_response(false, "Not enough stars", -1);
                            end;
                            v_u_8:set_star_currency(p94, v_u_8:get_star_currency(p94) - v96)
                        end;
                        v_u_8:add_song(p94, l_SongKey_0)
                        p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_84.UserId, v_u_8.PlayerBlobRequestType.Write, function(_) --[[ Line: 287 ]]
                            --[[ Upvalues: (ref 1): l_SongKey_0, (ref 2): p_u_23, (ref 3): v_u_4, (ref 4): p_u_84 ]]
                            p_u_23._evt:fire_event_to_client(v_u_4.EVT_Leaderboard_ServerSongBuyResponse, p_u_84, true, "", l_SongKey_0)
                        end)
                    end)
                end)
            end)
            local function _() --[[ Name: get_last_week_day_id ]] --[[ Line: 295 ]]
                --[[ Upvalues: (ref 1): p_u_23 ]]
                return p_u_23._api:get_day_id() - 7;
            end;
            local function _() --[[ Name: get_last_week_id ]] --[[ Line: 296 ]]
                --[[ Upvalues: (ref 1): p_u_23 ]]
                return p_u_23._api:get_week_id() - 1;
            end;
            local v_u_97 = v_u_3:new()
            local v_u_98 = v_u_3:new()
            p_u_23._evt:wait_on_event(v_u_4.EVT_Leaderboard_ViewLastWeekInfoClient, function(p_u_99) --[[ Line: 300 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (copy 3): v_u_98, (ref 4): v_u_25, (copy 5): v_u_97 ]]
                local v_u_100 = p_u_23._api:get_day_id() - 7
                local v_u_101 = p_u_23._api:get_week_id() - 1
                local function f_response_q1(p_u_102) --[[ Name: response_q1 ]] --[[ Line: 304 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (copy 3): p_u_99, (copy 4): v_u_100, (ref 5): v_u_98, (ref 6): v_u_25, (copy 7): v_u_101 ]]
                    local function _(p103) --[[ Name: response_q2 ]] --[[ Line: 305 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (ref 3): p_u_99, (copy 4): p_u_102 ]]
                        p_u_23._evt:fire_event_to_client(v_u_4.EVT_Leaderboard_ViewLastWeekInfoServer, p_u_99, p_u_102, p103)
                    end;
                    local v_u_104 = string.format("%d_%d", p_u_99.UserId, v_u_100)
                    if v_u_98:contains(v_u_104) then
                        p_u_23._evt:fire_event_to_client(v_u_4.EVT_Leaderboard_ViewLastWeekInfoServer, p_u_99, p_u_102, (v_u_98:get(v_u_104)))
                    else
                        v_u_25:dsapi_leaderboards_player_get_week_entered_leaderboards(p_u_99.UserId, v_u_100, v_u_101, function(p105) --[[ Line: 313 ]]
                            --[[ Upvalues: (ref 1): v_u_98, (copy 2): v_u_104, (ref 3): p_u_23, (ref 4): v_u_4, (ref 5): p_u_99, (copy 6): p_u_102 ]]
                            v_u_98:add(v_u_104, p105)
                            p_u_23._evt:fire_event_to_client(v_u_4.EVT_Leaderboard_ViewLastWeekInfoServer, p_u_99, p_u_102, p105)
                        end)
                    end;
                end;
                if v_u_97:contains(v_u_100) then
                    return f_response_q1(v_u_97:get(v_u_100));
                end;
                v_u_25:dsapi_leaderboards_get_info(function(p106) --[[ Line: 324 ]]
                    --[[ Upvalues: (ref 1): v_u_97, (copy 2): v_u_100, (copy 3): f_response_q1 ]]
                    v_u_97:add(v_u_100, p106)
                    f_response_q1(p106)
                end, v_u_100, v_u_101, 25)
            end)
            local function _(p107, p108, p109) --[[ Name: day_id_player_id_song_index_to_key ]] --[[ Line: 331 ]]
                return string.format("%d_%d_%d", p107, p108, p109);
            end;
            local v_u_110 = v_u_3:new()
            p_u_23._evt:wait_on_event(v_u_4.EVT_Leaderboard_ViewLastWeekSongPersonalClient, function(p_u_111, p_u_112) --[[ Line: 335 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): p_u_23, (ref 3): v_u_4, (ref 4): v_u_6, (copy 5): v_u_110, (ref 6): v_u_37, (ref 7): v_u_25 ]]
                v_u_12:is_int_greater_than(p_u_112, 0)
                local function f_response(p113) --[[ Name: response ]] --[[ Line: 337 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (copy 3): p_u_111 ]]
                    p_u_23._evt:fire_event_to_client(v_u_4.EVT_Leaderboard_ViewLastWeekSongPersonalServer, p_u_111, p113)
                end;
                local v_u_114 = p_u_23._api:get_day_id() - 7
                local v_u_115 = v_u_6:get_player_id(p_u_111)
                local v_u_116 = string.format("%d_%d_%d", v_u_114, v_u_115, p_u_112)
                if v_u_110:contains(v_u_116) then
                    return f_response(v_u_110:get(v_u_116));
                end;
                v_u_37:queue_key_request(p_u_111.UserId, function() --[[ Line: 347 ]]
                    --[[ Upvalues: (ref 1): v_u_25, (copy 2): v_u_115, (copy 3): p_u_112, (ref 4): v_u_110, (copy 5): v_u_116, (ref 6): p_u_23, (ref 7): v_u_4, (copy 8): p_u_111, (copy 9): v_u_114 ]]
                    v_u_25:dsapi_leaderboards_get_player_info(v_u_115, p_u_112, function(p117) --[[ Line: 348 ]]
                        --[[ Upvalues: (ref 1): v_u_110, (ref 2): v_u_116, (ref 3): p_u_23, (ref 4): v_u_4, (ref 5): p_u_111 ]]
                        v_u_110:add(v_u_116, p117)
                        p_u_23._evt:fire_event_to_client(v_u_4.EVT_Leaderboard_ViewLastWeekSongPersonalServer, p_u_111, p117)
                    end, v_u_114)
                end)
            end)
            v_u_16:server_handle_events(p_u_23)
        end;
        local v_u_118 = v_u_3:new()
        v24.get_playerid_leaderboard_song_info = function(_, p_u_119, p_u_120, p_u_121, p_u_122) --[[ Name: get_playerid_leaderboard_song_info ]] --[[ Line: 360 ]]
            --[[ Upvalues: (copy 1): v_u_118, (ref 2): v_u_3, (copy 3): f_get_playerid_entered_leaderboard_count, (copy 4): v_u_37, (copy 5): v_u_25, (ref 6): v_u_12, (ref 7): v_u_10 ]]
            if v_u_118:contains(p_u_119) ~= true then
                v_u_118:add(p_u_119, v_u_3:new())
            end;
            f_get_playerid_entered_leaderboard_count(p_u_119, function(p_u_123) --[[ Line: 365 ]]
                --[[ Upvalues: (ref 1): v_u_118, (copy 2): p_u_119, (copy 3): p_u_121, (ref 4): v_u_37, (ref 5): v_u_25, (ref 6): v_u_12, (ref 7): v_u_10, (copy 8): p_u_120, (copy 9): p_u_122 ]]
                local v_u_124 = v_u_118:get(p_u_119)
                if v_u_124:contains(p_u_121) == true then
                    p_u_122(v_u_10:from_info_table_and_player_leaderboard_info(p_u_120, v_u_124:get(p_u_121)), p_u_123)
                else
                    v_u_37:queue_key_request(p_u_119, function() --[[ Line: 368 ]]
                        --[[ Upvalues: (ref 1): v_u_25, (ref 2): p_u_119, (ref 3): p_u_121, (ref 4): v_u_12, (ref 5): v_u_10, (ref 6): p_u_120, (copy 7): v_u_124, (ref 8): p_u_122, (copy 9): p_u_123 ]]
                        v_u_25:dsapi_leaderboards_get_player_info(p_u_119, p_u_121, function(p125) --[[ Line: 369 ]]
                            --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_10, (ref 3): p_u_120, (ref 4): v_u_124, (ref 5): p_u_121, (ref 6): p_u_122, (ref 7): p_u_123 ]]
                            v_u_12:is_non_nil(p125)
                            local v126 = v_u_10:from_info_table_and_player_leaderboard_info(p_u_120, p125)
                            v_u_124:add(p_u_121, v126)
                            p_u_122(v126, p_u_123)
                        end)
                    end)
                end;
            end)
        end;
        v24.player_disconnecting = function(_, p127) --[[ Name: player_disconnecting ]] --[[ Line: 390 ]]
            --[[ Upvalues: (copy 1): v_u_118, (copy 2): v_u_31 ]]
            v_u_118:remove(p127)
            v_u_31:remove(p127)
        end;
        v24.clear_cached_playerid_leaderboard_song_info = function(_, p128, p129) --[[ Name: clear_cached_playerid_leaderboard_song_info ]] --[[ Line: 395 ]]
            --[[ Upvalues: (copy 1): v_u_118 ]]
            if v_u_118:contains(p128) == true then
                v_u_118:get(p128):remove(p129)
            end;
        end;
        local v_u_130 = -v_u_11.LEADERBOARD_SERVER_UPDATE_TIME_SEC
        local v_u_131 = v_u_2:new()
        local v_u_132 = false
        local v_u_133 = {}
        v24.get_validated_leaderboard_info = function(_, p134) --[[ Name: get_validated_leaderboard_info ]] --[[ Line: 405 ]]
            --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_130, (ref 3): v_u_11, (copy 4): v_u_131, (ref 5): v_u_132, (copy 6): v_u_25, (ref 7): v_u_12, (ref 8): v_u_133 ]]
            if p_u_23._api:get_global_time() - v_u_130 > v_u_11.LEADERBOARD_SERVER_UPDATE_TIME_SEC then
                v_u_131:push_back(p134)
                if v_u_132 ~= true then
                    v_u_132 = true
                    v_u_25:dsapi_leaderboards_get_info(function(p135) --[[ Line: 411 ]]
                        --[[ Upvalues: (ref 1): v_u_132, (ref 2): v_u_12, (ref 3): v_u_133, (ref 4): v_u_130, (ref 5): p_u_23, (ref 6): v_u_131 ]]
                        v_u_132 = false
                        v_u_12:is_non_nil(p135)
                        v_u_133 = p135
                        v_u_130 = p_u_23._api:get_global_time()
                        for v136 = 1, v_u_131:count() do
                            v_u_131:get(v136)(v_u_133)
                        end;
                        v_u_131:clear()
                    end)
                end;
            else
                p134(v_u_133)
            end;
        end;
        v24.write_play_for_playerid_and_songkey = function(p137, p_u_138, p_u_139, p_u_140, p_u_141) --[[ Name: write_play_for_playerid_and_songkey ]] --[[ Line: 433 ]]
            --[[ Upvalues: (copy 1): v_u_118, (ref 2): v_u_6, (copy 3): v_u_25 ]]
            p137:get_validated_leaderboard_info(function(p142) --[[ Line: 438 ]]
                --[[ Upvalues: (copy 1): p_u_139, (ref 2): v_u_118, (copy 3): p_u_138, (ref 4): v_u_6, (ref 5): v_u_25, (copy 6): p_u_140, (copy 7): p_u_141 ]]
                local v_u_143 = -1
                for v144 = 1, #p142 do
                    local v145 = p142[v144]
                    if v145.SongKey == p_u_139 then
                        v_u_143 = v145.SongIndex
                        break;
                    end;
                end;
                if v_u_143 ~= -1 then
                    if v_u_118:contains(p_u_138) then
                        v_u_118:get(p_u_138):remove(v_u_143)
                    end;
                    v_u_6:ptry(function() --[[ Line: 456 ]]
                        --[[ Upvalues: (ref 1): v_u_25, (ref 2): p_u_138, (ref 3): p_u_139, (ref 4): v_u_143, (ref 5): p_u_140, (ref 6): p_u_141 ]]
                        v_u_25:dsapi_write_play(p_u_138, p_u_139, v_u_143, p_u_140, p_u_141)
                    end)
                end;
            end)
        end;
        v24.day_update = function(_) --[[ Name: day_update ]] --[[ Line: 462 ]]
            --[[ Upvalues: (ref 1): v_u_130, (ref 2): v_u_11, (copy 3): v_u_31, (copy 4): v_u_118 ]]
            v_u_130 = -v_u_11.LEADERBOARD_SERVER_UPDATE_TIME_SEC
            v_u_31:clear()
            v_u_118:clear()
        end;
        v24.update = function(_, p_u_146) --[[ Name: update ]] --[[ Line: 468 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_133, (ref 3): v_u_13, (copy 4): v_u_35, (copy 5): v_u_36 ]]
            v_u_6:ptry(function() --[[ Line: 469 ]]
                --[[ Upvalues: (ref 1): v_u_133, (ref 2): v_u_13, (copy 3): p_u_146, (ref 4): v_u_35, (ref 5): v_u_36 ]]
                for v147 = 1, #v_u_133 do
                    local v148 = v_u_133[v147]
                    v148.TimeRemaining = math.max(v148.TimeRemaining - v_u_13:TimescaleToDeltaTime(p_u_146), 0)
                end;
                v_u_35:update(p_u_146)
                v_u_36:update(p_u_146)
            end)
        end;
        return v24;
    end
};
