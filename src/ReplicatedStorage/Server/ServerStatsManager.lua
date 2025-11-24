-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:15 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_7 = require(game.ReplicatedStorage.Shared.CooldownDelay)
local v_u_8 = require(game.ReplicatedStorage.Server.ServerAPIManager)
return {
    ["new"] = function(_, p_u_9) --[[ Name: new ]] --[[ Line: 15 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_4, (copy 3): v_u_3, (copy 4): v_u_7, (copy 5): v_u_1, (copy 6): v_u_8, (copy 7): v_u_5, (copy 8): v_u_6 ]]
        local v10 = {
            ["cons"] = function(_) end
        }
        local v_u_11 = 0
        local v_u_12 = 0
        local v_u_13 = 0
        local v_u_14 = 0
        local v_u_15 = v_u_2:new()
        local v_u_16 = v_u_2:new()
        local v_u_17 = v_u_4:running_avg_collector()
        local v_u_18 = v_u_4:running_avg_collector()
        local v_u_19 = v_u_4:running_avg_collector()
        local v_u_20 = v_u_4:running_avg_collector()
        local v_u_21 = v_u_4:running_avg_collector()
        local v_u_22 = stats()
        v10.get_time = function(_) --[[ Name: get_time ]] --[[ Line: 37 ]]
            --[[ Upvalues: (ref 1): v_u_11 ]]
            return v_u_11;
        end;
        local v_u_23 = v_u_2:new():add_set_from_table_list({
            v_u_3.EVT_ModelLoadDB_ClientRequestLoad,
            v_u_3.EVT_Spectate_ClientSendNoteSequenceUpdate,
            v_u_3.EVT_Leaderboard_ClientQuerySongIndex,
            v_u_3.EVT_LeaderboardEvent_ClientRequestLeaderboardData,
            v_u_3.EVT_Players_ClientQueryPlayerList,
            v_u_3.EVT_Lobby_ClientRequestSyncDanceToPlayer,
            v_u_3.EVT_GameLoad_MatchmakingV3_ClientReady,
            v_u_3.EVT_PlayerTrade_ClientPushLocalOffer,
            v_u_3.EVT_GameLoad_MatchmakingV3_ClientUpdateSettings,
            v_u_3.EVT_PlayerSongStats_ClientRequestRank,
            v_u_3.EVT_Trade_ClientSendTradeRequest,
            v_u_3.EVT_Chat_ClientSendMessage,
            v_u_3.EVT_Lobby_ClientRequestInfoForCharacters,
            v_u_3.EVT_Shop_ClientInfoRequest,
            v_u_3.EVT_ChallengePass_ClientRequestInfo,
            v_u_3.EVT_GameLoad_MatchmakingV3_ClientLeaveMatch,
            v_u_3.EVT_GameLoad_MatchmakingV3_ClientEnqueue,
            v_u_3.EVT_PetAssignment_RequestData_Client,
            v_u_3.EVT_Players_ClientSetSubscribePlayerListUpdates,
            v_u_3.EVT_Crafting_ClientCraftGatchaInfoRequest,
            v_u_3.EVT_PlayerStatus_ClientRequestInitial,
            v_u_3.EVT_DanceClub_ClientRequestCurrentSongInfo
        })
        local function _(p24, p25) --[[ Name: player_evt_key_hash ]] --[[ Line: 69 ]]
            return string.format("%s_%s", tostring(p24.Name), (tostring(p25)));
        end;
        local v_u_26 = v_u_7:new()
        local v_u_27 = v_u_2:new()
        v10.report_spremoteevent_receive = function(_, p28, p29) --[[ Name: report_spremoteevent_receive ]] --[[ Line: 74 ]]
            --[[ Upvalues: (copy 1): v_u_16, (copy 2): v_u_23, (copy 3): v_u_26, (copy 4): v_u_27, (ref 5): v_u_1, (copy 6): p_u_9, (ref 7): v_u_8 ]]
            if v_u_16:contains(p29) ~= true then
                v_u_16:add(p29, 0)
            end;
            v_u_16:add(p29, v_u_16:get(p29) + 1)
            local v30 = true
            if v_u_23:contains(p29) ~= true then
                local v31 = string.format("%s_%s", tostring(p28.Name), (tostring(p29)))
                if v_u_26:is_on_cooldown(v31) then
                    if v_u_27:contains(v31) == true then
                        v30 = false
                    else
                        v_u_27:add_set(v31)
                        local v32 = string.format("version(%s) evt(%s) player(%s) cooldown(%.2f)", tostring(2), tostring(p29), tostring(p28.Name), v_u_26:get_cooldown_time(v31))
                        v_u_1:warnf("SPRemoteEvent server_stats_manager skip " .. v32)
                        p_u_9._api:api_report_evt(v_u_8.ReportEvt_ReceiveSPRemoteEventHashCooldown, p28.UserId, p29, v32)
                        v30 = false
                    end;
                end;
                v_u_26:add_cooldown_to_id(v31, 0.25)
            end;
            return v30;
        end;
        v10.report_spremoteevent_send = function(_, _, p33) --[[ Name: report_spremoteevent_send ]] --[[ Line: 104 ]]
            --[[ Upvalues: (copy 1): v_u_15 ]]
            if v_u_15:contains(p33) ~= true then
                v_u_15:add(p33, 0)
            end;
            v_u_15:add(p33, v_u_15:get(p33) + 1)
        end;
        v10.report_web_failure = function(_, _) --[[ Name: report_web_failure ]] --[[ Line: 111 ]]
            --[[ Upvalues: (ref 1): v_u_14 ]]
            v_u_14 = v_u_14 + 1
        end;
        v10.report_stats = function(_) --[[ Name: report_stats ]] --[[ Line: 115 ]]
            --[[ Upvalues: (copy 1): v_u_15, (copy 2): v_u_16, (copy 3): p_u_9, (ref 4): v_u_11, (ref 5): v_u_14, (copy 6): v_u_17, (copy 7): v_u_18, (copy 8): v_u_19, (copy 9): v_u_20, (copy 10): v_u_21 ]]
            local v34 = {}
            for v35, v36 in v_u_15:key_itr() do
                v34[tostring(v35)] = v36
            end;
            local v37 = {}
            for v38, v39 in v_u_16:key_itr() do
                v37[tostring(v38)] = v39
            end;
            p_u_9._api:api_send_server_stats({
                ["SPID"] = p_u_9._api:get_spid(),
                ["ServerTime"] = v_u_11,
                ["SPRemoteEventSend"] = v34,
                ["SPRemoteEventReceive"] = v37,
                ["WebFailureCount"] = v_u_14,
                ["DataReceive"] = v_u_17:get_avg(),
                ["DataSend"] = v_u_18:get_avg(),
                ["PhysicsReceive"] = v_u_19:get_avg(),
                ["PhysicsSend"] = v_u_20:get_avg(),
                ["Memory"] = v_u_21:get_avg(),
                ["Players"] = #game:GetService("Players"):GetChildren()
            })
            v_u_14 = 0
            v_u_15:clear()
            v_u_16:clear()
            v_u_17:clear()
            v_u_18:clear()
            v_u_19:clear()
            v_u_20:clear()
            v_u_21:clear()
        end;
        v10.stat_avg_poll = function(_) --[[ Name: stat_avg_poll ]] --[[ Line: 150 ]]
            --[[ Upvalues: (copy 1): v_u_17, (copy 2): v_u_22, (copy 3): v_u_18, (copy 4): v_u_19, (copy 5): v_u_20, (copy 6): v_u_21, (ref 7): v_u_1 ]]
            local v40, v41 = pcall(function() --[[ Line: 151 ]]
                --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_22, (ref 3): v_u_18, (ref 4): v_u_19, (ref 5): v_u_20, (ref 6): v_u_21 ]]
                v_u_17:push_val(v_u_22.DataReceiveKbps)
                v_u_18:push_val(v_u_22.DataSendKbps)
                v_u_19:push_val(v_u_22.PhysicsReceiveKbps)
                v_u_20:push_val(v_u_22.PhysicsSendKbps)
                v_u_21:push_val(v_u_22:GetTotalMemoryUsageMb())
            end)
            if not v40 then
                v_u_1:warnf(v41)
            end;
        end;
        v10.update = function(p42, p43) --[[ Name: update ]] --[[ Line: 163 ]]
            --[[ Upvalues: (ref 1): v_u_11, (ref 2): v_u_5, (ref 3): v_u_13, (ref 4): v_u_6, (ref 5): v_u_12, (copy 6): v_u_26 ]]
            v_u_11 = v_u_11 + v_u_5:TimescaleToDeltaTime(p43)
            v_u_13 = v_u_13 + v_u_5:TimescaleToDeltaTime(p43)
            if v_u_13 > v_u_6.SERVER_STATS_AVG_POLL_FREQ_SEC then
                v_u_13 = 0
                p42:stat_avg_poll()
            end;
            v_u_12 = v_u_12 + v_u_5:TimescaleToDeltaTime(p43)
            if v_u_12 > v_u_6.SERVER_STATS_REPORT_FREQ_SEC then
                v_u_12 = 0
                p42:report_stats()
            end;
            v_u_26:update(p43)
        end;
        v10:cons()
        return v10;
    end
};
