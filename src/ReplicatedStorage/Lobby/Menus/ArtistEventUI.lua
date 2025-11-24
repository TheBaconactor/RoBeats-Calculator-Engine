-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:46 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_9 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_10 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_11 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_12 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_13 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_16 = require(game.ReplicatedStorage.AudioData.SongElementalColor)
require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
local v_u_17 = require(game.ReplicatedStorage.Lobby.UI.TabControllerBase)
local v_u_18 = require(game.ReplicatedStorage.PlayerInfo.PurchaseUtils)
local v_u_19 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_20 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_21 = require(game.ReplicatedStorage.Shared.HUDNotification)
local v_u_22 = require(game.ReplicatedStorage.AudioData.SelectableArtists)
local v_u_23 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_24 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_25 = require(game.ReplicatedStorage.PlayerInfo.Collection.CollectionInfo)
local v_u_26 = require(game.ReplicatedStorage.LocalShared.PlayerPolicy)
local v27 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_28 = nil
local v_u_29 = nil
local v_u_30 = nil
local v_u_31 = nil
local v_u_32 = nil
local v_u_33 = nil
local v_u_34 = nil
local v_u_35 = nil
local v_u_36 = nil
local v_u_37 = nil
local v_u_38 = nil
local v_u_39 = nil
local v_u_40 = nil
local v_u_41 = nil
local v_u_42 = nil
local v_u_43 = nil
v27:require_client(function() --[[ Line: 48 ]]
    --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_30, (ref 3): v_u_31, (ref 4): v_u_32, (ref 5): v_u_33, (ref 6): v_u_34, (ref 7): v_u_29, (ref 8): v_u_35, (ref 9): v_u_36, (ref 10): v_u_37, (ref 11): v_u_38, (ref 12): v_u_39, (ref 13): v_u_40, (ref 14): v_u_41, (ref 15): v_u_42, (ref 16): v_u_43 ]]
    v_u_28 = require(game.ReplicatedStorage.Lobby.Menus.MatchMakingV3UI)
    v_u_30 = require(game.ReplicatedStorage.Lobby.UI.ArtistEventUI.ArtistEventUITab_Play)
    v_u_31 = require(game.ReplicatedStorage.Lobby.UI.ArtistEventUI.ArtistEventUITab_Shop)
    v_u_32 = require(game.ReplicatedStorage.Lobby.UI.ArtistEventUI.ArtistEventUITab_Leaderboard)
    v_u_33 = require(game.ReplicatedStorage.Lobby.UI.ArtistEventUI.ArtistEventUITab_PetAssignment)
    v_u_34 = require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
    v_u_29 = require(game.ReplicatedStorage.Lobby.UI.MatchMakingV3GameStageSelectSection)
    v_u_35 = require(game.ReplicatedStorage.Lobby.Menus.ListSelectUI)
    v_u_36 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
    v_u_37 = require(game.ReplicatedStorage.Lobby.UI.PlayUI.PlayUISettingsSection)
    v_u_38 = require(game.ReplicatedStorage.Lobby.Menus.SongAcquiredV2UI)
    v_u_39 = require(game.ReplicatedStorage.Lobby.UI.SongFavoriteButton)
    v_u_40 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
    v_u_41 = require(game.ReplicatedStorage.Lobby.UI.SongDisplayElement)
    v_u_42 = require(game.ReplicatedStorage.EditorGame.UI.SavedMapInfoListUI)
    v_u_43 = require(game.ReplicatedStorage.Menu.ScreenGuiTextBoxUI)
