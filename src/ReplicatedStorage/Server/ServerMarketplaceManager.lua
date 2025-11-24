-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:16 PM
-- Cached decompilation

require(game.ReplicatedStorage.Server.DebugOut)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_5 = require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_6 = require(game.ReplicatedStorage.PlayerInfo.MarketplaceUtils)
local v_u_7 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_8 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_9 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.MarketplaceSale)
local v_u_11 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_12 = require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
return {
    ["new"] = function(_, p_u_13) --[[ Name: new ]] --[[ Line: 20 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_6, (copy 3): v_u_4, (copy 4): v_u_5, (copy 5): v_u_1, (copy 6): v_u_8, (copy 7): v_u_7, (copy 8): v_u_3, (copy 9): v_u_9, (copy 10): v_u_10, (copy 11): v_u_12, (copy 12): v_u_11 ]]
        local v14 = {}
        local v_u_15 = {}
        v14.start = function(p_u_16) --[[ Name: start ]] --[[ Line: 25 ]]
            --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_2, (ref 3): v_u_6, (ref 4): v_u_4, (ref 5): v_u_5, (ref 6): v_u_1, (ref 7): v_u_15, (ref 8): v_u_8, (ref 9): v_u_7, (ref 10): v_u_3, (ref 11): v_u_9, (ref 12): v_u_10 ]]
            p_u_13._evt:wait_on_event(v_u_2.EVT_Marketplace_ClientClaimSoldSales, function(p_u_17) --[[ Line: 26 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_6, (ref 3): v_u_4, (ref 4): v_u_2, (ref 5): v_u_5, (ref 6): v_u_1 ]]
                p_u_13._player_blob_manager:get_verified_cached_blob(p_u_17.UserId, function(p18) --[[ Line: 27 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_13, (copy 3): p_u_17, (ref 4): v_u_4, (ref 5): v_u_2, (ref 6): v_u_5, (ref 7): v_u_1 ]]
                    local v_u_19 = v_u_6:playerblob_claim_purchased_sales(p18)
                    if v_u_19:count() > 0 then
                        p_u_13._player_blob_manager:enqueue_blob_sync_request(p_u_17.UserId, v_u_4.PlayerBlobRequestType.Write, function(_) --[[ Line: 33 ]]
                            --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_2, (ref 3): p_u_17, (ref 4): v_u_6, (copy 5): v_u_19, (ref 6): v_u_5 ]]
                            p_u_13._evt:fire_event_to_client(v_u_2.EVT_Marketplace_ServerClaimSoldSalesResponse, p_u_17, v_u_6:sales_list_to_table(v_u_19))
                            p_u_13._api:api_report_evt(v_u_5.ReportEvt_MarketplaceSaleClaim, p_u_17.UserId, v_u_19:count())
                        end)
                    else
                        p_u_13._evt:fire_event_to_client(v_u_2.EVT_Marketplace_ServerClaimSoldSalesResponse, p_u_17, v_u_6:sales_list_to_table(v_u_1:new()))
                    end;
                end)
            end)
            p_u_13._evt:wait_on_event(v_u_2.EVT_Marketplace_ClientQueryServerSales, function(p20) --[[ Line: 44 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_2, (ref 3): v_u_15 ]]
                p_u_13._evt:fire_event_to_client(v_u_2.EVT_Marketplace_ServerQueryServerSalesResponse, p20, v_u_15)
            end)
            p_u_13._evt:wait_on_event(v_u_2.EVT_Marketplace_ClientCreateNewSale, function(p_u_21, p_u_22, p_u_23, p_u_24) --[[ Line: 48 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_7, (ref 3): v_u_3, (ref 4): p_u_13, (ref 5): v_u_9, (ref 6): v_u_6, (ref 7): v_u_4, (ref 8): v_u_10, (copy 9): p_u_16, (ref 10): v_u_2, (ref 11): v_u_5 ]]
                v_u_8:is_true(v_u_7:singleton():contains_material(p_u_22))
                v_u_8:is_true(v_u_7:singleton():is_material_tradeable(p_u_22))
                v_u_8:is_int(p_u_23)
                v_u_8:is_int(p_u_24)
                v_u_8:is_true(p_u_23 > 0)
                v_u_8:is_true(p_u_23 < v_u_3:input_max_number())
                v_u_8:is_true(p_u_24 > 0)
                v_u_8:is_true(p_u_24 < v_u_3:large_number())
                p_u_13._player_blob_manager:get_verified_cached_blob(p_u_21.UserId, function(p25) --[[ Line: 58 ]]
                    --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_9, (copy 3): p_u_22, (copy 4): p_u_23, (ref 5): v_u_6, (copy 6): p_u_21, (ref 7): p_u_13, (ref 8): v_u_4, (ref 9): v_u_10, (copy 10): p_u_24, (ref 11): p_u_16, (ref 12): v_u_2, (ref 13): v_u_5 ]]
                    v_u_8:is_true(p_u_23 <= v_u_9:get_count_of_material(p25, p_u_22))
                    local v26 = v_u_6:get_sales_list_from_playerblob(p25, p_u_21.Name, p_u_21.UserId)
                    local v_u_27 = v_u_6:get_sale_create_cost_for_playerblob_and_day_and_week(p25, p_u_13._api:get_day_id(), p_u_13._api:get_week_id())
                    v_u_8:is_true(v26:count() < v_u_6:get_player_max_sale_count())
                    v_u_8:is_true(v_u_27 <= v_u_4:get_star_currency(p25))
                    v_u_4:set_star_currency(p25, v_u_4:get_star_currency(p25) - v_u_27)
                    v_u_9:add_crafting_materials_of_id(p25, p_u_22, -p_u_23)
                    v_u_9:validate_playerblob_fevericon(p25, p_u_13)
                    local v_u_28 = v_u_10:new(v_u_6:playerblob_get_next_available_sale_id(p25), p_u_22, p_u_23, p_u_13._api:get_global_time(), p_u_24, false, "")
                    v_u_6:playerblob_add_sale(p25, v_u_28)
                    p_u_13._player_blob_manager:enqueue_blob_sync_request(p_u_21.UserId, v_u_4.PlayerBlobRequestType.Write, function(_) --[[ Line: 88 ]]
                        --[[ Upvalues: (ref 1): p_u_16, (ref 2): p_u_13, (ref 3): v_u_2, (ref 4): p_u_21, (ref 5): v_u_5, (copy 6): v_u_27, (copy 7): v_u_28 ]]
                        p_u_16:update_cached_sales_table()
                        p_u_13._evt:fire_event_to_client(v_u_2.EVT_Marketplace_ServerCreateNewSaleResponse, p_u_21)
                        p_u_13._api:api_report_evt(v_u_5.ReportEvt_MarketplaceSaleCreate, p_u_21.UserId, v_u_27, v_u_28:to_str())
                    end)
                end)
            end)
            p_u_13._evt:wait_on_event(v_u_2.EVT_Marketplace_ClientCancelSale, function(p_u_29, p_u_30) --[[ Line: 97 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_2, (ref 3): v_u_6, (ref 4): v_u_9, (ref 5): v_u_4, (copy 6): p_u_16, (ref 7): v_u_5 ]]
                local function f_response(p31, p32) --[[ Name: response ]] --[[ Line: 98 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_2, (copy 3): p_u_29 ]]
                    p_u_13._evt:fire_event_to_client(v_u_2.EVT_Marketplace_ServerCancelSaleResponse, p_u_29, p31, p32)
                end;
                p_u_13._player_blob_manager:get_verified_cached_blob(p_u_29.UserId, function(p33) --[[ Line: 102 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_30, (copy 3): f_response, (ref 4): v_u_9, (ref 5): p_u_13, (copy 6): p_u_29, (ref 7): v_u_4, (ref 8): p_u_16, (ref 9): v_u_2, (ref 10): v_u_5 ]]
                    local v_u_34 = v_u_6:playerblob_get_sale_index(p33, p_u_30)
                    if v_u_34 == nil then
                        return f_response(false, "Sale not found");
                    end;
                    if v_u_34:get_purchased() ~= false then
                        return f_response(false, "Sale has already been purchased");
                    end;
                    v_u_9:add_crafting_materials_of_id(p33, v_u_34:get_materialid(), v_u_34:get_count())
                    v_u_6:playerblob_remove_sale_index(p33, p_u_30)
                    p_u_13._player_blob_manager:enqueue_blob_sync_request(p_u_29.UserId, v_u_4.PlayerBlobRequestType.Write, function(_) --[[ Line: 118 ]]
                        --[[ Upvalues: (ref 1): p_u_16, (ref 2): p_u_13, (ref 3): v_u_2, (ref 4): p_u_29, (ref 5): v_u_5, (copy 6): v_u_34 ]]
                        p_u_16:update_cached_sales_table()
                        p_u_13._evt:fire_event_to_client(v_u_2.EVT_Marketplace_ServerCancelSaleResponse, p_u_29, true, "")
                        p_u_13._api:api_report_evt(v_u_5.ReportEvt_MarketplaceSaleCancel, p_u_29.UserId, 0, v_u_34:to_str())
                    end)
                end)
            end)
            p_u_13._evt:wait_on_event(v_u_2.EVT_Marketplace_ClientPurchaseSale, function(p_u_35, p_u_36, p_u_37) --[[ Line: 127 ]]
                --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_2, (ref 3): v_u_3, (ref 4): v_u_4, (ref 5): v_u_6, (ref 6): v_u_9, (copy 7): p_u_16, (ref 8): v_u_5, (ref 9): v_u_7 ]]
                local function f_response(p38, p39) --[[ Name: response ]] --[[ Line: 128 ]]
                    --[[ Upvalues: (ref 1): p_u_13, (ref 2): v_u_2, (copy 3): p_u_35 ]]
                    p_u_13._evt:fire_event_to_client(v_u_2.EVT_Marketplace_ServerPurchaseSaleResponse, p_u_35, p38, p39)
                end;
                p_u_13._player_blob_manager:get_ab_verified_cached_blobs(p_u_35.UserId, p_u_36, function(p40, p41) --[[ Line: 134 ]]
                    --[[ Upvalues: (copy 1): f_response, (ref 2): p_u_13, (copy 3): p_u_35, (copy 4): p_u_36, (ref 5): v_u_3, (ref 6): v_u_4, (ref 7): v_u_6, (copy 8): p_u_37, (ref 9): v_u_2, (ref 10): v_u_9, (ref 11): p_u_16, (ref 12): v_u_5, (ref 13): v_u_7 ]]
                    if p40 == nil then
                        return f_response(false, "Buyer playerblob not found");
                    end;
                    if p41 == nil then
                        return f_response(false, "Seller has left the server");
                    end;
                    local v_u_42 = p_u_13._player_manager:id_to_player(p_u_35.UserId)
                    local v_u_43 = p_u_13._player_manager:id_to_player(p_u_36)
                    if v_u_42 == nil or v_u_43 == nil then
                        return f_response(false, "Player has left");
                    end;
                    if p_u_35.UserId == p_u_36 then
                        return f_response(false, "Cannot purchase own sale");
                    end;
                    if v_u_3:player_id_online(p_u_35.UserId) ~= true or v_u_3:player_id_online(p_u_36) ~= true then
                        return f_response(false, "Player not online");
                    end;
                    if v_u_4:is_banned(p40) or v_u_4:is_banned(p41) then
                        return f_response(false, "Buyer or Seller is banned");
                    end;
                    local v_u_44 = v_u_6:playerblob_get_sale_index(p41, p_u_37)
                    if v_u_44 == nil then
                        return f_response(false, "Sale does not exist");
                    end;
                    if v_u_44:get_purchased() == true then
                        return f_response(false, "Sale has already been purchased");
                    end;
                    if v_u_44:get_price() > v_u_4:get_coin_currency(p40) then
                        return f_response(false, "Buyer does not have enough coins");
                    end;
                    if v_u_6:playerblob_mark_sale_index_as_purchased_by(p41, p_u_37, p_u_35.Name) ~= true then
                        p_u_13._evt:fire_event_to_client(v_u_2.EVT_Marketplace_ServerPurchaseSaleResponse, p_u_35, false, "Failed to purchase")
                    end;
                    v_u_4:set_coin_currency(p40, v_u_4:get_coin_currency(p40) - v_u_44:get_price())
                    v_u_9:add_crafting_materials_of_id(p40, v_u_44:get_materialid(), v_u_44:get_count())
                    p_u_13._player_blob_manager:verified_enqueue_ab_blob_sync_request(p_u_35.UserId, p40, p_u_36, p41, function(p45) --[[ Line: 167 ]]
                        --[[ Upvalues: (ref 1): p_u_16, (ref 2): p_u_13, (ref 3): v_u_2, (ref 4): p_u_35, (ref 5): v_u_5, (ref 6): p_u_36, (copy 7): v_u_44, (copy 8): v_u_43, (copy 9): v_u_42, (ref 10): v_u_7, (ref 11): v_u_3 ]]
                        p_u_16:update_cached_sales_table()
                        if p45 then
                            p_u_13._evt:fire_event_to_client(v_u_2.EVT_Marketplace_ServerPurchaseSaleResponse, p_u_35, true, "")
                            p_u_13._api:api_report_evt(v_u_5.ReportEvt_MarketplaceSaleBuy, p_u_35.UserId, p_u_36, v_u_44:to_str())
                            p_u_13._chat:get_chat_service():send_system_message_to_player_for_channel(v_u_43, p_u_13._chat:get_chat_service():get_channel(p_u_13._chat:get_chat_service():get_server_system_channel_id()), string.format("%s has purchased your marketplace sale of x%d %s for %s coins! Visit the marketplace to claim the coins.", v_u_42.Name, v_u_44:get_count(), v_u_7:singleton():get_material_name(v_u_44:get_materialid()), v_u_3:comma_value(v_u_44:get_price())), function(p46) --[[ Line: 176 ]]
                                --[[ Upvalues: (ref 1): v_u_3 ]]
                                p46:set_icon(v_u_3:important_assetid())
                            end)
                        else
                            p_u_13._evt:fire_event_to_client(v_u_2.EVT_Marketplace_ServerPurchaseSaleResponse, p_u_35, false, "Failed to sync")
                        end;
                    end)
                end)
            end)
        end;
        v14.update_cached_sales_table = function(_) --[[ Name: update_cached_sales_table ]] --[[ Line: 188 ]]
            --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_13, (ref 3): v_u_6, (ref 4): v_u_15 ]]
            local v47 = v_u_1:new()
            for v48, v49 in p_u_13._player_manager:players_key_itr() do
                local v50 = p_u_13._player_blob_manager:get_cached_blob(v48)
                if v50 ~= nil and v_u_6:playerblob_has_any_sales(v50) then
                    local v51 = v_u_6:get_sales_list_from_playerblob(v50, v49.Name, v48)
                    for v52 = 1, v51:count() do
                        if v51:get(v52):get_purchased() ~= true then
                            v47:push_back(v51:get(v52))
                        end;
                    end;
                end;
            end;
            v_u_15 = v_u_6:sales_list_to_table(v47)
        end;
        local l_SERVER_MARKETPLACE_REFRESH_TIME_SEC_0 = v_u_12.SERVER_MARKETPLACE_REFRESH_TIME_SEC
        v14.update = function(p53, p54) --[[ Name: update ]] --[[ Line: 206 ]]
            --[[ Upvalues: (ref 1): l_SERVER_MARKETPLACE_REFRESH_TIME_SEC_0, (ref 2): v_u_11, (ref 3): v_u_12 ]]
            l_SERVER_MARKETPLACE_REFRESH_TIME_SEC_0 = l_SERVER_MARKETPLACE_REFRESH_TIME_SEC_0 + v_u_11:TimescaleToDeltaTime(p54)
            if l_SERVER_MARKETPLACE_REFRESH_TIME_SEC_0 > v_u_12.SERVER_MARKETPLACE_REFRESH_TIME_SEC then
                l_SERVER_MARKETPLACE_REFRESH_TIME_SEC_0 = 0
                p53:update_cached_sales_table()
            end;
        end;
        return v14;
    end
};
