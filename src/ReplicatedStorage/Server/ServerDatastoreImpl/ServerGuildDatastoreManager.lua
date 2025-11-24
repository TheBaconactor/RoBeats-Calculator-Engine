-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:23 PM
-- Time elapsed: 32 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Server.ServerAPIManager)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_6 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_7 = require(game.ReplicatedStorage.Shared.WaitForFinish)
local v_u_8 = require(game.ReplicatedStorage.Shared.APICooldown)
require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_9 = require(game.ReplicatedStorage.Shared.GuildUtil)
local v_u_10 = require(game.ReplicatedStorage.Shared.GuildData)
local v_u_11 = require(game.ReplicatedStorage.Shared.GuildRank)
local v_u_12 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_13 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_14 = require(game.ReplicatedStorage.Shared.ErrorReportBase)
local s_DataStoreService_0 = game:GetService("DataStoreService")
return {
    ["new"] = function(_, p_u_15) --[[ Name: new ]] --[[ Line: 24 ]]
        --[[ Upvalues: (copy 1): v_u_12, (copy 2): v_u_7, (copy 3): v_u_4, (copy 4): v_u_9, (copy 5): v_u_14, (copy 6): v_u_10, (copy 7): v_u_5, (copy 8): v_u_1, (copy 9): v_u_6, (copy 10): v_u_11, (copy 11): v_u_2, (copy 12): v_u_8, (copy 13): s_DataStoreService_0, (copy 14): v_u_3, (copy 15): v_u_13 ]]
        local v_u_16 = {}
        local v_u_17 = v_u_12:new()
        v_u_16.update = function(_, p18) --[[ Name: update ]] --[[ Line: 29 ]]
            --[[ Upvalues: (copy 1): v_u_17 ]]
            v_u_17:update(p18)
        end;
        v_u_16.dsapi_player_get_blob_guild_data_only = function(p_u_19, p_u_20, p_u_21, p_u_22) --[[ Name: dsapi_player_get_blob_guild_data_only ]] --[[ Line: 33 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4, (ref 3): v_u_9, (copy 4): p_u_15, (ref 5): v_u_14, (ref 6): v_u_10, (ref 7): v_u_5, (ref 8): v_u_1 ]]
            local v_u_23 = v_u_7.Builder:new()
            local v_u_24 = false
            local v_u_25 = nil
            local v_u_26 = v_u_4.GuildDataDoWebAPIRead == true
            local v_u_27 = v_u_9:not_in_guild_id()
            local v_u_28 = false
            if v_u_4.GuildDataDoWebAPIRead == true then
                v_u_23:begin()
                p_u_15._api:api_player_get_blob_guild_data_only(p_u_20, p_u_21, function(p29, p30) --[[ Line: 45 ]]
                    --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25, (ref 3): v_u_27, (ref 4): v_u_28, (copy 5): v_u_23 ]]
                    v_u_24 = p29
                    v_u_25 = p30
                    if typeof(p30) == "table" and typeof(p30.GuildID) == "number" then
                        v_u_27 = p30.GuildID
                    end;
                    v_u_28 = true
                    return v_u_23:finish();
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIWrite == true then
                v_u_23:begin()
                local function f_request_finish_response(p_u_31, p_u_32) --[[ Name: request_finish_response ]] --[[ Line: 68 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_24, (ref 3): v_u_25, (ref 4): p_u_15, (copy 5): v_u_23, (copy 6): p_u_19, (copy 7): p_u_20, (ref 8): v_u_14, (ref 9): v_u_10, (copy 10): p_u_21, (ref 11): v_u_5, (ref 12): v_u_1 ]]
                    local function f_response_after_validating_player_in_guild_data() --[[ Name: response_after_validating_player_in_guild_data ]] --[[ Line: 69 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_24, (copy 3): p_u_31, (ref 4): v_u_25, (copy 5): p_u_32, (ref 6): p_u_15, (ref 7): v_u_23 ]]
                        if v_u_4.GuildDataDoDatastoreAPIRead == true then
                            v_u_24 = p_u_31
                            v_u_25 = {
                                ["GuildID"] = p_u_32,
                                ["DayID"] = p_u_15._api:get_day_id(),
                                ["WeekID"] = p_u_15._api:get_week_id()
                            }
                        end;
                        return v_u_23:finish();
                    end;
                    p_u_19:datastore_get_guild_data(p_u_32, function(p33, p34) --[[ Line: 82 ]]
                        --[[ Upvalues: (ref 1): p_u_15, (ref 2): p_u_20, (copy 3): p_u_32, (ref 4): v_u_14, (ref 5): v_u_10, (ref 6): p_u_21, (ref 7): p_u_19, (ref 8): v_u_5, (ref 9): v_u_1 ]]
                        if p33 ~= true then
                            return p_u_15._error_report:error_debug_log(string.format("dsapi_player_get_blob_guild_data_only player(%d) ds_guildid(%d) - guildid does not exist in DS", p_u_20, p_u_32), v_u_14.LOG_ERROR_GUILD_DATASTORE);
                        end;
                        local v35 = v_u_10:get_player_info(p34, p_u_20)
                        if v35 == nil then
                            return p_u_15._error_report:error_debug_log(string.format("dsapi_player_get_blob_guild_data_only player(%d) ds_guildid(%d) - player not in guild member list in DS", p_u_20, p_u_32), v_u_14.LOG_ERROR_GUILD_DATASTORE);
                        end;
                        local v_u_36 = v35:get_name()
                        if v_u_36 ~= p_u_21 then
                            p_u_19:datastore_update_guild_data(p_u_20, p_u_32, function(p37) --[[ Line: 102 ]]
                                --[[ Upvalues: (ref 1): v_u_10, (ref 2): p_u_20, (ref 3): p_u_21 ]]
                                local v38 = v_u_10:get_player_info(p37, p_u_20)
                                if v38 ~= nil then
                                    v38:set_name(p_u_21)
                                end;
                            end, function(_, _) --[[ Line: 108 ]]
                                --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_15, (ref 3): p_u_20, (ref 4): p_u_32, (copy 5): v_u_36, (ref 6): p_u_21, (ref 7): v_u_14 ]]
                                v_u_5:spawn(function() --[[ Line: 109 ]]
                                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_15, (ref 3): p_u_20, (ref 4): p_u_32, (ref 5): v_u_36, (ref 6): p_u_21, (ref 7): v_u_14 ]]
                                    v_u_5:wait(5)
                                    p_u_15._error_report:error_debug_log(string.format("dsapi_player_get_blob_guild_data_only player(%d) ds_guildid(%d) - updating name in DS from [%s] to [%s]", p_u_20, p_u_32, v_u_36, p_u_21), v_u_14.LOG_DEV_GUILD_DATASTORE)
                                end)
                            end)
                        end;
                        if v_u_5:is_dev_build() then
                            v_u_1:puts("dsapi_player_get_blob_guild_data_only validated player(%d) name(%s) in guild(%d)", p_u_20, p_u_21, p_u_32)
                        end;
                    end)
                    f_response_after_validating_player_in_guild_data()
                end;
                p_u_19:datastore_get_player_guild_info(p_u_20, function(p_u_39, p_u_40) --[[ Line: 127 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_9, (copy 3): v_u_26, (ref 4): v_u_28, (ref 5): v_u_27, (ref 6): v_u_1, (copy 7): p_u_20, (copy 8): p_u_19, (copy 9): f_request_finish_response ]]
                    v_u_5:spawn(function() --[[ Line: 128 ]]
                        --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_39, (copy 3): p_u_40, (ref 4): v_u_26, (ref 5): v_u_28, (ref 6): v_u_5, (ref 7): v_u_27, (ref 8): v_u_1, (ref 9): p_u_20, (ref 10): p_u_19, (ref 11): f_request_finish_response ]]
                        local v41 = v_u_9:not_in_guild_id()
                        if p_u_39 then
                            v41 = p_u_40:get_guildid()
                        end;
                        if v_u_26 == true then
                            while v_u_28 ~= true do
                                v_u_5:wait(0.25)
                            end;
                            if v41 ~= v_u_27 then
                                v_u_1:warnf("dsapi_player_get_blob_guild_data_only player(%d) - overriding DS guildid(%d) with WEBAPI value(%d), writing back to DS", p_u_20, v41, v_u_27)
                                local v_u_42 = v_u_27
                                return p_u_19:datastore_update_player_guild_info_no_cooldown(p_u_20, function(p43) --[[ Line: 145 ]]
                                    --[[ Upvalues: (ref 1): v_u_42 ]]
                                    p43:set_guild_id(v_u_42)
                                end, function() --[[ Line: 148 ]]
                                    --[[ Upvalues: (ref 1): f_request_finish_response, (ref 2): v_u_42 ]]
                                    return f_request_finish_response(true, v_u_42);
                                end);
                            end;
                        end;
                        return f_request_finish_response(p_u_39, v41);
                    end)
                end)
            end;
            v_u_23:wait_for_finish(function() --[[ Line: 159 ]]
                --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_24, (ref 3): v_u_25 ]]
                p_u_22(v_u_24, v_u_25)
            end)
        end;
        v_u_16.dsapi_player_sync_guild_data_only = function(p_u_44, p_u_45, p_u_46, p_u_47) --[[ Name: dsapi_player_sync_guild_data_only ]] --[[ Line: 164 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4, (copy 3): p_u_15, (ref 4): v_u_6, (ref 5): v_u_5, (ref 6): v_u_9 ]]
            local v_u_48 = v_u_7.Builder:new()
            local v_u_49 = false
            local v_u_50 = ""
            local v_u_51 = nil
            if v_u_4.GuildDataDoWebAPIWrite == true then
                v_u_48:begin()
                p_u_15._api:api_player_sync_guild_data_only(p_u_45, function(p52) --[[ Line: 175 ]]
                    --[[ Upvalues: (copy 1): p_u_46 ]]
                    return p_u_46(p52);
                end, function(p53, p54, p55) --[[ Line: 188 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_49, (ref 3): v_u_50, (ref 4): v_u_51, (copy 5): v_u_48 ]]
                    if v_u_4.GuildDataDoWebAPIRead == true then
                        v_u_49 = p53
                        v_u_50 = p54
                        v_u_51 = p55
                    end;
                    v_u_48:finish()
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIWrite == true then
                v_u_48:begin()
                local v56 = {}
                local v57 = p_u_46(v56)
                local v_u_58 = typeof(v56.guild_contribution) ~= "number" and 0 or v56.guild_contribution
                local function f_request_finish_response(p59, p60) --[[ Name: request_finish_response ]] --[[ Line: 222 ]]
                    --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_4, (ref 3): v_u_49, (ref 4): v_u_50, (ref 5): v_u_5, (ref 6): v_u_51, (copy 7): v_u_48 ]]
                    v_u_6:is_int(p59)
                    v_u_6:is_bool(p60)
                    local v61 = {
                        ["Ok"] = true,
                        ["Status"] = 0,
                        ["LastModifiedTime"] = 0,
                        ["ContributionPoints"] = p59,
                        ["DidCapContributionPoints"] = p60
                    }
                    if v_u_4.GuildDataDoDatastoreAPIRead == true then
                        v_u_49 = true
                        v_u_50 = v_u_5:table_to_string(v61)
                        v_u_51 = v61
                    end;
                    v_u_48:finish()
                end;
                if v57 == true and v_u_58 > 0 then
                    local v_u_62 = v_u_58
                    local v_u_63 = false
                    p_u_44:datastore_get_player_guild_info(p_u_45, function(_, p64) --[[ Line: 246 ]]
                        --[[ Upvalues: (copy 1): f_request_finish_response, (copy 2): p_u_44, (copy 3): p_u_45, (ref 4): p_u_15, (ref 5): v_u_58, (ref 6): v_u_9, (ref 7): v_u_62, (ref 8): v_u_63 ]]
                        if p64:is_in_guild() ~= true then
                            return f_request_finish_response(0, false);
                        end;
                        p_u_44:datastore_update_guild_week_contribution_info(p_u_45, p64:get_guildid(), p_u_15._api:get_week_id(), function(p65) --[[ Line: 255 ]]
                            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_58, (ref 3): v_u_9, (ref 4): v_u_62, (ref 5): v_u_63 ]]
                            local v66 = p65:get_or_create_member_info_for_rbxid(p_u_45)
                            local v67 = v66:get_current_week_contribution_points()
                            local v68 = v67 + v_u_58
                            if v_u_9:get_weekly_player_contribution_cap() < v68 then
                                v68 = v_u_9:get_weekly_player_contribution_cap()
                                v_u_62 = v68 - v67
                                v_u_63 = true
                            end;
                            v66:set_current_week_contribution_points(v68)
                        end, function(p69, p70) --[[ Line: 266 ]]
                            --[[ Upvalues: (ref 1): p_u_44, (ref 2): f_request_finish_response, (ref 3): v_u_62, (ref 4): v_u_63 ]]
                            if p69 == true then
                                p_u_44:datastore_update_guild_contribution_leaderboard_from_ds_guild_week_contribution_info_no_cooldown(p70, function(_) end)
                            end;
                            f_request_finish_response(v_u_62, v_u_63)
                        end)
                    end)
                else
                    f_request_finish_response(0, false)
                end;
            end;
            v_u_48:wait_for_finish(function() --[[ Line: 283 ]]
                --[[ Upvalues: (copy 1): p_u_47, (ref 2): v_u_49, (ref 3): v_u_50, (ref 4): v_u_51 ]]
                p_u_47(v_u_49, v_u_50, v_u_51)
            end)
        end;
        v_u_16.dsapi_guild_get_data = function(p_u_71, p_u_72, p_u_73) --[[ Name: dsapi_guild_get_data ]] --[[ Line: 288 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_15, (ref 3): v_u_10, (ref 4): v_u_9 ]]
            if v_u_4.GuildDataDoWebAPIRead == true then
                p_u_15._api:api_guild_get_data(p_u_72, function(p74, p75) --[[ Line: 291 ]]
                    --[[ Upvalues: (copy 1): p_u_73 ]]
                    p_u_73(p74, p75)
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIRead == true then
                p_u_71:datastore_get_guild_data(p_u_72, function(p76, p77) --[[ Line: 297 ]]
                    --[[ Upvalues: (copy 1): p_u_73, (ref 2): v_u_10, (ref 3): v_u_9, (copy 4): p_u_71, (copy 5): p_u_72, (ref 6): p_u_15 ]]
                    if p76 ~= true then
                        return p_u_73(false, v_u_10:new(v_u_9:not_in_guild_id()):to_table());
                    end;
                    p_u_71:datastore_read_full_contribution_info_to_data(p_u_72, p_u_72, p_u_15._api:get_week_id(), p77, function(p78) --[[ Line: 306 ]]
                        --[[ Upvalues: (ref 1): p_u_73 ]]
                        p_u_73(true, p78:to_table())
                    end)
                end)
            end;
        end;
        v_u_16.dsapi_guild_create = function(p_u_79, p_u_80, p_u_81, p_u_82) --[[ Name: dsapi_guild_create ]] --[[ Line: 314 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4, (ref 3): v_u_9, (copy 4): p_u_15, (ref 5): v_u_10, (ref 6): v_u_5, (ref 7): v_u_1, (ref 8): v_u_11 ]]
            local v_u_83 = v_u_7.Builder:new()
            local v_u_84 = false
            local v_u_85 = nil
            local v_u_86 = v_u_4.GuildDataDoWebAPIWrite == true and true or v_u_4.GuildDataDoWebAPIRead == true
            local v_u_87 = v_u_9:not_in_guild_id()
            local v_u_88 = false
            if v_u_4.GuildDataDoWebAPIWrite == true then
                v_u_83:begin()
                p_u_15._api:api_guild_create(p_u_80, p_u_81, function(p89, p90) --[[ Line: 326 ]]
                    --[[ Upvalues: (copy 1): v_u_86, (ref 2): v_u_87, (ref 3): v_u_88, (ref 4): v_u_4, (ref 5): v_u_84, (ref 6): v_u_85, (copy 7): v_u_83 ]]
                    if v_u_86 == true then
                        if typeof(p90.GuildId) == "number" then
                            v_u_87 = p90.GuildId
                        end;
                        v_u_88 = true
                    end;
                    if v_u_4.GuildDataDoWebAPIRead == true then
                        v_u_84 = p89
                        if p89 and p90 then
                            v_u_85 = p90
                        end;
                    end;
                    v_u_83:finish()
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIWrite == true then
                v_u_83:begin()
                local function f_request_finish_response(p_u_91, p92) --[[ Name: request_finish_response ]] --[[ Line: 347 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_9, (ref 3): v_u_4, (ref 4): v_u_84, (ref 5): v_u_85, (copy 6): v_u_83, (copy 7): p_u_79, (ref 8): p_u_15 ]]
                    if p92 == nil then
                        local v93 = v_u_10:new(v_u_9:not_in_guild_id())
                        if v_u_4.GuildDataDoDatastoreAPIRead == true then
                            v_u_84 = p_u_91
                            v_u_85 = v93:to_table()
                        end;
                        return v_u_83:finish();
                    end;
                    p_u_79:datastore_read_full_contribution_info_to_data_no_cooldown(p92:get_guildid(), p_u_15._api:get_week_id(), p92, function(p94) --[[ Line: 360 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_84, (copy 3): p_u_91, (ref 4): v_u_85, (ref 5): v_u_83 ]]
                        if v_u_4.GuildDataDoDatastoreAPIRead == true then
                            v_u_84 = p_u_91
                            v_u_85 = p94:to_table()
                        end;
                        v_u_83:finish()
                    end)
                end;
                p_u_79:datastore_get_player_guild_info(p_u_80, function(_, p95) --[[ Line: 371 ]]
                    --[[ Upvalues: (ref 1): p_u_15, (copy 2): p_u_80, (copy 3): f_request_finish_response, (copy 4): p_u_79, (ref 5): v_u_9, (ref 6): v_u_5, (copy 7): v_u_86, (ref 8): v_u_88, (ref 9): v_u_87, (ref 10): v_u_1, (copy 11): p_u_81, (ref 12): v_u_10, (ref 13): v_u_11 ]]
                    local v96 = p_u_15._player_manager:id_to_player(p_u_80)
                    if v96 == nil then
                        return f_request_finish_response(false);
                    end;
                    local l_Name_0 = v96.Name
                    if p95:is_in_guild() == true then
                        return f_request_finish_response(false);
                    end;
                    p_u_79:datastore_alloc_guild_id_no_cooldown(function(p_u_97) --[[ Line: 381 ]]
                        --[[ Upvalues: (ref 1): v_u_9, (ref 2): f_request_finish_response, (ref 3): v_u_5, (ref 4): v_u_86, (ref 5): v_u_88, (ref 6): v_u_87, (ref 7): v_u_1, (ref 8): p_u_79, (ref 9): p_u_81, (ref 10): v_u_10, (ref 11): p_u_80, (copy 12): l_Name_0, (ref 13): v_u_11 ]]
                        if p_u_97 == v_u_9:invalid_rbxid() then
                            return f_request_finish_response(false);
                        end;
                        v_u_5:spawn(function() --[[ Line: 387 ]]
                            --[[ Upvalues: (ref 1): v_u_86, (ref 2): v_u_88, (ref 3): v_u_5, (ref 4): p_u_97, (ref 5): v_u_87, (ref 6): v_u_1, (ref 7): p_u_79, (ref 8): p_u_81, (ref 9): v_u_10, (ref 10): p_u_80, (ref 11): l_Name_0, (ref 12): v_u_11, (ref 13): f_request_finish_response ]]
                            if v_u_86 == true then
                                while v_u_88 ~= true do
                                    v_u_5:wait(0.25)
                                end;
                                if p_u_97 ~= v_u_87 then
                                    if v_u_5:is_dev_build() then
                                        v_u_1:warnf("dsapi_guild_create allocated_guild_id(%d) ~= WEBAPI_neu_guildid(%d) - Using WEBAPI value.", p_u_97, v_u_87)
                                    end;
                                    p_u_79:datastore_alloc_guild_id_write(v_u_87 + 1)
                                    p_u_97 = v_u_87
                                end;
                            end;
                            p_u_79:datastore_update_guild_data(p_u_97, p_u_97, function(p98) --[[ Line: 405 ]]
                                --[[ Upvalues: (ref 1): p_u_81, (ref 2): v_u_10, (ref 3): p_u_80, (ref 4): l_Name_0, (ref 5): v_u_11 ]]
                                p98:set_name(p_u_81)
                                local v99 = v_u_10:get_or_create_player_info(p98, p_u_80, l_Name_0)
                                v99:set_rank(v_u_11.Owner)
                                v99:set_joined_week(0)
                            end, function(p100, p_u_101) --[[ Line: 415 ]]
                                --[[ Upvalues: (ref 1): f_request_finish_response, (ref 2): p_u_79, (ref 3): p_u_80, (ref 4): p_u_97 ]]
                                if p100 ~= true then
                                    return f_request_finish_response(false);
                                end;
                                p_u_79:datastore_update_player_guild_info_no_cooldown(p_u_80, function(p102) --[[ Line: 422 ]]
                                    --[[ Upvalues: (ref 1): p_u_97 ]]
                                    p102:set_guild_id(p_u_97)
                                end, function() --[[ Line: 425 ]]
                                    --[[ Upvalues: (ref 1): f_request_finish_response, (copy 2): p_u_101 ]]
                                    f_request_finish_response(true, p_u_101)
                                end)
                            end)
                        end)
                    end)
                end)
            end;
            v_u_83:wait_for_finish(function() --[[ Line: 436 ]]
                --[[ Upvalues: (copy 1): p_u_82, (ref 2): v_u_84, (ref 3): v_u_85 ]]
                p_u_82(v_u_84, v_u_85)
            end)
        end;
        v_u_16.dsapi_guild_update_info = function(p_u_103, p_u_104, p_u_105, p_u_106) --[[ Name: dsapi_guild_update_info ]] --[[ Line: 441 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4, (copy 3): p_u_15, (ref 4): v_u_5, (ref 5): v_u_1 ]]
            local v_u_107 = v_u_7.Builder:new()
            local v_u_108 = false
            local v_u_109 = nil
            if v_u_4.GuildDataDoWebAPIWrite == true then
                v_u_107:begin()
                p_u_15._api:api_guild_update_info(p_u_104, p_u_105, function(p110, p111) --[[ Line: 449 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_108, (ref 3): v_u_109, (copy 4): v_u_107 ]]
                    if v_u_4.GuildDataDoWebAPIRead == true then
                        v_u_108 = p110
                        if p110 and p111 then
                            v_u_109 = p111
                        end;
                    end;
                    v_u_107:finish()
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIWrite == true then
                v_u_107:begin()
                p_u_103:datastore_update_guild_data(p_u_104, p_u_104, function(p112) --[[ Line: 466 ]]
                    --[[ Upvalues: (copy 1): p_u_105, (ref 2): v_u_5, (ref 3): v_u_1 ]]
                    p112:set_icon(p_u_105:get_icon())
                    p112:set_message(p_u_105:get_message())
                    if v_u_5:is_dev_build() then
                        v_u_1:puts("dsapi_guild_update_info GuildDataDoDatastoreAPIWrite icon(%s) message(%s)", tostring(p_u_105:get_icon()), (tostring(p_u_105:get_message())))
                    end;
                end, function(p_u_113, p_u_114) --[[ Line: 473 ]]
                    --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_104, (copy 3): p_u_103, (ref 4): p_u_15, (ref 5): v_u_4, (ref 6): v_u_108, (ref 7): v_u_109, (copy 8): v_u_107 ]]
                    if p_u_113 ~= true then
                        v_u_1:warnf("dsapi_guild_update_info guild(%d) - datastore write failed", p_u_104)
                    end;
                    p_u_103:datastore_update_guild_contribution_leaderboard_from_guild_data_no_cooldown(p_u_114, function() --[[ Line: 477 ]]
                        --[[ Upvalues: (ref 1): p_u_103, (ref 2): p_u_104, (ref 3): p_u_15, (copy 4): p_u_114, (ref 5): v_u_4, (ref 6): v_u_108, (copy 7): p_u_113, (ref 8): v_u_109, (ref 9): v_u_107 ]]
                        p_u_103:datastore_read_full_contribution_info_to_data_no_cooldown(p_u_104, p_u_15._api:get_week_id(), p_u_114, function(p115) --[[ Line: 482 ]]
                            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_108, (ref 3): p_u_113, (ref 4): v_u_109, (ref 5): v_u_107 ]]
                            if v_u_4.GuildDataDoDatastoreAPIRead == true then
                                v_u_108 = p_u_113
                                v_u_109 = p115:to_table()
                            end;
                            v_u_107:finish()
                        end)
                    end)
                end)
            end;
            v_u_107:wait_for_finish(function() --[[ Line: 495 ]]
                --[[ Upvalues: (copy 1): p_u_106, (ref 2): v_u_108, (ref 3): v_u_109 ]]
                p_u_106(v_u_108, v_u_109)
            end)
        end;
        v_u_16.dsapi_guild_edit_member_rank = function(p_u_116, p_u_117, p_u_118, p_u_119, p_u_120, p_u_121) --[[ Name: dsapi_guild_edit_member_rank ]] --[[ Line: 500 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4, (copy 3): p_u_15, (ref 4): v_u_10, (ref 5): v_u_1, (ref 6): v_u_11 ]]
            local v_u_122 = v_u_7.Builder:new()
            local v_u_123 = false
            local v_u_124 = nil
            if v_u_4.GuildDataDoWebAPIWrite == true then
                v_u_122:begin()
                p_u_15._api:api_guild_edit_member_rank(p_u_117, p_u_118, p_u_119, p_u_120, function(p125, p126) --[[ Line: 508 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_123, (ref 3): v_u_124, (copy 4): v_u_122 ]]
                    if v_u_4.GuildDataDoWebAPIRead == true then
                        v_u_123 = p125
                        if p125 and p126 then
                            v_u_124 = p126
                        end;
                    end;
                    v_u_122:finish()
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIWrite == true then
                v_u_122:begin()
                p_u_116:datastore_update_guild_data(p_u_117, p_u_117, function(p127) --[[ Line: 525 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_118, (copy 3): p_u_119, (ref 4): v_u_1, (copy 5): p_u_117, (copy 6): p_u_120, (ref 7): v_u_11 ]]
                    local v128 = v_u_10:get_player_info(p127, p_u_118)
                    local v129 = v_u_10:get_player_info(p127, p_u_119)
                    if v128 == nil or v129 == nil then
                        return v_u_1:errf("dsapi_guild_edit_member_rank guild(%d) player(%d) tar(%d) - player or target not in guild", p_u_117, p_u_118, p_u_119);
                    end;
                    v129:set_rank(p_u_120)
                    if p_u_120 == v_u_11.Owner then
                        v128:set_rank(v_u_11.Admin)
                    end;
                end, function(p_u_130, p131) --[[ Line: 539 ]]
                    --[[ Upvalues: (copy 1): p_u_116, (copy 2): p_u_117, (ref 3): p_u_15, (ref 4): v_u_4, (ref 5): v_u_123, (ref 6): v_u_124, (copy 7): v_u_122 ]]
                    p_u_116:datastore_read_full_contribution_info_to_data_no_cooldown(p_u_117, p_u_15._api:get_week_id(), p131, function(p132) --[[ Line: 544 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_123, (copy 3): p_u_130, (ref 4): v_u_124, (ref 5): v_u_122 ]]
                        if v_u_4.GuildDataDoDatastoreAPIRead == true then
                            v_u_123 = p_u_130
                            v_u_124 = p132:to_table()
                        end;
                        v_u_122:finish()
                    end)
                end)
            end;
            v_u_122:wait_for_finish(function() --[[ Line: 556 ]]
                --[[ Upvalues: (copy 1): p_u_121, (ref 2): v_u_123, (ref 3): v_u_124 ]]
                p_u_121(v_u_123, v_u_124)
            end)
        end;
        v_u_16.dsapi_change_guild_name = function(p_u_133, p_u_134, p_u_135, p_u_136) --[[ Name: dsapi_change_guild_name ]] --[[ Line: 561 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4, (copy 3): p_u_15, (ref 4): v_u_9, (ref 5): v_u_1 ]]
            local v_u_137 = v_u_7.Builder:new()
            local v_u_138 = false
            local v_u_139 = nil
            if v_u_4.GuildDataDoWebAPIWrite == true then
                v_u_137:begin()
                p_u_15._api:api_change_guild_name(p_u_134, p_u_135, v_u_9:get_guild_change_name_cost(), function(p140, p141) --[[ Line: 569 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_138, (ref 3): v_u_139, (copy 4): v_u_137 ]]
                    if v_u_4.GuildDataDoWebAPIRead == true then
                        v_u_138 = p140
                        if p140 and p141 then
                            v_u_139 = p141
                        end;
                    end;
                    v_u_137:finish()
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIWrite == true then
                v_u_137:begin()
                p_u_133:datastore_update_guild_data(p_u_134, p_u_134, function(p142) --[[ Line: 586 ]]
                    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_1, (copy 3): p_u_134, (copy 4): p_u_135 ]]
                    if p142:get_star_currency() < v_u_9:get_guild_change_name_cost() then
                        return v_u_1:errf("dsapi_change_guild_name guild(%d) - not enough star currency", p_u_134);
                    end;
                    local v143 = p142:get_star_currency() - v_u_9:get_guild_change_name_cost()
                    if v143 < 0 then
                        return v_u_1:errf("dsapi_change_guild_name guild(%d) - star currency would go negative", p_u_134);
                    end;
                    p142:set_star_currency(v143)
                    p142:set_name(p_u_135)
                end, function(p_u_144, p_u_145) --[[ Line: 598 ]]
                    --[[ Upvalues: (copy 1): p_u_133, (copy 2): p_u_134, (ref 3): p_u_15, (ref 4): v_u_4, (ref 5): v_u_138, (ref 6): v_u_139, (copy 7): v_u_137 ]]
                    p_u_133:datastore_update_guild_contribution_leaderboard_from_guild_data_no_cooldown(p_u_145, function() --[[ Line: 600 ]]
                        --[[ Upvalues: (ref 1): p_u_133, (ref 2): p_u_134, (ref 3): p_u_15, (copy 4): p_u_145, (ref 5): v_u_4, (ref 6): v_u_138, (copy 7): p_u_144, (ref 8): v_u_139, (ref 9): v_u_137 ]]
                        p_u_133:datastore_read_full_contribution_info_to_data_no_cooldown(p_u_134, p_u_15._api:get_week_id(), p_u_145, function(p146) --[[ Line: 605 ]]
                            --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_138, (ref 3): p_u_144, (ref 4): v_u_139, (ref 5): v_u_137 ]]
                            if v_u_4.GuildDataDoDatastoreAPIRead == true then
                                v_u_138 = p_u_144
                                v_u_139 = p146:to_table()
                            end;
                            v_u_137:finish()
                        end)
                    end)
                end)
            end;
            v_u_137:wait_for_finish(function() --[[ Line: 618 ]]
                --[[ Upvalues: (copy 1): p_u_136, (ref 2): v_u_138, (ref 3): v_u_139 ]]
                p_u_136(v_u_138, v_u_139)
            end)
        end;
        v_u_16.dsapi_guild_add_member = function(p_u_147, p_u_148, p_u_149, p_u_150) --[[ Name: dsapi_guild_add_member ]] --[[ Line: 623 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4, (copy 3): p_u_15, (ref 4): v_u_10, (ref 5): v_u_9, (ref 6): v_u_1, (ref 7): v_u_11 ]]
            local v_u_151 = v_u_7.Builder:new()
            local v_u_152 = false
            local v_u_153 = nil
            if v_u_4.GuildDataDoWebAPIWrite == true then
                v_u_151:begin()
                p_u_15._api:api_guild_add_member(p_u_148, p_u_149, function(p154, p155) --[[ Line: 631 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_152, (ref 3): v_u_153, (copy 4): v_u_151 ]]
                    if v_u_4.GuildDataDoWebAPIRead == true then
                        v_u_152 = p154
                        if p154 and p155 then
                            v_u_153 = p155
                        end;
                    end;
                    v_u_151:finish()
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIWrite == true then
                v_u_151:begin()
                local function f_request_finish_response(p_u_156, p157) --[[ Name: request_finish_response ]] --[[ Line: 645 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_9, (ref 3): v_u_4, (ref 4): v_u_152, (ref 5): v_u_153, (copy 6): v_u_151, (copy 7): p_u_147, (copy 8): p_u_148, (ref 9): p_u_15 ]]
                    if p157 == nil then
                        local v158 = v_u_10:new(v_u_9:not_in_guild_id())
                        if v_u_4.GuildDataDoDatastoreAPIRead == true then
                            v_u_152 = p_u_156
                            v_u_153 = v158:to_table()
                        end;
                        return v_u_151:finish();
                    end;
                    p_u_147:datastore_read_full_contribution_info_to_data_no_cooldown(p_u_148, p_u_15._api:get_week_id(), p157, function(p159) --[[ Line: 658 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_152, (copy 3): p_u_156, (ref 4): v_u_153, (ref 5): v_u_151 ]]
                        if v_u_4.GuildDataDoDatastoreAPIRead == true then
                            v_u_152 = p_u_156
                            v_u_153 = p159:to_table()
                        end;
                        return v_u_151:finish();
                    end)
                end;
                p_u_147:datastore_get_player_guild_info(p_u_149, function(_, p160) --[[ Line: 669 ]]
                    --[[ Upvalues: (copy 1): f_request_finish_response, (ref 2): p_u_15, (copy 3): p_u_149, (copy 4): p_u_147, (copy 5): p_u_148, (ref 6): v_u_9, (ref 7): v_u_1, (ref 8): v_u_10, (ref 9): v_u_11 ]]
                    if p160:is_in_guild() == true then
                        return f_request_finish_response(false);
                    end;
                    local v161 = p_u_15._player_manager:id_to_player(p_u_149)
                    if v161 == nil then
                        return f_request_finish_response(false);
                    end;
                    local l_Name_1 = v161.Name
                    p_u_147:datastore_update_guild_data(p_u_149, p_u_148, function(p162) --[[ Line: 683 ]]
                        --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_1, (ref 3): p_u_148, (ref 4): p_u_149, (ref 5): v_u_10, (copy 6): l_Name_1, (ref 7): v_u_11, (ref 8): p_u_15 ]]
                        if p162:get_total_members() >= v_u_9:get_max_guild_players() then
                            return v_u_1:errf("dsapi_guild_add_member guild(%d) player(%d) - guild full", p_u_148, p_u_149);
                        end;
                        if v_u_10:get_player_info(p162, p_u_149) ~= nil then
                            return v_u_1:errf("dsapi_guild_add_member guild(%d) player(%d) - player already in guild", p_u_148, p_u_149);
                        end;
                        local v163 = v_u_10:get_or_create_player_info(p162, p_u_149, l_Name_1)
                        v163:set_rank(v_u_11.Member)
                        v163:set_joined_week(p_u_15._api:get_week_id())
                    end, function(p164, p_u_165) --[[ Line: 696 ]]
                        --[[ Upvalues: (ref 1): f_request_finish_response, (ref 2): p_u_147, (ref 3): p_u_149, (ref 4): p_u_148 ]]
                        if p164 ~= true then
                            return f_request_finish_response(false);
                        end;
                        p_u_147:datastore_update_player_guild_info_no_cooldown(p_u_149, function(p166) --[[ Line: 703 ]]
                            --[[ Upvalues: (ref 1): p_u_148 ]]
                            p166:set_guild_id(p_u_148)
                        end, function() --[[ Line: 706 ]]
                            --[[ Upvalues: (ref 1): f_request_finish_response, (copy 2): p_u_165 ]]
                            f_request_finish_response(true, p_u_165)
                        end)
                    end)
                end)
            end;
            v_u_151:wait_for_finish(function() --[[ Line: 715 ]]
                --[[ Upvalues: (copy 1): p_u_150, (ref 2): v_u_152, (ref 3): v_u_153 ]]
                p_u_150(v_u_152, v_u_153)
            end)
        end;
        v_u_16.dsapi_guild_remove_member = function(p_u_167, p_u_168, p_u_169, p_u_170) --[[ Name: dsapi_guild_remove_member ]] --[[ Line: 720 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4, (copy 3): p_u_15, (ref 4): v_u_10, (ref 5): v_u_9, (ref 6): v_u_2, (ref 7): v_u_11 ]]
            local v_u_171 = v_u_7.Builder:new()
            local v_u_172 = false
            local v_u_173 = nil
            if v_u_4.GuildDataDoWebAPIWrite == true then
                v_u_171:begin()
                p_u_15._api:api_guild_remove_member(p_u_168, p_u_169, function(p174, p175) --[[ Line: 728 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_172, (ref 3): v_u_173, (copy 4): v_u_171 ]]
                    if v_u_4.GuildDataDoWebAPIRead == true then
                        v_u_172 = p174
                        if p174 and p175 then
                            v_u_173 = p175
                        end;
                    end;
                    v_u_171:finish()
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIWrite == true then
                v_u_171:begin()
                local function f_request_finish_response(p_u_176, p177) --[[ Name: request_finish_response ]] --[[ Line: 742 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_9, (ref 3): v_u_4, (ref 4): v_u_172, (ref 5): v_u_173, (copy 6): v_u_171, (copy 7): p_u_167, (copy 8): p_u_168, (ref 9): p_u_15 ]]
                    if p177 == nil then
                        local v178 = v_u_10:new(v_u_9:not_in_guild_id())
                        if v_u_4.GuildDataDoDatastoreAPIRead == true then
                            v_u_172 = p_u_176
                            v_u_173 = v178:to_table()
                        end;
                        return v_u_171:finish();
                    end;
                    p_u_167:datastore_read_full_contribution_info_to_data_no_cooldown(p_u_168, p_u_15._api:get_week_id(), p177, function(p179) --[[ Line: 755 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_172, (copy 3): p_u_176, (ref 4): v_u_173, (ref 5): v_u_171 ]]
                        if v_u_4.GuildDataDoDatastoreAPIRead == true then
                            v_u_172 = p_u_176
                            v_u_173 = p179:to_table()
                        end;
                        return v_u_171:finish();
                    end)
                end;
                p_u_167:datastore_get_player_guild_info(p_u_169, function(_, p180) --[[ Line: 766 ]]
                    --[[ Upvalues: (copy 1): f_request_finish_response, (copy 2): p_u_168, (copy 3): p_u_167, (copy 4): p_u_169, (ref 5): v_u_2, (ref 6): v_u_11, (ref 7): v_u_7, (ref 8): p_u_15, (ref 9): v_u_9 ]]
                    if p180:is_in_guild() ~= true then
                        return f_request_finish_response(false);
                    end;
                    if p180:get_guildid() ~= p_u_168 then
                        return f_request_finish_response(false);
                    end;
                    p_u_167:datastore_update_guild_data(p_u_169, p_u_168, function(p_u_181) --[[ Line: 777 ]]
                        --[[ Upvalues: (ref 1): v_u_2, (ref 2): p_u_169, (ref 3): v_u_11 ]]
                        v_u_2:remove_if(p_u_181:get_member_infos(), function(p182) --[[ Line: 779 ]]
                            --[[ Upvalues: (ref 1): p_u_169 ]]
                            return p182:get_rbxid() == p_u_169;
                        end)
                        local function f_get_owner_count() --[[ Name: get_owner_count ]] --[[ Line: 783 ]]
                            --[[ Upvalues: (copy 1): p_u_181, (ref 2): v_u_11 ]]
                            local v183 = 0
                            for _, v184 in p_u_181:get_member_infos():key_itr() do
                                if v184:get_rank() == v_u_11.Owner then
                                    v183 = v183 + 1
                                end;
                            end;
                            return v183;
                        end;
                        if f_get_owner_count() == 0 then
                            for _, v185 in p_u_181:get_member_infos():key_itr() do
                                if v185:get_rank() == v_u_11.Admin then
                                    v185:set_rank(v_u_11.Owner)
                                    break;
                                end;
                            end;
                        end;
                        if f_get_owner_count() == 0 then
                            for _, v186 in p_u_181:get_member_infos():key_itr() do
                                if v186:get_rank() == v_u_11.Member then
                                    v186:set_rank(v_u_11.Owner)
                                    return;
                                end;
                            end;
                        end;
                    end, function(p187, p_u_188) --[[ Line: 813 ]]
                        --[[ Upvalues: (ref 1): f_request_finish_response, (ref 2): v_u_7, (ref 3): p_u_167, (ref 4): p_u_168, (ref 5): p_u_15, (ref 6): p_u_169, (ref 7): v_u_9 ]]
                        if p187 ~= true then
                            return f_request_finish_response(false);
                        end;
                        local v_u_189 = v_u_7.Builder:new()
                        v_u_189:begin()
                        p_u_167:datastore_update_guild_week_contribution_info(p_u_168, p_u_168, p_u_15._api:get_week_id(), function(p190) --[[ Line: 826 ]]
                            --[[ Upvalues: (ref 1): p_u_169 ]]
                            p190:get_rbxid_to_member_info_with_contribution():remove(p_u_169)
                        end, function(_, p191) --[[ Line: 829 ]]
                            --[[ Upvalues: (ref 1): p_u_167, (copy 2): v_u_189 ]]
                            p_u_167:datastore_update_guild_contribution_leaderboard_from_ds_guild_week_contribution_info_no_cooldown(p191, function(_) --[[ Line: 832 ]]
                                --[[ Upvalues: (ref 1): v_u_189 ]]
                                v_u_189:finish()
                            end)
                        end)
                        v_u_189:begin()
                        p_u_167:datastore_update_player_guild_info_no_cooldown(p_u_169, function(p192) --[[ Line: 843 ]]
                            --[[ Upvalues: (ref 1): v_u_9 ]]
                            p192:set_guild_id(v_u_9:not_in_guild_id())
                        end, function() --[[ Line: 846 ]]
                            --[[ Upvalues: (copy 1): v_u_189 ]]
                            v_u_189:finish()
                        end)
                        v_u_189:wait_for_finish(function() --[[ Line: 851 ]]
                            --[[ Upvalues: (ref 1): f_request_finish_response, (copy 2): p_u_188 ]]
                            f_request_finish_response(true, p_u_188)
                        end)
                    end)
                end)
            end;
            v_u_171:wait_for_finish(function() --[[ Line: 860 ]]
                --[[ Upvalues: (copy 1): p_u_170, (ref 2): v_u_172, (ref 3): v_u_173 ]]
                p_u_170(v_u_172, v_u_173)
            end)
        end;
        v_u_16.dsapi_guild_add_star_currency = function(p_u_193, p_u_194, p_u_195, p_u_196) --[[ Name: dsapi_guild_add_star_currency ]] --[[ Line: 865 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4, (copy 3): p_u_15, (ref 4): v_u_1 ]]
            local v_u_197 = v_u_7.Builder:new()
            local v_u_198 = false
            local v_u_199 = nil
            if v_u_4.GuildDataDoWebAPIWrite == true then
                v_u_197:begin()
                p_u_15._api:api_guild_add_star_currency(p_u_194, p_u_195, function(p200, p201) --[[ Line: 875 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_198, (ref 3): v_u_199, (copy 4): v_u_197 ]]
                    if v_u_4.GuildDataDoWebAPIRead == true then
                        v_u_198 = p200
                        if p200 and p201 then
                            v_u_199 = p201
                        end;
                    end;
                    v_u_197:finish()
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIWrite == true then
                v_u_197:begin()
                p_u_193:datastore_update_guild_data(p_u_194, p_u_194, function(p202) --[[ Line: 892 ]]
                    --[[ Upvalues: (copy 1): p_u_195, (ref 2): v_u_1, (copy 3): p_u_194 ]]
                    local v203 = p202:get_star_currency() + p_u_195
                    if v203 < 0 then
                        v_u_1:errf("dsapi_guild_add_star_currency guild(%d) - star currency would go negative", p_u_194)
                    end;
                    p202:set_star_currency(v203)
                end, function(p_u_204, p205) --[[ Line: 899 ]]
                    --[[ Upvalues: (copy 1): p_u_193, (copy 2): p_u_194, (ref 3): p_u_15, (ref 4): v_u_4, (ref 5): v_u_198, (ref 6): v_u_199, (copy 7): v_u_197 ]]
                    p_u_193:datastore_read_full_contribution_info_to_data_no_cooldown(p_u_194, p_u_15._api:get_week_id(), p205, function(p206) --[[ Line: 904 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_198, (copy 3): p_u_204, (ref 4): v_u_199, (ref 5): v_u_197 ]]
                        if v_u_4.GuildDataDoDatastoreAPIRead == true then
                            v_u_198 = p_u_204
                            v_u_199 = p206:to_table()
                        end;
                        return v_u_197:finish();
                    end)
                end)
            end;
            v_u_197:wait_for_finish(function() --[[ Line: 916 ]]
                --[[ Upvalues: (copy 1): p_u_196, (ref 2): v_u_198, (ref 3): v_u_199 ]]
                p_u_196(v_u_198, v_u_199)
            end)
        end;
        v_u_16.dsapi_create_guild_week_contribution_entry = function(p_u_207, p_u_208, p_u_209, p_u_210, p_u_211) --[[ Name: dsapi_create_guild_week_contribution_entry ]] --[[ Line: 921 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4, (copy 3): p_u_15, (ref 4): v_u_10, (ref 5): v_u_9, (ref 6): v_u_1 ]]
            local v_u_212 = v_u_7.Builder:new()
            local v_u_213 = false
            local v_u_214 = nil
            if v_u_4.GuildDataDoWebAPIWrite == true then
                v_u_212:begin()
                p_u_15._api:api_create_guild_week_contribution_entry(p_u_208, p_u_209, p_u_210, function(p215, p216) --[[ Line: 929 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_213, (ref 3): v_u_214, (copy 4): v_u_212 ]]
                    if v_u_4.GuildDataDoWebAPIRead == true then
                        v_u_213 = p215
                        if p215 and p216 then
                            v_u_214 = p216
                        end;
                    end;
                    v_u_212:finish()
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIWrite == true then
                v_u_212:begin()
                local function f_request_finish_response(p_u_217, p218) --[[ Name: request_finish_response ]] --[[ Line: 943 ]]
                    --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_9, (ref 3): v_u_4, (ref 4): v_u_213, (ref 5): v_u_214, (copy 6): v_u_212, (copy 7): p_u_207, (copy 8): p_u_208, (ref 9): p_u_15 ]]
                    if p218 == nil then
                        local v219 = v_u_10:new(v_u_9:not_in_guild_id())
                        if v_u_4.GuildDataDoDatastoreAPIRead == true then
                            v_u_213 = p_u_217
                            v_u_214 = v219:to_table()
                        end;
                        return v_u_212:finish();
                    end;
                    p_u_207:datastore_read_full_contribution_info_to_data_no_cooldown(p_u_208, p_u_15._api:get_week_id(), p218, function(p220) --[[ Line: 956 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_213, (copy 3): p_u_217, (ref 4): v_u_214, (ref 5): v_u_212 ]]
                        if v_u_4.GuildDataDoDatastoreAPIRead == true then
                            v_u_213 = p_u_217
                            v_u_214 = p220:to_table()
                        end;
                        return v_u_212:finish();
                    end)
                end;
                p_u_207:datastore_get_guild_data(p_u_208, function(p221, p_u_222) --[[ Line: 967 ]]
                    --[[ Upvalues: (copy 1): f_request_finish_response, (copy 2): p_u_210, (ref 3): v_u_1, (copy 4): p_u_208, (copy 5): p_u_207, (ref 6): p_u_15, (ref 7): v_u_10, (copy 8): p_u_209 ]]
                    if p221 ~= true then
                        return f_request_finish_response(false);
                    end;
                    if p_u_222:get_star_currency() ~= p_u_210 then
                        v_u_1:warnf("dsapi_create_guild_week_contribution_entry guild(%d) - star currency mismatch loaded(%d) expected(%d)", p_u_208, p_u_222:get_star_currency(), p_u_210)
                        return f_request_finish_response(false);
                    end;
                    p_u_207:datastore_update_guild_week_contribution_info(p_u_208, p_u_208, p_u_15._api:get_week_id(), function(p223) --[[ Line: 981 ]]
                        --[[ Upvalues: (ref 1): v_u_1, (ref 2): p_u_208, (ref 3): p_u_15, (ref 4): v_u_10, (ref 5): p_u_209 ]]
                        if p223:get_week_contribution_entry():is_entered() == true then
                            return v_u_1:errf("dsapi_create_guild_week_contribution_entry guild(%d) week(%d) - already entered this week", p_u_208, p_u_15._api:get_week_id());
                        end;
                        p223:set_week_contribution_entry(v_u_10.WeekContributionEntry:new(true, p_u_15._api:get_week_id(), p_u_209, 0, 0, 0))
                    end, function(p224, p225) --[[ Line: 996 ]]
                        --[[ Upvalues: (ref 1): f_request_finish_response, (ref 2): p_u_207, (copy 3): p_u_222 ]]
                        if p224 ~= true then
                            return f_request_finish_response(false);
                        end;
                        p_u_207:datastore_guild_data_and_week_contribution_info_update_contribution_leaderboard(p_u_222, p225, function() --[[ Line: 1003 ]]
                            --[[ Upvalues: (ref 1): f_request_finish_response, (ref 2): p_u_222 ]]
                            return f_request_finish_response(true, p_u_222);
                        end)
                    end)
                end)
            end;
            v_u_212:wait_for_finish(function() --[[ Line: 1012 ]]
                --[[ Upvalues: (copy 1): p_u_211, (ref 2): v_u_213, (ref 3): v_u_214 ]]
                p_u_211(v_u_213, v_u_214)
            end)
        end;
        v_u_16.dsapi_add_guild_bonus_entry = function(p_u_226, p_u_227, p_u_228, p_u_229) --[[ Name: dsapi_add_guild_bonus_entry ]] --[[ Line: 1017 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_4, (copy 3): p_u_15 ]]
            local v_u_230 = v_u_7.Builder:new()
            local v_u_231 = false
            local v_u_232 = nil
            if v_u_4.GuildDataDoWebAPIWrite == true then
                v_u_230:begin()
                p_u_15._api:api_add_guild_bonus_entry(p_u_227, p_u_228, function(p233, p234) --[[ Line: 1025 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_231, (ref 3): v_u_232, (copy 4): v_u_230 ]]
                    if v_u_4.GuildDataDoWebAPIRead == true then
                        v_u_231 = p233
                        if p233 and p234 then
                            v_u_232 = p234
                        end;
                    end;
                    v_u_230:finish()
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIWrite == true then
                v_u_230:begin()
                p_u_226:datastore_update_guild_data(p_u_227, p_u_227, function(p235) --[[ Line: 1042 ]]
                    --[[ Upvalues: (ref 1): p_u_15, (copy 2): p_u_228 ]]
                    p235:set_bonus_weekid(p_u_15._api:get_week_id())
                    p235:set_bonus_flag(p_u_228)
                end, function(p_u_236, p237) --[[ Line: 1046 ]]
                    --[[ Upvalues: (copy 1): p_u_226, (copy 2): p_u_227, (ref 3): p_u_15, (ref 4): v_u_4, (ref 5): v_u_231, (ref 6): v_u_232, (copy 7): v_u_230 ]]
                    p_u_226:datastore_read_full_contribution_info_to_data_no_cooldown(p_u_227, p_u_15._api:get_week_id(), p237, function(p238) --[[ Line: 1051 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_231, (copy 3): p_u_236, (ref 4): v_u_232, (ref 5): v_u_230 ]]
                        if v_u_4.GuildDataDoDatastoreAPIRead == true then
                            v_u_231 = p_u_236
                            v_u_232 = p238:to_table()
                        end;
                        v_u_230:finish()
                    end)
                end)
            end;
            v_u_230:wait_for_finish(function() --[[ Line: 1063 ]]
                --[[ Upvalues: (copy 1): p_u_229, (ref 2): v_u_231, (ref 3): v_u_232 ]]
                p_u_229(v_u_231, v_u_232)
            end)
        end;
        v_u_16.dsapi_change_guild_recruitment_state = function(p_u_239, p_u_240, p_u_241, p_u_242) --[[ Name: dsapi_change_guild_recruitment_state ]] --[[ Line: 1068 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_10, (ref 3): v_u_7, (ref 4): v_u_4, (copy 5): p_u_15 ]]
            v_u_6:is_enum_member(p_u_241, v_u_10.RecruitmentState)
            local v_u_243 = v_u_7.Builder:new()
            local v_u_244 = false
            local v_u_245 = nil
            if v_u_4.GuildDataDoWebAPIWrite == true then
                v_u_243:begin()
                p_u_15._api:api_change_recruitment_state(p_u_240, p_u_241, function(p246, p247) --[[ Line: 1077 ]]
                    --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_244, (ref 3): v_u_245, (copy 4): v_u_243 ]]
                    if v_u_4.GuildDataDoWebAPIRead == true then
                        v_u_244 = p246
                        if p246 and p247 then
                            v_u_245 = p247
                        end;
                    end;
                    v_u_243:finish()
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIWrite == true then
                v_u_243:begin()
                p_u_239:datastore_update_guild_data(p_u_240, p_u_240, function(p248) --[[ Line: 1094 ]]
                    --[[ Upvalues: (copy 1): p_u_241 ]]
                    p248:set_recruitment_state(p_u_241)
                end, function(p_u_249, p250) --[[ Line: 1097 ]]
                    --[[ Upvalues: (copy 1): p_u_239, (copy 2): p_u_240, (ref 3): p_u_15, (ref 4): v_u_4, (ref 5): v_u_244, (ref 6): v_u_245, (copy 7): v_u_243 ]]
                    p_u_239:datastore_read_full_contribution_info_to_data_no_cooldown(p_u_240, p_u_15._api:get_week_id(), p250, function(p251) --[[ Line: 1102 ]]
                        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_244, (copy 3): p_u_249, (ref 4): v_u_245, (ref 5): v_u_243 ]]
                        if v_u_4.GuildDataDoDatastoreAPIRead == true then
                            v_u_244 = p_u_249
                            v_u_245 = p251:to_table()
                        end;
                        v_u_243:finish()
                    end)
                end)
            end;
            v_u_243:wait_for_finish(function() --[[ Line: 1114 ]]
                --[[ Upvalues: (copy 1): p_u_242, (ref 2): v_u_244, (ref 3): v_u_245 ]]
                p_u_242(v_u_244, v_u_245)
            end)
        end;
        local function _(p252, _, p_u_253) --[[ Name: get_week_guild_contribution_leaderboard_tab ]] --[[ Line: 1119 ]]
            --[[ Upvalues: (copy 1): v_u_16 ]]
            v_u_16:datastore_get_guild_contribution_leaderboard_no_cooldown(p252, function(p254) --[[ Line: 1122 ]]
                --[[ Upvalues: (copy 1): p_u_253 ]]
                for v255, v256 in p254:key_itr() do
                    local v257 = v256:get_current_week_contribution_entry()
                    if v257 ~= nil then
                        v257:set_rank_from_list_index(v255)
                        v257:set_total_entries(p254:count())
                    end;
                end;
                local v258 = {}
                for _, v259 in p254:key_itr() do
                    v258[#v258 + 1] = v259:to_table()
                end;
                p_u_253(true, v258, p254)
            end)
        end;
        v_u_16.dsapi_guild_get_global_contribution_leaderboard = function(_, p_u_260) --[[ Name: dsapi_guild_get_global_contribution_leaderboard ]] --[[ Line: 1141 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_15, (copy 3): v_u_16 ]]
            if v_u_4.GuildDataDoWebAPIRead == true then
                p_u_15._api:api_guild_get_global_contribution_leaderboard(function(p261, p262) --[[ Line: 1143 ]]
                    --[[ Upvalues: (copy 1): p_u_260 ]]
                    p_u_260(p261, p262)
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIRead == true then
                local function v_u_265(p263, p264) --[[ Line: 1150 ]]
                    --[[ Upvalues: (copy 1): p_u_260 ]]
                    p_u_260(p263, p264)
                end;
                v_u_16:datastore_get_guild_contribution_leaderboard_no_cooldown(p_u_15._api:get_week_id(), function(p266) --[[ Line: 1122 ]]
                    --[[ Upvalues: (copy 1): v_u_265 ]]
                    for v267, v268 in p266:key_itr() do
                        local v269 = v268:get_current_week_contribution_entry()
                        if v269 ~= nil then
                            v269:set_rank_from_list_index(v267)
                            v269:set_total_entries(p266:count())
                        end;
                    end;
                    local v270 = {}
                    for _, v271 in p266:key_itr() do
                        v270[#v270 + 1] = v271:to_table()
                    end;
                    v_u_265(true, v270, p266)
                end)
            end;
        end;
        v_u_16.dsapi_guild_get_previous_week_global_contribution_leaderboard = function(_, p272, p273, p_u_274) --[[ Name: dsapi_guild_get_previous_week_global_contribution_leaderboard ]] --[[ Line: 1156 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_15, (copy 3): v_u_16 ]]
            if v_u_4.GuildDataDoWebAPIRead == true then
                p_u_15._api:api_guild_get_previous_week_global_contribution_leaderboard(p272, p273, function(p275, p276) --[[ Line: 1158 ]]
                    --[[ Upvalues: (copy 1): p_u_274 ]]
                    p_u_274(p275, p276)
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIRead == true then
                local function v_u_279(p277, p278) --[[ Line: 1164 ]]
                    --[[ Upvalues: (copy 1): p_u_274 ]]
                    p_u_274(p277, p278)
                end;
                v_u_16:datastore_get_guild_contribution_leaderboard_no_cooldown(p272, function(p280) --[[ Line: 1122 ]]
                    --[[ Upvalues: (copy 1): v_u_279 ]]
                    for v281, v282 in p280:key_itr() do
                        local v283 = v282:get_current_week_contribution_entry()
                        if v283 ~= nil then
                            v283:set_rank_from_list_index(v281)
                            v283:set_total_entries(p280:count())
                        end;
                    end;
                    local v284 = {}
                    for _, v285 in p280:key_itr() do
                        v284[#v284 + 1] = v285:to_table()
                    end;
                    v_u_279(true, v284, p280)
                end)
            end;
        end;
        v_u_16.dsapi_get_contribution_leaderboard_status = function(_, p_u_286, p_u_287) --[[ Name: dsapi_get_contribution_leaderboard_status ]] --[[ Line: 1170 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_15, (copy 3): v_u_16 ]]
            if v_u_4.GuildDataDoWebAPIRead == true then
                p_u_15._api:api_get_contribution_leaderboard_status(p_u_286, function(p288, p289) --[[ Line: 1172 ]]
                    --[[ Upvalues: (copy 1): p_u_287 ]]
                    p_u_287(p288, p289)
                end)
            end;
            if v_u_4.GuildDataDoDatastoreAPIRead == true then
                local function v_u_298(_, _, p290) --[[ Line: 1188 ]]
                    --[[ Upvalues: (copy 1): p_u_286, (copy 2): p_u_287 ]]
                    local v291 = {}
                    local v292 = nil
                    local v293 = -1
                    for v294, v295 in p290:key_itr() do
                        if v295:get_guildid() == p_u_286 then
                            v293 = v294
                            v292 = v295
                            break;
                        end;
                    end;
                    if v292 ~= nil then
                        v291.YourTeam = v292:to_table()
                        local v296 = p290:get(v293 - 1)
                        if v296 ~= nil then
                            v291.NextTeam = v296:to_table()
                        end;
                        local v297 = p290:get(v293 + 1)
                        if v297 ~= nil then
                            v291.PrevTeam = v297:to_table()
                        end;
                    end;
                    p_u_287(true, v291)
                end;
                v_u_16:datastore_get_guild_contribution_leaderboard_no_cooldown(p_u_15._api:get_week_id(), function(p299) --[[ Line: 1122 ]]
                    --[[ Upvalues: (copy 1): v_u_298 ]]
                    for v300, v301 in p299:key_itr() do
                        local v302 = v301:get_current_week_contribution_entry()
                        if v302 ~= nil then
                            v302:set_rank_from_list_index(v300)
                            v302:set_total_entries(p299:count())
                        end;
                    end;
                    local v303 = {}
                    for _, v304 in p299:key_itr() do
                        v303[#v303 + 1] = v304:to_table()
                    end;
                    v_u_298(true, v303, p299)
                end)
            end;
        end;
        local v_u_305 = v_u_8:new():set_cooldown(0.25)
        local v_u_306 = v_u_8:new():set_cooldown(1)
        local v_u_307 = s_DataStoreService_0:GetDataStore("PlayerGuildInfo")
        local v_u_308 = {}
        v_u_308.new = function(_, p_u_309, p_u_310) --[[ Name: new ]] --[[ Line: 1235 ]]
            --[[ Upvalues: (ref 1): v_u_6, (ref 2): v_u_9 ]]
            v_u_6:is_int(p_u_309)
            v_u_6:is_int(p_u_310)
            local v311 = {}
            v311.get_player_id = function(_) --[[ Name: get_player_id ]] --[[ Line: 1240 ]]
                --[[ Upvalues: (copy 1): p_u_309 ]]
                return p_u_309;
            end;
            v311.get_guildid = function(_) --[[ Name: get_guildid ]] --[[ Line: 1241 ]]
                --[[ Upvalues: (ref 1): p_u_310 ]]
                return p_u_310;
            end;
            v311.is_in_guild = function(_) --[[ Name: is_in_guild ]] --[[ Line: 1242 ]]
                --[[ Upvalues: (ref 1): p_u_310, (ref 2): v_u_9 ]]
                return p_u_310 ~= v_u_9:not_in_guild_id();
            end;
            v311.set_guild_id = function(_, p312) --[[ Name: set_guild_id ]] --[[ Line: 1244 ]]
                --[[ Upvalues: (ref 1): v_u_6, (ref 2): p_u_310 ]]
                v_u_6:is_int(p312)
                p_u_310 = p312
            end;
            v311.to_table = function(_) --[[ Name: to_table ]] --[[ Line: 1249 ]]
                --[[ Upvalues: (copy 1): p_u_309, (ref 2): p_u_310 ]]
                return {
                    ["PlayerID"] = p_u_309,
                    ["GuildID"] = p_u_310
                };
            end;
            return v311;
        end;
        v_u_308.from_table = function(_, p313) --[[ Name: from_table ]] --[[ Line: 1259 ]]
            --[[ Upvalues: (copy 1): v_u_308 ]]
            return v_u_308:new(p313.PlayerID, p313.GuildID);
        end;
        local function _(p314) --[[ Name: player_guild_info_ds_key ]] --[[ Line: 1263 ]]
            return string.format("player%d_guild", p314);
        end;
        v_u_16.datastore_update_player_guild_info_no_cooldown = function(_, p_u_315, p_u_316, p_u_317) --[[ Name: datastore_update_player_guild_info_no_cooldown ]] --[[ Line: 1265 ]]
            --[[ Upvalues: (copy 1): p_u_15, (copy 2): v_u_307, (copy 3): v_u_308, (ref 4): v_u_9 ]]
            local v318 = string.format("player%d_guild", p_u_315)
            local v_u_319 = nil
            p_u_15._datastore_api:do_datastore_update(v_u_307, v318, function(p320) --[[ Line: 1271 ]]
                --[[ Upvalues: (ref 1): v_u_319, (ref 2): v_u_308, (copy 3): p_u_315, (ref 4): v_u_9, (copy 5): p_u_316 ]]
                if typeof(p320) == "table" then
                    v_u_319 = v_u_308:from_table(p320)
                else
                    v_u_319 = v_u_308:new(p_u_315, v_u_9:not_in_guild_id())
                end;
                p_u_316(v_u_319)
                return v_u_319:to_table();
            end, function() --[[ Line: 1282 ]]
                --[[ Upvalues: (copy 1): p_u_317, (ref 2): v_u_319 ]]
                if p_u_317 then
                    p_u_317(v_u_319)
                end;
            end)
        end;
        v_u_16.datastore_get_player_guild_info = function(_, p_u_321, p_u_322) --[[ Name: datastore_get_player_guild_info ]] --[[ Line: 1288 ]]
            --[[ Upvalues: (copy 1): v_u_305, (copy 2): p_u_15, (copy 3): v_u_307, (copy 4): v_u_308, (ref 5): v_u_9 ]]
            local v_u_323 = string.format("player%d_guild", p_u_321)
            v_u_305:queue_key_request(p_u_321, function() --[[ Line: 1291 ]]
                --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_307, (copy 3): v_u_323, (ref 4): v_u_308, (copy 5): p_u_321, (ref 6): v_u_9, (copy 7): p_u_322 ]]
                p_u_15._datastore_api:do_datastore_get(v_u_307, v_u_323, function(p324, p325) --[[ Line: 1295 ]]
                    --[[ Upvalues: (ref 1): v_u_308, (ref 2): p_u_321, (ref 3): v_u_9, (ref 4): p_u_322 ]]
                    local v326 = v_u_308:new(p_u_321, v_u_9:not_in_guild_id())
                    if typeof(p325) == "table" then
                        v326 = v_u_308:from_table(p325)
                    end;
                    p_u_322(p324, v326)
                end)
            end)
        end;
        local function f_clean_write_copy_of_guild_data(p327) --[[ Name: clean_write_copy_of_guild_data ]] --[[ Line: 1307 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            local v328 = v_u_10:from_table(p327:to_table())
            v328:set_default_contribution_entry_info()
            for _, v329 in v328:get_member_infos():key_itr() do
                v329:set_current_week_contribution_points(0)
                v329:set_last_week_contribution_points(0)
            end;
            return v328;
        end;
        local v_u_330 = s_DataStoreService_0:GetDataStore("GuildData")
        local function _(p331) --[[ Name: guild_data_ds_key ]] --[[ Line: 1328 ]]
            return string.format("guild%d_data", p331);
        end;
        v_u_16.datastore_update_guild_data = function(_, p332, p_u_333, p_u_334, p_u_335) --[[ Name: datastore_update_guild_data ]] --[[ Line: 1330 ]]
            --[[ Upvalues: (copy 1): v_u_306, (copy 2): p_u_15, (copy 3): v_u_330, (ref 4): v_u_1, (ref 5): v_u_10, (ref 6): v_u_5, (copy 7): f_clean_write_copy_of_guild_data, (ref 8): v_u_9 ]]
            local v_u_336 = string.format("guild%d_data", p_u_333)
            v_u_306:queue_key_request(p332, function() --[[ Line: 1332 ]]
                --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_330, (copy 3): v_u_336, (ref 4): v_u_1, (ref 5): v_u_10, (copy 6): p_u_333, (ref 7): v_u_5, (copy 8): p_u_334, (ref 9): f_clean_write_copy_of_guild_data, (ref 10): v_u_9, (copy 11): p_u_335 ]]
                local v_u_337 = true
                local v_u_338 = nil
                p_u_15._datastore_api:do_datastore_update(v_u_330, v_u_336, function(p339) --[[ Line: 1338 ]]
                    --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_338, (ref 3): v_u_10, (ref 4): p_u_333, (ref 5): v_u_5, (ref 6): p_u_334, (ref 7): v_u_337, (ref 8): f_clean_write_copy_of_guild_data, (ref 9): v_u_9 ]]
                    if typeof(p339) == "table" and p339.Version == 2 then
                        v_u_1:warnf("BAD MIGRATION(datastore_update_guild_data) (Missing parent GuildData)")
                        p339 = {
                            ["GuildData"] = p339
                        }
                    end;
                    if typeof(p339) == "table" and p339.GuildData then
                        v_u_338 = v_u_10:from_table(p339.GuildData)
                    else
                        v_u_338 = v_u_10:new(p_u_333)
                    end;
                    if v_u_5:ptry(function() --[[ Line: 1355 ]]
                        --[[ Upvalues: (ref 1): p_u_334, (ref 2): v_u_338 ]]
                        p_u_334(v_u_338)
                    end) ~= true then
                        v_u_337 = false
                        return nil;
                    end;
                    local v340 = f_clean_write_copy_of_guild_data(v_u_338)
                    if v_u_9:validate_guild_data(v340) == true then
                        return {
                            ["GuildData"] = v340:to_table()
                        };
                    end;
                    v_u_1:warnf("ServerGuildDatastoreManager:datastore_update_guild_data validate_guild_data_failed")
                    v_u_337 = false
                    return nil;
                end, function() --[[ Line: 1377 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_335, (ref 3): v_u_337, (ref 4): v_u_338 ]]
                    v_u_5:spawn(function() --[[ Line: 1378 ]]
                        --[[ Upvalues: (ref 1): p_u_335, (ref 2): v_u_337, (ref 3): v_u_338 ]]
                        p_u_335(v_u_337, v_u_338)
                    end)
                end)
            end)
        end;
        v_u_16.datastore_get_guild_data = function(_, p_u_341, p_u_342) --[[ Name: datastore_get_guild_data ]] --[[ Line: 1386 ]]
            --[[ Upvalues: (copy 1): p_u_15, (copy 2): v_u_330, (ref 3): v_u_1, (ref 4): v_u_10 ]]
            p_u_15._datastore_api:do_datastore_get_no_cache(v_u_330, string.format("guild%d_data", p_u_341), function(_, p343) --[[ Line: 1391 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_10, (copy 3): p_u_341, (copy 4): p_u_342 ]]
                if typeof(p343) == "table" and p343.Version == 2 then
                    v_u_1:warnf("BAD MIGRATION(datastore_get_guild_data) (Missing parent GuildData)")
                    p343 = {
                        ["GuildData"] = p343
                    }
                end;
                local v344 = v_u_10:new(p_u_341)
                local v345
                if typeof(p343) == "table" and p343.GuildData then
                    v344 = v_u_10:from_table(p343.GuildData)
                    v345 = true
                else
                    v345 = false
                end;
                p_u_342(v345, v344)
            end)
        end;
        local function _() --[[ Name: get_guild_alloc_ds_key ]] --[[ Line: 1410 ]]
            return "guild_alloc";
        end;
        v_u_16.datastore_alloc_guild_id_no_cooldown = function(_, p_u_346) --[[ Name: datastore_alloc_guild_id_no_cooldown ]] --[[ Line: 1418 ]]
            --[[ Upvalues: (ref 1): v_u_9, (copy 2): p_u_15, (copy 3): v_u_330 ]]
            local v_u_347 = v_u_9:not_in_guild_id()
            p_u_15._datastore_api:do_datastore_update(v_u_330, "guild_alloc", function(p348) --[[ Line: 1423 ]]
                --[[ Upvalues: (ref 1): v_u_347 ]]
                local v349 = (typeof(p348) ~= "table" or typeof(p348.NextGuildID) ~= "number") and 1 or p348.NextGuildID
                v_u_347 = v349
                return {
                    ["NextGuildID"] = v349 + 1
                };
            end, function() --[[ Line: 1433 ]]
                --[[ Upvalues: (copy 1): p_u_346, (ref 2): v_u_347 ]]
                p_u_346(v_u_347)
            end)
        end;
        v_u_16.datastore_alloc_guild_id_write = function(_, p_u_350) --[[ Name: datastore_alloc_guild_id_write ]] --[[ Line: 1439 ]]
            --[[ Upvalues: (copy 1): p_u_15, (copy 2): v_u_330 ]]
            p_u_15._datastore_api:do_datastore_update(v_u_330, "guild_alloc", function(_) --[[ Line: 1443 ]]
                --[[ Upvalues: (copy 1): p_u_350 ]]
                return {
                    ["NextGuildID"] = p_u_350
                };
            end)
        end;
        local v_u_351 = {}
        v_u_351.new = function(_, p_u_352, p_u_353) --[[ Name: new ]] --[[ Line: 1464 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_3, (ref 3): v_u_2, (ref 4): v_u_11, (copy 5): v_u_351 ]]
            local v354 = {}
            local v_u_355 = v_u_10.WeekContributionEntry:default_value()
            local v_u_356 = v_u_3:new()
            v354.set_week_contribution_entry = function(_, p357) --[[ Name: set_week_contribution_entry ]] --[[ Line: 1470 ]]
                --[[ Upvalues: (ref 1): v_u_355 ]]
                v_u_355 = p357
            end;
            v354.get_guildid = function(_) --[[ Name: get_guildid ]] --[[ Line: 1472 ]]
                --[[ Upvalues: (copy 1): p_u_352 ]]
                return p_u_352;
            end;
            v354.get_week_id = function(_) --[[ Name: get_week_id ]] --[[ Line: 1473 ]]
                --[[ Upvalues: (copy 1): p_u_353 ]]
                return p_u_353;
            end;
            v354.get_week_contribution_entry = function(_) --[[ Name: get_week_contribution_entry ]] --[[ Line: 1474 ]]
                --[[ Upvalues: (ref 1): v_u_355 ]]
                return v_u_355;
            end;
            v354.get_rbxid_to_member_info_with_contribution = function(_) --[[ Name: get_rbxid_to_member_info_with_contribution ]] --[[ Line: 1475 ]]
                --[[ Upvalues: (copy 1): v_u_356 ]]
                return v_u_356;
            end;
            v354.get_member_info_list_copy = function(_) --[[ Name: get_member_info_list_copy ]] --[[ Line: 1477 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_3, (copy 3): v_u_356 ]]
                local v_u_358 = v_u_2:new()
                v_u_3:for_each_key_value_sorted(v_u_356, function(_, p359) --[[ Line: 1479 ]]
                    --[[ Upvalues: (copy 1): v_u_358 ]]
                    v_u_358:push_back(p359)
                end)
                return v_u_358;
            end;
            v354.get_or_create_member_info_for_rbxid = function(_, p360) --[[ Name: get_or_create_member_info_for_rbxid ]] --[[ Line: 1485 ]]
                --[[ Upvalues: (copy 1): v_u_356, (ref 2): v_u_10, (ref 3): v_u_11 ]]
                if not v_u_356:contains(p360) then
                    v_u_356:add(p360, v_u_10.MemberInfo:new(p360, "", v_u_11.Member))
                end;
                return v_u_356:get(p360);
            end;
            v354.write_as_current_week_to_guild_data = function(p361, p362) --[[ Name: write_as_current_week_to_guild_data ]] --[[ Line: 1492 ]]
                --[[ Upvalues: (ref 1): v_u_351 ]]
                v_u_351:write_current_week_ds_guild_week_contribution_info_to_guild_data(p361, p362)
            end;
            v354.write_as_last_week_to_guild_data = function(p363, p364) --[[ Name: write_as_last_week_to_guild_data ]] --[[ Line: 1496 ]]
                --[[ Upvalues: (ref 1): v_u_351 ]]
                v_u_351:write_last_week_ds_guild_week_contribution_info_to_guild_data(p363, p364)
            end;
            v354.to_table = function(p365) --[[ Name: to_table ]] --[[ Line: 1500 ]]
                --[[ Upvalues: (copy 1): p_u_352, (copy 2): p_u_353, (ref 3): v_u_355 ]]
                local v366 = {}
                for _, v367 in p365:get_member_info_list_copy():key_itr() do
                    v366[#v366 + 1] = v367:to_table()
                end;
                return {
                    ["GuildId"] = p_u_352,
                    ["WeekId"] = p_u_353,
                    ["WeekContributionEntry"] = v_u_355:to_table(),
                    ["MemberInfoWithContribution"] = v366
                };
            end;
            return v354;
        end;
        v_u_351.from_table = function(_, p368) --[[ Name: from_table ]] --[[ Line: 1518 ]]
            --[[ Upvalues: (copy 1): v_u_351, (ref 2): v_u_10 ]]
            local v369 = v_u_351:new(p368.GuildId, p368.WeekId)
            v369:set_week_contribution_entry(v_u_10.WeekContributionEntry:from_table(p368.WeekContributionEntry))
            for _, v370 in ipairs(p368.MemberInfoWithContribution) do
                v369:get_rbxid_to_member_info_with_contribution():add(v370.RbxId, v_u_10.MemberInfo:from_table(v370))
            end;
            return v369;
        end;
        local function f_write_ds_guild_week_contribution_info_to_guild_data(p371, p372, p373, p374) --[[ Name: write_ds_guild_week_contribution_info_to_guild_data ]] --[[ Line: 1527 ]]
            --[[ Upvalues: (ref 1): v_u_3 ]]
            local v375 = v_u_3:new()
            for _, v376 in p371:get_member_infos():key_itr() do
                v375:add(v376:get_rbxid(), v376)
            end;
            for v377, v378 in v375:key_itr() do
                if p372:get_rbxid_to_member_info_with_contribution():contains(v377) then
                    p373(v378, (p372:get_rbxid_to_member_info_with_contribution():get(v377)))
                else
                    p374(v378)
                end;
            end;
        end;
        v_u_351.write_current_week_ds_guild_week_contribution_info_to_guild_data = function(_, p379, p380) --[[ Name: write_current_week_ds_guild_week_contribution_info_to_guild_data ]] --[[ Line: 1543 ]]
            --[[ Upvalues: (copy 1): f_write_ds_guild_week_contribution_info_to_guild_data ]]
            p380:set_current_week_contribution_entry(p379:get_week_contribution_entry())
            f_write_ds_guild_week_contribution_info_to_guild_data(p380, p379, function(p381, p382) --[[ Line: 1548 ]]
                p381:set_current_week_contribution_points(p382:get_current_week_contribution_points())
            end, function(p383) --[[ Line: 1551 ]]
                p383:set_current_week_contribution_points(0)
            end)
        end;
        v_u_351.write_last_week_ds_guild_week_contribution_info_to_guild_data = function(_, p384, p385) --[[ Name: write_last_week_ds_guild_week_contribution_info_to_guild_data ]] --[[ Line: 1557 ]]
            --[[ Upvalues: (copy 1): f_write_ds_guild_week_contribution_info_to_guild_data ]]
            p385:set_last_week_contribution_entry(p384:get_week_contribution_entry())
            f_write_ds_guild_week_contribution_info_to_guild_data(p385, p384, function(p386, p387) --[[ Line: 1562 ]]
                p386:set_last_week_contribution_points(p387:get_current_week_contribution_points())
            end, function(p388) --[[ Line: 1565 ]]
                p388:set_last_week_contribution_points(0)
            end)
        end;
        local v_u_389 = s_DataStoreService_0:GetDataStore("GuildWeekContr")
        local function _(p390, p391) --[[ Name: guild_week_contribution_ds_key ]] --[[ Line: 1573 ]]
            return string.format("guild%d_week%d_contr", p390, p391);
        end;
        v_u_16.datastore_get_guild_week_contribution_info_no_cooldown = function(_, p_u_392, p_u_393, p_u_394) --[[ Name: datastore_get_guild_week_contribution_info_no_cooldown ]] --[[ Line: 1575 ]]
            --[[ Upvalues: (copy 1): p_u_15, (copy 2): v_u_389, (copy 3): v_u_351 ]]
            p_u_15._datastore_api:do_datastore_get(v_u_389, string.format("guild%d_week%d_contr", p_u_392, p_u_393), function(_, p395) --[[ Line: 1580 ]]
                --[[ Upvalues: (ref 1): v_u_351, (copy 2): p_u_392, (copy 3): p_u_393, (copy 4): p_u_394 ]]
                local v396 = v_u_351:new(p_u_392, p_u_393)
                if typeof(p395) == "table" then
                    v396 = v_u_351:from_table(p395)
                end;
                p_u_394(v396)
            end)
        end;
        v_u_16.datastore_update_guild_week_contribution_info = function(_, p397, p_u_398, p_u_399, p_u_400, p_u_401) --[[ Name: datastore_update_guild_week_contribution_info ]] --[[ Line: 1590 ]]
            --[[ Upvalues: (copy 1): v_u_306, (copy 2): p_u_15, (copy 3): v_u_389, (copy 4): v_u_351, (ref 5): v_u_5 ]]
            local v_u_402 = string.format("guild%d_week%d_contr", p_u_398, p_u_399)
            v_u_306:queue_key_request(p397, function() --[[ Line: 1592 ]]
                --[[ Upvalues: (ref 1): p_u_15, (ref 2): v_u_389, (copy 3): v_u_402, (ref 4): v_u_351, (copy 5): p_u_398, (copy 6): p_u_399, (ref 7): v_u_5, (copy 8): p_u_400, (copy 9): p_u_401 ]]
                local v_u_403 = true
                local v_u_404 = nil
                p_u_15._datastore_api:do_datastore_update(v_u_389, v_u_402, function(p405) --[[ Line: 1598 ]]
                    --[[ Upvalues: (ref 1): v_u_404, (ref 2): v_u_351, (ref 3): p_u_398, (ref 4): p_u_399, (ref 5): v_u_5, (ref 6): p_u_400, (ref 7): v_u_403 ]]
                    if typeof(p405) == "table" then
                        v_u_404 = v_u_351:from_table(p405)
                    else
                        v_u_404 = v_u_351:new(p_u_398, p_u_399)
                    end;
                    if v_u_5:ptry(function() --[[ Line: 1605 ]]
                        --[[ Upvalues: (ref 1): p_u_400, (ref 2): v_u_404 ]]
                        p_u_400(v_u_404)
                    end) ~= true then
                        v_u_403 = false
                        return nil;
                    end;
                    local v406 = 0
                    for _, v407 in v_u_404:get_rbxid_to_member_info_with_contribution():key_itr() do
                        v406 = v406 + v407:get_current_week_contribution_points()
                    end;
                    v_u_404:get_week_contribution_entry():set_contribution_points(v406)
                    v_u_404:get_week_contribution_entry():set_rank(0)
                    v_u_404:get_week_contribution_entry():set_total_entries(0)
                    return v_u_404:to_table();
                end, function() --[[ Line: 1625 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_401, (ref 3): v_u_403, (ref 4): v_u_404 ]]
                    v_u_5:spawn(function() --[[ Line: 1626 ]]
                        --[[ Upvalues: (ref 1): p_u_401, (ref 2): v_u_403, (ref 3): v_u_404 ]]
                        p_u_401(v_u_403, v_u_404)
                    end)
                end)
            end)
        end;
        local function _(p408, p409) --[[ Name: daily_archive_guild_data_key_for_guild_id_day_id ]] --[[ Line: 1634 ]]
            return string.format("agd_%d_%d", p408, p409 % 25);
        end;
        local v_u_410 = nil
        pcall(function() --[[ Line: 1640 ]]
            --[[ Upvalues: (ref 1): v_u_410, (ref 2): s_DataStoreService_0 ]]
            v_u_410 = s_DataStoreService_0:GetDataStore("GuildDataDailyArchive")
        end)
        local function _(p_u_411, p_u_412) --[[ Name: opt_write_to_full_contribution_guild_data_archive ]] --[[ Line: 1644 ]]
            --[[ Upvalues: (copy 1): v_u_17, (ref 2): v_u_5, (copy 3): p_u_15, (ref 4): v_u_410 ]]
            if v_u_17:is_on_cooldown(p_u_411) ~= true then
                v_u_17:add_cooldown_to_id(p_u_411, 300)
                v_u_5:spawn(function() --[[ Line: 1648 ]]
                    --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_15, (ref 3): v_u_410, (copy 4): p_u_411, (copy 5): p_u_412 ]]
                    v_u_5:wait(30)
                    p_u_15._datastore_api:do_datastore_set(v_u_410, string.format("agd_%d_%d", p_u_411, p_u_15._api:get_day_id() % 25), {
                        ["DayID"] = p_u_15._api:get_day_id(),
                        ["GuildData"] = p_u_412:to_table()
                    }, function(_, _) end)
                end)
            end;
        end;
        local v_u_418 = v_u_5:id_to_request_cache(300, v_u_351:new(v_u_9:not_in_guild_id(), -1), function(p_u_413, p_u_414) --[[ Line: 1666 ]]
            --[[ Upvalues: (copy 1): p_u_15, (copy 2): v_u_389, (copy 3): v_u_351 ]]
            p_u_15._datastore_api:do_datastore_get(v_u_389, string.format("guild%d_week%d_contr", p_u_413[1], p_u_413[2]), function(_, p415) --[[ Line: 1670 ]]
                --[[ Upvalues: (ref 1): v_u_351, (copy 2): p_u_413, (copy 3): p_u_414 ]]
                local v416 = v_u_351:new(p_u_413[1], p_u_413[2])
                if typeof(p415) == "table" then
                    v416 = v_u_351:from_table(p415)
                end;
                p_u_414(v416)
            end)
        end, function(p417) --[[ Line: 1679 ]]
            return string.format("%d_%d", p417[1], p417[2]);
        end)
        v_u_16.datastore_read_full_contribution_info_to_data_no_cooldown = function(p_u_419, p_u_420, p_u_421, p_u_422, p_u_423) --[[ Name: datastore_read_full_contribution_info_to_data_no_cooldown ]] --[[ Line: 1684 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): p_u_15, (copy 3): v_u_389, (copy 4): v_u_351, (copy 5): v_u_418, (copy 6): v_u_17, (ref 7): v_u_5, (ref 8): v_u_410 ]]
            local v_u_424 = v_u_7.Builder:new()
            v_u_424:begin()
            p_u_15._datastore_api:do_datastore_get_no_cache(v_u_389, string.format("guild%d_week%d_contr", p_u_420, p_u_421), function(_, p425) --[[ Line: 1691 ]]
                --[[ Upvalues: (ref 1): v_u_351, (copy 2): p_u_420, (copy 3): p_u_421, (copy 4): p_u_422, (copy 5): v_u_424, (copy 6): p_u_419 ]]
                local v426 = v_u_351:new(p_u_420, p_u_421)
                if typeof(p425) == "table" then
                    v426 = v_u_351:from_table(p425)
                end;
                v426:write_as_current_week_to_guild_data(p_u_422)
                if p_u_422:get_current_week_contribution_entry():is_entered() ~= true then
                    return v_u_424:finish();
                end;
                p_u_419:get_datastore_cached_current_week_leaderboard(function(p427) --[[ Line: 1702 ]]
                    --[[ Upvalues: (ref 1): p_u_420, (ref 2): p_u_422, (ref 3): v_u_424 ]]
                    local v428 = p427:count()
                    for v429, v430 in p427:key_itr() do
                        if v430:get_guildid() == p_u_420 then
                            v428 = v429
                            break;
                        end;
                    end;
                    p_u_422:get_current_week_contribution_entry():set_rank_from_list_index(v428)
                    p_u_422:get_current_week_contribution_entry():set_total_entries(p427:count())
                    return v_u_424:finish();
                end)
            end)
            v_u_424:begin()
            v_u_418:id_get_cached({ p_u_420, p_u_421 - 1 }, function(p431) --[[ Line: 1720 ]]
                --[[ Upvalues: (copy 1): p_u_422, (copy 2): v_u_424, (copy 3): p_u_419, (copy 4): p_u_420 ]]
                p431:write_as_last_week_to_guild_data(p_u_422)
                if p_u_422:get_last_week_contribution_entry():is_entered() ~= true then
                    return v_u_424:finish();
                end;
                p_u_419:get_datastore_cached_last_week_leaderboard(function(p432) --[[ Line: 1728 ]]
                    --[[ Upvalues: (ref 1): p_u_420, (ref 2): p_u_422, (ref 3): v_u_424 ]]
                    local v433 = p432:count()
                    for v434, v435 in p432:key_itr() do
                        if v435:get_guildid() == p_u_420 then
                            v433 = v434
                            break;
                        end;
                    end;
                    p_u_422:get_last_week_contribution_entry():set_rank_from_list_index(v433)
                    p_u_422:get_last_week_contribution_entry():set_total_entries(p432:count())
                    return v_u_424:finish();
                end)
            end)
            v_u_424:wait_for_finish(function() --[[ Line: 1743 ]]
                --[[ Upvalues: (copy 1): p_u_423, (copy 2): p_u_422, (copy 3): p_u_420, (ref 4): v_u_17, (ref 5): v_u_5, (ref 6): p_u_15, (ref 7): v_u_410 ]]
                p_u_423(p_u_422)
                local v_u_436 = p_u_420
                local v_u_437 = p_u_422
                if v_u_17:is_on_cooldown(v_u_436) ~= true then
                    v_u_17:add_cooldown_to_id(v_u_436, 300)
                    v_u_5:spawn(function() --[[ Line: 1648 ]]
                        --[[ Upvalues: (ref 1): v_u_5, (ref 2): p_u_15, (ref 3): v_u_410, (copy 4): v_u_436, (copy 5): v_u_437 ]]
                        v_u_5:wait(30)
                        p_u_15._datastore_api:do_datastore_set(v_u_410, string.format("agd_%d_%d", v_u_436, p_u_15._api:get_day_id() % 25), {
                            ["DayID"] = p_u_15._api:get_day_id(),
                            ["GuildData"] = v_u_437:to_table()
                        }, function(_, _) end)
                    end)
                end;
            end)
        end;
        v_u_16.datastore_read_full_contribution_info_to_data = function(p_u_438, p439, p_u_440, p_u_441, p_u_442, p_u_443) --[[ Name: datastore_read_full_contribution_info_to_data ]] --[[ Line: 1749 ]]
            --[[ Upvalues: (copy 1): v_u_305 ]]
            v_u_305:queue_key_request(p439, function() --[[ Line: 1750 ]]
                --[[ Upvalues: (copy 1): p_u_438, (copy 2): p_u_440, (copy 3): p_u_441, (copy 4): p_u_442, (copy 5): p_u_443 ]]
                p_u_438:datastore_read_full_contribution_info_to_data_no_cooldown(p_u_440, p_u_441, p_u_442, p_u_443)
            end)
        end;
        local v_u_444 = s_DataStoreService_0:GetDataStore("GuildWeekContrLB")
        local function _(p445) --[[ Name: guild_week_contribution_leaderboard_ds_key ]] --[[ Line: 1773 ]]
            return string.format("guild_lb_week%d", p445);
        end;
        local function f_DEBUG_guildid_to_datas(p446) --[[ Name: DEBUG_guildid_to_datas ]] --[[ Line: 1776 ]]
            --[[ Upvalues: (ref 1): v_u_13 ]]
            local v447 = v_u_13:new()
            for _, v448 in p446:key_itr() do
                v447:push_back_to(v448:get_guildid(), v448)
            end;
            return v447;
        end;
        local function f_DEBUG_validate_guild_data_list_has_duplicates(p449) --[[ Name: DEBUG_validate_guild_data_list_has_duplicates ]] --[[ Line: 1784 ]]
            --[[ Upvalues: (copy 1): f_DEBUG_guildid_to_datas ]]
            local v450 = false
            for _, v451 in f_DEBUG_guildid_to_datas(p449):key_itr() do
                if v451:count() > 1 then
                    v450 = true
                end;
            end;
            return v450;
        end;
        local function f_fn_sort_guild_data(p452, p453) --[[ Name: fn_sort_guild_data ]] --[[ Line: 1795 ]]
            local v454 = p452:get_current_week_contribution_entry():get_contribution_points()
            local v455 = p453:get_current_week_contribution_entry():get_contribution_points()
            if v454 == v455 then
                return p452:get_guildid() > p453:get_guildid();
            else
                return v455 < v454;
            end;
        end;
        local function f_DEBUG_deduplicate_guild_data_list(p456, p_u_457) --[[ Name: DEBUG_deduplicate_guild_data_list ]] --[[ Line: 1805 ]]
            --[[ Upvalues: (copy 1): f_DEBUG_guildid_to_datas, (ref 2): v_u_5, (ref 3): v_u_3, (copy 4): p_u_15, (ref 5): v_u_14, (copy 6): f_fn_sort_guild_data ]]
            local v_u_458 = f_DEBUG_guildid_to_datas(p456)
            local v_u_459 = ""
            pcall(function() --[[ Line: 1809 ]]
                --[[ Upvalues: (ref 1): v_u_459, (ref 2): v_u_5, (copy 3): p_u_457 ]]
                v_u_459 = v_u_5:table_to_string(p_u_457:to_table())
            end)
            local v_u_460 = ""
            pcall(function() --[[ Line: 1814 ]]
                --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_458, (ref 3): v_u_460, (ref 4): v_u_5 ]]
                local v461 = v_u_3:new()
                for v462, v463 in v_u_458:key_itr() do
                    v461:add(v462, v463:count())
                end;
                v_u_460 = v_u_5:table_to_string(v461:get_table())
            end)
            p_u_15._error_report:error_debug_log(string.format("guild_data_list---%s---\nupdating_guild_data---%s---", v_u_460, v_u_459), v_u_14.LOG_ERROR_GUILD_DATASTORE)
            for _, v464 in v_u_458:key_itr() do
                if v464:count() > 1 then
                    v464:sort(f_fn_sort_guild_data)
                    local v465 = v464:get(1)
                    v464:clear()
                    v464:push_back(v465)
                end;
            end;
            p456:clear()
            for _, v466 in v_u_458:key_itr() do
                p456:push_back(v466:get(1))
            end;
            p456:sort(f_fn_sort_guild_data)
        end;
        local function f_datastore_update_guild_contribution_leaderboard_from_post_write_current_week_to_guild_data_no_cooldown(p_u_467, p_u_468, p_u_469) --[[ Name: datastore_update_guild_contribution_leaderboard_from_post_write_current_week_to_guild_data_no_cooldown ]] --[[ Line: 1844 ]]
            --[[ Upvalues: (ref 1): v_u_2, (copy 2): p_u_15, (copy 3): v_u_444, (ref 4): v_u_10, (copy 5): f_fn_sort_guild_data, (copy 6): f_DEBUG_validate_guild_data_list_has_duplicates, (copy 7): f_DEBUG_deduplicate_guild_data_list, (ref 8): v_u_14 ]]
            local v_u_470 = p_u_468:get_guildid()
            if p_u_468:get_current_week_contribution_entry():is_entered() ~= true then
                return p_u_469(v_u_2:new());
            end;
            local v471 = string.format("guild_lb_week%d", p_u_467)
            local v_u_472 = v_u_2:new()
            p_u_15._datastore_api:do_datastore_update(v_u_444, v471, function(p473) --[[ Line: 1857 ]]
                --[[ Upvalues: (ref 1): v_u_472, (ref 2): v_u_2, (ref 3): v_u_10, (copy 4): v_u_470, (copy 5): p_u_468, (ref 6): f_fn_sort_guild_data, (ref 7): f_DEBUG_validate_guild_data_list_has_duplicates, (ref 8): f_DEBUG_deduplicate_guild_data_list, (ref 9): p_u_15, (ref 10): v_u_14, (copy 11): p_u_467 ]]
                v_u_472 = v_u_2:new()
                if typeof(p473) == "table" and type(p473.ContributionLeaderboard) == "table" then
                    for _, v474 in ipairs(p473.ContributionLeaderboard) do
                        v_u_472:push_back(v_u_10:from_table(v474))
                    end;
                end;
                v_u_2:remove_if(v_u_472, function(p475) --[[ Line: 1865 ]]
                    --[[ Upvalues: (ref 1): v_u_470 ]]
                    return p475:get_guildid() == v_u_470;
                end)
                v_u_472:push_back(p_u_468)
                v_u_472:sort(f_fn_sort_guild_data)
                if f_DEBUG_validate_guild_data_list_has_duplicates(v_u_472, p_u_468) == true then
                    f_DEBUG_deduplicate_guild_data_list(v_u_472, p_u_468)
                end;
                if v_u_472:count() > 1000 then
                    p_u_15._error_report:error_debug_log(string.format("datastore_update_guild_contribution_leaderboard_from_post_write_current_week_to_guild_data_no_cooldown count over limit(%d)", v_u_472:count()), v_u_14.LOG_ERROR_GUILD_DATASTORE)
                    while v_u_472:count() > 1000 do
                        v_u_472:pop_back()
                    end;
                end;
                for v476, v477 in v_u_472:key_itr() do
                    v477:get_current_week_contribution_entry():set_rank_from_list_index(v476)
                    v477:get_current_week_contribution_entry():set_total_entries(v_u_472:count())
                end;
                local v478 = v_u_2:new()
                for _, v479 in v_u_472:key_itr() do
                    v478:push_back(v479:to_table())
                end;
                return {
                    ["WeekID"] = p_u_467,
                    ["ContributionLeaderboard"] = v478:get_table()
                };
            end, function() --[[ Line: 1904 ]]
                --[[ Upvalues: (copy 1): p_u_469, (ref 2): v_u_472 ]]
                if p_u_469 then
                    p_u_469(v_u_472)
                end;
            end)
        end;
        v_u_16.datastore_guild_data_and_week_contribution_info_update_contribution_leaderboard = function(_, p480, p481, p_u_482) --[[ Name: datastore_guild_data_and_week_contribution_info_update_contribution_leaderboard ]] --[[ Line: 1910 ]]
            --[[ Upvalues: (copy 1): f_clean_write_copy_of_guild_data, (copy 2): f_datastore_update_guild_contribution_leaderboard_from_post_write_current_week_to_guild_data_no_cooldown ]]
            local v483 = f_clean_write_copy_of_guild_data(p480)
            p481:write_as_current_week_to_guild_data(v483)
            f_datastore_update_guild_contribution_leaderboard_from_post_write_current_week_to_guild_data_no_cooldown(p481:get_week_id(), v483, function(p484) --[[ Line: 1916 ]]
                --[[ Upvalues: (copy 1): p_u_482 ]]
                if p_u_482 then
                    p_u_482(p484)
                end;
            end)
        end;
        v_u_16.datastore_update_guild_contribution_leaderboard_from_ds_guild_week_contribution_info_no_cooldown = function(p_u_485, p_u_486, p_u_487) --[[ Name: datastore_update_guild_contribution_leaderboard_from_ds_guild_week_contribution_info_no_cooldown ]] --[[ Line: 1922 ]]
            --[[ Upvalues: (ref 1): v_u_2 ]]
            p_u_485:datastore_get_guild_data(p_u_486:get_guildid(), function(p488, p489) --[[ Line: 1925 ]]
                --[[ Upvalues: (copy 1): p_u_487, (ref 2): v_u_2, (copy 3): p_u_485, (copy 4): p_u_486 ]]
                if p488 == true then
                    p_u_485:datastore_guild_data_and_week_contribution_info_update_contribution_leaderboard(p489, p_u_486, p_u_487)
                elseif p_u_487 then
                    p_u_487(v_u_2:new())
                end;
            end)
        end;
        v_u_16.datastore_update_guild_contribution_leaderboard_from_guild_data_no_cooldown = function(p_u_490, p_u_491, p_u_492) --[[ Name: datastore_update_guild_contribution_leaderboard_from_guild_data_no_cooldown ]] --[[ Line: 1935 ]]
            --[[ Upvalues: (copy 1): p_u_15 ]]
            p_u_490:datastore_get_guild_week_contribution_info_no_cooldown(p_u_491:get_guildid(), p_u_15._api:get_week_id(), function(p493) --[[ Line: 1939 ]]
                --[[ Upvalues: (copy 1): p_u_490, (copy 2): p_u_491, (copy 3): p_u_492 ]]
                p_u_490:datastore_guild_data_and_week_contribution_info_update_contribution_leaderboard(p_u_491, p493, p_u_492)
            end)
        end;
        v_u_16.datastore_get_guild_contribution_leaderboard_no_cooldown = function(_, p494, p_u_495) --[[ Name: datastore_get_guild_contribution_leaderboard_no_cooldown ]] --[[ Line: 1945 ]]
            --[[ Upvalues: (copy 1): p_u_15, (copy 2): v_u_444, (ref 3): v_u_2, (ref 4): v_u_10 ]]
            p_u_15._datastore_api:do_datastore_get(v_u_444, string.format("guild_lb_week%d", p494), function(_, p496) --[[ Line: 1950 ]]
                --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_10, (copy 3): p_u_495 ]]
                local v497 = v_u_2:new()
                if typeof(p496) == "table" then
                    for _, v498 in pairs(p496.ContributionLeaderboard) do
                        v497:push_back(v_u_10:from_table(v498))
                    end;
                end;
                p_u_495(v497)
            end)
        end;
        local v_u_501 = v_u_5:request_cache(30, v_u_2:new(), function(p_u_499) --[[ Line: 1965 ]]
            --[[ Upvalues: (copy 1): v_u_16, (copy 2): p_u_15 ]]
            v_u_16:datastore_get_guild_contribution_leaderboard_no_cooldown(p_u_15._api:get_week_id(), function(p500) --[[ Line: 1968 ]]
                --[[ Upvalues: (copy 1): p_u_499 ]]
                p_u_499(p500)
            end)
        end)
        v_u_16.get_datastore_cached_current_week_leaderboard = function(_, p_u_502) --[[ Name: get_datastore_cached_current_week_leaderboard ]] --[[ Line: 1974 ]]
            --[[ Upvalues: (copy 1): v_u_501 ]]
            v_u_501:get_cached(function(p503) --[[ Line: 1975 ]]
                --[[ Upvalues: (copy 1): p_u_502 ]]
                p_u_502(p503)
            end)
        end;
        local v_u_506 = v_u_5:request_cache(600, v_u_2:new(), function(p_u_504) --[[ Line: 1983 ]]
            --[[ Upvalues: (copy 1): v_u_16, (copy 2): p_u_15 ]]
            v_u_16:datastore_get_guild_contribution_leaderboard_no_cooldown(p_u_15._api:get_week_id() - 1, function(p505) --[[ Line: 1986 ]]
                --[[ Upvalues: (copy 1): p_u_504 ]]
                p_u_504(p505)
            end)
        end)
        v_u_16.get_datastore_cached_last_week_leaderboard = function(_, p_u_507) --[[ Name: get_datastore_cached_last_week_leaderboard ]] --[[ Line: 1993 ]]
            --[[ Upvalues: (copy 1): v_u_506 ]]
            v_u_506:get_cached(function(p508) --[[ Line: 1994 ]]
                --[[ Upvalues: (copy 1): p_u_507 ]]
                p_u_507(p508)
            end)
        end;
        return v_u_16;
    end
};
