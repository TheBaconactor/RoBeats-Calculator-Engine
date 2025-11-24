-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:39 PM
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
require(game.ReplicatedStorage.Shared.ListAdapter)
require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_17 = require(game.ReplicatedStorage.AudioData.SongSpecialInfo)
local v_u_18 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
local v_u_19 = require(game.ReplicatedStorage.AudioData.AudioMod)
local v_u_20 = require(game.ReplicatedStorage.Shared.AudioRank)
local v_u_21 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITab)
local v_u_22 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUITabController_AllMySongs)
local v23 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_24 = nil
local v_u_25 = nil
local v_u_26 = nil
v23:require_client(function() --[[ Line: 41 ]]
    --[[ Upvalues: (ref 1): v_u_24, (ref 2): v_u_25, (ref 3): v_u_26 ]]
    v_u_24 = require(game.ReplicatedStorage.Lobby.Menus.CraftSongUI)
    v_u_25 = require(game.ReplicatedStorage.Lobby.UI.SongFavoriteButton)
    v_u_26 = require(game.ReplicatedStorage.Lobby.Menus.PlayUI)
end)
local v_u_27 = {
    ["State"] = {
        ["Loading"] = 1,
        ["Loaded"] = 2
    },
    ["get_restore_menu_name"] = function(_) --[[ Name: get_restore_menu_name ]] --[[ Line: 57 ]]
        return "SongSelectV3UI";
    end,
    ["create_info_state"] = function(_) --[[ Name: create_info_state ]] --[[ Line: 59 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26.InfoState:new();
    end
}
local l_AllMySongs_0 = v_u_21.AllMySongs
v_u_27.new = function(_, p_u_28, p_u_29, p_u_30, p_u_31, p_u_32) --[[ Name: new ]] --[[ Line: 61 ]]
    --[[ Upvalues: (copy 1): v_u_27, (copy 2): v_u_3, (copy 3): v_u_2, (copy 4): v_u_1, (copy 5): v_u_8, (copy 6): v_u_5, (copy 7): v_u_4, (copy 8): v_u_7, (ref 9): l_AllMySongs_0, (ref 10): v_u_26, (copy 11): v_u_11, (ref 12): v_u_25, (copy 13): v_u_10, (copy 14): v_u_19, (copy 15): v_u_14, (copy 16): v_u_15, (copy 17): v_u_12, (copy 18): v_u_21, (copy 19): v_u_22, (copy 20): v_u_9, (copy 21): v_u_17, (copy 22): v_u_13, (copy 23): v_u_20, (ref 24): v_u_24, (copy 25): v_u_16, (copy 26): v_u_18, (copy 27): v_u_6 ]]
    if p_u_29 == nil then
        p_u_29 = v_u_27:create_info_state()
    end;
    local l__spui_0 = p_u_28._spui
    local l__menus_0 = p_u_28._menus
    local v_u_33 = v_u_3:new(l__spui_0, l__menus_0)
    v_u_33.get_restore_name = function(_) --[[ Name: get_restore_name ]] --[[ Line: 76 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27:get_restore_menu_name();
    end;
    local v_u_34 = nil
    local v_u_35 = 1
    local v_u_36 = 1
    local v_u_37 = nil
    local v_u_38 = nil
    local v_u_39 = nil
    local v_u_40 = nil
    local v_u_41 = v_u_2:new()
    local v_u_42 = nil
    local v_u_43 = nil
    local v_u_44 = nil
    local v_u_45 = nil
    local v_u_46 = nil
    local v_u_47 = nil
    local v_u_48 = nil
    local v_u_49 = nil
    local v_u_50 = nil
    local v_u_51 = nil
    local v_u_52 = nil
    local v_u_53 = nil
    local v_u_54 = nil
    local v_u_55 = nil
    local v_u_56 = nil
    local v_u_57 = ""
    local v_u_58 = v_u_2:new()
    local v_u_59 = nil
    local v_u_60 = nil
    local v_u_61 = nil
    local v_u_62 = nil
    local v_u_63 = nil
    local v_u_64 = nil
    local v_u_65 = nil
    local v_u_66 = nil
    local v_u_67 = false
    local v_u_68 = nil
    local v_u_69 = nil
    local l_Loading_0 = v_u_27.State.Loading
    local v_u_70 = nil
    local v_u_71 = nil
    local v_u_72 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 111 ]]
        --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_1, (ref 3): v_u_8, (ref 4): v_u_72, (copy 5): p_u_28, (copy 6): v_u_33, (ref 7): v_u_5, (ref 8): v_u_4, (copy 9): l__spui_0, (ref 10): v_u_7, (copy 11): l__menus_0, (ref 12): v_u_37, (copy 13): v_u_41, (ref 14): l_AllMySongs_0, (ref 15): v_u_26, (ref 16): v_u_38, (ref 17): v_u_69, (ref 18): v_u_11, (ref 19): v_u_71, (ref 20): v_u_70, (ref 21): v_u_39, (ref 22): v_u_40, (ref 23): v_u_68, (ref 24): v_u_42, (ref 25): v_u_43, (ref 26): v_u_54, (ref 27): v_u_44, (ref 28): v_u_45, (ref 29): v_u_47, (ref 30): v_u_46, (ref 31): v_u_48, (ref 32): v_u_49, (ref 33): v_u_50, (ref 34): v_u_51, (ref 35): v_u_52, (ref 36): v_u_53, (ref 37): v_u_25, (ref 38): v_u_56, (ref 39): v_u_55, (ref 40): v_u_57, (ref 41): v_u_66, (ref 42): v_u_10, (copy 43): v_u_58, (ref 44): v_u_19, (ref 45): v_u_59, (ref 46): v_u_60, (ref 47): v_u_64, (ref 48): v_u_65, (ref 49): v_u_61, (ref 50): v_u_14, (ref 51): v_u_2, (copy 52): p_u_30, (ref 53): v_u_15, (ref 54): v_u_67, (ref 55): v_u_62, (ref 56): v_u_63, (ref 57): v_u_12, (ref 58): v_u_21, (ref 59): v_u_22, (copy 60): p_u_31, (copy 61): p_u_32 ]]
        v_u_34 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Util.SongSelectV3UI:Clone()
        v_u_34.Name = v_u_1:gen_name(v_u_34.Name)
        v_u_34.Parent = v_u_8:get_world_ui_folder()
        v_u_72 = p_u_28._bgm_manager:begin_preview_songkey()
        v_u_33._native_size = v_u_34.PrimaryPart.Size
        v_u_33._size = v_u_33._native_size
        v_u_33:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(v_u_33, v_u_34.PrimaryPart, v_u_34.BackButtonSurface), l__spui_0, function() --[[ Line: 124 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_7, (ref 3): l__menus_0, (ref 4): v_u_33 ]]
            p_u_28._sfx_manager:play_sfx(v_u_7.SFX_MENU_CLOSE)
            l__menus_0:remove_menu(v_u_33)
        end))
        v_u_37 = v_u_33:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(v_u_33, v_u_34.PrimaryPart, v_u_34.ArrowLeft), l__spui_0, function() --[[ Line: 133 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_7, (ref 3): v_u_41, (ref 4): l_AllMySongs_0, (ref 5): v_u_33, (ref 6): v_u_26 ]]
            p_u_28._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            if v_u_41:contains(l_AllMySongs_0) then
                local v73 = v_u_41:get(l_AllMySongs_0)
                v_u_33:set_page(v_u_33:get_page() - 1)
                if v_u_33:get_page() < v_u_26:get_page_first() then
                    v_u_33:set_page(v73:get_page_total() - 1)
                end;
                v_u_33:refresh_current_page()
            end;
        end))
        v_u_38 = v_u_33:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(v_u_33, v_u_34.PrimaryPart, v_u_34.ArrowRight), l__spui_0, function() --[[ Line: 149 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_7, (ref 3): v_u_41, (ref 4): l_AllMySongs_0, (ref 5): v_u_33, (ref 6): v_u_26 ]]
            p_u_28._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            if v_u_41:contains(l_AllMySongs_0) then
                local v74 = v_u_41:get(l_AllMySongs_0)
                v_u_33:set_page(v_u_33:get_page() + 1)
                if v_u_33:get_page() >= v74:get_page_total() then
                    v_u_33:set_page(v_u_26:get_page_first())
                end;
                v_u_33:refresh_current_page()
            end;
        end))
        v_u_69 = v_u_33:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(v_u_33, v_u_34.PrimaryPart, v_u_34.VIPButton), l__spui_0, function() --[[ Line: 165 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_7, (ref 3): l__menus_0, (ref 4): v_u_11, (ref 5): l__spui_0, (ref 6): v_u_33 ]]
            p_u_28._sfx_manager:play_sfx(v_u_7.SFX_MENU_OPEN)
            l__menus_0:push_menu(v_u_11:new(p_u_28, l__spui_0, l__menus_0))
            v_u_33:set_loading(true)
        end))
        v_u_69:set_visible(false)
        v_u_71 = v_u_34.MainSurface.SurfaceGui.Frame.LoadingSection
        v_u_70 = v_u_34.MainSurface.SurfaceGui.Frame.LoadedSection
        v_u_39 = v_u_70.PageDisplaySection.CurrentPageDisplay
        v_u_40 = v_u_70.PageDisplaySection.MaxPageDisplay
        v_u_68 = v_u_70.NoResultsText
        v_u_68.Visible = false
        local l_InfoSection_0 = v_u_70.InfoSection
        v_u_42 = l_InfoSection_0
        v_u_43 = l_InfoSection_0.NameDisplay
        v_u_54 = l_InfoSection_0.SpecialTextDisplay
        v_u_54.Visible = false
        v_u_44 = l_InfoSection_0.CoverBack
        v_u_45 = l_InfoSection_0.CoverBack.AlbumArt
        v_u_47 = l_InfoSection_0.CoverBack.ColorSection
        v_u_46 = l_InfoSection_0.CoverBack.AlbumArtOverlay
        v_u_48 = l_InfoSection_0.CoverBack.RankDisplay
        v_u_49 = l_InfoSection_0.RankDisplay
        v_u_50 = l_InfoSection_0.BestScoreDisplay
        v_u_51 = l_InfoSection_0.TimesPlayedDisplay
        v_u_52 = v_u_33:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(v_u_33, v_u_34.PrimaryPart, v_u_34.SongInfoButtons.InfoButton), l__spui_0, function() --[[ Line: 196 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_7, (ref 3): v_u_33 ]]
            p_u_28._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_33:show_info_displayed_description_popup()
        end):set_auto_zoffset_behaviour(true))
        v_u_52:set_visible(false)
        v_u_53 = v_u_25:new(p_u_28, v_u_33, v_u_4:new(v_u_33, v_u_34.PrimaryPart, v_u_34.SongInfoButtons.FavoriteButton), v_u_34.SongInfoButtons.FavoriteButton.SurfaceGui.Button.Icon)
        v_u_56 = v_u_34.SongInfoButtons.ArtistButton.SurfaceGui.Icon
        v_u_55 = v_u_33:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(v_u_33, v_u_34.PrimaryPart, v_u_34.SongInfoButtons.ArtistButton), l__spui_0, function() --[[ Line: 214 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_7, (ref 3): v_u_57, (ref 4): v_u_33, (ref 5): v_u_66, (ref 6): v_u_10 ]]
            p_u_28._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            if typeof(v_u_57) == "string" and #v_u_57 > 0 then
                local v75 = v_u_33:get_info_displayed_song_key()
                if v_u_66:get_current_text() == v_u_57 then
                    v_u_66:set_text("")
                else
                    v_u_66:set_text(v_u_57)
                end;
                v_u_33:reset_page()
                v_u_33:refresh_current_page()
                v_u_66:raise_changed()
                if v_u_10:singleton():contains_key(v75) then
                    v_u_33:select_songkey(v75)
                end;
            end;
        end):set_auto_zoffset_behaviour(true))
        v_u_55:set_visible(false)
        local function f_create_info_to_audiomod_button(p76, p77) --[[ Name: create_info_to_audiomod_button ]] --[[ Line: 236 ]]
            --[[ Upvalues: (ref 1): v_u_33, (ref 2): p_u_28, (ref 3): v_u_5, (ref 4): v_u_4, (ref 5): v_u_34, (ref 6): l__spui_0, (ref 7): v_u_7, (ref 8): v_u_10, (ref 9): v_u_58 ]]
            local v_u_78 = nil
            v_u_78 = v_u_33:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(v_u_33, v_u_34.PrimaryPart, p77), l__spui_0, function() --[[ Line: 241 ]]
                --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_7, (ref 3): v_u_33, (ref 4): v_u_78 ]]
                p_u_28._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
                v_u_33:select_songkey(v_u_78:get_bound_data().TargetSongKey)
            end):set_auto_zoffset_behaviour(true))
            v_u_78:bind_data({
                ["Toggle"] = v_u_5:button_bind_anim_toggle(v_u_78, function() --[[ Line: 247 ]]
                    --[[ Upvalues: (ref 1): v_u_33 ]]
                    return v_u_33:get_alpha();
                end),
                ["DifficultyDisplay"] = p77.SurfaceGui.Button.DifficultyDisplay,
                ["TargetSongKey"] = v_u_10:invalid_songkey()
            })
            v_u_78:set_visible(false)
            v_u_58:add(p76, v_u_78)
        end;
        f_create_info_to_audiomod_button(v_u_19.Easy, v_u_34.SongInfoButtons.EasyModeButton)
        f_create_info_to_audiomod_button(v_u_19.Normal, v_u_34.SongInfoButtons.NormalModeButton)
        f_create_info_to_audiomod_button(v_u_19.Hard, v_u_34.SongInfoButtons.HardModeButton)
        v_u_59 = v_u_70.FiltersSection
        local v79 = v_u_34.FilterButtonProtos.ClearFilterButton:Clone()
        v79.Parent = v_u_34
        v_u_60 = v_u_33:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(v_u_33, v_u_34.PrimaryPart, v79), l__spui_0, function() --[[ Line: 267 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_7, (ref 3): v_u_33 ]]
            p_u_28._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_33:do_clear_filters()
        end)):set_auto_zoffset_behaviour(true)
        local function f_get_artist_select_state_flag() --[[ Name: get_artist_select_state_flag ]] --[[ Line: 274 ]]
            --[[ Upvalues: (ref 1): v_u_64, (ref 2): v_u_65, (ref 3): v_u_66 ]]
            return string.format("%s_%s_%s", v_u_64:get_current_text(), v_u_65:get_current_text(), v_u_66:get_current_text());
        end;
        local v80 = v_u_34.FilterButtonProtos.SelectArtistButton:Clone()
        v80.Parent = v_u_34
        v_u_61 = v_u_33:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(v_u_33, v_u_34.PrimaryPart, v80), l__spui_0, function() --[[ Line: 285 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_7, (ref 3): l__menus_0, (ref 4): v_u_14, (ref 5): l__spui_0, (ref 6): v_u_41, (ref 7): l_AllMySongs_0, (ref 8): v_u_2, (ref 9): p_u_30, (ref 10): v_u_10, (ref 11): v_u_15, (ref 12): v_u_66, (ref 13): v_u_67, (ref 14): v_u_26, (copy 15): f_get_artist_select_state_flag ]]
            p_u_28._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            local v_u_81 = nil
            v_u_81 = l__menus_0:push_menu(v_u_14:new(p_u_28, l__spui_0, l__menus_0, function(p82) --[[ Line: 289 ]]
                --[[ Upvalues: (ref 1): v_u_41, (ref 2): l_AllMySongs_0, (ref 3): v_u_2, (ref 4): p_u_30, (ref 5): v_u_10, (ref 6): v_u_15 ]]
                p82:set_header_text("Select an artist...")
                if v_u_41:contains(l_AllMySongs_0) == true then
                    local v83 = v_u_2:new()
                    for v84, _ in v_u_41:get(l_AllMySongs_0):get_songkey_set():key_itr() do
                        if p_u_30 == nil or p_u_30(v84) == true then
                            local v85, v86 = v_u_15:artist_name_is_selectable((v_u_10:singleton():get_artist_for_key(v84)))
                            if v85 then
                                v83:add_set(v86)
                            end;
                        end;
                    end;
                    local v87 = p82:get_element_list()
                    for v88, _ in v83:key_itr() do
                        v87:push_back(v88)
                    end;
                    v87:sort(function(p89, p90) --[[ Line: 311 ]]
                        return string.lower(p89) < string.lower(p90);
                    end)
                end;
            end, function(p91, p92, p93, _) --[[ Line: 315 ]]
                --[[ Upvalues: (ref 1): v_u_15 ]]
                p92.Text = p91
                local v94 = v_u_15:artist_name_to_icon(p91)
                if #v94 > 0 then
                    p93.Image = v94
                end;
            end, function(p95) --[[ Line: 322 ]]
                --[[ Upvalues: (ref 1): v_u_66, (ref 2): v_u_67, (ref 3): v_u_26, (ref 4): v_u_81, (ref 5): f_get_artist_select_state_flag ]]
                if p95 ~= nil then
                    v_u_66:set_text(p95)
                    v_u_67 = true
                end;
                v_u_26:get_artist_select_page_save_state():on_list_select_save_page(v_u_81:get_list_adapter(), f_get_artist_select_state_flag())
            end))
            v_u_26:get_artist_select_page_save_state():open_to_saved_page(v_u_81:get_list_adapter(), f_get_artist_select_state_flag())
        end))
        local v96 = v_u_34.FilterButtonProtos.DifficultyUpButton:Clone()
        v96.Parent = v_u_34
        v_u_62 = v_u_33:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(v_u_33, v_u_34.PrimaryPart, v96), l__spui_0, function() --[[ Line: 340 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_7, (ref 3): v_u_33 ]]
            p_u_28._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_33:filter_on_change_difficulty(1)
        end)):set_auto_zoffset_behaviour(true)
        local v97 = v_u_34.FilterButtonProtos.DifficultyDownButton:Clone()
        v97.Parent = v_u_34
        v_u_63 = v_u_33:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(v_u_33, v_u_34.PrimaryPart, v97), l__spui_0, function() --[[ Line: 352 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_7, (ref 3): v_u_33 ]]
            p_u_28._sfx_manager:play_sfx(v_u_7.SFX_BUTTONPRESS)
            v_u_33:filter_on_change_difficulty(-1)
        end)):set_auto_zoffset_behaviour(true)
        v_u_64 = v_u_12:new(p_u_28, v_u_59.NameInput.TextLabel, nil, v_u_33, l__spui_0):set_empty_message("Search song name...."):set_send_behaviour_enabled(false):set_max_length(16)
        v_u_65 = v_u_12:new(p_u_28, v_u_59.DifficultyInput.TextLabel, nil, v_u_33, l__spui_0):set_empty_message("(1)"):set_send_behaviour_enabled(false):set_max_length(2):enforce_numeric(true)
        v_u_66 = v_u_12:new(p_u_28, v_u_59.ArtistNameInput.TextLabel, nil, v_u_33, l__spui_0):set_empty_message("Search artist..."):set_send_behaviour_enabled(false):set_max_length(16)
        v_u_64:set_text(v_u_26:get_filter_last_name_input_text())
        v_u_65:set_text(v_u_26:get_filter_last_difficulty_input_text())
        v_u_66:set_text(v_u_26:get_filter_last_artist_input_text())
        v_u_33:raise_filter_changed()
        v_u_41:add(v_u_21.AllMySongs, v_u_22:new(p_u_28, v_u_33, v_u_34, p_u_30, function(p98) --[[ Line: 400 ]]
            --[[ Upvalues: (ref 1): p_u_31, (ref 2): l__menus_0, (ref 3): v_u_33 ]]
            p_u_31(p98)
            l__menus_0:remove_menu(v_u_33)
        end, function(p99) --[[ Line: 403 ]]
            --[[ Upvalues: (ref 1): p_u_32 ]]
            if p_u_32 ~= nil then
                p_u_32(p99)
            end;
        end))
        for _, v100 in pairs(v_u_34.FilterButtonProtos:GetChildren()) do
            v100.Parent = nil
        end;
        v_u_33:update_selected_tab()
        v_u_33:transition_update_visual(0)
        v_u_33:layout()
        if v_u_10:singleton():contains_key(v_u_33:get_info_displayed_song_key()) then
            v_u_33:play_preview_for_songkey(v_u_33:get_info_displayed_song_key())
        end;
    end;
    v_u_33.do_clear_filters = function(_) --[[ Name: do_clear_filters ]] --[[ Line: 424 ]]
        --[[ Upvalues: (ref 1): v_u_64, (ref 2): v_u_65, (ref 3): v_u_66, (copy 4): v_u_41, (ref 5): l_AllMySongs_0, (ref 6): v_u_67 ]]
        v_u_64:set_text("")
        v_u_65:set_text("")
        v_u_66:set_text("")
        if v_u_41:contains(l_AllMySongs_0) then
            v_u_41:get(l_AllMySongs_0):on_clear_filter()
        end;
        v_u_67 = true
    end;
    v_u_33.get_current_infostate = function(_) --[[ Name: get_current_infostate ]] --[[ Line: 434 ]]
        --[[ Upvalues: (ref 1): p_u_29 ]]
        return p_u_29;
    end;
    v_u_33.get_page = function(p101) --[[ Name: get_page ]] --[[ Line: 438 ]]
        return p101:get_current_infostate():get_page();
    end;
    v_u_33.set_page = function(p102, p103) --[[ Name: set_page ]] --[[ Line: 439 ]]
        p102:get_current_infostate():set_page(p103)
    end;
    v_u_33.is_loading = function(_) --[[ Name: is_loading ]] --[[ Line: 441 ]]
        --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_27 ]]
        return l_Loading_0 == v_u_27.State.Loading;
    end;
    v_u_33.set_loading = function(p104, p105) --[[ Name: set_loading ]] --[[ Line: 442 ]]
        --[[ Upvalues: (ref 1): l_Loading_0, (ref 2): v_u_27, (ref 3): v_u_71, (ref 4): v_u_70, (ref 5): v_u_60, (ref 6): v_u_61, (ref 7): v_u_62, (ref 8): v_u_63, (copy 9): v_u_41, (ref 10): l_AllMySongs_0, (ref 11): v_u_52, (ref 12): v_u_53, (ref 13): v_u_55, (copy 14): v_u_58 ]]
        if p105 == true then
            l_Loading_0 = v_u_27.State.Loading
            v_u_71.Visible = true
            v_u_70.Visible = false
            v_u_60:set_visible(false)
            v_u_61:set_visible(false)
            v_u_62:set_visible(false)
            v_u_63:set_visible(false)
            v_u_52:set_visible(false)
            v_u_53:set_visible(false)
            v_u_55:set_visible(false)
            for _, v106 in v_u_58:key_itr() do
                v106:set_visible(false)
            end;
            for _, v107 in v_u_41:key_itr() do
                v107:set_visible(false)
            end;
        else
            l_Loading_0 = v_u_27.State.Loaded
            v_u_71.Visible = false
            v_u_70.Visible = true
            v_u_60:set_visible(true)
            v_u_61:set_visible(true)
            v_u_62:set_visible(true)
            v_u_63:set_visible(true)
            for v108, v109 in v_u_41:key_itr() do
                if v108 == l_AllMySongs_0 then
                    v109:set_visible(true)
                else
                    v109:set_visible(false)
                end;
            end;
            p104:opt_update_info_section()
        end;
        p104:update_page_display()
    end;
    v_u_33.reset_page = function(p110) --[[ Name: reset_page ]] --[[ Line: 480 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        p110:set_page(v_u_26:get_page_first())
        p110:update_page_display()
    end;
    v_u_33.update_selected_tab = function(p111) --[[ Name: update_selected_tab ]] --[[ Line: 484 ]]
        --[[ Upvalues: (copy 1): v_u_41, (ref 2): l_AllMySongs_0 ]]
        for v112, v113 in v_u_41:key_itr() do
            if v112 ~= l_AllMySongs_0 then
                v113:set_visible(false)
            end;
        end;
        p111:load_current_tab()
    end;
    local v_u_114 = -1
    v_u_33.load_current_tab = function(p_u_115) --[[ Name: load_current_tab ]] --[[ Line: 494 ]]
        --[[ Upvalues: (copy 1): v_u_41, (ref 2): l_AllMySongs_0, (ref 3): v_u_114, (copy 4): p_u_28, (ref 5): v_u_10 ]]
        if v_u_41:contains(l_AllMySongs_0) then
            v_u_114 = p_u_28._player_blob_manager:get_global_time_float()
            local v_u_116 = v_u_114
            local v117 = v_u_41:get(l_AllMySongs_0)
            p_u_115:set_loading(true)
            v117:load_data(function() --[[ Line: 501 ]]
                --[[ Upvalues: (copy 1): v_u_116, (ref 2): v_u_114, (copy 3): p_u_115, (ref 4): v_u_10 ]]
                if v_u_116 == v_u_114 then
                    p_u_115:set_loading(false)
                    p_u_115:refresh_current_page()
                    if p_u_115:get_info_displayed_song_key() ~= v_u_10:invalid_songkey() then
                        p_u_115:show_info_for_songkey(p_u_115:get_info_displayed_song_key())
                    end;
                end;
            end)
        end;
    end;
    v_u_33.refresh_current_page = function(p118) --[[ Name: refresh_current_page ]] --[[ Line: 512 ]]
        --[[ Upvalues: (copy 1): v_u_41, (ref 2): l_AllMySongs_0, (ref 3): v_u_26 ]]
        p118:set_loading(false)
        if v_u_41:contains(l_AllMySongs_0) then
            local v119 = v_u_41:get(l_AllMySongs_0)
            v119:refresh()
            if p118:get_page() >= v119:get_page_total() then
                p118:set_page(v_u_26:get_page_first())
                v119:refresh()
            end;
            p118:update_page_display()
        end;
    end;
    v_u_33.update_page_display = function(p120) --[[ Name: update_page_display ]] --[[ Line: 525 ]]
        --[[ Upvalues: (ref 1): v_u_39, (ref 2): v_u_40, (ref 3): v_u_37, (ref 4): v_u_38, (ref 5): v_u_42, (ref 6): v_u_69, (ref 7): v_u_68, (copy 8): v_u_41, (ref 9): l_AllMySongs_0, (copy 10): p_u_28, (ref 11): v_u_9 ]]
        if p120:is_loading() then
            v_u_39.Text = "-"
            v_u_40.Text = "-"
            v_u_37:set_visible(false)
            v_u_38:set_visible(false)
            v_u_42.Visible = false
            v_u_69:set_visible(false)
            v_u_68.Visible = false
            return;
        elseif v_u_41:contains(l_AllMySongs_0) then
            local v121 = v_u_41:get(l_AllMySongs_0):get_page_total()
            if v121 > 0 then
                v_u_39.Text = string.format("%d", p120:get_page() + 1)
                v_u_40.Text = string.format("%d", v121)
                v_u_37:set_visible(v121 > 1)
                v_u_38:set_visible(v121 > 1)
                v_u_68.Visible = false
            else
                v_u_39.Text = "-"
                v_u_40.Text = "-"
                v_u_37:set_visible(false)
                v_u_38:set_visible(false)
                v_u_68.Visible = true
            end;
            v_u_42.Visible = true
            v_u_69:set_visible(v_u_9:playerblob_has_vip_for_current_day(p_u_28._player_blob_manager:get_player_blob(), p_u_28:get_current_dayid()) ~= true)
        else
            v_u_39.Text = "-"
            v_u_40.Text = "-"
            v_u_37:set_visible(false)
            v_u_38:set_visible(false)
            v_u_42.Visible = false
            v_u_69:set_visible(false)
            v_u_68.Visible = false
        end;
    end;
    v_u_33.get_info_displayed_song_key = function(p122) --[[ Name: get_info_displayed_song_key ]] --[[ Line: 569 ]]
        return p122:get_current_infostate():get_info_displayed_song_key();
    end;
    v_u_33.set_info_displayed_song_key = function(p123, p124) --[[ Name: set_info_displayed_song_key ]] --[[ Line: 570 ]]
        p123:get_current_infostate():set_info_displayed_song_key(p124)
    end;
    local v_u_125 = -1
    v_u_33.opt_update_info_section = function(p126) --[[ Name: opt_update_info_section ]] --[[ Line: 573 ]]
        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_125, (copy 3): p_u_28, (ref 4): v_u_52, (ref 5): v_u_43, (ref 6): v_u_17, (ref 7): v_u_54, (ref 8): v_u_15, (ref 9): v_u_57, (ref 10): v_u_56, (ref 11): v_u_1, (ref 12): v_u_45, (ref 13): v_u_46, (ref 14): v_u_13, (ref 15): v_u_47, (ref 16): v_u_44, (ref 17): v_u_50, (ref 18): v_u_49, (ref 19): v_u_51, (ref 20): v_u_48, (ref 21): v_u_20, (ref 22): v_u_53, (ref 23): v_u_55, (copy 24): v_u_58, (ref 25): v_u_9, (ref 26): v_u_24, (copy 27): p_u_30, (ref 28): v_u_16 ]]
        if p126:is_loading() then
            return;
        else
            local v127 = p126:get_info_displayed_song_key()
            if v_u_10:singleton():contains_key(v127) and (v_u_125 ~= p_u_28._player_song_stats_manager:get_time_last_update() or v_u_52:get_visible() ~= true) then
                v_u_125 = p_u_28._player_song_stats_manager:get_time_last_update()
                v_u_43.Text = v_u_10:singleton():get_title_for_key(v127)
                local v128, v129 = v_u_17:songkey_has_special_info_text(v127)
                v_u_54.Visible = v128
                if v128 then
                    v_u_54.Text = v129
                end;
                local v130, v131 = v_u_15:artist_name_is_selectable(v_u_10:singleton():get_artist_for_key(v127))
                if v130 then
                    v_u_57 = v131
                    v_u_56.Image = v_u_15:artist_name_to_icon(v131)
                else
                    v_u_57 = ""
                    v_u_56.Image = v_u_1:transparent_assetid()
                end;
                v_u_10:singleton():render_coverimage_for_key(v_u_45, v_u_46, v127)
                v_u_13:render_songkey_colorsection(v127, v_u_47)
                v_u_44.Image = v_u_1:semitransparent_assetid()
                v_u_50.Text = p_u_28._player_song_stats_manager:get_best_score_display_str(v127)
                v_u_49.Text = p_u_28._player_song_stats_manager:get_rank_display_str(v127)
                v_u_51.Text = p_u_28._player_song_stats_manager:get_playcount_display_str(v127)
                local v132, v133 = p_u_28._player_song_stats_manager:get_best_grade_rank_value(v127)
                if v133 > 0 then
                    v_u_48.Image = v_u_20:get_rank_value_icon(v132)
                    v_u_48.Visible = true
                else
                    v_u_48.Visible = false
                end;
                v_u_52:set_visible(true)
                local v134 = p_u_28._player_blob_manager:get_player_blob()
                v_u_53:set_default_selected_songkey(v127)
                if #v_u_57 > 0 then
                    v_u_55:set_visible(true)
                else
                    v_u_55:set_visible(false)
                end;
                local v135 = v_u_10:singleton():key_get_audiomod(v127)
                local v136 = v_u_10:singleton():get_audiomod_to_modes_of_songkey(v127)
                for v137, v138 in v_u_58:key_itr() do
                    v138:set_visible(true)
                    local l_Toggle_0 = v138:get_bound_data().Toggle
                    local l_DifficultyDisplay_0 = v138:get_bound_data().DifficultyDisplay
                    if v136:contains(v137) then
                        local v139 = v136:get(v137)
                        v138:get_bound_data().TargetSongKey = v139
                        l_DifficultyDisplay_0.Text = tostring((v_u_10:singleton():get_difficulty_for_key(v139)))
                        l_DifficultyDisplay_0.TextColor3 = v_u_10:singleton():get_difficulty_color_for_key(v139)
                        local v140 = v_u_9:playerblob_has_access_to_song(p_u_28._player_blob_manager:get_player_blob(), v139, p_u_28:get_current_dayid(), p_u_28._player_blob_manager:get_cached_collection_info())
                        local v141 = v_u_24:get_songkey_recipe_id(v139)
                        local v142 = p_u_30 == nil and true or p_u_30(v139)
                        if v140 and v142 then
                            v138:set_enabled(true)
                            l_Toggle_0:set_toggle(true)
                        elseif v141 == nil or not v142 then
                            v138:set_enabled(false)
                            l_Toggle_0:set_toggle_off_alpha(0.2)
                            l_Toggle_0:set_toggle(false)
                        elseif v_u_16:can_craft_recipe(v134, v141) then
                            v138:set_enabled(true)
                            l_Toggle_0:set_toggle_off_alpha(0.6)
                            l_Toggle_0:set_toggle(false)
                        else
                            v138:set_enabled(false)
                            l_Toggle_0:set_toggle_off_alpha(0.2)
                            l_Toggle_0:set_toggle(false)
                        end;
                        if v135 == v137 then
                            v138:set_scale(1.35)
                            v138:set_unselected_zoffset(750)
                            v138:set_passive_anim(true)
                        else
                            v138:set_scale(0.85)
                            v138:set_unselected_zoffset(500)
                            v138:set_passive_anim(false)
                        end;
                    else
                        v138:get_bound_data().TargetSongKey = v_u_10:invalid_songkey()
                        l_DifficultyDisplay_0.Text = "-"
                        l_DifficultyDisplay_0.TextColor3 = Color3.new(1, 1, 1)
                        v138:set_enabled(false)
                        l_Toggle_0:set_toggle_off_alpha(0.25)
                        l_Toggle_0:set_toggle(false)
                        v138:set_scale(0.85)
                        v138:set_unselected_zoffset(500)
                    end;
                end;
            elseif v127 == v_u_10:invalid_songkey() then
                v_u_43.Text = "Click on a song to view info."
                v_u_57 = ""
                v_u_56.Image = v_u_1:transparent_assetid()
                v_u_54.Visible = false
                v_u_45.Image = v_u_1:transparent_assetid()
                v_u_46.Image = v_u_1:transparent_assetid()
                v_u_44.Image = v_u_1:transparent_assetid()
                v_u_47.Visible = false
                v_u_52:set_visible(false)
                v_u_53:set_visible(false)
                v_u_55:set_visible(false)
                for _, v143 in v_u_58:key_itr() do
                    v143:set_visible(false)
                end;
                v_u_50.Text = "-"
                v_u_49.Text = ""
                v_u_51.Text = "-"
                v_u_48.Visible = false
            end;
        end;
    end;
    v_u_33.hide_info_section = function(p144) --[[ Name: hide_info_section ]] --[[ Line: 713 ]]
        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_125 ]]
        p144:set_info_displayed_song_key(v_u_10:invalid_songkey())
        v_u_125 = -1
        p144:opt_update_info_section()
    end;
    v_u_33.show_info_for_songkey = function(p145, p146) --[[ Name: show_info_for_songkey ]] --[[ Line: 719 ]]
        --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_28, (ref 3): v_u_125 ]]
        if v_u_10:singleton():contains_key(p146) then
            p_u_28._game_join:set_last_loaded_songkey(p146)
        end;
        p_u_28._player_song_stats_manager:request_ranks_for_songkey(p146)
        p145:set_info_displayed_song_key(p146)
        v_u_125 = -1
        p145:opt_update_info_section()
    end;
    v_u_33.show_info_displayed_description_popup = function(p147) --[[ Name: show_info_displayed_description_popup ]] --[[ Line: 729 ]]
        --[[ Upvalues: (ref 1): v_u_18, (copy 2): p_u_28 ]]
        v_u_18:show_song_info_popup(p_u_28, (p147:get_info_displayed_song_key()))
    end;
    v_u_33.play_preview_for_songkey = function(_, p148) --[[ Name: play_preview_for_songkey ]] --[[ Line: 734 ]]
        --[[ Upvalues: (copy 1): p_u_28 ]]
        p_u_28._bgm_manager:preview_songkey(p148)
    end;
    v_u_33.select_songkey = function(p_u_149, p_u_150) --[[ Name: select_songkey ]] --[[ Line: 739 ]]
        --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_6, (copy 3): p_u_28, (ref 4): v_u_9, (ref 5): v_u_24, (ref 6): v_u_16, (copy 7): p_u_30, (ref 8): l_AllMySongs_0, (ref 9): v_u_21, (copy 10): v_u_41 ]]
        if v_u_10:singleton():contains_key(p_u_150) ~= true then
            return v_u_6:warnf("PlayUI:select_songkey(%s) does not contain", (tostring(p_u_150)));
        end;
        local v151 = p_u_28._player_blob_manager:get_player_blob()
        local v152 = v_u_9:playerblob_has_access_to_song(p_u_28._player_blob_manager:get_player_blob(), p_u_150, p_u_28:get_current_dayid(), p_u_28._player_blob_manager:get_cached_collection_info())
        local v153 = v_u_24:get_songkey_recipe_id(p_u_150)
        local v154
        if v153 == nil then
            v154 = false
        else
            v154 = v_u_16:can_craft_recipe(v151, v153)
        end;
        local v155 = p_u_30 == nil and true or p_u_30(p_u_150)
        if v152 and v155 then
            l_AllMySongs_0 = v_u_21.AllMySongs
            p_u_149:update_selected_tab()
            local v156 = v_u_41:get(v_u_21.AllMySongs)
            if v156:songkey_selected(p_u_150) then
                p_u_149:show_info_for_songkey(p_u_150)
                v156:update_play_button()
                return;
            end;
        elseif v154 and v155 then
            p_u_28._menus:push_menu(v_u_24:new(p_u_28, p_u_28._spui, p_u_28._menus, p_u_150, function() --[[ Line: 771 ]]
                --[[ Upvalues: (copy 1): p_u_149, (copy 2): p_u_150 ]]
                p_u_149:select_songkey(p_u_150)
            end))
        end;
    end;
    v_u_33.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 777 ]]
        --[[ Upvalues: (copy 1): v_u_41, (copy 2): p_u_28, (ref 3): v_u_72, (ref 4): v_u_34 ]]
        for _, v157 in v_u_41:key_itr() do
            v157:set_visible(false)
        end;
        p_u_28._bgm_manager:stop_song_preview(v_u_72)
        v_u_34:Destroy()
    end;
    v_u_33.on_refocus = function(p158) --[[ Name: on_refocus ]] --[[ Line: 785 ]]
        --[[ Upvalues: (copy 1): v_u_41, (ref 2): l_AllMySongs_0, (ref 3): v_u_10 ]]
        if v_u_41:contains(l_AllMySongs_0) and v_u_41:get(l_AllMySongs_0):requires_reload_on_menu_refocus() then
            p158:load_current_tab()
        else
            p158:refresh_current_page()
        end;
        if v_u_10:singleton():contains_key(p158:get_info_displayed_song_key()) then
            p158:play_preview_for_songkey(p158:get_info_displayed_song_key())
            p158:opt_update_info_section()
        end;
    end;
    v_u_33.behaviour_update = function(p159, p160, _) --[[ Name: behaviour_update ]] --[[ Line: 798 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_64, (ref 3): v_u_65, (ref 4): v_u_66, (ref 5): l_Loading_0, (ref 6): v_u_27, (copy 7): v_u_41, (ref 8): l_AllMySongs_0, (copy 9): p_u_28 ]]
        v_u_26:set_filter_last_name_input_text(v_u_64:get_current_text())
        v_u_26:set_filter_last_difficulty_input_text(v_u_65:get_current_text())
        v_u_26:set_filter_last_artist_input_text(v_u_66:get_current_text())
        if l_Loading_0 == v_u_27.State.Loaded then
            v_u_64:update(p160)
            v_u_65:update(p160)
            v_u_66:update(p160)
            if v_u_41:contains(l_AllMySongs_0) then
                v_u_41:get(l_AllMySongs_0):behaviour_update(p160)
                if p159:raise_filter_changed() then
                    p159:reset_page()
                    p159:hide_info_section()
                    p159:refresh_current_page()
                end;
            end;
        end;
        p159:opt_update_info_section()
        p159:behaviour_update_base(p160, p_u_28)
    end;
    v_u_33.get_filter_search_name = function(_) --[[ Name: get_filter_search_name ]] --[[ Line: 824 ]]
        --[[ Upvalues: (ref 1): v_u_64 ]]
        return v_u_64:get_current_text();
    end;
    v_u_33.get_filter_artist_name = function(_) --[[ Name: get_filter_artist_name ]] --[[ Line: 828 ]]
        --[[ Upvalues: (ref 1): v_u_66 ]]
        return v_u_66:get_current_text();
    end;
    v_u_33.get_filter_search_difficulty = function(_) --[[ Name: get_filter_search_difficulty ]] --[[ Line: 832 ]]
        --[[ Upvalues: (ref 1): v_u_65, (ref 2): v_u_1 ]]
        local v161 = tonumber((v_u_65:get_current_text()))
        return v_u_1:is_finite(v161) == false and -100 or v161;
    end;
    v_u_33.filter_on_change_difficulty = function(_, p162) --[[ Name: filter_on_change_difficulty ]] --[[ Line: 839 ]]
        --[[ Upvalues: (copy 1): v_u_41, (ref 2): l_AllMySongs_0, (ref 3): v_u_65, (ref 4): v_u_1 ]]
        if v_u_41:contains(l_AllMySongs_0) then
            local v163 = v_u_41:get(l_AllMySongs_0):get_max_difficulty()
            local v164 = tonumber(v_u_65:get_current_text())
            local v165 = (v_u_1:is_finite(v164) == false and 1 or v164) + p162
            if v165 > 0 then
                v163 = v163 < v165 and 1 or v165
            end;
            v_u_65:set_text((tostring(v163)))
            v_u_41:get(l_AllMySongs_0):on_filter_change_difficulty(v163)
        end;
    end;
    v_u_33.raise_filter_changed = function(_) --[[ Name: raise_filter_changed ]] --[[ Line: 858 ]]
        --[[ Upvalues: (ref 1): v_u_67, (ref 2): v_u_64, (ref 3): v_u_65, (ref 4): v_u_66 ]]
        local v166 = v_u_67
        v_u_67 = false
        return v166 or (v_u_64:raise_changed() or (v_u_65:raise_changed() or v_u_66:raise_changed()));
    end;
    v_u_33.layout = function(p167) --[[ Name: layout ]] --[[ Line: 867 ]]
        --[[ Upvalues: (copy 1): l__spui_0, (ref 2): v_u_36, (ref 3): v_u_34, (copy 4): v_u_41 ]]
        p167:opt_rescale_to_max_nxy(l__spui_0, 0.9, 0.85, v_u_36)
        local v168, v169 = p167:opt_update_cframe_params(l__spui_0, {
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p167:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v168 == true then
            v_u_34:SetPrimaryPartCFrame(v169)
        end;
        for _, v170 in v_u_41:key_itr() do
            v170:layout()
        end;
    end;
    v_u_33.set_alpha = function(_, p171) --[[ Name: set_alpha ]] --[[ Line: 883 ]]
        --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_1, (ref 3): v_u_34 ]]
        if v_u_35 ~= p171 then
            v_u_35 = p171
            v_u_1:r_set_alpha(v_u_34, v_u_35)
        end;
    end;
    v_u_33.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 889 ]]
        --[[ Upvalues: (ref 1): v_u_35 ]]
        return v_u_35;
    end;
    v_u_33.set_scale = function(_, p172) --[[ Name: set_scale ]] --[[ Line: 890 ]]
        --[[ Upvalues: (ref 1): v_u_36 ]]
        v_u_36 = p172
    end;
    v_u_33.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 891 ]]
        --[[ Upvalues: (ref 1): v_u_36 ]]
        return v_u_36;
    end;
    v_u_33.get_native_size = function(p173) --[[ Name: get_native_size ]] --[[ Line: 893 ]]
        return p173._native_size;
    end;
    v_u_33.get_size = function(p174) --[[ Name: get_size ]] --[[ Line: 896 ]]
        return p174._size;
    end;
    v_u_33.set_size = function(p175, p176) --[[ Name: set_size ]] --[[ Line: 899 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        p175._size = p176
        v_u_34.PrimaryPart.Size = Vector3.new(p176.X, p176.Y, 0)
    end;
    v_u_33.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 903 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        return v_u_34.PrimaryPart.Position;
    end;
    v_u_33.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 906 ]]
        --[[ Upvalues: (ref 1): v_u_34 ]]
        return v_u_34.PrimaryPart.SurfaceGui;
    end;
    v_u_33.set_showing = function(_, p177) --[[ Name: set_showing ]] --[[ Line: 909 ]]
        --[[ Upvalues: (ref 1): v_u_34, (ref 2): v_u_8 ]]
        if p177 then
            v_u_34.Parent = v_u_8:get_world_ui_folder()
        else
            v_u_34.Parent = nil
        end;
    end;
    f_cons()
    return v_u_33;
end;
return v_u_27;
