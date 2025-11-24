-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:22:12 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
require(game.ReplicatedStorage.Shared.SPUIChild)
require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_2 = require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_3 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_4 = require(game.ReplicatedStorage.EditorGame.Data.EditorGameData)
require(game.ReplicatedStorage.Shared.WaitForFinish)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Lobby.UI.UIToggleGroup)
local v_u_5 = require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
require(game.ReplicatedStorage.LocalShared.CharacterCulling)
local v_u_6 = require(game.ReplicatedStorage.EditorGame.Data.EditorDifficultyCalculation)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v7 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_8 = nil
local v_u_9 = nil
local v_u_10 = nil
local v_u_11 = nil
local v_u_12 = nil
local v_u_13 = nil
local v_u_14 = nil
local v_u_15 = nil
local v_u_16 = nil
v7:require_client(function() --[[ Line: 34 ]]
    --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_9, (ref 3): v_u_10, (ref 4): v_u_11, (ref 5): v_u_12, (ref 6): v_u_13, (ref 7): v_u_14, (ref 8): v_u_15, (ref 9): v_u_16 ]]
    v_u_8 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_9 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
    v_u_10 = require(game.ReplicatedStorage.EditorGame.UI.Element.EditorNoteTrackDisplay)
    v_u_11 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI_SongProgressSection)
    v_u_12 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI_TimingPointMenu)
    v_u_13 = require(game.ReplicatedStorage.EditorGame.UI.SavedMapInfoListUI)
    v_u_14 = require(game.ReplicatedStorage.Menu.ScreenGuiTextBoxUI)
    v_u_15 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.ValueInputUI)
