-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:16 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.ProdEnvSelector)
local v_u_7 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.WebNPCPurchaseInfo)
local v_u_9 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_10 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_11 = require(game.ReplicatedStorage.Shared.WebNPCAnchors)
local v_u_12 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_13 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_14 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
local v_u_17 = require(game.ReplicatedStorage.Shared.GuildMessage)
local v_u_18 = require(game.ReplicatedStorage.Server.ServerWebNPCRecentManager)
local v_u_19 = require(game.ReplicatedStorage.Shared.APICooldown)
local v_u_20 = require(game.ReplicatedStorage.Server.ServerDatastoreImpl.ServerWebNPCDatastoreManager)
local v21 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_22 = nil
v21:require_server(function() --[[ Line: 26 ]]
    --[[ Upvalues: (ref 1): v_u_22 ]]
    v_u_22 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
return {
    ["new"] = function(_, p_u_23) --[[ Name: new ]] --[[ Line: 38 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_12, (copy 4): v_u_18, (copy 5): v_u_20, (copy 6): v_u_4, (copy 7): v_u_5, (copy 8): v_u_1, (copy 9): v_u_10, (copy 10): v_u_19, (copy 11): v_u_13, (copy 12): v_u_16, (ref 13): v_u_22, (copy 14): v_u_8, (copy 15): v_u_14, (copy 16): v_u_15, (copy 17): v_u_6, (copy 18): v_u_7, (copy 19): v_u_11, (copy 20): v_u_17, (copy 21): v_u_9 ]]
        local v24 = {}
        local v_u_25 = v_u_3:new()
        local v_u_26 = v_u_2:new()
        local function _(p27) --[[ Name: webnpc_list_contains_id ]] --[[ Line: 45 ]]
            --[[ Upvalues: (copy 1): v_u_26 ]]
            for _, v28 in v_u_26:key_itr() do
                if v28:get_webnpcid() == p27 then
                    return true;
                end;
            end;
            return false;
        end;
        local v_u_29 = 0
        local v_u_30 = v_u_12:new()
        local v_u_31 = v_u_3:new()
        local v_u_32 = v_u_3:new()
        local v_u_33 = v_u_3:new()
        local v_u_34 = v_u_12:new()
        local v_u_35 = v_u_12:new()
        local v_u_36 = v_u_12:new()
        local v_u_37 = v_u_18:new(p_u_23)
        local v_u_38 = v_u_20:new(p_u_23)
        v24.start = function(p_u_39) --[[ Name: start ]] --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_26, (copy 3): p_u_23, (ref 4): v_u_4, (ref 5): v_u_29, (ref 6): v_u_5, (ref 7): v_u_1, (ref 8): v_u_10, (copy 9): v_u_38, (ref 10): v_u_19, (ref 11): v_u_13, (copy 12): v_u_31, (copy 13): v_u_30, (ref 14): v_u_16, (ref 15): v_u_22, (ref 16): v_u_8, (ref 17): v_u_14, (ref 18): v_u_15, (ref 19): v_u_6, (ref 20): v_u_7, (copy 21): v_u_33, (copy 22): v_u_34, (ref 23): v_u_11, (ref 24): v_u_17, (copy 25): v_u_25, (copy 26): v_u_35, (copy 27): v_u_37, (copy 28): v_u_36, (ref 29): v_u_3, (copy 30): v_u_32 ]]
            local function f_get_webnpc_data_table() --[[ Name: get_webnpc_data_table ]] --[[ Line: 71 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_26 ]]
                local v40 = v_u_2:new()
                for _, v41 in v_u_26:key_itr() do
                    v40:push_back(v41:to_table())
                end;
                return v40:get_table();
            end;
            local function _(p42) --[[ Name: visited_list_string_encode ]] --[[ Line: 79 ]]
                local v43 = {}
                for v44, v45 in pairs(p42) do
                    v43[tostring(v44)] = v45
                end;
                return v43;
            end;
            local v_u_46 = v_u_2:new()
            p_u_23._evt:wait_on_event(v_u_4.EVT_WebNPC_ClientRequestInfo, function(p_u_47) --[[ Line: 88 ]]
                --[[ Upvalues: (copy 1): p_u_39, (ref 2): p_u_23, (ref 3): v_u_4, (copy 4): f_get_webnpc_data_table, (ref 5): v_u_29, (copy 6): v_u_46, (ref 7): v_u_5, (ref 8): v_u_1, (ref 9): v_u_10, (ref 10): v_u_38 ]]
                local function _() --[[ Name: fire_info_response ]] --[[ Line: 89 ]]
                    --[[ Upvalues: (ref 1): p_u_39, (copy 2): p_u_47, (ref 3): p_u_23, (ref 4): v_u_4, (ref 5): f_get_webnpc_data_table ]]
                    p_u_39:playerid_get_webnpc_visited_list_tab(p_u_47.UserId, function(p48) --[[ Line: 90 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (ref 3): p_u_47, (ref 4): f_get_webnpc_data_table ]]
                        local l__evt_0 = p_u_23._evt
                        local l_EVT_WebNPC_ServerInfoResponse_0 = v_u_4.EVT_WebNPC_ServerInfoResponse
                        local v49 = p_u_47
                        local v50 = {
                            ["WebNPCInfo"] = f_get_webnpc_data_table()
                        }
                        local v51 = {}
                        for v52, v53 in pairs(p48) do
                            v51[tostring(v52)] = v53
                        end;
                        v50.VisitedList = v51
                        l__evt_0:fire_event_to_client(l_EVT_WebNPC_ServerInfoResponse_0, v49, v50)
                    end)
                end;
                if v_u_29 <= 0 then
                    local v54 = v_u_46:count() == 0
                    v_u_46:push_back(function() --[[ Line: 99 ]]
                        --[[ Upvalues: (ref 1): p_u_39, (copy 2): p_u_47, (ref 3): p_u_23, (ref 4): v_u_4, (ref 5): f_get_webnpc_data_table ]]
                        p_u_39:playerid_get_webnpc_visited_list_tab(p_u_47.UserId, function(p55) --[[ Line: 90 ]]
                            --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (ref 3): p_u_47, (ref 4): f_get_webnpc_data_table ]]
                            local l__evt_1 = p_u_23._evt
                            local l_EVT_WebNPC_ServerInfoResponse_1 = v_u_4.EVT_WebNPC_ServerInfoResponse
                            local v56 = p_u_47
                            local v57 = {
                                ["WebNPCInfo"] = f_get_webnpc_data_table()
                            }
                            local v58 = {}
                            for v59, v60 in pairs(p55) do
                                v58[tostring(v59)] = v60
                            end;
                            v57.VisitedList = v58
                            l__evt_1:fire_event_to_client(l_EVT_WebNPC_ServerInfoResponse_1, v56, v57)
                        end)
                    end)
                    if v54 then
                        if v_u_5.LogWebNPCData == true then
                            v_u_1:warnf("ServerWebNPCManager api_get_webnpcs")
                        end;
                        local v_u_61 = v_u_38:api_is_loading() and 5 or v_u_10.WEBNPC_UPDATE_FREQ_SEC
                        v_u_38:dsapi_get_webnpcs(function(p62) --[[ Line: 113 ]]
                            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_61, (ref 3): p_u_39, (ref 4): v_u_46 ]]
                            v_u_29 = v_u_61
                            p_u_39:process_webnpcs_tab(p62)
                            for _, v63 in v_u_46:key_itr() do
                                v63()
                            end;
                            v_u_46:clear()
                        end)
                        return;
                    end;
                else
                    p_u_39:playerid_get_webnpc_visited_list_tab(p_u_47.UserId, function(p64) --[[ Line: 90 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (copy 3): p_u_47, (ref 4): f_get_webnpc_data_table ]]
                        local l__evt_2 = p_u_23._evt
                        local l_EVT_WebNPC_ServerInfoResponse_2 = v_u_4.EVT_WebNPC_ServerInfoResponse
                        local v65 = p_u_47
                        local v66 = {
                            ["WebNPCInfo"] = f_get_webnpc_data_table()
                        }
                        local v67 = {}
                        for v68, v69 in pairs(p64) do
                            v67[tostring(v68)] = v69
                        end;
                        v66.VisitedList = v67
                        l__evt_2:fire_event_to_client(l_EVT_WebNPC_ServerInfoResponse_2, v65, v66)
                    end)
                end;
            end)
            local v_u_70 = v_u_19:new()
            p_u_23._evt:wait_on_event(v_u_4.EVT_WebNPC_ClientVisitNPC, function(p_u_71, p_u_72) --[[ Line: 129 ]]
                --[[ Upvalues: (ref 1): v_u_13, (copy 2): v_u_70, (ref 3): p_u_23, (ref 4): v_u_4, (ref 5): v_u_31, (ref 6): v_u_30, (copy 7): p_u_39, (ref 8): v_u_5, (ref 9): v_u_16, (ref 10): v_u_22, (ref 11): v_u_8, (ref 12): v_u_14 ]]
                v_u_13:is_int(p_u_72)
                v_u_70:queue_key_request(p_u_71.UserId, function() --[[ Line: 131 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (copy 3): p_u_71, (ref 4): v_u_31, (ref 5): v_u_30, (ref 6): p_u_39, (copy 7): p_u_72, (ref 8): v_u_5, (ref 9): v_u_16, (ref 10): v_u_22, (ref 11): v_u_8, (ref 12): v_u_14 ]]
                    local function f_response(p73, p74, p75) --[[ Name: response ]] --[[ Line: 132 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (ref 3): p_u_71 ]]
                        return p_u_23._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerAcknowledgeClientVisitNPC, p_u_71, p73, p74, p75 == nil and {} or p75);
                    end;
                    local l_UserId_0 = p_u_71.UserId
                    if v_u_31:contains(l_UserId_0) ~= true then
                        v_u_31:add(l_UserId_0, 0)
                    end;
                    if v_u_31:get(l_UserId_0) >= 15 then
                        return f_response(false, "collection max");
                    end;
                    if p_u_23._player_blob_manager:is_player_id_verified_cached_blob_locked(l_UserId_0) then
                        return f_response(false, "playerblob locked");
                    end;
                    if v_u_30:is_on_cooldown(l_UserId_0) then
                        v_u_31:add(l_UserId_0, 15)
                        return f_response(false, "cooldown");
                    end;
                    v_u_30:add_cooldown_to_id(l_UserId_0, 1.5)
                    p_u_39:playerid_set_webnpc_visited(l_UserId_0, p_u_72, function(p76, p77, p_u_78) --[[ Line: 156 ]]
                        --[[ Upvalues: (copy 1): f_response, (ref 2): p_u_23, (copy 3): l_UserId_0, (ref 4): v_u_31, (ref 5): v_u_5, (ref 6): v_u_16, (ref 7): v_u_22, (ref 8): p_u_72, (ref 9): v_u_8, (ref 10): v_u_14, (ref 11): p_u_71, (ref 12): v_u_4 ]]
                        if p76 ~= true then
                            return f_response(false, p77);
                        end;
                        p_u_23._player_blob_manager:get_verified_cached_blob(l_UserId_0, function(p79) --[[ Line: 160 ]]
                            --[[ Upvalues: (ref 1): f_response, (ref 2): v_u_31, (ref 3): l_UserId_0, (ref 4): v_u_5, (ref 5): p_u_23, (ref 6): v_u_16, (ref 7): v_u_22, (ref 8): p_u_72, (ref 9): v_u_8, (copy 10): p_u_78, (ref 11): v_u_14, (ref 12): p_u_71, (ref 13): v_u_4 ]]
                            if p79 == nil then
                                return f_response(false, "playerblob is nil");
                            end;
                            v_u_31:add(l_UserId_0, v_u_31:get(l_UserId_0) + 1)
                            if v_u_5.UseChallengePassV2 == true then
                                p_u_23._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_16.DailyMissionType.SpeakWebNPC, p79)
                            end;
                            p_u_23._special_event_manager:write_special_event_data_for_player_action(l_UserId_0, v_u_22.PlayerActionEvent.SpeakPlayerNPCRewards, {
                                ["WebNPCID"] = p_u_72
                            })
                            v_u_14:server_sync_reward_params(p_u_23, p_u_71, v_u_14:claim_reward_info_list_to_playerblob(p_u_23, p79, (v_u_8:tier_visit_reward_desc_info_list(p_u_78))), function(p80, _, p81) --[[ Line: 178 ]]
                                --[[ Upvalues: (ref 1): v_u_14, (ref 2): p_u_23, (ref 3): v_u_4, (ref 4): p_u_71 ]]
                                local v82 = v_u_14.RewardInfo:list_to_table(p81)
                                p_u_23._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerAcknowledgeClientVisitNPC, p_u_71, true, p80, v82 == nil and {} or v82)
                            end)
                        end)
                    end)
                end)
            end)
            local v_u_83 = v_u_19:new()
            p_u_23._evt:wait_on_event(v_u_4.EVT_WebNPC_ClientAttemptPurchase, function(p_u_84, p_u_85, p_u_86, p_u_87) --[[ Line: 190 ]]
                --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_8, (ref 3): v_u_15, (ref 4): p_u_23, (ref 5): v_u_4, (copy 6): v_u_83, (ref 7): v_u_6, (ref 8): v_u_1, (ref 9): v_u_7, (ref 10): v_u_38, (ref 11): v_u_33, (ref 12): v_u_34, (copy 13): p_u_39, (ref 14): v_u_2, (ref 15): v_u_11, (ref 16): v_u_29, (ref 17): v_u_10 ]]
                v_u_13:is_string(p_u_86)
                v_u_13:is_enum_member(p_u_85, v_u_8.Tiers)
                v_u_13:is_int(p_u_87)
                if p_u_87 ~= v_u_8.SELECTED_DANCE_RANDOM and v_u_15:singleton():contains_dance_for_id(p_u_87) ~= true then
                    v_u_13:is_true(false, "EVT_WebNPC_ClientAttemptPurchase invalid selected_dance_id")
                end;
                local l_UserId_1 = p_u_84.UserId
                local function f_response(p88, p89) --[[ Name: response ]] --[[ Line: 199 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (copy 3): p_u_84 ]]
                    p_u_23._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerAttemptPurchaseResponse, p_u_84, p88, p89)
                end;
                v_u_83:queue_key_request(p_u_84.UserId, function() --[[ Line: 203 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_86, (copy 3): p_u_84, (ref 4): p_u_23, (copy 5): f_response, (copy 6): l_UserId_1, (ref 7): v_u_1, (ref 8): v_u_8, (copy 9): p_u_85, (ref 10): v_u_7, (ref 11): v_u_38, (copy 12): p_u_87, (ref 13): v_u_33, (ref 14): v_u_34, (ref 15): v_u_4, (ref 16): p_u_39, (ref 17): v_u_2, (ref 18): v_u_11, (ref 19): v_u_29, (ref 20): v_u_10 ]]
                    v_u_6:spawn(function() --[[ Line: 204 ]]
                        --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_86, (ref 3): p_u_84, (ref 4): p_u_23, (ref 5): f_response, (ref 6): l_UserId_1, (ref 7): v_u_1, (ref 8): v_u_8, (ref 9): p_u_85, (ref 10): v_u_7, (ref 11): v_u_38, (ref 12): p_u_87, (ref 13): v_u_33, (ref 14): v_u_34, (ref 15): v_u_4, (ref 16): p_u_39, (ref 17): v_u_2, (ref 18): v_u_11, (ref 19): v_u_29, (ref 20): v_u_10 ]]
                        local v_u_90 = v_u_6:filter_string(p_u_86, p_u_84, p_u_84)
                        p_u_23._post_fn:enqueue_function(function() --[[ Line: 206 ]]
                            --[[ Upvalues: (ref 1): p_u_86, (copy 2): v_u_90, (ref 3): f_response, (ref 4): p_u_23, (ref 5): l_UserId_1, (ref 6): v_u_1, (ref 7): v_u_8, (ref 8): p_u_85, (ref 9): v_u_7, (ref 10): v_u_38, (ref 11): p_u_87, (ref 12): v_u_33, (ref 13): v_u_34, (ref 14): v_u_4, (ref 15): p_u_84, (ref 16): p_u_39, (ref 17): v_u_2, (ref 18): v_u_11, (ref 19): v_u_29, (ref 20): v_u_10 ]]
                            if p_u_86 ~= v_u_90 then
                                return f_response(false, string.format("Message did not pass roblox moderation(%s)", v_u_90));
                            end;
                            p_u_23._player_blob_manager:get_verified_cached_blob(l_UserId_1, function(p91) --[[ Line: 211 ]]
                                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_8, (ref 3): p_u_85, (ref 4): v_u_7, (ref 5): f_response, (ref 6): v_u_38, (ref 7): l_UserId_1, (ref 8): p_u_86, (ref 9): v_u_90, (ref 10): p_u_87, (ref 11): p_u_23, (ref 12): v_u_33, (ref 13): v_u_34, (ref 14): v_u_4, (ref 15): p_u_84, (ref 16): p_u_39, (ref 17): v_u_2, (ref 18): v_u_11, (ref 19): v_u_29, (ref 20): v_u_10 ]]
                                if p91 == nil then
                                    return v_u_1:errf("EVT_WebNPC_ClientAttemptPurchase blob is nil");
                                end;
                                local v92, v93 = v_u_8:tier_get_price_type_and_amount(p_u_85)
                                local v94 = false
                                local v_u_95 = ""
                                if v92 == v_u_7.CurrencyType.Coins then
                                    if v93 <= v_u_7:get_coin_currency(p91) then
                                        v_u_7:add_coin_currency(p91, -v93)
                                        v94 = true
                                    else
                                        v_u_95 = "Not enough coins."
                                    end;
                                elseif v92 == v_u_7.CurrencyType.Stars then
                                    if v93 <= v_u_7:get_star_currency(p91) then
                                        v_u_7:add_star_currency(p91, -v93)
                                        v94 = true
                                    else
                                        v_u_95 = "Not enough stars."
                                    end;
                                else
                                    v_u_1:errf("EVT_WebNPC_ClientAttemptPurchase unknown purchase type(%s)", (tostring(p_u_85)))
                                end;
                                if v94 == false then
                                    return f_response(false, v_u_95);
                                end;
                                v_u_38:dsapi_buy_webnpc(l_UserId_1, p_u_85, p_u_86, v_u_90, p_u_87, function(p_u_96, p_u_97) --[[ Line: 244 ]]
                                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): l_UserId_1, (ref 3): v_u_7, (ref 4): v_u_33, (ref 5): v_u_34, (ref 6): v_u_95, (ref 7): v_u_4, (ref 8): p_u_84, (ref 9): p_u_39, (ref 10): v_u_8, (ref 11): v_u_90, (ref 12): p_u_85, (ref 13): v_u_2, (ref 14): v_u_11, (ref 15): p_u_87, (ref 16): v_u_29, (ref 17): v_u_10 ]]
                                    p_u_23._player_blob_manager:enqueue_blob_sync_request(l_UserId_1, v_u_7.PlayerBlobRequestType.Write, function() --[[ Line: 248 ]]
                                        --[[ Upvalues: (copy 1): p_u_96, (ref 2): v_u_33, (ref 3): l_UserId_1, (ref 4): v_u_34, (ref 5): v_u_95, (ref 6): p_u_23, (ref 7): v_u_4, (ref 8): p_u_84, (copy 9): p_u_97, (ref 10): p_u_39, (ref 11): v_u_8, (ref 12): v_u_90, (ref 13): p_u_85, (ref 14): v_u_2, (ref 15): v_u_11, (ref 16): p_u_87, (ref 17): v_u_29, (ref 18): v_u_10 ]]
                                        if p_u_96 == true then
                                            v_u_33:remove(l_UserId_1)
                                            v_u_34:add_cooldown_to_id(l_UserId_1, 0)
                                            p_u_23._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerAttemptPurchaseResponse, p_u_84, true, v_u_95)
                                            if p_u_97 ~= nil then
                                                p_u_39:append_new_webnpc(v_u_8.NPCData:new(p_u_97.WebNPCID, p_u_84.Name, l_UserId_1, v_u_90, p_u_85, v_u_2:new(v_u_11:get_webnpc_anchor_table_list()):random(), p_u_87))
                                                v_u_29 = v_u_10.WEBNPC_UPDATE_FREQ_SEC
                                                return;
                                            end;
                                        else
                                            p_u_23._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerAttemptPurchaseResponse, p_u_84, false, "Web backend failed, please contact Robeats support about your purchase!")
                                        end;
                                    end)
                                end)
                            end)
                        end)
                    end)
                end)
            end)
            local v_u_98 = v_u_19:new()
            p_u_23._evt:wait_on_event(v_u_4.EVT_WebNPC_ClientRequestMyNPCs, function(p_u_99) --[[ Line: 284 ]]
                --[[ Upvalues: (copy 1): v_u_98, (ref 2): p_u_23, (ref 3): v_u_4, (ref 4): v_u_8, (ref 5): v_u_33, (ref 6): v_u_38, (ref 7): v_u_34, (ref 8): v_u_10 ]]
                v_u_98:queue_key_request(p_u_99.UserId, function() --[[ Line: 285 ]]
                    --[[ Upvalues: (copy 1): p_u_99, (ref 2): p_u_23, (ref 3): v_u_4, (ref 4): v_u_8, (ref 5): v_u_33, (ref 6): v_u_38, (ref 7): v_u_34, (ref 8): v_u_10 ]]
                    local l_UserId_2 = p_u_99.UserId
                    local function f_response(p100) --[[ Name: response ]] --[[ Line: 287 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (ref 3): p_u_99, (ref 4): v_u_8 ]]
                        p_u_23._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerResponseMyNPCs, p_u_99, v_u_8.NPCData:list_to_table(p100))
                    end;
                    if v_u_33:contains(l_UserId_2) then
                        return f_response(v_u_33:get(l_UserId_2));
                    end;
                    v_u_38:dsapi_player_get_webnpcs(l_UserId_2, function(p101) --[[ Line: 294 ]]
                        --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_33, (copy 3): l_UserId_2, (ref 4): v_u_34, (ref 5): v_u_10, (ref 6): p_u_23, (ref 7): v_u_4, (ref 8): p_u_99 ]]
                        local v102 = v_u_8.NPCData:table_to_list(p101)
                        v_u_33:add(l_UserId_2, v102)
                        v_u_34:add_cooldown_to_id(l_UserId_2, v_u_10.WEBNPC_UPDATE_FREQ_SEC)
                        p_u_23._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerResponseMyNPCs, p_u_99, v_u_8.NPCData:list_to_table(v102))
                    end)
                end)
            end)
            local v_u_103 = v_u_19:new()
            p_u_23._evt:wait_on_event(v_u_4.EVT_WebNPC_ClientRequestNPCMessages, function(p_u_104, p_u_105) --[[ Line: 307 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (ref 3): v_u_17, (copy 4): v_u_103 ]]
                local function _(p106) --[[ Name: response ]] --[[ Line: 308 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (copy 3): p_u_104, (ref 4): v_u_17 ]]
                    p_u_23._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerResponseNPCMessages, p_u_104, v_u_17:list_to_table(p106))
                end;
                v_u_103:queue_key_request(p_u_104.UserId, function() --[[ Line: 311 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (copy 2): p_u_105, (ref 3): v_u_4, (copy 4): p_u_104, (ref 5): v_u_17 ]]
                    p_u_23._datastore_api:get_webnpcid_messages(p_u_105, function(p107) --[[ Line: 312 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (ref 3): p_u_104, (ref 4): v_u_17 ]]
                        p_u_23._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerResponseNPCMessages, p_u_104, v_u_17:list_to_table(p107))
                    end)
                end)
            end)
            local v_u_108 = v_u_19:new()
            p_u_23._evt:wait_on_event(v_u_4.EVT_WebNPC_ClientRequestWebNPCIDInfo, function(p_u_109, p_u_110) --[[ Line: 321 ]]
                --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (copy 3): v_u_108, (ref 4): v_u_38 ]]
                local function f_response(p111, p112) --[[ Name: response ]] --[[ Line: 322 ]]
                    --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (copy 3): p_u_109 ]]
                    p_u_23._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerResponseWebNPCIDInfo, p_u_109, p111:to_table(), p112)
                end;
                v_u_108:queue_key_request(p_u_109.UserId, function() --[[ Line: 325 ]]
                    --[[ Upvalues: (ref 1): v_u_38, (copy 2): p_u_110, (copy 3): f_response ]]
                    v_u_38:dsapi_get_webnpcid_npc_data(p_u_110, function(p113, p114) --[[ Line: 326 ]]
                        --[[ Upvalues: (ref 1): f_response ]]
                        return f_response(p113, p114);
                    end)
                end)
            end)
            local function f_for_every_cached_webnpc_of_id(p115, p116) --[[ Name: for_every_cached_webnpc_of_id ]] --[[ Line: 333 ]]
                --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_33 ]]
                if v_u_25:contains(p115) then
                    p116(v_u_25:get(p115))
                end;
                for _, v117 in v_u_33:key_itr() do
                    for _, v118 in v117:key_itr() do
                        if v118:get_webnpcid() == p115 then
                            p116(v118)
                        end;
                    end;
                end;
            end;
            local function _(p119) --[[ Name: webnpcid_increment_comment_count ]] --[[ Line: 346 ]]
                --[[ Upvalues: (copy 1): f_for_every_cached_webnpc_of_id, (ref 2): v_u_38 ]]
                f_for_every_cached_webnpc_of_id(p119, function(p120) --[[ Line: 347 ]]
                    p120:set_comment_count(p120:get_comment_count() + 1)
                end)
                v_u_38:dsapi_webnpc_increment_comment_count(p119)
            end;
            local v_u_121 = v_u_19:new()
            p_u_23._evt:wait_on_event(v_u_4.EVT_WebNPC_ClientPostNPCMessage, function(p_u_122, p_u_123, p_u_124) --[[ Line: 355 ]]
                --[[ Upvalues: (ref 1): v_u_13, (copy 2): v_u_121, (ref 3): v_u_2, (ref 4): p_u_23, (ref 5): v_u_4, (ref 6): v_u_17, (ref 7): v_u_35, (ref 8): v_u_25, (ref 9): v_u_6, (copy 10): f_for_every_cached_webnpc_of_id, (ref 11): v_u_38, (ref 12): v_u_16, (ref 13): v_u_7, (ref 14): v_u_37 ]]
                v_u_13:is_int(p_u_123)
                v_u_13:is_string(p_u_124)
                v_u_121:queue_key_request(p_u_122.UserId, function() --[[ Line: 358 ]]
                    --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_23, (ref 3): v_u_4, (copy 4): p_u_122, (ref 5): v_u_17, (ref 6): v_u_35, (ref 7): v_u_25, (copy 8): p_u_123, (ref 9): v_u_6, (copy 10): p_u_124, (ref 11): f_for_every_cached_webnpc_of_id, (ref 12): v_u_38, (ref 13): v_u_16, (ref 14): v_u_7, (ref 15): v_u_37 ]]
                    local function f_response(p125, p126, p127, p128) --[[ Name: response ]] --[[ Line: 359 ]]
                        --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_23, (ref 3): v_u_4, (ref 4): p_u_122, (ref 5): v_u_17 ]]
                        if p127 == nil then
                            p127 = v_u_2:new()
                        end;
                        if p128 == nil then
                            p128 = false
                        end;
                        p_u_23._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerPostNPCMessageResponse, p_u_122, p125, p126, v_u_17:list_to_table(p127), p128)
                    end;
                    if v_u_35:is_on_cooldown(p_u_122.UserId) then
                        return f_response(false, "On cooldown");
                    end;
                    local v_u_129 = v_u_25:contains(p_u_123) and v_u_25:get(p_u_123):get_userid() == p_u_122.UserId and true or false
                    spawn(function() --[[ Line: 374 ]]
                        --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_124, (ref 3): p_u_122, (copy 4): f_response, (ref 5): p_u_23, (ref 6): v_u_35, (ref 7): p_u_123, (ref 8): v_u_17, (ref 9): f_for_every_cached_webnpc_of_id, (ref 10): v_u_38, (ref 11): v_u_129, (ref 12): v_u_16, (ref 13): v_u_7, (ref 14): v_u_2, (ref 15): v_u_4, (ref 16): v_u_37, (ref 17): v_u_25 ]]
                        local v_u_130 = v_u_6:filter_string(p_u_124, p_u_122, p_u_122)
                        if v_u_130 ~= p_u_124 then
                            return f_response(false, string.format("Message did not pass roblox moderation(%s)", v_u_130));
                        end;
                        p_u_23._post_fn:enqueue_function(function() --[[ Line: 379 ]]
                            --[[ Upvalues: (ref 1): v_u_35, (ref 2): p_u_122, (ref 3): p_u_23, (ref 4): p_u_123, (ref 5): v_u_17, (copy 6): v_u_130, (ref 7): f_for_every_cached_webnpc_of_id, (ref 8): v_u_38, (ref 9): v_u_129, (ref 10): v_u_16, (ref 11): f_response, (ref 12): v_u_7, (ref 13): v_u_2, (ref 14): v_u_4, (ref 15): v_u_37, (ref 16): v_u_25 ]]
                            v_u_35:add_cooldown_to_id(p_u_122.UserId, 2.5)
                            p_u_23._datastore_api:write_webnpcid_message(p_u_123, v_u_17:new():set_player_id_name(p_u_122.UserId, p_u_122.Name):set_message_time(p_u_23._api:get_global_time()):set_message_text(v_u_130), function(p_u_131) --[[ Line: 388 ]]
                                --[[ Upvalues: (ref 1): p_u_123, (ref 2): f_for_every_cached_webnpc_of_id, (ref 3): v_u_38, (ref 4): v_u_129, (ref 5): v_u_16, (ref 6): p_u_23, (ref 7): p_u_122, (ref 8): f_response, (ref 9): v_u_7, (ref 10): v_u_2, (ref 11): v_u_4, (ref 12): v_u_17, (ref 13): v_u_37, (ref 14): v_u_25 ]]
                                local v132 = p_u_123
                                f_for_every_cached_webnpc_of_id(v132, function(p133) --[[ Line: 347 ]]
                                    p133:set_comment_count(p133:get_comment_count() + 1)
                                end)
                                v_u_38:dsapi_webnpc_increment_comment_count(v132)
                                if v_u_129 == true or v_u_16:can_claim_daily_mission_type_playerblob_dayid_monthid(v_u_16.DailyMissionType.LikeOrPostWebNPC, p_u_23._player_blob_manager:get_cached_blob(p_u_122.UserId), p_u_23._api:get_day_id(), p_u_23._api:get_month_id()) ~= true then
                                    local v134 = nil
                                    if p_u_131 == nil then
                                        p_u_131 = v_u_2:new()
                                    end;
                                    if v134 == nil then
                                        v134 = false
                                    end;
                                    p_u_23._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerPostNPCMessageResponse, p_u_122, true, "", v_u_17:list_to_table(p_u_131), v134)
                                else
                                    p_u_23._player_blob_manager:get_verified_cached_blob(p_u_122.UserId, function(p135) --[[ Line: 391 ]]
                                        --[[ Upvalues: (ref 1): f_response, (copy 2): p_u_131, (ref 3): p_u_23, (ref 4): v_u_16, (ref 5): p_u_122, (ref 6): v_u_7 ]]
                                        if p135 == nil then
                                            return f_response(true, "", p_u_131);
                                        end;
                                        p_u_23._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_16.DailyMissionType.LikeOrPostWebNPC, p135)
                                        p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_122.UserId, v_u_7.PlayerBlobRequestType.Write, function(_) --[[ Line: 398 ]]
                                            --[[ Upvalues: (ref 1): f_response, (ref 2): p_u_131 ]]
                                            return f_response(true, "", p_u_131, true);
                                        end)
                                    end)
                                end;
                                v_u_37:flag_playerid_webnpcid_as_recent(p_u_122.UserId, p_u_123, v_u_25:get(p_u_123))
                            end)
                        end)
                    end)
                end)
            end)
            local function _(p136, p_u_137, p_u_138) --[[ Name: player_webnpcid_opt_increment_like_count ]] --[[ Line: 415 ]]
                --[[ Upvalues: (ref 1): p_u_23, (copy 2): f_for_every_cached_webnpc_of_id, (ref 3): v_u_38 ]]
                local l_UserId_3 = p136.UserId
                p_u_23._datastore_api:get_playerid_liked_web_npc_ids_set(l_UserId_3, function(p_u_139) --[[ Line: 417 ]]
                    --[[ Upvalues: (copy 1): p_u_137, (copy 2): p_u_138, (ref 3): f_for_every_cached_webnpc_of_id, (ref 4): v_u_38, (ref 5): p_u_23, (copy 6): l_UserId_3 ]]
                    if p_u_139:contains(p_u_137) then
                        return p_u_138(false, p_u_139);
                    end;
                    p_u_139:add_set(p_u_137)
                    f_for_every_cached_webnpc_of_id(p_u_137, function(p140) --[[ Line: 424 ]]
                        p140:set_like_count(p140:get_like_count() + 1)
                    end)
                    v_u_38:dsapi_webnpc_increment_like_count(p_u_137)
                    p_u_23._datastore_api:write_playerid_liked_web_npc_id(l_UserId_3, p_u_137, function() --[[ Line: 429 ]]
                        --[[ Upvalues: (ref 1): p_u_138, (copy 2): p_u_139 ]]
                        if p_u_138 ~= nil then
                            p_u_138(true, p_u_139)
                        end;
                    end)
                end)
            end;
            local v_u_141 = v_u_19:new():set_cooldown(5)
            p_u_23._evt:wait_on_event(v_u_4.EVT_WebNPC_ClientLikeNPC, function(p_u_142, p_u_143) --[[ Line: 437 ]]
                --[[ Upvalues: (ref 1): v_u_13, (copy 2): v_u_141, (ref 3): p_u_23, (ref 4): v_u_4, (ref 5): v_u_36, (ref 6): v_u_3, (ref 7): v_u_32, (ref 8): v_u_25, (ref 9): v_u_16, (ref 10): v_u_26, (ref 11): v_u_7, (ref 12): v_u_6, (ref 13): v_u_37, (copy 14): f_for_every_cached_webnpc_of_id, (ref 15): v_u_38 ]]
                v_u_13:is_int(p_u_143)
                v_u_141:queue_key_request(p_u_142.UserId, function() --[[ Line: 440 ]]
                    --[[ Upvalues: (copy 1): p_u_142, (ref 2): p_u_23, (ref 3): v_u_4, (ref 4): v_u_36, (ref 5): v_u_3, (ref 6): v_u_32, (ref 7): v_u_25, (copy 8): p_u_143, (ref 9): v_u_16, (ref 10): v_u_26, (ref 11): v_u_7, (ref 12): v_u_6, (ref 13): v_u_37, (ref 14): f_for_every_cached_webnpc_of_id, (ref 15): v_u_38 ]]
                    local l_UserId_4 = p_u_142.UserId
                    local function f_response(p144, p145, p146, p147) --[[ Name: response ]] --[[ Line: 442 ]]
                        --[[ Upvalues: (ref 1): p_u_23, (ref 2): v_u_4, (ref 3): p_u_142 ]]
                        if p147 == nil then
                            p147 = false
                        end;
                        p_u_23._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerLikeNPCResponse, p_u_142, p144, p145, p146:key_list():get_table(), p147)
                    end;
                    if v_u_36:is_on_cooldown(l_UserId_4) then
                        return f_response(false, "On cooldown", v_u_3:new());
                    end;
                    v_u_36:add_cooldown_to_id(l_UserId_4, 2.5)
                    if v_u_32:contains(l_UserId_4) ~= true then
                        v_u_32:add(l_UserId_4, 0)
                    end;
                    v_u_32:add(l_UserId_4, v_u_32:get(l_UserId_4) + 1)
                    local v_u_148 = v_u_25:contains(p_u_143) and v_u_25:get(p_u_143):get_userid() == l_UserId_4 and true or false
                    local v_u_149 = p_u_143
                    local function v_u_159(p_u_150, p_u_151) --[[ Line: 462 ]]
                        --[[ Upvalues: (ref 1): v_u_148, (ref 2): p_u_23, (copy 3): l_UserId_4, (copy 4): f_response, (ref 5): v_u_16, (ref 6): p_u_143, (ref 7): v_u_26, (ref 8): v_u_32, (ref 9): p_u_142, (ref 10): v_u_7, (ref 11): v_u_6, (ref 12): v_u_4, (ref 13): v_u_37, (ref 14): v_u_25 ]]
                        if p_u_150 == true and v_u_148 ~= true then
                            p_u_23._player_blob_manager:get_verified_cached_blob(l_UserId_4, function(p152) --[[ Line: 464 ]]
                                --[[ Upvalues: (ref 1): f_response, (copy 2): p_u_150, (copy 3): p_u_151, (ref 4): v_u_16, (ref 5): p_u_23, (ref 6): l_UserId_4, (ref 7): p_u_143, (ref 8): v_u_26, (ref 9): v_u_32, (ref 10): p_u_142, (ref 11): v_u_7, (ref 12): v_u_6 ]]
                                if p152 == nil then
                                    return f_response(p_u_150, "", p_u_151);
                                end;
                                if v_u_16:can_claim_daily_mission_type_playerblob_dayid_monthid(v_u_16.DailyMissionType.LikeOrPostWebNPC, p_u_23._player_blob_manager:get_cached_blob(l_UserId_4), p_u_23._api:get_day_id(), p_u_23._api:get_month_id()) == true then
                                    p_u_23._challengepass_manager:challengepassv2_daily_mission_playerblob_claim(v_u_16.DailyMissionType.LikeOrPostWebNPC, p152)
                                end;
                                local v153 = p_u_143
                                for _, v154 in v_u_26:key_itr() do
                                    if v154:get_webnpcid() == v153 then
                                        v157 = true
                                        -- ::l8:: (Possible bug with goto)
                                        if v157 == true then
                                            if v_u_32:get(l_UserId_4) < 200 then
                                                p152.CoinCurrency = p152.CoinCurrency + 5
                                                p_u_23._chat:get_chat_service():send_system_message_to_player_for_channel(p_u_142, p_u_23._chat:get_chat_service():get_channel(p_u_23._chat:get_chat_service():get_server_system_channel_id()), string.format("For voting on this NPC\'s message, you got %d coins!", 5), function(p155) --[[ Line: 477 ]]
                                                    --[[ Upvalues: (ref 1): v_u_7 ]]
                                                    p155:set_channel_name("")
                                                    p155:set_icon(v_u_7:currency_type_get_image(v_u_7.CurrencyType.Coins))
                                                end)
                                            end;
                                        else
                                            p_u_23._chat:get_chat_service():send_system_message_to_player_for_channel(p_u_142, p_u_23._chat:get_chat_service():get_channel(p_u_23._chat:get_chat_service():get_server_system_channel_id()), "NPC has already left the server, no rewards were granted for voting on this NPC\'s message.", function(p156) --[[ Line: 488 ]]
                                                --[[ Upvalues: (ref 1): v_u_6 ]]
                                                p156:set_channel_name("")
                                                p156:set_icon(v_u_6:important_assetid())
                                            end)
                                        end;
                                        p_u_23._player_blob_manager:enqueue_blob_sync_request(p_u_142.UserId, v_u_7.PlayerBlobRequestType.Write, function(_) --[[ Line: 498 ]]
                                            --[[ Upvalues: (ref 1): f_response, (ref 2): p_u_150, (ref 3): p_u_151 ]]
                                            return f_response(p_u_150, "", p_u_151, true);
                                        end)
                                        return;
                                    end;
                                end;
                                local v157 = false
                                break;
                            end)
                        else
                            local v158 = nil
                            if v158 == nil then
                                v158 = false
                            end;
                            p_u_23._evt:fire_event_to_client(v_u_4.EVT_WebNPC_ServerLikeNPCResponse, p_u_142, p_u_150, "", p_u_151:key_list():get_table(), v158)
                        end;
                        v_u_37:flag_playerid_webnpcid_as_recent(p_u_142.UserId, p_u_143, v_u_25:get(p_u_143))
                    end;
                    local l_UserId_5 = p_u_142.UserId
                    p_u_23._datastore_api:get_playerid_liked_web_npc_ids_set(l_UserId_5, function(p_u_160) --[[ Line: 417 ]]
                        --[[ Upvalues: (copy 1): v_u_149, (copy 2): v_u_159, (ref 3): f_for_every_cached_webnpc_of_id, (ref 4): v_u_38, (ref 5): p_u_23, (copy 6): l_UserId_5 ]]
                        if p_u_160:contains(v_u_149) then
                            return v_u_159(false, p_u_160);
                        end;
                        p_u_160:add_set(v_u_149)
                        f_for_every_cached_webnpc_of_id(v_u_149, function(p161) --[[ Line: 424 ]]
                            p161:set_like_count(p161:get_like_count() + 1)
                        end)
                        v_u_38:dsapi_webnpc_increment_like_count(v_u_149)
                        p_u_23._datastore_api:write_playerid_liked_web_npc_id(l_UserId_5, v_u_149, function() --[[ Line: 429 ]]
                            --[[ Upvalues: (ref 1): v_u_159, (copy 2): p_u_160 ]]
                            if v_u_159 ~= nil then
                                v_u_159(true, p_u_160)
                            end;
                        end)
                    end)
                end)
            end)
            v_u_37:start()
        end;
        local v_u_162 = v_u_3:new():add_set_from_table_list({ v_u_8.Tiers.Tier2, v_u_8.Tiers.Tier3 })
        local v_u_163 = v_u_3:new()
        v24.playerid_get_webnpc_visited_list_tab = function(_, p_u_164, p_u_165) --[[ Name: playerid_get_webnpc_visited_list_tab ]] --[[ Line: 520 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): v_u_25, (copy 3): v_u_162, (copy 4): v_u_163, (ref 5): v_u_1, (copy 6): p_u_23, (ref 7): v_u_13 ]]
            local function f_get_test_webnpcid_list() --[[ Name: get_test_webnpcid_list ]] --[[ Line: 522 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_25, (ref 3): v_u_162 ]]
                local v166 = v_u_2:new()
                for v167, v168 in v_u_25:key_itr() do
                    if v_u_162:contains(v168:get_tier()) then
                        v166:push_back(v167)
                    end;
                end;
                return v166;
            end;
            local function f_do_callback() --[[ Name: do_callback ]] --[[ Line: 532 ]]
                --[[ Upvalues: (ref 1): v_u_163, (copy 2): p_u_164, (ref 3): v_u_1, (copy 4): p_u_165 ]]
                local v169 = v_u_163:get(p_u_164)
                if typeof(v169) == "table" then
                    p_u_165(v169)
                else
                    v_u_1:warnf("playerid_get_webnpc_visited do_callback _playerid_to_cached_webnpc_visited does not contain(%s)", (tostring(p_u_164)))
                    p_u_165({})
                end;
            end;
            if v_u_163:contains(p_u_164) then
                f_do_callback()
            else
                p_u_23._datastore_api:datastore_api_player_get_visited_webnpcs(p_u_164, f_get_test_webnpcid_list(), function(p170) --[[ Line: 545 ]]
                    --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_25, (ref 3): v_u_162, (ref 4): v_u_163, (copy 5): p_u_164, (copy 6): f_do_callback ]]
                    for v171, v172 in pairs(p170) do
                        v_u_13:is_int(v171)
                        v_u_13:is_bool(v172)
                        local v173 = v_u_25:get(v171)
                        v_u_13:is_non_nil(v173)
                        v_u_13:is_true(v_u_162:contains(v173:get_tier()))
                    end;
                    v_u_163:add(p_u_164, p170)
                    f_do_callback()
                end)
            end;
        end;
        v24.playerid_set_webnpc_visited = function(_, p174, p175, p_u_176) --[[ Name: playerid_set_webnpc_visited ]] --[[ Line: 559 ]]
            --[[ Upvalues: (copy 1): v_u_163, (ref 2): v_u_1, (ref 3): v_u_8, (copy 4): v_u_25, (copy 5): v_u_162, (copy 6): p_u_23 ]]
            local v177 = v_u_163:get(p174)
            if v177 == nil then
                v_u_1:warnf("ServerWebNPCManager:playerid_set_webnpc_visited _playerid_to_cached_webnpc_visited cannot find(%d)", p174)
                p_u_176(false, "cannot find cached visited table")
                return;
            elseif v177[p175] == false then
                local l_Tier1_0 = v_u_8.Tiers.Tier1
                if v_u_25:contains(p175) then
                    l_Tier1_0 = v_u_25:get(p175):get_tier()
                end;
                if v_u_162:contains(l_Tier1_0) == true then
                    v177[p175] = true
                    p_u_23._datastore_api:datastore_api_player_set_webnpc_visited(p174, p175, function(p178) --[[ Line: 583 ]]
                        --[[ Upvalues: (copy 1): p_u_176, (ref 2): l_Tier1_0 ]]
                        if p178 == true then
                            p_u_176(true, "", l_Tier1_0)
                        else
                            p_u_176(false, "error on request", l_Tier1_0)
                        end;
                    end)
                else
                    v_u_1:warnf("ServerWebNPCManager:playerid_set_webnpc_visited found tier(%d) for webnpcid(%d) invalid", l_Tier1_0, p175)
                    p_u_176(false, "invalid tier")
                end;
            else
                v_u_1:warnf("ServerWebNPCManager:playerid_set_webnpc_visited _playerid_to_cached_webnpc_visited player(%d) webnpcid(%d) is(%s)", p174, p175, (tostring(v177[p175])))
                p_u_176(false, "visited table invalid value")
                return;
            end;
        end;
        v24.player_disconnecting = function(_, p179) --[[ Name: player_disconnecting ]] --[[ Line: 592 ]]
            --[[ Upvalues: (copy 1): v_u_163, (copy 2): v_u_37 ]]
            v_u_163:remove(p179)
            v_u_37:player_disconnecting(p179)
        end;
        local function f_add_webnpc_data(p180) --[[ Name: add_webnpc_data ]] --[[ Line: 597 ]]
            --[[ Upvalues: (ref 1): v_u_15, (copy 2): v_u_25, (copy 3): v_u_26 ]]
            if v_u_15:singleton():contains_dance_for_id(p180:get_danceid()) ~= true then
                p180:set_danceid(v_u_15:singleton():get_default_owned_danceid_set():key_list():random())
            end;
            v_u_25:add(p180:get_webnpcid(), p180)
            v_u_26:push_back(p180)
        end;
        v24.process_webnpcs_tab = function(_, p181) --[[ Name: process_webnpcs_tab ]] --[[ Line: 607 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_11, (copy 3): v_u_26, (ref 4): v_u_8, (copy 5): f_add_webnpc_data ]]
            local v182 = v_u_2:new():push_back_table_list(v_u_11:get_webnpc_anchor_table_list())
            v182:shuffle()
            v_u_26:clear()
            for v183 = 1, #p181 do
                if v182:count() <= 0 then
                    break;
                end;
                local v184 = v_u_8.NPCData:from_table(p181[v183])
                v184:set_anchor((v182:pop_back()))
                f_add_webnpc_data(v184)
            end;
        end;
        v24.append_new_webnpc = function(_, p185) --[[ Name: append_new_webnpc ]] --[[ Line: 627 ]]
            --[[ Upvalues: (copy 1): v_u_26, (ref 2): v_u_2, (ref 3): v_u_11, (copy 4): f_add_webnpc_data ]]
            if v_u_26:count() > 0 then
                v_u_26:pop_front()
            end;
            local v186 = v_u_2:new():push_back_table_list(v_u_11:get_webnpc_anchor_table_list())
            for _, v187 in v_u_26:key_itr() do
                v186:remove(v187:get_anchor())
            end;
            if v186:count() > 0 then
                p185:set_anchor(v186:random())
                f_add_webnpc_data(p185)
            end;
        end;
        v24.update = function(_, p_u_188) --[[ Name: update ]] --[[ Line: 646 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_9, (copy 3): v_u_30, (copy 4): v_u_34, (ref 5): v_u_3, (copy 6): v_u_33, (copy 7): v_u_35, (copy 8): v_u_36, (copy 9): v_u_37, (ref 10): v_u_6, (copy 11): v_u_38 ]]
            if v_u_29 > 0 then
                v_u_29 = v_u_29 - v_u_9:TimescaleToDeltaTime(p_u_188)
            end;
            v_u_30:update(p_u_188)
            v_u_34:update(p_u_188)
            v_u_3:remove_if(v_u_33, function(_, p189) --[[ Line: 653 ]]
                --[[ Upvalues: (ref 1): v_u_34 ]]
                return v_u_34:is_on_cooldown(p189) ~= true;
            end)
            v_u_35:update(p_u_188)
            v_u_36:update(p_u_188)
            v_u_37:update(p_u_188)
            v_u_6:ptry(function() --[[ Line: 660 ]]
                --[[ Upvalues: (ref 1): v_u_38, (copy 2): p_u_188 ]]
                v_u_38:update(p_u_188)
            end)
        end;
        return v24;
    end
};
