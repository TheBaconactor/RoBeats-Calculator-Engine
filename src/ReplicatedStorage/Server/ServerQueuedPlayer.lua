-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:15 PM
-- Cached decompilation

require(game.ReplicatedStorage.Server.DebugOut)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.ServerGameInstancePlayer)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_1 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_3 = require(game.ReplicatedStorage.Shared.MatchMakingSettings)
local v_u_4 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.AssertType)
return {
    ["new"] = function(_, p_u_5, p_u_6, p7) --[[ Name: new ]] --[[ Line: 14 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_1 ]]
        local v8 = {}
        local v_u_9 = 0
        local l_MMV3_INITIAL_MATCH_WAIT_TIME_MS_0 = v_u_2.MMV3_INITIAL_MATCH_WAIT_TIME_MS
        local v_u_10 = v_u_3:new()
        v_u_3:update_from_table(v_u_10, p7)
        v8.get_wait_time = function(_) --[[ Name: get_wait_time ]] --[[ Line: 22 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            return v_u_9;
        end;
        v8.reset_wait_time = function(_) --[[ Name: reset_wait_time ]] --[[ Line: 23 ]]
            --[[ Upvalues: (ref 1): v_u_9 ]]
            v_u_9 = 0
        end;
        v8.set_initial_match_wait_time = function(_, p11) --[[ Name: set_initial_match_wait_time ]] --[[ Line: 24 ]]
            --[[ Upvalues: (ref 1): l_MMV3_INITIAL_MATCH_WAIT_TIME_MS_0 ]]
            l_MMV3_INITIAL_MATCH_WAIT_TIME_MS_0 = p11
        end;
        v8.get_player_id = function(_) --[[ Name: get_player_id ]] --[[ Line: 25 ]]
            --[[ Upvalues: (copy 1): p_u_5 ]]
            return p_u_5;
        end;
        v8.get_match_mode = function(_) --[[ Name: get_match_mode ]] --[[ Line: 27 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_10 ]]
            return v_u_3:get_match_mode(v_u_10);
        end;
        v8.get_matchmaking_settings = function(_) --[[ Name: get_matchmaking_settings ]] --[[ Line: 28 ]]
            --[[ Upvalues: (copy 1): v_u_10 ]]
            return v_u_10;
        end;
        v8.should_start_matching = function(_) --[[ Name: should_start_matching ]] --[[ Line: 30 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): l_MMV3_INITIAL_MATCH_WAIT_TIME_MS_0 ]]
            return l_MMV3_INITIAL_MATCH_WAIT_TIME_MS_0 < v_u_9;
        end;
        v8.get_matchmaking_time = function(_) --[[ Name: get_matchmaking_time ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): l_MMV3_INITIAL_MATCH_WAIT_TIME_MS_0 ]]
            return v_u_9 - l_MMV3_INITIAL_MATCH_WAIT_TIME_MS_0;
        end;
        v8.get_requested_song_key = function(_) --[[ Name: get_requested_song_key ]] --[[ Line: 33 ]]
            --[[ Upvalues: (copy 1): p_u_6 ]]
            return p_u_6;
        end;
        v8.get_song_difficulty = function(_) --[[ Name: get_song_difficulty ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_6 ]]
            return v_u_4:singleton():get_difficulty_for_key(p_u_6);
        end;
        v8.update_matchmaking_settings = function(_, p12) --[[ Name: update_matchmaking_settings ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): v_u_10 ]]
            v_u_3:update_from_table(v_u_10, p12)
        end;
        v8.update = function(_, p13) --[[ Name: update ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_1 ]]
            v_u_9 = v_u_9 + v_u_1:TimescaleToDeltaTime(p13) * 1000
        end;
        return v8;
    end
};