end)
local v_u_49 = {
    ["note_data_to_osu_string"] = function(_, p17) --[[ Name: note_data_to_osu_string ]] --[[ Line: 224 ]]
        --[[ Upvalues: (copy 1): v_u_4 ]]
        local v18 = p17:get_type()
        local v19 = p17:get_track()
        local v20 = v19 == 1 and 64 or (v19 == 2 and 192 or (v19 == 3 and 320 or 448))
        local v21 = p17:get_time_ms()
        local v22 = v21 + p17:get_duration()
        local v23 = ""
        if v18 == v_u_4.NoteType.Single then
            return v23 .. string.format("%d,%d,%d,1,0,0:0:0:0:\n", v20, 192, v21);
        end;
        if v18 == v_u_4.NoteType.Hold then
            v23 = v23 .. string.format("%d,%d,%d,128,0,%d:0:0:0:0:\n", v20, 192, v21, v22)
        end;
        return v23;
    end,
    ["show_import_song_data"] = function(_, p_u_24, p_u_25, p_u_26) --[[ Name: show_import_song_data ]] --[[ Line: 286 ]]
        --[[ Upvalues: (ref 1): v_u_14, (copy 2): v_u_5, (copy 3): v_u_1, (copy 4): v_u_2, (copy 5): v_u_4, (ref 6): v_u_8, (ref 7): v_u_13 ]]
        p_u_24._menus:push_menu(v_u_14:new(p_u_24):eval(function(p27) --[[ Line: 289 ]]
            p27:get_title_display().Text = "Import Map"
            p27:get_sub_text_display().Text = "Paste Map Data Text:"
            p27:get_text_box().Text = ""
            p27:get_text_box().TextEditable = true
            p27:get_text_box().TextSize = 12
        end):set_okay_button_fn(function(p_u_28) --[[ Line: 297 ]]
            --[[ Upvalues: (ref 1): v_u_5, (ref 2): v_u_1, (ref 3): v_u_2, (ref 4): v_u_4, (copy 5): p_u_24, (ref 6): v_u_8, (copy 7): p_u_25, (ref 8): v_u_13, (copy 9): p_u_26 ]]
            local v_u_29 = v_u_5.CustomMapData:new()
            local v45, v46 = v_u_1:try(function() --[[ Line: 299 ]]
                --[[ Upvalues: (copy 1): p_u_28, (ref 2): v_u_1, (ref 3): v_u_2, (ref 4): v_u_4, (copy 5): v_u_29 ]]
                local v30 = false
                local v31 = 350
                local v32 = false
                for _, v33 in ipairs((string.split(p_u_28:get_text_box().Text, "\n"))) do
                    if v_u_1:string_starts_with(v33, "[TimingPoints]") then
                        v_u_2:puts("TimingPoints section start")
                        v30 = true
                        v32 = false
                    elseif v_u_1:string_starts_with(v33, "[HitObjects]") then
                        v_u_2:puts("HitObjects section start")
                        v30 = false
                        v32 = true
                    elseif #v33 == 0 then
                        v_u_2:puts("Empty line")
                        v30 = false
                        v32 = false
                    elseif v30 then
                        local v34 = string.split(v33, ",")
                        if #v34 >= 2 then
                            local v35 = tonumber(v34[1])
                            local v36 = tonumber(v34[2])
                            if v36 <= 0 then
                                v36 = v31
                            else
                                v31 = v36
                            end;
                            local v37 = v_u_4.TimingPoint:new()
                            v37:set_time_ms(v35)
                            v37:set_beat_length_ms(v36)
                            v_u_29:get_timing_points():push_back(v37)
                        end;
                        v_u_2:puts("TimingPoint[%s]", v33)
                    elseif v32 then
                        local v38 = string.split(v33, ",")
                        if #v38 >= 6 then
                            local v39 = tonumber(v38[1])
                            local v40 = v39 <= 64 and 1 or (v39 <= 192 and 2 or (v39 <= 320 and 3 or 4))
                            local v41 = tonumber(v38[3])
                            local l_Single_0 = v_u_4.NoteType.Single
                            local v42 = 0
                            if v38[4] == "128" then
                                l_Single_0 = v_u_4.NoteType.Hold
                                local v43 = string.split(v38[6], ":")
                                if #v43 >= 1 then
                                    v42 = tonumber(v43[1]) - v41
                                end;
                            end;
                            local v44 = v_u_4.Note:new()
                            v44:set_time_ms(v41)
                            v44:set_type(l_Single_0)
                            v44:set_track(v40)
                            if l_Single_0 == v_u_4.NoteType.Hold then
                                v44:set_duration(v42)
                            end;
                            v_u_29:get_notes():push_back(v44)
                        end;
                    end;
                end;
            end)
            if v45 ~= true then
                v_u_2:warnf("Parse Error: %s", v46.Error)
                return p_u_24._menus:push_menu(v_u_8:new(p_u_24, p_u_24._spui, p_u_24._menus):set_text("Import Map", string.format("Failed to parse map data.")));
            end;
            if v_u_29:get_timing_points():count() == 0 then
                return p_u_24._menus:push_menu(v_u_8:new(p_u_24, p_u_24._spui, p_u_24._menus):set_text("Import Map", "No timing points found in the map data."));
            end;
            if v_u_29:get_notes():count() == 0 then
                return p_u_24._menus:push_menu(v_u_8:new(p_u_24, p_u_24._spui, p_u_24._menus):set_text("Import Map", "No notes found in the map data."));
            end;
            local v47, v48 = v_u_4:validate_note_data_list(v_u_29:get_notes(), p_u_25:get_editor_note_track_display():get_songkey())
            if v47 ~= true then
                return p_u_24._menus:push_menu(v_u_8:new(p_u_24, p_u_24._spui, p_u_24._menus):set_text("Import Map", string.format("Map failed validation: %s", v48)));
            end;
            v_u_13:message_box_confirm(p_u_24, function() --[[ Line: 392 ]]
                --[[ Upvalues: (ref 1): p_u_25, (copy 2): v_u_29, (ref 3): p_u_26 ]]
                p_u_25:set_custom_map_data(v_u_29)
                p_u_25:load_custom_map_note_data()
                p_u_26()
            end, "Confirm", string.format("Import map with %d note(s) and %d timing point(s)?", v_u_29:get_notes():count(), v_u_29:get_timing_points():count()))
        end))
    end
}
v_u_49.show_settings_menu = function(_, p_u_50, p_u_51) --[[ Name: show_settings_menu ]] --[[ Line: 48 ]]
    --[[ Upvalues: (copy 1): v_u_6, (ref 2): v_u_15, (copy 3): v_u_1, (copy 4): v_u_3, (ref 5): v_u_13, (ref 6): v_u_8, (copy 7): v_u_49, (copy 8): v_u_5, (ref 9): v_u_16 ]]
    local v_u_52 = 0
    local function _() --[[ Name: recalc_difficulty ]] --[[ Line: 57 ]]
        --[[ Upvalues: (ref 1): v_u_52, (ref 2): v_u_6, (copy 3): p_u_51 ]]
        v_u_52 = v_u_6:editor_game_data_note_list_calculate_difficulty(p_u_51:get_editor_note_track_display():get_loaded_note_data())
    end;
    v_u_52 = v_u_6:editor_game_data_note_list_calculate_difficulty(p_u_51:get_editor_note_track_display():get_loaded_note_data())
    local v_u_53 = nil
    v_u_53 = p_u_50._menus:push_menu(v_u_15:new(p_u_50, p_u_50._spui, p_u_50._menus, function(p54) --[[ Line: 67 ]]
        --[[ Upvalues: (ref 1): v_u_52, (ref 2): v_u_6, (copy 3): p_u_51 ]]
        p54:set_header_text("Settings")
        p54:get_element_list():push_back("Calculate Difficulty")
        p54:get_element_list():push_back("Keybinds")
        p54:get_element_list():push_back("Clear All Notes")
        p54:get_element_list():push_back("Load Default Song Notes")
        p54:get_element_list():push_back("Export Note Data")
        p54:get_element_list():push_back("Import Note Data")
        v_u_52 = v_u_6:editor_game_data_note_list_calculate_difficulty(p_u_51:get_editor_note_track_display():get_loaded_note_data())
    end, function(p55, p56, p57, _, p58) --[[ Line: 78 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_51, (ref 3): v_u_52, (ref 4): v_u_3 ]]
        if p55 == "Clear All Notes" then
            p56.Text = "Clear All Notes"
            p57.Image = "rbxassetid://2813390949"
            p58:set_select_button_enabled(true)
            p58:set_select_button_text("Clear")
            p58:get_description_display().Text = "Clear all notes from the map."
            return;
        elseif p55 == "Keybinds" then
            p56.Text = "Keybinds"
            p57.Image = v_u_1:get_icon_keybinds_assetid()
            p58:set_select_button_enabled(true)
            p58:get_description_display().Text = "View keybinds."
            return;
        elseif p55 == "Load Default Song Notes" then
            p56.Text = "Load Default Song Notes"
            p57.Image = v_u_1:important_assetid()
            p58:set_select_button_enabled(true)
            p58:set_select_button_text("Load")
            p58:get_description_display().Text = "Reload the default song notes to this map."
            return;
        elseif p55 == "Export Note Data" then
            p56.Text = "Export Note Data"
            p57.Image = v_u_1:get_double_arrow_icon_assetid()
            p58:set_select_button_enabled(true)
            p58:set_select_button_text("Export")
            p58:get_description_display().Text = "Export the note data to text."
            return;
        elseif p55 == "Import Note Data" then
            p56.Text = "Import Note Data"
            p57.Image = v_u_1:get_double_arrow_icon_assetid()
            p58:set_select_button_enabled(true)
            p58:set_select_button_text("Import")
            p58:get_description_display().Text = "Import note data from text."
        elseif p55 == "Calculate Difficulty" then
            p56.Text = string.format("Assigned Difficulty: %s", p_u_51:get_saved_map_info():get_assigned_difficulty_string())
            p57.Image = v_u_1:get_iconhd_trophy()
            p58:set_select_button_enabled(true)
            p58:set_select_button_text("Assign")
            p58:get_description_display().Text = string.format("Estimated: %d (Default: %d)", v_u_52, v_u_3:singleton():get_difficulty_for_key(p_u_51:get_editor_note_track_display():get_songkey()))
        end;
    end, function(p59) --[[ Line: 125 ]]
        --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_50, (copy 3): p_u_51, (ref 4): v_u_53, (ref 5): v_u_8, (ref 6): v_u_49, (ref 7): v_u_52, (ref 8): v_u_5, (ref 9): v_u_16, (ref 10): v_u_1 ]]
        if p59 == nil then
            return;
        elseif p59 == "Clear All Notes" then
            v_u_13:message_box_confirm(p_u_50, function() --[[ Line: 128 ]]
                --[[ Upvalues: (ref 1): p_u_51, (ref 2): p_u_50, (ref 3): v_u_53 ]]
                p_u_51:get_editor_note_track_display():clear_all_notes()
                p_u_50._menus:remove_menu(v_u_53)
            end, "Clear All Notes", "Are you sure you want to clear all notes?")
            return;
        elseif p59 == "Keybinds" then
            p_u_50._menus:push_menu(v_u_8:new(p_u_50, p_u_50._spui, p_u_50._menus):set_text("Keybinds", "Play/Pause: Space\nScroll Forward/Back in Song: Up/W, Down/S or Scroll (Faster: Hold Shift)\nSelect Mode: Q/One (Shift + Click Select for multi-select)\nAdd Mode: E/Two\nDelete Mode: D/Three\nUndo: Z, Redo: X\nZoom: Ctrl + Scroll Up/Down\nTime Snap: Alt + Scroll Up/Down\nToggle Hold Note Length: E/Four (Hold Shift to reverse)\nCopy: C, Paste Mode: V/Five"))
            return;
        elseif p59 == "Load Default Song Notes" then
            v_u_13:message_box_confirm(p_u_50, function() --[[ Line: 152 ]]
                --[[ Upvalues: (ref 1): p_u_51, (ref 2): p_u_50, (ref 3): v_u_53 ]]
                p_u_51:load_songdatabase_note_data()
                p_u_50._menus:remove_menu(v_u_53)
            end, "Load Default Song Notes", "Are you sure you want to reset this map to the default song notes?")
            return;
        elseif p59 == "Export Note Data" then
            v_u_49:show_export_song_data(p_u_50, p_u_51)
            return;
        elseif p59 == "Import Note Data" then
            v_u_49:show_import_song_data(p_u_50, p_u_51, function() --[[ Line: 162 ]]
                --[[ Upvalues: (ref 1): p_u_50, (ref 2): v_u_53 ]]
                p_u_50._menus:remove_menu(v_u_53)
            end)
        elseif p59 == "Calculate Difficulty" then
            local v_u_60 = p_u_51:get_saved_map_info()
            local v61 = v_u_60:get_assigned_difficulty()
            if v_u_60:has_assigned_difficulty() ~= true then
                v61 = v_u_52
            end;
            local v62, v63 = v_u_5.SavedMapInfo:calc_difficulty_get_min_max_assigned_difficulty(v_u_52)
            p_u_50._menus:push_menu(v_u_16:new(p_u_50, p_u_50._spui, p_u_50._menus, v_u_1:clamp(v61, v62, v63), function(p64) --[[ Line: 178 ]]
                --[[ Upvalues: (copy 1): v_u_60 ]]
                v_u_60:set_assigned_difficulty(p64)
            end)):set_value_increment(1):set_reset_value(v_u_52):set_range_min_max(v62, v63):set_title_sub_text("Assign Difficulty", string.format("Estimated Difficulty: %d", v_u_52)):set_value_display_info_fn(function(p65) --[[ Line: 189 ]]
                return tostring(p65), "Difficulty";
            end)
        end;
    end)):set_close_on_element_select(false):set_refresh_on_refocus(true)
