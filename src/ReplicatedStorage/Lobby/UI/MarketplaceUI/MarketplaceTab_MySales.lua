-- Saved by UniversalSynSaveInstance (Join to Copy Games) https://discord.gg/wx4ThpAsmw

-- Decompiled with Medal's Decompiler. (Modified by SignalHub)
-- Decompiled at: 11/8/2025, 4:20:55 PM
-- Cached decompilation

local v_u_1 = require(game.ReplicatedStorage.Shared.SPUtil)
require(game.ReplicatedStorage.Shared.SPDict)
local v_u_2 = require(game.ReplicatedStorage.Shared.SPList)
require(game.ReplicatedStorage.Shared.SPUISystem)
require(game.ReplicatedStorage.Menu.MenuBase)
local v_u_3 = require(game.ReplicatedStorage.Shared.SPUIChild)
local v_u_4 = require(game.ReplicatedStorage.Menu.SPUIChildButton)
require(game.ReplicatedStorage.Shared.CurveUtil)
require(game.ReplicatedStorage.Shared.DebugOut)
require(game.ReplicatedStorage.Menu.MenuSystem)
local v_u_5 = require(game.ReplicatedStorage.Local.SFXManager)
local v_u_6 = require(game.ReplicatedStorage.Shared.SPRemoteEvent)
local v_u_7 = require(game.ReplicatedStorage.Shared.AssertType)
local v_u_8 = require(game.ReplicatedStorage.Lobby.UI.MarketplaceUI.MarketplaceTab)
local v_u_9 = require(game.ReplicatedStorage.PlayerInfo.MarketplaceUtils)
local v_u_10 = require(game.ReplicatedStorage.Crafting.CraftDatabase)
local v_u_11 = require(game.ReplicatedStorage.Crafting.CraftingMaterialBase)
local v_u_12 = require(game.ReplicatedStorage.PlayerInfo.PlayerBlob)
local v_u_13 = require(game.ReplicatedStorage.PlayerInfo.VIPInfo)
local v_u_14 = require(game.ReplicatedStorage.Lobby.Menus.VIPPurchaseUI)
local v_u_15 = require(game.ReplicatedStorage.Avatar.EquipmentUpgradeDatabase)
local v_u_16 = require(game.ReplicatedStorage.PlayerInfo.BoxInfo)
local v_u_17 = require(game.ReplicatedStorage.Lobby.Menus.MaterialSelectUI)
require(game.ReplicatedStorage.Lobby.Menus.TextInputUI)
local v_u_18 = require(game.ReplicatedStorage.Menu.PopupMessageUI)
local v_u_19 = require(game.ReplicatedStorage.Lobby.Menus.ValueInputUI)
local v20 = {}
local v_u_44 = {
    ["new"] = function(_, p_u_21, p_u_22, p_u_23, p_u_24, p_u_25, p_u_26) --[[ Name: new ]] --[[ Line: 297 ]]
        --[[ Upvalues: (copy 1): v_u_3, (copy 2): v_u_4, (copy 3): v_u_5, (copy 4): v_u_10, (copy 5): v_u_1 ]]
        local v28 = {
            ["behaviour_update"] = function(p27, _) --[[ Name: behaviour_update ]] --[[ Line: 370 ]]
                p27:update_active_for_display()
            end
        }
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
        local function f_cons() --[[ Name: cons ]] --[[ Line: 312 ]]
            --[[ Upvalues: (ref 1): v_u_29, (copy 2): p_u_25, (copy 3): p_u_26, (copy 4): p_u_24, (ref 5): v_u_30, (ref 6): v_u_3, (copy 7): p_u_22, (ref 8): v_u_31, (copy 9): p_u_21, (ref 10): v_u_4, (ref 11): v_u_5, (ref 12): v_u_35, (copy 13): p_u_23, (ref 14): v_u_33, (ref 15): v_u_32, (ref 16): v_u_34, (ref 17): v_u_36, (ref 18): v_u_37, (ref 19): v_u_38, (ref 20): v_u_39 ]]
            v_u_29 = p_u_25:Clone()
            v_u_29:SetPrimaryPartCFrame(p_u_26.CFrame)
            v_u_29.Parent = p_u_24
            v_u_30 = v_u_3:new(p_u_22, p_u_24.PrimaryPart, v_u_29.PrimaryPart)
            v_u_31 = p_u_22:add_cycle_element(p_u_21, 1, v_u_4:new(v_u_3:new(v_u_30, v_u_29.PrimaryPart, v_u_29.CancelButton), p_u_21._spui, function() --[[ Line: 321 ]]
                --[[ Upvalues: (ref 1): p_u_21, (ref 2): v_u_5, (ref 3): v_u_35, (ref 4): p_u_23 ]]
                p_u_21._sfx_manager:play_sfx(v_u_5.SFX_MENU_OPEN)
                if v_u_35 ~= nil then
                    p_u_23:cancel_sale(v_u_35)
                end;
            end))
            v_u_33 = v_u_29.MainSurface.SurfaceGui
            v_u_32 = v_u_33.Frame
            v_u_34 = v_u_32.ActiveForDisplay
            v_u_34.Text = ""
            v_u_36 = v_u_32.IconSection.Icon
            v_u_37 = v_u_32.CountDisplay.Display
            v_u_38 = v_u_32.NameDisplay
            v_u_39 = v_u_32.CoinSection.Display
        end;
        v28.update_from_sale = function(p40, p41) --[[ Name: update_from_sale ]] --[[ Line: 340 ]]
            --[[ Upvalues: (ref 1): v_u_35, (ref 2): v_u_36, (ref 3): v_u_10, (ref 4): v_u_37, (ref 5): v_u_38, (ref 6): v_u_39, (ref 7): v_u_1 ]]
            v_u_35 = p41
            if v_u_35 ~= nil then
                v_u_36.Image = v_u_10:singleton():get_material_icon(p41:get_materialid())
                v_u_37.Text = tostring(p41:get_count())
                v_u_38.Text = v_u_10:singleton():get_material_name(p41:get_materialid())
                v_u_38.TextColor3 = v_u_10:singleton():tier_get_color(v_u_10:singleton():get_material_tier(p41:get_materialid()))
                v_u_39.Text = v_u_1:comma_value(p41:get_price())
                p40:update_active_for_display()
            end;
        end;
        v28.update_active_for_display = function(_) --[[ Name: update_active_for_display ]] --[[ Line: 352 ]]
            --[[ Upvalues: (ref 1): v_u_35, (copy 2): p_u_21, (ref 3): v_u_34, (ref 4): v_u_1 ]]
            if v_u_35 ~= nil then
                v_u_34.Text = v_u_1:format_sec_time(p_u_21._player_blob_manager:get_global_time() - v_u_35:get_start_date())
            end;
        end;
        local v_u_42 = true
        v28.set_visible = function(_, p43) --[[ Name: set_visible ]] --[[ Line: 360 ]]
            --[[ Upvalues: (ref 1): v_u_42, (ref 2): v_u_32, (ref 3): v_u_31 ]]
            v_u_42 = p43
            v_u_32.Visible = v_u_42
            v_u_31:set_visible(v_u_42)
        end;
        v28.layout = function(_) --[[ Name: layout ]] --[[ Line: 366 ]]
            --[[ Upvalues: (ref 1): v_u_30 ]]
            v_u_30:layout()
        end;
        f_cons()
        return v28;
    end
}
v20.new = function(_, p_u_45, p_u_46, p_u_47, p_u_48, p_u_49) --[[ Name: new ]] --[[ Line: 32 ]]
    --[[ Upvalues: (copy 1): v_u_8, (copy 2): v_u_2, (copy 3): v_u_7, (copy 4): v_u_4, (copy 5): v_u_3, (copy 6): v_u_5, (copy 7): v_u_14, (copy 8): v_u_44, (copy 9): v_u_17, (copy 10): v_u_10, (copy 11): v_u_11, (copy 12): v_u_16, (copy 13): v_u_15, (copy 14): v_u_19, (copy 15): v_u_9, (copy 16): v_u_1, (copy 17): v_u_12, (copy 18): v_u_18, (copy 19): v_u_6, (copy 20): v_u_13 ]]
    local v_u_50 = v_u_8:new()
    v_u_50.get_tab = function(_) --[[ Name: get_tab ]] --[[ Line: 34 ]]
        --[[ Upvalues: (ref 1): v_u_8 ]]
        return v_u_8.Tab.MySales;
    end;
    local v_u_51 = nil
    local v_u_52 = nil
    local v_u_53 = nil
    local v_u_54 = nil
    local v_u_55 = nil
    local v_u_56 = v_u_2:new()
    local function f_cons() --[[ Name: cons ]] --[[ Line: 43 ]]
        --[[ Upvalues: (ref 1): v_u_51, (copy 2): p_u_49, (ref 3): v_u_7, (copy 4): v_u_50, (ref 5): v_u_52, (copy 6): p_u_48, (copy 7): p_u_45, (ref 8): v_u_4, (ref 9): v_u_3, (copy 10): p_u_46, (ref 11): v_u_5, (ref 12): v_u_53, (copy 13): p_u_47, (ref 14): v_u_14, (ref 15): v_u_55, (ref 16): v_u_54 ]]
        v_u_51 = p_u_49.MainSurface.SurfaceGui.Frame.LoadedFrame.MySalesSection
        v_u_7:is_non_nil(v_u_51)
        v_u_50:init_list_element_protos()
        v_u_52 = p_u_48:add_cycle_element(p_u_45, 1, v_u_4:new(v_u_3:new(p_u_48, p_u_49.PrimaryPart, p_u_49.MySalesElements.CreateSaleButton), p_u_46, function() --[[ Line: 51 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_5, (ref 3): v_u_50 ]]
            p_u_45._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            v_u_50:on_create_sale_pressed()
        end))
        v_u_4:button_add_enabled_anim(v_u_52, function() --[[ Line: 56 ]]
            --[[ Upvalues: (ref 1): p_u_48 ]]
            return p_u_48:get_alpha();
        end)
        v_u_53 = p_u_48:add_cycle_element(p_u_45, 1, v_u_4:new(v_u_3:new(p_u_48, p_u_49.PrimaryPart, p_u_49.MySalesElements.VIPButton), p_u_46, function() --[[ Line: 61 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): v_u_5, (ref 3): p_u_47, (ref 4): v_u_14, (ref 5): p_u_46, (ref 6): p_u_48 ]]
            p_u_45._sfx_manager:play_sfx(v_u_5.SFX_BUTTONPRESS)
            p_u_47:push_menu(v_u_14:new(p_u_45, p_u_46, p_u_47))
            p_u_47:remove_menu(p_u_48)
        end))
        v_u_55 = v_u_51.ActiveSalesDisplay
        v_u_55.Text = ""
        v_u_54 = v_u_51.SelectedItemSection.StarSection.Display
        v_u_54.Text = ""
        v_u_50:set_visible(false)
    end;
    v_u_50.init_list_element_protos = function(p57) --[[ Name: init_list_element_protos ]] --[[ Line: 76 ]]
        --[[ Upvalues: (copy 1): p_u_49, (ref 2): v_u_2, (ref 3): v_u_44, (copy 4): p_u_45, (copy 5): p_u_48, (copy 6): v_u_56 ]]
        local l_MySaleElementProto_0 = p_u_49.MySalesElements.MySaleElementProto
        l_MySaleElementProto_0.Parent = nil
        local v58 = v_u_2:new():push_back_table_list({
            p_u_49.MySalesElements.Anchors.Anchor1,
            p_u_49.MySalesElements.Anchors.Anchor2,
            p_u_49.MySalesElements.Anchors.Anchor3,
            p_u_49.MySalesElements.Anchors.Anchor4,
            p_u_49.MySalesElements.Anchors.Anchor5,
            p_u_49.MySalesElements.Anchors.Anchor6,
            p_u_49.MySalesElements.Anchors.Anchor7,
            p_u_49.MySalesElements.Anchors.Anchor8
        })
        for v59 = 1, v58:count() do
            v58:get(v59).Parent = nil
            v_u_56:push_back((v_u_44:new(p_u_45, p_u_48, p57, p_u_49, l_MySaleElementProto_0, v58:get(v59))))
        end;
    end;
    v_u_50.on_create_sale_pressed = function(p_u_60) --[[ Name: on_create_sale_pressed ]] --[[ Line: 96 ]]
        --[[ Upvalues: (copy 1): p_u_47, (ref 2): v_u_17, (copy 3): p_u_45, (copy 4): p_u_46, (ref 5): v_u_7, (ref 6): v_u_10, (ref 7): v_u_11, (ref 8): v_u_16, (ref 9): v_u_15, (ref 10): v_u_19, (ref 11): v_u_9, (ref 12): v_u_1, (ref 13): v_u_12, (ref 14): v_u_18 ]]
        p_u_47:push_menu(v_u_17:new(p_u_45, p_u_46, p_u_47, function(p_u_61, p_u_62) --[[ Line: 97 ]]
            --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_10, (ref 3): v_u_11, (ref 4): v_u_16, (ref 5): v_u_15, (ref 6): p_u_45, (ref 7): v_u_19, (ref 8): v_u_9, (ref 9): v_u_1, (ref 10): v_u_12, (ref 11): p_u_47, (ref 12): v_u_18, (ref 13): p_u_46, (copy 14): p_u_60 ]]
            v_u_7:is_true(v_u_10:singleton():contains_material(p_u_61))
            v_u_7:is_int_greater_than(p_u_62, 1)
            string.format("Enter price (in Coins) of your new sale of %d %s(s).", p_u_62, v_u_10:singleton():get_material_name(p_u_61))
            local v63 = v_u_10:singleton():get_material_tier(p_u_61)
            local v64 = v63 == v_u_11.Tier.T1 and 50 or (v63 == v_u_11.Tier.T2 and 100 or (v63 == v_u_11.Tier.T3 and 200 or (v63 == v_u_11.Tier.T4 and 500 or 1500)))
            local v65 = v_u_10:singleton():get_material_type(p_u_61)
            local v66
            if v65 == v_u_11.Type.Box then
                v66 = v_u_16:get_materialid_box_type(p_u_61) == v_u_11.BoxType.SmallNote and 100 or (v_u_16:get_materialid_box_type(p_u_61) == v_u_11.BoxType.MediumNote and 150 or (v_u_16:get_materialid_box_type(p_u_61) == v_u_11.BoxType.LargeNote and 200 or (v_u_16:get_materialid_box_type(p_u_61) == v_u_11.BoxType.Gem and 500 or v64 * 4)))
            elseif v65 == v_u_11.Type.Pet then
                v66 = v64 * 5
            elseif v65 == v_u_11.Type.FeverIcon then
                v66 = 2000
            elseif v65 == v_u_11.Type.Blueprint then
                v66 = v64 * 4
            else
                v66 = p_u_61 == v_u_15:singleton():get_upgrade_boost_material_id() and 1000 or (p_u_61 == v_u_15:singleton():get_upgrade_protect_material_id() and 500 or v64)
            end;
            local v67 = v66 * p_u_62
            local v68 = p_u_45
            v68._menus:push_menu(v_u_19:new(v68, v68._spui, v68._menus, v67, function(p_u_69) --[[ Line: 146 ]]
                --[[ Upvalues: (ref 1): v_u_7, (ref 2): p_u_45, (ref 3): v_u_9, (ref 4): v_u_1, (copy 5): p_u_62, (ref 6): v_u_10, (copy 7): p_u_61, (ref 8): v_u_12, (ref 9): p_u_47, (ref 10): v_u_18, (ref 11): p_u_46, (ref 12): p_u_60 ]]
                v_u_7:is_int(p_u_69)
                local v70 = p_u_45._player_blob_manager:get_player_blob()
                v_u_9:get_sales_list_from_playerblob(v70, v_u_1:get_local_username(), v_u_1:get_local_userid())
                p_u_47:push_menu(v_u_18:new(p_u_45, p_u_46, p_u_47):set_text("Confirm", (string.format("Create sale of %d %s(s) for %d Coin(s)?\nThis will cost %d Star(s). (You have: %d)", p_u_62, v_u_10:singleton():get_material_name(p_u_61), p_u_69, v_u_9:get_sale_create_cost_for_playerblob_and_day_and_week(v70, p_u_45._player_blob_manager:get_dayid(), p_u_45._player_blob_manager:get_weekid()), v_u_12:get_star_currency(v70)))):set_okay_button_fn(function() --[[ Line: 161 ]]
                    --[[ Upvalues: (ref 1): p_u_60, (ref 2): p_u_61, (ref 3): p_u_62, (copy 4): p_u_69 ]]
                    p_u_60:create_sale(p_u_61, p_u_62, p_u_69)
                end))
            end):set_value_increment(50):set_reset_value(v67):set_range_min_max(1, v_u_1:input_max_number()):set_title_sub_text("Sale Price", string.format("Enter price in coins for you new sale of x%d %s.", p_u_62, v_u_10:singleton():get_material_name(p_u_61))):set_value_display_info_fn(function(p71) --[[ Line: 172 ]]
                --[[ Upvalues: (ref 1): v_u_1 ]]
                return v_u_1:comma_value(p71), "Coins";
            end))
        end):set_fn_material_ids_filter(function(p72) --[[ Line: 175 ]]
            --[[ Upvalues: (ref 1): v_u_10 ]]
            return v_u_10:singleton():is_material_tradeable(p72) ~= true;
        end))
    end;
    v_u_50.create_sale = function(p_u_73, p74, p75, p76) --[[ Name: create_sale ]] --[[ Line: 180 ]]
        --[[ Upvalues: (ref 1): v_u_7, (ref 2): v_u_10, (copy 3): p_u_47, (ref 4): v_u_18, (copy 5): p_u_45, (copy 6): p_u_46, (ref 7): v_u_6 ]]
        v_u_7:is_true(v_u_10:singleton():contains_material(p74))
        v_u_7:is_int_greater_than(p75, 1)
        v_u_7:is_int_greater_than(p76, 0)
        local v_u_77 = p_u_47:push_menu(v_u_18:new(p_u_45, p_u_46, p_u_47):set_text("Creating Sale", "Please wait..."):set_close_button_visible(false))
        p_u_45._evt:wait_on_event_once(v_u_6.EVT_Marketplace_ServerCreateNewSaleResponse, function() --[[ Line: 186 ]]
            --[[ Upvalues: (ref 1): p_u_45, (ref 2): p_u_47, (copy 3): v_u_77, (copy 4): p_u_73 ]]
            p_u_45._player_blob_manager:do_sync(function() --[[ Line: 187 ]]
                --[[ Upvalues: (ref 1): p_u_47, (ref 2): v_u_77, (ref 3): p_u_73 ]]
                p_u_47:remove_menu(v_u_77)
                p_u_73:refresh_state()
            end)
        end)
        p_u_45._evt:fire_event_to_server(v_u_6.EVT_Marketplace_ClientCreateNewSale, p74, p75, p76)
    end;
    v_u_50.cancel_sale = function(p_u_78, p_u_79) --[[ Name: cancel_sale ]] --[[ Line: 195 ]]
        --[[ Upvalues: (ref 1): v_u_10, (copy 2): p_u_47, (ref 3): v_u_18, (copy 4): p_u_45, (copy 5): p_u_46, (ref 6): v_u_6 ]]
        p_u_47:push_menu(v_u_18:new(p_u_45, p_u_46, p_u_47):set_text("Confirm", (string.format("Cancel sale of %d %s(s)?", p_u_79:get_count(), v_u_10:singleton():get_material_name(p_u_79:get_materialid())))):set_okay_button_fn(function() --[[ Line: 197 ]]
            --[[ Upvalues: (ref 1): p_u_47, (ref 2): v_u_18, (ref 3): p_u_45, (ref 4): p_u_46, (ref 5): v_u_6, (copy 6): p_u_78, (copy 7): p_u_79 ]]
            local v_u_80 = p_u_47:push_menu(v_u_18:new(p_u_45, p_u_46, p_u_47):set_text("Canceling Sale", "Please wait..."):set_close_button_visible(false))
            p_u_45._evt:wait_on_event_once(v_u_6.EVT_Marketplace_ServerCancelSaleResponse, function(p81, p82) --[[ Line: 199 ]]
                --[[ Upvalues: (ref 1): p_u_47, (copy 2): v_u_80, (ref 3): v_u_18, (ref 4): p_u_45, (ref 5): p_u_46, (ref 6): p_u_78 ]]
                if p81 == true then
                    p_u_45._player_blob_manager:do_sync(function() --[[ Line: 206 ]]
                        --[[ Upvalues: (ref 1): p_u_47, (ref 2): v_u_80, (ref 3): p_u_78 ]]
                        p_u_47:remove_menu(v_u_80)
                        p_u_78:refresh_state()
                    end)
                else
                    p_u_47:remove_menu(v_u_80)
                    p_u_47:push_menu(v_u_18:new(p_u_45, p_u_46, p_u_47):set_text("Error", p82))
                    p_u_78:refresh_state()
                end;
            end)
            p_u_45._evt:fire_event_to_server(v_u_6.EVT_Marketplace_ClientCancelSale, p_u_79:get_index())
        end))
    end;
    local v_u_83 = false
    v_u_50.set_visible = function(p84, p85) --[[ Name: set_visible ]] --[[ Line: 216 ]]
        --[[ Upvalues: (ref 1): v_u_83 ]]
        v_u_83 = p85
        p84:refresh_state()
    end;
    v_u_50.layout = function(_) --[[ Name: layout ]] --[[ Line: 221 ]]
        --[[ Upvalues: (copy 1): v_u_56 ]]
        for v86 = 1, v_u_56:count() do
            v_u_56:get(v86):layout()
        end;
    end;
    v_u_50.behaviour_update = function(_, p87) --[[ Name: behaviour_update ]] --[[ Line: 227 ]]
        --[[ Upvalues: (copy 1): v_u_56 ]]
        for v88 = 1, v_u_56:count() do
            v_u_56:get(v88):behaviour_update(p87)
        end;
    end;
    v_u_50.refresh_state = function(_) --[[ Name: refresh_state ]] --[[ Line: 233 ]]
        --[[ Upvalues: (copy 1): p_u_48, (ref 2): v_u_83, (ref 3): v_u_51, (copy 4): p_u_45, (ref 5): v_u_9, (ref 6): v_u_1, (ref 7): v_u_52, (ref 8): v_u_12, (ref 9): v_u_54, (ref 10): v_u_55, (ref 11): v_u_13, (ref 12): v_u_53, (copy 13): v_u_56 ]]
        p_u_48:get_empty_display().Visible = false
        if v_u_83 == true then
            v_u_51.Visible = true
            local v89 = p_u_45._player_blob_manager:get_player_blob()
            local v90 = v_u_9:get_sales_list_from_playerblob(v89, v_u_1:get_local_username(), v_u_1:get_local_userid())
            v90:sort(function(p91, p92) --[[ Line: 240 ]]
                return p91:get_index() - p92:get_index();
            end)
            local v93 = v_u_9:get_sale_create_cost_for_playerblob_and_day_and_week(v89, p_u_45._player_blob_manager:get_dayid(), p_u_45._player_blob_manager:get_weekid())
            if v90:count() < v_u_9:get_player_max_sale_count() then
                v_u_52:set_visible(true)
                if v93 <= v_u_12:get_star_currency(v89) then
                    v_u_52:set_enabled(true)
                else
                    v_u_52:set_enabled(false)
                end;
                v_u_54.Text = tostring(v93)
            else
                v_u_54.Text = "-"
                v_u_52:set_visible(false)
            end;
            v_u_55.Text = string.format("%d Active Sale(s)", v90:count())
            if v90:count() == 0 then
                p_u_48:get_empty_display().Visible = true
                p_u_48:get_empty_display().Text = "You have no active sales."
            end;
            if v_u_13:playerblob_has_vip_for_current_day(v89, p_u_45:get_current_dayid()) then
                v_u_53:set_visible(false)
            else
                v_u_53:set_visible(true)
            end;
            for v94 = 1, v_u_56:count() do
                if v94 <= v90:count() then
                    v_u_56:get(v94):set_visible(true)
                    v_u_56:get(v94):update_from_sale(v90:get(v94))
                else
                    v_u_56:get(v94):set_visible(false)
                    v_u_56:get(v94):update_from_sale(nil)
                end;
            end;
        else
            v_u_51.Visible = false
            v_u_52:set_visible(false)
            v_u_53:set_visible(false)
            for v95 = 1, v_u_56:count() do
                v_u_56:get(v95):set_visible(false)
            end;
        end;
    end;
    f_cons()
    return v_u_50;
end;
return v20;
