-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.PlayerSettings)
require(game.ReplicatedStorage.Shared.NoteSkinColor)
require(game.ReplicatedStorage.Shared.NoteDisplayMode)
require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
require(game.ReplicatedStorage.Shared.Note2DSettings)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_3 = require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
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
local v_u_4 = require(game.ReplicatedStorage.Shared.SPDict)
local v20 = {
    ["ActiveTimeBar"] = {
        ["_new"] = function(_, p_u_21, p_u_22, p_u_23, p_u_24) --[[ Name: _new ]] --[[ Line: 49 ]]
            --[[ Upvalues: (copy 1): v_u_1 ]]
            local v25 = {}
            v25.rebind = function(_, p26, p27, p28, p29) --[[ Name: rebind ]] --[[ Line: 52 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): p_u_22, (ref 3): p_u_23, (ref 4): p_u_24 ]]
                p_u_21 = p26
                p_u_22 = p27
                p_u_23 = p28
                p_u_24 = p29
            end;
            v25.get_time_ms = function(_) --[[ Name: get_time_ms ]] --[[ Line: 59 ]]
                --[[ Upvalues: (ref 1): p_u_23 ]]
                return p_u_23;
            end;
            local v_u_30 = nil
            local v_u_31 = nil
            v25.cons = function(p32) --[[ Name: cons ]] --[[ Line: 64 ]]
                --[[ Upvalues: (ref 1): v_u_30, (ref 2): p_u_21, (ref 3): v_u_1, (ref 4): p_u_23, (ref 5): p_u_22, (ref 6): p_u_24, (ref 7): v_u_31 ]]
                v_u_30 = p_u_21._object_pool:depool_key_instance_type("ActiveTimeBarFill", "ImageLabel")
                v_u_30.Visible = true
                v_u_30.Image = ""
                v_u_30.BackgroundColor3 = v_u_1:color3(255, 255, 255)
                v_u_30.Name = v_u_1:gen_name(string.format("ActiveTimeBar ms(%.2f)", p_u_23))
                v_u_30.ZIndex = 4
                v_u_30.AnchorPoint = Vector2.new(0, 0.5)
                local v33 = p_u_22:get_divisor_count()
                if p_u_24 == 0 then
                    v_u_30.Size = UDim2.new(1, 0, 0, 4)
                    v_u_30.BackgroundTransparency = v_u_1:tra(0.75)
                elseif p_u_24 == v33 / 2 then
                    v_u_30.Size = UDim2.new(1, 0, 0, 2)
                    v_u_30.BackgroundTransparency = v_u_1:tra(0.5)
                else
                    v_u_30.Size = UDim2.new(1, 0, 0, 1)
                    v_u_30.BackgroundTransparency = v_u_1:tra(0.25)
                end;
                v_u_30.Parent = p_u_22:get_editor_note_track_display():get_parent_frame()
                if p_u_24 == 0 then
                    v_u_31 = p_u_21._object_pool:depool_key_instance_type("ActiveTimeBarText", "TextLabel")
                    v_u_31.Visible = true
                    v_u_31.BackgroundTransparency = 1
                    v_u_31.Text = v_u_1:format_ms_time_hundredth(p_u_23)
                    v_u_31.TextColor3 = v_u_1:color3(255, 255, 255)
                    v_u_31.Position = UDim2.new(0, 0, 0, 2)
                    v_u_31.Size = UDim2.new(1, 0, 0, 20)
                    v_u_31.TextXAlignment = Enum.TextXAlignment.Left
                    v_u_31.TextYAlignment = Enum.TextYAlignment.Top
                    v_u_31.Font = Enum.Font.SourceSans
                    v_u_31.TextSize = 12
                    v_u_31.ZIndex = 4
                    v_u_31.Parent = v_u_30
                end;
                p32:update_position_to_parent_track_display_time()
            end;
            v25.update_position_to_parent_track_display_time = function(p34) --[[ Name: update_position_to_parent_track_display_time ]] --[[ Line: 107 ]]
                --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_30 ]]
                v_u_30.Position = UDim2.new(0, 0, 0, p_u_22:get_editor_note_track_display():get_time_ms_display_position(p34:get_time_ms()).Y)
            end;
            v25.cleanup = function(p35) --[[ Name: cleanup ]] --[[ Line: 112 ]]
                --[[ Upvalues: (ref 1): v_u_31, (ref 2): p_u_21, (ref 3): v_u_30 ]]
                if v_u_31 ~= nil then
                    v_u_31.Parent = nil
                    p_u_21._object_pool:repool("ActiveTimeBarText", v_u_31)
                    v_u_31 = nil
                end;
                v_u_30.Parent = nil
                p_u_21._object_pool:repool("ActiveTimeBarFill", v_u_30)
                v_u_30 = nil
                p_u_21._lua_pool:repool("EditorNoteTrackDisplay_TimeBarRender_ActiveTimeBar", p35)
                p35:rebind()
            end;
            return v25;
        end
    }
}
local v_u_36 = {
    ["_new"] = function(_, p_u_21, p_u_22, p_u_23, p_u_24) --[[ Name: _new ]] --[[ Line: 49 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v25 = {}
        v25.rebind = function(_, p26, p27, p28, p29) --[[ Name: rebind ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): p_u_21, (ref 2): p_u_22, (ref 3): p_u_23, (ref 4): p_u_24 ]]
            p_u_21 = p26
            p_u_22 = p27
            p_u_23 = p28
            p_u_24 = p29
        end;
        v25.get_time_ms = function(_) --[[ Name: get_time_ms ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): p_u_23 ]]
            return p_u_23;
        end;
        local v_u_30 = nil
        local v_u_31 = nil
        v25.cons = function(p32) --[[ Name: cons ]] --[[ Line: 64 ]]
            --[[ Upvalues: (ref 1): v_u_30, (ref 2): p_u_21, (ref 3): v_u_1, (ref 4): p_u_23, (ref 5): p_u_22, (ref 6): p_u_24, (ref 7): v_u_31 ]]
            v_u_30 = p_u_21._object_pool:depool_key_instance_type("ActiveTimeBarFill", "ImageLabel")
            v_u_30.Visible = true
            v_u_30.Image = ""
            v_u_30.BackgroundColor3 = v_u_1:color3(255, 255, 255)
            v_u_30.Name = v_u_1:gen_name(string.format("ActiveTimeBar ms(%.2f)", p_u_23))
            v_u_30.ZIndex = 4
            v_u_30.AnchorPoint = Vector2.new(0, 0.5)
            local v33 = p_u_22:get_divisor_count()
            if p_u_24 == 0 then
                v_u_30.Size = UDim2.new(1, 0, 0, 4)
                v_u_30.BackgroundTransparency = v_u_1:tra(0.75)
            elseif p_u_24 == v33 / 2 then
                v_u_30.Size = UDim2.new(1, 0, 0, 2)
                v_u_30.BackgroundTransparency = v_u_1:tra(0.5)
            else
                v_u_30.Size = UDim2.new(1, 0, 0, 1)
                v_u_30.BackgroundTransparency = v_u_1:tra(0.25)
            end;
            v_u_30.Parent = p_u_22:get_editor_note_track_display():get_parent_frame()
            if p_u_24 == 0 then
                v_u_31 = p_u_21._object_pool:depool_key_instance_type("ActiveTimeBarText", "TextLabel")
                v_u_31.Visible = true
                v_u_31.BackgroundTransparency = 1
                v_u_31.Text = v_u_1:format_ms_time_hundredth(p_u_23)
                v_u_31.TextColor3 = v_u_1:color3(255, 255, 255)
                v_u_31.Position = UDim2.new(0, 0, 0, 2)
                v_u_31.Size = UDim2.new(1, 0, 0, 20)
                v_u_31.TextXAlignment = Enum.TextXAlignment.Left
                v_u_31.TextYAlignment = Enum.TextYAlignment.Top
                v_u_31.Font = Enum.Font.SourceSans
                v_u_31.TextSize = 12
                v_u_31.ZIndex = 4
                v_u_31.Parent = v_u_30
            end;
            p32:update_position_to_parent_track_display_time()
        end;
        v25.update_position_to_parent_track_display_time = function(p34) --[[ Name: update_position_to_parent_track_display_time ]] --[[ Line: 107 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_30 ]]
            v_u_30.Position = UDim2.new(0, 0, 0, p_u_22:get_editor_note_track_display():get_time_ms_display_position(p34:get_time_ms()).Y)
        end;
        v25.cleanup = function(p35) --[[ Name: cleanup ]] --[[ Line: 112 ]]
            --[[ Upvalues: (ref 1): v_u_31, (ref 2): p_u_21, (ref 3): v_u_30 ]]
            if v_u_31 ~= nil then
                v_u_31.Parent = nil
                p_u_21._object_pool:repool("ActiveTimeBarText", v_u_31)
                v_u_31 = nil
            end;
            v_u_30.Parent = nil
            p_u_21._object_pool:repool("ActiveTimeBarFill", v_u_30)
            v_u_30 = nil
            p_u_21._lua_pool:repool("EditorNoteTrackDisplay_TimeBarRender_ActiveTimeBar", p35)
            p35:rebind()
        end;
        return v25;
    end
}
v_u_36.new = function(_, p37, p38, p39, p40) --[[ Name: new ]] --[[ Line: 37 ]]
    --[[ Upvalues: (copy 1): v_u_36 ]]
    local v41 = p37._lua_pool:depool("EditorNoteTrackDisplay_TimeBarRender_ActiveTimeBar")
    if v41 == nil then
        local v42 = v_u_36:_new(p37, p38, p39, p40)
        v42:cons()
        return v42;
    else
        v41:rebind(p37, p38, p39, p40)
        v41:cons()
        return v41;
    end;
