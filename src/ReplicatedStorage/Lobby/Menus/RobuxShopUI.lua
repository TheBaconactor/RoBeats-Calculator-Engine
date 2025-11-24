-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:38 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPDict)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
local v_u_4 = require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_6 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
local v_u_7 = require(game.ReplicatedStorage.Shared.DebugOut)
local v_u_8 = require(game.ReplicatedStorage.Local.SFXManager)
require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_9 = require(game.ReplicatedStorage.LocalShared.EnvironmentSetup)
local v_u_10 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_11 = require(game.ReplicatedStorage.PlayerInfo.PurchaseInfo)
local v_u_12 = require(game.ReplicatedStorage.Lobby.Dialogue.BuyCurrencyShopDialogue)
local v_u_13 = require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_14 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_15 = require(game.ReplicatedStorage.Lobby.Util.RobuxShopCategory)
local v_u_16 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_17 = require(game.ReplicatedStorage.Shared.CurveUtil)
local v_u_18 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v_u_19 = require(game.ReplicatedStorage.LocalShared.PlayerPolicy)
local v_u_20 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v21 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_22 = nil
local v_u_23 = nil
local v_u_24 = nil
v21:require_client(function() --[[ Line: 28 ]]
    --[[ Upvalues: (ref 1): v_u_22, (ref 2): v_u_23, (ref 3): v_u_24 ]]
    v_u_22 = require(game.ReplicatedStorage.Lobby.Menus.VIPPurchaseUI)
    v_u_23 = require(game.ReplicatedStorage.Lobby.Menus.CraftingMaterialsAcquiredUI)
    v_u_24 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
end)
local v25 = {}
local l_CoinsAndStars_0 = v_u_15.CoinsAndStars
v25.set_selected_category = function(_, p26) --[[ Name: set_selected_category ]] --[[ Line: 38 ]]
    --[[ Upvalues: (copy 1): v_u_14, (copy 2): v_u_15, (ref 3): l_CoinsAndStars_0 ]]
    v_u_14:is_enum_member(p26, v_u_15)
    l_CoinsAndStars_0 = p26
