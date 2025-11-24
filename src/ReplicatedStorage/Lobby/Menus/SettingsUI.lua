-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:42 PM
-- Time elapsed: 24 milliseconds

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_7 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.UIToggleGroup)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_11 = require(game.ReplicatedStorage.Shared.PlayerSettings)
local v_u_12 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_13 = require(game.ReplicatedStorage.Shared.BrightnessSettings)
require(game.ReplicatedStorage.Shared.AssertType)
local v_u_14 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_15 = require(game.ReplicatedStorage.LocalShared.CharacterCulling)
local v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
require(game.ReplicatedStorage.Shared.NoteDisplayMode)
require(game.ReplicatedStorage.Shared.Note2DSettings)
local v_u_17 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
require(game.ReplicatedStorage.Shared.InputUtil)
local v18 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_19 = require(game.ReplicatedStorage.Shared.ModelLoadDB)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local s_Stats_0 = game:GetService("Stats")
require(game.ReplicatedStorage.Lobby.Menus.KeyBindsUI)
local v_u_20 = require(game.ReplicatedStorage.Lobby.Menus.TitleSelectUI)
require(game.ReplicatedStorage.Lobby.Menus.ValueInputUI)
local v_u_21 = require(game.ReplicatedStorage.LocalShared.LocalSharedSettingsUIUtil)
local v_u_22 = require(game.ReplicatedStorage.LocalShared.LocalFeverIconUtil)
local v_u_23 = require(game.ReplicatedStorage.PreviewGame.PreviewGameStartupMenu)
require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
require(game.ReplicatedStorage.EditorGame.Data.EditorExportData)
local v24 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_25 = nil
local v_u_26 = nil
local v_u_27 = nil
local v_u_28 = nil
local v_u_29 = nil
local v_u_30 = nil
local v_u_31 = nil
v24:require_client(function() --[[ Line: 47 ]]
    --[[ Upvalues: (ref 1): v_u_25, (ref 2): v_u_26, (ref 3): v_u_27, (ref 4): v_u_28, (ref 5): v_u_29, (ref 6): v_u_30, (ref 7): v_u_31 ]]
    v_u_25 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITabController_AllMySongs)
    v_u_26 = require(game.ReplicatedStorage.Lobby.Menus.NoteColorSelectV2UI)
    v_u_27 = require(game.ReplicatedStorage.Lobby.Menus.Event.ListeningPartyPreviewUI)
    v_u_28 = require(game.ReplicatedStorage.EditorGame.UI.EditorGameUI)
    v_u_29 = require(game.ReplicatedStorage.Lobby.Menus.SongSelectV3UI)
    v_u_30 = require(game.ReplicatedStorage.EditorGame.UI.SavedMapInfoListUI)
    v_u_31 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
