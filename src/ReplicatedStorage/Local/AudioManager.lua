-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:24 PM
-- Time elapsed: 15 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Local.SFXManager)
local v_u_3 = require(game.ReplicatedStorage.Local.Note)
local v_u_4 = require(game.ReplicatedStorage.Local.HeldNote)
require(game.ReplicatedStorage.Shared.NoteResult)
require(game.ReplicatedStorage.Shared.RandomLua)
local v_u_5 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_6 = require(game.ReplicatedStorage.Shared.Constants)
local v_u_7 = require(game.ReplicatedStorage.Local.HitSFXGroup)
local v_u_8 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_10 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_11 = require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.EventString)
local v_u_12 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_13 = require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_14 = require(game.ReplicatedStorage.SPChat.Shared.SPChatMessage)
local v_u_15 = require(game.ReplicatedStorage.EditorGame.Data.EditorDifficultyCalculation)
local v_u_16 = {
    ["Mode"] = {
        ["NotLoaded"] = 0,
        ["Loading"] = 1,
        ["PreStart"] = 3,
        ["Playing"] = 4,
        ["Paused"] = 5,
        ["PostPlaying"] = 6,
        ["Finished"] = 7
    }
}
local v_u_17 = 0
v_u_16.new = function(_, p_u_18) --[[ Name: new ]] --[[ Line: 37 ]]
    --[[ Upvalues: (copy 1): v_u_6, (copy 2): v_u_9, (copy 3): v_u_1, (copy 4): v_u_16, (copy 5): v_u_8, (copy 6): v_u_11, (copy 7): v_u_5, (copy 8): v_u_7, (copy 9): v_u_10, (ref 10): v_u_17, (copy 11): v_u_15, (copy 12): v_u_2, (copy 13): v_u_12, (copy 14): v_u_13, (copy 15): v_u_14, (copy 16): v_u_3, (copy 17): v_u_4 ]]
    local v_u_20 = {
        ["should_playing_game_flag_as_end"] = function(p19) --[[ Name: should_playing_game_flag_as_end ]] --[[ Line: 609 ]]
            return p19:get_current_time_ms() >= p19:get_song_length_ms();
        end
    }
    local l_NOTE_PREBUFFER_TIME_DEFAULT_0 = v_u_6.NOTE_PREBUFFER_TIME_DEFAULT
    v_u_20.get_note_prebuffer_base_time_ms = function(_) --[[ Name: get_note_prebuffer_base_time_ms ]] --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): l_NOTE_PREBUFFER_TIME_DEFAULT_0 ]]
        return l_NOTE_PREBUFFER_TIME_DEFAULT_0;
    end;
    local l_PRE_START_TIME_MS_MAX_0 = v_u_6.PRE_START_TIME_MS_MAX
    local l_POST_TIME_PLAYING_MS_MAX_0 = v_u_6.POST_TIME_PLAYING_MS_MAX
    local v_u_21 = 0
    local l_Sound_0 = Instance.new("Sound", v_u_9:get_local_elements_folder())
    l_Sound_0.Name = v_u_1:gen_name("BGM")
    local v_u_22 = 0
    local v_u_23 = 0
    v_u_20.update_bgm_to_stored_time_position = function(_) --[[ Name: update_bgm_to_stored_time_position ]] --[[ Line: 52 ]]
        --[[ Upvalues: (ref 1): l_Sound_0, (ref 2): v_u_22, (ref 3): v_u_23 ]]
        if l_Sound_0 ~= nil then
            l_Sound_0.TimePosition = v_u_22
            v_u_23 = l_Sound_0.TimePosition
        end;
    end;
    local v_u_24 = nil
    local v_u_25 = nil
    v_u_20.get_hit_sfx_group = function(_) --[[ Name: get_hit_sfx_group ]] --[[ Line: 61 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        return v_u_25;
    end;
    local l_NotLoaded_0 = v_u_16.Mode.NotLoaded
    v_u_20.get_current_mode = function(_) --[[ Name: get_current_mode ]] --[[ Line: 64 ]]
        --[[ Upvalues: (ref 1): l_NotLoaded_0 ]]
        return l_NotLoaded_0;
    end;
    v_u_20.Mode = function(_) --[[ Name: Mode ]] --[[ Line: 65 ]]
        --[[ Upvalues: (ref 1): v_u_16 ]]
        return v_u_16.Mode;
    end;
    v_u_20.get_bgm = function(_) --[[ Name: get_bgm ]] --[[ Line: 66 ]]
        --[[ Upvalues: (ref 1): l_Sound_0 ]]
        return l_Sound_0;
    end;
    local v_u_26 = 0
    v_u_20.get_pre_start_time_ms = function(_) --[[ Name: get_pre_start_time_ms ]] --[[ Line: 69 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26;
    end;
    local v_u_27 = 0
    local v_u_28 = 0.5
    local v_u_29 = false
    v_u_20.did_early_quit = function(_) --[[ Name: did_early_quit ]] --[[ Line: 74 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29;
    end;
    local v_u_30 = v_u_8:invalid_songkey()
    v_u_20.get_song_key = function(_) --[[ Name: get_song_key ]] --[[ Line: 77 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        return v_u_30;
    end;
    local v_u_31 = 0
    v_u_20.notify_held_note_begin = function(_, p32) --[[ Name: notify_held_note_begin ]] --[[ Line: 80 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        v_u_31 = p32
    end;
    local v_u_33 = 1
    local function _() --[[ Name: set_playback_speed_playing ]] --[[ Line: 85 ]]
        --[[ Upvalues: (ref 1): l_Sound_0, (ref 2): v_u_33 ]]
        if l_Sound_0 then
            l_Sound_0.PlaybackSpeed = v_u_33
        end;
    end;
    local function _() --[[ Name: set_playback_speed_paused ]] --[[ Line: 90 ]]
        --[[ Upvalues: (ref 1): l_Sound_0 ]]
        if l_Sound_0 then
            l_Sound_0.PlaybackSpeed = 0
        end;
    end;
    v_u_20.get_playback_speed = function(_) --[[ Name: get_playback_speed ]] --[[ Line: 95 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        return v_u_33;
    end;
    v_u_20.set_playback_speed = function(p34, p35) --[[ Name: set_playback_speed ]] --[[ Line: 96 ]]
        --[[ Upvalues: (ref 1): v_u_33, (ref 2): l_Sound_0 ]]
        v_u_33 = p35
        if l_Sound_0 then
            l_Sound_0.PlaybackSpeed = v_u_33
        end;
        p34:recalculate_note_timing()
    end;
    v_u_20.recalculate_note_timing = function(_) --[[ Name: recalculate_note_timing ]] --[[ Line: 104 ]]
        --[[ Upvalues: (ref 1): v_u_21, (ref 2): v_u_8, (ref 3): v_u_30, (copy 4): p_u_18, (ref 5): v_u_11, (ref 6): l_NOTE_PREBUFFER_TIME_DEFAULT_0, (ref 7): v_u_6, (ref 8): v_u_33, (ref 9): v_u_1, (ref 10): v_u_5 ]]
        v_u_21 = v_u_8:singleton():get_audio_time_offset_for_key(v_u_30) - p_u_18._player_settings_manager:get_key(v_u_11.Key.NoteOffset)
        if p_u_18._player_settings_manager:get_key(v_u_11.Key.FixedNoteSpeed) == true and not p_u_18:is_spectate() then
            l_NOTE_PREBUFFER_TIME_DEFAULT_0 = v_u_6.NOTE_PREBUFFER_TIME_DEFAULT
        else
            l_NOTE_PREBUFFER_TIME_DEFAULT_0 = v_u_8:singleton():songkey_get_prebuffer_time(v_u_30)
        end;
        if p_u_18:show_fullscreen_mobile_ui() then
            l_NOTE_PREBUFFER_TIME_DEFAULT_0 = l_NOTE_PREBUFFER_TIME_DEFAULT_0 * 0.8
        end;
        if v_u_33 ~= 1 then
            l_NOTE_PREBUFFER_TIME_DEFAULT_0 = l_NOTE_PREBUFFER_TIME_DEFAULT_0 * v_u_33
        end;
        if v_u_1:is_debug_user() then
            local v36 = p_u_18:es_gamelocal_get_local_tracksystem()
            v_u_5:puts("AudioManager:recalculate_note_timing _audio_time_offset_ms(%d) _note_prebuffer_base_time(%.2f) local_tracksystem_note_prebuffer_time_ms(%.2f)", v_u_21, l_NOTE_PREBUFFER_TIME_DEFAULT_0, not v36 and 0 or v36:get_note_prebuffer_time_ms())
        end;
    end;
    local function f_load_song_key_shared() --[[ Name: load_song_key_shared ]] --[[ Line: 135 ]]
        --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_30, (ref 3): v_u_25, (ref 4): v_u_7, (copy 5): p_u_18, (copy 6): v_u_20, (ref 7): l_Sound_0, (ref 8): v_u_22, (ref 9): v_u_28, (ref 10): v_u_10, (ref 11): v_u_17, (ref 12): v_u_1, (ref 13): v_u_5 ]]
        v_u_25 = v_u_7:new(p_u_18, (v_u_8:singleton():get_audio_hitsfxgroup_for_key(v_u_30)))
        v_u_25:preload()
        v_u_20:recalculate_note_timing()
        l_Sound_0.SoundId = v_u_8:singleton():get_audio_assetid_for_key(v_u_30)
        l_Sound_0.Volume = 0
        if l_Sound_0 then
            l_Sound_0.PlaybackSpeed = 0
        end;
        l_Sound_0.Playing = true
        v_u_22 = 0
        v_u_28 = v_u_8:singleton():get_audio_volume_for_key(v_u_30)
        if v_u_10.GameLoad_DebugExtraAudioLoadTime == true then
            v_u_17 = v_u_1:rand_rangef(3, 30)
            v_u_5:warnf("GameLoad_DebugExtraAudioLoadTime(%.2f)", v_u_17)
            spawn(function() --[[ Line: 154 ]]
                --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_5 ]]
                while v_u_17 > 0 do
                    v_u_17 = v_u_17 - 0.1
                    wait(0.1)
                end;
                v_u_5:warnf("GameLoad_DebugExtraAudioLoadTime finished")
            end)
        end;
    end;
    local function _(p37) --[[ Name: calculate_audio_data_difficulty ]] --[[ Line: 164 ]]
        --[[ Upvalues: (ref 1): v_u_15 ]]
        return v_u_15:bucket_hits_calculate_difficulty((v_u_15:map_data_calculate_hit_buckets(p37)));
    end;
    v_u_20.load_song = function(_, p_u_38) --[[ Name: load_song ]] --[[ Line: 170 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): l_NotLoaded_0, (ref 3): v_u_16, (ref 4): v_u_8, (ref 5): v_u_5, (ref 6): v_u_24, (ref 7): v_u_1, (ref 8): v_u_15, (copy 9): f_load_song_key_shared ]]
        v_u_30 = p_u_38
        l_NotLoaded_0 = v_u_16.Mode.Loading
        v_u_8:singleton():get_data_for_key(v_u_30, function(p39) --[[ Line: 173 ]]
            --[[ Upvalues: (ref 1): v_u_5, (copy 2): p_u_38, (ref 3): v_u_24, (ref 4): v_u_1, (ref 5): v_u_15, (ref 6): v_u_30, (ref 7): v_u_8 ]]
            if p39 == nil or p39.Loaded ~= true then
                return v_u_5:warnf("AudioManager:load_song(%d) is not loaded", p_u_38);
            end;
            v_u_24 = p39
            if v_u_1:is_dev_build() then
                v_u_5:warnf(">>DEBUG<< AudioManager:load_song(%d)[%s] SongDBDifficulty(%d) EditorDifficultyCalculation(%d)", v_u_30, v_u_8:singleton():key_to_name(v_u_30), v_u_8:singleton():get_difficulty_for_key(v_u_30), (v_u_15:bucket_hits_calculate_difficulty((v_u_15:map_data_calculate_hit_buckets(v_u_24)))))
            end;
        end)
        f_load_song_key_shared()
    end;
    v_u_20.load_song_key_with_custom_data = function(_, p40, p41) --[[ Name: load_song_key_with_custom_data ]] --[[ Line: 191 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): v_u_24, (ref 3): l_NotLoaded_0, (ref 4): v_u_16, (copy 5): f_load_song_key_shared, (copy 6): p_u_18, (ref 7): v_u_11, (ref 8): v_u_15, (ref 9): l_NOTE_PREBUFFER_TIME_DEFAULT_0, (ref 10): v_u_1, (ref 11): v_u_2, (ref 12): v_u_5 ]]
        v_u_30 = p40
        v_u_24 = p41:to_songdatabase_note_data()
        l_NotLoaded_0 = v_u_16.Mode.PreStart
        f_load_song_key_shared()
        if p_u_18._player_settings_manager:get_key(v_u_11.Key.FixedNoteSpeed) ~= true then
            local v42 = v_u_15:bucket_hits_calculate_difficulty((v_u_15:map_data_calculate_hit_buckets(v_u_24)))
            l_NOTE_PREBUFFER_TIME_DEFAULT_0 = v_u_1:round_to_nearest(v_u_1:clamp(v_u_2:YForPointOf2PtLineP1P2X(10, 1500, 30, 1000, v42), 1000, 1500), 25)
            if v_u_1:is_debug_user() then
                v_u_5:puts("AudioManager:load_song_key_with_custom_data(%d) _note_prebuffer_base_time(%d) calc_difficulty(%d)", v_u_30, l_NOTE_PREBUFFER_TIME_DEFAULT_0, v42)
            end;
            if p_u_18:show_fullscreen_mobile_ui() then
                l_NOTE_PREBUFFER_TIME_DEFAULT_0 = l_NOTE_PREBUFFER_TIME_DEFAULT_0 * 0.8
            end;
        end;
    end;
    local v_u_43 = 0
    v_u_20.load_retry = function(_) --[[ Name: load_retry ]] --[[ Line: 219 ]]
        --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_5, (ref 3): l_Sound_0, (ref 4): v_u_9, (ref 5): v_u_1, (ref 6): v_u_8, (ref 7): v_u_30, (ref 8): l_NotLoaded_0, (ref 9): v_u_16 ]]
        v_u_43 = v_u_43 + 1
        v_u_5:puts("AudioManager:load_retry(%d)", v_u_43)
        if l_Sound_0.IsLoaded ~= true then
            l_Sound_0:Destroy()
            l_Sound_0 = Instance.new("Sound", v_u_9:get_local_elements_folder())
            l_Sound_0.Name = v_u_1:gen_name("BGM")
            l_Sound_0.SoundId = v_u_8:singleton():get_audio_assetid_for_key(v_u_30)
            l_Sound_0.Volume = 0
            if l_Sound_0 then
                l_Sound_0.PlaybackSpeed = 0
            end;
            if l_NotLoaded_0 ~= v_u_16.Mode.Paused then
                l_Sound_0.Playing = true
            end;
        end;
    end;
    v_u_20.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 236 ]]
        --[[ Upvalues: (ref 1): l_Sound_0, (ref 2): v_u_24 ]]
        l_Sound_0:Destroy()
        l_Sound_0 = nil
        v_u_24 = nil
    end;
    v_u_20.is_ready_to_play = function(_) --[[ Name: is_ready_to_play ]] --[[ Line: 242 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): l_Sound_0, (ref 3): v_u_10, (ref 4): v_u_17 ]]
        local v44
        if v_u_24 == nil then
            v44 = false
        else
            v44 = l_Sound_0.IsLoaded == true
        end;
        if v_u_10.GameLoad_DebugExtraAudioLoadTime == true then
            if v44 then
                v44 = v_u_17 <= 0
            end;
        end;
        return v44;
    end;
    v_u_20.is_prestart = function(_) --[[ Name: is_prestart ]] --[[ Line: 250 ]]
        --[[ Upvalues: (ref 1): l_NotLoaded_0, (ref 2): v_u_16 ]]
        return l_NotLoaded_0 == v_u_16.Mode.PreStart;
    end;
    v_u_20.is_playing = function(_) --[[ Name: is_playing ]] --[[ Line: 251 ]]
        --[[ Upvalues: (ref 1): l_NotLoaded_0, (ref 2): v_u_16 ]]
        return l_NotLoaded_0 == v_u_16.Mode.Playing;
    end;
    v_u_20.is_finished = function(_) --[[ Name: is_finished ]] --[[ Line: 252 ]]
        --[[ Upvalues: (ref 1): l_NotLoaded_0, (ref 2): v_u_16 ]]
        return l_NotLoaded_0 == v_u_16.Mode.Finished;
    end;
    v_u_20.start_play = function(p_u_45) --[[ Name: start_play ]] --[[ Line: 254 ]]
        --[[ Upvalues: (ref 1): l_NotLoaded_0, (ref 2): v_u_16, (ref 3): v_u_26, (ref 4): v_u_24, (ref 5): v_u_8, (ref 6): v_u_30, (copy 7): p_u_18, (ref 8): v_u_12, (ref 9): v_u_22 ]]
        l_NotLoaded_0 = v_u_16.Mode.PreStart
        v_u_26 = 0
        if v_u_24 == nil and v_u_8:singleton():is_key_data_loaded(v_u_30) ~= true then
            local v_u_46 = nil
            v_u_46 = p_u_18._menus:push_menu(v_u_12:new(p_u_18:get_local_services(), p_u_18._spui, p_u_18._menus):set_text("Loading...", "Please wait..."):set_update_fn(function(_) --[[ Line: 266 ]]
                --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_30, (ref 3): v_u_24, (ref 4): l_NotLoaded_0, (ref 5): v_u_16, (copy 6): p_u_45, (ref 7): v_u_22, (ref 8): p_u_18, (ref 9): v_u_46 ]]
                if v_u_8:singleton():is_key_data_loaded(v_u_30) == true and v_u_24 ~= nil then
                    if l_NotLoaded_0 == v_u_16.Mode.PreStart or l_NotLoaded_0 == v_u_16.Mode.Playing then
                        p_u_45:set_skip_to_time_ms(v_u_22 * 1000)
                    end;
                    return p_u_18._menus:remove_menu(v_u_46);
                end;
                local v47, v48 = v_u_8:singleton():get_loading_retry_count_and_wait_time()
                v_u_46:set_text("Loading...", string.format("Loading map data...\nRetries(%d) Time(%.2f)", v47, v48))
            end))
        end;
    end;
    local v_u_49 = false
    local v_u_50 = 0
    local v_u_51 = 0
    v_u_20.raise_pre_start_trigger = function(_) --[[ Name: raise_pre_start_trigger ]] --[[ Line: 288 ]]
        --[[ Upvalues: (ref 1): v_u_49, (ref 2): v_u_50, (ref 3): v_u_51 ]]
        local v52 = v_u_49
        v_u_49 = false
        return v52, v_u_50, v_u_51;
    end;
    local v_u_53 = false
    local v_u_54 = 5
    local v_u_55 = 0
    v_u_20.raise_resync_update_mode = function(_) --[[ Name: raise_resync_update_mode ]] --[[ Line: 301 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): l_Sound_0, (ref 3): v_u_54 ]]
        v_u_22 = l_Sound_0.TimePosition
        v_u_54 = 0
    end;
    v_u_20.update = function(p56, p57, _) --[[ Name: update ]] --[[ Line: 308 ]]
        --[[ Upvalues: (ref 1): l_NotLoaded_0, (ref 2): v_u_16, (ref 3): v_u_26, (ref 4): v_u_2, (copy 5): l_PRE_START_TIME_MS_MAX_0, (ref 6): v_u_49, (ref 7): v_u_50, (ref 8): v_u_51, (ref 9): l_Sound_0, (ref 10): v_u_23, (ref 11): v_u_28, (ref 12): v_u_33, (ref 13): v_u_22, (copy 14): p_u_18, (ref 15): v_u_1, (ref 16): v_u_5, (ref 17): v_u_54, (ref 18): v_u_55, (ref 19): v_u_13, (ref 20): v_u_14, (ref 21): v_u_27, (copy 22): l_POST_TIME_PLAYING_MS_MAX_0, (ref 23): v_u_53 ]]
        if l_NotLoaded_0 == v_u_16.Mode.PreStart then
            local v58 = v_u_26
            local v59 = v_u_26 + v_u_2:TimescaleToDeltaTime(p57) * 1000
            v_u_26 = v59
            local v60 = l_PRE_START_TIME_MS_MAX_0 * 0.2
            local v61 = l_PRE_START_TIME_MS_MAX_0 * 0.4
            local v62 = l_PRE_START_TIME_MS_MAX_0 * 0.6
            local v63 = l_PRE_START_TIME_MS_MAX_0 * 0.8
            if v58 < v60 and v60 < v59 then
                v_u_49 = true
                v_u_50 = 1
                v_u_51 = v61 - v60
            elseif v58 < v61 and v61 < v59 then
                v_u_49 = true
                v_u_50 = 2
                v_u_51 = v62 - v61
            elseif v58 < v62 and v62 < v59 then
                v_u_49 = true
                v_u_50 = 3
                v_u_51 = v63 - v62
            elseif v58 < v63 and v63 < v59 then
                v_u_49 = true
                v_u_50 = 4
                v_u_51 = l_PRE_START_TIME_MS_MAX_0 - v63
            end;
            if l_PRE_START_TIME_MS_MAX_0 <= v_u_26 then
                v_u_26 = l_PRE_START_TIME_MS_MAX_0
                l_Sound_0.TimePosition = 0
                v_u_23 = l_Sound_0.TimePosition
                l_Sound_0.Volume = v_u_28
                if l_Sound_0 then
                    l_Sound_0.PlaybackSpeed = v_u_33
                end;
                v_u_22 = 0
                l_NotLoaded_0 = v_u_16.Mode.Playing
            end;
            p56:update_spawn_notes(p57, p_u_18)
            return;
        elseif l_NotLoaded_0 == v_u_16.Mode.Playing then
            local l_TimePosition_0 = l_Sound_0.TimePosition
            local l_IsLoaded_0 = l_Sound_0.IsLoaded
            if l_IsLoaded_0 then
                l_IsLoaded_0 = l_Sound_0.Playing
            end;
            local v64 = l_TimePosition_0 - v_u_23
            local v65 = v_u_2:TimescaleToDeltaTime(p57) * v_u_33
            if p56:should_playing_game_flag_as_end() then
                l_NotLoaded_0 = v_u_16.Mode.PostPlaying
                if v_u_1:is_debug_user() then
                    v_u_5:puts("[DEV] AudioManager:should_playing_game_flag_as_end() flag@1 get_current_time_ms(%.3f) song_length_ms(%.3f)", p56:get_current_time_ms(), p56:get_song_length_ms())
                end;
            else
                if v_u_54 < 1 then
                    v65 = v64
                end;
                if l_IsLoaded_0 ~= true or (v64 > 0 or l_TimePosition_0 > 0) then
                    v_u_22 = v_u_22 + v65
                    if p56:should_playing_game_flag_as_end() then
                        l_NotLoaded_0 = v_u_16.Mode.PostPlaying
                        if v_u_1:is_debug_user() then
                            v_u_5:puts("[DEV] AudioManager:should_playing_game_flag_as_end() flag@2 get_current_time_ms(%.3f) song_length_ms(%.3f)", p56:get_current_time_ms(), p56:get_song_length_ms())
                        end;
                        return;
                    end;
                    p56:update_spawn_notes(p57, p_u_18)
                    if l_Sound_0.IsLoaded == false then
                        v_u_55 = v_u_55 + v_u_2:TimescaleToDeltaTime(p57)
                        if v_u_55 > 10 then
                            v_u_55 = 0
                            p56:load_retry()
                            p56:update_bgm_to_stored_time_position()
                            l_Sound_0.Volume = v_u_28
                            l_TimePosition_0 = l_Sound_0.TimePosition
                            if l_Sound_0 then
                                l_Sound_0.PlaybackSpeed = v_u_33
                            end;
                        end;
                    end;
                    v_u_54 = v_u_54 + v_u_2:TimescaleToDeltaTime(p57)
                    local v66 = math.abs(v_u_22 - l_TimePosition_0)
                    if l_IsLoaded_0 and (v66 > 0.15 and v_u_54 > 5) then
                        v_u_5:puts("AudioManager: Force Sync BGM src(%.3f)->bgm(%.3f) [Diff: %.3f]", l_Sound_0.TimePosition, v_u_22, v66)
                        if v66 < 0.5 then
                            v_u_22 = l_TimePosition_0
                        else
                            p56:update_bgm_to_stored_time_position()
                        end;
                        v_u_54 = 0
                        l_TimePosition_0 = l_Sound_0.TimePosition
                    end;
                end;
                if p_u_18._input:control_pressed(v_u_13.KEY_DEBUG_1) then
                    local v67 = string.format("_bgm.TimePosition(%.3f)[Delta: %.3f] _bgm_time_position(%.3f)[Delta: %.3f] Diff[%.3f]", l_Sound_0.TimePosition, v64, v_u_22, v65, (math.abs(l_TimePosition_0 - v_u_22)))
                    p_u_18._chat:get_system_channel():add_message_to_channel(v_u_14:new(v67))
                    print(v67)
                end;
                v_u_23 = l_TimePosition_0
            end;
        else
            if l_NotLoaded_0 == v_u_16.Mode.PostPlaying then
                v_u_27 = v_u_27 + v_u_2:TimescaleToDeltaTime(p57) * 1000
                if l_POST_TIME_PLAYING_MS_MAX_0 < v_u_27 then
                    l_NotLoaded_0 = v_u_16.Mode.Finished
                    v_u_53 = true
                end;
            end;
            return;
        end;
    end;
    v_u_20.get_just_finished = function(_) --[[ Name: get_just_finished ]] --[[ Line: 471 ]]
        --[[ Upvalues: (ref 1): v_u_53 ]]
        local v68 = v_u_53
        v_u_53 = false
        return v68;
    end;
    local v_u_69 = false
    v_u_20.update_spawn_notes = function(p70, p71, _) --[[ Name: update_spawn_notes ]] --[[ Line: 478 ]]
        --[[ Upvalues: (ref 1): v_u_24, (copy 2): p_u_18, (copy 3): l_PRE_START_TIME_MS_MAX_0, (ref 4): v_u_69, (ref 5): v_u_3, (ref 6): v_u_4 ]]
        if v_u_24 == nil then
            return;
        end;
        p70:update_beat(p71, p_u_18)
        local v72 = v_u_69 and 0 or l_PRE_START_TIME_MS_MAX_0
        local v73 = p70:get_current_time_ms()
        for v74, v75 in p_u_18:es_gamelocal_get_tracksystems():key_itr() do
            local v76 = v75:get_note_prebuffer_time_ms()
            local v77 = v73 + v76 - v72
            for v78 = v75:get_audio_data_index(), #v_u_24.HitObjects do
                local l_HitObjects_0 = v_u_24.HitObjects[v78]
                if l_HitObjects_0.Time > v77 then
                    break;
                end;
                local v79 = l_HitObjects_0.Time + v72
                local l_Track_0 = l_HitObjects_0.Track
                if l_Track_0 == nil then
                    l_Track_0 = v75:gen_rand_note(v78, v79)
                end;
                if ((not p_u_18:show_fullscreen_mobile_ui() or v74 == p_u_18:get_local_game_slot()) and true or false) == true then
                    if l_HitObjects_0.Type == 1 then
                        v75:push_back_note(v_u_3:new(p_u_18, l_Track_0, v75:get_game_slot(), v73, v79, v78))
                    elseif l_HitObjects_0.Type == 2 then
                        v75:push_back_note(v_u_4:new(p_u_18, l_Track_0, v75:get_game_slot(), v73, v79, l_HitObjects_0.Duration, v76, v78))
                    end;
                end;
                v75:set_audio_data_index(v75:get_audio_data_index() + 1)
            end;
        end;
    end;
    local v_u_80 = 1
    v_u_20.get_beat_duration = function(p81) --[[ Name: get_beat_duration ]] --[[ Line: 543 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_1, (ref 3): v_u_80 ]]
        if v_u_24 == nil then
            return v_u_1:input_max_number();
        end;
        local l_BeatLength_0 = v_u_24.TimingPoints[1].BeatLength
        local v82 = p81:get_song_time_position_ms()
        for v83 = v_u_80, #v_u_24.TimingPoints do
            local l_TimingPoints_0 = v_u_24.TimingPoints[v83]
            if l_TimingPoints_0.Time > v82 then
                break;
            end;
            l_BeatLength_0 = l_TimingPoints_0.BeatLength
            v_u_80 = v83
        end;
        return l_BeatLength_0;
    end;
    local v_u_84 = false
    local v_u_85 = 0
    v_u_20.update_beat = function(p86, _, _) --[[ Name: update_beat ]] --[[ Line: 562 ]]
        --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_85, (ref 3): v_u_84 ]]
        local v87 = p86:get_beat_duration()
        local v88 = p86:get_song_time_position_ms()
        if math.floor((v88 - v_u_31) / v87) > math.floor((v_u_85 - v_u_31) / v87) then
            v_u_84 = true
        else
            v_u_84 = false
        end;
        v_u_85 = v88
    end;
    v_u_20.is_beat = function(_) --[[ Name: is_beat ]] --[[ Line: 577 ]]
        --[[ Upvalues: (ref 1): v_u_84 ]]
        return v_u_84;
    end;
    v_u_20.get_current_time_ms = function(p89) --[[ Name: get_current_time_ms ]] --[[ Line: 581 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return p89:get_song_time_position_ms() + v_u_26;
    end;
    v_u_20.get_song_time_position_ms = function(_) --[[ Name: get_song_time_position_ms ]] --[[ Line: 587 ]]
        --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_21 ]]
        return v_u_22 * 1000 + v_u_21;
    end;
    v_u_20.get_audio_time_offset_ms = function(_) --[[ Name: get_audio_time_offset_ms ]] --[[ Line: 592 ]]
        --[[ Upvalues: (ref 1): v_u_21 ]]
        return v_u_21;
    end;
    v_u_20.get_song_key_audio_length_ms = function(_) --[[ Name: get_song_key_audio_length_ms ]] --[[ Line: 594 ]]
        --[[ Upvalues: (ref 1): l_Sound_0, (ref 2): v_u_8, (ref 3): v_u_30 ]]
        local v90
        if l_Sound_0.IsLoaded == true then
            v90 = l_Sound_0.TimeLength
        else
            v90 = v_u_8:singleton():songkey_get_approx_length_sec(v_u_30)
        end;
        return v90 * 1000;
    end;
    v_u_20.get_song_length_ms = function(p91) --[[ Name: get_song_length_ms ]] --[[ Line: 605 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return p91:get_song_key_audio_length_ms() + v_u_26;
    end;
    v_u_20.notify_local_early_quit = function(_) --[[ Name: notify_local_early_quit ]] --[[ Line: 613 ]]
        --[[ Upvalues: (ref 1): l_Sound_0, (ref 2): l_NotLoaded_0, (ref 3): v_u_16, (ref 4): v_u_29 ]]
        l_Sound_0:Stop()
        l_NotLoaded_0 = v_u_16.Mode.Finished
        v_u_29 = true
    end;
    v_u_20.set_paused = function(_, p92) --[[ Name: set_paused ]] --[[ Line: 619 ]]
        --[[ Upvalues: (ref 1): l_NotLoaded_0, (ref 2): v_u_16, (ref 3): l_Sound_0, (ref 4): v_u_33 ]]
        if p92 == true then
            l_NotLoaded_0 = v_u_16.Mode.Paused
            if l_Sound_0 then
                l_Sound_0.PlaybackSpeed = 0
                return;
            end;
        else
            l_NotLoaded_0 = v_u_16.Mode.Playing
            if l_Sound_0 then
                l_Sound_0.PlaybackSpeed = v_u_33
            end;
        end;
    end;
    v_u_20.set_skip_to_time_ms = function(p_u_93, p_u_94) --[[ Name: set_skip_to_time_ms ]] --[[ Line: 632 ]]
        --[[ Upvalues: (ref 1): l_Sound_0, (ref 2): v_u_5, (ref 3): l_NotLoaded_0, (ref 4): v_u_16, (ref 5): v_u_22, (copy 6): p_u_18, (ref 7): v_u_24, (ref 8): v_u_69, (ref 9): v_u_28, (ref 10): v_u_33 ]]
        local function f_perform() --[[ Name: perform ]] --[[ Line: 633 ]]
            --[[ Upvalues: (ref 1): l_Sound_0, (ref 2): v_u_5, (ref 3): l_NotLoaded_0, (ref 4): v_u_16, (ref 5): v_u_22, (copy 6): p_u_94, (ref 7): p_u_18, (copy 8): p_u_93, (ref 9): v_u_24, (ref 10): v_u_69, (ref 11): v_u_28, (ref 12): v_u_33 ]]
            if l_Sound_0 == nil then
                return v_u_5:warnf("AudioManager:set_skip_to_time_ms _bgm is nil");
            end;
            l_NotLoaded_0 = v_u_16.Mode.Playing
            v_u_22 = p_u_94 / 1000
            for _, v95 in p_u_18:es_gamelocal_get_tracksystems():key_itr() do
                v95:set_audio_data_index(1)
                local v96 = p_u_93:get_song_time_position_ms() + v95:get_note_prebuffer_time_ms()
                for v97 = v95:get_audio_data_index(), #v_u_24.HitObjects do
                    if v_u_24.HitObjects[v97].Time > v96 then
                        break;
                    end;
                    v95:set_audio_data_index(v95:get_audio_data_index() + 1)
                end;
            end;
            v_u_69 = true
            l_Sound_0.Volume = v_u_28
            if l_Sound_0 then
                l_Sound_0.PlaybackSpeed = v_u_33
            end;
            p_u_93:update_bgm_to_stored_time_position()
            l_Sound_0.Playing = true
            p_u_93:raise_resync_update_mode()
        end;
        if v_u_24 then
            return f_perform();
        end;
        spawn(function() --[[ Line: 663 ]]
            --[[ Upvalues: (ref 1): v_u_24, (copy 2): f_perform, (ref 3): v_u_5 ]]
            local v98 = 0
            while v98 < 10 do
                if v_u_24 then
                    return f_perform();
                end;
                v98 = v98 + 1
                wait(0.25)
            end;
            v_u_5:warnf("AudioManager:set_skip_to_time_ms _current_audio_data is nil (timed out)")
        end)
    end;
    return v_u_20;
end;
return v_u_16;