end;
v25.new = function(_, p_u_27, p_u_28, p_u_29) --[[ Name: new ]] --[[ Line: 43 ]]
    --[[ Upvalues: (copy 1): v_u_19, (copy 2): v_u_4, (copy 3): v_u_2, (copy 4): v_u_3, (copy 5): v_u_10, (ref 6): l_CoinsAndStars_0, (copy 7): v_u_15, (copy 8): v_u_1, (copy 9): v_u_12, (copy 10): v_u_6, (copy 11): v_u_5, (copy 12): v_u_8, (ref 13): v_u_22, (copy 14): v_u_7, (copy 15): v_u_16, (copy 16): v_u_14, (copy 17): v_u_11, (copy 18): v_u_17, (copy 19): v_u_20, (ref 20): v_u_24, (copy 21): v_u_18, (ref 22): v_u_23, (copy 23): v_u_13, (copy 24): v_u_9 ]]
    if v_u_19:has_any_paid_item_restrictions() then
        return v_u_19:create_error_menu(p_u_27, p_u_28, p_u_29);
    end;
    local v_u_30 = v_u_4:new(p_u_28, p_u_29)
    local v_u_31 = nil
    local v_u_32 = nil
    local v_u_33 = nil
    local v_u_34 = nil
    local v_u_35 = nil
    local v_u_36 = v_u_2:new()
    local v_u_37 = v_u_3:new()
    local v_u_40 = v_u_10:new():set_fn_get_data_list(function() --[[ Line: 59 ]]
        --[[ Upvalues: (ref 1): v_u_37 ]]
        return v_u_37;
    end):set_fn_set_element_data(function(p38, p39) --[[ Line: 60 ]]
        if p39 == nil then
            p38:set_visible(false)
        else
            p38:set_visible(true)
            p38:set_display_element(p39)
        end;
    end)
    local v_u_41 = nil
    local v_u_42 = v_u_3:new()
    local v_u_43 = nil
    local v_u_44 = nil
    local v_u_49 = v_u_10:new():set_fn_get_data_list(function() --[[ Line: 73 ]]
        --[[ Upvalues: (ref 1): v_u_42 ]]
        return v_u_42;
    end):set_fn_set_element_data(function(p45, p46) --[[ Line: 74 ]]
        if p46 == nil then
            p45:set_visible(false)
        else
            p45:set_visible(true)
            p45:set_display_element(p46)
        end;
    end):set_fn_next_prev_visible(function(p47, p48) --[[ Line: 82 ]]
        --[[ Upvalues: (ref 1): v_u_43, (ref 2): v_u_44 ]]
        v_u_43:set_visible(p47)
        v_u_44:set_visible(p48)
    end)
    local function f_select_category(p50) --[[ Name: select_category ]] --[[ Line: 87 ]]
        --[[ Upvalues: (ref 1): l_CoinsAndStars_0, (ref 2): v_u_42, (ref 3): v_u_36, (ref 4): v_u_34, (ref 5): v_u_15, (copy 6): v_u_40, (copy 7): v_u_49 ]]
        l_CoinsAndStars_0 = p50
        v_u_42 = v_u_36:get(l_CoinsAndStars_0)
        v_u_34.Text = v_u_15:category_to_name(l_CoinsAndStars_0)
        v_u_40:refresh_element_data(function(p51) --[[ Line: 91 ]]
            p51:update_selected_status()
        end)
        v_u_49:page_update()
    end;
    local function f_cons() --[[ Name: cons ]] --[[ Line: 95 ]]
        --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_1, (copy 3): v_u_30, (ref 4): v_u_35, (ref 5): v_u_12, (copy 6): p_u_27, (ref 7): v_u_32, (ref 8): v_u_33, (ref 9): v_u_34, (ref 10): v_u_6, (ref 11): v_u_5, (copy 12): p_u_28, (ref 13): v_u_8, (copy 14): p_u_29, (copy 15): v_u_40, (ref 16): l_CoinsAndStars_0, (ref 17): v_u_10, (copy 18): f_select_category, (ref 19): v_u_15, (ref 20): v_u_36, (ref 21): v_u_41, (ref 22): v_u_22, (ref 23): v_u_43, (copy 24): v_u_49, (ref 25): v_u_44, (ref 26): v_u_7, (ref 27): v_u_16, (ref 28): v_u_37 ]]
        v_u_31 = game.ReplicatedStorage.LobbyElementProtos.WorldUIProto.Shop.RobuxShopUI:Clone()
        v_u_31.Name = v_u_1:gen_name(v_u_31.Name)
        v_u_30:set_showing(true)
        v_u_30._native_size = v_u_31.PrimaryPart.Size
        v_u_30._size = v_u_30._native_size
        v_u_35 = v_u_12:new(p_u_27, v_u_30, v_u_30, v_u_31)
        local l_Frame_0 = v_u_31.PrimaryPart.SurfaceGui.Frame
        v_u_32 = l_Frame_0.LoadingSection
        v_u_33 = l_Frame_0.LoadedSection
        v_u_34 = v_u_33.TabTitleDisplay
        v_u_30:add_cycle_element(p_u_27, 1, v_u_6:new(v_u_5:new(v_u_30, v_u_31.PrimaryPart, v_u_31.BackButtonSurface), p_u_28, function() --[[ Line: 113 ]]
            --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_8, (ref 3): p_u_29, (ref 4): v_u_30 ]]
            p_u_27._sfx_manager:play_sfx(v_u_8.SFX_MENU_CLOSE)
            p_u_29:remove_menu(v_u_30)
        end))
        local l_CategorySection_0 = v_u_31.CategorySection
        v_u_40:create_list_elements_from_anchors_and_proto({
            l_CategorySection_0.Anchors.Anchor1,
            l_CategorySection_0.Anchors.Anchor2,
            l_CategorySection_0.Anchors.Anchor3,
            l_CategorySection_0.Anchors.Anchor4,
            l_CategorySection_0.Anchors.Anchor5,
            l_CategorySection_0.Anchors.Anchor6
        }, l_CategorySection_0.CategoryButtonProto, v_u_31, function(p52) --[[ Line: 134 ]]
            --[[ Upvalues: (ref 1): l_CoinsAndStars_0, (ref 2): v_u_10, (ref 3): v_u_30, (ref 4): p_u_27, (ref 5): v_u_6, (ref 6): v_u_5, (ref 7): v_u_31, (ref 8): p_u_28, (ref 9): v_u_8, (ref 10): f_select_category, (ref 11): v_u_15, (ref 12): v_u_36, (ref 13): v_u_1 ]]
            local l_Frame_1 = p52.PrimaryPart.SurfaceGui.Frame
            local l_NameDisplay_0 = l_Frame_1.NameDisplay
            local l_Icon_0 = l_Frame_1.Icon
            local l_SaleOverlay_0 = l_Frame_1.SaleOverlay
            local l_ButtonBack_0 = l_Frame_1.ButtonBack
            local v_u_53 = l_CoinsAndStars_0
            local v55 = v_u_10.ButtonElement:new(v_u_30:add_cycle_element(p_u_27, 1, v_u_6:new(v_u_5:new(v_u_30, v_u_31.PrimaryPart, p52.PrimaryPart), p_u_28, function() --[[ Line: 146 ]]
                --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_8, (ref 3): f_select_category, (ref 4): v_u_53 ]]
                p_u_27._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
                f_select_category(v_u_53)
            end)):set_auto_zoffset_behaviour(true)):set_fn_set_display_element(function(p54) --[[ Line: 151 ]]
                --[[ Upvalues: (ref 1): v_u_53, (copy 2): l_NameDisplay_0, (ref 3): v_u_15, (copy 4): l_Icon_0, (copy 5): l_SaleOverlay_0, (ref 6): v_u_36 ]]
                v_u_53 = p54
                l_NameDisplay_0.Text = v_u_15:category_to_name(p54)
                l_Icon_0.Image = v_u_15:category_to_icon(p54)
                l_SaleOverlay_0.Visible = v_u_15:is_category_to_product_info_data_dict_category_matching_default(v_u_36, p54) ~= true
            end)
            v55.update_selected_status = function(_) --[[ Name: update_selected_status ]] --[[ Line: 157 ]]
                --[[ Upvalues: (ref 1): v_u_53, (ref 2): l_CoinsAndStars_0, (copy 3): l_ButtonBack_0, (ref 4): v_u_1 ]]
                if v_u_53 == l_CoinsAndStars_0 then
                    l_ButtonBack_0.Image = v_u_1:get_tab_selected_container_noarrow_assetid()
                else
                    l_ButtonBack_0.Image = v_u_1:get_tab_unselected_container_assetid()
                end;
            end;
            return v55;
        end)
        v_u_41 = v_u_30:add_cycle_element(p_u_27, 1, v_u_6:new(v_u_5:new(v_u_30, v_u_31.PrimaryPart, v_u_31.VIPButton), p_u_28, function() --[[ Line: 172 ]]
            --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_8, (ref 3): p_u_29, (ref 4): v_u_22, (ref 5): p_u_28 ]]
            p_u_27._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
            p_u_29:push_menu(v_u_22:new(p_u_27, p_u_28, p_u_29))
        end))
        local l_TabItemsSection_0 = v_u_31.TabItemsSection
        v_u_43 = v_u_30:add_cycle_element(p_u_27, 1, v_u_6:new(v_u_5:new(v_u_30, v_u_31.PrimaryPart, l_TabItemsSection_0.ArrowRight), p_u_28, function() --[[ Line: 185 ]]
            --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_8, (ref 3): v_u_49 ]]
            p_u_27._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_49:next_page()
        end))
        v_u_44 = v_u_30:add_cycle_element(p_u_27, 1, v_u_6:new(v_u_5:new(v_u_30, v_u_31.PrimaryPart, l_TabItemsSection_0.ArrowLeft), p_u_28, function() --[[ Line: 193 ]]
            --[[ Upvalues: (ref 1): p_u_27, (ref 2): v_u_8, (ref 3): v_u_49 ]]
            p_u_27._sfx_manager:play_sfx(v_u_8.SFX_BUTTONPRESS)
            v_u_49:prev_page()
        end))
        v_u_49:set_fn_update_page_display(function(p56, p57) --[[ Line: 199 ]]
            --[[ Upvalues: (ref 1): v_u_33 ]]
            v_u_33.TabItemsPageDisplay.Visible = p57 > 1
            v_u_33.TabItemsPageDisplay.Text = string.format("%d / %d", p56, p57)
        end)
        v_u_49:create_list_elements_from_anchors_and_proto({
            l_TabItemsSection_0.Anchors.Anchor1,
            l_TabItemsSection_0.Anchors.Anchor2,
            l_TabItemsSection_0.Anchors.Anchor3,
            l_TabItemsSection_0.Anchors.Anchor4,
            l_TabItemsSection_0.Anchors.Anchor5,
            l_TabItemsSection_0.Anchors.Anchor6,
            l_TabItemsSection_0.Anchors.Anchor7,
            l_TabItemsSection_0.Anchors.Anchor8
        }, l_TabItemsSection_0.ItemProto, v_u_31, function(p_u_58) --[[ Line: 217 ]]
            --[[ Upvalues: (ref 1): v_u_10, (ref 2): v_u_30, (ref 3): p_u_27, (ref 4): v_u_6, (ref 5): v_u_5, (ref 6): v_u_31, (ref 7): p_u_28, (ref 8): v_u_7, (ref 9): v_u_8, (ref 10): p_u_29, (ref 11): v_u_16 ]]
            local l_Frame_2 = p_u_58.PrimaryPart.SurfaceGui.Frame
            local l_Title_0 = l_Frame_2.Title
            local l_Display_0 = l_Frame_2.RobuxDisplay.Display
            local l_Icon_1 = l_Frame_2.Icon
            local l_SaleOverlay_1 = l_Frame_2.SaleOverlay
            local v_u_59 = nil
            local v_u_60 = nil
            return v_u_10.ButtonElement:new(v_u_30:add_cycle_element(p_u_27, 1, v_u_6:new(v_u_5:new(v_u_30, v_u_31.PrimaryPart, p_u_58.PrimaryPart), p_u_28, function() --[[ Line: 231 ]]
                --[[ Upvalues: (ref 1): v_u_59, (ref 2): v_u_7, (ref 3): p_u_27, (ref 4): v_u_8, (ref 5): v_u_30 ]]
                if v_u_59 == nil then
                    return v_u_7:warnf("purchase_info_data nil");
                end;
                p_u_27._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                v_u_30:prompt_purchase(v_u_59:get_product_id())
            end)):set_auto_zoffset_behaviour(true, function(p61) --[[ Line: 237 ]]
                --[[ Upvalues: (ref 1): v_u_60 ]]
                v_u_60:set_override_auto_zoffset_behaviour(p61)
            end):set_selected_rotation_amplitude(0.5):set_selected_tar_scale(1.05), function(p62) --[[ Line: 242 ]]
                --[[ Upvalues: (ref 1): v_u_60, (ref 2): v_u_30, (ref 3): p_u_27, (ref 4): v_u_6, (ref 5): v_u_5, (copy 6): p_u_58, (ref 7): p_u_28, (ref 8): v_u_59, (ref 9): v_u_7, (ref 10): v_u_8, (ref 11): p_u_29, (ref 12): v_u_16 ]]
                local v63 = p62:get_button()
                v_u_60 = v_u_30:add_cycle_element(p_u_27, 1, v_u_6:new(v_u_5:new(v63:get_uichild(), v63:get_uichild():get_child_part(), p_u_58.InfoButton), p_u_28, function() --[[ Line: 251 ]]
                    --[[ Upvalues: (ref 1): v_u_59, (ref 2): v_u_7, (ref 3): p_u_27, (ref 4): v_u_8, (ref 5): p_u_29, (ref 6): v_u_16, (ref 7): p_u_28 ]]
                    if v_u_59 == nil then
                        return v_u_7:warnf("purchase_info_data nil");
                    end;
                    p_u_27._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN)
                    p_u_29:push_menu(v_u_16:new(p_u_27, p_u_28, p_u_29):set_text(v_u_59:get_name(), string.format("Price: %d Robux\nContents: %s", v_u_59:get_robux_cost(), v_u_59:get_contents_description())))
                end))
            end):set_fn_set_display_element(function(p64) --[[ Line: 266 ]]
                --[[ Upvalues: (ref 1): v_u_59, (copy 2): l_Title_0, (copy 3): l_Display_0, (copy 4): l_Icon_1, (copy 5): l_SaleOverlay_1 ]]
                v_u_59 = p64
                l_Title_0.Text = v_u_59:get_name()
                l_Display_0.Text = tostring(v_u_59:get_robux_cost())
                l_Icon_1.Image = v_u_59:get_display_icon()
                l_SaleOverlay_1.Visible = v_u_59:has_copy_from_id()
            end):set_fn_set_visible(function(p65) --[[ Line: 275 ]]
                --[[ Upvalues: (ref 1): v_u_60 ]]
                v_u_60:set_visible(p65)
            end);
        end)
        local function _(p66) --[[ Name: update_display_loaded ]] --[[ Line: 283 ]]
            --[[ Upvalues: (ref 1): v_u_33, (ref 2): v_u_32, (ref 3): v_u_40, (ref 4): v_u_49, (ref 5): v_u_41 ]]
            v_u_33.Visible = p66
            v_u_32.Visible = not p66
            v_u_40:set_visible(p66)
            v_u_49:set_visible(p66)
            v_u_41:set_visible(p66)
        end;
        p_u_27._update_enqueue_fn:delay_sec_fn_call(0.1, function() --[[ Line: 292 ]]
            --[[ Upvalues: (ref 1): v_u_36, (ref 2): v_u_15, (ref 3): p_u_27, (ref 4): v_u_37, (ref 5): v_u_33, (ref 6): v_u_32, (ref 7): v_u_40, (ref 8): v_u_49, (ref 9): v_u_41, (ref 10): f_select_category, (ref 11): l_CoinsAndStars_0 ]]
            v_u_36 = v_u_15:generate_category_to_product_info_data_dict_for_day_event_list(p_u_27._player_blob_manager:get_day_event_list())
            v_u_37 = v_u_36:key_list()
            v_u_33.Visible = true
            v_u_32.Visible = false
            v_u_40:set_visible(true)
            v_u_49:set_visible(true)
            v_u_41:set_visible(true)
            v_u_40:page_update()
            f_select_category(l_CoinsAndStars_0)
        end)
        v_u_33.Visible = false
        v_u_32.Visible = true
        v_u_40:set_visible(false)
        v_u_49:set_visible(false)
        v_u_41:set_visible(false)
        v_u_30:transition_update_visual(0)
        v_u_30:layout()
    end;
    v_u_30.prompt_purchase = function(_, p67) --[[ Name: prompt_purchase ]] --[[ Line: 305 ]]
        --[[ Upvalues: (ref 1): v_u_14, (ref 2): v_u_11, (copy 3): p_u_27, (ref 4): v_u_8, (copy 5): p_u_29, (ref 6): v_u_16, (copy 7): p_u_28, (ref 8): v_u_17, (ref 9): v_u_20, (ref 10): v_u_24, (ref 11): v_u_18, (ref 12): v_u_23, (ref 13): v_u_35 ]]
        v_u_14:is_enum_member(p67, v_u_11)
        p_u_27._sfx_manager:play_sfx(v_u_8.SFX_MENU_OPEN_LONG)
        local v_u_68 = 0
        local v_u_69 = nil
        local v_u_71 = p_u_29:push_menu(v_u_16:new(p_u_27, p_u_28, p_u_29):set_text("", "Loading..."):set_title_sub_visible(false):set_close_button_visible(false):set_update_fn(function(p70) --[[ Line: 316 ]]
            --[[ Upvalues: (ref 1): v_u_68, (ref 2): v_u_17, (ref 3): v_u_69 ]]
            v_u_68 = v_u_68 + v_u_17:TimescaleToDeltaTime(p70)
            if v_u_68 > 3 then
                v_u_69:set_close_button_visible(true)
            end;
        end))
        p_u_27._player_blob_manager:set_iap_finish_fn(function(_, _, _, p72) --[[ Line: 324 ]]
            --[[ Upvalues: (ref 1): p_u_29, (ref 2): v_u_71, (ref 3): v_u_20, (ref 4): v_u_24, (ref 5): p_u_27, (ref 6): p_u_28, (ref 7): v_u_18, (ref 8): v_u_23, (ref 9): v_u_8, (ref 10): v_u_35 ]]
            p_u_29:remove_menu(v_u_71)
            if v_u_20.UseRewardDescriptionInfoAcquiredUI == true then
                p_u_29:push_menu(v_u_24:new(p_u_27, p_u_28, p_u_29, v_u_18.RewardInfo:table_to_list(p72)):set_header_text("Thank you for your purchase!"):set_sub_text("Acquired the following..."))
            else
                p_u_29:push_menu(v_u_23:new(p_u_27, p_u_28, p_u_29, v_u_18.RewardInfo:table_to_list(p72)))
                p_u_27._sfx_manager:play_sfx(v_u_8.SFX_FANFARE)
            end;
            v_u_35:item_purchased()
        end)
        p_u_27._player_blob_manager:prompt_product_purchase(p67)
    end;
    v_u_30.behaviour_update = function(p73, p74, p75) --[[ Name: behaviour_update ]] --[[ Line: 345 ]]
        --[[ Upvalues: (ref 1): v_u_13, (ref 2): v_u_35 ]]
        p73:behaviour_update_base(p74, p75)
        if p73._current_mode == v_u_13.MODE_OPEN then
            v_u_35:update(p74)
        end;
    end;
    v_u_30.do_remove = function(_, _) --[[ Name: do_remove ]] --[[ Line: 353 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        v_u_31:Destroy()
    end;
    local v_u_76 = 1
    local v_u_77 = 1
    v_u_30.layout = function(p78) --[[ Name: layout ]] --[[ Line: 359 ]]
        --[[ Upvalues: (copy 1): p_u_28, (ref 2): v_u_77, (ref 3): v_u_31, (copy 4): v_u_40, (copy 5): v_u_49, (ref 6): v_u_35 ]]
        p78:opt_rescale_to_max_nxy(p_u_28, 0.775, 0.9, v_u_77)
        local v79, v80 = p78:opt_update_cframe_params(p_u_28, {
            ["PositionNXY"] = Vector2.new(0.55, 0.45),
            ["OffsetXYZ"] = p78:anchored_offset(0.5, 0.5),
            ["LocalRotationOffset"] = Vector3.new(0, 0, 0)
        })
        if v79 == true then
            v_u_31:SetPrimaryPartCFrame(v80)
        end;
        v_u_40:layout()
        v_u_49:layout()
        v_u_35:layout()
    end;
    v_u_30.set_alpha = function(_, p81) --[[ Name: set_alpha ]] --[[ Line: 375 ]]
        --[[ Upvalues: (ref 1): v_u_76, (ref 2): v_u_1, (ref 3): v_u_31 ]]
        if v_u_76 ~= p81 then
            v_u_76 = p81
            v_u_1:r_set_alpha(v_u_31, v_u_76)
        end;
    end;
    v_u_30.get_alpha = function(_) --[[ Name: get_alpha ]] --[[ Line: 381 ]]
        --[[ Upvalues: (ref 1): v_u_76 ]]
        return v_u_76;
    end;
    v_u_30.set_scale = function(_, p82) --[[ Name: set_scale ]] --[[ Line: 382 ]]
        --[[ Upvalues: (ref 1): v_u_77 ]]
        v_u_77 = p82
    end;
    v_u_30.get_scale = function(_) --[[ Name: get_scale ]] --[[ Line: 383 ]]
        --[[ Upvalues: (ref 1): v_u_77 ]]
        return v_u_77;
    end;
    v_u_30.get_native_size = function(p83) --[[ Name: get_native_size ]] --[[ Line: 385 ]]
        return p83._native_size;
    end;
    v_u_30.get_size = function(p84) --[[ Name: get_size ]] --[[ Line: 388 ]]
        return p84._size;
    end;
    v_u_30.set_size = function(p85, p86) --[[ Name: set_size ]] --[[ Line: 391 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        p85._size = p86
        v_u_31.PrimaryPart.Size = Vector3.new(p86.X, p86.Y, 0)
    end;
    v_u_30.get_pos = function(_) --[[ Name: get_pos ]] --[[ Line: 395 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        return v_u_31.PrimaryPart.Position;
    end;
    v_u_30.get_sgui = function(_) --[[ Name: get_sgui ]] --[[ Line: 398 ]]
        --[[ Upvalues: (ref 1): v_u_31 ]]
        return v_u_31.PrimaryPart.SurfaceGui;
    end;
    v_u_30.set_showing = function(_, p87) --[[ Name: set_showing ]] --[[ Line: 401 ]]
        --[[ Upvalues: (ref 1): v_u_31, (ref 2): v_u_9 ]]
        if p87 then
            v_u_31.Parent = v_u_9:get_world_ui_folder()
        else
            v_u_31.Parent = nil
        end;
    end;
    f_cons()
    return v_u_30;
end;
return v25;
