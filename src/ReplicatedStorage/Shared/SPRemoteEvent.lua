-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:02 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Shared.EventString)
local v_u_7 = {}
for v8, v9 in pairs((require(game.ReplicatedStorage.Shared.SPRemoteEvent_Definitions))) do
    v_u_7[v8] = v9
end;
local v10 = v_u_4:new()
for v11, v12 in pairs(v_u_7) do
    if v10:contains(v12) then
        v_u_5:errf("SPRemoteEvent duplicate evtid %s = %s", tostring(v11), (tostring(v12)))
    end;
    v10:add_set(v12)
end;
local l_SPRemoteEvent_0 = game.ReplicatedStorage.Events.SPRemoteEvent
v_u_7.new = function(_, p_u_13) --[[ Name: new ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): l_SPRemoteEvent_0, (copy 3): v_u_2, (copy 4): v_u_4, (copy 5): v_u_1, (copy 6): v_u_6, (copy 7): v_u_5, (copy 8): v_u_7 ]]
    if p_u_13.IsServer == nil then
        p_u_13.IsServer = false
    end;
    local v17 = {
        ["_event"] = l_SPRemoteEvent_0,
        ["_waiting"] = v_u_2:new(),
        ["_nowaiter"] = v_u_2:new(),
        ["clear_pending_on"] = function(p14, p15) --[[ Name: clear_pending_on ]] --[[ Line: 256 ]]
            p14._nowaiter:list_of(p15):clear()
        end,
        ["get_recvct_max"] = function(_) --[[ Name: get_recvct_max ]] --[[ Line: 345 ]]
            return 25;
        end,
        ["disconnect"] = function(p16) --[[ Name: disconnect ]] --[[ Line: 373 ]]
            p16._event:Destroy()
        end
    }
    local v_u_18 = v_u_3:new()
    local v_u_19 = v_u_3:new()
    local v_u_20 = v_u_4:new()
    local v_u_21 = v_u_4:new()
    local function _(p22) --[[ Name: encoded_to_sprid ]] --[[ Line: 45 ]]
        --[[ Upvalues: (copy 1): v_u_20 ]]
        if v_u_20:contains(p22) then
            return v_u_20:get(p22);
        else
            return p22;
        end;
    end;
    local function _(p23) --[[ Name: sprid_to_encoded ]] --[[ Line: 49 ]]
        --[[ Upvalues: (copy 1): v_u_21 ]]
        if v_u_21:contains(p23) then
            return v_u_21:get(p23);
        else
            return p23;
        end;
    end;
    local v_u_24 = nil
    v17.set_error_report = function(_, p25) --[[ Name: set_error_report ]] --[[ Line: 55 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        v_u_24 = p25
    end;
    local function _(p_u_26) --[[ Name: try_report ]] --[[ Line: 56 ]]
        --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_24 ]]
        local v27, v28 = v_u_1:try(function() --[[ Line: 57 ]]
            --[[ Upvalues: (copy 1): p_u_26 ]]
            p_u_26()
        end)
        if not v27 and v_u_24 ~= nil then
            v_u_24:evt_report_error(v28)
        end;
        return v27, v28;
    end;
    v17.cons = function(p_u_29) --[[ Name: cons ]] --[[ Line: 68 ]]
        --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_6, (ref 3): v_u_5, (copy 4): v_u_20, (ref 5): v_u_1, (copy 6): v_u_18, (ref 7): v_u_24, (copy 8): v_u_19 ]]
        if p_u_13.IsServer then
            p_u_29:server_generate_encodings()
            p_u_29._event.OnServerEvent:Connect(function(p_u_30, p31, _, ...) --[[ Line: 73 ]]
                --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_5, (ref 3): v_u_20, (copy 4): p_u_29, (ref 5): v_u_1, (ref 6): v_u_18, (ref 7): v_u_24, (ref 8): v_u_19 ]]
                v_u_6:es_fn_enabled(true)
                v_u_5:set_as_server()
                if v_u_20:contains(p31) then
                    p31 = v_u_20:get(p31)
                end;
                if p_u_29:get_stats_manager() == nil or p_u_29:get_stats_manager():report_spremoteevent_receive(p_u_30, p31) ~= false then
                    if p_u_29._waiting:count_of(p31) == 0 then
                        p_u_29._nowaiter:push_back_to(p31, {
                            ["Player"] = p_u_30,
                            ["Args"] = v_u_1:tpack(v_u_1:arg_deconvert(...))
                        })
                        v_u_6:es_fn_enabled(false)
                    else
                        local v32 = p_u_29._waiting:list_of(p31)
                        for v33 = v32:count(), 1, -1 do
                            local v_u_34 = v32:get(v33)
                            if v_u_34.RemoveOnReceive == true then
                                v32:remove_at(v33)
                            end;
                            for v35 = 1, v_u_18:count() do
                                v_u_18:get(v35)()
                            end;
                            local v_u_36 = { v_u_1:arg_deconvert(...) }
                            local function v_u_37() --[[ Line: 121 ]]
                                --[[ Upvalues: (copy 1): v_u_34, (copy 2): p_u_30, (copy 3): v_u_36 ]]
                                v_u_34.Callback(p_u_30, unpack(v_u_36))
                            end;
                            local v38, v39 = v_u_1:try(function() --[[ Line: 57 ]]
                                --[[ Upvalues: (copy 1): v_u_37 ]]
                                v_u_37()
                            end)
                            if not v38 and v_u_24 ~= nil then
                                v_u_24:evt_report_error(v39)
                            end;
                            for v40 = 1, v_u_19:count() do
                                v_u_19:get(v40)()
                            end;
                        end;
                        v_u_6:es_fn_enabled(false)
                    end;
                else
                    if v_u_1:is_dev_build() then
                        warn("SPRemoteEvent server_stats_manager skip key", p31)
                    end;
                    return;
                end;
            end)
        else
            p_u_29._event.OnClientEvent:Connect(function(p41, ...) --[[ Line: 134 ]]
                --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_5, (ref 3): v_u_20, (copy 4): p_u_29, (ref 5): v_u_1, (ref 6): v_u_18, (ref 7): v_u_24, (ref 8): v_u_19 ]]
                v_u_6:es_fn_enabled(true)
                v_u_5:set_as_client()
                if v_u_20:contains(p41) then
                    p41 = v_u_20:get(p41)
                end;
                if p_u_29._waiting:count_of(p41) == 0 then
                    p_u_29._nowaiter:push_back_to(p41, {
                        ["Args"] = v_u_1:tpack(v_u_1:arg_deconvert(...))
                    })
                    v_u_6:es_fn_enabled(false)
                else
                    local v42 = p_u_29._waiting:list_of(p41)
                    for v43 = v42:count(), 1, -1 do
                        local v_u_44 = v42:get(v43)
                        if v_u_44.RemoveOnReceive == true then
                            v42:remove_at(v43)
                        end;
                        for v45 = 1, v_u_18:count() do
                            v_u_18:get(v45)()
                        end;
                        local v_u_46 = { v_u_1:arg_deconvert(...) }
                        local function v_u_47() --[[ Line: 159 ]]
                            --[[ Upvalues: (copy 1): v_u_44, (copy 2): v_u_46 ]]
                            v_u_44.Callback(unpack(v_u_46))
                        end;
                        local v48, v49 = v_u_1:try(function() --[[ Line: 57 ]]
                            --[[ Upvalues: (copy 1): v_u_47 ]]
                            v_u_47()
                        end)
                        if not v48 and v_u_24 ~= nil then
                            v_u_24:evt_report_error(v49)
                        end;
                        for v50 = 1, v_u_19:count() do
                            v_u_19:get(v50)()
                        end;
                    end;
                    v_u_6:es_fn_enabled(false)
                end;
            end)
        end;
    end;
    v17.fire_event_to_client = function(p51, p52, p53, ...) --[[ Name: fire_event_to_client ]] --[[ Line: 174 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_21, (copy 3): p_u_13, (ref 4): v_u_5 ]]
        assert(type(p52) == "number")
        if v_u_1:is_mock_debug_player(p53) ~= true then
            assert(type(p53) == "userdata")
            if p51:get_stats_manager() ~= nil then
                p51:get_stats_manager():report_spremoteevent_send(p53, p52)
            end;
            if v_u_21:contains(p52) then
                p52 = v_u_21:get(p52)
            end;
            if p_u_13.IsServer ~= true then
                v_u_5:errf("SPRemoteEvent fire_event_to_client not server")
            end;
            p51._event:FireClient(p53, p52, v_u_1:arg_convert(...))
        end;
    end;
    v17.fire_event_to_server = function(p_u_54, p55, ...) --[[ Name: fire_event_to_server ]] --[[ Line: 192 ]]
        --[[ Upvalues: (copy 1): p_u_13, (ref 2): v_u_5, (copy 3): v_u_21, (ref 4): v_u_1 ]]
        assert(type(p55) == "number")
        if p_u_13.IsServer ~= false then
            v_u_5:errf("SPRemoteEvent fire_event_to_server not client")
        end;
        local v_u_56 = p55
        if v_u_21:contains(v_u_56) then
            v_u_56 = v_u_21:get(v_u_56)
        end;
        local v_u_57 = { v_u_1:arg_convert(...) }
        spawn(function() --[[ Line: 202 ]]
            --[[ Upvalues: (copy 1): p_u_54, (ref 2): v_u_56, (copy 3): v_u_57 ]]
            p_u_54._event:FireServer(v_u_56, p_u_54:client_getincr_recvct(), unpack(v_u_57))
        end)
    end;
    v17.wait_on_event = function(p58, p59, p60) --[[ Name: wait_on_event ]] --[[ Line: 207 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_13, (ref 3): v_u_1 ]]
        if p59 == nil then
            v_u_5:errf("wait_on_event nil key")
        end;
        if p58._waiting:count_of(p59) ~= 0 then
            v_u_5:warnf("SPRemoteEvent:wait_on_event(%s) multiple count(%s)", tostring(p59), (tostring(p58._waiting:count_of(p59))))
        end;
        local v61 = p58._nowaiter:list_of(p59)
        for v62 = 1, v61:count() do
            local v63 = v61:get(v62)
            if p_u_13.IsServer then
                p60(v63.Player, v_u_1:tunpack(v63.Args))
            else
                p60(v_u_1:tunpack(v63.Args))
            end;
        end;
        v61:clear()
        p58._waiting:push_back_to(p59, {
            ["RemoveOnReceive"] = false,
            ["Callback"] = p60
        })
    end;
    v17.wait_on_event_once = function(p64, p65, p66) --[[ Name: wait_on_event_once ]] --[[ Line: 233 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_13, (ref 3): v_u_1 ]]
        if p65 == nil then
            v_u_5:errf("wait_on_event_once nil key")
        end;
        local v67 = p64._nowaiter:list_of(p65)
        for v68 = 1, v67:count() do
            local v69 = v67:get(v68)
            if p_u_13.IsServer then
                p66(v69.Player, v_u_1:tunpack(v69.Args))
            else
                p66(v_u_1:tunpack(v69.Args))
            end;
            v67:remove_at(v68)
            return;
        end;
        p64._waiting:push_back_to(p65, {
            ["RemoveOnReceive"] = true,
            ["Callback"] = p66
        })
    end;
    v17.remove_waits_on = function(p70, p71) --[[ Name: remove_waits_on ]] --[[ Line: 260 ]]
        --[[ Upvalues: (ref 1): v_u_5 ]]
        if p71 == nil then
            v_u_5:errf("remove_waits_on nil key")
        end;
        p70._waiting:list_of(p71):clear()
    end;
    v17.push_pre_post_callbacks = function(_, p72, p73) --[[ Name: push_pre_post_callbacks ]] --[[ Line: 268 ]]
        --[[ Upvalues: (copy 1): v_u_18, (copy 2): v_u_19 ]]
        v_u_18:push_back(p72)
        v_u_19:push_back(p73)
    end;
    v17.server_generate_encodings = function(_) --[[ Name: server_generate_encodings ]] --[[ Line: 273 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_20, (copy 3): v_u_21 ]]
        for _, v74 in pairs(v_u_7) do
            if typeof(v74) == "number" then
                v_u_20:add(v74, v74)
                v_u_21:add(v74, v74)
            end;
        end;
    end;
    v17.get_encodings = function(_) --[[ Name: get_encodings ]] --[[ Line: 291 ]]
        --[[ Upvalues: (copy 1): v_u_21 ]]
        local v75 = {}
        for v76, v77 in v_u_21:key_itr() do
            v75[tostring(v76)] = v77
        end;
        return v75;
    end;
    v17.client_load_encodings_from_table = function(_, p78) --[[ Name: client_load_encodings_from_table ]] --[[ Line: 299 ]]
        --[[ Upvalues: (copy 1): v_u_20, (copy 2): v_u_21 ]]
        for v79, v80 in pairs(p78) do
            local v81 = tonumber(v79)
            v_u_20:add(v80, v81)
            v_u_21:add(v81, v80)
        end;
    end;
    local v_u_82 = 0
    v17.client_getincr_recvct = function(_) --[[ Name: client_getincr_recvct ]] --[[ Line: 308 ]]
        --[[ Upvalues: (ref 1): v_u_82 ]]
        local v83 = v_u_82
        v_u_82 = v_u_82 + 1
        if v_u_82 > 25 then
            v_u_82 = 0
        end;
        return v83;
    end;
    v17.client_get_recvct = function(_) --[[ Name: client_get_recvct ]] --[[ Line: 317 ]]
        --[[ Upvalues: (ref 1): v_u_82 ]]
        return v_u_82;
    end;
    local v_u_84 = v_u_4:new()
    v17.server_player_disconnecting = function(_, p85) --[[ Name: server_player_disconnecting ]] --[[ Line: 322 ]]
        --[[ Upvalues: (copy 1): v_u_84 ]]
        v_u_84:remove(p85)
    end;
    v17.server_validate_playerid_recvct = function(p86, p87, p88) --[[ Name: server_validate_playerid_recvct ]] --[[ Line: 326 ]]
        --[[ Upvalues: (copy 1): v_u_84 ]]
        if v_u_84:contains(p87) == false then
            v_u_84:add(p87, 0)
        end;
        local v89 = v_u_84:get(p87)
        if v89 ~= p88 then
            p86:server_recvct_error_report(p87, p88, v89)
        end;
        local v90 = v89 + 1
        v_u_84:add(p87, v90 > 25 and 0 or v90)
    end;
    v17.server_get_playerid_recvct = function(_, p91) --[[ Name: server_get_playerid_recvct ]] --[[ Line: 341 ]]
        --[[ Upvalues: (copy 1): v_u_84 ]]
        return v_u_84:get(p91);
    end;
    local v_u_92 = false
    v17.server_shutting_down = function(_) --[[ Name: server_shutting_down ]] --[[ Line: 350 ]]
        --[[ Upvalues: (ref 1): v_u_92 ]]
        v_u_92 = true
    end;
    v17.server_recvct_error_report = function(_, p93, p94, p95) --[[ Name: server_recvct_error_report ]] --[[ Line: 354 ]]
        --[[ Upvalues: (ref 1): v_u_92, (ref 2): v_u_5, (ref 3): v_u_1 ]]
        if v_u_92 ~= true then
            v_u_5:errf("invalid recvct(%s) expected(%s) for player(%s)[%s]", tostring(p94), tostring(p95), tostring(p93), v_u_1:num_string(p93))
        end;
    end;
    local v_u_96 = nil
    v17.register_stats_manager = function(_, p97) --[[ Name: register_stats_manager ]] --[[ Line: 365 ]]
        --[[ Upvalues: (ref 1): v_u_96 ]]
        v_u_96 = p97
    end;
    v17.get_stats_manager = function(_) --[[ Name: get_stats_manager ]] --[[ Line: 369 ]]
        --[[ Upvalues: (ref 1): v_u_96 ]]
        return v_u_96;
    end;
    v17:cons()
    return v17;
end;
return v_u_7;
