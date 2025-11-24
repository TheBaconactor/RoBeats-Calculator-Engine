-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:43 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_7 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_10 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_11 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.Shared.NoteSkinColor)
local v_u_12 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_13 = require(game.ReplicatedStorage.Lobby.UI.UIToggleGroup)
require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_14 = require(game.ReplicatedStorage.Lobby.UI.NoteColorSelectUI.SmallNoteColor)
local v_u_15 = require(game.ReplicatedStorage.Lobby.UI.NoteColorSelectUI.SmallNoteColorDisplay)
local v_u_16 = require(game.ReplicatedStorage.Lobby.UI.NoteColorSelectUI.TrackColorDisplay)
local v17 = {}
local v_u_18 = {
    ["BaseColor"] = 1,
    ["FeverColor"] = 2
}
v17.new = function(_, p_u_19, p_u_20, p_u_21, p_u_22) --[[ Name: new ]] --[[ Line: 33 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_18, (copy 3): v_u_2, (copy 4): v_u_1, (copy 5): v_u_10, (copy 6): v_u_6, (copy 7): v_u_5, (copy 8): v_u_8, (copy 9): v_u_14, (copy 10): v_u_15, (copy 11): v_u_16, (copy 12): v_u_13, (copy 13): v_u_3, (copy 14): v_u_12, (copy 15): v_u_7, (copy 16): v_u_11, (copy 17): v_u_9 ]]
    local v_u_23 = v_u_4:new(p_u_20, p_u_21)
    local v_u_24 = nil
    v_u_23.get_obj = function(_) --[[ Name: get_obj ]] --[[ Line: 37 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24;
    end;
    local v_u_25 = 1
    local v_u_26 = 1
    local l_BaseColor_0 = v_u_18.BaseColor
    v_u_23.is_basecolor_mode = function(_) --[[ Name: is_basecolor_mode ]] --[[ Line: 43 ]]
        --[[ Upvalues: (ref 1): l_BaseColor_0, (ref 2): v_u_18 ]]
        return l_BaseColor_0 == v_u_18.BaseColor;
    end;
    v_u_23.is_fever_mode = function(_) --[[ Name: is_fever_mode ]] --[[ Line: 44 ]]
        --[[ Upvalues: (ref 1): l_BaseColor_0, (ref 2): v_u_18 ]]
        return l_BaseColor_0 == v_u_18.FeverColor;
    end;
    local v_u_27 = v_u_2:new()
    local v_u_28 = v_u_2:new()
    local v_u_29 = -1
    v_u_23.has_focused_track = function(_) --[[ Name: has_focused_track ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29 ~= -1;
    end;
    v_u_23.get_focused_track = function(_) --[[ Name: get_focused_track ]] --[[ Line: 51 ]]
        --[[ Upvalues: (ref 1): v_u_29 ]]
        return v_u_29;
    end;
    local v_u_30 = false
    v_u_23.is_default = function(_) --[[ Name: is_default ]] --[[ Line: 53 ]]
        --[[ Upvalues: (ref 1): v_u_30 ]]
        return v_u_30;
    end;
    local function f_get_default_dict() --[[ Name: get_default_dict ]] --[[ Line: 55 ]]
        --[[ Upvalues: (ref 1): v_u_2 ]]
        return v_u_2:new({
            0,
            0,
            0,
            0,
            0
        });
    end;
    local v_u_31 = v_u_2:new({
        0,
        0,
        0,
        0,
        0
    })
    local v_u_32 = v_u_2:new({
        0,
        0,
        0,
        0,
        0
    })
    local v_u_33 = v_u_2:new()
    local v_u_34 = v_u_2:new()
    local function f_reset_trackid_to_base_and_fever_smnote_to_track_spent() --[[ Name: reset_trackid_to_base_and_fever_smnote_to_track_spent ]] --[[ Line: 60 ]]
        --[[ Upvalues: (copy 1): v_u_33, (copy 2): f_get_default_dict, (copy 3): v_u_34 ]]
        for v35 = 1, 4 do
            v_u_33:add(v35, f_get_default_dict())
            v_u_34:add(v35, f_get_default_dict())
        end;
    end;
    f_reset_trackid_to_base_and_fever_smnote_to_track_spent()
    v_u_23.get_small_note_to_base_spent_dict = function(_) --[[ Name: get_small_note_to_base_spent_dict ]] --[[ Line: 68 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        return v_u_31;
    end;
    v_u_23.get_small_note_to_fever_spent_dict = function(_) --[[ Name: get_small_note_to_fever_spent_dict ]] --[[ Line: 69 ]]
        --[[ Upvalues: (ref 1): v_u_32 ]]
        return v_u_32;
    end;
    v_u_23.get_trackid_base_to_small_note_to_track_spend_dict = function(_) --[[ Name: get_trackid_base_to_small_note_to_track_spend_dict ]] --[[ Line: 70 ]]
        --[[ Upvalues: (copy 1): v_u_33 ]]
        return v_u_33;
    end;
    v_u_23.get_trackid_fever_to_small_note_to_track_spend_dict = function(_) --[[ Name: get_trackid_fever_to_small_note_to_track_spend_dict ]] --[[ Line: 71 ]]
        --[[ Upvalues: (copy 1): v_u_34 ]]
        return v_u_34;
    end;
    local v_u_36 = nil
    local v_u_37 = nil
    local v_u_38 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 77 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_1, (ref 3): v_u_10, (copy 4): v_u_23, (copy 5): p_u_19, (ref 6): v_u_6, (ref 7): v_u_5, (copy 8): p_u_20, (ref 9): v_u_8, (copy 10): p_u_21, (ref 11): v_u_30, (copy 12): v_u_27, (ref 13): v_u_14, (ref 14): v_u_15, (copy 15): v_u_28, (ref 16): v_u_16, (ref 17): v_u_36, (ref 18): v_u_13, (ref 19): v_u_3, (ref 20): v_u_29, (ref 21): v_u_37, (ref 22): v_u_18, (ref 23): l_BaseColor_0, (ref 24): v_u_38 ]]
        v_u_24 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Util.NoteColorSelectV2UI:Clone()
        v_u_24.Name = v_u_1:gen_name(v_u_24.Name)
        v_u_24.Parent = v_u_10:get_world_ui_folder()
        v_u_23._native_size = v_u_24.PrimaryPart.Size
        v_u_23._size = v_u_23._native_size
        v_u_23:add_cycle_element(p_u_19, 1, v_u_6:new(v_u_5:new(v_u_23, v_u_24.PrimaryPart, v_u_24.BackButtonSurface), p_u_20, function() --[[ Line: 88 ]]
            --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_8, (ref 3): p_u_21, (ref 4): v_u_23 ]]
            p_u_19._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
            p_u_21:remove_menu(v_u_23)
        end))
        v_u_23:add_cycle_element(p_u_19, 1, v_u_6:new(v_u_5:new(v_u_23, v_u_24.PrimaryPart, v_u_24.ResetToDefaultButton), p_u_20, function() --[[ Line: 97 ]]
            --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_8, (ref 3): v_u_30, (ref 4): v_u_23 ]]
            p_u_19._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            v_u_30 = true
            v_u_23:reset()
        end))
        local l_Frame_0 = v_u_24.PrimaryPart.SurfaceGui.Frame
        v_u_27:add(v_u_14.Red, v_u_15:new(v_u_23, p_u_19, v_u_14.Red, l_Frame_0.NoteRedDisplay, v_u_24.Arrows.RedNoteUpArrow, v_u_24.Arrows.RedNoteDownArrow))
        v_u_27:add(v_u_14.Green, v_u_15:new(v_u_23, p_u_19, v_u_14.Green, l_Frame_0.NoteGreenDisplay, v_u_24.Arrows.GreenNoteUpArrow, v_u_24.Arrows.GreenNoteDownArrow))
        v_u_27:add(v_u_14.Blue, v_u_15:new(v_u_23, p_u_19, v_u_14.Blue, l_Frame_0.NoteBlueDisplay, v_u_24.Arrows.BlueNoteUpArrow, v_u_24.Arrows.BlueNoteDownArrow))
        v_u_27:add(v_u_14.Orange, v_u_15:new(v_u_23, p_u_19, v_u_14.Orange, l_Frame_0.NoteOrangeDisplay, v_u_24.Arrows.OrangeNoteUpArrow, v_u_24.Arrows.OrangeNoteDownArrow))
        v_u_27:add(v_u_14.Purple, v_u_15:new(v_u_23, p_u_19, v_u_14.Purple, l_Frame_0.NotePurpleDisplay, v_u_24.Arrows.PurpleNoteUpArrow, v_u_24.Arrows.PurpleNoteDownArrow))
        v_u_28:add(1, v_u_16:new(v_u_23, p_u_19, 1, l_Frame_0.ColorPreviewTrack1))
        v_u_28:add(2, v_u_16:new(v_u_23, p_u_19, 2, l_Frame_0.ColorPreviewTrack2))
        v_u_28:add(3, v_u_16:new(v_u_23, p_u_19, 3, l_Frame_0.ColorPreviewTrack3))
        v_u_28:add(4, v_u_16:new(v_u_23, p_u_19, 4, l_Frame_0.ColorPreviewTrack4))
        v_u_36 = v_u_13:new(v_u_3:new():push_back_table_list({
            v_u_24.Track1Button,
            v_u_24.Track2Button,
            v_u_24.Track3Button,
            v_u_24.Track4Button
        }), v_u_3:new():push_back_table_list({
            1,
            2,
            3,
            4
        }), function(p39) --[[ Line: 154 ]]
            --[[ Upvalues: (ref 1): v_u_29, (ref 2): v_u_23 ]]
            if v_u_29 == p39 then
                v_u_29 = -1
            else
                v_u_29 = p39
            end;
            v_u_23:update_visual()
        end, function() --[[ Line: 162 ]]
            --[[ Upvalues: (ref 1): v_u_29 ]]
            return v_u_29;
        end, v_u_23, v_u_24.PrimaryPart, p_u_19, p_u_20)
        v_u_37 = v_u_13:new(v_u_3:new():push_back_table_list({ v_u_24.BaseColorButton, v_u_24.FeverColorButton }), v_u_3:new():push_back_table_list({ v_u_18.BaseColor, v_u_18.FeverColor }), function(p40) --[[ Line: 171 ]]
            --[[ Upvalues: (ref 1): l_BaseColor_0, (ref 2): v_u_29, (ref 3): v_u_23 ]]
            l_BaseColor_0 = p40
            v_u_29 = -1
            v_u_23:update_visual()
        end, function() --[[ Line: 176 ]]
            --[[ Upvalues: (ref 1): l_BaseColor_0 ]]
            return l_BaseColor_0;
        end, v_u_23, v_u_24.PrimaryPart, p_u_19, p_u_20)
        v_u_38 = v_u_23:add_cycle_element(p_u_19, 1, v_u_6:new(v_u_5:new(v_u_23, v_u_24.PrimaryPart, v_u_24.AcceptButton), p_u_20, function() --[[ Line: 185 ]]
            --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_8, (ref 3): v_u_23 ]]
            p_u_19._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN_LONG)
            v_u_23:accept_button_pressed()
        end))
        v_u_23:update_visual()
        v_u_23:transition_update_visual(0)
        v_u_23:layout()
    end;
    v_u_23.reset = function(p41) --[[ Name: reset ]] --[[ Line: 197 ]]
        --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_2, (ref 3): v_u_32, (copy 4): f_reset_trackid_to_base_and_fever_smnote_to_track_spent, (ref 5): v_u_29, (ref 6): l_BaseColor_0, (ref 7): v_u_18 ]]
        v_u_31 = v_u_2:new({
            0,
            0,
            0,
            0,
            0
        })
        v_u_32 = v_u_2:new({
            0,
            0,
            0,
            0,
            0
        })
        f_reset_trackid_to_base_and_fever_smnote_to_track_spent()
        v_u_29 = -1
        l_BaseColor_0 = v_u_18.BaseColor
        p41:update_visual()
    end;
    local function f_write_spend_changed_to_dict(p42, p43, p44) --[[ Name: write_spend_changed_to_dict ]] --[[ Line: 206 ]]
        --[[ Upvalues: (ref 1): v_u_12, (ref 2): v_u_7 ]]
        local v45 = 0
        if p44:contains(p42) then
            v_u_12:is_int(p44:get(p42))
            v45 = p44:get(p42)
        else
            v_u_7:warnf("dict does not contain small_note_color(%d) spend_Value(%d)", p42, p43)
        end;
        if v45 + p43 >= 0 then
            p44:add(p42, v45 + p43)
        end;
    end;
    v_u_23.note_spend_changed = function(p46, p47, p48) --[[ Name: note_spend_changed ]] --[[ Line: 219 ]]
        --[[ Upvalues: (ref 1): v_u_30, (ref 2): l_BaseColor_0, (ref 3): v_u_18, (copy 4): f_write_spend_changed_to_dict, (copy 5): v_u_33, (ref 6): v_u_29, (ref 7): v_u_31, (copy 8): v_u_34, (ref 9): v_u_32 ]]
        v_u_30 = false
        if l_BaseColor_0 == v_u_18.BaseColor then
            if p46:has_focused_track() then
                f_write_spend_changed_to_dict(p47, p48, v_u_33:get(v_u_29))
            else
                f_write_spend_changed_to_dict(p47, p48, v_u_31)
            end;
        elseif l_BaseColor_0 == v_u_18.FeverColor then
            if p46:has_focused_track() then
                f_write_spend_changed_to_dict(p47, p48, v_u_34:get(v_u_29))
            else
                f_write_spend_changed_to_dict(p47, p48, v_u_32)
            end;
        end;
        p46:update_visual()
    end;
    local function f_calc_spent_count_for_smnote_type(p49) --[[ Name: calc_spent_count_for_smnote_type ]] --[[ Line: 238 ]]
        --[[ Upvalues: (copy 1): f_write_spend_changed_to_dict, (ref 2): v_u_31, (ref 3): v_u_32, (copy 4): v_u_33, (copy 5): v_u_34 ]]
        f_write_spend_changed_to_dict(p49, 0, v_u_31)
        f_write_spend_changed_to_dict(p49, 0, v_u_32)
        for v50 = 1, 4 do
            f_write_spend_changed_to_dict(p49, 0, v_u_33:get(v50))
            f_write_spend_changed_to_dict(p49, 0, v_u_34:get(v50))
        end;
        local v51 = v_u_31:get(p49) + v_u_32:get(p49)
        for v52 = 1, 4 do
            v51 = v51 + v_u_33:get(v52):get(p49) + v_u_34:get(v52):get(p49)
        end;
        return v51;
    end;
    v_u_23.is_unchanged = function(p53) --[[ Name: is_unchanged ]] --[[ Line: 254 ]]
        --[[ Upvalues: (copy 1): v_u_27, (copy 2): f_calc_spent_count_for_smnote_type, (copy 3): p_u_19 ]]
        if p53:is_default() then
            return false;
        end;
        local v54 = 0
        for v55, _ in v_u_27:key_itr() do
            v54 = v54 + f_calc_spent_count_for_smnote_type(v55)
        end;
        p_u_19._player_blob_manager:get_player_blob()
        return v54 == 0;
    end;
    v_u_23.update_visual = function(p56) --[[ Name: update_visual ]] --[[ Line: 264 ]]
        --[[ Upvalues: (copy 1): v_u_28, (copy 2): v_u_27, (copy 3): f_calc_spent_count_for_smnote_type, (ref 4): v_u_36, (ref 5): v_u_37, (ref 6): v_u_38 ]]
        for _, v57 in v_u_28:key_itr() do
            v57:update_display_color()
        end;
        for v58, v59 in v_u_27:key_itr() do
            v59:set_spent_count((f_calc_spent_count_for_smnote_type(v58)))
        end;
        v_u_36:update_displays()
        v_u_37:update_displays()
        v_u_38:set_visible(p56:is_unchanged() ~= true)
    end;
    v_u_23.accept_button_pressed = function(p_u_60) --[[ Name: accept_button_pressed ]] --[[ Line: 295 ]]
        --[[ Upvalues: (ref 1): v_u_38, (copy 2): v_u_28, (copy 3): p_u_21, (ref 4): v_u_11, (copy 5): p_u_19, (copy 6): p_u_20, (ref 7): v_u_9, (ref 8): v_u_30 ]]
        v_u_38:set_visible(false)
        local v_u_61 = {}
        local v_u_62 = {}
        for v63, v64 in v_u_28:key_itr() do
            v_u_61[v63] = v64:calc_display_color(p_u_60:is_default(), false):to_int32()
            v_u_62[v63] = v64:calc_display_color(p_u_60:is_default(), true):to_int32()
        end;
        local v_u_65 = p_u_21:push_menu(v_u_11:new(p_u_19, p_u_20, p_u_21):set_text("Saving...", "Please wait..."):set_close_button_visible(false))
        local function _() --[[ Name: submit_color_changed ]] --[[ Line: 305 ]]
            --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_9, (ref 3): p_u_21, (copy 4): v_u_65, (ref 5): v_u_11, (ref 6): p_u_20, (copy 7): p_u_60, (ref 8): v_u_30, (copy 9): v_u_61, (copy 10): v_u_62 ]]
            p_u_19._evt:wait_on_event_once(v_u_9.EVT_Crafting_CraftNoteColorServerResponse, function(p66, p67) --[[ Line: 306 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_65, (ref 3): v_u_11, (ref 4): p_u_19, (ref 5): p_u_20, (ref 6): p_u_60, (ref 7): v_u_30 ]]
                if p66 == true then
                    p_u_19._player_blob_manager:do_sync(function() --[[ Line: 313 ]]
                        --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_65, (ref 3): p_u_60, (ref 4): v_u_30 ]]
                        p_u_21:remove_menu(v_u_65)
                        p_u_21:remove_menu(p_u_60)
                        v_u_30 = false
                        p_u_60:reset()
                    end)
                else
                    p_u_21:remove_menu(v_u_65)
                    p_u_21:push_menu(v_u_11:new(p_u_19, p_u_20, p_u_21):set_text("Error", p67))
                end;
            end)
            p_u_19._evt:fire_event_to_server(v_u_9.EVT_Crafting_CraftNoteColorClientRequest, v_u_61, v_u_62)
        end;
        if p_u_19._player_settings_manager:has_changes() then
            p_u_19._player_settings_manager:save_changes_to_playerblob(p_u_19, function() --[[ Line: 328 ]]
                --[[ Upvalues: (ref 1): p_u_19, (ref 2): v_u_9, (ref 3): p_u_21, (copy 4): v_u_65, (ref 5): v_u_11, (ref 6): p_u_20, (copy 7): p_u_60, (ref 8): v_u_30, (copy 9): v_u_61, (copy 10): v_u_62 ]]
                p_u_19._player_settings_manager:clear_changes()
                p_u_19._evt:wait_on_event_once(v_u_9.EVT_Crafting_CraftNoteColorServerResponse, function(p68, p69) --[[ Line: 306 ]]
                    --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_65, (ref 3): v_u_11, (ref 4): p_u_19, (ref 5): p_u_20, (ref 6): p_u_60, (ref 7): v_u_30 ]]
                    if p68 == true then
                        p_u_19._player_blob_manager:do_sync(function() --[[ Line: 313 ]]
                            --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_65, (ref 3): p_u_60, (ref 4): v_u_30 ]]
                            p_u_21:remove_menu(v_u_65)
                            p_u_21:remove_menu(p_u_60)
                            v_u_30 = false
                            p_u_60:reset()
                        end)
                    else
                        p_u_21:remove_menu(v_u_65)
                        p_u_21:push_menu(v_u_11:new(p_u_19, p_u_20, p_u_21):set_text("Error", p69))
                    end;
                end)
                p_u_19._evt:fire_event_to_server(v_u_9.EVT_Crafting_CraftNoteColorClientRequest, v_u_61, v_u_62)
            end)
        else
            p_u_19._evt:wait_on_event_once(v_u_9.EVT_Crafting_CraftNoteColorServerResponse, function(p70, p71) --[[ Line: 306 ]]
                --[[ Upvalues: (ref 1): p_u_21, (copy 2): v_u_65, (ref 3): v_u_11, (ref 4): p_u_19, (ref 5): p_u_20, (copy 6): p_u_60, (ref 7): v_u_30 ]]
                if p70 == true then
                    p_u_19._player_blob_manager:do_sync(function() --[[ Line: 313 ]]
                        --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_65, (ref 3): p_u_60, (ref 4): v_u_30 ]]
                        p_u_21:remove_menu(v_u_65)
                        p_u_21:remove_menu(p_u_60)
                        v_u_30 = false
                        p_u_60:reset()
                    end)
                else
                    p_u_21:remove_menu(v_u_65)
                    p_u_21:push_menu(v_u_11:new(p_u_19, p_u_20, p_u_21):set_text("Error", p71))
                end;
            end)
            p_u_19._evt:fire_event_to_server(v_u_9.EVT_Crafting_CraftNoteColorClientRequest, v_u_61, v_u_62)
        end;
    end;
    v_u_23.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 337 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_24 ]]
        if p_u_22 then
            p_u_22()
        end;
        v_u_24:Destroy()
    end;
    v_u_23.behaviour_update = function(p72, p73, _) --[[ Name: behaviour_update ]] --[[ Line: 342 ]]
        --[[ Upvalues: (copy 1): p_u_19 ]]
        p72:behaviour_update_base(p73, p_u_19)
    end;
    v_u_23.layout = function(p74) --[[ Name: layout ]] --[[ Line: 346 ]]
        --[[ Upvalues: (copy 1): p_u_20, (ref 2): v_u_26, (ref 3): v_u_24 ]]
        p74:opt_rescale_to_max_nxy(p_u_20, 0.8, 0.8, v_u_26)
        local v75, v76 = p74:opt_update_cframe_params(p_u_20, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p74:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v75 == true then
            v_u_24:SetPrimaryPartCFrame(v76)
        end;
    end;
    v_u_23.set_alpha = function(_, p77) --[[ Name: set_alpha ]] --[[ Line: 358 ]]
        --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_1, (ref 3): v_u_24 ]]
        if v_u_25 ~= p77 then
            v_u_25 = p77
            v_u_1:r_set_alpha(v_u_24, v_u_25)
        end;
    end;
    v_u_23.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 364 ]]
        --[[ Upvalues: (ref 1): v_u_25 ]]
        return v_u_25;
    end;
    v_u_23.set_scale = function(_, p78) --[[ Name: set_scale ]] --[[ Line: 365 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        v_u_26 = p78
    end;
    v_u_23.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 366 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26;
    end;
    v_u_23.get_native_size = function(p79) --[[ Name: get_native_size ]] --[[ Line: 368 ]]
        return p79._native_size;
    end;
    v_u_23.get_size = function(p80) --[[ Name: get_size ]] --[[ Line: 371 ]]
        return p80._size;
    end;
    v_u_23.set_size = function(p81, p82) --[[ Name: set_size ]] --[[ Line: 374 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        p81._size = p82
        v_u_24.PrimaryPart.Size = Vector3.new(p82.X, p82.Y, 0)
    end;
    v_u_23.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 378 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24.PrimaryPart.Position;
    end;
    v_u_23.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 381 ]]
        --[[ Upvalues: (ref 1): v_u_24 ]]
        return v_u_24.PrimaryPart.SurfaceGui;
    end;
    v_u_23.set_showing = function(_, p83) --[[ Name: set_showing ]] --[[ Line: 384 ]]
        --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_10 ]]
        if p83 then
            v_u_24.Parent = v_u_10:get_world_ui_folder()
        else
            v_u_24.Parent = nil
        end;
    end;
    f_cons()
    return v_u_23;
end;
return v17;
