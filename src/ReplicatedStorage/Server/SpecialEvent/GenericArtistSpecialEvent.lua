-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:19 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistEventInfo)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_3 = require(game.ReplicatedStorage.Shared.Override)
require(game.ReplicatedStorage.Avatar.PlayerBlobDance)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_4 = require(game.ReplicatedStorage.Server.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local _ = game:GetService("BadgeService")
local s_TeleportService_0 = game:GetService("TeleportService")
local v6 = {}
local v7 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_8 = nil
v7:require_server(function() --[[ Line: 21 ]]
    --[[ Upvalues: (ref 1): v_u_8 ]]
    v_u_8 = require(game.ReplicatedStorage.Server.ServerSpecialEventManager)
end)
v6.new = function(_, p_u_9) --[[ Name: new ]] --[[ Line: 25 ]]
    --[[ Upvalues: (ref 1): v_u_8, (copy 2): v_u_2, (copy 3): v_u_4, (copy 4): s_TeleportService_0, (copy 5): v_u_3, (copy 6): v_u_1, (copy 7): v_u_5 ]]
    local v10 = v_u_8.EventBase:new()
    local function _() --[[ Name: cons ]] --[[ Line: 28 ]]
        --[[ Upvalues: (copy 1): p_u_9, (ref 2): v_u_2, (ref 3): v_u_4, (ref 4): s_TeleportService_0 ]]
        p_u_9._evt:wait_on_event(v_u_2.EVT_SpecialEvent_GenericArtistTeleport_Client, function(p11) --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_4, (ref 2): s_TeleportService_0 ]]
            v_u_4:puts("[GenericArtistSpecialEvent] Teleporting player(%d) to (%d)", p11.UserId, 9180395108)
            s_TeleportService_0:TeleportAsync(9180395108, { p11 })
        end)
    end;
    v_u_3:get_base_fn(v10, "can_playerid_start_songkey")
    v10.can_playerid_start_songkey = function(_, _, p12, _) --[[ Name: can_playerid_start_songkey ]] --[[ Line: 102 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_9 ]]
        if v_u_1:is_event_active(p_u_9._api:get_day_event_list()) == true then
            return v_u_1:get_playable_song_set():contains(p12);
        else
            return false;
        end;
    end;
    v_u_3:get_base_fn(v10, "write_special_event_data_for_play")
    v10.write_special_event_data_for_play = function(_, p13, p14, _, _, p15, _, _) --[[ Name: write_special_event_data_for_play ]] --[[ Line: 108 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_9, (ref 3): v_u_5 ]]
        if v_u_1:is_event_active(p_u_9._api:get_day_event_list()) == true then
            if v_u_1:get_playable_song_set():contains(p14) == true then
                local v16 = p_u_9._player_manager:id_to_player(p15._id)
                local v17 = p_u_9._chat:get_chat_service()
                local v18 = p_u_9._chat:gameid_get_channel(p13._game_id)
                if v18 then
                    v17:send_system_message_to_player_for_channel(v16, v18, string.format("Your score has been registered in Super League Arcade!"), function(p19) --[[ Line: 144 ]]
                        --[[ Upvalues: (ref 1): v_u_5 ]]
                        p19:set_icon(v_u_5:important_assetid())
                    end)
                end;
            end;
        else
            return;
        end;
    end;
    p_u_9._evt:wait_on_event(v_u_2.EVT_SpecialEvent_GenericArtistTeleport_Client, function(p20) --[[ Line: 62 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): s_TeleportService_0 ]]
        v_u_4:puts("[GenericArtistSpecialEvent] Teleporting player(%d) to (%d)", p20.UserId, 9180395108)
        s_TeleportService_0:TeleportAsync(9180395108, { p20 })
    end)
    return v10;
end;
return v6;
