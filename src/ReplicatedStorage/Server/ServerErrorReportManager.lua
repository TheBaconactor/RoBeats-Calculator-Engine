-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:14 PM
-- Time elapsed: 12 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.ErrorReportBase)
require(game.ReplicatedStorage.Shared.Constants)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_7 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_9 = require(game.ReplicatedStorage.Shared.BuildConfig)
local s_DataStoreService_0 = game:GetService("DataStoreService")
return {
    ["new"] = function(_, p_u_10) --[[ Name: new ]] --[[ Line: 16 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_2, (copy 3): v_u_7, (copy 4): v_u_4, (copy 5): v_u_3, (copy 6): v_u_1, (copy 7): v_u_6, (copy 8): s_DataStoreService_0, (copy 9): v_u_8, (copy 10): v_u_9 ]]
        local v11 = v_u_5:new()
        local v_u_12 = v_u_2:new()
        local v_u_13 = v_u_2:new()
        v_u_2:new()
        local v_u_14 = v_u_7:new()
        local v_u_15 = v_u_7:new()
        local function f_cons() --[[ Name: cons ]] --[[ Line: 27 ]]
            --[[ Upvalues: (copy 1): p_u_10, (ref 2): v_u_4, (ref 3): v_u_3, (copy 4): v_u_13, (ref 5): v_u_1, (copy 6): v_u_14, (ref 7): v_u_6 ]]
            p_u_10._evt:wait_on_event(v_u_4.EVT_ErrorReport_ClientReportError, function(p16, p17, p18) --[[ Line: 28 ]]
                --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_13, (ref 3): v_u_1, (ref 4): v_u_14, (ref 5): p_u_10, (ref 6): v_u_6 ]]
                local v19 = v_u_3:hash_str(tostring(p17) .. tostring(p18))
                if v_u_13:contains(v19) then
                    return;
                else
                    v_u_13:add(v19, true)
                    v_u_1:warnf("EVT_ErrorReport_ClientReportError (%s) (%s)", p17, p18)
                    if not v_u_14:is_on_cooldown(p16.UserId) then
                        v_u_14:add_cooldown_to_id(p16.UserId, 10)
                        p_u_10._api:api_report_evt(v_u_6.ReportEvt_ClientError, p16.UserId, p_u_10._api:get_spid(), string.format("%s - %s", p17, p18))
                    end;
                end;
            end)
            p_u_10._evt:wait_on_event(v_u_4.EVT_EventReport_ClientReportEvent, function(p20, p21, p22, p23) --[[ Line: 42 ]]
                --[[ Upvalues: (ref 1): v_u_14, (ref 2): p_u_10 ]]
                local v24 = p22 == nil and 0 or p22
                local v25 = p23 == nil and "" or p23
                if not v_u_14:is_on_cooldown(p20.UserId) then
                    v_u_14:add_cooldown_to_id(p20.UserId, 10)
                    p_u_10._api:api_report_evt(p21, p20.UserId, v24, v25)
                end;
            end)
        end;
        v11.report_error_server = function(p26, p27) --[[ Name: report_error_server ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_3, (copy 3): v_u_12, (copy 4): p_u_10, (ref 5): v_u_6 ]]
            v_u_1:warnf("ServerErrorReportManager:report_error_server(%s, %s)", tostring(p27.Error), (tostring(p27.StackTrace)))
            local v28 = p26:player_name_sub(string.gsub(p27.Error, "%d+", "#"))
            local v29 = p26:player_name_sub(p27.StackTrace)
            local v30 = v_u_3:hash_str(v28 .. v29)
            if not v_u_12:contains(v30) then
                v_u_12:add(v30, true)
                p_u_10._api:api_report_evt(v_u_6.ReportEvt_ServerError, 0, p_u_10._api:get_spid(), string.format("%s - %s", v28, v29))
            end;
        end;
        v11.evt_report_error = function(p31, p32) --[[ Name: evt_report_error ]] --[[ Line: 66 ]]
            p31:report_error_server(p32)
        end;
        v11.report_web_error = function(_, p33, p34) --[[ Name: report_web_error ]] --[[ Line: 71 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("ServerErrorReportManager:report_web_error(%s, %s)", tostring(p33), (tostring(p34)))
        end;
        v11.update = function(_, p35) --[[ Name: update ]] --[[ Line: 81 ]]
            --[[ Upvalues: (copy 1): v_u_14, (copy 2): v_u_15 ]]
            v_u_14:update(p35)
            v_u_15:update(p35)
        end;
        local v_u_36 = s_DataStoreService_0:GetDataStore("ErrorDebugLog")
        local function _(p37) --[[ Name: dskey_for_log_id ]] --[[ Line: 100 ]]
            return string.format("Log_%d", p37);
        end;
        v11.error_debug_log = function(_, p_u_38, p_u_39) --[[ Name: error_debug_log ]] --[[ Line: 105 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_15, (ref 3): v_u_1, (copy 4): p_u_10, (copy 5): v_u_36, (ref 6): v_u_8, (ref 7): v_u_9 ]]
            if p_u_39 == nil then
                p_u_39 = v_u_5.LOG_DEFAULT
            end;
            if v_u_15:is_on_cooldown(p_u_39) then
                return v_u_1:warnf("ErrorDebugLog[%d]  Skipped (ON COOLDOWN): %s", p_u_39, p_u_38);
            end;
            v_u_15:add_cooldown_to_id(p_u_39, 0.5)
            p_u_10._datastore_api:do_datastore_update(v_u_36, string.format("Log_%d", p_u_39), function(p40) --[[ Line: 117 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_9, (copy 3): p_u_38 ]]
                local v41 = v_u_8:new()
                if typeof(p40) == "table" then
                    v41 = v_u_8:new(p40)
                end;
                v41:push_back(string.format("[%s] Build<%s> %s", os.date(nil), v_u_9:get_build_time_str(), p_u_38))
                if v41:count() > 1000 then
                    v41:pop_front()
                end;
                return v41:get_table();
            end, function() --[[ Line: 133 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): p_u_39, (copy 3): p_u_38 ]]
                v_u_1:warnf("ErrorDebugLog[%d]: %s", p_u_39, p_u_38)
            end)
        end;
        f_cons()
        return v11;
    end
};
