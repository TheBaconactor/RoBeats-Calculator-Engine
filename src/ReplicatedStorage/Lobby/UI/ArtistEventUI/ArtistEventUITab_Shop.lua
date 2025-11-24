-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:58 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_3 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_4 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_5 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_6 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_7 = require(game.ReplicatedStorage.AudioData.SongDatabase)
local v_u_8 = require(game.ReplicatedStorage.PlayerInfo.ArtistEventInfo)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
require(game.ReplicatedStorage.AudioData.SongElementalColor)
local v_u_10 = require(game.ReplicatedStorage.Lobby.UI.TabControllerBase)
local v_u_11 = require(game.ReplicatedStorage.Shared.ListAdapter)
local v_u_12 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
require(game.ReplicatedStorage.PlayerInfo.TitleDatabase)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.DanceDatabase)
local v_u_14 = require(game.ReplicatedStorage.Avatar.SPAvatarEquipmentDatabase)
local v_u_15 = require(game.ReplicatedStorage.Shared.DebugConfig)
local v_u_16 = require(game.ReplicatedStorage.Lobby.Menus.RewardDescriptionInfoAcquiredUI)
local v_u_17 = require(game.ReplicatedStorage.Shared.RewardDescriptionInfo)
local v18 = require(game.ReplicatedStorage.Shared.Dependency)
local v_u_19 = nil
v18:require_client(function() --[[ Line: 30 ]]
    --[[ Upvalues: (ref 1): v_u_19 ]]
    v_u_19 = require(game.ReplicatedStorage.Lobby.Menus.DanceSelectUI)
end)
local v20 = {}
local v_u_39 = {
    ["new"] = function(_, p_u_21, p_u_22, p_u_23, p_u_24) --[[ Name: new ]] --[[ Line: 37 ]]
        --[[ Upvalues: (copy 1): v_u_2, (copy 2): v_u_3, (copy 3): v_u_4, (copy 4): v_u_1, (copy 5): v_u_8, (copy 6): v_u_9, (copy 7): v_u_7, (copy 8): v_u_12, (copy 9): v_u_13, (copy 10): v_u_14 ]]
        local v25 = {}
        local v_u_26 = nil
        local v_u_27 = nil
        local v_u_28 = nil
        local l_Frame_0 = p_u_24.PrimaryPart.SurfaceGui.Frame
        local v_u_29 = nil
        local v_u_30 = nil
        local v_u_31 = nil
        local v_u_32 = nil
        local v_u_33 = nil
        local v_u_34 = nil
        v25.cons = function(_) --[[ Name: cons ]] --[[ Line: 48 ]]
            --[[ Upvalues: (ref 1): v_u_29, (copy 2): l_Frame_0, (ref 3): v_u_30, (ref 4): v_u_31, (ref 5): v_u_32, (ref 6): v_u_33, (ref 7): v_u_34, (ref 8): v_u_26, (ref 9): v_u_2, (copy 10): p_u_23, (copy 11): p_u_24, (ref 12): v_u_27, (copy 13): p_u_21, (ref 14): v_u_3, (ref 15): v_u_4, (ref 16): v_u_28, (copy 17): p_u_22 ]]
            v_u_29 = l_Frame_0.IconSection.IconDisplay
            v_u_30 = l_Frame_0.IconSection.IconOverlay
            v_u_31 = l_Frame_0.InfoSection.NameDisplay
            v_u_32 = l_Frame_0.InfoSection.DescriptionDisplay
            v_u_33 = l_Frame_0.PriceSection.PriceDisplay
            v_u_34 = l_Frame_0.ClaimedDisplay
            v_u_26 = v_u_2:new(p_u_23, p_u_23:get_uichild_parent(), p_u_24.PrimaryPart):set_default_sgui()
            v_u_27 = p_u_23:add_cycle_element(p_u_21, 1, v_u_3:new(v_u_2:new(v_u_26, p_u_24.MainSurface, p_u_24.BuyButton), p_u_21._spui, function() --[[ Line: 60 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_4, (ref 3): v_u_28, (ref 4): p_u_22 ]]
                p_u_21._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
                if v_u_28 ~= nil then
                    p_u_22:on_buy_item(v_u_28)
                end;
            end)):set_auto_zoffset_behaviour(true)
        end;
        v25.set_display_element = function(p35, p36) --[[ Name: set_display_element ]] --[[ Line: 70 ]]
            --[[ Upvalues: (ref 1): v_u_28, (ref 2): v_u_33, (ref 3): v_u_1, (ref 4): v_u_30, (ref 5): v_u_31, (ref 6): v_u_8, (ref 7): v_u_9, (ref 8): v_u_29, (ref 9): v_u_32, (ref 10): v_u_7, (ref 11): v_u_12, (ref 12): v_u_13, (ref 13): v_u_14, (copy 14): p_u_21, (ref 15): v_u_27, (ref 16): v_u_34 ]]
            v_u_28 = p36
            if v_u_28 then
                p35:set_visible(true)
                v_u_33.Text = v_u_1:comma_value(p36:get_price())
                v_u_30.Image = v_u_1:transparent_assetid()
                v_u_31.Text = v_u_8:get_name_for_shop_item(p36)
                if p36:get_type() == v_u_8.ShopItemType.Coins then
                    v_u_9:currency_type_render_icon(v_u_9.CurrencyType.Coins, v_u_29)
                    v_u_32.Text = "Spend event points to get coins!"
                elseif p36:get_type() == v_u_8.ShopItemType.Stars then
                    v_u_9:currency_type_render_icon(v_u_9.CurrencyType.Stars, v_u_29)
                    v_u_32.Text = "Spend event points to get stars!"
                elseif p36:get_type() == v_u_8.ShopItemType.Song then
                    v_u_7:singleton():render_coverimage_for_key(v_u_29, v_u_30, p36:get_reward_id())
                    v_u_32.Text = "Spend event points to get a copy of this song!"
                elseif p36:get_type() == v_u_8.ShopItemType.Material then
                    v_u_29.Image = v_u_12:singleton():get_material_icon(p36:get_reward_id())
                    local v37 = v_u_12:singleton():get_material(p36:get_reward_id())
                    if v37:is_pet() then
                        v_u_32.Text = "Spend event points to get this Mini! If you already own a copy, it will be stored in your crafting inventory."
                    else
                        v_u_32.Text = "Spend event points to get this item!"
                        if v37:is_tradeable() ~= true then
                            v_u_32.Text = v_u_32.Text .. " (Not Tradeable)"
                        end;
                    end;
                elseif p36:get_type() == v_u_8.ShopItemType.Title then
                    v_u_29.Image = v_u_1:important_assetid()
                    v_u_32.Text = "Spend event points to get this title!"
                elseif p36:get_type() == v_u_8.ShopItemType.Dance then
                    v_u_29.Image = v_u_13:singleton():get_dance_icon_for_id(p36:get_reward_id())
                    v_u_32.Text = "Spend event points to get this dance!"
                elseif p36:get_type() == v_u_8.ShopItemType.Equipment then
                    v_u_29.Image = v_u_14:singleton():get_equipment_for_id(p36:get_reward_id()):get_icon()
                    v_u_32.Text = "Spend event points to get this gear!"
                end;
                if p36:is_repeat() then
                    v_u_31.Text = "(Repeatable) " .. v_u_31.Text
                end;
                if v_u_8:can_playerblob_claim_shop_item(p_u_21._player_blob_manager:get_player_blob(), p36) then
                    v_u_27:set_visible(true)
                    v_u_34.Visible = false
                else
                    v_u_27:set_visible(false)
                    v_u_34.Visible = true
                end;
            else
                p35:set_visible(false)
                return;
            end;
        end;
        v25.set_visible = function(_, p38) --[[ Name: set_visible ]] --[[ Line: 134 ]]
            --[[ Upvalues: (ref 1): v_u_26, (ref 2): v_u_27 ]]
            v_u_26:set_visible(p38)
            v_u_27:set_visible(p38)
        end;
        v25.layout = function(_) --[[ Name: layout ]] --[[ Line: 139 ]]
            --[[ Upvalues: (ref 1): v_u_26 ]]
            v_u_26:layout()
        end;
        v25:cons()
        return v25;
    end
}
local v_u_40 = 0
v20.new = function(_, p_u_41, p_u_42, p_u_43) --[[ Name: new ]] --[[ Line: 149 ]]
    --[[ Upvalues: (copy 1): v_u_10, (copy 2): v_u_3, (copy 3): v_u_2, (copy 4): v_u_4, (copy 5): v_u_8, (copy 6): v_u_11, (ref 7): v_u_40, (copy 8): v_u_39, (copy 9): v_u_6, (copy 10): v_u_5, (copy 11): v_u_15, (copy 12): v_u_16, (copy 13): v_u_17, (ref 14): v_u_19 ]]
    local v44 = v_u_10:new()
    local v_u_45 = nil
    local v_u_46 = nil
    local v_u_47 = nil
    local v_u_48 = nil
    local v_u_49 = nil
    local v_u_50 = nil
    v44.cons = function(p_u_51) --[[ Name: cons ]] --[[ Line: 157 ]]
        --[[ Upvalues: (ref 1): v_u_45, (copy 2): p_u_43, (ref 3): v_u_49, (ref 4): v_u_50, (ref 5): v_u_47, (copy 6): p_u_42, (copy 7): p_u_41, (ref 8): v_u_3, (ref 9): v_u_2, (ref 10): v_u_4, (ref 11): v_u_46, (ref 12): v_u_48, (ref 13): v_u_8, (ref 14): v_u_11, (ref 15): v_u_40, (ref 16): v_u_39 ]]
        v_u_45 = p_u_43.MainSurface.SurfaceGui.Frame.TabShop
        v_u_45.Visible = false
        v_u_49 = v_u_45.PageDisplaySection.CurrentPageDisplay
        v_u_50 = v_u_45.PageDisplaySection.MaxPageDisplay
        v_u_47 = p_u_42:add_cycle_element(p_u_41, 1, v_u_3:new(v_u_2:new(p_u_42, p_u_43.PrimaryPart, p_u_43.TabShopElements.ArrowLeft), p_u_41._spui, function() --[[ Line: 167 ]]
            --[[ Upvalues: (ref 1): p_u_41, (ref 2): v_u_4, (ref 3): v_u_46 ]]
            p_u_41._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
            v_u_46:prev_page()
        end))
        v_u_48 = p_u_42:add_cycle_element(p_u_41, 1, v_u_3:new(v_u_2:new(p_u_42, p_u_43.PrimaryPart, p_u_43.TabShopElements.ArrowRight), p_u_41._spui, function() --[[ Line: 176 ]]
            --[[ Upvalues: (ref 1): p_u_41, (ref 2): v_u_4, (ref 3): v_u_46 ]]
            p_u_41._sfx_manager:play_sfx(v_u_4.SFX_BUTTONPRESS)
            v_u_46:next_page()
        end))
        local v_u_52 = v_u_8:get_event_info(p_u_42:get_event_id()):get_shop_items_list()
        v_u_46 = v_u_11:new():set_fn_get_data_list(function() --[[ Line: 184 ]]
            --[[ Upvalues: (copy 1): v_u_52 ]]
            return v_u_52;
        end):set_fn_set_element_data(function(p53, p54) --[[ Line: 185 ]]
            if p54 == nil then
                p53:set_visible(false)
            else
                p53:set_visible(true)
                p53:set_display_element(p54)
            end;
        end):set_fn_next_prev_visible(function(p55, p56) --[[ Line: 193 ]]
            --[[ Upvalues: (ref 1): v_u_48, (ref 2): v_u_47 ]]
            v_u_48:set_visible(p55)
            v_u_47:set_visible(p56)
        end):set_fn_update_page_display(function(p57, p58) --[[ Line: 197 ]]
            --[[ Upvalues: (ref 1): v_u_49, (ref 2): v_u_50 ]]
            v_u_49.Text = tostring(p57)
            v_u_50.Text = tostring(p58)
        end):set_do_wrap(true):set_i_offset(v_u_40):set_fn_store_i_offset(function(p59) --[[ Line: 203 ]]
            --[[ Upvalues: (ref 1): v_u_40 ]]
            v_u_40 = p59
        end)
        local l_Anchors_0 = p_u_43.TabShopElements.Anchors
        v_u_46:create_list_elements_from_anchors_and_proto({
            l_Anchors_0.Anchor1,
            l_Anchors_0.Anchor2,
            l_Anchors_0.Anchor3,
            l_Anchors_0.Anchor4
        }, p_u_43.TabShopElements.Proto, p_u_43, function(p60) --[[ Line: 217 ]]
            --[[ Upvalues: (ref 1): v_u_39, (ref 2): p_u_41, (copy 3): p_u_51, (ref 4): p_u_42 ]]
            return v_u_39:new(p_u_41, p_u_51, p_u_42, p60);
        end)
        p_u_51:refresh()
    end;
    v44.on_buy_item = function(_, p_u_61) --[[ Name: on_buy_item ]] --[[ Line: 224 ]]
        --[[ Upvalues: (copy 1): p_u_41, (ref 2): v_u_8, (copy 3): p_u_42, (ref 4): v_u_6, (ref 5): v_u_5, (ref 6): v_u_15, (ref 7): v_u_16, (ref 8): v_u_17, (ref 9): v_u_4, (ref 10): v_u_19 ]]
        local function f_do_purchase_event_shop_item() --[[ Name: do_purchase_event_shop_item ]] --[[ Line: 225 ]]
            --[[ Upvalues: (ref 1): p_u_41, (ref 2): v_u_8, (copy 3): p_u_61, (ref 4): p_u_42, (ref 5): v_u_6, (ref 6): v_u_5, (ref 7): v_u_15, (ref 8): v_u_16, (ref 9): v_u_17, (ref 10): v_u_4 ]]
            if v_u_8:playerblob_get_event_points((p_u_41._player_blob_manager:get_player_blob())) < p_u_61:get_price() then
                return p_u_42:prompt_event_point_purchase();
            end;
            local v_u_62 = p_u_41._menus:push_menu(v_u_6:new(p_u_41, p_u_41._spui, p_u_41._menus):set_text("Loading...", "Please wait..."):set_close_button_visible(false))
            p_u_41._evt:wait_on_event_once(v_u_5.EVT_ArtistEvent_ShopPurchase_Server, function(p_u_63, p_u_64, p_u_65) --[[ Line: 236 ]]
                --[[ Upvalues: (ref 1): p_u_41, (copy 2): v_u_62, (ref 3): v_u_6, (ref 4): v_u_15, (ref 5): v_u_16, (ref 6): v_u_17, (ref 7): v_u_8, (ref 8): p_u_61, (ref 9): v_u_4, (ref 10): p_u_42 ]]
                p_u_41._player_blob_manager:do_sync(function() --[[ Line: 237 ]]
                    --[[ Upvalues: (ref 1): p_u_41, (ref 2): v_u_62, (copy 3): p_u_63, (ref 4): v_u_6, (copy 5): p_u_64, (ref 6): v_u_15, (ref 7): v_u_16, (ref 8): v_u_17, (copy 9): p_u_65, (ref 10): v_u_8, (ref 11): p_u_61, (ref 12): v_u_4, (ref 13): p_u_42 ]]
                    p_u_41._menus:remove_menu(v_u_62)
                    if p_u_63 ~= true then
                        return p_u_41._menus:push_menu(v_u_6:new(p_u_41, p_u_41._spui, p_u_41._menus):set_text("Error", (tostring(p_u_64))));
                    end;
                    if v_u_15.UseRewardDescriptionInfoAcquiredUI == true then
                        p_u_41._menus:push_menu(v_u_16:new(p_u_41, p_u_41._spui, p_u_41._menus, v_u_17.RewardInfo:table_to_list(p_u_65)):set_header_text("Bought!"):set_sub_text("Bought from the event shop..."))
                    else
                        p_u_41._menus:push_menu(v_u_6:new(p_u_41, p_u_41._spui, p_u_41._menus):set_text("Claimed!", "Got: " .. v_u_8:get_name_for_shop_item(p_u_61)))
                        p_u_41._sfx_manager:play_sfx(v_u_4.SFX_ACQUIRE)
                    end;
                    p_u_42:update_selected_tab()
                end)
            end)
            p_u_41._evt:fire_event_to_server(v_u_5.EVT_ArtistEvent_ShopPurchase_Client, p_u_42:get_event_id(), p_u_61:get_item_id())
        end;
        if p_u_61:get_type() == v_u_8.ShopItemType.Dance then
            v_u_19:show_dance_preview_menu(p_u_41, p_u_61:get_reward_id(), function() --[[ Line: 266 ]]
                --[[ Upvalues: (copy 1): f_do_purchase_event_shop_item ]]
                f_do_purchase_event_shop_item()
            end)
        else
            f_do_purchase_event_shop_item()
        end;
    end;
    v44.set_visible = function(_, p66) --[[ Name: set_visible ]] --[[ Line: 274 ]]
        --[[ Upvalues: (ref 1): v_u_45, (ref 2): v_u_46 ]]
        v_u_45.Visible = p66
        v_u_46:set_visible(p66)
    end;
    v44.load_data = function(_, p67) --[[ Name: load_data ]] --[[ Line: 278 ]]
        p67()
    end;
    v44.refresh = function(_) --[[ Name: refresh ]] --[[ Line: 279 ]]
        --[[ Upvalues: (ref 1): v_u_46 ]]
        v_u_46:page_update()
    end;
    v44.layout = function(_) --[[ Name: layout ]] --[[ Line: 280 ]]
        --[[ Upvalues: (ref 1): v_u_46 ]]
        v_u_46:layout()
    end;
    v44.requires_reload_on_menu_refocus = function(_) --[[ Name: requires_reload_on_menu_refocus ]] --[[ Line: 281 ]]
        return false;
    end;
    v44.behaviour_update = function(_, _) end;
    v44:cons()
    return v44;
end;
return v20;
