-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:22 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Server.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.Server.ServerGameInstance_Elements.ServerGameInstanceMode)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_5 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.NotePlaybackSequence)
local v8 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_10 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_11 = require(game.ReplicatedStorage.Shared.NoteHitMode)
local v_u_12 = require(game.ReplicatedStorage.Shared.PlayerScore)
local v_u_13 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_14 = require(game.ReplicatedStorage.Shared.RandomLua)
local v15 = {}
local v_u_16 = v_u_1:new():push_back_table_list({
    44154266,
    107206636,
    2876672,
    60652528
})
local v_u_17 = nil
local v_u_18 = 0
v8:singleton():get_data_for_key(236, function(p19) --[[ Line: 31 ]]
    --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_18 ]]
    v_u_17 = p19
    for v20 = 1, #v_u_17.HitObjects do
        if v_u_17.HitObjects[v20].Type == 1 then
            v_u_18 = v_u_18 + 1
        else
            v_u_18 = v_u_18 + 2
        end;
    end;
    v_u_18 = v_u_18
end)
local function f_get_accuracy_for_index(p21) --[[ Name: get_accuracy_for_index ]] --[[ Line: 43 ]]
    --[[ Upvalues: (copy 1): v_u_4, (ref 2): v_u_18 ]]
    return v_u_4:clamp(p21 / v_u_18, 0, 1);
