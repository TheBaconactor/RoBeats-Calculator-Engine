-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:12 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_3 = require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.NoteSkinColor)
require(game.ReplicatedStorage.Shared.NoteDisplayMode)
require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_4 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
require(game.ReplicatedStorage.Shared.Note2DSettings)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPList)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
local v_u_8 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPRange)
local v_u_10 = require(game.ReplicatedStorage.Local.HeldNoteState)
local v11 = require(game.ReplicatedStorage.Avatar.GearStats)
local v_u_12 = require(game.ReplicatedStorage.Shared.NoteResult)
local v13 = require(game.ReplicatedStorage.Shared.NoteHitMode)
local v_u_14 = require(game.ReplicatedStorage.Effects.EffectSystem)
local v_u_15 = require(game.ReplicatedStorage.Avatar.ElementalColor)
local v_u_16 = require(game.ReplicatedStorage.Local.HitSFXGroup)
local v_u_17 = require(game.ReplicatedStorage.Shared.SPVector)
require(game.ReplicatedStorage.Shared.SPRect)
local v_u_18 = require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_19 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_20 = require(game.ReplicatedStorage.Shared.AssertType)
local v21 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_22 = nil
local v_u_23 = nil
local v_u_24 = nil
local v_u_25 = nil
local v_u_26 = nil
local v_u_27 = nil
v21:require_client(function() --[[ Line: 38 ]]
    --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_23, (ref 3): v_u_24, (ref 4): v_u_25, (ref 5): v_u_26, (ref 6): v_u_27 ]]
    v_u_22 = require(game.ReplicatedStorage.EditorGame.UI.Element.EditorGameDisplayUtil)
    v_u_23 = require(game.ReplicatedStorage.EditorGame.UI.Element.EditorNoteTrackDisplay_Track)
    v_u_24 = require(game.ReplicatedStorage.EditorGame.UI.Element.EditorNoteTrackDisplay_NoteSingle)
    v_u_25 = require(game.ReplicatedStorage.EditorGame.UI.Element.EditorNoteTrackDisplay_NoteHeld)
    v_u_26 = require(game.ReplicatedStorage.EditorGame.UI.Element.EditorNoteResultPopupEffectDecal)
    v_u_27 = require(game.ReplicatedStorage.EditorGame.UI.Element.EditorNoteTrackDisplay_TimeBarRender)
