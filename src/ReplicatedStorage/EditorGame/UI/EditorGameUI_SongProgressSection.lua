-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:11 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.NoteSkinColor)
require(game.ReplicatedStorage.Shared.NoteDisplayMode)
require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_3 = require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
require(game.ReplicatedStorage.Shared.Note2DSettings)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPRange)
require(game.ReplicatedStorage.Local.HeldNoteState)
require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.NoteResult)
require(game.ReplicatedStorage.Shared.NoteHitMode)
require(game.ReplicatedStorage.Effects.EffectSystem)
require(game.ReplicatedStorage.EditorGame.UI.Element.EditorNoteResultPopupEffectDecal)
require(game.ReplicatedStorage.Avatar.ElementalColor)
require(game.ReplicatedStorage.Local.HitSFXGroup)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_6 = require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
local v_u_7 = require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Shared.SPVector)
local v8 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_9 = nil
local v_u_10 = nil
v8:require_client(function() --[[ Line: 34 ]]
    --[[ Upvalues: (ref 1): v_u_9, (ref 2): v_u_10 ]]
    v_u_9 = require(game.ReplicatedStorage.EditorGame.UI.Element.EditorGameDisplayUtil)
    v_u_10 = require(game.ReplicatedStorage.EditorGame.Data.EditorDifficultyCalculation)
end)
local v11 = {}
local v_u_18 = {
    ["new"] = function(_, _, p_u_12, p_u_13, p_u_14) --[[ Name: new ]] --[[ Line: 42 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        local v_u_15 = {}
        local v_u_16 = nil
        local v_u_17 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_1, (copy 3): p_u_13, (copy 4): p_u_14, (copy 5): p_u_12, (ref 6): v_u_17, (copy 7): v_u_15 ]]
            v_u_16 = Instance.new("ImageLabel")
            v_u_16.Visible = true
            v_u_16.Image = ""
            v_u_16.BackgroundColor3 = v_u_1:color3(255, 255, 255)
            v_u_16.Name = string.format("SongTimerMarker_%d", p_u_13)
            v_u_16.ZIndex = 4
            v_u_16.AnchorPoint = Vector2.new(0, 0.5)
            if p_u_14 % 2 == 1 then
                v_u_16.Size = UDim2.new(1, 0, 0, 1)
                v_u_16.BackgroundTransparency = v_u_1:tra(0.25)
                v_u_16.Parent = p_u_12:get_display_frame()
            else
                v_u_16.Size = UDim2.new(1, 0, 0, 1)
                v_u_16.BackgroundTransparency = v_u_1:tra(0.1)
                v_u_16.Parent = p_u_12:get_display_frame()
            end;
            if p_u_14 % 2 == 1 then
                v_u_17 = Instance.new("TextLabel")
                v_u_17.Visible = true
                v_u_17.BackgroundTransparency = 1
                v_u_17.Text = v_u_1:format_ms_time(p_u_13)
                v_u_17.TextColor3 = v_u_1:color3(255, 255, 255)
                v_u_17.Position = UDim2.new(0, 0, 0, 2)
                v_u_17.Size = UDim2.new(1, 0, 0, 20)
                v_u_17.TextXAlignment = Enum.TextXAlignment.Left
                v_u_17.TextYAlignment = Enum.TextYAlignment.Top
                v_u_17.Font = Enum.Font.SourceSans
                v_u_17.TextSize = 12
                v_u_17.ZIndex = 4
                v_u_17.Parent = v_u_16
            end;
            v_u_15:update_position_to_parent_track_display_time()
        end;
        v_u_15.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 86 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_16 ]]
            if v_u_17 ~= nil then
                v_u_17.Parent = nil
                v_u_17:Destroy()
                v_u_17 = nil
            end;
            v_u_16.Parent = nil
            v_u_16:Destroy()
            v_u_16 = nil
        end;
        v_u_15.update_position_to_parent_track_display_time = function(_) --[[ Name: update_position_to_parent_track_display_time ]] --[[ Line: 98 ]]
            --[[ Upvalues: (copy 1): p_u_12, (ref 2): v_u_16, (ref 3): v_u_2, (copy 4): p_u_13 ]]
            v_u_16.Position = UDim2.new(0, 0, 0, v_u_2:YForPointOf2PtLineP1P2X(0, p_u_12:get_display_frame().AbsoluteSize.Y, p_u_12:get_editor_game_ui():get_editor_note_track_display():get_audio_duration_ms(), 0, p_u_13))
        end;
        f_cons()
        return v_u_15;
    end
}
local v_u_27 = {
    ["new"] = function(_, _, p_u_19, p_u_20, p_u_21) --[[ Name: new ]] --[[ Line: 111 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_2 ]]
        local v_u_22 = {}
        local v_u_23 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 116 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_1, (copy 3): p_u_20, (copy 4): p_u_19, (copy 5): v_u_22 ]]
            v_u_23 = Instance.new("ImageLabel")
            v_u_23.Visible = true
            v_u_23.Image = ""
            v_u_23.BackgroundColor3 = v_u_1:color3(255, 255, 255)
            v_u_23.Name = string.format("NoteDensityMarker_%d", p_u_20)
            v_u_23.ZIndex = 3
            v_u_23.AnchorPoint = Vector2.new(0, 1)
            v_u_23.Size = UDim2.new(1, 0, 0, 1)
            v_u_23.BackgroundTransparency = v_u_1:tra(0.05)
            v_u_23.Parent = p_u_19:get_note_density_fill_bar_root()
            v_u_22:update_size_and_position_to_bucket_note_count(0)
        end;
        v_u_22.update_size_and_position_to_bucket_note_count = function(_, p24) --[[ Name: update_size_and_position_to_bucket_note_count ]] --[[ Line: 131 ]]
            --[[ Upvalues: (copy 1): p_u_19, (ref 2): v_u_23, (ref 3): v_u_2, (copy 4): p_u_20, (ref 5): v_u_1, (copy 6): p_u_21 ]]
            local l_AbsoluteSize_0 = p_u_19:get_display_frame().AbsoluteSize
            local v25 = p_u_19:get_editor_game_ui():get_editor_note_track_display():get_audio_duration_ms()
            v_u_23.Position = UDim2.new(0, 0, 0, v_u_2:YForPointOf2PtLineP1P2X(0, l_AbsoluteSize_0.Y, v25, 0, p_u_20))
            local v26 = p_u_19:get_scaling_bucket_note_count()
            v_u_23.Size = UDim2.new(v_u_2:YForPointOf2PtLineP1P2X(0, 0, v26, 1, v_u_1:clamp(p24, 0, v26)), 0, 0, v_u_2:YForPointOf2PtLineP1P2X(0, 0, v25, l_AbsoluteSize_0.Y, p_u_21))
        end;
        v_u_22.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 147 ]]
            --[[ Upvalues: (ref 1): v_u_23 ]]
            v_u_23.Parent = nil
            v_u_23:Destroy()
            v_u_23 = nil
        end;
        f_cons()
        return v_u_22;
    end
}
v11.new = function(_, p_u_28, p_u_29, p_u_30) --[[ Name: new ]] --[[ Line: 157 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_5, (copy 3): v_u_7, (ref 4): v_u_9, (copy 5): v_u_6, (copy 6): v_u_1, (copy 7): v_u_18, (copy 8): v_u_27, (ref 9): v_u_10, (copy 10): v_u_2, (copy 11): v_u_3 ]]
    local v31 = {}
    v31.get_display_frame = function(_) --[[ Name: get_display_frame ]] --[[ Line: 160 ]]
        --[[ Upvalues: (copy 1): p_u_29 ]]
        return p_u_29;
    end;
    v31.get_editor_game_ui = function(_) --[[ Name: get_editor_game_ui ]] --[[ Line: 161 ]]
        --[[ Upvalues: (copy 1): p_u_30 ]]
        return p_u_30;
    end;
    local v_u_32 = v_u_4:new()
    local l_ImageLabel_0 = Instance.new("ImageLabel")
    local l_ImageLabel_1 = Instance.new("ImageLabel")
    local l_Frame_0 = Instance.new("Frame")
    local v_u_33 = v_u_5:new()
    v31.get_note_density_fill_bar_root = function(_) --[[ Name: get_note_density_fill_bar_root ]] --[[ Line: 169 ]]
        --[[ Upvalues: (copy 1): l_Frame_0 ]]
        return l_Frame_0;
    end;
    local v_u_34 = v_u_7.CursorFramePositionCalc:new(p_u_28._spui, p_u_30, p_u_30:get_sgui(), p_u_29)
    local function f_cons() --[[ Name: cons ]] --[[ Line: 178 ]]
        --[[ Upvalues: (copy 1): p_u_29, (copy 2): l_ImageLabel_0, (ref 3): v_u_9, (copy 4): p_u_28, (ref 5): v_u_6, (ref 6): v_u_1, (copy 7): l_ImageLabel_1, (copy 8): l_Frame_0 ]]
        p_u_29.ClipsDescendants = true
        l_ImageLabel_0.Visible = true
        l_ImageLabel_0.Image = ""
        l_ImageLabel_0.BackgroundColor3 = v_u_9:get_color3_for_track(p_u_28, v_u_6.Track.Track1, false)
        l_ImageLabel_0.Name = string.format("CurrentVisibleMarker")
        l_ImageLabel_0.ZIndex = 5
        l_ImageLabel_0.AnchorPoint = Vector2.new(0, 1)
        l_ImageLabel_0.BackgroundTransparency = v_u_1:tra(0.25)
        l_ImageLabel_0.Parent = p_u_29
        l_ImageLabel_0.Size = UDim2.new(1, 0, 0, 0)
        l_ImageLabel_0.Position = UDim2.new(0, 0, 0, 0)
        l_ImageLabel_1.Visible = false
        l_ImageLabel_1.Image = ""
        l_ImageLabel_1.BackgroundColor3 = v_u_1:color3(255, 255, 255)
        l_ImageLabel_1.Name = string.format("CursorVisibleMarker")
        l_ImageLabel_1.ZIndex = 6
        l_ImageLabel_1.AnchorPoint = Vector2.new(0, 1)
        l_ImageLabel_1.BackgroundTransparency = v_u_1:tra(0.15)
        l_ImageLabel_1.Parent = p_u_29
        l_ImageLabel_1.Size = UDim2.new(1, 0, 0, 0)
        l_ImageLabel_1.Position = UDim2.new(0, 0, 0, 0)
        l_Frame_0.Parent = p_u_29
        l_Frame_0.Name = "NoteDensityFillBarRoot"
        l_Frame_0.BackgroundTransparency = 1
        l_Frame_0.Size = UDim2.new(1, 0, 1, 0)
        l_Frame_0.ClipsDescendants = true
    end;
    local v_u_35 = 0
    local v_u_36 = 5000
    local v_u_37 = 0
    local v_u_38 = 0
    v31.render_song_time_markers = function(p39) --[[ Name: render_song_time_markers ]] --[[ Line: 216 ]]
        --[[ Upvalues: (copy 1): v_u_32, (copy 2): p_u_30, (ref 3): v_u_18, (copy 4): p_u_28, (copy 5): v_u_33, (ref 6): v_u_36, (ref 7): v_u_27, (ref 8): v_u_10, (ref 9): v_u_35, (ref 10): v_u_37 ]]
        for v40 = 1, v_u_32:count() do
            v_u_32:get(v40):cleanup()
        end;
        v_u_32:clear()
        local v41 = p_u_30:get_editor_note_track_display():get_audio_duration_ms()
        local v42 = 15000
        while v42 < v41 - 500 do
            v_u_32:push_back(v_u_18:new(p_u_28, p39, v42, v_u_32:count()))
            v42 = v42 + 15000
        end;
        for _, v43 in v_u_33:key_itr() do
            v43:cleanup()
        end;
        v_u_33:clear()
        v_u_36 = math.floor(v41 / 65)
        local v44 = 0
        while v44 < v41 do
            local v45 = v_u_27:new(p_u_28, p39, v44, v_u_36)
            local v46 = v_u_10:get_bucket_index(v44, v_u_36)
            v_u_33:add(v46, v45)
            v_u_35 = math.max(v_u_35, v46)
            v44 = v44 + v_u_36
        end;
        for _, v47 in v_u_10:editor_game_data_note_list_calculate_hit_buckets(p_u_30:get_editor_note_track_display():get_loaded_note_data(), nil, v_u_36):key_itr() do
            v_u_37 = math.max(v_u_37, v47)
        end;
    end;
    local v_u_48 = false
    v31.update = function(p49, _) --[[ Name: update ]] --[[ Line: 261 ]]
        --[[ Upvalues: (copy 1): p_u_30, (copy 2): l_ImageLabel_0, (copy 3): p_u_29, (ref 4): v_u_2, (copy 5): p_u_28, (copy 6): v_u_34, (copy 7): l_ImageLabel_1, (ref 8): v_u_3, (ref 9): v_u_48 ]]
        local v50 = p_u_30:get_editor_note_track_display()
        local v51 = v50:get_audio_duration_ms()
        if v51 <= 0 then
            l_ImageLabel_0.Size = UDim2.new(1, 0, 0, 0)
            l_ImageLabel_0.Position = UDim2.new(0, 0, 0, 0)
        else
            local v52 = v50:get_display_time_active_range_ms()
            local v53 = v52:max() - v52:min()
            local l_AbsoluteSize_1 = p_u_29.AbsoluteSize
            l_ImageLabel_0.Position = UDim2.new(0, 0, 0, v_u_2:YForPointOf2PtLineP1P2X(0, l_AbsoluteSize_1.Y, v51, 0, v52:min()))
            l_ImageLabel_0.Size = UDim2.new(1, 0, 0, (math.max(v_u_2:YForPointOf2PtLineP1P2X(0, 0, v51, l_AbsoluteSize_1.Y, v53), 5)))
            local v54
            if p_u_28._input:get_has_frame_focused_element() == true then
                v54 = false
            else
                local v55
                v54, v55 = v_u_34:test_cursor_over_frame()
                if v54 then
                    p_u_28._input:set_has_frame_focused_element(true)
                    l_ImageLabel_1.Visible = true
                    l_ImageLabel_1.Position = UDim2.new(0, 0, 0, v55._y)
                    l_ImageLabel_1.Size = l_ImageLabel_0.Size
                    if p_u_28._input:control_just_pressed(v_u_3.KEY_CLICK) then
                        v_u_48 = true
                    end;
                    if p_u_28._input:control_pressed(v_u_3.KEY_CLICK) then
                        if v_u_48 == true then
                            local v56 = v_u_2:YForPointOf2PtLineP1P2X(0, v51, l_AbsoluteSize_1.Y, 0, v55._y)
                            if v50:get_display_time_ms() ~= v56 then
                                v50:set_display_time_ms(v56)
                                v50:full_refresh_active_display_notes()
                                v50:update_playing_audio_state()
                                v50:flag_this_frame_as_not_playing()
                            end;
                        end;
                    else
                        v_u_48 = false
                    end;
                end;
            end;
            if v54 ~= true then
                l_ImageLabel_1.Visible = false
            end;
            p49:update_bucket_note_counts()
        end;
    end;
    local v_u_57 = v_u_5:new()
    local v_u_58 = 1
    local v_u_59 = 0
    v31.update_bucket_note_counts = function(_) --[[ Name: update_bucket_note_counts ]] --[[ Line: 325 ]]
        --[[ Upvalues: (copy 1): p_u_30, (copy 2): v_u_57, (ref 3): v_u_59, (ref 4): v_u_58, (ref 5): v_u_10, (ref 6): v_u_36, (ref 7): v_u_38, (copy 8): v_u_33, (ref 9): v_u_35, (ref 10): v_u_37 ]]
        local v60 = p_u_30:get_editor_note_track_display():get_loaded_note_data()
        v_u_57:add(v_u_59, 0)
        while v_u_58 <= v60:count() do
            local v61 = v60:get(v_u_58)
            local v62 = v_u_10:get_bucket_index(v61:get_time_ms(), v_u_36)
            if v62 == v_u_59 then
                v_u_10:note_data_increment_bucket_hits(v61, v_u_57, v_u_36)
            elseif v_u_59 < v62 then
                break;
            end;
            v_u_58 = v_u_58 + 1
        end;
        local v63 = v_u_57:get(v_u_59)
        v_u_38 = math.max(v_u_38, v63)
        if v_u_33:contains(v_u_59) then
            v_u_33:get(v_u_59):update_size_and_position_to_bucket_note_count(v63)
        end;
        v_u_59 = v_u_59 + 1
        if v_u_35 < v_u_59 then
            v_u_59 = 0
            v_u_58 = 1
            v_u_37 = v_u_38
            v_u_38 = 0
        end;
    end;
    v31.get_scaling_bucket_note_count = function(_) --[[ Name: get_scaling_bucket_note_count ]] --[[ Line: 357 ]]
        --[[ Upvalues: (ref 1): v_u_37 ]]
        return math.max(20, v_u_37);
    end;
    f_cons()
    return v31;
end;
return v11;