end)
local v_u_44 = {
    ["Tab"] = {
        ["Play"] = 1,
        ["Shop"] = 2,
        ["Leaderboard"] = 3,
        ["PetAssignment"] = 4
    },
    ["get_restore_menu_name"] = function(_) --[[ Name: get_restore_menu_name ]] --[[ Line: 81 ]]
        return "ArtistEventUI";
    end
}
local v_u_45 = false
local v_u_46 = 0
local v_u_47 = {
    ["Play"] = 1,
    ["Shop"] = 2,
    ["Leaderboard"] = 3,
    ["PetAssignment"] = 4
}
local l_Play_0 = v_u_47.Play
v_u_44.new = function(_, p_u_48, p_u_49, p_u_50) --[[ Name: new ]] --[[ Line: 83 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_44, (copy 3): v_u_13, (copy 4): v_u_2, (copy 5): v_u_14, (copy 6): v_u_7, (ref 7): v_u_45, (copy 8): v_u_12, (copy 9): v_u_1, (ref 10): v_u_37, (copy 11): v_u_5, (copy 12): v_u_4, (copy 13): v_u_9, (copy 14): v_u_20, (ref 15): v_u_43, (copy 16): v_u_11, (copy 17): v_u_10, (ref 18): v_u_38, (ref 19): v_u_39, (ref 20): v_u_41, (ref 21): v_u_42, (copy 22): v_u_23, (copy 23): v_u_47, (ref 24): v_u_30, (copy 25): v_u_17, (ref 26): l_Play_0, (ref 27): v_u_31, (copy 28): v_u_21, (ref 29): v_u_32, (ref 30): v_u_33, (ref 31): v_u_35, (copy 32): v_u_26, (copy 33): v_u_19, (copy 34): v_u_24, (copy 35): v_u_15, (copy 36): v_u_18, (ref 37): v_u_40, (copy 38): v_u_25, (copy 39): v_u_16, (copy 40): v_u_22, (ref 41): v_u_28, (copy 42): v_u_8, (copy 43): v_u_6 ]]
    local v_u_51 = v_u_3:new(p_u_49, p_u_50)
    v_u_51.get_restore_name = function(_) --[[ Name: get_restore_name ]] --[[ Line: 85 ]]
        --[[ Upvalues: (ref 1): v_u_44 ]]
        return v_u_44:get_restore_menu_name();
    end;
    local v_u_52 = nil
    v_u_51.get_uichild_parent = function(_) --[[ Name: get_uichild_parent ]] --[[ Line: 88 ]]
        --[[ Upvalues: (ref 1): v_u_52 ]]
        return v_u_52.PrimaryPart;
    end;
    local v_u_53 = 1
    local v_u_54 = v_u_13:invalid_songkey()
    v_u_51.get_selected_songkey = function(_) --[[ Name: get_selected_songkey ]] --[[ Line: 93 ]]
        --[[ Upvalues: (ref 1): v_u_54 ]]
        return v_u_54;
    end;
    local v_u_55 = nil
    local v_u_56 = -1
    v_u_51.get_event_id = function(_) --[[ Name: get_event_id ]] --[[ Line: 98 ]]
        --[[ Upvalues: (ref 1): v_u_56 ]]
        return v_u_56;
    end;
    local v_u_57 = v_u_2:new()
    local v_u_58 = v_u_2:new()
    local v_u_59 = nil
    local v_u_60 = nil
    local v_u_61 = 0
    local v_u_62 = nil
    local v_u_63 = nil
    local v_u_64 = nil
    local v_u_65 = nil
    local v_u_66 = nil
    local v_u_67 = nil
    local v_u_68 = nil
    local v_u_69 = nil
    local v_u_70 = nil
    local function f_cons() --[[ Name: cons ]] --[[ Line: 116 ]]
        --[[ Upvalues: (ref 1): v_u_14, (copy 2): p_u_48, (ref 3): v_u_7, (copy 4): p_u_50, (copy 5): v_u_51, (ref 6): v_u_56, (ref 7): v_u_45, (ref 8): v_u_52, (ref 9): v_u_12, (ref 10): v_u_1, (ref 11): v_u_64, (ref 12): v_u_65, (ref 13): v_u_37, (ref 14): v_u_5, (ref 15): v_u_4, (copy 16): p_u_49, (ref 17): v_u_9, (ref 18): v_u_20, (ref 19): v_u_43, (ref 20): v_u_11, (ref 21): v_u_67, (ref 22): v_u_54, (ref 23): v_u_13, (ref 24): v_u_10, (ref 25): v_u_38, (ref 26): v_u_66, (ref 27): v_u_39, (ref 28): v_u_68, (ref 29): v_u_41, (ref 30): v_u_69, (ref 31): v_u_42, (ref 32): v_u_70, (ref 33): v_u_61, (ref 34): v_u_55, (ref 35): v_u_59, (ref 36): v_u_60, (ref 37): v_u_23, (copy 38): v_u_58, (ref 39): v_u_47, (ref 40): v_u_30, (ref 41): v_u_17, (copy 42): v_u_57, (ref 43): l_Play_0, (ref 44): v_u_31, (ref 45): v_u_62, (ref 46): v_u_21, (ref 47): v_u_32, (ref 48): v_u_63, (ref 49): v_u_33 ]]
        local v71, v_u_72, _, v73 = v_u_14:is_event_active(p_u_48._player_blob_manager:get_day_event_list())
        if v71 == true then
            v_u_56 = v_u_72
            v_u_45 = false
            v_u_52 = v_u_12:get_lobby_ui_proto_root().Event.ArtistEventUI:Clone()
            v_u_52.Name = v_u_1:gen_name(v_u_52.Name)
            v_u_52.Parent = v_u_12:get_world_ui_folder()
            v_u_64 = p_u_48._bgm_manager:begin_preview_songkey()
            v_u_51._native_size = v_u_52.PrimaryPart.Size
            v_u_51._size = v_u_51._native_size
            v_u_65 = v_u_37:new(p_u_48, v_u_51, v_u_52, v_u_52.SettingsItems, v_u_52.MainSurface.SurfaceGui.Frame.SettingsSection)
            v_u_51:add_cycle_element(p_u_48, 1, v_u_5:new(v_u_4:new(v_u_51, v_u_52.PrimaryPart, v_u_52.BackButton), p_u_49, function() --[[ Line: 146 ]]
                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_9, (ref 3): p_u_50, (ref 4): v_u_51 ]]
                p_u_48._sfx_manager:play_sfx(v_u_9.SFX_MENU_CLOSE)
                p_u_50:remove_menu(v_u_51)
            end))
            v_u_51:add_cycle_element(p_u_48, 1, v_u_5:new(v_u_4:new(v_u_51, v_u_52.PrimaryPart, v_u_52.BuyEventPointsButton), p_u_49, function() --[[ Line: 155 ]]
                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_9, (ref 3): v_u_51 ]]
                p_u_48._sfx_manager:play_sfx(v_u_9.SFX_MENU_CLOSE)
                v_u_51:prompt_event_point_purchase()
            end))
            if v_u_20.PromoCodesActive == true and v_u_52:FindFirstChild("EnterPromoButton") then
                v_u_51:add_cycle_element(p_u_48, 1, v_u_5:new(v_u_4:new(v_u_51, v_u_52.PrimaryPart, v_u_52.EnterPromoButton), p_u_49, function() --[[ Line: 165 ]]
                    --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_9, (ref 3): v_u_43, (ref 4): v_u_51 ]]
                    p_u_48._sfx_manager:play_sfx(v_u_9.SFX_MENU_CLOSE)
                    v_u_43:show_text_input_box_ui(p_u_48, "Promo Codes", "Enter promo codes to redeem rewards!", "", function(p74) --[[ Line: 176 ]]
                        --[[ Upvalues: (ref 1): v_u_51 ]]
                        v_u_51:promo_button_pressed(p74)
                    end):set_text_box_empty_text("Enter promo code here..."):set_max_length(64)
                end))
            end;
            v_u_51:add_cycle_element(p_u_48, 1, v_u_5:new(v_u_4:new(v_u_51, v_u_52.PrimaryPart, v_u_52.InfoButton), p_u_49, function() --[[ Line: 189 ]]
                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_9, (ref 3): p_u_50, (ref 4): v_u_11, (ref 5): p_u_49, (ref 6): v_u_14 ]]
                p_u_48._sfx_manager:play_sfx(v_u_9.SFX_MENU_OPEN)
                p_u_50:push_menu(v_u_11:new(p_u_48, p_u_49, p_u_50):set_text("Artist Featuring Event", string.format("Earn event points by playing featured songs to buy limited-time items. Event points are applicable to the current event only. The following actions earn event points...\n\nPlay featured song with minimum accuracy requirement:\n ~%d point(s) per minute song length, scaled to accuracy.\nCheer for featured song: %d point(s).\nReceive cheer for featured song: %d point(s).", v_u_14:get_play_event_point_count(), v_u_14:get_cheer_event_point_count(), v_u_14:get_cheer_event_point_count())))
            end))
            v_u_67 = v_u_51:add_cycle_element(p_u_48, 1, v_u_5:new(v_u_4:new(v_u_51, v_u_52.PrimaryPart, v_u_52.BuySongButton), p_u_49, function() --[[ Line: 208 ]]
                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_9, (ref 3): v_u_14, (copy 4): v_u_72, (ref 5): v_u_54, (ref 6): v_u_7, (ref 7): p_u_50, (ref 8): v_u_11, (ref 9): p_u_49, (ref 10): v_u_13, (ref 11): v_u_10, (ref 12): v_u_51, (ref 13): v_u_38 ]]
                p_u_48._sfx_manager:play_sfx(v_u_9.SFX_MENU_OPEN)
                local v75, v_u_76 = v_u_14:get_eventid_songkey_purchase_info(v_u_72, v_u_54)
                if v75 ~= true then
                    return v_u_7:warnf("BuySongButton - can_buy false");
                end;
                p_u_50:push_menu(v_u_11:new(p_u_48, p_u_49, p_u_50):set_text("Buy Song", string.format("Buy song \'%s\' for %d Event Points?", v_u_13:singleton():get_title_for_key(v_u_54), v_u_76)):set_okay_button_fn(function() --[[ Line: 222 ]]
                    --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_14, (copy 3): v_u_76, (ref 4): p_u_50, (ref 5): v_u_11, (ref 6): p_u_49, (ref 7): v_u_10, (ref 8): v_u_51, (ref 9): v_u_38, (ref 10): v_u_54 ]]
                    if v_u_76 <= v_u_14:playerblob_get_event_points((p_u_48._player_blob_manager:get_player_blob())) then
                        local v_u_77 = p_u_50:push_menu(v_u_11:new(p_u_48, p_u_49, p_u_50):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                        p_u_48._evt:wait_on_event_once(v_u_10.EVT_ArtistEvent_BuySong_Server, function(p_u_78, p_u_79) --[[ Line: 230 ]]
                            --[[ Upvalues: (ref 1): p_u_48, (copy 2): v_u_77, (ref 3): v_u_51, (ref 4): p_u_50, (ref 5): v_u_11, (ref 6): p_u_49, (ref 7): v_u_38, (ref 8): v_u_54 ]]
                            p_u_48._player_blob_manager:do_sync(function() --[[ Line: 231 ]]
                                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_77, (ref 3): v_u_51, (copy 4): p_u_78, (ref 5): p_u_50, (ref 6): v_u_11, (ref 7): p_u_49, (copy 8): p_u_79, (ref 9): v_u_38, (ref 10): v_u_54 ]]
                                p_u_48._menus:remove_menu(v_u_77)
                                v_u_51:update_player_info_section()
                                if p_u_78 ~= true then
                                    return p_u_50:push_menu(v_u_11:new(p_u_48, p_u_49, p_u_50):set_text("Failed", p_u_79));
                                end;
                                p_u_50:push_menu(v_u_38:new(p_u_48, p_u_49, p_u_50, v_u_54))
                            end)
                        end)
                        p_u_48._evt:fire_event_to_server(v_u_10.EVT_ArtistEvent_BuySong_Client, v_u_54)
                    else
                        v_u_51:prompt_event_point_purchase()
                    end;
                end))
            end):set_passive_anim(true))
            v_u_5:button_add_enabled_anim(v_u_67, function() --[[ Line: 248 ]]
                --[[ Upvalues: (ref 1): v_u_51 ]]
                return v_u_51:get_alpha();
            end)
            v_u_67:set_visible(false)
            v_u_66 = v_u_39:new(p_u_48, v_u_51, v_u_4:new(v_u_51, v_u_52.PrimaryPart, v_u_52.FavoriteButton), v_u_52.FavoriteButton.SurfaceGui.Button.Icon):set_fn_get_selected_songkey(function() --[[ Line: 257 ]]
                --[[ Upvalues: (ref 1): v_u_54 ]]
                return v_u_54;
            end)
            v_u_68 = v_u_51:add_cycle_element(p_u_48, 1, v_u_5:new(v_u_4:new(v_u_51, v_u_52.PrimaryPart, v_u_52.SongInfoButton), p_u_49, function() --[[ Line: 262 ]]
                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_9, (ref 3): v_u_54, (ref 4): v_u_13, (ref 5): v_u_41 ]]
                p_u_48._sfx_manager:play_sfx(v_u_9.SFX_MENU_OPEN)
                if v_u_54 ~= v_u_13:invalid_songkey() then
                    v_u_41:show_song_info_popup(p_u_48, v_u_54)
                end;
            end))
            v_u_68:set_visible(false)
            v_u_69 = v_u_51:add_cycle_element(p_u_48, 1, v_u_5:new(v_u_4:new(v_u_51, v_u_52.PrimaryPart, v_u_52.SongEditorButton), p_u_49, function() --[[ Line: 274 ]]
                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_9, (ref 3): v_u_54, (ref 4): v_u_13, (ref 5): v_u_42 ]]
                p_u_48._sfx_manager:play_sfx(v_u_9.SFX_MENU_OPEN)
                if v_u_54 ~= v_u_13:invalid_songkey() then
                    v_u_42:show_published_map_list_ui_for_songkey(p_u_48, v_u_54)
                end;
            end))
            v_u_69:set_visible(false)
            v_u_70 = v_u_51:add_cycle_element(p_u_48, 1, v_u_5:new(v_u_4:new(v_u_51, v_u_52.PrimaryPart, v_u_52.EventEditorButton), p_u_49, function() --[[ Line: 286 ]]
                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_9, (ref 3): v_u_42 ]]
                p_u_48._sfx_manager:play_sfx(v_u_9.SFX_MENU_OPEN)
                v_u_42:show_published_map_list_ui_for_artist_event(p_u_48)
            end))
            local v80 = v_u_14:get_event_info(v_u_72)
            v_u_61 = v73 * 86400 + p_u_48._player_blob_manager:get_time_to_next_day_sec()
            local l_Frame_0 = v_u_52.MainSurface.SurfaceGui.Frame
            v_u_55 = l_Frame_0.SongInfoSection
            v_u_55.LoadedSection.Visible = false
            v_u_55.EmptySection.Visible = true
            local l_NewsSection_0 = l_Frame_0.NewsArea.NewsSection
            l_NewsSection_0.NewsHead.Text = v80:get_title()
            l_NewsSection_0.NewsSub.Text = v80:get_description()
            l_NewsSection_0.NewsImage.Image = v80:get_image()
            v_u_59 = l_Frame_0.PlayerInfoSection.EventPointsDisplay
            v_u_59.Text = ""
            v_u_60 = l_Frame_0.PlayerInfoSection.TimeSection.Display
            v_u_60.Text = "-"
            v_u_51:update_player_info_section()
            local v81 = v_u_52:FindFirstChild("EventPointsBonusButton")
            if v81 and v80:has_event_point_purchase_rewards() then
                local v_u_82 = v80:get_event_point_purchase_rewards()
                v_u_51:add_cycle_element(p_u_48, 1, v_u_5:new(v_u_4:new(v_u_51, v_u_52.PrimaryPart, v81), p_u_49, function() --[[ Line: 318 ]]
                    --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_9, (ref 3): p_u_50, (ref 4): v_u_11, (ref 5): p_u_49, (ref 6): v_u_23, (copy 7): v_u_82 ]]
                    p_u_48._sfx_manager:play_sfx(v_u_9.SFX_MENU_OPEN)
                    p_u_50:push_menu(v_u_11:new(p_u_48, p_u_49, p_u_50):set_text("Event Point Purchase Bonus", string.format("A portion of the proceeds from Event Point Purchases made with Robux during this event will go to the artists or label. In addition, for every 50 Robux spent, you will also get: %s", v_u_23:generate_only_items_description_from_rewardinfo_list(v_u_82))))
                end))
            else
                v81.Parent = nil
            end;
            v_u_58:add(v_u_47.Play, v_u_30:new(p_u_48, v_u_51, v_u_52))
            v_u_17:create_tab_to_button(v_u_47.Play, v_u_51, v_u_4:new(v_u_51, v_u_52.PrimaryPart, v_u_52.Tabs.TabPlay), p_u_48, v_u_57, function() --[[ Line: 339 ]]
                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_9, (ref 3): l_Play_0, (ref 4): v_u_47, (ref 5): v_u_51 ]]
                p_u_48._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
                l_Play_0 = v_u_47.Play
                v_u_51:update_selected_tab()
            end)
            v_u_58:add(v_u_47.Shop, v_u_31:new(p_u_48, v_u_51, v_u_52))
            v_u_17:create_tab_to_button(v_u_47.Shop, v_u_51, v_u_4:new(v_u_51, v_u_52.PrimaryPart, v_u_52.Tabs.TabShop), p_u_48, v_u_57, function() --[[ Line: 346 ]]
                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_9, (ref 3): l_Play_0, (ref 4): v_u_47, (ref 5): v_u_51 ]]
                p_u_48._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
                l_Play_0 = v_u_47.Shop
                v_u_51:update_selected_tab()
            end)
            if v_u_20.EventLeaderboardsEnabled == true then
                v_u_62 = v_u_21:create_display_wrapper(v_u_52.Tabs.TabLeaderboard.SurfaceGui.Frame.Notification, v_u_52.Tabs.TabLeaderboard.SurfaceGui.Frame.Notification.Display)
                v_u_58:add(v_u_47.Leaderboard, v_u_32:new(p_u_48, v_u_51, v_u_52, p_u_50))
                v_u_17:create_tab_to_button(v_u_47.Leaderboard, v_u_51, v_u_4:new(v_u_51, v_u_52.PrimaryPart, v_u_52.Tabs.TabLeaderboard), p_u_48, v_u_57, function() --[[ Line: 358 ]]
                    --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_9, (ref 3): l_Play_0, (ref 4): v_u_47, (ref 5): v_u_51 ]]
                    p_u_48._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
                    l_Play_0 = v_u_47.Leaderboard
                    v_u_51:update_selected_tab()
                end)
            else
                v_u_52.MainSurface.SurfaceGui.Frame.TabLeaderboard.Visible = false
                v_u_52.Tabs.TabLeaderboard.Parent = nil
                v_u_52.TabLeaderboardElements.Parent = nil
            end;
            if v_u_20.PetAssignmentEnabled == true then
                v_u_63 = v_u_21:create_display_wrapper(v_u_52.Tabs.TabPetAssignment.SurfaceGui.Frame.Notification, v_u_52.Tabs.TabPetAssignment.SurfaceGui.Frame.Notification.Display)
                v_u_58:add(v_u_47.PetAssignment, v_u_33:new(p_u_48, v_u_51, v_u_52, p_u_50))
                v_u_17:create_tab_to_button(v_u_47.PetAssignment, v_u_51, v_u_4:new(v_u_51, v_u_52.PrimaryPart, v_u_52.Tabs.TabPetAssignment), p_u_48, v_u_57, function() --[[ Line: 375 ]]
                    --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_9, (ref 3): l_Play_0, (ref 4): v_u_47, (ref 5): v_u_51 ]]
                    p_u_48._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
                    l_Play_0 = v_u_47.PetAssignment
                    v_u_51:update_selected_tab()
                end)
            end;
            v_u_51:update_selected_tab()
            if v_u_14:playerblob_needs_event_info_validate(p_u_48._player_blob_manager:get_player_blob(), v_u_72) then
                p_u_48._update_enqueue_fn:enqueue_function(function() --[[ Line: 388 ]]
                    --[[ Upvalues: (ref 1): p_u_50, (ref 2): v_u_11, (ref 3): p_u_48, (ref 4): p_u_49, (ref 5): v_u_10, (ref 6): v_u_51 ]]
                    local v_u_83 = p_u_50:push_menu(v_u_11:new(p_u_48, p_u_49, p_u_50):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                    p_u_48._evt:wait_on_event_once(v_u_10.EVT_ArtistEvent_ValidatePlayer_Server, function(_, _) --[[ Line: 394 ]]
                        --[[ Upvalues: (ref 1): p_u_48, (copy 2): v_u_83, (ref 3): v_u_51 ]]
                        p_u_48._player_blob_manager:do_sync(function(_) --[[ Line: 395 ]]
                            --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_83, (ref 3): v_u_51 ]]
                            p_u_48._menus:remove_menu(v_u_83)
                            v_u_51:update_player_info_section()
                        end)
                    end)
                    p_u_48._evt:fire_event_to_server(v_u_10.EVT_ArtistEvent_ValidatePlayer_Client)
                end)
            end;
        else
            v_u_7:warnf("ArtistEventUI attempted to open, ArtistEventInfo:is_event_active false")
            p_u_50:remove_menu(v_u_51)
        end;
    end;
    v_u_51.prompt_event_point_purchase = function(p_u_84) --[[ Name: prompt_event_point_purchase ]] --[[ Line: 405 ]]
        --[[ Upvalues: (ref 1): v_u_35, (copy 2): p_u_48, (ref 3): v_u_26, (ref 4): v_u_7, (ref 5): v_u_19, (ref 6): v_u_14, (ref 7): v_u_24, (ref 8): v_u_56, (ref 9): v_u_1, (ref 10): v_u_15, (ref 11): v_u_9, (ref 12): v_u_18, (copy 13): p_u_49, (copy 14): p_u_50, (ref 15): v_u_11, (ref 16): v_u_10, (ref 17): v_u_40, (ref 18): v_u_23 ]]
        local v_u_85 = nil
        v_u_85 = v_u_35:new(p_u_48, p_u_48._spui, p_u_48._menus, function(p86) --[[ Line: 411 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_7, (ref 3): v_u_19, (ref 4): v_u_14 ]]
            p86:set_header_text("Buy Event Points")
            if v_u_26:has_any_paid_item_restrictions() then
                v_u_7:warnf("PlayerPolicy disabling event point purchase")
            else
                p86:get_element_list():push_back(v_u_19.ProductID_EventPoint2000)
                p86:get_element_list():push_back(v_u_19.ProductID_EventPoint1000)
            end;
            for _, v89 in v_u_14:get_star_purchase_id_to_info():key_list():sort(function(p87, p88) --[[ Line: 419 ]]
                return p87 - p88;
            end):key_itr() do
                p86:get_element_list():push_back(v89)
            end;
        end, function(p90, p91, p92, _, p93) --[[ Line: 423 ]]
            --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_24, (ref 3): v_u_19, (ref 4): v_u_14, (ref 5): v_u_56, (ref 6): v_u_1, (ref 7): v_u_15 ]]
            local v94 = p_u_48._player_blob_manager:get_player_blob()
            if v_u_24:test_enum_member(p90, v_u_19) then
                local v95 = v_u_19:get_info_data_for_productid(p90)
                if v_u_14:get_event_info(v_u_56):has_event_point_purchase_rewards() then
                    p91.Text = string.format("%s (+Bonus)", v95:get_name())
                else
                    p91.Text = v95:get_name()
                end;
                p92.Image = v_u_1:important_assetid()
                p93:get_description_display().Text = string.format("%d Robux", v95:get_robux_cost())
                p93:set_select_button_enabled(true)
            elseif v_u_14:get_star_purchase_id_to_info():contains(p90) then
                local v96 = v_u_14:get_star_purchase_id_to_info():get(p90)
                p91.Text = string.format("%d Event Points", v96:get_event_point_amount())
                p92.Image = v_u_1:important_assetid()
                p93:get_description_display().Text = string.format("%d Stars", v96:get_star_amount())
                p93:set_select_button_enabled(v_u_15:get_star_currency(v94) >= v96:get_star_amount())
            end;
        end, function(p_u_97) --[[ Line: 445 ]]
            --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_9, (ref 3): v_u_24, (ref 4): v_u_19, (ref 5): v_u_18, (ref 6): p_u_49, (ref 7): p_u_50, (copy 8): p_u_84, (ref 9): v_u_85, (ref 10): v_u_14, (ref 11): v_u_11, (ref 12): v_u_10, (ref 13): v_u_40, (ref 14): v_u_23 ]]
            if p_u_97 == nil then
                return;
            else
                p_u_48._sfx_manager:play_sfx(v_u_9.SFX_BUTTONPRESS)
                if v_u_24:test_enum_member(p_u_97, v_u_19) then
                    v_u_18:purchase_prompt(p_u_48, p_u_49, p_u_50, p_u_97, function() --[[ Line: 449 ]]
                        --[[ Upvalues: (ref 1): p_u_84, (ref 2): p_u_48, (ref 3): v_u_9 ]]
                        p_u_84:load_current_tab()
                        p_u_48._sfx_manager:play_sfx(v_u_9.SFX_FANFARE)
                    end)
                    p_u_48._menus:remove_menu(v_u_85)
                elseif v_u_14:get_star_purchase_id_to_info():contains(p_u_97) then
                    local v98 = v_u_14:get_star_purchase_id_to_info():get(p_u_97)
                    p_u_48._menus:push_menu(v_u_11:new(p_u_48, p_u_48._spui, p_u_48._menus):set_text("Confirm", (string.format("Are you sure you want to buy %d Event Points for %d Stars?", v98:get_event_point_amount(), v98:get_star_amount()))):set_okay_button_fn(function() --[[ Line: 462 ]]
                        --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_11, (ref 3): v_u_10, (ref 4): v_u_85, (ref 5): p_u_50, (ref 6): v_u_40, (ref 7): p_u_49, (ref 8): v_u_23, (copy 9): p_u_97 ]]
                        local v_u_99 = p_u_48._menus:push_menu(v_u_11:new(p_u_48, p_u_48._spui, p_u_48._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
                        p_u_48._evt:wait_on_event_once(v_u_10.EVT_ArtistEvent_BuyEventPointStars_ServerResponse, function(p100, p101, p_u_102) --[[ Line: 464 ]]
                            --[[ Upvalues: (ref 1): p_u_48, (copy 2): v_u_99, (ref 3): v_u_11, (ref 4): v_u_85, (ref 5): p_u_50, (ref 6): v_u_40, (ref 7): p_u_49, (ref 8): v_u_23 ]]
                            if p100 ~= true then
                                p_u_48._menus:remove_menu(v_u_99)
                                return p_u_48._menus:push_menu(v_u_11:new(p_u_48, p_u_48._spui, p_u_48._menus):set_text("Error", p101));
                            end;
                            p_u_48._player_blob_manager:do_sync(function() --[[ Line: 469 ]]
                                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_85, (ref 3): v_u_99, (ref 4): p_u_50, (ref 5): v_u_40, (ref 6): p_u_49, (ref 7): v_u_23, (copy 8): p_u_102 ]]
                                p_u_48._menus:remove_menu(v_u_85)
                                p_u_48._menus:remove_menu(v_u_99)
                                p_u_50:push_menu(v_u_40:new(p_u_48, p_u_49, p_u_50, v_u_23.RewardInfo:table_to_list(p_u_102)):set_header_text("Event Points Purchased!"))
                            end)
                        end)
                        p_u_48._evt:fire_event_to_server(v_u_10.EVT_ArtistEvent_BuyEventPointStars_Client, p_u_97)
                    end))
                end;
            end;
        end, function(p103) --[[ Line: 483 ]]
            --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_1, (ref 3): v_u_14 ]]
            p103:set_sub_text(string.format("Event Points(s): %s", v_u_1:comma_value(v_u_14:playerblob_get_event_points((p_u_48._player_blob_manager:get_player_blob())))))
        end):set_close_on_element_select(false)
        p_u_48._menus:push_menu(v_u_85)
    end;
    v_u_51.update_player_info_section = function(_) --[[ Name: update_player_info_section ]] --[[ Line: 491 ]]
        --[[ Upvalues: (copy 1): p_u_48, (ref 2): v_u_59, (ref 3): v_u_1, (ref 4): v_u_14, (ref 5): l_Play_0, (ref 6): v_u_47, (ref 7): v_u_56, (ref 8): v_u_54, (ref 9): v_u_13, (ref 10): v_u_67, (ref 11): v_u_15, (ref 12): v_u_25, (ref 13): v_u_66 ]]
        local v104 = p_u_48._player_blob_manager:get_player_blob()
        v_u_59.Text = v_u_1:comma_value(v_u_14:playerblob_get_event_points(v104))
        local v105 = l_Play_0 == v_u_47.Play
        local v106, _ = v_u_14:get_eventid_songkey_purchase_info(v_u_56, v_u_54)
        if v105 and v_u_13:singleton():contains_key(v_u_54) then
            v_u_67:set_visible(true)
            if v106 and (v_u_15:get_song_key_owned_count(v104, v_u_54) == 0 and v_u_25:get_playerblob_songkey_in_collection(v104, v_u_54, p_u_48._player_blob_manager:get_cached_collection_info()) ~= true) then
                v_u_67:set_enabled(true)
            else
                v_u_67:set_enabled(false)
            end;
        else
            v_u_67:set_visible(false)
        end;
        v_u_66:refresh_display()
    end;
    v_u_51.update_selected_tab = function(p107) --[[ Name: update_selected_tab ]] --[[ Line: 513 ]]
        --[[ Upvalues: (copy 1): v_u_57, (ref 2): l_Play_0, (ref 3): v_u_1, (copy 4): v_u_58 ]]
        for v108, v109 in v_u_57:key_itr() do
            if v108 == l_Play_0 then
                v109:get_part().SurfaceGui.Frame.Tab_Container.Image = v_u_1:get_tab_selected_container_assetid()
                v109:set_unselected_zoffset(300)
            else
                v109:get_part().SurfaceGui.Frame.Tab_Container.Image = v_u_1:get_tab_unselected_container_assetid()
                v109:set_unselected_zoffset(200)
            end;
        end;
        for v110, v111 in v_u_58:key_itr() do
            if v110 ~= l_Play_0 then
                v111:set_visible(false)
            end;
        end;
        p107:load_current_tab()
    end;
    local v_u_112 = 0
    v_u_51.get_last_load_start_time = function(_) --[[ Name: get_last_load_start_time ]] --[[ Line: 533 ]]
        --[[ Upvalues: (ref 1): v_u_112 ]]
        return v_u_112;
    end;
    v_u_51.load_current_tab = function(p113) --[[ Name: load_current_tab ]] --[[ Line: 534 ]]
        --[[ Upvalues: (copy 1): v_u_58, (ref 2): l_Play_0, (ref 3): v_u_112, (copy 4): p_u_48, (ref 5): v_u_65 ]]
        if v_u_58:contains(l_Play_0) then
            v_u_112 = p_u_48._player_blob_manager:get_global_time_float()
            local v_u_114 = v_u_112
            local v115 = v_u_58:get(l_Play_0)
            v115:set_visible(true)
            v115:load_data(function() --[[ Line: 541 ]]
                --[[ Upvalues: (copy 1): v_u_114, (ref 2): v_u_112, (ref 3): v_u_58, (ref 4): l_Play_0 ]]
                if v_u_114 == v_u_112 then
                    v_u_58:get(l_Play_0):refresh()
                end;
            end)
            if typeof(v115.is_settings_section_visible) == "function" and v115:is_settings_section_visible() == true then
                v_u_65:set_visible(true)
            else
                v_u_65:set_visible(false)
            end;
        end;
        p113:update_player_info_section()
    end;
    v_u_51.preview_songkey = function(p116, p117) --[[ Name: preview_songkey ]] --[[ Line: 556 ]]
        --[[ Upvalues: (ref 1): v_u_13, (copy 2): p_u_48, (ref 3): v_u_54, (ref 4): v_u_68, (ref 5): v_u_69, (ref 6): v_u_55, (ref 7): v_u_16, (ref 8): v_u_22, (ref 9): v_u_1 ]]
        if v_u_13:singleton():contains_key(p117) then
            p_u_48._game_join:set_last_loaded_songkey(p117)
        end;
        v_u_54 = p117
        v_u_68:set_visible(true)
        v_u_69:set_visible(true)
        v_u_55.LoadedSection.Visible = true
        v_u_55.EmptySection.Visible = false
        local l_LoadedSection_0 = v_u_55.LoadedSection
        v_u_13:singleton():render_coverimage_for_key(l_LoadedSection_0.CoverBack.AlbumArt, l_LoadedSection_0.CoverBack.AlbumArtOverlay, v_u_54)
        v_u_16:render_songkey_colorsection(v_u_54, l_LoadedSection_0.CoverBack.ColorSection)
        l_LoadedSection_0.CoverBack.SongDifficultySection.Display.TextColor3 = v_u_13:singleton():get_difficulty_color_for_key(v_u_54)
        l_LoadedSection_0.CoverBack.SongDifficultySection.Display.Text = tostring(v_u_13:singleton():get_difficulty_for_key(v_u_54))
        l_LoadedSection_0.ArtistDisplay.Text = v_u_13:singleton():get_artist_for_key(v_u_54)
        l_LoadedSection_0.DescriptionDisplay.Text = v_u_13:singleton():get_description_for_key(v_u_54)
        l_LoadedSection_0.NameDisplay.Text = v_u_13:singleton():get_title_for_key(v_u_54)
        local v118, v119 = v_u_22:artist_name_is_selectable(v_u_13:singleton():get_artist_for_key(v_u_54))
        l_LoadedSection_0.ArtistIconDisplay.Visible = v118
        if v118 and #v_u_22:artist_name_to_icon(v119) > 0 then
            l_LoadedSection_0.ArtistIconDisplay.Image = v_u_22:artist_name_to_icon(v119)
        else
            l_LoadedSection_0.ArtistIconDisplay.Image = v_u_1:transparent_assetid()
        end;
        p_u_48._bgm_manager:preview_songkey(p117)
        p116:update_player_info_section()
    end;
    v_u_51.play_button_pressed = function(_) --[[ Name: play_button_pressed ]] --[[ Line: 588 ]]
        --[[ Upvalues: (ref 1): v_u_54, (ref 2): v_u_13, (ref 3): v_u_7, (copy 4): p_u_48, (ref 5): v_u_28 ]]
        if v_u_54 == v_u_13:invalid_songkey() then
            return v_u_7:warnf("NewSongEventUI:play_button_pressed invalid songkey");
        end;
        p_u_48._menus:push_menu(v_u_28:new(p_u_48, p_u_48._spui, p_u_48._menus, v_u_54, nil))
    end;
    v_u_51.promo_button_pressed = function(_, p120) --[[ Name: promo_button_pressed ]] --[[ Line: 597 ]]
        --[[ Upvalues: (copy 1): p_u_48, (ref 2): v_u_11, (ref 3): v_u_10, (ref 4): v_u_9, (copy 5): p_u_50, (ref 6): v_u_40, (copy 7): p_u_49, (ref 8): v_u_23 ]]
        p_u_48._player_blob_manager:get_player_blob()
        local v_u_121 = p_u_48._menus:push_menu(v_u_11:new(p_u_48, p_u_48._spui, p_u_48._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
        p_u_48._evt:wait_on_event_once(v_u_10.EVT_ArtistEvent_SendPromo_ServerResponse, function(p_u_122, p_u_123, p_u_124) --[[ Line: 605 ]]
            --[[ Upvalues: (ref 1): p_u_48, (copy 2): v_u_121, (ref 3): v_u_9, (ref 4): v_u_11, (ref 5): p_u_50, (ref 6): v_u_40, (ref 7): p_u_49, (ref 8): v_u_23 ]]
            p_u_48._player_blob_manager:do_sync(function() --[[ Line: 606 ]]
                --[[ Upvalues: (ref 1): p_u_48, (ref 2): v_u_121, (copy 3): p_u_122, (ref 4): v_u_9, (ref 5): v_u_11, (copy 6): p_u_123, (copy 7): p_u_124, (ref 8): p_u_50, (ref 9): v_u_40, (ref 10): p_u_49, (ref 11): v_u_23 ]]
                p_u_48._menus:remove_menu(v_u_121)
                if p_u_122 == true then
                    if typeof(p_u_124) == "table" and #p_u_124 > 0 then
                        p_u_50:push_menu(v_u_40:new(p_u_48, p_u_49, p_u_50, v_u_23.RewardInfo:table_to_list(p_u_124)):set_header_text("Promo code redeemed!"))
                    else
                        p_u_48._menus:push_menu(v_u_11:new(p_u_48, p_u_49, p_u_50):set_text("Promo Code", p_u_123))
                        p_u_48._sfx_manager:play_sfx(v_u_9.SFX_ACQUIRE)
                    end;
                else
                    p_u_48._sfx_manager:play_sfx(v_u_9.SFX_FAIL)
                    return p_u_48._menus:push_menu(v_u_11:new(p_u_48, p_u_48._spui, p_u_48._menus):set_text("Error", (tostring(p_u_123))));
                end;
            end)
        end)
        p_u_48._evt:fire_event_to_server(v_u_10.EVT_ArtistEvent_SendPromo_Client, p120)
    end;
    v_u_51.layout = function(p125) --[[ Name: layout ]] --[[ Line: 635 ]]
        --[[ Upvalues: (copy 1): p_u_49, (ref 2): v_u_53, (ref 3): v_u_52, (copy 4): v_u_58 ]]
        p_u_49:uiobj_rescale_to_max_nxy(p125, 0.85, 0.9, v_u_53)
        v_u_52:SetPrimaryPartCFrame(p_u_49:get_cframe({
            ["PositionNXY"] = Vector2.new(0.5, 0.5),
            ["OffsetXYZ"] = p125:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        }))
        for _, v126 in v_u_58:key_itr() do
            v126:layout()
        end;
    end;
    v_u_51.behaviour_update = function(p127, p128, p129) --[[ Name: behaviour_update ]] --[[ Line: 648 ]]
        --[[ Upvalues: (ref 1): v_u_8, (ref 2): v_u_61, (ref 3): v_u_6, (ref 4): v_u_60, (ref 5): v_u_1, (copy 6): v_u_58, (ref 7): l_Play_0, (ref 8): v_u_62, (ref 9): v_u_32, (ref 10): v_u_63, (ref 11): v_u_33 ]]
        p127:behaviour_update_base(p128, p129)
        if p127._current_mode == v_u_8.MODE_OPEN then
            v_u_61 = math.max(v_u_61 - v_u_6:TimescaleToDeltaTime(p128), 0)
            v_u_60.Text = v_u_1:format_sec_time(v_u_61)
            if v_u_58:contains(l_Play_0) then
                v_u_58:get(l_Play_0):behaviour_update(p128)
            end;
        end;
        if v_u_62 then
            local v130, v131 = v_u_32:has_notification()
            v_u_62:update_state(v130, v131)
        end;
        if v_u_63 then
            local v132, v133 = v_u_33:has_notification()
            v_u_63:update_state(v132, v133)
        end;
    end;
    v_u_51.visual_update = function(p134, p135, p136) --[[ Name: visual_update ]] --[[ Line: 671 ]]
        p134:visual_update_base(p135, p136)
    end;
    v_u_51.on_refocus = function(p137) --[[ Name: on_refocus ]] --[[ Line: 675 ]]
        p137:update_player_info_section()
    end;
    v_u_51.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 679 ]]
        --[[ Upvalues: (copy 1): p_u_48, (ref 2): v_u_64, (ref 3): v_u_52 ]]
        p_u_48._bgm_manager:stop_song_preview(v_u_64)
        v_u_52:Destroy()
    end;
    local v_u_138 = -1
    v_u_51.set_alpha = function(_, p139, p140) --[[ Name: set_alpha ]] --[[ Line: 685 ]]
        --[[ Upvalues: (ref 1): v_u_138, (ref 2): v_u_1, (ref 3): v_u_52 ]]
        if v_u_138 ~= p139 or p140 == true then
            v_u_138 = p139
            v_u_1:r_set_alpha(v_u_52, v_u_138)
        end;
    end;
    v_u_51.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 692 ]]
        --[[ Upvalues: (ref 1): v_u_138 ]]
        return v_u_138;
    end;
    v_u_51.set_scale = function(_, p141) --[[ Name: set_scale ]] --[[ Line: 693 ]]
        --[[ Upvalues: (ref 1): v_u_53 ]]
        v_u_53 = p141
    end;
    v_u_51.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 694 ]]
        --[[ Upvalues: (ref 1): v_u_53 ]]
        return v_u_53;
    end;
    v_u_51.get_native_size = function(p142) --[[ Name: get_native_size ]] --[[ Line: 695 ]]
        return p142._native_size;
    end;
    v_u_51.get_size = function(p143) --[[ Name: get_size ]] --[[ Line: 696 ]]
        return p143._size;
    end;
    v_u_51.set_size = function(p144, p145) --[[ Name: set_size ]] --[[ Line: 697 ]]
        --[[ Upvalues: (ref 1): v_u_52 ]]
        p144._size = p145
        v_u_52.PrimaryPart.Size = Vector3.new(p145.X, p145.Y, 0)
    end;
    v_u_51.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 701 ]]
        --[[ Upvalues: (ref 1): v_u_52 ]]
        return v_u_52.PrimaryPart.Position;
    end;
    v_u_51.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 702 ]]
        --[[ Upvalues: (ref 1): v_u_52 ]]
        return v_u_52.PrimaryPart.SurfaceGui;
    end;
    v_u_51.set_showing = function(_, p146) --[[ Name: set_showing ]] --[[ Line: 703 ]]
        --[[ Upvalues: (ref 1): v_u_52, (ref 2): v_u_12 ]]
        if p146 then
            v_u_52.Parent = v_u_12:get_world_ui_folder()
        else
            v_u_52.Parent = nil
        end;
    end;
    f_cons()
    return v_u_51;
end;
v_u_44.set_notification_display = function(_, p147, p148) --[[ Name: set_notification_display ]] --[[ Line: 715 ]]
    --[[ Upvalues: (ref 1): v_u_45, (ref 2): v_u_46 ]]
    v_u_45 = p147
    v_u_46 = p148
end;
v_u_44.has_notification = function(_) --[[ Name: has_notification ]] --[[ Line: 720 ]]
    --[[ Upvalues: (ref 1): v_u_45, (ref 2): v_u_46 ]]
    return v_u_45, v_u_46;
end;
return v_u_44;
