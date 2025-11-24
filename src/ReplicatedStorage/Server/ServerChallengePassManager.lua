-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:16 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassUtils)
local v_u_8 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_10 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Data)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
return {
    ["new"] = function(_, p_u_13) --[[ Name: new ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_7, (copy 4): v_u_6, (copy 5): v_u_8, (copy 6): v_u_1, (copy 7): v_u_11, (copy 8): v_u_12, (copy 9): v_u_2, (copy 10): v_u_10, (copy 11): v_u_9, (copy 12): v_u_5 ]]
        local v14 = {
            ["update"] = function(_, _) end
        }
        v14.start = function(p_u_15) --[[ Name: start ]] --[[ Line: 24 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_3, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): v_u_6, (ref 6): v_u_8, (ref 7): v_u_1, (ref 8): v_u_11, (ref 9): v_u_12, (ref 10): v_u_2, (ref 11): v_u_10 ]]
            p_u_15:get_challengepass_data()
            p_u_13._evt:wait_on_event(v_u_3.EVT_ChallengePass_ClientRequestInfo, function(p_u_16) --[[ Line: 27 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_13, (ref 3): v_u_3, (copy 4): p_u_15 ]]
                if v_u_4.UseChallengePassV2 == true then
                    return p_u_13._evt:fire_event_to_client(v_u_3.EVT_ChallengePass_ServerRequestInfoResponse, p_u_16, {}, p_u_13._api:get_month_id(), p_u_13._api:get_time_to_next_month_sec());
                end;
                p_u_15:get_challengepass_data(function(p17) --[[ Line: 31 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_3, (copy 3): p_u_16 ]]
                    p_u_13._evt:fire_event_to_client(v_u_3.EVT_ChallengePass_ServerRequestInfoResponse, p_u_16, p17, p_u_13._api:get_month_id(), p_u_13._api:get_time_to_next_month_sec())
                end)
            end)
            p_u_13._evt:wait_on_event(v_u_3.EVT_ChallengePass_ClientClaimRequest, function(p_u_18) --[[ Line: 36 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_3, (ref 3): v_u_4, (copy 4): p_u_15, (ref 5): v_u_7, (ref 6): v_u_6, (ref 7): v_u_8 ]]
                local function f_response(p19, p20) --[[ Name: response ]] --[[ Line: 37 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_3, (copy 3): p_u_18 ]]
                    p_u_13._evt:fire_event_to_client(v_u_3.EVT_ChallengePass_ServerClaimResponse, p_u_18, p19, p20)
                end;
                if v_u_4.UseChallengePassV2 == true then
                    return f_response(false, "Not Enabled");
                end;
                p_u_15:get_challengepass_data(function(_, p_u_21) --[[ Line: 45 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (copy 2): p_u_18, (ref 3): v_u_7, (copy 4): f_response, (ref 5): v_u_6, (ref 6): v_u_8 ]]
                    p_u_13._player_blob_manager:get_verified_cached_blob(p_u_18.UserId, function(p22) --[[ Line: 46 ]]
                        --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_21, (ref 3): f_response, (ref 4): p_u_13, (ref 5): p_u_18, (ref 6): v_u_6, (ref 7): v_u_8 ]]
                        local v23, v_u_24 = v_u_7:playerblob_get_challengepass_active_mission(p22, p_u_21)
                        if v23 == nil then
                            return f_response(false, "Target ChallengePass mission not found");
                        end;
                        if v_u_7:playerblob_get_challengepass_mission_state(p22, v23, p_u_13._api:get_day_id()) ~= v_u_7.ChallengePassMissionState.CurrentClaimable then
                            return f_response(false, "Target ChallengePass mission is not complete");
                        end;
                        local v_u_25 = v_u_7:playerblob_claim_challengepass_mission(p22, v23, p_u_13._api:get_day_id())
                        local v_u_26, v_u_27 = p_u_13._guild_manager:is_player_in_guild(p_u_18.UserId)
                        p_u_13._player_blob_manager:enqueue_blob_sync_request(p_u_18.UserId, v_u_6.PlayerBlobRequestType.Write, function(_) --[[ Line: 63 ]]
                            --[[ Upvalues: (ref 1): f_response, (copy 2): v_u_25 ]]
                            return f_response(true, v_u_25);
                        end, false, function(p28) --[[ Line: 67 ]]
                            --[[ Upvalues: (copy 1): v_u_26, (ref 2): v_u_8, (copy 3): v_u_24, (copy 4): v_u_27 ]]
                            if v_u_26 then
                                p28:set_guild_contribution(v_u_27, (v_u_8:contribution_source_to_points(v_u_8.ContributionSource.ChallengePassClaim, v_u_24)))
                            end;
                        end)
                    end)
                end)
            end)
            p_u_13._evt:wait_on_event(v_u_3.EVT_ChallengePassV2_ClientRequestInfo, function(p_u_29) --[[ Line: 79 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_1, (copy 3): p_u_15, (ref 4): p_u_13, (ref 5): v_u_3, (ref 6): v_u_11 ]]
                if v_u_4.UseChallengePassV2 ~= true then
                    v_u_1:errf("UseChallengePassV2 not enabled")
                end;
                p_u_15:get_challengepassv2_entry_list(function(p30) --[[ Line: 81 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_3, (copy 3): p_u_29, (ref 4): v_u_11 ]]
                    p_u_13._evt:fire_event_to_client(v_u_3.EVT_ChallengePassV2_ServerRequestInfoResponse, p_u_29, v_u_11:entry_list_to_table(p30))
                end)
            end)
            p_u_13._evt:wait_on_event(v_u_3.EVT_ChallengePassV2_ClientClaimRewards, function(p_u_31, _) --[[ Line: 90 ]]
                --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_1, (ref 3): p_u_13, (ref 4): v_u_3, (copy 5): p_u_15, (ref 6): v_u_12, (ref 7): v_u_2, (ref 8): v_u_10 ]]
                if v_u_4.UseChallengePassV2 ~= true then
                    v_u_1:errf("UseChallengePassV2 not enabled")
                end;
                local function f_response(p32) --[[ Name: response ]] --[[ Line: 93 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_3, (copy 3): p_u_31 ]]
                    p_u_13._evt:fire_event_to_client(v_u_3.EVT_ChallengePassV2_ServerClaimRewardsResponse, p_u_31, p32 == nil and {} or p32)
                end;
                p_u_15:get_challengepassv2_entry_list(function(p_u_33) --[[ Line: 98 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (copy 2): p_u_31, (ref 3): v_u_12, (copy 4): f_response, (ref 5): v_u_2, (ref 6): v_u_10, (ref 7): v_u_3 ]]
                    p_u_13._player_blob_manager:get_verified_cached_blob(p_u_31.UserId, function(p34) --[[ Line: 99 ]]
                        --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_33, (ref 3): p_u_13, (ref 4): f_response, (ref 5): v_u_2, (ref 6): v_u_10, (ref 7): p_u_31, (ref 8): v_u_3 ]]
                        if v_u_12:playerblob_has_any_claimable_rewards_for_day_month(p34, p_u_33, p_u_13._api:get_day_id(), p_u_13._api:get_month_id()) ~= true then
                            return f_response();
                        end;
                        local v35 = v_u_12:playerblob_get_points_total(p34)
                        local v36 = v_u_12:playerblob_get_standard_claimed_tier(p34)
                        local v37 = v_u_12:playerblob_get_vip_claimed_tier(p34)
                        local v38 = v_u_12:playerblob_has_challengepass_vip_unlocked_for_dayid_monthid(p34, p_u_13._api:get_day_id(), p_u_13._api:get_month_id())
                        local v39 = v_u_2:new()
                        for v40 = 1, p_u_33:count() do
                            local v41 = p_u_33:get(v40)
                            if v41:get_points() > v35 then
                                break;
                            end;
                            if v38 == true and v37 < v40 then
                                v39:push_back_from_list(v41:get_reward_list_vip())
                                v37 = v40
                            end;
                            if v36 < v40 then
                                v39:push_back_from_list(v41:get_reward_list_standard())
                                v36 = v40
                            end;
                        end;
                        v_u_12:playerblob_set_standard_claimed_tier(p34, v36)
                        v_u_12:playerblob_set_vip_claimed_tier(p34, v37)
                        local v_u_42 = v_u_10:claim_reward_info_list_to_playerblob(p_u_13, p34, v39)
                        v_u_10:server_sync_reward_params(p_u_13, p_u_31, v_u_42, function(_) --[[ Line: 128 ]]
                            --[[ Upvalues: (ref 1): v_u_10, (copy 2): v_u_42, (ref 3): p_u_13, (ref 4): v_u_3, (ref 5): p_u_31 ]]
                            local v43 = v_u_10.RewardInfo:list_to_table(v_u_10:reward_params_get_resolved_reward_list(v_u_42))
                            p_u_13._evt:fire_event_to_client(v_u_3.EVT_ChallengePassV2_ServerClaimRewardsResponse, p_u_31, v43 == nil and {} or v43)
                        end)
                    end)
                end)
            end)
        end;
        local v_u_44 = false
        local v_u_45 = {}
        local v_u_46 = v_u_2:new()
        local v_u_47 = v_u_2:new()
        v14.get_challengepass_data = function(_, p_u_48) --[[ Name: get_challengepass_data ]] --[[ Line: 140 ]]
            --[[ Upvalues: (ref 1): v_u_44, (copy 2): p_u_13, (ref 3): v_u_4, (ref 4): v_u_47, (ref 5): v_u_11, (ref 6): v_u_46, (ref 7): v_u_7, (ref 8): v_u_45 ]]
            if v_u_44 == false then
                p_u_13._api:api_get_challengepass_info(function(p49) --[[ Line: 142 ]]
                    --[[ Upvalues: (ref 1): v_u_44, (ref 2): v_u_4, (ref 3): v_u_47, (ref 4): v_u_11, (ref 5): v_u_46, (ref 6): v_u_7, (ref 7): v_u_45, (copy 8): p_u_48 ]]
                    v_u_44 = true
                    if v_u_4.UseChallengePassV2 == true then
                        v_u_47 = v_u_11:entry_list_from_legacy_challengepass_mission_json_tab(p49)
                    else
                        v_u_46 = v_u_7:json_to_challengepass_mission_list(p49)
                        v_u_45 = p49
                    end;
                    if p_u_48 then
                        p_u_48(v_u_45, v_u_46)
                    end;
                end)
            elseif p_u_48 then
                p_u_48(v_u_45, v_u_46)
            end;
        end;
        v14.get_cached_challengepass_mission_list = function(_) --[[ Name: get_cached_challengepass_mission_list ]] --[[ Line: 157 ]]
            --[[ Upvalues: (ref 1): v_u_46 ]]
            return v_u_46;
        end;
        v14.day_update = function(_) --[[ Name: day_update ]] --[[ Line: 161 ]]
            --[[ Upvalues: (ref 1): v_u_44 ]]
            v_u_44 = false
        end;
        v14.get_challengepassv2_entry_list = function(p50, p_u_51) --[[ Name: get_challengepassv2_entry_list ]] --[[ Line: 170 ]]
            --[[ Upvalues: (ref 1): v_u_47 ]]
            p50:get_challengepass_data(function() --[[ Line: 171 ]]
                --[[ Upvalues: (copy 1): p_u_51, (ref 2): v_u_47 ]]
                p_u_51(v_u_47)
            end)
        end;
        v14.challengepassv2_daily_mission_playerblob_claim = function(_, p52, p53) --[[ Name: challengepassv2_daily_mission_playerblob_claim ]] --[[ Line: 177 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_9, (ref 3): v_u_12, (ref 4): v_u_1, (ref 5): v_u_6, (copy 6): p_u_13, (ref 7): v_u_5, (ref 8): v_u_11 ]]
            if v_u_4.UseChallengePassV2 ~= true then
                return false;
            end;
            if v_u_9:test_enum_member(p52, v_u_12.DailyMissionType) ~= true then
                v_u_1:warnf("challengepassv2_playerblob_claim_daily_mission is not enum member(%s)", (tostring(p52)))
                return false;
            end;
            local v54 = p_u_13._player_manager:id_to_player((v_u_6:get_user_id(p53)))
            if v54 == nil then
                return false;
            end;
            local v55 = v_u_12:daily_mission_type_playerblob_claim_dayid_monthid(p52, p53, p_u_13._api:get_day_id(), p_u_13._api:get_month_id())
            if v55 == 0 then
                return false;
            end;
            p_u_13._chat:get_chat_service():send_system_message_to_player_for_channel(v54, p_u_13._chat:get_chat_service():get_channel(p_u_13._chat:get_chat_service():get_server_system_channel_id()), string.format("For completing the daily Challenge Pass task \"%s\", you got %s Points! (This Month: %s)", v_u_12:get_daily_mission_name(p52), v_u_5:comma_value(v55), v_u_12:playerblob_get_points_total(p53)), function(p56) --[[ Line: 197 ]]
                --[[ Upvalues: (ref 1): v_u_11 ]]
                p56:set_channel_name("")
                p56:set_icon(v_u_11:get_challengepassv2_square_icon_assetid())
            end)
            return true;
        end;
        v14.challengepassv2_weekly_mission_playerblob_claim = function(_, p57, p58) --[[ Name: challengepassv2_weekly_mission_playerblob_claim ]] --[[ Line: 206 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_9, (ref 3): v_u_12, (ref 4): v_u_1, (ref 5): v_u_6, (copy 6): p_u_13, (ref 7): v_u_5, (ref 8): v_u_11 ]]
            if v_u_4.UseChallengePassV2 ~= true then
                return false;
            end;
            if v_u_9:test_enum_member(p57, v_u_12.WeeklyMissionType) ~= true then
                v_u_1:warnf("challengepassv2_playerblob_claim_weekly_mission is not enum member(%s)", (tostring(p57)))
                return false;
            end;
            local v59 = p_u_13._player_manager:id_to_player((v_u_6:get_user_id(p58)))
            if v59 == nil then
                return false;
            end;
            local v60 = v_u_12:weekly_mission_type_playerblob_claim_weekid_monthid(p57, p58, p_u_13._api:get_week_id(), p_u_13._api:get_month_id())
            if v60 == 0 then
                return false;
            end;
            p_u_13._chat:get_chat_service():send_system_message_to_player_for_channel(v59, p_u_13._chat:get_chat_service():get_channel(p_u_13._chat:get_chat_service():get_server_system_channel_id()), string.format("For completing the weekly Challenge Pass task \"%s\", you got %s Points! (Monthly Total: %s)", v_u_12:get_weekly_mission_name(p57), v_u_5:comma_value(v60), v_u_12:playerblob_get_points_total(p58)), function(p61) --[[ Line: 226 ]]
                --[[ Upvalues: (ref 1): v_u_11 ]]
                p61:set_channel_name("")
                p61:set_icon(v_u_11:get_challengepassv2_square_icon_assetid())
            end)
            return true;
        end;
        return v14;
    end
};
