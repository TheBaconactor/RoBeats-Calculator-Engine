-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.ProdEnvSelector)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_8 = require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_9 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_10 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v_u_11 = require(game.ReplicatedStorage.Shared.ActiveTradeOffer)
local v_u_12 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_13 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_14 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.WaitForFinish)
local v_u_15 = require(game.ReplicatedStorage.Shared.VArg)
local v_u_16 = {
    ["ActivePlayerTrade"] = {}
}
local v_u_24 = {
    ["new"] = function(_, p_u_17, p_u_18, p_u_19) --[[ Name: new ]] --[[ Line: 24 ]]
        --[[ Upvalues: (copy 1): v_u_14, (copy 2): v_u_15, (copy 3): v_u_9, (copy 4): v_u_12, (copy 5): v_u_13 ]]
        v_u_14:is_table(p_u_18)
        v_u_14:is_int(p_u_19)
        v_u_14:is_bool(p_u_18.Accepted)
        v_u_14:is_true(p_u_18.Coins >= 0)
        for v20, v21 in pairs((v_u_15:sparse_array_deconvert(p_u_18.Materials))) do
            v_u_14:is_true(v_u_9:singleton():get_material(v20) ~= nil)
            v_u_14:is_true(v21 >= 0)
        end;
        local v22 = {}
        local l_TRADE_UPDATE_COOLDOWN_TIME_SEC_0 = v_u_12.TRADE_UPDATE_COOLDOWN_TIME_SEC
        v22.get_player = function(_) --[[ Name: get_player ]] --[[ Line: 39 ]]
            --[[ Upvalues: (copy 1): p_u_17 ]]
            return p_u_17;
        end;
        v22.get_player_offer_table = function(_) --[[ Name: get_player_offer_table ]] --[[ Line: 40 ]]
            --[[ Upvalues: (copy 1): p_u_18 ]]
            return p_u_18;
        end;
        v22.get_test_target_player_id = function(_) --[[ Name: get_test_target_player_id ]] --[[ Line: 41 ]]
            --[[ Upvalues: (copy 1): p_u_19 ]]
            return p_u_19;
        end;
        v22.get_time_pending_sec = function(_) --[[ Name: get_time_pending_sec ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): l_TRADE_UPDATE_COOLDOWN_TIME_SEC_0 ]]
            return l_TRADE_UPDATE_COOLDOWN_TIME_SEC_0;
        end;
        v22.update = function(_, p23) --[[ Name: update ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): l_TRADE_UPDATE_COOLDOWN_TIME_SEC_0, (ref 2): v_u_13 ]]
            l_TRADE_UPDATE_COOLDOWN_TIME_SEC_0 = l_TRADE_UPDATE_COOLDOWN_TIME_SEC_0 - v_u_13:TimescaleToDeltaTime(p23)
        end;
        return v22;
    end
}
v_u_16.new = function(_, p_u_25, _) --[[ Name: new ]] --[[ Line: 49 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_5, (copy 5): v_u_1, (copy 6): v_u_24, (copy 7): v_u_14, (copy 8): v_u_7, (copy 9): v_u_8, (copy 10): v_u_6, (copy 11): v_u_11, (copy 12): v_u_10, (copy 13): v_u_16 ]]
    local v28 = {
        ["player_disconnecting"] = function(p26, p27) --[[ Name: player_disconnecting ]] --[[ Line: 290 ]]
            p26:error_remove_active_trade_for_playerid(p27, "Player disconnected")
        end
    }
    local v_u_29 = v_u_2:new()
    local v_u_30 = v_u_3:new()
    v28.start = function(p_u_31) --[[ Name: start ]] --[[ Line: 55 ]]
        --[[ Upvalues: (copy 1): p_u_25, (ref 2): v_u_4, (ref 3): v_u_5, (ref 4): v_u_1, (copy 5): v_u_30, (ref 6): v_u_24, (ref 7): v_u_14, (ref 8): v_u_7, (copy 9): v_u_29 ]]
        p_u_25._evt:wait_on_event(v_u_4.EVT_PlayerTrade_ClientPushLocalOffer, function(p32, p33, p34) --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_1, (ref 3): v_u_30, (ref 4): v_u_24 ]]
            if v_u_5.TradeEnabled ~= true then
                return v_u_1:errf("EVT_PlayerTrade_ClientPushLocalOffer when TradeEnabled ~= true");
            end;
            v_u_30:add(p32.UserId, v_u_24:new(p32, p33, p34))
        end)
        p_u_25._evt:wait_on_event(v_u_4.EVT_PlayerTrade_ClientLeave, function(p35) --[[ Line: 63 ]]
            --[[ Upvalues: (copy 1): p_u_31 ]]
            p_u_31:error_remove_active_trade_for_playerid(p35.UserId, "Player left trade")
        end)
        p_u_25._evt:wait_on_event(v_u_4.EVT_PlayerTrade_ClientConfirm, function(p36, p37) --[[ Line: 67 ]]
            --[[ Upvalues: (ref 1): v_u_14, (copy 2): p_u_31, (ref 3): p_u_25, (ref 4): v_u_4, (ref 5): v_u_7, (ref 6): v_u_29 ]]
            v_u_14:is_bool(p37)
            local l_UserId_0 = p36.UserId
            local v_u_38 = p_u_31:find_active_trade_for_playerid(l_UserId_0)
            if v_u_38 == nil then
                return p_u_25._evt:fire_event_to_client(v_u_4.EVT_Trade_ServerError, p36, "Not in trade.");
            end;
            if v_u_38:has_both_accepted() ~= true then
                return p_u_31:error_remove_active_trade_for_playerid(l_UserId_0, "Attempted to confirm but both players had not accepted");
            end;
            if l_UserId_0 == v_u_38:get_player1_id() then
                v_u_38:set_player1_confirmed(p37)
            else
                if l_UserId_0 ~= v_u_38:get_player2_id() then
                    return p_u_31:error_remove_active_trade_for_playerid(l_UserId_0, "Player not found in active trade");
                end;
                v_u_38:set_player2_confirmed(p37)
            end;
            if p37 ~= true then
                return p_u_31:error_remove_active_trade_for_playerid(l_UserId_0, "Trade was not confirmed");
            end;
            local v39 = p_u_25._player_blob_manager:get_cached_blob(v_u_38:get_player1_id())
            local v40 = p_u_25._player_blob_manager:get_cached_blob(v_u_38:get_player2_id())
            if v39 == nil or v40 == nil then
                return p_u_31:error_remove_active_trade_for_playerid(l_UserId_0, "Apply Active Trade player blob not found");
            end;
            if v_u_7:is_banned(v39) or v_u_7:is_banned(v40) then
                return p_u_31:error_remove_active_trade_for_playerid(l_UserId_0, "Trade failed due to playerblob ban");
            end;
            if v_u_38:has_both_confirmed() == true then
                p_u_31:apply_active_trade(v_u_38, function() --[[ Line: 102 ]]
                    --[[ Upvalues: (ref 1): v_u_29, (copy 2): v_u_38 ]]
                    v_u_29:remove(v_u_38)
                end)
            end;
        end)
    end;
    v28.push_local_offer = function(p41, p42, p43, p44) --[[ Name: push_local_offer ]] --[[ Line: 111 ]]
        --[[ Upvalues: (copy 1): p_u_25, (ref 2): v_u_4, (ref 3): v_u_8, (ref 4): v_u_1 ]]
        local l_UserId_1 = p42.UserId
        local v45 = p41:find_active_trade_for_playerid(l_UserId_1)
        if v45 == nil then
            return p_u_25._evt:fire_event_to_client(v_u_4.EVT_Trade_ServerError, p42, "Not in trade.");
        end;
        if v45:has_both_accepted() == true then
            return p_u_25._evt:fire_event_to_client(v_u_4.EVT_Trade_ServerError, p42, "Tried to update trade after being accepted");
        end;
        if v45:has_both_confirmed() == true then
            return p_u_25._evt:fire_event_to_client(v_u_4.EVT_Trade_ServerError, p42, "Trade has already been confirmed");
        end;
        if l_UserId_1 == v45:get_player1_id() then
            if p44 ~= v45:get_player2_id() then
                return p41:error_remove_active_trade_for_playerid(l_UserId_1, "Target Player not found in active trade");
            end;
        else
            if l_UserId_1 ~= v45:get_player2_id() then
                return p41:error_remove_active_trade_for_playerid(l_UserId_1, "Player not found in active trade");
            end;
            if p44 ~= v45:get_player1_id() then
                return p41:error_remove_active_trade_for_playerid(l_UserId_1, "Target Player not found in active trade");
            end;
        end;
        if l_UserId_1 == v45:get_player1_id() then
            if v45:get_player1_offer():update_from_table(p43) == true then
                v45:get_player2_offer():set_accepted(false)
            end;
        elseif l_UserId_1 == v45:get_player2_id() and v45:get_player2_offer():update_from_table(p43) == true then
            v45:get_player1_offer():set_accepted(false)
        end;
        if v45:validate() ~= true then
            p_u_25._api:api_report_evt(v_u_8.ReportEvt_TradeValidateFailed_UpdateFromTable, v45:get_player1_id(), v45:get_player2_id(), v45:get_string())
            p41:error_remove_active_trade_for_playerid(l_UserId_1, "Client Local Offer validate failed")
            return v_u_1:errf("ActivePlayerTradeManager:apply_active_trade validate failed for players(%s)", (tostring(l_UserId_1)));
        end;
        v45:send_update_to_players()
    end;
    local v_u_46 = v_u_2:new()
    v28.update = function(p_u_47, p48) --[[ Name: update ]] --[[ Line: 165 ]]
        --[[ Upvalues: (copy 1): v_u_46, (copy 2): v_u_30, (ref 3): v_u_6 ]]
        v_u_46:clear()
        for v49, v_u_50 in v_u_30:key_itr() do
            v_u_50:update(p48)
            if v_u_50:get_time_pending_sec() <= 0 then
                v_u_46:push_back(v49)
                v_u_6:try(function() --[[ Line: 171 ]]
                    --[[ Upvalues: (copy 1): p_u_47, (copy 2): v_u_50 ]]
                    p_u_47:push_local_offer(v_u_50:get_player(), v_u_50:get_player_offer_table(), v_u_50:get_test_target_player_id())
                end)
            end;
        end;
        for v51 = 1, v_u_46:count() do
            v_u_30:remove(v_u_46:get(v51))
        end;
    end;
    v28.apply_active_trade = function(p_u_52, p_u_53, p_u_54) --[[ Name: apply_active_trade ]] --[[ Line: 182 ]]
        --[[ Upvalues: (copy 1): p_u_25, (ref 2): v_u_8, (ref 3): v_u_1, (ref 4): v_u_6, (ref 5): v_u_11, (ref 6): v_u_10 ]]
        local v_u_55 = p_u_53:get_player1_id()
        local v_u_56 = p_u_53:get_player2_id()
        p_u_25._player_blob_manager:get_ab_verified_cached_blobs(v_u_55, v_u_56, function(p57, p58) --[[ Line: 187 ]]
            --[[ Upvalues: (copy 1): p_u_53, (ref 2): p_u_25, (ref 3): v_u_8, (copy 4): v_u_55, (copy 5): v_u_56, (copy 6): p_u_52, (ref 7): v_u_1, (ref 8): v_u_6, (ref 9): v_u_11, (ref 10): v_u_10, (copy 11): p_u_54 ]]
            if p_u_53:validate() == true then
                if p_u_53:get_canceled() == true then
                    return p_u_52:error_remove_active_trade_for_playerid(v_u_55, "Apply Active Trade canceled");
                elseif p_u_53:is_completed() == true then
                    return v_u_1:warnf("ActivePlayerTradeManager:apply_active_trade on completed trade");
                else
                    local v59 = p_u_25._player_manager:id_to_player(v_u_55)
                    local v60 = p_u_25._player_manager:id_to_player(v_u_56)
                    if v59 == nil or v60 == nil then
                        if v60 ~= nil then
                            return p_u_52:error_remove_active_trade_for_playerid(v_u_56, "Apply Active Trade player left");
                        end;
                        if v59 ~= nil then
                            return p_u_52:error_remove_active_trade_for_playerid(v_u_55, "Apply Active Trade player left");
                        end;
                    else
                        if v_u_6:player_id_online(v_u_55) ~= true or v_u_6:player_id_online(v_u_56) ~= true then
                            return p_u_52:error_remove_active_trade_for_playerid(v_u_55, "Player not online");
                        end;
                        p_u_53:send_processing_evt_to_players()
                        p_u_25._api:api_report_evt(v_u_8.ReportEvt_TradeProcessed, v_u_55, v_u_56, p_u_53:get_string())
                        v_u_11:add_to_playerblob(p_u_53:get_player2_offer(), p57)
                        v_u_11:remove_from_playerblob(p_u_53:get_player1_offer(), p57)
                        v_u_10:validate_playerblob_fevericon(p57, p_u_25)
                        v_u_11:add_to_playerblob(p_u_53:get_player1_offer(), p58)
                        v_u_11:remove_from_playerblob(p_u_53:get_player2_offer(), p58)
                        v_u_10:validate_playerblob_fevericon(p58, p_u_25)
                        p_u_53:set_completed()
                        p_u_25._player_blob_manager:verified_enqueue_ab_blob_sync_request(v_u_55, p57, v_u_56, p58, function(_) --[[ Line: 232 ]]
                            --[[ Upvalues: (ref 1): p_u_53, (ref 2): p_u_54 ]]
                            p_u_53:send_completed_evt_to_players()
                            p_u_54()
                        end)
                    end;
                end;
            else
                p_u_25._api:api_report_evt(v_u_8.ReportEvt_TradeValidateFailed_ApplyActiveTrade, v_u_55, v_u_56, p_u_53:get_string())
                p_u_52:error_remove_active_trade_for_playerid(v_u_55, "Apply Active Trade validate failed")
                return v_u_1:errf("ActivePlayerTradeManager:apply_active_trade validate failed for players(%s,%s)", tostring(v_u_55), (tostring(v_u_56)));
            end;
        end, true)
    end;
    v28.find_active_trade_for_playerid = function(_, p61) --[[ Name: find_active_trade_for_playerid ]] --[[ Line: 249 ]]
        --[[ Upvalues: (copy 1): v_u_29 ]]
        for v62 = 1, v_u_29:count() do
            local v63 = v_u_29:get(v62)
            if v63:is_trade_for_playerid(p61) then
                return v63;
            end;
        end;
        return nil;
    end;
    v28.error_remove_active_trade_for_playerid = function(_, p64, p65) --[[ Name: error_remove_active_trade_for_playerid ]] --[[ Line: 257 ]]
        --[[ Upvalues: (copy 1): v_u_29, (ref 2): v_u_1 ]]
        for v66 = v_u_29:count(), 1, -1 do
            local v67 = v_u_29:get(v66)
            if v67:is_completed() then
                v_u_1:warnf("ActivePlayerTradeManager:error_remove_active_trade_for_playerid(%s,\"%s\") when trade is completed", tostring(p64), (tostring(p65)))
                return;
            end;
            if v67:is_trade_for_playerid(p64) then
                v67:send_err_to_players(p65)
                v_u_29:remove_at(v66)
                return;
            end;
        end;
    end;
    v28.create_active_player_trade_for_playerids = function(_, p68, p69) --[[ Name: create_active_player_trade_for_playerids ]] --[[ Line: 272 ]]
        --[[ Upvalues: (copy 1): v_u_29, (ref 2): v_u_1, (ref 3): v_u_16, (copy 4): p_u_25 ]]
        for v70 = 1, v_u_29:count() do
            local v71 = v_u_29:get(v70)
            if p68 == v71:get_player1_id() or p68 == v71:get_player2_id() then
                v_u_1:errf("ActivePlayerTradeManager:create_active_player_trade_for_playerids active trade already exists for player(%s)", (tostring(p68)))
            end;
            if p69 == v71:get_player1_id() or p69 == v71:get_player2_id() then
                v_u_1:errf("ActivePlayerTradeManager:create_active_player_trade_for_playerids active trade already exists for player(%s)", (tostring(p69)))
            end;
        end;
        local v72 = v_u_16.ActivePlayerTrade:new(p_u_25, p68, p69)
        v_u_29:push_back(v72)
        v72:send_update_to_players()
    end;
    return v28;
