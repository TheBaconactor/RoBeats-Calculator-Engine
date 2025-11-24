-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:44 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_7 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_8 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
require(game.ReplicatedStorage.Shared.AssertType)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_10 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_11 = require(game.ReplicatedStorage.Lobby.Menus.VIPPurchaseUI)
local v_u_12 = require(game.ReplicatedStorage.Lobby.UI.SPUITextInput)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_13 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_14 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
local v_u_15 = require(game.ReplicatedStorage.AudioData.SelectableArtists)
require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_16 = require(game.ReplicatedStorage.Crafting.PlayerBlobCrafting)
local v17 = require(game.ReplicatedStorage.Shared.ListAdapter)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_18 = require(game.ReplicatedStorage.AudioData.SongSpecialInfo)
local v_u_19 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
local v_u_20 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_21 = require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_22 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITab)
local v_u_23 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITabController_Recommended)
local v_u_24 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITabController_AllMySongs)
local v_u_25 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITabController_NowPlaying)
local v_u_26 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUISettingsSection)
local v27 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_28 = nil
local v_u_29 = nil
local v_u_30 = nil
v27:require_client(function() --[[ Line: 44 ]]
    --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_29, (ref 3): v_u_30 ]]
    v_u_28 = require(game.ReplicatedStorage.Lobby.Menus.CraftSongUI)
    v_u_29 = require(game.ReplicatedStorage.Lobby.UI.SongFavoriteButton)
    v_u_30 = require(game.ReplicatedStorage.EditorGame.UI.SavedMapInfoListUI)
end)
local v_u_31 = {
    ["State"] = {
        ["Loading"] = 1,
        ["Loaded"] = 2
    },
    ["get_page_first"] = function(_) --[[ Name: get_page_first ]] --[[ Line: 61 ]]
        return 0;
    end,
    ["InfoState"] = {},
    ["get_restore_menu_name"] = function(_) --[[ Name: get_restore_menu_name ]] --[[ Line: 94 ]]
        return "PlayUI";
    end
}
local l_AllMySongs_0 = v_u_22.AllMySongs
local v_u_32 = v_u_2:new()
v_u_31.get_tab_to_infostate = function(_) --[[ Name: get_tab_to_infostate ]] --[[ Line: 59 ]]
    --[[ Upvalues: (copy 1): v_u_32 ]]
    return v_u_32;
