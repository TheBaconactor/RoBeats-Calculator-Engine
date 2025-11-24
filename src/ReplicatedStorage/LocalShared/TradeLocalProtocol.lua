-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:01 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_6 = require(game.ReplicatedStorage.Shared.ActiveTradeOffer)
local v_u_7 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_8 = {
    ["Mode"] = {
        ["Error"] = 0,
        ["NotTrading"] = 1,
        ["TradeActive"] = 2,
        ["ActivePlayerTrade"] = 3,
        ["ActivePlayerTradeConfirmRequired"] = 4,
        ["ActivePlayerTradeConfirmSent"] = 5,
        ["ActivePlayerTradeProcessing"] = 6,
        ["ActivePlayerTradeComplete"] = 7
    },
    ["NO_UPDATE_TIME"] = 0
}
v_u_8.new = function(_, p_u_9) --[[ Name: new ]] --[[ Line: 23 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_6, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_7, (copy 8): v_u_1 ]]
    local v10 = {}
    local l_NotTrading_0 = v_u_8.Mode.NotTrading
    v10.get_current_mode = function(_) --[[ Name: get_current_mode ]] --[[ Line: 27 ]]
        --[[ Upvalues: (ref 1): l_NotTrading_0 ]]
        return l_NotTrading_0;
    end;
    local v_u_11 = v_u_2:new()
    local v_u_12 = v_u_2:new()
    local v_u_13 = v_u_3:new()
    v10.get_available_playerid_to_did_send_request_dict = function(_) --[[ Name: get_available_playerid_to_did_send_request_dict ]] --[[ Line: 33 ]]
        --[[ Upvalues: (copy 1): v_u_11 ]]
        return v_u_11;
    end;
    v10.playerid_to_username = function(_, p14) --[[ Name: playerid_to_username ]] --[[ Line: 34 ]]
        --[[ Upvalues: (copy 1): v_u_12 ]]
        return not v_u_12:contains(p14) and "???" or v_u_12:get(p14);
    end;
    v10.get_received_requests_playerids_list = function(_) --[[ Name: get_received_requests_playerids_list ]] --[[ Line: 38 ]]
        --[[ Upvalues: (copy 1): v_u_13 ]]
        return v_u_13;
    end;
    local v_u_15 = v_u_6:new()
    local v_u_16 = v_u_6:new()
    v10.get_active_trade_player_offer = function(_) --[[ Name: get_active_trade_player_offer ]] --[[ Line: 44 ]]
        --[[ Upvalues: (copy 1): v_u_15 ]]
        return v_u_15;
    end;
    v10.get_active_trade_target_offer = function(_) --[[ Name: get_active_trade_target_offer ]] --[[ Line: 45 ]]
        --[[ Upvalues: (copy 1): v_u_16 ]]
        return v_u_16;
    end;
    local l_NO_UPDATE_TIME_0 = v_u_8.NO_UPDATE_TIME
    v10.get_last_updated_time = function(_) --[[ Name: get_last_updated_time ]] --[[ Line: 49 ]]
        --[[ Upvalues: (ref 1): l_NO_UPDATE_TIME_0 ]]
        return l_NO_UPDATE_TIME_0;
    end;
    local v_u_17 = "???"
    v10.get_errmsg = function(_) --[[ Name: get_errmsg ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): v_u_17 ]]
        return v_u_17;
    end;
    local v_u_18 = -1
    local v_u_19 = "???"
    v10.get_active_player_trade_target_info = function(_) --[[ Name: get_active_player_trade_target_info ]] --[[ Line: 56 ]]
        --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_19 ]]
        return v_u_18, v_u_19;
    end;
    v10.start = function(p20) --[[ Name: start ]] --[[ Line: 58 ]]
        --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_5, (copy 3): v_u_11, (copy 4): v_u_12, (copy 5): v_u_13, (ref 6): l_NO_UPDATE_TIME_0, (ref 7): l_NotTrading_0, (ref 8): v_u_8, (ref 9): v_u_4, (ref 10): v_u_18, (ref 11): v_u_19, (copy 12): v_u_16, (copy 13): v_u_15, (ref 14): v_u_17 ]]
        p20:stop()
        p_u_9:wait_on_event(v_u_5.EVT_Trade_ServerPushTradeInfo, function(p21, p22, p23) --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_12, (ref 3): v_u_13, (ref 4): l_NO_UPDATE_TIME_0 ]]
            v_u_11:clear()
            v_u_12:clear()
            v_u_13:clear()
            for v24 = 1, #p21 do
                local v25 = p21[v24]
                local l_PlayerId_0 = v25.PlayerId
                local l_Name_0 = v25.Name
                v_u_11:add(l_PlayerId_0, false)
                v_u_12:add(l_PlayerId_0, l_Name_0)
            end;
            for v26 = 1, #p23 do
                local v27 = p23[v26]
                if v_u_11:contains(v27) then
                    v_u_11:add(v27, true)
                end;
            end;
            for v28 = 1, #p22 do
                local v29 = p22[v28]
                if v_u_11:contains(v29) then
                    v_u_13:push_back(v29)
                end;
            end;
            l_NO_UPDATE_TIME_0 = tick()
        end)
        p_u_9:wait_on_event(v_u_5.EVT_Trade_ServerPushPlayerTradeBegin, function(p30, p31) --[[ Line: 93 ]]
            --[[ Upvalues: (ref 1): l_NotTrading_0, (ref 2): v_u_8, (ref 3): v_u_4, (ref 4): v_u_18, (ref 5): v_u_19 ]]
            if l_NotTrading_0 == v_u_8.Mode.TradeActive then
                v_u_18 = p30
                v_u_19 = p31
                l_NotTrading_0 = v_u_8.Mode.ActivePlayerTrade
            else
                v_u_4:warnf("EVT_Trade_ServerPushPlayerTradeBegin TradeLocalProtocol invalid mode(%d)", l_NotTrading_0)
            end;
        end)
        p_u_9:wait_on_event(v_u_5.EVT_PlayerTrade_ServerNotifyOfferInfo, function(p32, p33) --[[ Line: 104 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_15, (ref 3): l_NO_UPDATE_TIME_0 ]]
            if v_u_16:update_from_table(p33) == true then
                v_u_15:update_accepted_from_table(p32)
            end;
            l_NO_UPDATE_TIME_0 = tick()
        end)
        p_u_9:wait_on_event(v_u_5.EVT_PlayerTrade_ServerNotifyTradeConfirm, function(p34, p35) --[[ Line: 112 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16, (ref 3): l_NO_UPDATE_TIME_0, (ref 4): l_NotTrading_0, (ref 5): v_u_8 ]]
            v_u_15:update_from_table(p34)
            v_u_16:update_from_table(p35)
            l_NO_UPDATE_TIME_0 = tick()
            l_NotTrading_0 = v_u_8.Mode.ActivePlayerTradeConfirmRequired
        end)
        p_u_9:wait_on_event(v_u_5.EVT_PlayerTrade_ServerNotifyTradeProcessing, function(p36, p37) --[[ Line: 119 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16, (ref 3): l_NotTrading_0, (ref 4): v_u_8 ]]
            v_u_15:update_from_table(p36)
            v_u_16:update_from_table(p37)
            l_NotTrading_0 = v_u_8.Mode.ActivePlayerTradeProcessing
        end)
        p_u_9:wait_on_event(v_u_5.EVT_PlayerTrade_ServerNotifyTradeCompleted, function(p38, p39) --[[ Line: 125 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_16, (ref 3): l_NotTrading_0, (ref 4): v_u_8 ]]
            v_u_15:update_from_table(p38)
            v_u_16:update_from_table(p39)
            l_NotTrading_0 = v_u_8.Mode.ActivePlayerTradeComplete
        end)
        p_u_9:wait_on_event(v_u_5.EVT_Trade_ServerError, function(p40) --[[ Line: 132 ]]
            --[[ Upvalues: (ref 1): l_NotTrading_0, (ref 2): v_u_8, (ref 3): v_u_17 ]]
            l_NotTrading_0 = v_u_8.Mode.Error
            v_u_17 = p40
        end)
        l_NO_UPDATE_TIME_0 = v_u_8.NO_UPDATE_TIME
        p_u_9:fire_event_to_server(v_u_5.EVT_Trade_ClientNotifyTradesOpenStatus, true)
        l_NotTrading_0 = v_u_8.Mode.TradeActive
    end;
    v10.send_trade_request_to_playerid = function(_, p41) --[[ Name: send_trade_request_to_playerid ]] --[[ Line: 143 ]]
        --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_5, (copy 3): v_u_11 ]]
        p_u_9:fire_event_to_server(v_u_5.EVT_Trade_ClientSendTradeRequest, p41)
        v_u_11:add(p41, true)
    end;
    v10.accept_trade_request_from_playerid = function(_, p42) --[[ Name: accept_trade_request_from_playerid ]] --[[ Line: 148 ]]
        --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_5 ]]
        p_u_9:fire_event_to_server(v_u_5.EVT_Trade_ClientAcceptTradeRequest, p42)
    end;
    local function _() --[[ Name: push_active_trade_player_offer_to_server ]] --[[ Line: 153 ]]
        --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_5, (copy 3): v_u_15, (ref 4): v_u_18 ]]
        p_u_9:fire_event_to_server(v_u_5.EVT_PlayerTrade_ClientPushLocalOffer, v_u_15:export_to_table(), v_u_18)
    end;
    v10.player_offer_add_material = function(_, p43) --[[ Name: player_offer_add_material ]] --[[ Line: 157 ]]
        --[[ Upvalues: (copy 1): v_u_15, (copy 2): p_u_9, (ref 3): v_u_5, (ref 4): v_u_18 ]]
        v_u_15:add_material(p43)
        v_u_15:set_accepted(false)
        p_u_9:fire_event_to_server(v_u_5.EVT_PlayerTrade_ClientPushLocalOffer, v_u_15:export_to_table(), v_u_18)
    end;
    v10.player_offer_remove_material = function(_, p44) --[[ Name: player_offer_remove_material ]] --[[ Line: 163 ]]
        --[[ Upvalues: (copy 1): v_u_15, (copy 2): p_u_9, (ref 3): v_u_5, (ref 4): v_u_18 ]]
        v_u_15:remove_material(p44)
        v_u_15:set_accepted(false)
        p_u_9:fire_event_to_server(v_u_5.EVT_PlayerTrade_ClientPushLocalOffer, v_u_15:export_to_table(), v_u_18)
    end;
    v10.player_offer_set_coins = function(_, p45) --[[ Name: player_offer_set_coins ]] --[[ Line: 169 ]]
        --[[ Upvalues: (copy 1): v_u_15, (copy 2): p_u_9, (ref 3): v_u_5, (ref 4): v_u_18 ]]
        v_u_15:set_coins(p45)
        v_u_15:set_accepted(false)
        p_u_9:fire_event_to_server(v_u_5.EVT_PlayerTrade_ClientPushLocalOffer, v_u_15:export_to_table(), v_u_18)
    end;
    v10.player_accept = function(_) --[[ Name: player_accept ]] --[[ Line: 175 ]]
        --[[ Upvalues: (copy 1): v_u_15, (copy 2): p_u_9, (ref 3): v_u_5, (ref 4): v_u_18 ]]
        v_u_15:set_accepted(true)
        p_u_9:fire_event_to_server(v_u_5.EVT_PlayerTrade_ClientPushLocalOffer, v_u_15:export_to_table(), v_u_18)
    end;
    v10.trade_leave = function(_) --[[ Name: trade_leave ]] --[[ Line: 180 ]]
        --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_5 ]]
        p_u_9:fire_event_to_server(v_u_5.EVT_PlayerTrade_ClientLeave)
    end;
    v10.trade_confirm = function(_, p46) --[[ Name: trade_confirm ]] --[[ Line: 184 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): l_NotTrading_0, (ref 3): v_u_8, (copy 4): p_u_9, (ref 5): v_u_5, (ref 6): v_u_4, (ref 7): v_u_1 ]]
        v_u_7:is_bool(p46)
        if l_NotTrading_0 == v_u_8.Mode.ActivePlayerTradeConfirmRequired or l_NotTrading_0 == v_u_8.Mode.ActivePlayerTradeConfirmSent then
            l_NotTrading_0 = v_u_8.Mode.ActivePlayerTradeConfirmSent
            p_u_9:fire_event_to_server(v_u_5.EVT_PlayerTrade_ClientConfirm, p46)
        else
            v_u_4:warnf("TradeLocalProtocol:trade_confirm when current mode was %s", v_u_1:enum_val_to_name(l_NotTrading_0, v_u_8.Mode))
        end;
    end;
    v10.stop = function(_) --[[ Name: stop ]] --[[ Line: 195 ]]
        --[[ Upvalues: (ref 1): l_NotTrading_0, (ref 2): v_u_8, (copy 3): p_u_9, (ref 4): v_u_5, (copy 5): v_u_11, (copy 6): v_u_12, (copy 7): v_u_13, (copy 8): v_u_15, (copy 9): v_u_16, (ref 10): l_NO_UPDATE_TIME_0, (ref 11): v_u_18 ]]
        if l_NotTrading_0 ~= v_u_8.Mode.NotTrading then
            p_u_9:fire_event_to_server(v_u_5.EVT_Trade_ClientNotifyTradesOpenStatus, false)
        end;
        l_NotTrading_0 = v_u_8.Mode.NotTrading
        v_u_11:clear()
        v_u_12:clear()
        v_u_13:clear()
        v_u_15:clear()
        v_u_16:clear()
        l_NO_UPDATE_TIME_0 = v_u_8.NO_UPDATE_TIME
        v_u_18 = -1
        p_u_9:remove_waits_on(v_u_5.EVT_Trade_ServerError)
        p_u_9:remove_waits_on(v_u_5.EVT_Trade_ServerPushTradeInfo)
        p_u_9:remove_waits_on(v_u_5.EVT_Trade_ServerPushPlayerTradeBegin)
        p_u_9:remove_waits_on(v_u_5.EVT_PlayerTrade_ServerNotifyOfferInfo)
        p_u_9:remove_waits_on(v_u_5.EVT_PlayerTrade_ServerNotifyTradeProcessing)
        p_u_9:remove_waits_on(v_u_5.EVT_PlayerTrade_ServerNotifyTradeConfirm)
        p_u_9:remove_waits_on(v_u_5.EVT_PlayerTrade_ServerNotifyTradeCompleted)
    end;
    v10.debug_start_active_player_trade = function(_) --[[ Name: debug_start_active_player_trade ]] --[[ Line: 219 ]]
        --[[ Upvalues: (ref 1): l_NotTrading_0, (ref 2): v_u_8, (ref 3): v_u_18, (ref 4): v_u_19 ]]
        l_NotTrading_0 = v_u_8.Mode.ActivePlayerTrade
        v_u_18 = 1
        v_u_19 = "TradeDebug"
    end;
    return v10;
end;
return v_u_8;