end;
v15.new = function(_, p_u_22) --[[ Name: new ]] --[[ Line: 47 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_16, (copy 3): v_u_9, (copy 4): v_u_3, (copy 5): v_u_6, (ref 6): v_u_17, (copy 7): v_u_5, (copy 8): v_u_14, (copy 9): v_u_13, (copy 10): v_u_4, (copy 11): v_u_1, (copy 12): v_u_12, (copy 13): v_u_7, (copy 14): v_u_11, (copy 15): v_u_10, (copy 16): f_get_accuracy_for_index ]]
    local v23 = {}
    local v_u_24 = nil
    v23.start = function(_) --[[ Name: start ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_24, (copy 3): p_u_22, (ref 4): v_u_16 ]]
        if v_u_2.SpectateDebugTestServer == true then
            v_u_24 = p_u_22._game_instance_manager:make_new_gameinstance()
            for v25 = 1, v_u_16:count() do
                local v26 = v_u_16:get(v25)
                p_u_22._id_to_player:add(v26, {
                    ["DebugMockPlayer"] = true,
                    ["Name"] = string.format("SpectateDebugPlayer%d", v25),
                    ["UserId"] = v26
                })
                v_u_24._match_making:request_slot_for_id(v26, 236)
            end;
        end;
    end;
    local v_u_27 = 0
    local v_u_28 = 0
    local v_u_29 = v_u_9:new()
    local v_u_30 = v_u_9:new()
    local v_u_31 = false
    local v_u_32 = 1
    local v_u_33 = 0
    v23.update = function(p34, p_u_35) --[[ Name: update ]] --[[ Line: 80 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_24, (ref 3): v_u_3, (ref 4): v_u_27, (ref 5): v_u_6, (ref 6): v_u_33, (ref 7): v_u_32, (ref 8): v_u_17, (ref 9): v_u_5, (copy 10): v_u_30, (ref 11): v_u_31 ]]
        if v_u_2.SpectateDebugTestServer == true then
            if v_u_24 == nil then
                return;
            elseif v_u_24._current_mode == v_u_3.MatchMaking then
                v_u_24._util:slots_foreach(function(p36) --[[ Line: 85 ]]
                    p36._ready = true
                end)
                return;
            elseif v_u_24._current_mode == v_u_3.SoundLoad then
                v_u_24._util:slots_foreach(function(p37) --[[ Line: 89 ]]
                    p37._loaded = true
                end)
                return;
            elseif v_u_24._current_mode == v_u_3.Game then
                v_u_27 = v_u_27 + v_u_6:TimescaleToDeltaTime(p_u_35)
                if v_u_2.SpectateDebugTestServerQuitters == true then
                    v_u_33 = v_u_33 + v_u_6:TimescaleToDeltaTime(p_u_35)
                    if v_u_33 > 5 then
                        if v_u_24._slots:contains(v_u_32) then
                            v_u_24:remove_player_from_slot(v_u_32)
                        end;
                        v_u_33 = 0
                        v_u_32 = v_u_32 + 1
                    end;
                end;
                if v_u_17 ~= nil and v_u_27 > v_u_5.SPECTATE_REPLICATION_EVERY_SEC then
                    p34:send_new_spectate_replication_data()
                    v_u_27 = 0
                end;
                v_u_24._util:slots_foreach(function(p38) --[[ Line: 112 ]]
                    --[[ Upvalues: (ref 1): v_u_30, (copy 2): p_u_35 ]]
                    local v39 = v_u_30:get(p38._id)
                    if v39 ~= nil then
                        v39:update(p_u_35, false, false)
                    end;
                end)
            elseif v_u_24._current_mode == v_u_3.GameEnding then
                if v_u_31 ~= true then
                    v_u_24._util:slots_foreach(function(p40) --[[ Line: 122 ]]
                        --[[ Upvalues: (ref 1): v_u_24 ]]
                        v_u_24._game_ending:notify_local_finished(p40._id, false, {
                            ["Score"] = p40._score,
                            ["Chain"] = 0,
                            ["PerfectCount"] = 0,
                            ["GreatCount"] = 0,
                            ["OkayCount"] = 0,
                            ["MissCount"] = 0,
                            ["NakedScore"] = p40._score,
                            ["Accuracy"] = 1,
                            ["FeverPercentage"] = 0,
                            ["ComboMax"] = 0
                        })
                    end)
                    v_u_31 = true
                    return;
                end;
            end;
        else
            return;
        end;
    end;
    local v_u_41 = v_u_14.mwc(0)
    local v_u_42 = v_u_9:new()
    local v_u_43 = 1
    v23.random_noteresult_and_time_ms = function(_, p44) --[[ Name: random_noteresult_and_time_ms ]] --[[ Line: 146 ]]
        --[[ Upvalues: (ref 1): v_u_13, (copy 2): v_u_42, (ref 3): v_u_43, (ref 4): v_u_4, (copy 5): v_u_41 ]]
        local v45, v46, v47, v48, v49, v50 = v_u_13:get_note_times(v_u_13:statsdict_base())
        if v_u_42:contains(p44) ~= true then
            v_u_42:add(p44, v_u_43)
            v_u_43 = v_u_43 + 1
        end;
        local v51 = v_u_42:get(p44)
        local v52
        if v51 == 1 then
            v52 = 0
        elseif v51 == 2 then
            v52 = math.floor((v_u_4:rand_rangef(v49, v46)))
        elseif v51 == 3 then
            v52 = math.floor((v_u_41:rand_rangef(v50 + 30, v45 - 30)))
        else
            v52 = math.floor((v_u_41:rand_rangef(v50 - 30, v45 + 30)))
        end;
        return v_u_4:timedelta_to_result(v52, v45, v46, v47, v48, v49, v50), v52;
    end;
    v23.send_new_spectate_replication_data = function(p_u_53) --[[ Name: send_new_spectate_replication_data ]] --[[ Line: 170 ]]
        --[[ Upvalues: (ref 1): v_u_24, (copy 2): v_u_29, (ref 3): v_u_1, (copy 4): v_u_30, (ref 5): v_u_12, (ref 6): v_u_13, (ref 7): v_u_7, (ref 8): v_u_28, (ref 9): v_u_11, (ref 10): v_u_10, (ref 11): f_get_accuracy_for_index, (ref 12): v_u_17, (copy 13): p_u_22 ]]
        v_u_24._util:slots_foreach(function(p54) --[[ Line: 171 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_1, (ref 3): v_u_30, (ref 4): v_u_12, (ref 5): v_u_13 ]]
            if v_u_29:contains(p54._id) ~= true then
                v_u_29:add(p54._id, {
                    ["_i_hitobjects"] = 1,
                    ["_heldnotes_to_close"] = v_u_1:new()
                })
                v_u_30:add(p54._id, v_u_12:new(236, v_u_13:statsdict_base()))
            end;
        end)
        local v_u_55 = math.floor(v_u_24._playback_time_ms)
        v_u_24._util:slots_foreach(function(p56) --[[ Line: 182 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_30, (ref 3): v_u_7, (ref 4): v_u_28, (copy 5): v_u_55, (copy 6): p_u_53, (ref 7): v_u_11, (ref 8): v_u_10, (ref 9): f_get_accuracy_for_index, (ref 10): v_u_17, (ref 11): p_u_22 ]]
            local l__id_0 = p56._id
            local v57 = v_u_29:get(l__id_0)
            local v58 = v_u_30:get(l__id_0)
            local v59 = v_u_7:new()
            v59:set_time_start(v_u_28)
            v59:set_score_start(p56._score)
            v59:set_combo_start(p56._chain)
            for v60 = v57._heldnotes_to_close:count(), 1, -1 do
                local v61 = v57._heldnotes_to_close:get(v60)
                if v61.ReleaseTime < v_u_55 then
                    v57._heldnotes_to_close:remove_at(v60)
                    local v62, v63 = p_u_53:random_noteresult_and_time_ms(p56._id)
                    local l_HeldHitTail_0 = v_u_11.HeldHitTail
                    if v62 == v_u_10.NoteResult_Miss then
                        l_HeldHitTail_0 = v_u_11.HeldTimeMissTail
                    end;
                    v59:add_note_event(v61.ReleaseTime + v63, v61.NoteIndex, v62, v63, v58:is_powerbar_active(), v61.Track, l_HeldHitTail_0, v58:get_power_bar_pct(), f_get_accuracy_for_index(v61.NoteIndex))
                    v58:register_hit_noteresult_hitmode(v62, l_HeldHitTail_0)
                end;
            end;
            if v_u_17 == nil then
                return;
            end;
            while v57._i_hitobjects <= #v_u_17.HitObjects do
                local l_HitObjects_0 = v_u_17.HitObjects[v57._i_hitobjects]
                if v_u_55 < l_HitObjects_0.Time then
                    break;
                end;
                local v64, v65 = p_u_53:random_noteresult_and_time_ms(p56._id)
                local l_NoteHit_0 = v_u_11.NoteHit
                if l_HitObjects_0.Type == 1 then
                    l_NoteHit_0 = v_u_11.NoteHit
                    if v64 == v_u_10.NoteResult_Miss then
                        l_NoteHit_0 = v_u_11.NoteMiss
                    end;
                    v59:add_note_event(l_HitObjects_0.Time + v65, v57._i_hitobjects, v64, v65, v58:is_powerbar_active(), l_HitObjects_0.Track, l_NoteHit_0, v58:get_power_bar_pct(), f_get_accuracy_for_index(v57._i_hitobjects))
                elseif l_HitObjects_0.Type == 2 then
                    l_NoteHit_0 = v_u_11.HeldHitHead
                    if v64 == v_u_10.NoteResult_Miss then
                        l_NoteHit_0 = v_u_11.HeldTimeMissHead
                    end;
                    v59:add_note_event(l_HitObjects_0.Time + v65, v57._i_hitobjects, v64, v65, v58:is_powerbar_active(), l_HitObjects_0.Track, l_NoteHit_0, v58:get_power_bar_pct(), f_get_accuracy_for_index(v57._i_hitobjects))
                    v57._heldnotes_to_close:push_back({
                        ["ReleaseTime"] = l_HitObjects_0.Time + l_HitObjects_0.Duration,
                        ["NoteIndex"] = v57._i_hitobjects,
                        ["Track"] = l_HitObjects_0.Track
                    })
                end;
                v58:register_hit_noteresult_hitmode(v64, l_NoteHit_0)
                v57._i_hitobjects = v57._i_hitobjects + 1
            end;
            v59:set_time_end(v_u_55)
            v59:set_score_end(v58:get_score())
            v59:set_combo_end(v58:get_chain())
            p56._score = v58:get_score()
            p56._chain = v58:get_chain()
            p56._power_bar_active = v58:is_powerbar_active()
            p_u_22._game_instance_manager:get_note_playback_sequence_manager():client_send_notesequence_update_for_playerid(l__id_0, v59)
        end)
        v_u_28 = v_u_55
    end;
    return v23;
end;
return v15;