end;
v_u_16.ActivePlayerTrade.new = function(_, p_u_73, p_u_74, p_u_75) --[[ Name: new ]] --[[ Line: 298 ]]
    --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_4 ]]
    local v76 = {}
    local v_u_77 = v_u_11:new()
    local v_u_78 = v_u_11:new()
    local v_u_79 = false
    local v_u_80 = false
    v76.get_canceled = function(_) --[[ Name: get_canceled ]] --[[ Line: 305 ]]
        --[[ Upvalues: (ref 1): v_u_79 ]]
        return v_u_79;
    end;
    v76.set_canceled = function(_) --[[ Name: set_canceled ]] --[[ Line: 306 ]]
        --[[ Upvalues: (ref 1): v_u_79 ]]
        v_u_79 = true
    end;
    v76.set_completed = function(_) --[[ Name: set_completed ]] --[[ Line: 308 ]]
        --[[ Upvalues: (ref 1): v_u_80 ]]
        v_u_80 = true
    end;
    v76.is_completed = function(_) --[[ Name: is_completed ]] --[[ Line: 309 ]]
        --[[ Upvalues: (ref 1): v_u_80 ]]
        return v_u_80;
    end;
    v76.get_player1_offer = function(_) --[[ Name: get_player1_offer ]] --[[ Line: 311 ]]
        --[[ Upvalues: (copy 1): v_u_77 ]]
        return v_u_77;
    end;
    v76.get_player2_offer = function(_) --[[ Name: get_player2_offer ]] --[[ Line: 312 ]]
        --[[ Upvalues: (copy 1): v_u_78 ]]
        return v_u_78;
    end;
    v76.get_player1_id = function(_) --[[ Name: get_player1_id ]] --[[ Line: 313 ]]
        --[[ Upvalues: (copy 1): p_u_74 ]]
        return p_u_74;
    end;
    v76.get_player2_id = function(_) --[[ Name: get_player2_id ]] --[[ Line: 314 ]]
        --[[ Upvalues: (copy 1): p_u_75 ]]
        return p_u_75;
    end;
    local v_u_81 = false
    local v_u_82 = false
    v76.set_player1_confirmed = function(_, p83) --[[ Name: set_player1_confirmed ]] --[[ Line: 318 ]]
        --[[ Upvalues: (ref 1): v_u_81 ]]
        v_u_81 = p83
    end;
    v76.set_player2_confirmed = function(_, p84) --[[ Name: set_player2_confirmed ]] --[[ Line: 319 ]]
        --[[ Upvalues: (ref 1): v_u_82 ]]
        v_u_82 = p84
    end;
    v76.send_err_to_players = function(p85, p86) --[[ Name: send_err_to_players ]] --[[ Line: 321 ]]
        --[[ Upvalues: (copy 1): p_u_73, (copy 2): p_u_74, (ref 3): v_u_4, (copy 4): p_u_75 ]]
        p85:set_canceled()
        local v87 = p_u_73._player_manager:id_to_player(p_u_74)
        if v87 then
            p_u_73._evt:fire_event_to_client(v_u_4.EVT_Trade_ServerError, v87, p86)
        end;
        local v88 = p_u_73._player_manager:id_to_player(p_u_75)
        if v88 then
            p_u_73._evt:fire_event_to_client(v_u_4.EVT_Trade_ServerError, v88, p86)
        end;
    end;
    v76.send_update_to_players = function(p89) --[[ Name: send_update_to_players ]] --[[ Line: 334 ]]
        --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_77, (copy 3): v_u_78, (copy 4): p_u_73, (copy 5): p_u_74, (copy 6): p_u_75 ]]
        local l_EVT_PlayerTrade_ServerNotifyOfferInfo_0 = v_u_4.EVT_PlayerTrade_ServerNotifyOfferInfo
        if p89:has_both_accepted() then
            l_EVT_PlayerTrade_ServerNotifyOfferInfo_0 = v_u_4.EVT_PlayerTrade_ServerNotifyTradeConfirm
        end;
        local v90 = v_u_77:export_to_table()
        local v91 = v_u_78:export_to_table()
        local v92 = p_u_73._player_manager:id_to_player(p_u_74)
        local v93 = p_u_73._player_manager:id_to_player(p_u_75)
        if v92 and v93 then
            p_u_73._evt:fire_event_to_client(l_EVT_PlayerTrade_ServerNotifyOfferInfo_0, v92, v90, v91)
            p_u_73._evt:fire_event_to_client(l_EVT_PlayerTrade_ServerNotifyOfferInfo_0, v93, v91, v90)
        end;
    end;
    v76.has_both_accepted = function(_) --[[ Name: has_both_accepted ]] --[[ Line: 351 ]]
        --[[ Upvalues: (copy 1): v_u_77, (copy 2): v_u_78 ]]
        local v94 = v_u_77:get_accepted()
        if v94 then
            v94 = v_u_78:get_accepted()
        end;
        return v94;
    end;
    v76.has_both_confirmed = function(_) --[[ Name: has_both_confirmed ]] --[[ Line: 355 ]]
        --[[ Upvalues: (ref 1): v_u_81, (ref 2): v_u_82 ]]
        local v95 = v_u_81
        if v95 then
            v95 = v_u_82
        end;
        return v95;
    end;
    v76.is_trade_for_playerid = function(_, p96) --[[ Name: is_trade_for_playerid ]] --[[ Line: 359 ]]
        --[[ Upvalues: (copy 1): p_u_74, (copy 2): p_u_75 ]]
        return p96 == p_u_74 and true or p96 == p_u_75;
    end;
    v76.validate = function(_) --[[ Name: validate ]] --[[ Line: 363 ]]
        --[[ Upvalues: (copy 1): p_u_73, (copy 2): p_u_74, (copy 3): p_u_75, (ref 4): v_u_11, (copy 5): v_u_77, (copy 6): v_u_78 ]]
        local v97 = p_u_73._player_blob_manager:get_cached_blob(p_u_74)
        local v98 = p_u_73._player_blob_manager:get_cached_blob(p_u_75)
        if v97 == nil or v98 == nil then
            return false;
        end;
        local v99 = v_u_11:validate_to_playerblob(v_u_77, v97)
        if v99 then
            v99 = v_u_11:validate_to_playerblob(v_u_78, v98)
        end;
        return v99;
    end;
    v76.send_processing_evt_to_players = function(_) --[[ Name: send_processing_evt_to_players ]] --[[ Line: 372 ]]
        --[[ Upvalues: (copy 1): p_u_73, (copy 2): p_u_74, (ref 3): v_u_4, (copy 4): v_u_77, (copy 5): v_u_78, (copy 6): p_u_75 ]]
        local v100 = p_u_73._player_manager:id_to_player(p_u_74)
        if v100 then
            p_u_73._evt:fire_event_to_client(v_u_4.EVT_PlayerTrade_ServerNotifyTradeProcessing, v100, v_u_77:export_to_table(), v_u_78:export_to_table())
        end;
        local v101 = p_u_73._player_manager:id_to_player(p_u_75)
        if v101 then
            p_u_73._evt:fire_event_to_client(v_u_4.EVT_PlayerTrade_ServerNotifyTradeProcessing, v101, v_u_78:export_to_table(), v_u_77:export_to_table())
        end;
    end;
    v76.send_completed_evt_to_players = function(_) --[[ Name: send_completed_evt_to_players ]] --[[ Line: 384 ]]
        --[[ Upvalues: (copy 1): p_u_73, (copy 2): p_u_74, (ref 3): v_u_4, (copy 4): v_u_77, (copy 5): v_u_78, (copy 6): p_u_75 ]]
        local v102 = p_u_73._player_manager:id_to_player(p_u_74)
        if v102 then
            p_u_73._evt:fire_event_to_client(v_u_4.EVT_PlayerTrade_ServerNotifyTradeCompleted, v102, v_u_77:export_to_table(), v_u_78:export_to_table())
        end;
        local v103 = p_u_73._player_manager:id_to_player(p_u_75)
        if v103 then
            p_u_73._evt:fire_event_to_client(v_u_4.EVT_PlayerTrade_ServerNotifyTradeCompleted, v103, v_u_78:export_to_table(), v_u_77:export_to_table())
        end;
    end;
    v76.get_string = function(_) --[[ Name: get_string ]] --[[ Line: 396 ]]
        --[[ Upvalues: (copy 1): v_u_77, (copy 2): v_u_78 ]]
        return v_u_77:to_string() .. "---" .. v_u_78:to_string();
    end;
    return v76;
end;
return v_u_16;
