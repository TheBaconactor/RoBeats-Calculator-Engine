-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:19 PM
-- Cached decompilation

require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistP2EventInfo)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_1 = require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Avatar.PlayerBlobAvatar)
local _ = game:GetService("BadgeService")
local v2 = {}
local v3 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_4 = nil
v3:require_server(function() --[[ Line: 21 ]]
    --[[ Upvalues: (ref 1): v_u_4 ]]
    v_u_4 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
v2.new = function(_, _) --[[ Name: new ]] --[[ Line: 25 ]]
    --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_1 ]]
    local v5 = v_u_4.EventBase:new()
    local function _() end;
    v_u_1:get_base_fn(v5, "can_playerid_start_songkey")
    v5.can_playerid_start_songkey = function(_, _, _, _) --[[ Name: can_playerid_start_songkey ]] --[[ Line: 105 ]]
        return false;
    end;
    v_u_1:get_base_fn(v5, "write_special_event_data_for_play")
    v5.write_special_event_data_for_play = function(_, _, _, _, _, _, _, _) end;
    return v5;
end;
return v2;
