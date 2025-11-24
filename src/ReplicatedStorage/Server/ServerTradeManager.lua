-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:16 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Server.ActivePlayerTradeManager)
local v_u_7 = {
    ["TradeActivePlayer"] = {},
    ["TradeRequest"] = {}
}
v_u_7.new = function(_, p_u_8) --[[ Name: new ]] --[[ Line: 12 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_6, (copy 3): v_u_5, (copy 4): v_u_7, (copy 5): v_u_1, (copy 6): v_u_4 ]]
    local v9 = {}
    local v_u_10 = v_u_3:new()
    local v_u_11 = v_u_6:new(p_u_8, v9)
    v9.start = function(p_u_12) --[[ Name: start ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): p_u_8, (ref 2): v_u_5, (copy 3): v_u_10, (ref 4): v_u_7, (copy 5): v_u_11, (ref 6): v_u_1 ]]
        p_u_8._evt:wait_on_event(v_u_5.EVT_Trade_ClientNotifyTradesOpenStatus, function(p13, p14) --[[ Line: 19 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_7, (copy 3): p_u_12 ]]
            local l_UserId_0 = p13.UserId
            if p14 == true then
                v_u_10:add(l_UserId_0, v_u_7.TradeActivePlayer:new(l_UserId_0, p13.Name))
            else
                p_u_12:remove_trade_active_playerid(l_UserId_0)
            end;
            p_u_12:push_trade_info()
        end)
        p_u_8._evt:wait_on_event(v_u_5.EVT_Trade_ClientSendTradeRequest, function(p15, p16) --[[ Line: 30 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_1, (ref 3): v_u_10, (ref 4): p_u_8, (ref 5): v_u_5, (copy 6): p_u_12 ]]
            local l_UserId_1 = p15.UserId
            if v_u_11:find_active_trade_for_playerid(l_UserId_1) ~= nil then
                return v_u_1:warnf("ClientSendTradeRequest src already in trade");
            end;
            if v_u_11:find_active_trade_for_playerid(p16) ~= nil then
                return v_u_1:warnf("ClientSendTradeRequest dest already in trade");
            end;
            if v_u_10:contains(l_UserId_1) ~= true then
                return p_u_8._evt:fire_event_to_client(v_u_5.EVT_Trade_ServerError, p15, "ClientSendTradeRequest src not active");
            end;
            if v_u_10:contains(p16) ~= true then
                return v_u_1:warnf("ClientSendTradeRequest dest not active");
            end;
            v_u_10:get(p16):add_trade_request_from_playerid(l_UserId_1)
            if v_u_10:get(l_UserId_1):contains_trade_request_from_playerid(p16) then
                return p_u_12:start_active_player_trade_for_playerids(l_UserId_1, p16, p15);
            end;
            p_u_12:push_trade_info({ l_UserId_1, p16 })
        end)
        p_u_8._evt:wait_on_event(v_u_5.EVT_Trade_ClientAcceptTradeRequest, function(p17, p18) --[[ Line: 57 ]]
            --[[ Upvalues: (copy 1): p_u_12 ]]
            p_u_12:start_active_player_trade_for_playerids(p18, p17.UserId, p17)
        end)
        v_u_11:start()
    end;
    v9.update = function(_, p19) --[[ Name: update ]] --[[ Line: 64 ]]
        --[[ Upvalues: (copy 1): v_u_11 ]]
        v_u_11:update(p19)
    end;
    v9.start_active_player_trade_for_playerids = function(p20, p21, p22, p23) --[[ Name: start_active_player_trade_for_playerids ]] --[[ Line: 68 ]]
        --[[ Upvalues: (copy 1): v_u_10, (copy 2): p_u_8, (ref 3): v_u_5, (copy 4): v_u_11 ]]
        if v_u_10:contains(p21) == true and v_u_10:contains(p22) == true then
            local v24 = v_u_10:get(p22)
            if v24:contains_trade_request_from_playerid(p21) == true then
                local v25 = v_u_10:get(p21):get_name()
                local v26 = v24:get_name()
                p20:remove_trade_active_playerid(p21)
                p20:remove_trade_active_playerid(p22)
                p20:push_trade_info()
                local v27 = p_u_8._player_manager:id_to_player(p22)
                local v28 = p_u_8._player_manager:id_to_player(p21)
                if v28 == nil or v27 == nil then
                    p_u_8._evt:fire_event_to_client(v_u_5.EVT_Trade_ServerError, p23, "ClientAcceptTradeRequest src player is nil")
                else
                    p_u_8._evt:fire_event_to_client(v_u_5.EVT_Trade_ServerPushPlayerTradeBegin, v28, p22, v26)
                    p_u_8._evt:fire_event_to_client(v_u_5.EVT_Trade_ServerPushPlayerTradeBegin, v27, p21, v25)
                    v_u_11:create_active_player_trade_for_playerids(p21, p22)
                end;
            else
                p_u_8._evt:fire_event_to_client(v_u_5.EVT_Trade_ServerError, p23, "ClientAcceptTradeRequest dest does not contain request from src")
                return;
            end;
        else
            p_u_8._evt:fire_event_to_client(v_u_5.EVT_Trade_ServerError, p23, "ClientAcceptTradeRequest src or dest not active")
            return;
        end;
    end;
    local v_u_29 = v_u_4:new()
    local v_u_30 = v_u_3:new()
    v9.push_trade_info = function(_, p31) --[[ Name: push_trade_info ]] --[[ Line: 103 ]]
        --[[ Upvalues: (copy 1): v_u_30, (copy 2): v_u_29, (copy 3): v_u_10, (copy 4): p_u_8, (ref 5): v_u_5 ]]
        local v32 = v_u_30:clear()
        if p31 then
            for v33 = 1, #p31 do
                v32:add(p31[v33], true)
            end;
        end;
        local v34 = v_u_29:clear()
        for v35, v36 in v_u_10:key_itr() do
            local v37 = v36:get_trade_requests()
            for v38 = 1, v37:count() do
                v34:push_back_to(v37:get(v38):get_src_playerid(), v35)
            end;
        end;
        local v39 = {}
        for _, v40 in v_u_10:key_itr() do
            v39[#v39 + 1] = {
                ["Name"] = v40:get_name(),
                ["PlayerId"] = v40:get_player_id()
            }
        end;
        for _, v41 in v_u_10:key_itr() do
            local v42 = v34:list_of(v41:get_player_id())
            local v43 = {}
            for v44 = 1, v42:count() do
                v43[#v43 + 1] = v42:get(v44)
            end;
            local v45 = v41:get_trade_requests()
            local v46 = {}
            for v47 = 1, v45:count() do
                v46[#v46 + 1] = v45:get(v47):get_src_playerid()
            end;
            local v48 = p_u_8._player_manager:id_to_player(v41:get_player_id())
            if v48 and (v32:count() == 0 or v32:contains(v41:get_player_id())) then
                p_u_8._evt:fire_event_to_client(v_u_5.EVT_Trade_ServerPushTradeInfo, v48, v39, v46, v43)
            end;
        end;
    end;
    v9.remove_trade_active_playerid = function(_, p49) --[[ Name: remove_trade_active_playerid ]] --[[ Line: 157 ]]
        --[[ Upvalues: (copy 1): v_u_10 ]]
        v_u_10:remove(p49)
        for _, v50 in v_u_10:key_itr() do
            v50:remove_trade_requests_from_playerid(p49)
        end;
    end;
    v9.player_disconnecting = function(p51, p52) --[[ Name: player_disconnecting ]] --[[ Line: 164 ]]
        --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_11 ]]
        if v_u_10:contains(p52) then
            p51:remove_trade_active_playerid(p52)
            p51:push_trade_info()
        end;
        v_u_11:player_disconnecting(p52)
    end;
    return v9;