end;
local function _(p66) --[[ Name: note_track_to_position_x ]] --[[ Line: 200 ]]
    return p66 == 1 and 64 or (p66 == 2 and 192 or (p66 == 3 and 320 or 448));
end;
local function _(p67) --[[ Name: position_x_to_note_track ]] --[[ Line: 212 ]]
    return p67 <= 64 and 1 or (p67 <= 192 and 2 or (p67 <= 320 and 3 or 4));
end;
v_u_49.show_export_song_data = function(_, p68, p69) --[[ Name: show_export_song_data ]] --[[ Line: 240 ]]
    --[[ Upvalues: (copy 1): v_u_5, (ref 2): v_u_10, (copy 3): v_u_49, (ref 4): v_u_14 ]]
    local v70 = v_u_5.CustomMapData:new()
    v_u_10:copy_editor_note_track_display_data_to_custom_map(p69:get_editor_note_track_display(), v70)
    local v71 = "[TimingPoints]\n"
    for _, v72 in v70:get_timing_points():key_itr() do
        v71 = v71 .. string.format("%d,%.2f,4,1,0,100,1,0\n", v72:get_time_ms(), v72:get_beat_length_ms())
    end;
    local v_u_73 = (v71 .. "\n") .. "[HitObjects]\n"
    for _, v74 in v70:get_notes():key_itr() do
        v_u_73 = v_u_73 .. v_u_49:note_data_to_osu_string(v74)
    end;
    p68._menus:push_menu(v_u_14:new(p68):eval(function(p75) --[[ Line: 273 ]]
        --[[ Upvalues: (ref 1): v_u_73 ]]
        p75:get_title_display().Text = "Export Map"
        p75:get_sub_text_display().Text = "Map Data Text:"
        p75:get_text_box().Text = v_u_73
        p75:get_text_box().TextEditable = false
        p75:get_text_box().TextSize = 12
        p75:select_all_text_box()
    end))
end;
return v_u_49;
