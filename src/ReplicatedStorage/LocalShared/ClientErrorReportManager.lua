-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:00 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_5 = require(game.ReplicatedStorage.Shared.ErrorReportBase)
return {
    ["new"] = function(_, p_u_6) --[[ Name: new ]] --[[ Line: 9 ]]
        --[[ Upvalues: (copy 1): v_u_5, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_4, (copy 5): v_u_1 ]]
        local v7 = v_u_5:new()
        local v_u_8 = v_u_2:new()
        v7.cons = function(_) end;
        v7.report_client_error = function(p9, p10) --[[ Name: report_client_error ]] --[[ Line: 17 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_8, (copy 3): p_u_6, (ref 4): v_u_4, (ref 5): v_u_1 ]]
            local v11 = p9:player_name_sub(string.gsub(p10.Error, "%d+", "#"))
            local v12 = p9:player_name_sub(p10.StackTrace)
            local v13 = v_u_3:hash_str(v11 .. v12)
            if not v_u_8:contains(v13) then
                v_u_8:add(v13, true)
                p_u_6._evt:fire_event_to_server(v_u_4.EVT_ErrorReport_ClientReportError, v11, v12)
                v_u_1:warnf("report_client_error (%s)--(%s)", tostring(p10.Error), (tostring(p10.StackTrace)))
            end;
        end;
        v7.evt_report_error = function(p14, p15) --[[ Name: evt_report_error ]] --[[ Line: 31 ]]
            p14:report_client_error(p15)
        end;
        v7:cons()
        return v7;
    end
};
