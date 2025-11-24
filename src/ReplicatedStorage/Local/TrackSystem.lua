-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:27 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_2 = require(game.ReplicatedStorage.Local.Track)
local v_u_3 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_4 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_8 = require(game.ReplicatedStorage.Shared.RandomLua)
local v_u_9 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_10 = require(game.ReplicatedStorage.Shared.NoteHitMode)
require(game.ReplicatedStorage.Shared.EventString)
require(game.ReplicatedStorage.Shared.NoteSkinColor)
local v_u_11 = require(game.ReplicatedStorage.Shared.GameNoteSkinInfo)
local v_u_12 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_13 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
local v_u_15 = require(game.ReplicatedStorage.Shared.Note2DSettings)
return {
    ["new"] = function(_, p_u_16, p_u_17) --[[ Name: new ]] --[[ Line: 22 ]]
        --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_1, (copy 3): v_u_11, (copy 4): v_u_13, (copy 5): v_u_14, (copy 6): v_u_15, (copy 7): v_u_12, (copy 8): v_u_9, (copy 9): v_u_2, (copy 10): v_u_3, (copy 11): v_u_7, (copy 12): v_u_6, (copy 13): v_u_4, (copy 14): v_u_5, (copy 15): v_u_10 ]]
        local v_u_19 = {
            ["init"] = function(p18) --[[ Name: init ]] --[[ Line: 69 ]]
                p18:tracksystem_update_note_display_mode()
            end
        }
        local v_u_20 = v_u_8.mwc(0)
        local v_u_21 = v_u_1:new()
        local v_u_22 = v_u_1:new()
        local v_u_23 = v_u_1:new()
        local v_u_24 = p_u_16._player_settings_manager:get_note_speed_multiplier()
        local v_u_25 = 1
        v_u_19.get_audio_data_index = function(_) --[[ Name: get_audio_data_index ]] --[[ Line: 31 ]]
            --[[ Upvalues: (ref 1): v_u_25 ]]
            return v_u_25;
        end;
        v_u_19.set_audio_data_index = function(_, p26) --[[ Name: set_audio_data_index ]] --[[ Line: 32 ]]
            --[[ Upvalues: (ref 1): v_u_25 ]]
            v_u_25 = p26
        end;
        local v_u_27 = nil
        v_u_19.get_statsdict = function(_) --[[ Name: get_statsdict ]] --[[ Line: 35 ]]
            --[[ Upvalues: (ref 1): v_u_27 ]]
            return v_u_27;
        end;
        v_u_19.tracksystem_autoplayer_init = function(_, p28) --[[ Name: tracksystem_autoplayer_init ]] --[[ Line: 36 ]]
            --[[ Upvalues: (ref 1): v_u_21 ]]
            v_u_21 = p28
        end;
        local v_u_29 = v_u_11:get_default_base_color_list()
        local v_u_30 = v_u_11:get_default_fever_color_list()
        v_u_19.get_basecolor_list = function(_) --[[ Name: get_basecolor_list ]] --[[ Line: 40 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            return v_u_29;
        end;
        v_u_19.get_fevercolor_list = function(_) --[[ Name: get_fevercolor_list ]] --[[ Line: 41 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            return v_u_30;
        end;
        local l_Default_0 = v_u_13.Default
        local v_u_31 = v_u_14:singleton():get_default_notedecal_id()
        local l_Default_1 = v_u_15.Width.Default
        local l_Default_2 = v_u_15.Position.Default
        local l_Default_3 = v_u_15.Background.Default
        v_u_19.get_player_note_display_mode_and_decal_id = function(_) --[[ Name: get_player_note_display_mode_and_decal_id ]] --[[ Line: 49 ]]
            --[[ Upvalues: (ref 1): l_Default_0, (ref 2): v_u_31 ]]
            return l_Default_0, v_u_31;
        end;
        v_u_19.get_player_note2d_settings = function(_) --[[ Name: get_player_note2d_settings ]] --[[ Line: 50 ]]
            --[[ Upvalues: (ref 1): l_Default_1, (ref 2): l_Default_2, (ref 3): l_Default_3 ]]
            return l_Default_1, l_Default_2, l_Default_3;
        end;
        local l_Default_4 = v_u_13.Default
        v_u_19.get_active_note_display_mode = function(_) --[[ Name: get_active_note_display_mode ]] --[[ Line: 54 ]]
            --[[ Upvalues: (ref 1): l_Default_4 ]]
            return l_Default_4;
        end;
        v_u_19.tracksystem_update_note_display_mode = function(p32) --[[ Name: tracksystem_update_note_display_mode ]] --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): l_Default_0, (ref 3): p_u_16, (ref 4): l_Default_4, (copy 5): v_u_23 ]]
            local l_Default_5 = v_u_13.Default
            if l_Default_0 ~= v_u_13.Default and p32:get_game_slot() == p_u_16:get_local_game_slot() then
                l_Default_5 = l_Default_0
            end;
            l_Default_4 = l_Default_5
            for v33 = 1, v_u_23:count() do
                v_u_23:get(v33):set_note_display_mode(l_Default_5)
            end;
        end;
        local v_u_34 = false
        v_u_19.set_force_update_auto_player = function(_, p35) --[[ Name: set_force_update_auto_player ]] --[[ Line: 75 ]]
            --[[ Upvalues: (ref 1): v_u_34 ]]
            v_u_34 = p35
        end;
        v_u_19.get_force_update_auto_player = function(_) --[[ Name: get_force_update_auto_player ]] --[[ Line: 76 ]]
            --[[ Upvalues: (ref 1): v_u_34 ]]
            return v_u_34;
        end;
        v_u_19.set_game_noteskin_info = function(_, p36, p37) --[[ Name: set_game_noteskin_info ]] --[[ Line: 78 ]]
            --[[ Upvalues: (ref 1): v_u_12, (copy 2): v_u_23, (ref 3): v_u_29, (ref 4): v_u_30, (ref 5): v_u_24, (ref 6): l_Default_0, (ref 7): v_u_31, (ref 8): l_Default_1, (ref 9): l_Default_2, (ref 10): l_Default_3 ]]
            local v38 = p36:get_slot_basecolor_list(p37)
            local v39 = p36:get_slot_fevercolor_list(p37)
            local v40 = p36:get_slot_notespeed_multiplier(p37)
            local v41 = p36:get_slot_display_mode(p37)
            local v42 = p36:get_slot_note_decal_id(p37)
            v_u_12:is_true(v38:count() == v_u_23:count())
            v_u_12:is_true(v39:count() == v_u_23:count())
            v_u_12:is_number(v40)
            v_u_29 = v38
            v_u_30 = v39
            v_u_24 = v40
            l_Default_0 = v41
            v_u_31 = v42
            l_Default_1 = p36:get_slot_note2d_settings_width(p37)
            l_Default_2 = p36:get_slot_note2d_setting_position(p37)
            l_Default_3 = p36:get_slot_note2d_setting_background(p37)
            for v43 = 1, v_u_23:count() do
                v_u_23:get(v43):set_game_noteskin_colors(v_u_29:get(v43):to_color3(), v_u_30:get(v43):to_color3())
            end;
        end;
        v_u_21.update = function(_) end;
        v_u_21.on_switch_focus_slot = function(_) end;
        if p_u_16._players._slots:contains(p_u_17) then
            v_u_27 = p_u_16._players._slots:get(p_u_17)._gear_stats
        else
            v_u_27 = v_u_9:statsdict_base()
        end;
        local function f_cons() --[[ Name: cons ]] --[[ Line: 113 ]]
            --[[ Upvalues: (copy 1): v_u_23, (ref 2): v_u_2, (copy 3): v_u_19, (ref 4): p_u_16 ]]
            v_u_23:push_back(v_u_2:new(v_u_19, p_u_16, 1))
            v_u_23:push_back(v_u_2:new(v_u_19, p_u_16, 2))
            v_u_23:push_back(v_u_2:new(v_u_19, p_u_16, 3))
            v_u_23:push_back(v_u_2:new(v_u_19, p_u_16, 4))
        end;
        v_u_19.push_back_note = function(_, p44) --[[ Name: push_back_note ]] --[[ Line: 120 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_30, (copy 3): v_u_22 ]]
            p44:set_note_colors(v_u_29:get(p44:get_track_index()), v_u_30:get(p44:get_track_index()))
            v_u_22:push_back(p44)
        end;
        v_u_19.reset = function(_) --[[ Name: reset ]] --[[ Line: 128 ]]
            --[[ Upvalues: (copy 1): v_u_22, (ref 2): p_u_16 ]]
            for v45 = 1, v_u_22:count() do
                v_u_22:get(v45):do_remove(p_u_16)
            end;
            v_u_22:clear()
        end;
        v_u_19.es_tracksystem_get_notes = function(_) --[[ Name: es_tracksystem_get_notes ]] --[[ Line: 136 ]]
            --[[ Upvalues: (copy 1): v_u_22 ]]
            return v_u_22;
        end;
        v_u_19.get_perfect_upper_lower_time = function(_) --[[ Name: get_perfect_upper_lower_time ]] --[[ Line: 137 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            return v_u_9:get_perfect_upper_lower_time(v_u_27);
        end;
        v_u_19.get_great_upper_lower_time = function(_) --[[ Name: get_great_upper_lower_time ]] --[[ Line: 138 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            return v_u_9:get_great_upper_lower_time(v_u_27);
        end;
        v_u_19.get_okay_upper_lower_time = function(_) --[[ Name: get_okay_upper_lower_time ]] --[[ Line: 139 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            return v_u_9:get_okay_upper_lower_time(v_u_27);
        end;
        v_u_19.get_perfect_points = function(_) --[[ Name: get_perfect_points ]] --[[ Line: 140 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            return v_u_9:get_perfect_points(v_u_27);
        end;
        v_u_19.get_great_points = function(_) --[[ Name: get_great_points ]] --[[ Line: 141 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            return v_u_9:get_great_points(v_u_27);
        end;
        v_u_19.get_okay_points = function(_) --[[ Name: get_okay_points ]] --[[ Line: 142 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            return v_u_9:get_okay_points(v_u_27);
        end;
        v_u_19.get_powerbar_multiplier = function(_) --[[ Name: get_powerbar_multiplier ]] --[[ Line: 143 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            return v_u_9:get_powerbar_multiplier(v_u_27);
        end;
        v_u_19.get_tier3_combo_count = function(_) --[[ Name: get_tier3_combo_count ]] --[[ Line: 144 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            local _, _, v46 = v_u_9:get_combo_thresholds(v_u_27)
            return v46;
        end;
        v_u_19.get_tier3_combo_mult = function(_) --[[ Name: get_tier3_combo_mult ]] --[[ Line: 145 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            local _, _, v47 = v_u_9:get_combo_multiplier(v_u_27)
            return v47;
        end;
        v_u_19.get_tier2_combo_count = function(_) --[[ Name: get_tier2_combo_count ]] --[[ Line: 146 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            local _, v48 = v_u_9:get_combo_thresholds(v_u_27)
            return v48;
        end;
        v_u_19.get_tier2_combo_mult = function(_) --[[ Name: get_tier2_combo_mult ]] --[[ Line: 147 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            local _, v49 = v_u_9:get_combo_multiplier(v_u_27)
            return v49;
        end;
        v_u_19.get_tier1_combo_count = function(_) --[[ Name: get_tier1_combo_count ]] --[[ Line: 148 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            return v_u_9:get_combo_thresholds(v_u_27);
        end;
        v_u_19.get_tier1_combo_mult = function(_) --[[ Name: get_tier1_combo_mult ]] --[[ Line: 149 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            return v_u_9:get_combo_multiplier(v_u_27);
        end;
        v_u_19.get_powerbar_base_decay_time_seconds = function(_) --[[ Name: get_powerbar_base_decay_time_seconds ]] --[[ Line: 150 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): p_u_16, (ref 3): v_u_27 ]]
            return v_u_9:get_powerbar_base_decay_time_seconds(p_u_16:es_gamelocal_get_audiomanager():get_song_length_ms(), v_u_27);
        end;
        v_u_19.get_powerbar_noteresult_fill = function(_, p50, p51) --[[ Name: get_powerbar_noteresult_fill ]] --[[ Line: 151 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            return v_u_9:get_powerbar_noteresult_fill(p50, p51, v_u_27);
        end;
        v_u_19.get_powerbar_noteresult_drain = function(_, p52) --[[ Name: get_powerbar_noteresult_drain ]] --[[ Line: 152 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            return v_u_9:get_powerbar_noteresult_drain(p52, v_u_27);
        end;
        v_u_19.get_chain_break = function(_, p53) --[[ Name: get_chain_break ]] --[[ Line: 153 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_27 ]]
            v_u_9:get_chain_break(p53, v_u_27)
        end;
        v_u_19.get_player_world_center = function(_) --[[ Name: get_player_world_center ]] --[[ Line: 154 ]]
            --[[ Upvalues: (ref 1): p_u_16 ]]
            return p_u_16:get_game_environment_center();
        end;
        v_u_19.get_player_world_position = function(_) --[[ Name: get_player_world_position ]] --[[ Line: 155 ]]
            --[[ Upvalues: (ref 1): v_u_3, (copy 2): p_u_17 ]]
            return v_u_3:slot_to_world_position(p_u_17);
        end;
        v_u_19.get_game_slot = function(_) --[[ Name: get_game_slot ]] --[[ Line: 156 ]]
            --[[ Upvalues: (copy 1): p_u_17 ]]
            return p_u_17;
        end;
        v_u_19.es_get_track = function(_, p54) --[[ Name: es_get_track ]] --[[ Line: 157 ]]
            --[[ Upvalues: (copy 1): v_u_23 ]]
            return v_u_23:get(p54);
        end;
        v_u_19.get_note_prebuffer_time_ms = function(_) --[[ Name: get_note_prebuffer_time_ms ]] --[[ Line: 160 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): p_u_16, (ref 3): v_u_27, (ref 4): v_u_24 ]]
            return v_u_9:get_note_prebuffer_time_ms(p_u_16:es_gamelocal_get_audiomanager():get_note_prebuffer_base_time_ms(), v_u_27) * v_u_24;
        end;
        local v_u_55 = 0
        local v_u_56 = 0
        v_u_19.gen_rand_note = function(_, _, p57) --[[ Name: gen_rand_note ]] --[[ Line: 167 ]]
            --[[ Upvalues: (copy 1): v_u_20, (ref 2): v_u_55, (ref 3): v_u_56 ]]
            local v58 = v_u_20:rand_rangei(1, 5)
            if v58 == v_u_55 and math.abs(p57 - v_u_56) < 10 then
                while v58 == v_u_55 do
                    v58 = v_u_20:rand_rangei(1, 5)
                end;
            end;
            v_u_55 = v58
            v_u_56 = p57
            return v58;
        end;
        v_u_19.es_teardown = function(p59) --[[ Name: es_teardown ]] --[[ Line: 181 ]]
            --[[ Upvalues: (copy 1): v_u_23, (ref 2): p_u_16 ]]
            p59:reset()
            for v60 = 1, v_u_23:count() do
                v_u_23:get(v60):teardown()
            end;
            v_u_23:clear()
            p_u_16 = nil
        end;
        v_u_19.es_update = function(_, p61, _) --[[ Name: es_update ]] --[[ Line: 191 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_22, (ref 3): p_u_16, (ref 4): v_u_21, (copy 5): p_u_17, (ref 6): v_u_34, (ref 7): v_u_6, (copy 8): v_u_23 ]]
            v_u_7:profilebegin("TrackSystem:update")
            v_u_7:profilebegin("_notes:update")
            for v62 = v_u_22:count(), 1, -1 do
                local v63 = v_u_22:get(v62)
                v63:update(p61, p_u_16)
                if v63:should_remove(p_u_16) then
                    v63:do_remove(p_u_16)
                    v_u_22:remove_at(v62)
                end;
            end;
            v_u_7:profileend()
            if v_u_21 and (p_u_16:get_local_game_slot() ~= p_u_17 or (p_u_16:is_spectate() == true or (v_u_34 == true or v_u_6.LocalAutoPlay == true))) then
                v_u_21:update(p61, p_u_16)
            end;
            v_u_7:profilebegin("_tracks:update")
            for v64 = 1, v_u_23:count() do
                v_u_23:get(v64):update(p61, p_u_16)
            end;
            v_u_7:profileend()
            v_u_7:profileend()
        end;
        v_u_19.es_tracksystem_press_index = function(p65, _, p66) --[[ Name: es_tracksystem_press_index ]] --[[ Line: 227 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): v_u_23, (copy 3): v_u_22, (ref 4): p_u_16, (ref 5): v_u_5, (copy 6): p_u_17, (ref 7): v_u_10 ]]
            local v67 = p65:es_get_track(p66)
            if v67 then
                v67:press()
            else
                v_u_4:warnf("TrackSystem:es_get_track(%d) is(%s) _tracks(%d)", p66, tostring(v67), v_u_23:count())
            end;
            local v68 = false
            for v69 = 1, v_u_22:count() do
                local v70 = v_u_22:get(v69)
                if v70:get_track_index() == p66 then
                    local v71, v72, v73 = v70:es_note_test_hit(p_u_16)
                    if v71 then
                        v70:es_note_on_hit(p_u_16, v72, v69, v73)
                        v68 = true
                        break;
                    end;
                end;
            end;
            if v68 == false and p_u_16:es_gamelocal_get_scoremanager():was_last_local_hit_whiff() ~= true then
                p_u_16:es_gamelocal_get_scoremanager():es_playerscore_register_hit(p_u_16, v_u_5.NoteResult_Miss, p_u_17, p66, {
                    ["PlaySFX"] = true,
                    ["PlayHoldEffect"] = false,
                    ["WhiffMiss"] = true,
                    ["HitTime"] = p_u_16:es_gamelocal_get_audiomanager():get_current_time_ms(),
                    ["Type"] = 0,
                    [v_u_10.ParamNoteHitMode] = v_u_10.WhiffMiss,
                    [v_u_10.ParamNoteIndex] = v_u_10.NoteIndexNone
                })
            end;
            return v68;
        end;
        v_u_19.es_tracksystem_release_index = function(p74, _, p75) --[[ Name: es_tracksystem_release_index ]] --[[ Line: 270 ]]
            --[[ Upvalues: (copy 1): v_u_22, (ref 2): p_u_16 ]]
            p74:es_get_track(p75):release()
            for v76 = 1, v_u_22:count() do
                local v77 = v_u_22:get(v76)
                if v77:get_track_index() == p75 then
                    local v78, v79, v80 = v77:es_note_test_release(p_u_16)
                    if v78 then
                        v77:es_note_on_release(p_u_16, v79, v76, v80)
                        return true;
                    end;
                end;
            end;
            return false;
        end;
        v_u_19.tracksystem_update_all_active_notes_display_mode = function(_) --[[ Name: tracksystem_update_all_active_notes_display_mode ]] --[[ Line: 286 ]]
            --[[ Upvalues: (copy 1): v_u_22 ]]
            for _, v81 in v_u_22:key_itr() do
                v81:update_note_display_mode()
            end;
        end;
        v_u_19.on_switch_focus_slot = function(p82) --[[ Name: on_switch_focus_slot ]] --[[ Line: 292 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): p_u_16 ]]
            v_u_21:on_switch_focus_slot()
            p82:tracksystem_update_note_display_mode()
            p82:tracksystem_update_all_active_notes_display_mode()
            p_u_16:es_gamelocal_get_audiomanager():recalculate_note_timing()
        end;
        v_u_19.on_switch_unfocus_slot = function(p83) --[[ Name: on_switch_unfocus_slot ]] --[[ Line: 300 ]]
            p83:tracksystem_update_note_display_mode()
            p83:tracksystem_update_all_active_notes_display_mode()
        end;
        f_cons()
        return v_u_19;
    end
};
