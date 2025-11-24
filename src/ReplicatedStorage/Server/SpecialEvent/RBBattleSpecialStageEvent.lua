-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:18 PM
-- Cached decompilation

local v1 = require(game.ReplicatedStorage.Shared.Dependency)
require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
require(game.ReplicatedStorage.Server.ServerAPIManager)
local v_u_2 = require(game.ServerScriptService.ServerPrivateConstants)
local _ = game:GetService("BadgeService")
local v_u_3 = nil
v1:require_server(function() --[[ Line: 15 ]]
    --[[ Upvalues: (ref 1): v_u_3 ]]
    v_u_3 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
return {
    ["new"] = function(_, _) --[[ Name: new ]] --[[ Line: 21 ]]
        --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_2 ]]
        local v4 = v_u_3.EventBase:new()
        v4.cons = function(_) end;
        v_u_2:get_special_stage_sequence()
        v4.write_special_event_data_for_play = function(_, _, _, _, _, _, _, _) end;
        v4:cons()
        return v4;
    end
};
