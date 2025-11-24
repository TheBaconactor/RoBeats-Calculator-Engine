-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:17 PM
-- Time elapsed: 71 milliseconds

local s_DataStoreService_0 = game:GetService("DataStoreService")
local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_4 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.FavoriteData)
local v_u_7 = require(game.ServerScriptService.ServerStatsCounter)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_9 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_10 = require(game.ReplicatedStorage.Shared.Mission.MissionLeaderboardEntry)
local v_u_11 = require(game.ReplicatedStorage.Shared.Mutex)
local v_u_12 = require(game.ReplicatedStorage.Shared.GuildMessage)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.WebNPCPurchaseInfo)
local v_u_14 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_15 = require(game.ServerScriptService.ServerPrivateConstants)
return {
    ["new"] = function(_, p_u_16) --[[ Name: new ]] --[[ Line: 26 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_14, (copy 3): v_u_4, (copy 4): v_u_15, (copy 5): v_u_7, (copy 6): v_u_1, (copy 7): v_u_11, (copy 8): s_DataStoreService_0, (copy 9): v_u_2, (copy 10): v_u_3, (copy 11): v_u_6, (copy 12): v_u_9, (copy 13): v_u_8, (copy 14): v_u_10, (copy 15): v_u_12, (copy 16): v_u_13 ]]
        local v17 = {}
        local function _(_, _, _) --[[ Name: DEV_datastore_request_random_delay ]] --[[ Line: 29 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            if v_u_5:is_dev_build() then
                v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
            end;
        end;
        local function _(p18) --[[ Name: trigger_datastore_chaos_monkey ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4 ]]
            if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring(p18)))
            end;
        end;
        local function f_trigger_datastore_lag_monkey(p19) --[[ Name: trigger_datastore_lag_monkey ]] --[[ Line: 42 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4 ]]
            if v_u_14.DatastoreLagMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                v_u_4:warnf("Triggering DatastoreLagMonkey for %s", (tostring(p19)))
                v_u_5:wait(30)
                v_u_4:errf("ServerDataStoreAPIManager %s lagmonkey fail", (tostring(p19)))
            end;
        end;
        local function f_run_datastore_request(p_u_20) --[[ Name: run_datastore_request ]] --[[ Line: 53 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_4 ]]
            if v_u_5:is_dev_build() ~= true then
                return p_u_20();
            end;
            local v_u_21 = false
            local function _() --[[ Name: run_datastore_call ]] --[[ Line: 60 ]]
                --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_21, (copy 3): p_u_20 ]]
                v_u_5:spawn(function() --[[ Line: 61 ]]
                    --[[ Upvalues: (ref 1): v_u_21, (ref 2): p_u_20 ]]
                    if v_u_21 ~= true then
                        p_u_20()
                        v_u_21 = true
                    end;
                end)
            end;
            local v22 = tick()
            v_u_5:spawn(function() --[[ Line: 61 ]]
                --[[ Upvalues: (ref 1): v_u_21, (copy 2): p_u_20 ]]
                if v_u_21 ~= true then
                    p_u_20()
                    v_u_21 = true
                end;
            end)
            local v23 = 1
            while v_u_21 ~= true do
                local v24 = tick()
                if v24 - v22 > 2.5 then
                    v23 = v23 + 1
                    v_u_5:spawn(function() --[[ Line: 61 ]]
                        --[[ Upvalues: (ref 1): v_u_21, (copy 2): p_u_20 ]]
                        if v_u_21 ~= true then
                            p_u_20()
                            v_u_21 = true
                        end;
                    end)
                    v_u_4:warnf("[DEV] ServerDataStoreAPIManager fn_datastore_call timed out, retrying(%d)", v23)
                else
                    v24 = v22
                end;
                v_u_5:wait(0.25)
                v22 = v24
            end;
        end;
        local function _(p_u_25, p26, p_u_27, p_u_28) --[[ Name: do_datastore_get ]] --[[ Line: 83 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_5, (ref 3): v_u_14, (ref 4): v_u_4, (ref 5): v_u_7, (copy 6): f_run_datastore_request, (copy 7): f_trigger_datastore_lag_monkey, (copy 8): p_u_16 ]]
            local v_u_29 = v_u_15:get_env_datastore_prefix() .. p26
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): p_u_25, (ref 2): v_u_29, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): p_u_28, (copy 10): p_u_27, (ref 11): p_u_16 ]]
                local v30 = tick()
                local v_u_31, v_u_32, v33
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_31 = false
                    v_u_32 = nil
                    v33 = 1
                else
                    v_u_31 = false
                    v_u_32 = nil
                    v33 = 1
                end;
                while v_u_31 ~= true do
                    local _, v34 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_32, (ref 8): p_u_25, (ref 9): v_u_29, (ref 10): p_u_28, (ref 11): v_u_31 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_32, (ref 3): p_u_25, (ref 4): v_u_29, (ref 5): p_u_28 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_32 = p_u_25:GetAsync(v_u_29, p_u_28)
                        end)
                        v_u_31 = true
                    end)
                    if v_u_31 ~= true then
                        if v33 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_29, (tostring(v34)));
                        end;
                        wait(v33)
                        v33 = v33 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_29, v33, (tostring(v34)))
                    end;
                end;
                if p_u_27 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_31, (ref 3): v_u_32 ]]
                        p_u_27(v_u_31, v_u_32)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", p_u_25.Name, v_u_29, tick() - v30)
            end)
        end;
        v17.do_datastore_get = function(_, p_u_35, p36, p_u_37) --[[ Name: do_datastore_get ]] --[[ Line: 120 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_5, (ref 3): v_u_14, (ref 4): v_u_4, (ref 5): v_u_7, (copy 6): f_run_datastore_request, (copy 7): f_trigger_datastore_lag_monkey, (copy 8): p_u_16 ]]
            local v_u_38 = v_u_15:get_env_datastore_prefix() .. p36
            local v_u_39 = nil
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): p_u_35, (ref 2): v_u_38, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_39, (copy 10): p_u_37, (ref 11): p_u_16 ]]
                local v40 = tick()
                local v_u_41, v_u_42, v43
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_41 = false
                    v_u_42 = nil
                    v43 = 1
                else
                    v_u_41 = false
                    v_u_42 = nil
                    v43 = 1
                end;
                while v_u_41 ~= true do
                    local _, v44 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_42, (ref 8): p_u_35, (ref 9): v_u_38, (ref 10): v_u_39, (ref 11): v_u_41 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_42, (ref 3): p_u_35, (ref 4): v_u_38, (ref 5): v_u_39 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_42 = p_u_35:GetAsync(v_u_38, v_u_39)
                        end)
                        v_u_41 = true
                    end)
                    if v_u_41 ~= true then
                        if v43 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_38, (tostring(v44)));
                        end;
                        wait(v43)
                        v43 = v43 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_38, v43, (tostring(v44)))
                    end;
                end;
                if p_u_37 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): p_u_37, (ref 2): v_u_41, (ref 3): v_u_42 ]]
                        p_u_37(v_u_41, v_u_42)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", p_u_35.Name, v_u_38, tick() - v40)
            end)
        end;
        v17.do_datastore_get_no_cache = function(_, p_u_45, p46, p_u_47) --[[ Name: do_datastore_get_no_cache ]] --[[ Line: 121 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_5, (ref 3): v_u_14, (ref 4): v_u_4, (ref 5): v_u_7, (copy 6): f_run_datastore_request, (copy 7): f_trigger_datastore_lag_monkey, (copy 8): p_u_16 ]]
            local l_DataStoreGetOptions_0 = Instance.new("DataStoreGetOptions")
            l_DataStoreGetOptions_0.UseCache = false
            local v_u_48 = v_u_15:get_env_datastore_prefix() .. p46
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): p_u_45, (ref 2): v_u_48, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): l_DataStoreGetOptions_0, (copy 10): p_u_47, (ref 11): p_u_16 ]]
                local v49 = tick()
                local v_u_50, v_u_51, v52
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_50 = false
                    v_u_51 = nil
                    v52 = 1
                else
                    v_u_50 = false
                    v_u_51 = nil
                    v52 = 1
                end;
                while v_u_50 ~= true do
                    local _, v53 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_51, (ref 8): p_u_45, (ref 9): v_u_48, (ref 10): l_DataStoreGetOptions_0, (ref 11): v_u_50 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_51, (ref 3): p_u_45, (ref 4): v_u_48, (ref 5): l_DataStoreGetOptions_0 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_51 = p_u_45:GetAsync(v_u_48, l_DataStoreGetOptions_0)
                        end)
                        v_u_50 = true
                    end)
                    if v_u_50 ~= true then
                        if v52 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_48, (tostring(v53)));
                        end;
                        wait(v52)
                        v52 = v52 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_48, v52, (tostring(v53)))
                    end;
                end;
                if p_u_47 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): p_u_47, (ref 2): v_u_50, (ref 3): v_u_51 ]]
                        p_u_47(v_u_50, v_u_51)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", p_u_45.Name, v_u_48, tick() - v49)
            end)
        end;
        local function _(p_u_54, p55, p_u_56, p_u_57) --[[ Name: do_datastore_set ]] --[[ Line: 127 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_5, (ref 3): v_u_14, (ref 4): v_u_4, (ref 5): v_u_7, (copy 6): f_run_datastore_request, (copy 7): f_trigger_datastore_lag_monkey, (copy 8): p_u_16 ]]
            local v_u_58 = v_u_15:get_env_datastore_prefix() .. p55
            v_u_5:spawn(function() --[[ Line: 130 ]]
                --[[ Upvalues: (copy 1): p_u_54, (ref 2): v_u_58, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): p_u_56, (copy 10): p_u_57, (ref 11): p_u_16 ]]
                local v59 = tick()
                local v_u_60, v61
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_60 = false
                    v61 = 1
                else
                    v_u_60 = false
                    v61 = 1
                end;
                while v_u_60 ~= true do
                    local _, v62 = pcall(function() --[[ Line: 136 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): p_u_54, (ref 8): v_u_58, (ref 9): p_u_56, (ref 10): v_u_60 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("set    ")))
                        end;
                        v_u_7:increment_datastore_set_count()
                        f_run_datastore_request(function() --[[ Line: 140 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): p_u_54, (ref 3): v_u_58, (ref 4): p_u_56 ]]
                            f_trigger_datastore_lag_monkey("set    ")
                            p_u_54:SetAsync(v_u_58, p_u_56)
                        end)
                        v_u_60 = true
                    end)
                    if v_u_60 ~= true then
                        if v61 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_set key(%s) failed(%s)", v_u_58, (tostring(v62)));
                        end;
                        wait(v61)
                        v61 = v61 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_set key(%s) wait(%d) failed(%s)", v_u_58, v61, (tostring(v62)))
                    end;
                end;
                if p_u_57 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 154 ]]
                        --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_60 ]]
                        p_u_57(v_u_60, "")
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "set    ", p_u_54.Name, v_u_58, tick() - v59)
            end)
        end;
        v17.do_datastore_set = function(_, p_u_63, p64, p_u_65, p_u_66) --[[ Name: do_datastore_set ]] --[[ Line: 162 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_5, (ref 3): v_u_14, (ref 4): v_u_4, (ref 5): v_u_7, (copy 6): f_run_datastore_request, (copy 7): f_trigger_datastore_lag_monkey, (copy 8): p_u_16 ]]
            local v_u_67 = v_u_15:get_env_datastore_prefix() .. p64
            v_u_5:spawn(function() --[[ Line: 130 ]]
                --[[ Upvalues: (copy 1): p_u_63, (ref 2): v_u_67, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): p_u_65, (copy 10): p_u_66, (ref 11): p_u_16 ]]
                local v68 = tick()
                local v_u_69, v70
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_69 = false
                    v70 = 1
                else
                    v_u_69 = false
                    v70 = 1
                end;
                while v_u_69 ~= true do
                    local _, v71 = pcall(function() --[[ Line: 136 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): p_u_63, (ref 8): v_u_67, (ref 9): p_u_65, (ref 10): v_u_69 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("set    ")))
                        end;
                        v_u_7:increment_datastore_set_count()
                        f_run_datastore_request(function() --[[ Line: 140 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): p_u_63, (ref 3): v_u_67, (ref 4): p_u_65 ]]
                            f_trigger_datastore_lag_monkey("set    ")
                            p_u_63:SetAsync(v_u_67, p_u_65)
                        end)
                        v_u_69 = true
                    end)
                    if v_u_69 ~= true then
                        if v70 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_set key(%s) failed(%s)", v_u_67, (tostring(v71)));
                        end;
                        wait(v70)
                        v70 = v70 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_set key(%s) wait(%d) failed(%s)", v_u_67, v70, (tostring(v71)))
                    end;
                end;
                if p_u_66 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 154 ]]
                        --[[ Upvalues: (ref 1): p_u_66, (ref 2): v_u_69 ]]
                        p_u_66(v_u_69, "")
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "set    ", p_u_63.Name, v_u_67, tick() - v68)
            end)
        end;
        local function _(p_u_72, p73, p_u_74, p_u_75) --[[ Name: do_datastore_update ]] --[[ Line: 164 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_5, (ref 3): v_u_14, (ref 4): v_u_4, (ref 5): v_u_7, (copy 6): f_run_datastore_request, (copy 7): f_trigger_datastore_lag_monkey, (copy 8): p_u_16 ]]
            local v_u_76 = v_u_15:get_env_datastore_prefix() .. p73
            v_u_5:spawn(function() --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): p_u_72, (ref 2): v_u_76, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): p_u_74, (copy 10): p_u_75, (ref 11): p_u_16 ]]
                local v77 = tick()
                local v_u_78, v79
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_78 = false
                    v79 = 1
                else
                    v_u_78 = false
                    v79 = 1
                end;
                while v_u_78 ~= true do
                    local _, v80 = pcall(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): p_u_72, (ref 8): v_u_76, (ref 9): p_u_74, (ref 10): v_u_78 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                        end;
                        v_u_7:increment_datastore_update_count()
                        f_run_datastore_request(function() --[[ Line: 178 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): p_u_72, (ref 3): v_u_76, (ref 4): p_u_74 ]]
                            f_trigger_datastore_lag_monkey("update ")
                            p_u_72:UpdateAsync(v_u_76, p_u_74)
                        end)
                        v_u_78 = true
                    end)
                    if v_u_78 ~= true then
                        if v79 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_76, (tostring(v80)));
                        end;
                        wait(v79)
                        v79 = v79 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_76, v79, (tostring(v80)))
                    end;
                end;
                if p_u_75 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                        --[[ Upvalues: (ref 1): p_u_75, (ref 2): v_u_78 ]]
                        p_u_75(v_u_78)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", p_u_72.Name, v_u_76, tick() - v77)
            end)
        end;
        v17.do_datastore_update = function(_, p_u_81, p82, p_u_83, p_u_84) --[[ Name: do_datastore_update ]] --[[ Line: 200 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_5, (ref 3): v_u_14, (ref 4): v_u_4, (ref 5): v_u_7, (copy 6): f_run_datastore_request, (copy 7): f_trigger_datastore_lag_monkey, (copy 8): p_u_16 ]]
            local v_u_85 = v_u_15:get_env_datastore_prefix() .. p82
            v_u_5:spawn(function() --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): p_u_81, (ref 2): v_u_85, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): p_u_83, (copy 10): p_u_84, (ref 11): p_u_16 ]]
                local v86 = tick()
                local v_u_87, v88
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_87 = false
                    v88 = 1
                else
                    v_u_87 = false
                    v88 = 1
                end;
                while v_u_87 ~= true do
                    local _, v89 = pcall(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): p_u_81, (ref 8): v_u_85, (ref 9): p_u_83, (ref 10): v_u_87 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                        end;
                        v_u_7:increment_datastore_update_count()
                        f_run_datastore_request(function() --[[ Line: 178 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): p_u_81, (ref 3): v_u_85, (ref 4): p_u_83 ]]
                            f_trigger_datastore_lag_monkey("update ")
                            p_u_81:UpdateAsync(v_u_85, p_u_83)
                        end)
                        v_u_87 = true
                    end)
                    if v_u_87 ~= true then
                        if v88 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_85, (tostring(v89)));
                        end;
                        wait(v88)
                        v88 = v88 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_85, v88, (tostring(v89)))
                    end;
                end;
                if p_u_84 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                        --[[ Upvalues: (ref 1): p_u_84, (ref 2): v_u_87 ]]
                        p_u_84(v_u_87)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", p_u_81.Name, v_u_85, tick() - v86)
            end)
        end;
        v17.do_datastore_delete = function(_, p_u_90, p91, p_u_92) --[[ Name: do_datastore_delete ]] --[[ Line: 202 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): v_u_5, (copy 3): f_run_datastore_request, (ref 4): v_u_4, (copy 5): p_u_16 ]]
            local v_u_93 = v_u_15:get_env_datastore_prefix() .. p91
            v_u_5:spawn(function() --[[ Line: 205 ]]
                --[[ Upvalues: (copy 1): p_u_90, (ref 2): v_u_93, (ref 3): v_u_5, (ref 4): f_run_datastore_request, (ref 5): v_u_4, (copy 6): p_u_92, (ref 7): p_u_16 ]]
                local v94 = tick()
                local v_u_95, v96
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_95 = false
                    v96 = 1
                else
                    v_u_95 = false
                    v96 = 1
                end;
                while v_u_95 ~= true do
                    local _, v97 = pcall(function() --[[ Line: 211 ]]
                        --[[ Upvalues: (ref 1): f_run_datastore_request, (ref 2): p_u_90, (ref 3): v_u_93, (ref 4): v_u_95 ]]
                        f_run_datastore_request(function() --[[ Line: 212 ]]
                            --[[ Upvalues: (ref 1): p_u_90, (ref 2): v_u_93 ]]
                            p_u_90:RemoveAsync(v_u_93)
                        end)
                        v_u_95 = true
                    end)
                    if v_u_95 ~= true then
                        if v96 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_delete key(%s) failed(%s)", v_u_93, (tostring(v97)));
                        end;
                        wait(v96)
                        v96 = v96 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_delete key(%s) wait(%d) failed(%s)", v_u_93, v96, (tostring(v97)))
                    end;
                end;
                if p_u_92 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 225 ]]
                        --[[ Upvalues: (ref 1): p_u_92, (ref 2): v_u_95 ]]
                        p_u_92(v_u_95)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "delete ", p_u_90.Name, v_u_93, tick() - v94)
            end)
        end;
        local v_u_98 = v_u_1:new()
        v17.update = function(_, p99) --[[ Name: update ]] --[[ Line: 235 ]]
            --[[ Upvalues: (ref 1): v_u_11, (copy 2): v_u_98 ]]
            v_u_11:update_mutex_list(v_u_98, p99)
        end;
        local v_u_100 = nil
        pcall(function() --[[ Line: 242 ]]
            --[[ Upvalues: (ref 1): v_u_100, (ref 2): s_DataStoreService_0 ]]
            v_u_100 = s_DataStoreService_0:GetDataStore("WebNPCVisit")
        end)
        local function _(p101) --[[ Name: get_webnpcvisit_key_for_playerid ]] --[[ Line: 245 ]]
            return string.format("webnpcvisit_table_playerid(%d)", p101);
        end;
        local function f_get_webnpcvisit_table(p102, p_u_103) --[[ Name: get_webnpcvisit_table ]] --[[ Line: 246 ]]
            --[[ Upvalues: (ref 1): v_u_100, (ref 2): v_u_2, (ref 3): v_u_15, (ref 4): v_u_5, (ref 5): v_u_14, (ref 6): v_u_4, (ref 7): v_u_7, (copy 8): f_run_datastore_request, (copy 9): f_trigger_datastore_lag_monkey, (copy 10): p_u_16 ]]
            if v_u_100 == nil then
                return p_u_103(false, {});
            end;
            v_u_2:is_int(p102)
            local v_u_104 = v_u_100
            local function v_u_107(p105, p106) --[[ Line: 251 ]]
                --[[ Upvalues: (copy 1): p_u_103, (ref 2): v_u_2 ]]
                if p106 == nil then
                    return p_u_103(p105, {});
                end;
                v_u_2:is_table(p106)
                return p_u_103(p105, p106);
            end;
            local v_u_108 = v_u_15:get_env_datastore_prefix() .. string.format("webnpcvisit_table_playerid(%d)", p102)
            local v_u_109 = nil
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): v_u_104, (ref 2): v_u_108, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_109, (copy 10): v_u_107, (ref 11): p_u_16 ]]
                local v110 = tick()
                local v_u_111, v_u_112, v113
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_111 = false
                    v_u_112 = nil
                    v113 = 1
                else
                    v_u_111 = false
                    v_u_112 = nil
                    v113 = 1
                end;
                while v_u_111 ~= true do
                    local _, v114 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_112, (ref 8): v_u_104, (ref 9): v_u_108, (ref 10): v_u_109, (ref 11): v_u_111 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_112, (ref 3): v_u_104, (ref 4): v_u_108, (ref 5): v_u_109 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_112 = v_u_104:GetAsync(v_u_108, v_u_109)
                        end)
                        v_u_111 = true
                    end)
                    if v_u_111 ~= true then
                        if v113 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_108, (tostring(v114)));
                        end;
                        wait(v113)
                        v113 = v113 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_108, v113, (tostring(v114)))
                    end;
                end;
                if v_u_107 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): v_u_107, (ref 2): v_u_111, (ref 3): v_u_112 ]]
                        v_u_107(v_u_111, v_u_112)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_104.Name, v_u_108, tick() - v110)
            end)
        end;
        v17.datastore_api_player_get_visited_webnpcs = function(_, p115, p_u_116, p_u_117) --[[ Name: datastore_api_player_get_visited_webnpcs ]] --[[ Line: 261 ]]
            --[[ Upvalues: (copy 1): f_get_webnpcvisit_table, (ref 2): v_u_3 ]]
            f_get_webnpcvisit_table(p115, function(p118, p119) --[[ Line: 262 ]]
                --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_116, (copy 3): p_u_117 ]]
                local v120 = v_u_3:new():add_set_from_table_list(p119)
                local v121 = {}
                for _, v122 in p_u_116:key_itr() do
                    if p118 then
                        v121[v122] = v120:contains(v122)
                    else
                        v121[v122] = true
                    end;
                end;
                p_u_117(v121)
            end)
        end;
        local v_u_123 = v_u_11:new():add_to_mutex_list(v_u_98)
        v17.datastore_api_player_set_webnpc_visited = function(_, p_u_124, p_u_125, p_u_126) --[[ Name: datastore_api_player_set_webnpc_visited ]] --[[ Line: 280 ]]
            --[[ Upvalues: (ref 1): v_u_100, (ref 2): v_u_11, (copy 3): v_u_123, (copy 4): f_get_webnpcvisit_table, (ref 5): v_u_3, (ref 6): v_u_1, (ref 7): v_u_15, (ref 8): v_u_5, (ref 9): v_u_14, (ref 10): v_u_4, (ref 11): v_u_7, (copy 12): f_run_datastore_request, (copy 13): f_trigger_datastore_lag_monkey, (copy 14): p_u_16 ]]
            if v_u_100 == nil then
                return p_u_126(false);
            end;
            v_u_11:critical_section(function() --[[ Line: 284 ]]
                --[[ Upvalues: (ref 1): v_u_123, (copy 2): p_u_124 ]]
                return v_u_123:test(p_u_124);
            end, function() --[[ Line: 286 ]]
                --[[ Upvalues: (ref 1): v_u_123, (copy 2): p_u_124 ]]
                v_u_123:retain(p_u_124)
            end, function() --[[ Line: 288 ]]
                --[[ Upvalues: (ref 1): v_u_123, (copy 2): p_u_124 ]]
                v_u_123:release(p_u_124)
            end, function(p127, p_u_128) --[[ Line: 290 ]]
                --[[ Upvalues: (copy 1): p_u_126, (ref 2): f_get_webnpcvisit_table, (copy 3): p_u_124, (ref 4): v_u_3, (copy 5): p_u_125, (ref 6): v_u_1, (ref 7): v_u_100, (ref 8): v_u_15, (ref 9): v_u_5, (ref 10): v_u_14, (ref 11): v_u_4, (ref 12): v_u_7, (ref 13): f_run_datastore_request, (ref 14): f_trigger_datastore_lag_monkey, (ref 15): p_u_16 ]]
                p127()
                local function f_response(p129) --[[ Name: response ]] --[[ Line: 293 ]]
                    --[[ Upvalues: (copy 1): p_u_128, (ref 2): p_u_126 ]]
                    p_u_128()
                    p_u_126(p129)
                end;
                f_get_webnpcvisit_table(p_u_124, function(_, p130) --[[ Line: 298 ]]
                    --[[ Upvalues: (ref 1): v_u_3, (ref 2): p_u_125, (copy 3): f_response, (ref 4): v_u_1, (ref 5): v_u_100, (ref 6): p_u_124, (copy 7): p_u_128, (ref 8): p_u_126, (ref 9): v_u_15, (ref 10): v_u_5, (ref 11): v_u_14, (ref 12): v_u_4, (ref 13): v_u_7, (ref 14): f_run_datastore_request, (ref 15): f_trigger_datastore_lag_monkey, (ref 16): p_u_16 ]]
                    if v_u_3:new():add_set_from_table_list(p130):contains(p_u_125) then
                        return f_response(false);
                    end;
                    local v131 = v_u_1:new()
                    v131:push_back_table_list(p130)
                    v131:push_back(p_u_125)
                    if v131:count() > 40 then
                        v131:pop_front()
                    end;
                    local v_u_132 = v_u_100
                    local v133 = string.format("webnpcvisit_table_playerid(%d)", p_u_124)
                    local l__table_0 = v131._table
                    local function v_u_135(p134) --[[ Line: 312 ]]
                        --[[ Upvalues: (ref 1): p_u_128, (ref 2): p_u_126 ]]
                        p_u_128()
                        p_u_126(p134)
                    end;
                    local v_u_136 = v_u_15:get_env_datastore_prefix() .. v133
                    v_u_5:spawn(function() --[[ Line: 130 ]]
                        --[[ Upvalues: (copy 1): v_u_132, (ref 2): v_u_136, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): l__table_0, (copy 10): v_u_135, (ref 11): p_u_16 ]]
                        local v137 = tick()
                        local v_u_138, v139
                        if v_u_5:is_dev_build() then
                            v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                            v_u_138 = false
                            v139 = 1
                        else
                            v_u_138 = false
                            v139 = 1
                        end;
                        while v_u_138 ~= true do
                            local _, v140 = pcall(function() --[[ Line: 136 ]]
                                --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_132, (ref 8): v_u_136, (ref 9): l__table_0, (ref 10): v_u_138 ]]
                                if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                                    v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("set    ")))
                                end;
                                v_u_7:increment_datastore_set_count()
                                f_run_datastore_request(function() --[[ Line: 140 ]]
                                    --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_132, (ref 3): v_u_136, (ref 4): l__table_0 ]]
                                    f_trigger_datastore_lag_monkey("set    ")
                                    v_u_132:SetAsync(v_u_136, l__table_0)
                                end)
                                v_u_138 = true
                            end)
                            if v_u_138 ~= true then
                                if v139 >= 64 then
                                    return v_u_4:errf("ServerDataStoreAPIManager do_datastore_set key(%s) failed(%s)", v_u_136, (tostring(v140)));
                                end;
                                wait(v139)
                                v139 = v139 * 2
                                v_u_4:warnf("ServerDataStoreAPIManager do_datastore_set key(%s) wait(%d) failed(%s)", v_u_136, v139, (tostring(v140)))
                            end;
                        end;
                        if v_u_135 then
                            p_u_16._post_fn:enqueue_function(function() --[[ Line: 154 ]]
                                --[[ Upvalues: (ref 1): v_u_135, (ref 2): v_u_138 ]]
                                v_u_135(v_u_138, "")
                            end)
                        end;
                        v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "set    ", v_u_132.Name, v_u_136, tick() - v137)
                    end)
                end)
            end)
        end;
        local v_u_141 = nil
        pcall(function() --[[ Line: 321 ]]
            --[[ Upvalues: (ref 1): v_u_141, (ref 2): s_DataStoreService_0 ]]
            v_u_141 = s_DataStoreService_0:GetDataStore("EventTrackQueuedClubSongDatastore")
        end)
        v17.datastore_api_increment_event_track_queued_club_song = function(_, p142) --[[ Name: datastore_api_increment_event_track_queued_club_song ]] --[[ Line: 324 ]]
            --[[ Upvalues: (ref 1): v_u_141, (ref 2): v_u_15, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (copy 7): f_run_datastore_request, (copy 8): f_trigger_datastore_lag_monkey, (copy 9): p_u_16 ]]
            local v_u_143 = v_u_141
            local function v_u_145(p144) --[[ Line: 325 ]]
                return (p144 == nil and 0 or p144) + 1;
            end;
            local v_u_146 = v_u_15:get_env_datastore_prefix() .. tostring(p142)
            local v_u_147 = nil
            v_u_5:spawn(function() --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): v_u_143, (ref 2): v_u_146, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_145, (copy 10): v_u_147, (ref 11): p_u_16 ]]
                local v148 = tick()
                local v_u_149, v150
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_149 = false
                    v150 = 1
                else
                    v_u_149 = false
                    v150 = 1
                end;
                while v_u_149 ~= true do
                    local _, v151 = pcall(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_143, (ref 8): v_u_146, (ref 9): v_u_145, (ref 10): v_u_149 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                        end;
                        v_u_7:increment_datastore_update_count()
                        f_run_datastore_request(function() --[[ Line: 178 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_143, (ref 3): v_u_146, (ref 4): v_u_145 ]]
                            f_trigger_datastore_lag_monkey("update ")
                            v_u_143:UpdateAsync(v_u_146, v_u_145)
                        end)
                        v_u_149 = true
                    end)
                    if v_u_149 ~= true then
                        if v150 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_146, (tostring(v151)));
                        end;
                        wait(v150)
                        v150 = v150 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_146, v150, (tostring(v151)))
                    end;
                end;
                if v_u_147 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                        --[[ Upvalues: (ref 1): v_u_147, (ref 2): v_u_149 ]]
                        v_u_147(v_u_149)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", v_u_143.Name, v_u_146, tick() - v148)
            end)
        end;
        local v_u_152 = nil
        pcall(function() --[[ Line: 332 ]]
            --[[ Upvalues: (ref 1): v_u_152, (ref 2): s_DataStoreService_0 ]]
            v_u_152 = s_DataStoreService_0:GetDataStore("EventTrackSongStartDatastore")
        end)
        v17.datastore_api_increment_song_start_count = function(_, p153, p_u_154) --[[ Name: datastore_api_increment_song_start_count ]] --[[ Line: 335 ]]
            --[[ Upvalues: (ref 1): v_u_152, (ref 2): v_u_15, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (copy 7): f_run_datastore_request, (copy 8): f_trigger_datastore_lag_monkey, (copy 9): p_u_16 ]]
            local v_u_155 = v_u_152
            local function v_u_157(p156) --[[ Line: 336 ]]
                --[[ Upvalues: (copy 1): p_u_154 ]]
                return (p156 == nil and 0 or p156) + p_u_154;
            end;
            local v_u_158 = v_u_15:get_env_datastore_prefix() .. tostring(p153)
            local v_u_159 = nil
            v_u_5:spawn(function() --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): v_u_155, (ref 2): v_u_158, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_157, (copy 10): v_u_159, (ref 11): p_u_16 ]]
                local v160 = tick()
                local v_u_161, v162
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_161 = false
                    v162 = 1
                else
                    v_u_161 = false
                    v162 = 1
                end;
                while v_u_161 ~= true do
                    local _, v163 = pcall(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_155, (ref 8): v_u_158, (ref 9): v_u_157, (ref 10): v_u_161 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                        end;
                        v_u_7:increment_datastore_update_count()
                        f_run_datastore_request(function() --[[ Line: 178 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_155, (ref 3): v_u_158, (ref 4): v_u_157 ]]
                            f_trigger_datastore_lag_monkey("update ")
                            v_u_155:UpdateAsync(v_u_158, v_u_157)
                        end)
                        v_u_161 = true
                    end)
                    if v_u_161 ~= true then
                        if v162 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_158, (tostring(v163)));
                        end;
                        wait(v162)
                        v162 = v162 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_158, v162, (tostring(v163)))
                    end;
                end;
                if v_u_159 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                        --[[ Upvalues: (ref 1): v_u_159, (ref 2): v_u_161 ]]
                        v_u_159(v_u_161)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", v_u_155.Name, v_u_158, tick() - v160)
            end)
        end;
        local v_u_164 = nil
        pcall(function() --[[ Line: 344 ]]
            --[[ Upvalues: (ref 1): v_u_164, (ref 2): s_DataStoreService_0 ]]
            v_u_164 = s_DataStoreService_0:GetDataStore("PromoCodes")
        end)
        local function _(p_u_165, p_u_166) --[[ Name: get_promocode_playerid_can_claim ]] --[[ Line: 347 ]]
            --[[ Upvalues: (ref 1): v_u_164, (ref 2): v_u_4, (ref 3): v_u_15, (ref 4): v_u_5, (ref 5): v_u_14, (ref 6): v_u_7, (copy 7): f_run_datastore_request, (copy 8): f_trigger_datastore_lag_monkey, (copy 9): p_u_16 ]]
            if v_u_164 == nil then
                return p_u_166(false, false);
            end;
            local v_u_167 = v_u_164
            local function v_u_170(p168, p169) --[[ Line: 349 ]]
                --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_165, (copy 3): p_u_166 ]]
                v_u_4:puts("get_promocode_playerid_can_claim(%s) do_datastore_get(%s,%s)", p_u_165, tostring(p168), (tostring(p169)))
                if p169 == true then
                    return p_u_166(p168, false);
                else
                    return p_u_166(p168, true);
                end;
            end;
            local v_u_171 = v_u_15:get_env_datastore_prefix() .. p_u_165
            local v_u_172 = nil
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): v_u_167, (ref 2): v_u_171, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_172, (copy 10): v_u_170, (ref 11): p_u_16 ]]
                local v173 = tick()
                local v_u_174, v_u_175, v176
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_174 = false
                    v_u_175 = nil
                    v176 = 1
                else
                    v_u_174 = false
                    v_u_175 = nil
                    v176 = 1
                end;
                while v_u_174 ~= true do
                    local _, v177 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_175, (ref 8): v_u_167, (ref 9): v_u_171, (ref 10): v_u_172, (ref 11): v_u_174 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_175, (ref 3): v_u_167, (ref 4): v_u_171, (ref 5): v_u_172 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_175 = v_u_167:GetAsync(v_u_171, v_u_172)
                        end)
                        v_u_174 = true
                    end)
                    if v_u_174 ~= true then
                        if v176 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_171, (tostring(v177)));
                        end;
                        wait(v176)
                        v176 = v176 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_171, v176, (tostring(v177)))
                    end;
                end;
                if v_u_170 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): v_u_170, (ref 2): v_u_174, (ref 3): v_u_175 ]]
                        v_u_170(v_u_174, v_u_175)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_167.Name, v_u_171, tick() - v173)
            end)
        end;
        local v_u_178 = v_u_11:new():add_to_mutex_list(v_u_98)
        v17.datastore_api_playerid_can_claim_promo_code = function(_, p_u_179, p_u_180, p_u_181) --[[ Name: datastore_api_playerid_can_claim_promo_code ]] --[[ Line: 360 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_16, (ref 3): v_u_164, (ref 4): v_u_11, (copy 5): v_u_178, (ref 6): v_u_4, (ref 7): v_u_15, (ref 8): v_u_14, (ref 9): v_u_7, (copy 10): f_run_datastore_request, (copy 11): f_trigger_datastore_lag_monkey ]]
            local function _(p182) --[[ Name: get_promocode_playerid_claim_count_key ]] --[[ Line: 361 ]]
                --[[ Upvalues: (ref 1): v_u_5 ]]
                if v_u_5:is_dev_build() then
                    return string.format("PD%s_cc", p182);
                else
                    return string.format("PC%s_cc", p182);
                end;
            end;
            local function _(p183) --[[ Name: get_promocode_playerid_claimed_key ]] --[[ Line: 368 ]]
                --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_179 ]]
                if v_u_5:is_dev_build() then
                    return string.format("PD%s_%d", p183, p_u_179);
                else
                    return string.format("PC%s_%d", p183, p_u_179);
                end;
            end;
            local v184 = p_u_180:get_code()
            local v_u_185
            if v_u_5:is_dev_build() then
                v_u_185 = string.format("PD%s_%d", v184, p_u_179)
            else
                v_u_185 = string.format("PC%s_%d", v184, p_u_179)
            end;
            local v_u_186 = p_u_16._player_blob_manager:get_cached_blob(p_u_179)
            if v_u_164 == nil or v_u_186 == nil then
                return p_u_181(false);
            end;
            v_u_11:critical_section(function() --[[ Line: 380 ]]
                --[[ Upvalues: (ref 1): v_u_178, (copy 2): p_u_179 ]]
                return v_u_178:test(p_u_179);
            end, function() --[[ Line: 382 ]]
                --[[ Upvalues: (ref 1): v_u_178, (copy 2): p_u_179 ]]
                v_u_178:retain(p_u_179)
            end, function() --[[ Line: 384 ]]
                --[[ Upvalues: (ref 1): v_u_178, (copy 2): p_u_179 ]]
                v_u_178:release(p_u_179)
            end, function(p187, p_u_188) --[[ Line: 386 ]]
                --[[ Upvalues: (copy 1): p_u_181, (copy 2): v_u_185, (ref 3): v_u_164, (copy 4): p_u_180, (ref 5): v_u_5, (ref 6): p_u_16, (copy 7): v_u_186, (ref 8): v_u_4, (copy 9): p_u_179, (ref 10): v_u_15, (ref 11): v_u_14, (ref 12): v_u_7, (ref 13): f_run_datastore_request, (ref 14): f_trigger_datastore_lag_monkey ]]
                p187()
                local function f_response(p189, p190, p191) --[[ Name: response ]] --[[ Line: 388 ]]
                    --[[ Upvalues: (copy 1): p_u_188, (ref 2): p_u_181 ]]
                    p_u_188()
                    p_u_181(p189, p190, p191)
                end;
                local v_u_192 = v_u_185
                local function v_u_221(p193, p194) --[[ Line: 393 ]]
                    --[[ Upvalues: (ref 1): v_u_164, (ref 2): p_u_180, (ref 3): v_u_5, (ref 4): p_u_16, (ref 5): v_u_186, (ref 6): v_u_185, (ref 7): v_u_4, (ref 8): p_u_179, (copy 9): f_response, (ref 10): v_u_15, (ref 11): v_u_14, (ref 12): v_u_7, (ref 13): f_run_datastore_request, (ref 14): f_trigger_datastore_lag_monkey, (copy 15): p_u_188, (ref 16): p_u_181 ]]
                    if p193 ~= true or p194 ~= true then
                        return f_response(false, "Already claimed.", 0);
                    end;
                    local v_u_195 = v_u_164
                    local v196 = p_u_180:get_code()
                    local v197
                    if v_u_5:is_dev_build() then
                        v197 = string.format("PD%s_cc", v196)
                    else
                        v197 = string.format("PC%s_cc", v196)
                    end;
                    local function v_u_214(p198) --[[ Line: 395 ]]
                        --[[ Upvalues: (ref 1): p_u_180, (ref 2): p_u_16, (ref 3): v_u_186, (ref 4): v_u_164, (ref 5): v_u_185, (ref 6): v_u_4, (ref 7): p_u_179, (ref 8): f_response, (ref 9): v_u_15, (ref 10): v_u_5, (ref 11): v_u_14, (ref 12): v_u_7, (ref 13): f_run_datastore_request, (ref 14): f_trigger_datastore_lag_monkey, (ref 15): p_u_188, (ref 16): p_u_181 ]]
                        local v_u_199 = p198 == nil and 0 or p198
                        local v_u_200 = false
                        local v_u_201 = nil
                        pcall(function() --[[ Line: 399 ]]
                            --[[ Upvalues: (ref 1): v_u_200, (ref 2): v_u_201, (ref 3): p_u_180, (ref 4): p_u_16, (ref 5): v_u_186, (ref 6): v_u_199 ]]
                            local v202, v203 = p_u_180:can_claim(p_u_16, v_u_186, v_u_199)
                            v_u_200 = v202
                            v_u_201 = v203
                        end)
                        local v204 = v_u_201 == nil and "Cannot claim code." or v_u_201
                        if not v_u_200 then
                            p_u_188()
                            p_u_181(false, v204, v_u_199)
                            return v_u_199;
                        end;
                        local v_u_205 = v_u_164
                        local function v_u_207(p206) --[[ Line: 404 ]]
                            --[[ Upvalues: (ref 1): v_u_4, (ref 2): p_u_179, (ref 3): p_u_180, (ref 4): v_u_199, (ref 5): f_response ]]
                            if p206 == true then
                                v_u_4:puts("datastore_api_playerid_can_claim_promo_code(%d,%s) claimed(%d)", p_u_179, p_u_180:get_code(), v_u_199)
                                return f_response(true, "", v_u_199);
                            else
                                v_u_4:warnf("datastore_api_playerid_can_claim_promo_code do_datastore_set failed")
                                return f_response(false, "Datastore Failed", v_u_199);
                            end;
                        end;
                        local v_u_208 = v_u_15:get_env_datastore_prefix() .. v_u_185
                        local v_u_209 = true
                        v_u_5:spawn(function() --[[ Line: 130 ]]
                            --[[ Upvalues: (copy 1): v_u_205, (ref 2): v_u_208, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_209, (copy 10): v_u_207, (ref 11): p_u_16 ]]
                            local v210 = tick()
                            local v_u_211, v212
                            if v_u_5:is_dev_build() then
                                v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                                v_u_211 = false
                                v212 = 1
                            else
                                v_u_211 = false
                                v212 = 1
                            end;
                            while v_u_211 ~= true do
                                local _, v213 = pcall(function() --[[ Line: 136 ]]
                                    --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_205, (ref 8): v_u_208, (ref 9): v_u_209, (ref 10): v_u_211 ]]
                                    if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                                        v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("set    ")))
                                    end;
                                    v_u_7:increment_datastore_set_count()
                                    f_run_datastore_request(function() --[[ Line: 140 ]]
                                        --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_205, (ref 3): v_u_208, (ref 4): v_u_209 ]]
                                        f_trigger_datastore_lag_monkey("set    ")
                                        v_u_205:SetAsync(v_u_208, v_u_209)
                                    end)
                                    v_u_211 = true
                                end)
                                if v_u_211 ~= true then
                                    if v212 >= 64 then
                                        return v_u_4:errf("ServerDataStoreAPIManager do_datastore_set key(%s) failed(%s)", v_u_208, (tostring(v213)));
                                    end;
                                    wait(v212)
                                    v212 = v212 * 2
                                    v_u_4:warnf("ServerDataStoreAPIManager do_datastore_set key(%s) wait(%d) failed(%s)", v_u_208, v212, (tostring(v213)))
                                end;
                            end;
                            if v_u_207 then
                                p_u_16._post_fn:enqueue_function(function() --[[ Line: 154 ]]
                                    --[[ Upvalues: (ref 1): v_u_207, (ref 2): v_u_211 ]]
                                    v_u_207(v_u_211, "")
                                end)
                            end;
                            v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "set    ", v_u_205.Name, v_u_208, tick() - v210)
                        end)
                        return v_u_199 + 1;
                    end;
                    local v_u_215 = v_u_15:get_env_datastore_prefix() .. v197
                    local v_u_216 = nil
                    v_u_5:spawn(function() --[[ Line: 168 ]]
                        --[[ Upvalues: (copy 1): v_u_195, (ref 2): v_u_215, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_214, (copy 10): v_u_216, (ref 11): p_u_16 ]]
                        local v217 = tick()
                        local v_u_218, v219
                        if v_u_5:is_dev_build() then
                            v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                            v_u_218 = false
                            v219 = 1
                        else
                            v_u_218 = false
                            v219 = 1
                        end;
                        while v_u_218 ~= true do
                            local _, v220 = pcall(function() --[[ Line: 174 ]]
                                --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_195, (ref 8): v_u_215, (ref 9): v_u_214, (ref 10): v_u_218 ]]
                                if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                                    v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                                end;
                                v_u_7:increment_datastore_update_count()
                                f_run_datastore_request(function() --[[ Line: 178 ]]
                                    --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_195, (ref 3): v_u_215, (ref 4): v_u_214 ]]
                                    f_trigger_datastore_lag_monkey("update ")
                                    v_u_195:UpdateAsync(v_u_215, v_u_214)
                                end)
                                v_u_218 = true
                            end)
                            if v_u_218 ~= true then
                                if v219 >= 64 then
                                    return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_215, (tostring(v220)));
                                end;
                                wait(v219)
                                v219 = v219 * 2
                                v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_215, v219, (tostring(v220)))
                            end;
                        end;
                        if v_u_216 then
                            p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                                --[[ Upvalues: (ref 1): v_u_216, (ref 2): v_u_218 ]]
                                v_u_216(v_u_218)
                            end)
                        end;
                        v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", v_u_195.Name, v_u_215, tick() - v217)
                    end)
                end;
                if v_u_164 == nil then
                    v_u_221(false, false)
                else
                    local v_u_222 = v_u_164
                    local function v_u_225(p223, p224) --[[ Line: 349 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_192, (copy 3): v_u_221 ]]
                        v_u_4:puts("get_promocode_playerid_can_claim(%s) do_datastore_get(%s,%s)", v_u_192, tostring(p223), (tostring(p224)))
                        if p224 == true then
                            return v_u_221(p223, false);
                        else
                            return v_u_221(p223, true);
                        end;
                    end;
                    local v_u_226 = v_u_15:get_env_datastore_prefix() .. v_u_192
                    local v_u_227 = nil
                    v_u_5:spawn(function() --[[ Line: 86 ]]
                        --[[ Upvalues: (copy 1): v_u_222, (ref 2): v_u_226, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_227, (copy 10): v_u_225, (ref 11): p_u_16 ]]
                        local v228 = tick()
                        local v_u_229, v_u_230, v231
                        if v_u_5:is_dev_build() then
                            v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                            v_u_229 = false
                            v_u_230 = nil
                            v231 = 1
                        else
                            v_u_229 = false
                            v_u_230 = nil
                            v231 = 1
                        end;
                        while v_u_229 ~= true do
                            local _, v232 = pcall(function() --[[ Line: 93 ]]
                                --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_230, (ref 8): v_u_222, (ref 9): v_u_226, (ref 10): v_u_227, (ref 11): v_u_229 ]]
                                if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                                    v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                                end;
                                v_u_7:increment_datastore_get_count()
                                f_run_datastore_request(function() --[[ Line: 97 ]]
                                    --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_230, (ref 3): v_u_222, (ref 4): v_u_226, (ref 5): v_u_227 ]]
                                    f_trigger_datastore_lag_monkey("get    ")
                                    v_u_230 = v_u_222:GetAsync(v_u_226, v_u_227)
                                end)
                                v_u_229 = true
                            end)
                            if v_u_229 ~= true then
                                if v231 >= 64 then
                                    return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_226, (tostring(v232)));
                                end;
                                wait(v231)
                                v231 = v231 * 2
                                v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_226, v231, (tostring(v232)))
                            end;
                        end;
                        if v_u_225 then
                            p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                                --[[ Upvalues: (ref 1): v_u_225, (ref 2): v_u_229, (ref 3): v_u_230 ]]
                                v_u_225(v_u_229, v_u_230)
                            end)
                        end;
                        v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_222.Name, v_u_226, tick() - v228)
                    end)
                end;
            end)
        end;
        local v_u_233 = nil
        local _, v_u_234 = pcall(function() --[[ Line: 429 ]]
            --[[ Upvalues: (ref 1): v_u_233, (ref 2): s_DataStoreService_0 ]]
            v_u_233 = s_DataStoreService_0:GetDataStore("FavoriteSongs")
        end)
        local function _(p235) --[[ Name: get_favorite_songs_key_for_playerid ]] --[[ Line: 432 ]]
            return string.format("favoritedata_playerid(%d)", p235);
        end;
        v17.get_favorite_songs_data = function(_, p_u_236, p_u_237) --[[ Name: get_favorite_songs_data ]] --[[ Line: 433 ]]
            --[[ Upvalues: (ref 1): v_u_233, (ref 2): v_u_6, (ref 3): v_u_2, (ref 4): v_u_15, (ref 5): v_u_5, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            if v_u_233 == nil then
                return p_u_237(false, v_u_6:new(p_u_236));
            end;
            v_u_2:is_int(p_u_236)
            local v_u_238 = v_u_233
            local function v_u_241(p239, p240) --[[ Line: 438 ]]
                --[[ Upvalues: (copy 1): p_u_237, (ref 2): v_u_6, (copy 3): p_u_236, (ref 4): v_u_2 ]]
                if p240 == nil then
                    return p_u_237(false, v_u_6:new(p_u_236));
                end;
                v_u_2:is_table(p240)
                return p_u_237(p239, v_u_6:from_table(p240));
            end;
            local v_u_242 = v_u_15:get_env_datastore_prefix() .. string.format("favoritedata_playerid(%d)", p_u_236)
            local v_u_243 = nil
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): v_u_238, (ref 2): v_u_242, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_243, (copy 10): v_u_241, (ref 11): p_u_16 ]]
                local v244 = tick()
                local v_u_245, v_u_246, v247
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_245 = false
                    v_u_246 = nil
                    v247 = 1
                else
                    v_u_245 = false
                    v_u_246 = nil
                    v247 = 1
                end;
                while v_u_245 ~= true do
                    local _, v248 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_246, (ref 8): v_u_238, (ref 9): v_u_242, (ref 10): v_u_243, (ref 11): v_u_245 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_246, (ref 3): v_u_238, (ref 4): v_u_242, (ref 5): v_u_243 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_246 = v_u_238:GetAsync(v_u_242, v_u_243)
                        end)
                        v_u_245 = true
                    end)
                    if v_u_245 ~= true then
                        if v247 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_242, (tostring(v248)));
                        end;
                        wait(v247)
                        v247 = v247 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_242, v247, (tostring(v248)))
                    end;
                end;
                if v_u_241 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): v_u_241, (ref 2): v_u_245, (ref 3): v_u_246 ]]
                        v_u_241(v_u_245, v_u_246)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_238.Name, v_u_242, tick() - v244)
            end)
        end;
        v17.datastore_api_player_set_favorite_songs = function(p249, p_u_250, p_u_251, p_u_252) --[[ Name: datastore_api_player_set_favorite_songs ]] --[[ Line: 448 ]]
            --[[ Upvalues: (ref 1): v_u_233, (copy 2): v_u_234, (ref 3): v_u_6, (ref 4): v_u_15, (ref 5): v_u_5, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            if v_u_233 == nil then
                return p_u_252(false, tostring(v_u_234), v_u_6:new(p_u_250));
            end;
            p249:get_favorite_songs_data(p_u_250, function(_, p_u_253) --[[ Line: 451 ]]
                --[[ Upvalues: (copy 1): p_u_251, (ref 2): v_u_6, (copy 3): p_u_252, (ref 4): v_u_233, (copy 5): p_u_250, (ref 6): v_u_15, (ref 7): v_u_5, (ref 8): v_u_14, (ref 9): v_u_4, (ref 10): v_u_7, (ref 11): f_run_datastore_request, (ref 12): f_trigger_datastore_lag_monkey, (ref 13): p_u_16 ]]
                if p_u_253:is_song_in_list(p_u_251) then
                    p_u_253:remove_song(p_u_251)
                else
                    if p_u_253:count() >= v_u_6:get_max_songs() then
                        return p_u_252(false, string.format("Cannot add more than (%d) songs to favorites list.", v_u_6:get_max_songs()), p_u_253);
                    end;
                    p_u_253:add_song(p_u_251)
                end;
                local v_u_254 = v_u_233
                local v255 = string.format("favoritedata_playerid(%d)", p_u_250)
                local v_u_256 = p_u_253:to_table()
                local function v_u_259(p257, p258) --[[ Line: 462 ]]
                    --[[ Upvalues: (ref 1): p_u_252, (copy 2): p_u_253 ]]
                    p_u_252(p257, p258, p_u_253)
                end;
                local v_u_260 = v_u_15:get_env_datastore_prefix() .. v255
                v_u_5:spawn(function() --[[ Line: 130 ]]
                    --[[ Upvalues: (copy 1): v_u_254, (ref 2): v_u_260, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_256, (copy 10): v_u_259, (ref 11): p_u_16 ]]
                    local v261 = tick()
                    local v_u_262, v263
                    if v_u_5:is_dev_build() then
                        v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                        v_u_262 = false
                        v263 = 1
                    else
                        v_u_262 = false
                        v263 = 1
                    end;
                    while v_u_262 ~= true do
                        local _, v264 = pcall(function() --[[ Line: 136 ]]
                            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_254, (ref 8): v_u_260, (ref 9): v_u_256, (ref 10): v_u_262 ]]
                            if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                                v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("set    ")))
                            end;
                            v_u_7:increment_datastore_set_count()
                            f_run_datastore_request(function() --[[ Line: 140 ]]
                                --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_254, (ref 3): v_u_260, (ref 4): v_u_256 ]]
                                f_trigger_datastore_lag_monkey("set    ")
                                v_u_254:SetAsync(v_u_260, v_u_256)
                            end)
                            v_u_262 = true
                        end)
                        if v_u_262 ~= true then
                            if v263 >= 64 then
                                return v_u_4:errf("ServerDataStoreAPIManager do_datastore_set key(%s) failed(%s)", v_u_260, (tostring(v264)));
                            end;
                            wait(v263)
                            v263 = v263 * 2
                            v_u_4:warnf("ServerDataStoreAPIManager do_datastore_set key(%s) wait(%d) failed(%s)", v_u_260, v263, (tostring(v264)))
                        end;
                    end;
                    if v_u_259 then
                        p_u_16._post_fn:enqueue_function(function() --[[ Line: 154 ]]
                            --[[ Upvalues: (ref 1): v_u_259, (ref 2): v_u_262 ]]
                            v_u_259(v_u_262, "")
                        end)
                    end;
                    v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "set    ", v_u_254.Name, v_u_260, tick() - v261)
                end)
            end)
        end;
        local v_u_265 = nil
        pcall(function() --[[ Line: 471 ]]
            --[[ Upvalues: (ref 1): v_u_265, (ref 2): s_DataStoreService_0 ]]
            v_u_265 = s_DataStoreService_0:GetDataStore("EventTrackPurchaseDatastore")
        end)
        v17.datastore_api_track_event_purchase = function(_, p_u_266, p_u_267, p_u_268) --[[ Name: datastore_api_track_event_purchase ]] --[[ Line: 474 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_265, (ref 3): v_u_15, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (copy 7): f_run_datastore_request, (copy 8): f_trigger_datastore_lag_monkey, (copy 9): p_u_16 ]]
            local function _() --[[ Name: get_datastore_key ]] --[[ Line: 475 ]]
                --[[ Upvalues: (copy 1): p_u_266, (copy 2): p_u_267, (copy 3): p_u_268, (ref 4): v_u_5 ]]
                local v269 = string.format("%s_%s_%s", tostring(p_u_266), tostring(p_u_267), (tostring(p_u_268)))
                if v_u_5:is_dev_build() then
                    v269 = "d_" .. v269
                end;
                return v269;
            end;
            local v_u_270 = v_u_265
            local v271 = string.format("%s_%s_%s", tostring(p_u_266), tostring(p_u_267), (tostring(p_u_268)))
            if v_u_5:is_dev_build() then
                v271 = "d_" .. v271
            end;
            local function v_u_273(p272) --[[ Line: 482 ]]
                return (p272 == nil and 0 or p272) + 1;
            end;
            local v_u_274 = v_u_15:get_env_datastore_prefix() .. v271
            local v_u_275 = nil
            v_u_5:spawn(function() --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): v_u_270, (ref 2): v_u_274, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_273, (copy 10): v_u_275, (ref 11): p_u_16 ]]
                local v276 = tick()
                local v_u_277, v278
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_277 = false
                    v278 = 1
                else
                    v_u_277 = false
                    v278 = 1
                end;
                while v_u_277 ~= true do
                    local _, v279 = pcall(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_270, (ref 8): v_u_274, (ref 9): v_u_273, (ref 10): v_u_277 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                        end;
                        v_u_7:increment_datastore_update_count()
                        f_run_datastore_request(function() --[[ Line: 178 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_270, (ref 3): v_u_274, (ref 4): v_u_273 ]]
                            f_trigger_datastore_lag_monkey("update ")
                            v_u_270:UpdateAsync(v_u_274, v_u_273)
                        end)
                        v_u_277 = true
                    end)
                    if v_u_277 ~= true then
                        if v278 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_274, (tostring(v279)));
                        end;
                        wait(v278)
                        v278 = v278 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_274, v278, (tostring(v279)))
                    end;
                end;
                if v_u_275 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                        --[[ Upvalues: (ref 1): v_u_275, (ref 2): v_u_277 ]]
                        v_u_275(v_u_277)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", v_u_270.Name, v_u_274, tick() - v276)
            end)
        end;
        local v_u_280 = nil
        pcall(function() --[[ Line: 493 ]]
            --[[ Upvalues: (ref 1): v_u_280, (ref 2): s_DataStoreService_0 ]]
            v_u_280 = s_DataStoreService_0:GetDataStore("VerifyClaimTeamLBDS")
        end)
        local function _(p281, p282) --[[ Name: verify_claim_team_leaderboard_datastore_key ]] --[[ Line: 496 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            if v_u_5:is_dev_build() then
                return string.format("dtlb_p%d_w%d", p281, p282);
            else
                return string.format("tlb_p%d_w%d", p281, p282);
            end;
        end;
        v17.datastore_api_get_team_leaderboard_can_claim = function(_, p283, p284, p_u_285) --[[ Name: datastore_api_get_team_leaderboard_can_claim ]] --[[ Line: 504 ]]
            --[[ Upvalues: (ref 1): v_u_280, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_15, (ref 5): v_u_14, (ref 6): v_u_7, (copy 7): f_run_datastore_request, (copy 8): f_trigger_datastore_lag_monkey, (copy 9): p_u_16 ]]
            local v_u_286 = v_u_280
            local v287
            if v_u_5:is_dev_build() then
                v287 = string.format("dtlb_p%d_w%d", p283, p284)
            else
                v287 = string.format("tlb_p%d_w%d", p283, p284)
            end;
            local function v_u_290(p288, p289) --[[ Line: 505 ]]
                --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_285 ]]
                v_u_4:puts("datastore_api_get_team_leaderboard_can_claim success(%s) datastore_value(%s)", tostring(p288), (tostring(p289)))
                if p288 and p289 ~= true then
                    p_u_285(true)
                else
                    p_u_285(false)
                end;
            end;
            local v_u_291 = v_u_15:get_env_datastore_prefix() .. v287
            local v_u_292 = nil
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): v_u_286, (ref 2): v_u_291, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_292, (copy 10): v_u_290, (ref 11): p_u_16 ]]
                local v293 = tick()
                local v_u_294, v_u_295, v296
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_294 = false
                    v_u_295 = nil
                    v296 = 1
                else
                    v_u_294 = false
                    v_u_295 = nil
                    v296 = 1
                end;
                while v_u_294 ~= true do
                    local _, v297 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_295, (ref 8): v_u_286, (ref 9): v_u_291, (ref 10): v_u_292, (ref 11): v_u_294 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_295, (ref 3): v_u_286, (ref 4): v_u_291, (ref 5): v_u_292 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_295 = v_u_286:GetAsync(v_u_291, v_u_292)
                        end)
                        v_u_294 = true
                    end)
                    if v_u_294 ~= true then
                        if v296 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_291, (tostring(v297)));
                        end;
                        wait(v296)
                        v296 = v296 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_291, v296, (tostring(v297)))
                    end;
                end;
                if v_u_290 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): v_u_290, (ref 2): v_u_294, (ref 3): v_u_295 ]]
                        v_u_290(v_u_294, v_u_295)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_286.Name, v_u_291, tick() - v293)
            end)
        end;
        v17.datastore_api_get_team_leaderboard_set_claimed = function(_, p298, p299, p_u_300) --[[ Name: datastore_api_get_team_leaderboard_set_claimed ]] --[[ Line: 515 ]]
            --[[ Upvalues: (ref 1): v_u_280, (ref 2): v_u_5, (ref 3): v_u_15, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (copy 7): f_run_datastore_request, (copy 8): f_trigger_datastore_lag_monkey, (copy 9): p_u_16 ]]
            local v_u_301 = v_u_280
            local v302
            if v_u_5:is_dev_build() then
                v302 = string.format("dtlb_p%d_w%d", p298, p299)
            else
                v302 = string.format("tlb_p%d_w%d", p298, p299)
            end;
            local function v_u_303() --[[ Line: 516 ]]
                --[[ Upvalues: (copy 1): p_u_300 ]]
                p_u_300()
            end;
            local v_u_304 = v_u_15:get_env_datastore_prefix() .. v302
            local v_u_305 = true
            v_u_5:spawn(function() --[[ Line: 130 ]]
                --[[ Upvalues: (copy 1): v_u_301, (ref 2): v_u_304, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_305, (copy 10): v_u_303, (ref 11): p_u_16 ]]
                local v306 = tick()
                local v_u_307, v308
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_307 = false
                    v308 = 1
                else
                    v_u_307 = false
                    v308 = 1
                end;
                while v_u_307 ~= true do
                    local _, v309 = pcall(function() --[[ Line: 136 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_301, (ref 8): v_u_304, (ref 9): v_u_305, (ref 10): v_u_307 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("set    ")))
                        end;
                        v_u_7:increment_datastore_set_count()
                        f_run_datastore_request(function() --[[ Line: 140 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_301, (ref 3): v_u_304, (ref 4): v_u_305 ]]
                            f_trigger_datastore_lag_monkey("set    ")
                            v_u_301:SetAsync(v_u_304, v_u_305)
                        end)
                        v_u_307 = true
                    end)
                    if v_u_307 ~= true then
                        if v308 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_set key(%s) failed(%s)", v_u_304, (tostring(v309)));
                        end;
                        wait(v308)
                        v308 = v308 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_set key(%s) wait(%d) failed(%s)", v_u_304, v308, (tostring(v309)))
                    end;
                end;
                if v_u_303 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 154 ]]
                        --[[ Upvalues: (ref 1): v_u_303, (ref 2): v_u_307 ]]
                        v_u_303(v_u_307, "")
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "set    ", v_u_301.Name, v_u_304, tick() - v306)
            end)
        end;
        local v_u_310 = nil
        pcall(function() --[[ Line: 527 ]]
            --[[ Upvalues: (ref 1): v_u_310, (ref 2): s_DataStoreService_0 ]]
            v_u_310 = s_DataStoreService_0:GetDataStore("VerifyClaimWeeklyLBDS")
        end)
        local function _(p311, p312) --[[ Name: verify_claim_weekly_leaderboard_datastore_key ]] --[[ Line: 530 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            if v_u_5:is_dev_build() then
                return string.format("dwlb_p%d_w%d", p311, p312);
            else
                return string.format("wlb_p%d_w%d", p311, p312);
            end;
        end;
        v17.datastore_api_get_weekly_leaderboard_can_claim = function(_, p313, p314, p_u_315) --[[ Name: datastore_api_get_weekly_leaderboard_can_claim ]] --[[ Line: 538 ]]
            --[[ Upvalues: (ref 1): v_u_310, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_15, (ref 5): v_u_14, (ref 6): v_u_7, (copy 7): f_run_datastore_request, (copy 8): f_trigger_datastore_lag_monkey, (copy 9): p_u_16 ]]
            local v_u_316 = v_u_310
            local v317
            if v_u_5:is_dev_build() then
                v317 = string.format("dwlb_p%d_w%d", p313, p314)
            else
                v317 = string.format("wlb_p%d_w%d", p313, p314)
            end;
            local function v_u_320(p318, p319) --[[ Line: 539 ]]
                --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_315 ]]
                v_u_4:puts("datastore_api_get_weekly_leaderboard_can_claim success(%s) datastore_value(%s)", tostring(p318), (tostring(p319)))
                if p318 and p319 ~= true then
                    p_u_315(true)
                else
                    p_u_315(false)
                end;
            end;
            local v_u_321 = v_u_15:get_env_datastore_prefix() .. v317
            local v_u_322 = nil
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): v_u_316, (ref 2): v_u_321, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_322, (copy 10): v_u_320, (ref 11): p_u_16 ]]
                local v323 = tick()
                local v_u_324, v_u_325, v326
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_324 = false
                    v_u_325 = nil
                    v326 = 1
                else
                    v_u_324 = false
                    v_u_325 = nil
                    v326 = 1
                end;
                while v_u_324 ~= true do
                    local _, v327 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_325, (ref 8): v_u_316, (ref 9): v_u_321, (ref 10): v_u_322, (ref 11): v_u_324 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_325, (ref 3): v_u_316, (ref 4): v_u_321, (ref 5): v_u_322 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_325 = v_u_316:GetAsync(v_u_321, v_u_322)
                        end)
                        v_u_324 = true
                    end)
                    if v_u_324 ~= true then
                        if v326 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_321, (tostring(v327)));
                        end;
                        wait(v326)
                        v326 = v326 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_321, v326, (tostring(v327)))
                    end;
                end;
                if v_u_320 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): v_u_320, (ref 2): v_u_324, (ref 3): v_u_325 ]]
                        v_u_320(v_u_324, v_u_325)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_316.Name, v_u_321, tick() - v323)
            end)
        end;
        v17.datastore_api_get_weekly_leaderboard_set_claimed = function(_, p328, p329, p_u_330) --[[ Name: datastore_api_get_weekly_leaderboard_set_claimed ]] --[[ Line: 549 ]]
            --[[ Upvalues: (ref 1): v_u_310, (ref 2): v_u_5, (ref 3): v_u_15, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (copy 7): f_run_datastore_request, (copy 8): f_trigger_datastore_lag_monkey, (copy 9): p_u_16 ]]
            local v_u_331 = v_u_310
            local v332
            if v_u_5:is_dev_build() then
                v332 = string.format("dwlb_p%d_w%d", p328, p329)
            else
                v332 = string.format("wlb_p%d_w%d", p328, p329)
            end;
            local function v_u_333() --[[ Line: 550 ]]
                --[[ Upvalues: (copy 1): p_u_330 ]]
                p_u_330()
            end;
            local v_u_334 = v_u_15:get_env_datastore_prefix() .. v332
            local v_u_335 = true
            v_u_5:spawn(function() --[[ Line: 130 ]]
                --[[ Upvalues: (copy 1): v_u_331, (ref 2): v_u_334, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_335, (copy 10): v_u_333, (ref 11): p_u_16 ]]
                local v336 = tick()
                local v_u_337, v338
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_337 = false
                    v338 = 1
                else
                    v_u_337 = false
                    v338 = 1
                end;
                while v_u_337 ~= true do
                    local _, v339 = pcall(function() --[[ Line: 136 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_331, (ref 8): v_u_334, (ref 9): v_u_335, (ref 10): v_u_337 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("set    ")))
                        end;
                        v_u_7:increment_datastore_set_count()
                        f_run_datastore_request(function() --[[ Line: 140 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_331, (ref 3): v_u_334, (ref 4): v_u_335 ]]
                            f_trigger_datastore_lag_monkey("set    ")
                            v_u_331:SetAsync(v_u_334, v_u_335)
                        end)
                        v_u_337 = true
                    end)
                    if v_u_337 ~= true then
                        if v338 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_set key(%s) failed(%s)", v_u_334, (tostring(v339)));
                        end;
                        wait(v338)
                        v338 = v338 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_set key(%s) wait(%d) failed(%s)", v_u_334, v338, (tostring(v339)))
                    end;
                end;
                if v_u_333 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 154 ]]
                        --[[ Upvalues: (ref 1): v_u_333, (ref 2): v_u_337 ]]
                        v_u_333(v_u_337, "")
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "set    ", v_u_331.Name, v_u_334, tick() - v336)
            end)
        end;
        local v_u_340 = nil
        pcall(function() --[[ Line: 559 ]]
            --[[ Upvalues: (ref 1): v_u_340, (ref 2): s_DataStoreService_0 ]]
            v_u_340 = s_DataStoreService_0:GetDataStore("LogClaimWeeklyLBDS")
        end)
        local function _(p341) --[[ Name: ds_key ]] --[[ Line: 562 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            if v_u_5:is_dev_build() then
                return string.format("dlcw_p%d", p341);
            else
                return string.format("lcw_p%d", p341);
            end;
        end;
        v17.log_claim_weekly_leaderboard = function(_, p342, p_u_343) --[[ Name: log_claim_weekly_leaderboard ]] --[[ Line: 569 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_340, (ref 3): v_u_1, (ref 4): v_u_15, (ref 5): v_u_14, (ref 6): v_u_4, (ref 7): v_u_7, (copy 8): f_run_datastore_request, (copy 9): f_trigger_datastore_lag_monkey, (copy 10): p_u_16 ]]
            local v344
            if v_u_5:is_dev_build() then
                v344 = string.format("dlcw_p%d", p342)
            else
                v344 = string.format("lcw_p%d", p342)
            end;
            local v_u_345 = v_u_340
            local function v_u_349(p346) --[[ Line: 571 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_343 ]]
                local v347 = v_u_1:new(p346 == nil and {} or p346)
                for _, v348 in p_u_343:key_itr() do
                    v347:push_back(v348)
                end;
                while v347:count() > 100 do
                    v347:pop_front()
                end;
                return v347:get_table();
            end;
            local v_u_350 = v_u_15:get_env_datastore_prefix() .. v344
            local v_u_351 = nil
            v_u_5:spawn(function() --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): v_u_345, (ref 2): v_u_350, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_349, (copy 10): v_u_351, (ref 11): p_u_16 ]]
                local v352 = tick()
                local v_u_353, v354
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_353 = false
                    v354 = 1
                else
                    v_u_353 = false
                    v354 = 1
                end;
                while v_u_353 ~= true do
                    local _, v355 = pcall(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_345, (ref 8): v_u_350, (ref 9): v_u_349, (ref 10): v_u_353 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                        end;
                        v_u_7:increment_datastore_update_count()
                        f_run_datastore_request(function() --[[ Line: 178 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_345, (ref 3): v_u_350, (ref 4): v_u_349 ]]
                            f_trigger_datastore_lag_monkey("update ")
                            v_u_345:UpdateAsync(v_u_350, v_u_349)
                        end)
                        v_u_353 = true
                    end)
                    if v_u_353 ~= true then
                        if v354 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_350, (tostring(v355)));
                        end;
                        wait(v354)
                        v354 = v354 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_350, v354, (tostring(v355)))
                    end;
                end;
                if v_u_351 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                        --[[ Upvalues: (ref 1): v_u_351, (ref 2): v_u_353 ]]
                        v_u_351(v_u_353)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", v_u_345.Name, v_u_350, tick() - v352)
            end)
        end;
        local v_u_356 = nil
        pcall(function() --[[ Line: 587 ]]
            --[[ Upvalues: (ref 1): v_u_356, (ref 2): s_DataStoreService_0 ]]
            v_u_356 = s_DataStoreService_0:GetDataStore("LogCollectionRegisterDS")
        end)
        v17.log_collection_register_for_playerid = function(_, p357, p_u_358) --[[ Name: log_collection_register_for_playerid ]] --[[ Line: 590 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_5, (ref 3): v_u_356, (ref 4): v_u_1, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_7, (copy 8): f_run_datastore_request, (copy 9): f_trigger_datastore_lag_monkey, (copy 10): p_u_16 ]]
            if typeof(p_u_358) ~= "table" then
                return v_u_4:warnf("ServerDataStoreAPIManager:log_collection_register_for_playerid(%d,%s) collection_register_data is not table", p357, (tostring(p_u_358)));
            end;
            local v359
            if v_u_5:is_dev_build() then
                v359 = string.format("d_creg(%d)", p357)
            else
                v359 = string.format("creg(%d)", p357)
            end;
            local v_u_360 = v_u_356
            local function v_u_363(p361) --[[ Line: 600 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_358 ]]
                local v362 = v_u_1:new((p361 == nil or typeof(p361) ~= "table") and {} or p361)
                v362:push_back(p_u_358)
                if v362:count() > 75 then
                    v362:pop_front()
                end;
                return v362:get_table();
            end;
            local v_u_364 = v_u_15:get_env_datastore_prefix() .. v359
            local v_u_365 = nil
            v_u_5:spawn(function() --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): v_u_360, (ref 2): v_u_364, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_363, (copy 10): v_u_365, (ref 11): p_u_16 ]]
                local v366 = tick()
                local v_u_367, v368
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_367 = false
                    v368 = 1
                else
                    v_u_367 = false
                    v368 = 1
                end;
                while v_u_367 ~= true do
                    local _, v369 = pcall(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_360, (ref 8): v_u_364, (ref 9): v_u_363, (ref 10): v_u_367 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                        end;
                        v_u_7:increment_datastore_update_count()
                        f_run_datastore_request(function() --[[ Line: 178 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_360, (ref 3): v_u_364, (ref 4): v_u_363 ]]
                            f_trigger_datastore_lag_monkey("update ")
                            v_u_360:UpdateAsync(v_u_364, v_u_363)
                        end)
                        v_u_367 = true
                    end)
                    if v_u_367 ~= true then
                        if v368 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_364, (tostring(v369)));
                        end;
                        wait(v368)
                        v368 = v368 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_364, v368, (tostring(v369)))
                    end;
                end;
                if v_u_365 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                        --[[ Upvalues: (ref 1): v_u_365, (ref 2): v_u_367 ]]
                        v_u_365(v_u_367)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", v_u_360.Name, v_u_364, tick() - v366)
            end)
        end;
        local v_u_370 = nil
        pcall(function() --[[ Line: 616 ]]
            --[[ Upvalues: (ref 1): v_u_370, (ref 2): s_DataStoreService_0 ]]
            v_u_370 = s_DataStoreService_0:GetDataStore("CollectionLeaderboardEntry")
        end)
        local function _() --[[ Name: get_global_collection_leaderboard_key ]] --[[ Line: 619 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            return v_u_5:is_dev_build() and "d_global_collection_leaderboard" or "global_collection_leaderboard";
        end;
        local v_u_371 = nil
        v17.write_collection_leaderboard_entry = function(_, p_u_372) --[[ Name: write_collection_leaderboard_entry ]] --[[ Line: 629 ]]
            --[[ Upvalues: (ref 1): v_u_371, (ref 2): v_u_9, (ref 3): v_u_370, (ref 4): v_u_5, (ref 5): v_u_8, (ref 6): v_u_1, (ref 7): v_u_15, (ref 8): v_u_14, (ref 9): v_u_4, (ref 10): v_u_7, (copy 11): f_run_datastore_request, (copy 12): f_trigger_datastore_lag_monkey, (copy 13): p_u_16 ]]
            local function f_check_should_write() --[[ Name: check_should_write ]] --[[ Line: 630 ]]
                --[[ Upvalues: (ref 1): v_u_371, (ref 2): v_u_9, (copy 3): p_u_372 ]]
                return v_u_371 == nil and true or ((v_u_371:count() == 0 or v_u_371:count() < v_u_9.COLLECTION_LEADERBOARD_ENTRY_COUNT) and true or v_u_371:get(v_u_371:count()):get_overall_point_amount() < p_u_372:get_overall_point_amount());
            end;
            if f_check_should_write() == true then
                local v_u_373 = v_u_370
                local function v_u_378(p374) --[[ Line: 639 ]]
                    --[[ Upvalues: (ref 1): v_u_371, (ref 2): v_u_8, (copy 3): f_check_should_write, (ref 4): v_u_1, (copy 5): p_u_372, (ref 6): v_u_9 ]]
                    v_u_371 = v_u_8.CollectionLeaderboardEntry:table_to_list(p374 == nil and {} or p374)
                    if f_check_should_write() == true then
                        v_u_1:remove_if(v_u_371, function(p375) --[[ Line: 645 ]]
                            --[[ Upvalues: (ref 1): p_u_372 ]]
                            return p375:get_player_id() == p_u_372:get_player_id();
                        end)
                        v_u_1:bininsert(v_u_371, p_u_372, function(p376, p377) --[[ Line: 649 ]]
                            return p376:get_overall_point_amount() > p377:get_overall_point_amount();
                        end)
                        if v_u_371:count() > v_u_9.COLLECTION_LEADERBOARD_ENTRY_COUNT then
                            v_u_371:pop_back()
                        end;
                        return v_u_8.CollectionLeaderboardEntry:list_to_table(v_u_371);
                    end;
                end;
                local v_u_379 = v_u_15:get_env_datastore_prefix() .. (v_u_5:is_dev_build() and "d_global_collection_leaderboard" or "global_collection_leaderboard")
                local v_u_380 = nil
                v_u_5:spawn(function() --[[ Line: 168 ]]
                    --[[ Upvalues: (copy 1): v_u_373, (ref 2): v_u_379, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_378, (copy 10): v_u_380, (ref 11): p_u_16 ]]
                    local v381 = tick()
                    local v_u_382, v383
                    if v_u_5:is_dev_build() then
                        v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                        v_u_382 = false
                        v383 = 1
                    else
                        v_u_382 = false
                        v383 = 1
                    end;
                    while v_u_382 ~= true do
                        local _, v384 = pcall(function() --[[ Line: 174 ]]
                            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_373, (ref 8): v_u_379, (ref 9): v_u_378, (ref 10): v_u_382 ]]
                            if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                                v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                            end;
                            v_u_7:increment_datastore_update_count()
                            f_run_datastore_request(function() --[[ Line: 178 ]]
                                --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_373, (ref 3): v_u_379, (ref 4): v_u_378 ]]
                                f_trigger_datastore_lag_monkey("update ")
                                v_u_373:UpdateAsync(v_u_379, v_u_378)
                            end)
                            v_u_382 = true
                        end)
                        if v_u_382 ~= true then
                            if v383 >= 64 then
                                return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_379, (tostring(v384)));
                            end;
                            wait(v383)
                            v383 = v383 * 2
                            v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_379, v383, (tostring(v384)))
                        end;
                    end;
                    if v_u_380 then
                        p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                            --[[ Upvalues: (ref 1): v_u_380, (ref 2): v_u_382 ]]
                            v_u_380(v_u_382)
                        end)
                    end;
                    v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", v_u_373.Name, v_u_379, tick() - v381)
                end)
            end;
        end;
        v17.get_collection_leaderboard_entries_list = function(_, p_u_385) --[[ Name: get_collection_leaderboard_entries_list ]] --[[ Line: 661 ]]
            --[[ Upvalues: (ref 1): v_u_371, (ref 2): v_u_370, (ref 3): v_u_5, (ref 4): v_u_8, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            if v_u_371 ~= nil then
                return p_u_385(v_u_371);
            end;
            local v_u_386 = v_u_370
            local function v_u_388(_, p387) --[[ Line: 663 ]]
                --[[ Upvalues: (ref 1): v_u_371, (ref 2): v_u_8, (copy 3): p_u_385 ]]
                v_u_371 = v_u_8.CollectionLeaderboardEntry:table_to_list(p387 == nil and {} or p387)
                return p_u_385(v_u_371);
            end;
            local v_u_389 = v_u_15:get_env_datastore_prefix() .. (v_u_5:is_dev_build() and "d_global_collection_leaderboard" or "global_collection_leaderboard")
            local v_u_390 = nil
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): v_u_386, (ref 2): v_u_389, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_390, (copy 10): v_u_388, (ref 11): p_u_16 ]]
                local v391 = tick()
                local v_u_392, v_u_393, v394
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_392 = false
                    v_u_393 = nil
                    v394 = 1
                else
                    v_u_392 = false
                    v_u_393 = nil
                    v394 = 1
                end;
                while v_u_392 ~= true do
                    local _, v395 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_393, (ref 8): v_u_386, (ref 9): v_u_389, (ref 10): v_u_390, (ref 11): v_u_392 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_393, (ref 3): v_u_386, (ref 4): v_u_389, (ref 5): v_u_390 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_393 = v_u_386:GetAsync(v_u_389, v_u_390)
                        end)
                        v_u_392 = true
                    end)
                    if v_u_392 ~= true then
                        if v394 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_389, (tostring(v395)));
                        end;
                        wait(v394)
                        v394 = v394 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_389, v394, (tostring(v395)))
                    end;
                end;
                if v_u_388 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): v_u_388, (ref 2): v_u_392, (ref 3): v_u_393 ]]
                        v_u_388(v_u_392, v_u_393)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_386.Name, v_u_389, tick() - v391)
            end)
        end;
        local v_u_396 = nil
        pcall(function() --[[ Line: 673 ]]
            --[[ Upvalues: (ref 1): v_u_396, (ref 2): s_DataStoreService_0 ]]
            v_u_396 = s_DataStoreService_0:GetDataStore("MissionLeaderboardDatastore")
        end)
        local function f_get_key_for_leaderboard_type_songkey_weekid(p397, p398, p399) --[[ Name: get_key_for_leaderboard_type_songkey_weekid ]] --[[ Line: 678 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_5 ]]
            if p397 == v_u_10.LeaderboardType.GearPower then
                if v_u_5:is_dev_build() then
                    return string.format("d_gear_power_mission_leaderboard_%d_%d", p398, p399);
                else
                    return string.format("gear_power_mission_leaderboard_%d_%d", p398, p399);
                end;
            elseif v_u_5:is_dev_build() then
                return string.format("d_total_score_mission_leaderboard_%d_%d", p398, p399);
            else
                return string.format("total_score_mission_leaderboard_%d_%d", p398, p399);
            end;
        end;
        local v_u_400 = v_u_3:new()
        v17.write_point_total_mission_leaderboard_entry = function(_, p401, p_u_402, p_u_403) --[[ Name: write_point_total_mission_leaderboard_entry ]] --[[ Line: 697 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_4, (ref 3): v_u_10, (copy 4): f_get_key_for_leaderboard_type_songkey_weekid, (copy 5): p_u_16, (ref 6): v_u_9, (ref 7): v_u_396, (copy 8): v_u_400, (ref 9): v_u_1, (ref 10): v_u_15, (ref 11): v_u_14, (ref 12): v_u_7, (copy 13): f_run_datastore_request, (copy 14): f_trigger_datastore_lag_monkey ]]
            if v_u_5:is_dev_build() then
                v_u_4:warnf("write_point_total_mission_leaderboard_entry(%d) %s", p401, v_u_5:table_to_string(p_u_402:to_table()))
            end;
            local l_TotalScore_0 = v_u_10.LeaderboardType.TotalScore
            local v_u_404 = f_get_key_for_leaderboard_type_songkey_weekid(l_TotalScore_0, p401, p_u_16._api:get_week_id())
            local function f_check_should_write(p405) --[[ Name: check_should_write ]] --[[ Line: 705 ]]
                --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_402 ]]
                return p405 == nil and true or ((p405:count() == 0 or p405:count() < v_u_9.MISSION_LEADERBOARD_ENTRY_COUNT) and true or p405:get(p405:count()):get_calculated_total_score() < p_u_402:get_calculated_total_score());
            end;
            local v_u_406 = v_u_396
            local function v_u_414(p407) --[[ Line: 711 ]]
                --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_400, (copy 3): v_u_404, (copy 4): f_check_should_write, (copy 5): p_u_402, (ref 6): v_u_1, (copy 7): p_u_403, (ref 8): v_u_5, (copy 9): l_TotalScore_0, (ref 10): v_u_4 ]]
                local v408 = v_u_10:table_to_list(p407 == nil and {} or p407)
                v_u_400:add(v_u_404, v408)
                if f_check_should_write() == true then
                    local v411 = v408:find(p_u_402, function(p409, p410) --[[ Line: 718 ]]
                        return p409:get_playerid_hash() == p410:get_playerid_hash();
                    end)
                    if v411 ~= -1 then
                        if v408:get(v411):get_calculated_total_score() >= p_u_402:get_calculated_total_score() then
                            return;
                        end;
                        v408:remove_at(v411)
                    end;
                    v_u_1:bininsert(v408, p_u_402, function(p412, p413) --[[ Line: 730 ]]
                        return p412:get_calculated_total_score() > p413:get_calculated_total_score();
                    end)
                    if v408:count() > 200 then
                        v408:pop_back()
                    end;
                    if p_u_403 ~= nil and v408:contains(p_u_402) then
                        p_u_403(string.format("Your match total score of %s has placed you %s on the weekly mission %s leaderboard!", v_u_5:comma_value(p_u_402:get_calculated_total_score()), v_u_5:num_placify((v408:find(p_u_402))), v_u_10.LeaderboardType:type_to_name(l_TotalScore_0)))
                    end;
                    if v_u_5:is_dev_build() then
                        v_u_4:warnf("write_point_total_mission_leaderboard_entry(TotalScore) update key(%s) write(%s)", v_u_404, v_u_5:table_to_string(v_u_10:list_to_table(v408)))
                    end;
                    return v_u_10:list_to_table(v408);
                end;
            end;
            local v_u_415 = v_u_15:get_env_datastore_prefix() .. v_u_404
            local v_u_416 = nil
            v_u_5:spawn(function() --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): v_u_406, (ref 2): v_u_415, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_414, (copy 10): v_u_416, (ref 11): p_u_16 ]]
                local v417 = tick()
                local v_u_418, v419
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_418 = false
                    v419 = 1
                else
                    v_u_418 = false
                    v419 = 1
                end;
                while v_u_418 ~= true do
                    local _, v420 = pcall(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_406, (ref 8): v_u_415, (ref 9): v_u_414, (ref 10): v_u_418 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                        end;
                        v_u_7:increment_datastore_update_count()
                        f_run_datastore_request(function() --[[ Line: 178 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_406, (ref 3): v_u_415, (ref 4): v_u_414 ]]
                            f_trigger_datastore_lag_monkey("update ")
                            v_u_406:UpdateAsync(v_u_415, v_u_414)
                        end)
                        v_u_418 = true
                    end)
                    if v_u_418 ~= true then
                        if v419 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_415, (tostring(v420)));
                        end;
                        wait(v419)
                        v419 = v419 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_415, v419, (tostring(v420)))
                    end;
                end;
                if v_u_416 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                        --[[ Upvalues: (ref 1): v_u_416, (ref 2): v_u_418 ]]
                        v_u_416(v_u_418)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", v_u_406.Name, v_u_415, tick() - v417)
            end)
            local l_GearPower_0 = v_u_10.LeaderboardType.GearPower
            local v_u_421 = f_get_key_for_leaderboard_type_songkey_weekid(l_GearPower_0, p401, p_u_16._api:get_week_id())
            local function f_check_should_write(p422) --[[ Name: check_should_write ]] --[[ Line: 762 ]]
                --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_402 ]]
                return p422 == nil and true or ((p422:count() == 0 or p422:count() < v_u_9.MISSION_LEADERBOARD_ENTRY_COUNT) and true or p422:get(p422:count()):get_calculated_total_gear_power() > p_u_402:get_calculated_total_gear_power());
            end;
            local v_u_423 = v_u_396
            local function v_u_431(p424) --[[ Line: 768 ]]
                --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_400, (copy 3): v_u_421, (copy 4): f_check_should_write, (copy 5): p_u_402, (ref 6): v_u_1, (copy 7): p_u_403, (ref 8): v_u_5, (copy 9): l_GearPower_0, (ref 10): v_u_4 ]]
                local v425 = v_u_10:table_to_list(p424 == nil and {} or p424)
                v_u_400:add(v_u_421, v425)
                if f_check_should_write() == true then
                    local v428 = v425:find(p_u_402, function(p426, p427) --[[ Line: 775 ]]
                        return p426:get_playerid_hash() == p427:get_playerid_hash();
                    end)
                    if v428 ~= -1 then
                        if v425:get(v428):get_calculated_total_gear_power() <= p_u_402:get_calculated_total_gear_power() then
                            return;
                        end;
                        v425:remove_at(v428)
                    end;
                    v_u_1:bininsert(v425, p_u_402, function(p429, p430) --[[ Line: 787 ]]
                        return p429:get_calculated_total_gear_power() < p430:get_calculated_total_gear_power();
                    end)
                    if v425:count() > 200 then
                        v425:pop_back()
                    end;
                    if p_u_403 ~= nil and v425:contains(p_u_402) then
                        p_u_403(string.format("Your match total gear power of %s has placed you %s on the weekly mission %s leaderboard!", v_u_5:comma_value(p_u_402:get_calculated_total_gear_power()), v_u_5:num_placify((v425:find(p_u_402))), v_u_10.LeaderboardType:type_to_name(l_GearPower_0)))
                    end;
                    if v_u_5:is_dev_build() then
                        v_u_4:warnf("write_point_total_mission_leaderboard_entry(GearPower) update key(%s) write(%s)", v_u_421, v_u_5:table_to_string(v_u_10:list_to_table(v425)))
                    end;
                    return v_u_10:list_to_table(v425);
                end;
            end;
            local v_u_432 = v_u_15:get_env_datastore_prefix() .. v_u_421
            local v_u_433 = nil
            v_u_5:spawn(function() --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): v_u_423, (ref 2): v_u_432, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_431, (copy 10): v_u_433, (ref 11): p_u_16 ]]
                local v434 = tick()
                local v_u_435, v436
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_435 = false
                    v436 = 1
                else
                    v_u_435 = false
                    v436 = 1
                end;
                while v_u_435 ~= true do
                    local _, v437 = pcall(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_423, (ref 8): v_u_432, (ref 9): v_u_431, (ref 10): v_u_435 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                        end;
                        v_u_7:increment_datastore_update_count()
                        f_run_datastore_request(function() --[[ Line: 178 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_423, (ref 3): v_u_432, (ref 4): v_u_431 ]]
                            f_trigger_datastore_lag_monkey("update ")
                            v_u_423:UpdateAsync(v_u_432, v_u_431)
                        end)
                        v_u_435 = true
                    end)
                    if v_u_435 ~= true then
                        if v436 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_432, (tostring(v437)));
                        end;
                        wait(v436)
                        v436 = v436 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_432, v436, (tostring(v437)))
                    end;
                end;
                if v_u_433 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                        --[[ Upvalues: (ref 1): v_u_433, (ref 2): v_u_435 ]]
                        v_u_433(v_u_435)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", v_u_423.Name, v_u_432, tick() - v434)
            end)
        end;
        v17.get_mission_leaderboard_entry_list_for_type_songkey_weekid = function(_, p438, p439, p440, p_u_441) --[[ Name: get_mission_leaderboard_entry_list_for_type_songkey_weekid ]] --[[ Line: 817 ]]
            --[[ Upvalues: (copy 1): f_get_key_for_leaderboard_type_songkey_weekid, (copy 2): v_u_400, (ref 3): v_u_396, (ref 4): v_u_10, (ref 5): v_u_15, (ref 6): v_u_5, (ref 7): v_u_14, (ref 8): v_u_4, (ref 9): v_u_7, (copy 10): f_run_datastore_request, (copy 11): f_trigger_datastore_lag_monkey, (copy 12): p_u_16 ]]
            local v_u_442 = f_get_key_for_leaderboard_type_songkey_weekid(p438, p439, p440)
            if v_u_400:contains(v_u_442) then
                return p_u_441(v_u_400:get(v_u_442));
            end;
            local v_u_443 = v_u_396
            local function v_u_446(_, p444) --[[ Line: 820 ]]
                --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_400, (copy 3): v_u_442, (copy 4): p_u_441 ]]
                local v445 = v_u_10:table_to_list(p444 == nil and {} or p444)
                v_u_400:add(v_u_442, v445)
                return p_u_441(v445);
            end;
            local v_u_447 = v_u_15:get_env_datastore_prefix() .. v_u_442
            local v_u_448 = nil
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): v_u_443, (ref 2): v_u_447, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_448, (copy 10): v_u_446, (ref 11): p_u_16 ]]
                local v449 = tick()
                local v_u_450, v_u_451, v452
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_450 = false
                    v_u_451 = nil
                    v452 = 1
                else
                    v_u_450 = false
                    v_u_451 = nil
                    v452 = 1
                end;
                while v_u_450 ~= true do
                    local _, v453 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_451, (ref 8): v_u_443, (ref 9): v_u_447, (ref 10): v_u_448, (ref 11): v_u_450 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_451, (ref 3): v_u_443, (ref 4): v_u_447, (ref 5): v_u_448 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_451 = v_u_443:GetAsync(v_u_447, v_u_448)
                        end)
                        v_u_450 = true
                    end)
                    if v_u_450 ~= true then
                        if v452 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_447, (tostring(v453)));
                        end;
                        wait(v452)
                        v452 = v452 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_447, v452, (tostring(v453)))
                    end;
                end;
                if v_u_446 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): v_u_446, (ref 2): v_u_450, (ref 3): v_u_451 ]]
                        v_u_446(v_u_450, v_u_451)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_443.Name, v_u_447, tick() - v449)
            end)
        end;
        local v_u_454 = v_u_11:new():add_to_mutex_list(v_u_98)
        local function _(p455, p456) --[[ Name: key_weekid_playerid_claimed ]] --[[ Line: 831 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            if v_u_5:is_dev_build() then
                return string.format("d_w%d_p%d_cl", p455, p456);
            else
                return string.format("w%d_p%d_cl", p455, p456);
            end;
        end;
        v17.do_mission_leaderboard_rewards_claimed_for_weekid_playerid = function(_, p457, p_u_458, p_u_459) --[[ Name: do_mission_leaderboard_rewards_claimed_for_weekid_playerid ]] --[[ Line: 835 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_11, (copy 3): v_u_454, (ref 4): v_u_2, (ref 5): v_u_396, (ref 6): v_u_4, (ref 7): v_u_15, (ref 8): v_u_14, (ref 9): v_u_7, (copy 10): f_run_datastore_request, (copy 11): f_trigger_datastore_lag_monkey, (copy 12): p_u_16 ]]
            local v_u_460
            if v_u_5:is_dev_build() then
                v_u_460 = string.format("d_w%d_p%d_cl", p457, p_u_458)
            else
                v_u_460 = string.format("w%d_p%d_cl", p457, p_u_458)
            end;
            v_u_11:critical_section(function() --[[ Line: 838 ]]
                --[[ Upvalues: (ref 1): v_u_454, (copy 2): p_u_458 ]]
                return v_u_454:test(p_u_458);
            end, function() --[[ Line: 840 ]]
                --[[ Upvalues: (ref 1): v_u_454, (copy 2): p_u_458 ]]
                v_u_454:retain(p_u_458)
            end, function() --[[ Line: 842 ]]
                --[[ Upvalues: (ref 1): v_u_454, (copy 2): p_u_458 ]]
                v_u_454:release(p_u_458)
            end, function(p461, p_u_462) --[[ Line: 844 ]]
                --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_459, (ref 3): v_u_396, (copy 4): v_u_460, (ref 5): v_u_4, (ref 6): v_u_15, (ref 7): v_u_5, (ref 8): v_u_14, (ref 9): v_u_7, (ref 10): f_run_datastore_request, (ref 11): f_trigger_datastore_lag_monkey, (ref 12): p_u_16 ]]
                p461()
                local function f_response(p463) --[[ Name: response ]] --[[ Line: 847 ]]
                    --[[ Upvalues: (copy 1): p_u_462, (ref 2): v_u_2, (ref 3): p_u_459 ]]
                    p_u_462()
                    v_u_2:is_bool(p463)
                    p_u_459(p463)
                end;
                local v_u_464 = v_u_396
                local function v_u_475(_, p465) --[[ Line: 853 ]]
                    --[[ Upvalues: (ref 1): v_u_396, (ref 2): v_u_460, (copy 3): f_response, (ref 4): v_u_4, (ref 5): v_u_15, (ref 6): v_u_5, (ref 7): v_u_14, (ref 8): v_u_7, (ref 9): f_run_datastore_request, (ref 10): f_trigger_datastore_lag_monkey, (ref 11): p_u_16 ]]
                    if p465 ~= nil then
                        return f_response(false);
                    end;
                    local v_u_466 = v_u_396
                    local function v_u_468(p467) --[[ Line: 855 ]]
                        --[[ Upvalues: (ref 1): f_response, (ref 2): v_u_4 ]]
                        if p467 == true then
                            return f_response(true);
                        end;
                        v_u_4:warnf("do_mission_leaderboard_rewards_claimed_for_weekid_playerid do_datastore_set failed")
                        return f_response(false);
                    end;
                    local v_u_469 = v_u_15:get_env_datastore_prefix() .. v_u_460
                    local v_u_470 = true
                    v_u_5:spawn(function() --[[ Line: 130 ]]
                        --[[ Upvalues: (copy 1): v_u_466, (ref 2): v_u_469, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_470, (copy 10): v_u_468, (ref 11): p_u_16 ]]
                        local v471 = tick()
                        local v_u_472, v473
                        if v_u_5:is_dev_build() then
                            v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                            v_u_472 = false
                            v473 = 1
                        else
                            v_u_472 = false
                            v473 = 1
                        end;
                        while v_u_472 ~= true do
                            local _, v474 = pcall(function() --[[ Line: 136 ]]
                                --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_466, (ref 8): v_u_469, (ref 9): v_u_470, (ref 10): v_u_472 ]]
                                if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                                    v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("set    ")))
                                end;
                                v_u_7:increment_datastore_set_count()
                                f_run_datastore_request(function() --[[ Line: 140 ]]
                                    --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_466, (ref 3): v_u_469, (ref 4): v_u_470 ]]
                                    f_trigger_datastore_lag_monkey("set    ")
                                    v_u_466:SetAsync(v_u_469, v_u_470)
                                end)
                                v_u_472 = true
                            end)
                            if v_u_472 ~= true then
                                if v473 >= 64 then
                                    return v_u_4:errf("ServerDataStoreAPIManager do_datastore_set key(%s) failed(%s)", v_u_469, (tostring(v474)));
                                end;
                                wait(v473)
                                v473 = v473 * 2
                                v_u_4:warnf("ServerDataStoreAPIManager do_datastore_set key(%s) wait(%d) failed(%s)", v_u_469, v473, (tostring(v474)))
                            end;
                        end;
                        if v_u_468 then
                            p_u_16._post_fn:enqueue_function(function() --[[ Line: 154 ]]
                                --[[ Upvalues: (ref 1): v_u_468, (ref 2): v_u_472 ]]
                                v_u_468(v_u_472, "")
                            end)
                        end;
                        v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "set    ", v_u_466.Name, v_u_469, tick() - v471)
                    end)
                end;
                local v_u_476 = v_u_15:get_env_datastore_prefix() .. v_u_460
                local v_u_477 = nil
                v_u_5:spawn(function() --[[ Line: 86 ]]
                    --[[ Upvalues: (copy 1): v_u_464, (ref 2): v_u_476, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_477, (copy 10): v_u_475, (ref 11): p_u_16 ]]
                    local v478 = tick()
                    local v_u_479, v_u_480, v481
                    if v_u_5:is_dev_build() then
                        v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                        v_u_479 = false
                        v_u_480 = nil
                        v481 = 1
                    else
                        v_u_479 = false
                        v_u_480 = nil
                        v481 = 1
                    end;
                    while v_u_479 ~= true do
                        local _, v482 = pcall(function() --[[ Line: 93 ]]
                            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_480, (ref 8): v_u_464, (ref 9): v_u_476, (ref 10): v_u_477, (ref 11): v_u_479 ]]
                            if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                                v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                            end;
                            v_u_7:increment_datastore_get_count()
                            f_run_datastore_request(function() --[[ Line: 97 ]]
                                --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_480, (ref 3): v_u_464, (ref 4): v_u_476, (ref 5): v_u_477 ]]
                                f_trigger_datastore_lag_monkey("get    ")
                                v_u_480 = v_u_464:GetAsync(v_u_476, v_u_477)
                            end)
                            v_u_479 = true
                        end)
                        if v_u_479 ~= true then
                            if v481 >= 64 then
                                return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_476, (tostring(v482)));
                            end;
                            wait(v481)
                            v481 = v481 * 2
                            v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_476, v481, (tostring(v482)))
                        end;
                    end;
                    if v_u_475 then
                        p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                            --[[ Upvalues: (ref 1): v_u_475, (ref 2): v_u_479, (ref 3): v_u_480 ]]
                            v_u_475(v_u_479, v_u_480)
                        end)
                    end;
                    v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_464.Name, v_u_476, tick() - v478)
                end)
            end)
        end;
        local v_u_483 = nil
        pcall(function() --[[ Line: 874 ]]
            --[[ Upvalues: (ref 1): v_u_483, (ref 2): s_DataStoreService_0 ]]
            v_u_483 = s_DataStoreService_0:GetDataStore("GuildActivityLog")
        end)
        local function _(p484) --[[ Name: key_guildid_activity_log ]] --[[ Line: 877 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            if v_u_5:is_dev_build() then
                return string.format("d_guildid_activity_log(%d)", p484);
            else
                return string.format("guildid_activity_log(%d)", p484);
            end;
        end;
        v17.write_guildid_activity_log_message = function(_, p485, p_u_486) --[[ Name: write_guildid_activity_log_message ]] --[[ Line: 881 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_483, (ref 3): v_u_5, (ref 4): v_u_12, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            v_u_2:is_int(p485)
            v_u_2:is_string(p_u_486:get_message_text())
            local v_u_487 = v_u_483
            local v488
            if v_u_5:is_dev_build() then
                v488 = string.format("d_guildid_activity_log(%d)", p485)
            else
                v488 = string.format("guildid_activity_log(%d)", p485)
            end;
            local function v_u_491(p489) --[[ Line: 884 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_486 ]]
                local v490 = v_u_12:table_to_list(p489 == nil and {} or p489)
                v490:push_front(p_u_486)
                if v490:count() > 100 then
                    v490:pop_back()
                end;
                return v_u_12:list_to_table(v490);
            end;
            local v_u_492 = v_u_15:get_env_datastore_prefix() .. v488
            local v_u_493 = nil
            v_u_5:spawn(function() --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): v_u_487, (ref 2): v_u_492, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_491, (copy 10): v_u_493, (ref 11): p_u_16 ]]
                local v494 = tick()
                local v_u_495, v496
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_495 = false
                    v496 = 1
                else
                    v_u_495 = false
                    v496 = 1
                end;
                while v_u_495 ~= true do
                    local _, v497 = pcall(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_487, (ref 8): v_u_492, (ref 9): v_u_491, (ref 10): v_u_495 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                        end;
                        v_u_7:increment_datastore_update_count()
                        f_run_datastore_request(function() --[[ Line: 178 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_487, (ref 3): v_u_492, (ref 4): v_u_491 ]]
                            f_trigger_datastore_lag_monkey("update ")
                            v_u_487:UpdateAsync(v_u_492, v_u_491)
                        end)
                        v_u_495 = true
                    end)
                    if v_u_495 ~= true then
                        if v496 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_492, (tostring(v497)));
                        end;
                        wait(v496)
                        v496 = v496 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_492, v496, (tostring(v497)))
                    end;
                end;
                if v_u_493 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                        --[[ Upvalues: (ref 1): v_u_493, (ref 2): v_u_495 ]]
                        v_u_493(v_u_495)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", v_u_487.Name, v_u_492, tick() - v494)
            end)
        end;
        v17.get_guildid_activity_log_messages = function(_, p498, p_u_499) --[[ Name: get_guildid_activity_log_messages ]] --[[ Line: 897 ]]
            --[[ Upvalues: (ref 1): v_u_483, (ref 2): v_u_5, (ref 3): v_u_12, (ref 4): v_u_1, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            local v_u_500 = v_u_483
            local v501
            if v_u_5:is_dev_build() then
                v501 = string.format("d_guildid_activity_log(%d)", p498)
            else
                v501 = string.format("guildid_activity_log(%d)", p498)
            end;
            local function v_u_504(p502, p503) --[[ Line: 898 ]]
                --[[ Upvalues: (copy 1): p_u_499, (ref 2): v_u_12, (ref 3): v_u_1 ]]
                if p502 and typeof(p503) == "table" then
                    p_u_499(v_u_12:table_to_list(p503))
                else
                    p_u_499(v_u_1:new())
                end;
            end;
            local v_u_505 = v_u_15:get_env_datastore_prefix() .. v501
            local v_u_506 = nil
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): v_u_500, (ref 2): v_u_505, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_506, (copy 10): v_u_504, (ref 11): p_u_16 ]]
                local v507 = tick()
                local v_u_508, v_u_509, v510
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_508 = false
                    v_u_509 = nil
                    v510 = 1
                else
                    v_u_508 = false
                    v_u_509 = nil
                    v510 = 1
                end;
                while v_u_508 ~= true do
                    local _, v511 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_509, (ref 8): v_u_500, (ref 9): v_u_505, (ref 10): v_u_506, (ref 11): v_u_508 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_509, (ref 3): v_u_500, (ref 4): v_u_505, (ref 5): v_u_506 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_509 = v_u_500:GetAsync(v_u_505, v_u_506)
                        end)
                        v_u_508 = true
                    end)
                    if v_u_508 ~= true then
                        if v510 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_505, (tostring(v511)));
                        end;
                        wait(v510)
                        v510 = v510 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_505, v510, (tostring(v511)))
                    end;
                end;
                if v_u_504 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): v_u_504, (ref 2): v_u_508, (ref 3): v_u_509 ]]
                        v_u_504(v_u_508, v_u_509)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_500.Name, v_u_505, tick() - v507)
            end)
        end;
        local v_u_512 = nil
        pcall(function() --[[ Line: 911 ]]
            --[[ Upvalues: (ref 1): v_u_512, (ref 2): s_DataStoreService_0 ]]
            v_u_512 = s_DataStoreService_0:GetDataStore("GuildMessageBoard")
        end)
        local function _(p513) --[[ Name: key_guildid_message_board ]] --[[ Line: 914 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            if v_u_5:is_dev_build() then
                return string.format("d_guildid_message_board(%d)", p513);
            else
                return string.format("guildid_message_board(%d)", p513);
            end;
        end;
        v17.write_guildid_message_board_message = function(_, p514, p_u_515, p_u_516) --[[ Name: write_guildid_message_board_message ]] --[[ Line: 918 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_512, (ref 3): v_u_5, (ref 4): v_u_12, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            v_u_2:is_int(p514)
            v_u_2:is_string(p_u_515:get_message_text())
            local v_u_517 = v_u_512
            local v518
            if v_u_5:is_dev_build() then
                v518 = string.format("d_guildid_message_board(%d)", p514)
            else
                v518 = string.format("guildid_message_board(%d)", p514)
            end;
            local function v_u_521(p519) --[[ Line: 921 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_515, (copy 3): p_u_516 ]]
                local v520 = v_u_12:table_to_list(p519 == nil and {} or p519)
                v520:push_front(p_u_515)
                if v520:count() > 100 then
                    v520:pop_back()
                end;
                if p_u_516 then
                    p_u_516(v520)
                end;
                return v_u_12:list_to_table(v520);
            end;
            local v_u_522 = v_u_15:get_env_datastore_prefix() .. v518
            local v_u_523 = nil
            v_u_5:spawn(function() --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): v_u_517, (ref 2): v_u_522, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_521, (copy 10): v_u_523, (ref 11): p_u_16 ]]
                local v524 = tick()
                local v_u_525, v526
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_525 = false
                    v526 = 1
                else
                    v_u_525 = false
                    v526 = 1
                end;
                while v_u_525 ~= true do
                    local _, v527 = pcall(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_517, (ref 8): v_u_522, (ref 9): v_u_521, (ref 10): v_u_525 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                        end;
                        v_u_7:increment_datastore_update_count()
                        f_run_datastore_request(function() --[[ Line: 178 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_517, (ref 3): v_u_522, (ref 4): v_u_521 ]]
                            f_trigger_datastore_lag_monkey("update ")
                            v_u_517:UpdateAsync(v_u_522, v_u_521)
                        end)
                        v_u_525 = true
                    end)
                    if v_u_525 ~= true then
                        if v526 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_522, (tostring(v527)));
                        end;
                        wait(v526)
                        v526 = v526 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_522, v526, (tostring(v527)))
                    end;
                end;
                if v_u_523 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                        --[[ Upvalues: (ref 1): v_u_523, (ref 2): v_u_525 ]]
                        v_u_523(v_u_525)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", v_u_517.Name, v_u_522, tick() - v524)
            end)
        end;
        v17.get_guildid_message_board_messages = function(_, p528, p_u_529) --[[ Name: get_guildid_message_board_messages ]] --[[ Line: 935 ]]
            --[[ Upvalues: (ref 1): v_u_512, (ref 2): v_u_5, (ref 3): v_u_12, (ref 4): v_u_1, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            local v_u_530 = v_u_512
            local v531
            if v_u_5:is_dev_build() then
                v531 = string.format("d_guildid_message_board(%d)", p528)
            else
                v531 = string.format("guildid_message_board(%d)", p528)
            end;
            local function v_u_534(p532, p533) --[[ Line: 936 ]]
                --[[ Upvalues: (copy 1): p_u_529, (ref 2): v_u_12, (ref 3): v_u_1 ]]
                if p532 and typeof(p533) == "table" then
                    p_u_529(v_u_12:table_to_list(p533))
                else
                    p_u_529(v_u_1:new())
                end;
            end;
            local v_u_535 = v_u_15:get_env_datastore_prefix() .. v531
            local v_u_536 = nil
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): v_u_530, (ref 2): v_u_535, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_536, (copy 10): v_u_534, (ref 11): p_u_16 ]]
                local v537 = tick()
                local v_u_538, v_u_539, v540
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_538 = false
                    v_u_539 = nil
                    v540 = 1
                else
                    v_u_538 = false
                    v_u_539 = nil
                    v540 = 1
                end;
                while v_u_538 ~= true do
                    local _, v541 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_539, (ref 8): v_u_530, (ref 9): v_u_535, (ref 10): v_u_536, (ref 11): v_u_538 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_539, (ref 3): v_u_530, (ref 4): v_u_535, (ref 5): v_u_536 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_539 = v_u_530:GetAsync(v_u_535, v_u_536)
                        end)
                        v_u_538 = true
                    end)
                    if v_u_538 ~= true then
                        if v540 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_535, (tostring(v541)));
                        end;
                        wait(v540)
                        v540 = v540 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_535, v540, (tostring(v541)))
                    end;
                end;
                if v_u_534 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): v_u_534, (ref 2): v_u_538, (ref 3): v_u_539 ]]
                        v_u_534(v_u_538, v_u_539)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_530.Name, v_u_535, tick() - v537)
            end)
        end;
        local v_u_542 = nil
        pcall(function() --[[ Line: 949 ]]
            --[[ Upvalues: (ref 1): v_u_542, (ref 2): s_DataStoreService_0 ]]
            v_u_542 = s_DataStoreService_0:GetDataStore("WebNPCMessageBoard")
        end)
        local function _(p543) --[[ Name: key_webnpcid_message_board ]] --[[ Line: 952 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            if v_u_5:is_dev_build() then
                return string.format("d_webnpcid_message_board(%d)", p543);
            else
                return string.format("webnpcid_message_board(%d)", p543);
            end;
        end;
        v17.write_webnpcid_message = function(_, p544, p_u_545, p_u_546) --[[ Name: write_webnpcid_message ]] --[[ Line: 956 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_542, (ref 3): v_u_5, (ref 4): v_u_12, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            v_u_2:is_int(p544)
            v_u_2:is_string(p_u_545:get_message_text())
            local v_u_547 = v_u_542
            local v548
            if v_u_5:is_dev_build() then
                v548 = string.format("d_webnpcid_message_board(%d)", p544)
            else
                v548 = string.format("webnpcid_message_board(%d)", p544)
            end;
            local function v_u_551(p549) --[[ Line: 959 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_545, (copy 3): p_u_546 ]]
                local v550 = v_u_12:table_to_list(p549 == nil and {} or p549)
                v550:push_front(p_u_545)
                if v550:count() > 100 then
                    v550:pop_back()
                end;
                if p_u_546 then
                    p_u_546(v550)
                end;
                return v_u_12:list_to_table(v550);
            end;
            local v_u_552 = v_u_15:get_env_datastore_prefix() .. v548
            local v_u_553 = nil
            v_u_5:spawn(function() --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): v_u_547, (ref 2): v_u_552, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_551, (copy 10): v_u_553, (ref 11): p_u_16 ]]
                local v554 = tick()
                local v_u_555, v556
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_555 = false
                    v556 = 1
                else
                    v_u_555 = false
                    v556 = 1
                end;
                while v_u_555 ~= true do
                    local _, v557 = pcall(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_547, (ref 8): v_u_552, (ref 9): v_u_551, (ref 10): v_u_555 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                        end;
                        v_u_7:increment_datastore_update_count()
                        f_run_datastore_request(function() --[[ Line: 178 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_547, (ref 3): v_u_552, (ref 4): v_u_551 ]]
                            f_trigger_datastore_lag_monkey("update ")
                            v_u_547:UpdateAsync(v_u_552, v_u_551)
                        end)
                        v_u_555 = true
                    end)
                    if v_u_555 ~= true then
                        if v556 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_552, (tostring(v557)));
                        end;
                        wait(v556)
                        v556 = v556 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_552, v556, (tostring(v557)))
                    end;
                end;
                if v_u_553 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                        --[[ Upvalues: (ref 1): v_u_553, (ref 2): v_u_555 ]]
                        v_u_553(v_u_555)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", v_u_547.Name, v_u_552, tick() - v554)
            end)
        end;
        v17.get_webnpcid_messages = function(_, p558, p_u_559) --[[ Name: get_webnpcid_messages ]] --[[ Line: 973 ]]
            --[[ Upvalues: (ref 1): v_u_542, (ref 2): v_u_5, (ref 3): v_u_12, (ref 4): v_u_1, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            local v_u_560 = v_u_542
            local v561
            if v_u_5:is_dev_build() then
                v561 = string.format("d_webnpcid_message_board(%d)", p558)
            else
                v561 = string.format("webnpcid_message_board(%d)", p558)
            end;
            local function v_u_564(p562, p563) --[[ Line: 974 ]]
                --[[ Upvalues: (copy 1): p_u_559, (ref 2): v_u_12, (ref 3): v_u_1 ]]
                if p562 and typeof(p563) == "table" then
                    p_u_559(v_u_12:table_to_list(p563))
                else
                    p_u_559(v_u_1:new())
                end;
            end;
            local v_u_565 = v_u_15:get_env_datastore_prefix() .. v561
            local v_u_566 = nil
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): v_u_560, (ref 2): v_u_565, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_566, (copy 10): v_u_564, (ref 11): p_u_16 ]]
                local v567 = tick()
                local v_u_568, v_u_569, v570
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_568 = false
                    v_u_569 = nil
                    v570 = 1
                else
                    v_u_568 = false
                    v_u_569 = nil
                    v570 = 1
                end;
                while v_u_568 ~= true do
                    local _, v571 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_569, (ref 8): v_u_560, (ref 9): v_u_565, (ref 10): v_u_566, (ref 11): v_u_568 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_569, (ref 3): v_u_560, (ref 4): v_u_565, (ref 5): v_u_566 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_569 = v_u_560:GetAsync(v_u_565, v_u_566)
                        end)
                        v_u_568 = true
                    end)
                    if v_u_568 ~= true then
                        if v570 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_565, (tostring(v571)));
                        end;
                        wait(v570)
                        v570 = v570 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_565, v570, (tostring(v571)))
                    end;
                end;
                if v_u_564 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): v_u_564, (ref 2): v_u_568, (ref 3): v_u_569 ]]
                        v_u_564(v_u_568, v_u_569)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_560.Name, v_u_565, tick() - v567)
            end)
        end;
        local v_u_572 = nil
        pcall(function() --[[ Line: 987 ]]
            --[[ Upvalues: (ref 1): v_u_572, (ref 2): s_DataStoreService_0 ]]
            v_u_572 = s_DataStoreService_0:GetDataStore("PlayerLikedWebNPCIDs")
        end)
        local function _(p573) --[[ Name: key_playerid_liked_web_npc_ids ]] --[[ Line: 990 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            if v_u_5:is_dev_build() then
                return string.format("d_playerid_liked_web_npc_ids(%d)", p573);
            else
                return string.format("playerid_liked_web_npc_ids(%d)", p573);
            end;
        end;
        v17.write_playerid_liked_web_npc_id = function(_, p574, p_u_575, p_u_576) --[[ Name: write_playerid_liked_web_npc_id ]] --[[ Line: 994 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_572, (ref 3): v_u_5, (ref 4): v_u_1, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            v_u_2:is_int(p574)
            v_u_2:is_int(p_u_575)
            local v_u_577 = v_u_572
            local v578
            if v_u_5:is_dev_build() then
                v578 = string.format("d_playerid_liked_web_npc_ids(%d)", p574)
            else
                v578 = string.format("playerid_liked_web_npc_ids(%d)", p574)
            end;
            local function v_u_581(p579) --[[ Line: 997 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_575, (copy 3): p_u_576 ]]
                local v580 = v_u_1:new(p579 == nil and {} or p579)
                if v580:contains(p_u_575) ~= true then
                    v580:push_front(p_u_575)
                end;
                if v580:count() > 512 then
                    v580:pop_back()
                end;
                if p_u_576 then
                    p_u_576(v580)
                end;
                return v580._table;
            end;
            local v_u_582 = v_u_15:get_env_datastore_prefix() .. v578
            local v_u_583 = nil
            v_u_5:spawn(function() --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): v_u_577, (ref 2): v_u_582, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_581, (copy 10): v_u_583, (ref 11): p_u_16 ]]
                local v584 = tick()
                local v_u_585, v586
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_585 = false
                    v586 = 1
                else
                    v_u_585 = false
                    v586 = 1
                end;
                while v_u_585 ~= true do
                    local _, v587 = pcall(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_577, (ref 8): v_u_582, (ref 9): v_u_581, (ref 10): v_u_585 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                        end;
                        v_u_7:increment_datastore_update_count()
                        f_run_datastore_request(function() --[[ Line: 178 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_577, (ref 3): v_u_582, (ref 4): v_u_581 ]]
                            f_trigger_datastore_lag_monkey("update ")
                            v_u_577:UpdateAsync(v_u_582, v_u_581)
                        end)
                        v_u_585 = true
                    end)
                    if v_u_585 ~= true then
                        if v586 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_582, (tostring(v587)));
                        end;
                        wait(v586)
                        v586 = v586 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_582, v586, (tostring(v587)))
                    end;
                end;
                if v_u_583 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                        --[[ Upvalues: (ref 1): v_u_583, (ref 2): v_u_585 ]]
                        v_u_583(v_u_585)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", v_u_577.Name, v_u_582, tick() - v584)
            end)
        end;
        v17.get_playerid_liked_web_npc_ids_set = function(_, p588, p_u_589) --[[ Name: get_playerid_liked_web_npc_ids_set ]] --[[ Line: 1013 ]]
            --[[ Upvalues: (ref 1): v_u_572, (ref 2): v_u_5, (ref 3): v_u_1, (ref 4): v_u_3, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            local v_u_590 = v_u_572
            local v591
            if v_u_5:is_dev_build() then
                v591 = string.format("d_playerid_liked_web_npc_ids(%d)", p588)
            else
                v591 = string.format("playerid_liked_web_npc_ids(%d)", p588)
            end;
            local function v_u_595(p592, p593) --[[ Line: 1014 ]]
                --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_589, (ref 3): v_u_3 ]]
                local v594 = v_u_1:new()
                if p592 and typeof(p593) == "table" then
                    v594 = v_u_1:new(p593)
                end;
                p_u_589(v_u_3:new():add_set_from_table_list(v594:get_table()))
            end;
            local v_u_596 = v_u_15:get_env_datastore_prefix() .. v591
            local v_u_597 = nil
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): v_u_590, (ref 2): v_u_596, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_597, (copy 10): v_u_595, (ref 11): p_u_16 ]]
                local v598 = tick()
                local v_u_599, v_u_600, v601
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_599 = false
                    v_u_600 = nil
                    v601 = 1
                else
                    v_u_599 = false
                    v_u_600 = nil
                    v601 = 1
                end;
                while v_u_599 ~= true do
                    local _, v602 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_600, (ref 8): v_u_590, (ref 9): v_u_596, (ref 10): v_u_597, (ref 11): v_u_599 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_600, (ref 3): v_u_590, (ref 4): v_u_596, (ref 5): v_u_597 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_600 = v_u_590:GetAsync(v_u_596, v_u_597)
                        end)
                        v_u_599 = true
                    end)
                    if v_u_599 ~= true then
                        if v601 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_596, (tostring(v602)));
                        end;
                        wait(v601)
                        v601 = v601 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_596, v601, (tostring(v602)))
                    end;
                end;
                if v_u_595 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): v_u_595, (ref 2): v_u_599, (ref 3): v_u_600 ]]
                        v_u_595(v_u_599, v_u_600)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_590.Name, v_u_596, tick() - v598)
            end)
        end;
        local v_u_603 = nil
        pcall(function() --[[ Line: 1026 ]]
            --[[ Upvalues: (ref 1): v_u_603, (ref 2): s_DataStoreService_0 ]]
            v_u_603 = s_DataStoreService_0:GetDataStore("PlayerRecentWebNPCs")
        end)
        local function _(p604) --[[ Name: key_playerid_recent_web_npcs ]] --[[ Line: 1029 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            if v_u_5:is_dev_build() then
                return string.format("d_playerid_recent_web_npcs(%d)", p604);
            else
                return string.format("playerid_recent_web_npcs(%d)", p604);
            end;
        end;
        v17.write_playerid_recent_web_npcs_list = function(_, p605, p606, p_u_607) --[[ Name: write_playerid_recent_web_npcs_list ]] --[[ Line: 1033 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_1, (ref 3): v_u_603, (ref 4): v_u_5, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            v_u_2:is_int(p605)
            v_u_2:is_function(p606.key_itr)
            local v608 = v_u_1:new()
            for _, v609 in p606:key_itr() do
                v_u_2:is_function(v609.get_webnpcid)
                v608:push_back(v609:to_table())
            end;
            local v_u_610 = v608:get_table()
            local v_u_611 = v_u_603
            local v612
            if v_u_5:is_dev_build() then
                v612 = string.format("d_playerid_recent_web_npcs(%d)", p605)
            else
                v612 = string.format("playerid_recent_web_npcs(%d)", p605)
            end;
            local function v_u_614(p613) --[[ Line: 1044 ]]
                --[[ Upvalues: (copy 1): p_u_607 ]]
                if p_u_607 then
                    p_u_607(p613)
                end;
            end;
            local v_u_615 = v_u_15:get_env_datastore_prefix() .. v612
            v_u_5:spawn(function() --[[ Line: 130 ]]
                --[[ Upvalues: (copy 1): v_u_611, (ref 2): v_u_615, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_610, (copy 10): v_u_614, (ref 11): p_u_16 ]]
                local v616 = tick()
                local v_u_617, v618
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_617 = false
                    v618 = 1
                else
                    v_u_617 = false
                    v618 = 1
                end;
                while v_u_617 ~= true do
                    local _, v619 = pcall(function() --[[ Line: 136 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_611, (ref 8): v_u_615, (ref 9): v_u_610, (ref 10): v_u_617 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("set    ")))
                        end;
                        v_u_7:increment_datastore_set_count()
                        f_run_datastore_request(function() --[[ Line: 140 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_611, (ref 3): v_u_615, (ref 4): v_u_610 ]]
                            f_trigger_datastore_lag_monkey("set    ")
                            v_u_611:SetAsync(v_u_615, v_u_610)
                        end)
                        v_u_617 = true
                    end)
                    if v_u_617 ~= true then
                        if v618 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_set key(%s) failed(%s)", v_u_615, (tostring(v619)));
                        end;
                        wait(v618)
                        v618 = v618 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_set key(%s) wait(%d) failed(%s)", v_u_615, v618, (tostring(v619)))
                    end;
                end;
                if v_u_614 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 154 ]]
                        --[[ Upvalues: (ref 1): v_u_614, (ref 2): v_u_617 ]]
                        v_u_614(v_u_617, "")
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "set    ", v_u_611.Name, v_u_615, tick() - v616)
            end)
        end;
        v17.get_playerid_recent_web_npcs_list = function(_, p620, p_u_621) --[[ Name: get_playerid_recent_web_npcs_list ]] --[[ Line: 1048 ]]
            --[[ Upvalues: (ref 1): v_u_603, (ref 2): v_u_5, (ref 3): v_u_1, (ref 4): v_u_13, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            local v_u_622 = v_u_603
            local v623
            if v_u_5:is_dev_build() then
                v623 = string.format("d_playerid_recent_web_npcs(%d)", p620)
            else
                v623 = string.format("playerid_recent_web_npcs(%d)", p620)
            end;
            local function v_u_628(p624, p625) --[[ Line: 1049 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_13, (copy 3): p_u_621 ]]
                local v626 = v_u_1:new()
                if p624 and typeof(p625) == "table" then
                    for _, v627 in v_u_1:new(p625):key_itr() do
                        v626:push_back(v_u_13.NPCData:from_table(v627))
                    end;
                end;
                p_u_621(v626)
            end;
            local v_u_629 = v_u_15:get_env_datastore_prefix() .. v623
            local v_u_630 = nil
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): v_u_622, (ref 2): v_u_629, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_630, (copy 10): v_u_628, (ref 11): p_u_16 ]]
                local v631 = tick()
                local v_u_632, v_u_633, v634
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_632 = false
                    v_u_633 = nil
                    v634 = 1
                else
                    v_u_632 = false
                    v_u_633 = nil
                    v634 = 1
                end;
                while v_u_632 ~= true do
                    local _, v635 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_633, (ref 8): v_u_622, (ref 9): v_u_629, (ref 10): v_u_630, (ref 11): v_u_632 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_633, (ref 3): v_u_622, (ref 4): v_u_629, (ref 5): v_u_630 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_633 = v_u_622:GetAsync(v_u_629, v_u_630)
                        end)
                        v_u_632 = true
                    end)
                    if v_u_632 ~= true then
                        if v634 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_629, (tostring(v635)));
                        end;
                        wait(v634)
                        v634 = v634 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_629, v634, (tostring(v635)))
                    end;
                end;
                if v_u_628 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): v_u_628, (ref 2): v_u_632, (ref 3): v_u_633 ]]
                        v_u_628(v_u_632, v_u_633)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_622.Name, v_u_629, tick() - v631)
            end)
        end;
        local v_u_636 = nil
        pcall(function() --[[ Line: 1064 ]]
            --[[ Upvalues: (ref 1): v_u_636, (ref 2): s_DataStoreService_0 ]]
            v_u_636 = s_DataStoreService_0:GetDataStore("GenericMessageBoard")
        end)
        local function _(p637) --[[ Name: key_message_board ]] --[[ Line: 1067 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            if v_u_5:is_dev_build() then
                return string.format("d_%s", p637);
            else
                return string.format("%s", p637);
            end;
        end;
        v17.write_key_message_board_message = function(_, p638, p_u_639, p_u_640) --[[ Name: write_key_message_board_message ]] --[[ Line: 1071 ]]
            --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_636, (ref 3): v_u_5, (ref 4): v_u_12, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            v_u_2:is_string(p638)
            v_u_2:is_string(p_u_639:get_message_text())
            local v_u_641 = v_u_636
            local v642
            if v_u_5:is_dev_build() then
                v642 = string.format("d_%s", p638)
            else
                v642 = string.format("%s", p638)
            end;
            local function v_u_645(p643) --[[ Line: 1074 ]]
                --[[ Upvalues: (ref 1): v_u_12, (copy 2): p_u_639, (copy 3): p_u_640 ]]
                local v644 = v_u_12:table_to_list(p643 == nil and {} or p643)
                v644:push_front(p_u_639)
                if v644:count() > 100 then
                    v644:pop_back()
                end;
                if p_u_640 then
                    p_u_640(v644)
                end;
                return v_u_12:list_to_table(v644);
            end;
            local v_u_646 = v_u_15:get_env_datastore_prefix() .. v642
            local v_u_647 = nil
            v_u_5:spawn(function() --[[ Line: 168 ]]
                --[[ Upvalues: (copy 1): v_u_641, (ref 2): v_u_646, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_645, (copy 10): v_u_647, (ref 11): p_u_16 ]]
                local v648 = tick()
                local v_u_649, v650
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_649 = false
                    v650 = 1
                else
                    v_u_649 = false
                    v650 = 1
                end;
                while v_u_649 ~= true do
                    local _, v651 = pcall(function() --[[ Line: 174 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_641, (ref 8): v_u_646, (ref 9): v_u_645, (ref 10): v_u_649 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("update ")))
                        end;
                        v_u_7:increment_datastore_update_count()
                        f_run_datastore_request(function() --[[ Line: 178 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_641, (ref 3): v_u_646, (ref 4): v_u_645 ]]
                            f_trigger_datastore_lag_monkey("update ")
                            v_u_641:UpdateAsync(v_u_646, v_u_645)
                        end)
                        v_u_649 = true
                    end)
                    if v_u_649 ~= true then
                        if v650 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_update key(%s) failed(%s)", v_u_646, (tostring(v651)));
                        end;
                        wait(v650)
                        v650 = v650 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_update key(%s) wait(%d) failed(%s)", v_u_646, v650, (tostring(v651)))
                    end;
                end;
                if v_u_647 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 192 ]]
                        --[[ Upvalues: (ref 1): v_u_647, (ref 2): v_u_649 ]]
                        v_u_647(v_u_649)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "update ", v_u_641.Name, v_u_646, tick() - v648)
            end)
        end;
        v17.get_key_message_board_messages = function(_, p652, p_u_653) --[[ Name: get_key_message_board_messages ]] --[[ Line: 1088 ]]
            --[[ Upvalues: (ref 1): v_u_636, (ref 2): v_u_5, (ref 3): v_u_12, (ref 4): v_u_1, (ref 5): v_u_15, (ref 6): v_u_14, (ref 7): v_u_4, (ref 8): v_u_7, (copy 9): f_run_datastore_request, (copy 10): f_trigger_datastore_lag_monkey, (copy 11): p_u_16 ]]
            local v_u_654 = v_u_636
            local v655
            if v_u_5:is_dev_build() then
                v655 = string.format("d_%s", p652)
            else
                v655 = string.format("%s", p652)
            end;
            local function v_u_658(p656, p657) --[[ Line: 1089 ]]
                --[[ Upvalues: (copy 1): p_u_653, (ref 2): v_u_12, (ref 3): v_u_1 ]]
                if p656 and typeof(p657) == "table" then
                    p_u_653(v_u_12:table_to_list(p657))
                else
                    p_u_653(v_u_1:new())
                end;
            end;
            local v_u_659 = v_u_15:get_env_datastore_prefix() .. v655
            local v_u_660 = nil
            v_u_5:spawn(function() --[[ Line: 86 ]]
                --[[ Upvalues: (copy 1): v_u_654, (ref 2): v_u_659, (ref 3): v_u_5, (ref 4): v_u_14, (ref 5): v_u_4, (ref 6): v_u_7, (ref 7): f_run_datastore_request, (ref 8): f_trigger_datastore_lag_monkey, (copy 9): v_u_660, (copy 10): v_u_658, (ref 11): p_u_16 ]]
                local v661 = tick()
                local v_u_662, v_u_663, v664
                if v_u_5:is_dev_build() then
                    v_u_5:wait(v_u_5:rand_rangef(0.1, 0.5))
                    v_u_662 = false
                    v_u_663 = nil
                    v664 = 1
                else
                    v_u_662 = false
                    v_u_663 = nil
                    v664 = 1
                end;
                while v_u_662 ~= true do
                    local _, v665 = pcall(function() --[[ Line: 93 ]]
                        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_5, (ref 3): v_u_4, (ref 4): v_u_7, (ref 5): f_run_datastore_request, (ref 6): f_trigger_datastore_lag_monkey, (ref 7): v_u_663, (ref 8): v_u_654, (ref 9): v_u_659, (ref 10): v_u_660, (ref 11): v_u_662 ]]
                        if v_u_14.DatastoreChaosMonkeyEnabled == true and v_u_5:rand_rangei(0, 5) == 0 then
                            v_u_4:errf("ServerDataStoreAPIManager %s chaosmonkey fail", (tostring("get    ")))
                        end;
                        v_u_7:increment_datastore_get_count()
                        f_run_datastore_request(function() --[[ Line: 97 ]]
                            --[[ Upvalues: (ref 1): f_trigger_datastore_lag_monkey, (ref 2): v_u_663, (ref 3): v_u_654, (ref 4): v_u_659, (ref 5): v_u_660 ]]
                            f_trigger_datastore_lag_monkey("get    ")
                            v_u_663 = v_u_654:GetAsync(v_u_659, v_u_660)
                        end)
                        v_u_662 = true
                    end)
                    if v_u_662 ~= true then
                        if v664 >= 64 then
                            return v_u_4:errf("ServerDataStoreAPIManager do_datastore_get key(%s) failed(%s)", v_u_659, (tostring(v665)));
                        end;
                        wait(v664)
                        v664 = v664 * 2
                        v_u_4:warnf("ServerDataStoreAPIManager do_datastore_get key(%s) wait(%d) failed(%s)", v_u_659, v664, (tostring(v665)))
                    end;
                end;
                if v_u_658 then
                    p_u_16._post_fn:enqueue_function(function() --[[ Line: 112 ]]
                        --[[ Upvalues: (ref 1): v_u_658, (ref 2): v_u_662, (ref 3): v_u_663 ]]
                        v_u_658(v_u_662, v_u_663)
                    end)
                end;
                v_u_4:puts("<RECV>%s(%s) key(%s) time(%.3f)", "get    ", v_u_654.Name, v_u_659, tick() - v661)
            end)
        end;
        return v17;
    end
};
