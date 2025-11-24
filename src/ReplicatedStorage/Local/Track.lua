-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:27 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_3 = require(game.ReplicatedStorage.Local.TriggerButton)
local v_u_4 = require(game.ReplicatedStorage.Shared.GameSlot)
local v_u_5 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_6 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_7 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
local v_u_8 = require(game.ReplicatedStorage.Shared.NoteSkinColor)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.EventString)
require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_9 = require(game.ReplicatedStorage.Shared.MatchMode)
local v_u_10 = require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_11 = require(game.ReplicatedStorage.Local.NoteDecal.TrackNoteDecalRender)
return {
    ["new"] = function(_, p_u_12, p_u_13, p_u_14) --[[ Name: new ]] --[[ Line: 18 ]]
        --[[ Upvalues: (copy 1): v_u_1, (copy 2): v_u_3, (copy 3): v_u_8, (copy 4): v_u_10, (copy 5): v_u_5, (copy 6): v_u_11, (copy 7): v_u_9, (copy 8): v_u_6, (copy 9): v_u_7, (copy 10): v_u_4, (copy 11): v_u_2 ]]
        local v_u_15 = {}
        local v_u_16 = nil
        local v_u_17 = nil
        local v_u_18 = 0
        local function _() --[[ Name: get_rotation ]] --[[ Line: 25 ]]
            --[[ Upvalues: (ref 1): v_u_18 ]]
            return v_u_18;
        end;
        local function _(p19) --[[ Name: set_rotation ]] --[[ Line: 28 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_16 ]]
            v_u_18 = p19
            v_u_16.PrimaryPart.Rotation = Vector3.new(0, -p19 - 180, 90)
        end;
        local v_u_20 = Vector3.new()
        v_u_15.world_to_player_dirn = function(_) --[[ Name: world_to_player_dirn ]] --[[ Line: 34 ]]
            --[[ Upvalues: (ref 1): v_u_20 ]]
            return v_u_20;
        end;
        local v_u_21 = 0
        local v_u_22 = Vector3.new()
        local v_u_23 = nil
        local function f_cons() --[[ Name: cons ]] --[[ Line: 43 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): v_u_1, (ref 3): v_u_17, (ref 4): v_u_3, (ref 5): p_u_13, (ref 6): p_u_12, (copy 7): p_u_14, (copy 8): v_u_15 ]]
            v_u_16 = game.ReplicatedStorage.ElementProtos.PlayerTrackProto:Clone()
            v_u_16.Name = v_u_1:gen_name(v_u_16.Name)
            v_u_17 = v_u_3:new(p_u_13, p_u_12, p_u_14)
            v_u_15:update_brick_color(1, p_u_13)
            v_u_15:recalc_track_size_and_position()
            v_u_17:create_control_popup()
        end;
        v_u_15.recalc_track_size_and_position = function(p24) --[[ Name: recalc_track_size_and_position ]] --[[ Line: 58 ]]
            --[[ Upvalues: (ref 1): p_u_12, (ref 2): v_u_20, (ref 3): v_u_1, (ref 4): v_u_16, (ref 5): v_u_21, (ref 6): p_u_13, (copy 7): p_u_14, (ref 8): v_u_22, (ref 9): v_u_18, (ref 10): v_u_17 ]]
            local v25 = p_u_12:get_player_world_center()
            local v26 = p_u_12:get_player_world_position() - v25
            v_u_20 = v26.unit
            local v27 = v_u_1:dir_ang_deg(v26.X, v26.Z)
            v_u_16.PrimaryPart.Size = Vector3.new(0.5, v26.Magnitude, 0.25)
            v_u_21 = v_u_16.PrimaryPart.Size.Y
            local v28 = p_u_13:show_fullscreen_mobile_ui() and 8 or 5
            local v29
            if p_u_14 == 1 then
                v29 = v28 * 1.5
            elseif p_u_14 == 2 then
                v29 = v28 * 0.5
            elseif p_u_14 == 3 then
                v29 = v28 * -0.5
            else
                v29 = v28 * -1.5
            end;
            if p_u_13:show_fullscreen_mobile_ui() then
                local v30 = v_u_1:ang_deg_dir(v27 + v29)
                local v31 = Vector3.new(v30.X, 0, v30.Y) * v26.Magnitude * 0.5 + v25
                v_u_22 = Vector3.new(v31.X, 0.5 + p_u_13:get_game_environment_center().Y, v31.Z)
                v_u_16.PrimaryPart.Position = v_u_22 + Vector3.new(0, -0.85, 0)
                v_u_18 = v27
                v_u_16.PrimaryPart.Rotation = Vector3.new(0, -v27 - 180, 90)
            else
                local v32 = v27 + v29
                local v33 = v_u_1:ang_deg_dir(v32)
                local v34 = Vector3.new(v33.X, 0, v33.Y) * v26.Magnitude * 0.5 + v25
                v_u_22 = Vector3.new(v34.X, 0.5 + p_u_13:get_game_environment_center().Y, v34.Z)
                v_u_16.PrimaryPart.Position = v_u_22 + Vector3.new(0, -0.85, 0)
                v_u_18 = v32
                v_u_16.PrimaryPart.Rotation = Vector3.new(0, -v32 - 180, 90)
                local v35 = v_u_18 - v29 * 0.25
                v_u_18 = v35
                v_u_16.PrimaryPart.Rotation = Vector3.new(0, -v35 - 180, 90)
            end;
            v_u_17:set_position(p24:get_end_position())
        end;
        v_u_15.teardown = function(_) --[[ Name: teardown ]] --[[ Line: 136 ]]
            --[[ Upvalues: (ref 1): v_u_16, (ref 2): p_u_12, (ref 3): v_u_17, (ref 4): p_u_13, (ref 5): v_u_23 ]]
            v_u_16:Destroy()
            v_u_16 = nil
            p_u_12 = nil
            v_u_17:teardown()
            v_u_17 = nil
            p_u_13 = nil
            p_u_12 = nil
            if v_u_23 then
                v_u_23:teardown()
                v_u_23 = nil
            end;
        end;
        local v_u_36 = v_u_8:get_default_base_color():to_color3()
        local v_u_37 = v_u_8:get_default_fever_color():to_color3()
        v_u_15.set_game_noteskin_colors = function(_, p38, p39) --[[ Name: set_game_noteskin_colors ]] --[[ Line: 155 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_37, (ref 3): v_u_17 ]]
            v_u_36 = p38
            v_u_37 = p39
            v_u_17:set_game_noteskin_colors(p38, p39)
        end;
        v_u_15.set_note_display_mode = function(p40, p41) --[[ Name: set_note_display_mode ]] --[[ Line: 161 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): p_u_13, (ref 3): p_u_12, (ref 4): v_u_16, (ref 5): v_u_5, (ref 6): v_u_17, (ref 7): v_u_23, (ref 8): v_u_11, (copy 9): p_u_14 ]]
            if p41 == v_u_10.Default then
                p40:recalc_track_size_and_position()
                if p_u_13:show_fullscreen_mobile_ui() then
                    if p_u_12:get_game_slot() == p_u_13:get_local_game_slot() then
                        v_u_16.Parent = v_u_5:get_local_elements_folder()
                    else
                        v_u_16.Parent = nil
                    end;
                else
                    v_u_16.Parent = v_u_5:get_local_elements_folder()
                end;
                v_u_17:set_note_display_mode(p41)
                if v_u_23 then
                    v_u_23:set_note_display_mode(p41)
                    return;
                end;
            elseif p41 == v_u_10.DecalDown or p41 == v_u_10.DecalUp then
                v_u_16.Parent = nil
                v_u_17:set_note_display_mode(p41)
                if v_u_23 == nil then
                    v_u_23 = v_u_11:new(p_u_13, p_u_12, p_u_14)
                end;
                v_u_23:set_note_display_mode(p41)
            end;
        end;
        local v_u_42 = 0
        v_u_15.update_brick_color = function(_, p43, _) --[[ Name: update_brick_color ]] --[[ Line: 189 ]]
            --[[ Upvalues: (ref 1): p_u_13, (ref 2): p_u_12, (ref 3): v_u_9, (ref 4): v_u_16, (ref 5): v_u_37, (ref 6): v_u_36, (ref 7): v_u_6, (ref 8): v_u_7, (ref 9): v_u_4, (ref 10): v_u_42, (ref 11): v_u_2 ]]
            if p_u_13._players._slots:contains(p_u_12:get_game_slot()) ~= false then
                local v44 = v_u_9:get_server_game_instance_player_powerbar_active((p_u_13._players._slots:get(p_u_12:get_game_slot())))
                if v44 then
                    v_u_16.PlayerTrackProto.Color = v_u_37
                else
                    v_u_16.PlayerTrackProto.Color = v_u_36
                end;
                local v45 = p_u_13._player_settings_manager:get_key(v_u_6.Key.BrightnessSettings) == v_u_7.Dark and 0.925 or 0.85
                if v_u_4:perp_view_slot(p_u_13:get_local_game_slot(), p_u_12:get_game_slot()) then
                    v45 = v45 * 1.15
                end;
                if v44 and p_u_13:es_gamelocal_get_audiomanager():is_beat() then
                    v_u_42 = -0.25
                    if p_u_13._player_settings_manager:get_key(v_u_6.Key.BrightnessSettings) == v_u_7.Dark then
                        v_u_42 = -0.1
                    end;
                end;
                v_u_16.PlayerTrackProto.Transparency = v45 + v_u_42
                v_u_42 = v_u_2:Expt(v_u_42, 0, v_u_2:NormalizedDefaultExptValueInSeconds(0.75), p43)
            end;
        end;
        v_u_15.update = function(p46, p47, _) --[[ Name: update ]] --[[ Line: 232 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): p_u_13, (ref 3): v_u_23 ]]
            v_u_17:update(p47, p_u_13)
            p46:update_brick_color(p47, p_u_13)
            if v_u_23 then
                v_u_23:update(p47)
            end;
        end;
        v_u_15.get_start_position = function(_) --[[ Name: get_start_position ]] --[[ Line: 240 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_18, (ref 3): v_u_22, (ref 4): v_u_21 ]]
            local l_unit_0 = v_u_1:ang_deg_dir(v_u_18).unit
            return v_u_22 + Vector3.new(l_unit_0.x, 0, l_unit_0.y) * -1 * v_u_21 * 0.5;
        end;
        v_u_15.get_end_position = function(_) --[[ Name: get_end_position ]] --[[ Line: 246 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_18, (ref 3): v_u_22, (ref 4): v_u_21 ]]
            local l_unit_1 = v_u_1:ang_deg_dir(v_u_18).unit
            return v_u_22 + Vector3.new(l_unit_1.x, 0, l_unit_1.y) * 1 * v_u_21 * 0.5 * 0.1;
        end;
        v_u_15.press = function(_) --[[ Name: press ]] --[[ Line: 253 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_23 ]]
            v_u_17:press()
            if v_u_23 then
                v_u_23:press()
            end;
        end;
        v_u_15.release = function(_) --[[ Name: release ]] --[[ Line: 257 ]]
            --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_23 ]]
            v_u_17:release()
            if v_u_23 then
                v_u_23:release()
            end;
        end;
        f_cons()
        return v_u_15;
    end
};
