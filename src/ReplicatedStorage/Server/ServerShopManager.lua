-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:15 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
require(game.ReplicatedStorage.Shared.ProdEnvSelector)
local v_u_9 = require(game.ReplicatedStorage.Server.ServerAPIManager)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.SellSong)
require(game.ReplicatedStorage.PlayerInfo.MatchLeavePenalty)
local v_u_11 = require(game.ReplicatedStorage.Server.ServerSongGatchaManager)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_12 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_13 = require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
require(game.ServerScriptService.SPDiveAPI)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.DanceType)
local v_u_16 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_17 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_18 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_19 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfoRewardDescription)
local v_u_20 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
return {
    ["new"] = function(_, p_u_21) --[[ Name: new ]] --[[ Line: 33 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_16, (copy 3): v_u_3, (copy 4): v_u_5, (copy 5): v_u_1, (copy 6): v_u_7, (copy 7): v_u_6, (copy 8): v_u_8, (copy 9): v_u_4, (copy 10): v_u_20, (copy 11): v_u_12, (copy 12): v_u_10, (copy 13): v_u_2, (copy 14): v_u_18, (copy 15): v_u_9, (copy 16): v_u_17, (copy 17): v_u_19, (copy 18): v_u_15, (copy 19): v_u_14, (copy 20): v_u_13 ]]
        local v22 = {}
        local s_MarketplaceService_0 = game:GetService("MarketplaceService")
        local v_u_23 = v_u_11:new(p_u_21, v22)
        local v_u_24 = v_u_16:new()
        v22.start = function(p_u_25) --[[ Name: start ]] --[[ Line: 41 ]]
            --[[ Upvalues: (copy 1): p_u_21, (ref 2): v_u_3, (ref 3): v_u_5, (ref 4): v_u_1, (ref 5): v_u_7, (ref 6): v_u_6, (ref 7): v_u_8, (ref 8): v_u_4, (ref 9): v_u_20, (copy 10): v_u_23, (ref 11): v_u_12, (ref 12): v_u_10, (ref 13): v_u_2, (ref 14): v_u_18, (copy 15): s_MarketplaceService_0, (ref 16): v_u_9, (ref 17): v_u_17, (ref 18): v_u_19, (ref 19): v_u_15, (ref 20): v_u_14, (ref 21): v_u_13 ]]
            p_u_21._evt:wait_on_event(v_u_3.EVT_Shop_ClientInfoRequest, function(p_u_26) --[[ Line: 45 ]]
                --[[ Upvalues: (copy 1): p_u_25, (ref 2): p_u_21, (ref 3): v_u_3 ]]
                p_u_25:get_updated_shop_info(function(p27) --[[ Line: 46 ]]
                    --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_3, (copy 3): p_u_26 ]]
                    p_u_21._evt:fire_event_to_client(v_u_3.EVT_Shop_ServerInfoResponse, p_u_26, p27, p_u_21._api:get_time_to_next_day_sec())
                end)
            end)
            p_u_21._evt:wait_on_event(v_u_3.EVT_Shop_ClientAttemptPurchaseSale, function(p_u_28, p_u_29) --[[ Line: 58 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_1, (copy 3): p_u_25, (ref 4): p_u_21, (ref 5): v_u_3, (ref 6): v_u_7, (ref 7): v_u_6, (ref 8): v_u_8, (ref 9): v_u_4, (ref 10): v_u_20 ]]
                local v_u_30 = v_u_5:get_player_id(p_u_28)
                v_u_1:puts("EVT_Shop_ClientAttemptPurchaseSale (%d)", v_u_30)
                p_u_25:get_updated_shop_info(function(p_u_31) --[[ Line: 62 ]]
                    --[[ Upvalues: (ref 1): p_u_21, (copy 2): v_u_30, (copy 3): p_u_29, (ref 4): v_u_3, (copy 5): p_u_28, (ref 6): v_u_7, (ref 7): v_u_6, (ref 8): v_u_8, (ref 9): v_u_4, (ref 10): v_u_20 ]]
                    p_u_21._player_blob_manager:get_verified_cached_blob(v_u_30, function(p32) --[[ Line: 63 ]]
                        --[[ Upvalues: (copy 1): p_u_31, (ref 2): p_u_29, (ref 3): p_u_21, (ref 4): v_u_3, (ref 5): p_u_28, (ref 6): v_u_7, (ref 7): v_u_6, (ref 8): v_u_8, (ref 9): v_u_4, (ref 10): v_u_20, (ref 11): v_u_30 ]]
                        local v33 = nil
                        for v34 = 1, #p_u_31.AvailableItems do
                            local l_AvailableItems_0 = p_u_31.AvailableItems[v34]
                            if l_AvailableItems_0.SaleId == p_u_29 then
                                v33 = l_AvailableItems_0
                                break;
                            end;
                        end;
                        local function f_err(p35) --[[ Name: err ]] --[[ Line: 74 ]]
                            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_3, (ref 3): p_u_28 ]]
                            p_u_21._evt:fire_event_to_client(v_u_3.EVT_Shop_ServerAttemptPurchaseSaleResponse, p_u_28, false, p35)
                        end;
                        if v33 == nil then
                            return f_err("Item not found.");
                        elseif p32 == nil then
                            return f_err("PlayerBlob not found.");
                        elseif v_u_7:get_count_for_song_shop_saleid(p32, p_u_29) > 0 then
                            return f_err("You\'ve already purchased this item.");
                        else
                            local l_PriceType_0 = v33.PriceType
                            local l_PriceValue_0 = v33.PriceValue
                            local l_SongKey_0 = v33.SongKey
                            local l_SaleComboKey_0 = v33.SaleComboKey
                            local v36 = ""
                            v_u_6:singleton():get_difficulty_for_key(l_SongKey_0)
                            local v37 = false
                            if l_PriceType_0 == v_u_7.CurrencyType.Coins then
                                if l_PriceValue_0 <= p32.CoinCurrency then
                                    p32.CoinCurrency = p32.CoinCurrency - l_PriceValue_0
                                    v37 = true
                                else
                                    v36 = "Not enough coins"
                                end;
                            elseif l_PriceType_0 == v_u_7.CurrencyType.Stars then
                                if l_PriceValue_0 <= p32.StarCurrency then
                                    p32.StarCurrency = p32.StarCurrency - l_PriceValue_0
                                    v37 = true
                                else
                                    v36 = "Not enough stars"
                                end;
                            end;
                            if v37 == false then
                                p_u_21._evt:fire_event_to_client(v_u_3.EVT_Shop_ServerAttemptPurchaseSaleResponse, p_u_28, false, v36)
                            else
                                v_u_7:currency_type_to_string(l_PriceType_0)
                                if l_SaleComboKey_0 == nil then
                                    v_u_7:add_song(p32, l_SongKey_0)
                                else
                                    v_u_8:playerblob_apply_salecombokey(p32, l_SaleComboKey_0)
                                end;
                                v_u_7:add_count_for_song_shop_saleid(p32, p_u_29, p_u_21._api:get_day_id(), 1)
                                if v_u_4.UseChallengePassV2 == true then
                                    p_u_21._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_20.DailyMissionType.BuySongShop, p32)
                                end;
                                p_u_21._player_blob_manager:enqueue_blob_sync_request(v_u_30, v_u_7.PlayerBlobRequestType.Write, function(_) --[[ Line: 137 ]]
                                    --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_3, (ref 3): p_u_28, (copy 4): l_SongKey_0 ]]
                                    p_u_21._evt:fire_event_to_client(v_u_3.EVT_Shop_ServerAttemptPurchaseSaleResponse, p_u_28, true, l_SongKey_0)
                                end)
                            end;
                        end;
                    end)
                end)
            end)
            v_u_23:start()
            p_u_21._evt:wait_on_event(v_u_3.EVT_Shop_ClientCombineSongAttempt, function(p_u_38, p_u_39) --[[ Line: 155 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_6, (ref 3): p_u_21, (ref 4): v_u_3, (ref 5): v_u_7 ]]
                v_u_1:puts("EVT_Shop_ClientCombineSongAttempt (%d)", p_u_38.UserId)
                local v40, v_u_41 = v_u_6:singleton():key_has_combineinfo(p_u_39)
                if v40 == false then
                    p_u_21._evt:fire_event_to_client(v_u_3.EVT_Shop_ServerCombineSongAttemptResponse, p_u_38, false, nil, "Song has no combine info.")
                else
                    p_u_21._player_blob_manager:get_verified_cached_blob(p_u_38.UserId, function(p42) --[[ Line: 170 ]]
                        --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_3, (copy 3): p_u_38, (ref 4): v_u_7, (copy 5): p_u_39, (copy 6): v_u_41 ]]
                        if p42 == nil then
                            p_u_21._evt:fire_event_to_client(v_u_3.EVT_Shop_ServerCombineSongAttemptResponse, p_u_38, false, nil, "PlayerBlob not found.")
                            return;
                        elseif v_u_7:get_song_key_owned_count(p42, p_u_39) < v_u_41.RequiredCount then
                            p_u_21._evt:fire_event_to_client(v_u_3.EVT_Shop_ServerCombineSongAttemptResponse, p_u_38, false, nil, "Owned count less than required.")
                        else
                            v_u_7:remove_songs(p42, p_u_39, v_u_41.RequiredCount)
                            v_u_7:add_song(p42, v_u_41.OutputKey)
                            p_u_21._mission_manager:apply_combine_song_count_to_mission_for_player_blob(p42, 1)
                            p_u_21._player_blob_manager:enqueue_blob_sync_request(p_u_38.UserId, v_u_7.PlayerBlobRequestType.Write, function(_) --[[ Line: 202 ]]
                                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_3, (ref 3): p_u_38, (ref 4): v_u_41 ]]
                                p_u_21._evt:fire_event_to_client(v_u_3.EVT_Shop_ServerCombineSongAttemptResponse, p_u_38, true, v_u_41.OutputKey, "")
                            end)
                        end;
                    end)
                end;
            end)
            p_u_21._evt:wait_on_event(v_u_3.EVT_Shop_ClientSellSongAttempt, function(p_u_43, p_u_44) --[[ Line: 217 ]]
                --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_6, (ref 3): p_u_21, (ref 4): v_u_3, (ref 5): v_u_10, (ref 6): v_u_7, (ref 7): v_u_2, (ref 8): v_u_18 ]]
                v_u_12:is_true(v_u_6:singleton():contains_key(p_u_44))
                local function f_response_err(p45) --[[ Name: response_err ]] --[[ Line: 219 ]]
                    --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_3 ]]
                    p_u_21._evt:fire_event_to_client(v_u_3.EVT_Shop_ServerSellSongAttemptResponse, false, p45, {})
                end;
                p_u_21._player_blob_manager:get_verified_cached_blob(p_u_43.UserId, function(p46) --[[ Line: 223 ]]
                    --[[ Upvalues: (copy 1): f_response_err, (ref 2): v_u_10, (copy 3): p_u_44, (ref 4): v_u_7, (ref 5): v_u_2, (ref 6): v_u_18, (ref 7): p_u_21, (copy 8): p_u_43, (ref 9): v_u_3 ]]
                    if p46 == nil then
                        return f_response_err("blob nil");
                    end;
                    if v_u_10:playerblob_can_sell_key(p46, p_u_44) ~= true then
                        return f_response_err("Failed to sell song.");
                    end;
                    if v_u_7:get_song_key_owned_count(p46, p_u_44) <= 0 then
                        return f_response_err("No copies owned.");
                    end;
                    v_u_7:remove_songs(p46, p_u_44, 1)
                    local v47 = v_u_2:new()
                    for v48, v49 in v_u_10:get_sell_rewards_dict(p_u_44):key_itr() do
                        v47:push_back(v_u_18.RewardInfo:new(v_u_18.RewardType.CraftingMaterials, v49, v48))
                    end;
                    v_u_18:server_sync_reward_params(p_u_21, p_u_43, v_u_18:claim_reward_info_list_to_playerblob(p_u_21, p46, v47), function(_, _, p50) --[[ Line: 241 ]]
                        --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_3, (ref 3): p_u_43, (ref 4): v_u_18 ]]
                        p_u_21._evt:fire_event_to_client(v_u_3.EVT_Shop_ServerSellSongAttemptResponse, p_u_43, true, "", v_u_18.RewardInfo:list_to_table(p50))
                    end)
                end)
            end)
            s_MarketplaceService_0.ProcessReceipt = function(p51) --[[ Line: 254 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_8, (ref 3): p_u_21, (ref 4): v_u_9, (ref 5): v_u_5, (ref 6): v_u_17, (ref 7): v_u_2, (ref 8): v_u_3, (ref 9): v_u_18, (ref 10): v_u_19 ]]
                local l_PurchaseId_0 = p51.PurchaseId
                local l_ProductId_0 = p51.ProductId
                local l_PlayerId_0 = p51.PlayerId
                v_u_1:puts("_marketplace_service.ProcessReceipt player(%s) productid(%s)", tostring(p51.PlayerId), (tostring(p51.ProductId)))
                local v52, v53 = v_u_8:productid_requires_day_event(l_ProductId_0)
                if v52 == true and p_u_21._api:get_day_event_list():is_event_type_active(v53) ~= true then
                    p_u_21._api:api_report_evt(v_u_9.ReportEvt_PurchaseFail, l_PlayerId_0, 1, string.format("productid(%s) purchaseid(%s)", tostring(l_ProductId_0), (tostring(l_PurchaseId_0))))
                    return Enum.ProductPurchaseDecision.NotProcessedYet;
                else
                    v_u_5:try(function() --[[ Line: 269 ]]
                        --[[ Upvalues: (ref 1): v_u_17, (ref 2): p_u_21, (copy 3): l_ProductId_0 ]]
                        local v54, v55 = v_u_17:is_event_active(p_u_21._api:get_day_event_list())
                        if v54 then
                            p_u_21._datastore_api:datastore_api_track_event_purchase(p_u_21._api:get_day_id(), v55, l_ProductId_0)
                        end;
                    end)
                    local v_u_56 = p_u_21._player_manager:id_to_player(l_PlayerId_0)
                    if v_u_56 == nil then
                        p_u_21._api:api_report_evt(v_u_9.ReportEvt_PurchaseFail, l_PlayerId_0, 2, string.format("productid(%s) purchaseid(%s)", tostring(l_ProductId_0), (tostring(l_PurchaseId_0))))
                        return Enum.ProductPurchaseDecision.NotProcessedYet;
                    else
                        p_u_21._player_blob_manager:get_verified_cached_blob(v_u_56.UserId, function(p57) --[[ Line: 283 ]]
                            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_9, (copy 3): l_PlayerId_0, (copy 4): l_ProductId_0, (copy 5): l_PurchaseId_0, (ref 6): v_u_2, (ref 7): v_u_3, (copy 8): v_u_56, (ref 9): v_u_18, (ref 10): v_u_19 ]]
                            if p57 == nil then
                                p_u_21._api:api_report_evt(v_u_9.ReportEvt_PurchaseFail, l_PlayerId_0, 3, string.format("productid(%s) purchaseid(%s)", tostring(l_ProductId_0), (tostring(l_PurchaseId_0))))
                                return Enum.ProductPurchaseDecision.NotProcessedYet;
                            end;
                            p_u_21._api:api_report_evt(v_u_9.ReportEvt_RobuxShopSale, l_ProductId_0, l_PlayerId_0)
                            local v_u_58 = false
                            local v_u_59 = ""
                            local function _(p60) --[[ Name: iap_finished_response ]] --[[ Line: 293 ]]
                                --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_21, (ref 3): v_u_3, (ref 4): v_u_56, (ref 5): l_ProductId_0, (ref 6): v_u_58, (ref 7): v_u_59, (ref 8): v_u_18 ]]
                                if p60 == nil then
                                    p60 = v_u_2:new()
                                end;
                                p_u_21._evt:fire_event_to_client(v_u_3.EVT_Shop_IAPFinished, v_u_56, l_ProductId_0, v_u_58, v_u_59, v_u_18.RewardInfo:list_to_table(p60))
                            end;
                            v_u_18:server_sync_reward_params(p_u_21, v_u_56, v_u_18:claim_reward_info_list_to_playerblob(p_u_21, p57, (v_u_19:get_reward_info_list_for_purchase_id(l_ProductId_0))), function(p61, _, p62) --[[ Line: 300 ]]
                                --[[ Upvalues: (ref 1): v_u_58, (ref 2): v_u_59, (ref 3): v_u_2, (ref 4): p_u_21, (ref 5): v_u_3, (ref 6): v_u_56, (ref 7): l_ProductId_0, (ref 8): v_u_18 ]]
                                v_u_58 = true
                                v_u_59 = p61
                                if p62 == nil then
                                    p62 = v_u_2:new()
                                end;
                                p_u_21._evt:fire_event_to_client(v_u_3.EVT_Shop_IAPFinished, v_u_56, l_ProductId_0, v_u_58, v_u_59, v_u_18.RewardInfo:list_to_table(p62))
                            end)
                        end)
                        return Enum.ProductPurchaseDecision.PurchaseGranted;
                    end;
                end;
            end;
            p_u_21._evt:wait_on_event(v_u_3.EVT_DanceShop_ClientInfoRequest, function(p_u_63) --[[ Line: 311 ]]
                --[[ Upvalues: (copy 1): p_u_25, (ref 2): p_u_21, (ref 3): v_u_3 ]]
                p_u_25:get_updated_dance_shop_info(function(p64) --[[ Line: 312 ]]
                    --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_3, (copy 3): p_u_63 ]]
                    p_u_21._evt:fire_event_to_client(v_u_3.EVT_DanceShop_ServerInfoResponse, p_u_63, p64, p_u_21._api:get_time_to_next_day_sec())
                end)
            end)
            p_u_21._evt:wait_on_event(v_u_3.EVT_DanceShop_ClientAttemptPurchase, function(p_u_65, p_u_66) --[[ Line: 322 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_3, (copy 3): p_u_25, (ref 4): v_u_15, (ref 5): v_u_14, (ref 6): v_u_13, (ref 7): v_u_7 ]]
                local function f_response(p67, p68, p69) --[[ Name: response ]] --[[ Line: 323 ]]
                    --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_3, (copy 3): p_u_65 ]]
                    p_u_21._evt:fire_event_to_client(v_u_3.EVT_DanceShop_ServerAttemptPurchaseResponse, p_u_65, p67, p68, p69)
                end;
                p_u_25:get_updated_dance_shop_info(function(p_u_70) --[[ Line: 327 ]]
                    --[[ Upvalues: (ref 1): p_u_21, (copy 2): p_u_65, (copy 3): p_u_66, (copy 4): f_response, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_13, (ref 8): v_u_7, (ref 9): v_u_3 ]]
                    p_u_21._player_blob_manager:get_verified_cached_blob(p_u_65.UserId, function(p71) --[[ Line: 328 ]]
                        --[[ Upvalues: (copy 1): p_u_70, (ref 2): p_u_66, (ref 3): f_response, (ref 4): v_u_15, (ref 5): v_u_14, (ref 6): v_u_13, (ref 7): v_u_7, (ref 8): p_u_21, (ref 9): p_u_65, (ref 10): v_u_3 ]]
                        local v72 = nil
                        for v73 = 1, #p_u_70.AvailableItems do
                            local l_AvailableItems_1 = p_u_70.AvailableItems[v73]
                            if l_AvailableItems_1.SaleId == p_u_66 then
                                v72 = l_AvailableItems_1
                                break;
                            end;
                        end;
                        if v72 == nil or p71 == nil then
                            return f_response(false, "Item not found.", 1);
                        end;
                        local l_DanceId_0 = v72.DanceId
                        v_u_15:type_to_string(v_u_14:singleton():get_dance_type_for_id(l_DanceId_0))
                        if v_u_13:get_owned_danceid_to_equipped_dict(p71):contains(l_DanceId_0) then
                            return f_response(false, "Dance already owned.", l_DanceId_0);
                        end;
                        local l_PriceType_1 = v72.PriceType
                        local l_PriceValue_1 = v72.PriceValue
                        local v74 = "Not enough currency"
                        local v75 = false
                        if l_PriceType_1 == v_u_7.CurrencyType.Coins then
                            if l_PriceValue_1 <= p71.CoinCurrency then
                                p71.CoinCurrency = p71.CoinCurrency - l_PriceValue_1
                                v75 = true
                            else
                                v74 = "Not enough coins"
                            end;
                        elseif l_PriceType_1 == v_u_7.CurrencyType.Stars then
                            if l_PriceValue_1 <= p71.StarCurrency then
                                p71.StarCurrency = p71.StarCurrency - l_PriceValue_1
                                v75 = true
                            else
                                v74 = "Not enough stars"
                            end;
                        end;
                        if v75 ~= true then
                            return f_response(false, v74, l_DanceId_0);
                        end;
                        v_u_13:add_owned_danceid(p71, l_DanceId_0)
                        v_u_13:set_danceid_equipped(p71, l_DanceId_0, true)
                        v_u_13:validate_playerblob(p71)
                        p_u_21._player_blob_manager:enqueue_blob_sync_request(p_u_65.UserId, v_u_7.PlayerBlobRequestType.Write, function(_) --[[ Line: 383 ]]
                            --[[ Upvalues: (copy 1): l_DanceId_0, (ref 2): p_u_21, (ref 3): v_u_3, (ref 4): p_u_65 ]]
                            p_u_21._evt:fire_event_to_client(v_u_3.EVT_DanceShop_ServerAttemptPurchaseResponse, p_u_65, true, "", l_DanceId_0)
                        end)
                    end)
                end)
            end)
            if v_u_5:is_dev_build() then
                v_u_8:run_dev_purchase_info_test()
            end;
        end;
        local v_u_76 = {
            ["SaleDay"] = 0,
            ["AvailableItems"] = {}
        }
        local v_u_77 = {
            ["SaleDay"] = 0,
            ["AvailableItems"] = {}
        }
        local v_u_78 = false
        local v_u_79 = false
        local v_u_80 = {
            ["PriceType"] = v_u_7.CurrencyType.Stars,
            ["PriceValue"] = 5
        }
        v22.day_update = function(_) --[[ Name: day_update ]] --[[ Line: 441 ]]
            --[[ Upvalues: (ref 1): v_u_78, (ref 2): v_u_79 ]]
            v_u_78 = false
            v_u_79 = false
        end;
        v22.get_cached_shop_info = function(_) --[[ Name: get_cached_shop_info ]] --[[ Line: 446 ]]
            --[[ Upvalues: (ref 1): v_u_76 ]]
            return v_u_76;
        end;
        v22.get_updated_shop_info = function(_, p_u_81) --[[ Name: get_updated_shop_info ]] --[[ Line: 450 ]]
            --[[ Upvalues: (ref 1): v_u_78, (copy 2): p_u_21, (ref 3): v_u_76 ]]
            if v_u_78 == false then
                p_u_21._api:api_get_sales_info(function(p82) --[[ Line: 452 ]]
                    --[[ Upvalues: (ref 1): v_u_78, (ref 2): v_u_76, (copy 3): p_u_81 ]]
                    v_u_78 = true
                    table.sort(p82.AvailableItems, function(p83, p84) --[[ Line: 454 ]]
                        return p83.SaleId < p84.SaleId;
                    end)
                    v_u_76 = p82
                    p_u_81(v_u_76)
                end)
            else
                p_u_81(v_u_76)
            end;
        end;
        v22.get_updated_gatcha_info = function(p85, p_u_86) --[[ Name: get_updated_gatcha_info ]] --[[ Line: 465 ]]
            --[[ Upvalues: (copy 1): v_u_80 ]]
            p85:get_updated_shop_info(function(p87) --[[ Line: 466 ]]
                --[[ Upvalues: (copy 1): p_u_86, (ref 2): v_u_80 ]]
                p_u_86(v_u_80, p87)
            end)
        end;
        v22.get_updated_dance_shop_info = function(_, p_u_88) --[[ Name: get_updated_dance_shop_info ]] --[[ Line: 471 ]]
            --[[ Upvalues: (ref 1): v_u_79, (copy 2): p_u_21, (ref 3): v_u_77 ]]
            if v_u_79 == false then
                p_u_21._api:api_get_dance_sales_info(function(p89) --[[ Line: 473 ]]
                    --[[ Upvalues: (ref 1): v_u_79, (ref 2): v_u_77, (copy 3): p_u_88 ]]
                    v_u_79 = true
                    v_u_77 = p89
                    p_u_88(v_u_77)
                end)
            else
                p_u_88(v_u_77)
            end;
        end;
        v22.update = function(_, p90) --[[ Name: update ]] --[[ Line: 483 ]]
            --[[ Upvalues: (copy 1): v_u_24 ]]
            v_u_24:update(p90)
        end;
        return v22;
    end
};
