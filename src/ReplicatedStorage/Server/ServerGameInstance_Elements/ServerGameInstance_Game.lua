-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:21 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Server.DebugOut)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
local v_u_2 = require(game.ReplicatedStorage.Shared.FlashEvery)
require(game.ReplicatedStorage.Shared.NoteResult)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_3 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstanceMode)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_5 = require(game.ReplicatedStorage.Shared.Constants)
return {
    ["new"] = function(_, _, p_u_6) --[[ Name: new ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2, (copy 3): v_u_3, (copy 4): v_u_5, (copy 5): v_u_4 ]]
        local v7 = {}
        v7.notify_hit = function(_, _, _) --[[ Name: notify_hit ]] --[[ Line: 21 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("unexpected ServerGameInstance_Game:notify_hit when ScoreReplicationV2 active")
        end;
        v7.notify_power_bar_status = function(_, _, _) --[[ Name: notify_power_bar_status ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:warnf("unexpected ServerGameInstance_Game:notify_power_bar_status when ScoreReplicationV2 active")
        end;
        local v_u_8 = v_u_2:new(0.25)
        v7.update = function(_, p9) --[[ Name: update ]] --[[ Line: 30 ]]
            --[[ Upvalues: (copy 1): v_u_8, (copy 2): p_u_6, (ref 3): v_u_3, (ref 4): v_u_5, (ref 5): v_u_4 ]]
            v_u_8:update(p9)
            if v_u_8:do_flash() then
                p_u_6._util:push_update_player_info()
            end;
            p_u_6._playback_time_ms = p_u_6._playback_time_ms + v_u_3:TimescaleToDeltaTime(p9) * 1000
            if (p_u_6._game_ending:all_players_finished() == true and p_u_6._playback_time_ms >= p_u_6._sound_length_ms - v_u_5.PRE_START_TIME_MS_MAX - v_u_5.POST_TIME_PLAYING_MS_MAX == true and true or (p_u_6._playback_time_ms >= p_u_6._sound_length_ms == true and true or (p_u_6._game_ending:single_player_game_and_early_quit() and true or false))) == true then
                p_u_6:set_frame_push_update_game_info()
                p_u_6._current_mode = v_u_4.GameEnding
            end;
        end;
        return v7;
    end
};