end;
v_u_31.InfoState.new = function(_) --[[ Name: new ]] --[[ Line: 64 ]]
    --[[ Upvalues: (copy 1): v_u_10 ]]
    local v33 = {}
    local v_u_34 = 0
    local v_u_35 = v_u_10:invalid_songkey()
    v33.get_page = function(_) --[[ Name: get_page ]] --[[ Line: 70 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        return v_u_34;
    end;
    v33.set_page = function(_, p36) --[[ Name: set_page ]] --[[ Line: 71 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        v_u_34 = p36
    end;
    v33.get_info_displayed_song_key = function(_) --[[ Name: get_info_displayed_song_key ]] --[[ Line: 73 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        return v_u_35;
    end;
    v33.set_info_displayed_song_key = function(_, p37) --[[ Name: set_info_displayed_song_key ]] --[[ Line: 74 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        v_u_35 = p37
    end;
    return v33;
end;
local v_u_38 = ""
v_u_31.get_filter_last_name_input_text = function(_) --[[ Name: get_filter_last_name_input_text ]] --[[ Line: 80 ]]
    --[[ Upvalues: (ref 1): v_u_38 ]]
    return v_u_38;
end;
v_u_31.set_filter_last_name_input_text = function(_, p39) --[[ Name: set_filter_last_name_input_text ]] --[[ Line: 81 ]]
    --[[ Upvalues: (ref 1): v_u_38 ]]
    v_u_38 = p39
end;
local v_u_40 = ""
v_u_31.get_filter_last_difficulty_input_text = function(_) --[[ Name: get_filter_last_difficulty_input_text ]] --[[ Line: 84 ]]
    --[[ Upvalues: (ref 1): v_u_40 ]]
    return v_u_40;
end;
v_u_31.set_filter_last_difficulty_input_text = function(_, p41) --[[ Name: set_filter_last_difficulty_input_text ]] --[[ Line: 85 ]]
    --[[ Upvalues: (ref 1): v_u_40 ]]
    v_u_40 = p41
end;
local v_u_42 = ""
v_u_31.get_filter_last_artist_input_text = function(_) --[[ Name: get_filter_last_artist_input_text ]] --[[ Line: 88 ]]
    --[[ Upvalues: (ref 1): v_u_42 ]]
    return v_u_42;
end;
v_u_31.set_filter_last_artist_input_text = function(_, p43) --[[ Name: set_filter_last_artist_input_text ]] --[[ Line: 89 ]]
    --[[ Upvalues: (ref 1): v_u_42 ]]
    v_u_42 = p43
end;
local v_u_44 = v17.SavePageState:new()
v_u_31.get_artist_select_page_save_state = function(_) --[[ Name: get_artist_select_page_save_state ]] --[[ Line: 92 ]]
    --[[ Upvalues: (copy 1): v_u_44 ]]
    return v_u_44;
end;
v_u_31.new = function(_, p_u_45, p_u_46, p_u_47) --[[ Name: new ]] --[[ Line: 96 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_31, (copy 3): v_u_2, (copy 4): v_u_1, (copy 5): v_u_8, (copy 6): v_u_5, (copy 7): v_u_4, (copy 8): v_u_7, (ref 9): l_AllMySongs_0, (copy 10): v_u_11, (ref 11): v_u_29, (copy 12): v_u_22, (copy 13): v_u_10, (ref 14): v_u_30, (copy 15): v_u_20, (copy 16): v_u_14, (copy 17): v_u_15, (copy 18): v_u_44, (copy 19): v_u_12, (ref 20): v_u_38, (ref 21): v_u_40, (ref 22): v_u_42, (copy 23): v_u_26, (copy 24): v_u_23, (copy 25): v_u_24, (copy 26): v_u_25, (copy 27): v_u_32, (copy 28): v_u_9, (copy 29): v_u_18, (copy 30): v_u_13, (copy 31): v_u_21, (ref 32): v_u_28, (copy 33): v_u_16, (copy 34): v_u_19, (copy 35): v_u_6 ]]
    local v_u_48 = v_u_3:new(p_u_46, p_u_47)
    v_u_48.get_restore_name = function(_) --[[ Name: get_restore_name ]] --[[ Line: 98 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        return v_u_31:get_restore_menu_name();
    end;
    local v_u_49 = nil
    local v_u_50 = 1
    local v_u_51 = 1
    local v_u_52 = nil
    local v_u_53 = nil
    local v_u_54 = nil
    local v_u_55 = nil
    local v_u_56 = v_u_2:new()
    local v_u_57 = v_u_2:new()
    local v_u_58 = nil
    local v_u_59 = nil
    local v_u_60 = nil
    local v_u_61 = nil
    local v_u_62 = nil
    local v_u_63 = nil
    local v_u_64 = nil
    local v_u_65 = nil
    local v_u_66 = nil
    local v_u_67 = nil
    local v_u_68 = nil
    local v_u_69 = nil
    local v_u_70 = nil
    local v_u_71 = nil
    local v_u_72 = nil
    local v_u_73 = nil
    local v_u_74 = ""
    local v_u_75 = v_u_2:new()
    local v_u_76 = nil
    local v_u_77 = nil
    local v_u_78 = nil
    local v_u_79 = nil
    local v_u_80 = nil
    local v_u_81 = nil
    local v_u_82 = nil
    local v_u_83 = nil
    local v_u_84 = false
    local v_u_85 = nil
    local v_u_86 = nil
    local v_u_87 = nil
    local l_Loading_0 = v_u_31.State.Loading
    local v_u_88 = nil
    local v_u_89 = nil
    local v_u_90 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 136 ]]
        --[[ Upvalues: (ref 1): v_u_49, (ref 2): v_u_1, (ref 3): v_u_8, (ref 4): v_u_90, (copy 5): p_u_45, (copy 6): v_u_48, (ref 7): v_u_5, (ref 8): v_u_4, (copy 9): p_u_46, (ref 10): v_u_7, (copy 11): p_u_47, (ref 12): v_u_52, (copy 13): v_u_57, (ref 14): l_AllMySongs_0, (ref 15): v_u_53, (ref 16): v_u_87, (ref 17): v_u_11, (ref 18): v_u_89, (ref 19): v_u_88, (ref 20): v_u_54, (ref 21): v_u_55, (ref 22): v_u_85, (ref 23): v_u_58, (ref 24): v_u_59, (ref 25): v_u_70, (ref 26): v_u_60, (ref 27): v_u_61, (ref 28): v_u_63, (ref 29): v_u_62, (ref 30): v_u_64, (ref 31): v_u_65, (ref 32): v_u_66, (ref 33): v_u_67, (ref 34): v_u_68, (ref 35): v_u_69, (ref 36): v_u_29, (ref 37): v_u_72, (ref 38): v_u_71, (ref 39): v_u_74, (ref 40): v_u_83, (ref 41): v_u_22, (ref 42): v_u_10, (ref 43): v_u_73, (ref 44): v_u_30, (copy 45): v_u_75, (ref 46): v_u_20, (copy 47): v_u_56, (ref 48): v_u_76, (ref 49): v_u_77, (ref 50): v_u_81, (ref 51): v_u_82, (ref 52): v_u_78, (ref 53): v_u_14, (ref 54): v_u_2, (ref 55): v_u_15, (ref 56): v_u_84, (ref 57): v_u_44, (ref 58): v_u_79, (ref 59): v_u_80, (ref 60): v_u_12, (ref 61): v_u_38, (ref 62): v_u_40, (ref 63): v_u_42, (ref 64): v_u_86, (ref 65): v_u_26, (ref 66): v_u_23, (ref 67): v_u_24, (ref 68): v_u_25 ]]
        v_u_49 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.PlayUI:Clone()
        v_u_49.Name = v_u_1:gen_name(v_u_49.Name)
        v_u_49.Parent = v_u_8:get_world_ui_folder()
        v_u_90 = p_u_45._bgm_manager:begin_preview_songkey()
        v_u_48._native_size = v_u_49.PrimaryPart.Size
        v_u_48._size = v_u_48._native_size
        v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, v_u_49.BackButtonSurface), p_u_46, function() --[[ Line: 149 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): p_u_47, (ref 4): v_u_48 ]]
            p_u_45._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
            p_u_47:remove_menu(v_u_48)
        end))
        v_u_52 = v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, v_u_49.ArrowLeft), p_u_46, function() --[[ Line: 158 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): v_u_57, (ref 4): l_AllMySongs_0, (ref 5): v_u_48 ]]
            p_u_45._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            if v_u_57:contains(l_AllMySongs_0) then
                local v91 = v_u_57:get(l_AllMySongs_0)
                v_u_48:set_page(v_u_48:get_page() - 1)
                if v_u_48:get_page() < 0 then
                    v_u_48:set_page(v91:get_page_total() - 1)
                end;
                v_u_48:refresh_current_page()
            end;
        end))
        v_u_53 = v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, v_u_49.ArrowRight), p_u_46, function() --[[ Line: 174 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): v_u_57, (ref 4): l_AllMySongs_0, (ref 5): v_u_48 ]]
            p_u_45._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            if v_u_57:contains(l_AllMySongs_0) then
                local v92 = v_u_57:get(l_AllMySongs_0)
                v_u_48:set_page(v_u_48:get_page() + 1)
                if v_u_48:get_page() >= v92:get_page_total() then
                    v_u_48:set_page(0)
                end;
                v_u_48:refresh_current_page()
            end;
        end))
        v_u_87 = v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, v_u_49.VIPButton), p_u_46, function() --[[ Line: 190 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): p_u_47, (ref 4): v_u_11, (ref 5): p_u_46, (ref 6): v_u_48 ]]
            p_u_45._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
            p_u_47:push_menu(v_u_11:new(p_u_45, p_u_46, p_u_47))
            v_u_48:set_loading(true)
        end))
        v_u_87:set_visible(false)
        v_u_89 = v_u_49.MainSurface.SurfaceGui.Frame.LoadingSection
        v_u_88 = v_u_49.MainSurface.SurfaceGui.Frame.LoadedSection
        v_u_54 = v_u_88.PageDisplaySection.CurrentPageDisplay
        v_u_55 = v_u_88.PageDisplaySection.MaxPageDisplay
        v_u_85 = v_u_88.NoResultsText
        v_u_85.Visible = false
        local l_InfoSection_0 = v_u_88.InfoSection
        v_u_58 = l_InfoSection_0
        v_u_59 = l_InfoSection_0.NameDisplay
        v_u_70 = l_InfoSection_0.SpecialTextDisplay
        v_u_70.Visible = false
        v_u_60 = l_InfoSection_0.CoverBack
        v_u_61 = l_InfoSection_0.CoverBack.AlbumArt
        v_u_63 = l_InfoSection_0.CoverBack.ColorSection
        v_u_62 = l_InfoSection_0.CoverBack.AlbumArtOverlay
        v_u_64 = l_InfoSection_0.CoverBack.RankDisplay
        v_u_65 = l_InfoSection_0.RankDisplay
        v_u_66 = l_InfoSection_0.BestScoreDisplay
        v_u_67 = l_InfoSection_0.TimesPlayedDisplay
        v_u_68 = v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, v_u_49.SongInfoButtons.InfoButton), p_u_46, function() --[[ Line: 221 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): v_u_48 ]]
            p_u_45._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_48:show_info_displayed_description_popup()
        end):set_auto_zoffset_behaviour(true))
        v_u_68:set_visible(false)
        v_u_69 = v_u_29:new(p_u_45, v_u_48, v_u_4:new(v_u_48, v_u_49.PrimaryPart, v_u_49.SongInfoButtons.FavoriteButton), v_u_49.SongInfoButtons.FavoriteButton.SurfaceGui.Button.Icon)
        v_u_72 = v_u_49.SongInfoButtons.ArtistButton.SurfaceGui.Icon
        v_u_71 = v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, v_u_49.SongInfoButtons.ArtistButton), p_u_46, function() --[[ Line: 239 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): v_u_74, (ref 4): v_u_48, (ref 5): v_u_83, (ref 6): l_AllMySongs_0, (ref 7): v_u_22, (ref 8): v_u_10 ]]
            p_u_45._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            if typeof(v_u_74) == "string" and #v_u_74 > 0 then
                local v93 = v_u_48:get_info_displayed_song_key()
                if v_u_83:get_current_text() == v_u_74 then
                    v_u_83:set_text("")
                else
                    v_u_83:set_text(v_u_74)
                end;
                v_u_48:reset_page()
                v_u_48:refresh_current_page()
                v_u_83:raise_changed()
                if l_AllMySongs_0 == v_u_22.AllMySongs and v_u_10:singleton():contains_key(v93) then
                    v_u_48:select_songkey(v93)
                end;
            end;
        end):set_auto_zoffset_behaviour(true))
        v_u_71:set_visible(false)
        v_u_73 = v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, v_u_49.SongInfoButtons.SongEditorButton), p_u_46, function() --[[ Line: 264 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): v_u_48, (ref 4): v_u_10, (ref 5): v_u_30 ]]
            p_u_45._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
            local v94 = v_u_48:get_info_displayed_song_key()
            if v94 ~= v_u_10:invalid_songkey() then
                v_u_30:show_published_map_list_ui_for_songkey(p_u_45, v94)
            end;
        end))
        v_u_73:set_visible(false)
        local function f_create_info_to_audiomod_button(p95, p96) --[[ Name: create_info_to_audiomod_button ]] --[[ Line: 274 ]]
            --[[ Upvalues: (ref 1): v_u_48, (ref 2): p_u_45, (ref 3): v_u_5, (ref 4): v_u_4, (ref 5): v_u_49, (ref 6): p_u_46, (ref 7): v_u_7, (ref 8): v_u_10, (ref 9): v_u_75 ]]
            local v_u_97 = nil
            v_u_97 = v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, p96), p_u_46, function() --[[ Line: 279 ]]
                --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): v_u_48, (ref 4): v_u_97 ]]
                p_u_45._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_48:select_songkey(v_u_97:get_bound_data().TargetSongKey)
            end):set_auto_zoffset_behaviour(true))
            v_u_97:bind_data({
                ["Toggle"] = v_u_5:button_bind_anim_toggle(v_u_97, function() --[[ Line: 285 ]]
                    --[[ Upvalues: (ref 1): v_u_48 ]]
                    return v_u_48:get_alpha();
                end),
                ["DifficultyDisplay"] = p96.SurfaceGui.Button.DifficultyDisplay,
                ["TargetSongKey"] = v_u_10:invalid_songkey()
            })
            v_u_97:set_visible(false)
            v_u_75:add(p95, v_u_97)
        end;
        f_create_info_to_audiomod_button(v_u_20.Easy, v_u_49.SongInfoButtons.EasyModeButton)
        f_create_info_to_audiomod_button(v_u_20.Normal, v_u_49.SongInfoButtons.NormalModeButton)
        f_create_info_to_audiomod_button(v_u_20.Hard, v_u_49.SongInfoButtons.HardModeButton)
        v_u_56:add(v_u_22.Recommended, v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, v_u_49.TabRecommended), p_u_46, function() --[[ Line: 300 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): l_AllMySongs_0, (ref 4): v_u_22, (ref 5): v_u_48 ]]
            p_u_45._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            l_AllMySongs_0 = v_u_22.Recommended
            v_u_48:update_selected_tab()
        end)):set_auto_zoffset_behaviour(true))
        v_u_56:add(v_u_22.NowPlaying, v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, v_u_49.TabNowPlaying), p_u_46, function() --[[ Line: 310 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): l_AllMySongs_0, (ref 4): v_u_22, (ref 5): v_u_48 ]]
            p_u_45._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            l_AllMySongs_0 = v_u_22.NowPlaying
            v_u_48:update_selected_tab()
        end)):set_auto_zoffset_behaviour(true))
        v_u_56:add(v_u_22.AllMySongs, v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, v_u_49.TabAllMySongs), p_u_46, function() --[[ Line: 320 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): l_AllMySongs_0, (ref 4): v_u_22, (ref 5): v_u_48 ]]
            p_u_45._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            l_AllMySongs_0 = v_u_22.AllMySongs
            v_u_48:update_selected_tab()
        end)):set_auto_zoffset_behaviour(true))
        v_u_76 = v_u_88.FiltersSection
        local v98 = v_u_49.FilterButtonProtos.ClearFilterButton:Clone()
        v98.Parent = v_u_49
        v_u_77 = v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, v98), p_u_46, function() --[[ Line: 337 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): v_u_48 ]]
            p_u_45._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_48:do_clear_filters()
        end)):set_auto_zoffset_behaviour(true)
        local function f_get_artist_select_state_flag() --[[ Name: get_artist_select_state_flag ]] --[[ Line: 344 ]]
            --[[ Upvalues: (ref 1): v_u_81, (ref 2): v_u_82, (ref 3): v_u_83 ]]
            return string.format("%s_%s_%s", v_u_81:get_current_text(), v_u_82:get_current_text(), v_u_83:get_current_text());
        end;
        local v99 = v_u_49.FilterButtonProtos.SelectArtistButton:Clone()
        v99.Parent = v_u_49
        v_u_78 = v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, v99), p_u_46, function() --[[ Line: 355 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): p_u_47, (ref 4): v_u_14, (ref 5): p_u_46, (ref 6): v_u_57, (ref 7): l_AllMySongs_0, (ref 8): v_u_2, (ref 9): v_u_10, (ref 10): v_u_15, (ref 11): v_u_83, (ref 12): v_u_84, (ref 13): v_u_44, (copy 14): f_get_artist_select_state_flag ]]
            p_u_45._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            local v_u_100 = nil
            v_u_100 = p_u_47:push_menu(v_u_14:new(p_u_45, p_u_46, p_u_47, function(p101) --[[ Line: 359 ]]
                --[[ Upvalues: (ref 1): v_u_57, (ref 2): l_AllMySongs_0, (ref 3): v_u_2, (ref 4): v_u_10, (ref 5): v_u_15 ]]
                p101:set_header_text("Select an artist...")
                if v_u_57:contains(l_AllMySongs_0) == true then
                    local v102 = v_u_2:new()
                    for v103, _ in v_u_57:get(l_AllMySongs_0):get_songkey_set():key_itr() do
                        local v104, v105 = v_u_15:artist_name_is_selectable((v_u_10:singleton():get_artist_for_key(v103)))
                        if v104 then
                            v102:add_set(v105)
                        end;
                    end;
                    local v106 = p101:get_element_list()
                    for v107, _ in v102:key_itr() do
                        v106:push_back(v107)
                    end;
                    v106:sort(function(p108, p109) --[[ Line: 375 ]]
                        return string.lower(p108) < string.lower(p109);
                    end)
                end;
            end, function(p110, p111, p112, _) --[[ Line: 379 ]]
                --[[ Upvalues: (ref 1): v_u_15 ]]
                p111.Text = p110
                local v113 = v_u_15:artist_name_to_icon(p110)
                if #v113 > 0 then
                    p112.Image = v113
                end;
            end, function(p114) --[[ Line: 386 ]]
                --[[ Upvalues: (ref 1): v_u_83, (ref 2): v_u_84, (ref 3): v_u_44, (ref 4): v_u_100, (ref 5): f_get_artist_select_state_flag ]]
                if p114 ~= nil then
                    v_u_83:set_text(p114)
                    v_u_84 = true
                end;
                v_u_44:on_list_select_save_page(v_u_100:get_list_adapter(), f_get_artist_select_state_flag())
            end))
            v_u_100:get_list_adapter():set_do_wrap(true)
            local v115 = string.lower(v_u_83:get_current_text())
            local v116 = v_u_100
            local v117 = ""
            for _, v118 in v_u_100:get_element_list():key_itr() do
                if string.lower(v118) == v115 then
                    v117 = v118
                    break;
                end;
            end;
            if #v117 > 0 then
                v116:get_list_adapter():go_to_page(v116:get_list_adapter():get_page_of_element(v117))
            else
                v_u_44:open_to_saved_page(v116:get_list_adapter(), f_get_artist_select_state_flag())
            end;
        end))
        local v119 = v_u_49.FilterButtonProtos.DifficultyUpButton:Clone()
        v119.Parent = v_u_49
        v_u_79 = v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, v119), p_u_46, function() --[[ Line: 418 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): v_u_48 ]]
            p_u_45._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_48:filter_on_change_difficulty(1)
        end)):set_auto_zoffset_behaviour(true)
        local v120 = v_u_49.FilterButtonProtos.DifficultyDownButton:Clone()
        v120.Parent = v_u_49
        v_u_80 = v_u_48:add_cycle_element(p_u_45, 1, v_u_5:new(v_u_4:new(v_u_48, v_u_49.PrimaryPart, v120), p_u_46, function() --[[ Line: 430 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_7, (ref 3): v_u_48 ]]
            p_u_45._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_48:filter_on_change_difficulty(-1)
        end)):set_auto_zoffset_behaviour(true)
        v_u_81 = v_u_12:new(p_u_45, v_u_76.NameInput.TextLabel, nil, v_u_48, p_u_46):set_empty_message("Search song name...."):set_send_behaviour_enabled(false):set_max_length(16)
        v_u_82 = v_u_12:new(p_u_45, v_u_76.DifficultyInput.TextLabel, nil, v_u_48, p_u_46):set_empty_message("(1)"):set_send_behaviour_enabled(false):set_max_length(2):enforce_numeric(true)
        v_u_83 = v_u_12:new(p_u_45, v_u_76.ArtistNameInput.TextLabel, nil, v_u_48, p_u_46):set_empty_message("Search artist..."):set_send_behaviour_enabled(false):set_max_length(16)
        v_u_81:set_text(v_u_38)
        v_u_82:set_text(v_u_40)
        v_u_83:set_text(v_u_42)
        v_u_48:raise_filter_changed()
        v_u_86 = v_u_26:new(p_u_45, v_u_48, v_u_49, v_u_49.SettingsItems, v_u_49.MainSurface.SurfaceGui.Frame.LoadedSection.SettingsSection)
        v_u_57:add(v_u_22.Recommended, v_u_23:new(p_u_45, v_u_48, v_u_49))
        v_u_57:add(v_u_22.AllMySongs, v_u_24:new(p_u_45, v_u_48, v_u_49))
        v_u_57:add(v_u_22.NowPlaying, v_u_25:new(p_u_45, v_u_48, v_u_49))
        for _, v121 in pairs(v_u_49.FilterButtonProtos:GetChildren()) do
            v121.Parent = nil
        end;
        v_u_48:update_selected_tab()
        v_u_48:transition_update_visual(0)
        v_u_48:layout()
        if v_u_10:singleton():contains_key(v_u_48:get_info_displayed_song_key()) then
            v_u_48:play_preview_for_songkey(v_u_48:get_info_displayed_song_key())
        end;
    end;
    v_u_48.do_clear_filters = function(_) --[[ Name: do_clear_filters ]] --[[ Line: 505 ]]
        --[[ Upvalues: (ref 1): v_u_81, (ref 2): v_u_82, (ref 3): v_u_83, (copy 4): v_u_57, (ref 5): l_AllMySongs_0, (ref 6): v_u_84 ]]
        v_u_81:set_text("")
        v_u_82:set_text("")
        v_u_83:set_text("")
        if v_u_57:contains(l_AllMySongs_0) then
            v_u_57:get(l_AllMySongs_0):on_clear_filter()
        end;
        v_u_84 = true
    end;
    v_u_48.get_current_infostate = function(_) --[[ Name: get_current_infostate ]] --[[ Line: 515 ]]
        --[[ Upvalues: (ref 1): v_u_32, (ref 2): l_AllMySongs_0, (ref 3): v_u_31 ]]
        if v_u_32:contains(l_AllMySongs_0) ~= true then
            v_u_32:add(l_AllMySongs_0, v_u_31.InfoState:new())
        end;
        return v_u_32:get(l_AllMySongs_0);
    end;
    v_u_48.get_page = function(p122) --[[ Name: get_page ]] --[[ Line: 522 ]]
        return p122:get_current_infostate():get_page();
    end;
    v_u_48.set_page = function(p123, p124) --[[ Name: set_page ]] --[[ Line: 523 ]]
        p123:get_current_infostate():set_page(p124)
    end;
    v_u_48.is_loading = function(_) --[[ Name: is_loading ]] --[[ Line: 525 ]]
        --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_31 ]]
        return l_Loading_0 == v_u_31.State.Loading;
    end;
    v_u_48.set_loading = function(p125, p126) --[[ Name: set_loading ]] --[[ Line: 526 ]]
        --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_31, (ref 3): v_u_89, (ref 4): v_u_88, (ref 5): v_u_77, (ref 6): v_u_78, (ref 7): v_u_79, (ref 8): v_u_80, (copy 9): v_u_57, (ref 10): l_AllMySongs_0, (ref 11): v_u_86, (ref 12): v_u_68, (ref 13): v_u_69, (ref 14): v_u_71, (ref 15): v_u_73, (copy 16): v_u_75 ]]
        if p126 == true then
            l_Loading_0 = v_u_31.State.Loading
            v_u_89.Visible = true
            v_u_88.Visible = false
            v_u_77:set_visible(false)
            v_u_78:set_visible(false)
            v_u_79:set_visible(false)
            v_u_80:set_visible(false)
            v_u_68:set_visible(false)
            v_u_69:set_visible(false)
            v_u_71:set_visible(false)
            v_u_73:set_visible(false)
            for _, v127 in v_u_75:key_itr() do
                v127:set_visible(false)
            end;
            for _, v128 in v_u_57:key_itr() do
                v128:set_visible(false)
            end;
            v_u_86:set_visible(false)
        else
            l_Loading_0 = v_u_31.State.Loaded
            v_u_89.Visible = false
            v_u_88.Visible = true
            v_u_77:set_visible(true)
            v_u_78:set_visible(true)
            v_u_79:set_visible(true)
            v_u_80:set_visible(true)
            for v129, v130 in v_u_57:key_itr() do
                if v129 == l_AllMySongs_0 then
                    v130:set_visible(true)
                else
                    v130:set_visible(false)
                end;
            end;
            v_u_86:set_visible(true)
            p125:opt_update_info_section()
        end;
        p125:update_page_display()
    end;
    v_u_48.reset_page = function(p131) --[[ Name: reset_page ]] --[[ Line: 567 ]]
        p131:set_page(0)
        p131:update_page_display()
    end;
    v_u_48.update_selected_tab = function(p132) --[[ Name: update_selected_tab ]] --[[ Line: 571 ]]
        --[[ Upvalues: (copy 1): v_u_56, (ref 2): l_AllMySongs_0, (ref 3): v_u_1, (copy 4): v_u_57 ]]
        for v133, v134 in v_u_56:key_itr() do
            if v133 == l_AllMySongs_0 then
                v134:get_part().SurfaceGui.Frame.Tab_Container.Image = v_u_1:get_tab_selected_container_assetid()
                v134:set_unselected_zoffset(300)
            else
                v134:get_part().SurfaceGui.Frame.Tab_Container.Image = v_u_1:get_tab_unselected_container_assetid()
                v134:set_unselected_zoffset(200)
            end;
        end;
        for v135, v136 in v_u_57:key_itr() do
            if v135 ~= l_AllMySongs_0 then
                v136:set_visible(false)
            end;
        end;
        p132:load_current_tab()
    end;
    local v_u_137 = -1
    v_u_48.load_current_tab = function(p_u_138) --[[ Name: load_current_tab ]] --[[ Line: 591 ]]
        --[[ Upvalues: (copy 1): v_u_57, (ref 2): l_AllMySongs_0, (ref 3): v_u_137, (copy 4): p_u_45, (ref 5): v_u_10 ]]
        if v_u_57:contains(l_AllMySongs_0) then
            v_u_137 = p_u_45._player_blob_manager:get_global_time_float()
            local v_u_139 = v_u_137
            local v140 = v_u_57:get(l_AllMySongs_0)
            p_u_138:set_loading(true)
            v140:load_data(function() --[[ Line: 598 ]]
                --[[ Upvalues: (copy 1): v_u_139, (ref 2): v_u_137, (copy 3): p_u_138, (ref 4): v_u_10 ]]
                if v_u_139 == v_u_137 then
                    p_u_138:set_loading(false)
                    p_u_138:refresh_current_page()
                    if p_u_138:get_info_displayed_song_key() ~= v_u_10:invalid_songkey() then
                        p_u_138:show_info_for_songkey(p_u_138:get_info_displayed_song_key())
                    end;
                end;
            end)
        end;
    end;
    v_u_48.refresh_current_page = function(p141) --[[ Name: refresh_current_page ]] --[[ Line: 609 ]]
        --[[ Upvalues: (copy 1): v_u_57, (ref 2): l_AllMySongs_0 ]]
        p141:set_loading(false)
        if v_u_57:contains(l_AllMySongs_0) then
            local v142 = v_u_57:get(l_AllMySongs_0)
            v142:refresh()
            if p141:get_page() >= v142:get_page_total() then
                p141:set_page(0)
                v142:refresh()
            end;
            p141:update_page_display()
        end;
    end;
    v_u_48.update_page_display = function(p143) --[[ Name: update_page_display ]] --[[ Line: 622 ]]
        --[[ Upvalues: (ref 1): v_u_54, (ref 2): v_u_55, (ref 3): v_u_52, (ref 4): v_u_53, (ref 5): v_u_58, (ref 6): v_u_87, (ref 7): v_u_85, (copy 8): v_u_57, (ref 9): l_AllMySongs_0, (copy 10): p_u_45, (ref 11): v_u_9 ]]
        if p143:is_loading() then
            v_u_54.Text = "-"
            v_u_55.Text = "-"
            v_u_52:set_visible(false)
            v_u_53:set_visible(false)
            v_u_58.Visible = false
            v_u_87:set_visible(false)
            v_u_85.Visible = false
            return;
        elseif v_u_57:contains(l_AllMySongs_0) then
            local v144 = v_u_57:get(l_AllMySongs_0):get_page_total()
            if v144 > 0 then
                v_u_54.Text = string.format("%d", p143:get_page() + 1)
                v_u_55.Text = string.format("%d", v144)
                v_u_52:set_visible(v144 > 1)
                v_u_53:set_visible(v144 > 1)
                v_u_85.Visible = false
            else
                v_u_54.Text = "-"
                v_u_55.Text = "-"
                v_u_52:set_visible(false)
                v_u_53:set_visible(false)
                v_u_85.Visible = true
            end;
            v_u_58.Visible = true
            v_u_87:set_visible(v_u_9:playerblob_has_vip_for_current_day(p_u_45._player_blob_manager:get_player_blob(), p_u_45:get_current_dayid()) ~= true)
        else
            v_u_54.Text = "-"
            v_u_55.Text = "-"
            v_u_52:set_visible(false)
            v_u_53:set_visible(false)
            v_u_58.Visible = false
            v_u_87:set_visible(false)
            v_u_85.Visible = false
        end;
    end;
    v_u_48.get_info_displayed_song_key = function(p145) --[[ Name: get_info_displayed_song_key ]] --[[ Line: 666 ]]
        return p145:get_current_infostate():get_info_displayed_song_key();
    end;
    v_u_48.set_info_displayed_song_key = function(p146, p147) --[[ Name: set_info_displayed_song_key ]] --[[ Line: 667 ]]
        p146:get_current_infostate():set_info_displayed_song_key(p147)
    end;
    local v_u_148 = -1
    v_u_48.opt_update_info_section = function(p149) --[[ Name: opt_update_info_section ]] --[[ Line: 670 ]]
        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_148, (copy 3): p_u_45, (ref 4): v_u_68, (ref 5): v_u_59, (ref 6): v_u_18, (ref 7): v_u_70, (ref 8): v_u_15, (ref 9): v_u_74, (ref 10): v_u_72, (ref 11): v_u_1, (ref 12): v_u_61, (ref 13): v_u_62, (ref 14): v_u_13, (ref 15): v_u_63, (ref 16): v_u_60, (ref 17): v_u_66, (ref 18): v_u_65, (ref 19): v_u_67, (ref 20): v_u_64, (ref 21): v_u_21, (ref 22): v_u_73, (ref 23): v_u_30, (ref 24): v_u_69, (ref 25): v_u_71, (copy 26): v_u_75, (ref 27): v_u_9, (ref 28): v_u_28, (ref 29): v_u_16 ]]
        if p149:is_loading() then
            return;
        else
            local v150 = p149:get_info_displayed_song_key()
            if v_u_10:singleton():contains_key(v150) and (v_u_148 ~= p_u_45._player_song_stats_manager:get_time_last_update() or v_u_68:get_visible() ~= true) then
                v_u_148 = p_u_45._player_song_stats_manager:get_time_last_update()
                v_u_59.Text = v_u_10:singleton():get_title_for_key(v150)
                local v151, v152 = v_u_18:songkey_has_special_info_text(v150)
                v_u_70.Visible = v151
                if v151 then
                    v_u_70.Text = v152
                end;
                local v153, v154 = v_u_15:artist_name_is_selectable(v_u_10:singleton():get_artist_for_key(v150))
                if v153 then
                    v_u_74 = v154
                    v_u_72.Image = v_u_15:artist_name_to_icon(v154)
                else
                    v_u_74 = ""
                    v_u_72.Image = v_u_1:transparent_assetid()
                end;
                v_u_10:singleton():render_coverimage_for_key(v_u_61, v_u_62, v150)
                v_u_13:render_songkey_colorsection(v150, v_u_63)
                v_u_60.Image = v_u_1:semitransparent_assetid()
                v_u_66.Text = p_u_45._player_song_stats_manager:get_best_score_display_str(v150)
                v_u_65.Text = p_u_45._player_song_stats_manager:get_rank_display_str(v150)
                v_u_67.Text = p_u_45._player_song_stats_manager:get_playcount_display_str(v150)
                local v155, v156 = p_u_45._player_song_stats_manager:get_best_grade_rank_value(v150)
                if v156 > 0 then
                    v_u_64.Image = v_u_21:get_rank_value_icon(v155)
                    v_u_64.Visible = true
                else
                    v_u_64.Visible = false
                end;
                v_u_68:set_visible(true)
                v_u_73:set_visible(v_u_30:can_show_editor_menu_for_songkey(v150))
                local v157 = p_u_45._player_blob_manager:get_player_blob()
                v_u_69:set_default_selected_songkey(v150)
                if #v_u_74 > 0 then
                    v_u_71:set_visible(true)
                else
                    v_u_71:set_visible(false)
                end;
                local v158 = v_u_10:singleton():key_get_audiomod(v150)
                local v159 = v_u_10:singleton():get_audiomod_to_modes_of_songkey(v150)
                for v160, v161 in v_u_75:key_itr() do
                    v161:set_visible(true)
                    local l_Toggle_0 = v161:get_bound_data().Toggle
                    local l_DifficultyDisplay_0 = v161:get_bound_data().DifficultyDisplay
                    if v159:contains(v160) then
                        local v162 = v159:get(v160)
                        v161:get_bound_data().TargetSongKey = v162
                        l_DifficultyDisplay_0.Text = tostring((v_u_10:singleton():get_difficulty_for_key(v162)))
                        l_DifficultyDisplay_0.TextColor3 = v_u_10:singleton():get_difficulty_color_for_key(v162)
                        local v163 = v_u_9:playerblob_has_access_to_song(p_u_45._player_blob_manager:get_player_blob(), v162, p_u_45:get_current_dayid(), p_u_45._player_blob_manager:get_cached_collection_info())
                        local v164 = v_u_28:get_songkey_recipe_id(v162)
                        if v163 then
                            v161:set_enabled(true)
                            l_Toggle_0:set_toggle(true)
                        elseif v164 == nil then
                            v161:set_enabled(false)
                            l_Toggle_0:set_toggle_off_alpha(0.2)
                            l_Toggle_0:set_toggle(false)
                        elseif v_u_16:can_craft_recipe(v157, v164) then
                            v161:set_enabled(true)
                            l_Toggle_0:set_toggle_off_alpha(0.6)
                            l_Toggle_0:set_toggle(false)
                        else
                            v161:set_enabled(false)
                            l_Toggle_0:set_toggle_off_alpha(0.2)
                            l_Toggle_0:set_toggle(false)
                        end;
                        if v158 == v160 then
                            v161:set_scale(1.35)
                            v161:set_unselected_zoffset(750)
                            v161:set_passive_anim(true)
                        else
                            v161:set_scale(0.85)
                            v161:set_unselected_zoffset(500)
                            v161:set_passive_anim(false)
                        end;
                    else
                        v161:get_bound_data().TargetSongKey = v_u_10:invalid_songkey()
                        l_DifficultyDisplay_0.Text = "-"
                        l_DifficultyDisplay_0.TextColor3 = Color3.new(1, 1, 1)
                        v161:set_enabled(false)
                        l_Toggle_0:set_toggle_off_alpha(0.25)
                        l_Toggle_0:set_toggle(false)
                        v161:set_scale(0.85)
                        v161:set_unselected_zoffset(500)
                    end;
                end;
            elseif v150 == v_u_10:invalid_songkey() then
                v_u_59.Text = "Click on a song to view info."
                v_u_74 = ""
                v_u_72.Image = v_u_1:transparent_assetid()
                v_u_70.Visible = false
                v_u_61.Image = v_u_1:transparent_assetid()
                v_u_62.Image = v_u_1:transparent_assetid()
                v_u_60.Image = v_u_1:transparent_assetid()
                v_u_63.Visible = false
                v_u_68:set_visible(false)
                v_u_69:set_visible(false)
                v_u_71:set_visible(false)
                v_u_73:set_visible(false)
                for _, v165 in v_u_75:key_itr() do
                    v165:set_visible(false)
                end;
                v_u_66.Text = "-"
                v_u_65.Text = ""
                v_u_67.Text = "-"
                v_u_64.Visible = false
            end;
        end;
    end;
    v_u_48.hide_info_section = function(p166) --[[ Name: hide_info_section ]] --[[ Line: 808 ]]
        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_148 ]]
        p166:set_info_displayed_song_key(v_u_10:invalid_songkey())
        v_u_148 = -1
        p166:opt_update_info_section()
    end;
    v_u_48.show_info_for_songkey = function(p167, p168) --[[ Name: show_info_for_songkey ]] --[[ Line: 814 ]]
        --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_45, (ref 3): v_u_148 ]]
        if v_u_10:singleton():contains_key(p168) then
            p_u_45._game_join:set_last_loaded_songkey(p168)
        end;
        p_u_45._player_song_stats_manager:request_ranks_for_songkey(p168)
        p167:set_info_displayed_song_key(p168)
        v_u_148 = -1
        p167:opt_update_info_section()
    end;
    v_u_48.show_info_displayed_description_popup = function(p169) --[[ Name: show_info_displayed_description_popup ]] --[[ Line: 824 ]]
        --[[ Upvalues: (ref 1): v_u_19, (copy 2): p_u_45 ]]
        v_u_19:show_song_info_popup(p_u_45, (p169:get_info_displayed_song_key()))
    end;
    v_u_48.play_preview_for_songkey = function(_, p170) --[[ Name: play_preview_for_songkey ]] --[[ Line: 829 ]]
        --[[ Upvalues: (copy 1): p_u_45 ]]
        p_u_45._bgm_manager:preview_songkey(p170)
    end;
    v_u_48.select_songkey = function(p_u_171, p_u_172) --[[ Name: select_songkey ]] --[[ Line: 834 ]]
        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_6, (copy 3): p_u_45, (ref 4): v_u_9, (ref 5): v_u_28, (ref 6): v_u_16, (ref 7): l_AllMySongs_0, (ref 8): v_u_22, (copy 9): v_u_57 ]]
        if v_u_10:singleton():contains_key(p_u_172) ~= true then
            return v_u_6:warnf("PlayUI:select_songkey(%s) does not contain", (tostring(p_u_172)));
        end;
        local v173 = p_u_45._player_blob_manager:get_player_blob()
        local v174 = v_u_9:playerblob_has_access_to_song(p_u_45._player_blob_manager:get_player_blob(), p_u_172, p_u_45:get_current_dayid(), p_u_45._player_blob_manager:get_cached_collection_info())
        local v175 = v_u_28:get_songkey_recipe_id(p_u_172)
        local v176
        if v175 == nil then
            v176 = false
        else
            v176 = v_u_16:can_craft_recipe(v173, v175)
        end;
        if v174 then
            l_AllMySongs_0 = v_u_22.AllMySongs
            p_u_171:update_selected_tab()
            local v177 = v_u_57:get(v_u_22.AllMySongs)
            if v177:songkey_selected(p_u_172) then
                p_u_171:show_info_for_songkey(p_u_172)
                v177:update_play_button()
                return;
            end;
        elseif v176 then
            p_u_45._menus:push_menu(v_u_28:new(p_u_45, p_u_45._spui, p_u_45._menus, p_u_172, function() --[[ Line: 861 ]]
                --[[ Upvalues: (copy 1): p_u_171, (copy 2): p_u_172 ]]
                p_u_171:select_songkey(p_u_172)
            end))
        end;
    end;
    v_u_48.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 867 ]]
        --[[ Upvalues: (copy 1): p_u_45, (copy 2): v_u_57, (ref 3): v_u_90, (ref 4): v_u_49 ]]
        p_u_45._player_status_manager:set_playerlist_info_update_subscribed(false)
        for _, v178 in v_u_57:key_itr() do
            v178:set_visible(false)
        end;
        p_u_45._bgm_manager:stop_song_preview(v_u_90)
        v_u_49:Destroy()
    end;
    v_u_48.on_refocus = function(p179) --[[ Name: on_refocus ]] --[[ Line: 876 ]]
        --[[ Upvalues: (copy 1): v_u_57, (ref 2): l_AllMySongs_0, (ref 3): v_u_10 ]]
        if v_u_57:contains(l_AllMySongs_0) and v_u_57:get(l_AllMySongs_0):requires_reload_on_menu_refocus() then
            p179:load_current_tab()
        else
            p179:refresh_current_page()
        end;
        if v_u_10:singleton():contains_key(p179:get_info_displayed_song_key()) then
            p179:play_preview_for_songkey(p179:get_info_displayed_song_key())
            p179:opt_update_info_section()
        end;
    end;
    v_u_48.behaviour_update = function(p180, p181, _) --[[ Name: behaviour_update ]] --[[ Line: 889 ]]
        --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_81, (ref 3): v_u_40, (ref 4): v_u_82, (ref 5): v_u_42, (ref 6): v_u_83, (ref 7): l_Loading_0, (ref 8): v_u_31, (copy 9): v_u_57, (ref 10): l_AllMySongs_0, (copy 11): p_u_45 ]]
        v_u_38 = v_u_81:get_current_text()
        v_u_40 = v_u_82:get_current_text()
        v_u_42 = v_u_83:get_current_text()
        if l_Loading_0 == v_u_31.State.Loaded then
            v_u_81:update(p181)
            v_u_82:update(p181)
            v_u_83:update(p181)
            if v_u_57:contains(l_AllMySongs_0) then
                v_u_57:get(l_AllMySongs_0):behaviour_update(p181)
                if p180:raise_filter_changed() then
                    p180:reset_page()
                    p180:hide_info_section()
                    p180:refresh_current_page()
                end;
            end;
        end;
        p180:opt_update_info_section()
        p180:behaviour_update_base(p181, p_u_45)
    end;
    v_u_48.get_filter_search_name = function(_) --[[ Name: get_filter_search_name ]] --[[ Line: 915 ]]
        --[[ Upvalues: (ref 1): v_u_81 ]]
        return v_u_81:get_current_text();
    end;
    v_u_48.get_filter_artist_name = function(_) --[[ Name: get_filter_artist_name ]] --[[ Line: 919 ]]
        --[[ Upvalues: (ref 1): v_u_83 ]]
        return v_u_83:get_current_text();
    end;
    v_u_48.get_filter_search_difficulty = function(_) --[[ Name: get_filter_search_difficulty ]] --[[ Line: 923 ]]
        --[[ Upvalues: (ref 1): v_u_82, (ref 2): v_u_1 ]]
        local v182 = tonumber((v_u_82:get_current_text()))
        return v_u_1:is_finite(v182) == false and -100 or v182;
    end;
    v_u_48.filter_on_change_difficulty = function(_, p183) --[[ Name: filter_on_change_difficulty ]] --[[ Line: 930 ]]
        --[[ Upvalues: (copy 1): v_u_57, (ref 2): l_AllMySongs_0, (ref 3): v_u_82, (ref 4): v_u_1 ]]
        if v_u_57:contains(l_AllMySongs_0) then
            local v184 = v_u_57:get(l_AllMySongs_0):get_max_difficulty()
            local v185 = tonumber(v_u_82:get_current_text())
            local v186 = (v_u_1:is_finite(v185) == false and 1 or v185) + p183
            if v186 > 0 then
                v184 = v184 < v186 and 1 or v186
            end;
            v_u_82:set_text((tostring(v184)))
            v_u_57:get(l_AllMySongs_0):on_filter_change_difficulty(v184)
        end;
    end;
    v_u_48.raise_filter_changed = function(_) --[[ Name: raise_filter_changed ]] --[[ Line: 949 ]]
        --[[ Upvalues: (ref 1): v_u_84, (ref 2): v_u_81, (ref 3): v_u_82, (ref 4): v_u_83 ]]
        local v187 = v_u_84
        v_u_84 = false
        return v187 or (v_u_81:raise_changed() or (v_u_82:raise_changed() or v_u_83:raise_changed()));
    end;
    v_u_48.layout = function(p188) --[[ Name: layout ]] --[[ Line: 958 ]]
        --[[ Upvalues: (copy 1): p_u_46, (ref 2): v_u_51, (ref 3): v_u_49, (copy 4): v_u_57 ]]
        p188:opt_rescale_to_max_nxy(p_u_46, 0.9, 0.9, v_u_51)
        local v189, v190 = p188:opt_update_cframe_params(p_u_46, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p188:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v189 == true then
            v_u_49:SetPrimaryPartCFrame(v190)
        end;
        for _, v191 in v_u_57:key_itr() do
            v191:layout()
        end;
    end;
    v_u_48.set_alpha = function(_, p192) --[[ Name: set_alpha ]] --[[ Line: 974 ]]
        --[[ Upvalues: (ref 1): v_u_50, (ref 2): v_u_1, (ref 3): v_u_49 ]]
        if v_u_50 ~= p192 then
            v_u_50 = p192
            v_u_1:r_set_alpha(v_u_49, v_u_50)
        end;
    end;
    v_u_48.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 980 ]]
        --[[ Upvalues: (ref 1): v_u_50 ]]
        return v_u_50;
    end;
    v_u_48.set_scale = function(_, p193) --[[ Name: set_scale ]] --[[ Line: 981 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        v_u_51 = p193
    end;
    v_u_48.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 982 ]]
        --[[ Upvalues: (ref 1): v_u_51 ]]
        return v_u_51;
    end;
    v_u_48.get_native_size = function(p194) --[[ Name: get_native_size ]] --[[ Line: 984 ]]
        return p194._native_size;
    end;
    v_u_48.get_size = function(p195) --[[ Name: get_size ]] --[[ Line: 987 ]]
        return p195._size;
    end;
    v_u_48.set_size = function(p196, p197) --[[ Name: set_size ]] --[[ Line: 990 ]]
        --[[ Upvalues: (ref 1): v_u_49 ]]
        p196._size = p197
        v_u_49.PrimaryPart.Size = Vector3.new(p197.X, p197.Y, 0)
    end;
    v_u_48.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 994 ]]
        --[[ Upvalues: (ref 1): v_u_49 ]]
        return v_u_49.PrimaryPart.Position;
    end;
    v_u_48.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 997 ]]
        --[[ Upvalues: (ref 1): v_u_49 ]]
        return v_u_49.PrimaryPart.SurfaceGui;
    end;
    v_u_48.set_showing = function(_, p198) --[[ Name: set_showing ]] --[[ Line: 1000 ]]
        --[[ Upvalues: (ref 1): v_u_49, (ref 2): v_u_8 ]]
        if p198 then
            v_u_49.Parent = v_u_8:get_world_ui_folder()
        else
            v_u_49.Parent = nil
        end;
    end;
    f_cons()
    return v_u_48;
end;
return v_u_31;