end;
v_u_7.TradeActivePlayer.new = function(_, p_u_53, p_u_54) --[[ Name: new ]] --[[ Line: 177 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_7 ]]
    local v55 = {}
    v55.get_name = function(_) --[[ Name: get_name ]] --[[ Line: 180 ]]
        --[[ Upvalues: (copy 1): p_u_54 ]]
        return p_u_54;
    end;
    v55.get_player_id = function(_) --[[ Name: get_player_id ]] --[[ Line: 181 ]]
        --[[ Upvalues: (copy 1): p_u_53 ]]
        return p_u_53;
    end;
    local v_u_56 = v_u_2:new()
    v55.get_trade_requests = function(_) --[[ Name: get_trade_requests ]] --[[ Line: 184 ]]
        --[[ Upvalues: (copy 1): v_u_56 ]]
        return v_u_56;
    end;
    v55.add_trade_request_from_playerid = function(p57, p58) --[[ Name: add_trade_request_from_playerid ]] --[[ Line: 186 ]]
        --[[ Upvalues: (copy 1): v_u_56, (ref 2): v_u_7 ]]
        if not p57:contains_trade_request_from_playerid(p58) then
            v_u_56:push_back(v_u_7.TradeRequest:new(p58))
        end;
    end;
    v55.contains_trade_request_from_playerid = function(_, p59) --[[ Name: contains_trade_request_from_playerid ]] --[[ Line: 191 ]]
        --[[ Upvalues: (copy 1): v_u_56 ]]
        for v60 = 1, v_u_56:count() do
            if v_u_56:get(v60):get_src_playerid() == p59 then
                return true;
            end;
        end;
        return false;
    end;
    v55.remove_trade_requests_from_playerid = function(_, p_u_61) --[[ Name: remove_trade_requests_from_playerid ]] --[[ Line: 200 ]]
        --[[ Upvalues: (copy 1): v_u_56 ]]
        v_u_56:remove_if(function(p62) --[[ Line: 201 ]]
            --[[ Upvalues: (copy 1): p_u_61 ]]
            return p62:get_src_playerid() == p_u_61;
        end)
    end;
    return v55;
end;
v_u_7.TradeRequest.new = function(_, p_u_63) --[[ Name: new ]] --[[ Line: 210 ]]
    local v64 = {}
    v64.get_src_playerid = function(_) --[[ Name: get_src_playerid ]] --[[ Line: 212 ]]
        --[[ Upvalues: (copy 1): p_u_63 ]]
        return p_u_63;
    end;
    return v64;
end;
return v_u_7;
