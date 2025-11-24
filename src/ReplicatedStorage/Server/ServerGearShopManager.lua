-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:14 PM
-- Cached decompilation

require(game.ReplicatedStorage.Server.DebugOut)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
local v_u_1 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
require(game.ReplicatedStorage.Shared.ProdEnvSelector)
require(game.ReplicatedStorage.Server.ServerAPIManager)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local v_u_4 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_5 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_6 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
return {
    ["new"] = function(_, p_u_7) --[[ Name: new ]] --[[ Line: 21 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_4, (copy 5): v_u_5, (copy 6): v_u_6 ]]
        local v8 = {
            ["update"] = function(_, _) end
        }
        v8.start = function(p_u_9) --[[ Name: start ]] --[[ Line: 39 ]]
            --[[ Upvalues: (copy 1): p_u_7, (ref 2): v_u_1, (ref 3): v_u_2, (ref 4): v_u_3, (ref 5): v_u_4, (ref 6): v_u_5, (ref 7): v_u_6 ]]
            p_u_7._evt:wait_on_event(v_u_1.EVT_GearShop_ClientInfoRequest, function(p_u_10) --[[ Line: 43 ]]
                --[[ Upvalues: (copy 1): p_u_9, (ref 2): p_u_7, (ref 3): v_u_1 ]]
                p_u_9:get_updated_gear_shop_info(function(p11) --[[ Line: 44 ]]
                    --[[ Upvalues: (ref 1): p_u_7, (ref 2): v_u_1, (copy 3): p_u_10 ]]
                    p_u_7._evt:fire_event_to_client(v_u_1.EVT_GearShop_ServerInfoResponse, p_u_10, p11, p_u_7._api:get_time_to_next_day_sec())
                end)
            end)
            p_u_7._evt:wait_on_event(v_u_1.EVT_GearShop_ClientAttemptPurchaseSale, function(p_u_12, p_u_13) --[[ Line: 56 ]]
                --[[ Upvalues: (copy 1): p_u_9, (ref 2): p_u_7, (ref 3): v_u_1, (ref 4): v_u_2, (ref 5): v_u_3, (ref 6): v_u_4, (ref 7): v_u_5, (ref 8): v_u_6 ]]
                p_u_9:get_updated_gear_shop_info(function(p_u_14) --[[ Line: 57 ]]
                    --[[ Upvalues: (ref 1): p_u_7, (copy 2): p_u_12, (copy 3): p_u_13, (ref 4): v_u_1, (ref 5): v_u_2, (ref 6): v_u_3, (ref 7): v_u_4, (ref 8): v_u_5, (ref 9): v_u_6 ]]
                    p_u_7._player_blob_manager:get_verified_cached_blob(p_u_12.UserId, function(p15) --[[ Line: 58 ]]
                        --[[ Upvalues: (copy 1): p_u_14, (ref 2): p_u_13, (ref 3): p_u_7, (ref 4): v_u_1, (ref 5): p_u_12, (ref 6): v_u_2, (ref 7): v_u_3, (ref 8): v_u_4, (ref 9): v_u_5, (ref 10): v_u_6 ]]
                        local v16 = nil
                        for v17 = 1, #p_u_14.AvailableItems do
                            local l_AvailableItems_0 = p_u_14.AvailableItems[v17]
                            if l_AvailableItems_0.SaleId == p_u_13 then
                                v16 = l_AvailableItems_0
                                break;
                            end;
                        end;
                        if v16 == nil then
                            return p_u_7._evt:fire_event_to_client(v_u_1.EVT_GearShop_ServerAttemptPurchaseSaleResponse, p_u_12, false, "Item not found.");
                        elseif p15 == nil then
                            return p_u_7._evt:fire_event_to_client(v_u_1.EVT_GearShop_ServerAttemptPurchaseSaleResponse, p_u_12, false, "PlayerBlob not found.");
                        elseif v_u_2:get_count_for_gear_shop_saleid(p15, p_u_13) > 0 then
                            return p_u_7._evt:fire_event_to_client(v_u_1.EVT_GearShop_ServerAttemptPurchaseSaleResponse, p_u_12, false, "You\'ve already purchased this item.");
                        elseif v_u_3:playerblob_can_add_more_gear(p15) == true then
                            local l_PriceType_0 = v16.PriceType
                            local l_PriceValue_0 = v16.PriceValue
                            local l_EquipmentID_0 = v16.EquipmentID
                            local l_MaterialID_0 = v16.MaterialID
                            local v18 = "Not enough currency"
                            local v19 = false
                            if l_PriceType_0 == v_u_2.CurrencyType.Coins then
                                if l_PriceValue_0 <= p15.CoinCurrency then
                                    p15.CoinCurrency = p15.CoinCurrency - l_PriceValue_0
                                    v19 = true
                                else
                                    v18 = "Not enough coins"
                                end;
                            elseif l_PriceType_0 == v_u_2.CurrencyType.Stars then
                                if l_PriceValue_0 <= p15.StarCurrency then
                                    p15.StarCurrency = p15.StarCurrency - l_PriceValue_0
                                    v19 = true
                                else
                                    v18 = "Not enough stars"
                                end;
                            end;
                            if v19 == false then
                                p_u_7._evt:fire_event_to_client(v_u_1.EVT_GearShop_ServerAttemptPurchaseSaleResponse, p_u_12, false, v18)
                            else
                                local v20 = -1
                                local v_u_21 = -1
                                local v_u_22 = -1
                                if v_u_4:singleton():contains_material(l_MaterialID_0) then
                                    v_u_5:add_crafting_materials_of_id(p15, l_MaterialID_0, 1)
                                else
                                    v_u_22 = v_u_3:playerblob_grant_equipmentid(p15, l_EquipmentID_0)
                                    l_MaterialID_0 = v20
                                    v_u_21 = l_EquipmentID_0
                                end;
                                v_u_2:add_count_for_gear_shop_saleid(p15, p_u_13, p_u_7._api:get_day_id(), 1)
                                p_u_7._player_blob_manager:enqueue_blob_sync_request(p_u_12.UserId, v_u_2.PlayerBlobRequestType.Write, function(p23) --[[ Line: 130 ]]
                                    --[[ Upvalues: (ref 1): p_u_7, (ref 2): v_u_1, (ref 3): p_u_12, (ref 4): v_u_21, (ref 5): l_MaterialID_0, (ref 6): v_u_22, (ref 7): v_u_6, (ref 8): v_u_3, (ref 9): v_u_2 ]]
                                    local function _() --[[ Name: response ]] --[[ Line: 131 ]]
                                        --[[ Upvalues: (ref 1): p_u_7, (ref 2): v_u_1, (ref 3): p_u_12, (ref 4): v_u_21, (ref 5): l_MaterialID_0 ]]
                                        p_u_7._evt:fire_event_to_client(v_u_1.EVT_GearShop_ServerAttemptPurchaseSaleResponse, p_u_12, true, "", v_u_21, l_MaterialID_0)
                                    end;
                                    local v24
                                    if v_u_22 == -1 or (v_u_21 == -1 or v_u_6:singleton():get_equipment_for_id(v_u_21) == nil) then
                                        v24 = false
                                    else
                                        v24 = v_u_3:get_equippedobj_for_slot(p23, v_u_6:singleton():get_equipment_for_id(v_u_21):get_avatar_slot()) == nil
                                    end;
                                    if v24 == true then
                                        v_u_3:playerblob_equip_ownedid(p23, v_u_22)
                                        p_u_7._player_blob_manager:enqueue_blob_sync_request(p_u_12.UserId, v_u_2.PlayerBlobRequestType.Write, function(p25) --[[ Line: 151 ]]
                                            --[[ Upvalues: (ref 1): p_u_7, (ref 2): v_u_1, (ref 3): p_u_12, (ref 4): v_u_21, (ref 5): l_MaterialID_0 ]]
                                            p_u_7._evt:fire_event_to_client(v_u_1.EVT_GearShop_ServerAttemptPurchaseSaleResponse, p_u_12, true, "", v_u_21, l_MaterialID_0)
                                            p_u_7._lobby_manager:update_player_character_to_equipped_data(p_u_12, p25)
                                        end)
                                    else
                                        p_u_7._evt:fire_event_to_client(v_u_1.EVT_GearShop_ServerAttemptPurchaseSaleResponse, p_u_12, true, "", v_u_21, l_MaterialID_0)
                                    end;
                                end)
                            end;
                        else
                            return p_u_7._evt:fire_event_to_client(v_u_1.EVT_GearShop_ServerAttemptPurchaseSaleResponse, p_u_12, false, "Max number of owned gear reached.");
                        end;
                    end)
                end)
            end)
        end;
        local v_u_26 = {
            ["SaleDay"] = 1,
            ["AvailableItems"] = {}
        }
        local v_u_27 = false
        v8.day_update = function(_) --[[ Name: day_update ]] --[[ Line: 170 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            v_u_27 = false
        end;
        v8.get_updated_gear_shop_info = function(_, p_u_28) --[[ Name: get_updated_gear_shop_info ]] --[[ Line: 174 ]]
            --[[ Upvalues: (ref 1): v_u_27, (copy 2): p_u_7, (ref 3): v_u_26 ]]
            if v_u_27 == false then
                p_u_7._api:api_get_gear_sales_info(function(p29) --[[ Line: 176 ]]
                    --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_26, (copy 3): p_u_28 ]]
                    v_u_27 = true
                    v_u_26 = p29
                    p_u_28(v_u_26)
                end)
            else
                p_u_28(v_u_26)
            end;
        end;
        return v8;
    end
};