end;
local v_u_43 = v_u_3.TimingPoint:from_table({
    ["Time"] = 0,
    ["BeatLength"] = 500
})
v20.new = function(_, p_u_44, p_u_45) --[[ Name: new ]] --[[ Line: 135 ]]
    --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_43, (copy 3): v_u_3, (copy 4): v_u_4, (copy 5): v_u_36 ]]
    local v46 = {}
    v46.get_editor_note_track_display = function(_) --[[ Name: get_editor_note_track_display ]] --[[ Line: 138 ]]
        --[[ Upvalues: (copy 1): p_u_45 ]]
        return p_u_45;
    end;
    local v_u_47 = v_u_2:new({ v_u_43 })
    v46.get_timing_points = function(_) --[[ Name: get_timing_points ]] --[[ Line: 142 ]]
        --[[ Upvalues: (copy 1): v_u_47 ]]
        return v_u_47;
    end;
    local v_u_48 = v_u_2:new()
    local v_u_49 = 4
    v46.get_divisor_count = function(_) --[[ Name: get_divisor_count ]] --[[ Line: 147 ]]
        --[[ Upvalues: (ref 1): v_u_49 ]]
        return v_u_49;
    end;
    v46.set_divisor_count = function(_, p50) --[[ Name: set_divisor_count ]] --[[ Line: 148 ]]
        --[[ Upvalues: (ref 1): v_u_49 ]]
        v_u_49 = p50
    end;
    v46.load_songdatabase_note_data_timing_points = function(_, p51) --[[ Name: load_songdatabase_note_data_timing_points ]] --[[ Line: 150 ]]
        --[[ Upvalues: (copy 1): v_u_47, (ref 2): v_u_3, (ref 3): v_u_43 ]]
        v_u_47:clear()
        for v52 = 1, #p51.TimingPoints do
            v_u_47:push_back(v_u_3.TimingPoint:from_table(p51.TimingPoints[v52]))
        end;
        if v_u_47:count() == 0 then
            v_u_47:push_back(v_u_43)
        end;
    end;
    local function f_calculate_active_timing_point() --[[ Name: calculate_active_timing_point ]] --[[ Line: 162 ]]
        --[[ Upvalues: (copy 1): p_u_45, (copy 2): v_u_47 ]]
        local v53 = p_u_45:get_display_time_ms()
        local v54 = 1
        for v55 = 1, v_u_47:count() do
            if v_u_47:get(v55):get_time_ms() >= v53 then
                break;
            end;
            v54 = v55
        end;
        return v_u_47:get(v54);
    end;
    v46.calculate_active_timing_point = function(_) --[[ Name: calculate_active_timing_point ]] --[[ Line: 176 ]]
        --[[ Upvalues: (copy 1): f_calculate_active_timing_point ]]
        return f_calculate_active_timing_point();
    end;
    local v_u_56 = v_u_4:new()
    v46.get_active_beat_times_ms_to_divisors = function(_) --[[ Name: get_active_beat_times_ms_to_divisors ]] --[[ Line: 179 ]]
        --[[ Upvalues: (copy 1): v_u_56, (copy 2): f_calculate_active_timing_point, (copy 3): p_u_45, (ref 4): v_u_49 ]]
        v_u_56:clear()
        local v57 = f_calculate_active_timing_point()
        local v58 = p_u_45:get_display_time_active_range_ms()
        local v59 = v57:get_time_ms() + math.ceil((v58:min() - v57:get_time_ms()) / v57:get_beat_length_ms()) * v57:get_beat_length_ms()
        local v60 = 0
        while v59 <= v58:max() do
            v_u_56:add(math.floor(v59), v60 % v_u_49)
            v59 = v59 + v57:get_beat_length_ms() / v_u_49
            v60 = v60 + 1
        end;
        return v_u_56;
    end;
    v46.full_refresh_active_time_bars = function(p61) --[[ Name: full_refresh_active_time_bars ]] --[[ Line: 196 ]]
        --[[ Upvalues: (copy 1): v_u_48 ]]
        for _, v62 in v_u_48:key_itr() do
            v62:cleanup()
        end;
        v_u_48:clear()
        p61:update_active_time_bars()
    end;
    v46.update_active_time_bars = function(p63) --[[ Name: update_active_time_bars ]] --[[ Line: 205 ]]
        --[[ Upvalues: (copy 1): p_u_45, (copy 2): v_u_48, (ref 3): v_u_36, (copy 4): p_u_44 ]]
        local v64 = p63:get_active_beat_times_ms_to_divisors()
        local v65 = p_u_45:get_display_time_active_range_ms()
        for v66 = v_u_48:count(), 1, -1 do
            local v67 = v_u_48:get(v66)
            v64:remove(v67:get_time_ms())
            if v65:contains_eq(v67:get_time_ms()) then
                v67:update_position_to_parent_track_display_time()
            else
                v67:cleanup()
                v_u_48:remove_at(v66)
            end;
        end;
        for v68, v69 in v64:key_itr() do
            if v65:contains_eq(v68) then
                v_u_48:push_back((v_u_36:new(p_u_44, p63, v68, v69)))
            end;
        end;
    end;
    v46.cleanup = function(_) --[[ Name: cleanup ]] --[[ Line: 234 ]]
        --[[ Upvalues: (copy 1): v_u_48 ]]
        for _, v70 in v_u_48:key_itr() do
            v70:cleanup()
        end;
        v_u_48:clear()
    end;
    return v46;
end;
return v20;