end)
local v36 = {
    ["Mode"] = {
        ["Select"] = 0,
        ["Add"] = 1,
        ["Delete"] = 2,
        ["Paste"] = 3
    },
    ["Select_SubModes"] = {
        ["One"] = 1,
        ["Multiple"] = 2
    },
    ["Add_SubModes"] = {
        ["Single"] = 1,
        ["Hold"] = 2
    },
    ["copy_editor_note_track_display_data_to_custom_map"] = function(_, p28, p29) --[[ Name: copy_editor_note_track_display_data_to_custom_map ]] --[[ Line: 1401 ]]
        --[[ Upvalues: (copy 1): v_u_7 ]]
        local v30 = p29:get_notes()
        v30:clear()
        local v31 = p28:get_loaded_note_data()
        for v32 = 1, v31:count() do
            v30:push_back((v_u_7.Note:from_table(v31:get(v32):to_table())))
        end;
        local v33 = p29:get_timing_points()
        v33:clear()
        local v34 = p28:get_time_bar_render():get_timing_points()
        for v35 = 1, v34:count() do
            v33:push_back((v_u_7.TimingPoint:from_table(v34:get(v35):to_table())))
        end;
    end
}
local v_u_37 = v11:get_note_time_obj(v11:statsdict_base())
local v_u_38 = v11:get_note_time_obj(v11:statsdict_base(), v11:note_hit_mode_get_time_multiplier(v13.HeldHitTail))
local v_u_39 = {
    ["Select"] = 0,
    ["Add"] = 1,
    ["Delete"] = 2,
    ["Paste"] = 3
}
local v_u_40 = {
    ["One"] = 1,
    ["Multiple"] = 2
}
local v_u_41 = {
    ["Single"] = 1,
    ["Hold"] = 2
}
local v_u_42 = Color3.fromRGB(255, 255, 255)
local v_u_43 = Color3.fromRGB(255, 0, 0)
v36.new = function(_, p_u_44, p_u_45, p46) --[[ Name: new ]] --[[ Line: 76 ]]
    --[[ Upvalues: (copy 1): v_u_39, (copy 2): v_u_20, (copy 3): v_u_40, (copy 4): v_u_41, (copy 5): v_u_1, (ref 6): v_u_27, (copy 7): v_u_5, (copy 8): v_u_14, (copy 9): v_u_18, (copy 10): v_u_17, (ref 11): v_u_22, (copy 12): v_u_7, (ref 13): v_u_23, (ref 14): v_u_24, (copy 15): v_u_42, (ref 16): v_u_25, (copy 17): v_u_8, (copy 18): v_u_3, (copy 19): v_u_16, (copy 20): v_u_2, (copy 21): v_u_9, (ref 22): v_u_26, (copy 23): v_u_15, (copy 24): v_u_12, (copy 25): v_u_10, (copy 26): v_u_37, (copy 27): v_u_38, (copy 28): v_u_4, (copy 29): v_u_6, (copy 30): v_u_19, (copy 31): v_u_43 ]]
    local v_u_47 = {}
    local l_Select_0 = v_u_39.Select
    v_u_47.get_current_mode = function(_) --[[ Name: get_current_mode ]] --[[ Line: 84 ]]
        --[[ Upvalues: (ref 1): l_Select_0 ]]
        return l_Select_0;
    end;
    v_u_47.set_current_mode = function(_, p48) --[[ Name: set_current_mode ]] --[[ Line: 85 ]]
        --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_39, (ref 3): l_Select_0 ]]
        v_u_20:is_enum_member(p48, v_u_39)
        l_Select_0 = p48
    end;
    local l_One_0 = v_u_40.One
    local l_Single_0 = v_u_41.Single
    v_u_47.get_select_sub_mode = function(_) --[[ Name: get_select_sub_mode ]] --[[ Line: 92 ]]
        --[[ Upvalues: (ref 1): l_One_0 ]]
        return l_One_0;
    end;
    v_u_47.set_select_sub_mode = function(_, p49) --[[ Name: set_select_sub_mode ]] --[[ Line: 93 ]]
        --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_40, (ref 3): l_One_0 ]]
        v_u_20:is_enum_member(p49, v_u_40)
        l_One_0 = p49
    end;
    v_u_47.get_add_sub_mode = function(_) --[[ Name: get_add_sub_mode ]] --[[ Line: 97 ]]
        --[[ Upvalues: (ref 1): l_Single_0 ]]
        return l_Single_0;
    end;
    v_u_47.set_add_sub_mode = function(_, p50) --[[ Name: set_add_sub_mode ]] --[[ Line: 98 ]]
        --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_41, (ref 3): l_Single_0 ]]
        v_u_20:is_enum_member(p50, v_u_41)
        l_Single_0 = p50
    end;
    v_u_47.get_parent_frame = function(_) --[[ Name: get_parent_frame ]] --[[ Line: 103 ]]
        --[[ Upvalues: (copy 1): p_u_45 ]]
        return p_u_45;
    end;
    v_u_47.set_alpha = function(_, p51) --[[ Name: set_alpha ]] --[[ Line: 104 ]]
        --[[ Upvalues: (copy 1): p_u_45, (ref 2): v_u_1 ]]
        p_u_45.GroupTransparency = v_u_1:tra(p51)
    end;
    local v_u_52 = v_u_27:new(p_u_44, v_u_47)
    v_u_47.get_time_bar_render = function(_) --[[ Name: get_time_bar_render ]] --[[ Line: 107 ]]
        --[[ Upvalues: (copy 1): v_u_52 ]]
        return v_u_52;
    end;
    local v_u_53 = v_u_5:new()
    v_u_47.get_editor_display_tracks = function(_) --[[ Name: get_editor_display_tracks ]] --[[ Line: 110 ]]
        --[[ Upvalues: (copy 1): v_u_53 ]]
        return v_u_53;
    end;
    local v_u_54 = v_u_5:new()
    local v_u_55 = 0
    local v_u_56 = 1
    local v_u_57 = 1100
    local v_u_58 = 1
    local v_u_59 = false
    local v_u_60 = true
    local v_u_61 = v_u_14:new()
    v_u_47.set_display_time_ms = function(_, p62) --[[ Name: set_display_time_ms ]] --[[ Line: 122 ]]
        --[[ Upvalues: (ref 1): v_u_55 ]]
        v_u_55 = p62
    end;
    v_u_47.get_display_time_ms = function(_) --[[ Name: get_display_time_ms ]] --[[ Line: 125 ]]
        --[[ Upvalues: (ref 1): v_u_55 ]]
        return v_u_55;
    end;
    v_u_47.get_track_note_prebuffer_time_ms = function(_) --[[ Name: get_track_note_prebuffer_time_ms ]] --[[ Line: 126 ]]
        --[[ Upvalues: (ref 1): v_u_57 ]]
        return v_u_57;
    end;
    v_u_47.set_track_note_prebuffer_time_ms = function(_, p63) --[[ Name: set_track_note_prebuffer_time_ms ]] --[[ Line: 127 ]]
        --[[ Upvalues: (ref 1): v_u_57, (ref 2): v_u_1 ]]
        v_u_57 = v_u_1:clamp(p63, 100, 5000)
    end;
    v_u_47.set_playing = function(p64, p65) --[[ Name: set_playing ]] --[[ Line: 128 ]]
        --[[ Upvalues: (ref 1): v_u_60, (ref 2): v_u_59 ]]
        p64:get_selected_note_index_set():clear()
        p64:full_refresh_active_display_notes()
        if p65 == true and v_u_60 == true then
            p64:update_autoplay()
        end;
        v_u_59 = p65
        p64:update_playing_audio_state()
    end;
    v_u_47.is_playing = function(_) --[[ Name: is_playing ]] --[[ Line: 142 ]]
        --[[ Upvalues: (ref 1): v_u_59 ]]
        return v_u_59;
    end;
    v_u_47.set_autoplay_enabled = function(_, p66) --[[ Name: set_autoplay_enabled ]] --[[ Line: 143 ]]
        --[[ Upvalues: (ref 1): v_u_60 ]]
        v_u_60 = p66
    end;
    v_u_47.is_autoplay_enabled = function(_) --[[ Name: is_autoplay_enabled ]] --[[ Line: 144 ]]
        --[[ Upvalues: (ref 1): v_u_60 ]]
        return v_u_60;
    end;
    v_u_47.set_playback_speed = function(_, p67) --[[ Name: set_playback_speed ]] --[[ Line: 145 ]]
        --[[ Upvalues: (ref 1): v_u_58, (ref 2): v_u_1 ]]
        v_u_58 = v_u_1:clamp(p67, 0.1, 5)
    end;
    v_u_47.get_playback_speed = function(_) --[[ Name: get_playback_speed ]] --[[ Line: 146 ]]
        --[[ Upvalues: (ref 1): v_u_58 ]]
        return v_u_58;
    end;
    local v_u_68 = v_u_5:new()
    v_u_47.get_loaded_note_data = function(_) --[[ Name: get_loaded_note_data ]] --[[ Line: 149 ]]
        --[[ Upvalues: (copy 1): v_u_68 ]]
        return v_u_68;
    end;
    local l_Sound_0 = Instance.new("Sound")
    l_Sound_0.Name = "EditorNoteTrackDisplay._playback_sound"
    l_Sound_0.Playing = false
    l_Sound_0.TimePosition = 0
    local v_u_69 = 0
    local v_u_70 = 0
    local v_u_71 = nil
    v_u_47.get_audio_duration_ms = function(_) --[[ Name: get_audio_duration_ms ]] --[[ Line: 161 ]]
        --[[ Upvalues: (ref 1): v_u_70 ]]
        return v_u_70;
    end;
    local l_ImageLabel_0 = Instance.new("ImageLabel")
    local v_u_72 = v_u_18.CursorFramePositionCalc:new(p_u_44._spui, p46, p46:get_sgui(), p_u_45)
    local v_u_73 = false
    local v_u_74 = v_u_17:new(0, 0)
    local function _() --[[ Name: update_cursor_preview_icon_to_last_cursor_pixxy ]] --[[ Line: 172 ]]
        --[[ Upvalues: (ref 1): v_u_73, (copy 2): l_ImageLabel_0, (copy 3): v_u_74 ]]
        if v_u_73 == true then
            l_ImageLabel_0.Position = UDim2.new(0, v_u_74._x, 0, v_u_74._y)
            l_ImageLabel_0.Visible = true
        else
            l_ImageLabel_0.Visible = false
        end;
    end;
    v_u_47.is_cursor_over_display = function(_) --[[ Name: is_cursor_over_display ]] --[[ Line: 181 ]]
        --[[ Upvalues: (ref 1): v_u_73 ]]
        return v_u_73;
    end;
    local function _() --[[ Name: last_cursor_pixxy_vec2 ]] --[[ Line: 182 ]]
        --[[ Upvalues: (copy 1): v_u_74 ]]
        return v_u_74:to_vector2();
    end;
    local v_u_75 = nil
    local v_u_76 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 187 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_45, (copy 3): l_ImageLabel_0, (ref 4): v_u_22, (ref 5): v_u_73, (copy 6): v_u_74, (ref 7): v_u_7, (ref 8): v_u_23, (copy 9): p_u_44, (copy 10): v_u_47, (copy 11): v_u_53, (ref 12): v_u_75, (ref 13): v_u_24, (ref 14): v_u_42, (ref 15): v_u_76, (ref 16): v_u_25 ]]
        v_u_1:r_set_alpha_v2_flag_as_notraverse(p_u_45)
        l_ImageLabel_0.Name = "CursorPreview"
        l_ImageLabel_0.Image = v_u_22:get_cursor_preview_assetid()
        l_ImageLabel_0.AnchorPoint = Vector2.new(0.5, 0.5)
        l_ImageLabel_0.Size = UDim2.new(0, 15, 0, 15)
        l_ImageLabel_0.BackgroundTransparency = v_u_1:tra(0)
        l_ImageLabel_0.ImageTransparency = v_u_1:tra(0.25)
        l_ImageLabel_0.Parent = p_u_45
        if v_u_73 == true then
            l_ImageLabel_0.Position = UDim2.new(0, v_u_74._x, 0, v_u_74._y)
            l_ImageLabel_0.Visible = true
        else
            l_ImageLabel_0.Visible = false
        end;
        for v77 = v_u_7.Track:get_track_begin(), v_u_7.Track:get_track_end() do
            v_u_53:push_back((v_u_23:new(p_u_44, v_u_47, v77, p_u_45)))
        end;
        local v78 = v_u_7.Note:new()
        v78:set_type(v_u_7.NoteType.Single)
        v78:set_time_ms(-100000)
        v_u_75 = v_u_24:new(p_u_44, v_u_47, v78, -1, p_u_45)
        v_u_75:set_custom_alpha(0.25)
        v_u_75:set_custom_color(true, v_u_42)
        local v79 = v_u_7.Note:new()
        v79:set_type(v_u_7.NoteType.Hold)
        v79:set_time_ms(-100000)
        v79:set_duration(1000)
        v_u_76 = v_u_25:new(p_u_44, v_u_47, v79, -2, p_u_45)
        v_u_76:set_custom_alpha(0.25)
        v_u_76:set_custom_color(true, v_u_42)
    end;
    v_u_47.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 239 ]]
        --[[ Upvalues: (copy 1): v_u_52, (copy 2): v_u_54, (copy 3): v_u_61, (copy 4): p_u_44, (copy 5): l_Sound_0 ]]
        v_u_52:cleanup()
        for v80 = 1, v_u_54:count() do
            v_u_54:get(v80):cleanup()
        end;
        v_u_54:clear()
        v_u_61:teardown(p_u_44)
        l_Sound_0.Parent = nil
        l_Sound_0.SoundId = ""
    end;
    local v_u_81 = v_u_8:invalid_songkey()
    v_u_47.get_songkey = function(_) --[[ Name: get_songkey ]] --[[ Line: 252 ]]
        --[[ Upvalues: (ref 1): v_u_81 ]]
        return v_u_81;
    end;
    local v_u_82 = 0.5
    v_u_47.load_songkey_audio = function(p83, p84, p_u_85) --[[ Name: load_songkey_audio ]] --[[ Line: 255 ]]
        --[[ Upvalues: (ref 1): v_u_81, (copy 2): l_Sound_0, (ref 3): v_u_8, (ref 4): v_u_82, (ref 5): v_u_69, (copy 6): p_u_44, (ref 7): v_u_3, (ref 8): v_u_70, (ref 9): v_u_71, (ref 10): v_u_16, (ref 11): v_u_1 ]]
        v_u_81 = p84
        l_Sound_0.Playing = false
        l_Sound_0.TimePosition = 0
        l_Sound_0.Parent = game.Workspace
        l_Sound_0.SoundId = v_u_8:singleton():get_audio_assetid_for_key(v_u_81)
        v_u_82 = v_u_8:singleton():get_audio_volume_for_key(v_u_81)
        l_Sound_0.Volume = v_u_82
        l_Sound_0.Looped = true
        v_u_69 = v_u_8:singleton():get_audio_time_offset_for_key(v_u_81) - p_u_44._player_settings_manager:get_key(v_u_3.Key.NoteOffset)
        v_u_70 = v_u_8:singleton():songkey_get_approx_length_sec(v_u_81) * 1000
        p83:update_playing_audio_state()
        v_u_71 = v_u_16:new(p_u_44, 2)
        v_u_71:set_volume(0.25)
        v_u_71:preload()
        v_u_70 = v_u_8:singleton():songkey_get_approx_length_sec(v_u_81) * 1000
        if l_Sound_0.IsLoaded == true then
            v_u_70 = l_Sound_0.TimeLength * 1000
            if p_u_85 then
                p_u_85()
                return;
            end;
        else
            spawn(function() --[[ Line: 282 ]]
                --[[ Upvalues: (ref 1): l_Sound_0, (ref 2): v_u_1, (ref 3): v_u_70, (copy 4): p_u_85 ]]
                while l_Sound_0.IsLoaded == false do
                    v_u_1:wait(0.1)
                    if not l_Sound_0:IsDescendantOf(game.Workspace) then
                        return;
                    end;
                end;
                v_u_70 = l_Sound_0.TimeLength * 1000
                if p_u_85 then
                    p_u_85()
                end;
            end)
        end;
    end;
    local function _() --[[ Name: get_expected_time_position_sec ]] --[[ Line: 297 ]]
        --[[ Upvalues: (ref 1): v_u_55, (ref 2): v_u_69 ]]
        return (v_u_55 + v_u_69) / 1000;
    end;
    local v_u_86 = 0
    v_u_47.update_playing_audio_state = function(p87) --[[ Name: update_playing_audio_state ]] --[[ Line: 302 ]]
        --[[ Upvalues: (ref 1): v_u_55, (ref 2): v_u_69, (copy 3): l_Sound_0, (ref 4): v_u_86, (ref 5): v_u_59 ]]
        l_Sound_0.TimePosition = (v_u_55 + v_u_69) / 1000
        v_u_86 = l_Sound_0.TimePosition
        l_Sound_0.PlaybackSpeed = p87:get_playback_speed()
        l_Sound_0.Playing = v_u_59
    end;
    local v_u_88 = 0
    local v_u_89 = 0
    local function f_recalculate_loaded_note_data_stats() --[[ Name: recalculate_loaded_note_data_stats ]] --[[ Line: 312 ]]
        --[[ Upvalues: (ref 1): v_u_88, (ref 2): v_u_89, (copy 3): v_u_68, (ref 4): v_u_7 ]]
        v_u_88 = 0
        v_u_89 = 0
        for v90 = 1, v_u_68:count() do
            local v91 = v_u_68:get(v90)
            if v91:get_type() == v_u_7.NoteType.Single then
                v_u_88 = v_u_88 + 1
            elseif v91:get_type() == v_u_7.NoteType.Hold then
                v_u_89 = v_u_89 + 1
            end;
        end;
    end;
    v_u_47.get_loaded_note_data_stats = function(_) --[[ Name: get_loaded_note_data_stats ]] --[[ Line: 324 ]]
        --[[ Upvalues: (ref 1): v_u_88, (ref 2): v_u_89 ]]
        return v_u_88, v_u_89;
    end;
    v_u_47.load_songdatabase_note_data = function(_, p92) --[[ Name: load_songdatabase_note_data ]] --[[ Line: 326 ]]
        --[[ Upvalues: (copy 1): v_u_68, (ref 2): v_u_7, (copy 3): v_u_52, (copy 4): f_recalculate_loaded_note_data_stats ]]
        v_u_68:clear()
        for v93 = 1, #p92.HitObjects do
            v_u_68:push_back((v_u_7.Note:from_table(p92.HitObjects[v93])))
        end;
        v_u_52:load_songdatabase_note_data_timing_points(p92)
        f_recalculate_loaded_note_data_stats()
    end;
    v_u_47.get_time_ms_display_position = function(p94, p95, p96) --[[ Name: get_time_ms_display_position ]] --[[ Line: 337 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_2 ]]
        if p96 == nil then
            p96 = v_u_7.Track.Track1
        end;
        local v97, v98 = p94:get_editor_display_tracks():get(p96):get_start_end_point_for_track_system_index()
        local v99 = 1 - (p95 - p94:get_display_time_ms()) / p94:get_track_note_prebuffer_time_ms()
        return Vector2.new(v_u_2:Lerp(v97.X, v98.X, v99), v_u_2:Lerp(v97.Y, v98.Y, v99));
    end;
    v_u_47.get_pix_display_position_to_time_ms_and_track_index = function(p100, p101) --[[ Name: get_pix_display_position_to_time_ms_and_track_index ]] --[[ Line: 350 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_53, (ref 3): v_u_2 ]]
        local l_Track1_0 = v_u_7.Track.Track1
        local v102 = 0
        for v103 = 1, v_u_53:count() do
            local v104, _ = v_u_53:get(v103):get_track_size_and_position()
            v102 = v102 + v104.X
            if p101.X <= v102 then
                l_Track1_0 = v103
                break;
            end;
            l_Track1_0 = v103
        end;
        local v105 = p100:get_display_time_ms()
        local l_Y_0 = p100:get_time_ms_display_position(v105).Y
        local v106 = p100:get_display_time_ms() + p100:get_track_note_prebuffer_time_ms()
        return math.round((v_u_2:YForPointOf2PtLineP1P2X(l_Y_0, v105, p100:get_time_ms_display_position(v106).Y, v106, p101.Y))), l_Track1_0;
    end;
    local v_u_107 = v_u_9:new(0, 0)
    v_u_47.get_display_time_active_range_ms = function(_) --[[ Name: get_display_time_active_range_ms ]] --[[ Line: 374 ]]
        --[[ Upvalues: (copy 1): v_u_107, (ref 2): v_u_55, (ref 3): v_u_57 ]]
        local v108 = v_u_107
        v108:set_min_max(v_u_55 - 500, v_u_55 + v_u_57)
        return v108;
    end;
    local function f_create_next_notes_from_current_time_active_range() --[[ Name: create_next_notes_from_current_time_active_range ]] --[[ Line: 383 ]]
        --[[ Upvalues: (copy 1): v_u_47, (ref 2): v_u_56, (copy 3): v_u_68, (ref 4): v_u_7, (ref 5): v_u_24, (copy 6): p_u_44, (copy 7): p_u_45, (copy 8): v_u_54, (ref 9): v_u_25 ]]
        local v109 = v_u_47:get_display_time_active_range_ms()
        for v110 = v_u_56, v_u_68:count() do
            local v111 = v_u_68:get(v110)
            local v112 = v111:get_time_ms()
            if v109:max() < v112 then
                break;
            end;
            if v111:get_type() == v_u_7.NoteType.Single then
                if v109:contains_eq(v112) then
                    v_u_54:push_back((v_u_24:new(p_u_44, v_u_47, v111, v110, p_u_45)))
                end;
            elseif v111:get_type() == v_u_7.NoteType.Hold and v112 + v111:get_duration() >= v109:min() then
                v_u_54:push_back((v_u_25:new(p_u_44, v_u_47, v111, v110, p_u_45)))
            end;
            v_u_56 = v110 + 1
        end;
    end;
    v_u_47.full_refresh_active_display_notes = function(_) --[[ Name: full_refresh_active_display_notes ]] --[[ Line: 424 ]]
        --[[ Upvalues: (copy 1): v_u_54, (ref 2): v_u_56, (copy 3): f_create_next_notes_from_current_time_active_range, (copy 4): v_u_52 ]]
        for _, v113 in v_u_54:key_itr() do
            v113:cleanup()
        end;
        v_u_54:clear()
        v_u_56 = 1
        f_create_next_notes_from_current_time_active_range()
        v_u_52:full_refresh_active_time_bars()
    end;
    local function _(p114) --[[ Name: remove_note_at_index ]] --[[ Line: 433 ]]
        --[[ Upvalues: (copy 1): v_u_54 ]]
        v_u_54:get(p114):cleanup()
        v_u_54:remove_at(p114)
    end;
    local function f_hit_effect_on_track(_, p115, p116) --[[ Name: hit_effect_on_track ]] --[[ Line: 438 ]]
        --[[ Upvalues: (copy 1): v_u_47, (copy 2): v_u_61, (ref 3): v_u_26, (copy 4): p_u_44, (ref 5): v_u_15, (copy 6): p_u_45 ]]
        if v_u_47:is_playing() == true then
            local v117 = v_u_47:get_editor_display_tracks():get(p116)
            local _, v118 = v117:get_start_end_point_for_track_system_index()
            local v119, _ = v117:get_track_size_and_position()
            local v120 = v_u_61:add_effect(v_u_26:new(p_u_44, v118, p115, "", 0, false, -1, v_u_15.Blue, 0, v_u_15.Green, 0))
            v120:set_track_size(v119)
            v120:set_frame_parent(p_u_45)
        end;
    end;
    local function _(p121, p122) --[[ Name: miss_effect_on_track ]] --[[ Line: 461 ]]
        --[[ Upvalues: (copy 1): v_u_47, (copy 2): f_hit_effect_on_track, (ref 3): v_u_12 ]]
        if v_u_47:is_autoplay_enabled() ~= true then
            f_hit_effect_on_track(p121, v_u_12.NoteResult_Miss, p122)
        end;
    end;
    local function _() --[[ Name: play_hit_sound ]] --[[ Line: 472 ]]
        --[[ Upvalues: (copy 1): v_u_47, (ref 2): v_u_71 ]]
        if v_u_47:is_playing() == true and v_u_71 ~= nil then
            v_u_71:play_alternating()
        end;
    end;
    v_u_47.update_active_display_notes = function(p123) --[[ Name: update_active_display_notes ]] --[[ Line: 478 ]]
        --[[ Upvalues: (copy 1): v_u_54, (ref 2): v_u_7, (ref 3): v_u_10, (copy 4): v_u_47, (copy 5): f_hit_effect_on_track, (ref 6): v_u_12, (copy 7): f_create_next_notes_from_current_time_active_range, (copy 8): v_u_52 ]]
        for v124 = v_u_54:count(), 1, -1 do
            local v125 = v_u_54:get(v124)
            local v126 = v125:get_note_loaded_data()
            if v126:get_type() == v_u_7.NoteType.Hold and (p123:is_playing() == true and v125:get_held_note_state() == v_u_10.Pre) and v126:get_time_ms() < p123:get_display_time_active_range_ms():min() then
                v125:set_held_note_state(v_u_10.HoldMissedActive)
                local v127 = v126:get_track()
                if v_u_47:is_autoplay_enabled() ~= true then
                    f_hit_effect_on_track(v125, v_u_12.NoteResult_Miss, v127)
                end;
            elseif v125:update_should_remove() then
                v_u_54:get(v124):cleanup()
                v_u_54:remove_at(v124)
                local v128 = v126:get_track()
                if v_u_47:is_autoplay_enabled() ~= true then
                    f_hit_effect_on_track(v125, v_u_12.NoteResult_Miss, v128)
                end;
            else
                v125:update_position_to_parent_track_display_time()
            end;
        end;
        f_create_next_notes_from_current_time_active_range()
        v_u_52:update_active_time_bars()
    end;
    local function _(p129, p130) --[[ Name: get_time_delta_ms_and_noteresult_to_target_time ]] --[[ Line: 509 ]]
        --[[ Upvalues: (ref 1): v_u_37, (copy 2): v_u_47, (ref 3): v_u_1 ]]
        if p130 == nil then
            p130 = v_u_37
        end;
        local v131 = v_u_47:get_display_time_ms() - p129
        return v131, v_u_1:timedelta_to_result_obj(v131, p130);
    end;
    local function f_on_track_pressed(p132) --[[ Name: on_track_pressed ]] --[[ Line: 518 ]]
        --[[ Upvalues: (copy 1): v_u_53, (copy 2): v_u_54, (ref 3): v_u_7, (ref 4): v_u_37, (copy 5): v_u_47, (ref 6): v_u_1, (ref 7): v_u_12, (copy 8): f_hit_effect_on_track, (ref 9): v_u_71, (ref 10): v_u_10 ]]
        v_u_53:get(p132):track_press()
        for v133 = 1, v_u_54:count() do
            local v134 = v_u_54:get(v133)
            local v135 = v134:get_note_loaded_data()
            if v135:get_track() == p132 then
                if v135:get_type() == v_u_7.NoteType.Single then
                    local v136, v137 = v135:get_time_ms()
                    if v137 == nil then
                        v137 = v_u_37
                    end;
                    local v138 = v_u_1:timedelta_to_result_obj(v_u_47:get_display_time_ms() - v136, v137)
                    if v138 ~= v_u_12.NoteResult_Miss then
                        f_hit_effect_on_track(v134, v138, p132)
                        if v_u_47:is_playing() == true and v_u_71 ~= nil then
                            v_u_71:play_alternating()
                        end;
                        v_u_54:get(v133):cleanup()
                        v_u_54:remove_at(v133)
                        return;
                    end;
                elseif v135:get_type() == v_u_7.NoteType.Hold then
                    if v134:get_held_note_state() == v_u_10.Pre then
                        local v139, v140 = v135:get_time_ms()
                        if v140 == nil then
                            v140 = v_u_37
                        end;
                        local v141 = v_u_1:timedelta_to_result_obj(v_u_47:get_display_time_ms() - v139, v140)
                        if v141 ~= v_u_12.NoteResult_Miss then
                            f_hit_effect_on_track(v134, v141, p132)
                            if v_u_47:is_playing() == true and v_u_71 ~= nil then
                                v_u_71:play_alternating()
                            end;
                            v134:set_held_note_state(v_u_10.Holding)
                            return;
                        end;
                    elseif v134:get_held_note_state() == v_u_10.HoldMissedActive then
                        local v142 = v135:get_time_ms() + v135:get_duration()
                        local v143 = nil
                        if v143 == nil then
                            v143 = v_u_37
                        end;
                        local v144 = v_u_1:timedelta_to_result_obj(v_u_47:get_display_time_ms() - v142, v143)
                        if v144 ~= v_u_12.NoteResult_Miss then
                            f_hit_effect_on_track(v134, v144, p132)
                            if v_u_47:is_playing() == true and v_u_71 ~= nil then
                                v_u_71:play_alternating()
                            end;
                            v_u_54:get(v133):cleanup()
                            v_u_54:remove_at(v133)
                            return;
                        end;
                    end;
                end;
            end;
        end;
    end;
    local function f_on_track_released(p145) --[[ Name: on_track_released ]] --[[ Line: 560 ]]
        --[[ Upvalues: (copy 1): v_u_53, (copy 2): v_u_54, (ref 3): v_u_7, (ref 4): v_u_10, (ref 5): v_u_38, (ref 6): v_u_37, (copy 7): v_u_47, (ref 8): v_u_1, (ref 9): v_u_12, (copy 10): f_hit_effect_on_track ]]
        v_u_53:get(p145):track_release()
        for v146 = 1, v_u_54:count() do
            local v147 = v_u_54:get(v146)
            local v148 = v147:get_note_loaded_data()
            if v148:get_track() == p145 and (v148:get_type() == v_u_7.NoteType.Hold and v147:get_held_note_state() == v_u_10.Holding) then
                local v149 = v148:get_time_ms() + v148:get_duration()
                local v150 = v_u_38
                if v150 == nil then
                    v150 = v_u_37
                end;
                local v151 = v_u_1:timedelta_to_result_obj(v_u_47:get_display_time_ms() - v149, v150)
                if v151 ~= v_u_12.NoteResult_Miss then
                    f_hit_effect_on_track(v147, v151, p145)
                    v_u_54:get(v146):cleanup()
                    v_u_54:remove_at(v146)
                    return;
                end;
                v147:set_held_note_state(v_u_10.HoldMissedActive)
                local v152 = v148:get_track()
                if v_u_47:is_autoplay_enabled() ~= true then
                    f_hit_effect_on_track(v147, v_u_12.NoteResult_Miss, v152)
                    return;
                end;
                break;
            end;
        end;
    end;
    v_u_47.update_autoplay = function(_) --[[ Name: update_autoplay ]] --[[ Line: 587 ]]
        --[[ Upvalues: (copy 1): v_u_54, (ref 2): v_u_7, (ref 3): v_u_37, (copy 4): v_u_47, (ref 5): v_u_1, (ref 6): v_u_12, (copy 7): f_on_track_pressed, (copy 8): f_on_track_released, (copy 9): v_u_53 ]]
        for v153 = v_u_54:count(), 1, -1 do
            local v154 = v_u_54:get(v153):get_note_loaded_data()
            local v155 = v154:get_track()
            if v154:get_type() == v_u_7.NoteType.Single then
                local v156, v157 = v154:get_time_ms()
                if v157 == nil then
                    v157 = v_u_37
                end;
                local v158 = v_u_47:get_display_time_ms() - v156
                if v158 >= 0 and v_u_1:timedelta_to_result_obj(v158, v157) ~= v_u_12.NoteResult_Miss then
                    f_on_track_pressed(v155)
                    f_on_track_released(v155)
                end;
            elseif v154:get_type() == v_u_7.NoteType.Hold then
                if v_u_53:get(v155):is_track_pressed() == false then
                    local v159, v160 = v154:get_time_ms()
                    if v160 == nil then
                        v160 = v_u_37
                    end;
                    local v161 = v_u_47:get_display_time_ms() - v159
                    if v161 >= 0 and v_u_1:timedelta_to_result_obj(v161, v160) ~= v_u_12.NoteResult_Miss then
                        f_on_track_pressed(v155)
                    end;
                else
                    local v162 = v154:get_time_ms() + v154:get_duration()
                    local v163 = nil
                    if v163 == nil then
                        v163 = v_u_37
                    end;
                    local v164 = v_u_47:get_display_time_ms() - v162
                    if v164 >= 0 and v_u_1:timedelta_to_result_obj(v164, v163) ~= v_u_12.NoteResult_Miss then
                        f_on_track_released(v155)
                    end;
                end;
            end;
        end;
    end;
    local v_u_165 = 9999
    v_u_47.get_time_since_any_pressed = function(_) --[[ Name: get_time_since_any_pressed ]] --[[ Line: 619 ]]
        --[[ Upvalues: (ref 1): v_u_165 ]]
        return v_u_165;
    end;
    local v_u_166 = {
        [v_u_4.KEY_TRACK1] = v_u_7.Track.Track1,
        [v_u_4.KEY_TRACK2] = v_u_7.Track.Track2,
        [v_u_4.KEY_TRACK3] = v_u_7.Track.Track3,
        [v_u_4.KEY_TRACK4] = v_u_7.Track.Track4
    }
    local v_u_167 = false
    v_u_47.flag_this_frame_as_not_playing = function(_) --[[ Name: flag_this_frame_as_not_playing ]] --[[ Line: 629 ]]
        --[[ Upvalues: (ref 1): v_u_167 ]]
        v_u_167 = true
    end;
    local v_u_168 = 0
    v_u_47.set_allow_resync_playback_sound_immediately = function(_) --[[ Name: set_allow_resync_playback_sound_immediately ]] --[[ Line: 637 ]]
        --[[ Upvalues: (ref 1): v_u_168 ]]
        v_u_168 = 5
    end;
    v_u_47.update = function(p169, p170) --[[ Name: update ]] --[[ Line: 641 ]]
        --[[ Upvalues: (copy 1): p_u_44, (copy 2): v_u_72, (copy 3): v_u_74, (ref 4): v_u_73, (copy 5): l_ImageLabel_0, (ref 6): v_u_167, (ref 7): v_u_165, (copy 8): v_u_166, (copy 9): f_on_track_pressed, (copy 10): f_on_track_released, (ref 11): v_u_2, (ref 12): v_u_86, (copy 13): l_Sound_0, (ref 14): v_u_70, (ref 15): v_u_55, (ref 16): v_u_69, (ref 17): v_u_168, (ref 18): v_u_6, (ref 19): v_u_1, (ref 20): v_u_82, (ref 21): v_u_4, (copy 22): v_u_52, (copy 23): v_u_53, (copy 24): v_u_54, (copy 25): v_u_61 ]]
        local v171
        if p_u_44._input:get_has_frame_focused_element() == true then
            v171 = false
        else
            local v172
            v171, v172 = v_u_72:test_cursor_over_frame()
            if v171 then
                p_u_44._input:set_has_frame_focused_element(true)
                v_u_74:set(v172._x, v172._y)
            end;
            v_u_73 = v171
            if v_u_73 == true then
                l_ImageLabel_0.Position = UDim2.new(0, v_u_74._x, 0, v_u_74._y)
                l_ImageLabel_0.Visible = true
            else
                l_ImageLabel_0.Visible = false
            end;
        end;
        if p169:is_playing() then
            if v_u_167 ~= true then
                if p169:is_autoplay_enabled() == true then
                    v_u_165 = 0
                    p169:update_autoplay()
                else
                    local v173 = false
                    for v174, v175 in pairs(v_u_166) do
                        v173 = p_u_44._input:control_pressed(v174) and true or v173
                        if p_u_44._input:control_just_pressed(v174) then
                            f_on_track_pressed(v175)
                        end;
                        if p_u_44._input:control_just_released(v174) then
                            f_on_track_released(v175)
                        end;
                    end;
                    if v173 then
                        v_u_165 = 0
                    else
                        v_u_165 = v_u_165 + v_u_2:TimescaleToDeltaTime(p170)
                    end;
                end;
            end;
            local v176 = v_u_86
            v_u_86 = l_Sound_0.TimePosition
            local v177 = (l_Sound_0.TimePosition - v176) * 1000
            local v178 = v_u_70 / 1000
            local v179 = (v_u_55 + v_u_69) / 1000
            v_u_168 = v_u_168 + v_u_2:TimescaleToDeltaTime(p170)
            if v_u_168 >= 5 and (l_Sound_0 and (l_Sound_0.IsLoaded == true and (v179 >= 0 and math.abs(l_Sound_0.TimePosition - v179) > 0.2))) then
                v_u_6:puts("EditorNoteTrackDisplay Force Resync Delta[%.3fs] Threshold[%.3fs] from(%.2fs) to(%.2fs)", l_Sound_0.TimePosition - v179, 0.2, l_Sound_0.TimePosition, v179)
                l_Sound_0.TimePosition = v_u_1:clamp(v179, 0, v178)
                v_u_168 = 0
            end;
            if v179 <= 0 and l_Sound_0.Playing == true then
                l_Sound_0.Volume = 0
                p169:set_allow_resync_playback_sound_immediately()
            elseif not v_u_1:flt_cmp_delta(l_Sound_0.Volume, v_u_82, 0.1) then
                l_Sound_0.Volume = v_u_82
                l_Sound_0.TimePosition = v179
            end;
            p169:set_display_time_ms(v_u_55 + v177)
            if p_u_44._input:control_pressed(v_u_4.KEY_DEBUG_1) then
                local v180 = (v_u_55 + v_u_69) / 1000
                v_u_6:puts("TimePosition(%.3f) LastTimePosition(%.3f) TimePosition_Delta(%.3f) - _display_time_ms Expected(%.3f) Delta(%.3f) game_delta_time_sec(%.3f)", l_Sound_0.TimePosition, v176, l_Sound_0.TimePosition - v176, v180, l_Sound_0.TimePosition - v180, v177 / 1000)
            end;
            if v177 > 0 then
                if v_u_70 < v_u_55 then
                    p169:set_display_time_ms(v_u_70)
                    p169:set_playing(false)
                end;
                if v_u_52:calculate_active_timing_point() ~= v_u_52:calculate_active_timing_point() then
                    v_u_52:full_refresh_active_time_bars()
                end;
                p169:update_active_display_notes()
            end;
        else
            p169:set_allow_resync_playback_sound_immediately()
            v_u_165 = 0
            for v181 = 1, v_u_53:count() do
                local v182 = v_u_53:get(v181)
                if v182:is_track_pressed() then
                    v182:track_release()
                end;
            end;
        end;
        if v_u_167 == true and (p169:is_playing() and (l_Sound_0 and l_Sound_0.IsLoaded == true)) then
            l_Sound_0.Volume = 0
            p169:set_allow_resync_playback_sound_immediately()
        end;
        v_u_167 = false
        p169:update_cursor_behaviour(p170, v171)
        for v183 = 1, v_u_53:count() do
            v_u_53:get(v183):update(p170)
        end;
        for v184 = 1, v_u_54:count() do
            v_u_54:get(v184):update(p170)
        end;
        v_u_61:update(p170, p_u_44)
        v_u_61:post_update(p170, p_u_44)
    end;
    local v_u_185 = v_u_19:new()
    local v_u_186 = v_u_19:new()
    v_u_47.get_hovered_note_index_set = function(_) --[[ Name: get_hovered_note_index_set ]] --[[ Line: 790 ]]
        --[[ Upvalues: (copy 1): v_u_185 ]]
        return v_u_185;
    end;
    v_u_47.get_selected_note_index_set = function(_) --[[ Name: get_selected_note_index_set ]] --[[ Line: 791 ]]
        --[[ Upvalues: (copy 1): v_u_186 ]]
        return v_u_186;
    end;
    local v_u_187 = Vector2.new(0, 0)
    local v_u_188 = v_u_7.UndoState:new()
    local v_u_189 = v_u_5:new()
    local v_u_190 = v_u_5:new()
    local v_u_191 = false
    v_u_47.has_current_drag_operation = function(_) --[[ Name: has_current_drag_operation ]] --[[ Line: 801 ]]
        --[[ Upvalues: (ref 1): v_u_191 ]]
        return v_u_191;
    end;
    local v_u_192 = 1
    v_u_47.set_hold_beat_length_multiplier = function(_, p193) --[[ Name: set_hold_beat_length_multiplier ]] --[[ Line: 804 ]]
        --[[ Upvalues: (ref 1): v_u_192 ]]
        v_u_192 = p193
    end;
    v_u_47.get_hold_beat_length_multiplier = function(_) --[[ Name: get_hold_beat_length_multiplier ]] --[[ Line: 805 ]]
        --[[ Upvalues: (ref 1): v_u_192 ]]
        return v_u_192;
    end;
    local v_u_194 = v_u_5:new()
    local v_u_195 = v_u_5:new()
    local v_u_196 = v_u_5:new()
    v_u_47.copy_selected_notes = function(p197) --[[ Name: copy_selected_notes ]] --[[ Line: 810 ]]
        --[[ Upvalues: (copy 1): v_u_194, (copy 2): v_u_186, (copy 3): v_u_68, (ref 4): v_u_7, (copy 5): v_u_195, (copy 6): v_u_196, (ref 7): v_u_24, (copy 8): p_u_44, (copy 9): p_u_45, (ref 10): v_u_42, (ref 11): v_u_25 ]]
        v_u_194:clear()
        for v198, _ in v_u_186:key_itr() do
            local v199 = v_u_68:get(v198)
            if v199 ~= nil then
                v_u_194:push_back((v_u_7.Note:from_table(v199:to_table())))
            end;
        end;
        if v_u_194:count() > 0 then
            local v200 = v_u_194:get(1):get_time_ms()
            for v201 = 1, v_u_194:count() do
                v200 = math.min(v200, v_u_194:get(v201):get_time_ms())
            end;
            for _, v202 in v_u_194:key_itr() do
                v202:set_time_ms(v202:get_time_ms() - v200)
            end;
        end;
        for _, v203 in v_u_195:key_itr() do
            v203:cleanup()
        end;
        v_u_195:clear()
        v_u_196:clear()
        for _, v204 in v_u_194:key_itr() do
            local v205 = v_u_7.Note:from_table(v204:to_table())
            v_u_196:push_back(v205)
            if v204:get_type() == v_u_7.NoteType.Single then
                local v206 = v_u_24:new(p_u_44, p197, v205, -1, p_u_45)
                v206:set_custom_alpha(0.25)
                v206:set_custom_color(true, v_u_42)
                v_u_195:push_back(v206)
            elseif v204:get_type() == v_u_7.NoteType.Hold then
                local v207 = v_u_25:new(p_u_44, p197, v205, -2, p_u_45)
                v207:set_custom_alpha(0.25)
                v207:set_custom_color(true, v_u_42)
                v_u_195:push_back(v207)
            end;
        end;
        for _, v208 in v_u_195:key_itr() do
            v208:get_note_loaded_data():set_time_ms(-100000)
            v208:update_position_to_parent_track_display_time()
        end;
        p197:push_display_message(string.format("Copied %d notes.", v_u_194:count()))
    end;
    local function f_update_current_drag_operation_and_undo_state() --[[ Name: update_current_drag_operation_and_undo_state ]] --[[ Line: 873 ]]
        --[[ Upvalues: (copy 1): v_u_68, (copy 2): v_u_186, (ref 3): v_u_188, (copy 4): v_u_47 ]]
        for v209 = 1, v_u_68:count() do
            local v210 = v_u_68:get(v209)
            if v_u_186:contains(v209) then
                v210:local_set_selection_start_time_ms(v210:get_time_ms())
                v210:local_set_selection_start_track(v210:get_track())
                v210:local_set_selection_start_duration(v210:get_duration())
            end;
        end;
        v_u_188:copy_current_editor_note_track_display_state(v_u_47)
    end;
    local function _() --[[ Name: push_current_undo_state ]] --[[ Line: 885 ]]
        --[[ Upvalues: (copy 1): v_u_189, (ref 2): v_u_188, (ref 3): v_u_7, (copy 4): f_update_current_drag_operation_and_undo_state, (copy 5): v_u_190 ]]
        v_u_189:push_back(v_u_188)
        if v_u_189:count() > 25 then
            v_u_189:pop_front()
        end;
        v_u_188 = v_u_7.UndoState:new()
        f_update_current_drag_operation_and_undo_state()
        v_u_190:clear()
    end;
    v_u_47.copy_current_state_and_push_undo_state = function(p211) --[[ Name: copy_current_state_and_push_undo_state ]] --[[ Line: 896 ]]
        --[[ Upvalues: (ref 1): v_u_188, (copy 2): v_u_189, (ref 3): v_u_7, (copy 4): f_update_current_drag_operation_and_undo_state, (copy 5): v_u_190 ]]
        v_u_188:copy_current_editor_note_track_display_state(p211)
        v_u_189:push_back(v_u_188)
        if v_u_189:count() > 25 then
            v_u_189:pop_front()
        end;
        v_u_188 = v_u_7.UndoState:new()
        f_update_current_drag_operation_and_undo_state()
        v_u_190:clear()
    end;
    local function _(p212) --[[ Name: apply_undo_state ]] --[[ Line: 901 ]]
        --[[ Upvalues: (copy 1): v_u_47, (copy 2): f_update_current_drag_operation_and_undo_state ]]
        p212:apply_undo_state_to_note_track_display(v_u_47)
        v_u_47:full_refresh_active_display_notes()
        f_update_current_drag_operation_and_undo_state()
    end;
    local function f_snap_time_ms_to_nearest_beat_time_ms(p213) --[[ Name: snap_time_ms_to_nearest_beat_time_ms ]] --[[ Line: 907 ]]
        --[[ Upvalues: (copy 1): v_u_52 ]]
        local v214 = p213
        local v215 = false
        for v216, _ in v_u_52:get_active_beat_times_ms_to_divisors():key_itr() do
            if v215 == false then
                v214 = v216
                v215 = true
            elseif v216 <= p213 and math.abs(v216 - p213) < math.abs(v214 - p213) then
                v214 = v216
            end;
        end;
        return v214;
    end;
    local function f_test_if_only_selected_hold_tail() --[[ Name: test_if_only_selected_hold_tail ]] --[[ Line: 922 ]]
        --[[ Upvalues: (copy 1): v_u_186, (ref 2): v_u_22, (copy 3): v_u_68, (ref 4): v_u_7 ]]
        if v_u_186:count() == 1 then
            local v217 = v_u_186:key_list():random()
            if v_u_186:get(v217) == v_u_22.BoundingBoxIndex.Tail then
                local v218 = v_u_68:get(v217)
                if v218:get_type() == v_u_7.NoteType.Hold then
                    return v218;
                else
                    return nil;
                end;
            else
                return nil;
            end;
        else
            return nil;
        end;
    end;
    local v_u_219 = v_u_5:new()
    local function f_get_active_display_notes_data_list() --[[ Name: get_active_display_notes_data_list ]] --[[ Line: 935 ]]
        --[[ Upvalues: (copy 1): v_u_219, (copy 2): v_u_54, (ref 3): v_u_5 ]]
        local v220 = v_u_219
        v220:clear()
        for v221 = 1, v_u_54:count() do
            v220:push_back(v_u_54:get(v221):get_note_loaded_data())
        end;
        v_u_5:sort_fast(v220, function(p222, p223) --[[ Line: 942 ]]
            return p222:get_time_ms() < p223:get_time_ms();
        end)
        return v220;
    end;
    local function f_loaded_note_data_needs_resort() --[[ Name: loaded_note_data_needs_resort ]] --[[ Line: 948 ]]
        --[[ Upvalues: (copy 1): v_u_68 ]]
        local v224 = 0
        local v225 = false
        for v226 = 1, v_u_68:count() do
            local v227 = v_u_68:get(v226)
            if v227:get_time_ms() < v224 then
                return true;
            end;
            v224 = v227:get_time_ms()
        end;
        return v225;
    end;
    local function _() --[[ Name: sort_loaded_note_data ]] --[[ Line: 964 ]]
        --[[ Upvalues: (ref 1): v_u_5, (copy 2): v_u_68, (copy 3): f_recalculate_loaded_note_data_stats ]]
        v_u_5:sort_fast(v_u_68, function(p228, p229) --[[ Line: 965 ]]
            return p228:get_time_ms() < p229:get_time_ms();
        end)
        f_recalculate_loaded_note_data_stats()
    end;
    local v_u_230 = v_u_19:new()
    local v_u_231 = v_u_19:new()
    v_u_47.update_cursor_behaviour = function(p232, _, p233) --[[ Name: update_cursor_behaviour ]] --[[ Line: 974 ]]
        --[[ Upvalues: (copy 1): v_u_74, (copy 2): v_u_185, (copy 3): v_u_54, (ref 4): v_u_75, (ref 5): v_u_76, (copy 6): v_u_195, (ref 7): v_u_39, (copy 8): p_u_44, (ref 9): v_u_4, (ref 10): v_u_187, (ref 11): v_u_40, (copy 12): v_u_186, (copy 13): f_update_current_drag_operation_and_undo_state, (ref 14): v_u_191, (copy 15): f_snap_time_ms_to_nearest_beat_time_ms, (copy 16): f_test_if_only_selected_hold_tail, (ref 17): v_u_1, (ref 18): v_u_7, (copy 19): v_u_52, (copy 20): v_u_68, (copy 21): f_loaded_note_data_needs_resort, (copy 22): v_u_230, (copy 23): v_u_231, (ref 24): v_u_5, (copy 25): f_recalculate_loaded_note_data_stats, (ref 26): v_u_188, (copy 27): v_u_189, (copy 28): v_u_190, (copy 29): v_u_47, (copy 30): f_get_active_display_notes_data_list, (ref 31): v_u_192, (ref 32): v_u_41, (ref 33): v_u_43, (copy 34): v_u_194, (copy 35): v_u_196, (ref 36): v_u_42, (ref 37): v_u_19, (ref 38): v_u_22 ]]
        local v234 = v_u_74:to_vector2()
        v_u_185:clear()
        if p233 then
            for v235 = 1, v_u_54:count() do
                local v236 = v_u_54:get(v235)
                local v237 = v236:get_bounding_sprect_list()
                for v238 = 1, v237:count() do
                    if v237:get(v238):contains_vec2(v234) then
                        v_u_185:add(v236:get_note_index(), v238)
                        break;
                    end;
                end;
                if v_u_185:count() > 0 then
                    break;
                end;
            end;
        end;
        v_u_75:get_note_loaded_data():set_time_ms(-100000)
        v_u_75:update_position_to_parent_track_display_time()
        v_u_76:get_note_loaded_data():set_time_ms(-100000)
        v_u_76:get_note_loaded_data():set_duration(10000)
        v_u_76:update_position_to_parent_track_display_time()
        for _, v239 in v_u_195:key_itr() do
            v239:get_note_loaded_data():set_time_ms(-100000)
            v239:update_position_to_parent_track_display_time()
        end;
        for v240 = 1, v_u_54:count() do
            v_u_54:get(v240):set_custom_color(false)
        end;
        if p232:get_current_mode() == v_u_39.Select then
            if p233 and p_u_44._input:control_just_pressed(v_u_4.KEY_CLICK) then
                v_u_187 = v234
                if v_u_185:count() > 0 then
                    if p_u_44._input:control_pressed(v_u_4.KEY_EDITOR_MODIFIER_SHIFT) == true then
                        p232:set_select_sub_mode(v_u_40.Multiple)
                        p232:push_updated_mode()
                    end;
                    if p232:get_select_sub_mode() == v_u_40.Multiple ~= true and v_u_186:contains(v_u_185:key_list():random()) ~= true then
                        v_u_186:clear()
                    end;
                    for v241, v242 in v_u_185:key_itr() do
                        v_u_186:add(v241, v242)
                    end;
                elseif p_u_44._input:control_pressed(v_u_4.KEY_EDITOR_MODIFIER_SHIFT) ~= true then
                    v_u_186:clear()
                end;
                f_update_current_drag_operation_and_undo_state()
                v_u_191 = true
            end;
            if p233 and (p_u_44._input:control_pressed(v_u_4.KEY_CLICK) and v_u_186:count() > 0) then
                local v243, v244 = p232:get_pix_display_position_to_time_ms_and_track_index(v_u_187)
                local v245 = f_snap_time_ms_to_nearest_beat_time_ms(v243)
                local v246, v247 = p232:get_pix_display_position_to_time_ms_and_track_index(v234)
                local v248 = f_snap_time_ms_to_nearest_beat_time_ms(v246) - v245
                local v249 = v247 - v244
                local v250 = f_test_if_only_selected_hold_tail()
                if v250 == nil then
                    local v251 = false
                    for v252, _ in v_u_186:key_itr() do
                        local v253 = v_u_68:get(v252)
                        if v253 == nil then
                            p232:push_display_message(string.format("Could not find matching index for current drag operation state selected note index %d", v252))
                            v_u_186:remove(v252)
                        else
                            local v254 = v253:local_get_selection_start_time_ms() + v248
                            local v255 = v_u_1:clamp(v253:local_get_selection_start_track() + v249, v_u_7.Track.Track1, v_u_7.Track.Track4)
                            if v254 ~= v253:get_time_ms() or v255 ~= v253:get_track() then
                                v253:set_time_ms(v254)
                                v253:set_track(v255)
                                v251 = true
                            end;
                        end;
                    end;
                    if v251 then
                        if f_loaded_note_data_needs_resort() then
                            local v256 = v_u_230
                            v256:clear()
                            for v257, v258 in v_u_186:key_itr() do
                                v256:add(v_u_68:get(v257), v258)
                            end;
                            local v259 = v_u_231
                            v259:clear()
                            for v260, v261 in v_u_185:key_itr() do
                                v259:add(v_u_68:get(v260), v261)
                            end;
                            v_u_5:sort_fast(v_u_68, function(p262, p263) --[[ Line: 965 ]]
                                return p262:get_time_ms() < p263:get_time_ms();
                            end)
                            f_recalculate_loaded_note_data_stats()
                            v_u_186:clear()
                            v_u_185:clear()
                            for v264 = 1, v_u_68:count() do
                                local v265 = v_u_68:get(v264)
                                if v256:contains(v265) then
                                    v_u_186:add(v264, (v256:get(v265)))
                                end;
                                if v259:contains(v265) then
                                    v_u_185:add(v264, (v259:get(v265)))
                                end;
                            end;
                            p232:full_refresh_active_display_notes()
                        elseif v_u_186:count() > 1 then
                            p232:full_refresh_active_display_notes()
                        else
                            p232:update_active_display_notes()
                        end;
                    end;
                else
                    local v266 = v250:local_get_selection_start_duration() + v248
                    local v267 = v_u_1:clamp(v250:local_get_selection_start_track() + v249, v_u_7.Track.Track1, v_u_7.Track.Track4)
                    local v268 = v_u_52:calculate_active_timing_point():get_beat_length_ms() / v_u_52:get_divisor_count() * 0.975
                    if v250:get_duration() ~= v266 or v267 ~= v250:get_track() then
                        if v268 < v266 then
                            v250:set_duration(v266)
                        end;
                        v250:set_track(v267)
                        p232:update_active_display_notes()
                    end;
                end;
            end;
            if v_u_191 == true and (p_u_44._input:control_just_released(v_u_4.KEY_CLICK) or p_u_44._input:control_pressed(v_u_4.KEY_CLICK) ~= true) then
                if v_u_188:undo_state_has_any_changes_from_note_track_display_state(p232) then
                    local v269, v270 = v_u_7:validate_note_data_list(p232:get_loaded_note_data(), p232:get_songkey())
                    if v269 == true then
                        v_u_189:push_back(v_u_188)
                        if v_u_189:count() > 25 then
                            v_u_189:pop_front()
                        end;
                        v_u_188 = v_u_7.UndoState:new()
                        f_update_current_drag_operation_and_undo_state()
                        v_u_190:clear()
                    else
                        p232:push_display_message(string.format("Invalid state(%s), applying undo to last state", v270))
                        v_u_188:apply_undo_state_to_note_track_display(v_u_47)
                        v_u_47:full_refresh_active_display_notes()
                        f_update_current_drag_operation_and_undo_state()
                    end;
                end;
                v_u_191 = false
                return;
            end;
        elseif p232:get_current_mode() == v_u_39.Add then
            if p233 then
                local v271, v272 = p232:get_pix_display_position_to_time_ms_and_track_index(v234)
                local v273 = f_snap_time_ms_to_nearest_beat_time_ms(v271)
                local v274 = v_u_52:calculate_active_timing_point():get_beat_length_ms()
                local v275 = math.max(v274 / 32, 4)
                local v276 = f_get_active_display_notes_data_list()
                local v277 = true
                for v278 = 1, v276:count() do
                    local v279 = v276:get(v278)
                    if v279:get_track() == v272 then
                        local v280 = v279:get_time_ms()
                        if math.abs(v280 - v273) < v275 or v279:get_type() == v_u_7.NoteType.Hold and (v280 - v275 < v273 and v273 < v279:get_time_ms() + v279:get_duration() + v275) then
                            v277 = false
                            break;
                        end;
                    end;
                end;
                local v281 = v274 * v_u_192
                if p232:get_add_sub_mode() == v_u_41.Hold then
                    local v282 = false
                    local v283 = 0
                    for v284 = 1, v276:count() do
                        local v285 = v276:get(v284)
                        if v285:get_track() == v272 then
                            local v286 = v285:get_time_ms()
                            if v273 - v275 <= v286 and v286 <= v273 + v281 + v275 then
                                v283 = v286
                                v282 = true
                                break;
                            end;
                        end;
                    end;
                    if v282 == true then
                        local v287 = f_snap_time_ms_to_nearest_beat_time_ms(v283 + v275) - v274 / v_u_52:get_divisor_count()
                        if v275 <= v287 - v273 then
                            v281 = v287 - v273
                        else
                            v277 = false
                        end;
                    end;
                end;
                if v277 == true then
                    local v288 = nil
                    if p232:get_add_sub_mode() == v_u_41.Single then
                        v_u_75:get_note_loaded_data():set_time_ms(v273)
                        v_u_75:get_note_loaded_data():set_track(v272)
                        v_u_75:update_position_to_parent_track_display_time()
                        if p_u_44._input:control_just_pressed(v_u_4.KEY_CLICK) then
                            p232:copy_current_state_and_push_undo_state()
                            v288 = v_u_7.Note:new()
                            v288:set_type(v_u_7.NoteType.Single)
                            v288:set_track(v272)
                            v288:set_time_ms(v273)
                            v_u_68:push_back(v288)
                        end;
                    elseif p232:get_add_sub_mode() == v_u_41.Hold then
                        v_u_76:get_note_loaded_data():set_time_ms(v273)
                        v_u_76:get_note_loaded_data():set_track(v272)
                        v_u_76:get_note_loaded_data():set_duration(v281)
                        v_u_76:update_position_to_parent_track_display_time()
                        if p_u_44._input:control_just_pressed(v_u_4.KEY_CLICK) then
                            p232:copy_current_state_and_push_undo_state()
                            v288 = v_u_7.Note:new()
                            v288:set_type(v_u_7.NoteType.Hold)
                            v288:set_track(v272)
                            v288:set_time_ms(v273)
                            v288:set_duration(v281)
                            v_u_68:push_back(v288)
                        end;
                    end;
                    if v288 ~= nil then
                        v_u_5:sort_fast(v_u_68, function(p289, p290) --[[ Line: 965 ]]
                            return p289:get_time_ms() < p290:get_time_ms();
                        end)
                        f_recalculate_loaded_note_data_stats()
                        local v291, v292 = v_u_7:validate_note_data_list(v_u_68, p232:get_songkey())
                        if v291 ~= true then
                            p232:push_display_message(string.format("Cannot place note: %s", v292))
                            v_u_68:remove(v288)
                        end;
                        p232:full_refresh_active_display_notes()
                        return;
                    end;
                end;
            end;
        elseif p232:get_current_mode() == v_u_39.Delete then
            if p233 then
                for v293 = 1, v_u_54:count() do
                    local v294 = v_u_54:get(v293)
                    if v_u_185:contains(v294:get_note_index()) == true then
                        v294:set_custom_color(true, v_u_43)
                    end;
                end;
                if p_u_44._input:control_just_pressed(v_u_4.KEY_CLICK) then
                    p232:copy_current_state_and_push_undo_state()
                    for v295, _ in v_u_185:key_itr() do
                        v_u_68:remove_at(v295)
                    end;
                    v_u_186:clear()
                    v_u_185:clear()
                    v_u_5:sort_fast(v_u_68, function(p296, p297) --[[ Line: 965 ]]
                        return p296:get_time_ms() < p297:get_time_ms();
                    end)
                    f_recalculate_loaded_note_data_stats()
                    p232:full_refresh_active_display_notes()
                    return;
                end;
            end;
        elseif p232:get_current_mode() == v_u_39.Paste and p233 then
            local v298, _ = p232:get_pix_display_position_to_time_ms_and_track_index(v234)
            local v299 = f_snap_time_ms_to_nearest_beat_time_ms(v298)
            for v300 = 1, v_u_195:count() do
                local v301 = v_u_194:get(v300)
                local v302 = v_u_195:get(v300)
                if v301 ~= nil and v302 ~= nil then
                    v302:get_note_loaded_data():set_time_ms(v299 + v301:get_time_ms())
                end;
            end;
            local v303, v304 = v_u_7:validate_note_data_list_paste(p232:get_loaded_note_data(), v_u_196, p232:get_songkey())
            for _, v305 in v_u_195:key_itr() do
                if v303 == true then
                    v305:set_custom_color(true, v_u_42)
                else
                    v305:set_custom_color(true, v_u_43)
                end;
                v305:update_position_to_parent_track_display_time()
            end;
            if p_u_44._input:control_just_pressed(v_u_4.KEY_CLICK) and v_u_196:count() > 0 then
                if v303 == true then
                    p232:copy_current_state_and_push_undo_state()
                    local v306 = v_u_19:new()
                    for _, v307 in v_u_196:key_itr() do
                        local v308 = v_u_7.Note:from_table(v307:to_table())
                        v_u_68:push_back(v308)
                        v306:add_set(v308)
                    end;
                    v_u_5:sort_fast(v_u_68, function(p309, p310) --[[ Line: 965 ]]
                        return p309:get_time_ms() < p310:get_time_ms();
                    end)
                    f_recalculate_loaded_note_data_stats()
                    local v311, v312 = v_u_7:validate_note_data_list(p232:get_loaded_note_data(), p232:get_songkey())
                    if v311 == true then
                        p232:get_selected_note_index_set():clear()
                        for v313 = 1, v_u_68:count() do
                            if v306:contains((v_u_68:get(v313))) then
                                v_u_186:add(v313, v_u_22.BoundingBoxIndex.Head)
                            end;
                        end;
                    else
                        p232:push_display_message(string.format("Post-paste invalid state(%s), applying undo to last state", v312))
                        v_u_188:apply_undo_state_to_note_track_display(v_u_47)
                        v_u_47:full_refresh_active_display_notes()
                        f_update_current_drag_operation_and_undo_state()
                    end;
                    p232:full_refresh_active_display_notes()
                    return;
                end;
                p232:push_display_message(string.format("Cannot paste: %s", v304))
            end;
        end;
    end;
    v_u_47.can_undo_last_operation = function(_) --[[ Name: can_undo_last_operation ]] --[[ Line: 1331 ]]
        --[[ Upvalues: (copy 1): v_u_189 ]]
        return v_u_189:count() > 0;
    end;
    v_u_47.undo_last_operation = function(p314) --[[ Name: undo_last_operation ]] --[[ Line: 1332 ]]
        --[[ Upvalues: (copy 1): v_u_189, (ref 2): v_u_7, (copy 3): v_u_190, (copy 4): v_u_47, (copy 5): f_update_current_drag_operation_and_undo_state ]]
        if v_u_189:count() == 0 then
            return p314:push_display_message("No undo actions available.");
        end;
        local v315 = v_u_7.UndoState:new()
        v315:copy_current_editor_note_track_display_state(p314)
        v_u_190:push_back(v315)
        local v316 = v_u_189:pop_back()
        v315:set_display_time_ms(v316:get_display_time_ms())
        v316:apply_undo_state_to_note_track_display(v_u_47)
        v_u_47:full_refresh_active_display_notes()
        f_update_current_drag_operation_and_undo_state()
        p314:push_display_message(string.format("Undoing last action (%d undo actions available).", v_u_189:count()))
    end;
    v_u_47.can_redo_last_operation = function(_) --[[ Name: can_redo_last_operation ]] --[[ Line: 1346 ]]
        --[[ Upvalues: (copy 1): v_u_190 ]]
        return v_u_190:count() > 0;
    end;
    v_u_47.redo_last_operation = function(p317) --[[ Name: redo_last_operation ]] --[[ Line: 1347 ]]
        --[[ Upvalues: (copy 1): v_u_190, (ref 2): v_u_7, (copy 3): v_u_189, (copy 4): v_u_47, (copy 5): f_update_current_drag_operation_and_undo_state ]]
        if v_u_190:count() == 0 then
            return p317:push_display_message("No redo actions available.");
        end;
        local v318 = v_u_7.UndoState:new()
        v318:copy_current_editor_note_track_display_state(p317)
        v_u_189:push_back(v318)
        local v319 = v_u_190:pop_back()
        v318:set_display_time_ms(v319:get_display_time_ms())
        v319:apply_undo_state_to_note_track_display(v_u_47)
        v_u_47:full_refresh_active_display_notes()
        f_update_current_drag_operation_and_undo_state()
        p317:push_display_message(string.format("Redoing last action (%d redos available).", v_u_190:count()))
    end;
    local v_u_320 = false
    local v_u_321 = ""
    v_u_47.get_display_message = function(_) --[[ Name: get_display_message ]] --[[ Line: 1364 ]]
        --[[ Upvalues: (ref 1): v_u_321 ]]
        return v_u_321;
    end;
    v_u_47.push_display_message = function(_, p322) --[[ Name: push_display_message ]] --[[ Line: 1365 ]]
        --[[ Upvalues: (ref 1): v_u_320, (ref 2): v_u_321 ]]
        v_u_320 = true
        v_u_321 = string.format("[%s] %s", os.date("%H:%M:%S"), p322)
    end;
    v_u_47.raise_display_message = function(_) --[[ Name: raise_display_message ]] --[[ Line: 1369 ]]
        --[[ Upvalues: (ref 1): v_u_320 ]]
        if v_u_320 ~= true then
            return false;
        end;
        v_u_320 = false
        return true;
    end;
    local v_u_323 = false
    v_u_47.push_updated_mode = function(_) --[[ Name: push_updated_mode ]] --[[ Line: 1377 ]]
        --[[ Upvalues: (ref 1): v_u_323 ]]
        v_u_323 = true
    end;
    v_u_47.raise_updated_mode = function(_) --[[ Name: raise_updated_mode ]] --[[ Line: 1380 ]]
        --[[ Upvalues: (ref 1): v_u_323 ]]
        if v_u_323 ~= true then
            return false;
        end;
        v_u_323 = false
        return true;
    end;
    v_u_47.clear_all_notes = function(p324) --[[ Name: clear_all_notes ]] --[[ Line: 1388 ]]
        --[[ Upvalues: (copy 1): f_recalculate_loaded_note_data_stats ]]
        p324:copy_current_state_and_push_undo_state()
        p324:get_loaded_note_data():clear()
        p324:get_selected_note_index_set():clear()
        p324:get_hovered_note_index_set():clear()
        f_recalculate_loaded_note_data_stats()
        p324:full_refresh_active_display_notes()
    end;
    f_cons()
    return v_u_47;
end;
return v36;
