-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:21:03 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_3 = require(game.ReplicatedStorage.Local.AudioManager)
local v_u_4 = require(game.ReplicatedStorage.Local.DebugOut)
return {
    ["new"] = function(_) --[[ Name: new ]] --[[ Line: 8 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_4 ]]
        local v5 = {}
        local v_u_6 = 0.16
        local v_u_7 = 5
        local v_u_8 = 0
        local v_u_9 = 0.016
        local v_u_10 = 1
        v5.update_game_lag_delay_sync = function(_, p11, p12) --[[ Name: update_game_lag_delay_sync ]] --[[ Line: 21 ]]
            --[[ Upvalues: (ref 1): v_u_3, (ref 2): v_u_2, (ref 3): v_u_1, (ref 4): v_u_10, (ref 5): v_u_9, (ref 6): v_u_6, (ref 7): v_u_8, (ref 8): v_u_4, (ref 9): v_u_7 ]]
            local v13 = false
            local v_u_14 = p11:es_gamelocal_get_audiomanager()
            if v_u_14:get_current_mode() == v_u_3.Mode.Playing then
                if v_u_14:get_song_time_position_ms() >= 2000 then
                    local v15 = v_u_2.do_profile == true and true or v_u_2:is_dev_build()
                    local v16 = v_u_1:TimescaleToDeltaTime(p12)
                    v_u_10 = v_u_10 + 1
                    v_u_9 = v_u_2:running_avg(v_u_9, v16, v_u_10)
                    if v_u_10 > 200 then
                        v_u_6 = math.max(v_u_9 * 10, 0.16)
                    end;
                    if v_u_6 < v16 then
                        local v17
                        if v_u_8 >= 4 then
                            if v15 then
                                v_u_4:warnf("more than %d sequential lag delay syncs, continuing frame", 4)
                                v17 = false
                            else
                                v17 = false
                            end;
                        else
                            v17 = true
                        end;
                        if v17 then
                            if v15 then
                                v_u_4:warnf("lag delay sync frame(%.2f) threshold(%.2f) frame_avg(%.2f) sequential_count(%d)", v16, v_u_6, v_u_9, v_u_8)
                            end;
                            v_u_7 = 0
                            v_u_8 = v_u_8 + 1
                            v_u_14:update_bgm_to_stored_time_position()
                            v_u_2:ptry(function() --[[ Line: 64 ]]
                                --[[ Upvalues: (copy 1): v_u_14 ]]
                                v_u_14:raise_resync_update_mode()
                            end)
                            return true;
                        end;
                    else
                        v_u_7 = v_u_7 + v16
                        if v_u_8 > 0 and v_u_7 > 2.5 then
                            v_u_8 = 0
                        end;
                    end;
                    return v13;
                end;
            end;
        end;
        return v5;
    end
};
