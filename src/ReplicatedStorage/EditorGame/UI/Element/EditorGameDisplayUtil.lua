-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:12 PM
-- Cached decompilation

require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_1 = require(game.ReplicatedStorage.Shared.NoteSkinColor)
require(game.ReplicatedStorage.Shared.NoteDisplayMode)
local v_u_2 = require(game.ReplicatedStorage.PlayerInfo.NoteDecalDatabase)
require(game.ReplicatedStorage.Shared.MatchMode)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.BrightnessSettings)
require(game.ReplicatedStorage.Shared.Note2DSettings)
require(game.ReplicatedStorage.Shared.DebugConfig)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPRange)
require(game.ReplicatedStorage.Local.HeldNoteState)
local v7 = {
    ["BoundingBoxIndex"] = {
        ["Head"] = 1,
        ["Tail"] = 2,
        ["Body"] = 3
    },
    ["get_note_decal_info"] = function(_, _) --[[ Name: get_note_decal_info ]] --[[ Line: 29 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        return v_u_2:singleton():get_info_for_id(2);
    end,
    ["get_cursor_preview_assetid"] = function(_) --[[ Name: get_cursor_preview_assetid ]] --[[ Line: 35 ]]
        --[[ Upvalues: (copy 1): v_u_2 ]]
        return v_u_2:singleton():get_info_for_id(1):get_single_note_fill_assetid();
    end,
    ["get_color3_for_track"] = function(_, _, _, p3) --[[ Name: get_color3_for_track ]] --[[ Line: 51 ]]
        --[[ Upvalues: (copy 1): v_u_1 ]]
        local v4, v5, v6
        if p3 then
            v4, v5, v6 = v_u_1:get_default_fever_color():get_rgb()
        else
            v4, v5, v6 = v_u_1:get_default_base_color():get_rgb()
        end;
        return Color3.fromRGB(v4, v5, v6);
    end,
    ["get_base_zindex"] = function(_) --[[ Name: get_base_zindex ]] --[[ Line: 63 ]]
        return 1;
    end,
    ["get_note_decal_render_pool_key"] = function(_) --[[ Name: get_note_decal_render_pool_key ]] --[[ Line: 64 ]]
        return "NoteDecalRender";
    end,
    ["get_held_note_decal_render_pool_key"] = function(_) --[[ Name: get_held_note_decal_render_pool_key ]] --[[ Line: 65 ]]
        return "HeldNoteDecalRender";
    end,
    ["get_held_node_decal_render_slice_pool_key"] = function(_) --[[ Name: get_held_node_decal_render_slice_pool_key ]] --[[ Line: 66 ]]
        return "HeldNoteDecalRender_Slice";
    end,
    ["get_note_hold_body_zindex"] = function(_) --[[ Name: get_note_hold_body_zindex ]] --[[ Line: 68 ]]
        return 6;
    end,
    ["get_unselected_note_zindex"] = function(_) --[[ Name: get_unselected_note_zindex ]] --[[ Line: 69 ]]
        return 8;
    end,
    ["get_selected_note_zindex"] = function(_) --[[ Name: get_selected_note_zindex ]] --[[ Line: 70 ]]
        return 15;
    end
}
local v_u_8 = Vector2.new(0, -13)
v7.get_note_decal_position_offset = function(_, _) --[[ Name: get_note_decal_position_offset ]] --[[ Line: 42 ]]
    --[[ Upvalues: (copy 1): v_u_8 ]]
    return v_u_8;
end;
local v_u_9 = Vector2.new(1, 0.3333333333333333)
v7.get_note_bounding_box_size_multiplier_vec2 = function(_, _) --[[ Name: get_note_bounding_box_size_multiplier_vec2 ]] --[[ Line: 47 ]]
    --[[ Upvalues: (copy 1): v_u_9 ]]
    return v_u_9;
end;
return v7;
