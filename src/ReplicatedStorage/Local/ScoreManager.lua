-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:27 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Local.NoteBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_3 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.Shared.PowerBarState)
local v_u_5 = require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Shared.PlayerScore)
local v_u_8 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_9 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.Constants)
local v_u_10 = require(game.ReplicatedStorage.Shared.EventString)
local v_u_11 = require(game.ReplicatedStorage.Local.Spectate.LocalNotePlaybackSequenceManager)
local v_u_12 = require(game.ReplicatedStorage.Shared.NoteHitMode)
local v_u_13 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_14 = require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Shared.FlashEvery)
local v_u_15 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_16 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_17 = require(game.ReplicatedStorage.Shared.NoteResultPositionSetting)
local v_u_18 = require(game.ReplicatedStorage.Shared.NoteResultSpreadSetting)
local v_u_19 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_20 = require(game.ReplicatedStorage.Effects.NoteResultPopupEffectV2)
local v_u_21 = require(game.ReplicatedStorage.Local.NoteDecal.NoteResultPopupEffectDecal)
return {
    ["new"] = function(_, p_u_22) --[[ Name: new ]] --[[ Line: 32 ]]
        --[[ Upvalues: (copy 1): v_u_11, (copy 2): v_u_14, (copy 3): v_u_9, (copy 4): v_u_7, (copy 5): v_u_5, (copy 6): v_u_8, (copy 7): v_u_13, (copy 8): v_u_19, (copy 9): v_u_17, (copy 10): v_u_15, (copy 11): v_u_1, (copy 12): v_u_18, (copy 13): v_u_21, (copy 14): v_u_20, (copy 15): v_u_2, (copy 16): v_u_12, (copy 17): v_u_16, (copy 18): v_u_6, (copy 19): v_u_3, (copy 20): v_u_10, (copy 21): v_u_4 ]]
        local v_u_24 = {
            ["get_power_bar_manual"] = function(_) --[[ Name: get_power_bar_manual ]] --[[ Line: 541 ]]
                return false;
            end,
            ["display_powerbar_active"] = function(p23) --[[ Name: display_powerbar_active ]] --[[ Line: 558 ]]
                return p23:get_matchmode_score_obj():is_powerbar_active();
            end,
            ["teardown"] = function(_) end
        }
        local v_u_25 = {
            ["Slot"] = 0,
            ["Track"] = 0
        }
        local v_u_26 = nil
        local v_u_27 = false
        local v_u_28 = nil
        local v_u_29 = nil
        v_u_24.get_score_objs = function(_) --[[ Name: get_score_objs ]] --[[ Line: 44 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_29 ]]
            return v_u_28, v_u_29;
        end;
        local v_u_30 = true
        local v_u_31 = nil
        v_u_24.set_should_update_local_servergameinstanceplayer = function(_, p32, p33) --[[ Name: set_should_update_local_servergameinstanceplayer ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_31 ]]
            v_u_30 = p32
            v_u_31 = p33
        end;
        local v_u_34 = true
        v_u_24.set_should_local_register_hit_apply_to_powerbar = function(_, p35) --[[ Name: set_should_local_register_hit_apply_to_powerbar ]] --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_34 ]]
            v_u_34 = p35
        end;
        local v_u_36 = nil
        v_u_24.set_fn_override_create_note_result_popup = function(_, p37) --[[ Name: set_fn_override_create_note_result_popup ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): v_u_36 ]]
            v_u_36 = p37
        end;
        local v_u_38 = v_u_11:new(p_u_22)
        v_u_24.initialize_localplayer = function(_, _, p39) --[[ Name: initialize_localplayer ]] --[[ Line: 62 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_9, (ref 3): v_u_28, (ref 4): v_u_7, (copy 5): p_u_22, (ref 6): v_u_5, (ref 7): v_u_29 ]]
            if v_u_14:get_selected_mode() == v_u_14.Casual then
                p39[v_u_9.Type.PerfectTime] = 0
                p39[v_u_9.Type.GreatTime] = 0
                p39[v_u_9.Type.OkayTime] = 0
            end;
            v_u_28 = v_u_7:new(p_u_22:es_gamelocal_get_audiomanager():get_song_key(), p39)
            if v_u_5.ScoreCalculationTreatAsNaked == true then
                v_u_28 = v_u_7:new(p_u_22:es_gamelocal_get_audiomanager():get_song_key(), v_u_9:statsdict_base())
            end;
            v_u_28:set_apply_hit_to_powerbar(false)
            v_u_29 = v_u_7:new(p_u_22:es_gamelocal_get_audiomanager():get_song_key(), v_u_9:statsdict_base())
            v_u_29:set_apply_hit_to_powerbar(false)
        end;
        local v_u_40 = v_u_8:new()
        v_u_24.get_registered_hits = function(_) --[[ Name: get_registered_hits ]] --[[ Line: 82 ]]
            --[[ Upvalues: (copy 1): v_u_40 ]]
            return v_u_40;
        end;
        v_u_24.get_primary_color = function(_) --[[ Name: get_primary_color ]] --[[ Line: 84 ]]
            --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_22 ]]
            return v_u_13:songkey_primary_color(p_u_22:es_gamelocal_get_audiomanager():get_song_key());
        end;
        v_u_24.get_secondary_color = function(_) --[[ Name: get_secondary_color ]] --[[ Line: 85 ]]
            --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_22 ]]
            return v_u_13:songkey_secondary_color(p_u_22:es_gamelocal_get_audiomanager():get_song_key());
        end;
        local v_u_41 = true
        v_u_24.was_last_local_hit_whiff = function(_) --[[ Name: was_last_local_hit_whiff ]] --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): v_u_41 ]]
            return v_u_41;
        end;
        v_u_24.create_note_result_popup = function(p42, p43, p44, p45, p46, p47, p48, p49, p50, p51, p52, p53) --[[ Name: create_note_result_popup ]] --[[ Line: 90 ]]
            --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_19, (ref 3): v_u_17, (ref 4): v_u_15, (ref 5): v_u_1, (ref 6): v_u_18, (ref 7): v_u_26, (ref 8): v_u_21, (ref 9): v_u_20, (copy 10): v_u_25 ]]
            local v54 = p_u_22._player_settings_manager:get_key(v_u_19.Key.NoteResultPositionSetting)
            local v55 = p_u_22._player_settings_manager:get_key(v_u_19.Key.NoteResultSpreadSetting)
            if v54 ~= v_u_17.Hidden then
                if p43:get_active_note_display_mode() == v_u_15.DecalUp or p43:get_active_note_display_mode() == v_u_15.DecalDown then
                    local _, v56 = p_u_22._ui_manager:get_decal_ui_manager():get_start_end_point_for_track_system_index(p43, p46)
                    local v57 = v_u_1:screen_size()
                    if v55 == v_u_18.Centered then
                        v56 = Vector2.new(v57.X * 0.5, v56.Y)
                    end;
                    local v58 = Vector2.new(v56.X, v56.Y)
                    if v54 == v_u_17.Middle then
                        v58 = Vector2.new(v56.X, v57.Y * 0.5)
                    elseif v54 == v_u_17.Top then
                        local v59 = p43:get_active_note_display_mode()
                        if v59 == v_u_15.DecalDown then
                            v58 = Vector2.new(v56.X, v57.Y * 0.2)
                        elseif v59 == v_u_15.DecalUp then
                            v58 = Vector2.new(v56.X, v57.Y * 0.8)
                        end;
                    end;
                    v_u_26 = p_u_22._effects:add_effect(v_u_21:new(p_u_22, v58, p47, p48, p49, p50, p51, p42:get_primary_color(), p52, p42:get_secondary_color(), p53))
                else
                    Vector3.new()
                    local v60 = p44:get_end_position()
                    local v61
                    if v54 == v_u_17.Middle or v54 == v_u_17.Top then
                        local v62 = v_u_1:screen_size()
                        local v63 = p_u_22._spui:calculate_center_position_and_normal_for_distance((v_u_1:get_camera_cframe().p - v60).Magnitude)
                        local v64 = v55 == v_u_18.Centered and 0.5 or v_u_1:get_camera():WorldToScreenPoint(v60).X / v62.X
                        local v65
                        if v54 == v_u_17.Middle then
                            v65 = p_u_22:show_fullscreen_mobile_ui() and 0.4 or 0.5
                        else
                            v65 = p_u_22:show_fullscreen_mobile_ui() and 0.2 or 0.25
                        end;
                        v61 = p_u_22._spui:calculate_nxy_position(v64, v65, v63)
                    else
                        if v55 == v_u_18.Centered then
                            v60 = (p43:es_get_track(1):get_end_position() + p43:es_get_track(4):get_end_position()) * 0.5
                        end;
                        v61 = v60 + Vector3.new(0, 1.5, 0) + p44:world_to_player_dirn() * 2
                    end;
                    v_u_26 = p_u_22._effects:add_effect(v_u_20:new(p_u_22, v61, p47, p48, p49, p50, p51, p42:get_primary_color(), p52, p42:get_secondary_color(), p53))
                end;
            end;
            v_u_25.Slot = p45
            v_u_25.Track = p46
        end;
        v_u_24.es_playerscore_register_hit = function(p66, _, p67, p68, p69, p70) --[[ Name: es_playerscore_register_hit ]] --[[ Line: 200 ]]
            --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_31, (ref 3): v_u_30, (ref 4): v_u_26, (copy 5): v_u_25, (ref 6): v_u_2, (ref 7): v_u_41, (ref 8): v_u_28, (ref 9): v_u_29, (ref 10): v_u_12, (ref 11): v_u_16, (ref 12): v_u_6, (ref 13): v_u_34, (ref 14): v_u_14, (copy 15): v_u_38, (ref 16): v_u_27, (ref 17): v_u_3, (ref 18): v_u_36, (copy 19): v_u_40 ]]
            local v71 = p70 == nil and {} or p70
            if v71.PlaySFX == nil then
                v71.PlaySFX = true
            end;
            if v71.HoldEffectPosition == nil then
                v71.HoldEffectPosition = p_u_22:es_gamelocal_tracksystem_of_index(p68):es_get_track(p69):get_end_position()
            end;
            if v71.NotifyServer == nil then
                v71.NotifyServer = true
            end;
            local v72 = v71.HitTime == nil and 0 or v71.HitTime
            local v73 = v71.Delta == nil and 0 or v71.Delta
            p_u_22._world_effect_manager:notify_hit(p_u_22, p67, p68, p69)
            if p68 == p_u_22:get_local_game_slot() then
                if v_u_31 ~= nil then
                    v_u_31(p67, p69, v71)
                end;
                if v_u_30 == true then
                    if v_u_26 ~= nil and (p68 == v_u_25.Slot and (p69 == v_u_25.Track and p67 == v_u_2.NoteResult_Miss)) then
                        v_u_26:set_anim_t(1)
                        v_u_26 = nil
                    end;
                    if v71.WhiffMiss == true then
                        v_u_41 = true
                    elseif p67 ~= v_u_2.NoteResult_Miss then
                        v_u_41 = false
                    end;
                    local v74 = v_u_28:get_chain()
                    local v75 = v_u_29:get_chain()
                    local v76 = v71[v_u_12.ParamNoteHitMode]
                    if v_u_16:test_enum_member(v76, v_u_12) ~= true then
                        v_u_6:warnf("ScoreManager:es_playerscore_register_hit note_hit_mode nil")
                        v76 = v_u_12.WhiffMiss
                    end;
                    if v74 == 0 and (v75 == 0 and v76 == v_u_12.WhiffMiss) then
                        return;
                    else
                        if v_u_34 then
                            v_u_29:es_playerscore_apply_hit_to_powerbar(p67)
                            v_u_28:es_playerscore_apply_hit_to_powerbar(p67)
                            v_u_29:update(0, false, false)
                            v_u_28:update(0, false, false)
                        end;
                        local v77 = p_u_22:es_gamelocal_tracksystem_of_index(p68)
                        local v78 = v77:es_get_track(p69)
                        local v79, v80, v81, v82, v83, v84 = v_u_29:register_hit_noteresult_hitmode(p67, v76)
                        v_u_29:get_raise_chain_broken()
                        v_u_29:get_raise_chain_broken_at()
                        v_u_29:get_chain()
                        local v85, v86, v87, v88, v89, v90 = v_u_28:register_hit_noteresult_hitmode(p67, v76)
                        v_u_28:get_raise_chain_broken()
                        v_u_28:get_raise_chain_broken_at()
                        v_u_28:get_chain()
                        local v91, v92, v93
                        if v_u_14:get_selected_mode() == v_u_14.Casual then
                            v91 = v80 * v81
                            v92 = v_u_29:is_powerbar_active()
                            v93 = v_u_29:get_combo_threshold()
                        else
                            v91 = v86 * v87
                            v92 = v_u_28:is_powerbar_active()
                            v93 = v_u_28:get_combo_threshold()
                            v84 = v90
                            v83 = v89
                            v82 = v88
                            v79 = v85
                        end;
                        if p_u_22:is_spectate() ~= true then
                            v_u_38:add_note_event(math.floor((p_u_22:es_gamelocal_get_audiomanager():get_song_time_position_ms())), v71[v_u_12.ParamNoteIndex], p67, v73, v_u_28:is_powerbar_active(), p69, v76, p66:get_power_bar_pct(), p66:get_accuracy())
                        end;
                        if v84 == true then
                            local v94 = p_u_22._players._slots:get(p_u_22:get_local_game_slot())
                            if v94 ~= nil then
                                p66:update_servergameinstanceplayer_score(v94)
                            end;
                            if v71.PlaySFX == true and v_u_27 == false then
                                if p_u_22:is_ingame_sfx_enabled() == true then
                                    if p67 == v_u_2.NoteResult_Perfect then
                                        if v71.IsHeldNoteBegin == true then
                                            p_u_22:es_gamelocal_get_audiomanager():get_hit_sfx_group():play_first()
                                        else
                                            p_u_22:es_gamelocal_get_audiomanager():get_hit_sfx_group():play_alternating()
                                        end;
                                    elseif p67 == v_u_2.NoteResult_Great then
                                        p_u_22:es_gamelocal_get_audiomanager():get_hit_sfx_group():play_first()
                                    elseif p67 == v_u_2.NoteResult_Okay then
                                        p_u_22._sfx_manager:play_sfx(v_u_3.SFX_DRUM_OKAY, 0.2)
                                    else
                                        p_u_22._sfx_manager:play_sfx(v_u_3.SFX_MISS)
                                    end;
                                end;
                                v_u_27 = true
                            end;
                            if v_u_36 == nil then
                                p66:create_note_result_popup(v77, v78, p68, p69, p67, v79, v91, v92, v93, v82, v83)
                            else
                                v_u_36(v77, v78, p68, p69, p67, v79, v91, v92, v93, v82, v83)
                            end;
                            if p67 == v_u_2.NoteResult_Miss then
                                if v84 then
                                    v_u_40:push_back({
                                        ["NoteResult"] = p67,
                                        ["HitTime"] = v72,
                                        ["Type"] = v71.Type
                                    })
                                    return;
                                end;
                            else
                                v_u_40:push_back({
                                    ["NoteResult"] = p67,
                                    ["HitTime"] = v72,
                                    ["Delta"] = v73,
                                    ["Fever"] = v_u_28:is_powerbar_active(),
                                    ["Type"] = v71.Type
                                })
                            end;
                        end;
                    end;
                else
                    return;
                end;
            else
                return;
            end;
        end;
        local function f_send_local_finished(p95) --[[ Name: send_local_finished ]] --[[ Line: 432 ]]
            --[[ Upvalues: (copy 1): v_u_38, (ref 2): v_u_28, (ref 3): v_u_10, (copy 4): v_u_24, (ref 5): v_u_1, (ref 6): v_u_5, (copy 7): p_u_22, (ref 8): v_u_4 ]]
            local v96 = v_u_38:process_pending_playback_sequence_and_serialize_to_table()
            local v97, v98, v99, v100, v101 = v_u_28:get_stat_counts()
            local v102 = v_u_10
            local v103 = {
                [v_u_10.ES_END_SCORE] = v_u_24:get_score(),
                [v_u_10.ES_END_NAKEDSCORE] = v_u_24:get_naked_score(),
                [v_u_10.ES_END_CHAIN] = v_u_24:get_chain(),
                [v_u_10.ES_END_ACCURACY] = v_u_24:get_accuracy(),
                [v_u_10.ES_END_PERFECTCOUNT] = v97,
                [v_u_10.ES_END_GREATCOUNT] = v98,
                [v_u_10.ES_END_OKAYCOUNT] = v99,
                [v_u_10.ES_END_MISSCOUNT] = v100,
                [v_u_10.ES_END_MAXCHAIN] = v101,
                [v_u_10.ES_END_FEVERPERCENTAGE] = v_u_24:get_fever_percentage()
            }
            v103[v_u_10.ES_END_AUTOPLAY] = v_u_1:tobool(v_u_5.LocalAutoPlay or v_u_5.PerfectAutoPlay)
            v103[v_u_10.ES_END_COMBOMAX] = v101
            p_u_22._evt:fire_event_to_server(v_u_4.EVT_Game_ClientNotifyLocalFinished, p95, v102:es_table_convert(v103), v96)
        end;
        v_u_24.notify_local_finished = function(p104) --[[ Name: notify_local_finished ]] --[[ Line: 452 ]]
            --[[ Upvalues: (copy 1): p_u_22, (copy 2): f_send_local_finished, (ref 3): v_u_5, (ref 4): v_u_6 ]]
            if p_u_22:is_networked() then
                f_send_local_finished(false)
            end;
            if v_u_5.PrintGearScore == true then
                v_u_6:puts("***GearMult(%.2f)", p104:get_score() / p104:get_naked_score())
                v_u_6:puts("***Accuracy(%.2f)", p104:get_accuracy())
            end;
        end;
        v_u_24.notify_local_early_quit = function(_) --[[ Name: notify_local_early_quit ]] --[[ Line: 463 ]]
            --[[ Upvalues: (copy 1): p_u_22, (copy 2): f_send_local_finished ]]
            if p_u_22:is_networked() then
                f_send_local_finished(true)
            end;
        end;
        v_u_24.post_update = function(_, _) --[[ Name: post_update ]] --[[ Line: 470 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_28, (ref 3): v_u_27 ]]
            v_u_29:post_update()
            v_u_28:post_update()
            v_u_27 = false
        end;
        v_u_24.get_chain_broken = function(_) --[[ Name: get_chain_broken ]] --[[ Line: 485 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28:get_raise_chain_broken(), v_u_28:get_raise_chain_broken_at();
        end;
        v_u_24.update = function(_, p105, _) --[[ Name: update ]] --[[ Line: 491 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_30, (copy 3): p_u_22, (ref 4): v_u_29, (ref 5): v_u_14, (ref 6): v_u_28, (ref 7): v_u_3, (copy 8): v_u_38 ]]
            if v_u_26 ~= nil and v_u_26:get_anim_t() > 0.25 then
                v_u_26 = nil
            end;
            if v_u_30 then
                local v106 = p_u_22._players._slots:get(p_u_22:get_local_game_slot())
                local v107 = false
                local v108, v109 = v_u_29:update(p105, false, false)
                if v108 then
                    v106._naked_power_bar_active = v109
                    v107 = v_u_14:get_selected_mode() == v_u_14.Casual and v109 and true or v107
                end;
                local v110, v111 = v_u_28:update(p105, false, false)
                if v110 then
                    v106._power_bar_active = v111
                    v107 = v_u_14:get_selected_mode() == v_u_14.Compete and v111 and true or v107
                end;
                if v107 then
                    p_u_22._sfx_manager:play_sfx(v_u_3.SFX_FEVERCHEER_1, 0.3)
                end;
            end;
            v_u_38:update(p105)
        end;
        v_u_24.get_accuracy = function(_) --[[ Name: get_accuracy ]] --[[ Line: 530 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28:get_accuracy();
        end;
        v_u_24.get_score = function(_) --[[ Name: get_score ]] --[[ Line: 534 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28:get_score();
        end;
        v_u_24.get_naked_score = function(_) --[[ Name: get_naked_score ]] --[[ Line: 535 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            return v_u_29:get_score();
        end;
        v_u_24.get_chain = function(_) --[[ Name: get_chain ]] --[[ Line: 536 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28:get_chain();
        end;
        v_u_24.get_chain_multiplier = function(_) --[[ Name: get_chain_multiplier ]] --[[ Line: 537 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28:get_chain_multiplier();
        end;
        v_u_24.is_powerbar_active = function(_) --[[ Name: is_powerbar_active ]] --[[ Line: 539 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28:is_powerbar_active();
        end;
        v_u_24.get_power_bar_pct = function(_) --[[ Name: get_power_bar_pct ]] --[[ Line: 540 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28:get_power_bar_pct();
        end;
        v_u_24.get_powerbar_notes_count = function(_) --[[ Name: get_powerbar_notes_count ]] --[[ Line: 542 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28:get_powerbar_notes_count();
        end;
        v_u_24.get_fever_percentage = function(_) --[[ Name: get_fever_percentage ]] --[[ Line: 543 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28:get_fever_percentage();
        end;
        v_u_24.get_end_records = function(_) --[[ Name: get_end_records ]] --[[ Line: 544 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            local v112, v113, v114, v115, v116 = v_u_28:get_stat_counts()
            return v112, v113, v114, v115, v116;
        end;
        v_u_24.get_local_note_count = function(_) --[[ Name: get_local_note_count ]] --[[ Line: 548 ]]
            --[[ Upvalues: (ref 1): v_u_28 ]]
            return v_u_28:get_local_note_count();
        end;
        v_u_24.get_matchmode_score_obj = function(_) --[[ Name: get_matchmode_score_obj ]] --[[ Line: 550 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_28, (ref 3): v_u_29 ]]
            if v_u_14:get_selected_mode() == v_u_14.Compete then
                return v_u_28;
            else
                return v_u_29;
            end;
        end;
        v_u_24.update_servergameinstanceplayer_score = function(_, p117) --[[ Name: update_servergameinstanceplayer_score ]] --[[ Line: 564 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_29 ]]
            p117._power_bar_active = v_u_28:is_powerbar_active()
            p117._fever_percentage = v_u_28:get_power_bar_pct()
            p117._score = v_u_28:get_score()
            p117._chain = v_u_28:get_chain()
            p117._naked_power_bar_active = v_u_29:is_powerbar_active()
            p117._naked_fever_percentage = v_u_29:get_power_bar_pct()
            p117._naked_score = v_u_29:get_score()
            p117._naked_chain = v_u_29:get_chain()
        end;
        local v_u_118 = 0
        v_u_24.set_spectate_replicate_accuracy = function(_, p119) --[[ Name: set_spectate_replicate_accuracy ]] --[[ Line: 577 ]]
            --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_6, (ref 3): v_u_118 ]]
            if p_u_22:is_spectate() ~= true then
                v_u_6:errf("ScoreManager:set_spectate_replicate_accuracy when not spectate")
            end;
            v_u_118 = p119
        end;
        v_u_24.get_spectate_replicate_accuracy = function(_) --[[ Name: get_spectate_replicate_accuracy ]] --[[ Line: 582 ]]
            --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_6, (ref 3): v_u_118 ]]
            if p_u_22:is_spectate() ~= true then
                v_u_6:errf("ScoreManager:get_spectate_replicate_accuracy when not spectate")
            end;
            return v_u_118;
        end;
        v_u_24.resync_note_sequence = function(_, p120) --[[ Name: resync_note_sequence ]] --[[ Line: 587 ]]
            --[[ Upvalues: (copy 1): v_u_38 ]]
            v_u_38:resync_note_sequence(p120)
        end;
        v_u_24.reset = function(_) --[[ Name: reset ]] --[[ Line: 591 ]]
            --[[ Upvalues: (copy 1): v_u_38 ]]
            v_u_38:reset()
        end;
        return v_u_24;
    end
};
