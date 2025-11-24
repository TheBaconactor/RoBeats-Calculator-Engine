-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:52 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.NoteResult)
local v_u_2 = require(game.ReplicatedStorage.Shared.UDimObjWrapper)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_4 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Local.DebugOut)
local v_u_5 = require(game.ReplicatedStorage.Avatar.GearStats)
require(game.ReplicatedStorage.Shared.EventString)
local v6 = {}
local v_u_7 = v_u_3:color3(243, 237, 0)
local v_u_8 = v_u_3:color3(0, 255, 0)
local v_u_9 = v_u_3:color3(0, 207, 256)
v6.new = function(_, p_u_10, p_u_11) --[[ Name: new ]] --[[ Line: 15 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_5, (copy 3): v_u_3, (copy 4): v_u_2, (copy 5): v_u_8, (copy 6): v_u_9, (copy 7): v_u_1, (copy 8): v_u_7 ]]
    local v12 = {}
    local v_u_13 = nil
    local v_u_14 = nil
    local v_u_15 = nil
    local v_u_16 = nil
    local v_u_17 = nil
    v12.cons = function(_) --[[ Name: cons ]] --[[ Line: 24 ]]
        --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_10, (ref 3): v_u_14, (ref 4): v_u_15, (ref 5): v_u_16, (ref 6): v_u_17 ]]
        v_u_13 = p_u_10.TimeLineProto
        v_u_14 = p_u_10.SongTimeMarkerProto
        v_u_15 = p_u_10.NoteElementProto
        v_u_16 = p_u_10.MissElementProto
        v_u_17 = p_u_10.FeverElementProto
        v_u_13.Parent = nil
        v_u_14.Parent = nil
        v_u_15.Parent = nil
        v_u_16.Parent = nil
        v_u_17.Parent = nil
    end;
    local v_u_18 = 0
    local v_u_19 = nil
    local v_u_20 = nil
    local v_u_21 = nil
    local v_u_22 = nil
    local v_u_23 = nil
    local v_u_24 = nil
    local v_u_25 = nil
    local v_u_26 = nil
    local function _(p27) --[[ Name: x_for_ms_time ]] --[[ Line: 41 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_18, (ref 3): v_u_19 ]]
        return math.floor((v_u_4:YForPointOf2PtLine(Vector2.new(0, 0), Vector2.new(v_u_18, v_u_19), p27)));
    end;
    local function _(p28) --[[ Name: y_for_ms_delta ]] --[[ Line: 45 ]]
        --[[ Upvalues: (ref 1): v_u_4, (ref 2): v_u_26, (ref 3): v_u_20, (ref 4): v_u_21 ]]
        return math.floor((v_u_4:YForPointOf2PtLine(Vector2.new(v_u_26, v_u_20), Vector2.new(v_u_21, 0), p28)));
    end;
    local v_u_29 = false
    v12.has_rendered_graph = function(_) --[[ Name: has_rendered_graph ]] --[[ Line: 51 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29;
    end;
    v12.render_graph = function(p30) --[[ Name: render_graph ]] --[[ Line: 53 ]]
        --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_19, (copy 3): p_u_10, (ref 4): v_u_20, (ref 5): v_u_18, (copy 6): p_u_11, (ref 7): v_u_5, (ref 8): v_u_21, (ref 9): v_u_22, (ref 10): v_u_23, (ref 11): v_u_24, (ref 12): v_u_25, (ref 13): v_u_26 ]]
        v_u_29 = true
        v_u_19 = p_u_10.Size.X.Offset
        v_u_20 = p_u_10.Size.Y.Offset
        v_u_18 = p_u_11:es_gamelocal_get_audiomanager():get_song_length_ms()
        local v31
        if p_u_11._players._slots:contains(p_u_11:get_local_game_slot()) then
            v31 = p_u_11._players._slots:get(p_u_11:get_local_game_slot())._gear_stats
        else
            v31 = v_u_5:get_imm_statsdict_base()
        end;
        local v32, v33, v34, v35, v36, v37 = v_u_5:get_note_times(v31)
        v_u_21 = v32
        v_u_22 = v33
        v_u_23 = v34
        v_u_24 = v35
        v_u_25 = v36
        v_u_26 = v37
        p30:render_time_lines()
        p30:render_song_time_markers()
        p30:render_notes()
    end;
    v12.render_time_lines = function(_) --[[ Name: render_time_lines ]] --[[ Line: 73 ]]
        --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_10, (ref 3): v_u_3, (ref 4): v_u_2, (ref 5): v_u_4, (ref 6): v_u_26, (ref 7): v_u_20, (ref 8): v_u_21, (ref 9): v_u_22, (ref 10): v_u_8, (ref 11): v_u_23, (ref 12): v_u_9, (ref 13): v_u_24, (ref 14): v_u_25 ]]
        local function f_make_line(p38, p39, p40) --[[ Name: make_line ]] --[[ Line: 74 ]]
            --[[ Upvalues: (ref 1): v_u_13, (ref 2): p_u_10, (ref 3): v_u_3, (ref 4): v_u_2, (ref 5): v_u_4, (ref 6): v_u_26, (ref 7): v_u_20, (ref 8): v_u_21 ]]
            local v41 = v_u_13:Clone()
            v41.Parent = p_u_10
            v41.BackgroundColor3 = p39
            v41.TextLabel.Text = p38
            v41.TextLabel.TextColor3 = p39
            v41.TextLabel.Name = v_u_3:r_set_alpha_generate_name({
                ["TextAlpha"] = 0.75
            }, v41.TextLabel)
            v_u_2:set_xy(v41, 0, (math.floor((v_u_4:YForPointOf2PtLine(Vector2.new(v_u_26, v_u_20), Vector2.new(v_u_21, 0), p40)))))
        end;
        f_make_line(string.format("+%dms (Great)", v_u_22), v_u_8, v_u_22)
        f_make_line(string.format("+%dms (Perfect)", v_u_23), v_u_9, v_u_23)
        f_make_line(string.format("%dms (Perfect)", v_u_24), v_u_9, v_u_24)
        f_make_line(string.format("%dms (Great)", v_u_25), v_u_8, v_u_25)
    end;
    v12.render_song_time_markers = function(_) --[[ Name: render_song_time_markers ]] --[[ Line: 90 ]]
        --[[ Upvalues: (ref 1): v_u_14, (copy 2): p_u_10, (ref 3): v_u_3, (ref 4): v_u_2, (ref 5): v_u_4, (ref 6): v_u_18, (ref 7): v_u_19 ]]
        local function f_make_marker(p42) --[[ Name: make_marker ]] --[[ Line: 91 ]]
            --[[ Upvalues: (ref 1): v_u_14, (ref 2): p_u_10, (ref 3): v_u_3, (ref 4): v_u_2, (ref 5): v_u_4, (ref 6): v_u_18, (ref 7): v_u_19 ]]
            local v43 = v_u_14:Clone()
            v43.Parent = p_u_10
            v43.TextLabel.Text = v_u_3:format_ms_time(p42)
            v43.TextLabel.Name = v_u_3:r_set_alpha_generate_name({
                ["TextAlpha"] = 0.75
            }, v43.TextLabel)
            v_u_2:set_xy(v43, math.floor((v_u_4:YForPointOf2PtLine(Vector2.new(0, 0), Vector2.new(v_u_18, v_u_19), p42))), 0)
        end;
        for v44 = 30000, v_u_18, 30000 do
            f_make_marker(v44)
        end;
    end;
    v12.render_notes = function(_) --[[ Name: render_notes ]] --[[ Line: 104 ]]
        --[[ Upvalues: (ref 1): v_u_16, (copy 2): p_u_10, (ref 3): v_u_3, (ref 4): v_u_2, (ref 5): v_u_4, (ref 6): v_u_18, (ref 7): v_u_19, (ref 8): v_u_15, (ref 9): v_u_1, (ref 10): v_u_9, (ref 11): v_u_8, (ref 12): v_u_7, (ref 13): v_u_26, (ref 14): v_u_20, (ref 15): v_u_21, (ref 16): v_u_17, (copy 17): p_u_11 ]]
        local function f_create_miss(p45) --[[ Name: create_miss ]] --[[ Line: 105 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): p_u_10, (ref 3): v_u_3, (ref 4): v_u_2, (ref 5): v_u_4, (ref 6): v_u_18, (ref 7): v_u_19 ]]
            local v46 = v_u_16:Clone()
            v46.Parent = p_u_10
            v46.Name = v_u_3:r_set_alpha_generate_name({
                ["BackgroundAlpha"] = 0.25
            }, v46)
            v_u_2:set_xy(v46, math.floor((v_u_4:YForPointOf2PtLine(Vector2.new(0, 0), Vector2.new(v_u_18, v_u_19), p45))), 0)
        end;
        local function f_create_note(p47, p48, p49, _) --[[ Name: create_note ]] --[[ Line: 111 ]]
            --[[ Upvalues: (ref 1): v_u_15, (ref 2): p_u_10, (ref 3): v_u_1, (ref 4): v_u_9, (ref 5): v_u_8, (ref 6): v_u_7, (ref 7): v_u_3, (ref 8): v_u_2, (ref 9): v_u_4, (ref 10): v_u_18, (ref 11): v_u_19, (ref 12): v_u_26, (ref 13): v_u_20, (ref 14): v_u_21 ]]
            local v50 = v_u_15:Clone()
            v50.Parent = p_u_10
            if p49 == v_u_1.NoteResult_Perfect then
                v50.BackgroundColor3 = v_u_9
            elseif p49 == v_u_1.NoteResult_Great then
                v50.BackgroundColor3 = v_u_8
            else
                v50.BackgroundColor3 = v_u_7
            end;
            v50.BorderSizePixel = 0
            v50.Name = v_u_3:r_set_alpha_generate_name({
                ["BackgroundAlpha"] = 0.75
            }, v50)
            v_u_2:set_xy(v50, math.floor((v_u_4:YForPointOf2PtLine(Vector2.new(0, 0), Vector2.new(v_u_18, v_u_19), p47))), (math.floor((v_u_4:YForPointOf2PtLine(Vector2.new(v_u_26, v_u_20), Vector2.new(v_u_21, 0), p48)))))
        end;
        local function f_create_fever_display(p51, p52) --[[ Name: create_fever_display ]] --[[ Line: 126 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): p_u_10, (ref 3): v_u_3, (ref 4): v_u_2, (ref 5): v_u_4, (ref 6): v_u_18, (ref 7): v_u_19 ]]
            local v53 = v_u_17:Clone()
            v53.Parent = p_u_10
            v53.BackgroundTransparency = v_u_3:tra(0.15)
            v53.Name = v_u_3:r_set_alpha_generate_name({
                ["BackgroundAlpha"] = 0.15
            }, v53)
            v_u_2:set_xy(v53, math.floor((v_u_4:YForPointOf2PtLine(Vector2.new(0, 0), Vector2.new(v_u_18, v_u_19), p51))), 0)
            v53.Size = UDim2.new(0, math.floor((v_u_4:YForPointOf2PtLine(Vector2.new(0, 0), Vector2.new(v_u_18, v_u_19), p52))) - math.floor((v_u_4:YForPointOf2PtLine(Vector2.new(0, 0), Vector2.new(v_u_18, v_u_19), p51))), 1, 0)
        end;
        local v54 = p_u_11:es_gamelocal_get_scoremanager():get_registered_hits()
        local v55 = 0
        local v56 = false
        for v57 = 1, v54:count() do
            local v58 = v54:get(v57)
            if v58.NoteResult == v_u_1.NoteResult_Miss then
                f_create_miss(v58.HitTime)
            else
                f_create_note(v58.HitTime, v58.Delta, v58.NoteResult, v58.Fever)
                if v56 == false and v58.Fever == true then
                    v55 = v58.HitTime
                    v56 = true
                elseif v56 == true and v58.Fever == false then
                    f_create_fever_display(v55, v58.HitTime)
                    v56 = false
                end;
            end;
        end;
    end;
    v12:cons()
    return v12;
end;
return v6;
