-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:47 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_3 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_4 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_5 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_6 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
require(game.ReplicatedStorage.Shared.SPVector)
local v_u_7 = require(game.ReplicatedStorage.Local.DebugOut)
require(game.ReplicatedStorage.Shared.InputUtil)
local v_u_8 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_10 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_11 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_12 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_13 = require(game.ReplicatedStorage.Lobby.NPC.NPCBase)
local v_u_14 = require(game.ReplicatedStorage.Lobby.Dialogue.BuyCurrencyShopDialogue)
local v_u_15 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_16 = require(game.ReplicatedStorage.Shared.SPMultiDict)
local v_u_17 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_18 = require(game.ReplicatedStorage.Lobby.Menus.VIPPurchaseUI)
local v_u_19 = require(game.ReplicatedStorage.PlayerInfo.DayEventInfo)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_20 = {
    ["Mode"] = {
        ["Closed"] = 1,
        ["InfoRequest"] = 2,
        ["Ready"] = 3,
        ["Purchasing"] = 4
    },
    ["Tab"] = {
        ["Currency"] = 1,
        ["Packs"] = 2
    }
}
local l_Currency_0 = v_u_20.Tab.Currency
local v_u_21 = false
v_u_20.new = function(_, p_u_22, p_u_23, p_u_24, _) --[[ Name: new ]] --[[ Line: 44 ]]
    --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_20, (copy 3): v_u_16, (copy 4): v_u_2, (copy 5): v_u_1, (copy 6): v_u_11, (copy 7): v_u_14, (copy 8): v_u_5, (copy 9): v_u_4, (copy 10): v_u_19, (copy 11): v_u_10, (ref 12): l_Currency_0, (copy 13): v_u_12, (copy 14): v_u_18, (ref 15): v_u_21, (copy 16): v_u_13, (copy 17): v_u_17, (copy 18): v_u_7, (copy 19): v_u_9, (copy 20): v_u_6, (copy 21): v_u_8, (copy 22): v_u_15 ]]
    local v25 = v_u_3:new(p_u_23, p_u_24)
    local l__shop_local_protocol_0 = p_u_22._shop_local_protocol
    local l_InfoRequest_0 = v_u_20.Mode.InfoRequest
    local function _() --[[ Name: request_response_kill ]] --[[ Line: 50 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_20 ]]
        return l_InfoRequest_0 == v_u_20.Mode.Closed;
    end;
    local v_u_26 = nil
    local v_u_27 = 1
    local v_u_28 = 1
    local v_u_29 = nil
    local v_u_30 = nil
    local v_u_31 = v_u_16:new()
    local v_u_32 = v_u_2:new()
    local v_u_33 = v_u_16:new()
    local v_u_34 = nil
    local v_u_35 = nil
    local v_u_36 = nil
    local v_u_37 = nil
    v25.cons = function(p_u_38) --[[ Name: cons ]] --[[ Line: 68 ]]
        --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_1, (ref 3): v_u_11, (ref 4): v_u_36, (ref 5): v_u_14, (copy 6): p_u_22, (ref 7): v_u_37, (ref 8): v_u_5, (ref 9): v_u_4, (copy 10): p_u_23, (copy 11): v_u_31, (ref 12): v_u_20, (ref 13): v_u_19, (ref 14): v_u_10, (copy 15): v_u_33, (ref 16): l_Currency_0, (ref 17): v_u_12, (copy 18): v_u_32, (copy 19): p_u_24, (ref 20): v_u_18, (ref 21): v_u_30, (ref 22): v_u_29, (ref 23): v_u_34, (ref 24): v_u_35, (ref 25): l_InfoRequest_0, (ref 26): v_u_21, (copy 27): l__shop_local_protocol_0, (ref 28): v_u_13 ]]
        v_u_26 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.BuyCurrencyV3UI:Clone()
        v_u_26.Name = v_u_1:gen_name(v_u_26.Name)
        v_u_26.Parent = v_u_11:get_world_ui_folder()
        p_u_38._native_size = v_u_26.PrimaryPart.Size
        p_u_38._size = p_u_38._native_size
        v_u_36 = v_u_14:new(p_u_22, p_u_38, p_u_38, v_u_26)
        v_u_37 = p_u_38:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(p_u_38, v_u_26.PrimaryPart, v_u_26.BackButtonSurface), p_u_23, function() --[[ Line: 80 ]]
            --[[ Upvalues: (copy 1): p_u_38 ]]
            p_u_38:close_menu()
        end))
        local function f_add_currency_button(p39, p40, p41) --[[ Name: add_currency_button ]] --[[ Line: 86 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_38, (ref 3): v_u_26, (ref 4): p_u_22, (ref 5): v_u_5, (ref 6): p_u_23, (ref 7): v_u_31, (ref 8): v_u_20 ]]
            local v_u_42 = nil
            local v43 = v_u_4:new(p_u_38, v_u_26.PrimaryPart, p39)
            if p41 then
                p41(v43)
            end;
            local v44 = p_u_38:add_cycle_element(p_u_22, 1, v_u_5:new(v43, p_u_23, function() --[[ Line: 95 ]]
                --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_42 ]]
                p_u_38:prompt_purchase(v_u_42:get_bound_data())
            end):bind_data(p40):set_selected_rotation_amplitude(0):set_auto_zoffset_behaviour(true))
            v_u_31:push_back_to(v_u_20.Tab.Currency, v44)
            p39.SurfaceGui.Enabled = true
            p39.SurfaceGui.Frame.SaleOverlay.Visible = false
            return v44;
        end;
        if p_u_22._player_blob_manager:get_day_event_list():is_event_type_active(v_u_19.EventType.StarSale) then
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.StarButton1, v_u_10.ProductID_Star1_V3_Sale50):get_part().SurfaceGui.Frame.SaleOverlay.Visible = true
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.StarButton2, v_u_10.ProductID_Star2_V3_Sale50):get_part().SurfaceGui.Frame.SaleOverlay.Visible = true
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.StarButton3, v_u_10.ProductID_Star3_V3_Sale50):get_part().SurfaceGui.Frame.SaleOverlay.Visible = true
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.StarButton4, v_u_10.ProductID_Star4_V3_Sale50, function(_) --[[ Line: 107 ]]
                --[[ Upvalues: (ref 1): v_u_26 ]]
                v_u_26.CurrencyPurchaseButtons.BestDealStarPopup.Parent = nil
            end):get_part().SurfaceGui.Frame.SaleOverlay.Visible = true
        else
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.StarButton1, v_u_10.ProductID_Star1_V3)
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.StarButton2, v_u_10.ProductID_Star2_V3)
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.StarButton3, v_u_10.ProductID_Star3_V3)
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.StarButton4, v_u_10.ProductID_Star4_V3, function(p45) --[[ Line: 114 ]]
                --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_33, (ref 3): v_u_20, (ref 4): v_u_4 ]]
                v_u_26.CurrencyPurchaseButtons.BestDealStarPopup.SurfaceGui.Enabled = true
                v_u_33:push_back_to(v_u_20.Tab.Currency, v_u_4:new(p45, p45:get_child_part(), v_u_26.CurrencyPurchaseButtons.BestDealStarPopup):set_default_sgui())
            end)
        end;
        if p_u_22._player_blob_manager:get_day_event_list():is_event_type_active(v_u_19.EventType.CoinSale) then
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.CoinButton1, v_u_10.ProductID_Coin1_V3_Sale50):get_part().SurfaceGui.Frame.SaleOverlay.Visible = true
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.CoinButton2, v_u_10.ProductID_Coin2_V3_Sale50):get_part().SurfaceGui.Frame.SaleOverlay.Visible = true
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.CoinButton3, v_u_10.ProductID_Coin3_V3_Sale50):get_part().SurfaceGui.Frame.SaleOverlay.Visible = true
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.CoinButton4, v_u_10.ProductID_Coin4_V3_Sale50, function(_) --[[ Line: 128 ]]
                --[[ Upvalues: (ref 1): v_u_26 ]]
                v_u_26.CurrencyPurchaseButtons.BestDealCoinPopup.Parent = nil
            end):get_part().SurfaceGui.Frame.SaleOverlay.Visible = true
        else
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.CoinButton1, v_u_10.ProductID_Coin1_V3)
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.CoinButton2, v_u_10.ProductID_Coin2_V3)
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.CoinButton3, v_u_10.ProductID_Coin3_V3)
            f_add_currency_button(v_u_26.CurrencyPurchaseButtons.CoinButton4, v_u_10.ProductID_Coin4_V3, function(p46) --[[ Line: 135 ]]
                --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_33, (ref 3): v_u_20, (ref 4): v_u_4 ]]
                v_u_26.CurrencyPurchaseButtons.BestDealCoinPopup.SurfaceGui.Enabled = true
                v_u_33:push_back_to(v_u_20.Tab.Currency, v_u_4:new(p46, p46:get_child_part(), v_u_26.CurrencyPurchaseButtons.BestDealCoinPopup):set_default_sgui())
            end)
        end;
        local function f_add_pack_button(p47, p48, p49) --[[ Name: add_pack_button ]] --[[ Line: 147 ]]
            --[[ Upvalues: (ref 1): v_u_4, (copy 2): p_u_38, (ref 3): v_u_26, (ref 4): p_u_22, (ref 5): v_u_5, (ref 6): p_u_23, (ref 7): v_u_31, (ref 8): v_u_20 ]]
            local v_u_50 = nil
            local v51 = v_u_4:new(p_u_38, v_u_26.PrimaryPart, p47)
            if p49 then
                p49(v51)
            end;
            local v52 = p_u_38:add_cycle_element(p_u_22, 1, v_u_5:new(v51, p_u_23, function() --[[ Line: 156 ]]
                --[[ Upvalues: (ref 1): p_u_38, (ref 2): v_u_50 ]]
                p_u_38:prompt_purchase(v_u_50:get_bound_data())
            end):bind_data(p48):set_selected_rotation_amplitude(0):set_auto_zoffset_behaviour(true))
            v_u_31:push_back_to(v_u_20.Tab.Packs, v52)
            return v52;
        end;
        if p_u_22._player_blob_manager:get_day_event_list():is_event_type_active(v_u_19.EventType.PackSale) then
            f_add_pack_button(v_u_26.PackPurchaseButtons.CoinPackButton, v_u_10.ProductID_CoinPack_V3_Sale50, function(_) --[[ Line: 163 ]]
                --[[ Upvalues: (ref 1): v_u_26 ]]
                v_u_26.PackPurchaseButtons.CoinPackPopup.Parent = nil
            end):get_part().SurfaceGui.Frame.SaleOverlay.Visible = true
            f_add_pack_button(v_u_26.PackPurchaseButtons.StarPackButton, v_u_10.ProductID_StarPack_V3_Sale50):get_part().SurfaceGui.Frame.SaleOverlay.Visible = true
            f_add_pack_button(v_u_26.PackPurchaseButtons.StarterPackButton, v_u_10.ProductID_StarterPack_V3_Sale50, function(_) --[[ Line: 167 ]]
                --[[ Upvalues: (ref 1): v_u_26 ]]
                v_u_26.PackPurchaseButtons.StarterPackPopup.Parent = nil
            end):get_part().SurfaceGui.Frame.SaleOverlay.Visible = true
        else
            f_add_pack_button(v_u_26.PackPurchaseButtons.CoinPackButton, v_u_10.ProductID_CoinPack_V3, function(p53) --[[ Line: 171 ]]
                --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_20, (ref 3): v_u_4, (ref 4): v_u_26 ]]
                v_u_33:push_back_to(v_u_20.Tab.Packs, v_u_4:new(p53, p53:get_child_part(), v_u_26.PackPurchaseButtons.CoinPackPopup):set_default_sgui())
            end):get_part().SurfaceGui.Frame.SaleOverlay.Visible = false
            f_add_pack_button(v_u_26.PackPurchaseButtons.StarPackButton, v_u_10.ProductID_StarPack_V3):get_part().SurfaceGui.Frame.SaleOverlay.Visible = false
            f_add_pack_button(v_u_26.PackPurchaseButtons.StarterPackButton, v_u_10.ProductID_StarterPack_V3, function(p54) --[[ Line: 179 ]]
                --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_20, (ref 3): v_u_4, (ref 4): v_u_26 ]]
                v_u_33:push_back_to(v_u_20.Tab.Packs, v_u_4:new(p54, p54:get_child_part(), v_u_26.PackPurchaseButtons.StarterPackPopup):set_default_sgui())
            end):get_part().SurfaceGui.Frame.SaleOverlay.Visible = false
        end;
        local function f_add_tab_button(p55, p_u_56) --[[ Name: add_tab_button ]] --[[ Line: 190 ]]
            --[[ Upvalues: (copy 1): p_u_38, (ref 2): p_u_22, (ref 3): v_u_5, (ref 4): v_u_4, (ref 5): v_u_26, (ref 6): p_u_23, (ref 7): l_Currency_0, (ref 8): v_u_12, (ref 9): v_u_32 ]]
            local v57 = p_u_38:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(p_u_38, v_u_26.PrimaryPart, p55), p_u_23, function() --[[ Line: 194 ]]
                --[[ Upvalues: (ref 1): l_Currency_0, (copy 2): p_u_56, (ref 3): p_u_22, (ref 4): v_u_12, (ref 5): p_u_38 ]]
                l_Currency_0 = p_u_56
                p_u_22._sfx_manager:play_sfx(v_u_12.SFX_MENU_OPEN)
                p_u_38:update_ui_mode()
            end):set_auto_zoffset_behaviour(true))
            v_u_32:add(p_u_56, v57)
            return v57;
        end;
        f_add_tab_button(v_u_26.TabButtons.TabCurrency, v_u_20.Tab.Currency):get_part().SurfaceGui.Frame.SaleOverlay.Visible = p_u_22._player_blob_manager:get_day_event_list():is_event_type_active(v_u_19.EventType.CoinSale) or p_u_22._player_blob_manager:get_day_event_list():is_event_type_active(v_u_19.EventType.StarSale)
        f_add_tab_button(v_u_26.TabButtons.TabPacks, v_u_20.Tab.Packs):get_part().SurfaceGui.Frame.SaleOverlay.Visible = p_u_22._player_blob_manager:get_day_event_list():is_event_type_active(v_u_19.EventType.PackSale)
        p_u_38:add_cycle_element(p_u_22, 1, v_u_5:new(v_u_4:new(p_u_38, v_u_26.PrimaryPart, v_u_26.TabButtons.TabVIP), p_u_23, function() --[[ Line: 210 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_12, (ref 3): p_u_24, (ref 4): v_u_18, (ref 5): p_u_23 ]]
            p_u_22._sfx_manager:play_sfx(v_u_12.SFX_MENU_OPEN)
            p_u_24:push_menu(v_u_18:new(p_u_22, p_u_23, p_u_24))
        end)):get_part().SurfaceGui.Frame.SaleOverlay.Visible = p_u_22._player_blob_manager:get_day_event_list():is_event_type_active(v_u_19.EventType.VIPSale)
        p_u_22:set_local_character_cframe(CFrame.new(v_u_1:get_randomized_character_position(v_u_11:get_lobby_anchors().Shop.CurrencyShop.StandAnchor.Position, v_u_11:get_lobby_anchors().Shop.CurrencyShop.LookAnchor.Position), v_u_11:get_lobby_anchors().Shop.CurrencyShop.LookAnchor.Position))
        p_u_22:transition_local_camera_cframe(CFrame.new(v_u_11:get_lobby_anchors().Shop.CurrencyShop.CameraAnchor.Position, v_u_11:get_lobby_anchors().Shop.CurrencyShop.LookAnchor.Position))
        v_u_30 = v_u_1:udim_obj_wrapper(v_u_26.MainSurface.SurfaceGui.Frame.LoadedFrame)
        v_u_29 = v_u_1:udim_obj_wrapper(v_u_26.MainSurface.SurfaceGui.Frame.LoadingFrame)
        v_u_34 = v_u_30._obj.CoinSection.Display
        v_u_35 = v_u_30._obj.StarSection.Display
        l_InfoRequest_0 = v_u_20.Mode.InfoRequest
        if v_u_21 == false and (p_u_22._player_blob_manager:get_day_event_list():is_event_type_active(v_u_19.EventType.PackSale) == true and (p_u_22._player_blob_manager:get_day_event_list():is_event_type_active(v_u_19.EventType.CoinSale) ~= true and p_u_22._player_blob_manager:get_day_event_list():is_event_type_active(v_u_19.EventType.StarSale) ~= true)) then
            l_Currency_0 = v_u_20.Tab.Packs
        end;
        v_u_21 = true
        p_u_38:update_ui_mode()
        l__shop_local_protocol_0:request_currency_purchase_info_v3(function(p58) --[[ Line: 244 ]]
            --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_20, (copy 3): p_u_38 ]]
            if l_InfoRequest_0 ~= v_u_20.Mode.Closed then
                l_InfoRequest_0 = v_u_20.Mode.Ready
                p_u_38:info_update(p58)
                p_u_38:update_ui_mode()
            end;
        end)
        p_u_22._npcs:get_npc(v_u_13.NPC.RobuxShopRoxie):set_visible(false)
        p_u_38:set_alpha(0)
    end;
    v25.prompt_purchase = function(p_u_59, p60) --[[ Name: prompt_purchase ]] --[[ Line: 255 ]]
        --[[ Upvalues: (ref 1): v_u_17, (ref 2): v_u_10, (ref 3): l_InfoRequest_0, (ref 4): v_u_20, (ref 5): v_u_7, (copy 6): p_u_22, (ref 7): v_u_12, (ref 8): v_u_9, (copy 9): p_u_24, (ref 10): v_u_6, (copy 11): p_u_23, (ref 12): v_u_8, (ref 13): v_u_36 ]]
        v_u_17:is_enum_member(p60, v_u_10)
        if l_InfoRequest_0 == v_u_20.Mode.Purchasing then
            v_u_7:errf("BuyCurrencyV3UI::prompt_purchase current_mode Purchasing")
        end;
        p_u_22._sfx_manager:play_sfx(v_u_12.SFX_MENU_OPEN_LONG)
        l_InfoRequest_0 = v_u_20.Mode.Purchasing
        p_u_59:update_ui_mode()
        local function _() --[[ Name: get_player_blob_hash ]] --[[ Line: 264 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_9 ]]
            local v61 = p_u_22._player_blob_manager:get_player_blob()
            return v_u_9:get_coin_currency(v61) + v_u_9:get_star_currency(v61) * 1000;
        end;
        local function _(p62, p63) --[[ Name: player_blob_hash_check ]] --[[ Line: 268 ]]
            --[[ Upvalues: (ref 1): p_u_22, (ref 2): v_u_7 ]]
            if p62 == p63 then
                p_u_22._update_enqueue_fn:enqueue_function(function() --[[ Line: 270 ]]
                    --[[ Upvalues: (ref 1): v_u_7 ]]
                    v_u_7:errf("BuyCurrencyV3UI:prompt_purchase player_blob_hash_check FAILED")
                end)
            end;
        end;
        local function _() --[[ Name: set_ui_mode_to_ready ]] --[[ Line: 276 ]]
            --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_20, (copy 3): p_u_59 ]]
            l_InfoRequest_0 = v_u_20.Mode.Ready
            p_u_59:update_ui_mode()
        end;
        local v64 = p_u_22._player_blob_manager:get_player_blob()
        local v_u_65 = v_u_9:get_coin_currency(v64) + v_u_9:get_star_currency(v64) * 1000
        local v_u_66 = 0
        local v_u_67 = nil
        local v_u_69 = p_u_24:push_menu(v_u_6:new(p_u_22, p_u_23, p_u_24):set_text("", "Loading..."):set_title_sub_visible(false):set_on_close_fn(function() --[[ Line: 287 ]]
            --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_20, (copy 3): p_u_59 ]]
            l_InfoRequest_0 = v_u_20.Mode.Ready
            p_u_59:update_ui_mode()
        end):set_close_button_visible(false):set_update_fn(function(p68) --[[ Line: 291 ]]
            --[[ Upvalues: (ref 1): v_u_66, (ref 2): v_u_8, (ref 3): v_u_67 ]]
            v_u_66 = v_u_66 + v_u_8:TimescaleToDeltaTime(p68)
            if v_u_66 > 3 then
                v_u_67:set_close_button_visible(true)
            end;
        end))
        p_u_22._player_blob_manager:set_iap_finish_fn(function(p70, p71, p72) --[[ Line: 299 ]]
            --[[ Upvalues: (ref 1): p_u_24, (ref 2): v_u_69, (ref 3): v_u_10, (ref 4): v_u_6, (ref 5): p_u_22, (ref 6): p_u_23, (ref 7): v_u_36, (copy 8): v_u_65, (ref 9): v_u_9, (ref 10): v_u_7, (ref 11): v_u_12 ]]
            p_u_24:remove_menu(v_u_69)
            if p71 ~= true then
                p72 = v_u_10:get_description_for_productid(p70)
            end;
            p_u_24:push_menu(v_u_6:new(p_u_22, p_u_23, p_u_24):set_text("Purchase Complete!", p72))
            v_u_36:item_purchased()
            local v73 = v_u_65
            local v74 = p_u_22._player_blob_manager:get_player_blob()
            if v73 == v_u_9:get_coin_currency(v74) + v_u_9:get_star_currency(v74) * 1000 then
                p_u_22._update_enqueue_fn:enqueue_function(function() --[[ Line: 270 ]]
                    --[[ Upvalues: (ref 1): v_u_7 ]]
                    v_u_7:errf("BuyCurrencyV3UI:prompt_purchase player_blob_hash_check FAILED")
                end)
            end;
            p_u_22._sfx_manager:play_sfx(v_u_12.SFX_FANFARE)
        end)
        p_u_22._player_blob_manager:prompt_product_purchase(p60)
    end;
    v25.update_ui_mode = function(_) --[[ Name: update_ui_mode ]] --[[ Line: 318 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_20, (ref 3): v_u_30, (ref 4): v_u_29, (ref 5): v_u_37, (copy 6): v_u_31, (ref 7): l_Currency_0, (copy 8): v_u_32, (ref 9): v_u_1, (copy 10): v_u_33 ]]
        local v75
        if l_InfoRequest_0 == v_u_20.Mode.InfoRequest or l_InfoRequest_0 == v_u_20.Mode.Purchasing then
            v_u_30:set_visible(false)
            v_u_29:set_visible(true)
            v75 = false
        else
            v_u_30:set_visible(true)
            v_u_29:set_visible(false)
            v75 = true
        end;
        v_u_37:set_visible(v75)
        for v76, v77 in v_u_31:key_itr() do
            for v78 = 1, v77:count() do
                local v79 = v77:get(v78)
                if v75 then
                    v79:set_visible(v76 == l_Currency_0)
                else
                    v79:set_visible(false)
                end;
            end;
        end;
        for v_u_80, v_u_81 in v_u_32:key_itr() do
            v_u_1:try(function() --[[ Line: 344 ]]
                --[[ Upvalues: (copy 1): v_u_80, (ref 2): l_Currency_0, (copy 3): v_u_81 ]]
                if v_u_80 == l_Currency_0 then
                    v_u_81:get_part().SurfaceGui.Frame.ImageLabel.Image = "rbxgameasset://Images/TCUI_news_pageitem_selected"
                else
                    v_u_81:get_part().SurfaceGui.Frame.ImageLabel.Image = "rbxgameasset://Images/TCUI_news_pageitem_unselected"
                end;
            end)
            v_u_81:set_visible(v75)
        end;
        for v82, v83 in v_u_33:key_itr() do
            for v84 = 1, v83:count() do
                local v85 = v83:get(v84)
                if v75 then
                    v85:set_visible(v82 == l_Currency_0)
                else
                    v85:set_visible(false)
                end;
            end;
        end;
    end;
    v25.info_update = function(_, p_u_86) --[[ Name: info_update ]] --[[ Line: 366 ]]
        --[[ Upvalues: (ref 1): v_u_1, (copy 2): v_u_31, (ref 3): v_u_17, (ref 4): v_u_20 ]]
        local function _(p87) --[[ Name: find_info_for_productid ]] --[[ Line: 367 ]]
            --[[ Upvalues: (copy 1): p_u_86 ]]
            local v88 = nil
            for v89 = 1, #p_u_86 do
                local v90 = p_u_86[v89]
                if v90.ProductID == p87 then
                    return v90;
                end;
            end;
            return v88;
        end;
        local function _(p_u_91, p_u_92) --[[ Name: currency_button_info_update ]] --[[ Line: 378 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:try(function() --[[ Line: 379 ]]
                --[[ Upvalues: (copy 1): p_u_91, (copy 2): p_u_92 ]]
                p_u_91.SurfaceGui.Frame.AmountDisplay.Text = string.format("%d", p_u_92.GetAmount)
                p_u_91.SurfaceGui.Frame.RobuxDisplay.TextLabel.Text = string.format("%d", p_u_92.RobuxCost)
            end)
        end;
        local function _(p_u_93, p_u_94) --[[ Name: pack_button_info_update ]] --[[ Line: 384 ]]
            --[[ Upvalues: (ref 1): v_u_1 ]]
            v_u_1:try(function() --[[ Line: 385 ]]
                --[[ Upvalues: (copy 1): p_u_93, (copy 2): p_u_94 ]]
                p_u_93.SurfaceGui.Frame.AmountDisplay.Text = p_u_94.PurchaseDescription
                p_u_93.SurfaceGui.Frame.RobuxDisplay.TextLabel.Text = string.format("%d", p_u_94.RobuxCost)
            end)
        end;
        for v95, v96 in v_u_31:key_itr() do
            for v97 = 1, v96:count() do
                local v98 = v96:get(v97)
                local v99 = v98:get_bound_data()
                local v_u_100 = nil
                for v101 = 1, #p_u_86 do
                    local v102 = p_u_86[v101]
                    if v102.ProductID == v99 then
                        v_u_100 = v102
                        break;
                    end;
                end;
                v_u_17:is_non_nil(v_u_100)
                if v95 == v_u_20.Tab.Currency then
                    v_u_17:is_true(v_u_100.IsCurrencyPurchase)
                    local v_u_103 = v98:get_part()
                    v_u_1:try(function() --[[ Line: 379 ]]
                        --[[ Upvalues: (copy 1): v_u_103, (copy 2): v_u_100 ]]
                        v_u_103.SurfaceGui.Frame.AmountDisplay.Text = string.format("%d", v_u_100.GetAmount)
                        v_u_103.SurfaceGui.Frame.RobuxDisplay.TextLabel.Text = string.format("%d", v_u_100.RobuxCost)
                    end)
                elseif v95 == v_u_20.Tab.Packs then
                    v_u_17:is_true(v_u_100.IsPack)
                    local v_u_104 = v98:get_part()
                    v_u_1:try(function() --[[ Line: 385 ]]
                        --[[ Upvalues: (copy 1): v_u_104, (copy 2): v_u_100 ]]
                        v_u_104.SurfaceGui.Frame.AmountDisplay.Text = v_u_100.PurchaseDescription
                        v_u_104.SurfaceGui.Frame.RobuxDisplay.TextLabel.Text = string.format("%d", v_u_100.RobuxCost)
                    end)
                end;
            end;
        end;
    end;
    v25.visual_update = function(p105, p106, p107) --[[ Name: visual_update ]] --[[ Line: 408 ]]
        --[[ Upvalues: (copy 1): p_u_22 ]]
        if p_u_22:transition_local_camera_cframe_finished() ~= false then
            p105:visual_update_base(p106, p107)
        end;
    end;
    local v_u_108 = 0
    v25.behaviour_update = function(p109, p110, p111) --[[ Name: behaviour_update ]] --[[ Line: 417 ]]
        --[[ Upvalues: (ref 1): v_u_108, (ref 2): v_u_8, (ref 3): v_u_15, (ref 4): l_InfoRequest_0, (ref 5): v_u_20, (ref 6): v_u_36 ]]
        p109:behaviour_update_base(p110, p111)
        p109:update_blob_sync()
        v_u_108 = v_u_8:incr_wrap(v_u_108, v_u_8:sec_to_tick(1.75) * p110, 1)
        if p109._current_mode == v_u_15.MODE_OPEN and (l_InfoRequest_0 == v_u_20.Mode.InfoRequest or (l_InfoRequest_0 == v_u_20.Mode.Ready or l_InfoRequest_0 == v_u_20.Mode.Purchasing)) then
            v_u_36:update(p110)
        end;
    end;
    local v_u_112 = -1
    v25.update_blob_sync = function(_) --[[ Name: update_blob_sync ]] --[[ Line: 431 ]]
        --[[ Upvalues: (ref 1): l_InfoRequest_0, (ref 2): v_u_20, (copy 3): p_u_22, (ref 4): v_u_112, (ref 5): v_u_34, (ref 6): v_u_9, (ref 7): v_u_35 ]]
        if l_InfoRequest_0 == v_u_20.Mode.Ready and (p_u_22._player_blob_manager:is_synced() and p_u_22._player_blob_manager:get_synced_time() ~= v_u_112) then
            v_u_112 = p_u_22._player_blob_manager:get_synced_time()
            local v113 = p_u_22._player_blob_manager:get_player_blob()
            v_u_34.Text = string.format("%d", v_u_9:get_coin_currency(v113))
            v_u_35.Text = string.format("%d", v_u_9:get_star_currency(v113))
        end;
    end;
    v25.layout = function(p114) --[[ Name: layout ]] --[[ Line: 443 ]]
        --[[ Upvalues: (copy 1): p_u_23, (ref 2): v_u_28, (ref 3): v_u_26, (ref 4): v_u_36, (copy 5): v_u_33, (ref 6): v_u_108 ]]
        p114:opt_rescale_to_max_nxy(p_u_23, 0.775, 0.925, v_u_28)
        local v115, v116 = p114:opt_update_cframe_params(p_u_23, {
            ["PositionNXY"] = Vector2.new(0.55, 0.45),
            ["OffsetXYZ"] = p114:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v115 == true then
            v_u_26:SetPrimaryPartCFrame(v116)
        end;
        v_u_36:layout()
        for _, v117 in v_u_33:key_itr() do
            for v118 = 1, v117:count() do
                local v119 = v117:get(v118)
                v119:set_scale(math.sin(v_u_108 * 3.141592653589793 * 2) * 0.1 + 1)
                v119:layout()
            end;
        end;
    end;
    v25.close_menu = function(p120) --[[ Name: close_menu ]] --[[ Line: 463 ]]
        --[[ Upvalues: (copy 1): p_u_22, (ref 2): v_u_12, (copy 3): p_u_24 ]]
        p_u_22._sfx_manager:play_sfx(v_u_12.SFX_MENU_CLOSE)
        p_u_24:remove_menu(p120)
    end;
    v25.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 468 ]]
        --[[ Upvalues: (ref 1): v_u_26, (copy 2): p_u_22, (ref 3): v_u_13 ]]
        v_u_26:Destroy()
        p_u_22._npcs:get_npc(v_u_13.NPC.RobuxShopRoxie):set_visible(true)
    end;
    v25.set_alpha = function(_, p121) --[[ Name: set_alpha ]] --[[ Line: 473 ]]
        --[[ Upvalues: (ref 1): v_u_27, (ref 2): v_u_1, (ref 3): v_u_26 ]]
        if v_u_27 ~= p121 then
            v_u_27 = p121
            v_u_1:r_set_alpha(v_u_26, v_u_27)
        end;
    end;
    v25.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 479 ]]
        --[[ Upvalues: (ref 1): v_u_27 ]]
        return v_u_27;
    end;
    v25.set_scale = function(_, p122) --[[ Name: set_scale ]] --[[ Line: 480 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        v_u_28 = p122
    end;
    v25.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 481 ]]
        --[[ Upvalues: (ref 1): v_u_28 ]]
        return v_u_28;
    end;
    v25.get_native_size = function(p123) --[[ Name: get_native_size ]] --[[ Line: 483 ]]
        return p123._native_size;
    end;
    v25.get_size = function(p124) --[[ Name: get_size ]] --[[ Line: 486 ]]
        return p124._size;
    end;
    v25.set_size = function(p125, p126) --[[ Name: set_size ]] --[[ Line: 489 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        p125._size = p126
        v_u_26.PrimaryPart.Size = Vector3.new(p126.X, p126.Y, 0)
    end;
    v25.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 493 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26.PrimaryPart.Position;
    end;
    v25.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 496 ]]
        --[[ Upvalues: (ref 1): v_u_26 ]]
        return v_u_26.PrimaryPart.SurfaceGui;
    end;
    v25:cons()
    return v25;
end;
return v_u_20;
