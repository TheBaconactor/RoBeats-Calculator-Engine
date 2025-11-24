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
require(game.ReplicatedStorage.Menu.SPUIButton)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIDisplay)
require(game.ReplicatedStorage.Menu.MenuSystem)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_7 = require(game.ReplicatedStorage.Local.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_9 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_10 = require(game.ReplicatedStorage.Shared.MissionInfo)
local v_u_11 = require(game.ReplicatedStorage.Shared.MissionTimeframe)
require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_12 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_13 = require(game.ReplicatedStorage.Lobby.UI.ButtonDrawer)
local v_u_14 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_15 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassUtils)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
local v_u_17 = require(game.ReplicatedStorage.PlayerInfo.PremiumRewardsInfo)
local v_u_18 = require(game.ReplicatedStorage.PlayerInfo.GroupRewardsInfo)
local v_u_19 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_20 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_21 = require(game.ReplicatedStorage.Shared.HUDNotification)
local v_u_22 = require(game.ReplicatedStorage.PlayerInfo.LoginRewardUtil)
require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfo)
require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_23 = require(game.ReplicatedStorage.LocalShared.PlayerPolicy)
local v_u_24 = require(game.ReplicatedStorage.PlayerInfo.PlatformPlayerRewardInfo)
local v_u_25 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_26 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_27 = require(game.ReplicatedStorage.PlayerInfo.FeverIconDatabase)
local v_u_28 = require(game.ReplicatedStorage.PlayerInfo.ChallengePassV2.ChallengePassV2Mission)
local v_u_29 = require(game.ReplicatedStorage.Lobby.UI.DanceHUD)
local v_u_30 = require(game.ReplicatedStorage.Lobby.UI.RadioHUD)
local v_u_31 = require(game.ReplicatedStorage.Lobby.Menus.SongShopUI)
local v_u_32 = require(game.ReplicatedStorage.Lobby.Menus.SongInventoryV2UI)
local v_u_33 = require(game.ReplicatedStorage.Lobby.Menus.SongGatchaUI)
local v_u_34 = require(game.ReplicatedStorage.Lobby.Menus.PlayerListUI)
local v_u_35 = require(game.ReplicatedStorage.Lobby.Menus.GearEquipV2UI)
local v_u_36 = require(game.ReplicatedStorage.Lobby.Menus.GearShopUI)
local v_u_37 = require(game.ReplicatedStorage.Lobby.Menus.MissionUI)
local v_u_38 = require(game.ReplicatedStorage.Lobby.Menus.CraftingUI)
local v_u_39 = require(game.ReplicatedStorage.Lobby.Menus.CraftingGatchaUI)
local v_u_40 = require(game.ReplicatedStorage.Lobby.Menus.SettingsUI)
local v_u_41 = require(game.ReplicatedStorage.Lobby.Menus.LeaderboardsUI)
local v_u_42 = require(game.ReplicatedStorage.Lobby.Menus.VIPPurchaseUI)
local v_u_43 = require(game.ReplicatedStorage.Lobby.Menus.MarketplaceUI)
local v_u_44 = require(game.ReplicatedStorage.Lobby.Menus.PlayUI)
local v_u_45 = require(game.ReplicatedStorage.Lobby.Menus.EquipUI)
local v_u_46 = require(game.ReplicatedStorage.Lobby.Menus.ArtistEventUI)
local v47 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_48 = nil
local v_u_49 = nil
local v_u_50 = nil
local v_u_51 = nil
local v_u_52 = nil
local v_u_53 = nil
local v_u_54 = nil
local v_u_55 = nil
v47:require_client(function() --[[ Line: 73 ]]
    --[[ Upvalues: (ref 1): v_u_48, (ref 2): v_u_49, (ref 3): v_u_50, (ref 4): v_u_51, (ref 5): v_u_52, (ref 6): v_u_53, (ref 7): v_u_54, (ref 8): v_u_55 ]]
    v_u_48 = require(game.ReplicatedStorage.Lobby.Menus.LoginRewardUI)
    v_u_49 = require(game.ReplicatedStorage.PlayerInfo.SpecialEventInfoData.GenericArtistP2EventInfo)
    v_u_50 = require(game.ReplicatedStorage.Lobby.Menus.Event.GenericArtistP2EventUI)
    v_u_51 = require(game.ReplicatedStorage.Lobby.Menus.RobuxShopUI)
    v_u_52 = require(game.ReplicatedStorage.Lobby.Menus.Collection.CollectionListViewUI)
    v_u_53 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
    v_u_54 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
    v_u_55 = require(game.ReplicatedStorage.EditorGame.UI.SavedMapInfoListUI)
end)
local v_u_56 = {
    ["Type"] = "LobbyHUDV2UI"
}
local l_Minimized_0 = v_u_13.State.Minimized
local l_Expanded_0 = v_u_13.State.Expanded
v_u_56.new = function(_, p_u_57, p_u_58, p_u_59) --[[ Name: new ]] --[[ Line: 101 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_56, (copy 3): l_Minimized_0, (copy 4): v_u_6, (copy 5): v_u_4, (copy 6): v_u_5, (copy 7): v_u_8, (copy 8): v_u_44, (ref 9): v_u_51, (copy 10): v_u_23, (copy 11): v_u_1, (copy 12): v_u_2, (copy 13): v_u_16, (copy 14): v_u_14, (copy 15): v_u_42, (copy 16): v_u_22, (copy 17): v_u_21, (ref 18): v_u_48, (copy 19): v_u_9, (copy 20): v_u_17, (copy 21): v_u_24, (copy 22): v_u_27, (ref 23): v_u_53, (copy 24): v_u_25, (copy 25): v_u_7, (copy 26): v_u_26, (ref 27): v_u_54, (copy 28): v_u_18, (copy 29): v_u_19, (copy 30): v_u_46, (copy 31): v_u_20, (copy 32): v_u_34, (copy 33): v_u_43, (copy 34): v_u_41, (copy 35): v_u_40, (ref 36): v_u_52, (ref 37): v_u_55, (copy 38): l_Expanded_0, (copy 39): v_u_37, (copy 40): v_u_32, (copy 41): v_u_45, (copy 42): v_u_35, (copy 43): v_u_38, (copy 44): v_u_31, (copy 45): v_u_36, (copy 46): v_u_33, (copy 47): v_u_39, (copy 48): v_u_12, (copy 49): v_u_13, (copy 50): v_u_29, (copy 51): v_u_30, (copy 52): v_u_11, (copy 53): v_u_10, (copy 54): v_u_28, (copy 55): v_u_15 ]]
    local v_u_60 = v_u_3:new(p_u_58, p_u_59)
    v_u_60.Type = v_u_56.Type
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
    local v_u_74 = nil
    local v_u_75 = nil
    local v_u_76 = nil
    local v_u_77 = 1
    local v_u_78 = 1
    v_u_60.swallows_input = function(_) --[[ Name: swallows_input ]] --[[ Line: 129 ]]
        return false;
    end;
    v_u_60.cycle_list_updated = function(_, _) end;
    v_u_60.update_default_input_pad_cycle_element_behaviour = function(_, _, _) end;
    local v_u_79 = nil
    local v_u_80 = nil
    local function f_refresh_buttondrawer() --[[ Name: refresh_buttondrawer ]] --[[ Line: 137 ]]
        --[[ Upvalues: (ref 1): v_u_80, (copy 2): p_u_57, (ref 3): l_Minimized_0 ]]
        v_u_80:refresh_expand_state_buttons()
        if p_u_57:get_control_script() then
            local v81
            if v_u_80:get_expand_state(2) == l_Minimized_0 then
                v81 = v_u_80:get_expand_state(3) == l_Minimized_0
            else
                v81 = false
            end;
            p_u_57:get_control_script():set_touch_jump_enabled(v81)
        end;
    end;
    local function f_init_buttondrawer_down_ui() --[[ Name: init_buttondrawer_down_ui ]] --[[ Line: 146 ]]
        --[[ Upvalues: (ref 1): v_u_62, (ref 2): v_u_65, (ref 3): v_u_6, (copy 4): p_u_58, (ref 5): v_u_66, (ref 6): v_u_4, (ref 7): v_u_5, (copy 8): p_u_57, (ref 9): v_u_8, (copy 10): p_u_59, (ref 11): v_u_44, (ref 12): v_u_51, (ref 13): v_u_23, (copy 14): v_u_60, (ref 15): v_u_1, (ref 16): v_u_2, (ref 17): v_u_16, (ref 18): v_u_14, (ref 19): v_u_69, (ref 20): v_u_42, (ref 21): v_u_22, (ref 22): v_u_21, (ref 23): v_u_48, (ref 24): v_u_9, (ref 25): v_u_17, (ref 26): v_u_24, (ref 27): v_u_27, (ref 28): v_u_53, (ref 29): v_u_25, (ref 30): v_u_7, (ref 31): v_u_26, (ref 32): v_u_54, (ref 33): v_u_18, (ref 34): v_u_19, (ref 35): v_u_72, (ref 36): v_u_71, (ref 37): v_u_46, (ref 38): v_u_20, (ref 39): v_u_70, (ref 40): v_u_80, (ref 41): v_u_34, (ref 42): v_u_43, (ref 43): v_u_41, (ref 44): v_u_40, (ref 45): v_u_52, (ref 46): v_u_55, (ref 47): l_Minimized_0, (copy 48): f_refresh_buttondrawer, (ref 49): l_Expanded_0 ]]
        local l_ButtonDrawerDown_0 = v_u_62.ButtonDrawerDown
        v_u_65 = v_u_6:new(l_ButtonDrawerDown_0, p_u_58, true):set_position_nxy(1, 0):set_anchor_rnxy(1, 0)
        v_u_66 = v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.BackMain)
        local v_u_82 = v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.PlayButton), p_u_58, function() --[[ Line: 159 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): p_u_59, (ref 4): v_u_44, (ref 5): p_u_58 ]]
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN_LONG)
            p_u_59:push_menu(v_u_44:new(p_u_57, p_u_58, p_u_59))
        end):set_auto_zoffset_behaviour(true):set_passive_anim()
        local function _() --[[ Name: show_robux_shop_ui ]] --[[ Line: 167 ]]
            --[[ Upvalues: (ref 1): p_u_59, (ref 2): v_u_51, (ref 3): p_u_57, (ref 4): p_u_58 ]]
            p_u_59:push_menu(v_u_51:new(p_u_57, p_u_58, p_u_59))
        end;
        local v_u_83 = v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.CurrencyDisplay), p_u_58, function() --[[ Line: 174 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): p_u_59, (ref 4): v_u_51, (ref 5): p_u_58 ]]
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            p_u_59:push_menu(v_u_51:new(p_u_57, p_u_58, p_u_59))
        end)
        v_u_83:set_pre_layout_fn(function() --[[ Line: 179 ]]
            --[[ Upvalues: (ref 1): p_u_58, (copy 2): v_u_82, (ref 3): v_u_23, (copy 4): v_u_83 ]]
            local v84 = p_u_58:get_cursor_nxy()
            local v85 = v_u_82:get_nrect(p_u_58)
            if v_u_23:has_any_paid_item_restrictions() then
                v_u_83:set_enabled(false, true)
                return;
            elseif v85:contains_vec2(v84) == true then
                v_u_83:set_enabled(false, true)
            else
                v_u_83:set_enabled(true, true)
            end;
        end)
        v_u_60:add_cycle_element(p_u_57, 1, v_u_83)
        v_u_60:add_cycle_element(p_u_57, 1, v_u_82)
        local l_BuyCurrencyButton_0 = l_ButtonDrawerDown_0.BuyCurrencyButton
        if v_u_23:has_any_paid_item_restrictions() then
            l_BuyCurrencyButton_0.Parent = nil
            v_u_1:if_exists(function() --[[ Line: 198 ]]
                --[[ Upvalues: (copy 1): l_ButtonDrawerDown_0, (copy 2): l_BuyCurrencyButton_0 ]]
                l_ButtonDrawerDown_0.BuyVIPButton.Position = l_BuyCurrencyButton_0.Position
            end)
        else
            v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_BuyCurrencyButton_0), p_u_58, function() --[[ Line: 206 ]]
                --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): p_u_59, (ref 4): v_u_51, (ref 5): p_u_58 ]]
                p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                p_u_59:push_menu(v_u_51:new(p_u_57, p_u_58, p_u_59))
            end):set_auto_zoffset_behaviour(true))
            v_u_1:if_exists(function() --[[ Line: 212 ]]
                --[[ Upvalues: (copy 1): l_BuyCurrencyButton_0, (ref 2): p_u_57, (ref 3): v_u_2, (ref 4): v_u_16 ]]
                l_BuyCurrencyButton_0.SurfaceGui.Frame.SaleOverlay.Visible = p_u_57._player_blob_manager:get_day_event_list():is_any_event_in_list_active(v_u_2:new({
                    v_u_16.EventType.CoinSale,
                    v_u_16.EventType.StarSale,
                    v_u_16.EventType.PackSale,
                    v_u_16.EventType.UpgradeSale,
                    v_u_16.EventType.CraftSale,
                    v_u_16.EventType.MiniSale
                }))
            end)
        end;
        local v86 = p_u_57._player_blob_manager:get_player_blob()
        local l_BuyVIPButton_0 = l_ButtonDrawerDown_0.BuyVIPButton
        if v_u_14:playerblob_has_vip_for_current_day(v86, p_u_57:get_current_dayid()) == true then
            l_BuyVIPButton_0.Parent = nil
        else
            v_u_69 = v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_BuyVIPButton_0), p_u_58, function() --[[ Line: 233 ]]
                --[[ Upvalues: (ref 1): p_u_59, (ref 2): v_u_42, (ref 3): p_u_57, (ref 4): p_u_58, (ref 5): v_u_8 ]]
                p_u_59:push_menu(v_u_42:new(p_u_57, p_u_58, p_u_59))
                p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            end):set_auto_zoffset_behaviour(true))
            v_u_69:set_visible(false)
            l_BuyVIPButton_0.SurfaceGui.Frame.SaleOverlay.Visible = p_u_57._player_blob_manager:get_day_event_list():is_event_type_active(v_u_16.EventType.VIPSale)
        end;
        local v_u_87 = v_u_2:new()
        local v_u_88 = l_ButtonDrawerDown_0.RewardsButtonAnchor1:Clone()
        for _, v89 in v_u_2:new({ l_ButtonDrawerDown_0.RewardsButtonAnchor1, l_ButtonDrawerDown_0.RewardsButtonAnchor2, l_ButtonDrawerDown_0.RewardsButtonAnchor3 }):key_itr() do
            v_u_87:push_back(v89.CFrame)
            v89.Parent = nil
        end;
        local function _() --[[ Name: has_any_anchors_left ]] --[[ Line: 253 ]]
            --[[ Upvalues: (copy 1): v_u_87 ]]
            return v_u_87:count() > 0;
        end;
        local function _(p90, p91) --[[ Name: claim_reward_button_anchor ]] --[[ Line: 254 ]]
            --[[ Upvalues: (copy 1): v_u_87, (copy 2): v_u_88, (copy 3): l_ButtonDrawerDown_0 ]]
            if v_u_87:count() > 0 then
                local v92 = v_u_87:pop_front()
                if p90 == nil then
                    p90 = v_u_88:Clone()
                    p90.Parent = l_ButtonDrawerDown_0
                end;
                p90.CFrame = v92
                p91(p90)
            elseif p90 then
                p90.Parent = nil
            end;
        end;
        if p_u_57._event_integration_manager:is_event_integration_hud_active() then
            local v93 = nil
            local function v95(p94) --[[ Line: 271 ]]
                --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_60, (ref 3): v_u_5, (ref 4): v_u_4, (ref 5): v_u_65, (ref 6): p_u_58, (ref 7): v_u_8 ]]
                p94.SurfaceGui.Frame.Icon.Image = p_u_57._event_integration_manager:get_hud_button_assetid()
                v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), p94), p_u_58, function() --[[ Line: 276 ]]
                    --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8 ]]
                    p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                    p_u_57._event_integration_manager:on_hud_button_pressed()
                end))
            end;
            if v_u_87:count() > 0 then
                local v96 = v_u_87:pop_front()
                if v93 == nil then
                    v93 = v_u_88:Clone()
                    v93.Parent = l_ButtonDrawerDown_0
                end;
                v93.CFrame = v96
                v95(v93)
            elseif v93 then
                v93.Parent = nil
            end;
        end;
        local v_u_97 = false
        if v_u_97 == false and v_u_22:playerblob_can_claim_login_reward_for_dayid_monthid(v86, p_u_57._player_blob_manager:get_dayid(), p_u_57._player_blob_manager:get_monthid()) then
            local l_LoginRewardsButton_0 = l_ButtonDrawerDown_0.LoginRewardsButton
            local function v100() --[[ Line: 336 ]]
                --[[ Upvalues: (ref 1): v_u_97, (ref 2): v_u_21, (copy 3): l_ButtonDrawerDown_0, (ref 4): v_u_22, (ref 5): v_u_60, (ref 6): p_u_57, (ref 7): v_u_5, (ref 8): v_u_4, (ref 9): v_u_65, (ref 10): p_u_58, (ref 11): v_u_8, (ref 12): p_u_59, (ref 13): v_u_48 ]]
                v_u_97 = true
                local v_u_98 = nil
                local v_u_99 = v_u_21:create_display_wrapper(l_ButtonDrawerDown_0.LoginRewardsButton.SurfaceGui.Frame.Notification, l_ButtonDrawerDown_0.LoginRewardsButton.SurfaceGui.Frame.Notification.Display)
                v_u_22:set_notification_state(true)
                v_u_99:update_state(v_u_22:get_notification_state(), 1)
                v_u_98 = v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.LoginRewardsButton), p_u_58, function() --[[ Line: 349 ]]
                    --[[ Upvalues: (ref 1): v_u_22, (copy 2): v_u_99, (ref 3): p_u_57, (ref 4): v_u_8, (ref 5): p_u_59, (ref 6): v_u_48, (ref 7): p_u_58, (ref 8): v_u_98 ]]
                    v_u_22:set_notification_state(false)
                    v_u_99:update_state(v_u_22:get_notification_state(), 0)
                    p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                    p_u_59:push_menu(v_u_48:new(p_u_57, p_u_58, p_u_59, function() --[[ Line: 353 ]]
                        --[[ Upvalues: (ref 1): v_u_98 ]]
                        v_u_98:set_visible(false)
                    end))
                end))
            end;
            if v_u_87:count() > 0 then
                local v101 = v_u_87:pop_front()
                if l_LoginRewardsButton_0 == nil then
                    l_LoginRewardsButton_0 = v_u_88:Clone()
                    l_LoginRewardsButton_0.Parent = l_ButtonDrawerDown_0
                end;
                l_LoginRewardsButton_0.CFrame = v101
                v100(l_LoginRewardsButton_0)
            elseif l_LoginRewardsButton_0 then
                l_LoginRewardsButton_0.Parent = nil
            end;
        else
            l_ButtonDrawerDown_0.LoginRewardsButton.Parent = nil
        end;
        if v_u_97 == false and (v_u_9.PremiumRewardsEnabled == true and (v_u_17:player_is_roblox_premium(game.Players.LocalPlayer) and v_u_17:playerblob_has_claimed_premium_rewards(v86) ~= true)) then
            local l_PremiumRewardsButton_0 = l_ButtonDrawerDown_0.PremiumRewardsButton
            local function v104() --[[ Line: 369 ]]
                --[[ Upvalues: (ref 1): v_u_97, (ref 2): v_u_21, (copy 3): l_ButtonDrawerDown_0, (ref 4): v_u_17, (ref 5): v_u_60, (ref 6): p_u_57, (ref 7): v_u_5, (ref 8): v_u_4, (ref 9): v_u_65, (ref 10): p_u_58, (ref 11): v_u_8 ]]
                v_u_97 = true
                local v_u_102 = nil
                local v_u_103 = v_u_21:create_display_wrapper(l_ButtonDrawerDown_0.PremiumRewardsButton.SurfaceGui.Frame.Notification, l_ButtonDrawerDown_0.PremiumRewardsButton.SurfaceGui.Frame.Notification.Display)
                v_u_103:update_state(v_u_17:get_notification_state(), 1)
                v_u_102 = v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.PremiumRewardsButton), p_u_58, function() --[[ Line: 380 ]]
                    --[[ Upvalues: (ref 1): v_u_17, (copy 2): v_u_103, (ref 3): p_u_57, (ref 4): v_u_8, (ref 5): v_u_102 ]]
                    v_u_17:set_notification_state(false)
                    v_u_103:update_state(v_u_17:get_notification_state(), 0)
                    p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                    v_u_17:claim_premium_rewards_button_pressed(p_u_57, function() --[[ Line: 384 ]]
                        --[[ Upvalues: (ref 1): v_u_102, (ref 2): p_u_57, (ref 3): v_u_8 ]]
                        v_u_102:set_visible(false)
                        p_u_57._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
                    end)
                end))
            end;
            if v_u_87:count() > 0 then
                local v105 = v_u_87:pop_front()
                if l_PremiumRewardsButton_0 == nil then
                    l_PremiumRewardsButton_0 = v_u_88:Clone()
                    l_PremiumRewardsButton_0.Parent = l_ButtonDrawerDown_0
                end;
                l_PremiumRewardsButton_0.CFrame = v105
                v104(l_PremiumRewardsButton_0)
            elseif l_PremiumRewardsButton_0 then
                l_PremiumRewardsButton_0.Parent = nil
            end;
        else
            l_ButtonDrawerDown_0.PremiumRewardsButton.Parent = nil
        end;
        if v_u_97 == false and (v_u_24:playerblob_has_claimed_reward_for_platform(v86, v_u_24:get_platform_local()) == false and v_u_24:did_complete_match_local()) then
            local l_PlatformPlayerRewardButton_0 = l_ButtonDrawerDown_0.PlatformPlayerRewardButton
            local function v111() --[[ Line: 399 ]]
                --[[ Upvalues: (ref 1): v_u_97, (ref 2): v_u_27, (ref 3): v_u_24, (copy 4): l_ButtonDrawerDown_0, (ref 5): v_u_60, (ref 6): p_u_57, (ref 7): v_u_5, (ref 8): v_u_4, (ref 9): v_u_65, (ref 10): p_u_58, (ref 11): v_u_8, (ref 12): v_u_53, (ref 13): p_u_59, (ref 14): v_u_25, (ref 15): v_u_7, (ref 16): v_u_26, (ref 17): v_u_54 ]]
                v_u_97 = true
                local v_u_106 = nil
                pcall(function() --[[ Line: 402 ]]
                    --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_24, (ref 3): l_ButtonDrawerDown_0 ]]
                    l_ButtonDrawerDown_0.PlatformPlayerRewardButton.SurfaceGui.Frame.PlatformIcon.Image = v_u_27:singleton():get_fevericon_for_id(v_u_24:platform_get_fevericon_id(v_u_24:get_platform_local())):get_image()
                end)
                v_u_106 = v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.PlatformPlayerRewardButton), p_u_58, function() --[[ Line: 410 ]]
                    --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): v_u_53, (ref 4): p_u_58, (ref 5): p_u_59, (ref 6): v_u_25, (ref 7): v_u_7, (ref 8): v_u_26, (ref 9): v_u_54, (ref 10): v_u_24, (ref 11): v_u_106 ]]
                    p_u_57._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                    local v_u_107 = p_u_57._menus:push_menu(v_u_53:new(p_u_57, p_u_58, p_u_59)):set_text("Loading...", ""):set_close_button_visible(false)
                    p_u_57._evt:wait_on_event_once(v_u_25.EVT_SpecialEvent_ServerClaimPlatformRewardResponse, function(p108, p109, p_u_110) --[[ Line: 415 ]]
                        --[[ Upvalues: (ref 1): p_u_57, (copy 2): v_u_107, (ref 3): v_u_7, (ref 4): v_u_26, (ref 5): v_u_54 ]]
                        if p108 ~= true then
                            p_u_57._menus:remove_menu(v_u_107)
                            return v_u_7:warnf("Failed to claim platform reward: %s", p109);
                        end;
                        p_u_57._player_blob_manager:do_sync(function() --[[ Line: 420 ]]
                            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_107, (ref 3): v_u_26, (copy 4): p_u_110, (ref 5): v_u_54 ]]
                            p_u_57._menus:remove_menu(v_u_107)
                            p_u_57._menus:push_menu(v_u_54:new(p_u_57, p_u_57._spui, p_u_57._menus, (v_u_26.RewardInfo:table_to_list(p_u_110)))):set_header_text("Rewards Acquired!")
                        end)
                    end)
                    p_u_57._evt:fire_event_to_server(v_u_25.EVT_SpecialEvent_ClientClaimPlatformReward, v_u_24:get_platform_local())
                    v_u_106:set_visible(false)
                    p_u_57._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
                end))
            end;
            if v_u_87:count() > 0 then
                local v112 = v_u_87:pop_front()
                if l_PlatformPlayerRewardButton_0 == nil then
                    l_PlatformPlayerRewardButton_0 = v_u_88:Clone()
                    l_PlatformPlayerRewardButton_0.Parent = l_ButtonDrawerDown_0
                end;
                l_PlatformPlayerRewardButton_0.CFrame = v112
                v111(l_PlatformPlayerRewardButton_0)
            elseif l_PlatformPlayerRewardButton_0 then
                l_PlatformPlayerRewardButton_0.Parent = nil
            end;
        else
            l_ButtonDrawerDown_0.PlatformPlayerRewardButton.Parent = nil
        end;
        if v_u_97 == false and (v_u_9.GroupRewardsEnabled == true and (v_u_18:playerblob_has_claimed_group_rewards(v86) ~= true and v_u_18:get_notification_state() == true)) then
            local l_GroupRewardsButton_0 = l_ButtonDrawerDown_0.GroupRewardsButton
            local function v115() --[[ Line: 444 ]]
                --[[ Upvalues: (ref 1): v_u_97, (ref 2): v_u_21, (copy 3): l_ButtonDrawerDown_0, (ref 4): v_u_18, (ref 5): v_u_60, (ref 6): p_u_57, (ref 7): v_u_5, (ref 8): v_u_4, (ref 9): v_u_65, (ref 10): p_u_58, (ref 11): v_u_8 ]]
                v_u_97 = true
                local v_u_113 = nil
                local v_u_114 = v_u_21:create_display_wrapper(l_ButtonDrawerDown_0.GroupRewardsButton.SurfaceGui.Frame.Notification, l_ButtonDrawerDown_0.GroupRewardsButton.SurfaceGui.Frame.Notification.Display)
                v_u_114:update_state(v_u_18:get_notification_state(), 1)
                v_u_113 = v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.GroupRewardsButton), p_u_58, function() --[[ Line: 455 ]]
                    --[[ Upvalues: (ref 1): v_u_18, (copy 2): v_u_114, (ref 3): p_u_57, (ref 4): v_u_8, (ref 5): v_u_113 ]]
                    v_u_18:set_notification_state(false)
                    v_u_114:update_state(v_u_18:get_notification_state(), 0)
                    p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                    v_u_18:claim_group_rewards_button_pressed(p_u_57, function() --[[ Line: 459 ]]
                        --[[ Upvalues: (ref 1): v_u_113, (ref 2): p_u_57, (ref 3): v_u_8 ]]
                        v_u_113:set_visible(false)
                        p_u_57._sfx_manager:play_sfx(v_u_8.SFX_ACQUIRE)
                    end)
                end))
            end;
            if v_u_87:count() > 0 then
                local v116 = v_u_87:pop_front()
                if l_GroupRewardsButton_0 == nil then
                    l_GroupRewardsButton_0 = v_u_88:Clone()
                    l_GroupRewardsButton_0.Parent = l_ButtonDrawerDown_0
                end;
                l_GroupRewardsButton_0.CFrame = v116
                v115(l_GroupRewardsButton_0)
            elseif l_GroupRewardsButton_0 then
                l_GroupRewardsButton_0.Parent = nil
            end;
        else
            l_ButtonDrawerDown_0.GroupRewardsButton.Parent = nil
        end;
        local v117, v118 = v_u_19:is_event_active(p_u_57._player_blob_manager:get_day_event_list())
        if v117 then
            local v119, v120 = v_u_19:get_event_info(v118):has_hud_icon()
            if v119 then
                local v_u_121 = 0
                local l_Frame_0 = l_ButtonDrawerDown_0.ArtistEventBigButton.SurfaceGui.Frame
                l_Frame_0.Icon.Image = v120
                local l_BackShine_0 = l_Frame_0.BackShine
                v_u_72 = v_u_21:create_display_wrapper(l_ButtonDrawerDown_0.ArtistEventBigButton.SurfaceGui.Frame.Notification, l_ButtonDrawerDown_0.ArtistEventBigButton.SurfaceGui.Frame.Notification.Display)
                v_u_71 = v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.ArtistEventBigButton), p_u_58, function() --[[ Line: 488 ]]
                    --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): p_u_59, (ref 4): v_u_46, (ref 5): p_u_58 ]]
                    p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                    p_u_59:push_menu(v_u_46:new(p_u_57, p_u_58, p_u_59))
                end):set_pre_layout_fn(function(p122) --[[ Line: 492 ]]
                    --[[ Upvalues: (ref 1): v_u_121, (ref 2): v_u_20, (copy 3): l_BackShine_0 ]]
                    v_u_121 = v_u_20:incr_wrap(v_u_121, v_u_20:sec_to_tick(40) * p122, 1)
                    l_BackShine_0.Rotation = v_u_121 * 360
                end))
                l_ButtonDrawerDown_0.NewSongEventButton.Parent = nil
            else
                v_u_70 = v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.NewSongEventButton), p_u_58, function() --[[ Line: 502 ]]
                    --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): p_u_59, (ref 4): v_u_46, (ref 5): p_u_58 ]]
                    p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                    p_u_59:push_menu(v_u_46:new(p_u_57, p_u_58, p_u_59))
                end))
                v_u_70:get_part().SurfaceGui.Frame.Notification.Visible = false
                l_ButtonDrawerDown_0.ArtistEventBigButton.Parent = nil
            end;
        else
            l_ButtonDrawerDown_0.ArtistEventBigButton.Parent = nil
            l_ButtonDrawerDown_0.NewSongEventButton.Parent = nil
        end;
        v_u_80:add_to_expanded_elements(3, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.PlayersButton), p_u_58, function() --[[ Line: 520 ]]
            --[[ Upvalues: (ref 1): p_u_59, (ref 2): v_u_34, (ref 3): p_u_57, (ref 4): p_u_58, (ref 5): v_u_8 ]]
            p_u_59:push_menu(v_u_34:new(p_u_57, p_u_58, p_u_59))
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
        end):set_auto_zoffset_behaviour(true)))
        if v_u_9.TradeEnabled == true then
            v_u_80:add_to_expanded_elements(2, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.MarketplaceButton), p_u_58, function() --[[ Line: 530 ]]
                --[[ Upvalues: (ref 1): v_u_9, (ref 2): p_u_59, (ref 3): v_u_43, (ref 4): p_u_57, (ref 5): p_u_58, (ref 6): v_u_8 ]]
                if v_u_9.TradeEnabled == true then
                    p_u_59:push_menu(v_u_43:new(p_u_57, p_u_58, p_u_59))
                end;
                p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            end):set_auto_zoffset_behaviour(true)))
        else
            l_ButtonDrawerDown_0.MarketplaceButton.Parent = nil
        end;
        v_u_80:add_to_expanded_elements(3, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.LeaderboardsButton), p_u_58, function() --[[ Line: 544 ]]
            --[[ Upvalues: (ref 1): p_u_59, (ref 2): v_u_41, (ref 3): p_u_57, (ref 4): p_u_58, (ref 5): v_u_8 ]]
            p_u_59:push_menu(v_u_41:new(p_u_57, p_u_58, p_u_59))
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
        end):set_auto_zoffset_behaviour(true)))
        v_u_80:add_to_expanded_elements(2, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.SettingsButton), p_u_58, function() --[[ Line: 553 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): p_u_59, (ref 4): v_u_40, (ref 5): p_u_58 ]]
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            p_u_59:push_menu(v_u_40:new(p_u_57, p_u_58, p_u_59))
        end):set_auto_zoffset_behaviour(true)))
        v_u_80:add_to_expanded_elements(2, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.CollectionButton), p_u_58, function() --[[ Line: 562 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): v_u_52, (ref 4): p_u_58, (ref 5): p_u_59 ]]
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            v_u_52:show_collection_ui(p_u_57, p_u_58, p_u_59)
        end):set_auto_zoffset_behaviour(true)))
        v_u_80:add_to_expanded_elements(2, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.EditorButton), p_u_58, function() --[[ Line: 571 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): v_u_55 ]]
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            v_u_55:show_editor_menu(p_u_57)
        end):set_auto_zoffset_behaviour(true)))
        v_u_80:add_to_expanded_elements(3, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.TeamButton), p_u_58, function() --[[ Line: 580 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8 ]]
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            p_u_57._guild_manager:show_guild_info_action(p_u_57)
            p_u_57._guild_manager:move_camera_to_guild_position(p_u_57)
        end):set_auto_zoffset_behaviour(true)))
        v_u_80:add_to_expanded_elements(3, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.MinimizeSocialButton), p_u_58, function() --[[ Line: 590 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): v_u_80, (ref 4): l_Minimized_0, (ref 5): f_refresh_buttondrawer ]]
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_80:set_expand_state(3, l_Minimized_0)
            f_refresh_buttondrawer()
        end):set_auto_zoffset_behaviour(true)))
        v_u_80:add_to_expanded_elements(2, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.MinimizeMiscButton), p_u_58, function() --[[ Line: 600 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): v_u_80, (ref 4): l_Minimized_0, (ref 5): f_refresh_buttondrawer ]]
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_80:set_expand_state(2, l_Minimized_0)
            f_refresh_buttondrawer()
        end):set_auto_zoffset_behaviour(true)))
        v_u_80:add_to_minimized_elements(3, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.MaximizeSocialButton), p_u_58, function() --[[ Line: 612 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): v_u_80, (ref 4): l_Expanded_0, (ref 5): f_refresh_buttondrawer ]]
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_80:set_expand_state(3, l_Expanded_0)
            f_refresh_buttondrawer()
        end):set_auto_zoffset_behaviour(true)))
        v_u_80:add_to_minimized_elements(2, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_65, v_u_65:get_part(), l_ButtonDrawerDown_0.MaximizeMiscButton), p_u_58, function() --[[ Line: 622 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): v_u_80, (ref 4): l_Expanded_0, (ref 5): f_refresh_buttondrawer ]]
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_80:set_expand_state(2, l_Expanded_0)
            f_refresh_buttondrawer()
        end):set_auto_zoffset_behaviour(true)))
        v_u_80:set_expand_state(3, l_Minimized_0)
        v_u_80:set_expand_state(2, l_Minimized_0)
        local l_Frame_1 = l_ButtonDrawerDown_0.BackMain.SurfaceGui.Frame
        v_u_80:add_to_expanded_uielements(3, l_Frame_1.SocialExpanded)
        v_u_80:add_to_minimized_uielements(3, l_Frame_1.SocialMinimized)
        v_u_80:add_to_expanded_uielements(2, l_Frame_1.MiscExpanded)
        v_u_80:add_to_minimized_uielements(2, l_Frame_1.MiscMinimized)
        f_refresh_buttondrawer()
    end;
    local function f_init_buttondrawer_ui() --[[ Name: init_buttondrawer_ui ]] --[[ Line: 641 ]]
        --[[ Upvalues: (ref 1): v_u_62, (ref 2): v_u_64, (ref 3): v_u_6, (copy 4): p_u_58, (copy 5): v_u_60, (copy 6): p_u_57, (ref 7): v_u_5, (ref 8): v_u_4, (copy 9): p_u_59, (ref 10): v_u_37, (ref 11): v_u_8, (ref 12): v_u_73, (ref 13): v_u_74, (ref 14): v_u_80, (ref 15): l_Minimized_0, (copy 16): f_refresh_buttondrawer, (ref 17): v_u_32, (ref 18): v_u_9, (ref 19): v_u_45, (ref 20): v_u_35, (ref 21): v_u_38, (ref 22): v_u_31, (ref 23): v_u_36, (ref 24): v_u_33, (ref 25): v_u_39, (ref 26): l_Expanded_0 ]]
        local l_ButtonDrawer_0 = v_u_62.ButtonDrawer
        v_u_64 = v_u_6:new(l_ButtonDrawer_0, p_u_58, true):set_position_nxy(1, 1):set_anchor_rnxy(1, 1)
        v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_64, v_u_64:get_part(), l_ButtonDrawer_0.MissionButton), p_u_58, function() --[[ Line: 650 ]]
            --[[ Upvalues: (ref 1): p_u_59, (ref 2): v_u_37, (ref 3): p_u_57, (ref 4): p_u_58, (ref 5): v_u_8 ]]
            p_u_59:push_menu(v_u_37:new(p_u_57, p_u_58, p_u_59))
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
        end))
        v_u_73 = l_ButtonDrawer_0.MissionButton.SurfaceGui.Frame.Notification
        v_u_74 = l_ButtonDrawer_0.MissionButton.SurfaceGui.Frame.Notification.Display
        v_u_73.Visible = false
        v_u_80:add_to_expanded_elements(1, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_64, v_u_64:get_part(), l_ButtonDrawer_0.MinimizeInventoryButton), p_u_58, function() --[[ Line: 664 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): v_u_80, (ref 4): l_Minimized_0, (ref 5): f_refresh_buttondrawer ]]
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_80:set_expand_state(1, l_Minimized_0)
            f_refresh_buttondrawer()
        end)))
        v_u_80:add_to_expanded_elements(1, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_64, v_u_64:get_part(), l_ButtonDrawer_0.SongsButton), p_u_58, function() --[[ Line: 674 ]]
            --[[ Upvalues: (ref 1): p_u_59, (ref 2): v_u_32, (ref 3): p_u_57, (ref 4): p_u_58, (ref 5): v_u_8 ]]
            p_u_59:push_menu(v_u_32:new(p_u_57, p_u_58, p_u_59))
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
        end)))
        v_u_80:add_to_expanded_elements(1, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_64, v_u_64:get_part(), l_ButtonDrawer_0.GearButton), p_u_58, function() --[[ Line: 683 ]]
            --[[ Upvalues: (ref 1): v_u_9, (ref 2): p_u_59, (ref 3): v_u_45, (ref 4): p_u_57, (ref 5): p_u_58, (ref 6): v_u_35, (ref 7): v_u_8 ]]
            if v_u_9.UseNewGearEquipUI == true then
                p_u_59:push_menu(v_u_45:new(p_u_57, p_u_58, p_u_59))
            else
                p_u_59:push_menu(v_u_35:new(p_u_57, p_u_58, p_u_59))
            end;
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
        end)))
        v_u_80:add_to_expanded_elements(1, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_64, v_u_64:get_part(), l_ButtonDrawer_0.CraftButton), p_u_58, function() --[[ Line: 696 ]]
            --[[ Upvalues: (ref 1): p_u_59, (ref 2): v_u_38, (ref 3): p_u_57, (ref 4): p_u_58, (ref 5): v_u_8 ]]
            p_u_59:push_menu(v_u_38:new(p_u_57, p_u_58, p_u_59))
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
        end)))
        v_u_80:add_to_expanded_elements(0, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_64, v_u_64:get_part(), l_ButtonDrawer_0.MinimizeShopButton), p_u_58, function() --[[ Line: 705 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): v_u_80, (ref 4): l_Minimized_0, (ref 5): f_refresh_buttondrawer ]]
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_80:set_expand_state(0, l_Minimized_0)
            f_refresh_buttondrawer()
        end)))
        v_u_80:add_to_expanded_elements(0, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_64, v_u_64:get_part(), l_ButtonDrawer_0.SongShopButton), p_u_58, function() --[[ Line: 715 ]]
            --[[ Upvalues: (ref 1): p_u_59, (ref 2): v_u_31, (ref 3): p_u_57, (ref 4): p_u_58, (ref 5): v_u_8 ]]
            p_u_59:push_menu(v_u_31:new(p_u_57, p_u_58, p_u_59))
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
        end)))
        v_u_80:add_to_expanded_elements(0, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_64, v_u_64:get_part(), l_ButtonDrawer_0.GearShopButton), p_u_58, function() --[[ Line: 724 ]]
            --[[ Upvalues: (ref 1): p_u_59, (ref 2): v_u_36, (ref 3): p_u_57, (ref 4): p_u_58, (ref 5): v_u_8 ]]
            p_u_59:push_menu(v_u_36:new(p_u_57, p_u_58, p_u_59))
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
        end)))
        v_u_80:add_to_expanded_elements(0, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_64, v_u_64:get_part(), l_ButtonDrawer_0.StarMachineButton), p_u_58, function() --[[ Line: 733 ]]
            --[[ Upvalues: (ref 1): p_u_59, (ref 2): v_u_33, (ref 3): p_u_57, (ref 4): p_u_58, (ref 5): v_u_8 ]]
            p_u_59:push_menu(v_u_33:new(p_u_57, p_u_58, p_u_59))
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
        end)))
        v_u_80:add_to_expanded_elements(0, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_64, v_u_64:get_part(), l_ButtonDrawer_0.NoteMachineButton), p_u_58, function() --[[ Line: 742 ]]
            --[[ Upvalues: (ref 1): p_u_59, (ref 2): v_u_39, (ref 3): p_u_57, (ref 4): p_u_58, (ref 5): v_u_8 ]]
            p_u_59:push_menu(v_u_39:new(p_u_57, p_u_58, p_u_59))
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
        end)))
        v_u_80:add_to_minimized_elements(1, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_64, v_u_64:get_part(), l_ButtonDrawer_0.ExpandInventoryButton), p_u_58, function() --[[ Line: 752 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): v_u_80, (ref 4): l_Expanded_0, (ref 5): f_refresh_buttondrawer ]]
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_80:set_expand_state(1, l_Expanded_0)
            f_refresh_buttondrawer()
        end)))
        v_u_80:add_to_minimized_elements(0, v_u_60:add_cycle_element(p_u_57, 1, v_u_5:new(v_u_4:new(v_u_64, v_u_64:get_part(), l_ButtonDrawer_0.ExpandShopButton), p_u_58, function() --[[ Line: 762 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_8, (ref 3): v_u_80, (ref 4): l_Expanded_0, (ref 5): f_refresh_buttondrawer ]]
            p_u_57._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_80:set_expand_state(0, l_Expanded_0)
            f_refresh_buttondrawer()
        end)))
        v_u_80:set_expand_state(1, l_Minimized_0)
        v_u_80:set_expand_state(0, l_Minimized_0)
        local l_Frame_2 = l_ButtonDrawer_0.BackMain.SurfaceGui.Frame
        v_u_80:add_to_expanded_uielements(0, l_Frame_2.ShopExpanded)
        v_u_80:add_to_minimized_uielements(0, l_Frame_2.ShopMinimized)
        v_u_80:add_to_expanded_uielements(1, l_Frame_2.InventoryExpanded)
        v_u_80:add_to_minimized_uielements(1, l_Frame_2.InventoryMinimized)
        f_refresh_buttondrawer()
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 781 ]]
        --[[ Upvalues: (ref 1): v_u_61, (ref 2): v_u_12, (ref 3): v_u_1, (copy 4): v_u_60, (copy 5): p_u_58, (ref 6): v_u_62, (ref 7): v_u_63, (ref 8): v_u_79, (ref 9): v_u_9, (ref 10): v_u_68, (ref 11): v_u_67, (ref 12): v_u_80, (ref 13): v_u_13, (copy 14): f_init_buttondrawer_ui, (copy 15): f_init_buttondrawer_down_ui, (ref 16): v_u_75, (ref 17): v_u_29, (copy 18): p_u_57, (copy 19): p_u_59, (ref 20): v_u_76, (ref 21): v_u_30, (ref 22): v_u_77 ]]
        v_u_61 = Instance.new("Folder", v_u_12:get_world_ui_folder())
        v_u_61.Name = v_u_1:gen_name("LobbyHUDUI")
        v_u_60._native_size = p_u_58:get_size_from_nxy(1, 1)
        v_u_60._size = v_u_60._native_size
        v_u_62 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.LobbyHUDV2:Clone()
        v_u_62.Name = v_u_1:gen_name(v_u_62.Name)
        v_u_60:set_showing(true)
        v_u_63 = game.ReplicatedStorage.WorldUIProto.WorldUINormalPlane:Clone()
        v_u_63.Name = v_u_1:gen_name(v_u_63.Name)
        v_u_63.PrimaryPart.CFrame = p_u_58:get_cframe()
        v_u_63.PrimaryPart.Size = Vector3.new(v_u_60._size.X, v_u_60._size.Y, 0)
        v_u_79 = v_u_62.UICenteringButton
        if v_u_9.HUDShowCenteringCursor ~= true then
            v_u_79.PrimaryPart.SurfaceGui.Enabled = false
        end;
        v_u_68 = v_u_62.ButtonDrawerDown.CurrencyDisplay.SurfaceGui.Frame.CoinSection.Display
        v_u_67 = v_u_62.ButtonDrawerDown.CurrencyDisplay.SurfaceGui.Frame.StarSection.Display
        v_u_80 = v_u_13:new()
        f_init_buttondrawer_ui()
        f_init_buttondrawer_down_ui()
        v_u_75 = v_u_29:new(p_u_57, p_u_58, p_u_59, v_u_60, v_u_62)
        v_u_76 = v_u_30:new(p_u_57, p_u_58, p_u_59, v_u_60, v_u_62)
        v_u_1:ptry(function() --[[ Line: 814 ]]
            --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_77, (ref 3): v_u_62 ]]
            local function _(p123, p124) --[[ Name: apply_image_alpha ]] --[[ Line: 815 ]]
                --[[ Upvalues: (ref 1): v_u_1, (ref 2): v_u_77 ]]
                p123.Name = v_u_1:r_set_alpha_generate_name({
                    ["ImageAlpha"] = p124
                }, "ImageLabel")
                v_u_1:r_set_alpha(p123, v_u_77)
            end;
            local l_Frame_3 = v_u_62.ButtonDrawerDown.BackMain.SurfaceGui.Frame
            local l_Back_0 = v_u_62.ButtonDrawerDown.CurrencyDisplay.SurfaceGui.Frame.Back
            l_Back_0.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_Back_0, v_u_77)
            local l_Bar_0 = l_Frame_3.MiscExpanded.Bar
            l_Bar_0.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_Bar_0, v_u_77)
            local l_ButtonBack_0 = l_Frame_3.MiscExpanded.ButtonBack
            l_ButtonBack_0.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_ButtonBack_0, v_u_77)
            local l_Bar_1 = l_Frame_3.MiscMinimized.Bar
            l_Bar_1.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_Bar_1, v_u_77)
            local l_ButtonBack_1 = l_Frame_3.MiscMinimized.ButtonBack
            l_ButtonBack_1.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_ButtonBack_1, v_u_77)
            local l_Bar_2 = l_Frame_3.SocialExpanded.Bar
            l_Bar_2.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_Bar_2, v_u_77)
            local l_ButtonBack_2 = l_Frame_3.SocialExpanded.ButtonBack
            l_ButtonBack_2.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_ButtonBack_2, v_u_77)
            local l_Bar_3 = l_Frame_3.SocialMinimized.Bar
            l_Bar_3.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_Bar_3, v_u_77)
            local l_ButtonBack_3 = l_Frame_3.SocialMinimized.ButtonBack
            l_ButtonBack_3.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_ButtonBack_3, v_u_77)
            local l_Frame_4 = v_u_62.ButtonDrawer.BackMain.SurfaceGui.Frame
            local l_Bar_4 = l_Frame_4.InventoryExpanded.Bar
            l_Bar_4.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_Bar_4, v_u_77)
            local l_ButtonBack_4 = l_Frame_4.InventoryExpanded.ButtonBack
            l_ButtonBack_4.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_ButtonBack_4, v_u_77)
            local l_Bar_5 = l_Frame_4.InventoryMinimized.Bar
            l_Bar_5.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_Bar_5, v_u_77)
            local l_ButtonBack_5 = l_Frame_4.InventoryMinimized.ButtonBack
            l_ButtonBack_5.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_ButtonBack_5, v_u_77)
            local l_Bar_6 = l_Frame_4.ShopExpanded.Bar
            l_Bar_6.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_Bar_6, v_u_77)
            local l_ButtonBack_6 = l_Frame_4.ShopExpanded.ButtonBack
            l_ButtonBack_6.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_ButtonBack_6, v_u_77)
            local l_Bar_7 = l_Frame_4.ShopMinimized.Bar
            l_Bar_7.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_Bar_7, v_u_77)
            local l_ButtonBack_7 = l_Frame_4.ShopMinimized.ButtonBack
            l_ButtonBack_7.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_ButtonBack_7, v_u_77)
            local l_BackCentral_0 = l_Frame_4.BackCentral
            l_BackCentral_0.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.5
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_BackCentral_0, v_u_77)
            local l_Back_1 = v_u_62.DanceButtonDrawer.MenuButton.SurfaceGui.Frame.Back
            l_Back_1.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.75
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_Back_1, v_u_77)
            local l_Back_2 = v_u_62.DanceButtonDrawer.OpenSurface.SurfaceGui.Frame.Back
            l_Back_2.Name = v_u_1:r_set_alpha_generate_name({
                ["ImageAlpha"] = 0.75
            }, "ImageLabel")
            v_u_1:r_set_alpha(l_Back_2, v_u_77)
        end)
        v_u_60:update_blob_sync()
        v_u_60:reset_selected_item()
        v_u_60:transition_update_visual(0)
        v_u_60:layout()
    end;
    v_u_60.layout = function(p125) --[[ Name: layout ]] --[[ Line: 853 ]]
        --[[ Upvalues: (ref 1): v_u_76, (copy 2): p_u_58, (ref 3): v_u_64, (ref 4): v_u_65, (ref 5): v_u_66, (ref 6): v_u_75, (ref 7): v_u_9, (ref 8): v_u_79, (ref 9): v_u_63 ]]
        v_u_76:layout()
        p_u_58:uiobj_rescale_to_max_nxy(v_u_64, 0.5, 0.45, 1)
        v_u_64:set_position_nxy(1, 1)
        v_u_64:set_position_offset_xy(0, v_u_76:get_uichild():get_size().Y)
        v_u_64:layout()
        p_u_58:uiobj_rescale_to_max_nxy(v_u_65, 0.5, 0.65, 1)
        v_u_65:layout()
        v_u_66:layout()
        v_u_75:layout()
        if v_u_9.HUDShowCenteringCursor then
            local v126 = p_u_58:get_cursor_nxy()
            v_u_79.PrimaryPart.CFrame = p_u_58:get_cframe({
                ["PositionNXY"] = v126
            })
        end;
        if v_u_63.PrimaryPart ~= nil then
            v_u_63.PrimaryPart.Size = Vector3.new(p_u_58:get_size_from_nxy(1, 1).X, p_u_58:get_size_from_nxy(1, 1).Y, 0)
            p125._size = v_u_63.PrimaryPart.Size
            v_u_63.PrimaryPart.CFrame = p_u_58:get_cframe()
        end;
    end;
    v_u_60.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 886 ]]
        --[[ Upvalues: (ref 1): v_u_61, (ref 2): v_u_63, (ref 3): v_u_62 ]]
        v_u_61:Destroy()
        v_u_63:Destroy()
        v_u_62:Destroy()
    end;
    local v_u_127 = -1
    v_u_60.update_blob_sync = function(_) --[[ Name: update_blob_sync ]] --[[ Line: 893 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): p_u_57, (ref 3): v_u_127, (ref 4): v_u_68, (ref 5): v_u_67, (ref 6): v_u_69, (ref 7): v_u_14, (ref 8): v_u_70, (ref 9): v_u_19, (ref 10): v_u_75, (ref 11): v_u_76, (ref 12): v_u_9, (ref 13): v_u_11, (ref 14): v_u_10, (ref 15): v_u_28, (ref 16): v_u_73, (ref 17): v_u_74, (ref 18): v_u_15, (ref 19): v_u_7 ]]
        local v145, v146 = v_u_1:try(function() --[[ Line: 894 ]]
            --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_127, (ref 3): v_u_68, (ref 4): v_u_1, (ref 5): v_u_67, (ref 6): v_u_69, (ref 7): v_u_14, (ref 8): v_u_70, (ref 9): v_u_19, (ref 10): v_u_75, (ref 11): v_u_76, (ref 12): v_u_9, (ref 13): v_u_11, (ref 14): v_u_10, (ref 15): v_u_28, (ref 16): v_u_73, (ref 17): v_u_74, (ref 18): v_u_15 ]]
            if p_u_57._player_blob_manager:is_synced() and p_u_57._player_blob_manager:get_synced_time() ~= v_u_127 then
                v_u_127 = p_u_57._player_blob_manager:get_synced_time()
                local v_u_128 = p_u_57._player_blob_manager:get_player_blob()
                v_u_68.Text = v_u_1:comma_value(v_u_128.CoinCurrency)
                v_u_67.Text = v_u_1:comma_value(v_u_128.StarCurrency)
                if v_u_69 then
                    v_u_69:set_visible(v_u_14:playerblob_has_vip_for_current_day(v_u_128, p_u_57:get_current_dayid()) ~= true)
                end;
                if v_u_70 then
                    local _, v129 = v_u_19:is_event_active(p_u_57._player_blob_manager:get_day_event_list())
                    if v_u_19:playerblob_needs_event_info_validate(v_u_128, v129) then
                        v_u_70:get_part().SurfaceGui.Frame.Notification.Visible = true
                        v_u_70:get_part().SurfaceGui.Frame.Notification.Display.Text = string.format("%d", 1)
                    else
                        v_u_70:get_part().SurfaceGui.Frame.Notification.Visible = false
                    end;
                end;
                v_u_75:playerblob_updated()
                v_u_76:playerblob_updated()
                if v_u_9.UseChallengePassV2 == true then
                    p_u_57._shop_local_protocol:request_challengepassv2_entry_list(function(p130) --[[ Line: 921 ]]
                        --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_11, (ref 3): v_u_10, (copy 4): v_u_128, (ref 5): v_u_28, (ref 6): v_u_73, (ref 7): v_u_74 ]]
                        local v_u_131 = p_u_57._player_blob_manager:get_server_mission_data()
                        local v132 = v_u_11:get_all()
                        local v_u_133 = 0
                        for v134 = 1, v132:count() do
                            local v_u_135 = v132:get(v134)
                            v_u_10:playerblob_missiondata_available_foreach(v_u_128, v_u_131, v_u_135, function(p136) --[[ Line: 927 ]]
                                --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_128, (copy 3): v_u_131, (copy 4): v_u_135, (ref 5): v_u_133 ]]
                                if v_u_10:playerblob_missiondata_missionid_is_completeable(v_u_128, v_u_131, v_u_135, v_u_10:mission_get_id(p136)) then
                                    v_u_133 = v_u_133 + 1
                                end;
                            end)
                        end;
                        if v_u_28:playerblob_has_any_claimable_rewards_for_day_month(v_u_128, p130, p_u_57._player_blob_manager:get_day_id(), p_u_57._player_blob_manager:get_month_id()) then
                            v_u_133 = v_u_133 + 1
                        end;
                        if v_u_133 > 0 then
                            v_u_73.Visible = true
                            v_u_74.Text = string.format("%d", v_u_133)
                        else
                            v_u_73.Visible = false
                        end;
                    end)
                    return;
                end;
                p_u_57._shop_local_protocol:request_challengepass_info_cached(function(p137) --[[ Line: 946 ]]
                    --[[ Upvalues: (ref 1): p_u_57, (ref 2): v_u_11, (ref 3): v_u_10, (copy 4): v_u_128, (ref 5): v_u_15, (ref 6): v_u_73, (ref 7): v_u_74 ]]
                    local v_u_138 = p_u_57._player_blob_manager:get_server_mission_data()
                    local v139 = v_u_11:get_all()
                    local v_u_140 = 0
                    for v141 = 1, v139:count() do
                        local v_u_142 = v139:get(v141)
                        v_u_10:playerblob_missiondata_available_foreach(v_u_128, v_u_138, v_u_142, function(p143) --[[ Line: 952 ]]
                            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_128, (copy 3): v_u_138, (copy 4): v_u_142, (ref 5): v_u_140 ]]
                            if v_u_10:playerblob_missiondata_missionid_is_completeable(v_u_128, v_u_138, v_u_142, v_u_10:mission_get_id(p143)) then
                                v_u_140 = v_u_140 + 1
                            end;
                        end)
                    end;
                    local v144 = v_u_15:playerblob_get_challengepass_active_mission(v_u_128, p137)
                    if v144 ~= nil and v_u_15:playerblob_get_challengepass_mission_state(v_u_128, v144, p_u_57:get_current_dayid()) == v_u_15.ChallengePassMissionState.CurrentClaimable then
                        v_u_140 = v_u_140 + 1
                    end;
                    if v_u_140 > 0 then
                        v_u_73.Visible = true
                        v_u_74.Text = string.format("%d", v_u_140)
                    else
                        v_u_73.Visible = false
                    end;
                end)
            end;
        end)
        if v145 ~= true then
            v_u_7:warnf("LobbyHUDV2UI:update_blob_sync error(%s)", v_u_1:table_to_string(v146))
            p_u_57._error_report:report_client_error(v146)
        end;
    end;
    v_u_60.behaviour_update = function(p147, p148, p149) --[[ Name: behaviour_update ]] --[[ Line: 980 ]]
        --[[ Upvalues: (ref 1): v_u_76, (ref 2): v_u_72, (ref 3): v_u_46 ]]
        p147:update_blob_sync()
        p147:behaviour_update_base(p148, p149)
        v_u_76:update(p148)
        if v_u_72 then
            local v150, v151 = v_u_46:has_notification()
            v_u_72:update_state(v150, v151)
        end;
    end;
    v_u_60.on_refocus = function(_) --[[ Name: on_refocus ]] --[[ Line: 991 ]]
        --[[ Upvalues: (copy 1): p_u_57, (ref 2): v_u_7 ]]
        local v152 = false
        for _, v153 in p_u_57._bgm_manager:get_preview_songkey_stack():key_itr() do
            if v153:end_on_finish() ~= true then
                v152 = true
            end;
        end;
        if v152 then
            v_u_7:warnf("LobbyHUDV2UI has preview song on refocus, stopping all song preview")
            p_u_57._bgm_manager:stop_all_song_preview()
        end;
    end;
    v_u_60.set_alpha = function(_, p154) --[[ Name: set_alpha ]] --[[ Line: 1005 ]]
        --[[ Upvalues: (ref 1): v_u_77, (ref 2): v_u_1, (ref 3): v_u_62 ]]
        if v_u_77 ~= p154 then
            v_u_77 = p154
            v_u_1:r_set_alpha(v_u_62, v_u_77)
        end;
    end;
    v_u_60.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 1011 ]]
        --[[ Upvalues: (ref 1): v_u_77 ]]
        return v_u_77;
    end;
    v_u_60.set_scale = function(_, p155) --[[ Name: set_scale ]] --[[ Line: 1012 ]]
        --[[ Upvalues: (ref 1): v_u_78 ]]
        v_u_78 = p155
    end;
    v_u_60.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 1013 ]]
        --[[ Upvalues: (ref 1): v_u_78 ]]
        return v_u_78;
    end;
    v_u_60.get_native_size = function(p156) --[[ Name: get_native_size ]] --[[ Line: 1015 ]]
        return p156._native_size;
    end;
    v_u_60.get_size = function(p157) --[[ Name: get_size ]] --[[ Line: 1018 ]]
        return p157._size;
    end;
    v_u_60.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 1021 ]]
        --[[ Upvalues: (ref 1): v_u_63 ]]
        return v_u_63.PrimaryPart.Position;
    end;
    v_u_60.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 1024 ]]
        --[[ Upvalues: (ref 1): v_u_7 ]]
        v_u_7:errf("LobbyHUDV2UI get_sgui")
        return nil;
    end;
    v_u_60.set_showing = function(_, p158) --[[ Name: set_showing ]] --[[ Line: 1028 ]]
        --[[ Upvalues: (ref 1): v_u_62, (ref 2): v_u_61 ]]
        if p158 then
            v_u_62.Parent = v_u_61
        else
            v_u_62.Parent = nil
        end;
    end;
    f_cons()
    return v_u_60;
end;
return v_u_56;
