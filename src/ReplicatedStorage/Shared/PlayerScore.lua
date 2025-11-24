-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:07 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Shared.PowerBarState)
local v_u_4 = require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_6 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Shared.EventString)
require(game.ReplicatedStorage.Shared.SPList)
local v_u_9 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_10 = require(game.ReplicatedStorage.Shared.NoteHitMode)
local v_u_11 = require(game.ReplicatedStorage.Shared.SPDict)
return {
    ["new"] = function(_, p12, p_u_13) --[[ Name: new ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_7, (copy 3): v_u_9, (copy 4): v_u_3, (copy 5): v_u_5, (copy 6): v_u_1, (copy 7): v_u_11, (copy 8): v_u_10, (copy 9): v_u_4, (copy 10): v_u_2, (copy 11): v_u_6 ]]
        local v21 = {
            ["get_powerbar_multiplier"] = function(p14) --[[ Name: get_powerbar_multiplier ]] --[[ Line: 243 ]]
                return not p14:is_powerbar_active() and 1 or p14:get_powerbar_multiplier_base();
            end,
            ["get_average_accuracy"] = function(p15) --[[ Name: get_average_accuracy ]] --[[ Line: 275 ]]
                local v16, v17, v18, v19 = p15:get_stat_counts()
                local v20 = v16 + v17 + v18 + v19
                return v20 == 0 and 0 or (v16 * 1 + v17 * 0.75 + v18 * 0.25) / v20;
            end
        }
        v_u_8:is_true(v_u_7:singleton():contains_key(p12))
        local v_u_22 = v_u_7:singleton():get_songkey_hit_objects_count(p12)
        local v_u_23 = v_u_7:singleton():songkey_get_prebuffer_time(p12)
        local v_u_24 = v_u_7:singleton():songkey_get_approx_length_sec(p12) * 1000
        local v_u_25 = v_u_9:songkey_get_color_list(p12)
        local v_u_26 = 0
        local v_u_27 = 0
        local v_u_28 = 0
        local l_PowerBar_Charging_0 = v_u_3.PowerBar_Charging
        local v_u_29 = 0
        local v_u_30 = 0
        local v_u_31 = 0
        local v_u_32 = 0
        local v_u_33 = 0
        local v_u_34 = 0
        local v_u_35 = 0
        local v_u_36 = 0
        local v_u_37 = false
        local v_u_38 = 0
        local v_u_39 = true
        v21.set_apply_hit_to_powerbar = function(_, p40) --[[ Name: set_apply_hit_to_powerbar ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_39 ]]
            v_u_39 = p40
        end;
        v21.get_statsdict = function(_) --[[ Name: get_statsdict ]] --[[ Line: 51 ]]
            --[[ Upvalues: (copy 1): p_u_13 ]]
            return p_u_13;
        end;
        local v_u_41 = v_u_7:singleton():get_songkey_hit_count(p12)
        v21.set_song_key_hit_count = function(_, p42) --[[ Name: set_song_key_hit_count ]] --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_41 ]]
            v_u_8:is_number(p42)
            v_u_41 = p42
        end;
        local v_u_43 = 0
        v21.get_local_note_count = function(_) --[[ Name: get_local_note_count ]] --[[ Line: 60 ]]
            --[[ Upvalues: (ref 1): v_u_43 ]]
            return v_u_43;
        end;
        v21.get_raise_chain_broken = function(_) --[[ Name: get_raise_chain_broken ]] --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            return v_u_37;
        end;
        v21.get_raise_chain_broken_at = function(_) --[[ Name: get_raise_chain_broken_at ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_38 ]]
            return v_u_38;
        end;
        v21.get_chain = function(_) --[[ Name: get_chain ]] --[[ Line: 63 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27;
        end;
        v21.get_stat_counts = function(_) --[[ Name: get_stat_counts ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_32, (ref 3): v_u_33, (ref 4): v_u_34, (ref 5): v_u_36 ]]
            return v_u_31, v_u_32, v_u_33, v_u_34, v_u_36;
        end;
        v21.set_stat_counts = function(_, p44, p45, p46, p47, p48) --[[ Name: set_stat_counts ]] --[[ Line: 65 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_32, (ref 3): v_u_33, (ref 4): v_u_34, (ref 5): v_u_36 ]]
            v_u_31 = p44
            v_u_32 = p45
            v_u_33 = p46
            v_u_34 = p47
            v_u_36 = p48
        end;
        v21.get_score = function(_) --[[ Name: get_score ]] --[[ Line: 72 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            return v_u_26;
        end;
        v21.get_power_bar_pct = function(_) --[[ Name: get_power_bar_pct ]] --[[ Line: 73 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28;
        end;
        v21.get_powerbar_notes_count = function(_) --[[ Name: get_powerbar_notes_count ]] --[[ Line: 74 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            return v_u_29;
        end;
        v21.get_fever_percentage = function(_) --[[ Name: get_fever_percentage ]] --[[ Line: 75 ]]
            --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_30 ]]
            return v_u_43 == 0 and 0 or v_u_30 / v_u_43;
        end;
        v21.set_chain = function(_, p49) --[[ Name: set_chain ]] --[[ Line: 82 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            v_u_27 = p49
        end;
        v21.es_playerscore_set_score = function(_, p50) --[[ Name: es_playerscore_set_score ]] --[[ Line: 84 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            v_u_26 = p50
        end;
        v21.es_playerscore_set_powerbar_state = function(_, p51, p52) --[[ Name: es_playerscore_set_powerbar_state ]] --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_3, (ref 3): l_PowerBar_Charging_0, (ref 4): v_u_28 ]]
            v_u_8:is_enum_member(p51, v_u_3)
            l_PowerBar_Charging_0 = p51
            v_u_28 = p52
        end;
        v21.es_playerscore_apply_hit_to_powerbar = function(p53, p54) --[[ Name: es_playerscore_apply_hit_to_powerbar ]] --[[ Line: 94 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_5, (ref 3): v_u_29, (copy 4): v_u_22, (ref 5): v_u_28, (ref 6): v_u_1 ]]
            v_u_8:is_enum_member(p54, v_u_5)
            if p53:is_powerbar_active() then
                v_u_28 = v_u_28 + p53:get_powerbar_noteresult_drain(p54, v_u_29, v_u_22)
            else
                v_u_28 = v_u_28 + p53:get_powerbar_noteresult_fill(p54, v_u_22)
            end;
            v_u_28 = v_u_1:clamp(v_u_28, 0, 1)
        end;
        local v_u_55 = true
        v21.set_track_hit_counts = function(_, p56) --[[ Name: set_track_hit_counts ]] --[[ Line: 109 ]]
            --[[ Upvalues: (ref 1): v_u_55 ]]
            v_u_55 = p56
        end;
        local v_u_57 = v_u_11:new():add_set_from_table_list({ v_u_10.NoteTimeMiss, v_u_10.HeldTimeMissHead, v_u_10.HeldTimeMissTail })
        local v_u_58 = v_u_11:new():add_set_from_table_list({ v_u_10.WhiffMiss, v_u_10.HeldReleaseEarly })
        v21.register_hit_noteresult_hitmode = function(p59, p60, p61) --[[ Name: register_hit_noteresult_hitmode ]] --[[ Line: 124 ]]
            --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_5, (ref 3): v_u_10, (ref 4): v_u_39, (ref 5): v_u_36, (ref 6): v_u_27, (ref 7): v_u_55, (ref 8): v_u_31, (ref 9): v_u_32, (ref 10): v_u_33, (ref 11): v_u_37, (ref 12): v_u_38, (copy 13): v_u_57, (ref 14): v_u_34, (copy 15): v_u_58, (ref 16): v_u_35, (ref 17): v_u_43, (ref 18): v_u_4, (ref 19): v_u_26, (ref 20): v_u_29, (ref 21): v_u_30 ]]
            v_u_8:is_enum_member(p60, v_u_5)
            v_u_8:is_enum_member(p61, v_u_10)
            if v_u_39 then
                p59:es_playerscore_apply_hit_to_powerbar(p60)
            end;
            v_u_36 = math.max(v_u_27, v_u_36)
            local v62 = false
            local v63 = true
            if p60 == v_u_5.NoteResult_Perfect then
                v_u_27 = v_u_27 + 1
                if v_u_55 then
                    v_u_31 = v_u_31 + 1
                end;
            elseif p60 == v_u_5.NoteResult_Great then
                v_u_27 = v_u_27 + 1
                if v_u_55 then
                    v_u_32 = v_u_32 + 1
                end;
            elseif p60 == v_u_5.NoteResult_Okay then
                if v_u_55 then
                    v_u_33 = v_u_33 + 1
                end;
            else
                if v_u_27 > 0 then
                    v_u_37 = true
                    v_u_38 = v_u_27
                    v_u_27 = p59:get_chain_break(v_u_27)
                elseif v_u_57:contains(p61) ~= true then
                    v63 = false
                end;
                if v63 then
                    if v_u_55 then
                        v_u_34 = v_u_34 + 1
                    end;
                    if v_u_58:contains(p61) then
                        if v_u_55 then
                            v_u_35 = v_u_35 + 1
                            v62 = true
                        else
                            v62 = true
                        end;
                    end;
                end;
            end;
            if v63 and v62 ~= true then
                v_u_43 = v_u_43 + 1
            end;
            local v64 = p59:result_to_point_total(p60)
            local v65 = p59:get_chain_multiplier()
            local v66 = p59:get_powerbar_multiplier()
            local v67, v68
            if v_u_4.ColorGearStatsEnabled == true then
                v67, v68 = p59:get_color_point_bonus_for_noteresult(p60)
                v64 = v64 + v67 + v68
            else
                v67 = 0
                v68 = 0
            end;
            local v69 = math.floor(v64 * v65 * v66)
            if v63 then
                v_u_26 = v_u_26 + v69
                if p60 ~= v_u_5.NoteResult_Miss then
                    v_u_29 = v_u_29 + 1
                    if p59:is_powerbar_active() then
                        v_u_30 = v_u_30 + 1
                    end;
                end;
            end;
            return v69, v65, v66, v67, v68, v63;
        end;
        v21.post_update = function(_) --[[ Name: post_update ]] --[[ Line: 206 ]]
            --[[ Upvalues: (ref 1): v_u_37 ]]
            v_u_37 = false
        end;
        v21.update = function(p70, p71, p72, p73) --[[ Name: update ]] --[[ Line: 210 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_2, (ref 3): v_u_1, (ref 4): l_PowerBar_Charging_0, (ref 5): v_u_3, (ref 6): v_u_29 ]]
            if p70:is_powerbar_active() then
                v_u_28 = v_u_28 - v_u_2:SecondsToTick(p70:get_powerbar_base_decay_time_seconds()) * p71
                if v_u_28 > 0 then
                    return false, true;
                end;
                v_u_28 = v_u_1:clamp(v_u_28, 0, 1)
                l_PowerBar_Charging_0 = v_u_3.PowerBar_Charging
                return true, false;
            else
                v_u_29 = 0
                if v_u_28 < 1 or p73 ~= false and (p73 ~= true or not p72) then
                    return false, false;
                end;
                l_PowerBar_Charging_0 = v_u_3.PowerBar_Active
                v_u_29 = 1
                return true, true;
            end;
        end;
        v21.get_chain_multiplier = function(_) --[[ Name: get_chain_multiplier ]] --[[ Line: 233 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13, (ref 3): v_u_27 ]]
            return v_u_6:get_continuous_combo_multiplier_for_combo(p_u_13, v_u_27);
        end;
        v21.get_combo_threshold = function(_) --[[ Name: get_combo_threshold ]] --[[ Line: 237 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13, (ref 3): v_u_27 ]]
            return v_u_6:get_combo_threshold(p_u_13, v_u_27);
        end;
        v21.is_powerbar_active = function(_) --[[ Name: is_powerbar_active ]] --[[ Line: 241 ]]
            --[[ Upvalues: (ref 1): l_PowerBar_Charging_0, (ref 2): v_u_3 ]]
            return l_PowerBar_Charging_0 == v_u_3.PowerBar_Active;
        end;
        v21.result_to_point_total = function(p74, p75) --[[ Name: result_to_point_total ]] --[[ Line: 251 ]]
            --[[ Upvalues: (ref 1): v_u_5 ]]
            if p75 == v_u_5.NoteResult_Perfect then
                return p74:get_perfect_points();
            elseif p75 == v_u_5.NoteResult_Great then
                return p74:get_great_points();
            else
                return p75 ~= v_u_5.NoteResult_Okay and 0 or p74:get_okay_points();
            end;
        end;
        local function _(p76, p77, p78, _, p79) --[[ Name: calc_accuracy ]] --[[ Line: 265 ]]
            return (p76 * 1 + p77 * 0.75 + p78 * 0.25) / p79;
        end;
        v21.get_accuracy = function(p80) --[[ Name: get_accuracy ]] --[[ Line: 269 ]]
            --[[ Upvalues: (ref 1): v_u_41, (ref 2): v_u_35 ]]
            local v81, v82, v83, _ = p80:get_stat_counts()
            return (v81 * 1 + v82 * 0.75 + v83 * 0.25) / (v_u_41 + v_u_35);
        end;
        v21.to_string = function(p84) --[[ Name: to_string ]] --[[ Line: 282 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_32, (ref 3): v_u_33, (ref 4): v_u_34, (ref 5): v_u_41, (ref 6): v_u_35 ]]
            return string.format("PlayerScore accuracy(%.4f) avg(%.4f): perfect(%d) great(%d) ok(%d) miss(%d) songkey_hit_count(%d) unindexed_miss_count(%d)", p84:get_accuracy(), p84:get_average_accuracy(), v_u_31, v_u_32, v_u_33, v_u_34, v_u_41, v_u_35);
        end;
        v21.get_perfect_upper_lower_time = function(_) --[[ Name: get_perfect_upper_lower_time ]] --[[ Line: 298 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            return v_u_6:get_perfect_upper_lower_time(p_u_13);
        end;
        v21.get_great_upper_lower_time = function(_) --[[ Name: get_great_upper_lower_time ]] --[[ Line: 299 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            return v_u_6:get_great_upper_lower_time(p_u_13);
        end;
        v21.get_okay_upper_lower_time = function(_) --[[ Name: get_okay_upper_lower_time ]] --[[ Line: 300 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            return v_u_6:get_okay_upper_lower_time(p_u_13);
        end;
        v21.get_perfect_points = function(_) --[[ Name: get_perfect_points ]] --[[ Line: 301 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            return v_u_6:get_perfect_points(p_u_13);
        end;
        v21.get_great_points = function(_) --[[ Name: get_great_points ]] --[[ Line: 302 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            return v_u_6:get_great_points(p_u_13);
        end;
        v21.get_okay_points = function(_) --[[ Name: get_okay_points ]] --[[ Line: 303 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            return v_u_6:get_okay_points(p_u_13);
        end;
        v21.get_powerbar_multiplier_base = function(_) --[[ Name: get_powerbar_multiplier_base ]] --[[ Line: 304 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            return v_u_6:get_powerbar_multiplier(p_u_13);
        end;
        v21.get_tier3_combo_count = function(_) --[[ Name: get_tier3_combo_count ]] --[[ Line: 305 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            local _, _, v85 = v_u_6:get_combo_thresholds(p_u_13)
            return v85;
        end;
        v21.get_tier3_combo_mult = function(_) --[[ Name: get_tier3_combo_mult ]] --[[ Line: 306 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            local _, _, v86 = v_u_6:get_combo_multiplier(p_u_13)
            return v86;
        end;
        v21.get_tier2_combo_count = function(_) --[[ Name: get_tier2_combo_count ]] --[[ Line: 307 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            local _, v87 = v_u_6:get_combo_thresholds(p_u_13)
            return v87;
        end;
        v21.get_tier2_combo_mult = function(_) --[[ Name: get_tier2_combo_mult ]] --[[ Line: 308 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            local _, v88 = v_u_6:get_combo_multiplier(p_u_13)
            return v88;
        end;
        v21.get_tier1_combo_count = function(_) --[[ Name: get_tier1_combo_count ]] --[[ Line: 309 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            return v_u_6:get_combo_thresholds(p_u_13);
        end;
        v21.get_tier1_combo_mult = function(_) --[[ Name: get_tier1_combo_mult ]] --[[ Line: 310 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            return v_u_6:get_combo_multiplier(p_u_13);
        end;
        v21.get_note_prebuffer_time_ms = function(_) --[[ Name: get_note_prebuffer_time_ms ]] --[[ Line: 312 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_23, (copy 3): p_u_13 ]]
            return v_u_6:get_note_prebuffer_time_ms(v_u_23, p_u_13);
        end;
        v21.get_powerbar_base_decay_time_seconds = function(_) --[[ Name: get_powerbar_base_decay_time_seconds ]] --[[ Line: 313 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_24, (copy 3): p_u_13 ]]
            return v_u_6:get_powerbar_base_decay_time_seconds(v_u_24, p_u_13);
        end;
        v21.get_powerbar_noteresult_fill = function(_, p89, p90) --[[ Name: get_powerbar_noteresult_fill ]] --[[ Line: 314 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            return v_u_6:get_powerbar_noteresult_fill(p89, p90, p_u_13);
        end;
        v21.get_powerbar_noteresult_drain = function(_, p91, _, _) --[[ Name: get_powerbar_noteresult_drain ]] --[[ Line: 315 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): p_u_13 ]]
            return v_u_6:get_powerbar_noteresult_drain(p91, p_u_13);
        end;
        local v_u_92 = true
        v21.set_chain_break_gear_stats_behaviour = function(_, p93) --[[ Name: set_chain_break_gear_stats_behaviour ]] --[[ Line: 318 ]]
            --[[ Upvalues: (ref 1): v_u_92 ]]
            v_u_92 = p93
        end;
        v21.get_chain_break = function(_, p94) --[[ Name: get_chain_break ]] --[[ Line: 320 ]]
            --[[ Upvalues: (ref 1): v_u_92, (ref 2): v_u_6, (copy 3): p_u_13 ]]
            return v_u_92 ~= true and 0 or v_u_6:get_chain_break(p94, p_u_13);
        end;
        v21.get_color_point_bonus_for_noteresult = function(_, p95) --[[ Name: get_color_point_bonus_for_noteresult ]] --[[ Line: 328 ]]
            --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_25, (copy 3): p_u_13 ]]
            return v_u_6:get_color_point_bonus_for_noteresult_colortable_statsdict(p95, v_u_25, p_u_13);
        end;
        return v21;
    end
};
