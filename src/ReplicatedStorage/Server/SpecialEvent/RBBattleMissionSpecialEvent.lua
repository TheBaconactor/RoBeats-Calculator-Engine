-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:18 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.Dependency)
local v2 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.MissionType)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.DebugOut)
local _ = game:GetService("BadgeService")
local v_u_4 = nil
v1:require_server(function() --[[ Line: 10 ]]
    --[[ Upvalues: (ref 1): v_u_4 ]]
    v_u_4 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
local v6 = {
    ["new"] = function(_, _) --[[ Name: new ]] --[[ Line: 22 ]]
        --[[ Upvalues: (ref 1): v_u_4 ]]
        local v5 = v_u_4.EventBase:new()
        v5.write_special_event_data_for_play = function(_, _, _, _, _, _, _, _) end;
        return v5;
    end
}
v3:new():push_back_table_list({ v2.EventMission.RBBattleMission1, v2.EventMission.RBBattleMission2, v2.EventMission.RBBattleMission3 })
return v6;
