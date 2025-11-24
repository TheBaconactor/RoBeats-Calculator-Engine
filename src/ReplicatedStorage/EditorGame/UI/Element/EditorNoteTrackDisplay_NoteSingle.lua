-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:13 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.NoteSkinColor)
require(game.ReplicatedStorage.Shared.NoteDisplayMode)
require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
require(game.ReplicatedStorage.Shared.SPRange)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPRect)
local v5 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_6 = nil
v5:require_client(function() --[[ Line: 15 ]]
    --[[ Upvalues: (ref 1): v_u_6 ]]
    v_u_6 = require(game.ReplicatedStorage.EditorGame.UI.Element.EditorGameDisplayUtil)
end)
local v_u_43 = {
    ["_new"] = function(_, p_u_7, p_u_8, p_u_9, p_u_10, p_u_11) --[[ Name: _new ]] --[[ Line: 42 ]]
        --[[ Upvalues: (ref 1): v_u_6, (copy 2): v_u_1, (copy 3): v_u_2, (copy 4): v_u_4, (copy 5): v_u_3 ]]
        local v12 = {}
        v12.rebind = function(_, p13, p14, p15, p16, p17) --[[ Name: rebind ]] --[[ Line: 52 ]]
            --[[ Upvalues: (ref 1): p_u_7, (ref 2): p_u_8, (ref 3): p_u_9, (ref 4): p_u_10, (ref 5): p_u_11 ]]
            p_u_7 = p13
            p_u_8 = p14
            p_u_9 = p15
            p_u_10 = p16
            p_u_11 = p17
        end;
        local v_u_18 = nil
        local v_u_19 = nil
        local v_u_20 = 0.85
        local v_u_21 = nil
        local v_u_22 = 1
        local v_u_23 = false
        local v_u_24 = Color3.fromRGB(255, 255, 255)
        local v_u_25 = 1
        local function f_update_fill_color() --[[ Name: update_fill_color ]] --[[ Line: 69 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_18, (ref 3): v_u_24, (ref 4): v_u_6, (ref 5): p_u_7, (ref 6): p_u_9, (ref 7): p_u_8, (ref 8): p_u_10, (ref 9): v_u_1, (ref 10): v_u_25, (ref 11): v_u_19 ]]
            if v_u_23 == true then
                v_u_18.ImageColor3 = v_u_24
            else
                v_u_18.ImageColor3 = v_u_6:get_color3_for_track(p_u_7, p_u_9:get_track(), p_u_8:get_selected_note_index_set():contains(p_u_10))
            end;
            v_u_18.ImageTransparency = v_u_1:tra(v_u_25)
            v_u_19.ImageTransparency = v_u_1:tra(v_u_25)
        end;
        v12.set_custom_color = function(_, p26, p27) --[[ Name: set_custom_color ]] --[[ Line: 79 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24, (copy 3): f_update_fill_color ]]
            local v28 = v_u_23 ~= p26 and true or v_u_24 ~= p27
            v_u_23 = p26
            v_u_24 = p27
            if v28 then
                f_update_fill_color()
            end;
        end;
        v12.set_custom_alpha = function(_, p29) --[[ Name: set_custom_alpha ]] --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): v_u_25, (copy 2): f_update_fill_color ]]
            v_u_25 = p29
            f_update_fill_color()
        end;
        local function _(p30) --[[ Name: update_zindex ]] --[[ Line: 93 ]]
            --[[ Upvalues: (ref 1): v_u_18, (ref 2): v_u_6, (ref 3): v_u_19 ]]
            if p30 then
                v_u_18.ZIndex = v_u_6:get_selected_note_zindex()
                v_u_19.ZIndex = v_u_6:get_selected_note_zindex() + 1
            else
                v_u_18.ZIndex = v_u_6:get_unselected_note_zindex()
                v_u_19.ZIndex = v_u_6:get_unselected_note_zindex() + 1
            end;
        end;
        local function _() --[[ Name: get_target_scale ]] --[[ Line: 103 ]]
            --[[ Upvalues: (ref 1): p_u_8, (ref 2): p_u_10 ]]
            return p_u_8:get_hovered_note_index_set():contains(p_u_10) == true and 1.15 or 1;
        end;
        v12.cons = function(p31) --[[ Name: cons ]] --[[ Line: 113 ]]
            --[[ Upvalues: (ref 1): v_u_23, (ref 2): v_u_24, (ref 3): v_u_25, (ref 4): v_u_20, (ref 5): v_u_22, (ref 6): p_u_9, (ref 7): v_u_6, (ref 8): p_u_7, (ref 9): v_u_18, (ref 10): v_u_1, (ref 11): p_u_10, (ref 12): p_u_11, (ref 13): v_u_21, (ref 14): p_u_8, (ref 15): v_u_19, (copy 16): f_update_fill_color ]]
            v_u_23 = false
            v_u_24 = Color3.fromRGB(255, 255, 255)
            v_u_25 = 1
            v_u_20 = 0.85
            v_u_22 = 1
            local v32 = p_u_9:get_track()
            local v33 = v_u_6:get_note_decal_info(p_u_7)
            v_u_20 = v33:get_note_size_scale()
            v_u_18 = p_u_7._object_pool:depool_key_instance_type(v_u_6:get_note_decal_render_pool_key(), "ImageLabel")
            v_u_18.Visible = true
            v_u_18.Image = v33:get_single_note_fill_assetid(v32)
            v_u_18.BackgroundTransparency = v_u_1:tra(0)
            v_u_18.Name = v_u_1:gen_name(string.format("NoteFill track(%d) index(%d)", v32, p_u_10))
            v_u_18.AnchorPoint = Vector2.new(0.5, 0.5)
            v_u_18.Parent = p_u_11
            v_u_21 = p_u_7._object_pool:depool_key_instance_type("UIScale", "UIScale")
            v_u_22 = p_u_8:get_hovered_note_index_set():contains(p_u_10) == true and 1.15 or 1
            v_u_21.Scale = v_u_22
            v_u_21.Parent = v_u_18
            v_u_19 = p_u_7._object_pool:depool_key_instance_type(v_u_6:get_note_decal_render_pool_key(), "ImageLabel")
            v_u_19.Visible = true
            v_u_19.Image = v33:get_single_note_outline_assetid(v32)
            v_u_19.ImageColor3 = v_u_1:color3(52, 41, 23)
            v_u_19.BackgroundTransparency = v_u_1:tra(0)
            v_u_19.Position = UDim2.new(0, 0, 0, 0)
            v_u_19.Size = UDim2.new(1, 0, 1, 0)
            v_u_19.Name = v_u_1:gen_name("Outline")
            v_u_19.AnchorPoint = Vector2.new(0, 0)
            v_u_19.Parent = v_u_18
            v_u_18.ZIndex = v_u_6:get_unselected_note_zindex()
            v_u_19.ZIndex = v_u_6:get_unselected_note_zindex() + 1
            f_update_fill_color()
            p31:update_position_to_parent_track_display_time()
        end;
        v12.cleanup = function(p34) --[[ Name: cleanup ]] --[[ Line: 160 ]]
            --[[ Upvalues: (ref 1): v_u_21, (ref 2): p_u_7, (ref 3): v_u_18, (ref 4): v_u_6, (ref 5): v_u_19 ]]
            v_u_21.Parent = nil
            v_u_21.Scale = 1
            p_u_7._object_pool:repool("UIScale", v_u_21)
            v_u_21 = nil
            v_u_18.Parent = nil
            p_u_7._object_pool:repool(v_u_6:get_note_decal_render_pool_key(), v_u_18)
            v_u_18 = nil
            v_u_19.Parent = nil
            p_u_7._object_pool:repool(v_u_6:get_note_decal_render_pool_key(), v_u_19)
            v_u_19 = nil
            p_u_7._lua_pool:repool("EditorNoteTrackDisplay_NoteSingle", p34)
            p34:rebind()
        end;
        v12.update_position_to_parent_track_display_time = function(_) --[[ Name: update_position_to_parent_track_display_time ]] --[[ Line: 178 ]]
            --[[ Upvalues: (ref 1): p_u_8, (ref 2): p_u_9, (ref 3): v_u_20, (ref 4): v_u_18, (ref 5): v_u_6, (ref 6): p_u_7 ]]
            local v35, _ = p_u_8:get_editor_display_tracks():get(p_u_9:get_track()):get_track_size_and_position()
            local v36 = v35.X * v_u_20
            v_u_18.Size = UDim2.new(0, v36, 0, v36)
            local v37 = p_u_8:get_time_ms_display_position(p_u_9:get_time_ms(), p_u_9:get_track())
            local v38 = v_u_6:get_note_decal_position_offset(p_u_7)
            v_u_18.Position = UDim2.new(0, v37.X + v38.X, 0, v37.Y + v38.Y)
        end;
        v12.update_should_remove = function(_) --[[ Name: update_should_remove ]] --[[ Line: 189 ]]
            --[[ Upvalues: (ref 1): p_u_8, (ref 2): p_u_9 ]]
            return p_u_9:get_time_ms() < p_u_8:get_display_time_active_range_ms():min();
        end;
        v12.get_note_index = function(_) --[[ Name: get_note_index ]] --[[ Line: 194 ]]
            --[[ Upvalues: (ref 1): p_u_10 ]]
            return p_u_10;
        end;
        v12.get_note_loaded_data = function(_) --[[ Name: get_note_loaded_data ]] --[[ Line: 195 ]]
            --[[ Upvalues: (ref 1): p_u_9 ]]
            return p_u_9;
        end;
        v12.update = function(_, p39) --[[ Name: update ]] --[[ Line: 197 ]]
            --[[ Upvalues: (ref 1): p_u_8, (ref 2): p_u_10, (ref 3): v_u_22, (ref 4): v_u_2, (ref 5): v_u_21, (ref 6): v_u_18, (ref 7): v_u_6, (ref 8): v_u_19, (copy 9): f_update_fill_color ]]
            local v40 = p_u_8:get_hovered_note_index_set():contains(p_u_10) == true and 1.15 or 1
            v_u_22 = v_u_2:expt_sec(v_u_22, v40, 0.5, p39)
            v_u_21.Scale = v_u_22
            if v40 > 1 then
                v_u_18.ZIndex = v_u_6:get_selected_note_zindex()
                v_u_19.ZIndex = v_u_6:get_selected_note_zindex() + 1
            else
                v_u_18.ZIndex = v_u_6:get_unselected_note_zindex()
                v_u_19.ZIndex = v_u_6:get_unselected_note_zindex() + 1
            end;
            f_update_fill_color()
        end;
        local v_u_41 = v_u_4:new()
        local v_u_42 = v_u_3:new({
            [v_u_6.BoundingBoxIndex.Head] = v_u_41
        })
        v12.get_bounding_sprect_list = function(_) --[[ Name: get_bounding_sprect_list ]] --[[ Line: 214 ]]
            --[[ Upvalues: (copy 1): v_u_41, (ref 2): v_u_18, (ref 3): v_u_6, (ref 4): p_u_7, (copy 5): v_u_42 ]]
            v_u_41:set_centerxy_wid_hei(v_u_18.Position.X.Offset, v_u_18.Position.Y.Offset, v_u_18.Size.X.Offset * v_u_6:get_note_bounding_box_size_multiplier_vec2(p_u_7).X, v_u_18.Size.Y.Offset * v_u_6:get_note_bounding_box_size_multiplier_vec2(p_u_7).Y)
            return v_u_42;
        end;
        return v12;
    end
}
v_u_43.new = function(_, p44, p45, p46, p47, p48) --[[ Name: new ]] --[[ Line: 24 ]]
    --[[ Upvalues: (copy 1): v_u_43 ]]
    local v49 = p44._lua_pool:depool("EditorNoteTrackDisplay_NoteSingle")
    if v49 == nil then
        local v50 = v_u_43:_new(p44, p45, p46, p47, p48)
        v50:cons()
        return v50;
    else
        v49:rebind(p44, p45, p46, p47, p48)
        v49:cons()
        return v49;
    end;
end;
return v_u_43;
