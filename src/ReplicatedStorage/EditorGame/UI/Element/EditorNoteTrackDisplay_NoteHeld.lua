-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:12 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.NoteSkinColor)
require(game.ReplicatedStorage.Shared.NoteDisplayMode)
require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
require(game.ReplicatedStorage.Shared.Note2DSettings)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPRange)
local v_u_4 = require(game.ReplicatedStorage.Local.HeldNoteState)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPRect)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPVector)
local v7 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_8 = nil
v7:require_client(function() --[[ Line: 22 ]]
    --[[ Upvalues: (ref 1): v_u_8 ]]
    v_u_8 = require(game.ReplicatedStorage.EditorGame.UI.Element.EditorGameDisplayUtil)
end)
local v_u_72 = {
    ["_new"] = function(_, p_u_9, p_u_10, p_u_11, p_u_12, p_u_13) --[[ Name: _new ]] --[[ Line: 49 ]]
        --[[ Upvalues: (copy 1): v_u_4, (ref 2): v_u_8, (copy 3): v_u_1, (copy 4): v_u_2, (copy 5): v_u_5, (copy 6): v_u_3, (copy 7): v_u_6 ]]
        local v_u_14 = {}
        v_u_14.rebind = function(_, p15, p16, p17, p18, p19) --[[ Name: rebind ]] --[[ Line: 59 ]]
            --[[ Upvalues: (ref 1): p_u_9, (ref 2): p_u_10, (ref 3): p_u_11, (ref 4): p_u_12, (ref 5): p_u_13 ]]
            p_u_9 = p15
            p_u_10 = p16
            p_u_11 = p17
            p_u_12 = p18
            p_u_13 = p19
        end;
        local v_u_20 = nil
        local v_u_21 = nil
        local v_u_22 = nil
        local v_u_23 = nil
        local v_u_24 = nil
        local v_u_25 = nil
        local v_u_26 = nil
        local v_u_27 = 1
        local v_u_28 = 1
        local v_u_29 = 0.85
        local v_u_30 = 0.4
        local l_Pre_0 = v_u_4.Pre
        local v_u_31 = false
        v_u_14.get_held_note_state = function(_) --[[ Name: get_held_note_state ]] --[[ Line: 79 ]]
            --[[ Upvalues: (ref 1): l_Pre_0 ]]
            return l_Pre_0;
        end;
        v_u_14.set_held_note_state = function(_, p32) --[[ Name: set_held_note_state ]] --[[ Line: 80 ]]
            --[[ Upvalues: (ref 1): l_Pre_0 ]]
            l_Pre_0 = p32
        end;
        v_u_14.set_did_trigger_tail = function(_, p33) --[[ Name: set_did_trigger_tail ]] --[[ Line: 81 ]]
            --[[ Upvalues: (ref 1): v_u_31 ]]
            v_u_31 = p33
        end;
        local v_u_34 = false
        local v_u_35 = Color3.fromRGB(255, 255, 255)
        local v_u_36 = 1
        local function f_update_fill_color() --[[ Name: update_fill_color ]] --[[ Line: 86 ]]
            --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_20, (ref 3): v_u_35, (ref 4): v_u_23, (ref 5): v_u_22, (ref 6): p_u_10, (ref 7): p_u_12, (ref 8): v_u_8, (ref 9): p_u_9, (ref 10): p_u_11 ]]
            if v_u_34 == true then
                v_u_20.ImageColor3 = v_u_35
                v_u_23.ImageColor3 = v_u_35
                v_u_22.ImageColor3 = v_u_35
            else
                local v37 = v_u_8:get_color3_for_track(p_u_9, p_u_11:get_track(), (p_u_10:get_selected_note_index_set():contains(p_u_12)))
                v_u_20.ImageColor3 = v37
                v_u_23.ImageColor3 = v37
                v_u_22.ImageColor3 = v37
            end;
        end;
        v_u_14.set_custom_color = function(_, p38, p39) --[[ Name: set_custom_color ]] --[[ Line: 100 ]]
            --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_35, (copy 3): f_update_fill_color ]]
            local v40 = v_u_34 ~= p38 and true or v_u_35 ~= p39
            v_u_34 = p38
            if p39 ~= nil then
                v_u_35 = p39
            end;
            if v40 then
                f_update_fill_color()
            end;
        end;
        v_u_14.set_custom_alpha = function(_, p41) --[[ Name: set_custom_alpha ]] --[[ Line: 111 ]]
            --[[ Upvalues: (ref 1): v_u_36, (copy 2): f_update_fill_color ]]
            v_u_36 = p41
            f_update_fill_color()
        end;
        local function f_update_zindex(p42, p43) --[[ Name: update_zindex ]] --[[ Line: 116 ]]
            --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_8, (ref 3): v_u_21, (ref 4): v_u_23, (ref 5): v_u_24, (ref 6): v_u_22 ]]
            if p42 then
                v_u_20.ZIndex = v_u_8:get_selected_note_zindex() + 2
                v_u_21.ZIndex = v_u_8:get_selected_note_zindex() + 3
            else
                v_u_20.ZIndex = v_u_8:get_unselected_note_zindex() + 2
                v_u_21.ZIndex = v_u_8:get_unselected_note_zindex() + 3
            end;
            if p43 then
                v_u_23.ZIndex = v_u_8:get_selected_note_zindex()
                v_u_24.ZIndex = v_u_8:get_selected_note_zindex() + 1
            else
                v_u_23.ZIndex = v_u_8:get_unselected_note_zindex()
                v_u_24.ZIndex = v_u_8:get_unselected_note_zindex() + 1
            end;
            v_u_22.ZIndex = v_u_8:get_note_hold_body_zindex()
        end;
        local function f_get_target_scale() --[[ Name: get_target_scale ]] --[[ Line: 136 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): p_u_12, (ref 3): v_u_8 ]]
            local v44 = 1
            local v45 = 1
            if p_u_10:get_hovered_note_index_set():contains(p_u_12) == true then
                local v46 = p_u_10:get_hovered_note_index_set():get(p_u_12)
                if v46 == v_u_8.BoundingBoxIndex.Head then
                    return 1.15, v45;
                end;
                v45 = v46 == v_u_8.BoundingBoxIndex.Tail and 1.15 or v45
            end;
            return v44, v45;
        end;
        v_u_14.cons = function(p47) --[[ Name: cons ]] --[[ Line: 153 ]]
            --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_36, (ref 3): v_u_27, (ref 4): v_u_28, (ref 5): v_u_29, (ref 6): v_u_30, (ref 7): l_Pre_0, (ref 8): v_u_4, (ref 9): v_u_31, (ref 10): p_u_11, (ref 11): v_u_8, (ref 12): p_u_9, (ref 13): v_u_20, (ref 14): v_u_1, (ref 15): p_u_12, (ref 16): p_u_13, (copy 17): f_get_target_scale, (ref 18): v_u_25, (ref 19): v_u_21, (ref 20): v_u_23, (ref 21): v_u_26, (ref 22): v_u_24, (ref 23): v_u_22, (copy 24): f_update_zindex, (copy 25): f_update_fill_color ]]
            v_u_34 = false
            v_u_36 = 1
            v_u_27 = 1
            v_u_28 = 1
            v_u_29 = 0.85
            v_u_30 = 0.4
            l_Pre_0 = v_u_4.Pre
            v_u_31 = false
            local v48 = p_u_11:get_track()
            local v49 = v_u_8:get_note_decal_info(p_u_9)
            v_u_29 = v49:get_note_size_scale()
            v_u_30 = v49:get_held_note_body_size_scale()
            v_u_20 = p_u_9._object_pool:depool_key_instance_type(v_u_8:get_held_note_decal_render_pool_key(), "ImageLabel")
            v_u_20.Visible = true
            v_u_20.Image = v49:get_held_note_fill_assetid(v48)
            v_u_20.ImageTransparency = v_u_1:tra(1)
            v_u_20.BackgroundTransparency = v_u_1:tra(0)
            v_u_20.Name = v_u_1:gen_name(string.format("HeldNoteHead track(%d) index(%d)", v48, p_u_12))
            v_u_20.AnchorPoint = Vector2.new(0.5, 0.5)
            v_u_20.Parent = p_u_13
            local v50, v51 = f_get_target_scale()
            v_u_25 = p_u_9._object_pool:depool_key_instance_type("UIScale", "UIScale")
            v_u_27 = v50
            v_u_25.Scale = v_u_27
            v_u_25.Parent = v_u_20
            v_u_21 = p_u_9._object_pool:depool_key_instance_type(v_u_8:get_held_note_decal_render_pool_key(), "ImageLabel")
            v_u_21.Visible = true
            v_u_21.Image = v49:get_held_note_outline_assetid(v48)
            v_u_21.ImageColor3 = v_u_1:color3(52, 41, 23)
            v_u_21.ImageTransparency = v_u_1:tra(1)
            v_u_21.BackgroundTransparency = v_u_1:tra(0)
            v_u_21.Position = UDim2.new(0, 0, 0, 0)
            v_u_21.Size = UDim2.new(1, 0, 1, 0)
            v_u_21.Name = v_u_1:gen_name("Outline")
            v_u_21.AnchorPoint = Vector2.new(0, 0)
            v_u_21.Parent = v_u_20
            v_u_23 = p_u_9._object_pool:depool_key_instance_type(v_u_8:get_held_note_decal_render_pool_key(), "ImageLabel")
            v_u_23.Visible = true
            v_u_23.Image = v49:get_held_note_fill_assetid(v48)
            v_u_23.ImageTransparency = v_u_1:tra(1)
            v_u_23.BackgroundTransparency = v_u_1:tra(0)
            v_u_23.Name = v_u_1:gen_name(string.format("HeldNoteTail track(%d) index(%d)", v48, p_u_12))
            v_u_23.AnchorPoint = Vector2.new(0.5, 0.5)
            v_u_23.Parent = p_u_13
            v_u_26 = p_u_9._object_pool:depool_key_instance_type("UIScale", "UIScale")
            v_u_28 = v51
            v_u_26.Scale = v_u_28
            v_u_26.Parent = v_u_23
            v_u_24 = p_u_9._object_pool:depool_key_instance_type(v_u_8:get_held_note_decal_render_pool_key(), "ImageLabel")
            v_u_24.Visible = true
            v_u_24.Image = v49:get_held_note_outline_assetid(v48)
            v_u_24.ImageColor3 = v_u_1:color3(52, 41, 23)
            v_u_24.ImageTransparency = v_u_1:tra(1)
            v_u_24.BackgroundTransparency = v_u_1:tra(0)
            v_u_24.Position = UDim2.new(0, 0, 0, 0)
            v_u_24.Size = UDim2.new(1, 0, 1, 0)
            v_u_24.Name = v_u_1:gen_name("Outline")
            v_u_24.AnchorPoint = Vector2.new(0, 0)
            v_u_24.Parent = v_u_23
            v_u_22 = p_u_9._object_pool:depool_key_instance_type(v_u_8:get_held_node_decal_render_slice_pool_key(), "ImageLabel")
            v_u_22.Visible = true
            v_u_22.ScaleType = Enum.ScaleType.Slice
            v_u_22.SliceCenter = Rect.new(81, 89, 81, 302)
            v_u_22.Image = v49:get_held_note_body_assetid()
            v_u_22.ImageTransparency = v_u_1:tra(1)
            v_u_22.BackgroundTransparency = v_u_1:tra(0)
            v_u_22.Name = v_u_1:gen_name(string.format("HeldNoteBody track(%d) index(%d)", v48, p_u_12))
            v_u_22.AnchorPoint = Vector2.new(0.5, 1)
            v_u_22.Parent = p_u_13
            f_update_zindex(false, false)
            f_update_fill_color()
            p47:update_position_to_parent_track_display_time()
        end;
        v_u_14.cleanup = function(p52) --[[ Name: cleanup ]] --[[ Line: 251 ]]
            --[[ Upvalues: (ref 1): v_u_25, (ref 2): p_u_9, (ref 3): v_u_26, (ref 4): v_u_20, (ref 5): v_u_8, (ref 6): v_u_21, (ref 7): v_u_22, (ref 8): v_u_23, (ref 9): v_u_24 ]]
            v_u_25.Parent = nil
            v_u_25.Scale = 1
            p_u_9._object_pool:repool("UIScale", v_u_25)
            v_u_25 = nil
            v_u_26.Parent = nil
            v_u_26.Scale = 1
            p_u_9._object_pool:repool("UIScale", v_u_26)
            v_u_26 = nil
            v_u_20.Parent = nil
            p_u_9._object_pool:repool(v_u_8:get_held_note_decal_render_pool_key(), v_u_20)
            v_u_20 = nil
            v_u_21.Parent = nil
            p_u_9._object_pool:repool(v_u_8:get_held_note_decal_render_pool_key(), v_u_21)
            v_u_21 = nil
            v_u_22.Parent = nil
            p_u_9._object_pool:repool(v_u_8:get_held_node_decal_render_slice_pool_key(), v_u_22)
            v_u_22 = nil
            v_u_23.Parent = nil
            p_u_9._object_pool:repool(v_u_8:get_held_note_decal_render_pool_key(), v_u_23)
            v_u_23 = nil
            v_u_24.Parent = nil
            p_u_9._object_pool:repool(v_u_8:get_held_note_decal_render_pool_key(), v_u_24)
            v_u_24 = nil
            p_u_9._lua_pool:repool("EditorNoteTrackDisplay_NoteHeld", p52)
            p52:rebind()
        end;
        local function f_update_body_transparency() --[[ Name: update_body_transparency ]] --[[ Line: 293 ]]
            --[[ Upvalues: (copy 1): v_u_14, (ref 2): v_u_4, (ref 3): v_u_31, (ref 4): p_u_10, (ref 5): p_u_12, (ref 6): v_u_8, (ref 7): v_u_22, (ref 8): v_u_1, (ref 9): v_u_36 ]]
            local v53 = v_u_14:get_held_note_state()
            local v54
            if v53 == v_u_4.HoldMissedActive then
                v54 = 0.9
            elseif v53 == v_u_4.Passed and v_u_31 then
                v54 = 1
            else
                v54 = 0.5
                if p_u_10:is_playing() ~= true then
                    if p_u_10:get_selected_note_index_set():contains(p_u_12) then
                        v54 = p_u_10:get_selected_note_index_set():count() == 1 and p_u_10:has_current_drag_operation() and 0.45 or v54
                    else
                        v54 = p_u_10:get_hovered_note_index_set():contains(p_u_12) and (p_u_10:has_current_drag_operation() ~= true and p_u_10:get_hovered_note_index_set():get(p_u_12) == v_u_8.BoundingBoxIndex.Body) and 0.45 or v54
                    end;
                end;
            end;
            v_u_22.ImageTransparency = v_u_1:tra(v_u_1:tra(v54) * v_u_36)
        end;
        v_u_14.update_position_to_parent_track_display_time = function(p55) --[[ Name: update_position_to_parent_track_display_time ]] --[[ Line: 321 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): p_u_11, (ref 3): l_Pre_0, (ref 4): v_u_4, (ref 5): v_u_8, (ref 6): p_u_9, (ref 7): v_u_20, (ref 8): v_u_23, (ref 9): v_u_29, (ref 10): v_u_1, (ref 11): v_u_36, (ref 12): v_u_21, (ref 13): v_u_31, (ref 14): v_u_24, (ref 15): v_u_22, (ref 16): v_u_30, (copy 17): f_update_body_transparency ]]
            local v56, _ = p_u_10:get_editor_display_tracks():get(p_u_11:get_track()):get_track_size_and_position()
            local v57 = p_u_11:get_time_ms() + p_u_11:get_duration()
            local v58 = p_u_10:get_time_ms_display_position(p_u_11:get_time_ms(), p_u_11:get_track())
            local v59 = p_u_10:get_time_ms_display_position(v57, p_u_11:get_track())
            if l_Pre_0 == v_u_4.Holding then
                v58 = p_u_10:get_time_ms_display_position(p_u_10:get_display_time_ms(), p_u_11:get_track())
                if v57 < p_u_10:get_display_time_ms() then
                    v59 = v58
                end;
            end;
            local v60 = v_u_8:get_note_decal_position_offset(p_u_9)
            v_u_20.Position = UDim2.new(0, v58.X + v60.X, 0, v58.Y + v60.Y)
            v_u_23.Position = UDim2.new(0, v59.X + v60.X, 0, v59.Y + v60.Y)
            local v61 = v56.X * v_u_29
            v_u_20.Size = UDim2.new(0, v61, 0, v61)
            v_u_23.Size = v_u_20.Size
            local v62 = p55:get_held_note_state()
            if v62 == v_u_4.Pre then
                v_u_20.ImageTransparency = v_u_1:tra(v_u_1:tra(0) * v_u_36)
                v_u_21.ImageTransparency = v_u_1:tra(v_u_1:tra(0) * v_u_36)
            else
                v_u_20.ImageTransparency = v_u_1:tra(v_u_1:tra(1) * v_u_36)
                v_u_21.ImageTransparency = v_u_1:tra(v_u_1:tra(1) * v_u_36)
            end;
            if v62 == v_u_4.Passed and v_u_31 then
                v_u_23.ImageTransparency = v_u_1:tra(v_u_1:tra(1) * v_u_36)
                v_u_24.ImageTransparency = v_u_1:tra(v_u_1:tra(1) * v_u_36)
            else
                v_u_23.ImageTransparency = v_u_1:tra(v_u_1:tra(0.25) * v_u_36)
                v_u_24.ImageTransparency = v_u_1:tra(v_u_1:tra(0.25) * v_u_36)
            end;
            v_u_22.Position = UDim2.new(0, v58.X + v60.X, 0, v58.Y + v60.Y)
            local v63 = v56.X * v_u_30
            v_u_22.Size = UDim2.new(0, v63, 0, -(v59.Y - v58.Y))
            if v62 == v_u_4.Holding then
                v_u_22.Position = UDim2.new(0, v58.X + v60.X, 0, v58.Y)
                v_u_22.Size = UDim2.new(0, v63, 0, -(v59.Y - v58.Y) - v60.Y)
            end;
            f_update_body_transparency()
        end;
        v_u_14.update_should_remove = function(_) --[[ Name: update_should_remove ]] --[[ Line: 378 ]]
            --[[ Upvalues: (ref 1): p_u_10, (ref 2): p_u_11 ]]
            return p_u_11:get_time_ms() + p_u_11:get_duration() < p_u_10:get_display_time_active_range_ms():min();
        end;
        v_u_14.get_note_index = function(_) --[[ Name: get_note_index ]] --[[ Line: 383 ]]
            --[[ Upvalues: (ref 1): p_u_12 ]]
            return p_u_12;
        end;
        v_u_14.get_note_loaded_data = function(_) --[[ Name: get_note_loaded_data ]] --[[ Line: 384 ]]
            --[[ Upvalues: (ref 1): p_u_11 ]]
            return p_u_11;
        end;
        v_u_14.update = function(_, p64) --[[ Name: update ]] --[[ Line: 386 ]]
            --[[ Upvalues: (copy 1): f_get_target_scale, (copy 2): f_update_zindex, (ref 3): v_u_27, (ref 4): v_u_2, (ref 5): v_u_28, (ref 6): v_u_25, (ref 7): v_u_26, (copy 8): f_update_fill_color, (copy 9): f_update_body_transparency ]]
            local v65, v66 = f_get_target_scale()
            f_update_zindex(v65 > 1, v66 > 1)
            v_u_27 = v_u_2:expt_sec(v_u_27, v65, 0.5, p64)
            v_u_28 = v_u_2:expt_sec(v_u_28, v66, 0.5, p64)
            v_u_25.Scale = v_u_27
            v_u_26.Scale = v_u_28
            f_update_fill_color()
            f_update_body_transparency()
        end;
        local v_u_67 = v_u_5:new()
        local v_u_68 = v_u_5:new()
        local v_u_69 = v_u_5:new()
        local v_u_70 = v_u_3:new({
            [v_u_8.BoundingBoxIndex.Head] = v_u_67,
            [v_u_8.BoundingBoxIndex.Tail] = v_u_69,
            [v_u_8.BoundingBoxIndex.Body] = v_u_68
        })
        local v_u_71 = v_u_6:new(0, 0)
        v_u_14.get_bounding_sprect_list = function(_) --[[ Name: get_bounding_sprect_list ]] --[[ Line: 414 ]]
            --[[ Upvalues: (copy 1): v_u_67, (ref 2): v_u_20, (ref 3): v_u_8, (ref 4): p_u_9, (copy 5): v_u_69, (ref 6): v_u_23, (copy 7): v_u_71, (ref 8): v_u_22, (copy 9): v_u_68, (copy 10): v_u_70 ]]
            v_u_67:set_centerxy_wid_hei(v_u_20.Position.X.Offset, v_u_20.Position.Y.Offset, v_u_20.Size.X.Offset * v_u_8:get_note_bounding_box_size_multiplier_vec2(p_u_9).X, v_u_20.Size.Y.Offset * v_u_8:get_note_bounding_box_size_multiplier_vec2(p_u_9).Y)
            v_u_69:set_centerxy_wid_hei(v_u_23.Position.X.Offset, v_u_23.Position.Y.Offset, v_u_23.Size.X.Offset * v_u_8:get_note_bounding_box_size_multiplier_vec2(p_u_9).X, v_u_23.Size.Y.Offset * v_u_8:get_note_bounding_box_size_multiplier_vec2(p_u_9).Y)
            v_u_71:set(v_u_22.Position.X.Offset - v_u_22.Size.X.Offset * v_u_22.AnchorPoint.X, v_u_22.Position.Y.Offset - v_u_22.Size.Y.Offset * v_u_22.AnchorPoint.Y)
            v_u_68:set(v_u_71._x, v_u_71._y, v_u_71._x + v_u_22.Size.X.Offset, v_u_71._y + v_u_22.Size.Y.Offset)
            return v_u_70;
        end;
        return v_u_14;
    end
}
v_u_72.new = function(_, p73, p74, p75, p76, p77) --[[ Name: new ]] --[[ Line: 31 ]]
    --[[ Upvalues: (copy 1): v_u_72 ]]
    local v78 = p73._lua_pool:depool("EditorNoteTrackDisplay_NoteHeld")
    if v78 == nil then
        local v79 = v_u_72:_new(p73, p74, p75, p76, p77)
        v79:cons()
        return v79;
    else
        v78:rebind(p73, p74, p75, p76, p77)
        v78:cons()
        return v78;
    end;
end;
return v_u_72;
