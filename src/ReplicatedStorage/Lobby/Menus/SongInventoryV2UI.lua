-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:39 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
require(game.ReplicatedStorage.Shared.SPVector)
local v_u_8 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_9 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_11 = require(game.ReplicatedStorage.Lobby.Menus.SongAcquiredV2UI)
local v_u_12 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.SellSong)
local v_u_14 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_15 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_16 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_17 = require(game.ReplicatedStorage.Lobby.UI.SongInventoryV2UIElement)
local v_u_18 = require(game.ReplicatedStorage.Lobby.UI.SongInventoryV2SearchSection)
local v19 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_20 = nil
local v_u_21 = nil
local v_u_22 = nil
local v_u_23 = nil
local v_u_24 = nil
local v_u_25 = nil
v19:require_client(function() --[[ Line: 34 ]]
    --[[ Upvalues: (ref 1): v_u_20, (ref 2): v_u_21, (ref 3): v_u_22, (ref 4): v_u_23, (ref 5): v_u_24, (ref 6): v_u_25 ]]
    v_u_20 = require(game.ReplicatedStorage.Lobby.Menus.CraftingUI)
    v_u_21 = require(game.ReplicatedStorage.Lobby.UI.CraftingUITabSongs)
    v_u_22 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_23 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
    v_u_24 = require(game.ReplicatedStorage.Lobby.Menus.CraftSongUI)
    v_u_25 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
end)
local v26 = {}
local v_u_27 = v_u_7:invalid_songkey()
v26.new = function(_, p_u_28, p_u_29, p_u_30, p_u_31) --[[ Name: new ]] --[[ Line: 47 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_2, (copy 3): v_u_1, (copy 4): v_u_12, (copy 5): v_u_5, (copy 6): v_u_4, (copy 7): v_u_9, (copy 8): v_u_7, (ref 9): v_u_23, (ref 10): v_u_22, (copy 11): v_u_18, (ref 12): v_u_27, (copy 13): v_u_17, (copy 14): v_u_10, (copy 15): v_u_8, (copy 16): v_u_15, (copy 17): v_u_14, (copy 18): v_u_13, (ref 19): v_u_24, (copy 20): v_u_6, (copy 21): v_u_11, (copy 22): v_u_16, (ref 23): v_u_25 ]]
    local v32 = v_u_3:new(p_u_29, p_u_30)
    local v_u_33 = nil
    local v_u_34 = v_u_2:new()
    local v_u_35 = nil
    local v_u_36 = nil
    local v_u_37 = nil
    local v_u_38 = 1
    local v_u_39 = 1
    local v_u_40 = 0
    local v_u_41 = 1
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
    local v_u_57 = nil
    local v_u_58 = nil
    local v_u_59 = nil
    local v_u_60 = nil
    local v_u_61 = nil
    local v_u_62 = nil
    local v_u_63 = nil
    local v_u_64 = nil
    v32.cons = function(p_u_65) --[[ Name: cons ]] --[[ Line: 95 ]]
        --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_1, (ref 3): v_u_12, (ref 4): v_u_64, (copy 5): p_u_28, (ref 6): v_u_42, (ref 7): v_u_43, (ref 8): v_u_44, (ref 9): v_u_45, (ref 10): v_u_46, (ref 11): v_u_47, (ref 12): v_u_48, (ref 13): v_u_49, (ref 14): v_u_50, (ref 15): v_u_51, (ref 16): v_u_52, (ref 17): v_u_53, (ref 18): v_u_54, (ref 19): v_u_55, (ref 20): v_u_56, (ref 21): v_u_62, (ref 22): v_u_36, (ref 23): v_u_5, (ref 24): v_u_4, (copy 25): p_u_29, (ref 26): v_u_9, (copy 27): v_u_34, (ref 28): v_u_37, (ref 29): v_u_61, (ref 30): v_u_41, (ref 31): v_u_7, (ref 32): v_u_23, (ref 33): v_u_38, (ref 34): v_u_57, (ref 35): v_u_58, (ref 36): v_u_59, (ref 37): v_u_60, (ref 38): v_u_22, (copy 39): p_u_30, (ref 40): v_u_63, (ref 41): v_u_18, (copy 42): p_u_31, (ref 43): v_u_27 ]]
        v_u_33 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.SongInventoryV2UI:Clone()
        v_u_33.Name = v_u_1:gen_name(v_u_33.Name)
        v_u_33.Parent = v_u_12:get_world_ui_folder()
        p_u_65._native_size = v_u_33.PrimaryPart.Size
        p_u_65._size = p_u_65._native_size
        v_u_64 = p_u_28._bgm_manager:begin_preview_songkey()
        local l_InfoPanel_0 = v_u_33.MainSurface.SurfaceGui.Frame.InfoPanel
        v_u_42 = l_InfoPanel_0.SongPanel.BestGradeFrame.Display
        v_u_43 = l_InfoPanel_0.SongPanel.BestScoreFrame.Display
        v_u_44 = l_InfoPanel_0.SongPanel.BestScoreFrame.RankDisplay
        v_u_45 = l_InfoPanel_0.SongPanel.PlayCountFrame.Display
        v_u_46 = l_InfoPanel_0.SongPanel.AlbumArt
        v_u_47 = l_InfoPanel_0.SongPanel.AlbumArtOverlay
        v_u_48 = l_InfoPanel_0.SongPanel.ColorSection
        v_u_49 = l_InfoPanel_0.ArtistDisplay
        v_u_50 = l_InfoPanel_0.CopiesDisplay
        v_u_51 = l_InfoPanel_0.TitleDisplay
        v_u_52 = l_InfoPanel_0.DescriptionDisplay
        v_u_53 = l_InfoPanel_0.DifficultyDisplay
        v_u_54 = l_InfoPanel_0.CopiesSubDisplay
        v_u_55 = l_InfoPanel_0.SellSubDisplay
        v_u_56 = l_InfoPanel_0.CraftDisplay
        v_u_62 = v_u_33.MainSurface.SurfaceGui.Frame.NoSongDisplay
        v_u_62.Visible = false
        v_u_36 = p_u_65:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(p_u_65, v_u_33.PrimaryPart, v_u_33.LeftArrowSurface), p_u_29, function() --[[ Line: 134 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_9, (copy 3): p_u_65, (ref 4): v_u_34 ]]
            p_u_28._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
            p_u_65:increment_selected_page_offset(-v_u_34:count())
        end):set_passive_anim())
        v_u_37 = p_u_65:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(p_u_65, v_u_33.PrimaryPart, v_u_33.RightArrowSurface), p_u_29, function() --[[ Line: 144 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_9, (copy 3): p_u_65, (ref 4): v_u_34 ]]
            p_u_28._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
            p_u_65:increment_selected_page_offset(v_u_34:count())
        end):set_passive_anim())
        v_u_36:set_visible(false)
        v_u_37:set_visible(false)
        v_u_61 = p_u_65:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(p_u_65, v_u_33.PrimaryPart, v_u_33.InfoButtonSurface), p_u_29, function() --[[ Line: 157 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_9, (ref 3): v_u_41, (ref 4): v_u_34, (ref 5): v_u_7, (ref 6): v_u_23 ]]
            p_u_28._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
            if v_u_41 <= v_u_34:count() then
                local v66 = v_u_34:get(v_u_41):get_song_key()
                if v_u_7:singleton():contains_key(v66) then
                    v_u_23:show_song_info_popup(p_u_28, v66)
                end;
            end;
        end):set_passive_anim():set_selected_rotation_amplitude(20))
        local function f_create_enable_anim_button(p_u_67, p_u_68, p_u_69, p_u_70) --[[ Name: create_enable_anim_button ]] --[[ Line: 169 ]]
            --[[ Upvalues: (copy 1): p_u_65, (ref 2): p_u_28, (ref 3): v_u_5, (ref 4): v_u_4, (ref 5): v_u_33, (ref 6): p_u_29, (ref 7): v_u_9, (ref 8): v_u_1, (ref 9): v_u_38 ]]
            local v_u_71 = -1
            return p_u_65:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(p_u_65, v_u_33.PrimaryPart, p_u_69), p_u_29, function() --[[ Line: 174 ]]
                --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_9, (copy 3): p_u_70 ]]
                p_u_28._sfx_manager:play_sfx(v_u_9.SFX_MENU_OPEN)
                p_u_70()
            end):set_enabled_anim_updatefn(function(p72, _) --[[ Line: 178 ]]
                --[[ Upvalues: (ref 1): v_u_71, (copy 2): p_u_67, (ref 3): v_u_1, (copy 4): p_u_68, (copy 5): p_u_69, (ref 6): v_u_38 ]]
                if p72 ~= v_u_71 then
                    local v73 = p72 == true and 1 or 0.25
                    p_u_67.Name = v_u_1:r_set_alpha_generate_name({
                        ["ImageAlpha"] = v73
                    }, "ImageLabel")
                    p_u_68.Name = v_u_1:r_set_alpha_generate_name({
                        ["TextAlpha"] = v73
                    }, "TextLabel")
                    v_u_1:r_set_alpha(p_u_69, v_u_38)
                    v_u_71 = p72
                end;
            end));
        end;
        v_u_57 = f_create_enable_anim_button(v_u_33.CraftButtonSurface.SurfaceGui.ImageLabel, v_u_33.CraftButtonSurface.SurfaceGui.ImageLabel.TextLabel, v_u_33.CraftButtonSurface, function() --[[ Line: 197 ]]
            --[[ Upvalues: (copy 1): p_u_65 ]]
            p_u_65:craft_button_pressed()
        end)
        v_u_58 = f_create_enable_anim_button(v_u_33.CombineButtonSurface.SurfaceGui.ImageLabel, v_u_33.CombineButtonSurface.SurfaceGui.ImageLabel.TextLabel, v_u_33.CombineButtonSurface, function() --[[ Line: 206 ]]
            --[[ Upvalues: (copy 1): p_u_65 ]]
            p_u_65:combine_button_pressed()
        end)
        v_u_59 = f_create_enable_anim_button(v_u_33.SellButtonSurface.SurfaceGui.ImageLabel, v_u_33.SellButtonSurface.SurfaceGui.ImageLabel.TextLabel, v_u_33.SellButtonSurface, function() --[[ Line: 215 ]]
            --[[ Upvalues: (copy 1): p_u_65 ]]
            p_u_65:sell_button_pressed()
        end)
        v_u_60 = p_u_65:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(p_u_65, v_u_33.PrimaryPart, v_u_33.PlayButtonSurface), p_u_29, function() --[[ Line: 223 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_9, (ref 3): v_u_34, (ref 4): v_u_41, (ref 5): v_u_7, (ref 6): v_u_22 ]]
            p_u_28._sfx_manager:play_sfx(v_u_9.SFX_MENU_OPEN)
            local v74 = v_u_34:get(v_u_41):get_song_key()
            if v_u_7:singleton():contains_key(v74) then
                p_u_28._menus:push_menu(v_u_22:new(p_u_28, p_u_28._spui, p_u_28._menus, v74, nil))
            end;
        end):set_passive_anim():set_auto_zoffset_behaviour(true))
        v_u_60:set_visible(false)
        p_u_65:add_cycle_element(p_u_28, 1, v_u_5:new(v_u_4:new(p_u_65, v_u_33.PrimaryPart, v_u_33.BackButtonSurface), p_u_29, function() --[[ Line: 239 ]]
            --[[ Upvalues: (ref 1): p_u_28, (ref 2): v_u_9, (ref 3): p_u_30, (copy 4): p_u_65 ]]
            p_u_28._sfx_manager:play_sfx(v_u_9.SFX_MENU_CLOSE)
            p_u_30:remove_menu(p_u_65)
        end))
        v_u_63 = v_u_18:new(p_u_28, p_u_29, p_u_30, p_u_65, v_u_33)
        v_u_33.PlayPreviewButton.Parent = nil
        p_u_65:setup_list_elements()
        if p_u_31 ~= nil then
            v_u_27 = p_u_31
        end;
        p_u_65:select_last_selected_songkey_or_reset()
        p_u_65:reset_selected_item()
        p_u_65:transition_update_visual(0)
        p_u_65:layout()
    end;
    v32.select_songkey = function(p75, p76) --[[ Name: select_songkey ]] --[[ Line: 260 ]]
        --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_34, (ref 3): v_u_40 ]]
        local v77 = false
        local v78 = 1
        local v79 = 1
        if p76 ~= nil and v_u_7:singleton():contains_key(p76) then
            local v80 = p75:get_song_list()
            for v81 = 0, math.ceil(v80:count() / v_u_34:count()) do
                for v82 = 1, v_u_34:count() do
                    local v83 = v81 * v_u_34:count() + v82
                    if v83 <= v80:count() and v80:get(v83) == p76 then
                        v78 = v81 * v_u_34:count()
                        v79 = v82
                        v77 = true
                        break;
                    end;
                end;
                if v77 then
                    break;
                end;
            end;
        end;
        if not v77 then
            return false;
        end;
        v_u_40 = v78
        p75:update_list_elements(v79)
        return true;
    end;
    v32.setup_list_elements = function(p_u_84) --[[ Name: setup_list_elements ]] --[[ Line: 296 ]]
        --[[ Upvalues: (ref 1): v_u_2, (ref 2): v_u_33, (ref 3): v_u_35, (ref 4): v_u_4, (ref 5): v_u_17, (copy 6): p_u_29, (ref 7): v_u_41, (copy 8): p_u_28, (ref 9): v_u_9, (copy 10): v_u_34, (ref 11): v_u_40 ]]
        local v85 = v_u_2:new()
        for v86 = 1, 12 do
            local v87 = v_u_33.Anchors:FindFirstChild(string.format("%d", v86))
            v87.Parent = nil
            v85:push_back(v87)
        end;
        local l_InventoryItemProto_0 = v_u_33.InventoryItemProto
        l_InventoryItemProto_0.Parent = nil
        v_u_35 = v_u_4:new(p_u_84, v_u_33.PrimaryPart, v_u_33.InventoryItemHighlight)
        v_u_35:set_sgui(v_u_33.InventoryItemHighlight.SurfaceGui)
        for v_u_88 = 1, v85:count() do
            local v89 = l_InventoryItemProto_0:Clone()
            v89.Name = string.format("SongElementProto(%d)", v_u_88)
            v89.Parent = v_u_33
            local v90 = v_u_17:new(v_u_4:new(p_u_84, v_u_33.PrimaryPart, v89), p_u_29, function() --[[ Line: 318 ]]
                --[[ Upvalues: (ref 1): v_u_41, (copy 2): v_u_88, (copy 3): p_u_84, (ref 4): p_u_28, (ref 5): v_u_9 ]]
                v_u_41 = v_u_88
                p_u_84:update_selected_element()
                p_u_28._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
            end)
            v90:set_position(v85:get(v_u_88).Position)
            p_u_84:add_cycle_element(p_u_28, 1, v90)
            v_u_34:push_back(v90)
        end;
        v_u_41 = 1
        v_u_40 = 0
    end;
    v32.get_song_list = function(_) --[[ Name: get_song_list ]] --[[ Line: 335 ]]
        --[[ Upvalues: (copy 1): p_u_28, (ref 2): v_u_63, (ref 3): v_u_10, (ref 4): v_u_7 ]]
        local v91 = p_u_28._player_blob_manager:get_player_blob()
        local v_u_92 = string.lower(v_u_63:get_search_name())
        return v_u_10:song_inventory_sorted_view(v91, v_u_63:get_sort_fnkey()):remove_if(function(p93) --[[ Line: 338 ]]
            --[[ Upvalues: (ref 1): v_u_7, (copy 2): v_u_92 ]]
            return #v_u_92 > 0 and string.find(string.lower(v_u_7:singleton():get_title_for_key(p93)), v_u_92, 1, true) == nil and true or (v_u_7:singleton():key_is_remix_flagged(p93) and true or false);
        end);
    end;
    v32.update_list_elements = function(p94, p95) --[[ Name: update_list_elements ]] --[[ Line: 351 ]]
        --[[ Upvalues: (copy 1): p_u_28, (ref 2): v_u_8, (copy 3): v_u_34, (ref 4): v_u_40, (ref 5): v_u_7, (ref 6): v_u_10, (ref 7): v_u_41, (ref 8): v_u_36, (ref 9): v_u_37, (ref 10): v_u_35, (ref 11): v_u_62, (ref 12): v_u_61 ]]
        if p_u_28._player_blob_manager:is_synced() == false then
            v_u_8:warnf("SongInventoryV2UI:update_list_elements player_blob is not synced")
            return;
        else
            local v96 = p_u_28._player_blob_manager:get_player_blob()
            local v97 = p94:get_song_list()
            for v98 = 1, v_u_34:count() do
                local v99 = v_u_34:get(v98)
                local v100 = v_u_40 + v98
                if v97:count() < v100 then
                    v99:set_song_info_empty()
                else
                    local v101 = v97:get(v100)
                    if v_u_7:singleton():contains_key(v101) then
                        v99:set_song_info(v101, v_u_10:get_song_key_owned_count(v96, v101))
                    else
                        v99:set_song_info_empty()
                    end;
                end;
            end;
            if p95 == nil then
                v_u_41 = 1
            else
                v_u_41 = p95
            end;
            v_u_36:set_visible(v_u_40 > 1)
            v_u_37:set_visible(v_u_40 + v_u_34:count() < v97:count())
            if v97:count() == 0 then
                v_u_35:set_visible(false)
                v_u_62.Visible = true
                v_u_61:set_visible(false)
                p94:update_selected_element_none()
            else
                v_u_35:set_visible(true)
                v_u_62.Visible = false
                v_u_61:set_visible(true)
                p94:update_selected_element()
            end;
        end;
    end;
    v32.update_selected_element = function(p102) --[[ Name: update_selected_element ]] --[[ Line: 396 ]]
        --[[ Upvalues: (copy 1): p_u_28, (ref 2): v_u_8, (ref 3): v_u_35, (copy 4): v_u_34, (ref 5): v_u_41, (ref 6): v_u_27, (ref 7): v_u_7, (ref 8): v_u_54, (ref 9): v_u_58, (ref 10): v_u_57, (ref 11): v_u_56, (ref 12): v_u_55, (ref 13): v_u_59, (ref 14): v_u_46, (ref 15): v_u_47, (ref 16): v_u_15, (ref 17): v_u_48, (ref 18): v_u_10, (ref 19): v_u_51, (ref 20): v_u_49, (ref 21): v_u_50, (ref 22): v_u_52, (ref 23): v_u_53, (ref 24): v_u_14, (ref 25): v_u_60, (ref 26): v_u_13 ]]
        if p_u_28._player_blob_manager:is_synced() == false then
            v_u_8:warnf("SongInventoryV2UI:update_list_elements player_blob is not synced")
        end;
        local v103 = p_u_28._player_blob_manager:get_player_blob()
        v_u_35:set_position_scaled_offset(v_u_34:get(v_u_41):get_pos(), Vector2.new(-0.05, -0.15))
        for v104 = 1, v_u_34:count() do
            v_u_34:get(v104):set_inventory_selected(v104 == v_u_41)
        end;
        local v105 = v_u_34:get(v_u_41):get_song_key()
        if v105 == nil then
            v_u_27 = v_u_7:invalid_songkey()
            v_u_54.Visible = false
            v_u_58:set_visible(false)
            v_u_57:set_visible(false)
            v_u_57:set_enabled(false)
            v_u_56.Text = ""
            v_u_55.Visible = false
            v_u_59:set_visible(false)
            return;
        else
            v_u_27 = v105
            if v_u_7:singleton():contains_key(v105) then
                p_u_28._bgm_manager:preview_songkey(v105)
            end;
            if v_u_7:singleton():contains_key(v105) then
                p_u_28._game_join:set_last_loaded_songkey(v105)
            end;
            v_u_7:singleton():render_coverimage_for_key(v_u_46, v_u_47, v105)
            v_u_15:render_songkey_colorsection(v105, v_u_48)
            local v106 = v_u_10:get_song_key_owned_count(v103, v105)
            v_u_51.Text = v_u_7:singleton():get_title_for_key(v105)
            v_u_49.Text = v_u_7:singleton():get_artist_for_key(v105)
            v_u_50.Text = v106
            v_u_52.Text = v_u_7:singleton():get_description_for_key(v105)
            v_u_53.Text = string.format("%d", v_u_7:singleton():get_difficulty_for_key(v105))
            p102:opt_update_player_song_stat_info()
            local v107, v108 = v_u_7:singleton():key_has_combineinfo(v105)
            if v107 == true then
                v_u_54.Visible = true
                v_u_54.Text = string.format("Combine %d copies of this song to get a harder version!", v108.RequiredCount)
                v_u_58:set_visible(true)
                if v108.RequiredCount <= v106 then
                    v_u_58:set_enabled(true)
                else
                    v_u_58:set_enabled(false)
                end;
            else
                v_u_54.Visible = false
                v_u_58:set_visible(false)
            end;
            if v_u_14:singleton():get_songkey_recipe_id(v105) == nil then
                if v_u_7:singleton():key_is_fusionresult_of(v105) == nil or v_u_14:singleton():get_songkey_recipe_id(v_u_7:singleton():key_is_fusionresult_of(v105)) == nil then
                    v_u_57:set_visible(false)
                    v_u_57:set_enabled(false)
                    v_u_56.Text = ""
                else
                    v_u_57:set_visible(true)
                    v_u_57:set_enabled(true)
                    v_u_56.Text = "Craft more copies of the normal mode."
                end;
            else
                v_u_57:set_visible(true)
                v_u_57:set_enabled(true)
                v_u_56.Text = "Craft more copies."
            end;
            v_u_60:set_visible(true)
            if v_u_13:can_sell_key(v105) then
                v_u_55.Visible = true
                v_u_59:set_visible(true)
                if v_u_13:playerblob_can_sell_key(v103, v105) then
                    v_u_59:set_enabled(true)
                else
                    v_u_59:set_enabled(false)
                end;
            else
                v_u_55.Visible = false
                v_u_59:set_visible(false)
                return;
            end;
        end;
    end;
    v32.update_selected_element_none = function(_) --[[ Name: update_selected_element_none ]] --[[ Line: 492 ]]
        --[[ Upvalues: (ref 1): v_u_46, (ref 2): v_u_47, (ref 3): v_u_48, (ref 4): v_u_51, (ref 5): v_u_49, (ref 6): v_u_50, (ref 7): v_u_52, (ref 8): v_u_53, (ref 9): v_u_42, (ref 10): v_u_43, (ref 11): v_u_45, (ref 12): v_u_44, (ref 13): v_u_54, (ref 14): v_u_56, (ref 15): v_u_58, (ref 16): v_u_57, (ref 17): v_u_60, (ref 18): v_u_27, (ref 19): v_u_7 ]]
        v_u_46.Image = ""
        v_u_47.Image = ""
        v_u_48.Visible = false
        v_u_51.Text = "None"
        v_u_49.Text = ""
        v_u_50.Text = "n/a"
        v_u_52.Text = ""
        v_u_53.Text = "n/a"
        v_u_42.Text = "n/a"
        v_u_43.Text = "n/a"
        v_u_45.Text = "n/a"
        v_u_44.Text = "n/a"
        v_u_54.Visible = false
        v_u_56.Text = ""
        v_u_58:set_visible(false)
        v_u_57:set_visible(false)
        v_u_60:set_visible(false)
        v_u_27 = v_u_7:invalid_songkey()
    end;
    local v_u_109 = -1
    local v_u_110 = -1
    v32.opt_update_player_song_stat_info = function(_) --[[ Name: opt_update_player_song_stat_info ]] --[[ Line: 517 ]]
        --[[ Upvalues: (copy 1): v_u_34, (ref 2): v_u_41, (ref 3): v_u_109, (ref 4): v_u_110, (copy 5): p_u_28, (ref 6): v_u_43, (ref 7): v_u_44, (ref 8): v_u_45, (ref 9): v_u_42 ]]
        local v111 = v_u_34:get(v_u_41):get_song_key()
        if v111 ~= nil then
            if v111 ~= v_u_109 or v_u_110 ~= p_u_28._player_song_stats_manager:get_time_last_update() then
                v_u_109 = v111
                v_u_110 = p_u_28._player_song_stats_manager:get_time_last_update()
                v_u_43.Text = p_u_28._player_song_stats_manager:get_best_score_display_str(v111)
                v_u_44.Text = p_u_28._player_song_stats_manager:get_rank_display_str(v111)
                v_u_45.Text = p_u_28._player_song_stats_manager:get_playcount_display_str(v111)
                v_u_42.Text = p_u_28._player_song_stats_manager:get_best_grade_display_str(v111)
            end;
        end;
    end;
    v32.increment_selected_page_offset = function(p112, p113) --[[ Name: increment_selected_page_offset ]] --[[ Line: 533 ]]
        --[[ Upvalues: (copy 1): p_u_28, (ref 2): v_u_8, (ref 3): v_u_40 ]]
        if p_u_28._player_blob_manager:is_synced() == false then
            v_u_8:warnf("SongInventoryV2UI:increment_selected_page_offset is not synced")
            return;
        else
            local v114 = p_u_28._player_blob_manager:get_player_blob()
            local v115 = v_u_40 + p113
            if v115 >= 0 and #v114.SongInventory >= v115 then
                v_u_40 = v115
                p112:update_list_elements()
            end;
        end;
    end;
    v32.craft_button_pressed = function(_) --[[ Name: craft_button_pressed ]] --[[ Line: 549 ]]
        --[[ Upvalues: (copy 1): v_u_34, (ref 2): v_u_41, (copy 3): p_u_28, (ref 4): v_u_24 ]]
        p_u_28._menus:push_menu(v_u_24:new(p_u_28, p_u_28._spui, p_u_28._menus, (v_u_34:get(v_u_41):get_song_key())))
    end;
    v32.combine_button_pressed = function(p_u_116) --[[ Name: combine_button_pressed ]] --[[ Line: 567 ]]
        --[[ Upvalues: (copy 1): p_u_30, (ref 2): v_u_6, (copy 3): p_u_28, (copy 4): p_u_29, (copy 5): v_u_34, (ref 6): v_u_41, (ref 7): v_u_7, (ref 8): v_u_38, (ref 9): v_u_11 ]]
        local v_u_117 = p_u_30:push_menu(v_u_6:new(p_u_28, p_u_29, p_u_30):set_text("Combining...", ""):set_close_button_visible(false))
        local v_u_118 = v_u_34:get(v_u_41):get_song_key()
        p_u_28._shop_local_protocol:try_combine_song(v_u_118, function(p119, p_u_120, p121) --[[ Line: 570 ]]
            --[[ Upvalues: (ref 1): p_u_30, (copy 2): v_u_117, (ref 3): v_u_6, (ref 4): p_u_28, (ref 5): p_u_29, (copy 6): p_u_116, (copy 7): v_u_118, (ref 8): v_u_7, (ref 9): v_u_38, (ref 10): v_u_11 ]]
            if p119 == false or p_u_120 == nil then
                p_u_30:remove_menu(v_u_117)
                p_u_30:push_menu(v_u_6:new(p_u_28, p_u_29, p_u_30):set_text("Combine failed.", p121))
            else
                p_u_28._player_blob_manager:do_sync(function(_) --[[ Line: 577 ]]
                    --[[ Upvalues: (ref 1): p_u_116, (ref 2): v_u_118, (ref 3): v_u_7, (ref 4): v_u_38, (ref 5): p_u_30, (ref 6): v_u_117, (ref 7): v_u_11, (ref 8): p_u_28, (ref 9): p_u_29, (copy 10): p_u_120 ]]
                    local v122 = p_u_116:select_songkey(v_u_118)
                    if v122 ~= true then
                        local v123 = v_u_7:singleton():key_get_combine_result(v_u_118)
                        if v_u_7:singleton():contains_key(v123) then
                            v122 = p_u_116:select_songkey(v123)
                        end;
                    end;
                    if v122 ~= true then
                        p_u_116:update_list_elements()
                    end;
                    p_u_116:set_alpha(v_u_38, true)
                    p_u_30:remove_menu(v_u_117)
                    p_u_30:push_menu(v_u_11:new(p_u_28, p_u_29, p_u_30, p_u_120))
                end)
            end;
        end)
    end;
    v32.sell_button_pressed = function(p_u_124) --[[ Name: sell_button_pressed ]] --[[ Line: 595 ]]
        --[[ Upvalues: (copy 1): v_u_34, (ref 2): v_u_41, (ref 3): v_u_13, (copy 4): p_u_30, (ref 5): v_u_6, (copy 6): p_u_28, (copy 7): p_u_29, (ref 8): v_u_7, (ref 9): v_u_38, (ref 10): v_u_16, (ref 11): v_u_25, (ref 12): v_u_9 ]]
        local v_u_125 = v_u_34:get(v_u_41):get_song_key()
        p_u_30:push_menu(v_u_6:new(p_u_28, p_u_29, p_u_30):set_text("Confirm Sell", string.format("Confirm selling \"%s\" for [%s]?", v_u_7:singleton():get_title_for_key(v_u_125), (v_u_13:rewards_dict_to_string((v_u_13:get_sell_rewards_dict(v_u_125)))))):set_okay_button_fn(function() --[[ Line: 607 ]]
            --[[ Upvalues: (ref 1): p_u_30, (ref 2): v_u_6, (ref 3): p_u_28, (ref 4): p_u_29, (copy 5): v_u_125, (copy 6): p_u_124, (ref 7): v_u_38, (ref 8): v_u_16, (ref 9): v_u_25, (ref 10): v_u_9 ]]
            local v_u_126 = p_u_30:push_menu(v_u_6:new(p_u_28, p_u_29, p_u_30):set_text("Selling...", ""):set_close_button_visible(false))
            p_u_28._shop_local_protocol:try_sell_song(v_u_125, function(p127, p128, p_u_129) --[[ Line: 609 ]]
                --[[ Upvalues: (ref 1): p_u_30, (copy 2): v_u_126, (ref 3): v_u_6, (ref 4): p_u_28, (ref 5): p_u_29, (ref 6): p_u_124, (ref 7): v_u_125, (ref 8): v_u_38, (ref 9): v_u_16, (ref 10): v_u_25, (ref 11): v_u_9 ]]
                if p127 == false then
                    p_u_30:remove_menu(v_u_126)
                    p_u_30:push_menu(v_u_6:new(p_u_28, p_u_29, p_u_30):set_text("Sell failed.", p128))
                else
                    p_u_28._player_blob_manager:do_sync(function(_) --[[ Line: 616 ]]
                        --[[ Upvalues: (ref 1): p_u_124, (ref 2): v_u_125, (ref 3): v_u_38, (ref 4): p_u_30, (ref 5): v_u_126, (ref 6): v_u_16, (copy 7): p_u_129, (ref 8): v_u_25, (ref 9): p_u_28, (ref 10): p_u_29, (ref 11): v_u_9 ]]
                        if p_u_124:select_songkey(v_u_125) ~= true then
                            p_u_124:update_list_elements()
                            p_u_124:update_selected_element()
                        end;
                        p_u_124:set_alpha(v_u_38, true)
                        p_u_30:remove_menu(v_u_126)
                        p_u_30:push_menu(v_u_25:new(p_u_28, p_u_29, p_u_30, (v_u_16.RewardInfo:table_to_list(p_u_129))))
                        p_u_28._sfx_manager:play_sfx(v_u_9.SFX_ACQUIRE)
                    end)
                end;
            end)
        end))
    end;
    v32.layout = function(p130) --[[ Name: layout ]] --[[ Line: 639 ]]
        --[[ Upvalues: (copy 1): p_u_29, (ref 2): v_u_39, (ref 3): v_u_33, (ref 4): v_u_35, (ref 5): v_u_63 ]]
        p_u_29:uiobj_rescale_to_max_nxy(p130, 0.825, 0.88, v_u_39)
        v_u_33:SetPrimaryPartCFrame(p_u_29:get_cframe({
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p130:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        }))
        v_u_35:layout()
        v_u_63:layout()
    end;
    v32.visual_update = function(p131, p132, p133) --[[ Name: visual_update ]] --[[ Line: 651 ]]
        p131:visual_update_base(p132, p133)
    end;
    v32.select_last_selected_songkey_or_reset = function(p134) --[[ Name: select_last_selected_songkey_or_reset ]] --[[ Line: 655 ]]
        --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_7, (ref 3): v_u_41, (ref 4): v_u_40 ]]
        local v135
        if v_u_27 == v_u_7:invalid_songkey() then
            v135 = false
        else
            v135 = p134:select_songkey(v_u_27)
        end;
        if v135 ~= true then
            v_u_41 = 1
            v_u_40 = 0
            p134:update_list_elements()
        end;
        p134:update_selected_element()
    end;
    v32.on_refocus = function(p136) --[[ Name: on_refocus ]] --[[ Line: 668 ]]
        p136:select_last_selected_songkey_or_reset()
    end;
    local v_u_137 = false
    v32.behaviour_update = function(p138, p139, p140) --[[ Name: behaviour_update ]] --[[ Line: 673 ]]
        --[[ Upvalues: (ref 1): v_u_61, (ref 2): v_u_137, (copy 3): v_u_34, (ref 4): v_u_41, (copy 5): p_u_28, (ref 6): v_u_46, (ref 7): v_u_1, (ref 8): v_u_47, (ref 9): v_u_48, (ref 10): v_u_63, (ref 11): v_u_27, (ref 12): v_u_7 ]]
        p138:behaviour_update_base(p139, p140)
        if p138:is_current_mode_open() == true then
            local v141
            if v_u_61:get_selected() then
                v141 = 0
                if v_u_137 == false then
                    local v142 = v_u_34:get(v_u_41):get_song_key()
                    if v142 ~= nil then
                        p_u_28._player_song_stats_manager:request_ranks_for_songkey(v142)
                    end;
                end;
            else
                v141 = 1
            end;
            v_u_137 = v_u_61:get_selected()
            v_u_46.ImageTransparency = v_u_1:tra(v141)
            v_u_47.ImageTransparency = v_u_1:tra(v141)
            v_u_48.PrimaryColorIcon.ImageTransparency = v_u_1:tra(v141)
            v_u_48.SecondaryColorIcon.ImageTransparency = v_u_1:tra(v141)
            v_u_63:behaviour_update(p139, p140)
            local v143, v144, _ = v_u_63:raise_changed()
            if v143 then
                if v144 then
                    v_u_27 = v_u_7:invalid_songkey()
                end;
                p138:select_last_selected_songkey_or_reset()
            end;
            p138:opt_update_player_song_stat_info()
        end;
    end;
    v32.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 709 ]]
        --[[ Upvalues: (copy 1): p_u_28, (ref 2): v_u_64, (ref 3): v_u_33, (ref 4): v_u_63 ]]
        p_u_28._bgm_manager:stop_song_preview(v_u_64)
        v_u_33:Destroy()
        v_u_63:cleanup()
    end;
    v32.set_alpha = function(_, p145, p146) --[[ Name: set_alpha ]] --[[ Line: 715 ]]
        --[[ Upvalues: (ref 1): v_u_38, (ref 2): v_u_1, (ref 3): v_u_33 ]]
        if v_u_38 ~= p145 or p146 == true then
            v_u_38 = p145
            v_u_1:r_set_alpha(v_u_33, v_u_38)
        end;
    end;
    v32.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 721 ]]
        --[[ Upvalues: (ref 1): v_u_38 ]]
        return v_u_38;
    end;
    v32.set_scale = function(_, p147) --[[ Name: set_scale ]] --[[ Line: 722 ]]
        --[[ Upvalues: (ref 1): v_u_39 ]]
        v_u_39 = p147
    end;
    v32.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 723 ]]
        --[[ Upvalues: (ref 1): v_u_39 ]]
        return v_u_39;
    end;
    v32.get_native_size = function(p148) --[[ Name: get_native_size ]] --[[ Line: 725 ]]
        return p148._native_size;
    end;
    v32.get_size = function(p149) --[[ Name: get_size ]] --[[ Line: 728 ]]
        return p149._size;
    end;
    v32.set_size = function(p150, p151) --[[ Name: set_size ]] --[[ Line: 731 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        p150._size = p151
        v_u_33.PrimaryPart.Size = Vector3.new(p151.X, p151.Y, 0)
    end;
    v32.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 735 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        return v_u_33.PrimaryPart.Position;
    end;
    v32.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 738 ]]
        --[[ Upvalues: (ref 1): v_u_33 ]]
        return v_u_33.PrimaryPart.SurfaceGui;
    end;
    v32.set_showing = function(_, p152) --[[ Name: set_showing ]] --[[ Line: 741 ]]
        --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_12 ]]
        if p152 then
            v_u_33.Parent = v_u_12:get_world_ui_folder()
        else
            v_u_33.Parent = nil
        end;
    end;
    v32:cons()
    return v32;
end;
return v26;
