-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:15 PM
-- Cached decompilation

require(game.ReplicatedStorage.Server.DebugOut)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_5 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
require(game.ReplicatedStorage.Shared.ProdEnvSelector)
local v_u_6 = require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_7 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.SongGatchaUtil)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
return {
    ["new"] = function(_, p_u_10, p_u_11) --[[ Name: new ]] --[[ Line: 20 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_7, (copy 3): v_u_8, (copy 4): v_u_6, (copy 5): v_u_3, (copy 6): v_u_4, (copy 7): v_u_5, (copy 8): v_u_2, (copy 9): v_u_9 ]]
        local v17 = {
            ["get_gatcha_info_from_id"] = function(_, p12, p13) --[[ Name: get_gatcha_info_from_id ]] --[[ Line: 49 ]]
                local v14 = nil
                for v15 = 1, #p12 do
                    local v16 = p12[v15]
                    if v16.ID == p13 then
                        return v16;
                    end;
                end;
                return v14;
            end
        }
        local v_u_18 = {
            {
                ["ID"] = 0,
                ["Cost"] = 1,
                ["Count"] = 1,
                ["Bonus"] = 0
            },
            {
                ["ID"] = 1,
                ["Cost"] = 5,
                ["Count"] = 5,
                ["Bonus"] = 0
            },
            {
                ["ID"] = 2,
                ["Cost"] = 10,
                ["Count"] = 11,
                ["Bonus"] = 1
            }
        }
        v17.get_updated_gatcha_info = function(_, p_u_19) --[[ Name: get_updated_gatcha_info ]] --[[ Line: 43 ]]
            --[[ Upvalues: (copy 1): p_u_11, (copy 2): v_u_18 ]]
            p_u_11:get_updated_shop_info(function(p20) --[[ Line: 44 ]]
                --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_18 ]]
                p_u_19(v_u_18, p20)
            end)
        end;
        v17.start = function(p_u_21) --[[ Name: start ]] --[[ Line: 61 ]]
            --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_1, (ref 3): v_u_7, (ref 4): v_u_8, (ref 5): v_u_6, (ref 6): v_u_3, (ref 7): v_u_4, (ref 8): v_u_5, (ref 9): v_u_2, (ref 10): v_u_9 ]]
            p_u_10._evt:wait_on_event(v_u_1.EVT_Shop_ClientSongGatchaInfoRequest, function(p_u_22) --[[ Line: 62 ]]
                --[[ Upvalues: (copy 1): p_u_21, (ref 2): p_u_10, (ref 3): v_u_1 ]]
                p_u_21:get_updated_gatcha_info(function(p23, _) --[[ Line: 63 ]]
                    --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_1, (copy 3): p_u_22 ]]
                    p_u_10._evt:fire_event_to_client(v_u_1.EVT_Shop_ServerSongGatchaInfoResponse, p_u_22, p23)
                end)
            end)
            p_u_10._evt:wait_on_event(v_u_1.EVT_Shop_ClientSongGatchaAttempt, function(p_u_24, p_u_25, p_u_26) --[[ Line: 72 ]]
                --[[ Upvalues: (copy 1): p_u_21, (ref 2): p_u_10, (ref 3): v_u_1, (ref 4): v_u_7, (ref 5): v_u_8, (ref 6): v_u_6, (ref 7): v_u_3, (ref 8): v_u_4, (ref 9): v_u_5, (ref 10): v_u_2, (ref 11): v_u_9 ]]
                p_u_21:get_updated_gatcha_info(function(p_u_27, _) --[[ Line: 73 ]]
                    --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_1, (copy 3): p_u_24, (ref 4): p_u_21, (copy 5): p_u_25, (ref 6): v_u_7, (copy 7): p_u_26, (ref 8): v_u_8, (ref 9): v_u_6, (ref 10): v_u_3, (ref 11): v_u_4, (ref 12): v_u_5, (ref 13): v_u_2, (ref 14): v_u_9 ]]
                    local function f_fail(p28) --[[ Name: fail ]] --[[ Line: 75 ]]
                        --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_1, (ref 3): p_u_24 ]]
                        p_u_10._evt:fire_event_to_client(v_u_1.EVT_Shop_ServerSongGatchaAttemptResponse, p_u_24, false, nil, p28)
                    end;
                    p_u_10._player_blob_manager:get_verified_cached_blob(p_u_24.UserId, function(p29) --[[ Line: 85 ]]
                        --[[ Upvalues: (copy 1): f_fail, (ref 2): p_u_21, (copy 3): p_u_27, (ref 4): p_u_25, (ref 5): v_u_7, (ref 6): p_u_26, (ref 7): v_u_8, (ref 8): p_u_10, (ref 9): v_u_6, (ref 10): p_u_24, (ref 11): v_u_3, (ref 12): v_u_4, (ref 13): v_u_5, (ref 14): v_u_2, (ref 15): v_u_9, (ref 16): v_u_1 ]]
                        if p29 == nil then
                            return f_fail("Invalid playerblob");
                        end;
                        local v30 = p_u_21:get_gatcha_info_from_id(p_u_27, p_u_25)
                        v_u_7:is_non_nil(v30)
                        v_u_7:is_enum_member(p_u_26, v_u_8.Tiers)
                        local l_Cost_0 = v30.Cost
                        local l_Count_0 = v30.Count
                        local l_Bonus_0 = v30.Bonus
                        v_u_7:is_int(l_Cost_0)
                        v_u_7:is_int(l_Count_0)
                        v_u_7:is_int(l_Bonus_0)
                        local v31
                        if l_Cost_0 <= p29.StarCurrency then
                            p29.StarCurrency = p29.StarCurrency - l_Cost_0
                            v31 = true
                        else
                            v31 = false
                        end;
                        if v31 == false then
                            return f_fail("Not enough currency.");
                        end;
                        p_u_10._api:api_report_evt(v_u_6.ReportEvt_StarMachineSale, l_Count_0, p_u_24.UserId)
                        local v32, v33 = v_u_8:tier_get_available_normal_hard_songs(p_u_26)
                        local v34 = v_u_8:tier_get_hardmode_roll_percentage_d100(p_u_26)
                        local v_u_35 = {}
                        for v36 = 1, l_Count_0 do
                            local v37
                            if v33:count() > 0 and v_u_3:rand_rangef(0, 100) < v34 then
                                v37 = v33:random()
                            else
                                v37 = v32:random()
                            end;
                            v_u_7:is_true(v_u_4:singleton():contains_key(v37))
                            v_u_5:add_song(p29, v37)
                            v_u_35[v36] = v37
                        end;
                        p_u_10._mission_manager:apply_star_machine_count_to_mission_for_player_blob(p29, l_Count_0)
                        if v_u_2.UseChallengePassV2 == true then
                            p_u_10._challengepass_manager:challengepassv2_weekly_mission_playerblob_claim(v_u_9.WeeklyMissionType.RollStarMachine, p29)
                        end;
                        p_u_10._player_blob_manager:enqueue_blob_sync_request(p_u_24.UserId, v_u_5.PlayerBlobRequestType.Write, function(_) --[[ Line: 139 ]]
                            --[[ Upvalues: (ref 1): p_u_10, (ref 2): v_u_1, (ref 3): p_u_24, (copy 4): v_u_35 ]]
                            p_u_10._evt:fire_event_to_client(v_u_1.EVT_Shop_ServerSongGatchaAttemptResponse, p_u_24, true, v_u_35, "")
                        end)
                    end)
                end)
            end)
        end;
        return v17;
    end
};