end)
local v_u_32 = {
    ["get_restore_menu_name"] = function(_) --[[ Name: get_restore_menu_name ]] --[[ Line: 62 ]]
        return "SettingsUI";
    end
}
v_u_32.new = function(_, p_u_33, p_u_34, p_u_35) --[[ Name: new ]] --[[ Line: 64 ]]
    --[[ Upvalues: (copy 1): v_u_4, (copy 2): v_u_32, (copy 3): v_u_3, (copy 4): v_u_1, (copy 5): v_u_9, (copy 6): v_u_6, (copy 7): v_u_5, (copy 8): v_u_8, (copy 9): v_u_20, (copy 10): v_u_22, (copy 11): v_u_14, (copy 12): v_u_23, (ref 13): v_u_26, (copy 14): v_u_21, (copy 15): v_u_12, (ref 16): v_u_31, (copy 17): v_u_10, (copy 18): v_u_11, (copy 19): v_u_13, (copy 20): v_u_17, (copy 21): v_u_15, (ref 22): v_u_25 ]]
    local v_u_36 = v_u_4:new(p_u_34, p_u_35)
    v_u_36.get_restore_name = function(_) --[[ Name: get_restore_name ]] --[[ Line: 66 ]]
        --[[ Upvalues: (ref 1): v_u_32 ]]
        return v_u_32:get_restore_menu_name();
    end;
    local v_u_37 = nil
    local v_u_38 = 1
    local v_u_39 = 1
    local v_u_40 = v_u_3:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 75 ]]
        --[[ Upvalues: (ref 1): v_u_37, (ref 2): v_u_1, (ref 3): v_u_9, (copy 4): v_u_36, (copy 5): p_u_33, (ref 6): v_u_6, (ref 7): v_u_5, (copy 8): p_u_34, (ref 9): v_u_8, (copy 10): p_u_35, (ref 11): v_u_20, (ref 12): v_u_22, (ref 13): v_u_14, (ref 14): v_u_23, (ref 15): v_u_26, (ref 16): v_u_21, (ref 17): v_u_12, (ref 18): v_u_32, (ref 19): v_u_31 ]]
        v_u_37 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.SettingsUI:Clone()
        v_u_37.Name = v_u_1:gen_name(v_u_37.Name)
        v_u_37.Parent = v_u_9:get_world_ui_folder()
        v_u_36._native_size = v_u_37.PrimaryPart.Size
        v_u_36._size = v_u_36._native_size
        v_u_36:add_cycle_element(p_u_33, 1, v_u_6:new(v_u_5:new(v_u_36, v_u_37.PrimaryPart, v_u_37.BackButtonSurface), p_u_34, function() --[[ Line: 86 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): p_u_33, (ref 3): v_u_8 ]]
            v_u_36:close_action()
            p_u_33._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
        end))
        v_u_36:add_cycle_element(p_u_33, 1, v_u_6:new(v_u_5:new(v_u_36, v_u_37.PrimaryPart, v_u_37.TitleSelectButton), p_u_34, function() --[[ Line: 95 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_8, (ref 3): p_u_35, (ref 4): v_u_20, (ref 5): p_u_34 ]]
            p_u_33._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            p_u_35:push_menu(v_u_20:new(p_u_33, p_u_34, p_u_35))
        end)):set_auto_zoffset_behaviour(true)
        local l_Icon_0 = v_u_37.IconSelectButton.SurfaceGui.Frame.Icon
        local function _() --[[ Name: update_fevericon_display ]] --[[ Line: 102 ]]
            --[[ Upvalues: (copy 1): l_Icon_0, (ref 2): v_u_22, (ref 3): p_u_33 ]]
            l_Icon_0.Image = v_u_22:get_player_fevericon_assetid(p_u_33)
        end;
        l_Icon_0.Image = v_u_22:get_player_fevericon_assetid(p_u_33)
        v_u_36:add_cycle_element(p_u_33, 1, v_u_6:new(v_u_5:new(v_u_36, v_u_37.PrimaryPart, v_u_37.IconSelectButton), p_u_34, function() --[[ Line: 109 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_8, (ref 3): v_u_22, (copy 4): l_Icon_0 ]]
            p_u_33._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            v_u_22:show_fever_icon_list_ui(p_u_33, function() --[[ Line: 111 ]]
                --[[ Upvalues: (ref 1): l_Icon_0, (ref 2): v_u_22, (ref 3): p_u_33 ]]
                l_Icon_0.Image = v_u_22:get_player_fevericon_assetid(p_u_33)
            end)
        end)):set_auto_zoffset_behaviour(true)
        v_u_36:add_cycle_element(p_u_33, 1, v_u_6:new(v_u_5:new(v_u_36, v_u_37.PrimaryPart, v_u_37.NoteColorsButton), p_u_34, function() --[[ Line: 120 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_8, (ref 3): v_u_14, (ref 4): v_u_23, (ref 5): p_u_35, (ref 6): v_u_26, (ref 7): p_u_34 ]]
            p_u_33._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            if v_u_14.NoteDisplayGoToPreviewGame == true then
                return p_u_33._spectate_manager:start_preview_game(v_u_23.NoteColor);
            end;
            p_u_35:push_menu(v_u_26:new(p_u_33, p_u_34, p_u_35))
        end)):set_auto_zoffset_behaviour(true)
        local v41 = v_u_6:button_bind_anim_toggle(v_u_21:create_keybinds_button(p_u_33, v_u_36, v_u_37, v_u_37.KeybindsButton), function() --[[ Line: 131 ]]
            --[[ Upvalues: (ref 1): v_u_36 ]]
            return v_u_36:get_alpha();
        end)
        if v_u_1:is_mobile() then
            v41:set_toggle(false)
        end;
        v_u_21:create_note_display_settings_button(p_u_33, v_u_37, v_u_36, v_u_37.NoteDisplayModeButton)
        v_u_21:create_note_offset_button(p_u_33, v_u_36, v_u_37, v_u_37.NoteOffsetButton)
        v_u_21:create_note_speed_button(p_u_33, v_u_36, v_u_37, v_u_37.NoteSpeedButton)
        v_u_36:add_cycle_element(p_u_33, 1, v_u_6:new(v_u_5:new(v_u_36, v_u_37.PrimaryPart, v_u_37.TipsButton), p_u_34, function() --[[ Line: 142 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_8, (ref 3): p_u_35, (ref 4): v_u_12, (ref 5): p_u_34 ]]
            p_u_33._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            p_u_35:push_menu(v_u_12:new(p_u_33, p_u_34, p_u_35):set_text("Tips", "- Coming from FNF or another rhythm game? Try 2D mode in \"Display Mode\", with arrow skins.\n- Set Lobby -> \"Character Display\" to \"Low\" or \"None\" if having performance issues.\n- Set your Roblox graphics level (ESC -> Settings) to minimum if having performance issues.\n- Setting Game -> \"Show Characters\" to \"Off\" will hide characters while in a match."))
        end)):set_auto_zoffset_behaviour(true)
        v_u_36:add_cycle_element(p_u_33, 1, v_u_6:new(v_u_5:new(v_u_36, v_u_37.PrimaryPart, v_u_37.MemoryStatsButton), p_u_34, function() --[[ Line: 154 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_8, (ref 3): v_u_32 ]]
            p_u_33._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_32:show_memory_stats_menu(p_u_33)
        end)):set_auto_zoffset_behaviour(true)
        v_u_6:set_button_text(v_u_36:add_cycle_element(p_u_33, 1, v_u_6:new(v_u_5:new(v_u_36, v_u_37.PrimaryPart, v_u_37.SettingsTestButton1), p_u_34, function() --[[ Line: 164 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_8, (ref 3): v_u_31 ]]
            p_u_33._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_31:show_recent_scores_for_player(p_u_33)
        end)):set_auto_zoffset_behaviour(true), "Your Plays")
        v_u_37.SettingsTestButton2.Parent = nil
        v_u_36:create_toggle_groups()
        v_u_36:reset_selected_item()
        v_u_36:transition_update_visual(0)
        v_u_36:layout()
    end;
    v_u_36.create_toggle_groups = function(p42) --[[ Name: create_toggle_groups ]] --[[ Line: 194 ]]
        --[[ Upvalues: (copy 1): v_u_40, (ref 2): v_u_10, (ref 3): v_u_3, (ref 4): v_u_37, (copy 5): p_u_33, (ref 6): v_u_11, (copy 7): p_u_34, (ref 8): v_u_13, (ref 9): v_u_17, (ref 10): v_u_1, (ref 11): v_u_15, (ref 12): v_u_25 ]]
        v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({ v_u_37.HitSFXSettings.True, v_u_37.HitSFXSettings.False }), v_u_3:new():push_back_table_list({ true, false }), function(p43) --[[ Line: 198 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            p_u_33._player_settings_manager:set_key(v_u_11.Key.HitSFX, p43)
        end, function() --[[ Line: 201 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            return p_u_33._player_settings_manager:get_key(v_u_11.Key.HitSFX);
        end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
        v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({ v_u_37.BGMSettings.True, v_u_37.BGMSettings.False }), v_u_3:new():push_back_table_list({ true, false }), function(p44) --[[ Line: 210 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            p_u_33._player_settings_manager:set_key(v_u_11.Key.BGM, p44)
        end, function() --[[ Line: 213 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            return p_u_33._player_settings_manager:get_key(v_u_11.Key.BGM);
        end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
        v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({ v_u_37.BrightnessSettings.Normal, v_u_37.BrightnessSettings.Dark }), v_u_3:new():push_back_table_list({ v_u_13.Normal, v_u_13.Dark }), function(p45) --[[ Line: 222 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            p_u_33._player_settings_manager:set_key(v_u_11.Key.BrightnessSettings, p45)
        end, function() --[[ Line: 225 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            return p_u_33._player_settings_manager:get_key(v_u_11.Key.BrightnessSettings);
        end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
        v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({ v_u_37.HeldNoteTransparent.True, v_u_37.HeldNoteTransparent.False }), v_u_3:new():push_back_table_list({ true, false }), function(p46) --[[ Line: 234 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            p_u_33._player_settings_manager:set_key(v_u_11.Key.HeldNoteTransparent, p46)
        end, function() --[[ Line: 237 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            return p_u_33._player_settings_manager:get_key(v_u_11.Key.HeldNoteTransparent);
        end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
        v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({ v_u_37.FixedNoteSpeed.True, v_u_37.FixedNoteSpeed.False }), v_u_3:new():push_back_table_list({ true, false }), function(p47) --[[ Line: 246 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            p_u_33._player_settings_manager:set_key(v_u_11.Key.FixedNoteSpeed, p47)
        end, function() --[[ Line: 249 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            return p_u_33._player_settings_manager:get_key(v_u_11.Key.FixedNoteSpeed);
        end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
        v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({ v_u_37.ShowComboDisplay.True, v_u_37.ShowComboDisplay.False }), v_u_3:new():push_back_table_list({ true, false }), function(p48) --[[ Line: 258 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            p_u_33._player_settings_manager:set_key(v_u_11.Key.ShowComboDisplay, p48)
        end, function() --[[ Line: 261 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            return p_u_33._player_settings_manager:get_key(v_u_11.Key.ShowComboDisplay);
        end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
        v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({ v_u_37.ShowHeldNoteTail.True, v_u_37.ShowHeldNoteTail.False }), v_u_3:new():push_back_table_list({ true, false }), function(p49) --[[ Line: 270 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            p_u_33._player_settings_manager:set_key(v_u_11.Key.ShowHeldNoteTail, p49)
        end, function() --[[ Line: 273 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            return p_u_33._player_settings_manager:get_key(v_u_11.Key.ShowHeldNoteTail);
        end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
        v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({ v_u_37.FeverIconDisplaySettings.Stars, v_u_37.FeverIconDisplaySettings.None, v_u_37.FeverIconDisplaySettings.Icon }), v_u_3:new():push_back_table_list({ v_u_17.FeverIconDisplay.Stars, v_u_17.FeverIconDisplay.None, v_u_17.FeverIconDisplay.Icon }), function(p50) --[[ Line: 282 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            p_u_33._player_settings_manager:set_key(v_u_11.Key.FeverIconDisplay, p50)
        end, function() --[[ Line: 285 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            return p_u_33._player_settings_manager:get_key(v_u_11.Key.FeverIconDisplay);
        end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
        local l_Frame_0 = v_u_37.MainSurface.SurfaceGui.Frame
        if v_u_1:is_mobile() then
            l_Frame_0.CharacterDisplay.TextLabel.Text = "Lobby Character Amount (Mobile)"
            v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({
                v_u_37.CharacterCullingSettings.None,
                v_u_37.CharacterCullingSettings.Low,
                v_u_37.CharacterCullingSettings.Medium,
                v_u_37.CharacterCullingSettings.High,
                v_u_37.CharacterCullingSettings.All
            }), v_u_3:new():push_back_table_list({
                v_u_15.Mode.None,
                v_u_15.Mode.Low,
                v_u_15.Mode.Medium,
                v_u_15.Mode.High,
                v_u_15.Mode.All
            }), function(p51) --[[ Line: 297 ]]
                --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
                p_u_33._player_settings_manager:set_key(v_u_11.Key.MobileCharacterCulling, p51)
            end, function() --[[ Line: 300 ]]
                --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
                return p_u_33._player_settings_manager:get_key(v_u_11.Key.MobileCharacterCulling);
            end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
        else
            l_Frame_0.CharacterDisplay.TextLabel.Text = "Lobby Character Amount (PC)"
            v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({
                v_u_37.CharacterCullingSettings.None,
                v_u_37.CharacterCullingSettings.Low,
                v_u_37.CharacterCullingSettings.Medium,
                v_u_37.CharacterCullingSettings.High,
                v_u_37.CharacterCullingSettings.All
            }), v_u_3:new():push_back_table_list({
                v_u_15.Mode.None,
                v_u_15.Mode.Low,
                v_u_15.Mode.Medium,
                v_u_15.Mode.High,
                v_u_15.Mode.All
            }), function(p52) --[[ Line: 310 ]]
                --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
                p_u_33._player_settings_manager:set_key(v_u_11.Key.PCCharacterCulling, p52)
            end, function() --[[ Line: 313 ]]
                --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
                return p_u_33._player_settings_manager:get_key(v_u_11.Key.PCCharacterCulling);
            end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
        end;
        if v_u_1:is_mobile() then
            v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({ v_u_37.MobileFullScreenUI.True, v_u_37.MobileFullScreenUI.False }), v_u_3:new():push_back_table_list({ true, false }), function(p53) --[[ Line: 324 ]]
                --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
                p_u_33._player_settings_manager:set_key(v_u_11.Key.MobileFullScreenUI, p53)
            end, function() --[[ Line: 327 ]]
                --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
                return p_u_33._player_settings_manager:get_key(v_u_11.Key.MobileFullScreenUI);
            end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
        else
            l_Frame_0.MobileFullScreenUI.Visible = false
            l_Frame_0.GameMobileSettingsTitle.Visible = false
            v_u_37.MobileFullScreenUI.Parent = nil
        end;
        v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({ v_u_37.ShowAllSongs.True, v_u_37.ShowAllSongs.False }), v_u_3:new():push_back_table_list({ true, false }), function(p54) --[[ Line: 341 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11, (ref 3): v_u_25 ]]
            p_u_33._player_settings_manager:set_key(v_u_11.Key.ShowAllSongs, p54)
            v_u_25:initial_settings_sync_update(p_u_33)
        end, function() --[[ Line: 345 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            return p_u_33._player_settings_manager:get_key(v_u_11.Key.ShowAllSongs);
        end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
        v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({ v_u_37.ArtistEventUseStage.True, v_u_37.ArtistEventUseStage.False }), v_u_3:new():push_back_table_list({ true, false }), function(p55) --[[ Line: 353 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11, (ref 3): v_u_25 ]]
            p_u_33._player_settings_manager:set_key(v_u_11.Key.ArtistEventUseStage, p55)
            v_u_25:initial_settings_sync_update(p_u_33)
        end, function() --[[ Line: 357 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            return p_u_33._player_settings_manager:get_key(v_u_11.Key.ArtistEventUseStage);
        end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
        v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({ v_u_37.GameShowCharacters.True, v_u_37.GameShowCharacters.False }), v_u_3:new():push_back_table_list({ true, false }), function(p56) --[[ Line: 365 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11, (ref 3): v_u_25 ]]
            p_u_33._player_settings_manager:set_key(v_u_11.Key.GameShowCharacters, p56)
            v_u_25:initial_settings_sync_update(p_u_33)
        end, function() --[[ Line: 369 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            return p_u_33._player_settings_manager:get_key(v_u_11.Key.GameShowCharacters);
        end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
        v_u_40:push_back(v_u_10:new(v_u_3:new():push_back_table_list({ v_u_37.ShowMissionDisplay.True, v_u_37.ShowMissionDisplay.False }), v_u_3:new():push_back_table_list({ true, false }), function(p57) --[[ Line: 377 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            p_u_33._player_settings_manager:set_key(v_u_11.Key.ShowGameMissionDisplay, p57)
        end, function() --[[ Line: 380 ]]
            --[[ Upvalues: (ref 1): p_u_33, (ref 2): v_u_11 ]]
            return p_u_33._player_settings_manager:get_key(v_u_11.Key.ShowGameMissionDisplay);
        end, p42, v_u_37.PrimaryPart, p_u_33, p_u_34))
    end;
    local v_u_58 = nil
    v_u_36.set_on_close_fn = function(p59, p60) --[[ Name: set_on_close_fn ]] --[[ Line: 388 ]]
        --[[ Upvalues: (ref 1): v_u_58 ]]
        v_u_58 = p60
        return p59;
    end;
    v_u_36.close_action = function(p61) --[[ Name: close_action ]] --[[ Line: 393 ]]
        --[[ Upvalues: (copy 1): p_u_33, (copy 2): p_u_35, (ref 3): v_u_12, (copy 4): p_u_34, (ref 5): v_u_58 ]]
        if p_u_33._player_settings_manager:has_changes() then
            local v_u_62 = p_u_35:push_menu(v_u_12:new(p_u_33, p_u_34, p_u_35):set_text("Saving...", "Please wait..."):set_close_button_visible(false))
            p_u_33._player_settings_manager:save_changes_to_playerblob(p_u_33, function() --[[ Line: 396 ]]
                --[[ Upvalues: (ref 1): p_u_35, (copy 2): v_u_62, (ref 3): p_u_33 ]]
                p_u_35:remove_menu(v_u_62)
                p_u_33._player_settings_manager:clear_changes()
            end)
        end;
        p_u_35:remove_menu(p61)
        if v_u_58 then
            v_u_58()
        end;
    end;
    v_u_36.behaviour_update = function(p63, p64, p65) --[[ Name: behaviour_update ]] --[[ Line: 407 ]]
        p63:behaviour_update_base(p64, p65)
    end;
    v_u_36.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 417 ]]
        --[[ Upvalues: (ref 1): v_u_37 ]]
        v_u_37:Destroy()
    end;
    v_u_36.layout = function(p66) --[[ Name: layout ]] --[[ Line: 421 ]]
        --[[ Upvalues: (copy 1): p_u_34, (ref 2): v_u_39, (ref 3): v_u_37 ]]
        p66:opt_rescale_to_max_nxy(p_u_34, 0.8, 0.8, v_u_39)
        local v67, v68 = p66:opt_update_cframe_params(p_u_34, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p66:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v67 == true then
            v_u_37:SetPrimaryPartCFrame(v68)
        end;
    end;
    v_u_36.set_alpha = function(_, p69) --[[ Name: set_alpha ]] --[[ Line: 433 ]]
        --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_1, (ref 3): v_u_37 ]]
        if v_u_38 ~= p69 then
            v_u_38 = p69
            v_u_1:r_set_alpha(v_u_37, v_u_38)
        end;
    end;
    v_u_36.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 439 ]]
        --[[ Upvalues: (ref 1): v_u_38 ]]
        return v_u_38;
    end;
    v_u_36.set_scale = function(_, p70) --[[ Name: set_scale ]] --[[ Line: 440 ]]
        --[[ Upvalues: (ref 1): v_u_39 ]]
        v_u_39 = p70
    end;
    v_u_36.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 441 ]]
        --[[ Upvalues: (ref 1): v_u_39 ]]
        return v_u_39;
    end;
    v_u_36.get_native_size = function(p71) --[[ Name: get_native_size ]] --[[ Line: 443 ]]
        return p71._native_size;
    end;
    v_u_36.get_size = function(p72) --[[ Name: get_size ]] --[[ Line: 446 ]]
        return p72._size;
    end;
    v_u_36.set_size = function(p73, p74) --[[ Name: set_size ]] --[[ Line: 449 ]]
        --[[ Upvalues: (ref 1): v_u_37 ]]
        p73._size = p74
        v_u_37.PrimaryPart.Size = Vector3.new(p74.X, p74.Y, 0)
    end;
    v_u_36.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 453 ]]
        --[[ Upvalues: (ref 1): v_u_37 ]]
        return v_u_37.PrimaryPart.Position;
    end;
    v_u_36.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 456 ]]
        --[[ Upvalues: (ref 1): v_u_37 ]]
        return v_u_37.PrimaryPart.SurfaceGui;
    end;
    v_u_36.set_showing = function(_, p75) --[[ Name: set_showing ]] --[[ Line: 459 ]]
        --[[ Upvalues: (ref 1): v_u_37, (ref 2): v_u_9 ]]
        if p75 then
            v_u_37.Parent = v_u_9:get_world_ui_folder()
        else
            v_u_37.Parent = nil
        end;
    end;
    f_cons()
    return v_u_36;
end;
local v_u_76 = v18.SavePageState:new()
local v_u_77 = v2:new()
local v_u_78 = v2:new()
v_u_32.show_memory_stats_menu = function(_, p_u_79) --[[ Name: show_memory_stats_menu ]] --[[ Line: 474 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_1, (copy 3): v_u_77, (copy 4): v_u_78, (copy 5): v_u_16, (copy 6): s_Stats_0, (copy 7): v_u_15, (copy 8): v_u_19, (copy 9): v_u_7, (copy 10): v_u_76, (copy 11): v_u_6 ]]
    local v_u_80 = v_u_3:new({
        Enum.DeveloperMemoryTag.Internal,
        Enum.DeveloperMemoryTag.HttpCache,
        Enum.DeveloperMemoryTag.Instances,
        Enum.DeveloperMemoryTag.Signals,
        Enum.DeveloperMemoryTag.LuaHeap,
        Enum.DeveloperMemoryTag.Script,
        Enum.DeveloperMemoryTag.PhysicsCollision,
        Enum.DeveloperMemoryTag.PhysicsParts,
        Enum.DeveloperMemoryTag.GraphicsSolidModels,
        Enum.DeveloperMemoryTag.GraphicsMeshParts,
        Enum.DeveloperMemoryTag.GraphicsParticles,
        Enum.DeveloperMemoryTag.GraphicsParts,
        Enum.DeveloperMemoryTag.GraphicsSpatialHash,
        Enum.DeveloperMemoryTag.GraphicsTerrain,
        Enum.DeveloperMemoryTag.GraphicsTexture,
        Enum.DeveloperMemoryTag.GraphicsTextureCharacter,
        Enum.DeveloperMemoryTag.Sounds,
        Enum.DeveloperMemoryTag.StreamingSounds,
        Enum.DeveloperMemoryTag.TerrainVoxels,
        Enum.DeveloperMemoryTag.Gui,
        Enum.DeveloperMemoryTag.Animation,
        Enum.DeveloperMemoryTag.Navigation,
        Enum.DeveloperMemoryTag.GeometryCSG
    })
    local function f_r_get_child_count(p81) --[[ Name: r_get_child_count ]] --[[ Line: 502 ]]
        --[[ Upvalues: (copy 1): f_r_get_child_count ]]
        local v82 = 0
        for _, v83 in pairs(p81:GetChildren()) do
            v82 = v82 + 1 + f_r_get_child_count(v83)
        end;
        return v82;
    end;
    local function f_format_number_value(p84) --[[ Name: format_number_value ]] --[[ Line: 510 ]]
        --[[ Upvalues: (ref 1): v_u_1 ]]
        return v_u_1:comma_value(math.floor(p84 * 100) / 100);
    end;
    local function f_data_element(p85, p86) --[[ Name: data_element ]] --[[ Line: 512 ]]
        --[[ Upvalues: (ref 1): v_u_77, (ref 2): v_u_78, (ref 3): v_u_1 ]]
        local v87 = tostring(p85)
        local v88 = not v_u_77:contains(v87) and 0 or v_u_77:get(v87)
        local v89 = not v_u_78:contains(v87) and 0 or v_u_78:get(v87)
        v_u_77:add(v87, p86)
        return {
            ["DisplayName"] = v87,
            ["Value"] = p86,
            ["ValueString"] = v_u_1:comma_value(math.floor(p86 * 100) / 100),
            ["LastValue"] = v88,
            ["LastValueString"] = v_u_1:comma_value(math.floor(v88 * 100) / 100),
            ["SavedValue"] = v89,
            ["SavedValueString"] = v_u_1:comma_value(math.floor(v89 * 100) / 100)
        };
    end;
    local v_u_90 = nil
    v_u_90 = p_u_79._menus:push_menu(v_u_16:new(p_u_79, p_u_79._spui, p_u_79._menus, function(p_u_91) --[[ Line: 539 ]]
        --[[ Upvalues: (copy 1): f_data_element, (ref 2): s_Stats_0, (copy 3): v_u_80, (copy 4): f_r_get_child_count, (copy 5): p_u_79, (ref 6): v_u_15, (ref 7): v_u_19, (ref 8): v_u_1, (ref 9): v_u_7 ]]
        p_u_91:set_header_text("Memory Stats")
        p_u_91:get_element_list():push_back((f_data_element("TotalMemoryUsageMb", s_Stats_0:GetTotalMemoryUsageMb())))
        p_u_91:get_element_list():push_back((f_data_element("DataReceiveKbps", s_Stats_0.DataReceiveKbps)))
        p_u_91:get_element_list():push_back((f_data_element("DataSendKbps", s_Stats_0.DataSendKbps)))
        p_u_91:get_element_list():push_back((f_data_element("InstanceCount", s_Stats_0.InstanceCount)))
        p_u_91:get_element_list():push_back((f_data_element("PrimitivesCount", s_Stats_0.PrimitivesCount)))
        for _, v92 in v_u_80:key_itr() do
            p_u_91:get_element_list():push_back((f_data_element("Memory Tag: " .. v92.Name, s_Stats_0:GetMemoryUsageMbForTag(v92))))
        end;
        for _, v93 in pairs(game.ReplicatedStorage:GetChildren()) do
            p_u_91:get_element_list():push_back((f_data_element("ReplicatedStorage Instances: " .. v93.Name, (f_r_get_child_count(v93)))))
        end;
        for _, v94 in pairs(game.Workspace:GetChildren()) do
            p_u_91:get_element_list():push_back((f_data_element("Workspace Instances: " .. v94.Name, (f_r_get_child_count(v94)))))
        end;
        for _, v95 in pairs(game.Lighting:GetChildren()) do
            p_u_91:get_element_list():push_back((f_data_element("Lighting Instances: " .. v95.Name, (f_r_get_child_count(v95)))))
        end;
        local v96, v97 = pcall(function() --[[ Line: 558 ]]
            --[[ Upvalues: (copy 1): p_u_91, (ref 2): f_data_element, (ref 3): p_u_79, (ref 4): v_u_15, (ref 5): v_u_19 ]]
            p_u_91:get_element_list():push_back((f_data_element("PlayerStatus Count", p_u_79._player_status_manager:get_playerstatus_count())))
            p_u_91:get_element_list():push_back((f_data_element("WebNPC LocalModelCache Count", p_u_79._webnpc_local_model_cache:get_cached_count())))
            p_u_91:get_element_list():push_back((f_data_element("CharacterCulling Player Count", v_u_15:get_player_count())))
            p_u_91:get_element_list():push_back((f_data_element("CharacterCulling NPC Count", v_u_15:get_npc_count())))
            p_u_91:get_element_list():push_back((f_data_element("CharacterCulling Follow NPC Count", v_u_15:get_follow_npc_count())))
            p_u_91:get_element_list():push_back((f_data_element("NPCManager NPC Count", p_u_79._npcs:get_id_to_npcs():count())))
            p_u_91:get_element_list():push_back((f_data_element("NPCManager WebNPC Count", p_u_79._npcs:get_web_npc_manager():count())))
            p_u_91:get_element_list():push_back((f_data_element("CharacterManager Nametag Count", p_u_79._lobby_join:get_character_manager():get_id_to_nametag_count())))
            p_u_91:get_element_list():push_back((f_data_element("CharacterManager PlayerInfo Count", p_u_79._lobby_join:get_character_manager():get_id_to_playerinfo_count())))
            p_u_91:get_element_list():push_back((f_data_element("ModelLoadDB Count", v_u_19:singleton():get_loaded_models_count())))
        end)
        v_u_1:ptry(function() --[[ Line: 570 ]]
            --[[ Upvalues: (ref 1): p_u_79, (copy 2): p_u_91, (ref 3): f_data_element ]]
            local v98 = p_u_79._lobby_join:get_lobby()
            if v98 then
                p_u_91:get_element_list():push_back((f_data_element("Lobby NPCManager Count", v98._npcs:get_id_to_npcs():count())))
            end;
        end)
        if v96 ~= true then
            v_u_7:warnf("Error while getting stats: %s", v97)
        end;
    end, function(p99, p100, p101, _, p102) --[[ Line: 581 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): f_format_number_value ]]
        p100.Text = p99.DisplayName
        p101.Image = v_u_1:important_assetid()
        p102:get_description_display().Text = string.format("Cur: %s, Last: %s (%s%s), Save: %s (%s%s)", p99.ValueString, p99.LastValueString, p99.Value > p99.LastValue and "+" or "", v_u_1:comma_value(math.floor((p99.Value - p99.LastValue) * 100) / 100), p99.SavedValueString, p99.Value > p99.SavedValue and "+" or "", f_format_number_value(p99.Value - p99.SavedValue))
        p102:set_select_button_enabled(false)
    end, function(p103) --[[ Line: 599 ]]
        --[[ Upvalues: (ref 1): v_u_76, (ref 2): v_u_90 ]]
        v_u_76:on_list_select_save_page(v_u_90:get_list_adapter())
        if p103 ~= nil then
        end;
    end)):set_close_on_element_select(false)
    v_u_90:set_settings_section_visible()
    local v104 = v_u_90:get_settings_buttons():get(1)
    if v104 then
        v104:set_visible(true)
        v104:bind_data(function() --[[ Line: 611 ]]
            --[[ Upvalues: (ref 1): v_u_90 ]]
            v_u_90:refresh()
        end)
        v_u_6:set_button_text(v104, "Refresh")
    end;
    local v105 = v_u_90:get_settings_buttons():get(2)
    if v105 then
        v105:set_visible(true)
        v105:bind_data(function() --[[ Line: 621 ]]
            --[[ Upvalues: (ref 1): v_u_90, (ref 2): v_u_78 ]]
            for _, v106 in v_u_90:get_element_list():key_itr() do
                v_u_78:add(v106.DisplayName, v106.Value)
            end;
            v_u_90:refresh()
        end)
        v_u_6:set_button_text(v105, "Save")
    end;
    v_u_90:get_list_adapter():set_do_wrap(true)
    v_u_76:open_to_saved_page(v_u_90:get_list_adapter())
end;
return v_u_32;
